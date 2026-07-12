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


def _is_production() -> bool:
    values = (
        os.environ.get("APP_ENV", ""),
        os.environ.get("ENVIRONMENT", ""),
        os.environ.get("RAILWAY_ENVIRONMENT", ""),
    )
    return any(value.strip().lower() in {"production", "prod"} for value in values if value)


def _railway_volume_directory() -> Path | None:
    """Return a declared Railway volume only when it exists in this service.

    Railway lets a service choose a custom mount path. The environment name can
    also be present in configuration shared with another service, so it is not
    evidence that this Web service has a volume by itself. Require an absolute,
    existing directory before using it for signed-session data.
    """
    configured = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if not configured:
        return None
    candidate = Path(configured).expanduser()
    if not candidate.is_absolute() or not os.path.isdir(candidate):
        return None
    return candidate


def _persistent_session_directory() -> Path | None:
    """Find a known persistent volume directory without creating one."""
    railway_volume = _railway_volume_directory()
    if railway_volume is not None:
        return railway_volume
    if os.path.isdir("/data"):
        return Path("/data")
    return None


def session_database_path() -> str:
    """Resolve the Web-owned auth/session database without using a Bot store."""
    configured = os.environ.get("WEBAPP_SESSION_DB_PATH", "").strip()
    if configured:
        return configured
    persistent_directory = _persistent_session_directory()
    if persistent_directory is not None:
        return str(persistent_directory / "toanaas_webapp_session.db")
    return "toanaas_webapp_session.db"


def ensure_copyfast_persistence() -> None:
    """Fail closed when production auth data would disappear on restart.

    Telegram link codes, signed sessions and callback nonces must survive a
    normal Railway restart. A local relative SQLite file is fine for tests and
    local development, but is never a production persistence plan.
    """
    if not _is_production():
        return
    configured = os.environ.get("WEBAPP_SESSION_DB_PATH", "").strip()
    if configured:
        if not Path(configured).expanduser().is_absolute():
            raise RuntimeError("WEBAPP_SESSION_DB_PATH phải là đường dẫn tuyệt đối khi production")
        return
    if _persistent_session_directory() is not None:
        return
    raise RuntimeError(
        "Production cần WEBAPP_SESSION_DB_PATH trên persistent volume, "
        "RAILWAY_VOLUME_MOUNT_PATH hợp lệ, hoặc mount /data cho signed session và Telegram link"
    )


@contextmanager
def transaction():
    path = session_database_path()
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
                bot_confirmed_at TEXT,
                confirmed_role TEXT,
                confirmed_display_name TEXT,
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
        # A Bot callback proves the Telegram identity, but a CSRF-protected
        # browser completion by the same initiating session commits it to the
        # Web account.  Keep the pending callback metadata on the one-time
        # row, never in a browser cookie or local storage.
        if "bot_confirmed_at" not in link_columns:
            conn.execute("ALTER TABLE telegram_link_codes ADD COLUMN bot_confirmed_at TEXT")
        if "confirmed_role" not in link_columns:
            conn.execute("ALTER TABLE telegram_link_codes ADD COLUMN confirmed_role TEXT")
        if "confirmed_display_name" not in link_columns:
            conn.execute("ALTER TABLE telegram_link_codes ADD COLUMN confirmed_display_name TEXT")
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
        # A short-lived receipt binds a Web feature confirm to an estimate
        # observed by this signed session.  It deliberately stores only
        # one-way hashes and timing/binding metadata: never prompt text,
        # quote price, provider data, job state, output, wallet or PayOS data.
        # The Telegram Bot remains the canonical quote/charge/job authority.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_feature_quote_receipts (
                token_hash TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                canonical_user_id TEXT NOT NULL,
                feature_key TEXT NOT NULL,
                input_digest TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                claimed_key_hash TEXT,
                claimed_at TEXT,
                consumed_at TEXT,
                created_at TEXT NOT NULL
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
        # Campaign Planner deliberately owns only Web planning metadata.  It
        # is not a mirror of the Bot's campaign, publishing, analytics,
        # wallet, PayOS or provider state.  Keeping a distinct table name
        # prevents older experimental `campaigns` schemas from being reused
        # with a different ownership/security contract.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_campaign_plans (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                title TEXT NOT NULL,
                destination_url TEXT NOT NULL,
                platform TEXT NOT NULL,
                objective TEXT NOT NULL,
                scheduled_for TEXT,
                approval_status TEXT NOT NULL DEFAULT 'draft',
                review_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Workspace drafts are Web-owned authoring notes, never a mirror of
        # Bot feature input, upload staging, quotes, jobs, wallet or provider
        # state.  Keeping their table separate makes the ownership boundary
        # explicit and lets a signed customer resume only safe scalar fields.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workspace_drafts (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                feature_key TEXT NOT NULL,
                title TEXT NOT NULL,
                input_json TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_sessions_account ON web_sessions(account_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audit_created ON web_audit_events(created_at)"
        )
        # Customer activity reads are owner-scoped and newest-first. This
        # additive index avoids a full audit-table scan without changing the
        # append-only audit contract or reusing the Bot audit database.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audit_account_created ON web_audit_events(account_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workspace_drafts_account_state_updated ON web_workspace_drafts(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_bridge_callback_nonce_expiry ON web_bridge_callback_nonces(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_telegram_login_browser ON telegram_login_codes(browser_token_hash, expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_telegram_link_session ON telegram_link_codes(account_id, initiating_session_id, expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_oauth_state_expiry ON web_oauth_states(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_external_identity_account ON web_external_identities(account_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_feature_quote_receipts_expiry ON web_feature_quote_receipts(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_feature_quote_receipts_session ON web_feature_quote_receipts(account_id, session_id, expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_campaign_plans_account_status_schedule ON web_campaign_plans(account_id, approval_status, scheduled_for)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_campaign_plans_account_updated ON web_campaign_plans(account_id, updated_at DESC)"
        )


def as_row(row: sqlite3.Row | tuple | None, columns: tuple[str, ...]) -> dict | None:
    if row is None:
        return None
    return dict(zip(columns, row))
