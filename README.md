# TruthKeep Memory v11

TruthKeep is a local-first memory engine for AI agents and MCP hosts. It focuses on one hard problem: remembering what is still true after facts change.

This repository is the v11 alpha enterprise-installer-ready package. It includes the core memory engine, OpenClaw Easy Mode, installer launchers, release verification scripts, and signing helpers.

## What It Does

- Stores memories in local SQLite.
- Keeps corrected facts ahead of outdated facts.
- Marks old facts as superseded instead of letting them leak back into recall.
- Explains why one memory was selected and why another was suppressed.
- Runs through MCP stdio with no HTTP daemon and no open ports by default.
- Provides an Easy Mode OpenClaw manifest with only five user-facing tools.

## Quick Start

### Windows

Double-click:

```text
installers/INSTALL_TRUTHKEEP_WINDOWS.cmd
```

Then restart OpenClaw and use `memory_status`.

### macOS / Linux

Run:

```bash
chmod +x ./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
```

Then restart OpenClaw and use `memory_status`.

## Easy Mode Tools

The default OpenClaw manifest exposes only:

- `memory_remember`
- `memory_recall`
- `memory_correct`
- `memory_status`
- `memory_profile`

Advanced graph and developer tools are included separately in `openclaw.plugin.advanced.json`.

## Developer Setup

Install locally:

```bash
pip install -e .
```

Run checks:

```bash
python -m pytest tests -q
python scripts/verify_enterprise_release.py
```

Run the MCP server:

```bash
truthkeep-mcp
```

## Python API Example

```python
from truthkeep import TruthKeep

tk = TruthKeep.auto()
tk.remember("Mimi's favorite drink is Bubble Tea.", subject="mimi.drink")
tk.correct("Correction: Mimi's favorite drink is Peach Tea.", subject="mimi.drink")

results = tk.recall("What is Mimi's favorite drink?")
print(results[0]["memory"]["content"])
```

## Enterprise Release Path

This package includes:

- Windows, macOS, and Linux installer launchers.
- Windows Authenticode, macOS notarization, and Linux signing helper scripts.
- `ENTERPRISE_RELEASE_MANIFEST.json` with file size and SHA256 metadata.
- `scripts/verify_enterprise_release.py` for release hygiene and manifest integrity checks.

Build and signing documentation:

- `docs/ENTERPRISE_INSTALLER_GUIDE.md`
- `docs/SIGNING_AND_NOTARIZATION.md`
- `docs/IT_ADMIN_DEPLOYMENT.md`
- `docs/ENTERPRISE_LIMITATIONS.md`

## Security Posture

TruthKeep v11 alpha is:

- local-first
- MCP stdio based
- no HTTP daemon by default
- no open TCP/UDP ports by default
- not cloud-backed by default

Important limitation: this package is enterprise-installer-ready, but not externally audited and not trusted-signed unless you sign platform artifacts with your own certificate or key.

## Version

- Runtime label: `v11.0-secure-mcp-stdio-alpha`
- Python package: `11.0.0a0`
- npm package: `11.0.0-alpha`
- Release channel: `v11-alpha-enterprise-installer-ready`

## License

MIT License.
