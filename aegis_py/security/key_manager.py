"""Quản lý khóa RSA per-scope cho TruthKeep Memory.

Mỗi scope (scope_type + scope_id) có 1 bộ khóa RSA riêng.
Khóa được sinh lazy (lần đầu encrypt) và lưu trong crypto_keys table.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .crypto_math import EuclidKeyForge, RSAKeyBundle

__all__ = ['KeyManager']


class KeyManager:
    """Quản lý khóa mật mã per-scope.

    - Mỗi scope có 1 RSA key bundle riêng
    - Khóa sinh bằng EuclidKeyForge (thuật toán Euclid 300 TCN)
    - Lưu trong SQLite table 'crypto_keys'
    - Lazy generation: khóa chỉ sinh khi lần đầu cần encrypt
    """

    DEFAULT_BIT_SIZE = 2048

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._cache: dict[str, RSAKeyBundle] = {}

    def _scope_key(self, scope_type: str, scope_id: str) -> str:
        """Build a cache key from scope_type and scope_id."""
        return f"{scope_type}:{scope_id}"

    @staticmethod
    def _bundle_from_row(row: Any) -> RSAKeyBundle:
        """Deserialize an RSAKeyBundle from a SQLite row (dict or tuple).

        The row must contain columns: n_hex, e, d_hex, p_hex, q_hex, bit_size.
        For tuple rows the order must match SELECT order above.
        """
        if isinstance(row, dict):
            data = row
        else:
            data = {
                "n_hex": row[0], "e": row[1], "d_hex": row[2],
                "p_hex": row[3], "q_hex": row[4], "bit_size": row[5],
            }
        return RSAKeyBundle(
            n=int(data["n_hex"], 16),
            e=int(data["e"]),
            d=int(data["d_hex"], 16),
            p=int(data["p_hex"], 16),
            q=int(data["q_hex"], 16),
            bit_size=int(data["bit_size"]),
        )

    def get_or_create_key(
        self, scope_type: str, scope_id: str
    ) -> tuple[str, RSAKeyBundle]:
        """Lấy hoặc tạo mới khóa RSA cho scope.

        Returns: (key_id, RSAKeyBundle)
        """
        cache_key = self._scope_key(scope_type, scope_id)

        # Check cache
        if cache_key in self._cache:
            row = self.conn.execute(
                "SELECT key_id FROM crypto_keys WHERE scope_type = ? AND scope_id = ?",
                (scope_type, scope_id),
            ).fetchone()
            if row:
                return row["key_id"] if isinstance(row, dict) else row[0], self._cache[cache_key]

        # Check database
        row = self.conn.execute(
            "SELECT key_id, n_hex, e, d_hex, p_hex, q_hex, bit_size "
            "FROM crypto_keys WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()

        if row:
            key_id_val = row["key_id"] if isinstance(row, dict) else row[0]
            # Slice past key_id column for _bundle_from_row
            if isinstance(row, dict):
                bundle_row = row
            else:
                bundle_row = row[1:]  # skip key_id at index 0
            bundle = self._bundle_from_row(bundle_row)
            self._cache[cache_key] = bundle
            return key_id_val, bundle

        # Generate new key — Euclid mở rộng ở đây!
        bundle = EuclidKeyForge.generate_rsa_params(self.DEFAULT_BIT_SIZE)
        key_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            "INSERT INTO crypto_keys "
            "(key_id, scope_type, scope_id, n_hex, e, d_hex, p_hex, q_hex, bit_size, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                key_id,
                scope_type,
                scope_id,
                hex(bundle.n),
                bundle.e,
                hex(bundle.d),
                hex(bundle.p),
                hex(bundle.q),
                bundle.bit_size,
                now_iso,
            ),
        )
        self.conn.commit()

        self._cache[cache_key] = bundle
        return key_id, bundle

    def load_key(self, key_id: str) -> Optional[RSAKeyBundle]:
        """Tải khóa bằng key_id."""
        row = self.conn.execute(
            "SELECT n_hex, e, d_hex, p_hex, q_hex, bit_size "
            "FROM crypto_keys WHERE key_id = ?",
            (key_id,),
        ).fetchone()

        if not row:
            return None

        return self._bundle_from_row(row)

    def rotate_key(
        self, scope_type: str, scope_id: str
    ) -> tuple[str, RSAKeyBundle]:
        """Xoay khóa — sinh khóa mới thay thế khóa cũ.

        Khóa cũ bị xóa, khóa mới được sinh.
        LƯU Ý: Memories đã encrypt bằng khóa cũ cần re-encrypt.
        """
        # Xóa khóa cũ
        self.conn.execute(
            "DELETE FROM crypto_keys WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        )
        cache_key = self._scope_key(scope_type, scope_id)
        self._cache.pop(cache_key, None)

        # Sinh khóa mới
        return self.get_or_create_key(scope_type, scope_id)
