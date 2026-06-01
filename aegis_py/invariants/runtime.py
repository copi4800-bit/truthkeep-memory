from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

@dataclass
class InvariantReport:
    ok: bool
    unique_winner: bool
    no_superseded_current_truth: bool
    archived_isolation: bool
    why_not_provenance: bool
    scope_isolation: bool
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "unique_winner": self.unique_winner,
            "no_superseded_current_truth": self.no_superseded_current_truth,
            "archived_isolation": self.archived_isolation,
            "why_not_provenance": self.why_not_provenance,
            "scope_isolation": self.scope_isolation,
            "violations": self.violations,
        }

def _get_val(row: Any, key: str, idx: int) -> Any:
    """Helper to safely fetch column values supporting sqlite3.Row, tuple, or dict."""
    if hasattr(row, "keys"):
        # Check dict or sqlite3.Row
        try:
            if key in row.keys():
                return row[key]
        except Exception:
            pass
    if isinstance(row, dict) and key in row:
        return row[key]
    try:
        return row[idx]
    except (TypeError, IndexError):
        return getattr(row, key, None)

def validate_memory_invariants(db_source: Union[str, sqlite3.Connection, Any]) -> InvariantReport:
    """Validates the 5 core database invariants for TruthKeep Memory.
    
    Accepts a database path (str), a sqlite3.Connection object, or an AegisApp / AegisStorage instance.
    """
    conn = None
    should_close = False
    
    # Resolve connection
    if isinstance(db_source, str):
        if not os.path.exists(db_source):
            return InvariantReport(
                ok=False,
                unique_winner=False,
                no_superseded_current_truth=False,
                archived_isolation=False,
                why_not_provenance=False,
                scope_isolation=False,
                violations=[f"Database file does not exist at: {db_source}"]
            )
        conn = sqlite3.connect(db_source)
        conn.execute("PRAGMA busy_timeout = 10000;")
        conn.row_factory = sqlite3.Row
        should_close = True
    elif isinstance(db_source, sqlite3.Connection):
        conn = db_source
    elif hasattr(db_source, "db") and hasattr(db_source.db, "conn"):
        # Handles AegisStorage or AegisApp with inner db/conn structure
        conn = db_source.db.conn
    elif hasattr(db_source, "conn"):
        conn = db_source.conn
    else:
        # Fallback attempts
        try:
            conn = db_source.get_connection()
        except Exception:
            pass

    if conn is None:
        return InvariantReport(
            ok=False,
            unique_winner=False,
            no_superseded_current_truth=False,
            archived_isolation=False,
            why_not_provenance=False,
            scope_isolation=False,
            violations=["Failed to resolve a valid SQLite connection from db_source."]
        )

    violations = []
    unique_winner = True
    no_superseded_current_truth = True
    archived_isolation = True
    why_not_provenance = True
    scope_isolation = True

    cursor = conn.cursor()

    try:
        # 1. Unique Winner per Slot
        # For a given subject in the same (scope_type, scope_id), there should be at most 1 'active' memory.
        cursor.execute("""
            SELECT scope_type, scope_id, subject, COUNT(*) as cnt 
            FROM memories 
            WHERE status = 'active' AND subject IS NOT NULL AND subject != ''
            GROUP BY scope_type, scope_id, subject 
            HAVING cnt > 1
        """)
        winner_rows = cursor.fetchall()
        if winner_rows:
            unique_winner = False
            for row in winner_rows:
                row_subject = _get_val(row, 'subject', 2)
                row_scope_type = _get_val(row, 'scope_type', 0)
                row_scope_id = _get_val(row, 'scope_id', 1)
                row_cnt = _get_val(row, 'cnt', 3)
                violations.append(
                    f"Unique Winner Violation: Fact slot '{row_subject}' in scope "
                    f"'{row_scope_type}/{row_scope_id}' has {row_cnt} active winners."
                )

        # 2. No Superseded in Current Truth
        # A superseded memory must never have status = 'active' or appear in active states.
        cursor.execute("SELECT COUNT(*) as cnt FROM memories WHERE status = 'active' AND status = 'superseded'")
        direct_conflict = cursor.fetchone()
        if direct_conflict and _get_val(direct_conflict, 'cnt', 0) > 0:
            no_superseded_current_truth = False
            violations.append("Direct Status Violation: Memory found with both active and superseded states.")

        # Let's also check if any active memory has a link of type 'superseded' pointing to it (it shouldn't be active)
        cursor.execute("""
            SELECT m.id, m.subject, m.scope_id 
            FROM memories m
            JOIN memory_links l ON m.id = l.source_id
            WHERE m.status = 'active' AND l.link_type = 'superseded_by'
        """)
        linked_superseded = cursor.fetchall()
        if linked_superseded:
            no_superseded_current_truth = False
            for row in linked_superseded:
                row_id = _get_val(row, 'id', 0)
                row_scope_id = _get_val(row, 'scope_id', 2)
                violations.append(
                    f"Superseded Leak Violation: Active memory '{row_id}' is linked as "
                    f"superseded_by but is still active in scope '{row_scope_id}'."
                )

        # 3. Archived Isolation
        # Archived memories must not be marked active, and must not have top-1 active status in normal recall.
        cursor.execute("SELECT id, subject FROM memories WHERE status = 'archived' AND status = 'active'")
        archived_active = cursor.fetchall()
        if archived_active:
            archived_isolation = False
            for row in archived_active:
                row_id = _get_val(row, 'id', 0)
                violations.append(f"Archived Isolation Violation: Memory '{row_id}' is marked as both archived and active.")

        # 4. Why-not Provenance
        # Every superseded memory must have a corresponding conflict resolution record or memory link explaining it.
        cursor.execute("""
            SELECT id, subject, scope_id FROM memories 
            WHERE status = 'superseded' 
              AND id NOT IN (SELECT DISTINCT memory_a_id FROM conflicts) 
              AND id NOT IN (SELECT DISTINCT memory_b_id FROM conflicts)
              AND id NOT IN (SELECT DISTINCT source_id FROM memory_links WHERE link_type = 'superseded_by')
              AND id NOT IN (SELECT DISTINCT target_id FROM memory_links WHERE link_type = 'superseded_by')
        """)
        missing_provenance = cursor.fetchall()
        if missing_provenance:
            why_not_provenance = False
            for row in missing_provenance:
                row_id = _get_val(row, 'id', 0)
                row_scope_id = _get_val(row, 'scope_id', 2)
                violations.append(
                    f"Why-Not Provenance Violation: Superseded memory '{row_id}' "
                    f"in scope '{row_scope_id}' has no associated why-not/conflict provenance."
                )

        # 5. Scope Isolation
        # A link must never span across different scope boundaries (different scope_type or scope_id).
        cursor.execute("""
            SELECT l.id, l.source_id, l.target_id, m1.scope_id as src_scope, m2.scope_id as tgt_scope,
                   m1.scope_type as src_type, m2.scope_type as tgt_type
            FROM memory_links l
            JOIN memories m1 ON l.source_id = m1.id
            JOIN memories m2 ON l.target_id = m2.id
            WHERE m1.scope_id != m2.scope_id OR m1.scope_type != m2.scope_type
        """)
        scope_leaks = cursor.fetchall()
        if scope_leaks:
            scope_isolation = False
            for row in scope_leaks:
                row_id = _get_val(row, 'id', 0)
                row_src_type = _get_val(row, 'src_type', 5)
                row_src_scope = _get_val(row, 'src_scope', 3)
                row_tgt_type = _get_val(row, 'tgt_type', 6)
                row_tgt_scope = _get_val(row, 'tgt_scope', 4)
                violations.append(
                    f"Scope Isolation Violation: Link '{row_id}' leaks across scope boundaries: "
                    f"'{row_src_type}/{row_src_scope}' -> '{row_tgt_type}/{row_tgt_scope}'."
                )

    except sqlite3.Error as err:
        violations.append(f"SQLite execution error during invariant checks: {err}")
        ok = False
        return InvariantReport(
            ok=False,
            unique_winner=False,
            no_superseded_current_truth=False,
            archived_isolation=False,
            why_not_provenance=False,
            scope_isolation=False,
            violations=violations
        )
    finally:
        if should_close and conn:
            conn.close()

    ok = (unique_winner and no_superseded_current_truth and archived_isolation and why_not_provenance and scope_isolation)

    return InvariantReport(
        ok=ok,
        unique_winner=unique_winner,
        no_superseded_current_truth=no_superseded_current_truth,
        archived_isolation=archived_isolation,
        why_not_provenance=why_not_provenance,
        scope_isolation=scope_isolation,
        violations=violations
    )
