from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


EASY_TOOL_ALLOWLIST = [
    "memory_remember",
    "memory_recall",
    "memory_correct",
    "memory_status",
    "memory_profile",
]

SUPPORTED_HOSTS = [
    "openclaw",
    "claude",
    "cursor",
    "cline",
    "roo",
    "continue",
    "vscode",
    "generic",
]


@dataclass(frozen=True)
class HostProfile:
    host: str
    display_name: str
    config_kind: str
    notes: str
    env_hint: str | None = None


def normalize_host(host: str | None) -> str:
    if not host:
        return "generic"
    normalized = host.strip().lower().replace("_", "-")
    aliases = {
        "claude-desktop": "claude",
        "claude_desktop": "claude",
        "cursor-ai": "cursor",
        "open-claw": "openclaw",
        "roocode": "roo",
        "roo-code": "roo",
        "continue-dev": "continue",
        "visual-studio-code": "vscode",
        "vs-code": "vscode",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_HOSTS:
        raise ValueError(f"Unsupported MCP host: {host}. Supported: {', '.join(SUPPORTED_HOSTS)}")
    return normalized


def get_profile(host: str) -> HostProfile:
    host = normalize_host(host)
    profiles: dict[str, HostProfile] = {
        "openclaw": HostProfile(
            host="openclaw",
            display_name="OpenClaw",
            config_kind="openclaw_plugin_manifest",
            notes="Uses TruthKeep OpenClaw Easy Mode manifest with five default memory tools.",
            env_hint="TRUTHKEEP_OPENCLAW_PLUGIN_DIR",
        ),
        "claude": HostProfile(
            host="claude",
            display_name="Claude Desktop",
            config_kind="mcpServers_json",
            notes="Uses a claude_desktop_config.json style mcpServers entry.",
        ),
        "cursor": HostProfile(
            host="cursor",
            display_name="Cursor",
            config_kind="mcpServers_json",
            notes="Uses a Cursor mcp.json style mcpServers entry when the Cursor profile folder exists.",
        ),
        "cline": HostProfile(
            host="cline",
            display_name="Cline",
            config_kind="mcpServers_json",
            notes="Uses a generic mcpServers entry. Exact host config location may vary by VS Code profile.",
        ),
        "roo": HostProfile(
            host="roo",
            display_name="Roo Code",
            config_kind="mcpServers_json",
            notes="Uses a generic mcpServers entry. Exact host config location may vary by VS Code profile.",
        ),
        "continue": HostProfile(
            host="continue",
            display_name="Continue",
            config_kind="mcpServers_json",
            notes="Uses a generic local MCP server block for hosts that accept mcpServers JSON.",
        ),
        "vscode": HostProfile(
            host="vscode",
            display_name="VS Code MCP Host",
            config_kind="mcpServers_json",
            notes="Uses a generic mcpServers entry for VS Code-compatible MCP clients.",
        ),
        "generic": HostProfile(
            host="generic",
            display_name="Generic MCP Host",
            config_kind="mcpServers_json",
            notes="Portable MCP stdio configuration that most MCP hosts can adapt.",
        ),
    }
    return profiles[host]


def _home() -> Path:
    return Path.home()


def truthkeep_config_root() -> Path:
    return Path(os.environ.get("TRUTHKEEP_CONFIG_DIR", str(_home() / ".truthkeep"))).expanduser()


def mcp_generated_dir() -> Path:
    return truthkeep_config_root() / "mcp"


def discover_truthkeep_mcp() -> str:
    path = shutil.which("truthkeep-mcp")
    if path:
        return os.path.abspath(path)
    # Windows editable installs may place scripts under Python/Scripts.
    py_dir = Path(sys.executable).parent
    for candidate in [py_dir / "Scripts" / "truthkeep-mcp.exe", py_dir / "Scripts" / "truthkeep-mcp", py_dir / "truthkeep-mcp"]:
        if candidate.exists():
            return str(candidate.resolve())
    return "truthkeep-mcp"


def build_mcp_server_config(command: str | None = None, db_path: str | None = None, mode: str = "easy", runtime_profile: str = "local") -> dict[str, Any]:
    env: dict[str, str] = {
        "TRUTHKEEP_MODE": mode,
        "TRUTHKEEP_TRANSPORT": "stdio",
        "TRUTHKEEP_OPEN_PORTS": "0",
        "TK_RUNTIME_PROFILE": runtime_profile,
    }
    if db_path:
        env["AEGIS_DB_PATH"] = db_path
    return {
        "command": command or discover_truthkeep_mcp(),
        "args": [],
        "env": env,
    }


def build_host_config(host: str, command: str | None = None, db_path: str | None = None, mode: str = "easy", runtime_profile: str = "local") -> dict[str, Any]:
    host = normalize_host(host)
    if host == "openclaw":
        return {
            "id": "truthkeep-memory",
            "name": "TruthKeep Memory",
            "description": "Local MCP memory that remembers what is still true.",
            "version": "11.0.0-alpha",
            "kind": "memory",
            "easyMode": True,
            "securityModel": {
                "transport": "mcp-stdio",
                "openPorts": False,
                "localOnly": True,
                "httpDaemon": False,
            },
            "mcp": build_mcp_server_config(command=command, db_path=db_path, mode=mode, runtime_profile=runtime_profile),
            "consumerSurface": {
                "defaultTools": EASY_TOOL_ALLOWLIST,
                "advancedToolsHiddenByDefault": True,
                "advancedManifest": "openclaw.plugin.advanced.json",
                "doctorCommand": "truthkeep mcp doctor openclaw",
            },
            "tools": [
                {"name": name, "description": f"TruthKeep Easy Mode tool: {name}"}
                for name in EASY_TOOL_ALLOWLIST
            ],
        }
    return {
        "mcpServers": {
            "truthkeep": build_mcp_server_config(command=command, db_path=db_path, mode=mode, runtime_profile=runtime_profile)
        }
    }


def candidate_config_paths(host: str) -> list[Path]:
    host = normalize_host(host)
    system = platform.system().lower()
    home = _home()
    paths: list[Path] = []

    if host == "openclaw":
        paths.append(Path(os.environ.get("TRUTHKEEP_OPENCLAW_PLUGIN_DIR", str(home / ".openclaw" / "plugins" / "truthkeep-memory"))) / "openclaw.plugin.json")
        return paths

    if host == "claude":
        if system == "windows":
            appdata = os.environ.get("APPDATA")
            if appdata:
                paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
        elif system == "darwin":
            paths.append(home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
        else:
            paths.append(home / ".config" / "Claude" / "claude_desktop_config.json")
    elif host == "cursor":
        # Cursor commonly supports a user-level mcp.json. Keep generated fallback for portability.
        paths.append(home / ".cursor" / "mcp.json")
        if system == "windows":
            userprofile = os.environ.get("USERPROFILE")
            if userprofile:
                paths.append(Path(userprofile) / ".cursor" / "mcp.json")
    elif host in {"cline", "roo", "vscode", "continue"}:
        # Extension config locations vary by host/profile; write generated config unless user passes --target.
        paths.append(mcp_generated_dir() / f"{host}.mcp.json")
    elif host == "generic":
        paths.append(mcp_generated_dir() / "truthkeep.generic.mcp.json")
    return list(dict.fromkeys(paths))


def preferred_config_path(host: str, explicit_target: str | None = None) -> Path:
    if explicit_target:
        return Path(explicit_target).expanduser()
    paths = candidate_config_paths(host)
    for path in paths:
        if path.exists() or path.parent.exists():
            return path
    return paths[0]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".truthkeep-backup-{stamp}")
    backup.write_bytes(path.read_bytes())
    return backup


def merge_mcp_config(existing: dict[str, Any], new_config: dict[str, Any]) -> dict[str, Any]:
    if "mcpServers" not in new_config:
        return new_config
    merged = dict(existing or {})
    current_servers = dict(merged.get("mcpServers") or {})
    current_servers["truthkeep"] = new_config["mcpServers"]["truthkeep"]
    merged["mcpServers"] = current_servers
    return merged


def install_host_config(host: str, target: str | None = None, db_path: str | None = None, command: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    host = normalize_host(host)
    profile = get_profile(host)
    path = preferred_config_path(host, explicit_target=target)
    config = build_host_config(host, command=command, db_path=db_path, mode="easy")

    if dry_run:
        return {"ok": True, "host": host, "path": str(path), "profile": asdict(profile), "config": config, "dry_run": True}

    path.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup(path)
    if host == "openclaw":
        final_config = config
    else:
        final_config = merge_mcp_config(_load_json(path), config)
    path.write_text(json.dumps(final_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "host": host, "path": str(path), "backup": str(backup) if backup else None, "profile": asdict(profile)}


def render_config(host: str, db_path: str | None = None, command: str | None = None) -> str:
    return json.dumps(build_host_config(host, command=command, db_path=db_path, mode="easy"), indent=2, ensure_ascii=False)


def doctor_host_config(host: str, target: str | None = None) -> dict[str, Any]:
    host = normalize_host(host)
    path = preferred_config_path(host, explicit_target=target)
    exists = path.exists()
    config = _load_json(path) if exists else {}
    if host == "openclaw":
        registered = exists and (config.get("id") == "truthkeep-memory" or config.get("mcp", {}).get("command"))
    else:
        registered = bool((config.get("mcpServers") or {}).get("truthkeep"))
    return {
        "host": host,
        "path": str(path),
        "exists": exists,
        "registered": registered,
        "profile": asdict(get_profile(host)),
    }


def compatibility_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for host in SUPPORTED_HOSTS:
        profile = get_profile(host)
        rows.append({
            "host": host,
            "display_name": profile.display_name,
            "config_kind": profile.config_kind,
            "status": "profile-ready" if host in {"openclaw", "claude", "cursor", "generic"} else "generated-config-ready",
            "notes": profile.notes,
        })
    return rows
