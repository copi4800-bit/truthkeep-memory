#!/usr/bin/env python3
"""Enterprise release gate for TruthKeep packages."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_DIRS = {'__pycache__','.pytest_cache','.git'}
BAD_SUFFIXES = {'.pyc','.pyo'}
BAD_NAMES = {'memory_aegis.db','memory_aegis.db-wal','memory_aegis.db-shm','truthkeep.log'}
MANIFEST_PATH = ROOT / 'ENTERPRISE_RELEASE_MANIFEST.json'
REQUIRED = [
    'ENTERPRISE_RELEASE_MANIFEST.json',
    'installers/INSTALL_TRUTHKEEP_WINDOWS.cmd',
    'installers/INSTALL_TRUTHKEEP_WINDOWS.ps1',
    'installers/INSTALL_TRUTHKEEP_MAC_LINUX.sh',
    'openclaw.plugin.json',
    'openclaw.plugin.advanced.json',
    'docs/ENTERPRISE_INSTALLER_GUIDE.md',
    'docs/SIGNING_AND_NOTARIZATION.md',
    'docs/IT_ADMIN_DEPLOYMENT.md',
    'installers/windows/sign_installer.ps1',
    'installers/macos/sign_and_notarize_macos.sh',
    'installers/linux/sign_linux_artifacts.sh',
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def iter_release_files():
    for p in sorted(ROOT.rglob('*')):
        rel_parts = p.relative_to(ROOT).parts
        if any(part in BAD_DIRS for part in rel_parts):
            continue
        if p == MANIFEST_PATH:
            continue
        if p.is_file() and p.name not in BAD_NAMES and p.suffix not in BAD_SUFFIXES:
            yield p

def verify_enterprise_manifest(failures: list[str]) -> None:
    if not MANIFEST_PATH.exists():
        failures.append('missing required enterprise file: ENTERPRISE_RELEASE_MANIFEST.json')
        return
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    except Exception as exc:
        failures.append(f'cannot parse ENTERPRISE_RELEASE_MANIFEST.json: {exc}')
        return
    entries = manifest.get('files')
    if not isinstance(entries, list):
        failures.append('ENTERPRISE_RELEASE_MANIFEST.json must contain a files list')
        return
    expected = {item.get('path'): item for item in entries if isinstance(item, dict)}
    actual = {p.relative_to(ROOT).as_posix(): p for p in iter_release_files()}
    if manifest.get('file_count') != len(entries):
        failures.append('enterprise manifest file_count does not match files list length')
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing:
        failures.append(f'enterprise manifest lists missing file(s): {", ".join(missing[:5])}')
    if extra:
        failures.append(f'enterprise manifest omits file(s): {", ".join(extra[:5])}')
    for rel in sorted(set(expected) & set(actual)):
        entry = expected[rel]
        path = actual[rel]
        if entry.get('size') != path.stat().st_size:
            failures.append(f'enterprise manifest size mismatch: {rel}')
            continue
        if entry.get('sha256') != sha256(path):
            failures.append(f'enterprise manifest hash mismatch: {rel}')

def main() -> int:
    failures = []
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT).as_posix()
        if any(part in BAD_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.is_file() and (p.suffix in BAD_SUFFIXES or p.name in BAD_NAMES):
            failures.append(f'forbidden runtime artifact: {rel}')
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            failures.append(f'missing required enterprise file: {rel}')
    verify_enterprise_manifest(failures)
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
