"""Hầm bảo mật Ký ức — Mã hóa/giải mã transparent cho Memory.

Write: plaintext → Euler cipher → encrypted_content + SHA-256 seal
Read:  encrypted_content → CRT fast decrypt → plaintext + verify seal
"""
from __future__ import annotations

from typing import Any, Optional

from .crypto_math import (
    EulerFermatCipher,
    compute_content_seal,
    verify_content_seal,
)
from .key_manager import KeyManager

__all__ = ['MemoryVault']


class MemoryVault:
    """Hầm bảo mật ký ức — Transparent encryption layer.

    Quy trình:
    1. WRITE: content → EulerFermat encrypt → hex → lưu encrypted_content
    2. READ:  encrypted_content → CRT fast decrypt → content → verify seal
    3. VERIFY: SHA-256(content) == content_seal → integrity OK
    """

    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager

    def seal_memory(
        self,
        content: str,
        scope_type: str,
        scope_id: str,
    ) -> dict[str, str]:
        """Mã hóa nội dung ký ức.

        Luồng:
        1. Lấy/tạo RSA key cho scope (Euclid sinh khóa)
        2. Euler cipher: C = M^e mod n (encrypt content)
        3. SHA-256 seal: hash(content) (integrity proof)

        Returns:
            {
                "encrypted_content": hex string,
                "key_id": key ID,
                "seal_hash": SHA-256 hex
            }
        """
        key_id, bundle = self.key_manager.get_or_create_key(scope_type, scope_id)

        # Euler/Fermat: Mã hóa content
        content_bytes = content.encode("utf-8")
        encrypted_hex = EulerFermatCipher.encrypt_bytes(
            content_bytes, bundle.e, bundle.n
        )

        # SHA-256: Integrity seal
        seal_hash = compute_content_seal(content)

        return {
            "encrypted_content": encrypted_hex,
            "key_id": key_id,
            "seal_hash": seal_hash,
        }

    def unseal_memory(self, encrypted_hex: str, key_id: str) -> Optional[str]:
        """Giải mã ký ức — dùng CRT fast path (4x nhanh hơn).

        Luồng:
        1. Tải khóa RSA bằng key_id
        2. CRT decrypt: xẻ phép tính → 4x faster
        3. Decode UTF-8 → plaintext

        Returns:
            Plaintext string, hoặc None nếu key không tìm thấy
        """
        bundle = self.key_manager.load_key(key_id)
        if bundle is None:
            return None

        # CRT fast path: Số dư Trung Hoa tăng tốc 4x
        content_bytes = EulerFermatCipher.decrypt_bytes(
            encrypted_hex, bundle.d, bundle.n, p=bundle.p, q=bundle.q
        )

        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"Decrypted content is not valid UTF-8 (key_id={key_id!r}). "
                f"Possible key mismatch or data corruption. "
                f"Raw hex: {content_bytes.hex()[:64]}..."
            ) from exc

    @staticmethod
    def verify_seal(content: str, seal_hash: str) -> bool:
        """Xác minh ký ức chưa bị can thiệp.

        So sánh SHA-256(content) với seal đã lưu.
        Nếu ai sửa content trong DB → seal không khớp → phát hiện tampering.
        """
        return verify_content_seal(content, seal_hash)
