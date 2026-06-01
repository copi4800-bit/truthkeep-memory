-- Migration 008: Nâng cấp Toán học Hiện đại Phase 2
-- Thêm cột Erdős Grid Cell ID và Poincaré TDA Signature
-- Hilbert vectors được lưu trong bảng memory_vectors sẵn có

ALTER TABLE memories ADD COLUMN erdos_cell_id INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN tda_signature TEXT;

CREATE INDEX IF NOT EXISTS idx_erdos_cell ON memories(erdos_cell_id);
