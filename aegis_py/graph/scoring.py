from __future__ import annotations

import math
from typing import Any
from .relation_types import RelationType


def compute_graph_score(storage: Any, memory_id: str, scope_type: str, scope_id: str) -> float:
    """Tính toán điểm số đồ thị (S_graph) dựa trên cấu trúc các mối quan hệ kề.
    
    Ngăn chặn 100% rò rỉ scope bằng cách lọc chặt chẽ scope_type và scope_id ở cả hai phía của liên kết.
    S_graph = sum(evidence_bonus) + sum(support_bonus) - sum(contradiction_penalty) - sum(superseded_penalty)
    """
    # SQL lọc chặt chẽ 100% ranh giới scope tại tầng DB
    query = """
        SELECT 
            l.link_type,
            l.weight,
            l.source_id,
            l.target_id
        FROM memory_links l
        JOIN memories s ON s.id = l.source_id
        JOIN memories t ON t.id = l.target_id
        WHERE (l.source_id = ? OR l.target_id = ?)
          AND s.scope_type = ? AND s.scope_id = ?
          AND t.scope_type = ? AND t.scope_id = ?
          AND s.status IN ('active', 'pending_resolve')
          AND t.status IN ('active', 'pending_resolve')
    """
    params = (memory_id, memory_id, scope_type, scope_id, scope_type, scope_id)
    rows = storage.fetch_all(query, params)
    
    evidence_bonus = 0.0
    support_bonus = 0.0
    contradiction_penalty = 0.0
    superseded_penalty = 0.0
    
    for row in rows:
        link_type = row["link_type"]
        weight = row["weight"]
        source_id = row["source_id"]
        target_id = row["target_id"]
        
        if link_type == RelationType.EVIDENCE_FOR.value:
            # Nếu node hiện tại là target (được làm bằng chứng bởi source)
            if target_id == memory_id:
                evidence_bonus += weight * 0.25
        elif link_type == RelationType.SUPPORTS.value:
            # Nếu node hiện tại được hỗ trợ bởi node khác
            if target_id == memory_id:
                support_bonus += weight * 0.15
        elif link_type == RelationType.CONTRADICTS.value:
            # Mối quan hệ mâu thuẫn làm giảm độ tin cậy của cả hai phía
            contradiction_penalty += weight * 0.40
        elif link_type == RelationType.SUPERSEDED_BY.value:
            # Bị thay thế bởi node khác
            if source_id == memory_id:
                superseded_penalty += weight * 1.50
        elif link_type == RelationType.SUPERSEDES.value:
            # Node khác bị thay thế bởi node hiện tại
            # (Đối với node hiện tại thì đây là điểm cộng, nhưng đối với node bị thay thế thì đây là điểm phạt. 
            # Tuy nhiên, nếu node hiện tại là target của SUPERSEDES, nghĩa là target bị source thay thế => target bị phạt)
            if target_id == memory_id:
                superseded_penalty += weight * 1.50
                
    s_graph = evidence_bonus + support_bonus - contradiction_penalty - superseded_penalty
    return s_graph
