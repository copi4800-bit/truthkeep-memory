"""Bảo mật Vi sai — Chống Membership Inference Attack.

Sử dụng Định lý Bayes (1763) để phát hiện và ngăn chặn
kẻ tấn công hỏi AI quanh co để rò rỉ ký ức nhạy cảm.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from .crypto_math import BayesianPrivacyGuard

__all__ = [
    'DifferentialPrivacyShield',
    'MetricDPGaussianNoise',
    'PaillierPartiallyHomomorphicEngine',
    'ShannonEntropyPoisonDetector'
]


class DifferentialPrivacyShield:
    """Lá chắn Bảo mật Vi sai — Bayesian Differential Privacy.

    Workflow:
    1. Track mọi query theo scope
    2. Tính probe_intensity: tần suất query giống nhau (phát hiện tấn công)
    3. Tính leakage_risk bằng Bayes cho mỗi kết quả
    4. Nếu risk > threshold → bơm nhiễu Laplace vào score
    5. Nếu risk > suppress_threshold → suppress kết quả hoàn toàn
    """

    MAX_SIMILAR_THRESHOLD = 5.0
    SUSPICIOUS_RATE_PER_MINUTE = 20.0
    FREQUENCY_WEIGHT = 0.6
    SIMILARITY_WEIGHT = 0.4
    PROBE_INTENSITY_MULTIPLIER = 10.0

    def __init__(
        self,
        epsilon: float = 1.0,
        noise_threshold: float = 0.5,
        suppress_threshold: float = 0.8,
        query_window_seconds: float = 300.0,
        max_tracked_queries: int = 100,
    ):
        self.epsilon = epsilon
        self.noise_threshold = noise_threshold
        self.suppress_threshold = suppress_threshold
        self.query_window = query_window_seconds
        self.max_tracked = max_tracked_queries

        # Track queries per scope: scope → [(timestamp, query_hash)]
        self._query_log: dict[str, list[tuple[float, int]]] = defaultdict(list)

    def _query_hash(self, query: str) -> int:
        """Hash nhanh query cho so sánh (không cần cryptographic)."""
        return hash(query.lower().strip())

    def _record_query(self, scope: str, query: str) -> None:
        """Ghi nhận query vào log."""
        now = time.time()
        qh = self._query_hash(query)

        log = self._query_log[scope]

        # Loại bỏ queries cũ ngoài window
        cutoff = now - self.query_window
        self._query_log[scope] = [
            (ts, h) for ts, h in log if ts > cutoff
        ][-self.max_tracked:]

        self._query_log[scope].append((now, qh))

    def _compute_probe_intensity(self, scope: str, query: str) -> float:
        """Tính cường độ probing — phát hiện Membership Inference Attack.

        Nếu ai đó hỏi nhiều câu giống nhau trong thời gian ngắn,
        probe_intensity tăng cao → có thể đang bị tấn công.

        Returns:
            0.0 (bình thường) → 1.0 (chắc chắn probing)
        """
        qh = self._query_hash(query)
        log = self._query_log.get(scope, [])

        if len(log) < 2:
            return 0.0

        # Đếm queries giống nhau (hoặc gần giống)
        similar_count = sum(1 for _, h in log if h == qh)

        # Tính tần suất query/phút
        if len(log) >= 2:
            time_span = max(0.01, log[-1][0] - log[0][0])
            query_rate = len(log) / (time_span / 60.0)
        else:
            query_rate = 0.0

        # Probe intensity: kết hợp repetition + rate
        repetition_score = min(1.0, similar_count / self.MAX_SIMILAR_THRESHOLD)
        rate_score = min(1.0, query_rate / self.SUSPICIOUS_RATE_PER_MINUTE)  # > 20 queries/phút = đáng ngờ

        intensity = repetition_score * self.FREQUENCY_WEIGHT + rate_score * self.SIMILARITY_WEIGHT
        return min(1.0, max(0.0, intensity))

    def _assess_single_result(
        self,
        result: dict[str, Any],
        probe_intensity: float,
    ) -> dict[str, Any] | None:
        """Assess a single search result for privacy risk.

        Returns the (possibly noise-injected) result dict, or ``None`` if the
        result should be suppressed.
        """
        # Lấy signals cần thiết
        score = float(result.get("score", 0.0))
        access_count = int(result.get("access_count", 0))
        confidence = float(result.get("confidence", 1.0))

        # Ước lượng query_similarity từ score (đã normalize)
        query_sim = min(1.0, score)

        # Tính prior exposure (kết hợp access_count + probe_intensity)
        effective_exposure = access_count + probe_intensity * self.PROBE_INTENSITY_MULTIPLIER

        # Bayes: P(leak | response)
        leakage_risk = BayesianPrivacyGuard.compute_leakage_risk(
            query_similarity=query_sim,
            prior_exposure=effective_exposure,
            response_confidence=confidence,
        )

        # Quyết định: suppress hoàn toàn?
        if leakage_risk > self.suppress_threshold:
            return None

        # Bơm nhiễu Laplace vào score?
        if leakage_risk > self.noise_threshold:
            noised_score = BayesianPrivacyGuard.apply_laplace_noise(
                score,
                epsilon=self.epsilon,
                sensitivity=0.1,
            )
            result = {**result, "score": max(0.0, noised_score)}
            result.setdefault("privacy", {})
            result["privacy"] = {
                "noise_applied": True,
                "leakage_risk": round(leakage_risk, 4),
                "probe_intensity": round(probe_intensity, 4),
            }

        return result

    def guard_search_results(
        self,
        results: list[dict[str, Any]],
        query: str,
        scope: str,
    ) -> list[dict[str, Any]]:
        """Post-search privacy filter — bảo vệ kết quả tìm kiếm.

        Luồng Bayesian:
        1. Ghi nhận query (track pattern)
        2. Tính probe_intensity (phát hiện tấn công?)
        3. Với mỗi kết quả:
           a. Tính leakage_risk bằng Bayes
           b. Nếu risk > noise_threshold → bơm nhiễu score
           c. Nếu risk > suppress_threshold → suppress hoàn toàn

        Args:
            results: Danh sách kết quả từ search engine
            query: Query gốc
            scope: Scope key (e.g. "project:my-project")

        Returns:
            results đã được bảo vệ (scores bị nhiễu, high-risk bị suppress)
        """
        self._record_query(scope, query)
        probe_intensity = self._compute_probe_intensity(scope, query)

        guarded: list[dict[str, Any]] = []

        for result in results:
            assessed = self._assess_single_result(result, probe_intensity)
            if assessed is not None:
                guarded.append(assessed)

        return guarded

    def get_privacy_stats(self, scope: str) -> dict[str, Any]:
        """Thống kê privacy cho scope."""
        log = self._query_log.get(scope, [])
        now = time.time()
        recent = [ts for ts, _ in log if now - ts < 60.0]

        return {
            "total_queries_tracked": len(log),
            "queries_last_minute": len(recent),
            "epsilon": self.epsilon,
            "noise_threshold": self.noise_threshold,
            "suppress_threshold": self.suppress_threshold,
        }


# ---------------------------------------------------------------------------
# 2. METRIC DIFFERENTIAL PRIVACY — Cynthia Dwork & CMAG Gaussian Noise (2025)
# ---------------------------------------------------------------------------

import random
import math

class MetricDPGaussianNoise:
    """Lõi Bảo mật Vi sai Gaussian cho Sentence Embeddings (CMAG 2025).

    Bơm nhiễu Gaussian trực tiếp vào vector nhúng để ngăn chặn Membership Inference Attacks.
    """

    @classmethod
    def generate_gaussian_noise(cls, sigma: float) -> float:
        """Sinh biến ngẫu nhiên Gaussian chuẩn bằng thuật toán Box-Muller."""
        u1 = random.random()
        u2 = random.random()
        while u1 < 1e-9:
            u1 = random.random()
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return z0 * sigma

    @classmethod
    def apply_metric_dp(
        cls,
        vector: list[float],
        epsilon: float = 1.0,
        delta: float = 1e-5,
        sensitivity: float = 2.0
    ) -> list[float]:
        """Bơm nhiễu Gaussian để đạt (epsilon, delta)-Differential Privacy trên metric space."""
        if not vector:
            return []

        dim = len(vector)
        # Tính toán sigma của cơ chế Gaussian: sigma = sensitivity * sqrt(2 * ln(1.25/delta)) / epsilon
        log_term = math.log(1.25 / delta)
        sigma = (sensitivity * math.sqrt(2.0 * log_term)) / epsilon

        # Bơm nhiễu vào từng chiều
        noised_vector = []
        for x in vector:
            noise = cls.generate_gaussian_noise(sigma)
            noised_vector.append(x + noise)

        # Re-normalize về mặt cầu đơn vị L2 để bảo toàn hình học vector và cosine similarity
        l2_norm = math.sqrt(sum(val * val for val in noised_vector))
        if l2_norm > 1e-9:
            noised_vector = [val / l2_norm for val in noised_vector]
        else:
            noised_vector = vector[:]  # Fallback nếu nhiễu triệt tiêu hoàn toàn

        return noised_vector


# ---------------------------------------------------------------------------
# 3. PAILLIER PARTIALLY HOMOMORPHIC ENGINE — Secure Vector Similarity Search
# ---------------------------------------------------------------------------

class PaillierPartiallyHomomorphicEngine:
    """Hệ mật mã đồng cấu cộng Paillier (Paillier Cryptosystem 1999).

    Hỗ trợ tính toán tích vô hướng (Dot Product) mù hoàn toàn trên máy chủ.
    """

    # Pre-selected primes cho môi trường cục bộ để tránh trễ CPU khi sinh khóa ngẫu nhiên
    DEFAULT_P = 9803
    DEFAULT_Q = 9923

    @classmethod
    def generate_keys(cls, p: int = DEFAULT_P, q: int = DEFAULT_Q) -> tuple[dict[str, int], dict[str, int]]:
        """Khởi tạo Public Key (n, g) và Private Key (lambda, mu) của hệ mật mã Paillier."""
        n = p * q
        g = n + 1  # Lựa chọn chuẩn g = n + 1

        # lambda = (p-1)*(q-1)
        lam = (p - 1) * (q - 1)

        # mu = lam^-1 mod n
        mu = cls._mod_inverse(lam, n)

        pub_key = {"n": n, "g": g, "n_sq": n * n}
        priv_key = {"lam": lam, "mu": mu, "n": n, "n_sq": n * n}

        return pub_key, priv_key

    @classmethod
    def encrypt(cls, plaintext: int, pub_key: dict[str, int], r_fixed: int | None = None) -> int:
        """Mã hóa số nguyên bản rõ m thành bản mã c: c = (1 + m*n) * r^n mod n^2."""
        n = pub_key["n"]
        n_sq = pub_key["n_sq"]

        # Ánh xạ số âm qua modulo arithmetic
        m = plaintext % n

        # Chọn số ngẫu nhiên r coprime với n
        r = r_fixed if r_fixed is not None else random.randint(1, n - 1)
        while cls._gcd(r, n) != 1:
            r = random.randint(1, n - 1)

        # c = (1 + m * n) * r^n mod n^2
        r_n = pow(r, n, n_sq)
        c = ((1 + m * n) * r_n) % n_sq
        return c

    @classmethod
    def decrypt(cls, ciphertext: int, priv_key: dict[str, int]) -> int:
        """Giải mã bản mã c thành bản rõ m sử dụng Private Key."""
        n = priv_key["n"]
        n_sq = priv_key["n_sq"]
        lam = priv_key["lam"]
        mu = priv_key["mu"]

        # u = c^lam mod n^2
        u = pow(ciphertext, lam, n_sq)

        # L(u) = (u - 1) // n
        l_u = (u - 1) // n

        # m = L(u) * mu mod n
        m = (l_u * mu) % n

        # Đưa số âm trở lại khoảng giá trị thực tế
        if m > n // 2:
            m -= n
        return m

    @classmethod
    def homomorphic_dot_product(
        cls,
        encrypted_vector: list[int],
        plaintext_query_vector: list[int],
        pub_key: dict[str, int]
    ) -> int:
        """Tính tích vô hướng đồng cấu giữa Encrypted Vector và Plaintext Query Vector trên Server.

        Sử dụng phép lũy thừa đồng cấu phép nhân: E(m)^k = E(k*m)
        Và phép nhân bản mã đồng cấu phép cộng: E(m1) * E(m2) = E(m1 + m2)
        """
        n_sq = pub_key["n_sq"]
        dim = len(encrypted_vector)
        if dim != len(plaintext_query_vector):
            raise ValueError("Vector dimensions must match")

        c_dot = 1
        for c_i, q_i in zip(encrypted_vector, plaintext_query_vector):
            if q_i == 0:
                continue
            elif q_i > 0:
                # E(m_i)^q_i = E(m_i * q_i)
                term = pow(c_i, q_i, n_sq)
            else:
                # Lũy thừa số âm: nghịch đảo modulo của c_i trước
                c_inv = cls._mod_inverse(c_i, n_sq)
                term = pow(c_inv, -q_i, n_sq)

            c_dot = (c_dot * term) % n_sq

        return c_dot

    @staticmethod
    def _gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    @classmethod
    def _ext_gcd(cls, a: int, b: int) -> tuple[int, int, int]:
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = cls._ext_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y

    @classmethod
    def _mod_inverse(cls, a: int, m: int) -> int:
        gcd, x, y = cls._ext_gcd(a, m)
        if gcd != 1:
            raise ValueError(f"Mod inverse of {a} mod {m} does not exist")
        return x % m


# ---------------------------------------------------------------------------
# 4. SHANNON ENTROPY ANOMALY DETECTOR — Information Theory Poison Defense
# ---------------------------------------------------------------------------

class ShannonEntropyPoisonDetector:
    """Hệ thống tự phòng vệ chống nhiễm độc bộ nhớ và Prompt Injection dựa trên Entropy thông tin.

    Phát hiện sự sụt giảm đột ngột của Entropy khi có tấn công lặp chuỗi.
    """

    @staticmethod
    def compute_shannon_entropy(text: str) -> float:
        """Tính toán Shannon Entropy của chuỗi ký tự (bits per character)."""
        if not text:
            return 0.0

        # Tần suất xuất hiện của từng ký tự
        char_counts: dict[str, int] = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        total_chars = len(text)
        entropy = 0.0
        for count in char_counts.values():
            p_x = count / total_chars
            entropy -= p_x * math.log2(p_x)

        return round(entropy, 4)

    @classmethod
    def assess_poison_risk(
        cls,
        text: str,
        danger_threshold: float = 3.2,
        warning_threshold: float = 3.7
    ) -> dict[str, Any]:
        """Đánh giá nguy cơ độc hại của chuỗi đầu vào dựa trên Entropy."""
        entropy = cls.compute_shannon_entropy(text)

        # Độ dài chuỗi tối thiểu để kiểm định đáng tin cậy
        if len(text) < 15:
            return {
                "entropy": entropy,
                "status": "safe",
                "risk_score": 0.0,
                "reason": "text_too_short"
            }

        # Phân loại trạng thái
        if entropy < danger_threshold:
            status = "poison_detected"
            risk_score = min(1.0, 0.7 + (danger_threshold - entropy) * 0.3)
            reason = "Entropy sụt giảm nghiêm trọng (phát hiện tấn công lặp chuỗi hoặc Prompt Injection)"
        elif entropy < warning_threshold:
            status = "warning"
            risk_score = 0.4 + (warning_threshold - entropy) * 0.6 * 0.5
            reason = "Entropy có dấu hiệu thấp hơn bình thường, cần giám sát"
        else:
            status = "safe"
            risk_score = 0.0
            reason = "Phân phối thông tin tự nhiên, an toàn"

        return {
            "entropy": entropy,
            "status": status,
            "risk_score": round(risk_score, 4),
            "reason": reason
        }
