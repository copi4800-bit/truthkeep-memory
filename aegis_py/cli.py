from __future__ import annotations

import argparse
import json
import io
import sys
import os
import time
import signal
import subprocess
from typing import Any, Sequence

from .app import AegisApp
from .version import get_runtime_version


def show_logs(tail_lines: int = 50, follow: bool = False) -> int:
    log_file = "truthkeep.log"
    if not os.path.exists(log_file):
        emit_output(f"No log file found at: {log_file}")
        return 0

    emit_output(f"Showing logs from: {log_file} (showing last {tail_lines} lines)")
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            for line in lines[-tail_lines:]:
                print(line, end="")
    except Exception as e:
        emit_output(f"Failed to read log file: {e}")
        return 1

    if not follow:
        return 0

    emit_output("\n--- Following logs (Press Ctrl+C to exit) ---")
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                print(line, end="")
    except KeyboardInterrupt:
        emit_output("\n[i] Log stream closed.")
        return 0
    except Exception as e:
        emit_output(f"\nError reading log stream: {e}")
        return 1


def run_mcp_probe(db_path: str, *, live: bool = False, timeout_seconds: float = 10.0) -> int:
    """Run a safe MCP readiness probe.

    Default mode intentionally uses the non-interactive startup probe so normal users
    never get stuck on stdio framing differences.  The live JSON-RPC probe remains
    available behind --live for developers.
    """
    import sys
    import threading

    if not live:
        emit_output("[*] Checking TruthKeep MCP startup readiness...")
        cmd = [sys.executable, "-m", "truthkeep.mcp", "--startup-probe"]
        try:
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
                env={**os.environ, "AEGIS_DB_PATH": db_path},
            )
        except subprocess.TimeoutExpired:
            emit_output("[!] MCP startup probe timed out. TruthKeep did not become ready in time.")
            return 1
        except Exception as e:
            emit_output(f"[!] Failed to run MCP startup probe: {e}")
            return 1

        if result.returncode != 0:
            emit_output("[!] MCP startup probe failed.")
            detail = (result.stderr or result.stdout or "").strip()
            if detail:
                emit_output(detail[-2000:])
            return 1

        output = (result.stdout or "").strip()
        try:
            payload = json.loads(output)
        except Exception:
            emit_output("[!] MCP startup probe returned non-JSON output:")
            emit_output(output[-2000:])
            return 1

        ready = bool(payload.get("ready"))
        health_state = payload.get("health_state") or payload.get("state") or "UNKNOWN"
        if ready:
            emit_output(f"[OK] TruthKeep MCP is ready. Health: {health_state}")
            return 0
        emit_output(f"[!] TruthKeep MCP is not ready. Health: {health_state}")
        emit_output(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1

    emit_output("[*] Initiating developer live MCP stdio JSON-RPC probe...")
    cmd = [sys.executable, "-m", "truthkeep.mcp"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env={**os.environ, "AEGIS_DB_PATH": db_path},
        )
    except Exception as e:
        emit_output(f"[!] Failed to spawn MCP subprocess: {e}")
        return 1

    def _readline_with_timeout(pipe, seconds: float) -> str | None:
        box: dict[str, str | None] = {"line": None}
        def target() -> None:
            try:
                box["line"] = pipe.readline()
            except Exception:
                box["line"] = None
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(seconds)
        return box["line"] if not thread.is_alive() else None

    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "truthkeep-cli-probe", "version": get_runtime_version()},
        },
    }
    tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    try:
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()
        init_line = _readline_with_timeout(proc.stdout, timeout_seconds)
        if not init_line:
            emit_output("[!] Live MCP probe timed out waiting for initialize response.")
            emit_output("    Tip: default `truthkeep mcp-probe` uses startup readiness and is recommended for normal users.")
            proc.kill()
            return 1
        init_resp = json.loads(init_line)
        if "error" in init_resp:
            emit_output(json.dumps(init_resp, indent=2, ensure_ascii=False))
            proc.kill()
            return 1
        proc.stdin.write(json.dumps(tools_req) + "\n")
        proc.stdin.flush()
        tools_line = _readline_with_timeout(proc.stdout, timeout_seconds)
        if not tools_line:
            emit_output("[!] Live MCP probe timed out waiting for tools/list response.")
            proc.kill()
            return 1
        tools_resp = json.loads(tools_line)
        tools = tools_resp.get("result", {}).get("tools", [])
        emit_output(f"[OK] Live MCP stdio probe passed. Tools visible: {len(tools)}")
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        return 0
    except Exception as e:
        emit_output(f"[!] Error during live MCP probe: {e}")
        proc.kill()
        return 1

def show_dashboard(db_path: str) -> int:
    db_abs = os.path.abspath(db_path)

    doctor_payload = None
    status_payload = None
    db_size_bytes = 0

    try:
        from .app import AegisApp
        app = AegisApp(db_abs)
        doctor_payload = app.doctor()
        status_payload = app.status()
        app.close()

        if os.path.exists(db_abs):
            db_size_bytes = os.path.getsize(db_abs)
    except Exception as e:
        emit_output(f"Error: Failed to connect to database for dashboard: {e}")
        return 1

    db_size_kb = db_size_bytes / 1024.0

    health = doctor_payload.get("health", {})
    health_state = health.get("state", "UNKNOWN")

    counts = status_payload.get("counts", {})
    total_memories = doctor_payload.get("counts", {}).get("memories", 0)
    conflict_count = doctor_payload.get("counts", {}).get("open_conflicts", 0)

    active_count = counts.get("active", 0)
    archived_count = counts.get("archived", 0)
    superseded_count = counts.get("superseded", 0)
    quarantined_count = doctor_payload.get("v10_governance", {}).get("quarantined_count", 0)

    compaction_pressure = doctor_payload.get("storage", {}).get("smilodon_peak_retirement_pressure", 0.0)
    stale_pressure = doctor_payload.get("v10_intelligence", {}).get("stale_pressure", 0)

    intel = doctor_payload.get("v10_intelligence", {})
    alignment_score = intel.get("truth_alignment_score", 0.95) * 100.0
    conflict_index = intel.get("conflict_load_index", 0.0)
    churn = intel.get("correction_churn", 0)
    winner_density = doctor_payload.get("v10_governance", {}).get("truth_winner_density", 0.0) * 100.0

    emit_output("======================================================================")
    emit_output("                     TRUTHKEEP MEMORY ASCII DASHBOARD                  ")
    emit_output("======================================================================")
    emit_output("[*] System Environment")
    emit_output(f"  Database Path : {db_abs}")
    emit_output(f"  DB Footprint  : {db_size_kb:.2f} KB")
    emit_output(f"  System Health : {health_state}")
    emit_output("  Security Mode : Secure Stdio (Zero Open Ports)")

    emit_output("")
    emit_output("[+] Cognitive Space Metrics")
    emit_output(f"  Total Memories: {total_memories:<12} Open Conflicts: {conflict_count}")
    emit_output(f"  - Active      : {active_count:<12} Compaction Pressure: {compaction_pressure:.2f}")
    emit_output(f"  - Archived    : {archived_count:<12} Stale Pressure: {stale_pressure}")
    emit_output(f"  - Superseded  : {superseded_count:<12} Why-Not Examples: Yes (via CLI recall)")
    if quarantined_count > 0:
        emit_output(f"  - Quarantined : {quarantined_count}")

    emit_output("")
    emit_output("[i] V10 Intelligence & Governance")
    emit_output(f"  Truth Alignment Score : {alignment_score:.1f}%")
    emit_output(f"  Conflict Load Index   : {conflict_index:.2f}")
    emit_output(f"  Correction Churn (7d) : {churn}")
    emit_output(f"  Truth Winner Density  : {winner_density:.1f}%")

    emit_output("======================================================================")
    emit_output("  Logs are monitored at: ./truthkeep.log")
    emit_output("======================================================================")

    return 0



EASY_DEFAULT_TOOLS = [
    "memory_remember",
    "memory_recall",
    "memory_correct",
    "memory_status",
    "memory_profile",
]


def _easy_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "memory_remember",
            "description": "[Easy] Store important current-truth information.",
            "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
        },
        {
            "name": "memory_recall",
            "description": "[Easy] Recall the latest trustworthy memory for a question.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
        {
            "name": "memory_correct",
            "description": "[Easy] Correct outdated or wrong memory while keeping why-not history.",
            "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
        },
        {
            "name": "memory_status",
            "description": "[Easy] Check TruthKeep health and local memory status.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "memory_profile",
            "description": "[Easy] Show the current remembered profile/preferences/projects.",
            "parameters": {"type": "object", "properties": {}},
        },
    ]


def _friendly_header(title: str) -> None:
    emit_output("=" * 70)
    emit_output(f" {title}")
    emit_output("=" * 70)


def _truthkeep_config_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".truthkeep")


def _openclaw_plugin_dir() -> str:
    return os.environ.get(
        "TRUTHKEEP_OPENCLAW_PLUGIN_DIR",
        os.path.join(os.path.expanduser("~"), ".openclaw", "plugins", "truthkeep-memory"),
    )


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_openclaw_easy_manifest() -> dict[str, Any]:
    return {
        "id": "truthkeep-memory",
        "name": "TruthKeep Memory",
        "description": "Local-first memory that prioritizes remembering what is still true.",
        "kind": "memory",
        "version": "11.0.0-alpha",
        "easyMode": True,
        "securityModel": {
            "transport": "mcp-stdio",
            "openPorts": False,
            "localOnly": True,
            "httpDaemon": False,
        },
        "consumerSurface": {
            "defaultTools": EASY_DEFAULT_TOOLS,
            "advancedToolsHiddenByDefault": True,
            "advancedManifest": "openclaw.plugin.advanced.json",
            "onboardingCommand": "truthkeep-setup",
            "doctorCommand": "truthkeep openclaw doctor",
        },
        "openclaw": {
            "extensions": ["./openclaw/truthkeep-memory.native.cjs"],
            "setupEntry": "./openclaw/truthkeep-memory.native.cjs",
        },
        "mcp": {
            "command": get_truthkeep_mcp_path(),
            "mode": "stdio",
        },
        "tools": _easy_tool_schemas(),
        "skills": [
            {"name": "Remember current truth", "description": "Store important facts until corrected."},
            {"name": "Recall current truth", "description": "Recall active, non-superseded memory."},
            {"name": "Correct memory", "description": "Update wrong or outdated memory safely."},
        ],
    }


def render_openclaw_mcp_config() -> str:
    config = {
        "mcpServers": {
            "truthkeep": {
                "command": get_truthkeep_mcp_path()
            }
        }
    }
    return json.dumps(config, indent=2, ensure_ascii=False)


def run_openclaw_install(db_path: str, *, dry_run: bool = False) -> int:
    _friendly_header("TruthKeep OpenClaw Easy Install")
    plugin_dir = _openclaw_plugin_dir()
    manifest_path = os.path.join(plugin_dir, "openclaw.plugin.json")
    emit_output("TruthKeep will be configured in local-only MCP stdio mode.")
    emit_output("No HTTP daemon. No open ports. No LAN exposure.")
    emit_output(f"OpenClaw plugin folder: {plugin_dir}")

    if dry_run:
        emit_output("\nDry run only. Generated manifest would be:")
        emit_output(json.dumps(build_openclaw_easy_manifest(), indent=2, ensure_ascii=False))
        return 0

    try:
        os.makedirs(plugin_dir, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(build_openclaw_easy_manifest(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        emit_output(f"[FAIL] Could not write OpenClaw plugin manifest: {e}")
        return 1

    emit_output(f"[OK] Wrote OpenClaw Easy Mode manifest: {manifest_path}")
    probe_result = run_mcp_probe(db_path, live=False)
    if probe_result == 0:
        emit_output("[OK] TruthKeep backend is ready for OpenClaw.")
    else:
        emit_output("[WARN] Manifest was written, but backend readiness probe failed.")
    emit_output("\nNext step: restart OpenClaw, then enable TruthKeep Memory if needed.")
    return probe_result


def run_openclaw_doctor(db_path: str) -> int:
    _friendly_header("TruthKeep OpenClaw Doctor")
    status = 0
    manifest_path = os.path.join(_openclaw_plugin_dir(), "openclaw.plugin.json")
    if os.path.exists(manifest_path):
        emit_output(f"[OK] Easy Mode manifest found: {manifest_path}")
    else:
        emit_output(f"[WARN] Easy Mode manifest not found: {manifest_path}")
        emit_output("       Run: truthkeep openclaw install")
        status = 1

    mcp_path = get_truthkeep_mcp_path()
    emit_output(f"[INFO] MCP command: {mcp_path}")
    if run_mcp_probe(db_path, live=False) != 0:
        status = 1

    try:
        app = AegisApp(db_path)
        try:
            payload = app.doctor()
            health_state = payload.get("health", {}).get("state") or payload.get("health_state") or "UNKNOWN"
            emit_output(f"[OK] Local database doctor state: {health_state}")
        finally:
            app.close()
    except Exception as e:
        emit_output(f"[FAIL] Local database doctor failed: {e}")
        status = 1
    return status


def run_openclaw_config() -> int:
    _friendly_header("TruthKeep OpenClaw MCP Config")
    emit_output("Copy this MCP config if your host asks for manual setup:")
    emit_output(render_openclaw_mcp_config())
    return 0


def run_openclaw_reset() -> int:
    _friendly_header("TruthKeep OpenClaw Reset")
    manifest_path = os.path.join(_openclaw_plugin_dir(), "openclaw.plugin.json")
    if not os.path.exists(manifest_path):
        emit_output("[OK] No Easy Mode manifest found. Nothing to reset.")
        return 0
    backup_path = manifest_path + ".bak"
    try:
        os.replace(manifest_path, backup_path)
        emit_output(f"[OK] Disabled OpenClaw Easy Mode manifest. Backup: {backup_path}")
        return 0
    except Exception as e:
        emit_output(f"[FAIL] Could not reset OpenClaw manifest: {e}")
        return 1


def run_repair(db_path: str, *, vacuum: bool = True) -> int:
    _friendly_header("TruthKeep Safe Repair")
    emit_output("Repair is local-only and creates a quick backup before compacting.")
    backup_dir = os.path.join(_truthkeep_config_dir(), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    if os.path.exists(db_path):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(backup_dir, f"memory_aegis-{stamp}.db")
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            emit_output(f"[OK] Backup created: {backup_path}")
        except Exception as e:
            emit_output(f"[WARN] Could not create backup before repair: {e}")
    else:
        emit_output("[INFO] Database does not exist yet; setup will create it.")

    app = AegisApp(db_path)
    try:
        result = app.compact_storage(vacuum=vacuum)
        emit_output("[OK] Storage compact/repair completed.")
        emit_output(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        emit_output(f"[FAIL] Repair failed: {e}")
        return 1
    finally:
        app.close()
    return 0


def run_easy_install(db_path: str) -> int:
    _friendly_header("TruthKeep Easy Install")
    emit_output("This sets up TruthKeep for people who do not want to touch technical details.")
    emit_output("Mode: local-only MCP stdio. No server. No open port. No cloud by default.\n")
    status = 0

    try:
        app = AegisApp(db_path)
        try:
            emit_output(f"[OK] Database ready: {os.path.abspath(app.db_path)}")
            doctor = app.doctor()
            health_state = doctor.get("health", {}).get("state") or doctor.get("health_state") or "UNKNOWN"
            emit_output(f"[OK] Doctor state: {health_state}")
        finally:
            app.close()
    except Exception as e:
        emit_output(f"[FAIL] Database setup/doctor failed: {e}")
        status = 1

    if run_mcp_probe(db_path, live=False) != 0:
        status = 1

    # Configure OpenClaw best-effort.  Failing this should not destroy local use.
    openclaw_status = run_openclaw_install(db_path)
    if openclaw_status != 0:
        emit_output("[WARN] OpenClaw setup needs attention. Run: truthkeep openclaw doctor")
        status = 1

    emit_output("\nEasy Mode summary:")
    if status == 0:
        emit_output("[READY] TruthKeep is ready for real local use.")
        emit_output("Use it from OpenClaw or MCP host with: truthkeep-mcp")
    else:
        emit_output("[CHECK] TruthKeep core may be installed, but at least one setup check failed.")
        emit_output("Run: truthkeep openclaw doctor")
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="truthkeep",
        description="TruthKeep Memory CLI: correctness-first local memory for AI agents.",
    )
    parser.add_argument(
        "--db-path",
        default="memory_aegis.db",
        help="SQLite database path. Defaults to ./memory_aegis.db",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    remember = subparsers.add_parser("remember", help="Store a memory using the consumer path.")
    remember.add_argument("content", help="Content to remember.")

    recall = subparsers.add_parser("recall", help="Recall memories using the consumer path.")
    recall.add_argument("query", help="What to recall.")
    recall.add_argument("--scope-type")
    recall.add_argument("--scope-id")

    correct = subparsers.add_parser("correct", help="Correct an existing fact.")
    correct.add_argument("content", help="Corrected content.")

    status = subparsers.add_parser("status", help="Show runtime status.")
    status.add_argument("--json", action="store_true", help="Emit structured JSON.")

    field = subparsers.add_parser("field-snapshot", help="Show Xi(t) whole-system v10 field snapshot.")
    field.add_argument("--scope-type")
    field.add_argument("--scope-id")

    prove = subparsers.add_parser("prove-it", help="Run the short proof flow and print its summary.")
    prove.add_argument("--json", action="store_true", help="Emit structured JSON instead of a short summary.")

    mcp = subparsers.add_parser("mcp", help="Universal MCP host integration commands.")
    mcp.add_argument("--json", action="store_true", help="Emit startup probe JSON when no MCP subcommand is provided.")
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=False)
    mcp_sub.add_parser("list-hosts", help="List supported MCP host profiles.")
    mcp_config = mcp_sub.add_parser("config", help="Print copy-paste MCP config for a host.")
    mcp_config.add_argument("host", nargs="?", default="generic", help="Host profile: openclaw, claude, cursor, cline, roo, continue, vscode, generic.")
    mcp_config.add_argument("--target", help="Optional target config path for documentation output.")
    mcp_install = mcp_sub.add_parser("install", help="Install/merge TruthKeep MCP config for a host.")
    mcp_install.add_argument("host", nargs="?", default="generic", help="Host profile to install.")
    mcp_install.add_argument("--target", help="Explicit config path to write.")
    mcp_install.add_argument("--dry-run", action="store_true", help="Show what would be written without touching files.")
    mcp_doctor = mcp_sub.add_parser("doctor", help="Check TruthKeep MCP readiness for a host.")
    mcp_doctor.add_argument("host", nargs="?", default="generic", help="Host profile to check.")
    mcp_doctor.add_argument("--target", help="Explicit config path to check.")
    mcp_smoke = mcp_sub.add_parser("smoke-test", help="Run a small local MCP memory smoke test.")
    mcp_smoke.add_argument("host", nargs="?", default="generic", help="Host label for reporting.")
    mcp_smoke.add_argument("--live", action="store_true", help="Also run developer live JSON-RPC probe.")
    mcp_export = mcp_sub.add_parser("export-matrix", help="Write MCP compatibility matrix Markdown.")
    mcp_export.add_argument("--out", default="docs/MCP_COMPATIBILITY.md", help="Output Markdown path.")

    # Local CLI Commands
    subparsers.add_parser("setup", help="Initialize the database and run migrations.")
    mcp_probe = subparsers.add_parser("mcp-probe", help="Run a safe MCP readiness probe. Default never hangs.")
    mcp_probe.add_argument("--live", action="store_true", help="Developer-only live JSON-RPC stdio probe.")
    mcp_probe.add_argument("--timeout", type=float, default=10.0, help="Probe timeout in seconds.")

    easy = subparsers.add_parser("easy", help="Easy Mode for non-technical users.")
    easy_sub = easy.add_subparsers(dest="easy_command", required=False)
    easy_sub.add_parser("install", help="Install/setup TruthKeep and OpenClaw with safe defaults.")
    easy_sub.add_parser("doctor", help="Run a friendly Easy Mode diagnostic.")
    easy_sub.add_parser("status", help="Alias for Easy Mode diagnostic.")
    easy_sub.add_parser("gui", help="Open the no-code desktop launcher.")

    openclaw = subparsers.add_parser("openclaw", help="OpenClaw Easy Mode integration commands.")
    openclaw_sub = openclaw.add_subparsers(dest="openclaw_command", required=True)
    oc_install = openclaw_sub.add_parser("install", help="Install TruthKeep Easy Mode manifest for OpenClaw.")
    oc_install.add_argument("--dry-run", action="store_true", help="Print config without writing files.")
    openclaw_sub.add_parser("doctor", help="Check OpenClaw + TruthKeep readiness.")
    openclaw_sub.add_parser("config", help="Print copy-paste MCP config.")
    openclaw_sub.add_parser("reset", help="Disable the generated OpenClaw Easy Mode manifest.")

    repair = subparsers.add_parser("repair", help="Create backup and run safe local repair/compact.")
    repair.add_argument("--no-vacuum", action="store_true", help="Skip SQLite VACUUM.")

    logs_parser = subparsers.add_parser("logs", help="View local logs directly.")
    logs_parser.add_argument("--tail", type=int, default=50, help="Number of lines to show from end of log file.")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Stream log file contents in real-time.")

    subparsers.add_parser("dashboard", help="Show the minimal ASCII system dashboard.")
    subparsers.add_parser("doctor", help="Run a diagnostic health self-check.")
    subparsers.add_parser("report", help="Generate a human-readable memory health report.")
    subparsers.add_parser("invariants", help="Run a comprehensive check on SQLite database invariants.")
    subparsers.add_parser("gui", help="Launch the premium desktop local UI application.")
    subparsers.add_parser("setup-hosts", help="Automatically configure TruthKeep MCP for Cursor and Claude Desktop.")

    profile = subparsers.add_parser("profile", help="Show or change TruthKeep runtime performance profile.")
    profile_sub = profile.add_subparsers(dest="profile_command", required=False)
    profile_sub.add_parser("show", help="Show active runtime profile and feature flags.")
    profile_set = profile_sub.add_parser("set", help="Persist runtime profile for future commands.")
    profile_set.add_argument("profile_name", choices=["demo", "local", "hardened", "enterprise"], help="Runtime profile to persist.")
    profile_sub.add_parser("doctor", help="Explain profile health and protected TruthKeep DNA flags.")
    profile_sub.add_parser("list", help="List available profiles.")
    profile_sub.add_parser("clear", help="Clear persisted profile and return to env/default resolution.")

    benchmark = subparsers.add_parser("benchmark", help="Run lightweight local benchmarks.")
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=False)
    benchmark_profiles = benchmark_sub.add_parser("profiles", help="Benchmark remember/recall/correct across runtime profiles.")
    benchmark_profiles.add_argument("--records", type=int, default=10, help="Synthetic records per profile. Default: 10")
    benchmark_profiles.add_argument("--out", default="reports/profile_benchmark.json", help="Raw JSON output path.")
    benchmark_profiles.add_argument("--markdown", default="reports/profile_benchmark.md", help="Markdown report output path.")

    compact = subparsers.add_parser("compact", help="Compact and clean up database storage to reclaim disk space.")
    compact.add_argument("--archived-days", type=int, default=30, help="Days to keep archived memories. Default: 30")
    compact.add_argument("--superseded-days", type=int, default=14, help="Days to keep superseded memories. Default: 14")
    compact.add_argument("--no-vacuum", action="store_true", help="Do not run SQLite VACUUM after deleting.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = build_parser()
        args = parser.parse_args(list(argv) if argv is not None else None)

        # Hỗ trợ tự động phân giải đường dẫn CSDL thông minh dựa trên vị trí cài đặt gói aegis_py
        if not args.db_path or args.db_path == "memory_aegis.db":
            package_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pkg_db = os.path.join(package_parent, "memory_aegis.db")
            if os.path.exists(pkg_db):
                args.db_path = pkg_db

        if args.command == "prove-it":
            from scripts.prove_it import build_proof_summary

            summary = build_proof_summary(db_path=args.db_path)
            if args.json:
                emit_output(json.dumps(summary, indent=2, ensure_ascii=False))
            else:
                emit_output(render_proof_summary(summary))
            return 0

        if args.command == "mcp":
            from .mcp_universal import (
                SUPPORTED_HOSTS,
                compatibility_matrix,
                doctor_host_config,
                install_host_config,
                render_config,
            )

            if getattr(args, "mcp_command", None) == "list-hosts":
                emit_output("Supported TruthKeep MCP host profiles:")
                for row in compatibility_matrix():
                    emit_output(f"- {row['host']:<10} {row['display_name']} [{row['status']}]")
                return 0

            if getattr(args, "mcp_command", None) == "config":
                _friendly_header(f"TruthKeep MCP Config: {args.host}")
                emit_output(render_config(args.host, db_path=args.db_path))
                if getattr(args, "target", None):
                    emit_output(f"\nSuggested target path: {args.target}")
                return 0

            if getattr(args, "mcp_command", None) == "install":
                _friendly_header(f"TruthKeep MCP Install: {args.host}")
                try:
                    result = install_host_config(args.host, target=args.target, db_path=args.db_path, dry_run=args.dry_run)
                except Exception as e:
                    emit_output(f"[FAIL] MCP host install failed: {e}")
                    return 1
                emit_output(json.dumps(result, indent=2, ensure_ascii=False))
                if not args.dry_run:
                    emit_output("\nNext step: restart the target MCP host so it reloads configuration.")
                return 0

            if getattr(args, "mcp_command", None) == "doctor":
                _friendly_header(f"TruthKeep MCP Doctor: {args.host}")
                status = 0
                try:
                    info = doctor_host_config(args.host, target=args.target)
                    emit_output(json.dumps(info, indent=2, ensure_ascii=False))
                    if not info.get("registered"):
                        emit_output(f"[WARN] TruthKeep is not registered for {args.host}. Run: truthkeep mcp install {args.host}")
                        status = 1
                except Exception as e:
                    emit_output(f"[FAIL] Host config check failed: {e}")
                    status = 1
                if run_mcp_probe(args.db_path, live=False) != 0:
                    status = 1
                return status

            if getattr(args, "mcp_command", None) == "smoke-test":
                _friendly_header(f"TruthKeep MCP Smoke Test: {args.host}")
                status = run_mcp_probe(args.db_path, live=False)
                if getattr(args, "live", False):
                    status = max(status, run_mcp_probe(args.db_path, live=True, timeout_seconds=5.0))
                if status == 0:
                    emit_output("[OK] MCP memory server startup is healthy. Host integration can now be tested in the real app.")
                else:
                    emit_output("[FAIL] MCP smoke test failed. Run: truthkeep doctor")
                return status

            if getattr(args, "mcp_command", None) == "export-matrix":
                rows = compatibility_matrix()
                out = args.out
                try:
                    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
                    lines = ["# TruthKeep MCP Compatibility Matrix", "", "| Host | Status | Config kind | Notes |", "|---|---:|---|---|"]
                    for row in rows:
                        lines.append(f"| {row['display_name']} | {row['status']} | {row['config_kind']} | {row['notes']} |")
                    with open(out, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines) + "\n")
                    emit_output(f"[OK] Wrote MCP compatibility matrix: {out}")
                    return 0
                except Exception as e:
                    emit_output(f"[FAIL] Could not write matrix: {e}")
                    return 1

            if args.json:
                from .mcp.server import AegisMCPServer

                server = AegisMCPServer(args.db_path)
                try:
                    emit_output(server.startup_probe())
                finally:
                    server.close()
            else:
                guidance = "\n".join([
                    "======================================================================",
                    "         TRUTHKEEP UNIVERSAL MCP MEMORY CONFIGURATION                 ",
                    "======================================================================",
                    "TruthKeep runs as local MCP stdio memory. No HTTP daemon. No open ports.",
                    "",
                    "Recommended commands:",
                    "  truthkeep mcp list-hosts",
                    "  truthkeep mcp config <host>",
                    "  truthkeep mcp install <host>",
                    "  truthkeep mcp doctor <host>",
                    "",
                    "Supported profiles:",
                    f"  {', '.join(SUPPORTED_HOSTS)}",
                    "",
                    "Core memory tools exposed in Easy Mode:",
                    "  memory_remember, memory_recall, memory_correct, memory_status, memory_profile",
                ])
                emit_output(guidance)
            return 0

        if args.command == "profile":
            from .runtime.profile import (
                clear_persisted_profile,
                describe_current_profile,
                get_profile,
                list_profiles,
                persist_profile,
            )
            cmd = getattr(args, "profile_command", None) or "show"
            if cmd == "list":
                emit_output("Available TruthKeep runtime profiles:")
                for name in list_profiles():
                    flags = get_profile(name)
                    emit_output(f"- {name:<10} {flags.description}")
                return 0
            if cmd == "set":
                result = persist_profile(args.profile_name)
                emit_output(json.dumps(result, indent=2, ensure_ascii=False))
                emit_output("Note: MCP host configs can still override this via TK_RUNTIME_PROFILE env.")
                return 0
            if cmd == "clear":
                emit_output(json.dumps(clear_persisted_profile(), indent=2, ensure_ascii=False))
                return 0
            payload = describe_current_profile()
            if cmd == "doctor":
                flags = payload["flags"]
                emit_output("======================================================================")
                emit_output("                 TRUTHKEEP RUNTIME PROFILE DOCTOR                    ")
                emit_output("======================================================================")
                emit_output(f"Current profile: {payload['active_profile']} [{flags['hot_path_policy']}]")
                emit_output("")
                emit_output("[Core TruthKeep DNA — always enforced]")
                for k, v in payload["dna_enforced"].items():
                    emit_output(f"  - {k:<28}: {'ON' if v else 'OFF'}")
                emit_output("")
                emit_output("[Optional heavy engines]")
                for key in ["enable_fhe_simulator", "enable_pqc_simulator", "enable_rsa_toy", "enable_tda_signature", "enable_strict_privacy", "enable_scoped_db_sharding", "enable_fast_crypto_backend"]:
                    emit_output(f"  - {key:<28}: {flags[key]}")
                emit_output("======================================================================")
                return 0
            emit_output(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        if args.command == "benchmark":
            cmd = getattr(args, "benchmark_command", None) or "profiles"
            if cmd == "profiles":
                from scripts.profile_benchmark import run_profile_benchmark, write_profile_reports
                report = run_profile_benchmark(records=args.records, db_root=os.path.join(os.getcwd(), ".truthkeep-profile-bench"))
                write_profile_reports(report, json_path=args.out, markdown_path=args.markdown)
                emit_output(f"[OK] Wrote profile benchmark JSON: {args.out}")
                emit_output(f"[OK] Wrote profile benchmark Markdown: {args.markdown}")
                return 0

        if args.command == "setup":
            app = AegisApp(args.db_path)
            try:
                emit_output(f"Database initialized and migrated successfully at: {os.path.abspath(app.db_path)}")
                emit_output("TruthKeep is ready for secure MCP stdio interactions.")
            finally:
                app.close()
            return 0

        if args.command == "mcp-probe":
            return run_mcp_probe(args.db_path, live=args.live, timeout_seconds=args.timeout)

        if args.command == "easy":
            easy_cmd = args.easy_command or "install"
            if easy_cmd == "install":
                return run_easy_install(args.db_path)
            if easy_cmd in {"doctor", "status"}:
                return run_openclaw_doctor(args.db_path)
            if easy_cmd == "gui":
                from .ux.no_code_launcher import launch_no_code_gui
                return launch_no_code_gui(args.db_path)

        if args.command == "openclaw":
            if args.openclaw_command == "install":
                return run_openclaw_install(args.db_path, dry_run=args.dry_run)
            if args.openclaw_command == "doctor":
                return run_openclaw_doctor(args.db_path)
            if args.openclaw_command == "config":
                return run_openclaw_config()
            if args.openclaw_command == "reset":
                return run_openclaw_reset()

        if args.command == "repair":
            return run_repair(args.db_path, vacuum=not args.no_vacuum)

        if args.command == "gui":
            from .ux.desktop import launch_gui
            return launch_gui(args.db_path)

        if args.command == "setup-hosts":
            return run_openclaw_install(args.db_path)

        if args.command == "logs":
            return show_logs(args.tail, args.follow)

        if args.command == "dashboard":
            return show_dashboard(args.db_path)

        if args.command == "doctor":
            app = AegisApp(args.db_path)
            try:
                payload = app.doctor()
                emit_output(json.dumps(payload, indent=2, ensure_ascii=False))
            finally:
                app.close()
            return 0

        if args.command == "report":
            app = AegisApp(args.db_path)
            try:
                report_text = app.memory_health_summary()
                emit_output(report_text)
            finally:
                app.close()
            return 0

        if args.command == "invariants":
            from .invariants.runtime import validate_memory_invariants
            report = validate_memory_invariants(args.db_path)
            emit_output(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
            return 0 if report.ok else 1

        app = AegisApp(args.db_path)
        try:
            if args.command == "compact":
                result = app.compact_storage(
                    archived_memory_days=args.archived_days,
                    superseded_memory_days=args.superseded_days,
                    evidence_days=30,
                    governance_days=30,
                    replication_days=14,
                    background_days=14,
                    vacuum=not args.no_vacuum,
                )
                emit_output(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            if args.command == "remember":
                emit_output(app.memory_remember(args.content))
                return 0
            if args.command == "recall":
                emit_output(app.memory_recall(args.query, scope_type=args.scope_type, scope_id=args.scope_id))
                return 0
            if args.command == "correct":
                emit_output(app.memory_correct(args.content))
                return 0
            if args.command == "status":
                payload = app.status()
                emit_output(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else render_status(payload))
                return 0
            if args.command == "field-snapshot":
                payload = app.v10_field_snapshot(scope_type=args.scope_type, scope_id=args.scope_id)
                emit_output(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        finally:
            app.close()
        parser.print_help(sys.stderr)
        return 1
    except KeyboardInterrupt:
        emit_output("\n[i] Operation cancelled by user.")
        return 0


def render_status(payload: dict[str, Any]) -> str:
    health = payload.get("health", {})
    counts = payload.get("counts", {})

    return "\n".join(
        [
            f"State: {health.get('state', 'UNKNOWN')}",
            f"Memories: {counts.get('total', 0)} total",
            f"Capabilities: {', '.join(sorted((health.get('capabilities') or {}).keys()))}",
        ]
    )


def render_proof_summary(summary: dict[str, Any]) -> str:
    metrics = summary.get("metrics", {})
    verdict = "PASS" if summary.get("passed") else "CHECK"
    return "\n".join(
        [
            f"TruthKeep proof: {verdict}",
            f"Correction-safe truth: {metrics.get('correction_top1_preserved')}",
            f"Why-not available: {metrics.get('why_not_available')}",
            f"V10 field snapshot available: {metrics.get('field_snapshot_available')}",
            f"Compressed tier available: {metrics.get('compressed_tier_available')}",
            f"Summary: {summary.get('summary')}",
        ]
    )


def emit_output(text: str, *, stream: io.TextIOBase | None = None) -> None:
    target = stream or sys.stdout
    try:
        print(text, file=target)
        return
    except UnicodeEncodeError:
        pass

    payload = f"{text}\n"
    encoding = getattr(target, "encoding", None) or "utf-8"
    buffer = getattr(target, "buffer", None)
    if buffer is not None:
        buffer.write(payload.encode(encoding, errors="replace"))
        buffer.flush()
        return
    target.write(payload.encode("ascii", errors="replace").decode("ascii"))
    target.flush()


def get_truthkeep_mcp_path() -> str:
    import shutil
    # Thử tìm mcp executable trong hệ thống
    path = shutil.which("truthkeep-mcp")
    if path:
        return os.path.abspath(path)

    # Thử tìm trong thư mục Scripts của Python executable đang chạy
    python_dir = os.path.dirname(sys.executable)
    mcp_win = os.path.join(python_dir, "Scripts", "truthkeep-mcp.exe")
    if os.path.exists(mcp_win):
        return mcp_win

    return "truthkeep-mcp" # Fallback


def run_setup_hosts() -> int:
    import json

    mcp_path = get_truthkeep_mcp_path()
    emit_output(f"[*] Detected TruthKeep MCP executable at: {mcp_path}")

    # 1. Tự động cấu hình Cursor
    cursor_dir = os.path.expandvars(r"%USERPROFILE%\.cursor")
    if os.path.exists(cursor_dir):
        mcp_json_path = os.path.join(cursor_dir, "mcp.json")
        try:
            config = {}
            if os.path.exists(mcp_json_path):
                try:
                    with open(mcp_json_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception:
                    pass

            if "mcpServers" not in config:
                config["mcpServers"] = {}

            config["mcpServers"]["truthkeep"] = {
                "command": mcp_path
            }

            with open(mcp_json_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            emit_output(f"[+] Successfully integrated TruthKeep MCP into Cursor global config: {mcp_json_path}")
        except Exception as e:
            emit_output(f"[!] Failed to write Cursor config: {e}")
    else:
        emit_output("[i] Cursor profile folder not detected. Skipping Cursor setup.")

    # 2. Tự động cấu hình Claude Desktop
    claude_dir = os.path.expandvars(r"%APPDATA%\Claude")
    if os.path.exists(claude_dir) or os.path.exists(os.path.join(os.path.expandvars(r"%APPDATA%"), "Claude")):
        os.makedirs(claude_dir, exist_ok=True)
        config_path = os.path.join(claude_dir, "claude_desktop_config.json")
        try:
            config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception:
                    pass

            if "mcpServers" not in config:
                config["mcpServers"] = {}

            config["mcpServers"]["truthkeep"] = {
                "command": mcp_path
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            emit_output(f"[+] Successfully integrated TruthKeep MCP into Claude Desktop: {config_path}")
        except Exception as e:
            emit_output(f"[!] Failed to write Claude Desktop config: {e}")
    else:
        emit_output("[i] Claude Desktop folder not detected. Skipping Claude setup.")

    emit_output("\n=======================================================")
    emit_output("   TRUTHKEEP MCP AUTOMATIC HOST INTEGRATION COMPLETE!  ")
    emit_output("=======================================================")
    emit_output("TruthKeep Memory is now globally configured as Plug-and-Play.")
    emit_output("Just open Cursor or Claude Desktop and start chatting immediately!")
    emit_output("=======================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
