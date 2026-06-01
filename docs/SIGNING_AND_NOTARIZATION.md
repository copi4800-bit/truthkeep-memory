# Signing and Notarization

TruthKeep can prepare installer artifacts, but it cannot sign them with a trusted identity unless you provide the signing credentials.

## Windows Authenticode

Requirements:

- Windows SDK installed.
- `signtool.exe` available on PATH.
- Code-signing certificate in PFX form.
- Timestamp server.

Command:

```powershell
$env:TRUTHKEEP_SIGNING_CERT_PFX="C:\certs\truthkeep.pfx"
$env:TRUTHKEEP_SIGNING_CERT_PASSWORD="..."
.\installers\windows\sign_installer.ps1 -FilePath .\dist-enterprise\truthkeep-windows-enterprise-payload.zip
```

Verification:

```powershell
signtool verify /pa /v .\dist-enterprise\truthkeep-windows-enterprise-payload.zip
```

## macOS Developer ID + Notarization

Requirements:

- Apple Developer account.
- Developer ID Installer certificate in Keychain.
- App-specific password or notarytool keychain profile.

Commands:

```bash
./installers/macos/build_pkg.sh
./installers/macos/sign_and_notarize_macos.sh \
  "Developer ID Installer: Your Name (TEAMID)" \
  "apple@example.com" \
  "TEAMID" \
  "app-specific-password"
```

## Linux signing

Recommended options:

- GPG detached signatures for `.deb` or tarball artifacts.
- cosign for supply-chain signed releases.

Command:

```bash
./installers/linux/build_deb.sh
./installers/linux/sign_linux_artifacts.sh
```

## Important wording

Before signing: `installer-ready` or `unsigned enterprise package`.

After signing with your certificate: `signed installer`.

After external security audit: `audited security`.
