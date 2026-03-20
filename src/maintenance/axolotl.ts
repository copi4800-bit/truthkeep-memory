import type { Database } from "better-sqlite3";
import type { AegisConfig } from "../core/models.js";

export class Axolotl {
  constructor(private db: Database, private config: AegisConfig) {}

  /**
   * Chặt đứt các nhánh dữ liệu phái sinh cũ để giải phóng không gian.
   */
  async pruneDerivedData(): Promise<number> {
    console.log("🦎 Axolotl: Đang chặt đứt dữ liệu phái sinh cũ (Pruning derived data)...");
    
    // Xóa các quan hệ phái sinh (derived_relations) có độ tin cậy thấp hoặc quá sâu
    const result = this.db.prepare(`
      DELETE FROM derived_relations 
      WHERE confidence < 0.3 OR derivation_depth > 3
    `).run();

    // Reset activation scores về 0 cho các node không được truy cập lâu ngày
    this.db.prepare(`
      UPDATE memory_nodes 
      SET activation_score = 0 
      WHERE last_access_at < date('now', '-30 days')
    `).run();

    console.log(`🦎 Axolotl: Đã dọn dẹp ${result.changes} quan hệ phái sinh.`);
    return result.changes;
  }

  /**
   * Tái sinh (Mọc lại) dữ liệu phái sinh từ các node quan trọng.
   */
  async regenerate(): Promise<{ createdRelations: number }> {
    console.log("🦎 Axolotl: Bắt đầu quá trình tái sinh tri thức (Regenerating)...");
    
    // Giả lập logic mọc lại: Quét các node "crystallized" và tạo lại các cạnh (edges) 
    // dựa trên subject trùng lặp nếu chúng chưa có liên kết.
    
    const stmt = this.db.prepare(`
      INSERT INTO memory_edges (id, src_node_id, dst_node_id, edge_type, weight, confidence, created_at, updated_at)
      SELECT 
        lower(hex(randomblob(16))), 
        a.id, 
        b.id, 
        'auto_link', 
        0.5, 
        0.8, 
        datetime('now'), 
        datetime('now')
      FROM memory_nodes a
      JOIN memory_nodes b ON a.canonical_subject = b.canonical_subject
      WHERE a.id < b.id 
        AND a.memory_state = 'crystallized'
        AND NOT EXISTS (
          SELECT 1 FROM memory_edges 
          WHERE (src_node_id = a.id AND dst_node_id = b.id)
             OR (src_node_id = b.id AND dst_node_id = a.id)
        )
      LIMIT 100
    `);

    const result = stmt.run();
    
    console.log(`🦎 Axolotl: Tái sinh thành công ${result.changes} liên kết tri thức mới.`);
    return { createdRelations: result.changes };
  }
}
