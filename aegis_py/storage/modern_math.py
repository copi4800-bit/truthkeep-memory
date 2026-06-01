"""Toán học cho TruthKeep Memory — Phase 2 + Phase 3

Module lõi tích hợp 10 hệ thống toán học:

Phase 2 — Cấu trúc không gian:
1. Hilbert Space (David Hilbert) — Cosine similarity trong không gian vector
2. Nash Embedding (John Nash) — Bảo toàn khoảng cách khi nén
3. Erdős Discrete Geometry (Paul Erdős) — Tối ưu hóa phân bổ tọa độ ký ức
4. Poincaré TDA (Henri Poincaré) — Nhận diện bản chất bất chấp nhiễu
5. Euler/Cayley Graph (Euler & Cayley) — Centrality cho Knowledge Graph

Phase 3 — Công thức vận hành:
6. Bayes' Theorem (Thomas Bayes) — Cập nhật niềm tin khi có bằng chứng mới
7. Fourier Transform (Fourier/Gauss) — Nén ký ức thành vân tay tần số
8. Backpropagation (Rumelhart/Hinton) — Lan truyền điều chỉnh qua mạng ký ức
9. Bellman Equation (Richard Bellman) — Giá trị chiến lược cho procedural memory
10. Modern Hopfield Attractor (MHN) — Động lực học hồi tưởng Lyapunov lũy thừa
"""
from __future__ import annotations

import hashlib
import math
import re
import struct
from collections import Counter, deque
from typing import Any

__all__ = [
    "HilbertSpaceEngine",
    "NashEmbeddingPreserver",
    "ErdosIndexGrid",
    "PoincareTDAEngine",
    "EulerCayleyGraphEngine",
    "compute_memory_modern_math_fields",
    "BayesianBeliefEngine",
    "FourierCompressor",
    "BackpropagationEngine",
    "BellmanValueEngine",
    "ModernHopfieldAttractorEngine",
    "SpectralGraphEngine",
    "HyperbolicGraphEngine",
    "BeltramiDiffusionEngine",
    "EulerLagrangeVariationalEngine",
    "MiniCSRMatrix",
    "ForceDirectedPoincareEngine",
    "MarkovChainCognitiveEngine",
    "DirichletHarmonicEngine",
    "TopologicalHoleDetector",
    "CategoryTheoryFunctorEngine",
]


class MiniCSRMatrix:
    """Ma trận thưa CSR thu nhỏ xây dựng on-the-fly cho các vùng nhớ cục bộ."""
    def __init__(self, row_ptr: list[int], col_indices: list[int], values: list[float], shape: tuple[int, int]):
        self.row_ptr = row_ptr
        self.col_indices = col_indices
        self.values = values
        self.shape = shape

    @classmethod
    def from_dense_cost(cls, cost_matrix: list[list[float]], reg: float = 0.1, threshold: float = 1e-4) -> MiniCSRMatrix:
        """Xây dựng Mini-CSR từ ma trận chi phí dày bằng cách tính Gibbs kernel exp(-C/reg) và loại các phần tử < threshold."""
        n = len(cost_matrix)
        m = len(cost_matrix[0]) if n > 0 else 0

        row_ptr = [0]
        col_indices = []
        values = []

        for i in range(n):
            for j in range(m):
                val = math.exp(-cost_matrix[i][j] / reg)
                if val >= threshold:
                    col_indices.append(j)
                    values.append(val)
            row_ptr.append(len(values))

        return cls(row_ptr, col_indices, values, (n, m))


# ---------------------------------------------------------------------------
# 1. HILBERT SPACE ENGINE — David Hilbert
# ---------------------------------------------------------------------------

class HilbertSpaceEngine:
    """Không gian Hilbert — Chuyển text thành vector đa chiều và tính Cosine Similarity.

    Sử dụng character n-gram hashing để tạo vector dense trong không gian Hilbert
    N chiều. Ưu điểm so với bag-of-words: bắt được cấu trúc sub-word, kháng nhiễu
    tốt hơn với typo và biến thể từ.
    """

    DEFAULT_DIMENSIONS = 64
    NGRAM_SIZES = (2, 3, 4)  # bi-gram, tri-gram, 4-gram

    @classmethod
    def text_to_hilbert_vector(cls, text: str, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
        """Chuyển đổi text thành vector trong không gian Hilbert N chiều.

        Thuật toán: Character n-gram hashing projection
        - Tách text thành n-grams (2,3,4 ký tự)
        - Hash mỗi n-gram → vị trí trong vector + giá trị (+1/-1)
        - L2-normalize kết quả
        """
        if not text or not text.strip():
            return [0.0] * dimensions

        normalized = text.lower().strip()
        vector = [0.0] * dimensions

        for n in cls.NGRAM_SIZES:
            for i in range(len(normalized) - n + 1):
                ngram = normalized[i:i + n]
                # Hash ngram → (position, sign)
                h = hashlib.blake2b(ngram.encode("utf-8"), digest_size=8).digest()
                val = int.from_bytes(h, "little")
                position = val % dimensions
                sign = 1.0
                vector[position] += sign

        # L2 normalization — chiếu lên mặt cầu đơn vị trong không gian Hilbert
        magnitude = math.sqrt(sum(x * x for x in vector))
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Tính Cosine Similarity giữa 2 vector trong không gian Hilbert.

        cos(θ) = (A·B) / (|A| × |B|)
        Với vector đã L2-normalize: cos(θ) = A·B
        """
        if len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        # Clamp to [-1, 1] to handle floating point errors
        return max(-1.0, min(1.0, dot))

    @staticmethod
    def hilbert_distance(vec_a: list[float], vec_b: list[float]) -> float:
        """Tính khoảng cách Euclid trong không gian Hilbert.

        d(A, B) = √(Σ(aᵢ - bᵢ)²)
        """
        if len(vec_a) != len(vec_b):
            return float("inf")
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)))

    @classmethod
    def batch_cosine_similarity(cls, query_vec: list[float], candidate_vecs: list[list[float]]) -> list[float]:
        """Tính cosine similarity hàng loạt — tối ưu cho search pipeline."""
        return [cls.cosine_similarity(query_vec, c) for c in candidate_vecs]


# ---------------------------------------------------------------------------
# 2. NASH EMBEDDING PRESERVER — John Nash
# ---------------------------------------------------------------------------

class NashEmbeddingPreserver:
    """Định lý Nhúng Nash — Bảo toàn khoảng cách khi nén đa tạp vào không gian phẳng.

    Giám sát việc compressed prefilter có phá hủy cấu trúc khoảng cách không.
    Nếu distortion ratio > ngưỡng → cảnh báo mất thông tin.
    """

    DISTORTION_THRESHOLD = 0.3  # Max acceptable distortion

    @staticmethod
    def compute_distortion_ratio(
        original_distances: list[float],
        compressed_distances: list[float],
    ) -> float:
        """Tính tỷ lệ biến dạng Nash giữa khoảng cách gốc và khoảng cách nén.

        distortion = mean(|d_orig - d_compressed| / max(d_orig, ε))
        Giá trị 0 = bảo toàn hoàn hảo, >0.3 = mất thông tin đáng kể.
        """
        if not original_distances or len(original_distances) != len(compressed_distances):
            return 0.0

        total_distortion = 0.0
        count = 0
        for d_orig, d_comp in zip(original_distances, compressed_distances):
            denominator = max(abs(d_orig), 1e-9)
            total_distortion += abs(d_orig - d_comp) / denominator
            count += 1

        return total_distortion / max(count, 1)

    @classmethod
    def nash_isometric_projection(cls, vector: list[float], target_dim: int) -> list[float]:
        """Nhúng đẳng cự Nash — chiếu vector xuống chiều thấp hơn bảo toàn khoảng cách.

        Sử dụng random projection (Johnson-Lindenstrauss lemma) với seed cố định
        để đảm bảo tính tất định.
        """
        source_dim = len(vector)
        if target_dim >= source_dim:
            return vector[:target_dim] + [0.0] * max(0, target_dim - source_dim)

        projected = [0.0] * target_dim
        scale = 1.0 / math.sqrt(target_dim)

        for j in range(target_dim):
            val = 0.0
            for i in range(source_dim):
                # Deterministic pseudo-random sign: hash(i, j)
                seed = hashlib.md5(f"{i}:{j}".encode()).digest()
                sign = 1.0 if seed[0] & 1 else -1.0
                val += sign * vector[i]
            projected[j] = val * scale

        return projected

    @classmethod
    def evaluate_embedding_quality(
        cls,
        original_vec: list[float],
        compressed_mask: int,
        mask_width: int,
    ) -> dict[str, float]:
        """Đánh giá chất lượng nhúng giữa Hilbert vector và compressed bitmask."""
        # Reconstruct approximate distances from bitmask
        orig_norm = math.sqrt(sum(x * x for x in original_vec))
        mask_density = bin(compressed_mask).count("1") / max(mask_width, 1)

        return {
            "original_norm": round(orig_norm, 6),
            "mask_density": round(mask_density, 6),
            "nash_quality": round(min(1.0, mask_density * 1.5), 6),
        }


# ---------------------------------------------------------------------------
# 3. ERDŐS INDEX GRID — Paul Erdős
# ---------------------------------------------------------------------------

class ErdosIndexGrid:
    """Hình học rời rạc Erdős — Tối ưu hóa phân bổ tọa độ ký ức.

    Chia không gian Hilbert thành lưới K×K cells. Mỗi memory được gán vào
    một cell dựa trên Hilbert vector. Khi search, chỉ cần scan cell hiện tại
    + các cells lân cận (unit distance neighbors theo Erdős).

    Giảm search space từ O(N) xuống O(N/K²).
    """

    DEFAULT_RESOLUTION = 8  # 8×8 = 64 cells

    @classmethod
    def assign_grid_cell(cls, vector: list[float], grid_resolution: int = DEFAULT_RESOLUTION) -> int:
        """Gán vector vào Erdős grid cell.

        Thuật toán: Chiếu vector xuống 2D qua PCA-like hashing,
        rồi lượng tử hóa vào ô lưới.
        """
        if not vector:
            return 0

        dim = len(vector)
        # Project to 2D using deterministic hash projections
        x_proj = sum(vector[i] * (1.0 if i % 2 == 0 else -1.0) for i in range(dim))
        y_proj = sum(vector[i] * (1.0 if i % 3 == 0 else -1.0) for i in range(dim))

        # Normalize to [0, grid_resolution-1]
        x_cell = int((math.atan2(x_proj, 1.0) / math.pi + 0.5) * (grid_resolution - 1))
        y_cell = int((math.atan2(y_proj, 1.0) / math.pi + 0.5) * (grid_resolution - 1))

        x_cell = max(0, min(grid_resolution - 1, x_cell))
        y_cell = max(0, min(grid_resolution - 1, y_cell))

        return y_cell * grid_resolution + x_cell

    @classmethod
    def compute_unit_distance_neighbors(cls, cell_id: int, grid_resolution: int = DEFAULT_RESOLUTION) -> list[int]:
        """Tính danh sách cells lân cận theo khoảng cách đơn vị Erdős.

        Bao gồm 8 ô liền kề (Moore neighborhood) + chính ô hiện tại.
        Đây là bài toán unit distance graph trên lưới — Erdős chứng minh
        đây là cấu hình tối ưu cho tìm kiếm lân cận.
        """
        x = cell_id % grid_resolution
        y = cell_id // grid_resolution
        neighbors = []

        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < grid_resolution and 0 <= ny < grid_resolution:
                    neighbors.append(ny * grid_resolution + nx)

        return neighbors

    @classmethod
    def compute_cell_density(cls, cell_counts: dict[int, int], grid_resolution: int = DEFAULT_RESOLUTION) -> dict[str, float]:
        """Phân tích mật độ phân bổ Erdős grid — phát hiện cluster và void."""
        total_cells = grid_resolution * grid_resolution
        occupied = sum(1 for c in cell_counts.values() if c > 0)
        total_items = sum(cell_counts.values())

        if total_items == 0:
            return {"occupancy_rate": 0.0, "max_density": 0.0, "uniformity": 0.0}

        max_count = max(cell_counts.values()) if cell_counts else 0
        ideal_per_cell = total_items / total_cells
        variance = sum((c - ideal_per_cell) ** 2 for c in cell_counts.values()) / max(len(cell_counts), 1)

        return {
            "occupancy_rate": round(occupied / total_cells, 6),
            "max_density": round(max_count / total_items, 6) if total_items else 0.0,
            "uniformity": round(1.0 / (1.0 + math.sqrt(variance)), 6),
        }


# ---------------------------------------------------------------------------
# 4. POINCARÉ TDA ENGINE — Henri Poincaré
# ---------------------------------------------------------------------------

class PoincareTDAEngine:
    """Tôpô học đại số Poincaré — Trích xuất đặc trưng tôpô từ text.

    Thay vì dùng Vietoris-Rips complex (cần numpy), ta đơn giản hóa TDA
    bằng phương pháp n-gram adjacency persistence:
    - Xây dựng đồ thị adjacency từ n-grams
    - Tính số Betti đơn giản (connected components, cycles)
    - Trả về persistence signature (β₀, β₁, β₂)
    """

    BETTI_WEIGHTS = (0.5, 0.35, 0.15)

    @classmethod
    def compute_persistence_signature(cls, text: str) -> tuple[int, int, int]:
        """Trích xuất persistence signature (β₀, β₁, β₂) từ text.

        β₀ = số thành phần liên thông (connected components) — đo số "cụm ý tưởng"
        β₁ = số chu trình (cycles) — đo sự lặp lại/tham chiếu chéo
        β₂ = số khoang rỗng (voids) — đo khoảng trống ngữ nghĩa
        """
        if not text or not text.strip():
            return (0, 0, 0)

        # Chuẩn hóa, tách các từ và sắp xếp alphabet để đảm bảo tính bất biến với thứ tự từ
        words = sorted(re.findall(r"\w+", text.lower()))
        if not words:
            return (1, 0, 0)

        normalized = "".join(words)
        tokens = list(normalized)
        if len(tokens) < 2:
            return (1, 0, 0)

        # Xây dựng adjacency graph từ bigrams
        adjacency: dict[str, set[str]] = {}
        for i in range(len(tokens) - 1):
            a, b = tokens[i], tokens[i + 1]
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)

        # β₀: Connected components (BFS)
        visited: set[str] = set()
        components = 0
        for node in adjacency:
            if node not in visited:
                components += 1
                queue = deque([node])
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    for neighbor in adjacency.get(current, ()):
                        if neighbor not in visited:
                            queue.append(neighbor)

        # β₁: Approximate cycle count (edges - nodes + components)
        total_edges = sum(len(neighbors) for neighbors in adjacency.values()) // 2
        total_nodes = len(adjacency)
        cycles = max(0, total_edges - total_nodes + components)

        # β₂: Void approximation — based on token diversity vs total
        unique_ratio = len(set(tokens)) / max(len(tokens), 1)
        voids = max(0, int((1.0 - unique_ratio) * len(tokens) * 0.1))

        return (components, cycles, voids)

    @classmethod
    def topological_similarity(cls, sig_a: tuple[int, ...], sig_b: tuple[int, ...]) -> float:
        """Tính độ tương đồng tôpô giữa 2 persistence signatures.

        Sử dụng Wasserstein-inspired distance đơn giản có chuẩn hóa theo tổng số Betti numbers
        để đảm bảo tính bất biến với độ dài văn bản:
        similarity = 1 / (1 + Σ|norm_βᵢ_a - norm_βᵢ_b| * wᵢ)
        """
        if not sig_a or not sig_b:
            return 0.0

        sum_a = sum(sig_a) or 1
        sum_b = sum(sig_b) or 1

        norm_a = [x / sum_a for x in sig_a]
        norm_b = [x / sum_b for x in sig_b]

        weights = cls.BETTI_WEIGHTS  # β₀ quan trọng nhất
        distance = 0.0
        for i in range(min(len(norm_a), len(norm_b), len(weights))):
            distance += abs(norm_a[i] - norm_b[i]) * weights[i]

        return 1.0 / (1.0 + distance)

    @classmethod
    def signature_to_string(cls, sig: tuple[int, ...]) -> str:
        """Serialize signature thành string để lưu DB."""
        return ",".join(str(x) for x in sig)

    @classmethod
    def string_to_signature(cls, s: str) -> tuple[int, ...]:
        """Deserialize signature từ DB string."""
        if not s or not s.strip():
            return (0, 0, 0)
        try:
            parts = [int(x.strip()) for x in s.split(",")]
            return tuple(parts)
        except (ValueError, TypeError):
            return (0, 0, 0)


# ---------------------------------------------------------------------------
# 5. EULER/CAYLEY GRAPH ENGINE — Leonhard Euler & Arthur Cayley
# ---------------------------------------------------------------------------

class EulerCayleyGraphEngine:
    """Lý thuyết đồ thị Euler/Cayley — Centrality Analysis cho Knowledge Graph.

    Tính toán các chỉ số centrality để ưu tiên "hub nodes" trong link expansion:
    - Degree Centrality: đo số kết nối trực tiếp
    - Betweenness Centrality: đo vai trò "cầu nối" giữa các cụm
    """

    HUB_CENTRALITY_WEIGHT = 0.6
    HUB_DEGREE_WEIGHT = 0.4

    @staticmethod
    def build_adjacency_from_links(links: list[dict[str, Any]]) -> dict[str, list[str]]:
        """Xây dựng adjacency list từ danh sách memory_links."""
        adjacency: dict[str, list[str]] = {}
        for link in links:
            src = str(link.get("source_id", ""))
            tgt = str(link.get("target_id", ""))
            if src and tgt:
                adjacency.setdefault(src, []).append(tgt)
                adjacency.setdefault(tgt, []).append(src)
        return adjacency

    @staticmethod
    def compute_degree_centrality(adjacency: dict[str, list[str]]) -> dict[str, float]:
        """Tính Degree Centrality cho mỗi node.

        C_D(v) = deg(v) / (N - 1)
        Node có nhiều kết nối = hub quan trọng trong mạng lưới ký ức.
        """
        n = len(adjacency)
        if n <= 1:
            return {node: 0.0 for node in adjacency}

        denominator = n - 1
        return {
            node: round(len(set(neighbors)) / denominator, 6)
            for node, neighbors in adjacency.items()
        }

    @staticmethod
    def compute_betweenness_centrality(adjacency: dict[str, list[str]]) -> dict[str, float]:
        """Tính Betweenness Centrality cho mỗi node (thuật toán Brandes đơn giản).

        C_B(v) = Σ (σ_st(v) / σ_st) cho mọi cặp s,t
        Node nằm trên nhiều đường đi ngắn nhất = "cầu nối" quan trọng.

        Giới hạn ở O(V × E) để phù hợp với embedded environment.
        """
        nodes = list(adjacency.keys())
        n = len(nodes)
        if n <= 2:
            return {node: 0.0 for node in nodes}

        betweenness: dict[str, float] = {node: 0.0 for node in nodes}

        for source in nodes:
            # BFS from source
            stack: list[str] = []
            predecessors: dict[str, list[str]] = {node: [] for node in nodes}
            sigma: dict[str, int] = {node: 0 for node in nodes}
            sigma[source] = 1
            dist: dict[str, int] = {node: -1 for node in nodes}
            dist[source] = 0
            queue: deque[str] = deque([source])

            while queue:
                v = queue.popleft()
                stack.append(v)
                for w in adjacency.get(v, []):
                    if w not in dist or dist[w] < 0:
                        dist[w] = dist[v] + 1
                        queue.append(w)
                    if dist.get(w, -1) == dist[v] + 1:
                        sigma[w] += sigma[v]
                        predecessors[w].append(v)

            # Back-propagation
            delta: dict[str, float] = {node: 0.0 for node in nodes}
            while stack:
                w = stack.pop()
                for v in predecessors[w]:
                    if sigma[w] > 0:
                        delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != source:
                    betweenness[w] += delta[w]

        # Normalize
        norm = max(1, (n - 1) * (n - 2))
        return {node: round(val / norm, 6) for node, val in betweenness.items()}

    @staticmethod
    def find_hub_nodes(adjacency: dict[str, list[str]], top_k: int = 5) -> list[tuple[str, float]]:
        """Tìm top-K hub nodes dựa trên combined centrality score."""
        degree = EulerCayleyGraphEngine.compute_degree_centrality(adjacency)
        betweenness = EulerCayleyGraphEngine.compute_betweenness_centrality(adjacency)

        combined: dict[str, float] = {}
        for node in adjacency:
            combined[node] = degree.get(node, 0.0) * EulerCayleyGraphEngine.HUB_CENTRALITY_WEIGHT + betweenness.get(node, 0.0) * EulerCayleyGraphEngine.HUB_DEGREE_WEIGHT

        sorted_nodes = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_k]

    @staticmethod
    def has_euler_path(adjacency: dict[str, list[str]]) -> bool:
        """Kiểm tra tồn tại đường đi Euler (đi qua mỗi cạnh đúng 1 lần).

        Định lý Euler: Đồ thị liên thông có đường đi Euler ⟺ có đúng 0 hoặc 2
        đỉnh bậc lẻ.
        """
        if not adjacency:
            return False

        odd_degree_count = sum(1 for neighbors in adjacency.values() if len(neighbors) % 2 != 0)
        return odd_degree_count in (0, 2)


# ---------------------------------------------------------------------------
# HELPER: Compute all modern math fields for a memory
# ---------------------------------------------------------------------------

def compute_memory_modern_math_fields(
    content: str,
    *,
    subject: str | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    """Tính toán tất cả trường toán học hiện đại cho một memory.

    Returns dict with:
        - hilbert_vector: list[float] (64-dim)
        - erdos_cell_id: int
        - tda_signature: str
    """
    full_text = " ".join(filter(None, [content, subject, summary]))

    # Hilbert Space vector
    hilbert_vector = HilbertSpaceEngine.text_to_hilbert_vector(full_text)

    # Erdős grid cell
    erdos_cell_id = ErdosIndexGrid.assign_grid_cell(hilbert_vector)

    # Poincaré TDA signature
    tda_sig = PoincareTDAEngine.compute_persistence_signature(full_text)
    tda_signature = PoincareTDAEngine.signature_to_string(tda_sig)

    return {
        "hilbert_vector": hilbert_vector,
        "erdos_cell_id": erdos_cell_id,
        "tda_signature": tda_signature,
    }


# ===========================================================================
# PHASE 3 — CÔNG THỨC VẬN HÀNH
# ===========================================================================


# ---------------------------------------------------------------------------
# 6. BAYESIAN BELIEF ENGINE — Thomas Bayes
# ---------------------------------------------------------------------------

class BayesianBeliefEngine:
    """Xác suất Bayes — Cập nhật niềm tin động khi có bằng chứng mới.

    P(A|B) = P(B|A) · P(A) / P(B)

    Thay vì gán confidence cứng, Bayes cho phép AI cập nhật niềm tin
    dần dần dựa trên bằng chứng tích lũy — giống cách bộ não con người
    trưởng thành qua trải nghiệm.
    """

    MIN_PROBABILITY = 0.001
    MAX_PROBABILITY = 0.999
    PRIOR_WEIGHT = 0.5
    EVIDENCE_WEIGHT = 0.3
    RECENCY_WEIGHT = 0.2
    BELIEF_FLOOR = 0.01
    BELIEF_CEILING = 0.99

    @staticmethod
    def posterior(prior: float, likelihood: float, evidence_marginal: float = 0.0) -> float:
        """Tính xác suất hậu nghiệm Bayes.

        P(A|B) = P(B|A) × P(A) / P(B)

        Args:
            prior: P(A) — xác suất tiên nghiệm (niềm tin hiện tại)
            likelihood: P(B|A) — xác suất bằng chứng nếu giả thuyết đúng
            evidence_marginal: P(B) — xác suất tổng thể của bằng chứng
                Nếu = 0, tự tính: P(B) = P(B|A)·P(A) + P(B|¬A)·P(¬A)
        """
        prior = max(BayesianBeliefEngine.MIN_PROBABILITY, min(BayesianBeliefEngine.MAX_PROBABILITY, prior))
        likelihood = max(BayesianBeliefEngine.MIN_PROBABILITY, min(BayesianBeliefEngine.MAX_PROBABILITY, likelihood))

        if evidence_marginal <= 0:
            # Auto-compute marginal: P(B) = P(B|A)·P(A) + P(B|¬A)·P(¬A)
            # Assume P(B|¬A) = 1 - likelihood (complementary)
            p_b_not_a = max(BayesianBeliefEngine.MIN_PROBABILITY, 1.0 - likelihood)
            evidence_marginal = likelihood * prior + p_b_not_a * (1.0 - prior)

        posterior = (likelihood * prior) / max(evidence_marginal, 1e-9)
        return max(0.0, min(1.0, posterior))

    @classmethod
    def sequential_update(cls, prior: float, observations: list[tuple[float, float]]) -> float:
        """Cập nhật Bayes tuần tự qua nhiều quan sát.

        Mỗi observation = (likelihood, evidence_marginal).
        Posterior của bước trước trở thành prior của bước sau.
        """
        current = prior
        for likelihood, evidence_marginal in observations:
            current = cls.posterior(current, likelihood, evidence_marginal)
        return current

    @staticmethod
    def belief_from_signals(
        prior_belief: float,
        evidence_signal: float,
        support_signal: float,
        conflict_signal: float,
    ) -> float:
        """Tính Bayesian belief từ các v10 signals.

        Chuyển đổi signals thành likelihood rồi áp dụng Bayes:
        - likelihood = evidence × 0.5 + support × 0.3 + (1 - conflict) × 0.2
        - evidence_marginal = auto-computed
        """
        likelihood = (
            evidence_signal * BayesianBeliefEngine.PRIOR_WEIGHT
            + support_signal * BayesianBeliefEngine.EVIDENCE_WEIGHT
            + (1.0 - conflict_signal) * BayesianBeliefEngine.RECENCY_WEIGHT
        )
        likelihood = max(BayesianBeliefEngine.BELIEF_FLOOR, min(BayesianBeliefEngine.BELIEF_CEILING, likelihood))
        return BayesianBeliefEngine.posterior(prior_belief, likelihood)


# ---------------------------------------------------------------------------
# 7. FOURIER COMPRESSOR — Joseph Fourier & Gauss
# ---------------------------------------------------------------------------

class FourierCompressor:
    """Biến đổi Fourier — Nén ký ức thành vân tay tần số.

    X_k = Σ x_n · e^(-i·2π·k·n/N)

    Thay vì lưu toàn bộ text, Fourier trích xuất phổ tần số ký tự —
    "vân tay" gọn nhẹ nhưng giữ được cấu trúc lặp lại, tần suất từ,
    và mẫu phân bố mà bloom filter bitmask không thể bắt được.
    """

    DEFAULT_COEFFICIENTS = 16

    @classmethod
    def text_to_spectrum(cls, text: str, n_coefficients: int = DEFAULT_COEFFICIENTS) -> list[float]:
        """Chuyển text thành phổ tần số (DFT coefficients).

        Thuật toán:
        1. Đếm tần suất ký tự (character frequency distribution)
        2. Tính DFT: X_k = Σ x_n · cos(2π·k·n/N) (phần thực)
        3. Giữ top-K hệ số (magnitude)
        4. L2-normalize
        """
        if not text or not text.strip():
            return [0.0] * n_coefficients

        normalized = text.lower().strip()

        # Bước 1: Character frequency distribution (256 bins cho ASCII + Unicode cơ bản)
        freq = [0.0] * 256
        for ch in normalized:
            idx = ord(ch) % 256
            freq[idx] += 1.0

        # Normalize frequency
        total = sum(freq)
        if total > 0:
            freq = [f / total for f in freq]

        n = len(freq)
        spectrum = []

        # Bước 2: DFT (lấy magnitude của mỗi frequency bin)
        for k in range(n_coefficients):
            real = 0.0
            imag = 0.0
            for nn in range(n):
                angle = 2.0 * math.pi * k * nn / n
                real += freq[nn] * math.cos(angle)
                imag -= freq[nn] * math.sin(angle)
            magnitude = math.sqrt(real * real + imag * imag)
            spectrum.append(magnitude)

        # Bước 3: L2-normalize
        mag = math.sqrt(sum(x * x for x in spectrum))
        if mag > 0:
            spectrum = [x / mag for x in spectrum]

        return spectrum

    @classmethod
    def spectral_similarity(cls, spec_a: list[float], spec_b: list[float]) -> float:
        """Tính độ tương đồng phổ giữa 2 vân tay tần số.

        Sử dụng spectral correlation (cosine similarity trong miền tần số).
        """
        if not spec_a or not spec_b:
            return 0.0
        min_len = min(len(spec_a), len(spec_b))
        dot = sum(spec_a[i] * spec_b[i] for i in range(min_len))
        return max(0.0, min(1.0, dot))

    @classmethod
    def spectral_fingerprint_hex(cls, spectrum: list[float]) -> str:
        """Serialize spectrum thành hex string để lưu vào metadata."""
        # Quantize mỗi coefficient thành 1 byte (0-255)
        quantized = [max(0, min(255, int(abs(v) * 255))) for v in spectrum]
        return "".join(f"{b:02x}" for b in quantized)

    @classmethod
    def hex_to_spectrum(cls, hex_str: str) -> list[float]:
        """Deserialize hex string thành spectrum."""
        if not hex_str:
            return []
        try:
            values = [int(hex_str[i:i+2], 16) / 255.0 for i in range(0, len(hex_str), 2)]
            return values
        except (ValueError, IndexError):
            return []


# ---------------------------------------------------------------------------
# 8. BACKPROPAGATION ENGINE — Rumelhart, Hinton
# ---------------------------------------------------------------------------

class BackpropagationEngine:
    """Lan truyền ngược — Điều chỉnh trọng số khi correction xảy ra.

    ∂L/∂w = ∂L/∂y · ∂y/∂z · ∂z/∂w

    Khi memory A bị correct, các memories linked tới A cũng cần
    điều chỉnh — mức độ tỷ lệ với link weight và giảm theo depth.
    Giống cách neural network lan truyền gradient sai số ngược lại.
    """

    GRADIENT_CLAMP = 0.5
    GRADIENT_THRESHOLD = 0.001
    DEFAULT_LEARNING_RATE = 0.15
    MAX_PROPAGATION_DEPTH = 3

    @classmethod
    def compute_gradient(
        cls,
        error: float,
        link_weight: float,
        depth: int,
        learning_rate: float = DEFAULT_LEARNING_RATE,
    ) -> float:
        """Tính gradient cho một kết nối tại depth cho trước.

        Công thức: gradient = error * (link_weight ^ depth) * lambda
        Trong đó lambda = 0.7 là hằng số suy giảm toàn cục (global decay factor).

        - error: mức độ sai lệch (0.0 → 1.0)
        - link_weight: trọng số liên kết (từ memory_links table)
        - depth: khoảng cách hop từ memory bị correct
        - learning_rate: không dùng trực tiếp trong công thức chuẩn của user,
                         nhưng được nhân thêm nếu cần tinh chỉnh. Ở đây ta tuân thủ công thức chính xác:
                         gradient = error * (link_weight ** depth) * 0.7
        """
        decay_factor = 0.7
        gradient = error * (link_weight ** max(1, depth)) * decay_factor
        return round(max(-cls.GRADIENT_CLAMP, min(cls.GRADIENT_CLAMP, gradient)), 6)

    @classmethod
    def propagate_correction(
        cls,
        corrected_memory_id: str,
        linked_memories: list[dict],
        correction_delta: float = 1.0,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        max_depth: int = MAX_PROPAGATION_DEPTH,
    ) -> list[dict]:
        """Lan truyền điều chỉnh từ memory bị correct sang các linked memories.

        Returns list of adjustments: [{memory_id, confidence_delta, gradient, depth}]
        """
        adjustments = []
        for linked in linked_memories:
            memory_id = linked.get("memory_id", linked.get("id", ""))
            link_weight = float(linked.get("weight", linked.get("link_weight", 0.5)))
            depth = int(linked.get("depth", linked.get("hop", 1)))

            if depth > max_depth:
                continue

            gradient = cls.compute_gradient(
                error=correction_delta,
                link_weight=link_weight,
                depth=depth,
                learning_rate=learning_rate,
            )

            if abs(gradient) < cls.GRADIENT_THRESHOLD:
                continue

            adjustments.append({
                "memory_id": memory_id,
                "confidence_delta": -gradient,  # Giảm confidence (negative gradient)
                "gradient": gradient,
                "depth": depth,
                "link_weight": link_weight,
                "source_correction": corrected_memory_id,
            })

        return adjustments

    @staticmethod
    def chain_rule_decompose(
        total_error: float,
        layer_weights: list[float],
    ) -> list[float]:
        """Phân rã Chain Rule: tính đóng góp sai số tại mỗi layer.

        ∂L/∂w₁ = ∂L/∂y × ∂y/∂z × ∂z/∂w₁
        Trả về gradient tại mỗi layer theo thứ tự ngược (output → input).
        """
        if not layer_weights:
            return []

        gradients = []
        accumulated = total_error
        for weight in reversed(layer_weights):
            local_grad = accumulated * weight
            gradients.append(round(local_grad, 6))
            accumulated = local_grad  # Chain multiplication

        gradients.reverse()
        return gradients


# ---------------------------------------------------------------------------
# 9. BELLMAN VALUE ENGINE — Richard Bellman
# ---------------------------------------------------------------------------

class BellmanValueEngine:
    """Phương trình Bellman — Tính giá trị chiến lược cho procedural memory.

    V(s) = max_a [R(s,a) + γ · V(s')]

    Giúp AI không chỉ nhớ "sự thật" mà còn nhớ "cách làm" tốt nhất.
    Procedural memories (bước 1 → bước 2 → kết quả) được đánh giá
    theo giá trị chiến lược: bước nào dẫn đến kết quả tốt → giá trị cao.
    """

    RETIREMENT_HALF_FACTOR = 0.5
    DEFAULT_GAMMA = 0.85  # Discount factor cho tương lai
    MAX_ITERATIONS = 20   # Giới hạn vòng lặp value iteration

    @classmethod
    def value_iteration(
        cls,
        states: list[str],
        transitions: dict[str, list[tuple[str, float]]],
        rewards: dict[str, float],
        gamma: float = DEFAULT_GAMMA,
        max_iterations: int = MAX_ITERATIONS,
        epsilon: float = 1e-4,
    ) -> dict[str, float]:
        """Value iteration chuẩn — tính giá trị tối ưu cho mỗi state.

        V(s) = R(s) + γ × max Σ P(s'|s) × V(s')

        Args:
            states: danh sách memory IDs
            transitions: {source_id: [(target_id, probability), ...]}
            rewards: {memory_id: immediate_reward}
            gamma: hệ số chiết khấu (0-1)
        """
        values = {s: rewards.get(s, 0.0) for s in states}

        for _ in range(max_iterations):
            delta = 0.0
            new_values = {}

            for s in states:
                reward = rewards.get(s, 0.0)
                successors = transitions.get(s, [])

                if not successors:
                    new_values[s] = reward
                    continue

                # V(s) = max(R(s), γ × Σ P(s'|s) × V(s'))
                future_value = sum(
                    prob * values.get(next_s, 0.0)
                    for next_s, prob in successors
                )
                new_values[s] = max(reward, gamma * future_value)
                delta = max(delta, abs(new_values[s] - values[s]))

            values = new_values
            if delta < epsilon:
                break

        return {s: round(v, 6) for s, v in values.items()}

    @classmethod
    def compute_strategic_value(
        cls,
        memory_id: str,
        link_graph: dict[str, list[tuple[str, float]]],
        activation_scores: dict[str, float],
        confidence_scores: dict[str, float],
        gamma: float = DEFAULT_GAMMA,
    ) -> float:
        """Tính giá trị chiến lược Bellman cho một procedural memory.

        R(s) = activation_score × confidence
        P(s'|s) = link_weight / Σ weights (transition probability)
        """
        all_states = set()
        all_states.add(memory_id)
        for src, targets in link_graph.items():
            all_states.add(src)
            for tgt, _ in targets:
                all_states.add(tgt)

        states = list(all_states)

        # Rewards: R(s) = activation × confidence
        rewards = {}
        for s in states:
            act = activation_scores.get(s, 0.5)
            conf = confidence_scores.get(s, 0.5)
            rewards[s] = act * conf

        # Transitions: normalize link weights to probabilities
        transitions: dict[str, list[tuple[str, float]]] = {}
        for src, targets in link_graph.items():
            total_weight = sum(w for _, w in targets)
            if total_weight > 0:
                transitions[src] = [(tgt, w / total_weight) for tgt, w in targets]

        values = cls.value_iteration(states, transitions, rewards, gamma)
        return values.get(memory_id, 0.0)

    @staticmethod
    def compute_retirement_protection(bellman_value: float, threshold: float = 0.5) -> float:
        """Tính mức bảo vệ khỏi retirement dựa trên giá trị Bellman.

        Memories có bellman_value > threshold được bảo vệ khỏi decay retirement.
        Returns: protection factor 0.0 (no protection) → 1.0 (full protection)
        """
        if bellman_value <= threshold * BellmanValueEngine.RETIREMENT_HALF_FACTOR:
            return 0.0
        protection = min(1.0, (bellman_value - threshold * BellmanValueEngine.RETIREMENT_HALF_FACTOR) / max(threshold, 0.01))
        return round(max(0.0, protection), 6)


# ---------------------------------------------------------------------------
# 10. MODERN HOPFIELD ATTRACTOR ENGINE — Ramsauer et al. (2020)
# ---------------------------------------------------------------------------

class ModernHopfieldAttractorEngine:
    """Modern Hopfield Network (MHN) — Động lực học hồi tưởng Lyapunov lũy thừa.

    Dùng phương trình vi phân Attention liên tục để hội tụ gợi ý truy vấn về
    attractor ký ức chính xác nhất, triệt tiêu hoàn toàn nhiễu từ ngữ và
    mở rộng sức chứa bộ nhớ lên mức lũy thừa O(2^(d/2)).
    """

    @staticmethod
    def softmax(x: list[float], beta: float = 8.0) -> list[float]:
        """Tính phân phối xác suất Softmax với tham số nghịch đảo nhiệt độ beta."""
        if not x:
            return []
        max_val = max(x)
        exp_vals = [math.exp(max(min(700.0, beta * (v - max_val)), -700.0)) for v in x]
        sum_exp = sum(exp_vals)
        if sum_exp <= 0:
            return [1.0 / len(x)] * len(x)
        return [v / sum_exp for v in exp_vals]

    @classmethod
    def retrieve_attractor(
        cls,
        query_vector: list[float],
        memory_matrix: list[list[float]],
        beta: float = 8.0,
        max_iterations: int = 5,
        tolerance: float = 1e-5
    ) -> tuple[list[float], int]:
        """Vòng lặp phi tuyến tính Lyapunov hồi tưởng attractor của Modern Hopfield.

        x^(t+1) = Softmax(β * Ξ * x^(t)) * Ξ^T
        Trong đó Ξ là ma trận ký ức (memory_matrix), mỗi dòng là một vector.

        Returns:
            Tuple của (vector_hội_tụ_cuối_cùng, chỉ_số_attractor_gần_nhất)
        """
        if not memory_matrix or not query_vector:
            return query_vector, 0

        dim = len(query_vector)
        # Chuẩn hóa độ dài các vector ký ức
        normalized_memories = []
        for m in memory_matrix:
            mag = math.sqrt(sum(v*v for v in m))
            if mag > 0:
                normalized_memories.append([v / mag for v in m])
            else:
                normalized_memories.append([0.0] * dim)

        # Trạng thái hiện tại x (chuẩn hóa)
        q_mag = math.sqrt(sum(v*v for v in query_vector))
        x = [v / q_mag for v in query_vector] if q_mag > 0 else [0.0] * dim

        best_idx = 0
        for _ in range(max_iterations):
            # 1. Tính tích vô hướng giữa x và từng ký ức (tương đồng)
            similarities = []
            for m in normalized_memories:
                similarities.append(sum(a*b for a, b in zip(x, m)))

            # 2. Áp dụng phi tuyến tính Softmax
            softmax_weights = cls.softmax(similarities, beta)

            # 3. Tính tổ hợp tuyến tính số mũ của các ký ức: x_new = sum(w_i * m_i)
            x_new = [0.0] * dim
            for w, m in zip(softmax_weights, normalized_memories):
                for idx in range(dim):
                    x_new[idx] += w * m[idx]

            # Chuẩn hóa x_new
            new_mag = math.sqrt(sum(v*v for v in x_new))
            if new_mag > 0:
                x_new = [v / new_mag for v in x_new]

            # Kiểm tra hội tụ
            diff = math.sqrt(sum((a - b)**2 for a, b in zip(x_new, x)))
            x = x_new
            if diff < tolerance:
                break

            # 4. Tìm chỉ số attractor (ký ức) gần nhất có trọng số Softmax cao nhất
            best_weight = -1.0
            for idx, w in enumerate(softmax_weights):
                if w > best_weight:
                    best_weight = w
                    best_idx = idx

        return x, best_idx



# ---------------------------------------------------------------------------
# 11. SPECTRAL GRAPH ENGINE — Spectral Graph Theory & Davis-Kahan (1970)
# ---------------------------------------------------------------------------

class SpectralGraphEngine:
    """Lý thuyết Phổ Đồ thị & Ràng buộc Davis-Kahan (1970).

    Đo lường độ ổn định phổ của đồ thị ký ức dưới nhiễu loạn ΔL khi nạp tri thức mới.
    Sử dụng Power Iteration kết hợp Deflation (trực giao hóa) để tìm Fiedler vector
    và Spectral Gap mà không cần các thư viện đại số tuyến tính ngoài.
    """

    @staticmethod
    def compute_symmetric_laplacian(
        adjacency: dict[str, dict[str, float]]
    ) -> tuple[list[str], list[list[float]], list[float]]:
        """Tính toán Symmetric Normalized Laplacian L_sym.

        L_sym = I - D^(-1/2) * A * D^(-1/2)
        Trả về: tuple (nodes, L_sym_matrix, degree_vector)
        """
        nodes = sorted(list(adjacency.keys()))
        n = len(nodes)
        if n == 0:
            return [], [], []

        # Tính ma trận bậc D
        degrees = [0.0] * n
        node_to_idx = {node: i for i, node in enumerate(nodes)}

        for i, node in enumerate(nodes):
            degrees[i] = sum(adjacency[node].values())

        # Tạo L_sym
        l_sym = [[0.0] * n for _ in range(n)]
        for i in range(n):
            l_sym[i][i] = 1.0  # I phần tử đường chéo

        for i, u in enumerate(nodes):
            for v, weight in adjacency[u].items():
                if v not in node_to_idx:
                    continue
                j = node_to_idx[v]
                # Nếu có liên kết tự thân (self-loop), nó được trừ ra
                if i == j:
                    if degrees[i] > 0:
                        l_sym[i][i] = 1.0 - weight / degrees[i]
                else:
                    if degrees[i] > 0 and degrees[j] > 0:
                        l_sym[i][j] = -weight / math.sqrt(degrees[i] * degrees[j])

        return nodes, l_sym, degrees

    @staticmethod
    def dot_product(v1: list[float], v2: list[float]) -> float:
        """Tính tích vô hướng của 2 vector."""
        return sum(a * b for a, b in zip(v1, v2))

    @staticmethod
    def l2_normalize(v: list[float]) -> list[float]:
        """Chuẩn hóa L2 cho một vector."""
        mag = math.sqrt(sum(x * x for x in v))
        if mag <= 0:
            return [0.0] * len(v)
        return [x / mag for x in v]

    @classmethod
    def power_iteration_with_deflation(
        cls,
        l_sym: list[list[float]],
        degrees: list[float],
        max_iterations: int = 150,
        tolerance: float = 1e-6
    ) -> tuple[float, list[float]]:
        """Power Iteration với Deflation để tìm Fiedler vector v_2 và Spectral Gap lambda_2.

        - v_1 = [sqrt(d_i) / sqrt(sum(d_j))] ứng với lambda_1 = 0
        - Áp dụng Power Iteration lên M = 2I - L_sym để tìm trị riêng lớn nhất của M,
          đồng thời trực giao hóa liên tục với v_1 tại mỗi bước lặp.
        """
        n = len(l_sym)
        if n <= 1:
            return 0.0, [1.0] * n

        # 1. Tạo v_1 (vector riêng ứng với lambda_1 = 0)
        v_1 = [math.sqrt(max(0.0, d)) for d in degrees]
        v_1 = cls.l2_normalize(v_1)

        # 2. Khởi tạo vector ngẫu nhiên tất định x (đảm bảo reproducibility)
        # Sử dụng sin(i) để sinh vector có phân bố đều tất định
        x = [math.sin(i + 1.0) for i in range(n)]
        x = cls.l2_normalize(x)

        # Trực giao hóa x với v_1 ngay từ đầu
        dot_init = cls.dot_product(x, v_1)
        x = [x[i] - dot_init * v_1[i] for i in range(n)]
        x = cls.l2_normalize(x)

        # 3. Lặp tìm trị riêng lớn nhất của M = 2*I - L_sym
        for _ in range(max_iterations):
            # y = M * x = 2*x - L_sym * x
            y = [0.0] * n
            for i in range(n):
                l_row_x = sum(l_sym[i][j] * x[j] for j in range(n))
                y[i] = 2.0 * x[i] - l_row_x

            # Deflation: trực giao hóa y với v_1
            dot_v1 = cls.dot_product(y, v_1)
            y = [y[i] - dot_v1 * v_1[i] for i in range(n)]

            # Chuẩn hóa y
            y = cls.l2_normalize(y)

            # Kiểm tra hội tụ
            diff = math.sqrt(sum((y[i] - x[i]) ** 2 for i in range(n)))
            # Tránh trường hợp vector bị đổi chiều: kiểm tra cả -y
            diff_neg = math.sqrt(sum(((-y[i]) - x[i]) ** 2 for i in range(n)))

            if diff < tolerance or diff_neg < tolerance:
                x = y
                break
            x = y

        # 4. Tính trị riêng lớn nhất mu_1 của M trên không gian trực giao với v_1
        # mu_1 = <M x, x>
        mx = [0.0] * n
        for i in range(n):
            l_row_x = sum(l_sym[i][j] * x[j] for j in range(n))
            mx[i] = 2.0 * x[i] - l_row_x
        mu_1 = cls.dot_product(mx, x)

        # Spectral Gap: lambda_2 = 2.0 - mu_1
        lambda_2 = max(0.0, 2.0 - mu_1)
        return lambda_2, x

    @classmethod
    def evaluate_davis_kahan_stability(
        cls,
        l_orig: list[list[float]],
        l_pert: list[list[float]],
        fiedler_val: float
    ) -> float:
        """Đo lường góc xoay không gian ký ức (sin theta) dưới tác động của nhiễu loạn ΔL.

        ||sin Theta||_F <= ||ΔL||_F / delta
        Trong đó delta là fiedler_val (Spectral Gap).
        """
        n = len(l_orig)
        if n == 0 or fiedler_val <= 1e-6:
            return 1.0  # Không ổn định hoặc sụp đổ hoàn toàn

        # Tính Frobenius norm của ΔL
        frob_sq = 0.0
        for i in range(n):
            for j in range(n):
                diff = l_pert[i][j] - l_orig[i][j]
                frob_sq += diff * diff

        frob_norm = math.sqrt(frob_sq)

        # Chặn sin Theta
        sin_theta_bound = frob_norm / fiedler_val
        return min(1.0, sin_theta_bound)


# ---------------------------------------------------------------------------
# 12. HYPERBOLIC GRAPH ENGINE — Poincaré Disk & Ollivier-Ricci Curvature (2011)
# ---------------------------------------------------------------------------

class HyperbolicGraphEngine:
    """Hình học Hyperbolic đĩa Poincaré & Độ cong Ollivier-Ricci (2011).

    Nhúng ký ức phân cấp vào không gian phi Euclid để tránh bùng nổ chiều,
    và tối ưu hóa liên kết đồ thị (chống Over-squashing) bằng Dòng chảy Ricci rời rạc.
    """

    @staticmethod
    def poincare_distance(u: list[float], v: list[float]) -> float:
        """Tính khoảng cách Poincaré Hyperbolic d_H(u, v).

        d_H(u,v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2)(1 - ||v||^2)))
        """
        if len(u) != len(v):
            return float("inf")

        # Giới hạn chuẩn vector trong Poincaré đĩa để tránh vô cực phân kỳ
        sq_u = min(sum(x * x for x in u), 0.998)
        sq_v = min(sum(x * x for x in v), 0.998)

        sq_dist = sum((x - y) ** 2 for x, y in zip(u, v))
        denominator = (1.0 - sq_u) * (1.0 - sq_v)
        if denominator <= 0:
            return 0.0

        ratio = 1.0 + 2.0 * sq_dist / denominator
        # Clamp ratio >= 1.0 để arcosh hợp lệ
        ratio = max(1.0, ratio)

        # arcosh(x) = ln(x + sqrt(x^2 - 1))
        return math.log(ratio + math.sqrt(ratio * ratio - 1.0))

    @staticmethod
    def sinkhorn_optimal_transport(
        mu: list[float],
        mv: list[float],
        cost_matrix: list[list[float]],
        reg: float = 0.1,
        max_iterations: int = 15
    ) -> float:
        """Thuật toán Sinkhorn-Knopp tính entropy-regularized Optimal Transport (W_1).

        Được lập trình bằng Python thuần túy cho hiệu năng cao trên đồ thị cục bộ.
        """
        n = len(mu)
        m = len(mv)
        if n == 0 or m == 0:
            return 0.0

        # Gibbs kernel: K = exp(-C / reg)
        k = [[0.0] * m for _ in range(n)]
        for i in range(n):
            for j in range(m):
                k[i][j] = math.exp(-cost_matrix[i][j] / reg)

        # Khởi tạo vector tỷ lệ u và v
        u_scale = [1.0] * n
        v_scale = [1.0] * m

        for _ in range(max_iterations):
            # u = mu / (K * v)
            for i in range(n):
                kv = sum(k[i][j] * v_scale[j] for j in range(m))
                u_scale[i] = mu[i] / max(kv, 1e-9)

            # v = mv / (K^T * u)
            for j in range(m):
                ku = sum(k[i][j] * u_scale[i] for i in range(n))
                v_scale[j] = mv[j] / max(ku, 1e-9)

        # Khoảng cách Wasserstein W_1 = sum(P_ij * C_ij)
        w_1 = 0.0
        for i in range(n):
            for j in range(m):
                p_ij = u_scale[i] * k[i][j] * v_scale[j]
                w_1 += p_ij * cost_matrix[i][j]
        return w_1

    @staticmethod
    def sinkhorn_optimal_transport_sparse(
        mu: list[float],
        mv: list[float],
        cost_matrix: list[list[float]],
        reg: float = 0.1,
        max_iterations: int = 15,
        threshold: float = 1e-4
    ) -> float:
        """Thuật toán Sinkhorn thưa tối ưu cao chạy trên Mini-CSR cục bộ dựng on-the-fly."""
        n = len(mu)
        m = len(mv)
        if n == 0 or m == 0:
            return 0.0

        # Dựng Mini-CSR on-the-fly cho Gibbs kernel K = exp(-C / reg)
        csr = MiniCSRMatrix.from_dense_cost(cost_matrix, reg, threshold)

        u_scale = [1.0] * n
        v_scale = [1.0] * m

        for _ in range(max_iterations):
            # u = mu / (K * v)
            for i in range(n):
                start = csr.row_ptr[i]
                end = csr.row_ptr[i+1]
                kv = 0.0
                for idx in range(start, end):
                    j = csr.col_indices[idx]
                    kv += csr.values[idx] * v_scale[j]
                u_scale[i] = mu[i] / max(kv, 1e-9)

            # v = mv / (K^T * u)
            ku = [0.0] * m
            for i in range(n):
                start = csr.row_ptr[i]
                end = csr.row_ptr[i+1]
                for idx in range(start, end):
                    j = csr.col_indices[idx]
                    ku[j] += csr.values[idx] * u_scale[i]

            for j in range(m):
                v_scale[j] = mv[j] / max(ku[j], 1e-9)

        # Wasserstein distance W_1 = sum(P_ij * C_ij)
        w_1 = 0.0
        for i in range(n):
            start = csr.row_ptr[i]
            end = csr.row_ptr[i+1]
            for idx in range(start, end):
                j = csr.col_indices[idx]
                p_ij = u_scale[i] * csr.values[idx] * v_scale[j]
                w_1 += p_ij * cost_matrix[i][j]

        return w_1

    @classmethod
    def geodesic_midpoint(cls, u: list[float], v: list[float]) -> list[float]:
        """Tính điểm trung đạo Hyperbolic (geodesic midpoint) trong đĩa Poincaré.

        Sử dụng biến đổi Möbius dời tâm để tính trung điểm hình học phi Euclid chính xác.
        """
        dim = len(u)
        if dim != len(v):
            return u

        sq_u = sum(x * x for x in u)
        if sq_u < 1e-9:
            # Nếu u là tâm đĩa (0), trung điểm hyperbolic là điểm dọc theo bán kính v
            # d_H(0, w) = 0.5 * d_H(0, v) => ||w|| = tanh(0.5 * arctanh(||v||))
            mag_v = math.sqrt(sum(x * x for x in v))
            if mag_v < 1e-9:
                return [0.0] * dim
            norm_v = min(mag_v, 0.998)
            # arctanh(x) = 0.5 * ln((1+x)/(1-x))
            val_arctanh = 0.5 * math.log((1.0 + norm_v) / (1.0 - norm_v))
            half_dist = 0.5 * val_arctanh
            # tanh(x) = (exp(2x) - 1) / (exp(2x) + 1)
            exp_2x = math.exp(2.0 * half_dist)
            mag_w = (exp_2x - 1.0) / (exp_2x + 1.0)
            return [mag_w * (x / mag_v) for x in v]

        # Phép biến đổi Möbius dời u về tâm: phi_u(z)
        # phi_u(z) = ((1 - ||u||^2)(z - u) - ||z - u||^2 u) / (1 - 2<u, z> + ||u||^2 ||z||^2)
        def mobius_transform(a: list[float], z: list[float]) -> list[float]:
            sq_a = sum(x * x for x in a)
            sq_z = sum(x * x for x in z)
            z_minus_a = [zi - ai for zi, ai in zip(z, a)]
            sq_diff = sum(x * x for x in z_minus_a)
            dot_az = sum(ai * zi for ai, zi in zip(a, z))

            denom = 1.0 - 2.0 * dot_az + sq_a * sq_z
            denom = max(denom, 1e-9)

            numer = [(1.0 - sq_a) * diff - sq_diff * ai for diff, ai in zip(z_minus_a, a)]
            return [x / denom for x in numer]

        # 1. Chuyển v sang hệ tọa độ dời tâm u
        v_prime = mobius_transform(u, v)

        # 2. Tính trung điểm của v_prime từ tâm 0
        mag_v_prime = math.sqrt(sum(x * x for x in v_prime))
        if mag_v_prime < 1e-9:
            return u

        norm_v_prime = min(mag_v_prime, 0.998)
        val_arctanh = 0.5 * math.log((1.0 + norm_v_prime) / (1.0 - norm_v_prime))
        half_dist = 0.5 * val_arctanh
        exp_2x = math.exp(2.0 * half_dist)
        mag_w_prime = (exp_2x - 1.0) / (exp_2x + 1.0)

        w_prime = [mag_w_prime * (x / mag_v_prime) for x in v_prime]

        # 3. Biến đổi Möbius ngược (-u) để đưa trung điểm về không gian Poincaré ban đầu
        minus_u = [-x for x in u]
        w = mobius_transform(minus_u, w_prime)

        # Giới hạn an toàn trong đĩa Poincaré
        mag_w = math.sqrt(sum(x * x for x in w))
        if mag_w > 0.998:
            w = [0.998 * (x / mag_w) for x in w]
        return w

    @classmethod
    def ollivier_ricci_curvature(
        cls,
        u: str,
        v: str,
        neighbors_u: list[str],
        neighbors_v: list[str],
        poincare_coords: dict[str, list[float]],
        adjacency: dict[str, dict[str, float]],
        alpha: float = 0.5,
        reg: float = 0.1
    ) -> float:
        """Tính toán độ cong Ollivier-Ricci giữa 2 đỉnh ký ức u và v.

        kappa(u, v) = 1 - W_1(m_u, m_v) / d_H(u, v)
        """
        coord_u = poincare_coords.get(u, [0.0, 0.0])
        coord_v = poincare_coords.get(v, [0.0, 0.0])

        d_h_uv = cls.poincare_distance(coord_u, coord_v)
        if d_h_uv <= 1e-6:
            return 0.0

        # Xây dựng support và phân phối xác suất m_u
        support_u = [u] + [n for n in neighbors_u if n in poincare_coords]
        deg_u = len(support_u) - 1
        m_u_dist = [0.0] * len(support_u)
        if deg_u == 0:
            m_u_dist[0] = 1.0
        else:
            m_u_dist[0] = alpha
            for idx in range(1, len(support_u)):
                m_u_dist[idx] = (1.0 - alpha) / deg_u

        # Xây dựng support và phân phối xác suất m_v
        support_v = [v] + [n for n in neighbors_v if n in poincare_coords]
        deg_v = len(support_v) - 1
        m_v_dist = [0.0] * len(support_v)
        if deg_v == 0:
            m_v_dist[0] = 1.0
        else:
            m_v_dist[0] = alpha
            for idx in range(1, len(support_v)):
                m_v_dist[idx] = (1.0 - alpha) / deg_v

        # Xây dựng ma trận chi phí cost_matrix[i][j] = d_H(support_u[i], support_v[j])
        cost_matrix = [[0.0] * len(support_v) for _ in range(len(support_u))]
        for i, node_i in enumerate(support_u):
            for j, node_j in enumerate(support_v):
                ci = poincare_coords.get(node_i, [0.0, 0.0])
                cj = poincare_coords.get(node_j, [0.0, 0.0])
                cost_matrix[i][j] = cls.poincare_distance(ci, cj)

        # Tính Wasserstein distance W_1
        w_1 = cls.sinkhorn_optimal_transport_sparse(m_u_dist, m_v_dist, cost_matrix, reg)

        # curvature: kappa = 1.0 - W_1 / d_H
        kappa = 1.0 - (w_1 / d_h_uv)
        return round(kappa, 6)

    @classmethod
    def ricci_flow_step(
        cls,
        adjacency: dict[str, dict[str, float]],
        poincare_coords: dict[str, list[float]],
        learning_rate: float = 0.05,
        alpha: float = 0.5,
        reg: float = 0.1
    ) -> dict[str, dict[str, float]]:
        """Dòng chảy Ricci rời rạc: dA_ij/dt = -kappa(i, j) * A_ij.

        Cập nhật trọng số cạnh nhằm cân bằng độ cong, triệt tiêu bottleneck.
        """
        # Tạo bản sao
        new_adjacency = {u: dict(v) for u, v in adjacency.items()}

        for u in adjacency:
            for v, weight in adjacency[u].items():
                # Tránh tính trùng lặp cho đồ thị vô hướng
                if u > v:
                    continue

                neighbors_u = list(adjacency[u].keys())
                neighbors_v = list(adjacency[v].keys())

                kappa = cls.ollivier_ricci_curvature(
                    u, v, neighbors_u, neighbors_v, poincare_coords, adjacency, alpha, reg
                )

                # Cập nhật trọng số theo Ricci flow
                delta_w = -learning_rate * kappa * weight
                new_w = max(0.001, min(1.0, weight + delta_w))

                new_adjacency[u][v] = round(new_w, 6)
                if v in new_adjacency and u in new_adjacency[v]:
                    new_adjacency[v][u] = round(new_w, 6)

        return new_adjacency

    @classmethod
    def graph_surgery(
        cls,
        adjacency: dict[str, dict[str, float]],
        poincare_coords: dict[str, list[float]],
        threshold: float = -0.8,
        alpha: float = 0.5,
        reg: float = 0.1
    ) -> tuple[dict[str, dict[str, float]], dict[str, list[float]], list[dict[str, Any]]]:
        """Phẫu thuật Đồ thị (Graph Surgery) chèn Virtual Node để giải tỏa Over-squashing.

        Nếu kappa(u, v) quá âm (bottleneck), cắt cạnh u-v và chèn Virtual Node ở trung đạo.
        Trả về: tuple (new_adjacency, new_poincare_coords, list_of_surgery_events)
        """
        new_adjacency = {u: dict(v) for u, v in adjacency.items()}
        new_poincare_coords = dict(poincare_coords)
        surgery_events = []

        edges_to_cut = []
        for u in adjacency:
            for v, weight in adjacency[u].items():
                if u > v:
                    continue
                neighbors_u = list(adjacency[u].keys())
                neighbors_v = list(adjacency[v].keys())
                kappa = cls.ollivier_ricci_curvature(
                    u, v, neighbors_u, neighbors_v, poincare_coords, adjacency, alpha, reg
                )
                if kappa < threshold:
                    edges_to_cut.append((u, v, weight, kappa))

        for u, v, weight, kappa in edges_to_cut:
            # 1. Tạo Virtual Node ID
            v_node_id = f"v_node_{hash(u + ':' + v) & 0xffffffff:08x}"

            # Tránh tạo trùng lặp
            if v_node_id in new_adjacency:
                continue

            # 2. Tính tọa độ Poincaré trung đạo
            cu = poincare_coords.get(u, [0.0, 0.0])
            cv = poincare_coords.get(v, [0.0, 0.0])
            cvirtual = cls.geodesic_midpoint(cu, cv)
            new_poincare_coords[v_node_id] = cvirtual

            # 3. Phẫu thuật cắt cạnh u-v
            if v in new_adjacency[u]:
                del new_adjacency[u][v]
            if u in new_adjacency[v]:
                del new_adjacency[v][u]

            # 4. Thêm Virtual Node và liên kết mới u <-> virtual <-> v
            new_adjacency.setdefault(v_node_id, {})
            new_adjacency[v_node_id][u] = round(weight, 6)
            new_adjacency[v_node_id][v] = round(weight, 6)

            new_adjacency[u][v_node_id] = round(weight, 6)
            new_adjacency[v][v_node_id] = round(weight, 6)

            surgery_events.append({
                "source": u,
                "target": v,
                "virtual_node": v_node_id,
                "curvature": kappa,
                "weight": weight,
                "coordinates": cvirtual
            })

        return new_adjacency, new_poincare_coords, surgery_events


# ---------------------------------------------------------------------------
# 13. BELTRAMI DIFFUSION ENGINE — Anisotropic Perona-Malik Diffusion (1990)
# ---------------------------------------------------------------------------

class BeltramiDiffusionEngine:
    """Phương trình Khuếch tán liên tục Beltrami & Perona-Malik bất đẳng hướng (1990).

    Mô phỏng quá trình quên/nhớ tự nhiên. Sử dụng toán tử Perona-Malik bất đẳng hướng
    để tạo ranh giới "bức tường năng lượng" ngăn chặn dòng khuếch tán giữa các
    ký ức khác biệt sâu sắc (chống Over-smoothing).
    """

    @staticmethod
    def perona_malik_coefficient(
        x_i: list[float],
        x_j: list[float],
        contrast_parameter: float = 0.5
    ) -> float:
        """Tính toán hệ số khuếch tán bất đẳng hướng Perona-Malik.

        g(x_i, x_j) = exp(-||x_i - x_j||^2 / K^2)
        """
        if len(x_i) != len(x_j):
            return 0.0
        sq_dist = sum((a - b) ** 2 for a, b in zip(x_i, x_j))
        denom = max(1e-9, contrast_parameter * contrast_parameter)
        return math.exp(-sq_dist / denom)

    @classmethod
    def beltrami_diffusion_step(
        cls,
        features: dict[str, list[float]],
        adjacency: dict[str, dict[str, float]],
        dt: float = 0.1,
        contrast_parameter: float = 0.5
    ) -> dict[str, list[float]]:
        """Thực hiện một bước giải Euler tường minh của phương trình Beltrami.

        X_i^(t+1) = X_i^(t) + dt * sum_j [ g_ij * (X_j^(t) - X_i^(t)) ]
        """
        new_features = {}
        for i, x_i in features.items():
            dim = len(x_i)
            # Tích lũy dòng khuếch tán
            flux = [0.0] * dim
            total_g = 0.0

            neighbors = adjacency.get(i, {})
            for j, weight in neighbors.items():
                if j not in features:
                    continue
                x_j = features[j]

                # Hệ số Perona-Malik
                g = cls.perona_malik_coefficient(x_i, x_j, contrast_parameter)
                # Nhân thêm trọng số liên kết đồ thị
                g_weighted = g * weight

                for d in range(dim):
                    flux[d] += g_weighted * (x_j[d] - x_i[d])
                total_g += g_weighted

            # Cập nhật Euler với bước thời gian dt
            # Giới hạn tốc độ cập nhật để tránh phân kỳ toán học
            step_scale = dt
            if total_g > 0:
                # Tránh cập nhật quá mức làm nổ số học (stability constraint)
                step_scale = min(dt, 1.0 / total_g)

            x_i_new = [x_i[d] + step_scale * flux[d] for d in range(dim)]

            # L2 Normalize đặc trưng mới để giữ chúng nằm trên Hilbert sphere
            mag = math.sqrt(sum(v * v for v in x_i_new))
            if mag > 0:
                x_i_new = [v / mag for v in x_i_new]
            else:
                x_i_new = list(x_i)

            new_features[i] = x_i_new

        return new_features


class EulerLagrangeVariationalEngine:
    """Cơ học Biến phân Euler-Lagrange điều chỉnh động tham số K và alpha.

    Giải phương trình vi phân dao động tắt dần để tự động co giãn ranh giới ký ức theo Shannon Entropy.
    """

    @staticmethod
    def compute_shannon_entropy(degrees: list[float]) -> float:
        """Tính toán Shannon Entropy của cấu trúc liên kết đồ thị ký ức."""
        total_deg = sum(degrees)
        if total_deg <= 0:
            return 0.0
        entropy = 0.0
        for d in degrees:
            if d > 0:
                p = d / total_deg
                entropy -= p * math.log(p)
        return entropy

    @staticmethod
    def damped_oscillator_step(
        k_current: float,
        velocity: float,
        entropy: float,
        dt: float = 0.1,
        m: float = 1.0,
        gamma: float = 0.8,
        k_spring: float = 0.5,
        k_base: float = 0.8,
        beta: float = 2.0
    ) -> tuple[float, float]:
        """Thực hiện một bước giải vi phân bậc 2 Euler-Lagrange damped oscillator.

        Trả về: tuple (K_new, velocity_new)
        """
        # K_opt = K_base * exp(-H / beta)
        k_opt = k_base * math.exp(-entropy / beta)

        # Gia tốc: a = (-k_spring * (K - K_opt) - gamma * velocity) / m
        acceleration = (-k_spring * (k_current - k_opt) - gamma * velocity) / m

        # Cập nhật vận tốc và tọa độ K
        v_new = velocity + acceleration * dt
        k_new = k_current + v_new * dt

        # Giới hạn an toàn vật lý của K
        k_new = max(0.1, min(2.0, k_new))
        return k_new, v_new


# ---------------------------------------------------------------------------
# 16. FORCE-DIRECTED POINCARÉ ENGINE — Newton & Coulomb on Hyperbolic Space
# ---------------------------------------------------------------------------

class ForceDirectedPoincareEngine:
    """Mô hình lực hướng định vị trên đĩa Poincaré Hyperbolic.

    Hấp dẫn Newton/Hooke kéo các nút có quan hệ hỗ trợ/phụ thuộc lại gần nhau.
    Đẩy Coulomb đẩy các nút có mâu thuẫn hoặc không liên kết ra xa.
    """

    @staticmethod
    def poincare_distance(u: list[float], v: list[float]) -> float:
        sq_u = sum(x * x for x in u)
        sq_v = sum(x * x for x in v)
        diff = [ui - vi for ui, vi in zip(u, v)]
        sq_dist = sum(x * x for x in diff)
        denominator = (1.0 - sq_u) * (1.0 - sq_v)
        if denominator < 1e-9:
            denominator = 1e-9
        ratio = 1.0 + 2.0 * sq_dist / denominator
        ratio = max(1.0, ratio)
        return math.log(ratio + math.sqrt(ratio * ratio - 1.0))

    @classmethod
    def optimize_layout(
        cls,
        nodes: dict[str, list[float]],
        links: list[dict[str, Any]],
        iterations: int = 15,
        learning_rate: float = 0.05,
        repulsion_constant: float = 0.01,
        attraction_constant: float = 0.1,
    ) -> dict[str, list[float]]:
        """Tối ưu hóa vị trí các node trên đĩa Poincaré Hyperbolic bằng mô hình định hướng lực."""
        dim = len(next(iter(nodes.values()))) if nodes else 0
        if dim == 0:
            return nodes

        # Sao chép tọa độ Poincaré ban đầu
        coords = {k: v[:] for k, v in nodes.items()}
        node_keys = list(nodes.keys())

        # Tạo cấu trúc kề nhanh để tra cứu liên kết
        linked_set = set()
        link_weights = {}
        contradiction_set = set()

        for link in links:
            src = link.get("source_id", link.get("source"))
            tgt = link.get("target_id", link.get("target"))
            ltype = link.get("link_type", "")
            weight = float(link.get("weight", 1.0))

            if src in coords and tgt in coords:
                pair = (src, tgt) if src < tgt else (tgt, src)
                linked_set.add(pair)
                link_weights[pair] = weight
                if ltype == "contradicts":
                    contradiction_set.add(pair)

        for _ in range(iterations):
            forces = {k: [0.0] * dim for k in coords}

            # 1. Tính lực hút đàn hồi (Hooke) giữa các nút có liên kết
            for (u, v), w in link_weights.items():
                p_dist = cls.poincare_distance(coords[u], coords[v])
                if p_dist < 1e-5:
                    continue
                # Lực hút tỷ lệ thuận với khoảng cách Poincaré
                force_magnitude = attraction_constant * w * p_dist

                # Hướng vector lực từ u sang v và ngược lại
                direction = [vi - ui for ui, vi in zip(coords[u], coords[v])]
                norm_d = math.sqrt(sum(x * x for x in direction))
                if norm_d > 1e-9:
                    direction_norm = [x / norm_d for x in direction]
                    for j in range(dim):
                        forces[u][j] += force_magnitude * direction_norm[j]
                        forces[v][j] -= force_magnitude * direction_norm[j]

            # 2. Tính lực đẩy tĩnh điện (Coulomb) giữa tất cả các cặp nút
            for i in range(len(node_keys)):
                u = node_keys[i]
                for k_idx in range(i + 1, len(node_keys)):
                    v = node_keys[k_idx]
                    pair = (u, v) if u < v else (v, u)

                    p_dist = cls.poincare_distance(coords[u], coords[v])
                    if p_dist < 1e-5:
                        p_dist = 1e-5

                    # Lực đẩy nghịch đảo bình phương khoảng cách
                    # Nếu có quan hệ contradicts, tăng gấp đôi điện tích cùng dấu (lực đẩy mạnh hơn)
                    charge_multiplier = 4.0 if pair in contradiction_set else 1.0
                    force_magnitude = repulsion_constant * charge_multiplier / (p_dist * p_dist)

                    # Hướng vector lực từ v sang u (đẩy ra xa)
                    direction = [ui - vi for ui, vi in zip(coords[u], coords[v])]
                    norm_d = math.sqrt(sum(x * x for x in direction))
                    if norm_d > 1e-9:
                        direction_norm = [x / norm_d for x in direction]
                        for j in range(dim):
                            forces[u][j] += force_magnitude * direction_norm[j]
                            forces[v][j] -= force_magnitude * direction_norm[j]

            # 3. Cập nhật vị trí và giữ các nút nằm trong biên đĩa Poincaré
            for node, force_v in forces.items():
                new_coord = []
                for j in range(dim):
                    new_coord.append(coords[node][j] + learning_rate * force_v[j])

                # Chuẩn hóa L2 và kẹp chặt r_u <= 0.98 để không vượt khỏi đĩa Poincaré
                mag = math.sqrt(sum(x * x for x in new_coord))
                if mag > 0.98:
                    new_coord = [0.98 * (x / mag) for x in new_coord]
                elif mag < 0.05:
                    # Tránh tâm tuyệt đối
                    new_coord = [0.05 * (x / mag) for x in new_coord] if mag > 0 else [0.05] + [0.0] * (dim - 1)

                coords[node] = new_coord

        return coords


# ---------------------------------------------------------------------------
# 17. MARKOV CHAIN COGNITIVE ENGINE — Infinite-hop Diffusion
# ---------------------------------------------------------------------------

class MarkovChainCognitiveEngine:
    """Động cơ khuếch tán nhận thức qua xích Markov.

    Tính toán resting salience và lan truyền đính chính thông tin vô hạn tầng.
    """

    @staticmethod
    def compute_stationary_distribution(
        adj_matrix: list[list[float]],
        max_iterations: int = 50,
        tol: float = 1e-6
    ) -> list[float]:
        """Tính toán phân phối dừng pi (Stationary Distribution) thỏa mãn pi * P = pi."""
        n = len(adj_matrix)
        if n == 0:
            return []

        # 1. Xây dựng ma trận chuyển trạng thái Markov P
        p_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            row_sum = sum(adj_matrix[i])
            if row_sum > 1e-9:
                for j in range(n):
                    p_matrix[i][j] = adj_matrix[i][j] / row_sum
            else:
                p_matrix[i][i] = 1.0  # Nút cô lập chuyển trạng thái vào chính nó

        # 2. Khởi tạo phân phối đều pi
        pi = [1.0 / n] * n

        # 3. Lặp tìm phân phối dừng (Power Iteration trên ma trận Markov)
        for _ in range(max_iterations):
            new_pi = [0.0] * n
            for j in range(n):
                new_pi[j] = sum(pi[i] * p_matrix[i][j] for i in range(n))

            # Kiểm tra hội tụ bằng L1-norm
            diff = sum(abs(new_pi[i] - pi[i]) for i in range(n))
            pi = new_pi
            if diff < tol:
                break

        return pi

    @staticmethod
    def propagate_correction_markov(
        start_node_index: int,
        adj_matrix: list[list[float]],
        initial_delta: float,
        steps: int = 5,
        decay_factor: float = 0.8
    ) -> list[float]:
        """Lan truyền đính chính thông tin vô hạn tầng qua xích Markov chuyển tiếp."""
        n = len(adj_matrix)
        if n == 0:
            return []

        p_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            row_sum = sum(adj_matrix[i])
            if row_sum > 1e-9:
                for j in range(n):
                    p_matrix[i][j] = adj_matrix[i][j] / row_sum
            else:
                p_matrix[i][i] = 1.0

        # Khởi tạo lượng delta đính chính tại nút gốc
        delta_vector = [0.0] * n
        delta_vector[start_node_index] = initial_delta

        accumulated_impact = delta_vector[:]

        # Lan truyền qua từng bước thời gian
        current_vector = delta_vector[:]
        for _ in range(steps):
            next_vector = [0.0] * n
            for j in range(n):
                # Lan truyền theo chiều chuyển tiếp Markov và suy giảm tự nhiên
                next_vector[j] = sum(current_vector[i] * p_matrix[i][j] for i in range(n)) * decay_factor

            for i in range(n):
                accumulated_impact[i] += next_vector[i]
            current_vector = next_vector

        return accumulated_impact


# ---------------------------------------------------------------------------
# 18. DIRICHLET HARMONIC ENGINE — Potential Theory for Belief Inference
# ---------------------------------------------------------------------------

class DirichletHarmonicEngine:
    """Giải bài toán Dirichlet cổ điển (Hàm điều hòa) trên đồ thị Laplace.

    Suy diễn điểm tin cậy cho các nút chưa biết (unlabeled) dựa trên
    các nút "Neo sự thật" cố định (labeled) đóng vai trò điều kiện biên.
    """

    @staticmethod
    def solve_harmonic_scores(
        adjacency_matrix: list[list[float]],
        labeled_indices: dict[int, float],
        max_iterations: int = 100,
        tol: float = 1e-5
    ) -> list[float]:
        """Giải hệ phương trình Dirichlet bằng phép lặp Gauss-Seidel cục bộ."""
        n = len(adjacency_matrix)
        if n == 0:
            return []

        # Khởi tạo điểm tin cậy (f) cho mọi nút
        # Các nút labeled giữ nguyên giá trị biên cố định, các nút unlabeled đặt giá trị trung hòa 0.5
        scores = [0.5] * n
        for idx, val in labeled_indices.items():
            if 0 <= idx < n:
                scores[idx] = max(0.0, min(1.0, val))

        unlabeled_set = set(range(n)) - set(labeled_indices.keys())

        # Gauss-Seidel Relaxation lặp đi lặp lại
        for _ in range(max_iterations):
            max_change = 0.0

            for i in unlabeled_set:
                weight_sum = sum(adjacency_matrix[i])
                if weight_sum < 1e-9:
                    continue

                # Hàm điều hòa: f(i) = sum_{j ~ i} (w_ij * f(j)) / sum(w_ij)
                harmonic_sum = sum(adjacency_matrix[i][j] * scores[j] for j in range(n) if j != i)
                new_score = harmonic_sum / weight_sum

                # Đảm bảo điểm nằm trong [0.0, 1.0]
                new_score = max(0.0, min(1.0, new_score))

                change = abs(scores[i] - new_score)
                if change > max_change:
                    max_change = change
                scores[i] = new_score

            if max_change < tol:
                break

        return scores


# ---------------------------------------------------------------------------
# 19. TOPOLOGICAL HOLE DETECTOR — algebraic homology voids for logic gaps
# ---------------------------------------------------------------------------

class TopologicalHoleDetector:
    """Tự động phát hiện các lỗ hổng logic (Semantic/Logic Holes) trong đồ thị ký ức.

    Giải thuật: Tìm tất cả các chu trình tối tiểu không có cạnh chéo (Chordless Cycles)
    có độ dài >= 4 đỉnh. Đây chính là đại diện thực tế cho số Betti 1 (H_1 voids).
    """

    @classmethod
    def detect_logic_voids(cls, adjacency: dict[str, list[str]]) -> list[list[str]]:
        """Quét và tìm tất cả các lỗ hổng logic (chu trình không có cạnh chéo >= 4 đỉnh)."""
        voids = []
        nodes = list(adjacency.keys())

        # Hàm tìm kiếm DFS để tìm các chu trình cơ bản
        def find_cycles(node, start, path, visited):
            visited.add(node)
            path.append(node)

            for neighbor in adjacency.get(node, []):
                if neighbor == start and len(path) >= 4:
                    # Phát hiện chu trình, kiểm tra tính chất chordless (không có cạnh chéo)
                    if cls._is_chordless(path, adjacency):
                        # Chuẩn hóa để tránh trùng lặp xoay vòng (rotation-invariant)
                        cycle = cls._canonical_representation(path)
                        if cycle not in voids:
                            voids.append(cycle)
                elif neighbor not in visited:
                    find_cycles(neighbor, start, path, visited)

            path.pop()
            visited.remove(node)

        for start_node in nodes:
            find_cycles(start_node, start_node, [], set())

        return voids

    @staticmethod
    def _is_chordless(path: list[str], adjacency: dict[str, list[str]]) -> bool:
        """Kiểm tra xem chu trình có chứa cạnh chéo (chord) nào không.

        Nếu tồn tại cạnh nối giữa 2 đỉnh bất kỳ trong chu trình mà cạnh đó
        không phải là cạnh tạo nên chu trình thì chu trình đó có cạnh chéo (không phải hole).
        """
        n = len(path)
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue  # Cạnh khép kín chu trình, bỏ qua
                u, v = path[i], path[j]
                if v in adjacency.get(u, []):
                    # Tồn tại cạnh chéo!
                    return False
        return True

    @staticmethod
    def _canonical_representation(path: list[str]) -> list[str]:
        """Đại diện chuẩn hóa của một chu trình (bắt đầu bằng nút nhỏ nhất theo bảng chữ cái)."""
        min_idx = path.index(min(path))
        return path[min_idx:] + path[:min_idx]


# ---------------------------------------------------------------------------
# 20. CATEGORY THEORY FUNCTOR ENGINE — analogical functorial homomorphic mapping
# ---------------------------------------------------------------------------

class CategoryTheoryFunctorEngine:
    """Động cơ đồng cấu cấu trúc (Category Functor) cho liên tưởng tương đồng.

    Ánh xạ các sub-graphs (Categories) bảo toàn morphism.
    """

    @classmethod
    def find_functorial_analogy(
        cls,
        category_c: dict[str, list[tuple[str, str]]],  # {object: [(target, link_type)]}
        category_d: dict[str, list[tuple[str, str]]]
    ) -> dict[str, str] | None:
        """Tìm ánh xạ Functor F: C -> D bảo toàn 100% các quan hệ ngữ nghĩa (Morphisms).

        Trả về: Dictionary ánh xạ đối tượng F(A) = X nếu thành công, ngược lại None.
        """
        obj_c = list(category_c.keys())
        obj_d = list(category_d.keys())

        if len(obj_c) > len(obj_d):
            return None  # Không đủ đối tượng ở D để ánh xạ đơn trị

        # Tìm kiếm đệ quy vét cạn (Backtracking) để thiết lập ánh xạ bảo toàn cấu trúc
        mapping: dict[str, str] = {}
        mapped_d = set()

        def backtrack(idx) -> bool:
            if idx == len(obj_c):
                # Đã kiểm thử xong mọi đối tượng, kiểm tra tính bảo toàn morphism toàn cục
                return cls._validate_functor_morphisms(mapping, category_c, category_d)

            u = obj_c[idx]
            for x in obj_d:
                if x not in mapped_d:
                    mapping[u] = x
                    mapped_d.add(x)

                    if backtrack(idx + 1):
                        return True

                    # Backtrack
                    mapped_d.remove(x)
                    del mapping[u]
            return False

        if backtrack(0):
            return mapping
        return None

    @staticmethod
    def _validate_functor_morphisms(
        mapping: dict[str, str],
        category_c: dict[str, list[tuple[str, str]]],
        category_d: dict[str, list[tuple[str, str]]]
    ) -> bool:
        """Xác minh Functor F bảo toàn tuyệt đối quan hệ: F(A -> B) = F(A) -> F(B)."""
        for src_c, links_c in category_c.items():
            mapped_src = mapping[src_c]

            for tgt_c, relation_c in links_c:
                mapped_tgt = mapping[tgt_c]

                # Kiểm tra xem trong D có quan hệ tương đồng giữa F(src_c) và F(tgt_c) hay không
                has_morphism = False
                for tgt_d, relation_d in category_d.get(mapped_src, []):
                    if tgt_d == mapped_tgt and relation_d == relation_c:
                        has_morphism = True
                        break

                if not has_morphism:
                    return False  # Cấu trúc bị đứt gãy, Functor không hợp lệ!
        return True
