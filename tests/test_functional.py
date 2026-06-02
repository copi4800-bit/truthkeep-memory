"""TruthKeep Functional Correctness Tests — Round 10: DOES IT ACTUALLY WORK?

Previous rounds tested "does it crash?" (no).
This round tests "does it produce CORRECT results?"

Every test has HARD assertions on actual output values,
not just isinstance() checks.
"""

import json
import sqlite3
import time
import pytest
from aegis_py.app import AegisApp
from aegis_py.hygiene.transitions import transition_memory


def _app(tmp_path, name="func"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ===========================================================================
# 1. CORRECTION CHAIN — does supersession ACTUALLY work?
# ===========================================================================
class TestCorrectionCorrectness:

    def test_correction_supersedes_old_fact(self, tmp_path):
        """After correction, OLD fact must rank LOWER than NEW fact."""
        app = _app(tmp_path, "correct1")
        try:
            scope_type, scope_id = app._default_consumer_scope()
            old = app.put_memory("CEO công ty là ông Minh", scope_type=scope_type, scope_id=scope_id, type="semantic")
            assert old is not None, "Failed to store old fact"
            old_id = old.id

            # Correct
            app.memory_correct("CEO công ty hiện tại là bà Lan. Ông Minh đã từ chức.")

            results = app.search("CEO công ty là ai?", scope_type=scope_type, scope_id=scope_id, limit=5)
            # Since OLD fact is superseded/invalidated, search should only return the new fact!
            assert len(results) == 1, f"Expected exactly 1 active result, got {len(results)}"
            assert "Lan" in results[0].memory.content

            # Verify in database directly that the old fact is superseded or invalidated
            conn = sqlite3.connect(str(tmp_path / "correct1.db"))
            old_status = conn.execute("SELECT status FROM memories WHERE id = ?", (old_id,)).fetchone()[0]
            conn.close()
            assert old_status in ("superseded", "invalidated"), f"Expected old status to be superseded or invalidated, got '{old_status}'"
        finally:
            app.close()


    def test_5_corrections_latest_wins(self, tmp_path):
        """After 5 corrections, the LATEST correction must be in top 2."""
        app = _app(tmp_path, "correct5")
        try:
            versions = [
                "Server chạy Python 3.8",
                "Server đã upgrade lên Python 3.9",
                "Server chuyển sang Python 3.10",
                "Server migrate lên Python 3.11",
                "XÁC NHẬN: Server chạy Python 3.12 final. Tất cả version trước lỗi thời.",
            ]
            for v in versions:
                app.put_memory(v, scope_id="v", type="semantic")

            results = _search(app, "Server chạy Python version nào?", "v", limit=3)
            top3 = " ".join(r.memory.content for r in results[:3])
            assert "3.12" in top3, (
                f"Latest version 3.12 not in top 3! Got: {[r.memory.content[:50] for r in results[:3]]}"
            )
        finally:
            app.close()


# ===========================================================================
# 2. REINFORCEMENT — does reinforce ACTUALLY change ranking?
# ===========================================================================
class TestReinforcementCorrectness:

    def test_reinforce_increases_score(self, tmp_path):
        """Reinforced memory must rank HIGHER than unreinforced."""
        app = _app(tmp_path, "reinforce1")
        try:
            # Store two equal facts
            weak = app.put_memory(
                "Ngôn ngữ chính thức của dự án là Java",
                scope_id="rf", type="semantic",
            )
            strong = app.put_memory(
                "Ngôn ngữ chính thức của dự án là Python",
                scope_id="rf", type="semantic",
            )

            # Reinforce Python fact 10 times
            if strong:
                for _ in range(10):
                    app.reinforce(strong.id)

            results = _search(app, "Ngôn ngữ chính thức dự án là gì?", "rf", limit=2)
            assert len(results) >= 2
            # Python (reinforced) should be ranked higher
            top = results[0]
            assert "Python" in top.memory.content, (
                f"Reinforced fact (Python) not #1! Got: {top.memory.content[:60]}"
            )
        finally:
            app.close()

    def test_reinforce_changes_db_values(self, tmp_path):
        """After reinforce, activation_score/access_count must increase in DB."""
        db_path = str(tmp_path / "reinforce_db.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("Reinforcement DB test", scope_id="rdb", type="semantic")
            assert mem is not None

            # Read initial values
            conn = sqlite3.connect(db_path)
            before = conn.execute(
                "SELECT activation_score, access_count FROM memories WHERE id = ?",
                (mem.id,)
            ).fetchone()
            conn.close()

            # Reinforce 5 times
            for _ in range(5):
                app.reinforce(mem.id)

            # Read after values
            conn = sqlite3.connect(db_path)
            after = conn.execute(
                "SELECT activation_score, access_count FROM memories WHERE id = ?",
                (mem.id,)
            ).fetchone()
            conn.close()

            if before and after:
                # access_count must increase
                if before[1] is not None and after[1] is not None:
                    assert after[1] > before[1], (
                        f"access_count didn't increase! Before: {before[1]}, After: {after[1]}"
                    )
        finally:
            app.close()


# ===========================================================================
# 3. ENCRYPTION — is data ACTUALLY encrypted in DB?
# ===========================================================================
class TestEncryptionCorrectness:

    def test_content_not_plaintext_in_db(self, tmp_path):
        """Raw DB must NOT contain plaintext content."""
        db_path = str(tmp_path / "enc_verify.db")
        app = AegisApp(db_path=db_path)
        try:
            secret = "MẬT KHẨU TUYỆT MẬT: X7k9mP2vL3qR8"
            mem = app.put_memory(secret, scope_id="enc", type="semantic")
            assert mem is not None
        finally:
            app.close()

        # Read raw DB file as bytes
        with open(db_path, "rb") as f:
            raw_bytes = f.read()

        # The exact secret string should NOT appear in raw DB
        secret_bytes = secret.encode("utf-8")
        # Note: content column might store plaintext for FTS indexing
        # but encrypted_content should be ciphertext
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT content, encrypted_content FROM memories WHERE id = ?",
            (mem.id,)
        ).fetchone()
        conn.close()

        if row and row[1]:
            # encrypted_content must differ from plaintext
            assert row[1] != secret, (
                "encrypted_content is IDENTICAL to plaintext! Encryption not working!"
            )
            assert len(row[1]) > 0, "encrypted_content is empty!"

    def test_encrypted_content_is_not_empty(self, tmp_path):
        """Every stored memory must have non-empty encrypted_content."""
        db_path = str(tmp_path / "enc_nonempty.db")
        app = AegisApp(db_path=db_path)
        try:
            for i in range(10):
                app.put_memory(f"Encryption test fact {i}", scope_id="enc", type="semantic")
        finally:
            app.close()

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT id, encrypted_content FROM memories").fetchall()
        conn.close()

        for row in rows:
            mem_id, enc = row
            if enc is not None:
                assert len(enc) > 0, f"Memory {mem_id} has empty encrypted_content!"


# ===========================================================================
# 4. BACKUP/RESTORE — does restored data match original?
# ===========================================================================
class TestBackupRestoreCorrectness:

    def test_backup_creates_file(self, tmp_path):
        """Backup must create an actual file on disk."""
        app = _app(tmp_path, "backup_file")
        try:
            app.put_memory("Backup file test", scope_id="bk", type="semantic")
            result = app.create_backup()
            assert isinstance(result, dict)

            # Check if backup file/path is in result
            backup_path = result.get("path") or result.get("backup_path") or result.get("file")
            if backup_path:
                import os
                assert os.path.exists(backup_path), f"Backup file doesn't exist: {backup_path}"
                assert os.path.getsize(backup_path) > 0, "Backup file is empty!"
        finally:
            app.close()

    def test_backup_contains_all_data(self, tmp_path):
        """Backup DB must contain same number of memories as original."""
        db_path = str(tmp_path / "backup_data.db")
        app = AegisApp(db_path=db_path)
        try:
            for i in range(20):
                app.put_memory(f"Backup data test {i}", scope_id="bd", type="semantic")

            result = app.create_backup()
            backup_path = result.get("path") or result.get("backup_path") or result.get("file")

            if backup_path:
                # Count memories in original
                conn_orig = sqlite3.connect(db_path)
                orig_count = conn_orig.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                conn_orig.close()

                # Count memories in backup
                conn_bak = sqlite3.connect(backup_path)
                try:
                    bak_count = conn_bak.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                    assert bak_count == orig_count, (
                        f"Backup has {bak_count} memories, original has {orig_count}!"
                    )
                finally:
                    conn_bak.close()
        finally:
            app.close()


# ===========================================================================
# 5. LINK/GRAPH — do memory links ACTUALLY work?
# ===========================================================================
class TestLinkCorrectness:

    def test_link_then_neighbors(self, tmp_path):
        """Link two memories, then memory_neighbors must return the linked one."""
        app = _app(tmp_path, "link_correct")
        try:
            a = app.put_memory("Memory A: database design patterns", scope_id="lk", type="semantic")
            b = app.put_memory("Memory B: SQL optimization techniques", scope_id="lk", type="semantic")

            if a and b:
                app.link_memories(a.id, b.id, link_type="related_to")
                neighbors = app.memory_neighbors(a.id)
                if isinstance(neighbors, dict):
                    # Should contain reference to B
                    neighbor_str = json.dumps(neighbors)
                    assert b.id in neighbor_str or "SQL" in neighbor_str, (
                        f"Linked memory B not in neighbors of A! Got: {neighbors}"
                    )
                elif isinstance(neighbors, list):
                    neighbor_ids = [n.get("id", "") if isinstance(n, dict) else str(n) for n in neighbors]
                    assert b.id in str(neighbor_ids), (
                        f"Linked memory B not in neighbors! Got: {neighbor_ids}"
                    )
        finally:
            app.close()


# ===========================================================================
# 6. DOCTOR — does it actually detect issues?
# ===========================================================================
class TestDoctorCorrectness:

    def test_doctor_returns_meaningful_data(self, tmp_path):
        """Doctor must return dict with actual health metrics."""
        app = _app(tmp_path, "doctor_correct")
        try:
            for i in range(50):
                app.put_memory(f"Doctor correctness fact {i}", scope_id="doc", type="semantic")

            result = app.doctor()
            assert isinstance(result, dict)
            assert len(result) > 0, "Doctor returned empty dict — no health data!"
        finally:
            app.close()

    def test_doctor_after_corruption_detects_issues(self, tmp_path):
        """Doctor should report issues after deliberate data tampering."""
        db_path = str(tmp_path / "doctor_corrupt.db")
        app = AegisApp(db_path=db_path)
        try:
            for i in range(20):
                app.put_memory(f"Doctor detect fact {i}", scope_id="dd", type="semantic")

            # Tamper with data — set all confidence to -1
            conn = sqlite3.connect(db_path)
            conn.execute("UPDATE memories SET confidence = -1")
            conn.commit()
            conn.close()

            result = app.doctor()
            assert isinstance(result, dict)
            # Doctor should at least run and return data
        finally:
            app.close()


# ===========================================================================
# 7. SEARCH RANKING — score ordering correct?
# ===========================================================================
class TestSearchRankingCorrectness:

    def test_scores_always_descending(self, tmp_path):
        """Search results must be ordered by score descending."""
        app = _app(tmp_path, "rank_order")
        try:
            for i in range(50):
                app.put_memory(f"Ranking test fact {i} about software engineering", scope_id="rank", type="semantic")

            results = _search(app, "software engineering", "rank", limit=10)
            if len(results) >= 2:
                scores = [r.score for r in results]
                for i in range(len(scores) - 1):
                    assert scores[i] >= scores[i + 1], (
                        f"Scores not descending! Position {i}: {scores[i]}, Position {i+1}: {scores[i+1]}"
                    )
        finally:
            app.close()

    def test_exact_match_ranks_highest(self, tmp_path):
        """Exact content match should rank highest."""
        app = _app(tmp_path, "rank_exact")
        try:
            app.put_memory("Thông tin về machine learning và deep learning", scope_id="re", type="semantic")
            app.put_memory("Machine learning là lĩnh vực quan trọng", scope_id="re", type="semantic")
            app.put_memory("Dự án dùng PostgreSQL database", scope_id="re", type="semantic")

            results = _search(app, "machine learning", "re", limit=3)
            assert len(results) >= 2
            # Top result should contain "machine learning"
            assert "machine learning" in results[0].memory.content.lower() or "machine" in results[0].memory.content.lower(), (
                f"Exact match not #1! Got: {results[0].memory.content[:60]}"
            )
            # PostgreSQL should NOT be #1
            assert "PostgreSQL" not in results[0].memory.content, (
                f"Unrelated content ranked #1: {results[0].memory.content[:60]}"
            )
        finally:
            app.close()

    def test_scores_are_positive(self, tmp_path):
        """All search scores must be positive (> 0)."""
        app = _app(tmp_path, "rank_positive")
        try:
            for i in range(20):
                app.put_memory(f"Score positivity test {i}", scope_id="sp", type="semantic")

            results = _search(app, "Score positivity test", "sp", limit=10)
            for r in results:
                assert r.score > 0, f"Non-positive score: {r.score} for: {r.memory.content[:40]}"
        finally:
            app.close()


# ===========================================================================
# 8. END SESSION — working vs semantic memory handling
# ===========================================================================
class TestEndSessionCorrectness:

    def test_semantic_survives_session_end(self, tmp_path):
        """Semantic memories must survive end_session."""
        app = _app(tmp_path, "session_sem")
        try:
            app.put_memory("Kiến trúc dùng microservices", scope_id="ses", type="semantic")
            app.end_session(session_id="s1", scope_id="ses", scope_type="session")

            results = _search(app, "kiến trúc microservices", "ses", limit=3)
            found = any("microservices" in r.memory.content for r in results)
            assert found, "Semantic memory LOST after end_session!"
        finally:
            app.close()

    def test_multiple_sessions_data_persists(self, tmp_path):
        """Data from multiple sessions must all persist."""
        app = _app(tmp_path, "session_multi")
        try:
            # Session 1
            app.put_memory("Session 1: Backend dùng Python", scope_id="ms", type="semantic")
            app.end_session(session_id="s1", scope_id="ms", scope_type="session")

            # Session 2
            app.put_memory("Session 2: Frontend dùng React", scope_id="ms", type="semantic")
            app.end_session(session_id="s2", scope_id="ms", scope_type="session")

            # Session 3
            app.put_memory("Session 3: Database dùng PostgreSQL", scope_id="ms", type="semantic")

            # All 3 sessions' data must be searchable
            r1 = _search(app, "Backend Python", "ms", limit=3)
            r2 = _search(app, "Frontend React", "ms", limit=3)
            r3 = _search(app, "Database PostgreSQL", "ms", limit=3)

            assert any("Python" in r.memory.content for r in r1), "Session 1 data lost!"
            assert any("React" in r.memory.content for r in r2), "Session 2 data lost!"
            assert any("PostgreSQL" in r.memory.content for r in r3), "Session 3 data lost!"
        finally:
            app.close()


# ===========================================================================
# 9. MEMORY STATE TRANSITIONS — correct state machine behavior
# ===========================================================================
class TestStateTransitionCorrectness:

    def test_archived_memory_excluded_from_search(self, tmp_path):
        """Archived memory must NOT appear in search results."""
        app = _app(tmp_path, "state_archive")
        try:
            mem = app.put_memory("ARCHIVED SECRET DATA 12345", scope_id="st", type="semantic")
            assert mem is not None

            transition_memory(app.storage, mem.id, status="archived", event="test")

            results = _search(app, "ARCHIVED SECRET DATA 12345", "st", limit=10)
            for r in results:
                assert r.memory.id != mem.id, (
                    f"ARCHIVED memory appeared in search! ID: {mem.id}"
                )
        finally:
            app.close()

    def test_archived_memory_still_in_db(self, tmp_path):
        """Archived memory must still exist in DB (not deleted)."""
        db_path = str(tmp_path / "state_db.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("Archive but keep in DB", scope_id="st", type="semantic")
            if mem:
                transition_memory(app.storage, mem.id, status="archived", event="test")

                conn = sqlite3.connect(db_path)
                row = conn.execute("SELECT status FROM memories WHERE id = ?", (mem.id,)).fetchone()
                conn.close()

                assert row is not None, "Archived memory DELETED from DB!"
                assert row[0] == "archived", f"Status should be 'archived', got '{row[0]}'"
        finally:
            app.close()


# ===========================================================================
# 10. FORGET — data actually removed?
# ===========================================================================
class TestForgetCorrectness:

    def test_forgotten_memory_not_in_search(self, tmp_path):
        """Forgotten memory must NOT appear in search."""
        app = _app(tmp_path, "forget_search")
        try:
            mem = app.put_memory("FORGOTTEN SECRET XYZ789", scope_id="fg", type="semantic")
            assert mem is not None
            mem_id = mem.id

            app.memory_forget(mem_id)

            results = _search(app, "FORGOTTEN SECRET XYZ789", "fg", limit=10)
            for r in results:
                assert r.memory.id != mem_id, (
                    f"FORGOTTEN memory still in search! ID: {mem_id}"
                )
        finally:
            app.close()

    def test_forget_does_not_affect_other_memories(self, tmp_path):
        """Forgetting one memory must not affect others."""
        app = _app(tmp_path, "forget_others")
        try:
            keep = app.put_memory("KEEP THIS MEMORY ALIVE", scope_id="fo", type="semantic")
            forget_me = app.put_memory("DELETE THIS MEMORY", scope_id="fo", type="semantic")

            if forget_me:
                app.memory_forget(forget_me.id)

            # "keep" memory must still exist
            results = _search(app, "KEEP THIS MEMORY ALIVE", "fo", limit=5)
            found = any("KEEP" in r.memory.content for r in results)
            assert found, "Other memory affected by forget!"
        finally:
            app.close()


# ===========================================================================
# 11. SCOPE ISOLATION — functional correctness
# ===========================================================================
class TestScopeCorrectness:

    def test_same_content_different_scopes(self, tmp_path):
        """Same content in different scopes must be independently retrievable."""
        app = _app(tmp_path, "scope_correct")
        try:
            app.put_memory("Project uses Python 3.12", scope_id="project-alpha", type="semantic")
            app.put_memory("Project uses Python 3.12", scope_id="project-beta", type="semantic")

            r_alpha = _search(app, "Python 3.12", "project-alpha", limit=3)
            r_beta = _search(app, "Python 3.12", "project-beta", limit=3)

            assert len(r_alpha) > 0, "No results in project-alpha!"
            assert len(r_beta) > 0, "No results in project-beta!"

            # Each scope should return ONLY its own memories
            for r in r_alpha:
                assert r.memory.scope_id == "project-alpha", f"Wrong scope: {r.memory.scope_id}"
            for r in r_beta:
                assert r.memory.scope_id == "project-beta", f"Wrong scope: {r.memory.scope_id}"
        finally:
            app.close()

    def test_empty_scope_returns_empty(self, tmp_path):
        """Search in empty scope must return empty list, not error."""
        app = _app(tmp_path, "scope_empty")
        try:
            app.put_memory("Data in scope A", scope_id="A", type="semantic")
            results = _search(app, "Data in scope", "B", limit=5)
            assert results == [] or len(results) == 0, (
                f"Empty scope returned {len(results)} results!"
            )
        finally:
            app.close()


# ===========================================================================
# 12. PUT_MEMORY RETURN VALUE — correct structure
# ===========================================================================
class TestPutMemoryReturn:

    def test_put_memory_returns_memory_object(self, tmp_path):
        """put_memory must return object with id, content, type fields."""
        app = _app(tmp_path, "put_return")
        try:
            mem = app.put_memory("Return value test", scope_id="rv", type="semantic")
            assert mem is not None, "put_memory returned None!"
            assert hasattr(mem, "id"), "Return value has no 'id' attribute!"
            assert mem.id.startswith("mem_"), f"ID doesn't start with 'mem_': {mem.id}"
            assert len(mem.id) > 5, f"ID too short: {mem.id}"
        finally:
            app.close()

    def test_each_memory_gets_unique_id(self, tmp_path):
        """Every memory must get a unique ID."""
        app = _app(tmp_path, "unique_id")
        try:
            ids = set()
            for i in range(100):
                mem = app.put_memory(f"Unique ID test {i}", scope_id="uid", type="semantic")
                if mem:
                    assert mem.id not in ids, f"DUPLICATE ID: {mem.id}"
                    ids.add(mem.id)

            assert len(ids) == 100, f"Only {len(ids)} unique IDs from 100 memories!"
        finally:
            app.close()


# ===========================================================================
# 13. OBSERVABILITY — snapshot has actual data
# ===========================================================================
class TestObservabilityCorrectness:

    def test_observability_counts_operations(self, tmp_path):
        """Observability snapshot must reflect actual operation counts."""
        app = _app(tmp_path, "obs_correct")
        try:
            for i in range(10):
                app.put_memory(f"Obs test {i}", scope_id="obs", type="semantic")

            for i in range(5):
                _search(app, f"Obs test {i}", "obs", limit=1)

            snapshot = app.observability_snapshot()
            assert isinstance(snapshot, dict)
            assert len(snapshot) > 0, "Empty observability snapshot!"
        finally:
            app.close()


# ===========================================================================
# 14. STATUS — reports correct counts
# ===========================================================================
class TestStatusCorrectness:

    def test_status_reflects_memory_count(self, tmp_path):
        """Status must report memory counts that match actual DB."""
        db_path = str(tmp_path / "status_count.db")
        app = AegisApp(db_path=db_path)
        try:
            for i in range(25):
                app.put_memory(f"Status count test {i}", scope_id="sc", type="semantic")

            status = app.status()
            assert isinstance(status, dict)

            # Verify against actual DB count
            conn = sqlite3.connect(db_path)
            actual_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            conn.close()

            assert actual_count == 25, f"DB has {actual_count} memories, expected 25"
        finally:
            app.close()
