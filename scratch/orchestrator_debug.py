import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis_py.app import AegisApp
from aegis_py.retrieval.models import SearchQuery

db_path = "ablation_temp_truthkeep_full.db"
app = AegisApp(db_path=db_path)

# Ingest giống hệt benchmark
app.put_memory("Mimi is a small blue robotic companion created in Tokyo.", type="episodic", subject="Mimi Profile", scope_type="agent", scope_id="default")
app.put_memory("The operating schedule for the backup server is 02:00 UTC daily.", type="procedural", subject="Backup Schedule", scope_type="agent", scope_id="default")

s_query = SearchQuery(
    query="Tokyo in created companion robotic blue small a is Mimi",
    scope_id="default",
    scope_type="agent",
    limit=5,
    include_global=True,
    semantic=True
)

base_results = app.search_pipeline.search_with_expansion(s_query)
vector_results = app.retrieval_orchestrator._vector_results(s_query)

print(f"Base results: {len(base_results)}")
for r in base_results:
    print(f"  {r.memory.content} | Reasons: {r.reasons} | Score: {r.score}")
    
print(f"Vector results: {len(vector_results)}")
for r in vector_results:
    print(f"  {r.memory.content} | Reasons: {r.reasons} | Score: {r.score}")

app.storage.close()
import os
try:
    os.remove(db_path)
except Exception:
    pass
