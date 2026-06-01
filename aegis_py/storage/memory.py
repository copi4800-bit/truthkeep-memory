from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .models import Memory, RETRIEVABLE_MEMORY_STATUS_SQL
from ..hygiene.transitions import now_iso, transition_memory
from .ancient_math import compute_memory_ancient_math_fields
from .modern_math import compute_memory_modern_math_fields

SECONDS_PER_DAY = 86400.0

# Staleness retention thresholds
STALENESS_ANNUAL_DAYS = 365
STALENESS_ANNUAL_MIN_ACCESS = 1
STALENESS_ANNUAL_CONFIDENCE = 0.9
STALENESS_ANNUAL_SALIENCE = 0.42
STALENESS_QUARTERLY_DAYS = 90
STALENESS_QUARTERLY_MIN_ACCESS = 0
STALENESS_QUARTERLY_CONFIDENCE = 0.85
STALENESS_QUARTERLY_SALIENCE = 0.4

__all__ = ["MemoryRepository"]


class MemoryRepository:
    """Memory-row and retention/query helpers behind StorageManager."""

    def __init__(self, storage: Any):
        self.storage = storage

    def put_memory(self, memory: Memory) -> bool:
        """Persist a new Memory, skipping duplicates by content+scope.

        Computes ancient-math fields (I-Ching, Luo-Shu), modern-math fields
        (Erdos cell, TDA signature), and optionally encrypts content before
        inserting into the database.

        Args:
            memory: The Memory dataclass to store.

        Returns:
            True if the memory was inserted, False if a duplicate existed.
        """
        conn = self.storage._get_connection()
        import hashlib
        content_seal = hashlib.sha256(memory.content.encode("utf-8")).hexdigest()
        existing = conn.execute(
            "SELECT id FROM memories WHERE (content = ? OR content_seal = ?) AND scope_id = ? AND scope_type = ? LIMIT 1",
            (memory.content, content_seal, memory.scope_id, memory.scope_type),
        ).fetchone()
        if existing:
            return False

        data = memory.model_dump(by_alias=True)
        evidence_link = self.storage._ensure_memory_evidence(memory)
        normalized_metadata = self.storage._ensure_admission_state(
            metadata=evidence_link["metadata"],
            status=memory.status,
        )
        normalized_metadata = self.storage._ensure_memory_state(
            metadata=normalized_metadata,
            status=memory.status,
        )
        memory.metadata = normalized_metadata
        data["metadata_json"] = json.dumps(normalized_metadata)
        data["created_at"] = data["created_at"].isoformat()
        data["updated_at"] = data["updated_at"].isoformat()
        if data["last_accessed_at"]:
            data["last_accessed_at"] = data["last_accessed_at"].isoformat()
        if data["expires_at"]:
            data["expires_at"] = data["expires_at"].isoformat()
        if data["archived_at"]:
            data["archived_at"] = data["archived_at"].isoformat()

        # Tính toán trạng thái nhận thức Kinh Dịch và Lạc Thư
        iching, checksum = compute_memory_ancient_math_fields(data)
        data["iching_state"] = iching
        data["luoshu_checksum"] = checksum

        # Tính toán trường toán học hiện đại (Erdős + Poincaré TDA)
        modern_fields = compute_memory_modern_math_fields(
            memory.content, subject=memory.subject, summary=memory.summary,
        )
        data["erdos_cell_id"] = modern_fields["erdos_cell_id"]
        data["tda_signature"] = modern_fields["tda_signature"]

        # Phase 4: Mật mã cổ điển — Mã hóa ký ức (Euclid + Euler + CRT + SHA-256)
        try:
            from ..security.memory_vault import MemoryVault
            from ..security.key_manager import KeyManager
            vault = MemoryVault(KeyManager(conn))
            seal_result = vault.seal_memory(
                content=memory.content,
                scope_type=memory.scope_type,
                scope_id=memory.scope_id,
            )
            data["encrypted_content"] = seal_result["encrypted_content"]
            data["encryption_key_id"] = seal_result["key_id"]
            data["content_seal"] = seal_result["seal_hash"]
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Encryption skipped: %s", e)

        # Strict Privacy Mode: Mã hóa đối xứng AES-256-GCM cho content và summary
        from aegis_py.security.config import SecurityConfig
        if SecurityConfig.strict_privacy_enabled():
            try:
                import os
                import hashlib
                from aegis_py.security.aes_gcm import AESGCMEngine, KeyDerivation

                # Derive AES key per scope
                passphrase = os.getenv("TK_MASTER_KEY", "aegis-secure-key-default-2026")
                salt = hashlib.sha256(f"{memory.scope_type}:{memory.scope_id}".encode("utf-8")).digest()[:16]
                aes_key, _ = KeyDerivation.derive_key(passphrase, salt=salt)
                aad = f"{memory.scope_type}:{memory.scope_id}".encode("utf-8")

                # Mã hóa content
                data["content"] = AESGCMEngine.encrypt_string(memory.content, aes_key, aad)

                # Mã hóa summary (nếu có)
                if memory.summary:
                    data["summary"] = AESGCMEngine.encrypt_string(memory.summary, aes_key, aad)

                # Đánh dấu trong metadata
                normalized_metadata["encrypted_by_aes_gcm"] = True
                data["metadata_json"] = json.dumps(normalized_metadata)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("Strict mode encryption failed: %s", e)

        existing_columns = self.storage._table_columns("memories")
        filtered = {key: value for key, value in data.items() if key in existing_columns}
        keys = ", ".join(filtered.keys())
        placeholders = ", ".join(["?" for _ in filtered])

        conn.execute(
            f"INSERT OR REPLACE INTO memories ({keys}) VALUES ({placeholders})",
            tuple(filtered.values()),
        )
        self.index_memory_vector(memory.id, commit=False)
        self.storage.bump_scope_revision(memory.scope_type, memory.scope_id, commit=False)
        conn.commit()
        return True

    def get_memory_state(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve the governance state envelope for a single memory.

        Args:
            memory_id: UUID of the memory to inspect.

        Returns:
            Dict with memory_id, status, admission_state, memory_state,
            or None if not found.
        """
        row = self.storage.fetch_one(
            "SELECT id, status, metadata_json FROM memories WHERE id = ?",
            (memory_id,),
        )
        if row is None:
            return None
        metadata = self.storage._coerce_metadata(row["metadata_json"])
        admission_state = self.storage._ensure_admission_state(
            metadata=metadata,
            status=row["status"],
        )["admission_state"]
        memory_state = self.storage._ensure_memory_state(
            metadata=metadata,
            status=row["status"],
        )["memory_state"]
        return {
            "memory_id": row["id"],
            "status": row["status"],
            "admission_state": admission_state,
            "memory_state": memory_state,
        }

    def summarize_memory_states(
        self,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate memory-state counts, optionally filtered by scope.

        Args:
            scope_type: Optional namespace kind filter.
            scope_id:   Optional namespace id filter.

        Returns:
            Dict with scope_type, scope_id, memory_records count,
            and state_counts mapping.
        """
        where_clauses: list[str] = []
        params: list[Any] = []
        if scope_type is not None:
            where_clauses.append("scope_type = ?")
            params.append(scope_type)
        if scope_id is not None:
            where_clauses.append("scope_id = ?")
            params.append(scope_id)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        rows = self.storage.fetch_all(
            f"SELECT id, status, metadata_json FROM memories {where_sql}",
            tuple(params),
        )
        counts: dict[str, int] = {}
        for row in rows:
            metadata = self.storage._coerce_metadata(row["metadata_json"])
            memory_state = self.storage._ensure_memory_state(
                metadata=metadata,
                status=row["status"],
            )["memory_state"]
            counts[memory_state] = counts.get(memory_state, 0) + 1
        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "memory_records": len(rows),
            "state_counts": counts,
        }

    def get_memory(self, memory_id: str) -> Memory | None:
        """Fetch a single Memory by its UUID, or None if absent.

        Args:
            memory_id: UUID of the memory to retrieve.

        Returns:
            A Memory dataclass instance, or None.
        """
        row = self.storage.fetch_one("SELECT * FROM memories WHERE id = ?", (memory_id,))
        if row:
            return self.storage._row_to_memory(row)
        return None

    def index_memory_vector(self, memory_id: str, *, commit: bool = True) -> None:
        """Compute and upsert the Hilbert-space embedding for a memory.

        Reads the memory's content, summary, and subject from the database,
        generates a dense vector via HilbertSpaceEngine, and stores it in
        the memory_vectors table.

        Args:
            memory_id: UUID of the memory to index.
            commit:    Whether to commit the transaction immediately.
        """
        row = self.storage.fetch_one(
            """
            SELECT id, scope_type, scope_id, content, summary, subject
            FROM memories
            WHERE id = ?
            """,
            (memory_id,),
        )
        if row is None:
            return
        text = " ".join(part for part in (row["content"], row["summary"], row["subject"]) if part)
        embedding = self.storage._embed_text(text)
        conn = self.storage._get_connection()
        conn.execute(
            """
            INSERT INTO memory_vectors (
                memory_id, scope_type, scope_id, token_count, embedding_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(memory_id) DO UPDATE SET
                scope_type=excluded.scope_type,
                scope_id=excluded.scope_id,
                token_count=excluded.token_count,
                embedding_json=excluded.embedding_json,
                updated_at=excluded.updated_at
            """,
            (
                memory_id,
                row["scope_type"],
                row["scope_id"],
                len(embedding),
                json.dumps(embedding, ensure_ascii=True),
                now_iso(),
            ),
        )

        # Phase 5: Mã hóa Đồng cấu (FHE CKKS) & Cam kết ZKP Plonky3
        try:
            from ..security.key_manager import KeyManager
            from ..security.fhe import CKKSRealSimulator
            from ..security.zkp import ZKPPLONK3Simulator

            key_mgr = KeyManager(conn)
            key_id_val, key_bundle = key_mgr.get_or_create_key(row["scope_type"], row["scope_id"])

            # Khởi tạo vector FHE (độ dài mặc định 64 chiều)
            fhe_vector = [0.0] * 64
            for k, v in embedding.items():
                try:
                    idx = int(k)
                    if 0 <= idx < 64:
                        fhe_vector[idx] = float(v)
                except (ValueError, TypeError):
                    pass

            # 1. Mã hóa CKKS FHE cho vector embedding
            fhe_secret = key_bundle.d % 2147483647
            fhe_sim = CKKSRealSimulator()
            encrypted_vec = fhe_sim.encrypt_vector(fhe_vector, fhe_secret)

            # 2. Tạo cam kết ZKP công khai
            zk_secret = key_bundle.d % 21888242871839275222246405745257275088696311157297823662689037894645226208583
            zk_sim = ZKPPLONK3Simulator()
            zk_commit = zk_sim.create_commitment(zk_secret)

            # 3. Lưu trữ vào bảng memories
            conn.execute(
                "UPDATE memories SET encrypted_vector = ?, zk_commitment = ? WHERE id = ?",
                (json.dumps(encrypted_vec), str(zk_commit), memory_id)
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Phase 5 vector encryption/ZKP skipped: %s", e)

        if commit:
            conn.commit()

    def search_memory_vectors(
        self,
        *,
        query: str,
        scope_type: str,
        scope_id: str,
        include_global: bool = False,
        limit: int = 10,
        min_similarity: float = 0.12,
    ) -> list[dict[str, Any]]:
        """Semantic vector search over indexed memories.

        Embeds the query text, computes cosine similarity against stored
        vectors, and returns the top-*limit* results above *min_similarity*.

        Args:
            query:          Natural-language search string.
            scope_type:     Namespace kind to search within.
            scope_id:       Namespace id to search within.
            include_global: Also search the 'global' scope.
            limit:          Max results to return.
            min_similarity: Minimum cosine similarity threshold.

        Returns:
            List of row dicts enriched with a ``vector_similarity`` key.
        """
        query_embedding = self.storage._embed_text(query)
        if not query_embedding:
            return []
        where = (
            "((v.scope_type = ? AND v.scope_id = ?) OR v.scope_type = 'global')"
            if include_global
            else "(v.scope_type = ? AND v.scope_id = ?)"
        )
        rows = self.storage.fetch_all(
            f"""
            SELECT v.memory_id, v.embedding_json, m.*
            FROM memory_vectors v
            JOIN memories m ON m.id = v.memory_id
            WHERE {where}
              AND m.status IN ({RETRIEVABLE_MEMORY_STATUS_SQL})
            ORDER BY m.updated_at DESC
            LIMIT ?
            """,
            (scope_type, scope_id, max(limit * 6, 25)),
        )
        ranked: list[dict[str, Any]] = []
        for row in rows:
            embedding = self.storage._coerce_metadata(row["embedding_json"])
            similarity = self.storage._cosine_similarity(query_embedding, embedding)
            if similarity < min_similarity:
                continue
            payload = dict(row)
            payload["vector_similarity"] = round(similarity, 6)
            ranked.append(payload)
        ranked.sort(
            key=lambda item: (
                item["vector_similarity"],
                float(item["activation_score"] or 0.0),
                item["updated_at"],
            ),
            reverse=True,
        )
        return ranked[:limit]

    def search_homomorphic_vectors(
        self,
        *,
        encrypted_query_vector: list[int],
        scope_type: str,
        scope_id: str,
        include_global: bool = False,
        limit: int = 10,
        min_similarity: float = 0.12,
    ) -> list[dict[str, Any]]:
        """Perform semantic search using Fully Homomorphic Encryption (FHE CKKS).

        Computes Cosine Similarity directly on encrypted vector payloads in the database
        without decrypting them in RAM. Decrypts similarity scores at the repository
        boundary using the scope's private key.
        """
        conn = self.storage._get_connection()
        where = (
            "((scope_type = ? AND scope_id = ?) OR scope_type = 'global')"
            if include_global
            else "(scope_type = ? AND scope_id = ?)"
        )

        # Lấy toàn bộ memories có encrypted_vector trong scope
        rows = self.storage.fetch_all(
            f"""
            SELECT id, scope_type, scope_id, encrypted_vector, status, content, summary, subject, activation_score, updated_at
            FROM memories
            WHERE {where}
              AND encrypted_vector IS NOT NULL
              AND status IN ({RETRIEVABLE_MEMORY_STATUS_SQL})
            """,
            (scope_type, scope_id),
        )

        if not rows:
            return []

        # Lấy khóa bí mật của scope để giải mã điểm số ở biên
        from ..security.key_manager import KeyManager
        from ..security.fhe import CKKSRealSimulator
        key_mgr = KeyManager(conn)
        key_id_val, key_bundle = key_mgr.get_or_create_key(scope_type, scope_id)
        fhe_secret = key_bundle.d % 2147483647
        fhe_sim = CKKSRealSimulator()

        ranked: list[dict[str, Any]] = []
        for row in rows:
            try:
                enc_vec = json.loads(row["encrypted_vector"])
                # AI Server thực hiện phép nhân vô hướng đồng cấu hoàn toàn mù (blind) trên RAM
                enc_score = fhe_sim.homomorphic_dot_product(encrypted_query_vector, enc_vec)

                # Giải mã điểm số tại biên an toàn
                similarity = fhe_sim.decrypt_score(enc_score, fhe_secret, len(enc_vec))

                if similarity < min_similarity:
                    continue

                payload = dict(row)
                payload["vector_similarity"] = round(similarity, 6)
                # Xóa encrypted_vector khỏi payload trả về để tránh phình dữ liệu
                payload.pop("encrypted_vector", None)
                ranked.append(payload)
            except Exception:
                pass

        ranked.sort(
            key=lambda item: (
                item["vector_similarity"],
                float(item["activation_score"] or 0.0),
                item["updated_at"],
            ),
            reverse=True,
        )
        return ranked[:limit]

    def search_fts(
        self,
        query: str,
        scope_type: str,
        scope_id: str,
        limit: int = 10,
        include_global: bool = True,
    ) -> list[tuple[Memory, float]]:
        """Full-text search over memory content via SQLite FTS5.

        Args:
            query:          Search query (special chars stripped).
            scope_type:     Namespace kind filter.
            scope_id:       Namespace id filter.
            limit:          Max results.
            include_global: Also search global scope.

        Returns:
            List of (Memory, rank) tuples ordered by FTS relevance.
        """
        scope_sql = "(m.scope_type = ? AND m.scope_id = ?)"
        if include_global:
            scope_sql = f"({scope_sql} OR m.scope_type = 'global')"

        chars_to_strip = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
        fts_query = query.translate(str.maketrans("", "", chars_to_strip))

        if not fts_query:
            sql = f"""
                SELECT *, 0.0 as rank FROM memories m
                WHERE {scope_sql} AND status IN ({RETRIEVABLE_MEMORY_STATUS_SQL})
                ORDER BY activation_score DESC
                LIMIT ?
            """
            params = (scope_type, scope_id, limit)
        else:
            sql = f"""
                SELECT m.*, fts.rank
                FROM memories_fts(?) fts
                JOIN memories m ON m.rowid = fts.rowid
                WHERE {scope_sql}
                  AND m.status IN ({RETRIEVABLE_MEMORY_STATUS_SQL})
                ORDER BY fts.rank
                LIMIT ?
            """
            params = (fts_query, scope_type, scope_id, limit)

        results: list[tuple[Memory, float]] = []
        conn = self.storage._get_connection()
        cursor = conn.execute(sql, params)
        for row in cursor:
            data = dict(row)
            rank = data.pop("rank")
            results.append((self.storage._row_to_memory(data), rank))
        return results

    def reinforce_memory(self, memory_id: str, increment: float = 1.0, max_score: float = 10.0) -> None:
        """Boost a memory's activation score with bounded reinforcement.

        Applies diminishing-return scaling based on access_count, updates
        I-Ching and Luo-Shu fields, and records retention metadata.

        Args:
            memory_id: UUID of the memory to reinforce.
            increment: Raw boost amount (will be bounded).
            max_score: Upper ceiling for activation_score.
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = self.storage._get_connection()
        row = conn.execute(
            "SELECT type, status, confidence, activation_score, access_count, metadata_json FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        if row is None:
            return
        current_score = float(row["activation_score"] or 0.0)
        access_count = int(row["access_count"] or 0)
        metadata = self.storage._coerce_metadata(row["metadata_json"])
        bounded_increment = min(increment, max(0.2, 0.6 / (1 + (access_count * 0.5))))
        next_score = min(max_score, current_score + bounded_increment)
        metadata["retention_stage"] = "active"
        metadata["retention_recovery_mode"] = "bounded_reinforcement"

        # Tính toán lại trạng thái Kinh Dịch và Lạc Thư
        temp_data = {
            "type": row["type"],
            "status": row["status"],
            "confidence": row["confidence"],
            "activation_score": next_score,
            "metadata_json": metadata,
        }
        iching, checksum = compute_memory_ancient_math_fields(temp_data)

        conn.execute(
            """
            UPDATE memories
            SET activation_score = ?,
                access_count = access_count + 1,
                last_accessed_at = ?,
                updated_at = ?,
                metadata_json = ?,
                iching_state = ?,
                luoshu_checksum = ?
            WHERE id = ?
            """,
            (next_score, now, now, json.dumps(metadata, ensure_ascii=True), iching, checksum, memory_id),
        )
        conn.commit()

    def apply_decay(
        self,
        half_life_days: float = 7.0,
        type_half_lives: dict[str, float] | None = None,
    ) -> None:
        """Apply time-based exponential decay to all active memories.

        Uses configurable half-lives (per memory type) modified by salience
        and reinforcement history.  Recomputes I-Ching / Luo-Shu fields
        after score adjustment.

        Args:
            half_life_days:   Default decay half-life in days.
            type_half_lives:  Optional per-type overrides.
        """
        now = datetime.now(timezone.utc)
        conn = self.storage._get_connection()
        mems = conn.execute(
            """
            SELECT id, type, activation_score, confidence, access_count, metadata_json,
                   last_accessed_at, updated_at
            FROM memories
            WHERE status = 'active'
            """
        ).fetchall()
        updates = []
        for row in mems:
            last_ref = row["last_accessed_at"] or row["updated_at"]
            last_time = datetime.fromisoformat(last_ref)
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)

            delta_days = (now - last_time).total_seconds() / SECONDS_PER_DAY
            if delta_days <= 0.1:
                continue
            effective_half_life = (
                type_half_lives.get(row["type"], half_life_days)
                if type_half_lives is not None
                else half_life_days
            )
            metadata = self.storage._coerce_metadata(row["metadata_json"])
            explicit_salience = float(metadata.get("salience", 0.0) or 0.0)
            inferred_salience = max(0.0, float(row["confidence"] or 1.0) - 1.0)
            salience = max(explicit_salience, inferred_salience)
            reinforcement_count = int(row["access_count"] or 0)
            effective_half_life = effective_half_life * (
                1.0 + (0.35 * min(salience, 1.0)) + min(1.2, reinforcement_count * 0.08)
            )
            new_score = row["activation_score"] * (0.5 ** (delta_days / effective_half_life))

            # Tính toán lại trạng thái Kinh Dịch và Lạc Thư
            temp_data = {
                "type": row["type"],
                "status": "active",
                "confidence": row["confidence"],
                "activation_score": new_score,
                "metadata_json": metadata,
            }
            iching, checksum = compute_memory_ancient_math_fields(temp_data)
            updates.append((new_score, now.isoformat(), iching, checksum, row["id"]))

        if updates:
            conn.executemany(
                "UPDATE memories SET activation_score = ?, updated_at = ?, iching_state = ?, luoshu_checksum = ? WHERE id = ?",
                updates
            )
            conn.commit()

    def apply_retention_policy(
        self,
        *,
        thresholds: dict[str, tuple[float, float, float]],
    ) -> dict[str, int]:
        """Evaluate all active/archived memories against retention thresholds.

        Classifies each memory into a retention stage (active, cold,
        archive_candidate, deprecated_candidate) and transitions status
        when warranted.

        Args:
            thresholds: Per-type (cold_min, archive_min, deprecated_min) tuples.

        Returns:
            Summary dict with counts per retention stage.
        """
        now = now_iso()
        rows = self.storage.fetch_all(
            """
            SELECT id, type, status, activation_score, archived_at, metadata_json
                 , confidence, access_count, last_accessed_at, updated_at, created_at
            FROM memories
            WHERE status IN ('active', 'archived')
            """
        )
        summary = {
            "cold": 0,
            "archive_candidate": 0,
            "deprecated_candidate": 0,
            "archived_now": 0,
        }
        for row in rows:
            thresholds_for_type = thresholds.get(row["type"], thresholds["episodic"])
            cold_min, archive_min, deprecated_min = thresholds_for_type
            score = float(row["activation_score"] or 0.0)
            if score > cold_min:
                stage = "active"
            elif score > archive_min:
                stage = "cold"
            elif score > deprecated_min:
                stage = "archive_candidate"
            else:
                stage = "deprecated_candidate"
            stage = self._apply_staleness_retention_guard(
                row=row,
                stage=stage,
                score=score,
                cold_min=cold_min,
            )
            self.storage._set_retention_stage(
                row["id"],
                stage=stage,
                current_status=row["status"],
                archived_at=row["archived_at"],
                at=now,
                score=score,
            )
            if stage in summary:
                summary[stage] += 1
            if row["status"] == "active" and stage in {"archive_candidate", "deprecated_candidate"}:
                summary["archived_now"] += 1
        return summary

    def _apply_staleness_retention_guard(
        self,
        *,
        row: Any,
        stage: str,
        score: float,
        cold_min: float,
    ) -> str:
        """Override retention stage for stale semantic memories.

        Guards against retaining low-value semantic memories that haven't
        been accessed in a long time, regardless of their activation score.

        Args:
            row:      Database row dict for the memory.
            stage:    Proposed retention stage.
            score:    Current activation score.
            cold_min: Cold threshold for this memory type.

        Returns:
            Possibly overridden retention stage string.
        """
        if row["status"] != "active" or row["type"] != "semantic":
            return stage

        metadata = self.storage._coerce_metadata(row["metadata_json"])
        if metadata.get("is_winner") or metadata.get("is_correction") or metadata.get("retention_pinned"):
            return stage

        last_ref = row["last_accessed_at"] or row["updated_at"] or row["created_at"]
        if not isinstance(last_ref, str):
            return stage
        try:
            last_time = datetime.fromisoformat(last_ref)
        except ValueError:
            return stage
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)

        dormant_days = (datetime.now(timezone.utc) - last_time).total_seconds() / SECONDS_PER_DAY
        confidence = float(row["confidence"] or 0.0)
        access_count = int(row["access_count"] or 0)

        if dormant_days >= STALENESS_ANNUAL_DAYS and access_count <= STALENESS_ANNUAL_MIN_ACCESS and confidence <= STALENESS_ANNUAL_CONFIDENCE and score <= max(cold_min, STALENESS_ANNUAL_SALIENCE):
            return "deprecated_candidate"
        if dormant_days >= STALENESS_QUARTERLY_DAYS and access_count <= STALENESS_QUARTERLY_MIN_ACCESS and confidence <= STALENESS_QUARTERLY_CONFIDENCE and score <= STALENESS_QUARTERLY_SALIENCE:
            return "archive_candidate"
        return stage

    def archive_expired(self, session_id: str | None = None) -> None:
        """Archive memories past their hard expiry date.

        Also archives working memories from the specified session.

        Args:
            session_id: Optional session whose working memories to archive.
        """
        now = now_iso()
        seen: set[str] = set()

        expired_rows = self.storage.fetch_all(
            """
            SELECT id, archived_at
            FROM memories
            WHERE status = 'active'
              AND expires_at IS NOT NULL
              AND expires_at < ?
            """,
            (now,),
        )
        for row in expired_rows:
            transition_memory(
                self.storage,
                row["id"],
                status="archived",
                event="archived_by_expiry",
                archived_at=row["archived_at"] or now,
                details={"reason": "hard_expiry"},
            )
            seen.add(row["id"])

        if session_id:
            session_rows = self.storage.fetch_all(
                """
                SELECT id, archived_at
                FROM memories
                WHERE status = 'active'
                  AND type = 'working'
                  AND session_id = ?
                """,
                (session_id,),
            )
            for row in session_rows:
                if row["id"] in seen:
                    continue
                transition_memory(
                    self.storage,
                    row["id"],
                    status="archived",
                    event="archived_on_session_end",
                    archived_at=row["archived_at"] or now,
                    details={"session_id": session_id},
                )

    def find_same_subject_peers(
        self,
        *,
        memory_id: str,
        scope_type: str,
        scope_id: str,
        subject: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find other retrievable memories with the same subject in a scope.

        Args:
            memory_id:  UUID to exclude (self).
            scope_type: Namespace kind.
            scope_id:   Namespace id.
            subject:    Subject key to match.
            limit:      Max results.

        Returns:
            List of row dicts with id, scope_type, scope_id, subject.
        """
        return [
            dict(row)
            for row in self.storage.fetch_all(
                f"""
                SELECT id, scope_type, scope_id, subject
                FROM memories
                WHERE id != ?
                  AND status IN ({RETRIEVABLE_MEMORY_STATUS_SQL})
                  AND scope_type = ?
                  AND scope_id = ?
                  AND subject = ?
                ORDER BY activation_score DESC, updated_at DESC
                LIMIT ?
                """,
                (memory_id, scope_type, scope_id, subject, limit),
            )
        ]

    def find_same_subject_typed_peers(
        self,
        *,
        memory_id: str,
        scope_type: str,
        scope_id: str,
        subject: str,
        peer_type: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find same-subject peers filtered to a specific memory type.

        Args:
            memory_id:  UUID to exclude (self).
            scope_type: Namespace kind.
            scope_id:   Namespace id.
            subject:    Subject key to match.
            peer_type:  Memory type filter (e.g. ``semantic``).
            limit:      Max results.

        Returns:
            List of row dicts with id, type, scope_type, scope_id, subject.
        """
        return [
            dict(row)
            for row in self.storage.fetch_all(
                f"""
                SELECT id, type, scope_type, scope_id, subject
                FROM memories
                WHERE id != ?
                  AND status IN ({RETRIEVABLE_MEMORY_STATUS_SQL})
                  AND scope_type = ?
                  AND scope_id = ?
                  AND subject = ?
                  AND type = ?
                ORDER BY activation_score DESC, updated_at DESC
                LIMIT ?
                """,
                (memory_id, scope_type, scope_id, subject, peer_type, limit),
            )
        ]

    def list_entity_peers(
        self,
        *,
        memory_id: str,
        scope_type: str,
        scope_id: str,
        entities: list[str],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find memories sharing entity overlap in metadata.

        Scans memories in the same scope and returns those whose metadata
        ``entities`` list intersects with the given entity set.

        Args:
            memory_id:  UUID to exclude (self).
            scope_type: Namespace kind.
            scope_id:   Namespace id.
            entities:   List of entity names to match.
            limit:      Max results.

        Returns:
            List of row dicts enriched with ``entity_overlap`` key.
        """
        if not entities:
            return []
        rows = self.storage.fetch_all(
            f"""
            SELECT *
            FROM memories
            WHERE id != ?
              AND status IN ({RETRIEVABLE_MEMORY_STATUS_SQL})
              AND scope_type = ?
              AND scope_id = ?
            ORDER BY activation_score DESC, updated_at DESC
            """,
            (memory_id, scope_type, scope_id),
        )
        matches: list[dict[str, Any]] = []
        entity_set = set(entities)
        for row in rows:
            payload = dict(row)
            metadata_raw = payload.get("metadata_json")
            metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw or {}
            peer_entities = metadata.get("entities") or []
            overlap = sorted(entity_set.intersection(peer_entities))
            if not overlap:
                continue
            payload["entity_overlap"] = overlap
            matches.append(payload)
            if len(matches) >= limit:
                break
        return matches
