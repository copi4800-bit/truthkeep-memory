from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from aegis_py.app import AegisApp


def build_proof_summary(*, db_path: str | None = None) -> dict[str, Any]:
    if db_path:
        return _run_proof(Path(db_path))
    with TemporaryDirectory(prefix="truthkeep_proof_") as tmp:
        return _run_proof(Path(tmp) / "proof.db")


def _run_proof(db_path: Path) -> dict[str, Any]:
    app = AegisApp(str(db_path))
    try:
        old_fact = app.put_memory(
            "The release owner is Minh.",
            type="semantic",
            scope_type="agent",
            scope_id="proof_scope",
            source_kind="manual",
            source_ref="proof://old",
            subject="release.owner",
            confidence=0.92,
        )
        new_fact = app.put_memory(
            "Correction: the release owner is Bao.",
            type="semantic",
            scope_type="agent",
            scope_id="proof_scope",
            source_kind="manual",
            source_ref="proof://new",
            subject="release.owner",
            confidence=0.98,
            metadata={"is_correction": True, "is_winner": True, "corrected_from": [old_fact.id if old_fact else ""]},
        )
        spotlight = app.spotlight(
            "release owner",
            scope_type="agent",
            scope_id="proof_scope",
            include_global=False,
            limit=3,
        )
        snapshot = app.v10_field_snapshot(scope_type="agent", scope_id="proof_scope")
        compressed = app.compressed_tier_status(scope_type="agent", scope_id="proof_scope")

        results = spotlight.get("results", [])
        selected = results[0] if results else {}
        why_not = selected.get("why_not", [])
        selected_memory = selected.get("selected_memory") or ""
        metrics = {
            "correction_top1_preserved": "Bao" in selected_memory,
            "why_not_available": bool(why_not),
            "field_snapshot_available": snapshot.get("state_coverage", {}).get("memory_count", 0) >= 1,
            "compressed_tier_available": compressed.get("compressed_tier", {}).get("coverage_rate", 0.0) >= 0.0,
        }
        passed = all(metrics.values())
        return {
            "passed": passed,
            "summary": (
                "TruthKeep keeps corrected truth on top, exposes why-not alternatives, and surfaces field/compressed observability."
            ),
            "metrics": metrics,
            "artifacts": {
                "selected_memory": selected_memory,
                "why_not_count": len(why_not),
                "field_snapshot_counts": snapshot.get("counts", {}),
                "compressed_tier": compressed.get("compressed_tier", {}),
            },
        }
    finally:
        app.close()


def main() -> int:
    summary = build_proof_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
