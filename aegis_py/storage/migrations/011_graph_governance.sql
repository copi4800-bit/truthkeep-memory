-- Migration 011: Graph Governance Upgrade
-- Xây dựng bảng graph_adjustment_audit để lưu nhật ký lan truyền hiệu chỉnh tri thức

CREATE TABLE IF NOT EXISTS graph_adjustment_audit (
    id TEXT PRIMARY KEY,
    source_memory_id TEXT NOT NULL,
    target_memory_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    reason TEXT,
    old_confidence REAL NOT NULL,
    new_confidence REAL NOT NULL,
    delta REAL NOT NULL,
    depth INTEGER NOT NULL,
    link_weight REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(source_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    FOREIGN KEY(target_memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_graph_audit_source ON graph_adjustment_audit(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_graph_audit_target ON graph_adjustment_audit(target_memory_id);
CREATE INDEX IF NOT EXISTS idx_graph_audit_created ON graph_adjustment_audit(created_at);
