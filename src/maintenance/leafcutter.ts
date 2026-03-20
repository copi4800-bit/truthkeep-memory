import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import crypto from "node:crypto";
import { promisify } from "node:util";
import type { Database } from "better-sqlite3";
import type { AegisConfig } from "../core/models.js";

const gzip = promisify(zlib.gzip);

export class LeafcutterAnt {
  constructor(private db: Database, private workspaceDir: string, private config: AegisConfig) {}

  /**
   * Chạy quy trình thanh trừng rác và lưu trữ lạnh.
   */
  async cleanAndArchive(): Promise<{ archivedEvents: number; archiveFile?: string }> {
    console.log("🐜 Leafcutter Ant: Bắt đầu thu gom rác (Cleaning & Archiving)...");
    
    if (this.config.archiveEnabled === false) {
      console.log("🐜 Leafcutter Ant: Tính năng Archive đang tắt.");
      return { archivedEvents: 0 };
    }

    const archiveResult = await this.archiveOldEvents();
    
    console.log(`🐜 Leafcutter Ant: Thu gom hoàn tất. Đã lưu trữ ${archiveResult.archivedEvents} sự kiện.`);
    return archiveResult;
  }

  /**
   * Di chuyển các event cũ sang file nén.
   */
  private async archiveOldEvents(): Promise<{ archivedEvents: number; archiveFile?: string }> {
    const days = this.config.archiveAfterDays || 90;
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();

    // 1. Tìm các event cần archive
    const events = this.db.prepare(`
      SELECT * FROM memory_events 
      WHERE created_at < ? 
      ORDER BY created_at ASC
    `).all(cutoff) as any[];

    if (events.length === 0) {
      return { archivedEvents: 0 };
    }

    // 2. Chuẩn bị file
    const archiveDir = path.join(this.workspaceDir, this.config.archiveDir || "archives", "events");
    if (!fs.existsSync(archiveDir)) {
      fs.mkdirSync(archiveDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const fileName = `events-${timestamp}.jsonl.gz`;
    const filePath = path.join(archiveDir, fileName);

    // 3. Chuyển đổi sang JSONL và nén Gzip
    const jsonl = events.map(e => JSON.stringify(e)).join("\n");
    const compressed = await gzip(jsonl);

    // 4. Ghi file
    fs.writeFileSync(filePath, compressed);

    // 5. Ghi log archive vào DB
    const fromTs = events[0].created_at;
    const toTs = events[events.length - 1].created_at;
    const archiveId = crypto.randomUUID();

    this.db.prepare(`
      INSERT INTO archive_log (id, archive_kind, file_path, row_count, compressed_bytes, from_timestamp, to_timestamp, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    `).run(archiveId, "events", fileName, events.length, compressed.length, fromTs, toTs);

    // 6. Xóa dữ liệu cũ trong DB (CHỈ sau khi đã ghi file thành công)
    const eventIds = events.map(e => e.id);
    const batchSize = 500;
    for (let i = 0; i < eventIds.length; i += batchSize) {
      const batch = eventIds.slice(i, i + batchSize);
      const placeholders = batch.map(() => "?").join(",");
      this.db.prepare(`DELETE FROM memory_events WHERE id IN (${placeholders})`).run(...batch);
    }

    // 7. Ghi nhận sự kiện Archive hoàn tất
    this.db.prepare(`
      INSERT INTO memory_events (id, event_type, payload_json, created_at)
      VALUES (?, 'archive_completed', ?, datetime('now'))
    `).run(crypto.randomUUID(), JSON.stringify({ archiveId, fileName, count: events.length }));

    return { 
      archivedEvents: events.length, 
      archiveFile: fileName 
    };
  }
}
