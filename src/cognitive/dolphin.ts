/**
 * Dolphin Layer — Fast probing, entity resolution, background consolidation.
 *
 * Orca cá voi sát thủ giao tiếp bằng tiếng gọi đặc biệt —
 * Dolphin layer giống như bộ phiên dịch nhanh giữa các entity.
 */

import type Database from "better-sqlite3";
import { newId, nowISO } from "../core/id.js";
import { jaccardSimilarity, tokenizeToSet } from "../core/normalize.js";

// --- Entity Resolution ---

interface MergeCandidate {
  entityId: string;
  targetEntityId: string;
  similarity: number;
}

/**
 * Run entity resolution — find and merge duplicate entities by name similarity.
 * Returns number of entities merged.
 */
export function resolveEntities(db: Database.Database, minSimilarity = 0.7): number {
  const now = nowISO();
  const entities = db.prepare(`
    SELECT id, canonical_name, entity_type, scope
    FROM entities WHERE status = 'active'
    ORDER BY created_at ASC
  `).all() as Array<{ id: string; canonical_name: string; entity_type: string; scope: string | null }>;

  if (entities.length < 2) return 0;

  const merges: MergeCandidate[] = [];

  // Compare all pairs — for small entity sets this is fine
  for (let i = 0; i < entities.length; i++) {
    for (let j = i + 1; j < entities.length; j++) {
      const a = entities[i];
      const b = entities[j];

      // Same type only
      if (a.entity_type !== b.entity_type) continue;

      // Check name similarity
      const sim = jaccardSimilarity(
        tokenizeToSet(a.canonical_name),
        tokenizeToSet(b.canonical_name),
      );

      // Also check if one is a substring of the other
      const aLower = a.canonical_name.toLowerCase();
      const bLower = b.canonical_name.toLowerCase();
      const substringMatch = aLower.includes(bLower) || bLower.includes(aLower);

      if (sim >= minSimilarity || (substringMatch && sim >= 0.3)) {
        merges.push({ entityId: b.id, targetEntityId: a.id, similarity: sim });
      }
    }
  }

  if (merges.length === 0) return 0;

  // Execute merges in a transaction
  const merge = db.transaction(() => {
    let count = 0;
    for (const m of merges) {
      // Move aliases from source to target
      db.prepare(`
        UPDATE OR IGNORE entity_aliases
        SET entity_id = ?, updated_at = ?
        WHERE entity_id = ?
      `).run(m.targetEntityId, now, m.entityId);

      // Add the merged entity's canonical name as an alias of the target
      db.prepare(`
        INSERT OR IGNORE INTO entity_aliases (id, entity_id, alias_text, alias_kind, confidence, created_at, updated_at)
        VALUES (?, ?, (SELECT canonical_name FROM entities WHERE id = ?), 'merged', ?, ?, ?)
      `).run(newId(), m.targetEntityId, m.entityId, m.similarity, now, now);

      // Reroute edges referencing the merged entity
      const affectedEdges = db.prepare(`
        SELECT id, extension_json FROM memory_edges
        WHERE json_extract(extension_json, '$.entity_id') = ?
      `).all(m.entityId) as Array<{ id: string; extension_json: string }>;

      for (const edge of affectedEdges) {
        const ext = JSON.parse(edge.extension_json);
        ext.entity_id = m.targetEntityId;
        ext.merged_from = m.entityId;
        db.prepare(
          "UPDATE memory_edges SET extension_json = ?, updated_at = ? WHERE id = ?",
        ).run(JSON.stringify(ext), now, edge.id);
      }

      // Mark source entity as merged
      db.prepare(
        "UPDATE entities SET status = 'merged', updated_at = ? WHERE id = ?",
      ).run(now, m.entityId);

      count++;
    }
    return count;
  });

  return merge();
}

// --- Co-occurrence Edge Rebuilder ---

/**
 * Rebuild co-occurrence edges between nodes that share entities.
 * Call after entity resolution to fix up edges that may have been fragmented.
 */
export function rebuildCoOccurrenceEdges(db: Database.Database): number {
  const now = nowISO();

  // Find all active entity mentions grouped by entity
  const entityMentions = db.prepare(`
    SELECT
      json_extract(extension_json, '$.entity_id') as entity_id,
      src_node_id as node_id
    FROM memory_edges
    WHERE edge_type = 'mentions_entity'
      AND status = 'active'
    ORDER BY entity_id
  `).all() as Array<{ entity_id: string; node_id: string }>;

  // Group by entity
  const entityToNodes = new Map<string, Set<string>>();
  for (const row of entityMentions) {
    if (!row.entity_id) continue;
    const nodes = entityToNodes.get(row.entity_id) ?? new Set();
    nodes.add(row.node_id);
    entityToNodes.set(row.entity_id, nodes);
  }

  let created = 0;

  const build = db.transaction(() => {
    for (const [entityId, nodes] of entityToNodes) {
      const nodeArr = [...nodes];
      for (let i = 0; i < nodeArr.length; i++) {
        for (let j = i + 1; j < nodeArr.length; j++) {
          // Check if edge already exists
          const existing = db.prepare(`
            SELECT id FROM memory_edges
            WHERE ((src_node_id = ? AND dst_node_id = ?) OR (src_node_id = ? AND dst_node_id = ?))
              AND edge_type = 'co_entity'
              AND json_extract(extension_json, '$.entity_id') = ?
          `).get(nodeArr[i], nodeArr[j], nodeArr[j], nodeArr[i], entityId) as { id: string } | undefined;

          if (!existing) {
            // Get entity name for the edge metadata
            const entity = db.prepare(
              "SELECT canonical_name FROM entities WHERE id = ?",
            ).get(entityId) as { canonical_name: string } | undefined;

            db.prepare(`
              INSERT INTO memory_edges (
                id, src_node_id, dst_node_id, edge_type, weight, confidence,
                scope, status, coactivation_count, created_at, updated_at, extension_json
              ) VALUES (?, ?, ?, 'co_entity', 0.4, 0.7, NULL, 'active', 1, ?, ?, ?)
            `).run(
              newId(), nodeArr[i], nodeArr[j],
              now, now,
              JSON.stringify({ entity_id: entityId, entity_name: entity?.canonical_name ?? "" }),
            );
            created++;
          }
        }
      }
    }
  });

  build();
  return created;
}

// --- Session Prewarm ---

/**
 * Prewarm cache for a session — identify likely-relevant entities and nodes.
 * Returns entity IDs that were prewarmed.
 */
export function prewarm(
  db: Database.Database,
  sessionKey: string,
): string[] {
  // Find entities from recent session interactions
  const recentEntities = db.prepare(`
    SELECT DISTINCT json_extract(me.extension_json, '$.entity_id') as entity_id
    FROM memory_edges me
    JOIN memory_nodes mn ON mn.id = me.src_node_id
    WHERE me.edge_type = 'mentions_entity'
      AND me.status = 'active'
      AND mn.scope = 'session'
      AND mn.status = 'active'
    ORDER BY mn.updated_at DESC
    LIMIT 20
  `).all() as Array<{ entity_id: string | null }>;

  const entityIds = recentEntities
    .map((r) => r.entity_id)
    .filter((id): id is string => id != null);

  if (entityIds.length === 0) return [];

  // Boost salience for nodes connected to these entities
  const now = nowISO();
  const boostNode = db.prepare(`
    UPDATE memory_nodes
    SET salience = MIN(1.0, salience + 0.1),
        updated_at = ?
    WHERE id IN (
      SELECT DISTINCT src_node_id FROM memory_edges
      WHERE edge_type IN ('mentions_entity', 'co_entity')
        AND status = 'active'
        AND json_extract(extension_json, '$.entity_id') IN (${entityIds.map(() => "?").join(",")})
    ) AND status = 'active'
  `);

  boostNode.run(now, ...entityIds);

  // Log prewarm event
  db.prepare(`
    INSERT INTO memory_events (id, event_type, scope, session_id, payload_json, created_at)
    VALUES (?, 'prewarm', 'session', ?, ?, ?)
  `).run(newId(), sessionKey, JSON.stringify({ entity_count: entityIds.length }), now);

  return entityIds;
}

// --- Session Consolidation ---

/**
 * Consolidate session — merge near-duplicate working_scratch nodes,
 * promote frequently-accessed nodes to stable, and clean up ephemeral data.
 */
export function consolidateSession(
  db: Database.Database,
  sessionKey: string,
): { promoted: number; merged: number; expired: number } {
  const now = nowISO();
  let promoted = 0;
  let merged = 0;
  let expired = 0;

  const consolidate = db.transaction(() => {
    // 1. Promote frequently-recalled session nodes to stable
    const hotNodes = db.prepare(`
      SELECT id FROM memory_nodes
      WHERE scope = 'session'
        AND status = 'active'
        AND memory_state = 'volatile'
        AND recall_count >= 2
    `).all() as Array<{ id: string }>;

    for (const node of hotNodes) {
      db.prepare(`
        UPDATE memory_nodes
        SET memory_state = 'stable', scope = 'user', updated_at = ?
        WHERE id = ?
      `).run(now, node.id);
      promoted++;
    }

    // 2. Expire old working_scratch nodes from this session
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    const staleNodes = db.prepare(`
      SELECT id FROM memory_nodes
      WHERE memory_type = 'working_scratch'
        AND status = 'active'
        AND scope = 'session'
        AND recall_count = 0
        AND updated_at < ?
    `).all(oneHourAgo) as Array<{ id: string }>;

    for (const node of staleNodes) {
      db.prepare(`
        UPDATE memory_nodes
        SET status = 'expired', updated_at = ?
        WHERE id = ?
      `).run(now, node.id);
      expired++;
    }

    // 3. Log consolidation event
    db.prepare(`
      INSERT INTO memory_events (id, event_type, scope, session_id, payload_json, created_at)
      VALUES (?, 'consolidate', 'session', ?, ?, ?)
    `).run(
      newId(), sessionKey,
      JSON.stringify({ promoted, merged, expired }),
      now,
    );
  });

  consolidate();
  return { promoted, merged, expired };
}

/**
 * Flush any pending consolidation work.
 */
export function flushPending(db: Database.Database): void {
  // Run entity resolution as background maintenance
  resolveEntities(db);
  // Rebuild co-occurrence edges
  rebuildCoOccurrenceEdges(db);
}
