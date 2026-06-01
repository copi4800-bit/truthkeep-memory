"""aegis_py.security — Classical Cryptography & Differential Privacy.

Phase 4 of TruthKeep Memory's mathematical upgrade. Implements 4 cryptographic
systems derived from ancient and classical mathematics:

- EuclidKeyForge: Extended GCD → modular inverse → RSA key generation (300 BCE)
- EulerFermatCipher: Modular exponentiation encryption/decryption (17th-18th c.)
- ChineseRemainderAccelerator: CRT-based 4x faster RSA decryption (3rd c.)
- BayesianPrivacyGuard: Differential privacy with Laplace noise (1763)

Also provides:
- KeyManager: Per-scope RSA key lifecycle management
- MemoryVault: Transparent encryption/decryption layer for memories
- DifferentialPrivacyShield: Query-level privacy protection with probing detection
"""

from .crypto_math import (
    RSAKeyBundle,
    MillerRabinPrimality,
    EuclidKeyForge,
    EulerFermatCipher,
    ChineseRemainderAccelerator,
    BayesianPrivacyGuard,
    compute_content_seal,
    verify_content_seal,
)
from .key_manager import KeyManager
from .memory_vault import MemoryVault
from .privacy_guard import DifferentialPrivacyShield

__all__ = [
    'RSAKeyBundle',
    'MillerRabinPrimality',
    'EuclidKeyForge',
    'EulerFermatCipher',
    'ChineseRemainderAccelerator',
    'BayesianPrivacyGuard',
    'compute_content_seal',
    'verify_content_seal',
    'KeyManager',
    'MemoryVault',
    'DifferentialPrivacyShield',
]
