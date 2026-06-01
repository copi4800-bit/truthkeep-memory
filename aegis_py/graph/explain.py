from __future__ import annotations

from typing import Any
from .relation_types import RelationType


RELATION_LABELS_VI = {
    RelationType.SUPERSEDES.value: "thay thế cho",
    RelationType.SUPERSEDED_BY.value: "bị thay thế bởi",
    RelationType.CONTRADICTS.value: "mâu thuẫn với",
    RelationType.RESOLVES.value: "giải quyết xung đột cho",
    RelationType.EVIDENCE_FOR.value: "là bằng chứng cho",
    RelationType.FALSIFIES.value: "bác bỏ",
    RelationType.SUPPORTS.value: "hỗ trợ cho",
    RelationType.DEPENDS_ON.value: "phụ thuộc vào",
    RelationType.DERIVED_FROM.value: "được kế thừa từ",
    RelationType.PART_OF.value: "là một phần của",
    RelationType.RELATED_TO.value: "có liên quan tới",
}


def explain_graph_path(
    storage: Any,
    source_id: str,
    target_id: str,
    scope_type: str,
    scope_id: str,
    max_hops: int = 3,
) -> dict[str, Any]:
    """Tìm đường đi ngắn nhất giữa source_id và target_id và sinh lời giải thích tiếng Việt điện ảnh."""
    if source_id == target_id:
        return {
            "found": True,
            "path": [source_id],
            "explanation": f"Ký ức [{source_id}] chính là bản thân nó.",
            "steps": [],
        }

    # BFS tìm đường đi ngắn nhất
    queue = [[source_id]]
    visited = {source_id}
    path_edges = []

    # Cache tất cả các cạnh trong scope để duyệt nhanh
    query = """
        SELECT 
            l.source_id, l.target_id, l.link_type, l.weight,
            s.content AS source_content, t.content AS target_content
        FROM memory_links l
        JOIN memories s ON s.id = l.source_id
        JOIN memories t ON t.id = l.target_id
        WHERE s.scope_type = ? AND s.scope_id = ?
          AND t.scope_type = ? AND t.scope_id = ?
          AND s.status IN ('active', 'pending_resolve', 'superseded', 'archived')
          AND t.status IN ('active', 'pending_resolve', 'superseded', 'archived')
    """
    rows = storage.fetch_all(query, (scope_type, scope_id, scope_type, scope_id))
    
    # Xây dựng danh sách kề
    adj: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        s, t = row["source_id"], row["target_id"]
        adj.setdefault(s, []).append({
            "neighbor": t,
            "direction": "forward",
            "link_type": row["link_type"],
            "weight": row["weight"],
            "source_content": row["source_content"],
            "target_content": row["target_content"],
        })
        adj.setdefault(t, []).append({
            "neighbor": s,
            "direction": "backward",
            "link_type": row["link_type"],
            "weight": row["weight"],
            "source_content": row["source_content"],
            "target_content": row["target_content"],
        })

    found_path = None
    while queue:
        curr_path = queue.pop(0)
        curr_node = curr_path[-1]
        
        if len(curr_path) - 1 >= max_hops:
            continue
            
        if curr_node == target_id:
            found_path = curr_path
            break
            
        for edge in adj.get(curr_node, []):
            neighbor = edge["neighbor"]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(curr_path + [neighbor])

    if not found_path:
        return {
            "found": False,
            "explanation": f"Không tìm thấy bất kỳ liên kết trực tiếp hay gián tiếp nào (tối đa {max_hops} hops) giữa hai ký ức trong scope [{scope_type}/{scope_id}].",
            "path": [],
            "steps": [],
        }

    # Xây dựng các bước giải thích
    steps = []
    explanation_parts = []
    
    for i in range(len(found_path) - 1):
        u = found_path[i]
        v = found_path[i+1]
        
        # Tìm cạnh tương ứng
        matching_edge = None
        for edge in adj.get(u, []):
            if edge["neighbor"] == v:
                matching_edge = edge
                break
                
        if matching_edge:
            link_type = matching_edge["link_type"]
            rel_label = RELATION_LABELS_VI.get(link_type, f"có quan hệ [{link_type}] với")
            weight = matching_edge["weight"]
            
            s_text = matching_edge["source_content"][:30] + "..." if len(matching_edge["source_content"]) > 30 else matching_edge["source_content"]
            t_text = matching_edge["target_content"][:30] + "..." if len(matching_edge["target_content"]) > 30 else matching_edge["target_content"]
            
            if matching_edge["direction"] == "forward":
                part = f"Ký ức [{u}] ('{s_text}') {rel_label} ký ức [{v}] ('{t_text}') [độ mạnh: {weight:.2f}]"
            else:
                part = f"Ký ức [{u}] ('{s_text}') {rel_label} ký ức [{v}] ('{t_text}') [định hướng ngược, độ mạnh: {weight:.2f}]"
                
            explanation_parts.append(part)
            steps.append({
                "source": u,
                "target": v,
                "link_type": link_type,
                "direction": matching_edge["direction"],
                "weight": weight,
            })

    explanation_str = " -> ".join(explanation_parts) + "."
    return {
        "found": True,
        "path": found_path,
        "explanation": explanation_str,
        "steps": steps,
    }


def explain_why_not(storage: Any, memory_id: str, scope_type: str, scope_id: str) -> dict[str, Any]:
    """Giải thích tại sao một ký ức cụ thể bị từ chối hoặc hạ rank trong Why-Not Analysis."""
    # 1. Kiểm tra xem ký ức có tồn tại không
    mem = storage.fetch_one(
        "SELECT status, content, confidence FROM memories WHERE id = ? AND scope_type = ? AND scope_id = ?",
        (memory_id, scope_type, scope_id)
    )
    if not mem:
        return {
            "status": "not_found",
            "explanation": f"Ký ức [{memory_id}] không tồn tại trong scope [{scope_type}/{scope_id}].",
        }
        
    status = mem["status"]
    content_snippet = mem["content"][:60] + "..." if len(mem["content"]) > 60 else mem["content"]
    confidence = mem["confidence"]
    
    # 2. Xử lý theo từng trạng thái cụ thể
    if status == "superseded":
        # Tìm node đã thay thế nó (quan hệ SUPERSEDES hướng ngược hoặc SUPERSEDED_BY hướng xuôi)
        query = """
            SELECT target_id, weight FROM memory_links 
            WHERE source_id = ? AND link_type = 'superseded_by'
            UNION
            SELECT source_id AS target_id, weight FROM memory_links
            WHERE target_id = ? AND link_type = 'supersedes'
            LIMIT 1
        """
        replacer = storage.fetch_one(query, (memory_id, memory_id))
        if replacer:
            replacer_id = replacer["target_id"]
            rep_mem = storage.fetch_one("SELECT content FROM memories WHERE id = ?", (replacer_id,))
            rep_snippet = rep_mem["content"][:40] + "..." if rep_mem and len(rep_mem["content"]) > 40 else (rep_mem["content"] if rep_mem else "Ký ức mới")
            
            return {
                "status": "superseded",
                "explanation": f"Ký ức [{memory_id}] ('{content_snippet}') không được recall vì đã bị thay thế hoàn toàn bởi ký ức mới hơn [{replacer_id}] ('{rep_snippet}') thông qua liên kết thay thế (độ mạnh: {replacer['weight']:.2f}).",
                "replacer_id": replacer_id,
            }
        else:
            return {
                "status": "superseded",
                "explanation": f"Ký ức [{memory_id}] ('{content_snippet}') có trạng thái 'superseded' (đã bị thay thế), tuy nhiên liên kết thay thế trực tiếp không được ghi nhận trong đồ thị.",
            }
            
    elif status == "archived":
        return {
            "status": "archived",
            "explanation": f"Ký ức [{memory_id}] ('{content_snippet}') đã bị đưa vào kho lưu trữ (archived) và không còn tham gia vào luồng tri thức hiện thời.",
        }
        
    elif status == "pending_resolve":
        # Tìm xem có mâu thuẫn nào đang mở không
        query = """
            SELECT 
                l.source_id, l.target_id, l.weight,
                s.content AS source_content, t.content AS target_content
            FROM memory_links l
            JOIN memories s ON s.id = l.source_id
            JOIN memories t ON t.id = l.target_id
            WHERE (l.source_id = ? OR l.target_id = ?)
              AND l.link_type = 'contradicts'
            LIMIT 1
        """
        conflict = storage.fetch_one(query, (memory_id, memory_id))
        if conflict:
            other_id = conflict["target_id"] if conflict["source_id"] == memory_id else conflict["source_id"]
            other_content = conflict["target_content"] if conflict["source_id"] == memory_id else conflict["source_content"]
            other_snippet = other_content[:40] + "..." if len(other_content) > 40 else other_content
            
            return {
                "status": "pending_resolve",
                "explanation": f"Ký ức [{memory_id}] ('{content_snippet}') đang ở trạng thái chờ giải quyết xung đột (pending_resolve) do mâu thuẫn trực tiếp với ký ức [{other_id}] ('{other_snippet}') [độ mạnh mâu thuẫn: {conflict['weight']:.2f}].",
                "conflicting_memory_id": other_id,
            }
            
    # Nếu trạng thái là active nhưng điểm quá thấp hoặc bị tranh chấp slot
    if confidence < 0.5:
        return {
            "status": "low_confidence",
            "explanation": f"Ký ức [{memory_id}] ('{content_snippet}') đang hoạt động (active), nhưng có độ tin cậy quá thấp ({confidence:.2f} < 0.50), không vượt qua ngưỡng lọc an toàn.",
        }
        
    return {
        "status": "active",
        "explanation": f"Ký ức [{memory_id}] ('{content_snippet}') hiện đang hoạt động bình thường với độ tin cậy {confidence:.2f}.",
    }
