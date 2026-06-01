"""Lightweight Runtime Profile Benchmark for TruthKeep.

This benchmark is intentionally small and safe. It measures the operational hot
path (`remember`, `recall`, `correct`) under each runtime profile and writes
both JSON and Markdown reports. It is not an enterprise load test; it is a local
regression guard that proves profile switching does not break TruthKeep's core.
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from aegis_py.app import AegisApp
from aegis_py.runtime.profile import PROFILES
from aegis_py.version import get_runtime_version


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * 0.95))))
    return ordered[idx]


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "count": float(len(values)),
        "p50_ms": round(statistics.median(values), 3) if values else 0.0,
        "p95_ms": round(_p95(values), 3),
        "max_ms": round(max(values), 3) if values else 0.0,
    }


def _measure(fn) -> tuple[Any, float]:
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return result, elapsed_ms


def run_profile_benchmark(*, records: int = 10, db_root: str | None = None) -> dict[str, Any]:
    records = max(5, int(records))
    root = Path(db_root or tempfile.mkdtemp(prefix="truthkeep-profile-bench-"))
    root.mkdir(parents=True, exist_ok=True)
    old_profile = os.environ.get("TK_RUNTIME_PROFILE")
    results: dict[str, Any] = {
        "truthkeep_version": get_runtime_version(),
        "records_per_profile": records,
        "profiles": {},
        "note": "Local hot-path benchmark; not a cloud/enterprise load test.",
    }

    try:
        for profile_name, flags in PROFILES.items():
            os.environ["TK_RUNTIME_PROFILE"] = profile_name
            db_path = root / f"{profile_name}.db"
            if db_path.exists():
                db_path.unlink()
            app = AegisApp(str(db_path))
            remember_ms: list[float] = []
            recall_ms: list[float] = []
            correct_ms: list[float] = []
            try:
                for idx in range(records):
                    content = f"Profile {profile_name}: project transport current truth is MCP stdio only #{idx}"
                    _, elapsed = _measure(lambda c=content: app.memory_remember(c))
                    remember_ms.append(elapsed)
                for idx in range(max(5, records // 3)):
                    _, elapsed = _measure(lambda: app.memory_recall("project transport current truth"))
                    recall_ms.append(elapsed)
                for idx in range(max(3, records // 5)):
                    content = f"Correction {idx}: not HTTP daemon, current truth is MCP stdio only in profile {profile_name}"
                    _, elapsed = _measure(lambda c=content: app.memory_correct(c))
                    correct_ms.append(elapsed)
                status = app.status()
            finally:
                app.close()
            results["profiles"][profile_name] = {
                "flags": flags.to_dict(),
                "remember": _stats(remember_ms),
                "recall": _stats(recall_ms),
                "correct": _stats(correct_ms),
                "db_size_bytes": db_path.stat().st_size if db_path.exists() else 0,
                "status_counts": status.get("counts", {}),
            }
    finally:
        if old_profile is None:
            os.environ.pop("TK_RUNTIME_PROFILE", None)
        else:
            os.environ["TK_RUNTIME_PROFILE"] = old_profile
    return results


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TruthKeep Runtime Profile Benchmark",
        "",
        f"TruthKeep version: `{report.get('truthkeep_version')}`",
        f"Records per profile: `{report.get('records_per_profile')}`",
        "",
        "This is a small local hot-path benchmark for `remember`, `recall`, and `correct`. It is not an enterprise load test.",
        "",
        "| Profile | Remember p50/p95 ms | Recall p50/p95 ms | Correct p50/p95 ms | DB KB | Heavy simulators |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, payload in report.get("profiles", {}).items():
        flags = payload.get("flags", {})
        heavy = []
        if flags.get("enable_fhe_simulator"):
            heavy.append("FHE")
        if flags.get("enable_pqc_simulator"):
            heavy.append("PQC")
        if flags.get("enable_tda_signature"):
            heavy.append("TDA")
        if not heavy:
            heavy.append("off")
        db_kb = payload.get("db_size_bytes", 0) / 1024.0
        r = payload["remember"]
        q = payload["recall"]
        c = payload["correct"]
        lines.append(
            f"| `{name}` | {r['p50_ms']} / {r['p95_ms']} | {q['p50_ms']} / {q['p95_ms']} | {c['p50_ms']} / {c['p95_ms']} | {db_kb:.1f} | {', '.join(heavy)} |"
        )
    lines.extend([
        "",
        "## DNA flags",
        "",
        "Graph governance, memory correction, superseded suppression, why-not provenance, and invariants must remain enabled in every profile.",
    ])
    return "\n".join(lines) + "\n"


def write_profile_reports(report: dict[str, Any], *, json_path: str, markdown_path: str) -> None:
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(markdown_path).write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    report = run_profile_benchmark(records=int(os.environ.get("TK_BENCH_RECORDS", "10")))
    write_profile_reports(report, json_path="reports/profile_benchmark.json", markdown_path="reports/profile_benchmark.md")
    print(render_markdown(report))
