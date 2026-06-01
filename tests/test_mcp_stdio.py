"""Unit tests for TruthKeep Secure MCP Stdio transport.

Spawns the MCP server as a subprocess, sends standard JSON-RPC initialize and
tools/list requests, and verifies correct responses over stdio.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import pytest


def test_mcp_stdio_jsonrpc_handshake():
    """Verify that MCP server starts and replies to standard JSON-RPC handshakes."""
    # Run the main FastMCP module using current Python interpreter
    cmd = [sys.executable, "-m", "truthkeep.mcp"]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    
    # 1. Send initialize request
    init_req = {
        "jsonrpc": "2.0",
        "id": 100,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest-stdio-tester", "version": "1.0.0"},
        },
    }
    
    try:
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()
        
        # Read response
        resp_str = proc.stdout.readline()
        assert resp_str, "Process stdout is empty"
        
        try:
            resp = json.loads(resp_str)
        except json.JSONDecodeError:
            # Fallback if there was a welcome line on stdout
            resp_str = proc.stdout.readline()
            resp = json.loads(resp_str)
            
        assert resp.get("jsonrpc") == "2.0"
        assert resp.get("id") == 100
        assert "result" in resp
        assert "protocolVersion" in resp["result"]
        assert "capabilities" in resp["result"]
        
        # 2. Send tools/list request
        tools_req = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/list",
            "params": {},
        }
        proc.stdin.write(json.dumps(tools_req) + "\n")
        proc.stdin.flush()
        
        tools_resp_str = proc.stdout.readline()
        tools_resp = json.loads(tools_resp_str)
        
        assert tools_resp.get("jsonrpc") == "2.0"
        assert tools_resp.get("id") == 101
        assert "result" in tools_resp
        
        tools = tools_resp["result"].get("tools", [])
        assert len(tools) > 0
        
        tool_names = [t.get("name") for t in tools]
        assert "put_memory" in tool_names
        assert "search_memories" in tool_names
        
    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=2.0)
