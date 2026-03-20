import type Database from "better-sqlite3";
import { CONSTANTS } from "../core/models.js";

/**
 * Stage 3: Orca Spreading Activation.
 *
 * Bounded BFS through the entity graph with exponential damping.
 * Bidirectional propagation — follows edges in both directions.
 */
export function spreadingActivation(
  seeds: Map<string, number>,
  db: Database.Database,
  config: {
    maxHops: number;
    dampingFactor: number;
    activationThreshold: number;
    maxNodes: number;
    scopeFilter?: string | null;
  },
): Map<string, number> {
  const activated = new Map(seeds);
  let frontier = new Map(seeds);
  const visited = new Set(seeds.keys());

  const getOutEdges = db.prepare(`
    SELECT dst_node_id as neighborId, edge_type, weight, confidence, scope
    FROM memory_edges
    WHERE src_node_id = ? AND status = 'active'
  `);

  const getInEdges = db.prepare(`
    SELECT src_node_id as neighborId, edge_type, weight, confidence, scope
    FROM memory_edges
    WHERE dst_node_id = ? AND status = 'active'
  `);

  for (let hop = 0; hop < config.maxHops; hop++) {
    if (activated.size >= config.maxNodes) break;

    const nextFrontier = new Map<string, number>();

    for (const [nodeId, activation] of frontier) {
      if (activated.size >= config.maxNodes) break;

      // Get neighbors in both directions
      const outEdges = getOutEdges.all(nodeId) as EdgeRow[];
      const inEdges = getInEdges.all(nodeId) as EdgeRow[];
      const allEdges = [...outEdges, ...inEdges];

      for (const edge of allEdges) {
        // Scope filter
        if (config.scopeFilter && edge.scope && edge.scope !== config.scopeFilter) {
          continue;
        }

        if (visited.has(edge.neighborId)) continue;

        // Propagated activation with damping
        const propagated =
          activation * config.dampingFactor * edge.weight * edge.confidence;

        if (propagated < config.activationThreshold) continue;

        // Accumulate from multiple paths
        const current = nextFrontier.get(edge.neighborId) ?? 0;
        nextFrontier.set(edge.neighborId, current + propagated);
      }
    }

    // Merge into activated set, respecting maxNodes
    // Sort by activation descending to keep best candidates
    const sorted = [...nextFrontier.entries()].sort((a, b) => b[1] - a[1]);
    for (const [nodeId, activation] of sorted) {
      if (activated.size >= config.maxNodes) break;
      const existing = activated.get(nodeId) ?? 0;
      activated.set(nodeId, existing + activation);
      visited.add(nodeId);
    }

    frontier = nextFrontier;
    if (frontier.size === 0) break;
  }

  return activated;
}

/**
 * Assign initial activation scores to seed nodes.
 */
export function assignInitialActivation(
  ftsResults: Array<{ nodeId: string; score: number }>,
  entityHits: Array<{ nodeId: string; confidence: number }>,
): Map<string, number> {
  const seeds = new Map<string, number>();

  for (const r of ftsResults) {
    seeds.set(r.nodeId, r.score);
  }

  for (const hit of entityHits) {
    const current = seeds.get(hit.nodeId) ?? 0;
    seeds.set(hit.nodeId, Math.max(current, hit.confidence));
  }

  return seeds;
}

/**
 * Reinforce edges between co-activated nodes (Hebbian learning).
 * Called after search results are successfully used.
 */
export function reinforceCoactivation(
  usedNodeIds: string[],
  db: Database.Database,
): void {
  const findEdge = db.prepare(`
    SELECT id, weight, coactivation_count FROM memory_edges
    WHERE ((src_node_id = ? AND dst_node_id = ?) OR (src_node_id = ? AND dst_node_id = ?))
      AND status = 'active'
    LIMIT 1
  `);

  const updateEdge = db.prepare(`
    UPDATE memory_edges
    SET weight = MIN(1.0, weight + ?),
        coactivation_count = coactivation_count + 1,
        last_activated_at = datetime('now'),
        updated_at = datetime('now')
    WHERE id = ?
  `);

  const txn = db.transaction(() => {
    for (let i = 0; i < usedNodeIds.length; i++) {
      for (let j = i + 1; j < usedNodeIds.length; j++) {
        const edge = findEdge.get(
          usedNodeIds[i], usedNodeIds[j],
          usedNodeIds[j], usedNodeIds[i],
        ) as { id: string; weight: number; coactivation_count: number } | undefined;

        if (edge) {
          updateEdge.run(CONSTANTS.HEBBIAN_INCREMENT, edge.id);
        }
      }
    }
  });

  txn();
}

// --- Internal Types ---

interface EdgeRow {
  neighborId: string;
  edge_type: string;
  weight: number;
  confidence: number;
  scope: string | null;
}
