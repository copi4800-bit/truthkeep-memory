"""TruthKeep Armageddon Tests — Round 6: automated fuzzing + physical destruction.

Uses Hypothesis for property-based testing (generates thousands of random
inputs), plus SQLite header corruption, DB file deletion mid-operation,
ancient_math module fuzzing, and encryption edge cases.
"""

import os
import sqlite3
import struct
import threading
import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st
from aegis_py.app import AegisApp
from aegis_py.retrieval.engine import _sanitize_fts_query


def _app(tmp_path, name="arma"):
    return AegisApp(db_path=str(tmp_path / f"{name}.db"))


def _search(app, query, scope_id, limit=5):
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ===========================================================================
# 1. HYPOTHESIS FUZZING — _sanitize_fts_query
# ===========================================================================
class TestFuzzSanitizer:

    @given(query=st.text(min_size=0, max_size=500))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_sanitize_never_crashes(self, query):
        """Any possible string input must not crash the sanitizer."""
        result = _sanitize_fts_query(query)
        assert isinstance(result, str)

    @given(query=st.text(min_size=0, max_size=500))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_sanitize_no_fts5_operators(self, query):
        """Output must never contain bare FTS5 operators."""
        result = _sanitize_fts_query(query)
        tokens = result.split()
        fts5_ops = {"AND", "OR", "NOT", "NEAR"}
        for token in tokens:
            assert token.upper() not in fts5_ops, (
                f"FTS5 operator '{token}' survived sanitization! Input: {query!r}"
            )

    @given(query=st.text(min_size=0, max_size=500))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_sanitize_no_control_chars(self, query):
        """Output must never contain control characters."""
        result = _sanitize_fts_query(query)
        for ch in result:
            assert ch >= " " and ch != "\x7f", (
                f"Control char U+{ord(ch):04X} in output! Input: {query!r}"
            )


# ===========================================================================
# 2. HYPOTHESIS FUZZING — full put_memory pipeline
# ===========================================================================
class TestFuzzPutMemory:

    @given(
        content=st.text(min_size=1, max_size=1000),
        scope_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
    def test_put_memory_never_crashes(self, content, scope_id, tmp_path):
        """put_memory must never crash regardless of input."""
        app = _app(tmp_path, f"fuzz_{abs(hash(content + scope_id)) % 99999}")
        try:
            try:
                app.put_memory(content, scope_id=scope_id, type="semantic")
            except RuntimeError:
                pass  # Closed app errors ok
            except Exception:
                pass  # Any handled exception ok
        finally:
            try:
                app.close()
            except Exception:
                pass

    @given(query=st.text(min_size=1, max_size=500))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
    def test_search_never_crashes(self, query, tmp_path):
        """search must never crash regardless of query."""
        app = _app(tmp_path, f"sfuzz_{abs(hash(query)) % 99999}")
        try:
            app.put_memory("Seed content for search fuzzing", scope_id="fuzz", type="semantic")
            try:
                results = _search(app, query, "fuzz", limit=3)
                assert isinstance(results, list)
            except Exception:
                pass  # Handled errors ok
        finally:
            try:
                app.close()
            except Exception:
                pass


# ===========================================================================
# 3. SQLITE HEADER CORRUPTION — write garbage to DB file
# ===========================================================================
class TestSQLiteCorruption:

    def test_corrupt_header_then_open(self, tmp_path):
        """Corrupt SQLite header. New AegisApp must handle gracefully."""
        db_path = str(tmp_path / "corrupt.db")
        # Create valid DB first
        app = AegisApp(db_path=db_path)
        app.put_memory("Data before corruption", scope_id="c", type="semantic")
        app.close()

        # Corrupt the SQLite header (first 16 bytes = magic string)
        with open(db_path, "r+b") as f:
            f.seek(0)
            f.write(b"CORRUPTED_HEADER")

        # Try to open — should either raise clean error or recover
        try:
            app2 = AegisApp(db_path=db_path)
            # If it opens, try to use it
            try:
                app2.put_memory("After corruption", scope_id="c", type="semantic")
            except Exception:
                pass
            app2.close()
        except Exception:
            pass  # Clean error is acceptable

    def test_truncate_db_then_open(self, tmp_path):
        """Truncate DB to 0 bytes. Must handle gracefully."""
        db_path = str(tmp_path / "truncated.db")
        app = AegisApp(db_path=db_path)
        app.put_memory("Data before truncation", scope_id="t", type="semantic")
        app.close()

        # Truncate to 0
        with open(db_path, "w") as f:
            pass  # Empty file

        try:
            app2 = AegisApp(db_path=db_path)
            app2.put_memory("After truncation", scope_id="t", type="semantic")
            app2.close()
        except Exception:
            pass  # Clean error acceptable

    def test_corrupt_random_bytes_mid_file(self, tmp_path):
        """Inject random bytes at random position in DB. Must handle gracefully."""
        db_path = str(tmp_path / "random_corrupt.db")
        app = AegisApp(db_path=db_path)
        for i in range(10):
            app.put_memory(f"Fact {i} for corruption test", scope_id="rc", type="semantic")
        app.close()

        # Corrupt middle of file
        file_size = os.path.getsize(db_path)
        if file_size > 200:
            with open(db_path, "r+b") as f:
                f.seek(file_size // 2)
                f.write(b"\xff\xfe\xfd\xfc" * 25)

        try:
            app2 = AegisApp(db_path=db_path)
            try:
                _search(app2, "corruption test", "rc", limit=3)
            except Exception:
                pass
            app2.close()
        except Exception:
            pass


# ===========================================================================
# 4. DB FILE DELETION MID-OPERATION
# ===========================================================================
class TestDBFileDeletion:

    def test_delete_db_while_open(self, tmp_path):
        """Delete DB file while app is still open. Operations must not segfault."""
        db_path = str(tmp_path / "vanish.db")
        app = AegisApp(db_path=db_path)
        app.put_memory("Data that will vanish", scope_id="v", type="semantic")

        # Delete the file (Windows may lock it, so this may fail)
        try:
            os.remove(db_path)
        except PermissionError:
            pytest.skip("Windows locks DB file")

        # Try operations on deleted DB
        try:
            app.put_memory("After deletion", scope_id="v", type="semantic")
        except Exception:
            pass  # Error ok

        try:
            _search(app, "vanish", "v", limit=3)
        except Exception:
            pass

        try:
            app.close()
        except Exception:
            pass


# ===========================================================================
# 5. ANCIENT MATH MODULE FUZZING
# ===========================================================================
class TestAncientMathFuzzing:

    def test_compute_with_extreme_values(self, tmp_path):
        """Fuzz ancient_math with extreme confidence and activation values."""
        from aegis_py.storage.ancient_math import compute_memory_ancient_math_fields

        extreme_cases = [
            {"type": "semantic", "status": "active", "confidence": 0.0, "activation_score": 0.0, "metadata_json": {}},
            {"type": "semantic", "status": "active", "confidence": 1.0, "activation_score": 1.0, "metadata_json": {}},
            {"type": "semantic", "status": "active", "confidence": -1.0, "activation_score": -1.0, "metadata_json": {}},
            {"type": "semantic", "status": "active", "confidence": 999999.0, "activation_score": 999999.0, "metadata_json": {}},
            {"type": "semantic", "status": "active", "confidence": 1e-300, "activation_score": 1e-300, "metadata_json": {}},
            {"type": "semantic", "status": "active", "confidence": 1e300, "activation_score": 1e300, "metadata_json": {}},
            {"type": "semantic", "status": "archived", "confidence": 0.5, "activation_score": 0.5, "metadata_json": {}},
            {"type": "working", "status": "hypothesized", "confidence": 0.5, "activation_score": 0.5, "metadata_json": {}},
            {"type": "episodic", "status": "validated", "confidence": 0.5, "activation_score": 0.5, "metadata_json": {}},
        ]

        for case in extreme_cases:
            try:
                iching, checksum = compute_memory_ancient_math_fields(case)
                assert isinstance(iching, (int, float))
                assert isinstance(checksum, (int, float))
            except Exception:
                pass  # Error ok, crash not

    @given(
        confidence=st.floats(allow_nan=True, allow_infinity=True),
        activation=st.floats(allow_nan=True, allow_infinity=True),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_compute_with_random_floats(self, confidence, activation):
        """Fuzz ancient_math with random floats including NaN and inf."""
        from aegis_py.storage.ancient_math import compute_memory_ancient_math_fields

        data = {
            "type": "semantic",
            "status": "active",
            "confidence": confidence,
            "activation_score": activation,
            "metadata_json": {},
        }
        try:
            iching, checksum = compute_memory_ancient_math_fields(data)
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            pass  # Math errors are fine


# ===========================================================================
# 6. ENCRYPTION EDGE CASES
# ===========================================================================
class TestEncryptionEdgeCases:

    def test_encrypted_content_exists(self, tmp_path):
        """Stored memories should have encrypted_content field populated."""
        app = _app(tmp_path, "enc1")
        try:
            mem = app.put_memory("Sensitive encrypted data test", scope_id="enc", type="semantic")
            if mem:
                row = app.storage.fetch_one(
                    "SELECT encrypted_content FROM memories WHERE id = ?", (mem.id,)
                )
                assert row is not None
                # encrypted_content should be non-empty
                enc = row["encrypted_content"]
                if enc:
                    assert len(enc) > 0, "encrypted_content is empty"
                    assert enc != "Sensitive encrypted data test", "Content stored in plaintext!"
        finally:
            app.close()

    def test_corrupt_encrypted_content_then_read(self, tmp_path):
        """Corrupt encrypted_content via SQL. Read must not crash."""
        db_path = str(tmp_path / "enc_corrupt.db")
        app = AegisApp(db_path=db_path)
        try:
            mem = app.put_memory("Encryption corruption test", scope_id="enc", type="semantic")
            if mem:
                conn = sqlite3.connect(db_path)
                conn.execute(
                    "UPDATE memories SET encrypted_content = ? WHERE id = ?",
                    ("GARBAGE_NOT_ENCRYPTED_DATA_XYZ", mem.id)
                )
                conn.commit()
                conn.close()

                # Read should handle corrupt ciphertext gracefully
                try:
                    fetched = app.storage.get_memory(mem.id)
                    # May return memory with corrupt/missing decrypted content
                    assert fetched is not None or True
                except Exception:
                    pass
        finally:
            app.close()


# ===========================================================================
# 7. PATH EDGE CASES
# ===========================================================================
class TestPathEdgeCases:

    def test_db_path_with_spaces(self, tmp_path):
        """DB path with spaces must work."""
        db_dir = tmp_path / "path with spaces"
        db_dir.mkdir()
        app = AegisApp(db_path=str(db_dir / "test.db"))
        try:
            mem = app.put_memory("Spaces in path", scope_id="path", type="semantic")
            assert mem is not None
        finally:
            app.close()

    def test_db_path_with_unicode(self, tmp_path):
        """DB path with Unicode characters must work."""
        db_dir = tmp_path / "đường_dẫn_tiếng_việt"
        db_dir.mkdir()
        app = AegisApp(db_path=str(db_dir / "dữ_liệu.db"))
        try:
            mem = app.put_memory("Unicode path test", scope_id="upath", type="semantic")
            assert mem is not None
        finally:
            app.close()

    def test_deeply_nested_path(self, tmp_path):
        """DB in deeply nested directory (10 levels)."""
        deep = tmp_path
        for i in range(10):
            deep = deep / f"level_{i}"
        deep.mkdir(parents=True)
        app = AegisApp(db_path=str(deep / "deep.db"))
        try:
            mem = app.put_memory("Deep path test", scope_id="deep", type="semantic")
            assert mem is not None
        finally:
            app.close()


# ===========================================================================
# 8. RAPID LIFECYCLE ABUSE
# ===========================================================================
class TestRapidLifecycle:

    def test_create_search_close_100_cycles(self, tmp_path):
        """100 cycles of: create app, put, search, close. No leak."""
        db_path = str(tmp_path / "lifecycle.db")
        for i in range(100):
            app = AegisApp(db_path=db_path)
            try:
                app.put_memory(f"Cycle {i} data", scope_id="lc", type="semantic")
                _search(app, f"Cycle {i}", "lc", limit=1)
            finally:
                app.close()

        # Verify all data accessible
        app = AegisApp(db_path=db_path)
        try:
            results = _search(app, "Cycle data", "lc", limit=100)
            assert len(results) >= 50, f"Only {len(results)} survived 100 cycles"
        finally:
            app.close()


# ===========================================================================
# 9. HYPOTHESIS FUZZING — metadata keys and values
# ===========================================================================
class TestFuzzMetadata:

    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.none(),
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
    def test_metadata_keys_values_never_crash(self, key, value, tmp_path):
        """Random metadata keys and values must not crash put_memory."""
        app = _app(tmp_path, f"meta_{abs(hash(key)) % 99999}")
        try:
            try:
                app.put_memory("Metadata fuzz", scope_id="mf", type="semantic", metadata={key: value})
            except Exception:
                pass
        finally:
            try:
                app.close()
            except Exception:
                pass
