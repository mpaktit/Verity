"""SQLite schema migrations for Verity."""

import sqlite3
from pathlib import Path

from app.db import get_db_path

CURRENT_VERSION = 1

MIGRATIONS = [
    # Version 1: initial schema
    """
    CREATE TABLE IF NOT EXISTS workers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'researcher',
        token TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS providers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        website TEXT,
        research_coverage REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'monitoring',
        risk_level TEXT NOT NULL DEFAULT 'medium',
        source_count INTEGER NOT NULL DEFAULT 0,
        signal TEXT,
        notes TEXT,
        last_scan TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        provider_id TEXT NOT NULL,
        source_type TEXT NOT NULL,
        url TEXT NOT NULL,
        last_checked_at TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        http_status INTEGER,
        content_hash TEXT,
        last_content TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS offers (
        id TEXT PRIMARY KEY,
        provider_id TEXT NOT NULL,
        title TEXT NOT NULL,
        product TEXT NOT NULL,
        category TEXT NOT NULL,
        offer_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        reward TEXT NOT NULL,
        eligibility TEXT NOT NULL,
        source_url TEXT,
        risk_level TEXT NOT NULL DEFAULT 'medium',
        official INTEGER NOT NULL DEFAULT 1,
        verified INTEGER NOT NULL DEFAULT 0,
        score INTEGER NOT NULL DEFAULT 0,
        expires_at TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS evidence (
        id TEXT PRIMARY KEY,
        offer_id TEXT NOT NULL,
        source_url TEXT NOT NULL,
        screenshot_url TEXT,
        note TEXT,
        validated_by TEXT,
        validated_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS research_runs (
        id TEXT PRIMARY KEY,
        provider_id TEXT NOT NULL,
        triggered_at TEXT NOT NULL,
        source_count INTEGER NOT NULL DEFAULT 0,
        findings TEXT,
        confidence REAL,
        status TEXT NOT NULL DEFAULT 'completed',
        created_at TEXT NOT NULL,
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        provider_id TEXT,
        provider_name TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'medium',
        status TEXT NOT NULL DEFAULT 'queued',
        category TEXT NOT NULL,
        summary TEXT NOT NULL,
        approaches TEXT NOT NULL,
        signals TEXT NOT NULL,
        last_action TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_attempts (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        worker_id TEXT NOT NULL,
        approach TEXT NOT NULL,
        notes TEXT NOT NULL,
        evidence_urls TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_reviews (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        reviewer_id TEXT NOT NULL,
        decision TEXT NOT NULL,
        notes TEXT NOT NULL,
        requires_manager_approval INTEGER NOT NULL DEFAULT 0,
        manager_decision TEXT,
        manager_notes TEXT,
        reviewed_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (reviewer_id) REFERENCES workers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        provider_id TEXT,
        severity TEXT NOT NULL DEFAULT 'medium',
        status TEXT NOT NULL DEFAULT 'active',
        last_checked TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        worker_id TEXT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        metadata TEXT,
        ip_address TEXT,
        user_agent TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlists (
        id TEXT PRIMARY KEY,
        worker_id TEXT NOT NULL,
        name TEXT NOT NULL,
        filters TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    )
    """,
    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_offers_provider ON offers(provider_id)",
    "CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status)",
    "CREATE INDEX IF NOT EXISTS idx_offers_score ON offers(score)",
    "CREATE INDEX IF NOT EXISTS idx_sources_provider ON sources(provider_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_provider ON tasks(provider_name)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_evidence_offer ON evidence(offer_id)",
    "CREATE INDEX IF NOT EXISTS idx_research_runs_provider ON research_runs(provider_id)",
]


def get_current_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            'SELECT COALESCE(MAX(version), 0) FROM schema_migrations'
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def run_migrations() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)'
        )
        conn.commit()

        current = get_current_version(conn)

        for index, migration_sql in enumerate(MIGRATIONS, start=1):
            if index <= current:
                continue
            conn.executescript(migration_sql)
            conn.execute(
                'INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)',
                (index, _now()),
            )
            conn.commit()

    finally:
        conn.close()


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()