# TruthKeep v11 Performance Modes Release Notes

This upgrade adds Runtime Profiles / Performance Modes on top of the existing MCP Universal build.

## What changed

- Added `aegis_py/runtime/profile.py`.
- Added CLI commands under `truthkeep profile`.
- Added `truthkeep benchmark profiles`.
- MCP host configs now include `TK_RUNTIME_PROFILE=local` by default.
- Heavy FHE/TDA simulator paths are gated by runtime flags.
- Security config now reports runtime profile and simulator flags.
- Added runtime profile tests.

## What did not change

The core remains intact:

- Memory correction
- Superseded suppression
- Why-not provenance
- Graph truth-governance
- Scope isolation
- Runtime invariants
- MCP stdio-only / no HTTP daemon

## Recommended defaults

For OpenClaw/Cursor/Claude/Cline/Roo/Continue use:

```bash
truthkeep profile set local
truthkeep mcp install <host>
```

For heavier local security experiments:

```bash
truthkeep profile set hardened
```

For many agents/scopes:

```bash
truthkeep profile set enterprise
```

Do not enable heavy simulators in normal MCP usage unless you know why you need them.
