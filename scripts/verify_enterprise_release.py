#!/usr/bin/env python3
"""Enterprise release gate for TruthKeep packages."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_DIRS = {'__pycache__','.pytest_cache','.git'}
BAD_SUFFIXES = {'.pyc','.pyo'}
BAD_NAMES = {'memory_aegis.db','memory_aegis.db-wal','memory_aegis.db-shm','truthkeep.log'}
REQUIRED = [
    'INSTALL_TRUTHKEEP_WINDOWS.cmd',
    'INSTALL_TRUTHKEEP_WINDOWS.ps1',
    'INSTALL_TRUTHKEEP_MAC_LINUX.sh',
    'openclaw.plugin.json',
    'openclaw.plugin.advanced.json',
    'docs/ENTERPRISE_INSTALLER_GUIDE.md',
    'docs/SIGNING_AND_NOTARIZATION.md',
    'docs/IT_ADMIN_DEPLOYMENT.md',
    'installers/windows/sign_installer.ps1',
    'installers/macos/sign_and_notarize_macos.sh',
    'installers/linux/sign_linux_artifacts.sh',
]

def main() -> int:
    failures = []
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT).as_posix()
        if any(part in BAD_DIRS for part in p.relative_to(ROOT).parts):
            failures.append(f'forbidden directory/file: {rel}')
        if p.is_file() and (p.suffix in BAD_SUFFIXES or p.name in BAD_NAMES):
            failures.append(f'forbidden runtime artifact: {rel}')
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            failures.append(f'missing required enterprise file: {rel}')
    manifest = ROOT / 'openclaw.plugin.json'
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
        tools = data.get('tools', [])
        if len(tools) != 5:
            failures.append(f'Easy OpenClaw manifest should expose exactly 5 tools, found {len(tools)}')
        if data.get('securityModel', {}).get('openPorts') is not False:
            failures.append('OpenClaw manifest must declare openPorts=false')
    except Exception as exc:
        failures.append(f'cannot parse openclaw.plugin.json: {exc}')
    if failures:
        print('[FAIL] Enterprise release gate failed:')
        for f in failures:
            print(' -', f)
        return 1
    print('[OK] Enterprise release gate passed.')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
