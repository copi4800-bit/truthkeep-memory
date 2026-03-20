import type Database from "better-sqlite3";

/**
 * Get current schema version from the database.
 * Returns 0 if schema_version table doesn't exist yet.
 */
export function getSchemaVersion(db: Database.Database): number {
  try {
    const row = db.prepare(
      "SELECT MAX(version) as version FROM schema_version",
    ).get() as { version: number | null } | undefined;
    return row?.version ?? 0;
  } catch {
    return 0;
  }
}

/**
 * Record a schema version migration.
 */
function recordVersion(
  db: Database.Database,
  version: number,
  description: string,
): void {
  db.prepare(
    "INSERT INTO schema_version (version, applied_at, description) VALUES (?, datetime('now'), ?)",
  ).run(version, description);
}

/**
 * Run all pending migrations sequentially.
 * Each migration is idempotent and wrapped in a transaction.
 */
export function runMigrations(db: Database.Database): void {
  const current = getSchemaVersion(db);

  const migrations: Array<{
    version: number;
    description: string;
    up: (db: Database.Database) => void;
  }> = [
    // v1 is the initial schema — created by schema.sql
    // Future migrations go here:
    //
    // {
    //   version: 2,
    //   description: "Add new_column to memory_nodes",
    //   up: (db) => {
    //     db.exec("ALTER TABLE memory_nodes ADD COLUMN new_column TEXT");
    //   },
    // },
  ];

  for (const migration of migrations) {
    if (migration.version <= current) continue;

    const run = db.transaction(() => {
      migration.up(db);
      recordVersion(db, migration.version, migration.description);
    });

    run();
  }
}

/**
 * Migrate data from OpenClaw builtin memory.db to Aegis v3.
 * Returns the number of nodes migrated.
 */
export function migrateFromBuiltin(
  aegisDb: Database.Database,
  builtinDbPath: string,
): number {
  // Attach the builtin database
  aegisDb.exec(`ATTACH DATABASE '${builtinDbPath}' AS builtin`);

  let count = 0;

  try {
    // Check if builtin has chunks table
    const hasChunks = aegisDb.prepare(
      "SELECT name FROM builtin.sqlite_master WHERE type='table' AND name='chunks'",
    ).get();

    if (!hasChunks) return 0;

    // Read all chunks from builtin
    const chunks = aegisDb.prepare(`
      SELECT id, path, start_line, end_line, text, source, updated_at
      FROM builtin.chunks
      WHERE text IS NOT NULL AND length(text) > 0
    `).all() as Array<{
      id: string;
      path: string;
      start_line: number;
      end_line: number;
      text: string;
      source: string;
      updated_at: string;
    }>;

    const now = new Date().toISOString();

    const insertNode = aegisDb.prepare(`
      INSERT OR IGNORE INTO memory_nodes (
        id, memory_type, content, canonical_subject, scope,
        status, importance, salience, memory_state,
        created_at, updated_at, first_seen_at,
        source_path, source_start_line, source_end_line
      ) VALUES (
        ?, 'semantic_fact', ?, NULL, ?,
        'active', 0.3, 0.3, 'stable',
        ?, ?, ?,
        ?, ?, ?
      )
    `);

    const migrate = aegisDb.transaction(() => {
      for (const chunk of chunks) {
        const scope = chunk.source === "sessions" ? "session" : "user";
        insertNode.run(
          chunk.id,
          chunk.text,
          scope,
          chunk.updated_at || now,
          chunk.updated_at || now,
          chunk.updated_at || now,
          chunk.path,
          chunk.start_line,
          chunk.end_line,
        );
        count++;
      }
    });

    migrate();
  } finally {
    aegisDb.exec("DETACH DATABASE builtin");
  }

  return count;
}
