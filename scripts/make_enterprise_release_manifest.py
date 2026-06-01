#!/usr/bin/env python3
"""Create SHA256 manifest for a clean TruthKeep enterprise release tree."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, sys, time
from pathlib import Path

EXCLUDE_DIRS = {'.git','__pycache__','.pytest_cache','dist-enterprise','.venv','node_modules'}
EXCLUDE_SUFFIXES = {'.pyc','.pyo'}
EXCLUDE_NAMES = {'memory_aegis.db','memory_aegis.db-wal','memory_aegis.db-shm','truthkeep.log'}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def iter_files(root: Path):
    for p in sorted(root.rglob('*')):
        rel_parts = p.relative_to(root).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        if p.is_file() and p.name not in EXCLUDE_NAMES and p.suffix not in EXCLUDE_SUFFIXES:
            yield p

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', default='ENTERPRISE_RELEASE_MANIFEST.json')
    ns = ap.parse_args()
    root = Path(ns.root).resolve()
    files = []
    for p in iter_files(root):
        files.append({
            'path': p.relative_to(root).as_posix(),
            'size': p.stat().st_size,
            'sha256': sha256(p),
        })
    manifest = {
        'name': 'TruthKeep Memory',
        'release': 'v11.0.0-alpha-enterprise-installer-ready',
        'generated_at_unix': int(time.time()),
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'signing_status': 'unsigned_source_manifest; sign platform installers with your own certificate/private key',
        'security_model': {
            'transport': 'mcp-stdio',
            'http_daemon': False,
            'open_ports': False,
            'cloud_default': False,
            'local_first': True,
        },
        'file_count': len(files),
        'files': files,
    }
    out = Path(ns.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'[OK] Manifest written: {out} ({len(files)} files)')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
