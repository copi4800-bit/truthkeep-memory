# TruthKeep v11 MCP Universal Upgrade — Release Notes

## Release name

```text
TruthKeep v11.0.0-alpha MCP Universal Memory Engine
```

## Purpose

This upgrade turns TruthKeep into a broader **local MCP memory engine** for multiple AI agent hosts while preserving the existing memory core.

It does not change the core philosophy:

```text
Not more memory. Truer memory.
Correctness-first. Long-horizon. Truth-governed.
```

## What changed

### Added Universal MCP host profiles

New module:

```text
aegis_py/mcp_universal.py
```

Supported profiles:

```text
openclaw
claude
cursor
cline
roo
continue
vscode
generic
```

### Added MCP universal CLI commands

```bash
truthkeep mcp list-hosts
truthkeep mcp config <host>
truthkeep mcp install <host>
truthkeep mcp doctor <host>
truthkeep mcp smoke-test <host>
truthkeep mcp export-matrix
```

### Added docs

```text
docs/MCP_UNIVERSAL_MEMORY_ENGINE.md
docs/MCP_COMPATIBILITY.md
docs/MCP_HOST_PROFILES.md
docs/MCP_SECURITY_NOTES.md
```

### Added examples

```text
examples/mcp/generic_mcp_config.json
examples/mcp/claude_desktop_config_snippet.json
examples/mcp/cursor_mcp_json_snippet.json
```

### Added tests

```text
tests/mcp_compat/test_mcp_universal_profiles.py
```

## What did not change

The following were intentionally left untouched:

```text
memory core
graph truth-governance
correction/superseded/why-not logic
invariants
security posture
SQLite local-first storage
MCP stdio-only transport
```

## Validation performed

```text
python -m compileall -q aegis_py truthkeep
python -m pytest -q tests/mcp_compat/test_mcp_universal_profiles.py tests/test_phase_132_openclaw_plugin_hardening.py tests/test_phase_133_openclaw_native_adapter.py
python -m truthkeep.cli mcp list-hosts
python -m truthkeep.cli mcp config generic
python -m truthkeep.cli mcp install generic --dry-run
python -m truthkeep.cli --db-path /tmp/tk_mcp_universal_test.db mcp smoke-test generic
```

Result:

```text
compileall: PASS
focused tests: 13 passed
mcp list-hosts: PASS
mcp config generic: PASS
mcp install generic --dry-run: PASS
mcp smoke-test generic: PASS
```

## Important limitation

This release adds **host profiles and generated configurations**. It does not claim every host GUI has been tested on every OS. Real-machine testing is still required for each host/version.

## Correct claim

```text
TruthKeep is now MCP-universal-profile-ready.
```

Not:

```text
Every MCP host is guaranteed 100% validated on every platform.
```
