# TruthKeep v11 MCP Universal + Performance Modes Final Report

## Build name

`TruthKeep v11.0.0-alpha MCP Universal + Runtime Profiles`

## Source base

Started from `truthkeep-memory-v11-mcp-universal.zip` and added a Runtime Profiles / Performance Modes layer.

## Core preservation

The upgrade does **not** remove or replace TruthKeep's core:

- Memory correction
- Superseded suppression
- Why-not provenance
- Graph truth-governance
- Scope isolation
- Runtime invariants
- SQLite local storage
- MCP stdio-only / zero open ports

## New runtime layer

Added:

- `aegis_py/runtime/profile.py`
- `truthkeep profile show|list|set|doctor|clear`
- `truthkeep benchmark profiles`
- `scripts/profile_benchmark.py`
- Runtime profile awareness in security config
- Runtime profile env in generated MCP configs: `TK_RUNTIME_PROFILE=local`

## Profiles

- `demo`: quick demos and tests.
- `local`: default MCP/local use.
- `hardened`: strict privacy/security candidate; heavy engines are allowed but not automatically put into MCP hot path.
- `enterprise`: throughput-oriented profile for larger local workloads/many scopes.

## Hot path safety

Heavy simulator paths are guarded so normal MCP calls do not accidentally pay their cost. To explicitly run heavy simulators inside hot paths, set:

```bash
TK_ALLOW_HEAVY_HOT_PATH=1
```

This is intentionally not the default.

## Validation performed

- `python -m compileall -q aegis_py truthkeep scripts`
- `python -m pytest -q tests/runtime/test_runtime_profiles.py tests/mcp_compat/test_mcp_universal_profiles.py`
- `python -m truthkeep.cli profile doctor`
- `python -m truthkeep.cli mcp config generic`
- `python -m truthkeep.cli benchmark profiles --records 1`

## Known limitation

The profile benchmark is a small local hot-path regression guard, not a real enterprise load test. Real enterprise readiness still requires multi-agent operation tests, strict privacy hardening, and third-party audit if claiming audited security.
