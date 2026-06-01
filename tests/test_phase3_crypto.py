"""
TruthKeep Memory — Phase 3 Crypto Test Vectors
================================================
Tests for:
  - AES-256-GCM encryption/decryption (aes_gcm.py)
  - HMAC-SHA256 signed audit log (signed_audit.py)
  - Dafny crypto_invariants.dfy properties

Each test verifies a specific security property proven (or assumed)
in the Dafny specification.
"""
from __future__ import annotations

import json
import os
import sqlite3

import pytest


# ══════════════════════════════════════════════════════════════════════════
# AES-GCM TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestAESGCMEngine:
    """Tests for AES-256-GCM encryption engine."""

    def _make_key(self) -> bytes:
        return os.urandom(32)

    # ── Encrypt/Decrypt Roundtrip ──

    def test_roundtrip_basic(self):
        """Encrypt then decrypt recovers original plaintext."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        plaintext = b"Hello TruthKeep Memory!"
        cipherdata = AESGCMEngine.encrypt(plaintext, key)
        decrypted = AESGCMEngine.decrypt(cipherdata, key)
        assert decrypted == plaintext

    def test_roundtrip_empty(self):
        """Empty plaintext roundtrips correctly."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        cipherdata = AESGCMEngine.encrypt(b"", key)
        assert AESGCMEngine.decrypt(cipherdata, key) == b""

    def test_roundtrip_unicode(self):
        """Unicode content (Vietnamese) roundtrips correctly."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        text = "Xin chào TruthKeep! Đây là ký ức tiếng Việt 🧠"
        cipherdata = AESGCMEngine.encrypt(text.encode("utf-8"), key)
        decrypted = AESGCMEngine.decrypt(cipherdata, key)
        assert decrypted.decode("utf-8") == text

    def test_roundtrip_large(self):
        """Large content (10KB) roundtrips correctly."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        plaintext = os.urandom(10240)
        cipherdata = AESGCMEngine.encrypt(plaintext, key)
        assert AESGCMEngine.decrypt(cipherdata, key) == plaintext

    def test_roundtrip_string(self):
        """String convenience methods work correctly."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        text = "Memory: User prefers dark mode"
        encrypted = AESGCMEngine.encrypt_string(text, key)
        assert isinstance(encrypted, str)  # base64 string
        assert AESGCMEngine.decrypt_string(encrypted, key) == text

    # ── Output Structure ──

    def test_output_size(self):
        """Output = nonce(12) + tag(16) + ciphertext = plaintext + 28."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        plaintext = b"test content"
        cipherdata = AESGCMEngine.encrypt(plaintext, key)
        assert len(cipherdata) == len(plaintext) + 28

    def test_output_size_empty(self):
        """Empty plaintext → 28 bytes output (nonce + tag only)."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        cipherdata = AESGCMEngine.encrypt(b"", key)
        assert len(cipherdata) == 28

    def test_unique_nonce(self):
        """Each encryption produces unique nonce (different ciphertext)."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        plaintext = b"same content"
        ct1 = AESGCMEngine.encrypt(plaintext, key)
        ct2 = AESGCMEngine.encrypt(plaintext, key)
        assert ct1 != ct2  # Different nonces → different ciphertext

    # ── Tamper Detection ──

    def test_tamper_ciphertext(self):
        """Modifying ciphertext → authentication failure."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        cipherdata = bytearray(AESGCMEngine.encrypt(b"secret data", key))
        # Flip a byte in the ciphertext portion (after nonce+tag)
        if len(cipherdata) > 29:
            cipherdata[29] ^= 0xFF
        with pytest.raises(ValueError, match="authentication failed"):
            AESGCMEngine.decrypt(bytes(cipherdata), key)

    def test_tamper_tag(self):
        """Modifying tag → authentication failure."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        cipherdata = bytearray(AESGCMEngine.encrypt(b"secret data", key))
        cipherdata[15] ^= 0xFF  # Flip byte in tag (bytes 12-27)
        with pytest.raises(ValueError, match="authentication failed"):
            AESGCMEngine.decrypt(bytes(cipherdata), key)

    def test_wrong_key(self):
        """Decrypting with wrong key → authentication failure."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key1 = self._make_key()
        key2 = self._make_key()
        cipherdata = AESGCMEngine.encrypt(b"secret", key1)
        with pytest.raises(ValueError, match="authentication failed"):
            AESGCMEngine.decrypt(cipherdata, key2)

    # ── AAD (Additional Authenticated Data) ──

    def test_aad_roundtrip(self):
        """AAD must match for successful decryption."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        aad = b"memory_id:abc123"
        plaintext = b"secret content"
        cipherdata = AESGCMEngine.encrypt(plaintext, key, aad=aad)
        assert AESGCMEngine.decrypt(cipherdata, key, aad=aad) == plaintext

    def test_aad_mismatch(self):
        """Wrong AAD → authentication failure."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        key = self._make_key()
        cipherdata = AESGCMEngine.encrypt(b"secret", key, aad=b"correct_aad")
        with pytest.raises(ValueError, match="authentication failed"):
            AESGCMEngine.decrypt(cipherdata, key, aad=b"wrong_aad")

    # ── Key Validation ──

    def test_invalid_key_size(self):
        """Non-32-byte key → ValueError."""
        from aegis_py.security.aes_gcm import AESGCMEngine
        with pytest.raises(ValueError, match="32 bytes"):
            AESGCMEngine.encrypt(b"test", b"short-key")


# ══════════════════════════════════════════════════════════════════════════
# KEY DERIVATION TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestKeyDerivation:
    """Tests for PBKDF2-HMAC-SHA256 key derivation."""

    def test_derived_key_size(self):
        """Derived key is always 32 bytes (AES-256)."""
        from aegis_py.security.aes_gcm import KeyDerivation
        key, salt = KeyDerivation.derive_key("my-passphrase")
        assert len(key) == 32

    def test_deterministic_with_same_salt(self):
        """Same passphrase + salt → same key."""
        from aegis_py.security.aes_gcm import KeyDerivation
        salt = os.urandom(16)
        key1, _ = KeyDerivation.derive_key("test-pass", salt=salt)
        key2, _ = KeyDerivation.derive_key("test-pass", salt=salt)
        assert key1 == key2

    def test_different_salt_different_key(self):
        """Different salt → different key (key separation)."""
        from aegis_py.security.aes_gcm import KeyDerivation
        key1, _ = KeyDerivation.derive_key("same-pass", salt=os.urandom(16))
        key2, _ = KeyDerivation.derive_key("same-pass", salt=os.urandom(16))
        assert key1 != key2

    def test_different_passphrase_different_key(self):
        """Different passphrase → different key."""
        from aegis_py.security.aes_gcm import KeyDerivation
        salt = os.urandom(16)
        key1, _ = KeyDerivation.derive_key("pass-A", salt=salt)
        key2, _ = KeyDerivation.derive_key("pass-B", salt=salt)
        assert key1 != key2

    def test_derive_bundle(self):
        """SymmetricKeyBundle is correctly constructed."""
        from aegis_py.security.aes_gcm import KeyDerivation
        bundle = KeyDerivation.derive_bundle("my-pass", "key-001")
        assert bundle.key_id == "key-001"
        assert len(bundle.key) == 32
        assert len(bundle.salt) == 16


# ══════════════════════════════════════════════════════════════════════════
# SIGNED AUDIT LOG TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestSignedAuditLog:
    """Tests for HMAC-SHA256 signed audit log with hash chain."""

    @pytest.fixture
    def audit_log(self, tmp_path):
        """Create a fresh signed audit log with in-memory DB."""
        from aegis_py.security.signed_audit import SignedAuditLog
        db_path = str(tmp_path / "test_audit.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        signing_key = os.urandom(32)
        log = SignedAuditLog(conn, signing_key=signing_key)
        return log

    # ── Append and Retrieve ──

    def test_append_single_event(self, audit_log):
        """Appending an event returns a valid AuditEntry."""
        entry = audit_log.append_event(
            event_kind="test_event",
            actor="user",
            scope_type="project",
            scope_id="demo",
            payload={"action": "test"},
        )
        assert entry.entry_id.startswith("audit_")
        assert entry.event_kind == "test_event"
        assert entry.actor == "user"
        assert len(entry.signature) == 64  # SHA-256 hex

    def test_first_entry_genesis_hash(self, audit_log):
        """First entry has prev_hash == GENESIS_HASH (64 zeros)."""
        from aegis_py.security.signed_audit import GENESIS_HASH
        entry = audit_log.append_event(
            event_kind="first",
            scope_type="project",
            scope_id="demo",
        )
        assert entry.prev_hash == GENESIS_HASH

    def test_chain_length(self, audit_log):
        """Chain length increments correctly."""
        for i in range(5):
            audit_log.append_event(
                event_kind=f"event_{i}",
                scope_type="project",
                scope_id="demo",
            )
        assert audit_log.get_chain_length("project", "demo") == 5

    def test_list_events(self, audit_log):
        """Listed events are in reverse chronological order."""
        for i in range(3):
            audit_log.append_event(
                event_kind=f"event_{i}",
                scope_type="project",
                scope_id="demo",
            )
        events = audit_log.list_events("project", "demo")
        assert len(events) == 3
        assert events[0].event_kind == "event_2"  # Newest first

    # ── Hash Chain Verification ──

    def test_verify_empty_chain(self, audit_log):
        """Empty chain is always valid."""
        result = audit_log.verify_chain("project", "empty")
        assert result.valid is True
        assert result.total_entries == 0

    def test_verify_single_entry_chain(self, audit_log):
        """Single-entry chain is valid."""
        audit_log.append_event(
            event_kind="single",
            scope_type="project",
            scope_id="demo",
        )
        result = audit_log.verify_chain("project", "demo")
        assert result.valid is True
        assert result.total_entries == 1
        assert result.verified_entries == 1

    def test_verify_multi_entry_chain(self, audit_log):
        """Multi-entry chain maintains hash links."""
        for i in range(10):
            audit_log.append_event(
                event_kind=f"event_{i}",
                scope_type="project",
                scope_id="demo",
                payload={"index": i},
            )
        result = audit_log.verify_chain("project", "demo")
        assert result.valid is True
        assert result.total_entries == 10
        assert result.verified_entries == 10

    # ── Tamper Detection ──

    def test_tamper_signature_detected(self, audit_log):
        """Modifying signature → chain verification fails."""
        audit_log.append_event(
            event_kind="legit",
            scope_type="project",
            scope_id="tamper_test",
        )
        # Tamper: modify signature in DB
        audit_log.conn.execute(
            "UPDATE signed_audit_log SET signature = 'fake_sig_' || signature "
            "WHERE scope_id = 'tamper_test'"
        )
        audit_log.conn.commit()

        result = audit_log.verify_chain("project", "tamper_test")
        assert result.valid is False
        assert "signature invalid" in result.error.lower() or "HMAC" in result.error

    def test_tamper_payload_detected(self, audit_log):
        """Modifying payload → HMAC verification fails."""
        audit_log.append_event(
            event_kind="original",
            scope_type="project",
            scope_id="payload_test",
            payload={"action": "create"},
        )
        # Tamper: modify payload
        audit_log.conn.execute(
            "UPDATE signed_audit_log SET payload_json = '{\"action\": \"DELETE_ALL\"}' "
            "WHERE scope_id = 'payload_test'"
        )
        audit_log.conn.commit()

        result = audit_log.verify_chain("project", "payload_test")
        assert result.valid is False

    def test_tamper_delete_middle_entry(self, audit_log):
        """Deleting a middle entry → hash chain broken."""
        entries = []
        for i in range(5):
            e = audit_log.append_event(
                event_kind=f"event_{i}",
                scope_type="project",
                scope_id="delete_test",
            )
            entries.append(e)

        # Delete entry #2 (middle)
        audit_log.conn.execute(
            "DELETE FROM signed_audit_log WHERE entry_id = ?",
            (entries[2].entry_id,),
        )
        audit_log.conn.commit()

        result = audit_log.verify_chain("project", "delete_test")
        assert result.valid is False
        assert result.first_broken_at is not None

    # ── Scope Isolation ──

    def test_scope_isolation(self, audit_log):
        """Different scopes have independent chains."""
        audit_log.append_event(
            event_kind="event_a", scope_type="project", scope_id="scope_A",
        )
        audit_log.append_event(
            event_kind="event_b", scope_type="project", scope_id="scope_B",
        )
        assert audit_log.get_chain_length("project", "scope_A") == 1
        assert audit_log.get_chain_length("project", "scope_B") == 1

        # Both chains valid independently
        assert audit_log.verify_chain("project", "scope_A").valid is True
        assert audit_log.verify_chain("project", "scope_B").valid is True


# ══════════════════════════════════════════════════════════════════════════
# CONTENT SEAL TESTS (existing, verify Dafny properties)
# ══════════════════════════════════════════════════════════════════════════

class TestContentSeal:
    """Tests verifying SHA-256 content seal properties."""

    def test_seal_deterministic(self):
        """Same content → same seal (deterministic)."""
        from aegis_py.security.crypto_math import compute_content_seal
        seal1 = compute_content_seal("hello world")
        seal2 = compute_content_seal("hello world")
        assert seal1 == seal2

    def test_seal_collision_resistant(self):
        """Different content → different seal."""
        from aegis_py.security.crypto_math import compute_content_seal
        seal1 = compute_content_seal("content A")
        seal2 = compute_content_seal("content B")
        assert seal1 != seal2

    def test_seal_verify_roundtrip(self):
        """compute → verify roundtrip works."""
        from aegis_py.security.crypto_math import compute_content_seal, verify_content_seal
        content = "important memory"
        seal = compute_content_seal(content)
        assert verify_content_seal(content, seal) is True
        assert verify_content_seal("tampered content", seal) is False

    def test_seal_is_hex_sha256(self):
        """Seal is a 64-character hex string (SHA-256)."""
        from aegis_py.security.crypto_math import compute_content_seal
        seal = compute_content_seal("test")
        assert len(seal) == 64
        assert all(c in "0123456789abcdef" for c in seal)
