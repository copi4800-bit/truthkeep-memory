from __future__ import annotations


EDGE_TYPE_ALIASES = {
    "same_subject": "derived_from",
    "procedural_supports_semantic": "depends_on",
    "supports": "supports",
    "extends": "part_of",
    "summary_of": "derived_from",
    "contradicts": "contradicts",
    "supersedes": "supersedes",
    "superseded_by": "superseded_by",
    "equivalence": "related_to",
}


def canonical_edge_type(link_type: str) -> str:
    # Trả về link_type chuẩn hóa ở dạng lowercase trùng khớp với RelationType
    normalized = link_type.lower()
    return EDGE_TYPE_ALIASES.get(normalized, normalized)
