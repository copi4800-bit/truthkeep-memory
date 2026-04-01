import os
import asyncio
import time
import json
from typing import List, Any
from aegis_py.storage.manager import StorageManager
from aegis_py.memory.core import MemoryManager
from aegis_py.retrieval.search import SearchPipeline
from aegis_py.retrieval.models import SearchQuery, SearchResult
from aegis_py.storage.models import Memory

class V10ShadowEvaluator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if os.path.exists(db_path):
            os.remove(db_path)
        self.storage = StorageManager(db_path)
        self.manager = MemoryManager(self.storage)
        self.pipeline = SearchPipeline(self.storage)
        self.scenarios = []

    def setup_scenarios(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        # Scenario 1: Truth Alignment (Correction)
        # Old fact vs New fact
        m1 = Memory(id="s1_old", type="semantic", content="Alice is the CEO.", subject="ceo", confidence=0.8, source_kind="manual", source_ref="m1", scope_type="agent", scope_id="s1")
        m2 = Memory(id="s1_new", type="semantic", content="Actually, Bob is the CEO now.", subject="ceo", confidence=1.0, source_kind="manual", source_ref="m2", scope_type="agent", scope_id="s1")
        self.manager.store(m1)
        self.manager.store(m2)
        self.storage.execute("UPDATE memories SET status = 'superseded' WHERE id = 's1_old'")
        # FTS manually for test
        self.storage.execute("INSERT INTO memories_fts(rowid, content, subject) VALUES ((SELECT rowid FROM memories WHERE id = 's1_old'), ?, ?)", (m1.content, m1.subject))
        self.storage.execute("INSERT INTO memories_fts(rowid, content, subject) VALUES ((SELECT rowid FROM memories WHERE id = 's1_new'), ?, ?)", (m2.content, m2.subject))
        self.scenarios.append({"name": "Truth Alignment", "query": "CEO", "expected_top": "s1_new", "scope": ("agent", "s1")})

        # Scenario 2: Trust vs Lexical
        # High lexical match but low trust vs Low lexical but high trust
        m3 = Memory(id="s2_flashy", type="semantic", content="X is super great project.", subject="proj_x", confidence=0.2, source_kind="manual", source_ref="m3", scope_type="agent", scope_id="s2", metadata={"is_winner": False})
        m4 = Memory(id="s2_trusted", type="semantic", content="Project X status is stable.", subject="proj_x", confidence=0.9, source_kind="manual", source_ref="m4", scope_type="agent", scope_id="s2", metadata={"is_winner": True})
        self.manager.store(m3)
        self.manager.store(m4)
        # Add 3 evidence events for m4 to boost v10 trust
        for i in range(3):
            self.storage.execute("INSERT INTO evidence_events (id, scope_type, scope_id, memory_id, source_kind, source_ref, raw_content, created_at) VALUES (?, 'agent', 's2', 's2_trusted', 'test', 'ref', 'Confirmed status', ?)", (f"evt_{i}", now))
        
        self.storage.execute("INSERT INTO memories_fts(rowid, content, subject) VALUES ((SELECT rowid FROM memories WHERE id = 's2_flashy'), ?, ?)", (m3.content, m3.subject))
        self.storage.execute("INSERT INTO memories_fts(rowid, content, subject) VALUES ((SELECT rowid FROM memories WHERE id = 's2_trusted'), ?, ?)", (m4.content, m4.subject))
        self.scenarios.append({"name": "Trust vs Lexical", "query": "Project X status", "expected_top": "s2_trusted", "scope": ("agent", "s2")})

        # Scenario 3: Conflict Suppression
        m5 = Memory(id="s3_normal", type="semantic", content="Server is at 10.0.0.1", subject="ip", confidence=0.7, source_kind="manual", source_ref="m5", scope_type="agent", scope_id="s3")
        m6 = Memory(id="s3_conflict", type="semantic", content="Server is at 10.0.0.2", subject="ip", confidence=0.7, source_kind="manual", source_ref="m6", scope_type="agent", scope_id="s3")
        self.manager.store(m5)
        self.manager.store(m6)
        self.storage.execute("INSERT INTO conflicts (id, subject_key, memory_a_id, memory_b_id, score, status, created_at) VALUES ('c1', 'ip', 's3_normal', 's3_conflict', 0.8, 'open', ?)", (now,))
        self.storage.execute("INSERT INTO memories_fts(rowid, content, subject) VALUES ((SELECT rowid FROM memories WHERE id = 's3_normal'), ?, ?)", (m5.content, m5.subject))
        self.storage.execute("INSERT INTO memories_fts(rowid, content, subject) VALUES ((SELECT rowid FROM memories WHERE id = 's3_conflict'), ?, ?)", (m6.content, m6.subject))
        self.scenarios.append({"name": "Conflict Suppression", "query": "Server IP", "expected_action": "suppress", "scope": ("agent", "s3")})

    async def evaluate(self):
        self.setup_scenarios()
        results = []
        
        print(f"{'Scenario':<25} | {'Metric':<20} | {'v10 Result':<10} | {'v10 Result':<10} | {'Status'}")
        print("-" * 85)

        for s in self.scenarios:
            # Run v10
            q_v10 = SearchQuery(query=s["query"], scope_type=s["scope"][0], scope_id=s["scope"][1], min_score=-10.0)
            setattr(q_v10, "scoring_mode", "v10_primary")
            
            start_v10 = time.perf_counter()
            res_v10 = self.pipeline.search(q_v10)
            lat_v10 = (time.perf_counter() - start_v10) * 1000

            # Run v10
            q_v10 = SearchQuery(query=s["query"], scope_type=s["scope"][0], scope_id=s["scope"][1], min_score=-10.0)
            setattr(q_v10, "scoring_mode", "v10_primary")
            
            start_v10 = time.perf_counter()
            res_v10 = self.pipeline.search(q_v10)
            lat_v10 = (time.perf_counter() - start_v10) * 1000

            v10_top = res_v10[0].memory.id if res_v10 else "None"
            v10_top = res_v10[0].memory.id if res_v10 else "None"
            
            success = False
            metric = "Top-1 Match"
            if "expected_top" in s:
                success = (v10_top == s["expected_top"])
                v10_val = "PASS" if v10_top == s["expected_top"] else "FAIL"
                v10_val = "PASS" if v10_top == s["expected_top"] else "FAIL"
            elif s.get("expected_action") == "suppress":
                metric = "Suppression"
                # v10 should penalize/suppress conflict records more heavily (lower score)
                v10_score = res_v10[0].score if res_v10 else 0
                v10_score = res_v10[0].v10_score if res_v10 else 0
                success = (v10_score < 0) # Should be heavily penalized
                v10_val = f"{v10_score:.2f}"
                v10_val = f"{v10_score:.2f}"

            status_mark = "✅" if success else "❌"
            print(f"{s['name']:<25} | {metric:<20} | {v10_val:<10} | {v10_val:<10} | {status_mark}")
            
            if not success:
                print(f"   [Audit all v10 results]:")
                for r in res_v10:
                    t = r.v10_trace
                    print(f"     - {r.memory.id}: score={r.v10_score:.2f}, base={t.base_score:.2f}, judge={t.judge_delta:+.2f}, factors={ {k:round(v,2) for k,v in t.factors.items() if abs(v)>0.01} }")
            
            results.append({
                "scenario": s["name"],
                "latency_v10": lat_v10,
                "latency_v10": lat_v10,
                "success": success
            })

        # Latency Report
        avg_lat_v10 = sum(r["latency_v10"] for r in results) / len(results)
        avg_lat_v10 = sum(r["latency_v10"] for r in results) / len(results)
        print("-" * 85)
        print(f"Average Latency (ms):      | v10: {avg_lat_v10:.2f}ms | v10: {avg_lat_v10:.2f}ms | Overhead: {((avg_lat_v10/avg_lat_v10)-1)*100:+.1f}%")
        
        # Cleanup
        self.storage.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

if __name__ == "__main__":
    evaluator = V10ShadowEvaluator("/home/hali/.openclaw/extensions/memory-aegis-v10/v10_shadow_eval.db")
    asyncio.run(evaluator.evaluate())
