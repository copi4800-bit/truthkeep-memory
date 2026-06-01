import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis_py.app import AegisApp
from aegis_py.retrieval.models import SearchQuery
from aegis_py.retrieval.engine import run_scoped_search

db_path = "ablation_temp_truthkeep_full.db"
app = AegisApp(db_path=db_path)

# Ingest giống hệt benchmark
app.put_memory("Mimi is a small blue robotic companion created in Tokyo.", type="episodic", subject="Mimi Profile", scope_type="agent", scope_id="default")

s_query = SearchQuery(
    query="Tokyo in created companion robotic blue small a is Mimi",
    scope_id="default",
    scope_type="agent",
    limit=5,
    include_global=True,
    semantic=True
)

canonical = run_scoped_search(
    app.storage,
    s_query.query,
    scope_type=s_query.scope_type,
    scope_id=s_query.scope_id,
    limit=s_query.limit,
    include_global=s_query.include_global,
)

for result in canonical:
    memory = app.storage.get_memory(result.id)
    if memory:
        from aegis_py.v10_scoring.query_signals import build_v10_query_signals
        from aegis_py.v10_scoring.adapter import map_to_v10_record
        
        query_signals = build_v10_query_signals(result, s_query.query, app.storage, context={"intent": "normal_recall"})
        v10_record = map_to_v10_record(memory, app.storage)
        
        trace = app.search_pipeline.v10_engine.scorer.score(v10_record, query_signals, intent="normal_recall")
        print(f"Base Score: {trace.base_score}")
        print(f"Judge Delta: {trace.judge_delta}")
        print(f"Life Delta: {trace.life_delta}")
        print(f"Hard Constraints Delta: {trace.hard_constraints_delta}")
        print(f"Trace Factors: {trace.factors}")
        print(f"Query Signals: {query_signals}")

app.storage.close()
import os
try:
    os.remove(db_path)
except Exception:
    pass
