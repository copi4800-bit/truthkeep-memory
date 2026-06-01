from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable

from ..storage.modern_math import NashEmbeddingPreserver, HilbertSpaceEngine, FourierCompressor
from ..config import features



def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"\w+", text.lower(), flags=re.UNICODE) if token]


def _band(score: float) -> str:
    if score >= 0.72:
        return "strong"
    if score >= 0.45:
        return "medium"
    return "light"


def _set_bit(mask: int, position: int) -> int:
    return mask | (1 << position)


def _bit_count(value: int) -> int:
    return int(value.bit_count())


def _hash_token(token: str, *, salt: str, width: int) -> int:
    digest = hashlib.blake2b(f"{salt}:{token}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % width


@dataclass(frozen=True)
class CompressedSignature:
    lexical_mask: int
    semantic_mask: int
    lexical_width: int
    semantic_width: int
    platonic_vertex: int = 0
    spectral_coefficients: tuple[float, ...] = ()  # Fourier spectral fingerprint


@dataclass(frozen=True)
class CompressedPrefilterMatch:
    score: float
    lexical_overlap: float
    semantic_overlap: float
    band: str
    tier: str
    platonic_similarity: float = 0.0
    nash_quality: float = 1.0
    spectral_similarity: float = 0.0  # Fourier spectral correlation


class CompressedCandidatePrefilter:
    """TurboQuant-inspired candidate prefilter using asymmetric compressed token signatures and Platonic spherical quantization."""

    def __init__(self, *, lexical_width: int = 64, semantic_width: int = 32):
        self.lexical_width = lexical_width
        self.semantic_width = semantic_width

    def build_signature(
        self,
        text: str,
        *,
        semantic_terms: Iterable[str] | None = None,
    ) -> CompressedSignature:
        lexical_mask = 0
        semantic_mask = 0
        for token in _tokens(text):
            lexical_mask = _set_bit(
                lexical_mask,
                _hash_token(token, salt="lexical", width=self.lexical_width),
            )
        for token in semantic_terms or ():
            normalized = str(token).strip().lower()
            if not normalized:
                continue
            semantic_mask = _set_bit(
                semantic_mask,
                _hash_token(normalized, salt="semantic", width=self.semantic_width),
            )
            
        # Tích hợp Platonic Quantization thông qua phép chiếu 3D giả lập mã hash
        from aegis_py.storage.ancient_math import PlatonicQuantizer
        import hashlib
        import struct
        import math
        
        h = hashlib.md5(text.encode("utf-8")).digest()
        x = struct.unpack("<h", h[0:2])[0] / 32768.0
        y = struct.unpack("<h", h[2:4])[0] / 32768.0
        z = struct.unpack("<h", h[4:6])[0] / 32768.0
        mag = math.sqrt(x*x + y*y + z*z)
        vec_3d = [x/mag, y/mag, z/mag] if mag > 0 else [1.0, 0.0, 0.0]
        
        platonic_vertex, _ = PlatonicQuantizer.quantize_vector(vec_3d)
        
        # Fourier spectral fingerprint (Phase 3)
        if features.ENABLE_FOURIER:
            spectral = tuple(FourierCompressor.text_to_spectrum(text, n_coefficients=16))
        else:
            spectral = tuple([0.0] * 16)

        
        return CompressedSignature(
            lexical_mask=lexical_mask,
            semantic_mask=semantic_mask,
            lexical_width=self.lexical_width,
            semantic_width=self.semantic_width,
            platonic_vertex=platonic_vertex,
            spectral_coefficients=spectral,
        )

    def match(
        self,
        query: CompressedSignature,
        candidate: CompressedSignature,
        *,
        tier: str,
    ) -> CompressedPrefilterMatch:
        lexical_overlap = self._overlap(query.lexical_mask, candidate.lexical_mask)
        semantic_overlap = self._overlap(query.semantic_mask, candidate.semantic_mask)
        
        # Điểm thưởng nếu trùng đỉnh Platonic (cùng nằm trong một diện đối xứng nhận thức)
        platonic_sim = 1.0 if query.platonic_vertex == candidate.platonic_vertex else 0.0
        platonic_bonus = 0.05 * platonic_sim
        
        # Nash Embedding Guard — đánh giá chất lượng bảo toàn khoảng cách
        query_density = _bit_count(query.lexical_mask) / max(query.lexical_width, 1)
        candidate_density = _bit_count(candidate.lexical_mask) / max(candidate.lexical_width, 1)
        nash_quality = NashEmbeddingPreserver.evaluate_embedding_quality(
            [query_density, candidate_density, lexical_overlap, semantic_overlap],
            candidate.lexical_mask,
            candidate.lexical_width,
        ).get("nash_quality", 1.0)
        
        # Fourier spectral similarity (Phase 3)
        spectral_sim = 0.0
        if features.ENABLE_FOURIER and query.spectral_coefficients and candidate.spectral_coefficients:
            spectral_sim = FourierCompressor.spectral_similarity(
                list(query.spectral_coefficients),
                list(candidate.spectral_coefficients),
            )
        spectral_bonus = spectral_sim * 0.05  # Tối đa +0.05 từ Fourier

        
        score = min(0.99, (lexical_overlap * 0.58) + (semantic_overlap * 0.22) + (spectral_sim * 0.15) + platonic_bonus)
        return CompressedPrefilterMatch(
            score=round(score, 6),
            lexical_overlap=round(lexical_overlap, 6),
            semantic_overlap=round(semantic_overlap, 6),
            band=_band(score),
            tier=tier,
            platonic_similarity=platonic_sim,
            nash_quality=round(nash_quality, 6),
            spectral_similarity=round(spectral_sim, 6),
        )

    def signature_from_payload(self, payload: dict[str, object] | None) -> CompressedSignature | None:
        if not isinstance(payload, dict):
            return None
        try:
            lexical_mask = int(str(payload.get("lexical_mask") or "0"), 16)
            semantic_mask = int(str(payload.get("semantic_mask") or "0"), 16)
            lexical_width = int(payload.get("lexical_width") or self.lexical_width)
            semantic_width = int(payload.get("semantic_width") or self.semantic_width)
            platonic_vertex = int(payload.get("platonic_vertex") or 0)
        except (TypeError, ValueError):
            return None
        return CompressedSignature(
            lexical_mask=lexical_mask,
            semantic_mask=semantic_mask,
            lexical_width=lexical_width,
            semantic_width=semantic_width,
            platonic_vertex=platonic_vertex,
        )

    def _overlap(self, left: int, right: int) -> float:
        if left == 0 or right == 0:
            return 0.0
        shared = _bit_count(left & right)
        total = max(_bit_count(left), 1)
        return shared / total
