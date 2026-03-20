import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { openDatabase, type AegisDatabase } from "../../src/db/connection.js";
import { ingestChunk } from "../../src/core/ingest.js";
import { storeElephantMemory } from "../../src/cognitive/elephant.js";
import {
  createPartition,
  addToPartition,
  getPartitionMembers,
  subgraphSearch,
  listPartitions,
  autoPartition,
  upsertContextTexture,
  getContextTexture,
  listContextTextures,
} from "../../src/cognitive/octopus.js";

let db: AegisDatabase;
let testDir: string;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-octopus-"));
  db = openDatabase(path.join(testDir, "test.db"));
});

afterEach(() => {
  db.close();
  fs.rmSync(testDir, { recursive: true, force: true });
});

describe("Subgraph partitions", () => {
  it("creates a partition", () => {
    const id = createPartition(db.db, "backend", "domain", { scope: "user" });

    const partition = db.db.prepare(
      "SELECT * FROM subgraph_partitions WHERE id = ?",
    ).get(id) as any;
    expect(partition.name).toBe("backend");
    expect(partition.partition_type).toBe("domain");
  });

  it("returns existing partition on duplicate name", () => {
    const id1 = createPartition(db.db, "frontend", "domain");
    const id2 = createPartition(db.db, "frontend", "domain");
    expect(id1).toBe(id2);
  });

  it("adds members to partition", () => {
    const partId = createPartition(db.db, "devops", "domain");
    const nodeId = ingestChunk(db.db, {
      sourcePath: "memory/deploy.md",
      content: "Deployment configuration for Kubernetes.",
      source: "memory",
    });

    addToPartition(db.db, partId, "node", nodeId, 0.8);

    const members = getPartitionMembers(db.db, partId);
    expect(members.length).toBe(1);
    expect(members[0].memberId).toBe(nodeId);
    expect(members[0].weight).toBe(0.8);
  });

  it("updates weight on duplicate membership", () => {
    const partId = createPartition(db.db, "test-part", "domain");
    const nodeId = ingestChunk(db.db, {
      sourcePath: "memory/t.md",
      content: "Test node.",
      source: "memory",
    });

    addToPartition(db.db, partId, "node", nodeId, 0.5);
    addToPartition(db.db, partId, "node", nodeId, 0.9);

    const members = getPartitionMembers(db.db, partId);
    expect(members.length).toBe(1);
    expect(members[0].weight).toBe(0.9);
  });
});

describe("subgraphSearch", () => {
  it("returns nodes belonging to partition", () => {
    const partId = createPartition(db.db, "search-part", "domain");

    const nodeA = ingestChunk(db.db, { sourcePath: "a.md", content: "Node A in partition.", source: "memory" });
    const nodeB = ingestChunk(db.db, { sourcePath: "b.md", content: "Node B in partition.", source: "memory" });
    ingestChunk(db.db, { sourcePath: "c.md", content: "Node C NOT in partition.", source: "memory" });

    addToPartition(db.db, partId, "node", nodeA);
    addToPartition(db.db, partId, "node", nodeB);

    const results = subgraphSearch(db.db, partId);
    expect(results.length).toBe(2);
    expect(results).toContain(nodeA);
    expect(results).toContain(nodeB);
  });

  it("filters given node IDs by partition membership", () => {
    const partId = createPartition(db.db, "filter-part", "domain");
    const nodeA = ingestChunk(db.db, { sourcePath: "fa.md", content: "In partition.", source: "memory" });
    const nodeB = ingestChunk(db.db, { sourcePath: "fb.md", content: "Not in partition.", source: "memory" });

    addToPartition(db.db, partId, "node", nodeA);

    const results = subgraphSearch(db.db, partId, [nodeA, nodeB]);
    expect(results.length).toBe(1);
    expect(results[0]).toBe(nodeA);
  });
});

describe("listPartitions", () => {
  it("lists all partitions with member count", () => {
    const p1 = createPartition(db.db, "alpha", "domain");
    const p2 = createPartition(db.db, "beta", "functional");

    const nodeId = ingestChunk(db.db, { sourcePath: "l.md", content: "Listed node.", source: "memory" });
    addToPartition(db.db, p1, "node", nodeId);

    const list = listPartitions(db.db);
    expect(list.length).toBe(2);

    const alpha = list.find((p) => p.name === "alpha");
    expect(alpha?.memberCount).toBe(1);
  });
});

describe("autoPartition", () => {
  it("auto-assigns nodes by memory_type", () => {
    // Create trauma node → should go to "safety" partition
    storeElephantMemory(db.db, "Never deploy on Friday", "trauma");

    // Create procedural node → should go to "procedures" partition
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, created_at, updated_at)
      VALUES ('proc-1', 'procedural', 'Run npm test before commit', 'active', 'volatile', ?, ?)
    `).run(now, now);

    const created = autoPartition(db.db);
    expect(created).toBeGreaterThanOrEqual(2);

    const partitions = listPartitions(db.db);
    const safety = partitions.find((p) => p.name === "safety");
    expect(safety).toBeDefined();
    expect(safety!.memberCount).toBeGreaterThanOrEqual(1);
  });

  it("does not create duplicates on repeat calls", () => {
    storeElephantMemory(db.db, "Safety rule", "invariant");

    autoPartition(db.db);
    const count1 = listPartitions(db.db).reduce((s, p) => s + p.memberCount, 0);

    autoPartition(db.db);
    const count2 = listPartitions(db.db).reduce((s, p) => s + p.memberCount, 0);

    expect(count1).toBe(count2);
  });
});

describe("Context textures", () => {
  it("creates a context texture", () => {
    const id = upsertContextTexture(db.db, "concise-coder", {
      toneProfile: "direct",
      verbosityProfile: "minimal",
      formatProfile: "code-first",
    });

    const texture = db.db.prepare(
      "SELECT * FROM context_textures WHERE id = ?",
    ).get(id) as any;
    expect(texture.name).toBe("concise-coder");
    expect(texture.tone_profile).toBe("direct");
    expect(texture.verbosity_profile).toBe("minimal");
  });

  it("updates existing texture on upsert", () => {
    const id1 = upsertContextTexture(db.db, "formal", { toneProfile: "professional" });
    const id2 = upsertContextTexture(db.db, "formal", { verbosityProfile: "detailed" });

    expect(id1).toBe(id2);

    const texture = db.db.prepare(
      "SELECT * FROM context_textures WHERE id = ?",
    ).get(id1) as any;
    expect(texture.tone_profile).toBe("professional");
    expect(texture.verbosity_profile).toBe("detailed");
  });

  it("retrieves texture by scope", () => {
    upsertContextTexture(db.db, "global-style", {
      scope: null,
      toneProfile: "friendly",
    });
    upsertContextTexture(db.db, "work-style", {
      scope: "work",
      toneProfile: "formal",
    });

    // Exact scope match preferred
    const workTexture = getContextTexture(db.db, "work");
    expect(workTexture?.name).toBe("work-style");
    expect(workTexture?.toneProfile).toBe("formal");
  });

  it("falls back to null scope texture", () => {
    upsertContextTexture(db.db, "default-style", {
      scope: null,
      toneProfile: "casual",
    });

    const texture = getContextTexture(db.db, "unknown-scope");
    expect(texture?.name).toBe("default-style");
  });

  it("returns null when no textures exist", () => {
    const texture = getContextTexture(db.db, "any");
    expect(texture).toBeNull();
  });

  it("lists all textures", () => {
    upsertContextTexture(db.db, "style-a");
    upsertContextTexture(db.db, "style-b");

    const list = listContextTextures(db.db);
    expect(list.length).toBe(2);
  });
});
