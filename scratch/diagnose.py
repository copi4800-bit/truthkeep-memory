import os
import sys

sys.path.insert(0, os.path.abspath("."))
from aegis_py.app import AegisApp
from aegis_py.retrieval.search import SearchPipeline, SearchQuery

db_path = "diagnose_temp.db"
if os.path.exists(db_path):
    os.remove(db_path)

app = AegisApp(db_path=db_path)
try:
    mem_mimi = app.put_memory("Mimi is a small blue robotic companion created in Tokyo.", type="episodic", subject="Mimi Profile", scope_type="agent", scope_id="default")
    
    # Cập nhật metadata_json chứa is_winner: true và status = active
    app.storage.execute(
        "UPDATE memories SET confidence = 1.0, activation_score = 2.0, status = 'active', metadata_json = '{\"is_winner\": true}' WHERE id = ?",
        (mem_mimi.id,)
    )
    
    # Khởi tạo SearchPipeline
    pipeline = SearchPipeline(app.storage)
    query_obj = SearchQuery(
        query="Mimi",
        scope_type="agent",
        scope_id="default",
        limit=5,
        include_global=False,
        semantic=False
    )
    
    from aegis_py.retrieval.engine import run_scoped_search
    canonical = run_scoped_search(pipeline.storage, "Mimi", scope_type="agent", scope_id="default", limit=5)
    
    for result in canonical:
        memory = pipeline.storage.get_memory(result.id)
        context = {"intent": "normal_recall"}
        from aegis_py.v10_scoring.query_signals import build_v10_query_signals
        from aegis_py.v10_scoring.adapter import map_to_v10_record
        query_signals = build_v10_query_signals(result, "Mimi", pipeline.storage, context=context)
        v10_record = map_to_v10_record(memory, pipeline.storage)
        decision = pipeline.v10_engine.govern(v10_record, query_signals, intent="normal_recall")
        print(f"Candidate: {memory.id}, status: {memory.status}, admissible: {decision.admissible}, v10_status: {decision.governance_status}, reasons: {decision.decision_reason}")
            
finally:
    app.storage.close()
    if os.path.exists(db_path):
        os.remove(db_path)
