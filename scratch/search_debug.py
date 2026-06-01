import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis_py.app import AegisApp

db_path = "ablation_temp_truthkeep_full.db"
app = AegisApp(db_path=db_path)

# Ingest giống hệt benchmark
app.put_memory("Mimi is a small blue robotic companion created in Tokyo.", type="episodic", subject="Mimi Profile", scope_type="agent", scope_id="default")
app.put_memory("The operating schedule for the backup server is 02:00 UTC daily.", type="procedural", subject="Backup Schedule", scope_type="agent", scope_id="default")

# Query
recall_2 = app.search_payload("Tokyo in created companion robotic blue small a is Mimi", scope_type="agent", scope_id="default", limit=5)

print(f"Recall count: {len(recall_2)}")
if recall_2:
    for idx, r in enumerate(recall_2):
        print(f"Rank {idx+1}: {r['memory']['content']}")
        print(f"Reasons: {r.get('reasons')}")
        print(f"Score: {r['score']}")

app.storage.close()
import os
try:
    os.remove(db_path)
except Exception:
    pass
