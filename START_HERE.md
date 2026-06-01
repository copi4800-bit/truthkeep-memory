# TruthKeep v11 Polished - Start Here

TruthKeep is a local-first memory engine for AI agents. It focuses on remembering what is still true, not on recalling as much context as possible.

## For Non-Technical Users

### Windows

Double-click:

```text
installers/INSTALL_TRUTHKEEP_WINDOWS.cmd
```

Then restart OpenClaw and use:

```text
memory_status
```

### macOS / Linux

Run:

```bash
./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
```

Then restart OpenClaw and use `memory_status`.

## What Easy Mode Does

- Creates or checks the local SQLite memory database.
- Installs the OpenClaw Easy Mode manifest.
- Uses MCP stdio only.
- Opens no HTTP port.
- Exposes only five basic tools by default.

## Five Default Tools

- `memory_remember`
- `memory_recall`
- `memory_correct`
- `memory_status`
- `memory_profile`

Advanced graph and developer tools are still in the package, but hidden from normal users by default.

## Core Promise

TruthKeep does not try to remember more. It tries to remember correctly for longer.

## Public Setup Command

OpenClaw and npm/package users can also run:

```bash
truthkeep-setup
```

It launches the same Easy Mode setup.

## Enterprise / One-Click Installer Path

For the easiest install, use the root installer launchers:

- `installers/INSTALL_TRUTHKEEP_WINDOWS.cmd`
- `installers/INSTALL_TRUTHKEEP_WINDOWS.ps1`
- `installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh`

For IT admins and signed installer builds, read:

- `docs/ENTERPRISE_INSTALLER_GUIDE.md`
- `docs/SIGNING_AND_NOTARIZATION.md`
- `docs/IT_ADMIN_DEPLOYMENT.md`

Note: trusted signing requires your own certificate or private key. TruthKeep cannot create a trusted signed installer without it.
