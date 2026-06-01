from __future__ import annotations

from enum import Enum
from typing import Any


class RelationType(str, Enum):
    SUPERSEDES = "supersedes"
    SUPERSEDED_BY = "superseded_by"
    CONTRADICTS = "contradicts"
    RESOLVES = "resolves"
    EVIDENCE_FOR = "evidence_for"
    FALSIFIES = "falsifies"
    SUPPORTS = "supports"
    DEPENDS_ON = "depends_on"
    DERIVED_FROM = "derived_from"
    PART_OF = "part_of"
    RELATED_TO = "related_to"


RELATION_RULES: dict[str, dict[str, Any]] = {
    RelationType.SUPERSEDES.value: {
        "directional": True,
        "current_truth_behavior": "promote_source_demote_target",
        "why_not_behavior": "show_target_as_superseded",
        "propagates_correction": True,
        "score_effect": "strong_positive_for_source_negative_for_target",
    },
    RelationType.SUPERSEDED_BY.value: {
        "directional": True,
        "current_truth_behavior": "demote_source_promote_target",
        "why_not_behavior": "show_source_as_superseded",
        "propagates_correction": False,
        "score_effect": "negative_for_source_positive_for_target",
    },
    RelationType.CONTRADICTS.value: {
        "directional": False,
        "current_truth_behavior": "increase_conflict",
        "why_not_behavior": "show_conflict_reason",
        "propagates_correction": True,
        "score_effect": "negative",
    },
    RelationType.RESOLVES.value: {
        "directional": True,
        "current_truth_behavior": "resolve_conflict",
        "why_not_behavior": "show_resolved_status",
        "propagates_correction": False,
        "score_effect": "positive",
    },
    RelationType.EVIDENCE_FOR.value: {
        "directional": True,
        "current_truth_behavior": "boost_target",
        "why_not_behavior": "explain_missing_evidence",
        "propagates_correction": False,
        "score_effect": "positive",
    },
    RelationType.FALSIFIES.value: {
        "directional": True,
        "current_truth_behavior": "demote_target",
        "why_not_behavior": "explain_falsification",
        "propagates_correction": True,
        "score_effect": "negative",
    },
    RelationType.SUPPORTS.value: {
        "directional": True,
        "current_truth_behavior": "boost_target_light",
        "why_not_behavior": "explain_supports",
        "propagates_correction": False,
        "score_effect": "positive",
    },
    RelationType.DEPENDS_ON.value: {
        "directional": True,
        "current_truth_behavior": "depends_on_source",
        "why_not_behavior": "explain_dependency",
        "propagates_correction": True,
        "score_effect": "none",
    },
    RelationType.DERIVED_FROM.value: {
        "directional": True,
        "current_truth_behavior": "derived_from_source",
        "why_not_behavior": "explain_derivation",
        "propagates_correction": True,
        "score_effect": "none",
    },
    RelationType.PART_OF.value: {
        "directional": True,
        "current_truth_behavior": "part_of_source",
        "why_not_behavior": "explain_aggregation",
        "propagates_correction": True,
        "score_effect": "none",
    },
    RelationType.RELATED_TO.value: {
        "directional": False,
        "current_truth_behavior": "none",
        "why_not_behavior": "none",
        "propagates_correction": False,
        "score_effect": "none",
    },
}


def validate_relation_type(link_type: str) -> bool:
    """Check if the given link_type matches a standard RelationType enum value."""
    try:
        RelationType(link_type)
        return True
    except ValueError:
        return False
