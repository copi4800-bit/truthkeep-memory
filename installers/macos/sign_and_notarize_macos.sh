#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IDENTITY="${1:-${TRUTHKEEP_MACOS_INSTALLER_IDENTITY:-}}"
APPLE_ID="${2:-${APPLE_ID:-}}"
TEAM_ID="${3:-${APPLE_TEAM_ID:-}}"
APP_PASSWORD="${4:-${APPLE_APP_PASSWORD:-}}"
PKG="$ROOT/dist-enterprise/macos/TruthKeepMemory-unsigned.pkg"
SIGNED="$ROOT/dist-enterprise/macos/TruthKeepMemory-signed.pkg"

if [ -z "$IDENTITY" ]; then echo "Missing Developer ID Installer identity."; exit 1; fi
if [ ! -f "$PKG" ]; then echo "Build pkg first: installers/macos/build_pkg.sh"; exit 1; fi
productsign --sign "$IDENTITY" "$PKG" "$SIGNED"
pkgutil --check-signature "$SIGNED"

if [ -n "$APPLE_ID" ] && [ -n "$TEAM_ID" ] && [ -n "$APP_PASSWORD" ]; then
  xcrun notarytool submit "$SIGNED" --apple-id "$APPLE_ID" --team-id "$TEAM_ID" --password "$APP_PASSWORD" --wait
  xcrun stapler staple "$SIGNED"
  echo "[OK] Signed, notarized, and stapled: $SIGNED"
else
  echo "[OK] Signed but not notarized: $SIGNED"
  echo "Set APPLE_ID, APPLE_TEAM_ID, APPLE_APP_PASSWORD to notarize."
fi
