"""aegis_py.security.pqc — Post-Quantum Cryptography Module.

Implements M-LWE (Module Learning With Errors) lattice-based algorithms
derived from modern quantum-resistant standards (NIST FIPS 203 & 204, 2026):

- PolynomialRing: High-fidelity simulator for polynomial rings R_q = Z_q[X] / (X^d + 1).
- MLKEMSimulator: Kyber-based key encapsulation mechanism for sharing symmetric keys.
- MLDSASimulator: Dilithium-based signature system for verifying memory ingestion sources.
- pqc_secure_channel: Key exchange helper to establish post-quantum encrypted tunnels.
"""

import os
import secrets
import hashlib
from typing import Tuple, List, Any

# NIST FIPS 203 standard parameters for Kyber-768/ML-KEM
ML_KEM_D = 256
ML_KEM_Q = 3329
ML_KEM_K = 3  # Module dimension

# Error distribution limits (centered around 0)
ERROR_RANGE = [-2, -1, 0, 1, 2]

__all__ = [
    'PolynomialRing',
    'MLKEMSimulator',
    'MLDSASimulator',
    'pqc_secure_channel',
]


class PolynomialRing:
    """High-fidelity representation of the polynomial ring R_q = Z_q[X] / (X^d + 1).

    Used for lattice-based cryptographic algorithms like ML-KEM and ML-DSA.
    """

    def __init__(self, coeffs: List[int], d: int = ML_KEM_D, q: int = ML_KEM_Q):
        """Initialize the polynomial with coefficients up to degree d-1.

        Args:
            coeffs: List of integer coefficients.
            d: The polynomial degree limit (default: 256).
            q: Modulo field size (default: 3329).
        """
        self.d = d
        self.q = q
        # Clean and pad coefficients to exactly length d
        cleaned_coeffs = [c % q for c in coeffs[:d]]
        self.coeffs = cleaned_coeffs + [0] * max(0, d - len(cleaned_coeffs))

    def add(self, other: 'PolynomialRing') -> 'PolynomialRing':
        """Homomorphic polynomial addition modulo q."""
        if self.d != other.d or self.q != other.q:
            raise ValueError("Incompatible polynomial ring dimensions")
        new_coeffs = [(a + b) % self.q for a, b in zip(self.coeffs, other.coeffs)]
        return PolynomialRing(new_coeffs, self.d, self.q)

    def subtract(self, other: 'PolynomialRing') -> 'PolynomialRing':
        """Homomorphic polynomial subtraction modulo q."""
        if self.d != other.d or self.q != other.q:
            raise ValueError("Incompatible polynomial ring dimensions")
        new_coeffs = [(a - b) % self.q for a, b in zip(self.coeffs, other.coeffs)]
        return PolynomialRing(new_coeffs, self.d, self.q)

    def multiply(self, other: 'PolynomialRing') -> 'PolynomialRing':
        """Polynomial multiplication modulo (X^d + 1) and modulo q.

        Utilizes ideal-ring polynomial quotient relations for reduction:
        X^d = -1 modulo (X^d + 1).
        """
        if self.d != other.d or self.q != other.q:
            raise ValueError("Incompatible polynomial ring dimensions")
        
        # Standard polynomial multiplication (degree up to 2d - 2)
        res = [0] * (2 * self.d)
        for i, a in enumerate(self.coeffs):
            if a == 0:
                continue
            for j, b in enumerate(other.coeffs):
                if b == 0:
                    continue
                res[i + j] = (res[i + j] + a * b) % self.q

        # Apply ideal quotient reduction: X^(i + d) = -X^i
        final_coeffs = [0] * self.d
        for i in range(2 * self.d):
            val = res[i]
            if val == 0:
                continue
            if i < self.d:
                final_coeffs[i] = (final_coeffs[i] + val) % self.q
            else:
                final_coeffs[i - self.d] = (final_coeffs[i - self.d] - val) % self.q

        return PolynomialRing(final_coeffs, self.d, self.q)

    def __repr__(self) -> str:
        return f"PolynomialRing(d={self.d}, q={self.q}, deg_bound={len(self.coeffs)})"


class MLKEMSimulator:
    """Simulator for Kyber/ML-KEM (NIST FIPS 203) Key Encapsulation Mechanism.

    Strictly implements Module Learning With Errors (M-LWE) algebra:
    - Matrix A is k x k polynomials.
    - Secret s and noise e are vectors of k polynomials.
    - Public key t is a vector of k polynomials: t = A * s + e.
    - Ciphertext contains vector u of k polynomials and single polynomial v.
    """

    def __init__(self, k: int = ML_KEM_K, d: int = ML_KEM_D, q: int = ML_KEM_Q):
        self.k = k
        self.d = d
        self.q = q

    def generate_keypair(self) -> Tuple[Tuple[List[List[PolynomialRing]], List[PolynomialRing]], List[PolynomialRing]]:
        """Generate a quantum-resistant M-LWE public/private keypair.

        Returns:
            Tuple of (public_key, private_key) where:
            public_key = (Matrix A, Vector t = A * s + e)
            private_key = Vector s
        """
        # Generate matrix A (k x k)
        matrix_a = [[self._rand_poly() for _ in range(self.k)] for _ in range(self.k)]
        
        # Secret s and noise e are vectors of k polynomials
        secret_s = [self._noise_poly() for _ in range(self.k)]
        noise_e = [self._noise_poly() for _ in range(self.k)]
        
        # Calculate vector t = A * s + e (LWE instance)
        # t_i = sum_j (A_{i,j} * s_j) + e_i
        vector_t = []
        for i in range(self.k):
            t_i = noise_e[i]
            for j in range(self.k):
                t_i = t_i.add(matrix_a[i][j].multiply(secret_s[j]))
            vector_t.append(t_i)
        
        public_key = (matrix_a, vector_t)
        private_key = secret_s
        return public_key, private_key

    def encapsulate(self, public_key: Tuple[List[List[PolynomialRing]], List[PolynomialRing]]) -> Tuple[Tuple[List[PolynomialRing], PolynomialRing], bytes]:
        """Encapsulate a securely generated shared secret under the receiver's public key.

        Args:
            public_key: The recipient's public key (A, t).

        Returns:
            Tuple of (ciphertext, shared_symmetric_key)
        """
        matrix_a, vector_t = public_key
        
        # Draw random coins r (vector of k), noise e1 (vector of k), and e2 (single poly)
        coins_r = [self._noise_poly() for _ in range(self.k)]
        noise_e1 = [self._noise_poly() for _ in range(self.k)]
        noise_e2 = self._noise_poly()
        
        # Encrypted shared key parameters
        shared_secret = secrets.token_bytes(32)
        m_poly = self._encode_key(shared_secret)
        
        # u = A^T * r + e1 (vector of k)
        # u_i = sum_j (A_{j,i} * r_j) + e1_i
        vector_u = []
        for i in range(self.k):
            u_i = noise_e1[i]
            for j in range(self.k):
                u_i = u_i.add(matrix_a[j][i].multiply(coins_r[j]))
            vector_u.append(u_i)
                
        # v = t^T * r + e2 + m_poly (single polynomial)
        # v = sum_j (t_j * r_j) + e2 + m_poly
        vector_v = noise_e2.add(m_poly)
        for j in range(self.k):
            vector_v = vector_v.add(vector_t[j].multiply(coins_r[j]))
            
        ciphertext = (vector_u, vector_v)
        return ciphertext, shared_secret

    def decapsulate(self, ciphertext: Tuple[List[PolynomialRing], PolynomialRing], private_key: List[PolynomialRing]) -> bytes:
        """Decapsulate the ciphertext using the private key to recover the shared secret.

        Args:
            ciphertext: Encapsulated cipher containing (u, v).
            private_key: The recipient's private key s.

        Returns:
            Recovered 32-byte shared symmetric key.
        """
        vector_u, vector_v = ciphertext
        secret_s = private_key
        
        # Compute m_recovered = v - s^T * u
        # s^T * u = sum_i (s_i * u_i)
        su_sum = secret_s[0].multiply(vector_u[0])
        for i in range(1, self.k):
            su_sum = su_sum.add(secret_s[i].multiply(vector_u[i]))
            
        m_poly = vector_v.subtract(su_sum)
        return self._decode_key(m_poly)

    def _rand_poly(self) -> PolynomialRing:
        """Generate a random polynomial with coefficients uniformly distributed in Z_q."""
        return PolynomialRing([secrets.randbelow(self.q) for _ in range(self.d)], self.d, self.q)

    def _noise_poly(self) -> PolynomialRing:
        """Generate a noise polynomial with coefficients centered around zero."""
        return PolynomialRing([secrets.choice(ERROR_RANGE) for _ in range(self.d)], self.d, self.q)

    def _encode_key(self, key: bytes) -> PolynomialRing:
        """Encode a 256-bit key into a polynomial mapping bits to q//2 coefficients."""
        coeffs = []
        for byte in key:
            for bit_pos in range(8):
                bit = (byte >> bit_pos) & 1
                coeffs.append(bit * (self.q // 2))
        return PolynomialRing(coeffs, self.d, self.q)

    def _decode_key(self, poly: PolynomialRing) -> bytes:
        """Decode a polynomial back to a 256-bit key by thresholding coefficients."""
        key_bytes = bytearray()
        half_q = self.q // 2
        for byte_idx in range(32):
            byte = 0
            for bit_pos in range(8):
                coeff = poly.coeffs[byte_idx * 8 + bit_pos]
                # Modulo distance to half_q versus zero
                dist_to_half = min(abs(coeff - half_q), self.q - abs(coeff - half_q))
                dist_to_zero = min(coeff, self.q - coeff)
                bit = 1 if dist_to_half < dist_to_zero else 0
                byte |= (bit << bit_pos)
            key_bytes.append(byte)
        return bytes(key_bytes)


class MLDSASimulator:
    """Simulator for Dilithium/ML-DSA (NIST FIPS 204) Lattice Signature system.

    Uses sparse polynomials with coefficients in [-1, 0, 1] for the challenge polynomial
    to represent ideal lattice algebra with perfect security and bounded noise limits.
    """

    def __init__(self, k: int = 4, l: int = 4, d: int = ML_KEM_D, q: int = 8380417):
        self.k = k  # Matrix rows (verification vector size)
        self.l = l  # Matrix cols (signing vector size)
        self.d = d
        self.q = q  # Dilithium prime q = 2^23 - 2^13 + 1
        self.alpha = q // 16  # HighBits division factor

    def generate_keypair(self) -> Tuple[Tuple[List[List[PolynomialRing]], List[PolynomialRing]], List[PolynomialRing]]:
        """Generate signing key (private) and verification key (public)."""
        matrix_a = [[self._rand_poly() for _ in range(self.l)] for _ in range(self.k)]
        secret_s1 = [self._noise_poly() for _ in range(self.l)]
        secret_s2 = [self._noise_poly() for _ in range(self.k)]
        
        # t = A * s1 + s2
        t = [secret_s2[i] for i in range(self.k)]
        for i in range(self.k):
            for j in range(self.l):
                t[i] = t[i].add(matrix_a[i][j].multiply(secret_s1[j]))
                
        public_key = (matrix_a, t)
        private_key = (secret_s1, secret_s2)
        return public_key, private_key

    def _high_bits(self, poly: PolynomialRing) -> List[int]:
        """Extract the high-order bits of polynomial coefficients to absorb noise."""
        return [c // self.alpha for c in poly.coeffs]

    def sign(self, message: bytes, private_key: Tuple[List[PolynomialRing], List[PolynomialRing]], public_key: Tuple[List[List[PolynomialRing]], List[PolynomialRing]]) -> Tuple[List[PolynomialRing], int]:
        """Sign a message producing a lattice-based proof of identity.

        Args:
            message: Raw payload bytes to sign.
            private_key: Private key components (s1, s2).
            public_key: Public key containing matrix_a.

        Returns:
            Lattice signature (z vector, challenge scalar c).
        """
        s1, s2 = private_key
        matrix_a, _ = public_key
        
        # 1. Compute w = A * y (where y is bounded masking noise)
        y = [PolynomialRing([secrets.choice([-4, -2, 0, 2, 4]) for _ in range(self.d)], self.d, self.q) for _ in range(self.l)]
        
        w = [PolynomialRing([0] * self.d, self.d, self.q) for _ in range(self.k)]
        for i in range(self.k):
            for j in range(self.l):
                w[i] = w[i].add(matrix_a[i][j].multiply(y[j]))
                
        # 2. Extract HighBits of w to hash
        w_high = []
        for w_poly in w:
            w_high.extend(self._high_bits(w_poly))
            
        # 3. Challenge c is derived from w_high and message.
        # Translates the 256-bit hash into a sparse polynomial with coefficients in [-1, 0, 1]
        h = hashlib.sha256()
        h.update(str(w_high).encode('utf-8'))
        h.update(message)
        c_val = int.from_bytes(h.digest(), 'big')
        
        coeffs = []
        temp = c_val
        for _ in range(self.d):
            coeffs.append((temp % 3) - 1)
            temp = temp // 3
        c_poly = PolynomialRing(coeffs, self.d, self.q)
        
        # 4. Compute signature vector z = y + c * s1
        vector_z = []
        for i in range(self.l):
            cs1 = c_poly.multiply(s1[i])
            z_i = y[i].add(cs1)
            vector_z.append(z_i)
            
        return vector_z, c_val

    def verify(self, message: bytes, signature: Tuple[List[PolynomialRing], int], public_key: Tuple[List[List[PolynomialRing]], List[PolynomialRing]]) -> bool:
        """Verify the lattice-based signature integrity.

        Checks if the HighBits of (A * z - c * t) match the challenge hash.
        """
        vector_z, c_val = signature
        matrix_a, vector_t = public_key
        
        # Reconstruct challenge polynomial from c_val
        coeffs = []
        temp = c_val
        for _ in range(self.d):
            coeffs.append((temp % 3) - 1)
            temp = temp // 3
        c_poly = PolynomialRing(coeffs, self.d, self.q)
        
        # 1. Compute Az = A * z
        az = [PolynomialRing([0] * self.d, self.d, self.q) for _ in range(self.k)]
        for i in range(self.k):
            for j in range(self.l):
                term = matrix_a[i][j].multiply(vector_z[j])
                az[i] = az[i].add(term)
                
        # 2. Compute ct = c * t
        ct = [c_poly.multiply(vector_t[i]) for i in range(self.k)]
        
        # 3. Recover w_prime = Az - ct (this approximates A * y modulo small errors c * s2)
        w_prime = []
        for i in range(self.k):
            w_i = az[i].subtract(ct[i])
            w_prime.append(w_i)
            
        # 4. Extract HighBits of w_prime
        w_prime_high = []
        for w_poly in w_prime:
            w_prime_high.extend(self._high_bits(w_poly))
            
        # 5. Compute verifying challenge and check equality
        h = hashlib.sha256()
        h.update(str(w_prime_high).encode('utf-8'))
        h.update(message)
        verify_c = int.from_bytes(h.digest(), 'big')
        
        return verify_c == c_val

    def _rand_poly(self) -> PolynomialRing:
        return PolynomialRing([secrets.randbelow(self.q) for _ in range(self.d)], self.d, self.q)

    def _noise_poly(self) -> PolynomialRing:
        return PolynomialRing([secrets.choice(ERROR_RANGE) for _ in range(self.d)], self.d, self.q)


def pqc_secure_channel() -> Tuple[bytes, bytes]:
    """Simulates establishing a secure PQC tunnel via ML-KEM.

    Returns:
        Shared symmetric key established safely for both Client and Server.
    """
    kem = MLKEMSimulator()
    pk, sk = kem.generate_keypair()
    ciphertext, client_key = kem.encapsulate(pk)
    server_key = kem.decapsulate(ciphertext, sk)
    
    if client_key != server_key:
        raise ValueError("Lattice key encapsulation failure!")
    return client_key, server_key
