/**
 * AegisMemoryManager — implements OpenClaw's MemorySearchManager interface.
 *
 * This is the main bridge between Memory Aegis v3 and OpenClaw.
 */

import fs from "node:fs";
import path from "node:path";
import type Database from "better-sqlite3";
import { openDatabase, resolveDbPath, type AegisDatabase } from "./db/connection.js";
import { runMigrations, migrateFromBuiltin } from "./db/migrate.js";
import { executeRetrievalPipeline } from "./retrieval/pipeline.js";
import { ingestBatch } from "./core/ingest.js";
import { microChunk } from "./cognitive/nutcracker.js";
import { flushPending } from "./cognitive/dolphin.js";
import { runMaintenanceCycle } from "./retention/maintenance.js";
import { autoPartition } from "./cognitive/octopus.js";
import { autoSetScratchTTL } from "./cognitive/nutcracker.js";
import { createSnapshot, exportLogicalData, type BackupResult, type ExportResult } from "./cognitive/tardigrade.js";
import { restoreFromSnapshot, type RestoreResult } from "./cognitive/planarian.js";
import { type AegisConfig, DEFAULT_AEGIS_CONFIG, type CognitiveLayers, type AegisTelemetry } from "./core/models.js";
import type { MemorySearchResult } from "./retrieval/packet.js";
import { Honeybee } from "./telemetry/honeybee.js";
import { Axolotl } from "./maintenance/axolotl.js";

// --- OpenClaw-compatible types (mirrored from openclaw/src/memory/types.ts) ---

type MemorySource = "memory" | "sessions";

type MemoryEmbeddingProbeResult = {
  ok: boolean;
  error?: string;
};

type MemorySyncProgressUpdate = {
  completed: number;
  total: number;
  label?: string;
};

type MemoryProviderStatus = {
  backend: string;
  provider: string;
  model?: string;
  files?: number;
  chunks?: number;
  dirty?: boolean;
  workspaceDir?: string;
  dbPath?: string;
  sources?: MemorySource[];
  sourceCounts?: Array<{ source: MemorySource; files: number; chunks: number }>;
  fts?: { enabled: boolean; available: boolean; error?: string };
  vector?: { enabled: boolean; available?: boolean; dims?: number };
  custom?: Record<string, unknown>;
};

// --- Manager Cache ---

const MANAGER_CACHE = new Map<string, AegisMemoryManager>();

// --- Main Class ---

export class AegisMemoryManager {
  private aegisDb: AegisDatabase;
  private dirty = false;
  private readonly config: AegisConfig;
  private readonly dbPath: string;

  private constructor(
    private readonly workspaceDir: string,
    private readonly agentId: string,
    config: Partial<AegisConfig>,
  ) {
    this.config = { ...DEFAULT_AEGIS_CONFIG, ...config };
    this.dbPath = resolveDbPath(workspaceDir);
    this.aegisDb = openDatabase(this.dbPath);
    runMigrations(this.aegisDb.db);
  }

  /**
   * Factory method — creates or returns cached manager for an agent.
   */
  static async create(params: {
    agentId: string;
    workspaceDir: string;
    config?: Partial<AegisConfig>;
    purpose?: "default" | "status";
  }): Promise<AegisMemoryManager | null> {
    const cacheKey = `${params.agentId}:${params.workspaceDir}`;

    if (params.purpose !== "status") {
      const cached = MANAGER_CACHE.get(cacheKey);
      if (cached) return cached;
    }

    try {
      const manager = new AegisMemoryManager(
        params.workspaceDir,
        params.agentId,
        params.config ?? {},
      );

      // Auto-migrate from builtin if this is first use
      const builtinPath = path.join(params.workspaceDir, "memory.db");
      if (
        fs.existsSync(builtinPath) &&
        manager.getNodeCount() === 0
      ) {
        const migrated = migrateFromBuiltin(manager.aegisDb.db, builtinPath);
        if (migrated > 0) {
          manager.dirty = true;
        }
      }

      if (params.purpose !== "status") {
        MANAGER_CACHE.set(cacheKey, manager);
      }

      return manager;
    } catch (error) {
      console.error("[AegisMemoryManager.create] initialization failed:", error);
      return null;
    }
  }

  // === MemorySearchManager Interface ===

  async search(
    query: string,
    opts?: { maxResults?: number; minScore?: number; sessionKey?: string },
  ): Promise<MemorySearchResult[]> {
    return executeRetrievalPipeline(this.aegisDb.db, query, this.config, {
      maxResults: opts?.maxResults,
      minScore: opts?.minScore,
      sessionKey: opts?.sessionKey,
    });
  }

  async readFile(params: {
    relPath: string;
    from?: number;
    lines?: number;
  }): Promise<{ text: string; path: string }> {
    // Aegis-native path
    if (params.relPath.startsWith("aegis://")) {
      const parts = params.relPath.split("/");
      const nodeId = parts[parts.length - 1];

      const node = this.aegisDb.db.prepare(
        "SELECT content FROM memory_nodes WHERE id = ?",
      ).get(nodeId) as { content: string } | undefined;

      if (!node) throw new Error(`Memory node not found: ${nodeId}`);

      const lines = node.content.split("\n");
      const from = params.from ?? 0;
      const count = params.lines ?? lines.length;
      const text = lines.slice(from, from + count).join("\n");

      // Touch node for retention
      this.aegisDb.db.prepare(`
        UPDATE memory_nodes
        SET last_access_at = datetime('now'), recall_count = recall_count + 1, updated_at = datetime('now')
        WHERE id = ?
      `).run(nodeId);

      return { text, path: params.relPath };
    }

    // Physical file read
    const absolutePath = path.isAbsolute(params.relPath)
      ? params.relPath
      : path.resolve(this.workspaceDir, params.relPath);

    const content = await fs.promises.readFile(absolutePath, "utf-8");
    const lines = content.split("\n");
    const from = params.from ?? 0;
    const count = params.lines ?? lines.length;
    const text = lines.slice(from, from + count).join("\n");

    return { text, path: params.relPath };
  }

  status(): MemoryProviderStatus {
    const stats = this.getStats();

    return {
      backend: "aegis",
      provider: "aegis-fts5",
      model: undefined,
      files: stats.sourceFileCount,
      chunks: stats.nodeCount,
      dirty: this.dirty,
      workspaceDir: this.workspaceDir,
      dbPath: this.dbPath,
      sources: ["memory", "sessions"],
      sourceCounts: [
        { source: "memory", files: stats.memoryFileCount, chunks: stats.memoryNodeCount },
        { source: "sessions", files: stats.sessionFileCount, chunks: stats.sessionNodeCount },
      ],
      fts: { enabled: true, available: true },
      vector: {
        enabled: this.config.embeddingAccelerator,
        available: this.config.embeddingAccelerator,
      },
      custom: {
        aegis: {
          version: "3.0.0",
          schemaVersion: stats.schemaVersion,
          layers: this.config.enabledLayers,
          entityCount: stats.entityCount,
          edgeCount: stats.edgeCount,
          procedureCount: stats.procedureCount,
          crystallizedCount: stats.crystallizedCount,
          suppressedCount: stats.suppressedCount,
        },
      },
    };
  }

  async sync(params?: {
    reason?: string;
    force?: boolean;
    sessionFiles?: string[];
    progress?: (update: MemorySyncProgressUpdate) => void;
  }): Promise<void> {
    const memoryDir = path.join(this.workspaceDir, "memory");
    const files: Array<{ path: string; content: string; source: MemorySource }> = [];

    // Scan memory directory
    if (fs.existsSync(memoryDir)) {
      const memoryFiles = await this.scanDirectory(memoryDir, "memory");
      files.push(...memoryFiles);
    }

    // Scan MEMORY.md
    const memoryMd = path.join(this.workspaceDir, "MEMORY.md");
    if (fs.existsSync(memoryMd)) {
      const content = await fs.promises.readFile(memoryMd, "utf-8");
      files.push({ path: "MEMORY.md", content, source: "memory" });
    }

    // Scan session files
    if (params?.sessionFiles) {
      for (const sessionFile of params.sessionFiles) {
        try {
          const content = await fs.promises.readFile(sessionFile, "utf-8");
          files.push({
            path: path.relative(this.workspaceDir, sessionFile),
            content,
            source: "sessions",
          });
        } catch {
          // Skip unreadable session files
        }
      }
    }

    params?.progress?.({ completed: 0, total: files.length, label: "Indexing files" });

    // Chunk and ingest
    const chunks = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileChunks = microChunk(file.content);

      for (const chunk of fileChunks) {
        chunks.push({
          sourcePath: file.path,
          content: chunk.content,
          source: file.source as "memory" | "sessions",
          startLine: chunk.startLine,
          endLine: chunk.endLine,
        });
      }

      params?.progress?.({ completed: i + 1, total: files.length, label: "Indexing files" });
    }

    if (chunks.length > 0) {
      ingestBatch(this.aegisDb.db, chunks);
    }

    this.dirty = false;
  }

  async probeEmbeddingAvailability(): Promise<MemoryEmbeddingProbeResult> {
    // Aegis v3 does NOT require embeddings — always available
    return { ok: true };
  }

  async probeVectorAvailability(): Promise<boolean> {
    // FTS5 replaces vector search — always available
    return true;
  }

  async close(): Promise<void> {
    const cacheKey = `${this.agentId}:${this.workspaceDir}`;
    if (!MANAGER_CACHE.has(cacheKey)) return; // Already closed

    try {
      flushPending(this.aegisDb.db);
    } catch {
      // Ignore errors during flush on close
    }

    this.aegisDb.close();
    MANAGER_CACHE.delete(cacheKey);
  }

  // === Cognitive Access ===

  /**
   * Expose internal database for hooks and cognitive layers.
   */
  getDb(): Database.Database {
    return this.aegisDb.db;
  }

  /**
   * Run full maintenance cycle: decay, TTL, partitioning, FTS optimize, and Viper rotation.
   */
  async runMaintenance(): Promise<import("./retention/maintenance.js").MaintenanceReport> {
    const report = await runMaintenanceCycle(this.aegisDb.db, this.workspaceDir, this.config);
    autoSetScratchTTL(this.aegisDb.db);
    autoPartition(this.aegisDb.db);
    return report;
  }

  // === Disaster Recovery ===

  /**
   * Run Tardigrade layer to create a snapshot or logical export.
   */
  async backup(mode: "snapshot" | "export", destDir: string): Promise<BackupResult | ExportResult> {
    if (mode === "snapshot") {
      return createSnapshot(this.aegisDb.db, destDir);
    } else {
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      const exportPath = path.join(destDir, `aegis-export-${ts}.jsonl`);
      return exportLogicalData(this.aegisDb.db, exportPath);
    }
  }

  /**
   * Run Planarian layer to restore the database from a backup snapshot.
   * WARNING: Overwrites the current active database!
   */
  async restore(snapshotPath: string): Promise<RestoreResult> {
    return restoreFromSnapshot(snapshotPath, this.dbPath);
  }

  /**
   * Honeybee: Thu thập số liệu thống kê chi tiết.
   */
  async getHoneybeeStats(): Promise<{ text: string; data: AegisTelemetry }> {
    const honeybee = new Honeybee(this.aegisDb.db, this.workspaceDir);
    const data = await honeybee.collect();
    const text = honeybee.render(data);
    return { text, data };
  }

  /**
   * Axolotl: Tái tạo dữ liệu phái sinh.
   */
  async regenerateDerivedData(): Promise<{ createdRelations: number }> {
    const axolotl = new Axolotl(this.aegisDb.db, this.config);
    return axolotl.regenerate();
  }

  // === Helpers ===

  layerEnabled(layer: CognitiveLayers): boolean {
    return this.config.enabledLayers.includes(layer);
  }

  private getNodeCount(): number {
    const row = this.aegisDb.db.prepare(
      "SELECT COUNT(*) as count FROM memory_nodes",
    ).get() as { count: number };
    return row.count;
  }

  private getStats() {
    const db = this.aegisDb.db;

    const nodeCount = (db.prepare("SELECT COUNT(*) as c FROM memory_nodes WHERE status='active'").get() as { c: number }).c;
    const edgeCount = (db.prepare("SELECT COUNT(*) as c FROM memory_edges WHERE status='active'").get() as { c: number }).c;
    const entityCount = (db.prepare("SELECT COUNT(*) as c FROM entities WHERE status='active'").get() as { c: number }).c;
    const procedureCount = (db.prepare("SELECT COUNT(*) as c FROM procedures WHERE status='active'").get() as { c: number }).c;
    const crystallizedCount = (db.prepare("SELECT COUNT(*) as c FROM memory_nodes WHERE memory_state='crystallized'").get() as { c: number }).c;
    const suppressedCount = (db.prepare("SELECT COUNT(*) as c FROM memory_nodes WHERE memory_state='suppressed'").get() as { c: number }).c;

    const memoryNodeCount = (db.prepare("SELECT COUNT(*) as c FROM memory_nodes WHERE scope != 'session' AND status='active'").get() as { c: number }).c;
    const sessionNodeCount = (db.prepare("SELECT COUNT(*) as c FROM memory_nodes WHERE scope = 'session' AND status='active'").get() as { c: number }).c;

    // Count unique source files
    const memoryFileCount = (db.prepare("SELECT COUNT(DISTINCT source_path) as c FROM memory_nodes WHERE scope != 'session' AND source_path IS NOT NULL").get() as { c: number }).c;
    const sessionFileCount = (db.prepare("SELECT COUNT(DISTINCT source_path) as c FROM memory_nodes WHERE scope = 'session' AND source_path IS NOT NULL").get() as { c: number }).c;

    let schemaVersion = 1;
    try {
      const row = db.prepare("SELECT MAX(version) as v FROM schema_version").get() as { v: number | null };
      schemaVersion = row?.v ?? 1;
    } catch { /* table may not exist */ }

    return {
      nodeCount,
      edgeCount,
      entityCount,
      procedureCount,
      crystallizedCount,
      suppressedCount,
      memoryNodeCount,
      sessionNodeCount,
      memoryFileCount,
      sessionFileCount,
      sourceFileCount: memoryFileCount + sessionFileCount,
      schemaVersion,
    };
  }

  private async scanDirectory(
    dir: string,
    source: MemorySource,
  ): Promise<Array<{ path: string; content: string; source: MemorySource }>> {
    const results: Array<{ path: string; content: string; source: MemorySource }> = [];

    const entries = await fs.promises.readdir(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        const subResults = await this.scanDirectory(fullPath, source);
        results.push(...subResults);
      } else if (entry.isFile() && /\.(md|txt|yaml|yml|json)$/i.test(entry.name)) {
        try {
          const content = await fs.promises.readFile(fullPath, "utf-8");
          results.push({
            path: path.relative(this.workspaceDir, fullPath),
            content,
            source,
          });
        } catch {
          // Skip unreadable files
        }
      }
    }

    return results;
  }
}

/**
 * Close all cached managers.
 */
export async function closeAllManagers(): Promise<void> {
  for (const manager of MANAGER_CACHE.values()) {
    await manager.close();
  }
  MANAGER_CACHE.clear();
}
