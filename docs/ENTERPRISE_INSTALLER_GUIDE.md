# TruthKeep Enterprise Installer Guide

This guide turns the existing TruthKeep source package into deployable IT artifacts.

## What this package can do now

- Local-only TruthKeep installation.
- OpenClaw Easy Mode configuration.
- MCP stdio only.
- No HTTP daemon.
- No open TCP/UDP ports.
- Five default OpenClaw tools for normal users.
- Advanced tools kept in `openclaw.plugin.advanced.json` for developers.
- Build/signing scripts for Windows, macOS, and Linux packaging.

## What it cannot do without your certificate

It cannot create a trusted signed installer by itself. Trusted signing requires your private code-signing certificate, for example:

- Windows: Authenticode certificate + Windows SDK `signtool.exe`.
- macOS: Apple Developer ID Installer certificate + notarization credentials.
- Linux: GPG/cosign key controlled by the release owner.

## User-facing install path

### Windows

Double-click:

```text
installers/INSTALL_TRUTHKEEP_WINDOWS.cmd
```

or run PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\installers\INSTALL_TRUTHKEEP_WINDOWS.ps1
```

### macOS/Linux

```bash
chmod +x ./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
./installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh
```

## IT packaging path

### Windows payload

```powershell
.\installers\windows\build_installer.ps1
.\installers\windows\sign_installer.ps1 -FilePath .\dist-enterprise\truthkeep-windows-enterprise-payload.zip -CertPath C:\path\cert.pfx
```

Optional EXE wrapping can be done with Inno Setup using:

```text
installers/windows/TruthKeepSetup.iss
```

### macOS pkg

```bash
./installers/macos/build_pkg.sh
./installers/macos/sign_and_notarize_macos.sh "Developer ID Installer: Your Name (TEAMID)"
```

### Linux deb

```bash
./installers/linux/build_deb.sh
./installers/linux/sign_linux_artifacts.sh
```

## Release gate

Before distributing:

```bash
python scripts/verify_enterprise_release.py
python scripts/make_enterprise_release_manifest.py --root . --out ENTERPRISE_RELEASE_MANIFEST.json
```

## Security promise

TruthKeep Enterprise Easy Mode remains local-first:

- It does not start an HTTP daemon.
- It does not bind `127.0.0.1` or `0.0.0.0`.
- It does not expose LAN or internet APIs.
- It relies on MCP stdio and local SQLite.

## Recommended distribution name

```text
TruthKeepMemory-v11.0.0-alpha-enterprise-installer-ready
```

Do not claim `audited security` until an external audit has been completed.
