#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/dist-enterprise/macos"
PKGROOT="$OUT/pkgroot/Applications/TruthKeepMemory"
rm -rf "$OUT"
mkdir -p "$PKGROOT"
rsync -a --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.pytest_cache' --exclude '*.db' --exclude '*.db-wal' --exclude '*.db-shm' --exclude 'truthkeep.log' "$ROOT/" "$PKGROOT/"
mkdir -p "$OUT/scripts"
cat > "$OUT/scripts/postinstall" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
cd /Applications/TruthKeepMemory
./INSTALL_TRUTHKEEP_MAC_LINUX.sh || true
EOS
chmod +x "$OUT/scripts/postinstall"
pkgbuild --root "$OUT/pkgroot" --scripts "$OUT/scripts" --identifier "ai.truthkeep.memory" --version "11.0.0-alpha" "$OUT/TruthKeepMemory-unsigned.pkg"
python "$ROOT/scripts/make_enterprise_release_manifest.py" --root "$ROOT" --out "$ROOT/dist-enterprise/ENTERPRISE_RELEASE_MANIFEST.json"
echo "[OK] Unsigned pkg created: $OUT/TruthKeepMemory-unsigned.pkg"
echo "Next: installers/macos/sign_and_notarize_macos.sh <DeveloperID Installer Name> <apple-id> <team-id> <app-password>"
