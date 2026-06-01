"""TruthKeep Ragnarök Tests — Round 9: MCP layer, Hygiene beasts, 10K scale.

This is the FINAL round — attacks the last 3 untested surfaces:
1. MCP server argument parsing (the actual production entry point)
2. Hygiene beasts (smilodon, librarian, nutcracker)
3. Scale: 10,000+ memories in single scope
"""

import time
import threading
import pytest
from aegis_py.app import AegisApp


def _app(tmp_path, name="ragnarok"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ===========================================================================
# 1. SCALE: 10,000 MEMORIES IN SINGLE SCOPE
# ===========================================================================
class TestScale10K:

    def test_10k_memories_search_returns_results(self, tmp_path):
        """Store 10,000 memories in one scope. Search must still return results."""
        app = _app(tmp_path, "scale_10k")
        try:
            # Batch insert 10,000
            for i in range(10_000):
                app.put_memory(
                    f"Scale test memory number {i}: random data about topic {i % 100}",
                    scope_id="massive", type="semantic",
                )

            # Search must return results
            results = _search(app, "Scale test memory topic 42", "massive", limit=5)
            assert len(results) > 0, "No results from 10K memories!"
        finally:
            app.close()

    def test_10k_memories_search_latency(self, tmp_path):
        """Search latency on 10K memories must be < 5 seconds."""
        app = _app(tmp_path, "scale_latency")
        try:
            for i in range(10_000):
                app.put_memory(
                    f"Latency benchmark fact {i} about engineering team {i % 50}",
                    scope_id="lat", type="semantic",
                )

            # Measure search latency (average of 5 queries)
            times = []
            queries = [
                "engineering team 25",
                "latency benchmark fact 9999",
                "random nonexistent content xyz",
                "engineering team",
                "fact about team 0",
            ]
            for q in queries:
                start = time.perf_counter()
                _search(app, q, "lat", limit=5)
                times.append(time.perf_counter() - start)

            avg = sum(times) / len(times)
            assert avg < 5.0, f"Search too slow on 10K: avg={avg:.2f}s"
        finally:
            app.close()

    def test_10k_memories_doctor(self, tmp_path):
        """Doctor on 10K memories must not crash or timeout."""
        app = _app(tmp_path, "scale_doctor")
        try:
            for i in range(10_000):
                app.put_memory(f"Doctor scale fact {i}", scope_id="doc", type="semantic")

            start = time.perf_counter()
            result = app.doctor()
            elapsed = time.perf_counter() - start
            assert isinstance(result, dict)
            assert elapsed < 60, f"Doctor took {elapsed:.1f}s on 10K — too slow!"
        finally:
            app.close()

    def test_10k_memories_status(self, tmp_path):
        """Status/footprint on 10K memories."""
        app = _app(tmp_path, "scale_status")
        try:
            for i in range(10_000):
                app.put_memory(f"Status scale fact {i}", scope_id="st", type="semantic")

            status = app.status()
            assert isinstance(status, dict)

            footprint = app.storage_footprint()
            assert isinstance(footprint, dict)
        finally:
            app.close()


# ===========================================================================
# 2. HYGIENE BEASTS — trigger maintenance subsystems
# ===========================================================================
class TestHygieneBeasts:

    def test_maintenance_full_cycle(self, tmp_path):
        """Full maintenance cycle on populated DB."""
        app = _app(tmp_path, "hygiene_full")
        try:
            for i in range(100):
                app.put_memory(f"Hygiene fact {i}", scope_id="hyg", type="semantic")

            # Archive some
            results = _search(app, "Hygiene fact", "hyg", limit=10)
            for r in results[:5]:
                try:
                    from aegis_py.hygiene.transitions import transition_memory
                    transition_memory(app.storage, r.memory.id, status="archived", event="test")
                except Exception:
                    pass

            # Run full maintenance
            result = app.maintenance()
            assert isinstance(result, dict)
        finally:
            app.close()

    def test_maintenance_after_mass_corrections(self, tmp_path):
        """Maintenance after 50 corrections."""
        app = _app(tmp_path, "hygiene_correct")
        try:
            for i in range(50):
                app.put_memory(f"CEO là người {i}", scope_id="default", type="semantic")
                try:
                    app.memory_correct(f"CEO thực tế là người {i+1}")
                except Exception:
                    pass

            result = app.maintenance()
            assert isinstance(result, dict)
        finally:
            app.close()

    def test_maintenance_after_mass_forget(self, tmp_path):
        """Maintenance after forgetting 50 memories."""
        app = _app(tmp_path, "hygiene_forget")
        try:
            ids = []
            for i in range(100):
                m = app.put_memory(f"Forgettable fact {i}", scope_id="fg", type="semantic")
                if m:
                    ids.append(m.id)

            for mid in ids[:50]:
                try:
                    app.memory_forget(mid)
                except Exception:
                    pass

            result = app.maintenance()
            assert isinstance(result, dict)
        finally:
            app.close()

    def test_compact_after_maintenance(self, tmp_path):
        """Compaction after maintenance cycle."""
        app = _app(tmp_path, "hygiene_compact")
        try:
            for i in range(100):
                app.put_memory(f"Compact fact {i}", scope_id="cmp", type="semantic")

            app.maintenance()
            result = app.compact_storage(scope_id="cmp", scope_type="session")
            assert isinstance(result, dict) or result is None
        finally:
            app.close()

    def test_double_maintenance(self, tmp_path):
        """Running maintenance twice in a row must not corrupt."""
        app = _app(tmp_path, "hygiene_double")
        try:
            for i in range(50):
                app.put_memory(f"Double maintenance fact {i}", scope_id="dm", type="semantic")

            r1 = app.maintenance()
            r2 = app.maintenance()
            assert isinstance(r1, dict)
            assert isinstance(r2, dict)

            # Data must survive
            results = _search(app, "Double maintenance", "dm", limit=5)
            assert len(results) > 0
        finally:
            app.close()

    def test_concurrent_maintenance(self, tmp_path):
        """Two threads running maintenance simultaneously."""
        app = _app(tmp_path, "hygiene_race")
        errors = []

        for i in range(50):
            app.put_memory(f"Concurrent maintenance {i}", scope_id="cm", type="semantic")

        def maintainer(tid):
            try:
                app.maintenance()
            except Exception as e:
                errors.append(f"Thread {tid}: {e}")

        threads = [threading.Thread(target=maintainer, args=(t,)) for t in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        app.close()
        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"Concurrent maintenance errors: {real_errors}"


# ===========================================================================
# 3. MCP-LIKE ARGUMENT PARSING — simulate what MCP server receives
# ===========================================================================
class TestMCPArgumentParsing:

    def test_put_memory_missing_content(self, tmp_path):
        """put_memory with empty/None content."""
        app = _app(tmp_path, "mcp_empty")
        try:
            for content in ["", "   ", None]:
                try:
                    app.put_memory(content, scope_id="mcp", type="semantic")
                except Exception:
                    pass  # Error ok, crash not
        finally:
            app.close()

    def test_put_memory_missing_scope(self, tmp_path):
        """put_memory with empty/None scope_id."""
        app = _app(tmp_path, "mcp_noscope")
        try:
            for scope in ["", None, "   "]:
                try:
                    app.put_memory("Test content", scope_id=scope, type="semantic")
                except Exception:
                    pass
        finally:
            app.close()

    def test_put_memory_invalid_type(self, tmp_path):
        """put_memory with invalid memory type."""
        app = _app(tmp_path, "mcp_badtype")
        try:
            evil_types = ["", None, "INVALID", "sql_injection", "semantic; DROP TABLE", 123, True, []]
            for t in evil_types:
                try:
                    app.put_memory("Test", scope_id="mcp", type=t)
                except Exception:
                    pass
        finally:
            app.close()

    def test_search_missing_query(self, tmp_path):
        """search with empty/None query."""
        app = _app(tmp_path, "mcp_noquery")
        try:
            app.put_memory("Seed data", scope_id="mcp", type="semantic")
            for q in ["", "   ", None]:
                try:
                    _search(app, q, "mcp", limit=3)
                except Exception:
                    pass
        finally:
            app.close()

    def test_search_invalid_limit(self, tmp_path):
        """search with invalid limit values."""
        app = _app(tmp_path, "mcp_badlimit")
        try:
            app.put_memory("Limit test", scope_id="mcp", type="semantic")
            evil_limits = [0, -1, -999, 999999, None]
            for lim in evil_limits:
                try:
                    app.search("Limit test", scope_id="mcp", scope_type="session", limit=lim)
                except Exception:
                    pass
        finally:
            app.close()

    def test_reinforce_invalid_id(self, tmp_path):
        """reinforce with invalid memory IDs."""
        app = _app(tmp_path, "mcp_reinforce")
        try:
            evil_ids = ["", None, "not_a_real_id", "mem_" + "x" * 10000, "'; DROP TABLE;--", 123]
            for mid in evil_ids:
                try:
                    app.reinforce(mid)
                except Exception:
                    pass
        finally:
            app.close()

    def test_memory_correct_invalid_input(self, tmp_path):
        """memory_correct with edge case inputs."""
        app = _app(tmp_path, "mcp_correct")
        try:
            evil_inputs = [None, 123, [], {}, True, ""]
            for inp in evil_inputs:
                try:
                    app.memory_correct(inp)
                except Exception:
                    pass
        finally:
            app.close()

    def test_memory_forget_invalid_id(self, tmp_path):
        """memory_forget with invalid IDs."""
        app = _app(tmp_path, "mcp_forget")
        try:
            evil_ids = ["", None, 123, "mem_nonexistent", "'; DROP TABLE;--"]
            for mid in evil_ids:
                try:
                    app.memory_forget(mid)
                except Exception:
                    pass
        finally:
            app.close()

    def test_end_session_invalid_args(self, tmp_path):
        """end_session with invalid arguments."""
        app = _app(tmp_path, "mcp_session")
        try:
            evil_combos = [
                {"session_id": None, "scope_id": "x", "scope_type": "session"},
                {"session_id": "", "scope_id": "", "scope_type": ""},
                {"session_id": "test", "scope_id": None, "scope_type": None},
                {"session_id": 123, "scope_id": 456, "scope_type": 789},
            ]
            for combo in evil_combos:
                try:
                    app.end_session(**combo)
                except Exception:
                    pass
        finally:
            app.close()

    def test_link_memories_invalid_args(self, tmp_path):
        """link_memories with invalid arguments."""
        app = _app(tmp_path, "mcp_link")
        try:
            evil_combos = [
                ("", "", "related"),
                (None, None, None),
                ("mem_fake1", "mem_fake2", ""),
                ("mem_fake1", "mem_fake2", "'; DROP TABLE;--"),
                ("mem_fake1", "mem_fake2", "A" * 10000),
            ]
            for src, dst, ltype in evil_combos:
                try:
                    app.link_memories(src, dst, link_type=ltype)
                except Exception:
                    pass
        finally:
            app.close()


# ===========================================================================
# 4. SCALE + CONCURRENCY COMBINED — the ultimate stress
# ===========================================================================
class TestScaleConcurrency:

    def test_5_threads_writing_2000_each(self, tmp_path):
        """5 threads each writing 2000 memories (10K total). Must not crash."""
        app = _app(tmp_path, "scale_threads")
        errors = []

        def writer(thread_id):
            try:
                for i in range(2000):
                    try:
                        app.put_memory(
                            f"Thread {thread_id} fact {i} about system {i % 20}",
                            scope_id="scale_t", type="semantic",
                        )
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=300)

        # Verify data exists
        try:
            results = _search(app, "Thread fact system", "scale_t", limit=5)
            assert len(results) > 0, "No data after 5-thread 10K write!"
        finally:
            app.close()

        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"Scale concurrency errors: {real_errors[:3]}"

    def test_search_during_10k_writes(self, tmp_path):
        """Search while 10K memories are being written."""
        app = _app(tmp_path, "scale_search_write")
        errors = []
        search_results = []

        # Seed some data
        for i in range(100):
            app.put_memory(f"Seed fact {i}", scope_id="srw", type="semantic")

        def writer():
            try:
                for i in range(5000):
                    try:
                        app.put_memory(f"Writing fact {i}", scope_id="srw", type="semantic")
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"Writer: {e}")

        def searcher():
            try:
                for i in range(100):
                    try:
                        results = _search(app, "Seed fact", "srw", limit=3)
                        search_results.append(len(results))
                    except Exception:
                        pass
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Searcher: {e}")

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=searcher)
        t1.start()
        t2.start()
        t1.join(timeout=300)
        t2.join(timeout=300)

        app.close()
        real_errors = [e for e in errors if "locked" not in e.lower()]
        assert len(real_errors) == 0, f"Search-during-write errors: {real_errors}"
        # At least some searches should have returned results
        assert sum(search_results) > 0, "Zero search results during 10K writes!"
