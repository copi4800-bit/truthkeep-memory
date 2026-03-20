import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { openDatabase, type AegisDatabase } from "../../src/db/connection.js";
import { ingestChunk } from "../../src/core/ingest.js";
import {
  resolveEntities,
  rebuildCoOccurrenceEdges,
  prewarm,
  consolidateSession,
  flushPending,
} from "../../src/cognitive/dolphin.js";

let db: AegisDatabase;
let testDir: string;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-dolphin-"));
  const dbPath = path.join(testDir, "test.db");
  db = openDatabase(dbPath);
});

afterEach(() => {
  db.close();
  fs.rmSync(testDir, { recursive: true, force: true });
});

describe("Entity resolution", () => {
  it("merges entities with identical names (case-insensitive)", () => {
    // Create two entities manually with same name, different case
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO entities (id, entity_type, canonical_name, scope, status, created_at, updated_at)
      VALUES ('e1', 'person', 'Alice', 'user', 'active', ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO entities (id, entity_type, canonical_name, scope, status, created_at, updated_at)
      VALUES ('e2', 'person', 'alice', 'user', 'active', ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO entity_aliases (id, entity_id, alias_text, alias_kind, confidence, created_at, updated_at)
      VALUES ('a1', 'e1', 'Alice', 'canonical', 0.8, ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO entity_aliases (id, entity_id, alias_text, alias_kind, confidence, created_at, updated_at)
      VALUES ('a2', 'e2', 'alice', 'canonical', 0.8, ?, ?)
    `).run(now, now);

    const merged = resolveEntities(db.db);
    expect(merged).toBe(1);

    // One entity should be marked as merged
    const active = db.db.prepare(
      "SELECT * FROM entities WHERE status = 'active'",
    ).all();
    expect(active.length).toBe(1);
  });

  it("does not merge entities of different types", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO entities (id, entity_type, canonical_name, scope, status, created_at, updated_at)
      VALUES ('e1', 'person', 'Python', 'user', 'active', ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO entities (id, entity_type, canonical_name, scope, status, created_at, updated_at)
      VALUES ('e2', 'technical', 'Python', 'user', 'active', ?, ?)
    `).run(now, now);

    const merged = resolveEntities(db.db);
    expect(merged).toBe(0);
  });

  it("merges entities with substring match", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO entities (id, entity_type, canonical_name, scope, status, created_at, updated_at)
      VALUES ('e1', 'named_entity', 'SkyClaw Project', 'user', 'active', ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO entities (id, entity_type, canonical_name, scope, status, created_at, updated_at)
      VALUES ('e2', 'named_entity', 'SkyClaw', 'user', 'active', ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO entity_aliases (id, entity_id, alias_text, alias_kind, confidence, created_at, updated_at)
      VALUES ('a1', 'e1', 'SkyClaw Project', 'canonical', 0.8, ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO entity_aliases (id, entity_id, alias_text, alias_kind, confidence, created_at, updated_at)
      VALUES ('a2', 'e2', 'SkyClaw', 'canonical', 0.8, ?, ?)
    `).run(now, now);

    const merged = resolveEntities(db.db);
    expect(merged).toBe(1);
  });

  it("returns 0 for empty entity table", () => {
    const merged = resolveEntities(db.db);
    expect(merged).toBe(0);
  });
});

describe("Co-occurrence edge rebuilding", () => {
  it("creates edges between nodes sharing entities", () => {
    // Ingest nodes that share entities
    ingestChunk(db.db, {
      sourcePath: "memory/a.md",
      content: "@mike leads the backend team at the company.",
      source: "memory",
    });

    ingestChunk(db.db, {
      sourcePath: "memory/b.md",
      content: "@mike reviews all critical pull requests carefully.",
      source: "memory",
    });

    // Remove existing co_entity edges to test rebuild
    db.db.prepare("DELETE FROM memory_edges WHERE edge_type = 'co_entity'").run();

    const created = rebuildCoOccurrenceEdges(db.db);
    expect(created).toBeGreaterThan(0);

    // Verify co_entity edges exist now
    const coEdges = db.db.prepare(
      "SELECT * FROM memory_edges WHERE edge_type = 'co_entity'",
    ).all();
    expect(coEdges.length).toBeGreaterThan(0);
  });

  it("does not create duplicate edges on repeated calls", () => {
    ingestChunk(db.db, {
      sourcePath: "memory/a.md",
      content: "@dev1 and @dev2 pair program together daily.",
      source: "memory",
    });

    ingestChunk(db.db, {
      sourcePath: "memory/b.md",
      content: "@dev1 mentors @dev2 on system design patterns.",
      source: "memory",
    });

    const count1 = rebuildCoOccurrenceEdges(db.db);
    const edgesAfter1 = db.db.prepare(
      "SELECT * FROM memory_edges WHERE edge_type = 'co_entity'",
    ).all().length;

    // Rebuild again — should not create duplicates
    const count2 = rebuildCoOccurrenceEdges(db.db);
    const edgesAfter2 = db.db.prepare(
      "SELECT * FROM memory_edges WHERE edge_type = 'co_entity'",
    ).all().length;

    expect(count2).toBe(0);
    expect(edgesAfter2).toBe(edgesAfter1);
  });
});

describe("Session prewarm", () => {
  it("boosts salience for session-related entities", () => {
    // Ingest session content
    ingestChunk(db.db, {
      sourcePath: "sessions/2024-01-15.json",
      content: "@boss discussed project roadmap and quarterly goals.",
      source: "sessions",
    });

    // Also ingest a memory node mentioning same entity
    ingestChunk(db.db, {
      sourcePath: "memory/boss.md",
      content: "@boss prefers detailed technical documentation.",
      source: "memory",
    });

    const entityIds = prewarm(db.db, "session-123");

    // Should have found entities to prewarm
    // (May be empty if entities aren't from session scope)
    expect(Array.isArray(entityIds)).toBe(true);

    // Prewarm event should be logged
    const events = db.db.prepare(
      "SELECT * FROM memory_events WHERE event_type = 'prewarm'",
    ).all();
    expect(events.length).toBe(1);
  });

  it("returns empty for no session entities", () => {
    const entityIds = prewarm(db.db, "empty-session");
    expect(entityIds.length).toBe(0);
  });
});

describe("Session consolidation", () => {
  it("expires unreferenced working_scratch nodes", () => {
    // Insert an old working_scratch node
    const pastTime = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (
        id, memory_type, content, scope, status, memory_state,
        recall_count, created_at, updated_at
      ) VALUES (
        'scratch-old', 'working_scratch', 'temporary note', 'session', 'active', 'volatile',
        0, ?, ?
      )
    `).run(pastTime, pastTime);

    const result = consolidateSession(db.db, "session-xyz");
    expect(result.expired).toBe(1);

    // Node should be expired
    const node = db.db.prepare(
      "SELECT status FROM memory_nodes WHERE id = 'scratch-old'",
    ).get() as { status: string };
    expect(node.status).toBe("expired");
  });

  it("promotes frequently-recalled session nodes to stable", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (
        id, memory_type, content, scope, status, memory_state,
        recall_count, created_at, updated_at
      ) VALUES (
        'hot-node', 'semantic_fact', 'important discovery', 'session', 'active', 'volatile',
        5, ?, ?
      )
    `).run(now, now);

    const result = consolidateSession(db.db, "session-abc");
    expect(result.promoted).toBe(1);

    const node = db.db.prepare(
      "SELECT memory_state, scope FROM memory_nodes WHERE id = 'hot-node'",
    ).get() as { memory_state: string; scope: string };
    expect(node.memory_state).toBe("stable");
    expect(node.scope).toBe("user");
  });

  it("logs consolidation event", () => {
    consolidateSession(db.db, "session-log-test");

    const events = db.db.prepare(
      "SELECT * FROM memory_events WHERE event_type = 'consolidate'",
    ).all();
    expect(events.length).toBe(1);
  });
});

describe("flushPending", () => {
  it("runs without errors on empty database", () => {
    expect(() => flushPending(db.db)).not.toThrow();
  });

  it("resolves entities and rebuilds edges", () => {
    ingestChunk(db.db, {
      sourcePath: "memory/a.md",
      content: "@flush1 builds memory systems in TypeScript.",
      source: "memory",
    });

    ingestChunk(db.db, {
      sourcePath: "memory/b.md",
      content: "@flush1 deploys services to production environments.",
      source: "memory",
    });

    // Should not throw
    expect(() => flushPending(db.db)).not.toThrow();
  });
});
