import { describe, it, expect } from "vitest";
import {
  computeRetention,
  computeFinalScore,
  normalizeScores,
  computeScopeFit,
} from "../../src/retrieval/reranker.js";
import type { MemoryNode } from "../../src/core/models.js";

function makeNode(overrides: Partial<MemoryNode> = {}): MemoryNode {
  return {
    id: "test-node",
    memory_type: "semantic_fact",
    content: "test content",
    canonical_subject: null,
    scope: "user",
    tier: null,
    status: "active",
    importance: 0.5,
    salience: 0.5,
    activation_score: 0,
    base_decay_rate: 0.1,
    stability_score: 0.5,
    interference_score: 0,
    override_priority: 0,
    memory_state: "volatile",
    recall_count: 0,
    frequency_count: 0,
    reusability_score: 0,
    approval_score: 0,
    raw_hash: null,
    normalized_hash: null,
    structure_hash: null,
    fingerprint_version: null,
    drift_status: null,
    ttl_expires_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    first_seen_at: null,
    last_seen_at: null,
    last_access_at: null,
    crystallized_at: null,
    extension_json: null,
    source_path: null,
    source_start_line: null,
    source_end_line: null,
    ...overrides,
  };
}

describe("computeRetention", () => {
  it("crystallized memories always return 1.0", () => {
    const node = makeNode({ memory_state: "crystallized" });
    expect(computeRetention(node, new Date().toISOString())).toBe(1.0);
  });

  it("trauma memories always return 1.0", () => {
    const node = makeNode({ memory_type: "trauma" });
    expect(computeRetention(node, new Date().toISOString())).toBe(1.0);
  });

  it("invariant memories always return 1.0", () => {
    const node = makeNode({ memory_type: "invariant" });
    expect(computeRetention(node, new Date().toISOString())).toBe(1.0);
  });

  it("recent volatile memory has high retention", () => {
    const now = new Date().toISOString();
    const node = makeNode({
      created_at: now,
      last_access_at: now,
      importance: 0.8,
      salience: 0.7,
    });
    const retention = computeRetention(node, now);
    expect(retention).toBeGreaterThan(0.5);
  });

  it("old volatile memory decays", () => {
    const old = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString();
    const now = new Date().toISOString();
    const node = makeNode({
      created_at: old,
      last_access_at: old,
      base_decay_rate: 0.1,
    });
    const retention = computeRetention(node, now);
    expect(retention).toBeLessThan(0.5);
  });

  it("high recall count improves retention", () => {
    const old = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
    const now = new Date().toISOString();

    const lowRecall = makeNode({
      created_at: old,
      last_access_at: old,
      recall_count: 0,
      base_decay_rate: 0.1,
    });

    const highRecall = makeNode({
      created_at: old,
      last_access_at: old,
      recall_count: 10,
      frequency_count: 5,
      base_decay_rate: 0.1,
    });

    const retLow = computeRetention(lowRecall, now);
    const retHigh = computeRetention(highRecall, now);
    expect(retHigh).toBeGreaterThan(retLow);
  });

  it("high interference reduces retention", () => {
    const old = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
    const now = new Date().toISOString();

    const noInterference = makeNode({
      created_at: old,
      last_access_at: old,
      interference_score: 0,
      base_decay_rate: 0.1,
    });

    const highInterference = makeNode({
      created_at: old,
      last_access_at: old,
      interference_score: 0.8,
      base_decay_rate: 0.1,
    });

    const retClean = computeRetention(noInterference, now);
    const retDirty = computeRetention(highInterference, now);
    expect(retClean).toBeGreaterThan(retDirty);
  });
});

describe("computeFinalScore", () => {
  it("higher FTS score = higher final score", () => {
    const node = makeNode();
    const base = { ftsScore: 0, activationScore: 0, entityOverlap: 0, retention: 0.5, scopeFit: 0.5, procedureBonus: 0, overridePriority: 0 };

    const lowFts = computeFinalScore(node, { ...base, ftsScore: 0.2 });
    const highFts = computeFinalScore(node, { ...base, ftsScore: 0.9 });
    expect(highFts).toBeGreaterThan(lowFts);
  });

  it("elephant override adds significant bonus", () => {
    const node = makeNode({ override_priority: 100 });
    const signals = { ftsScore: 0.1, activationScore: 0, entityOverlap: 0, retention: 0.5, scopeFit: 0.5, procedureBonus: 0, overridePriority: 100 };
    const score = computeFinalScore(node, signals);
    expect(score).toBeGreaterThan(10); // Override multiplier = 2.0 × 100
  });

  it("suppressed memory gets penalty", () => {
    const normal = makeNode();
    const suppressed = makeNode({ memory_state: "suppressed" });
    const signals = { ftsScore: 0.5, activationScore: 0.3, entityOverlap: 0.2, retention: 0.5, scopeFit: 0.5, procedureBonus: 0, overridePriority: 0 };

    const normalScore = computeFinalScore(normal, signals);
    const suppressedScore = computeFinalScore(suppressed, signals);
    expect(suppressedScore).toBeLessThan(normalScore);
  });
});

describe("normalizeScores", () => {
  it("empty array returns empty", () => {
    expect(normalizeScores([])).toEqual([]);
  });

  it("single item returns 1.0", () => {
    expect(normalizeScores([42])).toEqual([1.0]);
  });

  it("all same returns all 1.0", () => {
    expect(normalizeScores([5, 5, 5])).toEqual([1, 1, 1]);
  });

  it("output is in [0, 1]", () => {
    const result = normalizeScores([1, 5, 10, 50, 100]);
    for (const s of result) {
      expect(s).toBeGreaterThanOrEqual(0);
      expect(s).toBeLessThanOrEqual(1);
    }
  });

  it("preserves relative order", () => {
    const result = normalizeScores([1, 5, 10]);
    expect(result[2]).toBeGreaterThan(result[1]);
    expect(result[1]).toBeGreaterThan(result[0]);
  });
});

describe("computeScopeFit", () => {
  it("global scope returns high score", () => {
    expect(computeScopeFit("global")).toBe(0.9);
  });

  it("session scope with key returns high score", () => {
    expect(computeScopeFit("session", "some-key")).toBe(0.8);
  });

  it("user scope returns moderate score", () => {
    expect(computeScopeFit("user")).toBe(0.7);
  });

  it("null scope returns neutral", () => {
    expect(computeScopeFit(null)).toBe(0.5);
  });
});
