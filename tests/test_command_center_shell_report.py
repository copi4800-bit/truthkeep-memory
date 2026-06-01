from __future__ import annotations

from aegis_py.command_center_shell_report import render_command_center_shell_html


def test_command_center_shell_report_renders_all_major_panels():
    payload = {
        "command_center_text": "[TruthKeep Command Center]\n[Workflow Loop]\n[Truth Timeline]\n[Operator Mode]",
        "result": {
            "hero": {
                "readiness": "ready",
                "health_state": "HEALTHY",
                "truth_role": "winner",
                "governance_status": "active",
                "selected_memory": "Correction: the release owner is Bao.",
            },
            "ordinary_mode": {
                "description": "The narrow daily path for normal use.",
                "actions": [{"tool": "memory_recall", "why": "Inspect the current truth."}],
            },
            "workflow_loop": {
                "steps": [{"title": "Verify", "summary": "Confirm the winning fact."}],
            },
            "truth_timeline": {
                "story": "Current truth replaced an older candidate.",
                "preview": ["winner: Bao", "superseded: Linh"],
            },
            "deep_inspection": {
                "summary": "Governance chose the newer correction.",
                "signals": ["trust=0.91", "readiness=0.84", "evidence=2"],
            },
            "operator_mode": {
                "description": "Inspection and maintenance tools for advanced use.",
                "actions": ["memory_governance", "memory_v10_field_snapshot"],
            },
            "recommended_commands": ["truthkeep field-snapshot", "truthkeep prove-it"],
        },
    }

    html = render_command_center_shell_html(payload)

    assert "TruthKeep Command Center" in html
    assert "Ordinary Mode" in html
    assert "Workflow Loop" in html
    assert "Truth Timeline" in html
    assert "Deep Inspection" in html
    assert "Operator Mode" in html
