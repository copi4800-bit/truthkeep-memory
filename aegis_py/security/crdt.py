"""
TruthKeep Memory — CRDT-Based Distributed Consistency (Phase 5)
================================================================
Level 8 Research Roadmap: Distributed Memory Consistency.

Implements Conflict-free Replicated Data Types (CRDTs) for
multi-node memory synchronization:

1. LWW-Register (Last-Writer-Wins Register) for memory content
2. G-Counter (Grow-only Counter) for access_count
3. OR-Set (Observed-Remove Set) for memory collections
4. Vector Clock for causal ordering
5. Merge logic for conflict-free synchronization

Design principles:
  - Eventual consistency: all replicas converge to same state
  - Conflict-free: no manual merge needed for CRDT operations
  - Causal ordering: vector clocks track happens-before relation
  - Partition tolerant: nodes can diverge and resync later

NOTE: This is a research-grade implementation for modeling and
verification. Production deployment would need network transport,
failure detection, and garbage collection of tombstones.
"""
from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

__all__ = [
    "VectorClock",
    "LWWRegister",
    "GCounter",
    "ORSet",
    "CRDTMemoryState",
    "CRDTSyncEngine",
]


# =========================================================================
# 1. VECTOR CLOCK -- Causal ordering
# =========================================================================

class VectorClock:
    """Vector Clock for causal ordering of distributed events.

    Each node maintains a counter. When node i performs an action,
    it increments clock[i]. When receiving a message, it takes
    the element-wise max of local and received clocks.

    Properties (verified in Dafny spec):
      - Reflexive: vc <= vc
      - Antisymmetric: vc1 <= vc2 and vc2 <= vc1 => vc1 == vc2
      - Transitive: vc1 <= vc2 and vc2 <= vc3 => vc1 <= vc3
      - Concurrent detection: not (vc1 <= vc2) and not (vc2 <= vc1)
    """

    __slots__ = ("_clock",)

    def __init__(self, clock: Optional[dict[str, int]] = None):
        self._clock: dict[str, int] = dict(clock) if clock else {}

    def increment(self, node_id: str) -> "VectorClock":
        """Increment this node's counter (local event)."""
        new_clock = dict(self._clock)
        new_clock[node_id] = new_clock.get(node_id, 0) + 1
        return VectorClock(new_clock)

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Element-wise max merge (receive event)."""
        all_nodes = set(self._clock) | set(other._clock)
        merged = {}
        for node in all_nodes:
            merged[node] = max(
                self._clock.get(node, 0),
                other._clock.get(node, 0),
            )
        return VectorClock(merged)

    def happens_before(self, other: "VectorClock") -> bool:
        """True if self < other (self happens-before other).

        self < other iff:
          - forall node: self[node] <= other[node]
          - exists node: self[node] < other[node]
        """
        all_nodes = set(self._clock) | set(other._clock)
        all_leq = all(
            self._clock.get(n, 0) <= other._clock.get(n, 0)
            for n in all_nodes
        )
        any_lt = any(
            self._clock.get(n, 0) < other._clock.get(n, 0)
            for n in all_nodes
        )
        return all_leq and any_lt

    def concurrent_with(self, other: "VectorClock") -> bool:
        """True if neither happens-before the other."""
        return not self.happens_before(other) and not other.happens_before(self) and self != other

    def get(self, node_id: str) -> int:
        return self._clock.get(node_id, 0)

    def to_dict(self) -> dict[str, int]:
        return dict(self._clock)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "VectorClock":
        return cls(data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return NotImplemented
        all_nodes = set(self._clock) | set(other._clock)
        return all(
            self._clock.get(n, 0) == other._clock.get(n, 0)
            for n in all_nodes
        )

    def __repr__(self) -> str:
        return f"VectorClock({self._clock})"


# =========================================================================
# 2. LWW-REGISTER -- Last-Writer-Wins Register
# =========================================================================

@dataclass
class LWWRegister:
    """Last-Writer-Wins Register CRDT.

    For memory content: concurrent writes are resolved by timestamp.
    The write with the latest timestamp wins.

    Properties (verified in Dafny spec):
      - Commutativity: merge(a, b) == merge(b, a)
      - Idempotency: merge(a, a) == a
      - Associativity: merge(merge(a, b), c) == merge(a, merge(b, c))

    Maps to: Memory.content, Memory.confidence, Memory.status
    """
    value: Any
    timestamp: str  # ISO 8601
    node_id: str    # Which node wrote this value

    def merge(self, other: "LWWRegister") -> "LWWRegister":
        """Merge two registers: latest timestamp wins.

        Tie-breaking: if timestamps equal, higher node_id wins
        (deterministic, but arbitrary).
        """
        if self.timestamp > other.timestamp:
            return LWWRegister(self.value, self.timestamp, self.node_id)
        elif other.timestamp > self.timestamp:
            return LWWRegister(other.value, other.timestamp, other.node_id)
        else:
            # Tie-break by node_id (deterministic)
            if self.node_id >= other.node_id:
                return LWWRegister(self.value, self.timestamp, self.node_id)
            return LWWRegister(other.value, other.timestamp, other.node_id)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "timestamp": self.timestamp, "node_id": self.node_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LWWRegister":
        return cls(value=data["value"], timestamp=data["timestamp"], node_id=data["node_id"])


# =========================================================================
# 3. G-COUNTER -- Grow-only Counter
# =========================================================================

class GCounter:
    """Grow-only Counter CRDT.

    Each node maintains its own count. Total = sum of all node counts.
    Merge = element-wise max.

    Properties (verified in Dafny spec):
      - Monotonic: value only increases
      - Commutativity: merge(a, b) == merge(b, a)
      - Idempotency: merge(a, a) == a

    Maps to: Memory.access_count (only grows via reinforce)
    """

    __slots__ = ("_counts",)

    def __init__(self, counts: Optional[dict[str, int]] = None):
        self._counts: dict[str, int] = dict(counts) if counts else {}

    def increment(self, node_id: str, amount: int = 1) -> "GCounter":
        """Increment this node's count."""
        if amount < 0:
            raise ValueError("G-Counter can only grow (amount must be >= 0)")
        new_counts = dict(self._counts)
        new_counts[node_id] = new_counts.get(node_id, 0) + amount
        return GCounter(new_counts)

    def value(self) -> int:
        """Total count across all nodes."""
        return sum(self._counts.values())

    def merge(self, other: "GCounter") -> "GCounter":
        """Element-wise max merge."""
        all_nodes = set(self._counts) | set(other._counts)
        merged = {}
        for node in all_nodes:
            merged[node] = max(
                self._counts.get(node, 0),
                other._counts.get(node, 0),
            )
        return GCounter(merged)

    def to_dict(self) -> dict[str, int]:
        return dict(self._counts)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "GCounter":
        return cls(data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GCounter):
            return NotImplemented
        all_nodes = set(self._counts) | set(other._counts)
        return all(
            self._counts.get(n, 0) == other._counts.get(n, 0)
            for n in all_nodes
        )

    def __repr__(self) -> str:
        return f"GCounter(value={self.value()}, counts={self._counts})"


# =========================================================================
# 4. OR-SET -- Observed-Remove Set
# =========================================================================

class ORSet:
    """Observed-Remove Set CRDT.

    Add and remove operations are conflict-free:
    - Add(elem): assigns a unique tag to elem
    - Remove(elem): removes all tags currently associated with elem
    - Concurrent add+remove: add wins (the new tag survives)

    Properties (verified in Dafny spec):
      - Add-wins semantics: concurrent add+remove => element present
      - Commutativity: merge order doesn't matter
      - Idempotency: merge(a, a) == a

    Maps to: Set of active memory IDs in a scope
    """

    __slots__ = ("_elements", "_tombstones")

    def __init__(
        self,
        elements: Optional[dict[str, set[str]]] = None,
        tombstones: Optional[dict[str, set[str]]] = None,
    ):
        # element_value -> set of unique tags
        self._elements: dict[str, set[str]] = {
            k: set(v) for k, v in (elements or {}).items()
        }
        self._tombstones: dict[str, set[str]] = {
            k: set(v) for k, v in (tombstones or {}).items()
        }

    def add(self, element: str, node_id: str) -> "ORSet":
        """Add element with a unique tag."""
        tag = f"{node_id}:{uuid.uuid4().hex[:8]}"
        new_elements = {k: set(v) for k, v in self._elements.items()}
        new_tombstones = {k: set(v) for k, v in self._tombstones.items()}

        if element not in new_elements:
            new_elements[element] = set()
        new_elements[element].add(tag)

        return ORSet(new_elements, new_tombstones)

    def remove(self, element: str) -> "ORSet":
        """Remove element: tombstone all currently observed tags."""
        new_elements = {k: set(v) for k, v in self._elements.items()}
        new_tombstones = {k: set(v) for k, v in self._tombstones.items()}

        if element in new_elements:
            if element not in new_tombstones:
                new_tombstones[element] = set()
            new_tombstones[element].update(new_elements[element])
            del new_elements[element]

        return ORSet(new_elements, new_tombstones)

    def contains(self, element: str) -> bool:
        """Check if element is in the set (has live tags)."""
        if element not in self._elements:
            return False
        live = self._elements[element] - self._tombstones.get(element, set())
        return len(live) > 0

    def elements(self) -> set[str]:
        """Return all live elements."""
        result = set()
        for elem, tags in self._elements.items():
            live = tags - self._tombstones.get(elem, set())
            if live:
                result.add(elem)
        return result

    def merge(self, other: "ORSet") -> "ORSet":
        """Merge two OR-Sets: union of elements, union of tombstones."""
        all_keys = set(self._elements) | set(other._elements)
        merged_elements: dict[str, set[str]] = {}
        for key in all_keys:
            merged_elements[key] = (
                self._elements.get(key, set()) | other._elements.get(key, set())
            )

        all_tomb_keys = set(self._tombstones) | set(other._tombstones)
        merged_tombstones: dict[str, set[str]] = {}
        for key in all_tomb_keys:
            merged_tombstones[key] = (
                self._tombstones.get(key, set()) | other._tombstones.get(key, set())
            )

        return ORSet(merged_elements, merged_tombstones)

    def to_dict(self) -> dict[str, Any]:
        return {
            "elements": {k: sorted(v) for k, v in self._elements.items()},
            "tombstones": {k: sorted(v) for k, v in self._tombstones.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ORSet":
        return cls(
            elements={k: set(v) for k, v in data.get("elements", {}).items()},
            tombstones={k: set(v) for k, v in data.get("tombstones", {}).items()},
        )

    def __repr__(self) -> str:
        return f"ORSet({self.elements()})"


# =========================================================================
# 5. CRDT MEMORY STATE -- Composite CRDT for a single memory
# =========================================================================

@dataclass
class CRDTMemoryState:
    """Composite CRDT state for a single TruthKeep memory.

    Combines multiple CRDTs:
      - content: LWW-Register (last writer wins for content)
      - confidence: LWW-Register (last writer wins for confidence)
      - status: LWW-Register (last writer wins for status)
      - access_count: G-Counter (monotonically growing)
      - clock: VectorClock (causal ordering)
    """
    memory_id: str
    content: LWWRegister
    confidence: LWWRegister
    status: LWWRegister
    access_count: GCounter
    clock: VectorClock

    def merge(self, other: "CRDTMemoryState") -> "CRDTMemoryState":
        """Merge two states for the same memory."""
        if self.memory_id != other.memory_id:
            raise ValueError(
                f"Cannot merge different memories: {self.memory_id} vs {other.memory_id}"
            )
        return CRDTMemoryState(
            memory_id=self.memory_id,
            content=self.content.merge(other.content),
            confidence=self.confidence.merge(other.confidence),
            status=self.status.merge(other.status),
            access_count=self.access_count.merge(other.access_count),
            clock=self.clock.merge(other.clock),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content.to_dict(),
            "confidence": self.confidence.to_dict(),
            "status": self.status.to_dict(),
            "access_count": self.access_count.to_dict(),
            "clock": self.clock.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CRDTMemoryState":
        return cls(
            memory_id=data["memory_id"],
            content=LWWRegister.from_dict(data["content"]),
            confidence=LWWRegister.from_dict(data["confidence"]),
            status=LWWRegister.from_dict(data["status"]),
            access_count=GCounter.from_dict(data["access_count"]),
            clock=VectorClock.from_dict(data["clock"]),
        )


# =========================================================================
# 6. CRDT SYNC ENGINE -- Multi-node synchronization
# =========================================================================

class CRDTSyncEngine:
    """Sync engine that manages CRDT states across nodes.

    Operations:
      - create_memory(): initialize CRDT state for new memory
      - update_content(): LWW update content
      - reinforce(): G-Counter increment access_count
      - supersede(): LWW update status to superseded
      - merge_remote(): merge incoming CRDT state from another node
      - export_delta(): export changed states for sync
      - import_delta(): import and merge remote deltas

    Consistency guarantee:
      All nodes that have received the same set of operations
      will converge to the same state, regardless of order.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._states: dict[str, CRDTMemoryState] = {}
        self._dirty: set[str] = set()  # Memory IDs changed since last export

    def create_memory(
        self,
        memory_id: str,
        content: str,
        confidence: float = 0.85,
        status: str = "active",
    ) -> CRDTMemoryState:
        """Initialize CRDT state for a new memory."""
        now = datetime.now(timezone.utc).isoformat()
        clock = VectorClock().increment(self.node_id)

        state = CRDTMemoryState(
            memory_id=memory_id,
            content=LWWRegister(content, now, self.node_id),
            confidence=LWWRegister(confidence, now, self.node_id),
            status=LWWRegister(status, now, self.node_id),
            access_count=GCounter(),
            clock=clock,
        )
        self._states[memory_id] = state
        self._dirty.add(memory_id)
        return state

    def update_content(
        self, memory_id: str, new_content: str
    ) -> Optional[CRDTMemoryState]:
        """Update memory content (LWW)."""
        if memory_id not in self._states:
            return None
        state = self._states[memory_id]
        now = datetime.now(timezone.utc).isoformat()
        self._states[memory_id] = CRDTMemoryState(
            memory_id=memory_id,
            content=LWWRegister(new_content, now, self.node_id),
            confidence=state.confidence,
            status=state.status,
            access_count=state.access_count,
            clock=state.clock.increment(self.node_id),
        )
        self._dirty.add(memory_id)
        return self._states[memory_id]

    def reinforce(self, memory_id: str) -> Optional[CRDTMemoryState]:
        """Increment access count (G-Counter)."""
        if memory_id not in self._states:
            return None
        state = self._states[memory_id]
        self._states[memory_id] = CRDTMemoryState(
            memory_id=memory_id,
            content=state.content,
            confidence=state.confidence,
            status=state.status,
            access_count=state.access_count.increment(self.node_id),
            clock=state.clock.increment(self.node_id),
        )
        self._dirty.add(memory_id)
        return self._states[memory_id]

    def supersede(self, memory_id: str) -> Optional[CRDTMemoryState]:
        """Mark memory as superseded (LWW status)."""
        if memory_id not in self._states:
            return None
        state = self._states[memory_id]
        now = datetime.now(timezone.utc).isoformat()
        self._states[memory_id] = CRDTMemoryState(
            memory_id=memory_id,
            content=state.content,
            confidence=state.confidence,
            status=LWWRegister("superseded", now, self.node_id),
            access_count=state.access_count,
            clock=state.clock.increment(self.node_id),
        )
        self._dirty.add(memory_id)
        return self._states[memory_id]

    def merge_remote(self, remote_state: CRDTMemoryState) -> CRDTMemoryState:
        """Merge incoming state from another node."""
        mid = remote_state.memory_id
        if mid in self._states:
            merged = self._states[mid].merge(remote_state)
        else:
            merged = remote_state
        self._states[mid] = merged
        self._dirty.add(mid)
        return merged

    def get_state(self, memory_id: str) -> Optional[CRDTMemoryState]:
        """Get current CRDT state for a memory."""
        return self._states.get(memory_id)

    def export_delta(self) -> list[dict[str, Any]]:
        """Export dirty states as JSON-serializable deltas."""
        deltas = []
        for mid in self._dirty:
            if mid in self._states:
                deltas.append(self._states[mid].to_dict())
        self._dirty.clear()
        return deltas

    def import_delta(self, deltas: list[dict[str, Any]]) -> int:
        """Import and merge remote deltas. Returns count of merged states."""
        count = 0
        for delta_dict in deltas:
            remote = CRDTMemoryState.from_dict(delta_dict)
            self.merge_remote(remote)
            count += 1
        return count

    def all_memory_ids(self) -> set[str]:
        """Return all tracked memory IDs."""
        return set(self._states.keys())
