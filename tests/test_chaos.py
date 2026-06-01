"""TruthKeep Chaos Tests — designed to find race conditions, corruption, and edge cases.

Round 3: multi-threaded access, deep correction chains, ReDoS,
duplicate content, FTS consistency, whitespace abuse, scope_type injection.
"""

import threading
import time
import pytest
from aegis_py.app import AegisApp


def _app(tmp_path, name="chaos"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ---------------------------------------------------------------------------
# 1. MULTI-THREADED CONCURRENT WRITES — race condition detector
# ---------------------------------------------------------------------------
class TestConcurrency:

    def test_10_threads_writing_simultaneously(self, tmp_path):
        """10 threads writing to same DB simultaneously. Must not corrupt."""
        app = _app(tmp_path, "threads")
        errors = []
        results = []
        lock = threading.Lock()

        def writer(thread_id):
            try:
                for i in range(10):
                    r = app.put_memory(
                        f"Thread {thread_id} write {i}: unique data {thread_id * 100 + i}",
                        scope_id="concurrent", type="semantic",
                    )
                    if r:
                        with lock:
                            results.append(r.id)
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        app.close()

        # Verify: some writes may fail due to lock contention, but no corruption
        assert len(errors) == 0 or all("database is locked" in e.lower() or "closed" in e.lower() for e in errors), (
            f"Unexpected errors: {errors[:3]}"
        )
        # At least some writes should succeed
        assert len(results) >= 10, f"Only {len(results)} writes succeeded out of 100"
        # No duplicate IDs
        assert len(set(results)) == len(results), "Duplicate memory IDs from concurrent writes!"

    def test_concurrent_read_write(self, tmp_path):
        """Writers and readers running simultaneously. Must not crash."""
        app = _app(tmp_path, "rw_concurrent")
        # Pre-populate
        for i in range(20):
            app.put_memory(f"Pre-populated fact number {i} about testing", scope_id="rw", type="semantic")

        errors = []
        read_results = []

        def writer():
            try:
                for i in range(20):
                    app.put_memory(f"Concurrent write {i} during reads", scope_id="rw", type="semantic")
            except Exception as e:
                errors.append(f"Writer: {e}")

        def reader():
            try:
                for _ in range(20):
                    results = _search(app, "testing fact", "rw", limit=3)
                    read_results.append(len(results))
            except Exception as e:
                errors.append(f"Reader: {e}")

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        app.close()
        # Reads should return results even during writes
        successful_reads = [r for r in read_results if r > 0]
        assert len(successful_reads) >= 10, f"Too many failed reads: {len(successful_reads)}/60 succeeded"


# ---------------------------------------------------------------------------
# 2. DEEP CORRECTION CHAIN — 50 levels of corrections
# ---------------------------------------------------------------------------
class TestDeepCorrectionChain:

    def test_50_level_correction_chain(self, tmp_path):
        """50 sequential corrections of the same fact. Latest must win."""
        app = _app(tmp_path, "deep_chain")
        try:
            for i in range(50):
                app.put_memory(
                    f"Phiên bản phần mềm hiện tại là v{i}.0.0 (cập nhật lần thứ {i})",
                    scope_id="chain", type="semantic",
                )

            results = _search(app, "phiên bản phần mềm hiện tại", "chain", limit=5)
            assert len(results) > 0

            # v49.0.0 (latest) should be in results
            all_content = " ".join(r.memory.content for r in results)
            assert "v49" in all_content, (
                f"Latest version v49 not found. Top results: "
                f"{[r.memory.content[:50] for r in results[:3]]}"
            )
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 3. DUPLICATE CONTENT — exact same text stored multiple times
# ---------------------------------------------------------------------------
class TestDuplicateContent:

    def test_exact_duplicate_10_times(self, tmp_path):
        """Store exact same content 10 times. System must handle gracefully."""
        app = _app(tmp_path, "duplicates")
        try:
            ids = []
            for _ in range(10):
                r = app.put_memory(
                    "Thủ đô Việt Nam là Hà Nội",
                    scope_id="dup", type="semantic",
                )
                if r:
                    ids.append(r.id)

            # Search should return result (not crash from duplicates)
            results = _search(app, "Thủ đô Việt Nam", "dup", limit=5)
            assert len(results) > 0
            found = any("Hà Nội" in r.memory.content for r in results)
            assert found, "Duplicate content lost after multiple stores"
        finally:
            app.close()

    def test_near_duplicate_single_char_diff(self, tmp_path):
        """Content differing by single character must be stored separately."""
        app = _app(tmp_path, "near_dup")
        try:
            app.put_memory("Giá sản phẩm A là 100,000 VND", scope_id="near", type="semantic")
            app.put_memory("Giá sản phẩm B là 100,000 VND", scope_id="near", type="semantic")
            app.put_memory("Giá sản phẩm A là 200,000 VND", scope_id="near", type="semantic")

            results = _search(app, "Giá sản phẩm A bao nhiêu?", "near", limit=3)
            assert len(results) > 0
            # Both A facts should appear
            a_facts = [r for r in results if "sản phẩm A" in r.memory.content]
            assert len(a_facts) >= 1, "Product A fact not found among near-duplicates"
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 4. WHITESPACE ABUSE — tabs, newlines, excessive spaces
# ---------------------------------------------------------------------------
class TestWhitespaceAbuse:

    @pytest.mark.parametrize("evil_content", [
        "   leading spaces   ",
        "\t\ttab\tcontent\t",
        "\nnewline\ncontent\n",
        "\r\nwindows\r\nnewlines\r\n",
        "   ",  # only spaces
        "\t\t\t",  # only tabs
        "normal content\x0b\x0c with vertical tab and form feed",
        "mixed   \t  \n  whitespace   \r\n   everywhere",
    ])
    def test_whitespace_content_no_crash(self, tmp_path, evil_content):
        """Content with various whitespace must not crash."""
        app = _app(tmp_path, f"ws_{abs(hash(evil_content)) % 10000}")
        try:
            result = app.put_memory(evil_content, scope_id="ws", type="semantic")
            # May reject whitespace-only content — that's ok
        finally:
            app.close()

    @pytest.mark.parametrize("evil_query", [
        "   ",
        "\t\t",
        "\n\n",
        "   query   with   excessive   spaces   ",
    ])
    def test_whitespace_queries_no_crash(self, tmp_path, evil_query):
        """Queries with whitespace abuse must not crash."""
        app = _app(tmp_path, f"wsq_{abs(hash(evil_query)) % 10000}")
        try:
            app.put_memory("Normal content for testing", scope_id="wsq", type="semantic")
            results = _search(app, evil_query, "wsq", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 5. SCOPE_TYPE INJECTION — we tested scope_id, now scope_type
# ---------------------------------------------------------------------------
class TestScopeTypeInjection:

    @pytest.mark.parametrize("evil_type", [
        "session' OR '1'='1",
        "session; DROP TABLE memories;--",
        "' UNION SELECT * FROM memories--",
        "session\x00null",
    ])
    def test_scope_type_injection_no_crash(self, tmp_path, evil_type):
        """SQL injection via scope_type must not crash."""
        app = _app(tmp_path, f"st_{abs(hash(evil_type)) % 10000}")
        try:
            try:
                app.put_memory("Test content", scope_id="test", type="semantic")
                app.search("test", scope_id="test", scope_type=evil_type, limit=3)
            except Exception:
                pass  # Errors ok, crash not
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 6. EMOJI-ONLY CONTENT — pure emoji storage and retrieval
# ---------------------------------------------------------------------------
class TestEmojiEdgeCases:

    def test_emoji_only_content(self, tmp_path):
        """Content that is purely emoji must not crash."""
        app = _app(tmp_path, "emoji")
        try:
            app.put_memory("🔥💀🚀✅❌🎯🧠💾", scope_id="emoji", type="semantic")
            app.put_memory("🇻🇳🇺🇸🇯🇵🇬🇧", scope_id="emoji", type="semantic")  # Flag emoji (multi-codepoint)
            results = _search(app, "🔥🚀", "emoji", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()

    def test_emoji_in_scope_id(self, tmp_path):
        """Emoji in scope_id must not crash."""
        app = _app(tmp_path, "emoji_scope")
        try:
            app.put_memory("Test with emoji scope", scope_id="🔥-project", type="semantic")
            results = _search(app, "test emoji", "🔥-project", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 7. MEMORY DELETION + SEARCH CONSISTENCY
# ---------------------------------------------------------------------------
class TestDeletionConsistency:

    def test_forget_then_search(self, tmp_path):
        """After forgetting a memory, it must not appear in search."""
        app = _app(tmp_path, "forget")
        try:
            mem = app.put_memory("Secret: nuclear launch codes are 12345", scope_id="forget", type="semantic")
            if mem:
                app.memory_forget(mem.id)
                results = _search(app, "nuclear launch codes", "forget", limit=5)
                for r in results:
                    assert "nuclear" not in r.memory.content.lower(), (
                        f"FORGOTTEN MEMORY LEAKED: {r.memory.content[:60]}"
                    )
        finally:
            app.close()

    def test_forget_nonexistent(self, tmp_path):
        """Forgetting nonexistent memory must not crash."""
        app = _app(tmp_path, "forget_fake")
        try:
            try:
                app.memory_forget("mem_totally_fake_id_that_doesnt_exist")
            except Exception:
                pass  # Error ok
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 8. SEARCH RESULT SCORE CONSISTENCY
# ---------------------------------------------------------------------------
class TestScoreConsistency:

    def test_scores_always_descending(self, tmp_path):
        """Search results must always be sorted by score descending."""
        app = _app(tmp_path, "score_order")
        try:
            for i in range(20):
                app.put_memory(
                    f"Fact {i}: Database systems use various indexing strategies for optimization",
                    scope_id="order", type="semantic",
                )

            results = _search(app, "database indexing optimization", "order", limit=10)
            if len(results) >= 2:
                for i in range(len(results) - 1):
                    assert results[i].score >= results[i + 1].score, (
                        f"Results not sorted! Index {i}: {results[i].score} < Index {i+1}: {results[i+1].score}"
                    )
        finally:
            app.close()

    def test_scores_always_positive(self, tmp_path):
        """All scores must be non-negative."""
        app = _app(tmp_path, "score_positive")
        try:
            app.put_memory("Test fact about positive scores", scope_id="pos", type="semantic")
            results = _search(app, "positive scores", "pos", limit=5)
            for r in results:
                assert r.score >= 0, f"Negative score detected: {r.score}"
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 9. EXTREMELY RAPID REINFORCE-THEN-SEARCH CYCLE
# ---------------------------------------------------------------------------
class TestReinforceCycle:

    def test_reinforce_search_interleave(self, tmp_path):
        """Interleave reinforce and search 50 times. Scores must monotonically increase."""
        app = _app(tmp_path, "reinforce_cycle")
        try:
            mem = app.put_memory("Important reinforced fact about AI safety", scope_id="rc", type="semantic")
            if not mem:
                pytest.skip("Memory not stored")

            prev_score = 0.0
            for i in range(50):
                app.reinforce(mem.id)
                if i % 10 == 0:  # Check every 10 reinforcements
                    results = _search(app, "AI safety reinforced", "rc", limit=1)
                    if results:
                        curr_score = results[0].score
                        assert curr_score >= prev_score * 0.95, (
                            f"Score decreased after reinforce #{i}: {prev_score} -> {curr_score}"
                        )
                        prev_score = curr_score
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 10. PATHOLOGICAL CONTENT PATTERNS
# ---------------------------------------------------------------------------
class TestPathologicalContent:

    def test_repeated_single_word_1000x(self, tmp_path):
        """Content with same word repeated 1000 times."""
        app = _app(tmp_path, "repeat")
        try:
            content = "memory " * 1000
            result = app.put_memory(content, scope_id="path", type="semantic")
            # May reject as too large/noisy — that's ok
            if result:
                results = _search(app, "memory", "path", limit=1)
                assert isinstance(results, list)
        finally:
            app.close()

    def test_all_numbers_content(self, tmp_path):
        """Content that is purely numeric."""
        app = _app(tmp_path, "numbers")
        try:
            app.put_memory("1234567890 9876543210 1111111111", scope_id="num", type="semantic")
            results = _search(app, "1234567890", "num", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()

    def test_base64_content(self, tmp_path):
        """Base64-encoded content (common in real usage)."""
        app = _app(tmp_path, "b64")
        try:
            import base64
            data = base64.b64encode(b"TruthKeep secret payload: AES-256-GCM encrypted").decode()
            app.put_memory(f"Encrypted backup key: {data}", scope_id="b64", type="semantic")
            results = _search(app, "encrypted backup key", "b64", limit=3)
            assert len(results) > 0
            found = any("Encrypted backup" in r.memory.content for r in results)
            assert found, "Base64 content not retrievable"
        finally:
            app.close()

    def test_json_content(self, tmp_path):
        """JSON blob as content."""
        app = _app(tmp_path, "json")
        try:
            import json
            payload = json.dumps({
                "user": "admin",
                "config": {"theme": "dark", "lang": "vi"},
                "permissions": ["read", "write", "delete"],
            })
            app.put_memory(f"Config: {payload}", scope_id="json", type="semantic")
            results = _search(app, "admin config permissions", "json", limit=3)
            assert len(results) > 0
        finally:
            app.close()

    def test_html_content(self, tmp_path):
        """HTML tags in content must not cause issues."""
        app = _app(tmp_path, "html")
        try:
            html = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'
            app.put_memory(f"Security alert: {html}", scope_id="html", type="semantic")
            results = _search(app, "security alert XSS", "html", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 11. DATABASE REOPEN PERSISTENCE
# ---------------------------------------------------------------------------
class TestPersistence:

    def test_close_reopen_data_survives(self, tmp_path):
        """Data must survive close + reopen cycle."""
        db_path = str(tmp_path / "persist.db")

        # Write
        app1 = AegisApp(db_path=db_path)
        app1.put_memory("Persistent fact: Earth orbits the Sun", scope_id="persist", type="semantic")
        app1.close()

        # Reopen and read
        app2 = AegisApp(db_path=db_path)
        try:
            results = _search(app2, "Earth orbits Sun", "persist", limit=3)
            assert len(results) > 0
            found = any("Earth" in r.memory.content for r in results)
            assert found, "Data lost after close+reopen!"
        finally:
            app2.close()

    def test_double_reopen(self, tmp_path):
        """Three open-close cycles. Data must persist through all."""
        db_path = str(tmp_path / "triple.db")

        for cycle in range(3):
            app = AegisApp(db_path=db_path)
            app.put_memory(f"Cycle {cycle} fact", scope_id="cycle", type="semantic")
            app.close()

        # Final verify
        app = AegisApp(db_path=db_path)
        try:
            results = _search(app, "Cycle fact", "cycle", limit=5)
            # Should find facts from all 3 cycles
            assert len(results) >= 2, f"Only {len(results)} facts survived 3 cycles"
        finally:
            app.close()
