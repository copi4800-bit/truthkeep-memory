"""Mật mã Cổ điển cho TruthKeep Memory — Phase 4

Module lõi tích hợp 4 thuật toán mật mã nghìn năm:

1. Thuật toán Euclid mở rộng (300 TCN) — Sinh khóa RSA
2. Định lý Euler & Fermat (TK 17-18) — Mã hóa / Giải mã ký ức
3. Định lý Số dư Trung Hoa (TK 3) — Tăng tốc giải mã 4x
4. Định lý Bayes (1763) — Bảo mật vi sai chống gián điệp

Pure Python — KHÔNG phụ thuộc pycryptodome/cryptography.

NOTE: This module uses ``random`` instead of ``secrets`` for PRNG.
On CPython, ``random`` uses Mersenne Twister which is NOT cryptographically
secure. For production deployment on servers, swap to ``secrets.randbelow()``
and ``secrets.token_bytes()``. The current choice of ``random`` is deliberate
for embedded device compatibility (ESP32/MicroPython where ``secrets`` may not
be available). For the 512-bit key size used here, this is an acceptable
tradeoff.
"""
from __future__ import annotations

import hashlib
import math
import random
import secrets
from dataclasses import dataclass
from typing import Any, Optional

# Use cryptographically secure PRNG via secrets.SystemRandom
cryptorand = secrets.SystemRandom()


__all__ = [
    'RSAKeyBundle', 'MillerRabinPrimality', 'EuclidKeyForge',
    'EulerFermatCipher', 'ChineseRemainderAccelerator',
    'BayesianPrivacyGuard', 'compute_content_seal', 'verify_content_seal',
]


# ---------------------------------------------------------------------------
# UTILITY: Miller-Rabin Primality Test
# ---------------------------------------------------------------------------

class MillerRabinPrimality:
    """Test tính nguyên tố bằng thuật toán Miller-Rabin (xác suất).

    Xác suất sai: ≤ 4^(-k) với k witness rounds.
    k=20 → P(sai) ≤ 10^(-12) — an toàn cho mọi ứng dụng thực tế.
    """

    # Các số nguyên tố nhỏ để loại nhanh
    SMALL_PRIMES = [
        2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
        53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113,
    ]

    @classmethod
    def is_probably_prime(cls, n: int, k: int = 20) -> bool:
        """Test xem n có phải số nguyên tố không (xác suất).

        Thuật toán:
        1. Loại nhanh bằng phép chia cho primes nhỏ
        2. Viết n-1 = 2^r × d (d lẻ)
        3. Chọn a ngẫu nhiên, kiểm tra a^d mod n
        4. Lặp r-1 lần: x = x² mod n
        """
        if n < 2:
            return False
        if n in (2, 3):
            return True
        if n % 2 == 0:
            return False

        # Loại nhanh bằng primes nhỏ
        for p in cls.SMALL_PRIMES:
            if n == p:
                return True
            if n % p == 0:
                return False

        # Viết n-1 = 2^r × d
        r, d = 0, n - 1
        while d % 2 == 0:
            r += 1
            d //= 2

        # k witness rounds
        for _ in range(k):
            a = cryptorand.randrange(2, n - 1)
            x = pow(a, d, n)  # a^d mod n — Python builtin modular exp

            if x == 1 or x == n - 1:
                continue

            for _ in range(r - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False  # Composite — không nguyên tố

        return True  # Probably prime

    @classmethod
    def generate_prime(cls, bits: int) -> int:
        """Sinh số nguyên tố ngẫu nhiên có đúng `bits` bit.

        Thuật toán:
        1. Sinh random odd number có MSB=1 (đúng bit length)
        2. Test Miller-Rabin
        3. Lặp lại nếu không prime (trung bình cần ~bits/2 lần thử)
        """
        while True:
            # Sinh random number có đúng `bits` bit
            n = cryptorand.getrandbits(bits)
            n |= (1 << (bits - 1)) | 1  # Set MSB (đúng kích thước) và LSB (lẻ)

            if cls.is_probably_prime(n):
                return n


# ---------------------------------------------------------------------------
# RSA KEY BUNDLE — Bộ khóa đầy đủ
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RSAKeyBundle:
    """Bộ khóa RSA sinh bởi EuclidKeyForge.

    Chứa đầy đủ thông tin cho cả mã hóa (public) lẫn giải mã (private + CRT):
    - (n, e) = Public key — dùng cho mã hóa
    - (n, d) = Private key — dùng cho giải mã (chậm)
    - (p, q, d) = CRT components — dùng cho giải mã nhanh 4x
    """
    n: int           # Modulus: n = p × q
    e: int           # Public exponent (thường 65537)
    d: int           # Private exponent: (e × d) ≡ 1 (mod φ(n))
    p: int           # Số nguyên tố thứ 1
    q: int           # Số nguyên tố thứ 2
    bit_size: int    # Kích thước khóa (bits)

    def public_key(self) -> tuple[int, int]:
        """Trả về khóa công khai (n, e)"""
        return (self.n, self.e)

    def private_key(self) -> tuple[int, int]:
        """Trả về khóa bí mật (n, d)"""
        return (self.n, self.d)

    def to_hex_dict(self) -> dict[str, Any]:
        """Serialize thành hex strings cho lưu trữ."""
        return {
            "n_hex": hex(self.n),
            "e": self.e,
            "d_hex": hex(self.d),
            "p_hex": hex(self.p),
            "q_hex": hex(self.q),
            "bit_size": self.bit_size,
        }

    @classmethod
    def from_hex_dict(cls, data: dict[str, Any]) -> RSAKeyBundle:
        """Deserialize từ hex strings."""
        return cls(
            n=int(data["n_hex"], 16),
            e=int(data["e"]),
            d=int(data["d_hex"], 16),
            p=int(data["p_hex"], 16),
            q=int(data["q_hex"], 16),
            bit_size=int(data["bit_size"]),
        )


# ---------------------------------------------------------------------------
# 1. THUẬT TOÁN EUCLID MỞ RỘNG (300 TCN) — Lò Rèn Khóa
# ---------------------------------------------------------------------------

class EuclidKeyForge:
    """Thuật toán Euclid mở rộng (300 TCN) — Lò rèn khóa bảo mật.

    Euclid tìm GCD (ước số chung lớn nhất). Mở rộng thành Extended GCD
    để tìm nghịch đảo mô-đun — bước BẮT BUỘC để sinh khóa giải mã RSA.

    Ví dụ:
        (17 × d) ≡ 1 (mod 120)
        → extended_gcd(17, 120) → gcd=1, x=53, y=-7
        → d = 53 (vì 17 × 53 = 901 = 7×120 + 1)
    """

    @staticmethod
    def extended_gcd(a: int, b: int) -> tuple[int, int, int]:
        """Thuật toán Euclid mở rộng — tìm gcd, x, y sao cho a×x + b×y = gcd(a,b).

        Đệ quy:
        - Base: gcd(0, b) = b, x=0, y=1
        - Step: gcd(b%a, a) → back-substitute x, y

        Returns: (gcd, x, y)
        """
        if a == 0:
            return b, 0, 1

        gcd, x1, y1 = EuclidKeyForge.extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y

    @staticmethod
    def mod_inverse(e: int, phi_n: int) -> int:
        """Tìm nghịch đảo mô-đun: d sao cho (e × d) ≡ 1 (mod φ(n)).

        Đây là bước Euclid dùng để sinh khóa giải mã RSA.
        Nếu gcd(e, φ(n)) ≠ 1, không tồn tại nghịch đảo.

        Args:
            e: Số mũ công khai (public exponent)
            phi_n: Giá trị Euler φ(n) = (p-1)(q-1)

        Returns:
            d: Khóa giải mã bí mật
        """
        gcd, x, _ = EuclidKeyForge.extended_gcd(e, phi_n)
        if gcd != 1:
            raise ValueError(
                f"Nghịch đảo mô-đun không tồn tại: gcd({e}, {phi_n}) = {gcd} ≠ 1"
            )
        return x % phi_n

    @staticmethod
    def generate_rsa_params(bit_size: int = 512) -> RSAKeyBundle:
        """Sinh bộ khóa RSA hoàn chỉnh.

        Thuật toán:
        1. Sinh 2 số nguyên tố p, q bằng Miller-Rabin
        2. Tính n = p × q (modulus)
        3. Tính φ(n) = (p-1)(q-1) (hàm Euler)
        4. Chọn e = 65537 (chuẩn công nghiệp)
        5. Tính d = mod_inverse(e, φ(n)) bằng Euclid mở rộng

        Args:
            bit_size: Kích thước khóa (bits). 512 cho embedded, 2048+ cho production.

        Returns:
            RSAKeyBundle chứa đầy đủ thông tin khóa.
        """
        half = bit_size // 2

        while True:
            p = MillerRabinPrimality.generate_prime(half)
            q = MillerRabinPrimality.generate_prime(half)

            if p == q:
                continue  # p và q phải khác nhau

            n = p * q
            phi_n = (p - 1) * (q - 1)

            # Chọn e: ưu tiên 65537 (chuẩn), fallback sang primes nhỏ hơn
            e = 65537
            if math.gcd(e, phi_n) != 1:
                for candidate in [257, 17, 13, 7, 5, 3]:
                    if math.gcd(candidate, phi_n) == 1:
                        e = candidate
                        break
                else:
                    continue  # Rất hiếm — thử lại

            # Euclid mở rộng tìm khóa giải mã d
            d = EuclidKeyForge.mod_inverse(e, phi_n)

            # Kiểm tra: (e × d) mod φ(n) phải = 1
            assert (e * d) % phi_n == 1, "Euclid verification failed"

            return RSAKeyBundle(n=n, e=e, d=d, p=p, q=q, bit_size=bit_size)


# ---------------------------------------------------------------------------
# 2. ĐỊNH LÝ EULER & FERMAT (TK 17-18) — Ổ Khóa Mật Mã
# ---------------------------------------------------------------------------

class EulerFermatCipher:
    """Định lý Euler & Fermat — Ổ khóa toán học cho ký ức AI.

    Mã hóa: C = M^e mod n  (Euler's theorem đảm bảo khả nghịch)
    Giải mã: M = C^d mod n  (Fermat's little theorem chứng minh đúng đắn)

    Ví dụ với p=3, q=11, n=33, e=3, d=7:
        Khóa: encrypt(7, 3, 33) = 7³ mod 33 = 343 mod 33 = 13
        Mở:   decrypt(13, 7, 33) = 13⁷ mod 33 = 62748517 mod 33 = 7 ✓
    """

    @staticmethod
    def encrypt_int(m: int, e: int, n: int) -> int:
        """Mã hóa số nguyên: C = M^e mod n.

        Sử dụng Python builtin pow(m, e, n) — hiệu quả O(log e) nhờ
        square-and-multiply algorithm.
        """
        if m < 0 or m >= n:
            raise ValueError(f"Plaintext {m} ngoài phạm vi [0, {n})")
        return pow(m, e, n)

    @staticmethod
    def decrypt_int(c: int, d: int, n: int) -> int:
        """Giải mã số nguyên: M = C^d mod n (đường chậm — không dùng CRT)."""
        return pow(c, d, n)

    @staticmethod
    def encrypt_bytes(data: bytes, e: int, n: int) -> str:
        """Mã hóa dữ liệu bytes thành chuỗi hex.

        Thuật toán:
        1. Chia data thành blocks (mỗi block < n)
        2. Chuyển block → integer
        3. Euler cipher: C = M^e mod n
        4. Chuyển C → hex, nối bằng ':'

        Format output: "original_length:hex_block_1:hex_block_2:..."
        """
        block_size = (n.bit_length() - 1) // 8  # Max bytes/block
        if block_size < 1:
            raise ValueError("Khóa quá nhỏ để mã hóa")

        cipher_size = (n.bit_length() + 7) // 8  # Bytes/cipher block

        chunks: list[str] = []
        for i in range(0, len(data), block_size):
            block = data[i : i + block_size]
            # Pad block lên full block_size (data ở trái, zeros ở phải)
            # để decrypt khôi phục đúng khi ghép các blocks liên tiếp
            padded = block.ljust(block_size, b"\x00")
            m = int.from_bytes(padded, "big")
            c = pow(m, e, n)
            chunks.append(c.to_bytes(cipher_size, "big").hex())

        # Prepend original length cho giải mã chính xác
        return f"{len(data)}:" + ":".join(chunks)

    @staticmethod
    def decrypt_bytes(
        cipher_hex: str,
        d: int,
        n: int,
        p: int | None = None,
        q: int | None = None,
    ) -> bytes:
        """Giải mã chuỗi hex thành bytes.

        Nếu p, q được cung cấp → dùng CRT fast path (4x nhanh hơn).
        """
        parts = cipher_hex.split(":")
        original_length = int(parts[0])
        chunks = parts[1:]

        block_size = (n.bit_length() - 1) // 8
        result = bytearray()

        for chunk_hex in chunks:
            c = int.from_bytes(bytes.fromhex(chunk_hex), "big")

            # CRT fast path nếu có p, q
            if p is not None and q is not None:
                m = ChineseRemainderAccelerator.crt_decrypt(c, d, p, q)
            else:
                m = pow(c, d, n)

            # Pad block to block_size (giữ leading zeros)
            m_bytes = m.to_bytes(block_size, "big")
            result.extend(m_bytes)

        return bytes(result[:original_length])


# ---------------------------------------------------------------------------
# 3. ĐỊNH LÝ SỐ DƯ TRUNG HOA (TK 3) — Tăng Tốc Giải Mã 4x
# ---------------------------------------------------------------------------

class ChineseRemainderAccelerator:
    """Định lý Số dư Trung Hoa (Tôn Tử, TK 3) — Tăng tốc giải mã.

    Thay vì tính C^d mod n trực tiếp (rất chậm khi n lớn):
    1. Tính M₁ = C^(d mod p-1) mod p     ← nhỏ hơn nhiều
    2. Tính M₂ = C^(d mod q-1) mod q     ← nhỏ hơn nhiều
    3. Gộp M₁, M₂ → M bằng Garner's algorithm

    Tốc độ: ~4x nhanh hơn (vì phép mũ trên p, q nhỏ hơn n một nửa bit).

    Ví dụ: C=13, d=7, p=3, q=11, n=33
        M₁ = 13^(7 mod 2) mod 3 = 13^1 mod 3 = 1
        M₂ = 13^(7 mod 10) mod 11 = 13^7 mod 11 = 7
        Garner: q_inv = mod_inverse(11, 3) = 2
                h = (2 × (1 - 7)) mod 3 = (2 × (-6)) mod 3 = 0
                M = 7 + 0 × 11 = 7 ✓
    """

    @staticmethod
    def crt_decrypt(c: int, d: int, p: int, q: int) -> int:
        """Giải mã CRT fast path — 4x nhanh hơn direct decrypt.

        Thuật toán:
        1. dp = d mod (p-1), dq = d mod (q-1)
        2. M₁ = C^dp mod p, M₂ = C^dq mod q
        3. Garner combine: M = M₂ + ((M₁ - M₂) × q_inv mod p) × q
        """
        dp = d % (p - 1)
        dq = d % (q - 1)
        q_inv = EuclidKeyForge.mod_inverse(q, p)

        m1 = pow(c, dp, p)
        m2 = pow(c, dq, q)

        # Garner's formula
        h = (q_inv * (m1 - m2)) % p
        m = m2 + h * q

        return m

    @staticmethod
    def garner_combine(m_p: int, m_q: int, p: int, q: int) -> int:
        """Garner's algorithm — Gộp 2 phần dư thành giá trị gốc.

        Cho hệ: x ≡ m_p (mod p), x ≡ m_q (mod q)
        Nghiệm duy nhất: x = m_q + ((m_p - m_q) × q_inv mod p) × q
        """
        q_inv = EuclidKeyForge.mod_inverse(q, p)
        h = (q_inv * (m_p - m_q)) % p
        return m_q + h * q

    @staticmethod
    def general_crt(residues: list[int], moduli: list[int]) -> int:
        """CRT tổng quát cho hệ nhiều phương trình.

        Cho: x ≡ r₁ (mod m₁), x ≡ r₂ (mod m₂), ...
        Tìm x duy nhất (mod M = m₁ × m₂ × ...)

        Áp dụng: phân tán ký ức vào nhiều node, mỗi node giữ 1 phần dư.
        """
        if len(residues) != len(moduli):
            raise ValueError("Số phần dư và moduli phải bằng nhau")

        M = 1
        for m in moduli:
            M *= m

        x = 0
        for ri, mi in zip(residues, moduli):
            Mi = M // mi
            yi = EuclidKeyForge.mod_inverse(Mi, mi)
            x += ri * Mi * yi

        return x % M


# ---------------------------------------------------------------------------
# 4. ĐỊNH LÝ BAYES (1763) — Lá Chắn Chống Gián Điệp
# ---------------------------------------------------------------------------

class BayesianPrivacyGuard:
    """Định lý Bayes (Thomas Bayes, 1763) — Bảo mật vi sai.

    P(leak | response) = P(response | leak) × P(leak) / P(response)

    Kẻ tấn công không cần bẻ khóa — chỉ cần hỏi AI hàng nghìn câu
    quanh co để xem AI có "lỡ miệng" lặp lại ký ức nhạy cảm không
    (Membership Inference Attack).

    Lá chắn này:
    1. Tính P(leak | response) bằng Bayes
    2. Nếu risk > ε → bơm nhiễu Laplace vào score
    3. Track query patterns để phát hiện probing
    """

    EXPOSURE_DENOMINATOR = 10.0
    EPSILON_FLOOR = 1e-15
    MAX_NOISE_CLAMP = 0.4999999
    BASE_LEAK_GIVEN_NO_LEAK = 0.1
    PATTERN_LEAK_FACTOR = 0.3
    DEFAULT_RISK_THRESHOLD = 0.7

    @classmethod
    def compute_leakage_risk(
        cls,
        query_similarity: float,
        prior_exposure: float,
        response_confidence: float,
    ) -> float:
        """Tính xác suất rò rỉ dữ liệu bằng Bayes.

        P(leak | response) = P(response | leak) × P(leak) / P(response)

        Args:
            query_similarity: Cosine similarity giữa query và memory (0-1)
            prior_exposure: Số lần memory đã bị truy cập
            response_confidence: Confidence score của response (0-1)

        Returns:
            Posterior probability of data leakage (0-1)
        """
        # P(leak) = prior dựa trên exposure history
        # Nhiều lần truy cập = xác suất rò rỉ cao hơn
        p_leak = min(0.95, prior_exposure / (prior_exposure + cls.EXPOSURE_DENOMINATOR))

        # P(response | leak): nếu dữ liệu bị rò, response sẽ rất giống memory
        p_response_given_leak = max(0.01, query_similarity * response_confidence)

        # P(response | ¬leak): xác suất response ngẫu nhiên (không rò)
        p_response_given_no_leak = cls.BASE_LEAK_GIVEN_NO_LEAK + (1.0 - query_similarity) * cls.PATTERN_LEAK_FACTOR

        # P(response) = tổng xác suất (Total probability theorem)
        p_response = (
            p_response_given_leak * p_leak
            + p_response_given_no_leak * (1.0 - p_leak)
        )

        if p_response < cls.EPSILON_FLOOR:
            return 0.0

        # Bayes' Theorem: P(leak | response)
        posterior = (p_response_given_leak * p_leak) / p_response
        return min(1.0, max(0.0, round(posterior, 8)))

    @classmethod
    def apply_laplace_noise(
        cls,
        value: float,
        epsilon: float,
        sensitivity: float,
    ) -> float:
        """Bơm nhiễu Laplace vào giá trị — cơ chế Differential Privacy.

        Nhiễu Laplace: noise ~ Lap(0, sensitivity/ε)
        - ε nhỏ = nhiều nhiễu = bảo mật hơn (nhưng kết quả kém chính xác)
        - ε lớn = ít nhiễu = chính xác hơn (nhưng ít bảo mật)

        Apple dùng ε=2-8, Google dùng ε=1-3.

        Args:
            value: Giá trị gốc cần bảo vệ
            epsilon: Privacy budget (thấp = bảo mật hơn)
            sensitivity: Max thay đổi khi thêm/bỏ 1 record
        """
        scale = sensitivity / max(epsilon, cls.EPSILON_FLOOR)

        # Sinh biến ngẫu nhiên Laplace: Lap(0, scale)
        # Phương pháp: inverse CDF transform
        u = cryptorand.random() - 0.5
        # Clamp để tránh log(0)
        u = max(-cls.MAX_NOISE_CLAMP, min(cls.MAX_NOISE_CLAMP, u))
        noise = -scale * math.copysign(1.0, u) * math.log(1.0 - 2.0 * abs(u))

        return value + noise

    @classmethod
    def should_suppress(cls, leakage_risk: float, threshold: float | None = None) -> bool:
        """Quyết định có nên suppress/redact response không.

        Nếu P(leak | response) > threshold → SUPPRESS để bảo vệ người dùng.
        """
        if threshold is None:
            threshold = cls.DEFAULT_RISK_THRESHOLD
        return leakage_risk > threshold

    @classmethod
    def sequential_leakage_update(
        cls,
        prior_risk: float,
        observations: list[tuple[float, float]],
    ) -> float:
        """Cập nhật tuần tự P(leak) qua nhiều query — sequential Bayesian update.

        Mỗi observation là (query_similarity, response_confidence).
        Sau mỗi query, posterior trở thành prior cho query tiếp theo.

        Phát hiện probing attack: nếu ai đó hỏi nhiều câu giống nhau,
        cumulative risk sẽ tăng dần.
        """
        risk = prior_risk
        for sim, conf in observations:
            p_obs_given_leak = max(0.01, sim * conf)
            p_obs_given_safe = cls.BASE_LEAK_GIVEN_NO_LEAK + (1.0 - sim) * cls.PATTERN_LEAK_FACTOR

            p_obs = p_obs_given_leak * risk + p_obs_given_safe * (1.0 - risk)
            if p_obs < cls.EPSILON_FLOOR:
                continue

            risk = (p_obs_given_leak * risk) / p_obs
            risk = min(0.999, max(0.001, risk))

        return round(risk, 8)


# ---------------------------------------------------------------------------
# 5. TIỆN ÍCH MÃ HÓA
# ---------------------------------------------------------------------------

def compute_content_seal(content: str) -> str:
    """Tính SHA-256 seal cho nội dung — integrity proof.

    Nếu ai can thiệp content trong DB, seal sẽ không khớp.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def verify_content_seal(content: str, seal: str) -> bool:
    """Xác minh content chưa bị can thiệp bằng SHA-256 seal."""
    return compute_content_seal(content) == seal
