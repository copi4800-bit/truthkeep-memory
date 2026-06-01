from __future__ import annotations

from pathlib import Path

PACKAGE_VERSION = "11.0.0a0"
NPM_VERSION = "11.0.0-alpha"
DEFAULT_RUNTIME_VERSION = "v11.0-secure-mcp-stdio-alpha"


def get_runtime_version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION.md"
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_RUNTIME_VERSION
    return version or DEFAULT_RUNTIME_VERSION
