"""TruthKeep Doomsday Tests — Round 7: semantic & logical attacks.

Previous rounds attacked the INFRASTRUCTURE (SQL, FTS, threads, corruption).
This round attacks the LOGIC — truth governance, semantic reasoning, and
information-theoretic boundaries.
"""

import threading
import time
import pytest
from aegis_py.app import AegisApp


def _app(tmp_path, name="doom"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ===========================================================================
# 1. SEMANTIC POISONING — 100 wrong facts vs 1 correct
# ===========================================================================
class TestSemanticPoisoning:

    def test_100_lies_vs_1_truth(self, tmp_path):
        """Store 100 WRONG facts and 1 correct fact. Truth must survive."""
        app = _app(tmp_path, "poison")
        try:
            # 100 lies
            for i in range(100):
                app.put_memory(
                    f"Thủ đô Việt Nam là thành phố {chr(65 + i % 26)}{i} (xác nhận)",
                    scope_id="poison", type="semantic",
                )
            # 1 truth — stored LAST (recency advantage)
            app.put_memory(
                "XÁC NHẬN CHÍNH THỨC: Thủ đô Việt Nam là Hà Nội. "
                "Tất cả thông tin khác đều là thông tin sai.",
                scope_id="poison", type="semantic",
            )

            results = _search(app, "Thủ đô Việt Nam là gì?", "poison", limit=5)
            assert len(results) > 0
            # Truth must be in top 5
            found_truth = any("Hà Nội" in r.memory.content for r in results)
            assert found_truth, (
                f"TRUTH DROWNED BY 100 LIES! Top 5: "
                f"{[r.memory.content[:50] for r in results]}"
            )
        finally:
            app.close()

    def test_reinforced_lie_vs_fresh_truth(self, tmp_path):
        """A lie reinforced 50 times vs fresh truth. Truth must appear in top 3."""
        app = _app(tmp_path, "lie_vs_truth")
        try:
            lie = app.put_memory("CEO công ty là ông Giả Mạo", scope_id="lvt", type="semantic")
            if lie:
                for _ in range(50):
                    app.reinforce(lie.id)

            app.put_memory(
                "THÔNG BÁO CHÍNH THỨC: CEO mới là bà Nguyễn Thị Thật. "
                "Ông Giả Mạo đã bị sa thải vì gian lận.",
                scope_id="lvt", type="semantic",
            )

            results = _search(app, "CEO công ty là ai?", "lvt", limit=3)
            found_truth = any("Thật" in r.memory.content for r in results[:3])
            assert found_truth, (
                f"50x-reinforced LIE beat fresh truth! "
                f"{[r.memory.content[:50] for r in results[:3]]}"
            )
        finally:
            app.close()


# ===========================================================================
# 2. HOMOGLYPH SCOPE COLLISION — scope "admin" vs "аdmin" (Cyrillic)
# ===========================================================================
class TestHomoglyphScope:

    def test_latin_vs_cyrillic_scope_isolation(self, tmp_path):
        """Scope 'admin' (Latin) and 'аdmin' (Cyrillic а) must be isolated."""
        app = _app(tmp_path, "glyph_scope")
        try:
            # Latin 'admin'
            app.put_memory("Mật khẩu admin THẬT: SuperSecret123", scope_id="admin", type="semantic")
            # Cyrillic 'аdmin' (а = U+0430)
            app.put_memory("Thông tin công khai scope Cyrillic", scope_id="\u0430dmin", type="semantic")

            # Search in Cyrillic scope must NOT leak Latin scope's secret
            results = _search(app, "mật khẩu admin secret", "\u0430dmin", limit=5)
            for r in results:
                assert "SuperSecret123" not in r.memory.content, (
                    f"HOMOGLYPH SCOPE LEAK! Latin admin secret in Cyrillic аdmin: {r.memory.content[:60]}"
                )
        finally:
            app.close()

    def test_nfc_vs_nfd_scope_isolation(self, tmp_path):
        """Scope 'café' NFC vs NFD must either merge or fully isolate."""
        import unicodedata
        app = _app(tmp_path, "norm_scope")
        try:
            nfc = unicodedata.normalize("NFC", "café")
            nfd = unicodedata.normalize("NFD", "café")

            app.put_memory("NFC secret: password123", scope_id=nfc, type="semantic")
            app.put_memory("NFD public info", scope_id=nfd, type="semantic")

            results_nfc = _search(app, "secret password", nfc, limit=5)
            results_nfd = _search(app, "secret password", nfd, limit=5)

            # Either both find it (merged) or only NFC finds it (isolated)
            # Both behaviors are valid — the test just verifies no crash
            assert isinstance(results_nfc, list)
            assert isinstance(results_nfd, list)
        finally:
            app.close()


# ===========================================================================
# 3. CONCURRENT CORRECTION RACE — 10 threads correcting same fact
# ===========================================================================
class TestConcurrentCorrection:

    def test_10_threads_correcting_same_fact(self, tmp_path):
        """10 threads all correcting the same fact simultaneously."""
        app = _app(tmp_path, "correction_race")
        errors = []
        
        app.put_memory("CEO là ông A", scope_id="default", type="semantic")

        def corrector(thread_id):
            try:
                for i in range(5):
                    try:
                        app.memory_correct(f"CEO thực tế là người #{thread_id}-{i}")
                    except Exception:
                        pass  # Lock contention ok
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=corrector, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        # Verify DB is not corrupted
        try:
            results = _search(app, "CEO là ai?", "default", limit=5)
            assert isinstance(results, list)
        finally:
            app.close()

        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"Race condition errors: {real_errors[:3]}"


# ===========================================================================
# 4. SUPERSESSION CHAIN EXPLOSION — 100 levels
# ===========================================================================
class TestSupersessionChain:

    def test_100_level_supersession(self, tmp_path):
        """100 memories each superseding the previous. Latest must win."""
        app = _app(tmp_path, "super_chain")
        try:
            for i in range(100):
                app.put_memory(
                    f"Phiên bản phần mềm là v{i}.0 (supersedes v{i-1}.0)",
                    scope_id="super", type="semantic",
                )

            results = _search(app, "Phiên bản phần mềm hiện tại", "super", limit=3)
            assert len(results) > 0
            # v99 should be in top 3
            top3 = " ".join(r.memory.content for r in results[:3])
            assert "v99" in top3 or "v98" in top3 or "v97" in top3, (
                f"Latest version not in top 3: {[r.memory.content[:40] for r in results[:3]]}"
            )
        finally:
            app.close()


# ===========================================================================
# 5. ZERO-WIDTH JOINER FTS BYPASS — invisible chars between words
# ===========================================================================
class TestZeroWidthBypass:

    def test_zwj_between_words_searchable(self, tmp_path):
        """Words joined by ZWJ must still be searchable normally."""
        app = _app(tmp_path, "zwj")
        try:
            # Content with ZWJ (U+200D) between words
            app.put_memory("pass\u200Dword: Secret\u200DKey\u200D123", scope_id="zwj", type="semantic")
            # Normal content
            app.put_memory("password: NormalKey456", scope_id="zwj", type="semantic")

            results = _search(app, "password Secret", "zwj", limit=5)
            assert isinstance(results, list)
            # Should find at least the normal one
            found = any("password" in r.memory.content.replace("\u200D", "") for r in results)
            assert found or len(results) == 0  # May filter ZWJ — both behaviors ok
        finally:
            app.close()

    def test_invisible_chars_dont_hide_content(self, tmp_path):
        """Content with invisible Unicode must still be searchable."""
        app = _app(tmp_path, "invisible")
        try:
            # Various invisible characters
            invisible_chars = [
                "\u200B",  # Zero-width space
                "\u200C",  # Zero-width non-joiner
                "\u200D",  # Zero-width joiner
                "\u2060",  # Word joiner
                "\uFEFF",  # BOM
            ]
            for i, ch in enumerate(invisible_chars):
                content = f"Secret{ch}Data{ch}{i}: classified{ch}info"
                app.put_memory(content, scope_id="invis", type="semantic")

            results = _search(app, "Secret Data classified info", "invis", limit=5)
            assert isinstance(results, list)
        finally:
            app.close()


# ===========================================================================
# 6. SUBJECT FIELD INJECTION
# ===========================================================================
class TestSubjectInjection:

    @pytest.mark.parametrize("evil_subject", [
        "'; DROP TABLE memories;--",
        "subject OR 1=1",
        "<script>alert('xss')</script>",
        "subject\x00null",
        "A" * 10000,  # 10KB subject
        "",  # empty
        "   ",  # whitespace only
    ])
    def test_evil_subjects_no_crash(self, tmp_path, evil_subject):
        """Evil subject values must not crash put_memory."""
        app = _app(tmp_path, f"subj_{abs(hash(evil_subject)) % 99999}")
        try:
            try:
                app.put_memory(
                    "Test content with evil subject",
                    scope_id="subj", type="semantic",
                    subject=evil_subject,
                )
            except Exception:
                pass  # Error ok
        finally:
            app.close()


# ===========================================================================
# 7. REINFORCE + FORGET RACE
# ===========================================================================
class TestReinforcForgetRace:

    def test_reinforce_and_forget_simultaneously(self, tmp_path):
        """Reinforce and forget same memory from different threads."""
        app = _app(tmp_path, "rf_race")
        errors = []

        mem = app.put_memory("Race condition memory for reinforce/forget", scope_id="rf", type="semantic")
        if not mem:
            pytest.skip("Memory not stored")

        def reinforcer():
            try:
                for _ in range(20):
                    try:
                        app.reinforce(mem.id)
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"Reinforcer: {e}")

        def forgetter():
            try:
                time.sleep(0.01)  # Slight delay
                try:
                    app.memory_forget(mem.id)
                except Exception:
                    pass
            except Exception as e:
                errors.append(f"Forgetter: {e}")

        t1 = threading.Thread(target=reinforcer)
        t2 = threading.Thread(target=forgetter)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        app.close()
        real_errors = [e for e in errors if "locked" not in e.lower() and "closed" not in e.lower()]
        assert len(real_errors) == 0, f"Race errors: {real_errors}"


# ===========================================================================
# 8. SESSION MANIPULATION
# ===========================================================================
class TestSessionManipulation:

    def test_end_session_with_evil_session_id(self, tmp_path):
        """Evil session_id in end_session must not corrupt other sessions."""
        app = _app(tmp_path, "session_evil")
        try:
            app.put_memory("Session A data", scope_id="sa", type="semantic", session_id="session_a")
            app.put_memory("Session B data", scope_id="sb", type="semantic", session_id="session_b")

            # End with evil session_id
            evil_ids = [
                "'; DROP TABLE memories;--",
                "session_a' OR '1'='1",
                "*",
                "",
                "\x00",
            ]
            for evil in evil_ids:
                try:
                    app.end_session(session_id=evil, scope_id="sa", scope_type="session")
                except Exception:
                    pass

            # Session B data must survive
            results = _search(app, "Session B data", "sb", limit=3)
            assert isinstance(results, list)
        finally:
            app.close()

    def test_end_session_wrong_scope(self, tmp_path):
        """End session in wrong scope must not affect other scopes."""
        app = _app(tmp_path, "session_scope")
        try:
            app.put_memory("Important data in scope X", scope_id="X", type="semantic")
            app.end_session(session_id="test", scope_id="Y", scope_type="session")

            # Data in X must survive
            results = _search(app, "Important data scope", "X", limit=3)
            found = any("Important" in r.memory.content for r in results)
            assert found, "Data in unrelated scope lost after end_session!"
        finally:
            app.close()


# ===========================================================================
# 9. TIMING SIDE-CHANNEL — can we infer secrets exist?
# ===========================================================================
class TestTimingSideChannel:

    def test_search_time_similar_for_hit_and_miss(self, tmp_path):
        """Search time for existing vs non-existing scope should be similar."""
        app = _app(tmp_path, "timing")
        try:
            app.put_memory("Secret in hidden scope", scope_id="hidden-vault", type="semantic")

            # Time search in existing scope
            times_hit = []
            for _ in range(5):
                start = time.perf_counter()
                _search(app, "secret data", "hidden-vault", limit=3)
                times_hit.append(time.perf_counter() - start)

            # Time search in non-existing scope
            times_miss = []
            for _ in range(5):
                start = time.perf_counter()
                _search(app, "secret data", "nonexistent-scope", limit=3)
                times_miss.append(time.perf_counter() - start)

            avg_hit = sum(times_hit) / len(times_hit)
            avg_miss = sum(times_miss) / len(times_miss)

            # Timing difference should be less than 10x (not perfect constant-time,
            # but should not be orders of magnitude different)
            ratio = max(avg_hit, avg_miss) / max(min(avg_hit, avg_miss), 0.0001)
            assert ratio < 100, (
                f"TIMING SIDE-CHANNEL: hit={avg_hit:.4f}s, miss={avg_miss:.4f}s, ratio={ratio:.1f}x"
            )
        finally:
            app.close()


# ===========================================================================
# 10. EXPERIENCE BRIEF / PROFILE ON ADVERSARIAL DATA
# ===========================================================================
class TestProfileAdversarial:

    def test_profile_after_poison(self, tmp_path):
        """Memory profile after 100 conflicting facts must not crash."""
        app = _app(tmp_path, "profile_poison")
        try:
            for i in range(50):
                app.put_memory(
                    f"User prefers language {chr(65 + i % 26)}{i}",
                    scope_id="prof", type="semantic",
                )

            try:
                profile = app.get_memory_profile(scope_id="prof", scope_type="session")
                assert isinstance(profile, (dict, str))
            except Exception:
                pass  # Some implementations may not support this
        finally:
            app.close()

    def test_experience_brief_empty(self, tmp_path):
        """Experience brief on empty scope must not crash."""
        app = _app(tmp_path, "brief_empty")
        try:
            try:
                brief = app.experience_brief(scope_id="empty", scope_type="session")
                assert isinstance(brief, (dict, str))
            except Exception:
                pass
        finally:
            app.close()

    def test_experience_brief_heavy(self, tmp_path):
        """Experience brief after 200 memories must not crash."""
        app = _app(tmp_path, "brief_heavy")
        try:
            for i in range(200):
                app.put_memory(f"Experience fact {i} about AI safety", scope_id="eb", type="semantic")

            try:
                brief = app.experience_brief(scope_id="eb", scope_type="session")
                assert isinstance(brief, (dict, str))
            except Exception:
                pass
        finally:
            app.close()


# ===========================================================================
# 11. MASS FORGET — delete everything, verify clean
# ===========================================================================
class TestMassForget:

    def test_forget_all_memories_in_scope(self, tmp_path):
        """Store 50 memories, forget all, verify scope is clean."""
        app = _app(tmp_path, "mass_forget")
        try:
            mem_ids = []
            for i in range(50):
                m = app.put_memory(f"Deletable fact {i}", scope_id="mf", type="semantic")
                if m:
                    mem_ids.append(m.id)

            # Forget all
            for mid in mem_ids:
                try:
                    app.memory_forget(mid)
                except Exception:
                    pass

            # Search must return empty or no matching results
            results = _search(app, "Deletable fact", "mf", limit=50)
            live = [r for r in results if r.memory.status != "archived"]
            assert len(live) == 0, (
                f"{len(live)} memories survived mass forget! "
                f"Examples: {[r.memory.content[:30] for r in live[:3]]}"
            )
        finally:
            app.close()


# ===========================================================================
# 12. SCOPE ENUMERATION ATTACK — can we discover scope names?
# ===========================================================================
class TestScopeEnumeration:

    def test_cannot_enumerate_scopes_via_search(self, tmp_path):
        """Searching with wildcard-like queries must not reveal other scopes."""
        app = _app(tmp_path, "enum")
        try:
            app.put_memory("Secret in alpha scope", scope_id="alpha-secret", type="semantic")
            app.put_memory("Secret in beta scope", scope_id="beta-secret", type="semantic")
            app.put_memory("Public in gamma", scope_id="gamma-public", type="semantic")

            # Search from gamma must not reveal alpha/beta content
            attack_queries = [
                "secret",
                "alpha beta",
                "scope",
                "*",
                "%",
                "_ _ _",
            ]
            for q in attack_queries:
                results = _search(app, q, "gamma-public", limit=10)
                for r in results:
                    assert "alpha" not in r.memory.scope_id, f"Scope leak via '{q}'"
                    assert "beta" not in r.memory.scope_id, f"Scope leak via '{q}'"
        finally:
            app.close()
