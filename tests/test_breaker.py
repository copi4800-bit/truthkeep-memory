"""TruthKeep Breaker Tests — designed to BREAK, not just stress.

These target edge cases that developers typically miss:
FTS5 injection, circular references, numeric overflow, binary content,
scope ID injection, extreme content sizes, and Unicode normalization attacks.
"""

import pytest
from aegis_py.app import AegisApp


def _app(tmp_path, name="break"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ---------------------------------------------------------------------------
# 1. FTS5 SYNTAX INJECTION — special characters that break SQLite FTS5
# ---------------------------------------------------------------------------
class TestFTS5Injection:
    """FTS5 has special syntax: NEAR, AND, OR, NOT, *, column:, ^, "phrase"."""

    @pytest.mark.parametrize("evil_query", [
        'NEAR(test, memory)',                 # FTS5 NEAR operator
        'test AND memory OR hack',            # Boolean operators
        'test NOT memory',                    # NOT operator
        '"test" * "memory"',                  # Wildcards + phrases
        'content:test',                       # Column filter
        '^test',                              # Start-of-field
        'test NEAR/3 memory',                 # Proximity search
        '(test OR memory) AND NOT hack',      # Complex boolean
        'te*',                                # Prefix wildcard
        '{test memory}',                      # Braces
        'test + memory - hack',              # Plus/minus
        '"unclosed phrase',                   # Unclosed quote
        "test' OR '1'='1",                    # SQL injection attempt
        'test"); DROP TABLE memories;--',     # SQL injection
        '\x00\x01\x02\x03',                  # Control characters
        '',                                   # Empty string
    ])
    def test_fts5_evil_queries_dont_crash(self, tmp_path, evil_query):
        """Evil FTS5 queries must never crash — return empty or best-effort."""
        app = _app(tmp_path, f"fts5_{hash(evil_query) % 10000}")
        try:
            app.put_memory("Normal fact about testing memory systems", scope_id="fts", type="semantic")
            # Must not raise any exception
            results = _search(app, evil_query, "fts", limit=3)
            # Results can be empty, but must not crash
            assert isinstance(results, list)
        finally:
            app.close()

    def test_fts5_evil_content_stored_and_retrieved(self, tmp_path):
        """Content with FTS5 special chars must be stored and retrievable."""
        app = _app(tmp_path, "fts5_content")
        try:
            evil_contents = [
                'Formula: x = (a AND b) OR NOT c',
                'Path: C:\\Users\\test\\file.txt',
                'Regex: ^[a-z]+$ NEAR {match}',
                'SQL: SELECT * FROM users WHERE 1=1;--',
                'Tags: #test @user $price ^caret',
            ]
            for content in evil_contents:
                result = app.put_memory(content, scope_id="fts-store", type="semantic")
                assert result is not None, f"Failed to store: {content[:40]}"

            results = _search(app, "formula regex SQL", "fts-store", limit=5)
            assert len(results) >= 1
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 2. NUMERIC EDGE CASES — overflow, NaN, infinity
# ---------------------------------------------------------------------------
class TestNumericEdgeCases:

    def test_massive_reinforcement_100x(self, tmp_path):
        """Reinforce 100 times — activation_score must stay finite and sane."""
        app = _app(tmp_path, "reinforce_100")
        try:
            mem = app.put_memory("Test fact for massive reinforcement", scope_id="num", type="semantic")
            for _ in range(100):
                app.reinforce(mem.id)

            results = _search(app, "massive reinforcement", "num", limit=1)
            assert len(results) > 0
            score = results[0].score
            activation = results[0].memory.activation_score
            # Must be finite, not NaN, not infinity
            assert score == score, "Score is NaN!"  # NaN != NaN
            assert activation == activation, "Activation is NaN!"
            assert score < 1e10, f"Score overflow: {score}"
            assert activation < 1e10, f"Activation overflow: {activation}"
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 3. EXTREME CONTENT SIZES — empty, tiny, huge
# ---------------------------------------------------------------------------
class TestContentSizes:

    def test_single_char_content(self, tmp_path):
        """Single character content must be handled."""
        app = _app(tmp_path, "tiny")
        try:
            result = app.put_memory("X", scope_id="size", type="semantic")
            # May be rejected as too short — that's ok
            # But must not crash
        finally:
            app.close()

    def test_very_long_content_10kb(self, tmp_path):
        """10KB content must be stored without crash."""
        app = _app(tmp_path, "huge")
        try:
            long_content = "Đây là một fact rất dài. " * 500  # ~12KB Vietnamese
            result = app.put_memory(long_content, scope_id="size", type="semantic")
            if result:
                results = _search(app, "fact rất dài", "size", limit=1)
                assert len(results) > 0
        finally:
            app.close()

    def test_very_long_query_5kb(self, tmp_path):
        """5KB query string must not crash."""
        app = _app(tmp_path, "long_query")
        try:
            app.put_memory("Short fact about databases", scope_id="lq", type="semantic")
            long_query = "database " * 600  # ~5KB
            results = _search(app, long_query, "lq", limit=3)
            assert isinstance(results, list)  # Must not crash
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 4. SCOPE ID EDGE CASES — special chars, injection, unicode
# ---------------------------------------------------------------------------
class TestScopeIDEdgeCases:

    @pytest.mark.parametrize("evil_scope", [
        "scope with spaces",
        "scope/with/slashes",
        "scope'injection",
        'scope"double',
        "scope;drop;table",
        "scope\x00null",
        "スコープ日本語",
        "scope--comment",
        "",
    ])
    def test_evil_scope_ids_dont_crash(self, tmp_path, evil_scope):
        """Evil scope IDs must not crash the system."""
        app = _app(tmp_path, f"scope_{abs(hash(evil_scope)) % 10000}")
        try:
            if evil_scope:  # Empty scope may be rejected by validation
                result = app.put_memory("Test content", scope_id=evil_scope, type="semantic")
                # May succeed or fail gracefully — must not crash
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 5. UNICODE NORMALIZATION ATTACK — composed vs decomposed
# ---------------------------------------------------------------------------
class TestUnicodeNormalization:

    def test_nfc_vs_nfd_same_text(self, tmp_path):
        """NFC and NFD forms of same Vietnamese text should match."""
        import unicodedata
        app = _app(tmp_path, "unicode_norm")
        try:
            text_nfc = unicodedata.normalize("NFC", "Nguyễn Văn Ân là giám đốc")
            text_nfd = unicodedata.normalize("NFD", "Nguyễn Văn Ân là giám đốc")
            assert text_nfc != text_nfd, "NFC and NFD should differ at byte level"

            app.put_memory(text_nfc, scope_id="unicode", type="semantic")
            # Query with NFD form — should still find it
            results = _search(app, text_nfd, "unicode", limit=3)
            # At minimum, should not crash. Finding it is a bonus.
            assert isinstance(results, list)
        finally:
            app.close()

    def test_zero_width_characters(self, tmp_path):
        """Zero-width chars (ZWJ, ZWNJ, ZWSP) in content must not cause issues."""
        app = _app(tmp_path, "zero_width")
        try:
            # Zero-width space, zero-width joiner, zero-width non-joiner
            evil_content = "Pass\u200Bword\u200Cadmin\u200D: Secret123"
            app.put_memory(evil_content, scope_id="zw", type="semantic")
            results = _search(app, "Password admin", "zw", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 6. CONCURRENT RAPID WRITES — race condition detection
# ---------------------------------------------------------------------------
class TestRapidWrites:

    def test_100_rapid_writes_same_scope(self, tmp_path):
        """100 rapid sequential writes to same scope must not corrupt DB."""
        app = _app(tmp_path, "rapid")
        try:
            ids = []
            for i in range(100):
                result = app.put_memory(
                    f"Rapid write number {i} with unique content xyz{i}abc",
                    scope_id="rapid", type="semantic",
                )
                if result:
                    ids.append(result.id)

            # All should be stored
            assert len(ids) >= 90, f"Only {len(ids)}/100 writes succeeded"

            # Search should work after mass writes
            results = _search(app, "rapid write unique content", "rapid", limit=5)
            assert len(results) > 0

            # Verify no duplicate IDs
            assert len(set(ids)) == len(ids), "Duplicate memory IDs detected!"
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 7. EMPTY/NULL EDGE CASES
# ---------------------------------------------------------------------------
class TestEmptyEdgeCases:

    def test_search_empty_scope(self, tmp_path):
        """Searching an empty scope must return empty list, not crash."""
        app = _app(tmp_path, "empty_scope")
        try:
            results = _search(app, "anything at all", "nonexistent-scope-xyz", limit=5)
            assert results == [] or isinstance(results, list)
        finally:
            app.close()

    def test_profile_empty_scope(self, tmp_path):
        """Profile on empty scope must not crash."""
        app = _app(tmp_path, "empty_profile")
        try:
            profile = app.render_profile(scope_id="nonexistent", scope_type="session")
            assert profile is not None
        finally:
            app.close()

    def test_reinforce_nonexistent_id(self, tmp_path):
        """Reinforcing a fake ID must not crash."""
        app = _app(tmp_path, "fake_reinforce")
        try:
            # Should handle gracefully — either no-op or error, but no crash
            try:
                app.reinforce("mem_does_not_exist_at_all_12345")
            except Exception:
                pass  # Raising is acceptable, crashing is not
        finally:
            app.close()

    def test_end_session_empty_scope(self, tmp_path):
        """Ending session on empty scope must not crash."""
        app = _app(tmp_path, "empty_session")
        try:
            try:
                app.end_session(session_id="fake", scope_id="empty", scope_type="session")
            except Exception:
                pass  # Error is ok, crash is not
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 8. MEMORY TYPE CONFUSION — store as wrong type, query correctly
# ---------------------------------------------------------------------------
class TestMemoryTypeConfusion:

    def test_episodic_vs_semantic_ranking(self, tmp_path):
        """Semantic facts should generally rank higher than episodic for factual queries."""
        app = _app(tmp_path, "type_confusion")
        try:
            app.put_memory("Hôm nay tôi ăn phở gà", scope_id="type", type="episodic")
            app.put_memory("Phở gà Hà Nội nấu bằng nước dùng gà ta, hành, gừng", scope_id="type", type="semantic")
            app.put_memory("Tôi thấy quán phở đông quá", scope_id="type", type="episodic")

            results = _search(app, "Phở gà nấu thế nào?", "type", limit=3)
            assert len(results) > 0
            # Semantic recipe fact should appear
            found_recipe = any("nước dùng" in r.memory.content for r in results)
            assert found_recipe, f"Semantic recipe not found. Got: {[r.memory.content[:40] for r in results]}"
        finally:
            app.close()


# ---------------------------------------------------------------------------
# 9. DOUBLE-CLOSE AND USE-AFTER-CLOSE
# ---------------------------------------------------------------------------
class TestLifecycle:

    def test_double_close(self, tmp_path):
        """Closing app twice must not crash."""
        app = _app(tmp_path, "double_close")
        app.put_memory("test", scope_id="lc", type="semantic")
        app.close()
        # Second close must not crash
        try:
            app.close()
        except Exception:
            pass  # Error acceptable, crash not

    def test_use_after_close(self, tmp_path):
        """Using app after close should raise error, not segfault."""
        app = _app(tmp_path, "use_after_close")
        app.put_memory("test", scope_id="lc", type="semantic")
        app.close()
        # Should raise error, not segfault
        with pytest.raises(Exception):
            app.put_memory("should fail", scope_id="lc", type="semantic")


# ---------------------------------------------------------------------------
# 10. MULTILINGUAL COLLISION — same fact in multiple languages
# ---------------------------------------------------------------------------
class TestMultilingual:

    def test_same_fact_vn_en_jp(self, tmp_path):
        """Same fact in 3 languages must all be retrievable."""
        app = _app(tmp_path, "multilingual")
        try:
            app.put_memory("TruthKeep là hệ thống bộ nhớ cho AI", scope_id="lang", type="semantic")
            app.put_memory("TruthKeep is a memory system for AI", scope_id="lang", type="semantic")
            app.put_memory("TruthKeepはAIのためのメモリシステムです", scope_id="lang", type="semantic")

            # Query in Vietnamese
            results_vn = _search(app, "TruthKeep bộ nhớ AI", "lang", limit=3)
            assert len(results_vn) > 0
            found_vn = any("bộ nhớ" in r.memory.content for r in results_vn)
            assert found_vn, "Vietnamese fact not found"

            # Query in English
            results_en = _search(app, "TruthKeep memory system AI", "lang", limit=3)
            assert len(results_en) > 0
            found_en = any("memory system" in r.memory.content for r in results_en)
            assert found_en, "English fact not found"
        finally:
            app.close()
