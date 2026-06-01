#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/dist-enterprise/linux"
PKG="$OUT/truthkeep-memory_11.0.0-alpha_all"
rm -rf "$OUT"
mkdir -p "$PKG/opt/truthkeep-memory" "$PKG/DEBIAN" "$PKG/usr/local/bin"
rsync -a --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.pytest_cache' --exclude '*.db' --exclude '*.db-wal' --exclude '*.db-shm' --exclude 'truthkeep.log' "$ROOT/" "$PKG/opt/truthkeep-memory/"
cat > "$PKG/DEBIAN/control" <<'EOS'
Package: truthkeep-memory
Version: 11.0.0-alpha
Section: utils
Priority: optional
Architecture: all
Maintainer: TruthKeep
Depends: python3 (>= 3.11), python3-pip
Description: TruthKeep Memory local-first AI memory engine for OpenClaw/MCP.
EOS
cat > "$PKG/usr/local/bin/truthkeep-easy-install" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/truthkeep-memory
./INSTALL_TRUTHKEEP_MAC_LINUX.sh
EOS
chmod +x "$PKG/usr/local/bin/truthkeep-easy-install"
dpkg-deb --build "$PKG" "$OUT/truthkeep-memory_11.0.0-alpha_all.deb"
sha256sum "$OUT/truthkeep-memory_11.0.0-alpha_all.deb" > "$OUT/truthkeep-memory_11.0.0-alpha_all.deb.sha256"
python "$ROOT/scripts/make_enterprise_release_manifest.py" --root "$ROOT" --out "$ROOT/dist-enterprise/ENTERPRISE_RELEASE_MANIFEST.json"
echo "[OK] Debian package built at $OUT/truthkeep-memory_11.0.0-alpha_all.deb"
