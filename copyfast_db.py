"""Web-owned persistence for account, project, authoring and audit records.

The standalone Web App owns its sessions, projects and Studio Documents. It
never stores a Telegram-Bot Xu ledger, PayOS webhook/order authority, or raw
third-party provider credential/payload. Bot connectivity is an optional
integration, not the database authority for Web-owned work.
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


def asset_vault_enabled() -> bool:
    """Whether the private, Web-owned Asset Vault is deliberately enabled."""
    return os.environ.get("WEBAPP_ASSET_VAULT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def project_package_enabled() -> bool:
    """Whether immutable, Web-owned Project Package exports are enabled.

    Package exports have a separate storage boundary from Asset Vault uploads.
    They stay opt-in because a completed package is a private downloadable
    artifact and production must never place it on an ephemeral filesystem.
    """
    return os.environ.get("WEBAPP_PROJECT_PACKAGE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def document_operations_enabled() -> bool:
    """Whether bounded, Web-native document operations are deliberately enabled."""
    return os.environ.get("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def image_to_pdf_enabled() -> bool:
    """Whether the Pillow-backed Image-to-PDF decoder is deliberately enabled.

    This stays separate from the base Document Operations flag because image
    decoding has its own dependency and memory boundary.  Its route still
    requires the Asset Vault and generated-output storage contracts.
    """
    return os.environ.get("WEBAPP_IMAGE_TO_PDF_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def pdf_to_word_enabled() -> bool:
    """Whether the private PDF-text-to-DOCX exporter is deliberately enabled.

    This remains independent from the base document switch: a DOCX writer is
    not the same runtime boundary as PDF parsing, and a disabled exporter must
    fail closed rather than advertising an OCR or layout-conversion service.
    """
    return os.environ.get("WEBAPP_PDF_TO_WORD_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def pdf_to_images_enabled() -> bool:
    """Whether the private PDFium-backed PDF-to-images renderer is enabled.

    Rendering is a decoder and disk-amplification boundary distinct from PDF
    parsing or DOCX export.  Keep it independently fail-closed so enabling
    Document Operations never silently enables rasterization work.
    """
    return os.environ.get("WEBAPP_PDF_TO_IMAGES_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def image_operations_enabled() -> bool:
    """Whether bounded, Web-native private image operations are enabled.

    Image transformations are deliberately a separate runtime and storage
    boundary from document operations.  They consume immutable Asset Vault
    sources and create new private artifacts; they are never Bot jobs,
    provider calls, wallet entries or payment actions.
    """
    return os.environ.get("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def image_resize_enabled() -> bool:
    """Whether the Pillow-backed Resize & Aspect Studio executor is enabled.

    A narrow switch lets production keep the image-operation storage boundary
    prepared while still failing closed until this decoder-backed operation is
    explicitly reviewed and enabled.
    """
    return os.environ.get("WEBAPP_IMAGE_RESIZE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def image_enhance_enabled() -> bool:
    """Whether the bounded local Image Enhance Studio executor is enabled.

    This flag is deliberately narrower than the shared Image Operations
    storage boundary.  It only unlocks deterministic Pillow adjustments and
    never grants a provider-backed AI edit, Bot job, wallet mutation or
    payment action.
    """
    return os.environ.get("WEBAPP_IMAGE_ENHANCE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def memory_center_enabled() -> bool:
    """Whether the Web-owned Memory Center is available to signed accounts.

    Notes and reminders use the existing persistent Web session database and
    no provider, Bot, wallet or payment runtime.  They are therefore useful
    by default, while an operator can still turn the complete Web-owned
    surface off with an explicit false value during maintenance.
    """
    return os.environ.get("WEBAPP_MEMORY_CENTER_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def asset_vault_directory() -> Path:
    """Resolve the dedicated private blob directory for the Web Asset Vault.

    The directory is never mounted as static content.  In production it must
    live *under* the service's persistent volume, not merely on an arbitrary
    absolute filesystem path.  Local development gets an isolated sibling of
    the configured Web session database so test data cannot leak into source
    files or the legacy Bot asset area.
    """
    if not asset_vault_enabled():
        raise RuntimeError("WEBAPP_ASSET_VAULT_ENABLED chưa được bật")

    configured = os.environ.get("WEBAPP_ASSET_VAULT_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_ASSET_VAULT_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        if persistent_directory is not None:
            candidate = persistent_directory / "toanaas_webapp_assets"
        else:
            database_parent = Path(session_database_path()).expanduser().resolve().parent
            candidate = database_parent / "toanaas_webapp_assets"

    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_ASSET_VAULT_ROOT không được nằm trong static")

    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError(
                "Asset Vault production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data"
            )
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError(
                "WEBAPP_ASSET_VAULT_ROOT phải là thư mục con của persistent volume khi production"
            )

    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise RuntimeError("WEBAPP_ASSET_VAULT_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_asset_vault_persistence() -> Path | None:
    """Validate the vault boundary before the app serves enabled uploads."""
    if not asset_vault_enabled():
        return None
    return asset_vault_directory()


def project_package_directory() -> Path:
    """Resolve a private artifact root for immutable Project Packages.

    This root deliberately never shares Asset Vault's directory, is never
    mounted as static content, and must be a child of the service's persistent
    volume in production.  Keeping the two roots separate prevents a package
    export from being mistaken for a customer-uploaded source file.
    """
    if not project_package_enabled():
        raise RuntimeError("WEBAPP_PROJECT_PACKAGE_ENABLED chưa được bật")

    configured = os.environ.get("WEBAPP_PROJECT_PACKAGE_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_PROJECT_PACKAGE_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        if persistent_directory is not None:
            candidate = persistent_directory / "toanaas_webapp_project_packages"
        else:
            database_parent = Path(session_database_path()).expanduser().resolve().parent
            candidate = database_parent / "toanaas_webapp_project_packages"

    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_PROJECT_PACKAGE_ROOT không được nằm trong static")

    if asset_vault_enabled():
        vault_directory = asset_vault_directory().resolve()
        if candidate == vault_directory or _is_within(candidate, vault_directory) or _is_within(vault_directory, candidate):
            raise RuntimeError("WEBAPP_PROJECT_PACKAGE_ROOT phải tách riêng Asset Vault")

    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError(
                "Project Package production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data"
            )
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError(
                "WEBAPP_PROJECT_PACKAGE_ROOT phải là thư mục con của persistent volume khi production"
            )

    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise RuntimeError("WEBAPP_PROJECT_PACKAGE_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_project_package_persistence() -> Path | None:
    """Validate the private Project Package artifact boundary when enabled."""
    if not project_package_enabled():
        return None
    return project_package_directory()


def document_operations_directory() -> Path:
    """Resolve the isolated private root for generated document outputs.

    Document operations consume verified Asset Vault inputs but must never
    write their generated files back into the input vault or Project Package
    archive.  A distinct root also makes any later retention policy explicit.
    """
    if not document_operations_enabled():
        raise RuntimeError("WEBAPP_DOCUMENT_OPERATIONS_ENABLED chưa được bật")

    configured = os.environ.get("WEBAPP_DOCUMENT_OPERATIONS_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_DOCUMENT_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        if persistent_directory is not None:
            candidate = persistent_directory / "toanaas_webapp_document_operations"
        else:
            database_parent = Path(session_database_path()).expanduser().resolve().parent
            candidate = database_parent / "toanaas_webapp_document_operations"

    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_DOCUMENT_OPERATIONS_ROOT không được nằm trong static")

    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError("WEBAPP_DOCUMENT_OPERATIONS_ROOT phải tách riêng Asset Vault và Project Package")

    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError(
                "Document Operations production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data"
            )
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError(
                "WEBAPP_DOCUMENT_OPERATIONS_ROOT phải là thư mục con của persistent volume khi production"
            )

    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise RuntimeError("WEBAPP_DOCUMENT_OPERATIONS_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_document_operations_persistence() -> Path | None:
    """Validate the private generated-document storage boundary when enabled."""
    if not document_operations_enabled():
        return None
    # PDF Split intentionally accepts only an integrity-checked Asset Vault
    # input. Do not expose a misleading "enabled" document runtime when that
    # private input boundary is absent.
    if not asset_vault_enabled():
        raise RuntimeError("Document Operations cần WEBAPP_ASSET_VAULT_ENABLED=true")
    return document_operations_directory()


def image_operations_directory() -> Path:
    """Resolve the private output root for Web-native image operations.

    This must remain distinct from uploads, Project Package archives and
    generated documents.  Keeping a separate root makes retention, backup and
    incident response explicit, and prevents a generated PNG from ever being
    confused with a source Asset Vault object.
    """
    if not image_operations_enabled():
        raise RuntimeError("WEBAPP_IMAGE_OPERATIONS_ENABLED chưa được bật")

    configured = os.environ.get("WEBAPP_IMAGE_OPERATIONS_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_IMAGE_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        if persistent_directory is not None:
            candidate = persistent_directory / "toanaas_webapp_image_operations"
        else:
            database_parent = Path(session_database_path()).expanduser().resolve().parent
            candidate = database_parent / "toanaas_webapp_image_operations"

    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_IMAGE_OPERATIONS_ROOT không được nằm trong static")

    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    if document_operations_enabled():
        private_roots.append(document_operations_directory().resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError(
                "WEBAPP_IMAGE_OPERATIONS_ROOT phải tách riêng Asset Vault, Project Package và Document Operations"
            )

    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError(
                "Image Operations production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data"
            )
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError(
                "WEBAPP_IMAGE_OPERATIONS_ROOT phải là thư mục con của persistent volume khi production"
            )

    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise RuntimeError("WEBAPP_IMAGE_OPERATIONS_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_image_operations_persistence() -> Path | None:
    """Validate private inputs/outputs before an enabled image runtime serves."""
    if not image_operations_enabled():
        return None
    if not asset_vault_enabled():
        raise RuntimeError("Image Operations cần WEBAPP_ASSET_VAULT_ENABLED=true")
    return image_operations_directory()


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
    # SQLite leaves referential integrity opt-in per connection. The Web
    # schema uses owner-scoped relationships (including ordered PDF Merge
    # sources), so enforce them before any schema or application write.
    conn.execute("PRAGMA foreign_keys=ON")
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
                request_fingerprint TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                PRIMARY KEY(scope, key)
            )
            """
        )
        idempotency_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_idempotency)").fetchall()}
        if "request_fingerprint" not in idempotency_columns:
            conn.execute("ALTER TABLE web_idempotency ADD COLUMN request_fingerprint TEXT NOT NULL DEFAULT ''")
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
        # Memory Center is a separate Web-owned knowledge/task surface.  It
        # intentionally never mirrors Bot `memory_*` tables, canonical
        # Telegram identity, wallet, PayOS, provider or job state. UUIDs keep
        # object references unguessable and every read/write is owner scoped
        # in the router.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_memory_notes (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                category TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'normal',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_memory_note_versions (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                category TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'normal',
                created_at TEXT NOT NULL,
                UNIQUE(note_id, revision),
                FOREIGN KEY(note_id) REFERENCES web_memory_notes(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_memory_reminders (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                note_id TEXT,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                due_at TEXT NOT NULL,
                next_run_at TEXT NOT NULL,
                timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
                repeat_rule TEXT NOT NULL DEFAULT 'none',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                last_completed_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(note_id) REFERENCES web_memory_notes(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_memory_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                note_id TEXT,
                reminder_id TEXT,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_memory_notes_account_state_updated ON web_memory_notes(account_id, state, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_memory_note_versions_note_revision ON web_memory_note_versions(note_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_memory_reminders_account_state_next ON web_memory_reminders(account_id, state, next_run_at ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_memory_events_account_created ON web_memory_events(account_id, created_at DESC)"
        )
        # Project Center is a first-class, Web-owned work surface.  It holds
        # customer-authored briefs and Studio Documents independently from the
        # Telegram Bot.  It intentionally has no wallet, payment, provider,
        # engine-job or delivery columns: those integrations must be added by
        # a dedicated, separately audited adapter later.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_projects (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                objective TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_studio_documents (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                state TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES web_projects(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Immutable snapshots make collaboration/recovery explicit without
        # retaining browser state or pretending a Bot/provider made a result.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_studio_document_versions (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(document_id, revision),
                FOREIGN KEY(document_id) REFERENCES web_studio_documents(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Asset Vault stores metadata for private, Web-owned blobs. The
        # browser never receives ``storage_key`` or a filesystem path, and the
        # table deliberately has no Bot job, provider, payment or Xu columns.
        # A project relationship is optional and remains owner-scoped.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_asset_files (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                display_name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                extension TEXT NOT NULL,
                content_type TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        # Project Packages are immutable Web-owned snapshots and private ZIP
        # artifacts.  They intentionally do not reuse Asset Vault metadata:
        # Asset Vault holds customer sources/references while this table holds
        # a server-built export with its own state, integrity data and audit.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_project_packages (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_snapshot_json TEXT NOT NULL,
                snapshot_digest TEXT NOT NULL,
                document_count INTEGER NOT NULL DEFAULT 0,
                asset_reference_count INTEGER NOT NULL DEFAULT 0,
                storage_key TEXT UNIQUE,
                original_filename TEXT,
                content_type TEXT,
                byte_size INTEGER,
                sha256 TEXT,
                failure_code TEXT,
                created_at TEXT NOT NULL,
                queued_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(account_id, project_id, idempotency_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        # State transition history is kept independently so a completed ZIP
        # can be distinguished from a browser-only success message.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_project_package_events (
                id TEXT PRIMARY KEY,
                package_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(package_id) REFERENCES web_project_packages(id)
            )
            """
        )
        package_event_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_project_package_events)").fetchall()}
        if "sequence" not in package_event_columns:
            conn.execute("ALTER TABLE web_project_package_events ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0")
        # Generated document outputs are a separate Web-native execution
        # surface. Input stays in Asset Vault, output stays in an isolated
        # directory/table, and neither is a Bot job, asset, payment or ledger.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                project_id TEXT,
                kind TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_count INTEGER NOT NULL DEFAULT 1,
                requested_page_range TEXT NOT NULL,
                selected_start_page INTEGER,
                selected_end_page INTEGER,
                source_page_count INTEGER,
                output_page_count INTEGER,
                storage_key TEXT UNIQUE,
                original_filename TEXT,
                content_type TEXT,
                byte_size INTEGER,
                sha256 TEXT,
                failure_code TEXT,
                created_at TEXT NOT NULL,
                queued_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(account_id, kind, idempotency_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_operation_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_document_operations(id)
            )
            """
        )
        document_event_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_document_operation_events)").fetchall()}
        if "sequence" not in document_event_columns:
            conn.execute("ALTER TABLE web_document_operation_events ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0")
        document_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_document_operations)").fetchall()}
        if "source_count" not in document_columns:
            conn.execute("ALTER TABLE web_document_operations ADD COLUMN source_count INTEGER NOT NULL DEFAULT 1")
        # A merge has several independently verified Asset Vault sources. The
        # operation row retains its first source for compatibility, while this
        # immutable ordered map keeps every input hash/size out of browser
        # responses and prevents a later Asset Vault change from rewriting a
        # recorded operation intent.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_operation_sources (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                source_index INTEGER NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(operation_id, source_index),
                UNIQUE(operation_id, source_asset_id),
                FOREIGN KEY(operation_id) REFERENCES web_document_operations(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        # Image operations have an independent lifecycle and artifact store.
        # Do not reuse `web_document_operations`: an image transform has a
        # different decoder boundary, output contract and retention policy.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                project_id TEXT,
                kind TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_width INTEGER,
                source_height INTEGER,
                target_width INTEGER NOT NULL,
                target_height INTEGER NOT NULL,
                preset TEXT NOT NULL,
                fit_mode TEXT NOT NULL,
                storage_key TEXT UNIQUE,
                original_filename TEXT,
                content_type TEXT,
                byte_size INTEGER,
                sha256 TEXT,
                failure_code TEXT,
                created_at TEXT NOT NULL,
                queued_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                updated_at TEXT NOT NULL,
                settings_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(account_id, kind, idempotency_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        image_operation_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_image_operations)").fetchall()}
        if "settings_json" not in image_operation_columns:
            # Append-only migration: preserve all existing resize index offsets
            # and immutable request/asset evidence while adding canonical
            # server-normalized settings for later Web-native image kinds.
            conn.execute("ALTER TABLE web_image_operations ADD COLUMN settings_json TEXT NOT NULL DEFAULT '{}'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_operation_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_image_operations(id)
            )
            """
        )
        image_event_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_image_operation_events)").fetchall()}
        if "sequence" not in image_event_columns:
            conn.execute("ALTER TABLE web_image_operation_events ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0")
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
            "CREATE INDEX IF NOT EXISTS idx_web_projects_account_state_updated ON web_projects(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_studio_documents_project_state_updated ON web_studio_documents(project_id, account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_studio_document_versions_document_revision ON web_studio_document_versions(document_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_asset_files_account_state_updated ON web_asset_files(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_asset_files_project_account_state ON web_asset_files(project_id, account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_project_packages_account_updated ON web_project_packages(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_project_packages_project_account_updated ON web_project_packages(project_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_project_package_events_package_sequence ON web_project_package_events(package_id, sequence ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_operations_account_updated ON web_document_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_operations_source_account ON web_document_operations(source_asset_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_operation_events_operation_sequence ON web_document_operation_events(operation_id, sequence ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_operation_sources_operation_order ON web_document_operation_sources(operation_id, source_index ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_operations_account_updated ON web_image_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_operations_source_account ON web_image_operations(source_asset_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_operation_events_operation_sequence ON web_image_operation_events(operation_id, sequence ASC, id ASC)"
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
