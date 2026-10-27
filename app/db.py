"""Database connection management for Verity."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

_db_path = Path(settings.DATABASE_URL.replace('sqlite:///', ''))


def get_db_path() -> Path:
    return _db_path


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(_db_path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA busy_timeout = 5000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    from app.migrate import run_migrations
    run_migrations()