#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ARTIFACT="${1:-$ROOT/dist-enterprise/linux/truthkeep-memory_11.0.0-alpha_all.deb}"
if [ ! -f "$ARTIFACT" ]; then echo "Artifact not found: $ARTIFACT"; exit 1; fi
if command -v gpg >/dev/null 2>&1; then
  gpg --detach-sign --armor "$ARTIFACT"
  echo "[OK] GPG signature created: $ARTIFACT.asc"
else
  echo "[ERROR] gpg not found. Install GnuPG or sign artifacts in CI."
  exit 1
fi
