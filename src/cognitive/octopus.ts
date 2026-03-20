/**
 * Octopus Layer — Subgraph partitions, context textures, specialist payloads.
 *
 * Như bạch tuộc có 8 cánh tay độc lập — mỗi subgraph là một
 * "chuyên gia" riêng biệt cho domain cụ thể.
 */

import type Database from "better-sqlite3";
import { newId, nowISO } from "../core/id.js";

// ============================================================
// A. Subgraph Partitions
// ============================================================

/**
 * Create a logical subgraph partition (e.g., "backend", "devops", "personal").
 */
export function createPartition(
  db: Database.Database,
  name: string,
  partitionType: string,
  opts?: {
    scope?: string;
    activationPolicy?: string;
  },
): string {
  const now = nowISO();

  // Check existing
  const existing = db.prepare(
    "SELECT id FROM subgraph_partitions WHERE name = ? COLLATE NOCASE",
  ).get(name) as { id: string } | undefined;

  if (existing) return existing.id;

  const id = newId();
  db.prepare(`
    INSERT INTO subgraph_partitions (
      id, name, scope, partition_type, activation_policy, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(
    id, name, opts?.scope ?? null, partitionType,
    opts?.activationPolicy ?? null, now, now,
  );

  return id;
}

/**
 * Add a member (node, entity, concept) to a subgraph partition.
 */
export function addToPartition(
  db: Database.Database,
  partitionId: string,
  memberKind: string,
  memberId: string,
  weight = 1.0,
): string {
  const now = nowISO();

  // Check duplicate
  const existing = db.prepare(`
    SELECT id FROM subgraph_memberships
    WHERE partition_id = ? AND member_kind = ? AND member_id = ?
  `).get(partitionId, memberKind, memberId) as { id: string } | undefined;

  if (existing) {
    db.prepare(
      "UPDATE subgraph_memberships SET weight = ? WHERE id = ?",
    ).run(weight, existing.id);
    return existing.id;
  }

  const id = newId();
  db.prepare(`
    INSERT INTO subgraph_memberships (id, partition_id, member_kind, member_id, weight, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(id, partitionId, memberKind, memberId, weight, now);

  return id;
}

/**
 * Get all members of a subgraph partition.
 */
export function getPartitionMembers(
  db: Database.Database,
  partitionId: string,
): Array<{ memberKind: string; memberId: string; weight: number }> {
  return db.prepare(`
    SELECT member_kind as memberKind, member_id as memberId, weight
    FROM subgraph_memberships
    WHERE partition_id = ?
    ORDER BY weight DESC
  `).all(partitionId) as Array<{ memberKind: string; memberId: string; weight: number }>;
}

/**
 * Execute a scoped retrieval within a subgraph partition.
 * Returns node IDs that belong to the partition, filtered by status.
 */
export function subgraphSearch(
  db: Database.Database,
  partitionId: string,
  nodeIds?: string[],
): string[] {
  if (nodeIds && nodeIds.length > 0) {
    // Filter given nodes by membership in partition
    const placeholders = nodeIds.map(() => "?").join(",");
    const rows = db.prepare(`
      SELECT member_id FROM subgraph_memberships
      WHERE partition_id = ?
        AND member_kind = 'node'
        AND member_id IN (${placeholders})
      ORDER BY weight DESC
    `).all(partitionId, ...nodeIds) as Array<{ member_id: string }>;

    return rows.map((r) => r.member_id);
  }

  // Return all active nodes in partition
  const rows = db.prepare(`
    SELECT sm.member_id
    FROM subgraph_memberships sm
    JOIN memory_nodes mn ON mn.id = sm.member_id
    WHERE sm.partition_id = ?
      AND sm.member_kind = 'node'
      AND mn.status = 'active'
    ORDER BY sm.weight DESC
  `).all(partitionId) as Array<{ member_id: string }>;

  return rows.map((r) => r.member_id);
}

/**
 * List all partitions.
 */
export function listPartitions(
  db: Database.Database,
): Array<{ id: string; name: string; type: string; memberCount: number }> {
  return db.prepare(`
    SELECT
      sp.id, sp.name, sp.partition_type as type,
      COUNT(sm.id) as memberCount
    FROM subgraph_partitions sp
    LEFT JOIN subgraph_memberships sm ON sm.partition_id = sp.id
    GROUP BY sp.id
    ORDER BY sp.name
  `).all() as Array<{ id: string; name: string; type: string; memberCount: number }>;
}

/**
 * Auto-assign nodes to partitions based on scope and memory_type.
 * Returns number of memberships created.
 */
export function autoPartition(db: Database.Database): number {
  const now = nowISO();
  let created = 0;

  const partitionRules: Array<{
    name: string;
    type: string;
    filter: string;
    params: unknown[];
  }> = [
    {
      name: "procedures",
      type: "functional",
      filter: "memory_type IN ('procedural', 'tool_artifact')",
      params: [],
    },
    {
      name: "safety",
      type: "functional",
      filter: "memory_type IN ('trauma', 'invariant')",
      params: [],
    },
    {
      name: "identity",
      type: "functional",
      filter: "memory_type = 'identity'",
      params: [],
    },
    {
      name: "corrections",
      type: "functional",
      filter: "memory_type = 'correction'",
      params: [],
    },
  ];

  const txn = db.transaction(() => {
    for (const rule of partitionRules) {
      const partitionId = createPartition(db, rule.name, rule.type);

      const nodes = db.prepare(`
        SELECT id FROM memory_nodes
        WHERE status = 'active' AND ${rule.filter}
      `).all(...rule.params) as Array<{ id: string }>;

      for (const node of nodes) {
        const existing = db.prepare(`
          SELECT id FROM subgraph_memberships
          WHERE partition_id = ? AND member_kind = 'node' AND member_id = ?
        `).get(partitionId, node.id) as { id: string } | undefined;

        if (!existing) {
          db.prepare(`
            INSERT INTO subgraph_memberships (id, partition_id, member_kind, member_id, weight, created_at)
            VALUES (?, ?, 'node', ?, 1.0, ?)
          `).run(newId(), partitionId, node.id, now);
          created++;
        }
      }
    }
  });

  txn();
  return created;
}

// ============================================================
// B. Context Textures
// ============================================================

/**
 * Create or update a context texture — output shaping profile.
 */
export function upsertContextTexture(
  db: Database.Database,
  name: string,
  opts?: {
    scope?: string;
    toneProfile?: string;
    formatProfile?: string;
    verbosityProfile?: string;
    toolingBias?: string;
    guardrailProfile?: string;
    activationRules?: Record<string, unknown>;
  },
): string {
  const now = nowISO();

  const existing = db.prepare(
    "SELECT id FROM context_textures WHERE name = ? COLLATE NOCASE",
  ).get(name) as { id: string } | undefined;

  if (existing) {
    db.prepare(`
      UPDATE context_textures SET
        scope = COALESCE(?, scope),
        tone_profile = COALESCE(?, tone_profile),
        format_profile = COALESCE(?, format_profile),
        verbosity_profile = COALESCE(?, verbosity_profile),
        tooling_bias = COALESCE(?, tooling_bias),
        guardrail_profile = COALESCE(?, guardrail_profile),
        activation_rules_json = COALESCE(?, activation_rules_json),
        updated_at = ?
      WHERE id = ?
    `).run(
      opts?.scope ?? null, opts?.toneProfile ?? null,
      opts?.formatProfile ?? null, opts?.verbosityProfile ?? null,
      opts?.toolingBias ?? null, opts?.guardrailProfile ?? null,
      opts?.activationRules ? JSON.stringify(opts.activationRules) : null,
      now, existing.id,
    );
    return existing.id;
  }

  const id = newId();
  db.prepare(`
    INSERT INTO context_textures (
      id, name, scope, tone_profile, format_profile, verbosity_profile,
      tooling_bias, guardrail_profile, activation_rules_json,
      created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    id, name, opts?.scope ?? null,
    opts?.toneProfile ?? null, opts?.formatProfile ?? null,
    opts?.verbosityProfile ?? null, opts?.toolingBias ?? null,
    opts?.guardrailProfile ?? null,
    opts?.activationRules ? JSON.stringify(opts.activationRules) : null,
    now, now,
  );

  return id;
}

/**
 * Get the active context texture for a given scope.
 * Returns the most specific match (exact scope > null scope).
 */
export function getContextTexture(
  db: Database.Database,
  scope?: string,
): {
  id: string;
  name: string;
  toneProfile: string | null;
  formatProfile: string | null;
  verbosityProfile: string | null;
  toolingBias: string | null;
  guardrailProfile: string | null;
} | null {
  // Try exact scope match first, then fallback to null scope
  const row = db.prepare(`
    SELECT id, name, tone_profile, format_profile, verbosity_profile,
           tooling_bias, guardrail_profile
    FROM context_textures
    WHERE scope = ? OR scope IS NULL
    ORDER BY CASE WHEN scope = ? THEN 0 ELSE 1 END
    LIMIT 1
  `).get(scope ?? null, scope ?? null) as {
    id: string; name: string;
    tone_profile: string | null; format_profile: string | null;
    verbosity_profile: string | null; tooling_bias: string | null;
    guardrail_profile: string | null;
  } | undefined;

  if (!row) return null;

  return {
    id: row.id,
    name: row.name,
    toneProfile: row.tone_profile,
    formatProfile: row.format_profile,
    verbosityProfile: row.verbosity_profile,
    toolingBias: row.tooling_bias,
    guardrailProfile: row.guardrail_profile,
  };
}

/**
 * List all context textures.
 */
export function listContextTextures(
  db: Database.Database,
): Array<{ id: string; name: string; scope: string | null }> {
  return db.prepare(
    "SELECT id, name, scope FROM context_textures ORDER BY name",
  ).all() as Array<{ id: string; name: string; scope: string | null }>;
}
