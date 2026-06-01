import json
import subprocess
import sys
from pathlib import Path


def test_enterprise_manifest_does_not_hash_itself(tmp_path: Path):
    root = tmp_path / "release"
    root.mkdir()
    (root / "payload.txt").write_text("payload", encoding="utf-8")
    manifest = root / "ENTERPRISE_RELEASE_MANIFEST.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/make_enterprise_release_manifest.py",
            "--root",
            str(root),
            "--out",
            str(manifest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(manifest.read_text(encoding="utf-8"))
    paths = [item["path"] for item in data["files"]]
    assert "payload.txt" in paths
    assert "ENTERPRISE_RELEASE_MANIFEST.json" not in paths
    assert data["file_count"] == 1
    assert "[OK] Manifest written:" in result.stdout
