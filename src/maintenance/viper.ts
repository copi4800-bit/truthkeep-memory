import fs from "node:fs";
import path from "node:path";
import type { Database } from "better-sqlite3";
import type { AegisConfig } from "../core/models.js";

export class Viper {
  constructor(private db: Database, private workspaceDir: string, private config: AegisConfig) {}

  /**
   * Chạy toàn bộ quy trình "Lột xác" của Viper.
   */
  async shedSkin(): Promise<void> {
    console.log("🐍 Viper: Bắt đầu quá trình lột xác (Shedding skin)...");
    
    // 1. Xoay vòng bản sao lưu (Backup Rotation)
    const exportsDir = path.join(this.workspaceDir, "exports");
    if (fs.existsSync(exportsDir)) {
      this.rotateBackups(exportsDir);
    }

    // 2. Thực thi Hard Caps cho Interaction States
    this.enforceInteractionStateCaps();

    // 3. Kiểm soát dung lượng file Capture
    this.compactCaptureFiles();
    
    console.log("🐍 Viper: Lột xác hoàn tất.");
  }

  /**
   * Xoay vòng bản sao lưu theo quy tắc 7 ngày / 4 tuần / 3 tháng.
   */
  private rotateBackups(dir: string): void {
    const files = fs.readdirSync(dir)
      .filter(f => f.startsWith("aegis-snapshot-") || f.startsWith("aegis-export-"))
      .map(f => ({ name: f, path: path.join(dir, f), mtime: fs.statSync(path.join(dir, f)).mtime }));

    if (files.length === 0) return;

    // Sắp xếp theo thời gian mới nhất trước
    files.sort((a, b) => b.mtime.getTime() - a.mtime.getTime());

    const keepDaily = this.config.keepDaily || 7;
    const keepWeekly = this.config.keepWeekly || 4;
    const keepMonthly = this.config.keepMonthly || 3;

    // Một thuật toán đơn giản: Giữ lại X bản mới nhất. 
    // Trong tương lai có thể nâng cấp lên phân loại theo ngày/tuần/tháng chính xác hơn.
    const totalToKeep = keepDaily; // Hiện tại giữ theo số ngày cấu hình
    
    if (files.length > totalToKeep) {
      const toDelete = files.slice(totalToKeep);
      console.log(`🐍 Viper: Xóa ${toDelete.length} bản backup cũ...`);
      for (const file of toDelete) {
        try {
          fs.unlinkSync(file.path);
        } catch (err) {
          console.error(`Lỗi khi xóa backup ${file.name}:`, err);
        }
      }
    }
  }

  /**
   * Giới hạn số lượng Interaction States cho mỗi session (mặc định 10).
   */
  private enforceInteractionStateCaps(): void {
    const maxStates = this.config.maxInteractionStatesPerSession || 10;
    
    console.log(`🐍 Viper: Đang giới hạn Interaction States (Max: ${maxStates})...`);
    
    // Tìm các session có nhiều hơn maxStates bản ghi
    const sessions = this.db.prepare("SELECT DISTINCT session_id FROM interaction_states").all() as any[];
    
    for (const session of sessions) {
      this.db.prepare(`
        DELETE FROM interaction_states
        WHERE id IN (
          SELECT id FROM interaction_states
          WHERE session_id = ?
          ORDER BY last_updated_at DESC
          LIMIT -1 OFFSET ?
        )
      `).run(session.session_id, maxStates);
    }
  }

  /**
   * Nén hoặc cắt bớt các file capture nếu quá dung lượng cho phép.
   */
  private compactCaptureFiles(): void {
    const memoryDir = path.join(this.workspaceDir, "memory");
    const captureFile = path.join(memoryDir, "aegis-session-capture.md");
    const maxBytes = this.config.maxScratchCaptureBytes || (1024 * 1024); // 1MB

    if (fs.existsSync(captureFile)) {
      const stats = fs.statSync(captureFile);
      if (stats.size > maxBytes) {
        console.log(`🐍 Viper: File capture quá lớn (${(stats.size / 1024 / 1024).toFixed(2)} MB). Đang cắt bớt...`);
        
        // Giữ lại 20% dung lượng cuối cùng của file (những gì mới nhất)
        const content = fs.readFileSync(captureFile, "utf-8");
        const lines = content.split("\n");
        const keepLines = lines.slice(Math.floor(lines.length * 0.8));
        fs.writeFileSync(captureFile, keepLines.join("\n"), "utf-8");
      }
    }
  }
}
