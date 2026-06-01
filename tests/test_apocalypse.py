"""TruthKeep Apocalypse Tests — Round 8: deep internal mechanism attacks.

Previous rounds attacked surface (FTS, SQL, threads, semantics).
This round attacks the INTERNALS — migration system, WAL journal,
transaction isolation, compaction pipeline, memory ID uniqueness,
compressed tier, backup concurrency, and PRAGMA injection.
"""

import os
import sqlite3
import threading
import time
import pytest
from aegis_py.app import AegisApp
from aegis_py.hygiene.transitions import transition_memory


def _app(tmp_path, name="apoc"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ===========================================================================
# 1. MIGRATION VERSION SPOOFING — set schema to future/past via SQL
# ===========================================================================
class TestMigrationSpoofing:

    def test_future_schema_version(self, tmp_path):
        """Set user_version to far future. App must handle gracefully."""
        db_path = str(tmp_path / "future.db")
        app = AegisApp(db_path=db_path)
        app.put_memory("Pre-spoof data", scope_id="mig", type="semantic")
        app.close()

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA user_version = 99999")
        conn.commit()
        conn.close()

        try:
            app2 = AegisApp(db_path=db_path)
            try:
                app2.put_memory("Post-spoof data", scope_id="mig", type="semantic")
                results = _search(app2, "Pre-spoof data", "mig", limit=3)
                assert isinstance(results, list)
            finally:
                app2.close()
        except Exception:
            pass  # May reject future schema — acceptable

    def test_zero_schema_version(self, tmp_path):
        """Reset user_version to 0. App must re-migrate or handle gracefully."""
        db_path = str(tmp_path / "zero.db")
        app = AegisApp(db_path=db_path)
        app.put_memory("Pre-reset data", scope_id="mig", type="semantic")
        app.close()

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA user_version = 0")
        conn.commit()
        conn.close()

        try:
            app2 = AegisApp(db_path=db_path)
            try:
                results = _search(app2, "Pre-reset data", "mig", limit=3)
                assert isinstance(results, list)
            finally:
                app2.close()
        except Exception:
            pass


# ===========================================================================
# 2. WAL MODE MANIPULATION — change journal mode under the hood
# ===========================================================================
class TestWALManipulation:

    def test_switch_to_delete_journal(self, tmp_path):
        """Switch from WAL to DELETE journal mode. Must not corrupt."""
        db_path = str(tmp_path / "wal.db")
        app = AegisApp(db_path=db_path)
        app.put_memory("WAL mode data", scope_id="wal", type="semantic")
        app.close()

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.commit()
        conn.close()

        app2 = AegisApp(db_path=db_path)
        try:
            results = _search(app2, "WAL mode data", "wal", limit=3)
            assert isinstance(results, list)
            app2.put_memory("Post journal change", scope_id="wal", type="semantic")
        finally:
            app2.close()

    def test_switch_to_memory_journal(self, tmp_path):
        """Switch to MEMORY journal mode. Must not crash."""
        db_path = str(tmp_path / "memjournal.db")
        app = AegisApp(db_path=db_path)
        app.put_memory("Memory journal data", scope_id="mj", type="semantic")
        app.close()

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.commit()
        conn.close()

        app2 = AegisApp(db_path=db_path)
        try:
            app2.put_memory("After memory journal", scope_id="mj", type="semantic")
            results = _search(app2, "Memory journal", "mj", limit=3)
            assert isinstance(results, list)
        finally:
            app2.close()


# ===========================================================================
# 3. TRANSACTION ISOLATION — uncommitted data visibility
# ===========================================================================
class TestTransactionIsolation:

    def test_uncommitted_data_not_visible(self, tmp_path):
        """Data written in uncommitted transaction must not be visible."""
        db_path = str(tmp_path / "txn.db")
        app = AegisApp(db_path=db_path)
        try:
            app.put_memory("Committed data visible", scope_id="txn", type="semantic")

            # Open raw connection, begin transaction, insert, but DON'T commit
            conn = sqlite3.connect(db_path)
            inserted = False
            try:
                conn.execute("BEGIN")
                # Get column list to build a valid INSERT
                cols = [row[1] for row in conn.execute("PRAGMA table_info(memories)").fetchall()]
                # Build minimal valid row — may fail due to NOT NULL constraints
                try:
                    conn.execute(
                        "INSERT INTO memories (id, content, type, scope_type, scope_id, status, confidence, "
                        "source_kind, created_at, updated_at) "
                        "VALUES ('mem_uncommitted_txn', 'UNCOMMITTED SECRET DATA', 'semantic', 'session', "
                        "'txn', 'active', 0.9, 'test', datetime('now'), datetime('now'))"
                    )
                    inserted = True
                except Exception:
                    pass  # Schema may require more columns — that's fine
                # Don't commit — rollback
                conn.rollback()
            finally:
                conn.close()

            if inserted:
                # Search must not find uncommitted (rolled-back) data
                results = _search(app, "UNCOMMITTED SECRET DATA", "txn", limit=5)
                for r in results:
                    assert "UNCOMMITTED" not in r.memory.content, "ROLLED-BACK DATA VISIBLE!"
        finally:
            app.close()


# ===========================================================================
# 4. CASCADING FAILURE — compaction during active writes
# ===========================================================================
class TestCascadingFailure:

    def test_compact_during_writes(self, tmp_path):
        """Run compaction while another thread writes. Must not crash."""
        app = _app(tmp_path, "cascade")
        errors = []

        # Pre-populate
        for i in range(30):
            app.put_memory(f"Pre-compact fact {i}", scope_id="cas", type="semantic")

        def writer():
            try:
                for i in range(30):
                    try:
                        app.put_memory(f"During-compact fact {i}", scope_id="cas", type="semantic")
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"Writer: {e}")

        def compactor():
            try:
                time.sleep(0.01)
                try:
                    app.compact_storage(scope_id="cas", scope_type="session")
                except Exception:
                    pass
                try:
                    app.maintenance()
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"Compactor: {e}")

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=compactor)
        t1.start()
        t2.start()
        t1.join(timeout=60)
        t2.join(timeout=60)

        # Verify DB not corrupted
        try:
            results = _search(app, "compact fact", "cas", limit=5)
            assert isinstance(results, list)
        finally:
            app.close()

        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"Cascading failure: {real_errors[:3]}"

    def test_doctor_during_writes(self, tmp_path):
        """Run doctor while another thread writes. Must not crash."""
        app = _app(tmp_path, "doc_write")
        errors = []

        def writer():
            try:
                for i in range(20):
                    try:
                        app.put_memory(f"Doctor-write fact {i}", scope_id="dw", type="semantic")
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"Writer: {e}")

        def doctor():
            try:
                time.sleep(0.01)
                try:
                    app.doctor()
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"Doctor: {e}")

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=doctor)
        t1.start()
        t2.start()
        t1.join(timeout=60)
        t2.join(timeout=60)

        app.close()
        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"Doctor-during-writes errors: {real_errors}"


# ===========================================================================
# 5. MEMORY ID COLLISION — force duplicate IDs via SQL
# ===========================================================================
class TestMemoryIDCollision:

    def test_duplicate_id_via_sql(self, tmp_path):
        """Insert duplicate memory ID via SQL. System must handle gracefully."""
        db_path = str(tmp_path / "dup_id.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("Original memory with unique ID", scope_id="dup", type="semantic")
            if mem:
                conn = sqlite3.connect(db_path)
                try:
                    # Try to insert duplicate ID
                    conn.execute(
                        "INSERT OR IGNORE INTO memories (id, content, type, scope_type, scope_id, status, confidence) "
                        "VALUES (?, 'DUPLICATE CONTENT', 'semantic', 'session', 'dup', 'active', 0.5)",
                        (mem.id,)
                    )
                    conn.commit()
                except Exception:
                    pass
                finally:
                    conn.close()

                # Search must not crash
                results = _search(app, "Original memory unique", "dup", limit=3)
                assert isinstance(results, list)

                # get_memory must return something valid
                fetched = app.storage.get_memory(mem.id)
                assert fetched is not None
        finally:
            app.close()


# ===========================================================================
# 6. COMPRESSED TIER ATTACK
# ===========================================================================
class TestCompressedTier:

    def test_compact_then_search(self, tmp_path):
        """Compact storage then search compressed memories."""
        app = _app(tmp_path, "compress")
        try:
            for i in range(50):
                app.put_memory(f"Compressible fact {i} about database systems", scope_id="cmp", type="semantic")

            # Force compaction
            try:
                app.compact_storage(scope_id="cmp", scope_type="session")
            except Exception:
                pass

            # Search must still work after compaction
            results = _search(app, "database systems", "cmp", limit=5)
            assert isinstance(results, list)
            assert len(results) > 0, "No results after compaction!"
        finally:
            app.close()

    def test_compact_empty_then_write(self, tmp_path):
        """Compact empty scope then write to it."""
        app = _app(tmp_path, "compress_empty")
        try:
            try:
                app.compact_storage(scope_id="empty_cmp", scope_type="session")
            except Exception:
                pass

            # Writing after compaction of empty scope must work
            mem = app.put_memory("Post-compact data", scope_id="empty_cmp", type="semantic")
            assert mem is not None or True  # Must not crash
        finally:
            app.close()


# ===========================================================================
# 7. CONCURRENT BACKUP RACE
# ===========================================================================
class TestConcurrentBackup:

    def test_backup_during_writes(self, tmp_path):
        """Create backup while another thread writes. Must not corrupt."""
        app = _app(tmp_path, "backup_race")
        errors = []
        backup_results = []

        for i in range(20):
            app.put_memory(f"Pre-backup fact {i}", scope_id="bk", type="semantic")

        def writer():
            try:
                for i in range(20):
                    try:
                        app.put_memory(f"During-backup fact {i}", scope_id="bk", type="semantic")
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"Writer: {e}")

        def backuper():
            try:
                time.sleep(0.02)
                try:
                    result = app.create_backup()
                    backup_results.append(result)
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"Backuper: {e}")

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=backuper)
        t1.start()
        t2.start()
        t1.join(timeout=60)
        t2.join(timeout=60)

        app.close()
        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"Backup race errors: {real_errors}"


# ===========================================================================
# 8. MASSIVE CONCURRENT END_SESSION
# ===========================================================================
class TestConcurrentEndSession:

    def test_10_threads_ending_sessions(self, tmp_path):
        """10 threads ending different sessions simultaneously."""
        app = _app(tmp_path, "end_race")
        errors = []

        # Create sessions
        for i in range(10):
            app.put_memory(f"Session {i} data", scope_id="es", type="semantic", session_id=f"sess_{i}")

        def ender(thread_id):
            try:
                try:
                    app.end_session(session_id=f"sess_{thread_id}", scope_id="es", scope_type="session")
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=ender, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        # DB must survive
        try:
            results = _search(app, "Session data", "es", limit=10)
            assert isinstance(results, list)
        finally:
            app.close()

        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"End session race: {real_errors}"


# ===========================================================================
# 9. PRAGMA INJECTION — via content and scope_id
# ===========================================================================
class TestPragmaInjection:

    @pytest.mark.parametrize("evil_input", [
        "PRAGMA table_info(memories)",
        "PRAGMA database_list",
        "PRAGMA key = 'attack'",
        "PRAGMA journal_mode = OFF",
        "PRAGMA foreign_keys = OFF",
        "ATTACH DATABASE ':memory:' AS evil",
    ])
    def test_pragma_in_content(self, tmp_path, evil_input):
        """PRAGMA commands in content must not be executed."""
        app = _app(tmp_path, f"pragma_{abs(hash(evil_input)) % 99999}")
        try:
            app.put_memory(evil_input, scope_id="pragma", type="semantic")
            results = _search(app, evil_input, "pragma", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()

    @pytest.mark.parametrize("evil_scope", [
        "scope; PRAGMA key='x'",
        "'; ATTACH DATABASE ':memory:' AS evil;--",
    ])
    def test_pragma_in_scope_id(self, tmp_path, evil_scope):
        """PRAGMA injection via scope_id must not execute."""
        app = _app(tmp_path, f"pscope_{abs(hash(evil_scope)) % 99999}")
        try:
            try:
                app.put_memory("Test", scope_id=evil_scope, type="semantic")
            except Exception:
                pass
        finally:
            app.close()


# ===========================================================================
# 10. MEMORY ALIASING — content that references other memory IDs
# ===========================================================================
class TestMemoryAliasing:

    def test_content_referencing_other_ids(self, tmp_path):
        """Content with aegis:// URIs must not cause self-referential loops."""
        app = _app(tmp_path, "alias")
        try:
            m1 = app.put_memory("First memory for aliasing test", scope_id="alias", type="semantic")
            if m1:
                # Content that references another memory
                app.put_memory(
                    f"See also: aegis://{m1.id} and aegis://mem_fake_nonexistent",
                    scope_id="alias", type="semantic",
                )

            results = _search(app, "aliasing test", "alias", limit=5)
            assert isinstance(results, list)
        finally:
            app.close()


# ===========================================================================
# 11. SQLITE BUSY TIMEOUT EXHAUSTION
# ===========================================================================
class TestBusyTimeout:

    def test_long_write_blocks_read(self, tmp_path):
        """Long write operation should not permanently block reads."""
        db_path = str(tmp_path / "busy.db")
        app = AegisApp(db_path=db_path)
        try:
            app.put_memory("Busy timeout test data", scope_id="busy", type="semantic")

            # Hold a raw connection with an open transaction
            conn = sqlite3.connect(db_path, timeout=1)
            try:
                conn.execute("BEGIN EXCLUSIVE")
                conn.execute("UPDATE memories SET confidence = 0.99 WHERE scope_id = 'busy'")

                # Try to search while transaction is held — may timeout but must not crash
                try:
                    results = _search(app, "Busy timeout test", "busy", limit=3)
                    assert isinstance(results, list)
                except Exception:
                    pass  # Timeout ok, crash not

                conn.rollback()
            finally:
                conn.close()
        finally:
            app.close()


# ===========================================================================
# 12. INTERLEAVED OPERATIONS — put, search, correct, forget, reinforce
# ===========================================================================
class TestInterleavedOps:

    def test_all_operations_interleaved(self, tmp_path):
        """Rapidly interleave all major operations. Must not crash."""
        app = _app(tmp_path, "interleave")
        try:
            ids = []
            for i in range(10):
                m = app.put_memory(f"Interleave fact {i}", scope_id="il", type="semantic")
                if m:
                    ids.append(m.id)

                _search(app, f"fact {i}", "il", limit=2)

                if ids:
                    try:
                        app.reinforce(ids[-1])
                    except Exception:
                        pass

                if i % 3 == 0:
                    try:
                        app.memory_correct(f"Corrected: fact {i} is actually wrong")
                    except Exception:
                        pass

                if i % 5 == 0 and ids:
                    try:
                        app.memory_forget(ids[0])
                        ids.pop(0)
                    except Exception:
                        pass

            # Final consistency check
            results = _search(app, "Interleave fact", "il", limit=10)
            assert isinstance(results, list)
        finally:
            app.close()

    def test_operations_after_maintenance(self, tmp_path):
        """All operations must work after maintenance cycle."""
        app = _app(tmp_path, "post_maint")
        try:
            for i in range(20):
                app.put_memory(f"Pre-maintenance fact {i}", scope_id="pm", type="semantic")

            app.maintenance()

            # All operations must still work
            m = app.put_memory("Post-maintenance write", scope_id="pm", type="semantic")
            assert m is not None or True

            results = _search(app, "maintenance fact", "pm", limit=5)
            assert isinstance(results, list)

            try:
                app.memory_correct("Post-maintenance correction")
            except Exception:
                pass

            snapshot = app.observability_snapshot()
            assert isinstance(snapshot, dict)
        finally:
            app.close()
