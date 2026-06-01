# Changelog

All notable changes to TruthKeep Memory are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v10.7-secure-mcp-stdio-dev-beta] — 2026-05-27

### Phase 7C — v10.7-secure-mcp-stdio: Zero Open Ports Security Model

#### Added
- **MCP Stdio JSON-RPC Real Probe**: Added `truthkeep mcp-probe` command executing a live stdio subprocess test (spawn, initialize handshake, discover tools, read output, check timeouts, and terminate cleanly).
- **Zero Open Ports Scanner script**: Added `scripts/check_no_open_ports.py` to verify that no TCP/UDP listening interfaces are bound or opened during TruthKeep executions.
- **MCP Stdio Cursor/Claude integration configurations**: Added copy-pasteable configuration guides.

#### Changed
- **Zero Network Exposure**: Removed local HTTP daemon sidecar, local TCP server, local routes, and bearer token auth, guaranteeing 100% loopback isolation with no open ports.
- **FastMCP Stdio Integration**: Wired `truthkeep-mcp` to launch a real stdio JSON-RPC FastMCP server when spawned without arguments, making it perfectly compatible with Cursor, Claude Desktop, and OpenClaw.
- **SQLite direct commands**: Redirected `status` and `dashboard` to query the local SQLite DB directly, preventing network overhead.

## [v10.6.0] — 2026-05-27

### Phase 7B — Professional Packaging, Clean Benchmarks & Robust CLI Sidecar

#### Added
- **Full CLI ASCII Dashboard**: Added `truthkeep dashboard` displaying SQLite size, active/superseded counts, health status, and live daemon information.
- **CLI logs following**: Added `truthkeep logs` with `--tail N` and `--follow` (`-f`) for real-time monitoring with clean Ctrl+C exiting.
- **CLI restart**: Added `truthkeep restart` for clean daemon refresh.
- **Quickstart Guide**: Added `QUICKSTART_5_MINUTES.md` for rapid onboarding.
- **Keystore tested matrix**: Added `INSTALL.md` with supported Python matrix (3.11-3.12).
- **Rich Examples Library**: Added configurations for Claude Desktop, Cursor, OpenClaw, and integrated Mimi Robot via client sidecar protocol.
- **Seeded & JSON Benchmarks**: Ablation study script now supports `--seed`, `--cases` (up to 300), and custom JSON data outputs.

#### Changed
- **Readiness Probe**: Upgraded `truthkeep start --background` to block 1.5 seconds and check child PID, logs traceback error detection, and DB health connection.
- **Scientific wording**: Cleaned claims across all docs (e.g. proof sketches, TDA-inspired, simulators).
- **Hardened mode warning**: Active hardened mode now triggers explicit runtime warning.

## [v10.4.0] — 2026-05-26

### Phase 4 — Classical Cryptography

#### Added
- **RSA Key Generation** via Extended Euclidean Algorithm (Euclid, 300 BCE)
  - `EuclidKeyForge` class with `extended_gcd()`, `mod_inverse()`, `generate_rsa_params()`
  - Miller-Rabin primality testing with 20 witness rounds
  - `RSAKeyBundle` dataclass with full key components (n, e, d, p, q)
- **Euler-Fermat Cipher** for memory encryption/decryption
  - `EulerFermatCipher` with `encrypt_int()`, `decrypt_int()`, `encrypt_bytes()`, `decrypt_bytes()`
  - Block-based encryption with automatic padding and hex serialization
- **Chinese Remainder Theorem** acceleration for decryption
  - `ChineseRemainderAccelerator` with `crt_decrypt()` — 4× faster than direct path
  - Garner's algorithm for combining partial results
  - General CRT solver for multi-modulus systems
- **Bayesian Privacy Guard** against Membership Inference Attacks
  - `BayesianPrivacyGuard` with `compute_leakage_risk()`, `apply_laplace_noise()`, `should_suppress()`
  - Sequential Bayesian leakage update for probing detection
- **SHA-256 Content Sealing** with `compute_content_seal()` and `verify_content_seal()`
- **Key Manager** for per-scope RSA key lifecycle (`key_manager.py`)
- **Memory Vault** for transparent encrypt/decrypt layer (`memory_vault.py`)
- **Differential Privacy Shield** with query tracking and probe detection (`privacy_guard.py`)

## [v10.3.0] — 2026-05-26

### Phase 3 — Operational Formulas

#### Added
- **Bayesian Belief Engine** (Thomas Bayes, 1763)
  - `BayesianBeliefEngine` with `posterior()`, `sequential_update()`, `belief_from_signals()`
  - Dynamic confidence updates from v10 evidence/support/conflict signals
- **Fourier Compressor** (Joseph Fourier, 1822)
  - `FourierCompressor` with `text_to_spectrum()`, `spectral_similarity()`, `spectral_fingerprint_hex()`
  - Character frequency DFT for memory fingerprinting
  - Integration with compressed prefilter pipeline
- **Backpropagation Engine** (Rumelhart & Hinton, 1986)
  - `BackpropagationEngine` with `compute_gradient()`, `propagate_correction()`, `chain_rule_decompose()`
  - Correction propagation through memory link graph (max depth=2)
- **Bellman Value Engine** (Richard Bellman, 1957)
  - `BellmanValueEngine` with `value_iteration()`, `compute_strategic_value()`, `compute_retirement_protection()`
  - Strategic value assessment for procedural memories
  - Integration with decay/retirement hygiene pipeline

## [v10.2.0] — 2026-05-26

### Phase 2 — Spatial Architecture

#### Added
- **Hilbert Space Engine** (David Hilbert, 1900s)
  - `HilbertSpaceEngine` with `text_to_hilbert_vector()`, `cosine_similarity()`, `hilbert_distance()`
  - Character n-gram hashing into 64-dimensional Hilbert space
  - L2-normalized vectors for unit-sphere cosine similarity
- **Nash Embedding Preserver** (John Nash, 1956)
  - `NashEmbeddingPreserver` with `compute_distortion_ratio()`, `nash_isometric_projection()`
  - Distortion monitoring for compressed prefilter quality
- **Erdős Index Grid** (Paul Erdős, 1946)
  - `ErdosIndexGrid` with `assign_grid_cell()`, `compute_unit_distance_neighbors()`
  - 8×8 spatial grid for O(N/K²) search optimization
- **Poincaré TDA Engine** (Henri Poincaré, 1895)
  - `PoincareTDAEngine` with `compute_persistence_signature()`, `topological_similarity()`
  - Betti numbers (β₀, β₁, β₂) for topological text fingerprinting
- **Euler/Cayley Graph Engine** (Euler 1736, Cayley 1878)
  - `EulerCayleyGraphEngine` with `compute_degree_centrality()`, `compute_betweenness_centrality()`, `find_hub_nodes()`
  - Knowledge graph centrality analysis for link expansion

## [v10.1.0] — 2026-05-26

### Phase 1 — Ancient Eastern Mathematics

#### Added
- **I Ching State Encoder** (易經, c. 1000 BCE)
  - `IChingStateEncoder` with 6-bit hexagram encoding for memory states
  - Changing line detection (Hào Động) via XOR for state transitions
- **Luoshu Integrity Validator** (洛書, c. 650 BCE)
  - `LuoshuIntegrityValidator` with magic square weight encryption and tamper detection
- **Platonic Quantizer** (Plato, c. 360 BCE)
  - `PlatonicQuantizer` with icosahedron vertex projection using golden ratio φ
- **Fibonacci Decay Engine** (Leonardo Fibonacci, 1202)
  - `FibonacciDecayEngine` with golden ratio non-linear priority decay
- Integration function `compute_memory_ancient_math_fields()` for write-time computation

## [v10.0.0] — 2026-04-03

### Base v10 Release

#### Added
- Truth-aware memory selection with `winner / contender / superseded` states
- Correction-first design — new corrections cleanly replace old facts
- `why this / why not` explainability for retrieval results
- Governed recall — policy and truth state influence what is returned
- Spotlight and full-core showcase demo surfaces
- Long-horizon hygiene: decay, consolidation, archive behavior
- Local SQLite storage with MCP/OpenClaw-compatible surfaces
- Compressed retrieval tier (TurboQuant-inspired software prefilter)
- v10 field snapshot with Xi(t) state exposure
- Standalone CLI entry points (`truthkeep` command)
- Consumer shell, dashboard shell, workflow shell UX
- Experience brief and truth transition timeline surfaces
- 185 tests passing across full suite

[v10.4.0]: https://github.com/truthkeep/truthkeep-memory/compare/v10.3.0...v10.4.0
[v10.3.0]: https://github.com/truthkeep/truthkeep-memory/compare/v10.2.0...v10.3.0
[v10.2.0]: https://github.com/truthkeep/truthkeep-memory/compare/v10.1.0...v10.2.0
[v10.1.0]: https://github.com/truthkeep/truthkeep-memory/compare/v10.0.0...v10.1.0
[v10.0.0]: https://github.com/truthkeep/truthkeep-memory/releases/tag/v10.0.0
