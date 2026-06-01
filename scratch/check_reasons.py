import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis_py.app import AegisApp
from aegis_py.retrieval.engine import run_scoped_search

db_path = "ablation_temp_truthkeep_full.db"
app = AegisApp(db_path=db_path)

# Ingest giống hệt benchmark
app.put_memory("Mimi is a small blue robotic companion created in Tokyo.", type="episodic", subject="Mimi Profile", scope_type="agent", scope_id="default")

canonical = run_scoped_search(
    app.storage,
    "Tokyo in created companion robotic blue small a is Mimi",
    scope_type="agent",
    scope_id="default",
    limit=5
)

print(f"Canonical results count: {len(canonical)}")
if canonical:
    for idx, r in enumerate(canonical):
        print(f"Rank {idx+1}: {r.content}")
        print(f"Reasons: {r.reasons}")
        print(f"Score: {r.score}")

app.storage.close()
import os
try:
    os.remove(db_path)
except Exception:
    pass
