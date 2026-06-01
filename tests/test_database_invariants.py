from __future__ import annotations

import os
import sqlite3
import pytest
from aegis_py.invariants.runtime import validate_memory_invariants, InvariantReport


@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary SQLite database with the baseline schema for testing."""
    db_path = str(tmp_path / "test_invariants.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Simple baseline schema matching memories and memory_links
    cursor.execute("""
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            scope_type TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            session_id TEXT,
            content TEXT NOT NULL,
            summary TEXT,
            subject TEXT,
            source_kind TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            confidence REAL NOT NULL DEFAULT 1.0,
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE memory_links (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            link_type TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 1.0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE conflicts (
            id TEXT PRIMARY KEY,
            memory_a_id TEXT NOT NULL,
            memory_b_id TEXT NOT NULL,
            subject_key TEXT,
            resolution TEXT
        )
    """)
    
    conn.commit()
    yield conn
    conn.close()


def test_invariants_all_green_empty(temp_db):
    """Verifies that an empty database passes all invariants."""
    report = validate_memory_invariants(temp_db)
    assert report.ok is True
    assert report.unique_winner is True
    assert report.no_superseded_current_truth is True
    assert report.archived_isolation is True
    assert report.why_not_provenance is True
    assert report.scope_isolation is True
    assert len(report.violations) == 0


def test_invariants_unique_winner_violation(temp_db):
    """Verifies that multiple active memories in the same slot trigger a violation."""
    cursor = temp_db.cursor()
    
    # Insert two active memories with the same subject in the same scope
    cursor.execute("""
        INSERT INTO memories (id, type, scope_type, scope_id, content, subject, source_kind, status)
        VALUES 
            ('mem_1', 'semantic', 'session', 'user_a', 'Bao likes coffee', 'coffee_pref', 'direct', 'active'),
            ('mem_2', 'semantic', 'session', 'user_a', 'Bao likes green tea', 'coffee_pref', 'direct', 'active')
    """)
    temp_db.commit()
    
    report = validate_memory_invariants(temp_db)
    assert report.ok is False
    assert report.unique_winner is False
    assert any("Unique Winner Violation" in v for v in report.violations)


def test_invariants_superseded_leak_violation(temp_db):
    """Verifies that an active memory linked as superseded triggers a violation."""
    cursor = temp_db.cursor()
    
    # Insert memory and link
    cursor.execute("""
        INSERT INTO memories (id, type, scope_type, scope_id, content, subject, source_kind, status)
        VALUES ('mem_1', 'semantic', 'session', 'user_a', 'Old preference', 'pref', 'direct', 'active')
    """)
    cursor.execute("""
        INSERT INTO memory_links (id, source_id, target_id, link_type)
        VALUES ('link_1', 'mem_1', 'mem_2', 'superseded_by')
    """)
    temp_db.commit()
    
    report = validate_memory_invariants(temp_db)
    assert report.ok is False
    assert report.no_superseded_current_truth is False
    assert any("Superseded Leak Violation" in v for v in report.violations)


def test_invariants_why_not_provenance_violation(temp_db):
    """Verifies that a superseded memory with no history/links triggers a violation."""
    cursor = temp_db.cursor()
    
    # Insert superseded memory with no links or conflict resolutions
    cursor.execute("""
        INSERT INTO memories (id, type, scope_type, scope_id, content, subject, source_kind, status)
        VALUES ('mem_1', 'semantic', 'session', 'user_a', 'Superseded info', 'pref', 'direct', 'superseded')
    """)
    temp_db.commit()
    
    report = validate_memory_invariants(temp_db)
    assert report.ok is False
    assert report.why_not_provenance is False
    assert any("Why-Not Provenance Violation" in v for v in report.violations)


def test_invariants_scope_isolation_violation(temp_db):
    """Verifies that a memory link spanning different scopes triggers a violation."""
    cursor = temp_db.cursor()
    
    # Insert memories in different scopes
    cursor.execute("""
        INSERT INTO memories (id, type, scope_type, scope_id, content, subject, source_kind, status)
        VALUES 
            ('mem_1', 'semantic', 'session', 'user_a', 'Info A', 'pref', 'direct', 'active'),
            ('mem_2', 'semantic', 'session', 'user_b', 'Info B', 'pref', 'direct', 'active')
    """)
    # Link them
    cursor.execute("""
        INSERT INTO memory_links (id, source_id, target_id, link_type)
        VALUES ('link_1', 'mem_1', 'mem_2', 'supports')
    """)
    temp_db.commit()
    
    report = validate_memory_invariants(temp_db)
    assert report.ok is False
    assert report.scope_isolation is False
    assert any("Scope Isolation Violation" in v for v in report.violations)
