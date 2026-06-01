<![CDATA[<div align="center">

# 🧠 TruthKeep Memory

### The Memory Engine That Knows What's Still True

[![CI/CD](https://github.com/copi4800-bit/truthkeep-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/copi4800-bit/truthkeep-memory/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v11.0--alpha-orange.svg)](docs/VERSION.md)

**TruthKeep is a local-first, governed memory engine for AI agents and MCP hosts.**
<br>It doesn't just store facts — it tracks which facts are *still true*, explains *why*, and proves *how it decided*.

</div>

---

## Why TruthKeep?

Most AI memory systems are glorified key-value stores. They remember everything, forget nothing, and when facts change, old information silently leaks back into context — causing hallucinations.

**TruthKeep solves this with truth governance:**

| Problem | TruthKeep's Answer |
|---|---|
| Old facts leak back | Superseded memories are **quarantined**, never returned silently |
| No audit trail | Every decision has a **full provenance chain** — who changed what, when, and why |
| "Why did it say that?" | **Explainable retrieval** — every result comes with why-this and why-not reasoning |
| Conflicting facts | **Constitutional Memory** — 5-level precedence hierarchy resolves disputes automatically |
| Privacy & security | **Zero-dependency crypto stack** — AES-256-GCM, ZKP, post-quantum, FHE, differential privacy |
| Single-node only | **CRDT-ready** — VectorClock, LWW-Register, OR-Set for eventual consistency |

---

## ⚡ Quick Start

### Windows

```text
installers/INSTALL_TRUTHKEEP_WINDOWS.cmd
```

### macOS / Linux

```bash
chmod +x ./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
```

### Python API

```python
from truthkeep import TruthKeep

tk = TruthKeep.auto()

# Store a fact
tk.remember("Mimi's favorite drink is Bubble Tea.", subject="mimi.drink")

# Correct it — old fact becomes superseded, not deleted
tk.correct("Correction: Mimi's favorite drink is Peach Tea.", subject="mimi.drink")

# Recall returns ONLY the current truth
results = tk.recall("What is Mimi's favorite drink?")
print(results[0]["memory"]["content"])
# → "Correction: Mimi's favorite drink is Peach Tea."
```

### MCP Server

```bash
pip install -e .
truthkeep-mcp
```

---

## 🏛️ Architecture

### Constitutional Memory (V10 Governance)

Every memory decision is governed by a 5-level Constitution — inspired by legal systems, not heuristics:

```
C0: SYSTEM_SAFETY     — ZKP auth + content safety + tamper detection
C1: USER_OVERRIDE      — Explicit user corrections always honored
C2: CANONICAL_TRUTH    — Superseded exclusion + Winner Invariant
C3: GOVERNANCE_RISK    — High-conflict quarantine + ambiguity escalation
C4: SOFT_JUDGMENT      — Low relevance suppression
```

Each memory has a **governance status** (candidate → active → disputed → superseded → archived) and a **truth role** (winner / contender / loser). Only one winner per fact-slot per scope.

### 23-Beast Architecture

TruthKeep's internals are organized as 23 specialized "beasts" — each responsible for a single concern:

| Beast | Domain | What It Does |
|---|---|---|
| 🦎 **Axolotl** | Schema | Soft repair, FTS rebuild, orphan cleanup |
| 📚 **Librarian** | Consolidation | Merge equivalent memories, index locality reports |
| 🔩 **Nutcracker** | Storage | VACUUM, compaction pressure, DB health |
| 🐦 **Bowerbird** | Taxonomy | Subject normalization, drift detection |
| 🦷 **Smilodon** | Decay | Type-specific half-lives, Fibonacci decay, crystallization |
| 🐒 **Meerkat** | Conflicts | Contradiction detection, quarantine escalation |
| 🕵️ **Explainer** | Trust | Trust shapes (strong/weak/uncertain), provenance |
| 🛡️ **Guardian** | Security | Boundary protection, scope isolation |
| ... | ... | *23 total, compressed into 6 lean runtime modules* |

### 10-Signal Dynamics Engine

Every memory carries 10 real-time signals, updated on every interaction:

```
evidence · support · conflict · usage · regret
stability · decay · belief · trust · readiness
```

- **Bayesian Belief Update**: Blends Bayesian posterior (70%) with legacy model (30%)
- **Trust Score**: Sigmoid aggregation across all signals
- **Transition Gates**: Auto-promote (draft → validated) or demote based on signal thresholds
- **Outcome Feedback Loop**: Success/relevance scores propagate back to improve future retrieval

---

## 🔐 Security Stack

All cryptography is **pure Python — zero external dependencies**:

| Layer | Technology | Purpose |
|---|---|---|
| **Encryption** | AES-256-GCM | Encrypted backup/restore with PBKDF2 key derivation |
| **Access Control** | Schnorr/PLONK ZKP | Zero-knowledge proof gates — memory-level access without revealing keys |
| **Post-Quantum** | ML-KEM (Kyber) + ML-DSA (Dilithium) | Lattice-based crypto, quantum-resistant |
| **Homomorphic** | Ring-LWE FHE + Paillier | Compute similarity scores on encrypted data |
| **Privacy** | Bayesian DP + Rényi DP | Membership inference detection, Laplace noise, budget tracking |
| **Audit** | HMAC-SHA256 Chain | Append-only hash-chained audit log, tamper detection |
| **Integrity** | Luoshu Magic Square | Weight tamper detection via matrix ratio consistency |
| **Poison Detection** | Shannon Entropy | Prompt injection detection via entropy analysis |

---

## 📐 Mathematical Engines

TruthKeep embeds **20+ mathematical engines** for retrieval, scoring, and integrity:

<details>
<summary><b>Ancient Mathematics</b></summary>

- **I-Ching State Encoder** — 64 hexagram states (6-bit binary) encoding memory kind + truth state + trust level. Changing Lines (Hào Động) detection for state transitions
- **Luoshu Integrity Validator** — Magic square tamper detection via matrix invariants
- **Platonic Quantizer** — Icosahedron vertex projection for vector quantization
- **Fibonacci Decay Engine** — Golden ratio non-linear decay (φ^(-t/24))

</details>

<details>
<summary><b>Modern Mathematics</b></summary>

- **Hilbert Space Engine** — N-gram hashing → 64-dim vector + cosine similarity
- **Nash Embedding Preserver** — Johnson-Lindenstrauss random projection, distortion monitoring
- **Erdős Index Grid** — 8×8 grid cell assignment for O(N/K²) search
- **Poincaré TDA Engine** — Topological data analysis via Betti numbers (β₀, β₁, β₂)
- **Euler-Cayley Graph Engine** — Degree + betweenness centrality, hub detection
- **Bayesian Belief Engine** — Sequential belief update with evidence accumulation
- **Fourier Compressor** — DFT character frequency fingerprinting
- **Backpropagation Engine** — Gradient propagation through memory graph on corrections
- **Bellman Value Engine** — Strategic value for procedural memories, retirement protection
- **Hopfield Attractor Engine** — Lyapunov attractor dynamics for recall
- **Spectral Graph Engine** — Eigenvalue-based graph analysis
- **Hyperbolic Graph Engine** — Poincaré disk embeddings
- **Category Theory Functor Engine** — Compositional memory transformations
- *...and more*

</details>

---

## 🖥️ Desktop GUI

Premium dark-theme desktop application built with **PySide6 (Qt6)**:

- **Dashboard** — Real-time stats: total memories, active, conflicts, invariants, security mode
- **Memory Browser** — Search, filter by scope/status, inspect with why-not analysis
- **Correction History** — Full timeline of superseded facts with change reasons
- **Backup & Security** — AES-256-GCM encrypted backup/restore with passphrase

Zero network ports. Connects directly to the local SQLite database.

---

## 🔧 MCP Tools

### Easy Mode (5 tools — default)

| Tool | Purpose |
|---|---|
| `memory_remember` | Store a new memory |
| `memory_recall` | Search with governed truth filtering |
| `memory_correct` | Correct an outdated fact |
| `memory_status` | System health at a glance |
| `memory_profile` | User interaction profile |

### Advanced Mode (40+ tools)

<details>
<summary><b>Full tool catalog</b></summary>

**Truth & Governance:**
`memory_core_showcase` · `memory_experience_brief` · `memory_spotlight` · `memory_context_pack` · `memory_governance` · `memory_v10_field_snapshot`

**Conflict Resolution:**
`memory_conflict_prompt` · `memory_conflict_resolve`

**Graph & Links:**
`memory_link_store` · `memory_link_neighbors` · `memory_evidence_artifacts` · `memory_visualize`

**Health & Maintenance:**
`memory_doctor` · `memory_clean` · `memory_rebuild` · `memory_scan` · `memory_taxonomy_clean`

**Storage & Sync:**
`memory_storage_compact` · `memory_storage_footprint` · `memory_compressed_tier_status` · `memory_sync_export` · `memory_sync_preview` · `memory_sync_import`

**Backup & Restore:**
`memory_backup_upload` · `memory_backup_list` · `memory_backup_preview` · `memory_backup_download`

**Background Operations:**
`memory_background_plan` · `memory_background_shadow` · `memory_background_apply` · `memory_background_rollback`

**Shells & Workflows:**
`memory_consumer_shell` · `memory_workflow_shell` · `memory_dashboard_shell` · `memory_command_center_shell` · `memory_truth_transition_timeline`

</details>

---

## 🛡️ Runtime Invariants

TruthKeep enforces **5 database invariants** on every operation — violations are detected and reported automatically:

1. **Unique Winner** — At most 1 active memory per fact-slot per scope
2. **No Superseded Leakage** — Superseded memories never appear as active truth
3. **Archived Isolation** — Archived memories never resurface
4. **Why-Not Provenance** — Every suppressed memory has a documented reason
5. **Scope Isolation** — Links never cross scope boundaries

---

## 🏗️ Developer Setup

```bash
# Install
pip install -e .

# Run tests (350+ tests)
python -m pytest tests -q

# Verify enterprise release
python scripts/verify_enterprise_release.py

# Start MCP server
truthkeep-mcp
```

---

## 📦 Enterprise Release

This package includes:

- One-click installer launchers for Windows, macOS, and Linux
- Platform signing scripts (Authenticode, notarization, GPG)
- `ENTERPRISE_RELEASE_MANIFEST.json` with SHA256 integrity metadata
- Release verification gate (`scripts/verify_enterprise_release.py`)

📖 **Docs:** [Enterprise Guide](docs/ENTERPRISE_INSTALLER_GUIDE.md) · [Signing](docs/SIGNING_AND_NOTARIZATION.md) · [IT Admin](docs/IT_ADMIN_DEPLOYMENT.md) · [Limitations](docs/ENTERPRISE_LIMITATIONS.md)

---

## 🔒 Security Posture

TruthKeep v11 is:

- ✅ **Local-first** — SQLite, no cloud
- ✅ **MCP stdio** — no HTTP daemon
- ✅ **Zero open ports** — no TCP/UDP listeners
- ✅ **Encrypted at rest** — AES-256-GCM backup
- ✅ **Post-quantum ready** — ML-KEM + ML-DSA
- ✅ **Differentially private** — Bayesian DP + Rényi budget
- ⚠️ **Not externally audited** — enterprise-installer-ready, not audit-certified

---

## 📄 License

[MIT License](LICENSE)

<div align="center">

---

*TruthKeep doesn't try to remember more. It tries to remember correctly.*

</div>
]]>
