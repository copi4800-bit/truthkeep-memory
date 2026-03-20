import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { openDatabase, type AegisDatabase } from "../../src/db/connection.js";
import { ingestChunk } from "../../src/core/ingest.js";
import { dedupByFingerprint, findDuplicateCluster } from "../../src/cognitive/salmon.js";

let db: AegisDatabase;
let testDir: string;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-salmon-"));
  db = openDatabase(path.join(testDir, "test.db"));
});

afterEach(() => {
  db.close();
  fs.rmSync(testDir, { recursive: true, force: true });
});

describe("dedupByFingerprint", () => {
  it("returns empty map for empty input", () => {
    const result = dedupByFingerprint(db.db, new Map());
    expect(result.size).toBe(0);
  });

  it("keeps all nodes when no duplicates exist", () => {
    const id1 = ingestChunk(db.db, {
      sourcePath: "a.md",
      content: "Completely unique content about quantum physics.",
      source: "memory",
    });
    const id2 = ingestChunk(db.db, {
      sourcePath: "b.md",
      content: "Entirely different text about medieval history.",
      source: "memory",
    });

    const activated = new Map([
      [id1, 0.8],
      [id2, 0.6],
    ]);

    const result = dedupByFingerprint(db.db, activated);
    expect(result.size).toBe(2);
    expect(result.has(id1)).toBe(true);
    expect(result.has(id2)).toBe(true);
  });

  it("keeps node with highest activation when normalized hashes match", () => {
    // Manually insert two nodes with same normalized_hash but different raw_hash
    const now = new Date().toISOString();
    const hash = "aaaa_same_normalized_hash";

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, raw_hash, created_at, updated_at)
      VALUES ('node-a', 'semantic_fact', 'content A', 'active', ?, 'raw_a', ?, ?)
    `).run(hash, now, now);

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, raw_hash, created_at, updated_at)
      VALUES ('node-b', 'semantic_fact', 'content B', 'active', ?, 'raw_b', ?, ?)
    `).run(hash, now, now);

    const activated = new Map([
      ["node-a", 0.3],
      ["node-b", 0.9], // Higher score
    ]);

    const result = dedupByFingerprint(db.db, activated);
    expect(result.size).toBe(1);
    expect(result.has("node-b")).toBe(true); // Kept (higher score)
    expect(result.has("node-a")).toBe(false); // Removed (lower score)
  });

  it("preserves nodes without normalized_hash", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, created_at, updated_at)
      VALUES ('no-hash', 'semantic_fact', 'no hash node', 'active', NULL, ?, ?)
    `).run(now, now);

    const activated = new Map([["no-hash", 0.5]]);
    const result = dedupByFingerprint(db.db, activated);
    expect(result.size).toBe(1);
    expect(result.has("no-hash")).toBe(true);
  });
});

describe("findDuplicateCluster", () => {
  it("returns empty for node without normalized_hash", () => {
    const result = findDuplicateCluster(db.db, "nonexistent");
    expect(result).toEqual([]);
  });

  it("returns empty for unique content", () => {
    const nodeId = ingestChunk(db.db, {
      sourcePath: "unique.md",
      content: "This content is absolutely unique and has no duplicates anywhere.",
      source: "memory",
    });

    const result = findDuplicateCluster(db.db, nodeId);
    expect(result).toEqual([]);
  });

  it("finds nodes sharing the same normalized_hash", () => {
    const now = new Date().toISOString();
    const hash = "bbbb_shared_hash";

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, raw_hash, created_at, updated_at)
      VALUES ('dup-1', 'semantic_fact', 'content', 'active', ?, 'raw1', ?, ?)
    `).run(hash, now, now);

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, raw_hash, created_at, updated_at)
      VALUES ('dup-2', 'semantic_fact', 'content', 'active', ?, 'raw2', ?, ?)
    `).run(hash, now, now);

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, raw_hash, created_at, updated_at)
      VALUES ('dup-3', 'semantic_fact', 'content', 'active', ?, 'raw3', ?, ?)
    `).run(hash, now, now);

    const result = findDuplicateCluster(db.db, "dup-1");
    expect(result).toHaveLength(2);
    expect(result).toContain("dup-2");
    expect(result).toContain("dup-3");
  });

  it("excludes non-active nodes", () => {
    const now = new Date().toISOString();
    const hash = "cccc_mixed_status";

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, raw_hash, created_at, updated_at)
      VALUES ('active-1', 'semantic_fact', 'content', 'active', ?, 'r1', ?, ?)
    `).run(hash, now, now);

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, normalized_hash, raw_hash, created_at, updated_at)
      VALUES ('expired-1', 'semantic_fact', 'content', 'expired', ?, 'r2', ?, ?)
    `).run(hash, now, now);

    const result = findDuplicateCluster(db.db, "active-1");
    expect(result).toHaveLength(0); // expired node excluded
  });
});
