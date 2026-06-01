# TruthKeep v11 Performance Modes Upgrade Report

This upgrade implements the Runtime Profiles / Performance Modes layer described in the user-supplied architecture note.

## Goal

Keep TruthKeep's mathematical/research core intact, but make runtime behavior configurable so MCP/local use stays fast and heavy simulator paths are not accidentally placed on every agent call.

## Added

- `aegis_py/runtime/profile.py`
- `aegis_py/runtime/__init__.py`
- `truthkeep profile show|list|set|doctor|clear`
- `truthkeep benchmark profiles`
- `scripts/profile_benchmark.py`
- `docs/RUNTIME_PROFILES.md`
- `docs/PERFORMANCE_MODES_RELEASE_NOTES_v11.md`
- `tests/runtime/test_runtime_profiles.py`

## Integrated

- MCP host configs now include `TK_RUNTIME_PROFILE=local`.
- `aegis_py/security/config.py` reports runtime profile and simulator flags.
- FHE/ZKP vector simulator path is gated so it does not run in normal hot-path MCP usage.
- Poincare/TDA diagnostics are gated behind runtime profile + explicit `TK_ALLOW_HEAVY_HOT_PATH=1`.

## Always-on TruthKeep DNA

These features remain enabled in all profiles:

- Graph governance
- Memory correction
- Superseded suppression
- Why-not provenance
- Runtime invariants

## Validation performed

- `python -m compileall -q aegis_py truthkeep scripts`
- `python -m pytest -q tests/runtime/test_runtime_profiles.py tests/mcp_compat/test_mcp_universal_profiles.py`
- `python -m truthkeep.cli profile doctor`
- `python -m truthkeep.cli mcp config generic`
- `python -m truthkeep.cli benchmark profiles --records 5`

## Important note

This is not a cloud/enterprise load-test result. It is a local hot-path regression guard. The correct next step is real MCP usage across OpenClaw/Cursor/Claude/Cline/Roo/Continue on real machines.
