-- Migration 010: Phase 5 Advanced PQC, FHE & ZKP Upgrade
-- Adds quantum-safe, homomorphic and zero-knowledge memory attributes.

-- Column for storing CKKS-encrypted Hilbert embedding vector (stored as JSON string of encrypted integers)
ALTER TABLE memories ADD COLUMN encrypted_vector TEXT;

-- Column for storing Plonky3/KZG public ZKP commitment (stored as a stringified large prime field integer)
ALTER TABLE memories ADD COLUMN zk_commitment TEXT;
