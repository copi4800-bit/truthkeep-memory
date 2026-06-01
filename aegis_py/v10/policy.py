from __future__ import annotations
from typing import Any, Dict
from .models import DecisionObject, GovernanceStatus, TruthRole, RetrievableMode

CONFLICT_SEVERITY_THRESHOLD = 0.8
ENTROPY_THRESHOLD = 0.7
BUDGET_THRESHOLD = 0.8
LOW_RELEVANCE_THRESHOLD = 0.3

class MemoryConstitution:
    """The hierarchical law system for Aegis v10 memory governance."""
    
    # Precedence Levels
    LEVELS = {
        "C0": "SYSTEM_SAFETY",
        "C1": "USER_OVERRIDE",
        "C2": "CANONICAL_TRUTH",
        "C3": "GOVERNANCE_RISK",
        "C4": "SOFT_JUDGMENT"
    }

    def enforce(self, d: DecisionObject, m: Any, context: Dict[str, Any]) -> DecisionObject:
        """Applies the constitution in order of precedence (C0 -> C4)."""
        
        # --- C0: ZKP Access Control (Phase 5) ---
        zk_commit = getattr(m, "zk_commitment", None)
        if zk_commit:
            from ..security.zkp import ZKPPLONK3Simulator
            zk_proof = context.get("zk_proof")
            zk_challenge = context.get("zk_challenge")
            zkp_verified = False
            if zk_proof and zk_challenge:
                try:
                    commit_int = int(zk_commit)
                    zk_sim = ZKPPLONK3Simulator()
                    zkp_verified = zk_sim.verify_proof(commit_int, zk_challenge, zk_proof)
                except Exception:
                    pass
            
            if not zkp_verified:
                d.admissible = False
                d.governance_status = GovernanceStatus.REVOKED
                d.retrievable_mode = RetrievableMode.NONE
                d.policy_trace.append("C0_ZKP_AUTH_FAILURE")
                return d

        # --- C0: System Safety (Rule 4, 7) ---
        if self._violates_safety(m):
            d.admissible = False
            d.governance_status = GovernanceStatus.REVOKED
            d.retrievable_mode = RetrievableMode.NONE
            d.policy_trace.append("C0_SAFETY_VIOLATION")
            return d
            
        # --- C1: User Explicit Override (Rule 1) ---
        if context.get("intent") in ["user_override_active", "preference_lookup"]:
            if m.metadata.get("is_correction") or m.metadata.get("is_winner"):
                d.admissible = True
                d.governance_status = GovernanceStatus.ACTIVE
                d.truth_role = TruthRole.WINNER
                d.policy_trace.append("C1_USER_OVERRIDE_APPLIED")
            
        # --- C2: Canonical Truth (Rule 2, 3) ---
        if getattr(m.correction, "is_superseded", False):
            d.admissible = False
            d.governance_status = GovernanceStatus.SUPERSEDED
            d.retrievable_mode = RetrievableMode.AUDIT
            d.policy_trace.append("ARCHELON_SUPERSEDED_INVARIANT")
            d.policy_trace.append("C2_SUPERSEDED_EXCLUSION")
            return d

        if d.truth_role == TruthRole.WINNER:
            self._apply_archelon_winner_invariant(d, m)
            d.policy_trace.append("C2_SLOT_WINNER_PROTECTION")
            
        # --- C3: Governance Risk & Budget (Rule 4, 9, 11) ---
        conflict_severity = getattr(m.conflict, "unresolved_contradiction", 0.0)
        entropy = d.score_trace.factors.get("entropy", 0.0) if d.score_trace else 0.0
        
        # Rule 4: High Conflict Quarantine
        if conflict_severity > CONFLICT_SEVERITY_THRESHOLD:
            d.admissible = False
            d.governance_status = GovernanceStatus.QUARANTINED
            d.retrievable_mode = RetrievableMode.CONFLICT_PROBE
            d.policy_trace.append("C3_HIGH_CONFLICT_QUARANTINE")
            
        # Rule 9 & 11: Budget Pressure & Ambiguity Escalation
        budget_pressure = context.get("budget_pressure", 0.0)
        if (entropy > ENTROPY_THRESHOLD or budget_pressure > BUDGET_THRESHOLD) and d.governance_status != GovernanceStatus.ACTIVE:
            d.governance_status = GovernanceStatus.PENDING_REVIEW
            d.policy_trace.append("C3_AMBIGUITY_ESC_TO_REVIEW")

        # --- C4: Soft Judgment Adjustment ---
        score = context.get("score", 0.0)
        if score < LOW_RELEVANCE_THRESHOLD and d.governance_status not in [GovernanceStatus.ACTIVE, GovernanceStatus.SUPERSEDED]:
            d.admissible = False
            d.policy_trace.append("C4_LOW_RELEVANCE_SUPPRESSION")

        # Final synchronization
        if not d.admissible and d.retrievable_mode == RetrievableMode.NORMAL:
            if d.governance_status == GovernanceStatus.QUARANTINED:
                d.retrievable_mode = RetrievableMode.CONFLICT_PROBE
            elif d.governance_status == GovernanceStatus.PENDING_REVIEW:
                d.retrievable_mode = RetrievableMode.REVIEW_ONLY
            else:
                d.retrievable_mode = RetrievableMode.NONE
            
        return d

    def _apply_archelon_winner_invariant(self, d: DecisionObject, m: Any) -> None:
        """Enforce the Archelon Winner Invariant for slot winners.

        Winners with unresolved conflict above the severity threshold
        are left untouched.  Otherwise, the decision is forced to
        admissible/active/normal.

        Args:
            d: The DecisionObject being evaluated.
            m: The memory wrapper with conflict metadata.
        """
        conflict_severity = getattr(m.conflict, "unresolved_contradiction", 0.0)
        if conflict_severity > CONFLICT_SEVERITY_THRESHOLD:
            return
        d.admissible = True
        d.governance_status = GovernanceStatus.ACTIVE
        d.retrievable_mode = RetrievableMode.NORMAL
        d.policy_trace.append("ARCHELON_WINNER_INVARIANT")

    def _violates_safety(self, m: Any) -> bool:
        """Check whether a memory violates system safety rules.

        Detects illegal content keywords and cryptographic seal mismatches
        (Phase 4 tamper detection).

        Args:
            m: The memory wrapper to inspect.

        Returns:
            True if the memory should be blocked, False otherwise.
        """
        # Phase 4: Real safety filter — legacy + cryptographic integrity
        content_upper = m.content.upper()
        if "ILLEGAL_CONTENT" in content_upper:
            return True
        # Phát hiện ký ức bị can thiệp (tampered) qua cryptographic seal
        meta = getattr(m, "metadata", None) or {}
        if meta.get("integrity_warning") == "content_seal_mismatch":
            return True  # Tampered memory → block
        return False
