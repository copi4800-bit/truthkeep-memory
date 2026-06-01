from __future__ import annotations

import json

from aegis_py.mcp_universal import (
    SUPPORTED_HOSTS,
    build_host_config,
    compatibility_matrix,
    normalize_host,
    render_config,
)


def test_all_supported_hosts_have_profiles() -> None:
    rows = compatibility_matrix()
    assert {row["host"] for row in rows} == set(SUPPORTED_HOSTS)


def test_generic_config_has_truthkeep_mcp_server() -> None:
    payload = json.loads(render_config("generic"))
    assert "mcpServers" in payload
    server = payload["mcpServers"]["truthkeep"]
    assert server["command"]
    assert server["env"]["TRUTHKEEP_TRANSPORT"] == "stdio"
    assert server["env"]["TRUTHKEEP_OPEN_PORTS"] == "0"


def test_openclaw_config_has_easy_tool_allowlist() -> None:
    payload = build_host_config("openclaw")
    assert payload["easyMode"] is True
    assert payload["securityModel"]["openPorts"] is False
    assert payload["consumerSurface"]["defaultTools"] == [
        "memory_remember",
        "memory_recall",
        "memory_correct",
        "memory_status",
        "memory_profile",
    ]


def test_host_aliases() -> None:
    assert normalize_host("claude-desktop") == "claude"
    assert normalize_host("roo-code") == "roo"
    assert normalize_host("vs-code") == "vscode"
