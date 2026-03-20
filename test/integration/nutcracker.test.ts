import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { openDatabase, type AegisDatabase } from "../../src/db/connection.js";
import {
  setTTL,
  clearTTL,
  findExpiredTTL,
  expireTTLNodes,
  autoSetScratchTTL,
} from "../../src/cognitive/nutcracker.js";

let db: AegisDatabase;
let testDir: string;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-nutcracker-"));
  db = openDatabase(path.join(testDir, "test.db"));
});

afterEach(() => {
  db.close();
  fs.rmSync(testDir, { recursive: true, force: true });
});

describe("TTL lifecycle", () => {
  it("sets TTL on a node", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, created_at, updated_at)
      VALUES ('ttl-node', 'working_scratch', 'temp data', 'active', 'volatile', ?, ?)
    `).run(now, now);

    setTTL(db.db, "ttl-node", 2); // 2 hours

    const node = db.db.prepare(
      "SELECT ttl_expires_at FROM memory_nodes WHERE id = 'ttl-node'",
    ).get() as any;
    expect(node.ttl_expires_at).not.toBeNull();
  });

  it("clears TTL from a node", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, ttl_expires_at, created_at, updated_at)
      VALUES ('clear-node', 'working_scratch', 'temp', 'active', 'volatile', ?, ?, ?)
    `).run(new Date(Date.now() + 3600000).toISOString(), now, now);

    clearTTL(db.db, "clear-node");

    const node = db.db.prepare(
      "SELECT ttl_expires_at FROM memory_nodes WHERE id = 'clear-node'",
    ).get() as any;
    expect(node.ttl_expires_at).toBeNull();
  });

  it("finds expired TTL nodes", () => {
    const now = new Date().toISOString();
    const past = new Date(Date.now() - 1000).toISOString();

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, ttl_expires_at, created_at, updated_at)
      VALUES ('expired-ttl', 'working_scratch', 'old temp', 'active', 'volatile', ?, ?, ?)
    `).run(past, now, now);

    const expired = findExpiredTTL(db.db);
    expect(expired.length).toBe(1);
    expect(expired[0].id).toBe("expired-ttl");
  });

  it("expires TTL nodes", () => {
    const now = new Date().toISOString();
    const past = new Date(Date.now() - 1000).toISOString();

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, ttl_expires_at, created_at, updated_at)
      VALUES ('to-expire', 'working_scratch', 'temp', 'active', 'volatile', ?, ?, ?)
    `).run(past, now, now);

    const count = expireTTLNodes(db.db);
    expect(count).toBe(1);

    const node = db.db.prepare(
      "SELECT status FROM memory_nodes WHERE id = 'to-expire'",
    ).get() as any;
    expect(node.status).toBe("expired");
  });

  it("does not expire nodes with future TTL", () => {
    const now = new Date().toISOString();
    const future = new Date(Date.now() + 3600000).toISOString();

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, ttl_expires_at, created_at, updated_at)
      VALUES ('future-ttl', 'working_scratch', 'still valid', 'active', 'volatile', ?, ?, ?)
    `).run(future, now, now);

    const count = expireTTLNodes(db.db);
    expect(count).toBe(0);
  });
});

describe("autoSetScratchTTL", () => {
  it("sets TTL on working_scratch nodes without TTL", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, created_at, updated_at)
      VALUES ('scratch-1', 'working_scratch', 'temp note 1', 'active', 'volatile', ?, ?)
    `).run(now, now);
    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, created_at, updated_at)
      VALUES ('scratch-2', 'working_scratch', 'temp note 2', 'active', 'volatile', ?, ?)
    `).run(now, now);

    const count = autoSetScratchTTL(db.db, 12);
    expect(count).toBe(2);

    const node = db.db.prepare(
      "SELECT ttl_expires_at FROM memory_nodes WHERE id = 'scratch-1'",
    ).get() as any;
    expect(node.ttl_expires_at).not.toBeNull();
  });

  it("does not touch non-scratch nodes", () => {
    const now = new Date().toISOString();
    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, created_at, updated_at)
      VALUES ('fact-1', 'semantic_fact', 'important fact', 'active', 'volatile', ?, ?)
    `).run(now, now);

    const count = autoSetScratchTTL(db.db);
    expect(count).toBe(0);
  });

  it("does not overwrite existing TTL", () => {
    const now = new Date().toISOString();
    const existingTTL = new Date(Date.now() + 48 * 3600000).toISOString();

    db.db.prepare(`
      INSERT INTO memory_nodes (id, memory_type, content, status, memory_state, ttl_expires_at, created_at, updated_at)
      VALUES ('has-ttl', 'working_scratch', 'temp with ttl', 'active', 'volatile', ?, ?, ?)
    `).run(existingTTL, now, now);

    const count = autoSetScratchTTL(db.db);
    expect(count).toBe(0);

    const node = db.db.prepare(
      "SELECT ttl_expires_at FROM memory_nodes WHERE id = 'has-ttl'",
    ).get() as any;
    expect(node.ttl_expires_at).toBe(existingTTL);
  });
});
