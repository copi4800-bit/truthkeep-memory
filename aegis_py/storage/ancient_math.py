from __future__ import annotations
import math
import json
from typing import Any

__all__ = [
    "IChingStateEncoder",
    "LuoshuIntegrityValidator",
    "PlatonicQuantizer",
    "FibonacciDecayEngine",
    "compute_memory_ancient_math_fields",
]

# --- Named constants ---
INTEGRITY_TOLERANCE = 0.01
VERIFIED_CONFIDENCE_THRESHOLD = 0.85
TRUST_VERIFIED = 0.9
TRUST_DISPUTED = 0.3
TRUST_DEFAULT = 0.6

class IChingStateEncoder:
    """Mã hóa trạng thái bộ nhớ AI bằng 64 quẻ dịch (6-bit binary) và tính toán Hào Động"""
    
    HEXAGRAMS = {
        0b111111: "Thuần Càn (Tối thượng - Hệ thống & Bất biến)",
        0b000000: "Thuần Khôn (Nguyên thủy - Nháp & Chưa xác thực)",
        0b100101: "Hỏa Lôi Phệ Hạp (Đang tranh chấp - Cần hiệu đính)",
        0b010101: "Thủy Hỏa Ký Tế (Đã hoàn thành - Winner tin cậy)",
        0b101010: "Hỏa Thủy Vị Tế (Bị thay thế - Superseded/Archived)",
        0b010100: "Thủy Lôi Truân (Khởi đầu gian nan - Tranh chấp cần kiểm chứng)"
    }

    @staticmethod
    def encode_state(kind: str, truth: str, trust: str) -> int:
        """Encode memory kind, truth-state, and trust-level into a 6-bit I-Ching hexagram code.

        Bits 0-1: memory kind  (working/episodic/semantic/procedural)
        Bits 2-3: truth state  (candidate/winner/superseded/archived)
        Bits 4-5: trust level  (unverified/verified/disputed/immutable)
        """
        # Vạch 1-2: Loại bộ nhớ
        kind_bits = {"working": 0b00, "episodic": 0b01, "semantic": 0b10, "procedural": 0b11}.get(kind, 0b10)
        # Vạch 3-4: Trạng thái chân thực
        truth_bits = {"candidate": 0b00, "winner": 0b01, "superseded": 0b10, "archived": 0b11}.get(truth, 0b01)
        # Vạch 5-6: Mức độ tin cậy
        trust_bits = {"unverified": 0b00, "verified": 0b01, "disputed": 0b10, "immutable": 0b11}.get(trust, 0b01)
        
        return (trust_bits << 4) | (truth_bits << 2) | kind_bits

    @classmethod
    def get_hexagram_name(cls, code: int) -> str:
        """Return the Vietnamese hexagram name for the given 6-bit code.

        Falls back to a generic label for codes not in the lookup table.
        """
        return cls.HEXAGRAMS.get(code, f"Quẻ Dịch số {code} (Trạng thái hỗn hợp)")

    @classmethod
    def calculate_changing_lines(cls, old_code: int, new_code: int) -> list[int]:
        """Xác định vị trí các Hào bị biến đổi (Hào Động) giữa hai trạng thái bộ nhớ"""
        diff = old_code ^ new_code
        changing = []
        for i in range(6):
            if (diff >> i) & 1:
                changing.append(i + 1) # Hào 1 đến Hào 6
        return changing


class LuoshuIntegrityValidator:
    """Xác thực toàn vẹn trọng số bộ nhớ dựa trên Ô vuông ma thuật Lạc Thư"""
    
    LUOSHU_MATRIX = [
        [4, 9, 2],
        [3, 5, 7],
        [8, 1, 6]
    ]
    
    @classmethod
    def encrypt_weights(cls, base_weights: list[float]) -> list[list[float]]:
        """Nhúng chéo trọng số cơ bản vào ma trận Lạc Thư đối xứng để mã hóa bảo mật"""
        assert len(base_weights) == 3, "Cần đúng 3 tham số trọng số [trust, confidence, relevance]"
        encrypted = []
        for i, w in enumerate(base_weights):
            row = []
            for val in cls.LUOSHU_MATRIX[i]:
                row.append(w * val)
            encrypted.append(row)
        return encrypted
    
    @classmethod
    def validate_node_integrity(cls, weights_3x3: list[list[float]]) -> tuple[bool, float]:
        """Kiểm tra tính nhất quán tỷ lệ của ma trận trọng số. Phát hiện can thiệp trái phép."""
        row_errors = []
        for r in range(3):
            recovered = []
            for c in range(3):
                val = weights_3x3[r][c]
                ref = cls.LUOSHU_MATRIX[r][c]
                recovered.append(val / ref if ref != 0 else 0.0)
            row_err = max(recovered) - min(recovered)
            row_errors.append(row_err)
            
        error_score = sum(row_errors) / 3.0
        is_secure = error_score < INTEGRITY_TOLERANCE
        return is_secure, error_score


class PlatonicQuantizer:
    """Lượng tử hóa vector ngữ nghĩa dựa trên hình chiếu đỉnh Khối 20 mặt đều (Icosahedron)"""
    
    PHI = (1.0 + math.sqrt(5.0)) / 2.0
    
    ICOSAHEDRON_VERTICES = [
        [-1.0,  PHI,  0.0], [ 1.0,  PHI,  0.0], [-1.0, -PHI,  0.0], [ 1.0, -PHI,  0.0],
        [ 0.0, -1.0,  PHI], [ 0.0,  1.0,  PHI], [ 0.0, -1.0, -PHI], [ 0.0,  1.0, -PHI],
        [ PHI,  0.0, -1.0], [ PHI,  0.0,  1.0], [-PHI,  0.0, -1.0], [-PHI,  0.0,  1.0]
    ]
    
    @classmethod
    def _normalize(cls, vec: list[float]) -> list[float]:
        """L2-normalize a vector; returns a zero vector if magnitude is 0."""
        mag = math.sqrt(sum(x*x for x in vec))
        if mag == 0:
            return [0.0] * len(vec)
        return [x / mag for x in vec]
        
    @classmethod
    def quantize_vector(cls, vector_3d: list[float]) -> tuple[int, float]:
        """Chiếu vector 3D vào đỉnh Platonic gần nhất trong O(1)"""
        norm_v = cls._normalize(vector_3d)
        best_vertex_idx = -1
        max_similarity = -2.0
        
        for i, vertex in enumerate(cls.ICOSAHEDRON_VERTICES):
            norm_vertex = cls._normalize(vertex)
            dot_product = sum(norm_v[j] * norm_vertex[j] for j in range(3))
            if dot_product > max_similarity:
                max_similarity = dot_product
                best_vertex_idx = i
                
        return best_vertex_idx, max_similarity


class FibonacciDecayEngine:
    """Động cơ tính suy giảm độ ưu tiên (Decay) dựa trên dãy số Fibonacci"""
    
    FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    PHI = 1.6180339887
    
    @classmethod
    def calculate_retained_salience(cls, initial_salience: float, access_interval_hours: float) -> float:
        """Tính độ salience còn lại dựa trên tỷ lệ vàng phi tuyến tính"""
        decay_factor = 1.0 / (cls.PHI ** (access_interval_hours / 24.0))
        return initial_salience * decay_factor


def compute_memory_ancient_math_fields(row: dict[str, Any]) -> tuple[int, float]:
    """Tính toán đồng thời cả iching_state và luoshu_checksum từ dữ liệu bộ nhớ"""

    
    kind = row.get("type") or "semantic"
    status = row.get("status") or "active"
    confidence = row.get("confidence")
    confidence = float(confidence) if confidence is not None else 1.0
    activation_score = row.get("activation_score")
    activation_score = float(activation_score) if activation_score is not None else 1.0
    
    metadata_raw = row.get("metadata_json") or row.get("metadata")
    try:
        if isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw)
        else:
            metadata = metadata_raw or {}
    except (json.JSONDecodeError, ValueError, TypeError):
        metadata = {}
        
    is_immutable = metadata.get("is_immutable", False)
    is_winner = metadata.get("is_winner", False)
    
    # Xác định trạng thái tin cậy (trust)
    if is_immutable:
        trust = "immutable"
    elif status in ("reconcile_required", "conflict_candidate"):
        trust = "disputed"
    elif confidence >= VERIFIED_CONFIDENCE_THRESHOLD:
        trust = "verified"
    else:
        trust = "unverified"
        
    # Xác định trạng thái sự thật (truth)
    if is_winner:
        truth = "winner"
    elif status == "superseded":
        truth = "superseded"
    elif status == "archived":
        truth = "archived"
    else:
        truth = "candidate"
        
    iching = IChingStateEncoder.encode_state(kind, truth, trust)
    
    trust_val = TRUST_VERIFIED if trust in ("verified", "immutable") else (TRUST_DISPUTED if trust == "disputed" else TRUST_DEFAULT)
    
    encrypted = LuoshuIntegrityValidator.encrypt_weights([trust_val, confidence, activation_score])
    _, checksum = LuoshuIntegrityValidator.validate_node_integrity(encrypted)
    
    return iching, checksum
