/**
 * Salmon Layer — Identity dedup at retrieval time.
 *
 * Như cá hồi nhớ đường về — nhận diện nội dung trùng lặp
 * trong kết quả tìm kiếm bằng fingerprint (normalized_hash).
 *
 * Khác với ingest-time dedup (ingest.ts:checkDedup):
 * - Ingest dedup ngăn tạo duplicate nodes
 * - Salmon dedup loại nodes tương tự khỏi **kết quả retrieval**
 */

import type Database from "better-sqlite3";

/**
 * Deduplicate activated nodes by normalized fingerprint hash.
 *
 * Groups nodes that share the same normalized_hash and keeps only
 * the one with the highest activation score per group.
 */
export function dedupByFingerprint(
  db: Database.Database,
  activated: Map<string, number>,
): Map<string, number> {
  if (activated.size === 0) return activated;

  const nodeIds = [...activated.keys()];

  // Fetch fingerprint hashes for all activated nodes
  const placeholders = nodeIds.map(() => "?").join(",");
  const rows = db.prepare(`
    SELECT id, normalized_hash FROM memory_nodes
    WHERE id IN (${placeholders}) AND normalized_hash IS NOT NULL
  `).all(...nodeIds) as Array<{ id: string; normalized_hash: string }>;

  // Group by normalized_hash
  const groups = new Map<string, Array<{ id: string; score: number }>>();

  for (const row of rows) {
    const score = activated.get(row.id) ?? 0;
    const group = groups.get(row.normalized_hash);
    if (group) {
      group.push({ id: row.id, score });
    } else {
      groups.set(row.normalized_hash, [{ id: row.id, score }]);
    }
  }

  // Collect IDs to remove (keep highest score per group)
  const toRemove = new Set<string>();

  for (const members of groups.values()) {
    if (members.length <= 1) continue;

    // Sort descending by score, keep first
    members.sort((a, b) => b.score - a.score);
    for (let i = 1; i < members.length; i++) {
      toRemove.add(members[i].id);
    }
  }

  if (toRemove.size === 0) return activated;

  // Build deduplicated map
  const deduped = new Map<string, number>();
  for (const [nodeId, score] of activated) {
    if (!toRemove.has(nodeId)) {
      deduped.set(nodeId, score);
    }
  }

  return deduped;
}

/**
 * Find all nodes that share the same normalized_hash as the given node.
 * Useful for diagnostics and manual dedup review.
 */
export function findDuplicateCluster(
  db: Database.Database,
  nodeId: string,
): string[] {
  const node = db.prepare(
    "SELECT normalized_hash FROM memory_nodes WHERE id = ?",
  ).get(nodeId) as { normalized_hash: string | null } | undefined;

  if (!node?.normalized_hash) return [];

  const rows = db.prepare(
    "SELECT id FROM memory_nodes WHERE normalized_hash = ? AND id != ? AND status = 'active'",
  ).all(node.normalized_hash, nodeId) as Array<{ id: string }>;

  return rows.map((r) => r.id);
}
