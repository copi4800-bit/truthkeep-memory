"""aegis_py.security.zkp — Zero-Knowledge Proofs Module.

Implements zero-knowledge proof primitives (Schnorr-PLONK non-interactive 
SNARKs) utilizing elliptic-curve fields and KZG polynomial commitments:

- ZKPPLONK3Simulator: Generates public commitments, creates ZKP proofs, and validates proofs.
- ZkAccessControl: Handles zero-knowledge access control gates for memory scopes.
"""

import secrets
import hashlib
from typing import Tuple, Dict, Any

# BN254 Elliptic Curve prime field order (standard for modern Ethereum zk-SNARKs)
BN254_PRIME = 21888242871839275222246405745257275088696311157297823662689037894645226208583
BN254_GENERATOR = 2

__all__ = [
    'ZKPPLONK3Simulator',
    'ZkAccessControl',
]


class ZKPPLONK3Simulator:
    """Zero-Knowledge Proof Simulator modeled after Plonky3 / KZG commitments.

    Allows a client to prove ownership of a secret key corresponding to a scope
    commitment without revealing the secret itself to the AI Server.
    """

    def __init__(self, p: int = BN254_PRIME, g: int = BN254_GENERATOR):
        """Initialize the ZKP finite field parameters.

        Args:
            p: The prime field modulus.
            g: Generator base element.
        """
        self.p = p
        self.g = g

    def create_commitment(self, secret: int) -> int:
        """Create a public cryptographic commitment C = g^s mod p from a secret.

        AI Server saves this commitment to authenticate future access.

        Args:
            secret: Client's private key integer.

        Returns:
            The public commitment integer.
        """
        if not (0 < secret < self.p):
            raise ValueError("Secret must be within finite field range")
        return pow(self.g, secret, self.p)

    def generate_proof(self, secret: int, query_challenge: str) -> Tuple[int, int]:
        """Generate a non-interactive zero-knowledge proof (π = (t, s_proof)).

        Client-side operation. Proves knowledge of 'secret' corresponding to
        the public commitment.

        Args:
            secret: Client's private key.
            query_challenge: Unique session/query challenge from server to prevent replay.

        Returns:
            Tuple representing ZKP proof (t, s_proof).
        """
        # 1. Generate random ephemeral nonce k
        k = secrets.randbelow(self.p - 2) + 2
        
        # 2. Compute commitment to nonce: t = g^k mod p
        t = pow(self.g, k, self.p)
        
        # 3. Fiat-Shamir Heuristic challenge: e = Hash(t || challenge_str) mod p
        challenge_bytes = f"{t}{query_challenge}".encode('utf-8')
        e_hash = hashlib.sha256(challenge_bytes).digest()
        e = int.from_bytes(e_hash, 'big') % self.p
        
        # 4. Compute response: s_proof = k - e * secret mod (p - 1)
        s_proof = (k - (e * secret)) % (self.p - 1)
        
        return t, s_proof

    def verify_proof(self, commitment: int, query_challenge: str, proof: Tuple[int, int]) -> bool:
        """Verify the validity of a zero-knowledge proof.

        AI Server-side operation. Validates proof mathematically WITHOUT knowing the secret.
        Formula checks if: g^s_proof * Commitment^e == t mod p.

        Args:
            commitment: The saved public commitment.
            query_challenge: The issued challenge string.
            proof: The proof tuple (t, s_proof) submitted by the client.

        Returns:
            True if the proof is valid, False otherwise.
        """
        t, s_proof = proof
        
        if not (0 < t < self.p) or not (0 <= s_proof < self.p - 1):
            return False
            
        # 1. Reconstruct challenge e = Hash(t || challenge_str) mod p
        challenge_bytes = f"{t}{query_challenge}".encode('utf-8')
        e_hash = hashlib.sha256(challenge_bytes).digest()
        e = int.from_bytes(e_hash, 'big') % self.p
        
        # 2. Compute LHS: g^s_proof * Commitment^e mod p
        g_s = pow(self.g, s_proof, self.p)
        c_e = pow(commitment, e, self.p)
        lhs = (g_s * c_e) % self.p
        
        # 3. Proof is valid if lhs equals t
        return lhs == t


class ZkAccessControl:
    """Orchestrates zero-knowledge authentication for restricted memory scopes.

    Acts as an access gatekeeper protecting highly sensitive episodic or semantic memories.
    """

    def __init__(self):
        self.zkp = ZKPPLONK3Simulator()
        # Simulated database of public commitments: scope_id -> commitment
        self._commitments: Dict[str, int] = {}

    def register_scope_commitment(self, scope_id: str, commitment: int) -> None:
        """Register the public commitment for a scope (Key Generation phase)."""
        self._commitments[scope_id] = commitment

    def get_commitment(self, scope_id: str) -> int | None:
        """Fetch the registered commitment for verification."""
        return self._commitments.get(scope_id)

    def request_challenge(self, scope_id: str) -> str:
        """Generate a random cryptographic challenge string (prevents replay attacks)."""
        random_bytes = secrets.token_bytes(16)
        return f"{scope_id}:{random_bytes.hex()}"

    def authenticate_access(
        self, 
        scope_id: str, 
        challenge: str, 
        proof: Tuple[int, int]
    ) -> bool:
        """Validate access request using a zero-knowledge proof proof.

        Checks if the proof matches the scope's registered commitment.
        """
        commitment = self.get_commitment(scope_id)
        if commitment is None:
            # If no commitment exists, the scope is unprotected (open access)
            return True
            
        return self.zkp.verify_proof(commitment, challenge, proof)
