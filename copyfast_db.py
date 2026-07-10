"""Web-only persistence for authentication, CSRF and audit records.

This database never stores a wallet balance, PayOS order, job result, or
provider payload. Those values remain canonical in the Telegram bot and are
retrieved through the private bridge.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def transaction():
    configured = os.environ.get("WEBAPP_SESSION_DB_PATH", "").strip()
    if configured:
        path = configured
    elif os.path.isdir("/data"):
        path = "/data/toanaas_webapp_session.db"
    else:
        path = "toanaas_webapp_session.db"
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_copyfast_schema() -> None:
    """Create additive, idempotent tables owned solely by the web app."""
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_accounts (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                canonical_user_id TEXT UNIQUE,
                role_cache TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_sessions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                csrf_token TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_link_codes (
                code_hash TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                canonical_user_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_idempotency (
                scope TEXT NOT NULL,
                key TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(scope, key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_audit_events (
                id TEXT PRIMARY KEY,
                account_id TEXT,
                canonical_user_id TEXT,
                action TEXT NOT NULL,
                request_id TEXT NOT NULL,
                target TEXT,
                outcome TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_sessions_account ON web_sessions(account_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audit_created ON web_audit_events(created_at)"
        )


def as_row(row: sqlite3.Row | tuple | None, columns: tuple[str, ...]) -> dict | None:
    if row is None:
        return None
    return dict(zip(columns, row))
