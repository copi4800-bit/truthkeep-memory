#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================================"
echo " TruthKeep Enterprise Easy Installer - macOS/Linux"
echo "============================================================"
echo " Local-only. No HTTP daemon. No open ports. OpenClaw MCP stdio."
echo ""

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[ERROR] Python 3.11+ was not found."
  exit 1
fi

$PY - <<'PYCHK'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PYCHK
if [ $? -ne 0 ]; then
  echo "[ERROR] Python 3.11+ is required."
  exit 1
fi

$PY -m pip install --upgrade pip
$PY -m pip install -e .
$PY -m truthkeep.cli easy install
$PY -m truthkeep.cli openclaw install
$PY -m truthkeep.cli openclaw doctor

echo ""
echo "[OK] TruthKeep is installed and OpenClaw Easy Mode is ready."
echo "Restart OpenClaw, then use: memory_status, memory_remember, memory_recall, memory_correct, memory_profile"
