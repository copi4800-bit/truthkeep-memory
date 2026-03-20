import fs from "node:fs";
import path from "node:path";
import type { Database } from "better-sqlite3";
import type { AegisTelemetry } from "../core/models.js";

export class Honeybee {
  constructor(private db: Database, private workspaceDir: string) {}

  /**
   * Thu thập toàn bộ số liệu Telemetry từ DB và Filesystem.
   */
  async collect(): Promise<AegisTelemetry> {
    const dbPath = path.join(this.workspaceDir, "memory-aegis.db");
    const walPath = `${dbPath}-wal`;

    const dbStats = fs.existsSync(dbPath) ? fs.statSync(dbPath) : { size: 0 };
    const walStats = fs.existsSync(walPath) ? fs.statSync(walPath) : { size: 0 };

    const row = this.db.prepare("SELECT * FROM v_aegis_telemetry").get() as any;

    // Tính toán tốc độ tăng trưởng (Growth Rate)
    // Dựa trên dung lượng DB lưu trong event log hoặc ước tính đơn giản từ timestamp
    const growth24h = this.estimateGrowth(24);
    const growth7d = this.estimateGrowth(24 * 7);

    return {
      db_size_bytes: dbStats.size,
      wal_size_bytes: walStats.size,
      node_count_active: row.node_count_active || 0,
      node_count_archived: row.node_count_archived || 0,
      edge_count: row.edge_count || 0,
      entity_count: row.entity_count || 0,
      event_count: row.event_count || 0,
      dedup_hit_count: row.dedup_hit_count || 0,
      derived_relation_count: row.derived_relation_count || 0,
      interaction_state_count: row.interaction_state_count || 0,
      latest_backup_at: row.latest_backup_at,
      latest_archive_at: row.latest_archive_at,
      growth_24h_bytes: growth24h,
      growth_7d_bytes: growth7d,
    };
  }

  /**
   * Ước tính mức tăng trưởng dựa trên số lượng event được tạo ra.
   * (Phiên bản đơn giản: 1 event ~ 1KB trung bình bao gồm cả node liên quan)
   */
  private estimateGrowth(hours: number): number {
    const since = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
    const row = this.db
      .prepare("SELECT COUNT(*) as count FROM memory_events WHERE created_at > ?")
      .get(since) as any;
    return (row.count || 0) * 1024; // 1KB per event
  }

  /**
   * Định dạng kết quả thành văn bản cho "Vũ điệu Ong mật".
   */
  render(t: AegisTelemetry): string {
    const mb = (bytes: number) => (bytes / (1024 * 1024)).toFixed(2);
    
    return [
      "🐝 **Aegis v3 Honeybee Stats**",
      `• **Dung lượng DB:** ${mb(t.db_size_bytes)} MB (WAL: ${mb(t.wal_size_bytes)} MB)`,
      `• **Nodes (Active/Archive):** ${t.node_count_active} / ${t.node_count_archived}`,
      `• **Quan hệ (Edges):** ${t.edge_count}`,
      `• **Thực thể (Entities):** ${t.entity_count}`,
      `• **Sự kiện (Events):** ${t.event_count}`,
      `• **Dedup Hits (Salmon):** ${t.dedup_hit_count}`,
      `• **Derived Data (Axolotl):** ${t.derived_relation_count}`,
      `• **Tăng trưởng (24h/7d):** +${mb(t.growth_24h_bytes)} MB / +${mb(t.growth_7d_bytes)} MB`,
      "",
      `• **Backup gần nhất:** ${t.latest_backup_at || "N/A"}`,
      `• **Archive gần nhất:** ${t.latest_archive_at || "N/A"}`,
      "",
      "👉 *Dữ liệu được thu thập thời gian thực từ v_aegis_telemetry.*"
    ].join("\n");
  }
}
