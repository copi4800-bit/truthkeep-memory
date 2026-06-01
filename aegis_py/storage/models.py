from __future__ import annotations
"""Core data model layer for TruthKeep Memory.

Defines the foundational dataclasses that represent all persistent entities
in the memory system: memories, evidence events, memory links, conflicts,
and style-related profiles.  Every storage, retrieval, and governance
operation ultimately reads or writes instances of these models.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "Memory",
    "EvidenceEvent",
    "MemoryLink",
    "Conflict",
    "StyleSignal",
    "StyleProfile",
    "ADMISSION_STATES",
    "RETRIEVABLE_MEMORY_STATUSES",
    "RETRIEVABLE_MEMORY_STATUS_SQL",
]


def _now_utc() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


ADMISSION_STATES = {
    "draft",
    "validated",
    "hypothesized",
    "invalidated",
    "consolidated",
    "archived",
}

RETRIEVABLE_MEMORY_STATUSES = ("active", "crystallized")
RETRIEVABLE_MEMORY_STATUS_SQL = ", ".join(f"'{status}'" for status in RETRIEVABLE_MEMORY_STATUSES)


@dataclass
class Memory:
    """Central data model for a single memory record.

    A Memory captures one unit of knowledge — a fact, preference, episode,
    or procedure — stored within a scoped namespace.

    Identity & Classification:
        id:             Unique UUID string.
        type:           Memory category ("working", "episodic", "semantic",
                        "procedural").
        scope_type:     Namespace kind (e.g. "project", "user").
        scope_id:       Namespace identifier within scope_type.
        source_kind:    How the memory was created ("user_explicit",
                        "agent_inferred", etc.).

    Content:
        content:        The primary text payload.
        summary:        Optional condensed description.
        subject:        Optional subject key for conflict detection.
        source_ref:     Optional URI/reference to the originating artefact.
        origin_node_id: ID of the original memory this was derived from.
        session_id:     Session that produced this memory.

    Lifecycle:
        status:         Row-level status ("active", "crystallized",
                        "archived", "superseded", "expired").
        confidence:     Belief strength [0.0 – 1.0], updated via Bayes.
        activation_score: Salience / decay score.
        access_count:   How many times this memory has been reinforced.
        created_at:     When the record was first persisted (UTC).
        updated_at:     Last modification timestamp (UTC).
        last_accessed_at: Last retrieval or reinforcement timestamp.
        expires_at:     Hard expiry; memory is auto-archived past this.
        archived_at:    When the memory was moved to archive.

    Ancient-Math Fields:
        iching_state:    6-bit I-Ching hexagram encoding memory trust/truth.
        luoshu_checksum: Luo-Shu magic-square integrity checksum.

    Modern-Math Fields:
        erdos_cell_id:   Erdos grid cell assignment for spatial indexing.
        tda_signature:   Poincare TDA persistence signature string.

    Security (Phase 4 & 5):
        encrypted_content: AES-encrypted payload (if encryption enabled).
        encryption_key_id: Key identifier used for encryption.
        content_seal:      SHA-256 seal for tamper detection.
        encrypted_vector:  CKKS-encrypted Hilbert embedding vector.
        zk_commitment:     Plonky3/KZG public commitment.

    Extensible:
        metadata:       Free-form dict for admission_state, memory_state,
                        evidence links, retention info, and more.
    """
    id: str
    type: str
    scope_type: str
    scope_id: str
    content: str
    source_kind: str
    summary: str | None = None
    subject: str | None = None
    source_ref: str | None = None
    origin_node_id: str | None = None
    session_id: str | None = None
    status: str = "active"
    confidence: float = 1.0
    activation_score: float = 1.0
    access_count: int = 0
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    last_accessed_at: datetime | None = None
    expires_at: datetime | None = None
    archived_at: datetime | None = None
    iching_state: int = 0
    luoshu_checksum: float = 0.0
    erdos_cell_id: int = 0
    tda_signature: str = ""
    encrypted_content: str | None = None
    encryption_key_id: str | None = None
    content_seal: str | None = None
    encrypted_vector: str | None = None
    zk_commitment: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def metadata_json(self) -> dict[str, Any]:
        """Return the raw metadata dict (alias kept for DB column compatibility)."""
        return self.metadata

    @property
    def admission_state(self) -> str | None:
        """Extract the admission state string from metadata, or None if absent."""
        value = self.metadata.get("admission_state")
        if isinstance(value, str):
            return value
        return None

    @property
    def memory_state(self) -> str | None:
        """Extract the memory lifecycle state string from metadata, or None if absent."""
        value = self.metadata.get("memory_state")
        if isinstance(value, str):
            return value
        return None

    def model_dump(self, *, by_alias: bool = False) -> dict[str, Any]:
        """Serialize the Memory to a plain dict.

        When *by_alias* is True the ``metadata`` key is renamed to
        ``metadata_json`` to match the database column name.
        """
        payload = asdict(self)
        if by_alias:
            payload["metadata_json"] = payload.pop("metadata")
        return payload


@dataclass
class EvidenceEvent:
    """An atomic evidence event that backs one or more memories.

    Captures the raw content, provenance, and session context of an
    observation before it is promoted into a Memory record.
    """
    id: str
    scope_type: str
    scope_id: str
    raw_content: str
    source_kind: str
    session_id: str | None = None
    source_ref: str | None = None
    memory_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now_utc)

    @property
    def metadata_json(self) -> dict[str, Any]:
        """Return the raw metadata dict."""
        return self.metadata

    def model_dump(self, *, by_alias: bool = False) -> dict[str, Any]:
        """Serialize the EvidenceEvent to a plain dict."""
        payload = asdict(self)
        if by_alias:
            payload["metadata_json"] = payload.pop("metadata")
        return payload


@dataclass
class MemoryLink:
    """A weighted, typed edge connecting two memories in the knowledge graph.

    Links carry a *link_type* (e.g. ``same_subject``, ``supports``,
    ``contradicts``) and a numeric *weight* used by graph-analysis engines.
    """
    id: str
    source_id: str
    target_id: str
    link_type: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now_utc)

    @property
    def metadata_json(self) -> dict[str, Any]:
        """Return the raw metadata dict."""
        return self.metadata

    def model_dump(self, *, by_alias: bool = False) -> dict[str, Any]:
        """Serialize the MemoryLink to a plain dict."""
        payload = asdict(self)
        if by_alias:
            payload["metadata_json"] = payload.pop("metadata")
        return payload


@dataclass
class Conflict:
    """A detected contradiction between two memories on the same subject.

    Tracks severity *score*, human-readable *reason*, optional *resolution*,
    and lifecycle *status* (``open`` -> ``resolved``).
    """
    id: str
    memory_a_id: str
    memory_b_id: str
    subject_key: str | None = None
    score: float = 0.0
    reason: str | None = None
    resolution: str | None = None
    status: str = "open"
    created_at: datetime = field(default_factory=_now_utc)
    resolved_at: datetime | None = None

    def model_dump(self, *, by_alias: bool = False) -> dict[str, Any]:
        """Serialize the Conflict to a plain dict."""
        return asdict(self)


@dataclass
class StyleSignal:
    """A single style/preference signal captured from a user session.

    Aggregated into a StyleProfile to guide response tone, formatting,
    and other interaction preferences.
    """
    id: str
    session_id: str | None = None
    scope_id: str | None = None
    scope_type: str | None = None
    signal_key: str | None = None
    signal_value: Any = None
    agent_id: str | None = None
    signal: str | None = None
    weight: float = 1.0
    created_at: datetime = field(default_factory=_now_utc)

    def model_dump(self, *, by_alias: bool = False) -> dict[str, Any]:
        """Serialize the StyleSignal to a plain dict."""
        return asdict(self)


@dataclass
class StyleProfile:
    """Aggregated user style preferences for a given scope.

    Stores a JSON dict of preferences (e.g. verbosity, formality) that
    agents use to tailor responses.
    """
    id: str
    scope_id: str
    scope_type: str
    preferences_json: dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=_now_utc)

    def model_dump(self, *, by_alias: bool = False) -> dict[str, Any]:
        """Serialize the StyleProfile to a plain dict."""
        return asdict(self)
