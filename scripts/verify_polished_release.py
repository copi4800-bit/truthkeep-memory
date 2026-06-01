from __future__ import annotations

from pathlib import Path
import sys

BAD_DIRS = {"__pycache__", ".pytest_cache", ".git"}
BAD_SUFFIXES = {".pyc", ".pyo"}
BAD_NAMES = {"memory_aegis.db", "memory_aegis.db-wal", "memory_aegis.db-shm", "truthkeep.log"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    bad: list[str] = []
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if any(part in BAD_DIRS for part in rel.parts):
            bad.append(str(rel))
            continue
        if p.name in BAD_NAMES or p.suffix in BAD_SUFFIXES:
            bad.append(str(rel))
    if bad:
        print("[FAIL] Release hygiene found unwanted files:")
        for item in bad[:100]:
            print(" -", item)
        if len(bad) > 100:
            print(f" ... and {len(bad)-100} more")
        return 1
    print("[OK] Polished release hygiene passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
