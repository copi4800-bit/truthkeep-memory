"""aegis_py.security.config — Cryptographic & Privacy Mode Configuration.

Defines the 3 distinct security modes (demo, local, hardened) and manages
the active cryptographic key size, algorithm configurations, and keystore backends.
"""

import os
from typing import Literal

SecurityMode = Literal["demo", "local", "hardened"]

# Chế độ hoạt động bảo mật (mặc định là 'local', có thể ghi đè qua biến môi trường TK_SECURITY_MODE)
ACTIVE_SECURITY_MODE: SecurityMode = os.getenv("TK_SECURITY_MODE", "local").lower() # type: ignore

if ACTIVE_SECURITY_MODE not in ("demo", "local", "hardened"):
    ACTIVE_SECURITY_MODE = "local"

# Chế độ bảo mật nghiêm ngặt quyền riêng tư (mã hóa cứng SQLite, chặn FTS5 plaintext, redacted logs)
ACTIVE_PRIVACY_MODE: str = os.getenv("TK_PRIVACY_MODE", "").lower()
STRICT_PRIVACY_ACTIVE: bool = (ACTIVE_PRIVACY_MODE == "strict") or (ACTIVE_SECURITY_MODE == "hardened")

class SecurityConfig:
    """Security environment configuration based on active mode."""

    @staticmethod
    def get_rsa_bit_size() -> int:
        """Returns RSA key bit size based on active security level."""
        if ACTIVE_SECURITY_MODE == "demo":
            return 512  # Fast key generation for test/embed
        elif ACTIVE_SECURITY_MODE == "local":
            return 1024 # Standard local personal security
        else:
            return 2048 # High hardened security

    @staticmethod
    def use_cryptographically_secure_prng() -> bool:
        """Returns True if cryptographically secure secrets module must be used."""
        return ACTIVE_SECURITY_MODE in ("local", "hardened") or STRICT_PRIVACY_ACTIVE

    @staticmethod
    def enforce_app_level_encryption() -> bool:
        """Returns True if memory contents must be encrypted at rest in SQLite."""
        return STRICT_PRIVACY_ACTIVE

    @staticmethod
    def is_simulator_enabled() -> bool:
        """Returns True if cryptographic simulators (FHE, ZKP, PQC) are used."""
        return ACTIVE_SECURITY_MODE in ("demo", "local")

    @staticmethod
    def strict_privacy_enabled() -> bool:
        """Returns True if no plaintext indices are allowed to be persisted."""
        return STRICT_PRIVACY_ACTIVE

def get_security_status() -> dict[str, object]:
    """Returns status dictionary of the active security environment."""
    return {
        "active_mode": ACTIVE_SECURITY_MODE,
        "privacy_mode": "strict" if STRICT_PRIVACY_ACTIVE else "standard",
        "rsa_bit_size": SecurityConfig.get_rsa_bit_size(),
        "secure_prng": SecurityConfig.use_cryptographically_secure_prng(),
        "app_level_encryption": SecurityConfig.enforce_app_level_encryption(),
        "strict_privacy": SecurityConfig.strict_privacy_enabled(),
        "simulators_active": SecurityConfig.is_simulator_enabled(),
    }


if ACTIVE_SECURITY_MODE == "hardened":
    import warnings
    warnings.warn(
        "WARNING: hardened mode is currently an architecture scaffold, not audited production security.",
        RuntimeWarning,
        stacklevel=2
    )
