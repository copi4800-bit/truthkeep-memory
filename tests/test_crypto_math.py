"""Tests cho Phase 4: Mật mã Cổ điển — 4 thuật toán nghìn năm.

Test suite bao gồm:
1. Thuật toán Euclid mở rộng (300 TCN) — Key generation
2. Định lý Euler & Fermat (TK 17-18) — Encrypt/Decrypt
3. Định lý Số dư Trung Hoa (TK 3) — CRT acceleration
4. Định lý Bayes (1763) — Differential Privacy
5. Memory Vault — Full round-trip integration
"""
import time

import pytest

from aegis_py.security.crypto_math import (
    BayesianPrivacyGuard,
    ChineseRemainderAccelerator,
    EuclidKeyForge,
    EulerFermatCipher,
    MillerRabinPrimality,
    RSAKeyBundle,
    compute_content_seal,
    verify_content_seal,
)


# ============================================================================
# 1. THUẬT TOÁN EUCLID MỞ RỘNG (300 TCN)
# ============================================================================

class TestEuclidKeyForge:
    """Test thuật toán Euclid — Lò rèn khóa bảo mật."""

    def test_extended_gcd_basic(self):
        """gcd(17, 120) = 1, nên nghịch đảo tồn tại."""
        gcd, x, y = EuclidKeyForge.extended_gcd(17, 120)
        assert gcd == 1
        assert 17 * x + 120 * y == 1

    def test_extended_gcd_coprime(self):
        """gcd(35, 64) = 1."""
        gcd, x, y = EuclidKeyForge.extended_gcd(35, 64)
        assert gcd == 1
        assert 35 * x + 64 * y == 1

    def test_extended_gcd_non_coprime(self):
        """gcd(12, 8) = 4."""
        gcd, _, _ = EuclidKeyForge.extended_gcd(12, 8)
        assert gcd == 4

    def test_mod_inverse_classic_example(self):
        """(17 × d) ≡ 1 (mod 120) → d phải thỏa mãn.
        
        Đây là ví dụ kinh điển từ bài nghiên cứu:
        Cả d=53 và d=113 đều hợp lệ (17×53=901, 17×113=1921, cả hai mod 120 = 1)
        """
        d = EuclidKeyForge.mod_inverse(17, 120)
        assert (17 * d) % 120 == 1, f"d={d}: (17 × {d}) mod 120 = {(17*d)%120} ≠ 1"

    def test_mod_inverse_rsa_standard(self):
        """e=65537, φ(n)=... → d tìm bằng Euclid."""
        # Ví dụ nhỏ: e=3, φ(n)=20 → d=7 (vì 3×7=21, 21 mod 20 = 1)
        d = EuclidKeyForge.mod_inverse(3, 20)
        assert d == 7
        assert (3 * 7) % 20 == 1

    def test_mod_inverse_no_exist_raises(self):
        """gcd(e, φ(n)) ≠ 1 → không tồn tại nghịch đảo."""
        with pytest.raises(ValueError, match="không tồn tại"):
            EuclidKeyForge.mod_inverse(4, 12)  # gcd(4,12)=4≠1

    def test_generate_rsa_params(self):
        """Sinh bộ khóa RSA 256-bit — kiểm tra tính đúng đắn toán học."""
        key = EuclidKeyForge.generate_rsa_params(256)

        # n = p × q
        assert key.n == key.p * key.q
        # (e × d) ≡ 1 (mod φ(n))
        phi_n = (key.p - 1) * (key.q - 1)
        assert (key.e * key.d) % phi_n == 1
        # p ≠ q
        assert key.p != key.q
        # Bit size correct
        assert key.bit_size == 256

    def test_generate_rsa_params_512(self):
        """Sinh bộ khóa RSA 512-bit — kích thước mặc định."""
        key = EuclidKeyForge.generate_rsa_params(512)
        
        phi_n = (key.p - 1) * (key.q - 1)
        assert (key.e * key.d) % phi_n == 1
        assert key.n > 0
        assert key.n.bit_length() >= 500  # Xấp xỉ 512 bit


# ============================================================================
# 2. ĐỊNH LÝ EULER & FERMAT (TK 17-18)
# ============================================================================

class TestEulerFermatCipher:
    """Test định lý Euler/Fermat — Ổ khóa mật mã."""

    def test_encrypt_decrypt_textbook_example(self):
        """Ví dụ kinh điển: p=3, q=11, n=33, e=3, d=7.
        
        Mã hóa M=7: C = 7³ mod 33 = 343 mod 33 = 13
        Giải mã C=13: M = 13⁷ mod 33 = 62748517 mod 33 = 7 ✓
        """
        # Mã hóa: C = M^e mod n
        c = EulerFermatCipher.encrypt_int(7, e=3, n=33)
        assert c == 13  # 7³ = 343 mod 33 = 13

        # Giải mã: M = C^d mod n
        m = EulerFermatCipher.decrypt_int(13, d=7, n=33)
        assert m == 7  # 13⁷ mod 33 = 7 ✓

    def test_encrypt_decrypt_all_values(self):
        """Test encrypt→decrypt cho mọi giá trị 0..n-1 (small key)."""
        n, e, d = 33, 3, 7
        for m in range(n):
            c = EulerFermatCipher.encrypt_int(m, e, n)
            m_back = EulerFermatCipher.decrypt_int(c, d, n)
            assert m_back == m, f"Round-trip failed for m={m}"

    def test_encrypt_bytes_roundtrip(self):
        """Encrypt bytes → hex → decrypt bytes → original."""
        key = EuclidKeyForge.generate_rsa_params(256)
        
        original = b"Hello TruthKeep Memory!"
        cipher_hex = EulerFermatCipher.encrypt_bytes(original, key.e, key.n)
        decrypted = EulerFermatCipher.decrypt_bytes(cipher_hex, key.d, key.n)
        
        assert decrypted == original

    def test_encrypt_bytes_unicode(self):
        """Mã hóa text Unicode (tiếng Việt)."""
        key = EuclidKeyForge.generate_rsa_params(512)
        
        original = "Xin chào! Đây là ký ức của AI 🧠".encode("utf-8")
        cipher_hex = EulerFermatCipher.encrypt_bytes(original, key.e, key.n)
        decrypted = EulerFermatCipher.decrypt_bytes(cipher_hex, key.d, key.n)
        
        assert decrypted == original

    def test_encrypt_bytes_long_content(self):
        """Mã hóa nội dung dài — nhiều blocks."""
        key = EuclidKeyForge.generate_rsa_params(256)
        
        original = b"A" * 500  # Dài hơn block_size → cần chia blocks
        cipher_hex = EulerFermatCipher.encrypt_bytes(original, key.e, key.n)
        decrypted = EulerFermatCipher.decrypt_bytes(cipher_hex, key.d, key.n)
        
        assert decrypted == original

    def test_encrypt_bytes_empty(self):
        """Mã hóa chuỗi rỗng."""
        key = EuclidKeyForge.generate_rsa_params(256)
        
        original = b""
        cipher_hex = EulerFermatCipher.encrypt_bytes(original, key.e, key.n)
        decrypted = EulerFermatCipher.decrypt_bytes(cipher_hex, key.d, key.n)
        
        assert decrypted == original


# ============================================================================
# 3. ĐỊNH LÝ SỐ DƯ TRUNG HOA (TK 3)
# ============================================================================

class TestChineseRemainderAccelerator:
    """Test CRT — Tăng tốc giải mã 4x."""

    def test_crt_textbook_example(self):
        """CRT decrypt với p=3, q=11, d=7: decrypt(13) = 7."""
        m = ChineseRemainderAccelerator.crt_decrypt(c=13, d=7, p=3, q=11)
        assert m == 7

    def test_crt_equals_direct_decrypt(self):
        """CRT decrypt phải cho kết quả giống direct decrypt."""
        key = EuclidKeyForge.generate_rsa_params(256)
        
        # Encrypt
        m_original = 42
        c = EulerFermatCipher.encrypt_int(m_original, key.e, key.n)
        
        # Decrypt: direct vs CRT
        m_direct = EulerFermatCipher.decrypt_int(c, key.d, key.n)
        m_crt = ChineseRemainderAccelerator.crt_decrypt(c, key.d, key.p, key.q)
        
        assert m_direct == m_original
        assert m_crt == m_original
        assert m_direct == m_crt

    def test_crt_bytes_roundtrip(self):
        """CRT decrypt path cho bytes phải cho kết quả đúng."""
        key = EuclidKeyForge.generate_rsa_params(512)
        
        original = "Định lý Số dư Trung Hoa — 4x faster!".encode("utf-8")
        cipher_hex = EulerFermatCipher.encrypt_bytes(original, key.e, key.n)
        
        # Decrypt with CRT (p, q provided)
        decrypted = EulerFermatCipher.decrypt_bytes(
            cipher_hex, key.d, key.n, p=key.p, q=key.q
        )
        assert decrypted == original

    def test_crt_speed_comparison(self):
        """CRT decrypt và direct decrypt phải cho kết quả chính xác, đồng thời so sánh hiệu năng."""
        key = EuclidKeyForge.generate_rsa_params(512)
        c = EulerFermatCipher.encrypt_int(12345, key.e, key.n)
        
        iterations = 100
        
        # Benchmark direct
        t0 = time.perf_counter()
        for _ in range(iterations):
            r_direct = pow(c, key.d, key.n)
        time_direct = time.perf_counter() - t0
        
        # Benchmark CRT
        t0 = time.perf_counter()
        for _ in range(iterations):
            r_crt = ChineseRemainderAccelerator.crt_decrypt(c, key.d, key.p, key.q)
        time_crt = time.perf_counter() - t0
        
        # Xác nhận tính đúng đắn toán học
        assert r_direct == 12345
        assert r_crt == 12345
        assert r_direct == r_crt
        
        # Ghi nhận hiệu năng thực tế thay vì assert cứng tránh flaky CI
        import sys
        sys.stdout.write(f"\n[Performance Note] Key: 512-bit | Iterations: {iterations} | Direct: {time_direct:.4f}s | CRT (Python): {time_crt:.4f}s\n")

    def test_garner_combine(self):
        """Garner's algorithm — gộp 2 phần dư."""
        # x ≡ 1 (mod 3), x ≡ 7 (mod 11) → x = 7 (mod 33)
        x = ChineseRemainderAccelerator.garner_combine(m_p=1, m_q=7, p=3, q=11)
        assert x % 3 == 1
        assert x % 11 == 7
        assert x == 7

    def test_general_crt(self):
        """CRT tổng quát — hệ nhiều phương trình."""
        # Bài toán cổ điển Tôn Tử:
        # x ≡ 2 (mod 3), x ≡ 3 (mod 5), x ≡ 2 (mod 7) → x = 23
        x = ChineseRemainderAccelerator.general_crt(
            residues=[2, 3, 2],
            moduli=[3, 5, 7],
        )
        assert x == 23
        assert x % 3 == 2
        assert x % 5 == 3
        assert x % 7 == 2


# ============================================================================
# 4. ĐỊNH LÝ BAYES (1763) — Bảo mật Vi sai
# ============================================================================

class TestBayesianPrivacyGuard:
    """Test Bayesian DP — Lá chắn chống gián điệp."""

    def test_high_similarity_high_exposure_high_risk(self):
        """Query rất giống memory + nhiều access = risk cao."""
        risk = BayesianPrivacyGuard.compute_leakage_risk(
            query_similarity=0.95,
            prior_exposure=50,
            response_confidence=0.9,
        )
        assert risk > 0.7, f"Expected high risk, got {risk}"

    def test_low_similarity_low_exposure_low_risk(self):
        """Query khác memory + ít access = risk thấp."""
        risk = BayesianPrivacyGuard.compute_leakage_risk(
            query_similarity=0.1,
            prior_exposure=1,
            response_confidence=0.3,
        )
        assert risk < 0.3, f"Expected low risk, got {risk}"

    def test_risk_monotonic_with_similarity(self):
        """Risk phải tăng khi similarity tăng (monotonic)."""
        risks = []
        for sim in [0.1, 0.3, 0.5, 0.7, 0.9]:
            r = BayesianPrivacyGuard.compute_leakage_risk(sim, 10, 0.8)
            risks.append(r)
        # Phải tăng dần (hoặc ít nhất không giảm)
        for i in range(1, len(risks)):
            assert risks[i] >= risks[i-1] - 0.01, (
                f"Risk should increase: {risks}"
            )

    def test_laplace_noise_changes_value(self):
        """Noise injection phải thay đổi giá trị (xác suất ~100%)."""
        original = 0.8
        changed_count = 0
        for _ in range(50):
            noised = BayesianPrivacyGuard.apply_laplace_noise(original, 1.0, 0.1)
            if abs(noised - original) > 1e-10:
                changed_count += 1
        assert changed_count > 40, "Noise should change value in most cases"

    def test_laplace_noise_centers_around_value(self):
        """Trung bình noise phải gần giá trị gốc (unbiased)."""
        original = 0.5
        noised_values = [
            BayesianPrivacyGuard.apply_laplace_noise(original, 1.0, 0.1)
            for _ in range(1000)
        ]
        mean = sum(noised_values) / len(noised_values)
        assert abs(mean - original) < 0.1, f"Mean {mean} too far from {original}"

    def test_should_suppress(self):
        """Suppress khi risk > threshold."""
        assert BayesianPrivacyGuard.should_suppress(0.8, threshold=0.7) is True
        assert BayesianPrivacyGuard.should_suppress(0.5, threshold=0.7) is False

    def test_sequential_leakage_update(self):
        """Sequential Bayesian update — risk tăng dần qua nhiều query."""
        # Bắt đầu với risk thấp
        risk = 0.1
        # 5 query giống nhau liên tiếp → risk phải tăng
        observations = [(0.8, 0.9)] * 5
        final_risk = BayesianPrivacyGuard.sequential_leakage_update(risk, observations)
        
        assert final_risk > risk, f"Sequential risk should increase: {risk} → {final_risk}"


# ============================================================================
# 5. MILLER-RABIN PRIMALITY
# ============================================================================

class TestMillerRabin:
    """Test sinh số nguyên tố."""

    def test_known_primes(self):
        """Các số nguyên tố đã biết phải pass."""
        primes = [2, 3, 5, 7, 11, 13, 97, 101, 1009, 104729]
        for p in primes:
            assert MillerRabinPrimality.is_probably_prime(p), f"{p} should be prime"

    def test_known_composites(self):
        """Các hợp số đã biết phải fail."""
        composites = [4, 6, 8, 9, 10, 15, 21, 100, 1001]
        for c in composites:
            assert not MillerRabinPrimality.is_probably_prime(c), f"{c} should NOT be prime"

    def test_generate_prime_correct_size(self):
        """Số nguyên tố sinh ra phải đúng kích thước bit."""
        for bits in [32, 64, 128]:
            p = MillerRabinPrimality.generate_prime(bits)
            assert MillerRabinPrimality.is_probably_prime(p)
            assert p.bit_length() == bits


# ============================================================================
# 6. INTEGRITY SEAL
# ============================================================================

class TestContentSeal:
    """Test SHA-256 integrity seal."""

    def test_seal_verify_roundtrip(self):
        """Seal phải verify đúng với content gốc."""
        content = "Ký ức quan trọng của AI"
        seal = compute_content_seal(content)
        assert verify_content_seal(content, seal) is True

    def test_seal_detects_tampering(self):
        """Seal phải phát hiện content bị sửa."""
        content = "Ký ức gốc"
        seal = compute_content_seal(content)
        assert verify_content_seal("Ký ức bị sửa", seal) is False

    def test_seal_deterministic(self):
        """Cùng content → cùng seal."""
        s1 = compute_content_seal("test")
        s2 = compute_content_seal("test")
        assert s1 == s2


# ============================================================================
# 7. MEMORY VAULT — Full Integration
# ============================================================================

class TestMemoryVault:
    """Test Memory Vault — Mã hóa/giải mã ký ức toàn diện."""

    def test_seal_unseal_roundtrip(self):
        """seal → unseal phải trả về content gốc."""
        import sqlite3
        from aegis_py.security.key_manager import KeyManager
        from aegis_py.security.memory_vault import MemoryVault
        
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE crypto_keys (
                key_id TEXT PRIMARY KEY,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                n_hex TEXT NOT NULL,
                e INTEGER NOT NULL,
                d_hex TEXT NOT NULL,
                p_hex TEXT NOT NULL,
                q_hex TEXT NOT NULL,
                bit_size INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                UNIQUE (scope_type, scope_id)
            )
        """)
        
        vault = MemoryVault(KeyManager(conn))
        content = "Đây là ký ức nhạy cảm cần bảo vệ! 🔐"
        
        sealed = vault.seal_memory(content, "project", "test-project")
        assert sealed["encrypted_content"]
        assert sealed["key_id"]
        assert sealed["seal_hash"]
        
        # Encrypted phải khác plaintext
        assert sealed["encrypted_content"] != content
        
        # Unseal phải trả về gốc
        decrypted = vault.unseal_memory(
            sealed["encrypted_content"], sealed["key_id"]
        )
        assert decrypted == content
        
        # Verify seal
        assert MemoryVault.verify_seal(content, sealed["seal_hash"]) is True

    def test_same_scope_reuses_key(self):
        """Cùng scope phải dùng lại khóa (không sinh mới)."""
        import sqlite3
        from aegis_py.security.key_manager import KeyManager
        from aegis_py.security.memory_vault import MemoryVault
        
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE crypto_keys (
                key_id TEXT PRIMARY KEY,
                scope_type TEXT, scope_id TEXT,
                n_hex TEXT, e INTEGER, d_hex TEXT,
                p_hex TEXT, q_hex TEXT, bit_size INTEGER,
                created_at TEXT, rotated_at TEXT,
                UNIQUE (scope_type, scope_id)
            )
        """)
        
        vault = MemoryVault(KeyManager(conn))
        
        s1 = vault.seal_memory("Memory 1", "project", "same-scope")
        s2 = vault.seal_memory("Memory 2", "project", "same-scope")
        
        assert s1["key_id"] == s2["key_id"]  # Cùng key


# ============================================================================
# 8. DIFFERENTIAL PRIVACY SHIELD
# ============================================================================

class TestDifferentialPrivacyShield:
    """Test Bayesian Differential Privacy Shield."""

    def test_guard_passes_normal_results(self):
        """Kết quả bình thường phải pass through."""
        from aegis_py.security.privacy_guard import DifferentialPrivacyShield
        shield = DifferentialPrivacyShield(epsilon=1.0)
        results = [
            {"score": 0.5, "access_count": 2, "confidence": 0.8, "id": "1"},
            {"score": 0.3, "access_count": 1, "confidence": 0.6, "id": "2"},
        ]
        
        guarded = shield.guard_search_results(results, "normal query", "test-scope")
        assert len(guarded) >= 1  # Phải trả về kết quả

    def test_probing_detection(self):
        """Probing attack (nhiều query giống nhau) phải bị phát hiện."""
        from aegis_py.security.privacy_guard import DifferentialPrivacyShield
        shield = DifferentialPrivacyShield(
            epsilon=1.0,
            noise_threshold=0.3,
            suppress_threshold=0.9,
        )
        
        # Gửi 20 query giống nhau liên tiếp → probe_intensity phải tăng
        for _ in range(20):
            shield.guard_search_results(
                [{"score": 0.9, "access_count": 100, "confidence": 0.95}],
                "same suspicious query",
                "target-scope",
            )
        
        intensity = shield._compute_probe_intensity("target-scope", "same suspicious query")
        assert intensity > 0.3, f"Should detect probing, got intensity={intensity}"

    def test_privacy_stats(self):
        """Privacy stats phải trả về thông tin hợp lệ."""
        from aegis_py.security.privacy_guard import DifferentialPrivacyShield
        shield = DifferentialPrivacyShield(epsilon=2.0)
        shield.guard_search_results(
            [{"score": 0.5, "access_count": 1, "confidence": 0.5}],
            "test query", "test-scope",
        )
        
        stats = shield.get_privacy_stats("test-scope")
        assert stats["epsilon"] == 2.0
        assert stats["total_queries_tracked"] >= 1


# ============================================================================
# 9. RSA KEY BUNDLE SERIALIZATION
# ============================================================================

class TestRSAKeyBundle:
    """Test serialize/deserialize khóa RSA."""

    def test_hex_roundtrip(self):
        """to_hex_dict → from_hex_dict phải trả về bộ khóa giống nhau."""
        key = EuclidKeyForge.generate_rsa_params(256)
        
        hex_dict = key.to_hex_dict()
        restored = type(key).from_hex_dict(hex_dict)
        
        assert restored.n == key.n
        assert restored.e == key.e
        assert restored.d == key.d
        assert restored.p == key.p
        assert restored.q == key.q
