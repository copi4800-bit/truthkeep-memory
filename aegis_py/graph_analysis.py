from __future__ import annotations

from collections import deque
from typing import Any

from .storage.modern_math import EulerCayleyGraphEngine


def summarize_local_graph(*, nodes: list[dict[str, Any]], links: list[dict[str, Any]]) -> dict[str, Any]:
    """Return bounded local-only graph diagnostics over SQLite-backed snapshots.
    
    Enhanced with Euler/Cayley centrality analysis (Leonhard Euler & Arthur Cayley).
    """
    adjacency: dict[str, set[str]] = {}
    for node in nodes:
        adjacency.setdefault(node["id"], set())
    for link in links:
        source = link.get("source")
        target = link.get("target")
        if source not in adjacency or target not in adjacency:
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)

    visited: set[str] = set()
    component_sizes: list[int] = []
    for node_id in adjacency:
        if node_id in visited:
            continue
        queue = deque([node_id])
        visited.add(node_id)
        size = 0
        while queue:
            current = queue.popleft()
            size += 1
            for neighbor in adjacency[current]:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)
        component_sizes.append(size)

    degrees = sorted(
        (
            {"id": node_id, "degree": len(neighbors)}
            for node_id, neighbors in adjacency.items()
        ),
        key=lambda item: (-item["degree"], item["id"]),
    )

    # --- Euler/Cayley Centrality Analysis ---
    adjacency_lists = {node_id: list(neighbors) for node_id, neighbors in adjacency.items()}
    degree_centrality = EulerCayleyGraphEngine.compute_degree_centrality(adjacency_lists)
    hub_nodes = EulerCayleyGraphEngine.find_hub_nodes(adjacency_lists, top_k=5)
    has_euler_path = EulerCayleyGraphEngine.has_euler_path(adjacency_lists)

    return {
        "backend": "python",
        "analysis_mode": "local_only",
        "authoritative": False,
        "component_count": len(component_sizes),
        "largest_component": max(component_sizes, default=0),
        "top_degrees": degrees[:5],
        # Euler/Cayley enhancements
        "euler_cayley": {
            "hub_nodes": [{"id": node_id, "centrality": score} for node_id, score in hub_nodes],
            "has_euler_path": has_euler_path,
            "max_degree_centrality": max(degree_centrality.values(), default=0.0),
        },
    }
