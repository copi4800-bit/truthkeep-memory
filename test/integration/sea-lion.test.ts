import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { openDatabase, type AegisDatabase } from "../../src/db/connection.js";
import { ingestChunk } from "../../src/core/ingest.js";
import {
  upsertConcept,
  addInheritance,
  resolveInheritedRules,
  transitiveInference,
  cacheDerivedRelation,
  getCachedDerivedRelations,
  purgeExpiredDerivedRelations,
} from "../../src/cognitive/sea-lion.js";

let db: AegisDatabase;
let testDir: string;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-sealion-"));
  db = openDatabase(path.join(testDir, "test.db"));
});

afterEach(() => {
  db.close();
  fs.rmSync(testDir, { recursive: true, force: true });
});

describe("Concept management", () => {
  it("creates a concept node", () => {
    const id = upsertConcept(db.db, "TypeScript", "language", {
      priority: 5,
      confidence: 0.9,
      rulePayload: { superset_of: "JavaScript" },
    });

    const concept = db.db.prepare("SELECT * FROM concept_nodes WHERE id = ?").get(id) as any;
    expect(concept.canonical_name).toBe("TypeScript");
    expect(concept.concept_type).toBe("language");
    expect(concept.confidence).toBe(0.9);
    expect(JSON.parse(concept.rule_payload_json).superset_of).toBe("JavaScript");
  });

  it("updates existing concept on upsert", () => {
    const id1 = upsertConcept(db.db, "Python", "language", { confidence: 0.5 });
    const id2 = upsertConcept(db.db, "Python", "language", { confidence: 0.9 });

    expect(id1).toBe(id2);

    const concept = db.db.prepare("SELECT confidence FROM concept_nodes WHERE id = ?").get(id1) as any;
    expect(concept.confidence).toBe(0.9);
  });
});

describe("Concept inheritance", () => {
  it("creates inheritance link", () => {
    const langId = upsertConcept(db.db, "Programming Language", "category");
    const tsId = upsertConcept(db.db, "TypeScript", "language");

    const linkId = addInheritance(
      db.db,
      { kind: "concept", id: tsId },
      { kind: "concept", id: langId },
      "is_a",
      10,
    );

    const link = db.db.prepare("SELECT * FROM concept_inheritance WHERE id = ?").get(linkId) as any;
    expect(link.src_id).toBe(tsId);
    expect(link.dst_id).toBe(langId);
    expect(link.inheritance_type).toBe("is_a");
  });
});

describe("resolveInheritedRules", () => {
  it("walks inheritance chain to find rules", () => {
    // Build hierarchy: Node → TypeScript → Programming Language (has rule)
    const nodeId = ingestChunk(db.db, {
      sourcePath: "memory/ts.md",
      content: "TypeScript configuration for the SkyClaw project.",
      source: "memory",
    });

    const tsId = upsertConcept(db.db, "TypeScript", "language");
    const langId = upsertConcept(db.db, "Programming Language", "category", {
      rulePayload: { always_lint: true, require_tests: true },
      confidence: 0.8,
    });

    // Node inherits from TypeScript
    addInheritance(db.db, { kind: "node", id: nodeId }, { kind: "concept", id: tsId }, "uses");
    // TypeScript inherits from Programming Language
    addInheritance(db.db, { kind: "concept", id: tsId }, { kind: "concept", id: langId }, "is_a");

    const rules = resolveInheritedRules(db.db, nodeId);
    expect(rules.length).toBeGreaterThan(0);
    expect(rules[0].dstNodeId).toBe(langId);
    expect(rules[0].depth).toBe(2);
    expect(rules[0].via.length).toBe(2);
  });

  it("respects max depth limit", () => {
    // Create a deep chain beyond MAX_INHERITANCE_DEPTH
    const concepts: string[] = [];
    for (let i = 0; i < 8; i++) {
      concepts.push(upsertConcept(db.db, `Level${i}`, "category", {
        rulePayload: i === 7 ? { deep_rule: true } : undefined,
        confidence: 0.9,
      }));
    }

    const nodeId = ingestChunk(db.db, {
      sourcePath: "memory/deep.md",
      content: "Deep inheritance test content.",
      source: "memory",
    });

    // Chain: node → L0 → L1 → ... → L7
    addInheritance(db.db, { kind: "node", id: nodeId }, { kind: "concept", id: concepts[0] }, "uses");
    for (let i = 0; i < concepts.length - 1; i++) {
      addInheritance(
        db.db,
        { kind: "concept", id: concepts[i] },
        { kind: "concept", id: concepts[i + 1] },
        "is_a",
      );
    }

    const rules = resolveInheritedRules(db.db, nodeId);
    // Should not reach depth 8 (max is 5)
    for (const r of rules) {
      expect(r.depth).toBeLessThanOrEqual(5);
    }
  });

  it("returns empty for node with no inheritance", () => {
    const nodeId = ingestChunk(db.db, {
      sourcePath: "memory/orphan.md",
      content: "Orphan node with no concept links.",
      source: "memory",
    });

    const rules = resolveInheritedRules(db.db, nodeId);
    expect(rules.length).toBe(0);
  });
});

describe("transitiveInference", () => {
  it("follows typed edge chain", () => {
    // A --[related_to]--> B --[implies]--> C
    const idA = ingestChunk(db.db, { sourcePath: "a.md", content: "Node A content alpha.", source: "memory" });
    const idB = ingestChunk(db.db, { sourcePath: "b.md", content: "Node B content beta.", source: "memory" });
    const idC = ingestChunk(db.db, { sourcePath: "c.md", content: "Node C content gamma.", source: "memory" });

    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_edges (id, src_node_id, dst_node_id, edge_type, weight, confidence, status, coactivation_count, created_at, updated_at)
      VALUES (?, ?, ?, 'related_to', 0.8, 0.9, 'active', 1, ?, ?)
    `).run("e1", idA, idB, now, now);

    db.db.prepare(`
      INSERT INTO memory_edges (id, src_node_id, dst_node_id, edge_type, weight, confidence, status, coactivation_count, created_at, updated_at)
      VALUES (?, ?, ?, 'implies', 0.7, 0.8, 'active', 1, ?, ?)
    `).run("e2", idB, idC, now, now);

    const results = transitiveInference(db.db, idA, ["related_to", "implies"]);
    expect(results.length).toBe(1);
    expect(results[0].dstNodeId).toBe(idC);
    expect(results[0].depth).toBe(2);
    expect(results[0].confidence).toBeGreaterThan(0);
    expect(results[0].confidence).toBeLessThan(1);
  });

  it("returns empty for broken chain", () => {
    const idA = ingestChunk(db.db, { sourcePath: "x.md", content: "Isolated node.", source: "memory" });

    const results = transitiveInference(db.db, idA, ["related_to", "implies"]);
    expect(results.length).toBe(0);
  });

  it("returns empty for empty edge chain", () => {
    const results = transitiveInference(db.db, "any-id", []);
    expect(results.length).toBe(0);
  });
});

describe("Derived relations cache", () => {
  it("caches and retrieves derived relation", () => {
    const idA = ingestChunk(db.db, { sourcePath: "dr1.md", content: "Derived source.", source: "memory" });
    const idB = ingestChunk(db.db, { sourcePath: "dr2.md", content: "Derived target.", source: "memory" });

    cacheDerivedRelation(db.db, idA, idB, "inferred", ["step1", "step2"], 0.7);

    const cached = getCachedDerivedRelations(db.db, idA);
    expect(cached.length).toBe(1);
    expect(cached[0].dstNodeId).toBe(idB);
    expect(cached[0].confidence).toBe(0.7);
    expect(cached[0].path).toEqual(["step1", "step2"]);
  });

  it("filters by derivation type", () => {
    const idA = ingestChunk(db.db, { sourcePath: "ft1.md", content: "Filter test.", source: "memory" });
    const idB = ingestChunk(db.db, { sourcePath: "ft2.md", content: "Target one.", source: "memory" });
    const idC = ingestChunk(db.db, { sourcePath: "ft3.md", content: "Target two.", source: "memory" });

    cacheDerivedRelation(db.db, idA, idB, "inferred", ["p1"], 0.8);
    cacheDerivedRelation(db.db, idA, idC, "transitive", ["p2"], 0.6);

    const inferred = getCachedDerivedRelations(db.db, idA, "inferred");
    expect(inferred.length).toBe(1);
    expect(inferred[0].dstNodeId).toBe(idB);
  });

  it("purges expired relations", () => {
    const idA = ingestChunk(db.db, { sourcePath: "exp1.md", content: "Expire test.", source: "memory" });
    const idB = ingestChunk(db.db, { sourcePath: "exp2.md", content: "Target.", source: "memory" });

    // Insert with already-expired timestamp
    const past = new Date(Date.now() - 1000).toISOString();
    db.db.prepare(`
      INSERT INTO derived_relations (id, src_node_id, dst_node_id, derivation_type, derivation_path_json, derivation_depth, confidence, expires_at, created_at)
      VALUES (?, ?, ?, 'test', '[]', 1, 0.5, ?, ?)
    `).run("dr-expired", idA, idB, past, past);

    const purged = purgeExpiredDerivedRelations(db.db);
    expect(purged).toBe(1);
  });
});
