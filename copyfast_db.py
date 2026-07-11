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
                password_login_enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        account_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_accounts)").fetchall()}
        if "password_login_enabled" not in account_columns:
            conn.execute("ALTER TABLE web_accounts ADD COLUMN password_login_enabled INTEGER NOT NULL DEFAULT 1")
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
        # Minimal Web-owned profile defaults. This is presentation/session
        # metadata only; it never mirrors Telegram identity, Xu, PayOS, jobs
        # or provider state from the Bot.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_account_profiles (
                account_id TEXT PRIMARY KEY,
                locale TEXT NOT NULL DEFAULT 'vi',
                timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
                avatar_style TEXT NOT NULL DEFAULT 'gradient',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
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
                initiating_session_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Older COPYFAST databases were created before link codes recorded
        # the initiating session.  This is deliberately additive: it lets a
        # successful Telegram callback revoke *other* sessions without
        # logging out the browser that created the one-time code.
        link_columns = {row[1] for row in conn.execute("PRAGMA table_info(telegram_link_codes)").fetchall()}
        if "initiating_session_id" not in link_columns:
            conn.execute("ALTER TABLE telegram_link_codes ADD COLUMN initiating_session_id TEXT")
        # Telegram passwordless sign-in uses a separate, browser-bound
        # challenge.  It never stores a raw Telegram ID in a cookie or allows
        # a browser to submit one.  The bot callback is still the authority
        # that proves the Telegram identity.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_login_codes (
                code_hash TEXT PRIMARY KEY,
                browser_token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                canonical_user_id TEXT,
                failure_code TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        login_columns = {row[1] for row in conn.execute("PRAGMA table_info(telegram_login_codes)").fetchall()}
        if "failure_code" not in login_columns:
            conn.execute("ALTER TABLE telegram_login_codes ADD COLUMN failure_code TEXT")
        # OAuth identity data belongs to the Web account layer.  Subjects are
        # HMAC-hashed before storage; no provider access/refresh token is ever
        # persisted.  The Bot remains the sole authority for Telegram and all
        # billing, wallet, job and provider-engine state.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_oauth_states (
                state_hash TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                purpose TEXT NOT NULL,
                account_id TEXT,
                initiating_session_id TEXT,
                return_path TEXT NOT NULL DEFAULT '/',
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_external_identities (
                provider TEXT NOT NULL,
                subject_hash TEXT NOT NULL,
                account_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL,
                PRIMARY KEY(provider, subject_hash),
                UNIQUE(account_id, provider),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_bridge_callback_nonces (
                request_id TEXT PRIMARY KEY,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_bridge_callback_nonce_expiry ON web_bridge_callback_nonces(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_telegram_login_browser ON telegram_login_codes(browser_token_hash, expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_oauth_state_expiry ON web_oauth_states(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_external_identity_account ON web_external_identities(account_id)"
        )


def as_row(row: sqlite3.Row | tuple | None, columns: tuple[str, ...]) -> dict | None:
    if row is None:
        return None
    return dict(zip(columns, row))
