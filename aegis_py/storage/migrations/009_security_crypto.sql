-- Migration 009: Bảo mật Mật mã Cổ điển (Phase 4)
-- Thuật toán Euclid (300 TCN) + Euler/Fermat (TK 17-18) + CRT (TK 3) + Bayes (1763)

-- Bảng khóa RSA per-scope (sinh bởi EuclidKeyForge)
CREATE TABLE IF NOT EXISTS crypto_keys (
    key_id          TEXT PRIMARY KEY,
    scope_type      TEXT NOT NULL,
    scope_id        TEXT NOT NULL,
    n_hex           TEXT NOT NULL,
    e               INTEGER NOT NULL,
    d_hex           TEXT NOT NULL,
    p_hex           TEXT NOT NULL,
    q_hex           TEXT NOT NULL,
    bit_size        INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    rotated_at      TEXT,
    UNIQUE (scope_type, scope_id)
);

-- Cột mã hóa trên memories table
ALTER TABLE memories ADD COLUMN encrypted_content TEXT;
ALTER TABLE memories ADD COLUMN encryption_key_id TEXT;
ALTER TABLE memories ADD COLUMN content_seal TEXT;

-- Log truy vấn cho Bayesian DP (chống Membership Inference Attack)
CREATE TABLE IF NOT EXISTS privacy_query_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type      TEXT NOT NULL,
    scope_id        TEXT NOT NULL,
    query_hash      TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    leakage_risk    REAL DEFAULT 0.0
);
