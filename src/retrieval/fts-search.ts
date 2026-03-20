import type Database from "better-sqlite3";
import { buildFtsQuery, bm25RankToScore } from "../core/normalize.js";
import { CONSTANTS } from "../core/models.js";

export interface FtsResult {
  nodeId: string;
  score: number;
  content: string;
  memoryType: string;
  scope: string | null;
}

/**
 * Stage 1: FTS5 seed generation.
 * Queries the memory_nodes_fts virtual table and returns scored results.
 */
export function fts5Search(
  db: Database.Database,
  query: string,
  limit: number = CONSTANTS.FTS_CANDIDATE_LIMIT,
): FtsResult[] {
  const ftsQuery = buildFtsQuery(query);
  if (!ftsQuery) return [];

  try {
    const rows = db.prepare(`
      SELECT
        mn.id as nodeId,
        rank as bm25_rank,
        mn.content,
        mn.memory_type as memoryType,
        mn.scope
      FROM memory_nodes_fts fts
      JOIN memory_nodes mn ON mn.rowid = fts.rowid
      WHERE memory_nodes_fts MATCH ?
        AND mn.status = 'active'
        AND mn.memory_state != 'archived'
      ORDER BY rank
      LIMIT ?
    `).all(ftsQuery, limit) as Array<{
      nodeId: string;
      bm25_rank: number;
      content: string;
      memoryType: string;
      scope: string | null;
    }>;

    return rows.map((row) => ({
      nodeId: row.nodeId,
      score: bm25RankToScore(row.bm25_rank),
      content: row.content,
      memoryType: row.memoryType,
      scope: row.scope,
    }));
  } catch {
    // FTS query syntax error — fall back to simple LIKE search
    return fallbackSearch(db, query, limit);
  }
}

/**
 * Fallback search using LIKE when FTS5 query fails.
 */
function fallbackSearch(
  db: Database.Database,
  query: string,
  limit: number,
): FtsResult[] {
  const pattern = `%${query}%`;
  const rows = db.prepare(`
    SELECT id as nodeId, content, memory_type as memoryType, scope
    FROM memory_nodes
    WHERE status = 'active'
      AND memory_state != 'archived'
      AND (content LIKE ? OR canonical_subject LIKE ?)
    ORDER BY importance DESC, updated_at DESC
    LIMIT ?
  `).all(pattern, pattern, limit) as Array<{
    nodeId: string;
    content: string;
    memoryType: string;
    scope: string | null;
  }>;

  return rows.map((row, i) => ({
    ...row,
    score: 0.5 * (1 - i / Math.max(rows.length, 1)), // Simple rank-based score
  }));
}

/**
 * Find entity matches from the query against known entities/aliases.
 * Returns node IDs linked to matching entities.
 */
export function findEntityMatches(
  db: Database.Database,
  query: string,
): Array<{ nodeId: string; confidence: number }> {
  const tokens = query.match(/[\p{L}\p{N}_]+/gu) ?? [];
  if (tokens.length === 0) return [];

  const results: Array<{ nodeId: string; confidence: number }> = [];

  for (const token of tokens) {
    // Check entity aliases
    const matches = db.prepare(`
      SELECT DISTINCT me.src_node_id as nodeId, a.confidence
      FROM entity_aliases a
      JOIN entities e ON a.entity_id = e.id
      JOIN memory_edges me ON json_extract(me.extension_json, '$.entity_id') = e.id
      WHERE a.alias_text = ? COLLATE NOCASE
        AND e.status = 'active'
        AND me.status = 'active'
    `).all(token) as Array<{ nodeId: string; confidence: number }>;

    results.push(...matches);
  }

  return results;
}
