# Memory Aegis v10: The Constitutional Memory Engine

Welcome to the **Constitutional Edition** of Memory Aegis. Version 10 is not just a search engine or a scorer; it is a **Governance-First Truth & Policy Engine** with a 5-tier Constitutional policy pipeline that sits above the mathematical scoring layer.

## 🚀 What's New in v10

### 1. Constitutional Governance Engine (Hiến pháp cho Trí nhớ)
Unlike v9 which relied solely on residual scoring, v10 adds a **hard governance layer** that enforces truth regardless of score:

| Priority | Level | Function |
|---|---|---|
| 0 | `C0 SYSTEM_SAFETY` | Block illegal/harmful content |
| 1 | `C1 USER_OVERRIDE` | User corrections always win |
| 2 | `C2 CANONICAL_TRUTH` | Superseded facts are hard-excluded |
| 3 | `C3 GOVERNANCE_RISK` | Quarantine high-conflict memories |
| 4 | `C4 SOFT_JUDGMENT` | Filter low-relevance results |

### 2. Truth Registry (Sổ Đăng ký Sự thật)
Every "fact slot" (identified by subject) has exactly one **Winner** and zero or more **Contenders**:
- **Winner**: Always returned in normal recall. Protected by `C2_SLOT_WINNER_PROTECTION`.
- **Contender**: Pending review. Only surfaces in audit/explain mode.
- **Loser/Superseded**: Hard-excluded. Can never be returned in normal recall.
- **Margin-aware selection**: Winners must have a score margin > 0.2 to be auto-confirmed.

### 3. Zero-Locking Identity System
No hardcoded pronouns or verb lists. The system learns persona exclusively from explicit user commands:
- `"Gọi [X] là [Y]"` → Sets user honorific
- `"Xưng là [Z]"` → Sets assistant honorific
- Default: Neutral, professional tone

### 4. Zero-Config Facade API
```python
from aegis_py.facade import Aegis

aegis = Aegis.auto()
aegis.remember("Python là ngôn ngữ phổ biến nhất 2026")
results = aegis.recall("ngôn ngữ lập trình")
aegis.correct("Thực ra Rust mới là phổ biến nhất 2026")
print(aegis.status())
```

### 5. Review Queue with Priority Scoring
High-entropy or high-risk memories are automatically escalated:
```
Q_priority = risk * 0.4 + impact * 0.4 + ambiguity * 0.2
```

---

## 🔧 V10 Core (Still Active)

The v9 Residual Judgment Engine remains the scoring foundation:
```
S_final = S_base + Δ_judge + Δ_life + H_constraints
```

- `aegis_py/v9/scorer.py`: The mathematical brain with fortress calibration
- `aegis_py/v9/adapter.py`: Data mapper for raw storage → v9 signals
- `aegis_py/v9/translator.py`: Faithful human-readable explanations

---

## 🛠 Technical Implementation

### V10 Core Components
- `aegis_py/v10/engine.py`: Main `govern()` pipeline
- `aegis_py/v10/policy.py`: `MemoryConstitution` with C0-C4 enforcement
- `aegis_py/v10/truth_registry.py`: `resolve_slot_ownership()` with margin checks
- `aegis_py/v10/review.py`: `ReviewQueueV10` with priority scoring
- `aegis_py/v10/events.py`: `EventLogger` for full audit trail
- `aegis_py/v10/models.py`: `DecisionObject`, `GovernanceStatus`, `TruthRole`, `RetrievableMode`

### Integration Point (app.py)
V10 governance is wired into `search_payload()`:
```python
for r in results:
    decision = self.v10_engine.govern(r.memory, query_signals, intent)
    r.v10_decision = decision
    if decision.admissible and decision.retrievable_mode == NORMAL:
        governed_results.append(r)
```

### How to Run V10 Gauntlet
```bash
export PYTHONPATH=.
python3 scripts/v10_gauntlet_test.py
python3 scripts/super_stress_v10.py
```

---

*Memory Aegis v10: Because in the world of AI, Governance over Score is the only path to Truth.* 🛡️
