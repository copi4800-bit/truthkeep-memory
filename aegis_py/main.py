from typing import Optional
import os
import sys
import traceback
import threading

# Suppress FastMCP stdout startup banner which can corrupt stdio MCP protocols
os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - depends on optional runtime package
    FastMCP = None

from .app import AegisApp

mcp = FastMCP("Aegis Memory Console") if FastMCP is not None else None

# Thread-safe global app initialization (double-checked locking pattern)
_app_lock = threading.Lock()
_app: Optional[AegisApp] = None

def get_app() -> AegisApp:
    global _app
    if _app is None:
        with _app_lock:
            if _app is None:
                _app = AegisApp()
    return _app

def put_memory(content: str, type: str = "episodic", scope_id: str = "default", session_id: Optional[str] = None) -> str:
    """
    Ingests a new memory into the engine.
    - content: The factual content or message to remember.
    - type: 'episodic' (events), 'semantic' (facts), 'working' (tasks/temp).
    - scope_id: The project, user, or topic ID the memory belongs to.
    - session_id: (Optional) The current conversation session ID for signal tracking.
    """
    try:
        app = get_app()
        mem = app.put_memory(content, type=type, scope_id=scope_id, session_id=session_id)
        if mem is None:
            return "No memory stored."
        return f"Memory stored: {mem.id} ({mem.type})"
    except Exception as e:
        sys.stderr.write(f"Error in put_memory: {traceback.format_exc()}\n")
        return f"Error: {str(e)}"

def search_memories(query: str, scope_id: str, limit: int = 5) -> str:
    """
    Retrieves relevant memories based on a query within a scope.
    """
    try:
        app = get_app()
        results = app.search(query, scope_id=scope_id, limit=limit)
        if not results:
            return "No relevant memories found."

        output = []
        for r in results:
            output.append(f"- [{r.memory.type}] {r.memory.content} (Score: {r.score:.2f})\n  Reason: {r.reason}")
        return "\n".join(output)
    except Exception as e:
        sys.stderr.write(f"Error in search_memories: {traceback.format_exc()}\n")
        return f"Error: {str(e)}"

def get_memory_profile(scope_id: str) -> str:
    """
    Returns a human-readable summary of the learned interaction style and core facts for a scope.
    Use this to understand who you are talking to and how they like to interact.
    """
    try:
        app = get_app()
        return app.render_profile(scope_id)
    except Exception as e:
        sys.stderr.write(f"Error in get_memory_profile: {traceback.format_exc()}\n")
        return f"Error: {str(e)}"

def get_service_info() -> dict:
    """
    Returns the Python-owned local-service descriptor for thin hosts or operator tooling.
    """
    try:
        app = get_app()
        surface = app.public_surface()
        return {
            "backend": "python",
            "service": {
                "name": "Aegis Python MCP Service",
                "runtime_version": surface["engine"]["runtime_version"],
                "deployment_model": surface["service_boundary"]["deployment_model"],
                "preferred_transport": surface["service_boundary"]["preferred_transport"],
            },
            "startup_contract": surface["service_boundary"]["startup_contract"],
            "default_operations": surface["consumer_contract"]["default_operations"],
        }
    except Exception as e:
        sys.stderr.write(f"Error in get_service_info: {traceback.format_exc()}\n")
        return {
            "backend": "python",
            "error": str(e),
            "status": "UNHEALTHY"
        }

def get_startup_probe() -> dict:
    """
    Returns a lightweight startup probe for process-managed local service usage.
    """
    try:
        app = get_app()
        doctor = app.doctor()
        ready = doctor["health_state"] in {"HEALTHY", "DEGRADED_SYNC"}
        return {
            "backend": "python",
            "ready": ready,
            "health_state": doctor["health_state"],
            "workspace": doctor["workspace"],
            "database": doctor["database"],
        }
    except Exception as e:
        sys.stderr.write(f"Error in get_startup_probe: {traceback.format_exc()}\n")
        return {
            "backend": "python",
            "ready": False,
            "health_state": "BROKEN",
            "error": str(e)
        }

def reinforce_fact(memory_id: str) -> str:
    """
    Manually increases the activation score of an existing memory.
    Use this when a piece of information is explicitly confirmed as important.
    """
    try:
        app = get_app()
        app.reinforce(memory_id)
        return f"Memory {memory_id} reinforced."
    except Exception as e:
        sys.stderr.write(f"Error in reinforce_fact: {traceback.format_exc()}\n")
        return f"Error: {str(e)}"

def end_current_session(session_id: str, scope_id: str):
    """
    Finalizes the current session: archives working memory and consolidates learned style signals.
    """
    try:
        app = get_app()
        app.end_session(session_id, scope_id, "session")
        return "Session finalized. Habits consolidated."
    except Exception as e:
        sys.stderr.write(f"Error in end_current_session: {traceback.format_exc()}\n")
        return f"Error: {str(e)}"

if mcp is not None:
    mcp.tool()(put_memory)
    mcp.tool()(search_memories)
    mcp.tool()(get_memory_profile)
    mcp.tool()(get_service_info)
    mcp.tool()(get_startup_probe)
    mcp.tool()(reinforce_fact)
    mcp.tool()(end_current_session)

if __name__ == "__main__":
    if mcp is None:
        raise SystemExit("fastmcp is not installed")
    mcp.run()
