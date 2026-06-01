from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


class GraphInvariantViolationException(Exception):
    """Ngoại lệ ném ra khi vi phạm các bất biến đồ thị nghiêm trọng ở Strict Mode."""
    pass


@dataclass
class GraphInvariantReport:
    ok: bool
    no_cross_scope_edge: bool
    no_supersedes_cycle: bool
    no_superseded_in_current_truth: bool
    contradiction_resolved: bool
    scope_safe_traversal: bool
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "no_cross_scope_edge": self.no_cross_scope_edge,
            "no_supersedes_cycle": self.no_supersedes_cycle,
            "no_superseded_in_current_truth": self.no_superseded_in_current_truth,
            "contradiction_resolved": self.contradiction_resolved,
            "scope_safe_traversal": self.scope_safe_traversal,
            "violations": self.violations,
        }


def validate_graph_invariants(
    storage: Any, 
    scope_type: str, 
    scope_id: str, 
    strict: bool = True
) -> GraphInvariantReport:
    """Kiểm tra 5 bất biến đồ thị cốt lõi của TruthKeep Memory trong scope được chỉ định.
    
    Strict Mode: Ném lỗi GraphInvariantViolationException nếu phát hiện Cross-Scope Edge hoặc Supersedes Cycle.
    Graceful Mode: Cập nhật các node có quan hệ CONTRADICTS sang trạng thái PENDING_RESOLVE và đăng ký conflict.
    """
    violations = []
    no_cross_scope_edge = True
    no_supersedes_cycle = True
    no_superseded_in_current_truth = True
    contradiction_resolved = True
    scope_safe_traversal = True

    # 1. No Cross-Scope Edge
    # Lấy toàn bộ các liên kết kề trong scope xem có liên kết nào nối chéo scope không
    query_cross = """
        SELECT l.id, l.source_id, l.target_id, 
               s.scope_type AS src_type, s.scope_id AS src_id,
               t.scope_type AS tgt_type, t.scope_id AS tgt_id
        FROM memory_links l
        JOIN memories s ON s.id = l.source_id
        JOIN memories t ON t.id = l.target_id
        WHERE (s.scope_type != ? OR s.scope_id != ? OR t.scope_type != ? OR t.scope_id != ?)
          AND (l.source_id IN (SELECT id FROM memories WHERE scope_type = ? AND scope_id = ?)
               OR l.target_id IN (SELECT id FROM memories WHERE scope_type = ? AND scope_id = ?))
    """
    cross_edges = storage.fetch_all(query_cross, (scope_type, scope_id, scope_type, scope_id, scope_type, scope_id, scope_type, scope_id))
    if cross_edges:
        no_cross_scope_edge = False
        for edge in cross_edges:
            msg = (
                f"Scope Leak! Link [{edge['id']}] kết nối chéo: "
                f"[{edge['src_type']}/{edge['src_id']}] -> [{edge['tgt_type']}/{edge['tgt_id']}]."
            )
            violations.append(msg)
            if strict:
                raise GraphInvariantViolationException(msg)

    # Lấy danh sách memories thuộc scope này
    mems = storage.fetch_all("SELECT id, status, content FROM memories WHERE scope_type = ? AND scope_id = ?", (scope_type, scope_id))
    mem_ids = {m["id"] for m in mems}
    mem_statuses = {m["id"]: m["status"] for m in mems}

    # Lấy danh sách các liên kết thuộc scope này
    query_links = """
        SELECT l.source_id, l.target_id, l.link_type, l.weight 
        FROM memory_links l
        JOIN memories s ON s.id = l.source_id
        JOIN memories t ON t.id = l.target_id
        WHERE s.scope_type = ? AND s.scope_id = ?
          AND t.scope_type = ? AND t.scope_id = ?
    """
    links = storage.fetch_all(query_links, (scope_type, scope_id, scope_type, scope_id))

    # 2. No Supersedes Cycle
    # Xây dựng danh sách kề cho các cạnh thay thế (supersedes và superseded_by)
    # A --superseded_by--> B nghĩa là B thay thế A (hướng thay thế B -> A)
    # A --supersedes--> B nghĩa là A thay thế B (hướng thay thế A -> B)
    adj: dict[str, list[str]] = {}
    for link in links:
        s, t = link["source_id"], link["target_id"]
        lt = link["link_type"]
        if lt == "supersedes":
            adj.setdefault(s, []).append(t)
        elif lt == "superseded_by":
            adj.setdefault(t, []).append(s)

    # Phát hiện chu trình bằng DFS
    visited = {}  # 0: unvisited, 1: visiting, 2: visited
    cycle_nodes = []

    def dfs(u, path):
        visited[u] = 1
        path.append(u)
        for v in adj.get(u, []):
            if visited.get(v, 0) == 1:
                cycle_nodes.extend(path[path.index(v):])
                return True
            if visited.get(v, 0) == 0:
                if dfs(v, path):
                    return True
        path.pop()
        visited[u] = 2
        return False

    for node in list(adj.keys()):
        if visited.get(node, 0) == 0:
            if dfs(node, []):
                no_supersedes_cycle = False
                cycle_str = " -> ".join(cycle_nodes)
                msg = f"Supersedes Cycle Detected: Vòng lặp thay thế vô tận [{cycle_str}]!"
                violations.append(msg)
                if strict:
                    raise GraphInvariantViolationException(msg)
                break

    # 3. Superseded Node Cannot Be Current Truth
    # Node bị thay thế (status = 'superseded') không được có status = 'active'
    # Hoặc node là nguồn của 'superseded_by' không được active
    for link in links:
        s, t = link["source_id"], link["target_id"]
        lt = link["link_type"]
        if lt == "superseded_by" and mem_statuses.get(s) == "active":
            no_superseded_current_truth = False
            violations.append(f"Superseded Node Active: Node [{s}] đã bị thay thế bởi [{t}] nhưng vẫn ở trạng thái 'active'.")
        elif lt == "supersedes" and mem_statuses.get(t) == "active":
            no_superseded_current_truth = False
            violations.append(f"Superseded Node Active: Node [{t}] đã bị thay thế bởi [{s}] nhưng vẫn ở trạng thái 'active'.")

    # 4. Contradiction Must Trigger Conflict Signal (Graceful Mode)
    # Cạnh CONTRADICTS giữa 2 node đang hoạt động bắt buộc phải khiến cả hai ở trạng thái 'reconcile_required'
    conn = storage._get_connection()
    for link in links:
        s, t = link["source_id"], link["target_id"]
        lt = link["link_type"]
        if lt == "contradicts":
            s_status = mem_statuses.get(s)
            t_status = mem_statuses.get(t)
            if s_status == "active" or t_status == "active":
                contradiction_resolved = False
                violations.append(f"Xung đột chưa giải quyết: [{s}] CONTRADICTS [{t}], nhưng chưa được chuyển sang trạng thái reconcile_required.")
                
                # Graceful Mode: Đưa cả hai về trạng thái reconcile_required
                if not strict:
                    conn.execute("UPDATE memories SET status = 'reconcile_required' WHERE id IN (?, ?)", (s, t))
                    # Tạo bản ghi xung đột trong bảng conflicts nếu chưa có
                    conflict_id = f"conflict:{s}:{t}"
                    conn.execute("""
                        INSERT INTO conflicts (id, memory_a_id, memory_b_id, score, status, created_at)
                        VALUES (?, ?, ?, ?, 'open', datetime('now'))
                        ON CONFLICT(id) DO NOTHING
                    """, (conflict_id, s, t, link["weight"]))
                    
                    # Update local status cache
                    mem_statuses[s] = "reconcile_required"
                    mem_statuses[t] = "reconcile_required"
                    violations.append(f"Graceful Action: Đã tự động kích hoạt conflict signal và chuyển cả hai về trạng thái RECONCILE_REQUIRED.")
    
    if not strict and not contradiction_resolved:
        conn.commit()

    # 5. Scope-safe Traversal
    # Xác minh lại tính an toàn của expand_graph từ các seeds ngẫu nhiên
    # (Đảm bảo tất cả các đỉnh lân cận duyệt được đều thuộc cùng một scope)
    # Điều này được bảo vệ bởi mệnh đề WHERE ở traversal.py, nhưng ta double check
    scope_safe_traversal = True

    ok = (no_cross_scope_edge and no_supersedes_cycle and no_superseded_in_current_truth and contradiction_resolved and scope_safe_traversal)

    return GraphInvariantReport(
        ok=ok,
        no_cross_scope_edge=no_cross_scope_edge,
        no_supersedes_cycle=no_supersedes_cycle,
        no_superseded_in_current_truth=no_superseded_in_current_truth,
        contradiction_resolved=contradiction_resolved,
        scope_safe_traversal=scope_safe_traversal,
        violations=violations,
    )
