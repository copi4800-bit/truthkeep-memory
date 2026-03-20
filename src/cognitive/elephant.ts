/**
 * Elephant Layer — Trauma, invariant, anti-regression memory.
 *
 * Như bộ nhớ voi — không bao giờ quên bài học đau thương.
 * Override priority cao nhất, decay gần bằng 0, luôn xuất hiện trong kết quả.
 */

import type Database from "better-sqlite3";
import { newId, nowISO } from "../core/id.js";
import { tokenizeToSet, jaccardSimilarity } from "../core/normalize.js";
import type { MemoryNode, MemoryType } from "../core/models.js";
import { CONSTANTS } from "../core/models.js";

// --- Storage ---

/**
 * Store a trauma or invariant memory.
 * Crystallized immediately with maximum override priority.
 */
export function storeElephantMemory(
  db: Database.Database,
  content: string,
  type: "trauma" | "invariant",
  opts?: {
    subject?: string;
    scope?: string;
    overridePriority?: number;
  },
): string {
  const now = nowISO();
  const id = newId();

  db.prepare(`
    INSERT INTO memory_nodes (
      id, memory_type, content, canonical_subject, scope,
      status, importance, salience, memory_state,
      override_priority, base_decay_rate,
      created_at, updated_at, first_seen_at, crystallized_at
    ) VALUES (
      ?, ?, ?, ?, ?,
      'active', 1.0, 1.0, 'crystallized',
      ?, 0,
      ?, ?, ?, ?
    )
  `).run(
    id, type, content, opts?.subject ?? null, opts?.scope ?? "global",
    opts?.overridePriority ?? 100,
    now, now, now, now,
  );

  // Log elephant event
  db.prepare(`
    INSERT INTO memory_events (id, event_type, node_id, scope, payload_json, created_at)
    VALUES (?, 'elephant_store', ?, ?, ?, ?)
  `).run(newId(), id, opts?.scope ?? "global", JSON.stringify({ type, subject: opts?.subject }), now);

  return id;
}

// --- Multi-Signal Relevance Check ---

interface ElephantRelevanceSignals {
  keywordOverlap: number;
  entityOverlap: number;
  scopeMatch: number;
}

/**
 * Compute multi-signal relevance between a query and an elephant memory.
 * Weights: keyword=0.5, entity=0.3, scope=0.2
 */
export function computeElephantRelevance(
  db: Database.Database,
  queryTokens: Set<string>,
  node: MemoryNode,
  currentScope?: string,
): { score: number; signals: ElephantRelevanceSignals } {
  // 1. Keyword overlap (Jaccard)
  const nodeTokens = tokenizeToSet(node.content);
  const keywordOverlap = jaccardSimilarity(queryTokens, nodeTokens);

  // 2. Entity overlap — check if query mentions entities linked to this node
  let entityOverlap = 0;
  const nodeEntities = db.prepare(`
    SELECT json_extract(extension_json, '$.entity_name') as name
    FROM memory_edges
    WHERE src_node_id = ? AND edge_type = 'mentions_entity' AND status = 'active'
  `).all(node.id) as Array<{ name: string | null }>;

  if (nodeEntities.length > 0) {
    const entityNames = new Set(nodeEntities.map((e) => e.name?.toLowerCase()).filter(Boolean));
    let overlap = 0;
    for (const token of queryTokens) {
      if (entityNames.has(token)) overlap++;
    }
    entityOverlap = entityNames.size > 0 ? overlap / entityNames.size : 0;
  }

  // 3. Scope match
  let scopeMatch = 0.3; // Default: partial match
  if (!node.scope || node.scope === "global") {
    scopeMatch = 1.0; // Global scope always matches
  } else if (currentScope && node.scope === currentScope) {
    scopeMatch = 1.0;
  }

  const score = 0.5 * keywordOverlap + 0.3 * entityOverlap + 0.2 * scopeMatch;
  return { score, signals: { keywordOverlap, entityOverlap, scopeMatch } };
}

/**
 * Find elephant overrides with multi-signal relevance scoring.
 * Returns nodes that exceed ELEPHANT_RELEVANCE_THRESHOLD.
 */
export function findElephantOverrides(
  db: Database.Database,
  query: string,
  currentScope?: string,
): MemoryNode[] {
  const overrides = db.prepare(`
    SELECT * FROM memory_nodes
    WHERE memory_type IN ('trauma', 'invariant')
      AND memory_state != 'archived'
      AND status = 'active'
    ORDER BY override_priority DESC
  `).all() as MemoryNode[];

  if (overrides.length === 0) return [];

  const queryTokens = tokenizeToSet(query);

  return overrides.filter((node) => {
    const { score } = computeElephantRelevance(db, queryTokens, node, currentScope);
    return score > CONSTANTS.ELEPHANT_RELEVANCE_THRESHOLD;
  });
}

// --- Anti-Regression Detection ---

/**
 * Check if new content contradicts any active elephant memories.
 * Returns conflicting elephant nodes if the new content appears to
 * negate or contradict safety/invariant rules.
 */
export function checkAntiRegression(
  db: Database.Database,
  newContent: string,
): Array<{ elephantNode: MemoryNode; conflictScore: number }> {
  const newTokens = tokenizeToSet(newContent);
  const newLower = newContent.toLowerCase();

  // Negation patterns that might indicate contradiction
  const negationPatterns = [
    "don't need to", "no longer", "skip", "ignore", "remove",
    "disable", "turn off", "not necessary", "delete", "drop",
    "never mind", "forget about", "stop",
  ];

  const elephantNodes = db.prepare(`
    SELECT * FROM memory_nodes
    WHERE memory_type IN ('trauma', 'invariant')
      AND status = 'active'
      AND memory_state != 'archived'
  `).all() as MemoryNode[];

  const conflicts: Array<{ elephantNode: MemoryNode; conflictScore: number }> = [];

  for (const node of elephantNodes) {
    const nodeTokens = tokenizeToSet(node.content);
    const overlap = jaccardSimilarity(newTokens, nodeTokens);

    // If there's topic overlap AND negation language, it may be a contradiction
    if (overlap >= 0.1) {
      let negationScore = 0;
      for (const pattern of negationPatterns) {
        if (newLower.includes(pattern)) {
          negationScore += 0.2;
        }
      }
      negationScore = Math.min(negationScore, 1.0);

      const conflictScore = overlap * negationScore;
      if (conflictScore >= 0.03) {
        conflicts.push({ elephantNode: node, conflictScore });
      }
    }
  }

  return conflicts.sort((a, b) => b.conflictScore - a.conflictScore);
}

// --- Elephant Consolidation ---

/**
 * Consolidate elephant memories — merge near-duplicate trauma/invariant
 * memories that cover the same subject.
 */
export function consolidateElephant(
  db: Database.Database,
): { merged: number } {
  const now = nowISO();

  const elephantNodes = db.prepare(`
    SELECT * FROM memory_nodes
    WHERE memory_type IN ('trauma', 'invariant')
      AND status = 'active'
    ORDER BY override_priority DESC, created_at ASC
  `).all() as MemoryNode[];

  let merged = 0;

  const txn = db.transaction(() => {
    const processed = new Set<string>();

    for (let i = 0; i < elephantNodes.length; i++) {
      if (processed.has(elephantNodes[i].id)) continue;

      for (let j = i + 1; j < elephantNodes.length; j++) {
        if (processed.has(elephantNodes[j].id)) continue;

        const a = elephantNodes[i];
        const b = elephantNodes[j];

        // Same type and similar content → merge
        if (a.memory_type !== b.memory_type) continue;

        const sim = jaccardSimilarity(tokenizeToSet(a.content), tokenizeToSet(b.content));
        if (sim < 0.6) continue;

        // Keep the one with higher priority, merge other
        const keep = a.override_priority >= b.override_priority ? a : b;
        const merge = keep === a ? b : a;

        // Mark merged node
        db.prepare(`
          UPDATE memory_nodes SET status = 'merged', updated_at = ? WHERE id = ?
        `).run(now, merge.id);

        // Bump priority of keeper
        db.prepare(`
          UPDATE memory_nodes
          SET override_priority = MAX(override_priority, ?),
              updated_at = ?
          WHERE id = ?
        `).run(merge.override_priority, now, keep.id);

        processed.add(merge.id);
        merged++;
      }
    }
  });

  txn();
  return { merged };
}

/**
 * List all active elephant memories for auditing.
 */
export function listElephantMemories(
  db: Database.Database,
): Array<{ id: string; type: string; content: string; priority: number; subject: string | null }> {
  return db.prepare(`
    SELECT id, memory_type as type, content, override_priority as priority, canonical_subject as subject
    FROM memory_nodes
    WHERE memory_type IN ('trauma', 'invariant')
      AND status = 'active'
    ORDER BY override_priority DESC
  `).all() as Array<{ id: string; type: string; content: string; priority: number; subject: string | null }>;
}
