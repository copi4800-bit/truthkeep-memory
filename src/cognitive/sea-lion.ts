/**
 * Sea Lion Layer — Bounded transitive inference, concept inheritance.
 *
 * Như sư tử biển biểu diễn xiếc — suy luận chuỗi từ A→B→C
 * qua concept hierarchy với confidence decay tại mỗi bước.
 */

import type Database from "better-sqlite3";
import { newId, nowISO } from "../core/id.js";
import { CONSTANTS } from "../core/models.js";

// --- Concept Management ---

/**
 * Create or update a concept node (rule, policy, category).
 */
export function upsertConcept(
  db: Database.Database,
  name: string,
  conceptType: string,
  opts?: {
    priority?: number;
    overridePolicy?: string;
    confidence?: number;
    rulePayload?: Record<string, unknown>;
    validFrom?: string;
    validTo?: string;
  },
): string {
  const now = nowISO();

  // Check if concept exists
  const existing = db.prepare(
    "SELECT id FROM concept_nodes WHERE canonical_name = ? COLLATE NOCASE AND concept_type = ?",
  ).get(name, conceptType) as { id: string } | undefined;

  if (existing) {
    db.prepare(`
      UPDATE concept_nodes SET
        priority = COALESCE(?, priority),
        override_policy = COALESCE(?, override_policy),
        confidence = COALESCE(?, confidence),
        rule_payload_json = COALESCE(?, rule_payload_json),
        valid_from = COALESCE(?, valid_from),
        valid_to = COALESCE(?, valid_to),
        updated_at = ?
      WHERE id = ?
    `).run(
      opts?.priority ?? null, opts?.overridePolicy ?? null,
      opts?.confidence ?? null,
      opts?.rulePayload ? JSON.stringify(opts.rulePayload) : null,
      opts?.validFrom ?? null, opts?.validTo ?? null,
      now, existing.id,
    );
    return existing.id;
  }

  const id = newId();
  db.prepare(`
    INSERT INTO concept_nodes (
      id, concept_type, canonical_name, priority, override_policy,
      valid_from, valid_to, confidence, rule_payload_json,
      created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    id, conceptType, name,
    opts?.priority ?? 0,
    opts?.overridePolicy ?? null,
    opts?.validFrom ?? null,
    opts?.validTo ?? null,
    opts?.confidence ?? 0.5,
    opts?.rulePayload ? JSON.stringify(opts.rulePayload) : null,
    now, now,
  );

  return id;
}

/**
 * Create an inheritance link between concepts or between a concept and a memory node.
 */
export function addInheritance(
  db: Database.Database,
  src: { kind: string; id: string },
  dst: { kind: string; id: string },
  inheritanceType: string,
  priority = 0,
): string {
  const id = newId();
  const now = nowISO();

  db.prepare(`
    INSERT INTO concept_inheritance (
      id, src_kind, src_id, dst_kind, dst_id,
      inheritance_type, priority, active, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
  `).run(id, src.kind, src.id, dst.kind, dst.id, inheritanceType, priority, now);

  return id;
}

// --- Transitive Inference ---

interface InferenceResult {
  dstNodeId: string;
  confidence: number;
  depth: number;
  via: string[];
}

/**
 * Resolve inherited rules for a memory node via concept hierarchy.
 *
 * Walks the concept_inheritance graph upward from the node,
 * collecting applicable rules/policies with decaying confidence.
 */
export function resolveInheritedRules(
  db: Database.Database,
  nodeId: string,
): InferenceResult[] {
  const maxDepth = CONSTANTS.MAX_INHERITANCE_DEPTH;
  const minConfidence = CONSTANTS.INFERENCE_CONFIDENCE_THRESHOLD;
  const decay = CONSTANTS.INFERENCE_CONFIDENCE_DECAY;

  const results: InferenceResult[] = [];
  const visited = new Set<string>();

  // BFS through inheritance graph
  interface QueueItem {
    kind: string;
    id: string;
    confidence: number;
    depth: number;
    path: string[];
  }

  const queue: QueueItem[] = [{ kind: "node", id: nodeId, confidence: 1.0, depth: 0, path: [] }];

  while (queue.length > 0) {
    const current = queue.shift()!;
    const key = `${current.kind}:${current.id}`;

    if (visited.has(key)) continue;
    if (current.depth > maxDepth) continue;
    if (current.confidence < minConfidence) continue;

    visited.add(key);

    // Find parent concepts this item inherits from
    const parents = db.prepare(`
      SELECT dst_kind, dst_id, inheritance_type, priority
      FROM concept_inheritance
      WHERE src_kind = ? AND src_id = ? AND active = 1
      ORDER BY priority DESC
    `).all(current.kind, current.id) as Array<{
      dst_kind: string; dst_id: string; inheritance_type: string; priority: number;
    }>;

    for (const parent of parents) {
      const parentKey = `${parent.dst_kind}:${parent.dst_id}`;
      if (visited.has(parentKey)) continue;

      const newConfidence = current.confidence * decay;
      if (newConfidence < minConfidence) continue;

      const newPath = [...current.path, `${parent.inheritance_type}→${parent.dst_id}`];

      // If parent is a concept with a rule, collect it
      if (parent.dst_kind === "concept") {
        const concept = db.prepare(
          "SELECT * FROM concept_nodes WHERE id = ?",
        ).get(parent.dst_id) as {
          id: string; rule_payload_json: string | null; confidence: number;
        } | undefined;

        if (concept?.rule_payload_json) {
          results.push({
            dstNodeId: parent.dst_id,
            confidence: newConfidence * concept.confidence,
            depth: current.depth + 1,
            via: newPath,
          });
        }
      }

      // If parent is a node, add as reachable
      if (parent.dst_kind === "node") {
        results.push({
          dstNodeId: parent.dst_id,
          confidence: newConfidence,
          depth: current.depth + 1,
          via: newPath,
        });
      }

      queue.push({
        kind: parent.dst_kind,
        id: parent.dst_id,
        confidence: newConfidence,
        depth: current.depth + 1,
        path: newPath,
      });
    }
  }

  return results.sort((a, b) => b.confidence - a.confidence);
}

/**
 * Run bounded transitive inference from a start node through typed edge chains.
 *
 * Example: If A --[related_to]--> B --[implies]--> C,
 * then transitiveInference(db, A, ["related_to", "implies"]) discovers C.
 */
export function transitiveInference(
  db: Database.Database,
  startNodeId: string,
  edgeChain: string[],
): InferenceResult[] {
  const decay = CONSTANTS.INFERENCE_CONFIDENCE_DECAY;
  const minConfidence = CONSTANTS.INFERENCE_CONFIDENCE_THRESHOLD;

  if (edgeChain.length === 0) return [];

  let currentNodes = new Map<string, { confidence: number; path: string[] }>();
  currentNodes.set(startNodeId, { confidence: 1.0, path: [] });

  for (let step = 0; step < edgeChain.length; step++) {
    const edgeType = edgeChain[step];
    const nextNodes = new Map<string, { confidence: number; path: string[] }>();

    for (const [nodeId, state] of currentNodes) {
      const neighbors = db.prepare(`
        SELECT dst_node_id, weight, confidence
        FROM memory_edges
        WHERE src_node_id = ? AND edge_type = ? AND status = 'active'
      `).all(nodeId, edgeType) as Array<{
        dst_node_id: string; weight: number; confidence: number;
      }>;

      for (const n of neighbors) {
        const newConfidence = state.confidence * decay * n.confidence;
        if (newConfidence < minConfidence) continue;

        const newPath = [...state.path, `${edgeType}→${n.dst_node_id}`];
        const existing = nextNodes.get(n.dst_node_id);

        if (!existing || existing.confidence < newConfidence) {
          nextNodes.set(n.dst_node_id, { confidence: newConfidence, path: newPath });
        }
      }
    }

    currentNodes = nextNodes;
    if (currentNodes.size === 0) break;
  }

  return [...currentNodes.entries()].map(([nodeId, state]) => ({
    dstNodeId: nodeId,
    confidence: state.confidence,
    depth: edgeChain.length,
    via: state.path,
  })).sort((a, b) => b.confidence - a.confidence);
}

// --- Derived Relations Cache ---

/**
 * Cache a derived relation for fast lookups.
 * Expired after a configurable period to force re-inference.
 */
export function cacheDerivedRelation(
  db: Database.Database,
  srcNodeId: string,
  dstNodeId: string,
  derivationType: string,
  path: string[],
  confidence: number,
  ttlDays = 7,
): string {
  const now = nowISO();
  const id = newId();
  const expiresAt = new Date(Date.now() + ttlDays * 24 * 60 * 60 * 1000).toISOString();

  db.prepare(`
    INSERT INTO derived_relations (
      id, src_node_id, dst_node_id, derivation_type,
      derivation_path_json, derivation_depth, confidence,
      expires_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    id, srcNodeId, dstNodeId, derivationType,
    JSON.stringify(path), path.length, confidence,
    expiresAt, now,
  );

  return id;
}

/**
 * Look up cached derived relations from a source node.
 */
export function getCachedDerivedRelations(
  db: Database.Database,
  srcNodeId: string,
  derivationType?: string,
): Array<{ dstNodeId: string; confidence: number; depth: number; path: string[] }> {
  const now = nowISO();
  let query = `
    SELECT dst_node_id, confidence, derivation_depth, derivation_path_json
    FROM derived_relations
    WHERE src_node_id = ?
      AND (expires_at IS NULL OR expires_at > ?)
  `;
  const params: unknown[] = [srcNodeId, now];

  if (derivationType) {
    query += " AND derivation_type = ?";
    params.push(derivationType);
  }

  query += " ORDER BY confidence DESC";

  const rows = db.prepare(query).all(...params) as Array<{
    dst_node_id: string; confidence: number;
    derivation_depth: number; derivation_path_json: string;
  }>;

  return rows.map((r) => ({
    dstNodeId: r.dst_node_id,
    confidence: r.confidence,
    depth: r.derivation_depth,
    path: JSON.parse(r.derivation_path_json),
  }));
}

/**
 * Purge expired derived relations.
 */
export function purgeExpiredDerivedRelations(db: Database.Database): number {
  const now = nowISO();
  const result = db.prepare(
    "DELETE FROM derived_relations WHERE expires_at IS NOT NULL AND expires_at < ?",
  ).run(now);
  return result.changes;
}
