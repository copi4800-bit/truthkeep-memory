from __future__ import annotations

import json
from enum import Enum
from typing import Any

from .relation_types import RelationType, RELATION_RULES


class TraversalMode(str, Enum):
    CURRENT_TRUTH = "current_truth"
    WHY_NOT = "why_not"
    AUDIT = "audit"
    IMPACT_ANALYSIS = "impact_analysis"
    EVIDENCE_SEARCH = "evidence_search"
    DEPENDENCY_TRACE = "dependency_trace"


def expand_graph(
    storage: Any,
    *,
    seed_ids: list[str],
    mode: TraversalMode | str,
    max_hops: int = 2,
    scope_type: str,
    scope_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Duyệt đồ thị có hướng và bảo vệ scope nghiêm ngặt từ tầng DB.
    
    Ngăn chặn 100% Cross-Scope Leak bằng Edge Filtering trực tiếp trong câu lệnh SQL.
    Đảm bảo traversal định hướng theo từng chế độ nghiệp vụ.
    """
    if not seed_ids:
        return []

    mode_str = mode.value if isinstance(mode, TraversalMode) else str(mode)
    visited = set(seed_ids)
    queue = list(seed_ids)
    expanded_links: list[dict[str, Any]] = []

    # Định nghĩa các mối quan hệ được phép đi qua cho từng mode và hướng đi của chúng
    # Hướng: "forward" (từ source sang target), "backward" (từ target sang source), hoặc "both"
    ALLOWED_RELATIONS: dict[str, dict[str, str]] = {}
    
    if mode_str == TraversalMode.CURRENT_TRUTH.value:
        ALLOWED_RELATIONS = {
            RelationType.EVIDENCE_FOR.value: "forward",
            RelationType.SUPPORTS.value: "forward",
            RelationType.RESOLVES.value: "forward",
            RelationType.DERIVED_FROM.value: "forward",
            RelationType.PART_OF.value: "forward",
            RelationType.RELATED_TO.value: "both",
        }
    elif mode_str == TraversalMode.WHY_NOT.value:
        ALLOWED_RELATIONS = {
            RelationType.SUPERSEDES.value: "forward",     # Đi từ winner sang node bị thay thế (source -> target)
            RelationType.SUPERSEDED_BY.value: "backward", # Đi từ winner sang node bị thay thế (target -> source)
            RelationType.CONTRADICTS.value: "both",
            RelationType.FALSIFIES.value: "forward",      # Đi từ falsifier sang falsified node
        }
    elif mode_str == TraversalMode.IMPACT_ANALYSIS.value:
        ALLOWED_RELATIONS = {
            RelationType.DEPENDS_ON.value: "backward",    # Đi ngược từ node bị đổi sang node phụ thuộc nó (target -> source)
            RelationType.DERIVED_FROM.value: "backward",
            RelationType.PART_OF.value: "backward",
        }
    elif mode_str == TraversalMode.EVIDENCE_SEARCH.value:
        ALLOWED_RELATIONS = {
            RelationType.EVIDENCE_FOR.value: "forward",
            RelationType.SUPPORTS.value: "forward",
        }
    elif mode_str == TraversalMode.DEPENDENCY_TRACE.value:
        ALLOWED_RELATIONS = {
            RelationType.DEPENDS_ON.value: "forward",     # Đi xuôi cây phụ thuộc (source -> target)
        }
    else:  # AUDIT mode đi tất cả các chiều
        ALLOWED_RELATIONS = {r.value: "both" for r in RelationType}

    # BFS duyệt đồ thị theo từng hop
    for hop in range(max_hops):
        if not queue or len(expanded_links) >= limit:
            break
            
        current_seeds = list(queue)
        queue = []
        
        placeholders = ",".join("?" for _ in current_seeds)
        
        # SQL lọc chặt chẽ 100% ranh giới scope tại tầng DB (Edge Filtering)
        # s là source node, t là target node. Cả hai bắt buộc phải thuộc cùng scope_type và scope_id được truyền vào.
        query = f"""
            SELECT 
                l.id AS link_id,
                l.link_type,
                l.weight,
                l.source_id,
                l.target_id,
                l.metadata_json,
                s.status AS source_status,
                t.status AS target_status
            FROM memory_links l
            JOIN memories s ON s.id = l.source_id
            JOIN memories t ON t.id = l.target_id
            WHERE (l.source_id IN ({placeholders}) OR l.target_id IN ({placeholders}))
              AND s.scope_type = ? AND s.scope_id = ?
              AND t.scope_type = ? AND t.scope_id = ?
              AND s.status IN ('active', 'reconcile_required', 'conflict_candidate', 'superseded', 'archived')
              AND t.status IN ('active', 'reconcile_required', 'conflict_candidate', 'superseded', 'archived')
        """
        
        params = (*current_seeds, *current_seeds, scope_type, scope_id, scope_type, scope_id)
        rows = storage.fetch_all(query, params)
        
        for row in rows:
            link_type = row["link_type"]
            source_id = row["source_id"]
            target_id = row["target_id"]
            
            if link_type not in ALLOWED_RELATIONS:
                continue
                
            direction = ALLOWED_RELATIONS[link_type]
            
            # Xác định node tiếp theo có thể duyệt qua dựa trên hướng của mối quan hệ
            next_node = None
            if direction == "both":
                if source_id in current_seeds:
                    next_node = target_id
                elif target_id in current_seeds:
                    next_node = source_id
            elif direction == "forward" and source_id in current_seeds:
                next_node = target_id
            elif direction == "backward" and target_id in current_seeds:
                next_node = source_id
                
            if next_node and next_node not in visited:
                visited.add(next_node)
                queue.append(next_node)
                
                metadata = row["metadata_json"]
                expanded_links.append({
                    "link_id": row["link_id"],
                    "link_type": link_type,
                    "weight": row["weight"],
                    "source_id": source_id,
                    "target_id": target_id,
                    "neighbor_id": next_node,
                    "metadata": json.loads(metadata) if isinstance(metadata, str) else metadata or {},
                })
                
                if len(expanded_links) >= limit:
                    break
                    
    return expanded_links
