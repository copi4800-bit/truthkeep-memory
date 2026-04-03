import json

from aegis_py.app import AegisApp
from aegis_py.mcp.server import AegisMCPServer


def test_ingest_persists_canonical_v10_state(tmp_path):
    app = AegisApp(str(tmp_path / "phase124_ingest.db"))
    try:
        stored = app.put_memory(
            "The release owner is Bao and Bao currently signs the rollout ledger.",
            type="semantic",
            scope_type="agent",
            scope_id="phase124_scope",
            source_kind="manual",
            source_ref="test://phase124-ingest",
            subject="release.owner",
            confidence=0.93,
            metadata={"is_winner": True},
        )
        row = app.storage.fetch_one("SELECT metadata_json FROM memories WHERE id = ?", (stored.id,))
        metadata = json.loads(row["metadata_json"])
        state = metadata["v10_state"]

        assert state["state_version"] == 1
        assert "belief_score" in state
        assert "trust_score" in state
        assert "readiness_score" in state
        assert "conflict_signal" in state
        assert "stability_signal" in state
        assert "last_v10_update_at" in state
        assert metadata["v10_dynamics"]["belief_score"] == state["belief_score"]
    finally:
        app.close()


def test_backfill_v10_state_restores_missing_canonical_contract(tmp_path):
    app = AegisApp(str(tmp_path / "phase124_backfill.db"))
    try:
        stored = app.put_memory(
            "The duty manager is Linh this week.",
            type="semantic",
            scope_type="agent",
            scope_id="phase124_scope",
            source_kind="manual",
            source_ref="test://phase124-backfill",
            subject="duty.manager",
            confidence=0.88,
        )
        app.storage.execute(
            "UPDATE memories SET metadata_json = json_remove(metadata_json, '$.v10_state') WHERE id = ?",
            (stored.id,),
        )

        result = app.backfill_v10_state(scope_type="agent", scope_id="phase124_scope")
        refreshed = app.storage.get_memory(stored.id)
        state = refreshed.metadata["v10_state"]

        assert result["refreshed"] >= 1
        assert state["state_version"] == 1
        assert "last_v10_update_at" in state
        assert refreshed.metadata["v10_dynamics"]["state_version"] == 1
    finally:
        app.close()


def test_v10_field_snapshot_reports_xi_t_state_coverage_and_energy_aliases(tmp_path):
    app = AegisApp(str(tmp_path / "phase124_snapshot.db"))
    try:
        app.put_memory(
            "Bao prefers black coffee during release nights.",
            type="semantic",
            scope_type="agent",
            scope_id="phase124_scope",
            source_kind="manual",
            source_ref="test://phase124-snapshot",
            subject="bao.preference.drink",
            confidence=0.9,
        )
        snapshot = app.v10_field_snapshot(scope_type="agent", scope_id="phase124_scope")

        assert snapshot["state_coverage"]["memory_count"] >= 1
        assert snapshot["state_coverage"]["canonical"] >= 1
        assert "belief_score" in snapshot["averages"]
        assert "stability_signal" in snapshot["averages"]
        assert "bundle_energy_proxy" in snapshot["energy"]
        assert "objective_proxy" in snapshot["energy"]
    finally:
        app.close()


def test_memory_v10_field_snapshot_tool_returns_operator_payload(tmp_path):
    server = AegisMCPServer(str(tmp_path / "phase124_tool.db"))
    try:
        server.app.put_memory(
            "The compliance owner is Minh.",
            type="semantic",
            scope_type="agent",
            scope_id="phase124_scope",
            source_kind="manual",
            source_ref="test://phase124-tool",
            subject="compliance.owner",
            confidence=0.9,
        )

        payload = json.loads(
            server.run_tool(
                "memory_v10_field_snapshot",
                {"scopeType": "agent", "scopeId": "phase124_scope"},
            )
        )

        assert payload["state_coverage"]["canonical"] >= 1
        assert "bundle_energy_proxy" in payload["energy"]
    finally:
        server.close()
