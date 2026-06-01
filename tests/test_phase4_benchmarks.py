"""
TruthKeep Memory -- Phase 4 Large-Scale Benchmark Suite
=======================================================
Level 8 Research Roadmap: Performance verification at scale.

Benchmarks:
  1. Write throughput: put_memory() at scale
  2. Search latency: FTS5 search at various corpus sizes
  3. Correction throughput: supersession flow at scale
  4. Crypto overhead: AES-GCM encrypt/decrypt at scale
  5. Audit chain: signed audit append + verify at scale
  6. Math kernel: Hilbert, cosine, Bayes throughput

Output: Raw latencies with P50/P95/P99 percentiles
Seed: 42 (deterministic, reproducible)

Usage:
    python -m pytest tests/test_phase4_benchmarks.py -v --tb=short -s
    BENCH_SCALE=medium python -m pytest tests/test_phase4_benchmarks.py -v -s
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# Deterministic seed for reproducibility
SEED = 42
random.seed(SEED)

# Scale tiers (override via env var BENCH_SCALE)
_scale = os.getenv("BENCH_SCALE", "small")
SCALES = {
    "small":  {"write": 300,  "search_corpus": 300,  "correct": 50,  "decay": 300,  "crypto": 500,  "audit": 200},
    "medium": {"write": 3000, "search_corpus": 3000, "correct": 300, "decay": 3000, "crypto": 2000, "audit": 1000},
    "large":  {"write": 30000,"search_corpus": 30000,"correct": 1000,"decay": 30000,"crypto": 10000,"audit": 5000},
}
SCALE = SCALES.get(_scale, SCALES["small"])

# -- Test Data Generator ---------------------------------------------------

SUBJECTS = [
    "Python syntax", "Rust ownership", "Docker networking", "Git branching",
    "React hooks", "CSS grid", "SQL joins", "API design", "Testing patterns",
    "CI/CD pipelines", "Kubernetes pods", "Redis caching", "GraphQL schema",
    "WebSocket protocol", "OAuth2 flow", "JWT tokens", "Database indexing",
    "Memory management", "Thread safety", "Error handling", "Logging best practices",
    "Code review", "Refactoring", "Design patterns", "Architecture decisions",
    "Performance tuning", "Security headers", "CORS policy", "Rate limiting",
    "Load balancing", "Microservices", "Event sourcing", "CQRS pattern",
]

CONTENT_TEMPLATES = [
    "The user prefers {subject} because it improves code quality significantly.",
    "Important: {subject} should always use best practices for maintainability.",
    "User confirmed that {subject} is critical for the current project setup.",
    "When working with {subject}, always consider edge cases and error handling.",
    "The team decided to adopt {subject} as the standard approach going forward.",
    "{subject} requires careful configuration to avoid common pitfalls in production.",
    "Best practice for {subject}: use incremental rollouts with feature flags.",
    "Note about {subject}: the user has extensive experience and prefers advanced patterns.",
]

MEMORY_TYPES = ["semantic", "procedural", "episodic", "working"]


def generate_memory_content(index: int) -> tuple[str, str, str]:
    """Generate deterministic test memory content.
    Returns: (content, subject, memory_type)
    """
    rng = random.Random(SEED + index)
    subject = rng.choice(SUBJECTS)
    template = rng.choice(CONTENT_TEMPLATES)
    content = template.format(subject=subject)
    content += f" [ref:{index:06d}]"
    memory_type = rng.choice(MEMORY_TYPES)
    return content, subject, memory_type


def generate_search_queries(n: int) -> list[str]:
    """Generate deterministic search queries."""
    rng = random.Random(SEED + 99999)
    queries = []
    for _ in range(n):
        subject = rng.choice(SUBJECTS)
        queries.append(subject)
    return queries


# -- Benchmark Result Data -------------------------------------------------

@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    operation_count: int
    total_seconds: float
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def ops_per_second(self) -> float:
        return self.operation_count / max(self.total_seconds, 1e-9)

    @property
    def p50_ms(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        idx = int(len(self.latencies_ms) * 0.95)
        return sorted(self.latencies_ms)[min(idx, len(self.latencies_ms) - 1)]

    @property
    def p99_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        idx = int(len(self.latencies_ms) * 0.99)
        return sorted(self.latencies_ms)[min(idx, len(self.latencies_ms) - 1)]

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "operation_count": self.operation_count,
            "total_seconds": round(self.total_seconds, 3),
            "ops_per_second": round(self.ops_per_second, 1),
            "mean_ms": round(self.mean_ms, 3),
            "p50_ms": round(self.p50_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "p99_ms": round(self.p99_ms, 3),
            "seed": SEED,
            "scale": _scale,
        }


def _make_memory(i: int, id_prefix: str = "bench", scope_id: str = "bench"):
    """Create a Memory instance for benchmarking."""
    from aegis_py.storage.models import Memory
    from datetime import datetime, timezone

    content, subject, mtype = generate_memory_content(i)
    now = datetime.now(timezone.utc)
    return Memory(
        id=f"{id_prefix}_{i:06d}",
        content=content,
        subject=subject,
        type=mtype,
        scope_type="project",
        scope_id=scope_id,
        source_kind="message",
        created_at=now,
        updated_at=now,
        confidence=0.85,
        activation_score=1.0,
        access_count=0,
        status="active",
    )


# -- Fixtures ---------------------------------------------------------------

@pytest.fixture(scope="module")
def bench_storage(tmp_path_factory):
    """Create a StorageManager for benchmarking."""
    from aegis_py.storage.manager import StorageManager
    db_path = tmp_path_factory.mktemp("bench") / "bench.db"
    storage = StorageManager(str(db_path))
    yield storage
    storage.close()


@pytest.fixture(scope="module")
def populated_storage(tmp_path_factory):
    """Pre-populated storage with SCALE['search_corpus'] memories."""
    from aegis_py.storage.manager import StorageManager

    db_path = tmp_path_factory.mktemp("bench_pop") / "bench_populated.db"
    storage = StorageManager(str(db_path))

    for i in range(SCALE["search_corpus"]):
        mem = _make_memory(i, id_prefix="pop", scope_id="benchmark")
        storage.put_memory(mem)

    yield storage
    storage.close()


# ===========================================================================
# BENCHMARK 1: Write Throughput
# ===========================================================================

class TestWriteThroughput:
    """Measure put_memory() throughput."""

    def test_write_throughput(self, bench_storage):
        """Write N memories and measure throughput."""
        n = SCALE["write"]
        latencies = []

        for i in range(n):
            mem = _make_memory(i + 100000, id_prefix="write", scope_id="write_bench")
            t0 = time.perf_counter()
            bench_storage.put_memory(mem)
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="write_throughput",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 50, f"Write too slow: {result.ops_per_second:.0f} ops/s"
        assert result.p95_ms < 200, f"Write P95 too high: {result.p95_ms:.1f}ms"

        print(f"\n[WRITE] {result.ops_per_second:.0f} ops/s, "
              f"P50={result.p50_ms:.1f}ms, P95={result.p95_ms:.1f}ms, P99={result.p99_ms:.1f}ms")


# ===========================================================================
# BENCHMARK 2: Search Latency
# ===========================================================================

class TestSearchLatency:
    """Measure FTS5 search latency on populated corpus."""

    def test_search_latency(self, populated_storage):
        """Search on corpus of N memories."""
        from aegis_py.retrieval.search import SearchPipeline
        from aegis_py.retrieval.models import SearchQuery

        pipeline = SearchPipeline(populated_storage)
        queries = generate_search_queries(100)
        latencies = []

        for query_text in queries:
            sq = SearchQuery(
                query=query_text,
                scope_id="benchmark",
                scope_type="project",
                limit=10,
            )
            t0 = time.perf_counter()
            pipeline.search(sq)
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="search_latency",
            operation_count=len(queries),
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.p95_ms < 500, f"Search P95 too high: {result.p95_ms:.1f}ms"

        print(f"\n[SEARCH] corpus={SCALE['search_corpus']}: "
              f"P50={result.p50_ms:.1f}ms, P95={result.p95_ms:.1f}ms, P99={result.p99_ms:.1f}ms")


# ===========================================================================
# BENCHMARK 3: Correction Throughput
# ===========================================================================

class TestCorrectionThroughput:
    """Measure correction/supersession flow throughput."""

    def test_correction_throughput(self, tmp_path):
        """Measure time to correct N memories."""
        from aegis_py.storage.manager import StorageManager
        from datetime import datetime, timezone

        db_path = str(tmp_path / "correct_bench.db")
        storage = StorageManager(db_path)
        now = datetime.now(timezone.utc).isoformat()
        n = SCALE["correct"]

        # Phase 1: Create originals
        for i in range(n):
            mem = _make_memory(i + 200000, id_prefix="orig", scope_id="correct_bench")
            storage.put_memory(mem)

        # Phase 2: Correct each
        latencies = []
        for i in range(n):
            old_id = f"orig_{i + 200000:06d}"

            t0 = time.perf_counter()
            storage.execute(
                "UPDATE memories SET status = 'superseded', updated_at = ? WHERE id = ?",
                (now, old_id),
            )
            new_mem = _make_memory(i + 300000, id_prefix="corrected", scope_id="correct_bench")
            storage.put_memory(new_mem)
            latencies.append((time.perf_counter() - t0) * 1000)

        storage.close()

        result = BenchmarkResult(
            name="correction_throughput",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 30, f"Correction too slow: {result.ops_per_second:.0f} ops/s"

        print(f"\n[CORRECT] {result.ops_per_second:.0f} ops/s, "
              f"P50={result.p50_ms:.1f}ms, P95={result.p95_ms:.1f}ms")


# ===========================================================================
# BENCHMARK 4: AES-GCM Crypto Overhead
# ===========================================================================

class TestCryptoOverhead:
    """Measure AES-GCM encryption/decryption overhead."""

    def test_aes_gcm_encrypt_throughput(self):
        """Measure AES-GCM encryption speed."""
        from aegis_py.security.aes_gcm import AESGCMEngine, KeyDerivation

        key, _ = KeyDerivation.derive_key("benchmark-key", salt=b"fixed-salt-16byt")
        n = SCALE["crypto"]
        latencies = []

        for i in range(n):
            content = f"Memory content #{i}: This is benchmark data for crypto overhead measurement."
            t0 = time.perf_counter()
            AESGCMEngine.encrypt_string(content, key)
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="aes_gcm_encrypt",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 1000, f"AES encrypt too slow: {result.ops_per_second:.0f} ops/s"

        print(f"\n[AES-ENC] {result.ops_per_second:.0f} ops/s, "
              f"P50={result.p50_ms:.3f}ms, P95={result.p95_ms:.3f}ms")

    def test_aes_gcm_decrypt_throughput(self):
        """Measure AES-GCM decryption speed."""
        from aegis_py.security.aes_gcm import AESGCMEngine, KeyDerivation

        key, _ = KeyDerivation.derive_key("benchmark-key", salt=b"fixed-salt-16byt")
        n = SCALE["crypto"]

        ciphertexts = []
        for i in range(n):
            content = f"Memory content #{i}: Decryption benchmark data."
            ciphertexts.append(AESGCMEngine.encrypt_string(content, key))

        latencies = []
        for ct in ciphertexts:
            t0 = time.perf_counter()
            AESGCMEngine.decrypt_string(ct, key)
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="aes_gcm_decrypt",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 1000, f"AES decrypt too slow: {result.ops_per_second:.0f} ops/s"

        print(f"\n[AES-DEC] {result.ops_per_second:.0f} ops/s, "
              f"P50={result.p50_ms:.3f}ms, P95={result.p95_ms:.3f}ms")

    def test_aes_vs_rsa_comparison(self):
        """Compare AES-GCM vs RSA encryption speed."""
        from aegis_py.security.aes_gcm import AESGCMEngine, KeyDerivation
        from aegis_py.security.crypto_math import EuclidKeyForge, EulerFermatCipher

        content = "Benchmark: Compare AES-GCM vs RSA encryption speed."
        n_rsa = 10
        n_aes = 200

        # AES-GCM timing
        aes_key, _ = KeyDerivation.derive_key("bench", salt=b"fixed-salt-16byt")
        t0 = time.perf_counter()
        for _ in range(n_aes):
            AESGCMEngine.encrypt_string(content, aes_key)
        aes_time = (time.perf_counter() - t0) / n_aes

        # RSA timing (512-bit for benchmark)
        rsa_bundle = EuclidKeyForge.generate_rsa_params(512)
        t0 = time.perf_counter()
        for _ in range(n_rsa):
            EulerFermatCipher.encrypt_bytes(content.encode(), rsa_bundle.e, rsa_bundle.n)
        rsa_time = (time.perf_counter() - t0) / n_rsa

        speedup = rsa_time / max(aes_time, 1e-9)

        # Log result regardless of speedup
        print(f"\n[AES-vs-RSA] AES={aes_time*1000:.3f}ms, RSA={rsa_time*1000:.3f}ms, "
              f"Speedup={speedup:.1f}x")

        # AES should be at least comparable (512-bit RSA is small)
        assert speedup > 0.5, f"AES unexpectedly slower than 512-bit RSA"


# ===========================================================================
# BENCHMARK 5: Signed Audit Log
# ===========================================================================

class TestAuditBenchmarks:
    """Measure signed audit log performance."""

    def test_audit_append_throughput(self, tmp_path):
        """Measure audit log append throughput."""
        from aegis_py.security.signed_audit import SignedAuditLog

        conn = sqlite3.connect(str(tmp_path / "audit_bench.db"))
        conn.row_factory = sqlite3.Row
        log = SignedAuditLog(conn, signing_key=os.urandom(32))

        n = SCALE["audit"]
        latencies = []

        for i in range(n):
            t0 = time.perf_counter()
            log.append_event(
                event_kind="benchmark_event",
                actor="benchmark",
                scope_type="project",
                scope_id="audit_bench",
                payload={"index": i, "data": f"event_{i}"},
            )
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="audit_append",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 30, f"Audit append too slow: {result.ops_per_second:.0f} ops/s"

        print(f"\n[AUDIT-APPEND] {result.ops_per_second:.0f} ops/s, "
              f"P50={result.p50_ms:.1f}ms, P95={result.p95_ms:.1f}ms")

        # Chain verification benchmark
        t0 = time.perf_counter()
        verify_result = log.verify_chain("project", "audit_bench")
        verify_time = (time.perf_counter() - t0) * 1000

        assert verify_result.valid is True
        assert verify_result.verified_entries == n

        print(f"[AUDIT-VERIFY] {n} entries: {verify_time:.1f}ms "
              f"({verify_time/n:.3f}ms/entry)")

        conn.close()


# ===========================================================================
# BENCHMARK 6: Math Kernel Performance
# ===========================================================================

class TestMathKernelBenchmarks:
    """Measure math kernel performance (Hilbert, cosine, Bayes)."""

    def test_hilbert_vector_throughput(self):
        """Measure Hilbert space vector computation speed."""
        from aegis_py.storage.modern_math import HilbertSpaceEngine

        n = SCALE["crypto"]
        latencies = []

        for i in range(n):
            text = f"Memory content number {i} with some varied text for hashing"
            t0 = time.perf_counter()
            HilbertSpaceEngine.text_to_hilbert_vector(text)
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="hilbert_vector",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 5000, f"Hilbert too slow: {result.ops_per_second:.0f} ops/s"

        print(f"\n[HILBERT] {result.ops_per_second:.0f} ops/s, P50={result.p50_ms:.3f}ms")

    def test_cosine_similarity_throughput(self):
        """Measure cosine similarity computation speed."""
        from aegis_py.storage.modern_math import HilbertSpaceEngine

        vectors = [
            HilbertSpaceEngine.text_to_hilbert_vector(f"text variant {i}")
            for i in range(100)
        ]

        n = SCALE["crypto"]
        latencies = []
        rng = random.Random(SEED)

        for _ in range(n):
            v1 = rng.choice(vectors)
            v2 = rng.choice(vectors)
            t0 = time.perf_counter()
            HilbertSpaceEngine.cosine_similarity(v1, v2)
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="cosine_similarity",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 10000, f"Cosine too slow: {result.ops_per_second:.0f} ops/s"

        print(f"\n[COSINE] {result.ops_per_second:.0f} ops/s, P50={result.p50_ms:.4f}ms")

    def test_bayesian_posterior_throughput(self):
        """Measure Bayesian posterior computation speed."""
        from aegis_py.storage.modern_math import BayesianBeliefEngine

        n = SCALE["crypto"]
        latencies = []
        rng = random.Random(SEED)

        for _ in range(n):
            prior = rng.uniform(0.1, 0.9)
            likelihood = rng.uniform(0.1, 0.9)
            t0 = time.perf_counter()
            BayesianBeliefEngine.posterior(prior, likelihood)
            latencies.append((time.perf_counter() - t0) * 1000)

        result = BenchmarkResult(
            name="bayesian_posterior",
            operation_count=n,
            total_seconds=sum(latencies) / 1000,
            latencies_ms=latencies,
        )

        assert result.ops_per_second > 100000, f"Bayes too slow: {result.ops_per_second:.0f} ops/s"

        print(f"\n[BAYES] {result.ops_per_second:.0f} ops/s, P50={result.p50_ms:.4f}ms")
