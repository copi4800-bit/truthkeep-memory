from __future__ import annotations

from typing import Any


def _to_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_command_center_shell_payload(*, query: str, scope_type: str, scope_id: str, consumer_shell: dict[str, Any], dashboard_shell: dict[str, Any], workflow_shell: dict[str, Any], truth_transition_timeline: dict[str, Any], experience_brief: dict[str, Any], core_showcase: dict[str, Any]) -> dict[str, Any]:
    consumer = consumer_shell.get("result") or {}
    dashboard = dashboard_shell.get("result") or {}
    workflow = workflow_shell.get("result") or {}
    timeline = truth_transition_timeline.get("result") or {}
    brief = experience_brief.get("result") or {}
    showcase = core_showcase.get("result") or {}
    hero = {
        "headline": consumer.get("hero", {}).get("headline") or dashboard.get("hero", {}).get("headline") or "No command center headline available.",
        "readiness": consumer.get("hero", {}).get("readiness") or dashboard.get("hero", {}).get("readiness"),
        "health_state": consumer.get("hero", {}).get("health_state") or dashboard.get("hero", {}).get("health_state"),
        "truth_role": brief.get("hero", {}).get("truth_role") or dashboard.get("hero", {}).get("truth_role"),
        "governance_status": brief.get("hero", {}).get("governance_status") or dashboard.get("hero", {}).get("governance_status"),
        "selected_memory": brief.get("hero", {}).get("selected_memory") or workflow.get("current_truth") or "No current truth selected.",
    }
    payload = {
        "query": query,
        "scope": {"scope_type": scope_type, "scope_id": scope_id},
        "hero": hero,
        "ordinary_mode": {
            "description": consumer.get("ordinary_lane", {}).get("description", "The narrow daily path for normal use."),
            "actions": _to_list(consumer.get("primary_actions"))[:3],
            "workflow": _to_list(consumer.get("ordinary_lane", {}).get("workflow"))[:4],
        },
        "workflow_loop": {
            "steps": _to_list(workflow.get("workflow_steps"))[:4],
            "verification": workflow.get("verification", {}),
        },
        "truth_timeline": {
            "story": timeline.get("transition_story") or "No truth transition story available.",
            "preview": _to_list(timeline.get("timeline_preview"))[:4],
        },
        "deep_inspection": {
            "summary": showcase.get("human_reason") or brief.get("human_reason") or "No deep inspection summary available.",
            "signals": [
                f"trust={showcase.get('verdict', {}).get('trust_score')}",
                f"readiness={showcase.get('verdict', {}).get('readiness_score')}",
                f"evidence={showcase.get('evidence_summary', {}).get('count')}",
            ],
        },
        "operator_mode": {
            "description": consumer.get("operator_lane", {}).get("description", "Inspection and maintenance tools for advanced use."),
            "actions": _to_list(consumer.get("operator_lane", {}).get("operations"))[:6],
        },
        "recommended_commands": [
            "truthkeep field-snapshot",
            "truthkeep prove-it",
            "python scripts/demo_command_center_shell.py",
        ],
        "command_center_text": "",
    }
    payload["command_center_text"] = render_command_center_shell_text(payload)
    return {"query": query, "scope": {"scope_type": scope_type, "scope_id": scope_id}, "ready": bool(consumer_shell.get("ready")), "command_center_text": payload["command_center_text"], "result": payload}


def render_command_center_shell_text(payload: dict[str, Any]) -> str:
    hero = payload["hero"]
    lines = [
        "[TruthKeep Command Center]",
        f"readiness={hero.get('readiness')} | health={hero.get('health_state')} | truth_role={hero.get('truth_role')} | governance={hero.get('governance_status')}",
        "",
        "[Headline]",
        hero.get("headline") or "No command center headline available.",
        "",
        "[Current Truth]",
        hero.get("selected_memory") or "No current truth selected.",
        "",
        "[Ordinary Mode]",
        payload["ordinary_mode"]["description"],
    ]
    for item in payload["ordinary_mode"]["actions"]:
        lines.append(f"- {item.get('tool')}: {item.get('why')}")
    if payload["ordinary_mode"]["workflow"]:
        lines.append(f"workflow={payload['ordinary_mode']['workflow']}")
    lines.extend(["", "[Workflow Loop]"])
    for step in payload["workflow_loop"]["steps"]:
        lines.append(f"- {step.get('title')} | tool={step.get('tool')}")
    lines.extend(["", "[Truth Timeline]", payload["truth_timeline"]["story"]])
    for item in payload["truth_timeline"]["preview"]:
        lines.append(f"- {item}")
    lines.extend(["", "[Deep Inspection]", payload["deep_inspection"]["summary"]])
    for item in payload["deep_inspection"]["signals"]:
        lines.append(f"- {item}")
    lines.extend(["", "[Operator Mode]", payload["operator_mode"]["description"]])
    for item in payload["operator_mode"]["actions"]:
        lines.append(f"- {item}")
    lines.extend(["", "[Recommended Commands]"])
    for item in payload["recommended_commands"]:
        lines.append(f"- {item}")
    return "\n".join(lines)
