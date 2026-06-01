# TruthKeep Easy Mode

TruthKeep Easy Mode is the non-technical setup path. It does not change the TruthKeep core. It only makes installation, OpenClaw integration, diagnostics, repair, and onboarding easier.

## Principles

- Remember right, not wide.
- Local-first SQLite memory.
- MCP stdio only.
- No HTTP daemon.
- No open ports.
- No cloud by default.
- Advanced graph/dev tools are hidden by default.

## Quick Start

```bash
truthkeep easy install
```

Then restart OpenClaw.

## Check Health

```bash
truthkeep openclaw doctor
```

## Manual MCP Config

```bash
truthkeep openclaw config
```

## Repair

```bash
truthkeep repair
```

Repair creates a local backup first, then compacts/repairs local storage.

## Default Tools

Easy Mode exposes only these default tools to non-technical users:

- `memory_remember`
- `memory_recall`
- `memory_correct`
- `memory_status`
- `memory_profile`

Advanced graph/governance/debug tools remain available for developers but should be hidden by default in user-facing hosts.
