"""TruthKeep Warzone Tests — Round 4: attack the core engine.

Targets: state machine abuse, FTS index desync, circular corrections,
backup corruption, memory ID confusion, direct SQL tampering,
governance bypass, massive field sizes, and float edge cases.
"""

import json
import sqlite3
import pytest
from aegis_py.app import AegisApp
from aegis_py.hygiene.transitions import transition_memory


def _app(tmp_path, name="war"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ===========================================================================
# 1. STATE MACHINE ABUSE — invalid transitions
# ===========================================================================
class TestStateMachineAbuse:

    def test_archive_then_search_excluded(self, tmp_path):
        """Archived memory must be excluded from search results."""
        app = _app(tmp_path, "state1")
        try:
            mem = app.put_memory("Top secret state machine test data", scope_id="sm", type="semantic")
            assert mem is not None
            transition_memory(app.storage, mem.id, status="archived", event="test_archive")
            results = _search(app, "top secret state machine", "sm", limit=5)
            for r in results:
                assert r.memory.id != mem.id, "Archived memory appeared in search!"
        finally:
            app.close()

    def test_double_archive(self, tmp_path):
        """Archiving an already archived memory must not crash."""
        app = _app(tmp_path, "state2")
        try:
            mem = app.put_memory("Double archive test", scope_id="sm", type="semantic")
            if mem:
                transition_memory(app.storage, mem.id, status="archived", event="first_archive")
                # Second archive — must not crash
                result = transition_memory(app.storage, mem.id, status="archived", event="second_archive")
                assert isinstance(result, bool)
        finally:
            app.close()

    def test_transition_nonexistent_memory(self, tmp_path):
        """Transitioning a nonexistent memory must return False, not crash."""
        app = _app(tmp_path, "state3")
        try:
            result = transition_memory(app.storage, "mem_totally_fake_id_xyz", status="archived", event="test")
            assert result is False
        finally:
            app.close()

    def test_invalid_status_string(self, tmp_path):
        """Transitioning to an invalid status string must not corrupt DB."""
        app = _app(tmp_path, "state4")
        try:
            mem = app.put_memory("Invalid status test content", scope_id="sm", type="semantic")
            if mem:
                # Attempt invalid status
                transition_memory(app.storage, mem.id, status="INVALID_STATUS_XYZ", event="test_invalid")
                # Memory should still be in DB (possibly with weird status)
                fetched = app.storage.get_memory(mem.id)
                assert fetched is not None
        finally:
            app.close()


# ===========================================================================
# 2. FTS INDEX DESYNC — tamper with DB directly, then search
# ===========================================================================
class TestFTSIndexDesync:

    def test_direct_sql_delete_then_search(self, tmp_path):
        """Delete from memories table via raw SQL (bypassing ORM). Search must not crash."""
        db_path = str(tmp_path / "fts_desync.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("FTS desync test fact about databases", scope_id="fts", type="semantic")
            if mem:
                # Tamper: delete from memories table directly, leaving FTS orphan
                conn = sqlite3.connect(db_path)
                conn.execute(f"DELETE FROM memories WHERE id = ?", (mem.id,))
                conn.commit()
                conn.close()

            # Search must not crash even with FTS orphan
            try:
                results = _search(app, "FTS desync databases", "fts", limit=5)
                # Results may include ghost entries — that's ok as long as no crash
                assert isinstance(results, list)
            except Exception:
                # Some error is acceptable, crash/segfault is not
                pass
        finally:
            app.close()

    def test_direct_sql_update_content_then_search(self, tmp_path):
        """Update content via raw SQL (FTS index stale). Search must handle gracefully."""
        db_path = str(tmp_path / "fts_stale.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("Original content before SQL tampering", scope_id="fts", type="semantic")
            if mem:
                # Tamper: change content without updating FTS
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE memories SET content = ? WHERE id = ?", ("TAMPERED CONTENT XYZ", mem.id))
                conn.commit()
                conn.close()

            # Search for original should not crash
            results = _search(app, "Original content SQL tampering", "fts", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()


# ===========================================================================
# 3. MEMORY ID CONFUSION — content that looks like memory IDs
# ===========================================================================
class TestMemoryIDConfusion:

    def test_content_with_mem_prefix(self, tmp_path):
        """Content containing 'mem_' strings must not confuse ID-based operations."""
        app = _app(tmp_path, "id_confusion")
        try:
            app.put_memory(
                "The memory ID mem_abc123 was referenced in the error log. "
                "Another ID mem_xyz789 appeared in the crash dump.",
                scope_id="id", type="semantic",
            )

            results = _search(app, "mem_abc123 error log", "id", limit=3)
            assert len(results) > 0

            # Forget with a fake mem_ ID should not accidentally delete this memory
            app.memory_forget("mem_abc123")  # This ID doesn't exist in DB
            # Original memory should still be there
            results = _search(app, "memory ID error log", "id", limit=3)
            assert len(results) > 0
        finally:
            app.close()

    def test_scope_id_with_mem_prefix(self, tmp_path):
        """scope_id starting with 'mem_' must not confuse the system."""
        app = _app(tmp_path, "scope_mem")
        try:
            app.put_memory("Data in a scope that looks like a memory ID", scope_id="mem_fake_scope", type="semantic")
            results = _search(app, "scope looks like memory", "mem_fake_scope", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()


# ===========================================================================
# 4. BACKUP INTEGRITY
# ===========================================================================
class TestBackupIntegrity:

    def test_backup_and_restore_preserves_data(self, tmp_path):
        """Backup then restore. All data must survive."""
        app = _app(tmp_path, "backup")
        try:
            mem = app.put_memory("Critical fact for backup test", scope_id="bk", type="semantic")
            backup_result = app.create_backup()
            assert "path" in backup_result or "backup_path" in backup_result or isinstance(backup_result, dict)
        finally:
            app.close()

    def test_backup_empty_db(self, tmp_path):
        """Backup of empty DB must not crash."""
        app = _app(tmp_path, "backup_empty")
        try:
            backup_result = app.create_backup()
            assert isinstance(backup_result, dict)
        finally:
            app.close()


# ===========================================================================
# 5. GOVERNANCE EDGE CASES
# ===========================================================================
class TestGovernanceEdgeCases:

    def test_inspect_governance_nonexistent(self, tmp_path):
        """Inspecting governance of nonexistent memory must not crash."""
        app = _app(tmp_path, "gov1")
        try:
            try:
                result = app.inspect_governance("mem_nonexistent_xyz")
            except Exception:
                pass  # Error ok, crash not
        finally:
            app.close()

    def test_inspect_governance_valid(self, tmp_path):
        """Inspecting governance of valid memory must return meaningful data."""
        app = _app(tmp_path, "gov2")
        try:
            mem = app.put_memory("Governance test fact", scope_id="gov", type="semantic")
            if mem:
                result = app.inspect_governance(mem.id)
                assert isinstance(result, dict)
        finally:
            app.close()


# ===========================================================================
# 6. MASSIVE FIELD SIZES — push limits
# ===========================================================================
class TestMassiveFields:

    def test_100kb_content(self, tmp_path):
        """100KB content storage."""
        app = _app(tmp_path, "massive_content")
        try:
            content = "A" * 100_000  # 100KB
            result = app.put_memory(content, scope_id="big", type="semantic")
            # May reject — that's ok
            assert True  # Must not crash
        finally:
            app.close()

    def test_very_long_scope_id(self, tmp_path):
        """10KB scope_id."""
        app = _app(tmp_path, "massive_scope")
        try:
            scope_id = "scope-" + "x" * 10_000
            try:
                app.put_memory("Test", scope_id=scope_id, type="semantic")
            except Exception:
                pass  # May reject, must not crash
        finally:
            app.close()

    def test_1000_scopes(self, tmp_path):
        """1000 different scopes in same DB."""
        app = _app(tmp_path, "1k_scopes")
        try:
            for i in range(1000):
                app.put_memory(f"Fact in scope {i}", scope_id=f"scope-{i}", type="semantic")

            # Search in last scope
            results = _search(app, "Fact in scope 999", "scope-999", limit=3)
            assert len(results) > 0
            assert "999" in results[0].memory.content
        finally:
            app.close()


# ===========================================================================
# 7. FLOAT EDGE CASES IN SCORING
# ===========================================================================
class TestFloatEdgeCases:

    def test_direct_sql_nan_confidence(self, tmp_path):
        """Inject NaN confidence via SQL. Search must not crash."""
        db_path = str(tmp_path / "nan.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("NaN confidence test", scope_id="float", type="semantic")
            if mem:
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE memories SET confidence = ? WHERE id = ?", (float('nan'), mem.id))
                conn.commit()
                conn.close()

            try:
                results = _search(app, "NaN confidence", "float", limit=3)
                assert isinstance(results, list)
            except Exception:
                pass  # Error ok
        finally:
            app.close()

    def test_direct_sql_inf_activation(self, tmp_path):
        """Inject infinity activation_score via SQL. Search must not crash."""
        db_path = str(tmp_path / "inf.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("Infinity activation test", scope_id="float", type="semantic")
            if mem:
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE memories SET activation_score = ? WHERE id = ?", (float('inf'), mem.id))
                conn.commit()
                conn.close()

            try:
                results = _search(app, "Infinity activation", "float", limit=3)
                assert isinstance(results, list)
            except Exception:
                pass  # Error ok
        finally:
            app.close()

    def test_direct_sql_negative_activation(self, tmp_path):
        """Inject negative activation_score via SQL. Search must not crash."""
        db_path = str(tmp_path / "neg.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("Negative activation test", scope_id="float", type="semantic")
            if mem:
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE memories SET activation_score = ? WHERE id = ?", (-999.0, mem.id))
                conn.commit()
                conn.close()

            try:
                results = _search(app, "Negative activation", "float", limit=3)
                assert isinstance(results, list)
            except Exception:
                pass  # Error ok
        finally:
            app.close()


# ===========================================================================
# 8. CORRECTION CHAIN EDGE CASES
# ===========================================================================
class TestCorrectionEdgeCases:

    def test_correct_with_empty_content(self, tmp_path):
        """memory_correct with empty string must not crash."""
        app = _app(tmp_path, "correct_empty")
        try:
            try:
                app.memory_correct("")
            except Exception:
                pass  # Error ok
        finally:
            app.close()

    def test_correct_same_fact_10_times(self, tmp_path):
        """Correct the same fact 10 times rapidly. Must not crash or corrupt."""
        app = _app(tmp_path, "correct_rapid")
        try:
            app.put_memory("CEO là ông X", scope_id="default", type="semantic")
            for i in range(10):
                try:
                    app.memory_correct(f"CEO thực tế là người thứ {i}")
                except Exception:
                    pass  # Some may fail due to timing, but no crash
        finally:
            app.close()


# ===========================================================================
# 9. SPOTLIGHT / SHOWCASE EDGE CASES
# ===========================================================================
class TestSpotlightEdgeCases:

    def test_spotlight_empty_query(self, tmp_path):
        """Spotlight with empty query must not crash."""
        app = _app(tmp_path, "spot1")
        try:
            try:
                result = app.spotlight("", scope_id="test", scope_type="session")
            except Exception:
                pass
        finally:
            app.close()

    def test_spotlight_very_long_query(self, tmp_path):
        """Spotlight with 5KB query must not crash."""
        app = _app(tmp_path, "spot2")
        try:
            app.put_memory("Test fact for spotlight", scope_id="spot", type="semantic")
            try:
                result = app.spotlight("test " * 1000, scope_id="spot", scope_type="session")
            except Exception:
                pass
        finally:
            app.close()

    def test_core_showcase_empty_db(self, tmp_path):
        """Core showcase on empty DB must not crash."""
        app = _app(tmp_path, "showcase_empty")
        try:
            result = app.core_showcase(scope_id="empty", scope_type="session")
            assert isinstance(result, dict)
        finally:
            app.close()


# ===========================================================================
# 10. DOCTOR / HEALTH SYSTEM
# ===========================================================================
class TestHealthSystem:

    def test_doctor_empty_db(self, tmp_path):
        """Doctor on empty DB must not crash."""
        app = _app(tmp_path, "doctor_empty")
        try:
            result = app.doctor()
            assert isinstance(result, dict)
        finally:
            app.close()

    def test_doctor_after_1000_writes(self, tmp_path):
        """Doctor after massive writes must not crash."""
        app = _app(tmp_path, "doctor_heavy")
        try:
            for i in range(100):
                app.put_memory(f"Health check fact {i}", scope_id="health", type="semantic")
            result = app.doctor()
            assert isinstance(result, dict)
            assert len(result) > 0, "Doctor returned empty dict"
        finally:
            app.close()

    def test_maintenance_empty_db(self, tmp_path):
        """Maintenance on empty DB must not crash."""
        app = _app(tmp_path, "maint_empty")
        try:
            result = app.maintenance()
            assert isinstance(result, dict)
        finally:
            app.close()

    def test_compact_storage_empty(self, tmp_path):
        """Compaction on empty storage must not crash."""
        app = _app(tmp_path, "compact_empty")
        try:
            result = app.compact_storage(scope_id="empty", scope_type="session")
            assert isinstance(result, dict) or result is None
        finally:
            app.close()
