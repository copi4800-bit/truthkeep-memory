from __future__ import annotations

from aegis_py.app import AegisApp


def test_row_to_memory_ignores_legacy_kind_column(tmp_path):
    app = AegisApp(str(tmp_path / "legacy_kind.db"))
    try:
        memory = app.put_memory(
            "Legacy kind compatibility check.",
            type="semantic",
            scope_type="agent",
            scope_id="legacy",
            source_kind="manual",
            subject="legacy.kind",
        )
        row = app.storage.fetch_one("SELECT * FROM memories WHERE id = ?", (memory.id,))
        legacy_row = dict(row)
        legacy_row["kind"] = "semantic"

        hydrated = app.storage._row_to_memory(legacy_row)

        assert hydrated.id == memory.id
        assert hydrated.type == "semantic"
        assert hydrated.content == "Legacy kind compatibility check."
    finally:
        app.close()
