# IT Admin Deployment Guide

## Deployment model

TruthKeep runs local-only on each workstation.

```text
OpenClaw -> MCP stdio -> truthkeep-mcp -> local SQLite
```

No service is installed. No HTTP daemon is started. No ports are opened.

## Default user tools

The Easy Mode OpenClaw manifest exposes only:

- `memory_remember`
- `memory_recall`
- `memory_correct`
- `memory_status`
- `memory_profile`

Advanced tools are in `openclaw.plugin.advanced.json` and should not be deployed to non-technical users by default.

## Windows silent-ish deployment

TruthKeep currently uses a script-based installer. For a managed environment, wrap it with your software deployment tool:

```powershell
powershell -ExecutionPolicy Bypass -File installers/INSTALL_TRUTHKEEP_WINDOWS.ps1
```

## macOS/Linux deployment

```bash
./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
```

## Health checks

```bash
truthkeep openclaw doctor
truthkeep easy status
truthkeep mcp-probe
```

## Data location

TruthKeep uses a local SQLite database. Keep it in the user's profile/application data folder unless your organization provides a managed encrypted local path.

## Backup policy

Use encrypted backups when strict privacy is enabled. Do not distribute raw database files unless the recipient is authorized to read all memory content.

## Security notes

- Do not expose TruthKeep over HTTP.
- Do not wrap it in a LAN service.
- Do not store secrets in memory.
- Do not deploy advanced tools to regular users by default.
