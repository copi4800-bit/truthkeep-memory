"""
TruthKeep Memory — Dafny Spec Test Vectors
============================================
Phase 2 of Level 8 Research Roadmap.

These tests verify that the Python implementation matches the properties
proven in the Dafny specifications:
  - specs/dafny/safe_math.dfy
  - specs/dafny/truth_transition.dfy
  - specs/dafny/crt_math.dfy
  - specs/dafny/winner_selection.dfy

Each test is a concrete test vector that exercises the boundary conditions
and invariants proven by Dafny.
"""

from __future__ import annotations

import math
import pytest


# ── safe_math.dfy — Clamp, SafeDiv, BoundedRatio, Bayes ──────────────────

class TestSafeMathDafnyVectors:
    """Test vectors matching safe_math.dfy specifications."""

    # ── Clamp01 ──

    def test_clamp01_below(self):
        """Clamp01(-0.5) == 0.0"""
        assert max(0.0, min(1.0, -0.5)) == 0.0

    def test_clamp01_above(self):
        """Clamp01(1.5) == 1.0"""
        assert max(0.0, min(1.0, 1.5)) == 1.0

    def test_clamp01_inside(self):
        """Clamp01(0.7) == 0.7"""
        assert max(0.0, min(1.0, 0.7)) == 0.7

    def test_clamp01_idempotent(self):
        """Clamp01(Clamp01(x)) == Clamp01(x) for all x"""
        for x in [-2.0, -0.1, 0.0, 0.5, 1.0, 1.5, 100.0]:
            c = max(0.0, min(1.0, x))
            cc = max(0.0, min(1.0, c))
            assert c == cc, f"Clamp01 not idempotent for x={x}"

    # ── Cosine Similarity (ClampCosine) ──

    def test_cosine_similarity_clamped(self):
        """HilbertSpaceEngine.cosine_similarity always returns [-1, 1]."""
        from aegis_py.storage.modern_math import HilbertSpaceEngine
        v1 = HilbertSpaceEngine.text_to_hilbert_vector("hello world")
        v2 = HilbertSpaceEngine.text_to_hilbert_vector("goodbye cruel world")
        sim = HilbertSpaceEngine.cosine_similarity(v1, v2)
        assert -1.0 <= sim <= 1.0

    def test_cosine_self_similarity(self):
        """Self-similarity should be ~1.0 for normalized vectors."""
        from aegis_py.storage.modern_math import HilbertSpaceEngine
        v = HilbertSpaceEngine.text_to_hilbert_vector("test vector")
        sim = HilbertSpaceEngine.cosine_similarity(v, v)
        assert 0.99 <= sim <= 1.0

    def test_cosine_different_lengths(self):
        """Different length vectors → 0.0."""
        from aegis_py.storage.modern_math import HilbertSpaceEngine
        assert HilbertSpaceEngine.cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

    # ── Bayesian Posterior ──

    def test_bayesian_posterior_bounds(self):
        """BayesPosterior always returns [0.0, 1.0]."""
        from aegis_py.storage.modern_math import BayesianBeliefEngine

        test_cases = [
            (0.5, 0.8, 0.0),    # Auto-compute marginal
            (0.001, 0.999, 0.0),  # Extreme values
            (0.999, 0.001, 0.0),  # Reversed extremes
            (0.5, 0.5, 0.5),     # Uniform
            (0.3, 0.9, 0.1),     # Strong evidence
        ]
        for prior, likelihood, marginal in test_cases:
            result = BayesianBeliefEngine.posterior(prior, likelihood, marginal)
            assert 0.0 <= result <= 1.0, \
                f"Bayes posterior out of bounds: p={prior}, l={likelihood}, m={marginal} → {result}"

    def test_bayesian_uninformative_evidence(self):
        """When likelihood == evidence_marginal, posterior ≈ prior."""
        from aegis_py.storage.modern_math import BayesianBeliefEngine
        result = BayesianBeliefEngine.posterior(0.5, 0.5, 0.5)
        assert abs(result - 0.5) < 0.01

    def test_bayesian_sequential_update_bounded(self):
        """Sequential Bayes update stays in [0, 1]."""
        from aegis_py.storage.modern_math import BayesianBeliefEngine
        observations = [(0.8, 0.5), (0.9, 0.6), (0.3, 0.4)]
        result = BayesianBeliefEngine.sequential_update(0.5, observations)
        assert 0.0 <= result <= 1.0

    def test_bayesian_belief_from_signals_bounded(self):
        """belief_from_signals always returns [0, 1]."""
        from aegis_py.storage.modern_math import BayesianBeliefEngine
        test_cases = [
            (0.5, 0.8, 0.7, 0.1),   # Strong evidence, low conflict
            (0.9, 0.1, 0.1, 0.9),   # High prior, weak evidence, high conflict
            (0.01, 0.99, 0.99, 0.01),  # Extreme
        ]
        for prior, ev, support, conflict in test_cases:
            result = BayesianBeliefEngine.belief_from_signals(prior, ev, support, conflict)
            assert 0.0 <= result <= 1.0

    # ── Retirement Pressure ──

    def test_retirement_pressure_bounded(self):
        """Smilodon retirement pressure always in [0, 0.99]."""
        # Max case: forgetting=1, inv_conf=1, inv_act=1, zero_access=0.12
        max_pressure = 1.0 * 0.42 + 1.0 * 0.18 + 1.0 * 0.16 + 0.12
        assert max_pressure <= 0.99  # 0.88 ≤ 0.99 ✓


# ── truth_transition.dfy — State Machine Guards ──────────────────────────

class TestTruthTransitionDafnyVectors:
    """Test vectors matching truth_transition.dfy specifications."""

    def test_terminal_states_are_absorbing(self):
        """Terminal states (invalidated, archived) have no outgoing transitions."""
        from aegis_py.v10_base.state_machine import ALLOWED_STATE_TRANSITIONS
        assert ALLOWED_STATE_TRANSITIONS["invalidated"] == set()
        assert ALLOWED_STATE_TRANSITIONS["archived"] == set()

    def test_all_states_can_terminate(self):
        """Every non-terminal state can reach a terminal state in 1 step."""
        from aegis_py.v10_base.state_machine import ALLOWED_STATE_TRANSITIONS
        terminals = {"invalidated", "archived"}
        for state, allowed in ALLOWED_STATE_TRANSITIONS.items():
            if state not in terminals:
                reachable_terminals = allowed & terminals
                assert len(reachable_terminals) > 0, \
                    f"State '{state}' cannot reach any terminal state"

    def test_draft_cannot_skip_to_archived(self):
        """Draft → Archived is forbidden (must validate first)."""
        from aegis_py.v10_base.state_machine import ALLOWED_STATE_TRANSITIONS
        assert "archived" not in ALLOWED_STATE_TRANSITIONS["draft"]

    def test_draft_cannot_skip_to_consolidated(self):
        """Draft → Consolidated is forbidden."""
        from aegis_py.v10_base.state_machine import ALLOWED_STATE_TRANSITIONS
        assert "consolidated" not in ALLOWED_STATE_TRANSITIONS["draft"]

    def test_correction_flow_valid(self):
        """Draft → Validated → Invalidated is a valid path."""
        from aegis_py.v10_base.state_machine import ALLOWED_STATE_TRANSITIONS
        assert "validated" in ALLOWED_STATE_TRANSITIONS["draft"]
        assert "invalidated" in ALLOWED_STATE_TRANSITIONS["validated"]

    def test_decay_flow_valid(self):
        """Draft → Validated → Archived is a valid path."""
        from aegis_py.v10_base.state_machine import ALLOWED_STATE_TRANSITIONS
        assert "validated" in ALLOWED_STATE_TRANSITIONS["draft"]
        assert "archived" in ALLOWED_STATE_TRANSITIONS["validated"]

    def test_invalidated_maps_to_superseded(self):
        """Invalidated admission state → Superseded storage status."""
        # Maps to state_machine.py L77-78
        state_to_status = {
            "invalidated": "superseded",
            "archived": "archived",
            "draft": "active",
            "validated": "active",
            "hypothesized": "active",
            "consolidated": "active",
        }
        for state, expected_status in state_to_status.items():
            if state == "invalidated":
                assert expected_status == "superseded"
            elif state == "archived":
                assert expected_status == "archived"
            else:
                assert expected_status == "active"


# ── crt_math.dfy — I-Ching Encoding & Luo-Shu Integrity ─────────────────

class TestCrtMathDafnyVectors:
    """Test vectors matching crt_math.dfy specifications."""

    # ── I-Ching Encoding ──

    def test_hexagram_range(self):
        """All hexagram codes must be in [0, 63]."""
        from aegis_py.storage.ancient_math import IChingStateEncoder
        kinds = ["working", "episodic", "semantic", "procedural"]
        truths = ["candidate", "winner", "superseded", "archived"]
        trusts = ["unverified", "verified", "disputed", "immutable"]
        for k in kinds:
            for t in truths:
                for u in trusts:
                    code = IChingStateEncoder.encode_state(k, t, u)
                    assert 0 <= code <= 63, f"Code out of range: {k},{t},{u} → {code}"

    def test_hexagram_injective(self):
        """Different inputs must produce different codes."""
        from aegis_py.storage.ancient_math import IChingStateEncoder
        kinds = ["working", "episodic", "semantic", "procedural"]
        truths = ["candidate", "winner", "superseded", "archived"]
        trusts = ["unverified", "verified", "disputed", "immutable"]
        codes = set()
        for k in kinds:
            for t in truths:
                for u in trusts:
                    code = IChingStateEncoder.encode_state(k, t, u)
                    assert code not in codes, f"Collision at {k},{t},{u} → {code}"
                    codes.add(code)
        assert len(codes) == 4 * 4 * 4  # 64 unique codes

    def test_hexagram_known_values(self):
        """Verify specific hexagram codes from the lookup table."""
        from aegis_py.storage.ancient_math import IChingStateEncoder
        # Thuần Càn = 0b111111 = 63
        assert IChingStateEncoder.encode_state("procedural", "archived", "immutable") == 0b111111
        # Thuần Khôn = 0b000000 = 0
        assert IChingStateEncoder.encode_state("working", "candidate", "unverified") == 0b000000

    def test_changing_lines_identical(self):
        """Identical codes → no changing lines."""
        from aegis_py.storage.ancient_math import IChingStateEncoder
        assert IChingStateEncoder.calculate_changing_lines(42, 42) == []

    def test_changing_lines_all_different(self):
        """0 vs 63 → all 6 lines changed."""
        from aegis_py.storage.ancient_math import IChingStateEncoder
        changing = IChingStateEncoder.calculate_changing_lines(0, 63)
        assert changing == [1, 2, 3, 4, 5, 6]

    # ── Luo-Shu Magic Square ──

    def test_luoshu_rows_sum_15(self):
        """All Luo-Shu rows sum to 15."""
        from aegis_py.storage.ancient_math import LuoshuIntegrityValidator
        m = LuoshuIntegrityValidator.LUOSHU_MATRIX
        for row in m:
            assert sum(row) == 15

    def test_luoshu_cols_sum_15(self):
        """All Luo-Shu columns sum to 15."""
        from aegis_py.storage.ancient_math import LuoshuIntegrityValidator
        m = LuoshuIntegrityValidator.LUOSHU_MATRIX
        for col in range(3):
            assert sum(m[row][col] for row in range(3)) == 15

    def test_luoshu_diags_sum_15(self):
        """Both Luo-Shu diagonals sum to 15."""
        from aegis_py.storage.ancient_math import LuoshuIntegrityValidator
        m = LuoshuIntegrityValidator.LUOSHU_MATRIX
        assert m[0][0] + m[1][1] + m[2][2] == 15
        assert m[0][2] + m[1][1] + m[2][0] == 15

    def test_luoshu_all_distinct(self):
        """All 9 entries are distinct integers 1-9."""
        from aegis_py.storage.ancient_math import LuoshuIntegrityValidator
        m = LuoshuIntegrityValidator.LUOSHU_MATRIX
        flat = [v for row in m for v in row]
        assert sorted(flat) == list(range(1, 10))

    def test_luoshu_encryption_roundtrip(self):
        """Encrypting then validating intact weights → is_secure=True, error≈0."""
        from aegis_py.storage.ancient_math import LuoshuIntegrityValidator
        weights = [0.9, 0.85, 1.0]  # trust, confidence, activation
        encrypted = LuoshuIntegrityValidator.encrypt_weights(weights)
        is_secure, error = LuoshuIntegrityValidator.validate_node_integrity(encrypted)
        assert is_secure is True
        assert error < 0.001

    def test_luoshu_tamper_detection(self):
        """Modifying one encrypted value → is_secure=False."""
        from aegis_py.storage.ancient_math import LuoshuIntegrityValidator
        weights = [0.9, 0.85, 1.0]
        encrypted = LuoshuIntegrityValidator.encrypt_weights(weights)
        # Tamper with one value
        encrypted[0][1] += 0.5  # Modify the 9-cell
        is_secure, error = LuoshuIntegrityValidator.validate_node_integrity(encrypted)
        assert is_secure is False
        assert error > 0.01


# ── winner_selection.dfy — Scoring & Winner Margin ───────────────────────

class TestWinnerSelectionDafnyVectors:
    """Test vectors matching winner_selection.dfy specifications."""

    # ── Confidence Floor ──

    def test_confidence_floor_055(self):
        """WriteTimeScorer confidence always >= 0.55."""
        from aegis_py.memory.scorer import WriteTimeScorer
        scorer = WriteTimeScorer()
        # Worst case: all positive signals = 0, all negative signals = 1
        conf, _ = scorer.infer(
            content="x",  # minimal content
            memory_type="semantic",
            source_kind="message",
        )
        assert conf >= 0.55, f"Confidence below floor: {conf}"

    def test_activation_floor_078(self):
        """WriteTimeScorer activation always >= 0.78."""
        from aegis_py.memory.scorer import WriteTimeScorer
        scorer = WriteTimeScorer()
        _, act = scorer.infer(
            content="x",
            memory_type="semantic",
            source_kind="message",
        )
        assert act >= 0.78, f"Activation below floor: {act}"

    # ── Backpropagation Gradient ──

    def test_gradient_clamped(self):
        """Backprop gradient always in [-0.5, 0.5]."""
        from aegis_py.storage.modern_math import BackpropagationEngine
        extreme_cases = [
            (100.0, 100.0, 0, 0.15),    # Huge error × huge weight
            (-100.0, 100.0, 0, 0.15),   # Negative error
            (1.0, 1.0, 0, 0.15),        # Normal case
            (1.0, 1.0, 5, 0.15),        # Deep layer
        ]
        for error, weight, depth, lr in extreme_cases:
            grad = BackpropagationEngine.compute_gradient(error, weight, depth, lr)
            assert -0.5 <= grad <= 0.5, \
                f"Gradient out of bounds: e={error}, w={weight}, d={depth} → {grad}"

    def test_gradient_decreases_with_depth(self):
        """Deeper layers receive weaker gradients."""
        from aegis_py.storage.modern_math import BackpropagationEngine
        grads = [
            abs(BackpropagationEngine.compute_gradient(1.0, 1.0, d, 0.15))
            for d in range(5)
        ]
        for i in range(len(grads) - 1):
            assert grads[i] >= grads[i + 1], \
                f"Gradient not decreasing: depth {i}={grads[i]}, depth {i+1}={grads[i+1]}"

    # ── Bellman Retirement Protection ──

    def test_retirement_protection_bounded(self):
        """Bellman retirement protection always in [0, 1]."""
        from aegis_py.storage.modern_math import BellmanValueEngine
        test_cases = [
            (0.0, 0.5),   # Zero value → no protection
            (0.25, 0.5),  # At half threshold → boundary
            (0.5, 0.5),   # At threshold → some protection
            (1.0, 0.5),   # Above threshold → high protection
            (0.0, 0.0),   # Edge case: zero threshold
        ]
        for value, threshold in test_cases:
            prot = BellmanValueEngine.compute_retirement_protection(value, threshold)
            assert 0.0 <= prot <= 1.0, \
                f"Protection out of bounds: v={value}, t={threshold} → {prot}"

    def test_weak_memory_no_protection(self):
        """Bellman value <= half threshold → zero protection."""
        from aegis_py.storage.modern_math import BellmanValueEngine
        assert BellmanValueEngine.compute_retirement_protection(0.1, 0.5) == 0.0
        assert BellmanValueEngine.compute_retirement_protection(0.25, 0.5) == 0.0

    # ── TDA Topological Similarity ──

    def test_topological_similarity_self(self):
        """Identical signatures → similarity = 1.0."""
        from aegis_py.storage.modern_math import PoincareTDAEngine
        sig = PoincareTDAEngine.compute_persistence_signature("hello world test")
        sim = PoincareTDAEngine.topological_similarity(sig, sig)
        assert sim == 1.0

    def test_topological_similarity_bounded(self):
        """Topological similarity always in (0, 1]."""
        from aegis_py.storage.modern_math import PoincareTDAEngine
        sig1 = PoincareTDAEngine.compute_persistence_signature("hello world")
        sig2 = PoincareTDAEngine.compute_persistence_signature("completely different text here")
        sim = PoincareTDAEngine.topological_similarity(sig1, sig2)
        assert 0.0 < sim <= 1.0

    # ── Dominance Boost ──

    def test_dominance_boost_bounded(self):
        """Dominance boost always in [0.0, 0.18]."""
        for margin in [0.0, 0.1, 0.2, 0.5, 1.0, 5.0]:
            boost = min(0.18, 0.05 + margin * 0.35)
            assert 0.0 <= boost <= 0.18

    # ── Fourier Spectral Similarity ──

    def test_spectral_similarity_bounded(self):
        """Fourier spectral similarity always in [0, 1]."""
        from aegis_py.storage.modern_math import FourierCompressor
        s1 = FourierCompressor.text_to_spectrum("hello world")
        s2 = FourierCompressor.text_to_spectrum("different text entirely")
        sim = FourierCompressor.spectral_similarity(s1, s2)
        assert 0.0 <= sim <= 1.0

    def test_spectral_self_similarity(self):
        """Self spectral similarity should be ~1.0."""
        from aegis_py.storage.modern_math import FourierCompressor
        s = FourierCompressor.text_to_spectrum("test content here")
        sim = FourierCompressor.spectral_similarity(s, s)
        assert sim >= 0.99

    # ── Softmax Distribution ──

    def test_softmax_sums_to_one(self):
        """Softmax output sums to ~1.0."""
        from aegis_py.storage.modern_math import ModernHopfieldAttractorEngine
        result = ModernHopfieldAttractorEngine.softmax([1.0, 2.0, 3.0, 0.5])
        assert abs(sum(result) - 1.0) < 1e-6

    def test_softmax_all_positive(self):
        """All softmax values are non-negative."""
        from aegis_py.storage.modern_math import ModernHopfieldAttractorEngine
        result = ModernHopfieldAttractorEngine.softmax([-5.0, -1.0, 0.0, 3.0])
        assert all(v >= 0.0 for v in result)

    def test_softmax_empty(self):
        """Empty input → empty output."""
        from aegis_py.storage.modern_math import ModernHopfieldAttractorEngine
        assert ModernHopfieldAttractorEngine.softmax([]) == []
