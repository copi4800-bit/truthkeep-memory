import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { openDatabase, type AegisDatabase } from "../../src/db/connection.js";
import { ingestChunk } from "../../src/core/ingest.js";
import { createSnapshot, exportLogicalData } from "../../src/cognitive/tardigrade.js";

let db: AegisDatabase;
let testDir: string;
let backupDir: string;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-tardigrade-"));
  db = openDatabase(path.join(testDir, "test.db"));
  backupDir = path.join(testDir, "backups");
});

afterEach(() => {
  try {
    db.close();
  } catch {}
  try {
    fs.rmSync(testDir, { recursive: true, force: true });
  } catch (e) {
    // Ignore EPERM on Windows
  }
});

describe("Tardigrade Backup", () => {
  it("creates a safe snapshot of the database", async () => {
    // 1. Ingest some test data
    ingestChunk(db.db, {
      sourcePath: "doc.txt",
      content: "This is memory data to backup.",
      source: "memory",
    });

    // 2. Create snapshot
    const result = await createSnapshot(db.db, backupDir);

    // 3. Verify snapshot result
    expect(result.snapshotPath).toContain(".db.bak");
    expect(fs.existsSync(result.snapshotPath)).toBe(true);
    expect(result.sizeBytes).toBeGreaterThan(0);
    expect(result.checksum).toMatch(/^[a-f0-9]{64}$/i); // valid sha256 hex
  });

  it("exports logical JSONL data", () => {
    // 1. Ingest test data
    ingestChunk(db.db, {
      sourcePath: "exportation.txt",
      content: "Data to export as jsonl.",
      source: "memory",
    });

    // 2. Export 
    const exportPath = path.join(backupDir, "export.jsonl");
    const result = exportLogicalData(db.db, exportPath);

    // 3. Verify physical result
    expect(fs.existsSync(exportPath)).toBe(true);
    expect(result.nodeCount).toBeGreaterThan(0);

    // 4. Verify text content
    const content = fs.readFileSync(exportPath, "utf-8");
    expect(content).toContain("exportation.txt");
    expect(content).toContain("Data to export as jsonl.");
  });
});
