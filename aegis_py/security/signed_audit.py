"""HMAC-SHA256 Signed Audit Log cho TruthKeep Memory — Phase 3 Crypto.

Tamper-proof audit log sử dụng hash chain + HMAC signing:

1. Mỗi audit entry có HMAC-SHA256 signature (chống giả mạo)
2. Entries liên kết bằng hash chain: entry[n].prev_hash = SHA256(entry[n-1])
   → Nếu ai xóa/sửa 1 entry giữa chain, toàn bộ chain sau đó sẽ invalid
3. Chain verification: quét từ đầu → cuối, kiểm tra mỗi link
4. Audit log KHÔNG BAO GIỜ xóa entries (append-only)

Maps to:
  - GovernanceRepository.record_governance_event() → thêm HMAC
  - GovernanceRepository.record_memory_state_transition() → thêm HMAC
  - Mới: verify_audit_chain() để kiểm tra toàn vẹn
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..hygiene.transitions import now_iso

__all__ = [
    "SignedAuditLog",
    "AuditEntry",
    "AuditVerificationResult",
]


# ─────────────────────────────────────────────────────────────────────────
# GENESIS HASH — Mốc đầu tiên của chuỗi
# ─────────────────────────────────────────────────────────────────────────

GENESIS_HASH = "0" * 64  # SHA-256 of nothing — đánh dấu entry đầu tiên


@dataclass(frozen=True)
class AuditEntry:
    """Một entry trong signed audit log.

    Fields:
        entry_id: Unique ID (audit_xxxxx)
        event_kind: Loại sự kiện (state_transition, governance, correction, etc.)
        actor: Ai thực hiện (system, user, consolidator, etc.)
        scope_type: Phạm vi (project, global, etc.)
        scope_id: ID phạm vi
        memory_id: ID memory liên quan (nếu có)
        payload: Chi tiết sự kiện (JSON-serializable)
        created_at: ISO timestamp
        prev_hash: SHA-256 hash của entry trước đó (hash chain)
        signature: HMAC-SHA256(signing_key, canonical_content)
    """
    entry_id: str
    event_kind: str
    actor: str
    scope_type: str
    scope_id: str
    memory_id: Optional[str]
    payload: dict[str, Any]
    created_at: str
    prev_hash: str  # Hash chain link
    signature: str  # HMAC-SHA256 signature


@dataclass
class AuditVerificationResult:
    """Kết quả xác minh audit chain.

    valid: True nếu toàn bộ chain intact
    total_entries: Tổng số entries
    verified_entries: Số entries verified OK
    first_broken_at: Index của entry đầu tiên bị lỗi (nếu có)
    error: Mô tả lỗi (nếu có)
    """
    valid: bool
    total_entries: int
    verified_entries: int
    first_broken_at: Optional[int] = None
    error: Optional[str] = None


class SignedAuditLog:
    """HMAC-SHA256 Signed Audit Log với hash chain.

    Bảo mật:
    - HMAC-SHA256 chống giả mạo entry
    - Hash chain chống xóa/chèn entry
    - Append-only: không có API xóa
    - Verification: quét toàn bộ chain bất kỳ lúc nào

    Usage:
        log = SignedAuditLog(conn, signing_key=b"secret-key-32-bytes....")
        log.append_event(event_kind="correction", actor="user", ...)
        result = log.verify_chain(scope_type="project", scope_id="demo")
    """

    TABLE_NAME = "signed_audit_log"

    def __init__(self, conn: Any, signing_key: bytes):
        """
        Args:
            conn: SQLite connection
            signing_key: 32-byte HMAC signing key (nên derive từ master key)
        """
        self.conn = conn
        self.signing_key = signing_key
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Tạo table nếu chưa có."""
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                entry_id     TEXT PRIMARY KEY,
                event_kind   TEXT NOT NULL,
                actor        TEXT NOT NULL DEFAULT 'system',
                scope_type   TEXT NOT NULL,
                scope_id     TEXT NOT NULL,
                memory_id    TEXT,
                payload_json TEXT NOT NULL DEFAULT '{{}}',
                created_at   TEXT NOT NULL,
                prev_hash    TEXT NOT NULL,
                signature    TEXT NOT NULL
            )
        """)
        self.conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_sal_scope
            ON {self.TABLE_NAME} (scope_type, scope_id, created_at)
        """)
        self.conn.commit()

    # ── Core Operations ──────────────────────────────────────────────

    def append_event(
        self,
        *,
        event_kind: str,
        actor: str = "system",
        scope_type: str,
        scope_id: str,
        memory_id: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        """Append một entry mới vào audit log.

        Luồng:
        1. Lấy hash của entry cuối cùng (prev_hash)
        2. Tạo canonical content string
        3. Tính HMAC-SHA256 signature
        4. INSERT vào DB
        5. Return AuditEntry

        Returns:
            AuditEntry đã được sign
        """
        entry_id = f"audit_{uuid.uuid4().hex[:16]}"
        created_at = now_iso()
        payload = payload or {}
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=True)

        # Lấy prev_hash: hash của entry cuối cùng trong scope
        prev_hash = self._get_last_hash(scope_type, scope_id)

        # Canonical content cho HMAC
        canonical = self._canonical_content(
            entry_id=entry_id,
            event_kind=event_kind,
            actor=actor,
            scope_type=scope_type,
            scope_id=scope_id,
            memory_id=memory_id or "",
            payload_json=payload_json,
            created_at=created_at,
            prev_hash=prev_hash,
        )

        # HMAC-SHA256 signature
        signature = hmac.new(
            self.signing_key, canonical.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # INSERT
        self.conn.execute(
            f"""
            INSERT INTO {self.TABLE_NAME}
                (entry_id, event_kind, actor, scope_type, scope_id,
                 memory_id, payload_json, created_at, prev_hash, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id, event_kind, actor, scope_type, scope_id,
                memory_id, payload_json, created_at, prev_hash, signature,
            ),
        )
        self.conn.commit()

        return AuditEntry(
            entry_id=entry_id,
            event_kind=event_kind,
            actor=actor,
            scope_type=scope_type,
            scope_id=scope_id,
            memory_id=memory_id,
            payload=payload,
            created_at=created_at,
            prev_hash=prev_hash,
            signature=signature,
        )

    def verify_chain(
        self,
        scope_type: str,
        scope_id: str,
    ) -> AuditVerificationResult:
        """Verify toàn bộ audit chain cho một scope.

        Kiểm tra:
        1. Entry đầu tiên có prev_hash == GENESIS_HASH
        2. Mỗi entry có prev_hash == SHA256(entry trước)
        3. Mỗi entry có HMAC signature hợp lệ
        4. Không có gap (entry bị xóa)

        Returns:
            AuditVerificationResult
        """
        rows = self.conn.execute(
            f"""
            SELECT entry_id, event_kind, actor, scope_type, scope_id,
                   memory_id, payload_json, created_at, prev_hash, signature
            FROM {self.TABLE_NAME}
            WHERE scope_type = ? AND scope_id = ?
            ORDER BY rowid ASC
            """,
            (scope_type, scope_id),
        ).fetchall()

        if not rows:
            return AuditVerificationResult(
                valid=True, total_entries=0, verified_entries=0
            )

        total = len(rows)
        expected_prev_hash = GENESIS_HASH

        for idx, row in enumerate(rows):
            r = dict(row) if hasattr(row, "keys") else {
                "entry_id": row[0], "event_kind": row[1], "actor": row[2],
                "scope_type": row[3], "scope_id": row[4], "memory_id": row[5],
                "payload_json": row[6], "created_at": row[7],
                "prev_hash": row[8], "signature": row[9],
            }

            # 1. Check prev_hash chain
            if r["prev_hash"] != expected_prev_hash:
                return AuditVerificationResult(
                    valid=False,
                    total_entries=total,
                    verified_entries=idx,
                    first_broken_at=idx,
                    error=f"Hash chain broken at entry {idx}: "
                          f"expected prev_hash={expected_prev_hash[:16]}..., "
                          f"got {r['prev_hash'][:16]}...",
                )

            # 2. Verify HMAC signature
            canonical = self._canonical_content(
                entry_id=r["entry_id"],
                event_kind=r["event_kind"],
                actor=r["actor"],
                scope_type=r["scope_type"],
                scope_id=r["scope_id"],
                memory_id=r["memory_id"] or "",
                payload_json=r["payload_json"],
                created_at=r["created_at"],
                prev_hash=r["prev_hash"],
            )
            expected_sig = hmac.new(
                self.signing_key, canonical.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(r["signature"], expected_sig):
                return AuditVerificationResult(
                    valid=False,
                    total_entries=total,
                    verified_entries=idx,
                    first_broken_at=idx,
                    error=f"HMAC signature invalid at entry {idx} "
                          f"(entry_id={r['entry_id']}). Possible tampering.",
                )

            # 3. Update expected_prev_hash for next entry
            expected_prev_hash = self._hash_entry(r)

        return AuditVerificationResult(
            valid=True, total_entries=total, verified_entries=total
        )

    def list_events(
        self,
        scope_type: str,
        scope_id: str,
        limit: int = 50,
    ) -> list[AuditEntry]:
        """List audit events cho scope (newest first)."""
        rows = self.conn.execute(
            f"""
            SELECT entry_id, event_kind, actor, scope_type, scope_id,
                   memory_id, payload_json, created_at, prev_hash, signature
            FROM {self.TABLE_NAME}
            WHERE scope_type = ? AND scope_id = ?
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (scope_type, scope_id, limit),
        ).fetchall()

        results = []
        for row in rows:
            r = dict(row) if hasattr(row, "keys") else {
                "entry_id": row[0], "event_kind": row[1], "actor": row[2],
                "scope_type": row[3], "scope_id": row[4], "memory_id": row[5],
                "payload_json": row[6], "created_at": row[7],
                "prev_hash": row[8], "signature": row[9],
            }
            try:
                payload = json.loads(r["payload_json"])
            except (json.JSONDecodeError, TypeError):
                payload = {}

            results.append(AuditEntry(
                entry_id=r["entry_id"],
                event_kind=r["event_kind"],
                actor=r["actor"],
                scope_type=r["scope_type"],
                scope_id=r["scope_id"],
                memory_id=r["memory_id"],
                payload=payload,
                created_at=r["created_at"],
                prev_hash=r["prev_hash"],
                signature=r["signature"],
            ))
        return results

    def get_chain_length(self, scope_type: str, scope_id: str) -> int:
        """Return số entries trong chain."""
        row = self.conn.execute(
            f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()
        return row[0] if row else 0

    # ── Internal helpers ─────────────────────────────────────────────

    def _get_last_hash(self, scope_type: str, scope_id: str) -> str:
        """Lấy hash của entry cuối cùng trong scope, hoặc GENESIS_HASH."""
        row = self.conn.execute(
            f"""
            SELECT entry_id, event_kind, actor, scope_type, scope_id,
                   memory_id, payload_json, created_at, prev_hash, signature
            FROM {self.TABLE_NAME}
            WHERE scope_type = ? AND scope_id = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (scope_type, scope_id),
        ).fetchone()

        if not row:
            return GENESIS_HASH

        r = dict(row) if hasattr(row, "keys") else {
            "entry_id": row[0], "event_kind": row[1], "actor": row[2],
            "scope_type": row[3], "scope_id": row[4], "memory_id": row[5],
            "payload_json": row[6], "created_at": row[7],
            "prev_hash": row[8], "signature": row[9],
        }
        return self._hash_entry(r)

    @staticmethod
    def _hash_entry(entry: dict[str, Any]) -> str:
        """SHA-256 hash của toàn bộ entry (dùng cho hash chain link)."""
        content = (
            f"{entry['entry_id']}|{entry['event_kind']}|{entry['actor']}|"
            f"{entry['scope_type']}|{entry['scope_id']}|{entry.get('memory_id', '')}|"
            f"{entry['payload_json']}|{entry['created_at']}|"
            f"{entry['prev_hash']}|{entry['signature']}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_content(
        *,
        entry_id: str,
        event_kind: str,
        actor: str,
        scope_type: str,
        scope_id: str,
        memory_id: str,
        payload_json: str,
        created_at: str,
        prev_hash: str,
    ) -> str:
        """Build canonical string cho HMAC signing.

        Thứ tự cố định, deterministic — đảm bảo cùng content luôn cho
        cùng signature.
        """
        return (
            f"v1|{entry_id}|{event_kind}|{actor}|"
            f"{scope_type}|{scope_id}|{memory_id}|"
            f"{payload_json}|{created_at}|{prev_hash}"
        )
