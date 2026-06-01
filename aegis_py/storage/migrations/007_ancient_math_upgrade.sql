-- Migration: 007_ancient_math_upgrade.sql
-- Description: Bổ sung các cột trạng thái Kinh Dịch và chữ ký số Lạc Thư cho memories.

ALTER TABLE memories ADD COLUMN iching_state INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN luoshu_checksum REAL DEFAULT 0.0;

CREATE INDEX IF NOT EXISTS idx_memories_iching ON memories(iching_state);
