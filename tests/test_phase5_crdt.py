"""Unit tests for TruthKeep Phase 5 CRDT-based Distributed Consistency.

Tests all components of Conflict-free Replicated Data Types (CRDTs):
- VectorClock (Causal ordering)
- LWW-Register (Last-Writer-Wins Register)
- G-Counter (Grow-only Counter)
- OR-Set (Observed-Remove Set)
- CRDTMemoryState (Composite memory state)
- CRDTSyncEngine (Multi-node replication, convergence verification)
"""

import pytest
import time
from datetime import datetime, timezone
from aegis_py.security.crdt import (
    VectorClock,
    LWWRegister,
    GCounter,
    ORSet,
    CRDTMemoryState,
    CRDTSyncEngine,
)


# =========================================================================
# 1. VECTOR CLOCK TESTS
# =========================================================================

def test_vector_clock_causal_relations():
    """Test happens-before, concurrent, and equal vector clock relations."""
    vc1 = VectorClock()
    
    # Empty clocks are equal
    assert vc1 == VectorClock()
    
    # Local events increment node clock
    vc_a1 = vc1.increment("nodeA")
    assert vc_a1.get("nodeA") == 1
    assert vc_a1.get("nodeB") == 0
    
    # Causality happens-before relation (vc1 < vc_a1)
    assert vc1.happens_before(vc_a1)
    assert not vc_a1.happens_before(vc1)
    
    # Sequence of events on nodeA
    vc_a2 = vc_a1.increment("nodeA")
    assert vc_a1.happens_before(vc_a2)
    assert vc1.happens_before(vc_a2)
    
    # Event on nodeB starting from vc_a1 (causal path nodeA -> nodeB)
    vc_b1 = vc_a1.increment("nodeB")
    assert vc_a1.happens_before(vc_b1)
    assert vc_b1.get("nodeA") == 1
    assert vc_b1.get("nodeB") == 1
    
    # Concurrent events (diverged paths)
    # vc_a2 (nodeA: 2, nodeB: 0) vs vc_b1 (nodeA: 1, nodeB: 1)
    assert not vc_a2.happens_before(vc_b1)
    assert not vc_b1.happens_before(vc_a2)
    assert vc_a2.concurrent_with(vc_b1)
    
    # Merge concurrent clocks
    merged = vc_a2.merge(vc_b1)
    assert merged.get("nodeA") == 2
    assert merged.get("nodeB") == 1
    
    assert vc_a2.happens_before(merged)
    assert vc_b1.happens_before(merged)


def test_vector_clock_serialization():
    """Test VectorClock to_dict/from_dict roundtrip."""
    vc = VectorClock({"nodeA": 5, "nodeB": 2})
    data = vc.to_dict()
    assert data == {"nodeA": 5, "nodeB": 2}
    
    restored = VectorClock.from_dict(data)
    assert restored == vc


# =========================================================================
# 2. LWW-REGISTER TESTS
# =========================================================================

def test_lww_register_merge():
    """Test Last-Writer-Wins register convergence and tie-breaking."""
    t1 = "2026-05-27T10:00:00Z"
    t2 = "2026-05-27T10:05:00Z"
    t3 = "2026-05-27T10:05:00Z"  # Tie timestamp
    
    reg_a = LWWRegister(value="Initial Content", timestamp=t1, node_id="nodeA")
    reg_b = LWWRegister(value="Updated Content", timestamp=t2, node_id="nodeB")
    
    # Merge commutative check
    merged_ab = reg_a.merge(reg_b)
    merged_ba = reg_b.merge(reg_a)
    
    assert merged_ab == merged_ba
    assert merged_ab.value == "Updated Content"
    assert merged_ab.node_id == "nodeB"
    
    # Idempotency
    assert reg_a.merge(reg_a) == reg_a
    
    # Tie-breaking by node_id (lexicographical)
    reg_tie_a = LWWRegister(value="ValA", timestamp=t3, node_id="nodeA")
    reg_tie_b = LWWRegister(value="ValB", timestamp=t3, node_id="nodeB")
    
    # nodeB >= nodeA, so nodeB wins
    merged_tie_ab = reg_tie_a.merge(reg_tie_b)
    assert merged_tie_ab.value == "ValB"
    assert merged_tie_ab.node_id == "nodeB"
    
    merged_tie_ba = reg_tie_b.merge(reg_tie_a)
    assert merged_tie_ba.value == "ValB"


def test_lww_register_serialization():
    """Test LWWRegister serialization."""
    reg = LWWRegister("active", "2026-05-27T12:00:00Z", "nodeA")
    data = reg.to_dict()
    
    assert data == {
        "value": "active",
        "timestamp": "2026-05-27T12:00:00Z",
        "node_id": "nodeA",
    }
    
    restored = LWWRegister.from_dict(data)
    assert restored == reg


# =========================================================================
# 3. G-COUNTER TESTS
# =========================================================================

def test_g_counter_increment_and_merge():
    """Test Grow-only Counter monotonicity and cross-node convergence."""
    gcA = GCounter()
    gcB = GCounter()
    
    # Increments on node A
    gcA = gcA.increment("nodeA", 5)
    assert gcA.value() == 5
    
    # Increment with default amount (1)
    gcA = gcA.increment("nodeA")
    assert gcA.value() == 6
    
    # Decrement must raise ValueError
    with pytest.raises(ValueError, match="G-Counter can only grow"):
        gcA.increment("nodeA", -1)
        
    # Increments on node B
    gcB = gcB.increment("nodeB", 3)
    assert gcB.value() == 3
    
    # Merge A and B
    merged_ab = gcA.merge(gcB)
    merged_ba = gcB.merge(gcA)
    
    assert merged_ab == merged_ba
    # Total = sum of node A count (6) and node B count (3) = 9
    assert merged_ab.value() == 9
    
    # Subsequent merge with old values shouldn't decrease count
    gcA_stale = GCounter({"nodeA": 2})
    merged_stale = merged_ab.merge(gcA_stale)
    assert merged_stale.value() == 9


def test_g_counter_serialization():
    """Test GCounter serialization."""
    gc = GCounter({"nodeA": 10, "nodeB": 15})
    data = gc.to_dict()
    assert data == {"nodeA": 10, "nodeB": 15}
    
    restored = GCounter.from_dict(data)
    assert restored == gc


# =========================================================================
# 4. OR-SET TESTS
# =========================================================================

def test_or_set_add_remove_and_merge():
    """Test Observed-Remove Set add, remove, and add-wins conflict resolution."""
    set_a = ORSet()
    set_b = ORSet()
    
    # Add element
    set_a = set_a.add("mem-1", "nodeA")
    assert set_a.contains("mem-1")
    assert set_a.elements() == {"mem-1"}
    
    # Merge A with empty set B
    merged = set_a.merge(set_b)
    assert merged.contains("mem-1")
    
    # Add concurrent element on set B
    set_b = set_b.add("mem-2", "nodeB")
    
    # Merge A and B
    merged_ab = set_a.merge(set_b)
    assert merged_ab.elements() == {"mem-1", "mem-2"}
    
    # Remove element from merged set
    removed = merged_ab.remove("mem-1")
    assert not removed.contains("mem-1")
    assert removed.elements() == {"mem-2"}
    
    # Test concurrent Add and Remove (Add-Wins)
    # Node A removes "mem-1" (observes Node A's tags)
    removed_a = set_a.remove("mem-1")
    
    # Concurrent Node B adds "mem-1" again
    added_b = set_b.add("mem-1", "nodeB")
    
    # Merge removal on A and concurrent addition on B
    # Since B added "mem-1" with a new tag, "mem-1" should survive (add wins)
    add_wins = removed_a.merge(added_b)
    assert add_wins.contains("mem-1")
    assert add_wins.elements() == {"mem-1", "mem-2"}


def test_or_set_serialization():
    """Test ORSet serialization."""
    s = ORSet()
    s = s.add("mem-abc", "nodeA")
    data = s.to_dict()
    
    assert "elements" in data
    assert "tombstones" in data
    assert "mem-abc" in data["elements"]
    
    restored = ORSet.from_dict(data)
    assert restored.elements() == s.elements()


# =========================================================================
# 5. CRDT MEMORY STATE & SYNC ENGINE TESTS
# =========================================================================

def test_crdt_sync_engine_local_operations():
    """Test simple CRDTSyncEngine workflow of local creation and mutation."""
    engine = CRDTSyncEngine("nodeA")
    
    # 1. Create a memory
    state = engine.create_memory("mem-1", "Original Text", confidence=0.9)
    assert state.memory_id == "mem-1"
    assert state.content.value == "Original Text"
    assert state.confidence.value == 0.9
    assert state.status.value == "active"
    assert state.access_count.value() == 0
    assert state.clock.get("nodeA") == 1
    
    # 2. Update content
    state_updated = engine.update_content("mem-1", "Updated Text")
    assert state_updated.content.value == "Updated Text"
    assert state_updated.clock.get("nodeA") == 2
    
    # 3. Reinforce (access count)
    state_reinforced = engine.reinforce("mem-1")
    assert state_reinforced.access_count.value() == 1
    assert state_reinforced.clock.get("nodeA") == 3
    
    # 4. Supersede
    state_superseded = engine.supersede("mem-1")
    assert state_superseded.status.value == "superseded"
    assert state_superseded.clock.get("nodeA") == 4
    
    # Check tracking list
    assert engine.all_memory_ids() == {"mem-1"}


def test_crdt_sync_engine_convergence():
    """Test eventual consistency: divergent nodes merge to identical states.

    Verifies mathematical convergence:
        All nodes merge independent changes and arrive at the exact same state,
        completely resolving concurrent updates, increments, and status changes.
    """
    node_a = CRDTSyncEngine("nodeA")
    node_b = CRDTSyncEngine("nodeB")
    
    # Node A creates the shared memory
    node_a.create_memory("shared-mem", "Seed text", confidence=0.5)
    
    # Sync initial state from A to B
    delta_a = node_a.export_delta()
    assert len(delta_a) == 1
    
    node_b.import_delta(delta_a)
    assert "shared-mem" in node_b.all_memory_ids()
    assert node_b.get_state("shared-mem").content.value == "Seed text"
    
    # Sleep to ensure unique monotonically increasing timestamps
    time.sleep(0.01)
    
    # DIVERGING ACTIONS:
    # Node A updates content and reinforces
    node_a.update_content("shared-mem", "Text written by A")
    node_a.reinforce("shared-mem")
    
    # Concurrent Node B reinforces access twice and supersedes status
    node_b.reinforce("shared-mem")
    node_b.reinforce("shared-mem")
    node_b.supersede("shared-mem")
    
    # Verify states are currently diverged
    state_a = node_a.get_state("shared-mem")
    state_b = node_b.get_state("shared-mem")
    assert state_a.content.value == "Text written by A"
    assert state_b.content.value == "Seed text"
    assert state_a.status.value == "active"
    assert state_b.status.value == "superseded"
    assert state_a.access_count.value() == 1
    assert state_b.access_count.value() == 2
    
    # SYNC / REPLICATION MERGE:
    # Export deltas
    delta_a_changes = node_a.export_delta()
    delta_b_changes = node_b.export_delta()
    
    # A imports B's changes, B imports A's changes
    node_a.import_delta(delta_b_changes)
    node_b.import_delta(delta_a_changes)
    
    # CONVERGENCE ASSERTS:
    final_a = node_a.get_state("shared-mem")
    final_b = node_b.get_state("shared-mem")
    
    # 1. State equality
    assert final_a.to_dict() == final_b.to_dict()
    
    # 2. Correct merged values:
    # - content: "Text written by A" wins (latest timestamp)
    assert final_a.content.value == "Text written by A"
    # - status: "superseded" wins (latest timestamp from B's write)
    assert final_a.status.value == "superseded"
    # - access_count: A reinforced (1) + B reinforced twice (2) = 3 total
    assert final_a.access_count.value() == 3
    # - clock: merged vector clock (A: 3, B: 3)
    assert final_a.clock.get("nodeA") == 3
    assert final_a.clock.get("nodeB") == 3
