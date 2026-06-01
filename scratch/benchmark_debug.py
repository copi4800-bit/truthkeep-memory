import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis_py.app import AegisApp

db_path = "ablation_temp_truthkeep_full.db"
app = AegisApp(db_path=db_path)

# Ingest giống hệt benchmark
app.put_memory("Mimi is a small blue robotic companion created in Tokyo.", type="episodic", subject="Mimi Profile", scope_type="agent", scope_id="default")
mem_mimi = app.storage.fetch_one("SELECT id FROM memories WHERE subject = 'Mimi Profile'")
if mem_mimi:
    app.storage.execute("UPDATE memories SET confidence = 1.0, activation_score = 1.5 WHERE id = ?", (mem_mimi["id"],))

mem_base = app.put_memory("The operating schedule for the backup server is 02:00 UTC daily.", type="procedural", subject="Backup Schedule", scope_type="agent", scope_id="default")
base_id = mem_base.id if mem_base else None

mem_linked = app.put_memory("The maintenance script relies on the backup server schedule.", type="procedural", subject="Maintenance Job", scope_type="agent", scope_id="default")
linked_id = mem_linked.id if mem_linked else None

if base_id and linked_id:
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat()
    app.storage.execute(
        "INSERT INTO memory_links (source_id, target_id, link_type, weight, created_at) VALUES (?, ?, 'procedural_supports_semantic', 0.8, ?)",
        (base_id, linked_id, now_str)
    )
    
app.put_memory("Mimi creator left Tokyo in 2024 to join research team.", type="episodic", subject="Mimi Profile", scope_type="agent", scope_id="default")

# Nạp 50 noise
for i in range(50):
    app.put_memory(
        f"Synthetic background knowledge noise block number {i} containing random technical context details.",
        type="semantic",
        subject=f"Noise block {i}",
        scope_type="agent",
        scope_id="default"
    )

app.put_memory("The operating schedule for the backup server is now changed to 04:00 UTC daily.", type="procedural", subject="Backup Schedule", scope_type="agent", scope_id="default")

# Query 1
recall_1 = app.search_payload("What is the operating schedule of the backup server?", scope_type="agent", scope_id="default", limit=5)
print(f"Recall 1 Count: {len(recall_1)}")
if recall_1:
    for idx, r in enumerate(recall_1):
        print(f"  Rank {idx+1}: {r['memory']['content']} | Reasons: {r.get('reasons')} | Score: {r['score']}")

# Query 2
recall_2 = app.search_payload("Tokyo in created companion robotic blue small a is Mimi", scope_type="agent", scope_id="default", limit=5)
print(f"Recall 2 Count: {len(recall_2)}")
if recall_2:
    for idx, r in enumerate(recall_2):
        print(f"  Rank {idx+1}: {r['memory']['content']} | Reasons: {r.get('reasons')} | Score: {r['score']}")

app.storage.close()
import os
try:
    os.remove(db_path)
except Exception:
    pass
