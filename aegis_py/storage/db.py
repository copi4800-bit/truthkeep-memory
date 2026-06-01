from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Iterable, Optional


class DatabaseManager:
    """SQLite connection manager for the Python Aegis runtime."""

    def __init__(self, db_path: str = "memory_aegis.db"):
        self.db_path = db_path
        import threading
        self._local = threading.local()

    @property
    def conn(self) -> Optional[sqlite3.Connection]:
        if hasattr(self._local, "conn"):
            return self._local.conn
        return None

    @conn.setter
    def conn(self, value: Optional[sqlite3.Connection]):
        self._local.conn = value

    def connect(self) -> sqlite3.Connection:
        if self.conn is None:
            if self.db_path != ":memory:":
                Path(self.db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = ON;")
            if self.db_path != ":memory:":
                self.conn.execute("PRAGMA journal_mode = WAL;")
                self.conn.execute("PRAGMA synchronous = NORMAL;")
                self.conn.execute("PRAGMA busy_timeout = 10000;")
            self.conn.row_factory = sqlite3.Row
            
            # Đăng ký các hàm nhận thức toán học cổ đại vào SQLite
            from aegis_py.storage.ancient_math import IChingStateEncoder, LuoshuIntegrityValidator
            
            def sql_iching_state(kind, status, confidence, metadata_json_str):
                import json
                try:
                    metadata = json.loads(metadata_json_str or "{}")
                except Exception:
                    metadata = {}
                is_immutable = metadata.get("is_immutable", False)
                is_winner = metadata.get("is_winner", False)
                
                # Xác định trạng thái tin cậy (trust)
                if is_immutable:
                    trust = "immutable"
                elif status in ("reconcile_required", "conflict_candidate"):
                    trust = "disputed"
                elif (confidence or 1.0) >= 0.85:
                    trust = "verified"
                else:
                    trust = "unverified"
                    
                # Xác định trạng thái sự thật (truth)
                if is_winner:
                    truth = "winner"
                elif status == "superseded":
                    truth = "superseded"
                elif status == "archived":
                    truth = "archived"
                else:
                    truth = "candidate"
                    
                return IChingStateEncoder.encode_state(kind or "semantic", truth, trust)
                
            def sql_luoshu_checksum(status, confidence, activation_score, metadata_json_str):
                import json
                try:
                    metadata = json.loads(metadata_json_str or "{}")
                except Exception:
                    metadata = {}
                is_immutable = metadata.get("is_immutable", False)
                
                # Xác định trạng thái tin cậy (trust)
                if is_immutable:
                    trust_str = "immutable"
                elif status in ("reconcile_required", "conflict_candidate"):
                    trust_str = "disputed"
                elif (confidence or 1.0) >= 0.85:
                    trust_str = "verified"
                else:
                    trust_str = "unverified"
                    
                trust_val = 0.9 if trust_str in ("verified", "immutable") else (0.3 if trust_str == "disputed" else 0.6)
                conf_val = confidence if confidence is not None else 1.0
                rel_val = activation_score if activation_score is not None else 0.9
                
                encrypted = LuoshuIntegrityValidator.encrypt_weights([trust_val, conf_val, rel_val])
                _, checksum = LuoshuIntegrityValidator.validate_node_integrity(encrypted)
                return checksum
                
            self.conn.create_function("iching_state_calc", 4, sql_iching_state)
            self.conn.create_function("luoshu_checksum_calc", 4, sql_luoshu_checksum)
        return self.conn

    def initialize(self) -> None:
        conn = self.connect()
        migrations_dir = Path(__file__).parent / "migrations"
        
        from aegis_py.ops.migration import MigrationManager
        migrator = MigrationManager(conn, str(migrations_dir))
        migrator.run_migrations()

    def execute(self, query: str, params: Iterable = ()) -> sqlite3.Cursor:
        conn = self.connect()
        cursor = conn.execute(query, tuple(params))
        conn.commit()
        return cursor

    def executemany(self, query: str, rows: Iterable[Iterable]) -> None:
        conn = self.connect()
        conn.executemany(query, rows)
        conn.commit()

    def fetch_all(self, query: str, params: Iterable = ()) -> list[sqlite3.Row]:
        conn = self.connect()
        cursor = conn.execute(query, tuple(params))
        return cursor.fetchall()

    def fetch_one(self, query: str, params: Iterable = ()) -> sqlite3.Row | None:
        conn = self.connect()
        cursor = conn.execute(query, tuple(params))
        return cursor.fetchone()

    def put_memory(self, memory) -> str:
        from ..hygiene.transitions import now_iso

        memory_id = getattr(memory, "id", None) or str(uuid.uuid4())
        metadata = dict(getattr(memory, "metadata", {}) or {})
        now = now_iso()
        
        # Tính toán trạng thái nhận thức Kinh Dịch và Lạc Thư
        from aegis_py.storage.ancient_math import compute_memory_ancient_math_fields
        temp_data = {
            "type": memory.type,
            "status": getattr(memory, "status", "active"),
            "confidence": getattr(memory, "confidence", 1.0),
            "activation_score": getattr(memory, "activation_score", 1.0),
            "metadata_json": metadata,
        }
        iching, checksum = compute_memory_ancient_math_fields(temp_data)
        
        # Tính toán trường toán học hiện đại (Erdős + Poincaré TDA)
        from aegis_py.storage.modern_math import compute_memory_modern_math_fields
        modern_fields = compute_memory_modern_math_fields(
            memory.content,
            subject=getattr(memory, "subject", None),
            summary=getattr(memory, "summary", None),
        )
        erdos_cell_id = modern_fields["erdos_cell_id"]
        tda_signature = modern_fields["tda_signature"]
        
        self.execute(
            """
            INSERT INTO memories (
                id, type, scope_type, scope_id, session_id, content, summary, subject,
                source_kind, source_ref, status, confidence, activation_score, access_count,
                created_at, updated_at, last_accessed_at, expires_at, archived_at, metadata_json,
                iching_state, luoshu_checksum, erdos_cell_id, tda_signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                memory.type,
                memory.scope_type,
                memory.scope_id,
                getattr(memory, "session_id", None),
                memory.content,
                getattr(memory, "summary", None),
                getattr(memory, "subject", None),
                memory.source_kind,
                getattr(memory, "source_ref", None),
                getattr(memory, "status", "active"),
                getattr(memory, "confidence", 1.0),
                getattr(memory, "activation_score", 1.0),
                getattr(memory, "access_count", 0),
                now,
                now,
                getattr(memory, "last_accessed_at", None),
                getattr(memory, "expires_at", None),
                getattr(memory, "archived_at", None),
                json.dumps(metadata, ensure_ascii=True),
                iching,
                checksum,
                erdos_cell_id,
                tda_signature,
            ),
        )
        return memory_id

    def record_evidence_artifact(
        self,
        *,
        artifact_kind: str,
        scope_type: str,
        scope_id: str,
        payload: dict,
        memory_id: str | None = None,
        evidence_event_id: str | None = None,
    ) -> str:
        from ..hygiene.transitions import now_iso

        artifact_id = f"art_{uuid.uuid4().hex[:16]}"
        self.execute(
            """
            INSERT INTO evidence_artifacts (
                id, artifact_kind, scope_type, scope_id, memory_id, evidence_event_id, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                artifact_kind,
                scope_type,
                scope_id,
                memory_id,
                evidence_event_id,
                json.dumps(payload, ensure_ascii=True),
                now_iso(),
            ),
        )
        return artifact_id

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None
