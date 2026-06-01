# TruthKeep Memory

**The memory engine that knows what's still true.**

[![CI/CD](https://github.com/copi4800-bit/truthkeep-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/copi4800-bit/truthkeep-memory/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![v11.0-alpha](https://img.shields.io/badge/version-v11.0--alpha-orange.svg)](docs/VERSION.md)

TruthKeep is a local-first memory engine for AI agents and MCP hosts. It doesn't just store facts — it governs them. When facts change, old information is superseded, not silently leaked. Every retrieval result comes with *why this was selected* and *why the alternatives were not*.

> Most AI memory is a key-value store that causes hallucinations when facts change.
> TruthKeep is a **governed truth system** that prevents them.

---

## Quick Start

**Windows** — double-click `installers/INSTALL_TRUTHKEEP_WINDOWS.cmd`

**macOS / Linux:**
```bash
chmod +x ./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh && ./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
```

**Python:**
```python
from truthkeep import TruthKeep

tk = TruthKeep.auto()
tk.remember("Mimi's favorite drink is Bubble Tea.", subject="mimi.drink")
tk.correct("Correction: Mimi's favorite drink is Peach Tea.", subject="mimi.drink")

results = tk.recall("What is Mimi's favorite drink?")
print(results[0]["memory"]["content"])
# → "Correction: Mimi's favorite drink is Peach Tea."
# The old fact is superseded — it will never leak back.
```

**MCP Server:**
```bash
pip install -e .
truthkeep-mcp
```

---

## What Makes TruthKeep Different

### 🏛️ Constitutional Memory

Every memory decision passes through a 5-level Constitution:

- **C0 — System Safety:** ZKP authentication, content safety, tamper detection
- **C1 — User Override:** Explicit corrections are always honored
- **C2 — Canonical Truth:** Only one winner per fact-slot — superseded facts are excluded
- **C3 — Governance Risk:** High-conflict memories are quarantined for review
- **C4 — Soft Judgment:** Low-relevance results are suppressed

Each memory has a governance status (`candidate → active → disputed → superseded → archived`) and a truth role (`winner / contender / loser`).

### 🐾 23-Beast Architecture

The engine is built from 23 specialized internal modules ("beasts"), each owning a single concern:

**Retrieval** — Explainer (trust shapes) · Scout (FTS recall) · Reranker (result shaping) · Navigator (graph expansion) · Scope (anti-leak filtering)

**Hygiene** — Librarian (semantic merge) · Nutcracker (VACUUM & compaction) · Axolotl (schema repair) · Bowerbird (taxonomy cleanup) · Smilodon (decay & crystallization)

**Governance** — Meerkat (conflict detection) · Guardian (boundary protection) · Constitution (policy discipline)

All 23 beasts are compressed into **6 lean runtime modules** — no bloat.

### ⚡ 10-Signal Dynamics

Every memory carries 10 live signals updated on every interaction:

```
evidence · support · conflict · usage · regret · stability · decay · belief · trust · readiness
```

Bayesian belief updates, sigmoid trust aggregation, automatic state transitions (draft → validated → consolidated), and outcome feedback loops that improve retrieval over time.

### 🛡️ 5 Runtime Invariants

Enforced on every operation — violations are auto-detected:

1. **Unique Winner** — one active truth per fact-slot per scope
2. **No Superseded Leakage** — old facts never resurface
3. **Archived Isolation** — archived memories stay archived
4. **Why-Not Provenance** — every suppressed result has a reason
5. **Scope Isolation** — links never cross scope boundaries

---

## Security

All cryptography is **pure Python — zero external dependencies:**

- **AES-256-GCM** — encrypted backup/restore with PBKDF2 key derivation
- **Zero-Knowledge Proofs** — Schnorr/PLONK-style access gates
- **Post-Quantum Crypto** — ML-KEM (Kyber) + ML-DSA (Dilithium), lattice-based
- **Fully Homomorphic Encryption** — Ring-LWE FHE + Paillier for encrypted vector scoring
- **Differential Privacy** — Bayesian DP, Rényi DP budget tracking, Laplace noise injection
- **HMAC-SHA256 Audit Chain** — append-only, hash-chained, tamper-evident
- **Shannon Entropy Poison Detection** — prompt injection defense

---

## Mathematical Engines

TruthKeep embeds 20+ mathematical engines — not as gimmicks, but as core scoring and integrity infrastructure:

**Spatial:** Hilbert Space vectors · Nash embedding preservation · Erdős grid search · Poincaré TDA (Betti numbers) · Euler-Cayley graph centrality · Hyperbolic embeddings

**Operational:** Bayesian belief update · Fourier fingerprinting · Backpropagation through memory graph · Bellman strategic value · Hopfield attractor recall · Markov cognitive chains

**Integrity:** I-Ching state encoding (64 hexagrams) · Luoshu magic square tamper detection · Platonic icosahedron quantization · Fibonacci golden-ratio decay

---

## MCP Tools

**Easy Mode** (5 tools — default for end users):

`memory_remember` · `memory_recall` · `memory_correct` · `memory_status` · `memory_profile`

**Advanced Mode** (40+ tools for developers):

Truth & governance · conflict resolution · graph links · evidence artifacts · health diagnostics · storage compaction · sync envelopes · encrypted backup · background operations · workflow shells · visualization

See [`openclaw.plugin.advanced.json`](openclaw.plugin.advanced.json) for the full catalog.

---

## Desktop GUI

Premium dark-theme application built with PySide6 (Qt6):

- **Dashboard** — live stats, invariant checks, security mode
- **Memory Browser** — search, filter, inspect with why-not analysis
- **Correction History** — full supersession timeline
- **Backup & Security** — AES-256-GCM encrypted backup/restore

Zero network ports. Local SQLite only.

---

## Developer Setup

```bash
pip install -e .
python -m pytest tests -q          # 350+ tests
python scripts/verify_enterprise_release.py
truthkeep-mcp                      # start MCP server
```

---

## Enterprise

One-click installers for Windows, macOS, and Linux. Platform signing scripts (Authenticode, notarization, GPG). SHA256 integrity manifest. Release verification gate.

**Docs:** [Enterprise Guide](docs/ENTERPRISE_INSTALLER_GUIDE.md) · [Signing](docs/SIGNING_AND_NOTARIZATION.md) · [IT Admin](docs/IT_ADMIN_DEPLOYMENT.md) · [Limitations](docs/ENTERPRISE_LIMITATIONS.md)

---

## Security Posture

- ✅ Local-first — SQLite, no cloud
- ✅ MCP stdio — no HTTP daemon
- ✅ Zero open ports
- ✅ Encrypted at rest — AES-256-GCM
- ✅ Post-quantum ready — ML-KEM + ML-DSA
- ✅ Differentially private — Bayesian DP + Rényi budget
- ⚠️ Not externally audited

---

## License

[MIT](LICENSE)

---

*TruthKeep doesn't try to remember more. It tries to remember correctly.*
