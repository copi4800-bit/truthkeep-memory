# TruthKeep v11 Polished — Start Here

TruthKeep is a local-first memory engine for AI agents. It focuses on **remembering what is still true**, not on recalling as much context as possible.

## For non-technical users

### Windows
Double-click:

```text
RUN_TRUTHKEEP_WINDOWS.cmd
```

Then choose:

```text
1. Install / Repair Easy Mode
2. Check OpenClaw
```

Restart OpenClaw after install.

### macOS / Linux
Run:

```bash
./RUN_TRUTHKEEP_MAC_LINUX.sh
```

## What Easy Mode does

- Creates/checks the local SQLite memory database.
- Installs the OpenClaw Easy Mode manifest.
- Uses MCP stdio only.
- Opens no HTTP port.
- Exposes only five basic tools by default.

## Five default tools

- `memory_remember`
- `memory_recall`
- `memory_correct`
- `memory_status`
- `memory_profile`

Advanced graph/dev tools are still in the package, but hidden from normal users by default.

## Core promise

TruthKeep does not try to remember more. It tries to remember correctly for longer.


## Public setup command

OpenClaw and npm/package users can also run:

```bash
truthkeep-setup
```

It launches the same Easy Mode setup.

## Enterprise / one-click installer path

For the easiest install, use the new installer launchers:

### Windows

Double-click:

```text
INSTALL_TRUTHKEEP_WINDOWS.cmd
```

### macOS / Linux

```bash
./INSTALL_TRUTHKEEP_MAC_LINUX.sh
```

For IT admins and signed installer builds, read:

```text
docs/ENTERPRISE_INSTALLER_GUIDE.md
docs/SIGNING_AND_NOTARIZATION.md
docs/IT_ADMIN_DEPLOYMENT.md
```

Note: trusted signing requires your own certificate/private key. TruthKeep cannot create a trusted signed installer without it.
