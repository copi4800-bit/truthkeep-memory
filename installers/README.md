# TruthKeep Installers

TruthKeep v11 now includes an enterprise-installer-ready shell.

## Normal users

Use root launchers:

- `INSTALL_TRUTHKEEP_WINDOWS.cmd`
- `INSTALL_TRUTHKEEP_WINDOWS.ps1`
- `INSTALL_TRUTHKEEP_MAC_LINUX.sh`

Legacy launchers still work and call these new installer scripts:

- `RUN_TRUTHKEEP_WINDOWS.cmd`
- `RUN_TRUTHKEEP_WINDOWS.ps1`
- `RUN_TRUTHKEEP_MAC_LINUX.sh`

## IT admins

Read:

- `docs/ENTERPRISE_INSTALLER_GUIDE.md`
- `docs/SIGNING_AND_NOTARIZATION.md`
- `docs/IT_ADMIN_DEPLOYMENT.md`

## Platform folders

- `installers/windows/` — Windows payload build, Inno Setup script, Authenticode signing helper.
- `installers/macos/` — pkg build, Developer ID signing, notarization helper.
- `installers/linux/` — deb build and GPG signing helper.

## Signing truth

The package includes signing scripts, but trusted signing requires your certificate/private key. Without that, this is `enterprise-installer-ready`, not `trusted signed by publisher`.
