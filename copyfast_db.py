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


PRODUCTION_LIKE_ENVIRONMENT_VALUES = frozenset({"production", "prod", "live"})


def is_production_like_environment() -> bool:
    """Return whether the Web service must use deployment-grade safeguards.

    Keep this tiny helper dependency-free so every Web boundary can make the
    same decision without importing application/router code.  Railway labels
    a public production service either ``production``/``prod`` or ``live``;
    treating only the first two as production would let a live deployment use
    development CORS, cookie, SQLite or scheduler assumptions after restart.
    """
    values = (
        os.environ.get("APP_ENV", ""),
        os.environ.get("ENVIRONMENT", ""),
        os.environ.get("RAILWAY_ENVIRONMENT", ""),
    )
    return any(value.strip().lower() in PRODUCTION_LIKE_ENVIRONMENT_VALUES for value in values if value)


def _is_production() -> bool:
    """Backward-compatible private alias for older Web storage helpers."""
    return is_production_like_environment()


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
    return candidate.resolve()


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


def asset_vault_video_preview_enabled() -> bool:
    """Whether the bounded private Asset Vault video inspector is enabled.

    This is a read-only, same-origin Blob preview of an owner's already stored
    video.  It deliberately does not enable Video Studio, Bot/Core Bridge,
    FFmpeg, providers, jobs, wallet/Xu, PayOS, publishing or a public media
    delivery surface.  Requiring the Asset Vault flag as well keeps the
    effective capability fail-closed when the private storage boundary is off.
    """

    return (
        asset_vault_enabled()
        and os.environ.get("WEBAPP_VIDEO_PREVIEW_ENABLED", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )


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


def subtitle_asset_operations_enabled() -> bool:
    """Whether private SRT/VTT Asset Vault operations are deliberately enabled.

    This is separate from Subtitle Studio's authored-text workspace. It only
    permits a bounded, deterministic file conversion after the owner-scoped
    Asset Vault and isolated output root have been validated; it never enables
    ASR, translation, dubbing, provider, Bot, wallet/Xu or PayOS work.
    """

    return os.environ.get("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def audio_asset_operations_enabled() -> bool:
    """Whether bounded, private Audio Asset Operations are deliberately enabled.

    This is an isolated local FFmpeg/ffprobe boundary for an owner's existing
    Asset Vault audio.  It never turns on provider music/voice generation, Bot
    work, a canonical job, wallet/Xu, PayOS, publishing or a generic media
    executor.
    """

    return os.environ.get("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def image_to_pdf_enabled() -> bool:
    """Whether the Pillow-backed Image-to-PDF decoder is deliberately enabled.

    This stays separate from the base Document Operations flag because image
    decoding has its own dependency and memory boundary.  Its route still
    requires the Asset Vault and generated-output storage contracts.
    """
    return os.environ.get("WEBAPP_IMAGE_TO_PDF_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def image_ocr_enabled() -> bool:
    """Whether private, local Image OCR is deliberately enabled.

    OCR invokes a service-installed Tesseract binary and decodes an image, so
    it remains a separate fail-closed switch from generic Document Operations
    and Image → PDF.  A disabled switch must never make a browser OCR claim or
    start a local process.
    """

    return os.environ.get("WEBAPP_DOCUMENT_OCR_IMAGE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def pdf_ocr_enabled() -> bool:
    """Whether bounded local PDF-raster OCR is deliberately enabled.

    PDF OCR combines PDFium rasterization with the service-installed local
    Tesseract runtime. It remains independent from Image OCR and PDF-to-images
    so either underlying capability can stay disabled without accidentally
    enabling a multi-page text extraction workload.
    """

    return os.environ.get("WEBAPP_DOCUMENT_OCR_PDF_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def pdf_ocr_word_enabled() -> bool:
    """Whether scanned-PDF OCR-to-DOCX is deliberately enabled.

    This combines an untrusted PDF rasterizer, local Tesseract and DOCX
    writing.  Keep it independent from both TXT OCR and selectable-text PDF
    export so an operator must explicitly opt in to the larger execution
    surface and no existing route gains an unstated OCR fallback.
    """

    return os.environ.get("WEBAPP_PDF_OCR_WORD_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


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


def video_operations_enabled() -> bool:
    """Whether bounded, Web-native private video operations are enabled.

    This is a distinct execution and storage boundary from Video Studio.  It
    never enables Bot video jobs, provider generation, wallet/Xu, PayOS,
    social publishing or browser-supplied FFmpeg arguments.
    """

    return os.environ.get("WEBAPP_VIDEO_OPERATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def video_poster_enabled() -> bool:
    """Whether the private, FFmpeg-backed Video Poster operation is enabled.

    A separate false-by-default switch means an operator can prepare the
    Web-owned storage boundary without accidentally executing a media binary.
    """

    return os.environ.get("WEBAPP_VIDEO_POSTER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def frame_video_operations_enabled() -> bool:
    """Whether the bounded Asset Vault image-to-video executor is enabled.

    Frame Video Lab is deliberately not a switch for Video Studio, Bot jobs,
    remote providers, wallets, PayOS, publishing or arbitrary FFmpeg work.
    It only enables one private, deterministic image-sequence MP4 boundary.
    """

    return os.environ.get("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def video_transform_operations_enabled() -> bool:
    """Whether the bounded private Video Finishing executor is enabled.

    This is intentionally narrower than the existing Video Poster and Frame
    Video boundaries.  It permits one owner-scoped local video transform with
    a closed render spec; it never enables Bot jobs, remote providers, wallet
    or PayOS writes, arbitrary FFmpeg filters, publishing, or browser-owned
    file locations.
    """

    return os.environ.get("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


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


def image_brand_overlay_enabled() -> bool:
    """Whether the private Image Brand Overlay Studio executor is enabled.

    The switch is deliberately narrower than Image Operations itself.  It
    unlocks only a bounded server-side Pillow composition from owner-scoped
    Asset Vault images; it never grants browser canvas rendering, a Bot job,
    provider access, wallet mutation or payment action.
    """
    return os.environ.get("WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def storyboard_grid_enabled() -> bool:
    """Whether private Web-native storyboard-grid splitting is enabled.

    This is intentionally narrower than the shared Image Operations boundary.
    It permits only a deterministic, owner-scoped Asset Vault image to be
    split into verified JPEG scene files and a private ZIP/manifest.  It never
    enables a Bot job, provider request, wallet/Xu mutation, PayOS action or
    browser-side rendering fallback.
    """
    return os.environ.get("WEBAPP_STORYBOARD_GRID_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def memory_center_enabled() -> bool:
    """Whether the Web-owned Memory Center is available to signed accounts.

    Notes and reminders use the existing persistent Web session database and
    no provider, Bot, wallet or payment runtime.  They are therefore useful
    by default, while an operator can still turn the complete Web-owned
    surface off with an explicit false value during maintenance.
    """
    return os.environ.get("WEBAPP_MEMORY_CENTER_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def data_controls_enabled() -> bool:
    """Whether the Web-only Privacy & Data Control Center is available.

    The center can return a bounded direct authoring-data attachment and record
    a staged erasure-review request, so it is deliberately disabled until the
    operator explicitly enables the independent Web capability.  It never
    grants Bot/Telegram, wallet, PayOS, provider, job, Asset Vault or file
    deletion authority.
    """

    return os.environ.get("WEBAPP_DATA_CONTROLS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def governance_documents_enabled() -> bool:
    """Whether the local Web Governance Documents module is deliberately on.

    Existing Admin ERP navigation historically treats its umbrella flag as
    enabled unless explicitly disabled.  Governance documents are a new
    durable internal-record surface, so retain that umbrella kill switch *and*
    require a second false-by-default opt-in.  This helper never grants Bot,
    bridge, wallet/Xu, PayOS, provider, job, notification or publication
    authority; it only controls the Web-owned tables declared below.
    """

    enabled_values = {"1", "true", "yes", "on"}
    umbrella = os.environ.get("WEBAPP_ADMIN_ERP_ENABLED", "true").strip().lower() in enabled_values
    dedicated = os.environ.get("WEBAPP_GOVERNANCE_DOCUMENTS_ENABLED", "false").strip().lower() in enabled_values
    return umbrella and dedicated


def admin_document_archive_enabled() -> bool:
    """Whether the Web-owned Admin Internal Document Archive is enabled.

    This is deliberately separate from text-only Governance Documents and from
    customer Asset Vaults: it accepts immutable private admin-record blobs.
    Both the Admin ERP umbrella and this false-by-default gate must be enabled
    before the archive can touch its own tables or storage root.  It never
    grants Bot, bridge, Telegram, wallet/Xu, PayOS, provider, job, customer or
    finance authority.
    """

    enabled_values = {"1", "true", "yes", "on"}
    umbrella = os.environ.get("WEBAPP_ADMIN_ERP_ENABLED", "true").strip().lower() in enabled_values
    dedicated = os.environ.get("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED", "false").strip().lower() in enabled_values
    return umbrella and dedicated


def support_desk_enabled() -> bool:
    """Whether the independently owned Web Support Desk is available.

    The desk persists only to the signed Web application's database.  It
    neither mirrors Bot ticket tables nor creates Telegram, email, payment,
    wallet, provider or job activity, so it can be safely useful by default.
    Operators may still close the complete surface during maintenance with an
    explicit false value.
    """
    return os.environ.get("WEBAPP_SUPPORT_DESK_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def prompt_library_enabled() -> bool:
    """Whether the private, Web-owned Prompt Library is available.

    Prompt templates, revisions and local previews use only the signed Web
    session database.  They do not contact Bot runtime, provider, wallet or
    payment systems, so the surface is useful by default while still having a
    single maintenance switch for operators.
    """
    return os.environ.get("WEBAPP_PROMPT_LIBRARY_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def prompt_studio_enabled() -> bool:
    """Whether the transient, deterministic Prompt Blueprint Composer is available.

    This switch only governs a signed request/response text planner.  It has
    no persistence, Bot/Core Bridge, provider/model, job, wallet/Xu, PayOS,
    asset, publication or delivery implication, so it can be useful by
    default while retaining a deliberate maintenance gate.
    """

    return os.environ.get("WEBAPP_PROMPT_STUDIO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def music_media_workspace_enabled() -> bool:
    """Whether the Web-native Audio Library & Briefing workspace is available.

    Collections, audio references and deterministic music-brief directions are
    owned solely by signed Web accounts.  They deliberately never call a music
    provider, create a Bot job, mutate Xu/PayOS, copy Telegram state, fetch a
    remote URL or store a private file path.  The feature is useful by default
    while retaining one explicit maintenance switch for operators.
    """
    return os.environ.get("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def music_media_workspace_preview_enabled() -> bool:
    """Whether signed owners may stream an attached Web Asset Vault audio reference.

    This is deliberately disabled unless an operator enables it.  It is not a
    provider catalog, Bot-cache adapter, remote URL fetcher, media generator,
    wallet/payment flow or output-delivery signal: the route can only read a
    previously verified, owner-scoped audio file already attached to a Web
    Media Workspace collection.
    """

    return music_media_workspace_enabled() and os.environ.get(
        "WEBAPP_MEDIA_WORKSPACE_PREVIEW_ENABLED", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}


def content_studio_enabled() -> bool:
    """Whether the independently owned Creative Content Studio is available.

    Briefs, content pieces, revisions and reference snapshots remain in the
    signed Web account database.  They do not call the Bot, a provider,
    payments, Xu, jobs, Telegram, publishing or delivery systems, so the
    authoring workspace is useful by default while retaining one deliberate
    maintenance switch for operators.
    """
    return os.environ.get("WEBAPP_CONTENT_STUDIO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def channel_strategy_enabled() -> bool:
    """Whether signed accounts may use Web-native Channel Strategy profiles.

    The profile, its history and deterministic review preview live only in the
    Web session database.  This switch never enables a channel connection,
    social lookup, analytics import, Bot/Core Bridge request, provider, job,
    wallet/Xu, PayOS, publishing or delivery capability.
    """
    return os.environ.get("WEBAPP_CHANNEL_STRATEGY_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def trend_research_enabled() -> bool:
    """Whether the deterministic manual Trend Research planner is available.

    This flag exposes only a request/response checklist derived from the Bot's
    static ``/trend_research`` guidance. It never enables live platform
    search, scraping, a provider/model, Bot/Core Bridge call, Xu/wallet,
    PayOS, job, asset, media output, publishing or delivery capability.
    """
    return os.environ.get("WEBAPP_TREND_RESEARCH_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def growth_review_enabled() -> bool:
    """Whether the manual, rule-based Growth Review is available.

    The switch permits only deterministic arithmetic over metric values the
    signed browser explicitly submits.  It never enables a social/platform
    connection, Bot/Core Bridge, AI/provider call, canonical revenue, wallet,
    PayOS, job, asset, publish or delivery capability.
    """

    return os.environ.get("WEBAPP_GROWTH_REVIEW_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def media_factory_enabled() -> bool:
    """Whether the deterministic Web Media Factory Blueprint is available.

    This flag exposes only a signed, transient plan ported from the Bot's
    ``/media_factory`` fallback text. It never enables live trend/social
    search, a provider/model, Bot/Core Bridge call, Xu/wallet, PayOS, job,
    asset/media output, publication, delivery or webhook capability.
    """
    return os.environ.get("WEBAPP_MEDIA_FACTORY_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def voice_studio_enabled() -> bool:
    """Whether the Web-native Voice Studio & Consent Vault is available.

    The vault persists only signed-account authoring metadata, explicit
    self-attestation notes, scripts and deterministic cue sheets.  It does
    not create or retain audio, provider voice IDs, Telegram state, jobs, Xu,
    PayOS or delivery records, so it can remain useful by default while an
    operator retains one deliberate maintenance switch.
    """
    return os.environ.get("WEBAPP_VOICE_STUDIO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def video_studio_enabled() -> bool:
    """Whether the Web-native Video Production Studio is available.

    Plans, scene directions, self-review state and revision snapshots stay in
    the signed Web account database.  The switch never enables an execution
    engine, a Bot companion, media ingest, provider call, wallet mutation or
    payment action.  It is on by default because the planning-only surface is
    useful without any of those integrations.
    """
    return os.environ.get("WEBAPP_VIDEO_STUDIO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def subtitle_studio_enabled() -> bool:
    """Whether the Web-native Subtitle, Transcript & Language Studio is available.

    This switch exposes only signed-account authored cue text, revisions and
    bounded SRT/VTT text transforms.  It never enables media upload, ASR,
    translation, TTS, dubbing, provider/Bot calls, jobs, wallet, PayOS or
    delivery functionality.
    """
    return os.environ.get("WEBAPP_SUBTITLE_STUDIO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def image_studio_enabled() -> bool:
    """Whether the Web-native Image Creative Studio is available.

    The studio owns signed-account creative directions, explicit references
    to existing private image metadata, revisions and self-review state.  It
    does not enable an image engine, asset upload, browser media URL,
    provider/Bot call, job, wallet, payment or delivery capability.
    """
    return os.environ.get("WEBAPP_IMAGE_STUDIO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def document_workspace_enabled() -> bool:
    """Whether the Web-native Document & PDF Workspace is available.

    This flag exposes only signed-account authoring records: document briefs,
    planned workflows, revision snapshots and opaque references to existing
    private Asset Vault metadata.  It does *not* enable a document provider,
    OCR, translation, Bot bridge, job, wallet, payment or output-delivery
    capability.  The harmless planning surface is useful by default while an
    explicit false value keeps a single maintenance switch.
    """
    return os.environ.get("WEBAPP_DOCUMENT_WORKSPACE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def chat_workspace_enabled() -> bool:
    """Whether the Web-native Conversation Workspace is available.

    This switch only allows private, signed-account conversation planning
    records: human-authored prompts, context cards, decisions and metadata
    revisions. It does *not* enable a model, Gemini, Bot/Core Bridge,
    provider stream, wallet/Xu, PayOS, job, upload, output or delivery.
    """
    return os.environ.get("WEBAPP_CHAT_WORKSPACE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def chat_execution_enabled() -> bool:
    """Whether a reviewed Web-native Chat execution adapter is enabled.

    This is deliberately off by default.  It is only an operator intent flag:
    the standalone Web App must still fail closed until a separately reviewed
    adapter is present.  Reading this switch never enables a Bot/Core Bridge,
    provider/model call, wallet/Xu mutation, PayOS action, job, output or
    delivery by itself.
    """
    return os.environ.get("WEBAPP_CHAT_EXECUTION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def analytics_workspace_enabled() -> bool:
    """Whether the Web-native manual Analytics Workspace is available.

    This only enables owner-scoped, user-supplied metric records and local
    arithmetic.  It never enables a social/platform API, Bot/Core Bridge,
    provider, AI recommendation, revenue ledger, wallet/Xu, PayOS, job,
    publishing, upload or report-file delivery integration.
    """
    return os.environ.get("WEBAPP_ANALYTICS_WORKSPACE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def analytics_workspace_export_enabled() -> bool:
    """Whether finalized manual Analytics CSV attachments are deliberately enabled.

    This is narrower than the authoring workspace flag because an attachment
    can leave the browser.  When enabled it permits only a bounded,
    CSRF-protected CSV response made from the signed owner's manual records;
    it does not enable Bot/campaign reports, platform data, provider calls,
    assets, jobs, wallet/Xu, PayOS or a stored delivery artifact.
    """

    return os.environ.get("WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def workboard_enabled() -> bool:
    """Whether the signed-account Web-native Workboard is available.

    Workboard records only private planning metadata, checklist progress and
    references to other rows already owned by the same Web account.  Enabling
    it never calls a Bot, provider or social API, creates a job, publishes
    content, mutates a wallet/Xu ledger, starts a payment, or delivers an
    external notification.  It is useful by default while retaining one
    explicit maintenance switch for operators.
    """
    return os.environ.get("WEBAPP_WORKBOARD_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def starter_kits_enabled() -> bool:
    """Whether signed users can install reviewed Web-native Starter Kits.

    A Starter Kit creates only owner-scoped Project, Studio Document and
    Workboard planning records in one local database transaction.  This flag
    cannot enable a Bot/Core Bridge, provider, job, media output, wallet/Xu,
    PayOS, publishing or notification action.
    """
    return os.environ.get("WEBAPP_STARTER_KITS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def autopilot_enabled() -> bool:
    """Whether the controlled Operations Autopilot surface is enabled.

    The default is deliberately fail-closed.  Turning this flag on only
    enables authenticated observation, deterministic complaint triage and the
    internal scheduler endpoint; it never grants an external provider,
    payment, wallet, deployment or messaging capability.
    """
    return os.environ.get("WEBAPP_AUTOPILOT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def autopilot_safe_remediation_enabled() -> bool:
    """Whether the small, allow-listed local remediation set is enabled.

    This is intentionally separate from :func:`autopilot_enabled` so an
    operator can inspect operations and record authenticated ticks before
    allowing even low-risk metadata writes such as SLA classification.
    """
    return os.environ.get("WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def autopilot_heartbeat_followup_enabled() -> bool:
    """Whether a late scheduler heartbeat may create Web-only metadata.

    The flag is deliberately separate from the broader Operations flags so a
    deployed Cron cannot begin creating operational incidents merely because
    routine Support triage was enabled.  Even when enabled, the feature only
    records a bounded local Operations incident; it cannot restart a Cron,
    change Railway, contact anyone, or invoke Bot/provider/payment/wallet/job
    authority.
    """
    return os.environ.get("WEBAPP_AUTOPILOT_HEARTBEAT_FOLLOWUP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def notification_center_enabled() -> bool:
    """Whether signed accounts may read their private Web inbox."""
    return os.environ.get("WEBAPP_NOTIFICATION_CENTER_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def notification_automation_enabled() -> bool:
    """Whether the isolated scheduler may materialize allowed inbox records."""
    return os.environ.get("WEBAPP_NOTIFICATION_AUTOMATION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def reliability_followup_enabled() -> bool:
    """Whether Runtime Reliability Follow-up may persist Web-only metadata.

    This deliberately defaults to disabled.  Enabling it does not authorize a
    repair, deployment, provider call, money movement, customer reply or
    external notification; it only allows a later reviewed service to retain
    bounded, sanitized Web-runtime follow-up records.
    """
    return os.environ.get("WEBAPP_RELIABILITY_FOLLOWUP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


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


def subtitle_asset_operations_directory() -> Path:
    """Resolve an isolated root for verified private subtitle artifacts."""

    if not subtitle_asset_operations_enabled():
        raise RuntimeError("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED chưa được bật")
    configured = os.environ.get("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        candidate = (
            persistent_directory / "toanaas_webapp_subtitle_asset_operations"
            if persistent_directory is not None
            else Path(session_database_path()).expanduser().resolve().parent / "toanaas_webapp_subtitle_asset_operations"
        )
    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT không được nằm trong static")
    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    if document_operations_enabled():
        private_roots.append(document_operations_directory().resolve())
    if image_operations_enabled():
        private_roots.append(image_operations_directory().resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError(
                "WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT phải tách riêng Asset Vault, Project Package, Document Operations và Image Operations"
            )
    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError("Subtitle Asset Operations production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data")
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT phải là thư mục con của persistent volume khi production")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise RuntimeError("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_subtitle_asset_operations_persistence() -> Path | None:
    """Validate private SRT/VTT output storage before the feature is served."""

    if not subtitle_asset_operations_enabled():
        return None
    if not asset_vault_enabled():
        raise RuntimeError("Subtitle Asset Operations cần WEBAPP_ASSET_VAULT_ENABLED=true")
    return subtitle_asset_operations_directory()


def audio_asset_operations_directory() -> Path:
    """Resolve an isolated root for verified local audio operation artifacts."""

    if not audio_asset_operations_enabled():
        raise RuntimeError("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED chưa được bật")
    configured = os.environ.get("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        candidate = (
            persistent_directory / "toanaas_webapp_audio_asset_operations"
            if persistent_directory is not None
            else Path(session_database_path()).expanduser().resolve().parent / "toanaas_webapp_audio_asset_operations"
        )
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT không được là symbolic link")
    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT không được nằm trong static")
    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    if document_operations_enabled():
        private_roots.append(document_operations_directory().resolve())
    if image_operations_enabled():
        private_roots.append(image_operations_directory().resolve())
    if subtitle_asset_operations_enabled():
        private_roots.append(subtitle_asset_operations_directory().resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError(
                "WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT phải tách riêng Asset Vault, Project Package, Document Operations, Image Operations và Subtitle Asset Operations"
            )
    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError("Audio Asset Operations production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data")
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT phải là thư mục con của persistent volume khi production")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_audio_asset_operations_persistence() -> Path | None:
    """Validate the opt-in private audio output root before it is served."""

    if not audio_asset_operations_enabled():
        return None
    if not asset_vault_enabled():
        raise RuntimeError("Audio Asset Operations cần WEBAPP_ASSET_VAULT_ENABLED=true")
    return audio_asset_operations_directory()


def video_operations_directory() -> Path:
    """Resolve the isolated private output root for Web-native video work.

    Video poster extraction consumes an immutable Asset Vault source and
    produces a new JPEG.  It may never share the input vault, package,
    document or image-operation roots, because an output must remain plainly
    distinguishable from a customer source or a Bot-owned delivery.
    """

    if not video_operations_enabled():
        raise RuntimeError("WEBAPP_VIDEO_OPERATIONS_ENABLED chưa được bật")

    configured = os.environ.get("WEBAPP_VIDEO_OPERATIONS_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_VIDEO_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        if persistent_directory is not None:
            candidate = persistent_directory / "toanaas_webapp_video_operations"
        else:
            database_parent = Path(session_database_path()).expanduser().resolve().parent
            candidate = database_parent / "toanaas_webapp_video_operations"

    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_VIDEO_OPERATIONS_ROOT không được nằm trong static")

    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    if document_operations_enabled():
        private_roots.append(document_operations_directory().resolve())
    if image_operations_enabled():
        private_roots.append(image_operations_directory().resolve())
    if audio_asset_operations_enabled():
        private_roots.append(audio_asset_operations_directory().resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError(
                "WEBAPP_VIDEO_OPERATIONS_ROOT phải tách riêng Asset Vault, Project Package, Document Operations, Image Operations và Audio Asset Operations"
            )

    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError(
                "Video Operations production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data"
            )
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError(
                "WEBAPP_VIDEO_OPERATIONS_ROOT phải là thư mục con của persistent volume khi production"
            )

    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise RuntimeError("WEBAPP_VIDEO_OPERATIONS_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_video_operations_persistence() -> Path | None:
    """Validate the isolated output boundary before video execution is served."""

    if not video_operations_enabled():
        return None
    if not asset_vault_enabled():
        raise RuntimeError("Video Operations cần WEBAPP_ASSET_VAULT_ENABLED=true")
    return video_operations_directory()


def frame_video_operations_directory() -> Path:
    """Resolve the isolated private output root for Frame Video Lab.

    The image-sequence renderer consumes only immutable Asset Vault images and
    creates a private MP4.  Its root must remain separate from every existing
    input/output boundary so a generated video can never be mistaken for an
    upload, document conversion, image transform, poster, subtitle artifact,
    package export or Bot-owned delivery.
    """

    if not frame_video_operations_enabled():
        raise RuntimeError("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED chưa được bật")

    configured = os.environ.get("WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        if persistent_directory is not None:
            candidate = persistent_directory / "toanaas_webapp_frame_video_operations"
        else:
            database_parent = Path(session_database_path()).expanduser().resolve().parent
            candidate = database_parent / "toanaas_webapp_frame_video_operations"

    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT không được là symbolic link")
    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT không được nằm trong static")

    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    if document_operations_enabled():
        private_roots.append(document_operations_directory().resolve())
    if image_operations_enabled():
        private_roots.append(image_operations_directory().resolve())
    if subtitle_asset_operations_enabled():
        private_roots.append(subtitle_asset_operations_directory().resolve())
    if audio_asset_operations_enabled():
        private_roots.append(audio_asset_operations_directory().resolve())
    if video_operations_enabled():
        private_roots.append(video_operations_directory().resolve())
    if video_transform_operations_enabled():
        transform_configured = os.environ.get("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT", "").strip()
        if transform_configured:
            transform_candidate = Path(transform_configured).expanduser()
            if not transform_candidate.is_absolute():
                raise RuntimeError("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
        else:
            transform_persistent = _persistent_session_directory()
            transform_candidate = (
                transform_persistent / "toanaas_webapp_video_transform_operations"
                if transform_persistent is not None
                else Path(session_database_path()).expanduser().resolve().parent / "toanaas_webapp_video_transform_operations"
            )
        if transform_candidate.exists() and transform_candidate.is_symlink():
            raise RuntimeError("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT không được là symbolic link")
        private_roots.append(transform_candidate.resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError(
                "WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT phải tách riêng Asset Vault, Project Package, Document Operations, Image Operations, Subtitle Asset Operations, Audio Asset Operations và Video Operations"
            )

    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError(
                "Frame Video Lab production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data"
            )
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError(
                "WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT phải là thư mục con của persistent volume khi production"
            )

    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_frame_video_operations_persistence() -> Path | None:
    """Validate Frame Video's opt-in private storage boundary at startup."""

    if not frame_video_operations_enabled():
        return None
    if not asset_vault_enabled():
        raise RuntimeError("Frame Video Lab cần WEBAPP_ASSET_VAULT_ENABLED=true")
    return frame_video_operations_directory()


def video_transform_operations_directory() -> Path:
    """Resolve the isolated private root for Video Finishing Lab artifacts.

    Transformed videos must never share a directory with uploaded assets,
    Poster/Frame Video output, documents, images, packages, or Bot-owned
    storage.  The operation stores only an opaque receipt in SQLite and every
    local path is reconstructed below this root by server code.
    """

    if not video_transform_operations_enabled():
        raise RuntimeError("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED chưa được bật")

    configured = os.environ.get("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        if persistent_directory is not None:
            candidate = persistent_directory / "toanaas_webapp_video_transform_operations"
        else:
            database_parent = Path(session_database_path()).expanduser().resolve().parent
            candidate = database_parent / "toanaas_webapp_video_transform_operations"

    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT không được là symbolic link")
    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT không được nằm trong static")

    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    if document_operations_enabled():
        private_roots.append(document_operations_directory().resolve())
    if image_operations_enabled():
        private_roots.append(image_operations_directory().resolve())
    if subtitle_asset_operations_enabled():
        private_roots.append(subtitle_asset_operations_directory().resolve())
    if audio_asset_operations_enabled():
        private_roots.append(audio_asset_operations_directory().resolve())
    if video_operations_enabled():
        private_roots.append(video_operations_directory().resolve())
    if frame_video_operations_enabled():
        private_roots.append(frame_video_operations_directory().resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError(
                "WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT phải tách riêng Asset Vault, Project Package, Document Operations, Image Operations, Subtitle Asset Operations, Audio Asset Operations, Video Operations và Frame Video"
            )

    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError(
                "Video Finishing Lab production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data"
            )
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError(
                "WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT phải là thư mục con của persistent volume khi production"
            )

    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_video_transform_operations_persistence() -> Path | None:
    """Validate Video Finishing's opt-in isolated storage at startup."""

    if not video_transform_operations_enabled():
        return None
    if not asset_vault_enabled():
        raise RuntimeError("Video Finishing Lab cần WEBAPP_ASSET_VAULT_ENABLED=true")
    return video_transform_operations_directory()


def admin_document_archive_directory() -> Path:
    """Resolve the isolated private blob root for Admin Internal Documents."""

    if not admin_document_archive_enabled():
        raise RuntimeError("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED chưa được bật")
    configured = os.environ.get("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT phải là đường dẫn tuyệt đối")
    else:
        persistent_directory = _persistent_session_directory()
        candidate = (
            persistent_directory / "toanaas_webapp_admin_document_archive"
            if persistent_directory is not None
            else Path(session_database_path()).expanduser().resolve().parent / "toanaas_webapp_admin_document_archive"
        )
    candidate = candidate.resolve()
    static_directory = (Path(__file__).resolve().parent / "static").resolve()
    if _is_within(candidate, static_directory):
        raise RuntimeError("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT không được nằm trong static")
    private_roots: list[Path] = []
    if asset_vault_enabled():
        private_roots.append(asset_vault_directory().resolve())
    if project_package_enabled():
        private_roots.append(project_package_directory().resolve())
    if document_operations_enabled():
        private_roots.append(document_operations_directory().resolve())
    if image_operations_enabled():
        private_roots.append(image_operations_directory().resolve())
    if subtitle_asset_operations_enabled():
        private_roots.append(subtitle_asset_operations_directory().resolve())
    for private_root in private_roots:
        if candidate == private_root or _is_within(candidate, private_root) or _is_within(private_root, candidate):
            raise RuntimeError(
                "WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT phải tách riêng Asset Vault, Project Package, Document Operations, Image Operations và Subtitle Asset Operations"
            )
    if _is_production():
        persistent_directory = _persistent_session_directory()
        if persistent_directory is None:
            raise RuntimeError("Admin Document Archive production cần RAILWAY_VOLUME_MOUNT_PATH hợp lệ hoặc mount /data")
        persistent_directory = persistent_directory.resolve()
        if candidate == persistent_directory or not _is_within(candidate, persistent_directory):
            raise RuntimeError("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT phải là thư mục con của persistent volume khi production")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise RuntimeError("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT không phải thư mục hợp lệ")
    return candidate


def ensure_admin_document_archive_persistence() -> Path | None:
    """Validate the dedicated immutable admin-record storage when enabled."""

    if not admin_document_archive_enabled():
        return None
    return admin_document_archive_directory()


def session_database_path() -> str:
    """Resolve the Web-owned auth/session database without using a Bot store.

    A production-like process may never fall back to an arbitrary absolute
    container path.  SQLite sessions hold CSRF, link-code and replay state,
    so an ``/app/*.db`` value would appear to work until a normal deploy
    discarded it.  Resolve the file and prove it sits below this Web service's
    verified Railway volume (or verified ``/data``) before returning it.
    """
    configured = os.environ.get("WEBAPP_SESSION_DB_PATH", "").strip()
    if configured:
        if _is_production():
            return str(_validated_production_session_database_path(configured))
        return configured
    persistent_directory = _persistent_session_directory()
    if persistent_directory is not None:
        return str(persistent_directory.resolve() / "toanaas_webapp_session.db")
    if _is_production():
        raise RuntimeError(
            "Production cần WEBAPP_SESSION_DB_PATH là file dưới persistent volume, "
            "RAILWAY_VOLUME_MOUNT_PATH hợp lệ, hoặc mount /data cho signed session và Telegram link"
        )
    return "toanaas_webapp_session.db"


def _validated_production_session_database_path(configured: str) -> Path:
    """Return a resolved session *file* only after volume-boundary proof."""
    raw_path = Path(configured).expanduser()
    if not raw_path.is_absolute():
        raise RuntimeError("WEBAPP_SESSION_DB_PATH phải là đường dẫn tuyệt đối khi production")
    persistent_directory = _persistent_session_directory()
    if persistent_directory is None:
        raise RuntimeError(
            "Production cần WEBAPP_SESSION_DB_PATH là file dưới persistent volume, "
            "RAILWAY_VOLUME_MOUNT_PATH hợp lệ, hoặc mount /data cho signed session và Telegram link"
        )
    candidate = raw_path.resolve()
    volume = persistent_directory.resolve()
    if candidate == volume or not _is_within(candidate, volume):
        raise RuntimeError(
            "WEBAPP_SESSION_DB_PATH phải là file dưới persistent volume khi production"
        )
    # The SQLite database need not exist until the first clean startup, but a
    # pre-existing directory/special path is never a database file.  Resolving
    # first also rejects a symlink that escapes the declared volume.
    if candidate.exists() and not candidate.is_file():
        raise RuntimeError("WEBAPP_SESSION_DB_PATH phải trỏ tới file database, không phải thư mục")
    return candidate


def ensure_copyfast_persistence() -> None:
    """Fail closed when production auth data would disappear on restart.

    Telegram link codes, signed sessions and callback nonces must survive a
    normal Railway restart. A local relative SQLite file is fine for tests and
    local development, but is never a production persistence plan.
    """
    if not _is_production():
        return
    # ``session_database_path`` performs the complete resolve + volume-boundary
    # check.  Keep a single authority so every request path and all schedulers
    # receive the same failure rather than allowing an early SQLite connection
    # to create an ephemeral database first.
    session_database_path()


def web_scheduler_persistence_ready() -> bool:
    """Whether a Web scheduler's SQLite replay/lease state survives restart.

    Production-like Web startup already requires its signed-session database
    below this service's verified volume.  Operations Autopilot repeats the
    same proof deliberately because losing nonce/lease/run history after a
    restart could permit a signed scheduler request to be replayed.  Local and
    test environments intentionally do not need that Railway attestation.
    """
    if not _is_production():
        return True
    persistent_directory = _persistent_session_directory()
    if persistent_directory is None:
        return False
    try:
        database_path = Path(session_database_path()).expanduser().resolve()
        return _is_within(database_path, persistent_directory.resolve())
    except (OSError, RuntimeError):
        return False


def operations_autopilot_persistence_ready() -> bool:
    """Compatibility name for Operations Autopilot's scheduler guard."""
    return web_scheduler_persistence_ready()


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


@contextmanager
def best_effort_transaction(*, timeout_seconds: float = 0.05):
    """Open a short, non-blocking write transaction for observability only.

    Request-path telemetry must never wait behind a long-running SQLite writer
    and make an already failing customer response slower.  Callers must treat
    ``sqlite3.OperationalError`` as a dropped observation, not a business
    failure.  This helper owns no schema creation and is deliberately not used
    for sessions, money, account writes or any user-facing state change.
    """
    bounded_timeout = max(0.001, min(float(timeout_seconds), 0.25))
    path = session_database_path()
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=bounded_timeout)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={max(1, int(bounded_timeout * 1000))}")
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def read_transaction():
    """Open a deferred, query-only SQLite transaction for owner-scoped reads.

    The Web app creates additive schema during lifespan/startup and uses
    ``transaction()`` for mutations. After session authentication, read-heavy
    workspace handlers use this path so their own vault query does not add a
    second immediate write reservation just to render a private list/detail.
    """
    path = session_database_path()
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA query_only=ON")
    try:
        conn.execute("BEGIN")
        yield conn
        conn.rollback()
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
        # First-run Workspace setup is strictly Web-owned preference metadata.
        # It does not mirror Telegram identity, wallet/Xu, PayOS, Bot jobs or
        # provider state, and it only guides signed-account navigation.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workspace_setup_profiles (
                account_id TEXT PRIMARY KEY,
                setup_state TEXT NOT NULL DEFAULT 'not_started'
                    CHECK(setup_state IN ('not_started', 'completed', 'skipped')),
                role TEXT NOT NULL DEFAULT ''
                    CHECK(role IN ('', 'solo_creator', 'team_lead', 'operator', 'learner')),
                goal TEXT NOT NULL DEFAULT ''
                    CHECK(goal IN ('', 'organize_work', 'create_content', 'build_brand', 'run_operations', 'learn_workflows')),
                experience TEXT NOT NULL DEFAULT ''
                    CHECK(experience IN ('', 'new', 'growing', 'advanced')),
                focus_areas_json TEXT NOT NULL DEFAULT '[]',
                revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0),
                completed_at TEXT,
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
        # A provider may prove control of a contact address without making
        # that address a password-login identifier for this Web account.  In
        # particular, a verified OAuth identity whose address is already
        # held by another account receives an isolated OAuth-only account
        # with an internal alias in ``web_accounts.email``.  Keep its public,
        # provider-verified contact here instead.  Deliberately do *not* add
        # a unique constraint on ``email``: two separate Web accounts can
        # legitimately carry the same verified contact while remaining
        # isolated, and no account is reclaimed or merged automatically.
        #
        # The immutable provider subject stays exclusively as an HMAC in
        # ``web_external_identities``.  This table never receives it, tokens,
        # or any provider credential.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_account_oauth_contacts (
                account_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL CHECK(provider IN ('google', 'github', 'apple')),
                email TEXT NOT NULL,
                verified_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # A password account may prove control of its own login mailbox through
        # a Web-owned, short-lived email link. This is deliberately separate
        # from OAuth contacts: neither table may merge accounts, alter a
        # password identifier, or become a Bot identity/payment/wallet record.
        # The contact row stores no token or delivery credential.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_account_email_contacts (
                account_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                verification_method TEXT NOT NULL CHECK(verification_method='email_link'),
                verified_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Delivery metadata is intentionally minimal and additive. The raw
        # verification token never reaches SQLite; only a server-secret HMAC
        # digest is retained. A challenge can only be consumed after a
        # successful SMTP handoff marked it sent.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_email_verification_challenges (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                email TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('prepared', 'sent', 'failed', 'consumed', 'superseded')),
                expires_at TEXT NOT NULL,
                sent_at TEXT,
                consumed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_email_verification_account_created
            ON web_email_verification_challenges(account_id, created_at DESC)
            """
        )
        # Password recovery is a separate Web-only, expiring proof. It shares
        # no token or state with mailbox-assurance challenges and never
        # creates a session by itself. Keeping it separate makes revocation,
        # audit and retention rules independently reviewable.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_password_recovery_challenges (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                email TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('prepared', 'sent', 'failed', 'consumed', 'superseded')),
                expires_at TEXT NOT NULL,
                sent_at TEXT,
                consumed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_password_recovery_account_created
            ON web_password_recovery_challenges(account_id, created_at DESC)
            """
        )
        # TOTP factors are an optional Web-only second factor. The raw shared
        # secret is never stored: secret_ciphertext is authenticated
        # encryption controlled by the dedicated Web MFA key, and enrollment
        # / login tokens are HMAC digests only. None of these tables mirrors
        # Telegram identity, Bot state, wallet/Xu, PayOS, provider or job
        # authority.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_totp_factors (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                secret_ciphertext TEXT NOT NULL,
                enrollment_token_hash TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('prepared', 'active', 'disabled', 'superseded')),
                revision INTEGER NOT NULL DEFAULT 1,
                enrollment_expires_at TEXT,
                enabled_at TEXT,
                disabled_at TEXT,
                last_counter INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_web_totp_factors_one_active
            ON web_totp_factors(account_id) WHERE state='active'
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_totp_factors_account_state
            ON web_totp_factors(account_id, state, updated_at DESC)
            """
        )
        # Recovery codes are generated once after a successfully confirmed
        # factor and stored as keyed digests only. A consumed/invalidated row
        # remains as a bounded security audit marker rather than becoming a
        # reusable credential.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_totp_recovery_codes (
                id TEXT PRIMARY KEY,
                factor_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                code_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                used_at TEXT,
                invalidated_at TEXT,
                FOREIGN KEY(factor_id) REFERENCES web_totp_factors(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_totp_recovery_codes_factor
            ON web_totp_recovery_codes(factor_id, account_id, used_at, invalidated_at)
            """
        )
        # Password login may complete its first factor before a signed session
        # exists. This short-lived, opaque challenge binds the second-factor
        # proof to that successful password check without exposing an account
        # id or persisting a raw browser token.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_totp_login_challenges (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending', 'consumed', 'locked', 'superseded')),
                attempt_count INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_totp_login_challenges_account
            ON web_totp_login_challenges(account_id, state, expires_at, created_at DESC)
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_idempotency_scope_created ON web_idempotency(scope, created_at)"
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
        # Password credential throttling is a tiny, Web-owned abuse-control
        # record.  It intentionally persists only HMAC fingerprints and fixed
        # timing/counter fields: never an email address, remote IP, password,
        # cookie, session ID, request body or Bot/provider/payment state. The
        # third key also holds a domain-separated HMAC-only email-global
        # sentinel; it is never a literal marker or raw network address.
        # ``BEGIN IMMEDIATE`` in copyfast_auth_throttle serializes updates so
        # a restart or concurrent Web worker cannot reset/overrun a bucket.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_auth_throttle_buckets (
                action TEXT NOT NULL,
                email_hmac TEXT NOT NULL,
                client_scope_hmac TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                window_started_at INTEGER NOT NULL,
                expires_at_epoch INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(action, email_hmac, client_scope_hmac)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_auth_throttle_expiry ON web_auth_throttle_buckets(expires_at_epoch)"
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
                revision INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Campaign Planner predates optimistic source binding for explicit
        # in-app reminders.  The additive revision lets a schedule intent
        # fail closed after any local plan edit without changing old plan IDs,
        # Calendar semantics or canonical Bot campaign state.
        campaign_plan_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_campaign_plans)").fetchall()}
        if "revision" not in campaign_plan_columns:
            conn.execute("ALTER TABLE web_campaign_plans ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
        conn.execute(
            "UPDATE web_campaign_plans SET revision=1 WHERE revision IS NULL OR typeof(revision)!='integer' OR revision<1"
        )
        # A Campaign schedule intent is a separate, explicit owner request
        # for exactly one future private Inbox record.  It deliberately keeps
        # only opaque source coordinates and a digest — never a Campaign
        # title, destination URL, review note, publishing payload, provider
        # handle, payment data or a copy of the source itself.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_campaign_schedule_intents (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                source_revision INTEGER NOT NULL,
                source_snapshot_hash TEXT NOT NULL,
                trigger_local_at TEXT NOT NULL,
                timezone TEXT NOT NULL,
                trigger_at TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_by_account_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                dispatched_at TEXT,
                guarded_at TEXT,
                guard_code TEXT,
                cancelled_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(created_by_account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(plan_id) REFERENCES web_campaign_plans(id)
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
                lifecycle_revision INTEGER NOT NULL DEFAULT 1,
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
        # Support Desk is a separate, account-owned customer-service surface.
        # These names intentionally never overlap Bot `support_tickets` /
        # `support_ticket_messages`: a Web case cannot become a hidden Bot
        # ticket, Telegram alert, Xu refund, PayOS action or provider task.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_cases (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                subject TEXT NOT NULL,
                initial_detail TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'new',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_public_message_at TEXT NOT NULL,
                resolved_at TEXT,
                closed_at TEXT,
                -- This is deliberately separate from generic updated_at.
                -- It is set only when a customer is actually waiting for a
                -- Web Support response, so internal routing/triage cannot
                -- make an overdue request look newly serviced.
                customer_waiting_since TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Older local databases predate the semantic SLA clock.  A NULL
        # clock is intentionally fail-closed: Operations will not infer a
        # customer wait from generic update time or create/close an SLA
        # incident until a genuine Web customer-waiting event establishes it.
        support_case_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_support_cases)").fetchall()}
        if "customer_waiting_since" not in support_case_columns:
            conn.execute("ALTER TABLE web_support_cases ADD COLUMN customer_waiting_since TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_messages (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                author_account_id TEXT NOT NULL,
                author_role TEXT NOT NULL,
                visibility TEXT NOT NULL DEFAULT 'public',
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(author_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                actor_account_id TEXT,
                action TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_cases_account_state_updated ON web_support_cases(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_cases_state_updated ON web_support_cases(state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_cases_state_customer_waiting ON web_support_cases(state, customer_waiting_since ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_messages_case_visibility_created ON web_support_messages(case_id, visibility, created_at ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_events_case_created ON web_support_events(case_id, created_at ASC, id ASC)"
        )
        # Evidence attachments deliberately link an already-private Asset
        # Vault record instead of accepting a second file-upload route in
        # Support Desk.  The snapshots keep a historical, bounded display
        # projection without ever exposing the Asset Vault storage key, hash
        # or original filename through a case/event/audit response.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_case_attachments (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                display_name_snapshot TEXT NOT NULL,
                content_type_snapshot TEXT NOT NULL,
                byte_size_snapshot INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(case_id, asset_id),
                CHECK(byte_size_snapshot > 0 AND byte_size_snapshot <= 5242880),
                CHECK(content_type_snapshot IN ('image/png', 'image/jpeg', 'image/webp', 'text/plain')),
                FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_case_attachments_case_created ON web_support_case_attachments(case_id, created_at ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_case_attachments_account_case ON web_support_case_attachments(account_id, case_id, created_at ASC)"
        )
        # Customer Care control data is deliberately additive to the original
        # Web Support Desk case table.  It records only Web-native internal
        # queue, assignment, SLA and escalation metadata; it never becomes a
        # Bot ticket, payment/refund record, provider retry or outbound
        # notification.  Keeping it in separate tables preserves existing
        # case rows and makes the customer-facing projection fail closed: only
        # staff handlers join and return this metadata.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_case_controls (
                case_id TEXT PRIMARY KEY,
                team_queue TEXT NOT NULL DEFAULT 'general',
                assigned_account_id TEXT,
                sla_class TEXT NOT NULL DEFAULT 'standard',
                first_staff_touched_at TEXT,
                escalation_state TEXT NOT NULL DEFAULT 'none',
                escalation_reason TEXT NOT NULL DEFAULT '',
                escalation_requested_at TEXT,
                escalation_acknowledged_at TEXT,
                escalation_resolved_at TEXT,
                escalation_actor_account_id TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(assigned_account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(escalation_actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_case_control_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                actor_account_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                action TEXT NOT NULL,
                previous_value TEXT NOT NULL DEFAULT '',
                next_value TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_case_controls_queue_sla_updated ON web_support_case_controls(team_queue, sla_class, updated_at DESC, case_id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_case_controls_assignee_updated ON web_support_case_controls(assigned_account_id, updated_at DESC, case_id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_case_control_events_case_created ON web_support_case_control_events(case_id, created_at ASC, id ASC)"
        )
        # Prompt Library is a private Web-owned template vault.  It does not
        # reuse the frozen Bot's global prompt seed or mutable JSON path:
        # every record belongs to a signed Web account and every change has a
        # compact immutable snapshot for conflict-safe version history.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_prompt_templates (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                product_context TEXT NOT NULL DEFAULT '',
                platform TEXT NOT NULL DEFAULT '',
                style TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT '',
                prompt_text TEXT NOT NULL,
                negative_prompt TEXT NOT NULL DEFAULT '',
                variables_json TEXT NOT NULL DEFAULT '[]',
                tags_json TEXT NOT NULL DEFAULT '[]',
                source_note TEXT NOT NULL DEFAULT '',
                license_note TEXT NOT NULL DEFAULT '',
                quality_score INTEGER NOT NULL DEFAULT 50,
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
            CREATE TABLE IF NOT EXISTS web_prompt_template_versions (
                id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                product_context TEXT NOT NULL DEFAULT '',
                platform TEXT NOT NULL DEFAULT '',
                style TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT '',
                prompt_text TEXT NOT NULL,
                negative_prompt TEXT NOT NULL DEFAULT '',
                variables_json TEXT NOT NULL DEFAULT '[]',
                tags_json TEXT NOT NULL DEFAULT '[]',
                source_note TEXT NOT NULL DEFAULT '',
                license_note TEXT NOT NULL DEFAULT '',
                quality_score INTEGER NOT NULL DEFAULT 50,
                state TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                UNIQUE(template_id, revision),
                FOREIGN KEY(template_id) REFERENCES web_prompt_templates(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_prompt_template_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(template_id) REFERENCES web_prompt_templates(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_prompt_templates_account_state_updated ON web_prompt_templates(account_id, state, updated_at DESC, id DESC)"
        )
        # A saved Free Prompt Gallery seed is still a normal, private Prompt
        # Library template.  This tiny owner-scoped provenance map only
        # prevents an explicit Web save click from creating duplicate copies
        # of the same immutable Gallery item.  It has no Bot/global-library
        # relationship, no content payload, no provider/job/payment field and
        # cascades away if the owner deliberately purges the template.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_prompt_gallery_saves (
                account_id TEXT NOT NULL,
                gallery_prompt_id TEXT NOT NULL,
                snapshot_version TEXT NOT NULL,
                template_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(account_id, gallery_prompt_id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(template_id) REFERENCES web_prompt_templates(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_prompt_gallery_saves_template ON web_prompt_gallery_saves(template_id, account_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_prompt_template_versions_template_revision ON web_prompt_template_versions(template_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_prompt_template_events_account_created ON web_prompt_template_events(account_id, created_at DESC, id DESC)"
        )
        # Audio Library & Briefing is intentionally a Web-native organizer, not
        # a mirror of Telegram preview state or an external provider catalog.
        # Items retain only an owner-checked Asset Vault ID plus declared
        # attribution/rights metadata; no storage key, URL, Bot file ID,
        # provider payload, job, wallet or payment data is persisted here.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_media_collections (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                creative_brief TEXT NOT NULL DEFAULT '',
                prompt_mode TEXT NOT NULL DEFAULT 'background',
                use_context TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                rights_note TEXT NOT NULL DEFAULT '',
                policy_marker TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_media_collection_versions (
                id TEXT PRIMARY KEY,
                collection_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(collection_id, revision),
                FOREIGN KEY(collection_id) REFERENCES web_media_collections(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_media_items (
                id TEXT PRIMARY KEY,
                collection_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'music',
                title_override TEXT NOT NULL DEFAULT '',
                attribution TEXT NOT NULL DEFAULT '',
                license_note TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                favorite INTEGER NOT NULL DEFAULT 0,
                user_declared_duration_seconds INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(collection_id, asset_id),
                FOREIGN KEY(collection_id) REFERENCES web_media_collections(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_media_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                collection_id TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(collection_id) REFERENCES web_media_collections(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_media_collections_account_state_updated ON web_media_collections(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_media_collection_versions_collection_revision ON web_media_collection_versions(collection_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_media_items_collection_updated ON web_media_items(collection_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_media_items_asset_account ON web_media_items(asset_id, account_id, id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_media_events_account_created ON web_media_events(account_id, created_at DESC, id DESC)"
        )
        # Creative Content Studio is a signed-account authoring surface.  Its
        # records are deliberately separate from Bot feature forms, jobs,
        # provider calls, payments and output delivery.  Reference IDs point
        # only to existing Web-owned metadata; snapshot JSON stores the
        # authoring fields and reference labels needed for immutable history,
        # never a campaign destination, media storage key, URL or provider
        # data.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_briefs (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                campaign_plan_id TEXT,
                prompt_template_id TEXT,
                media_collection_id TEXT,
                title TEXT NOT NULL,
                content_kind TEXT NOT NULL,
                subject TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                audience TEXT NOT NULL DEFAULT '',
                platform TEXT NOT NULL DEFAULT '',
                tone TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT 'vi',
                call_to_action TEXT NOT NULL DEFAULT '',
                brief_text TEXT NOT NULL,
                constraints TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                rights_note TEXT NOT NULL DEFAULT '',
                policy_marker TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                selected_variant_id TEXT,
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id),
                FOREIGN KEY(campaign_plan_id) REFERENCES web_campaign_plans(id),
                FOREIGN KEY(prompt_template_id) REFERENCES web_prompt_templates(id),
                FOREIGN KEY(media_collection_id) REFERENCES web_media_collections(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_brief_versions (
                id TEXT PRIMARY KEY,
                brief_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(brief_id, revision),
                FOREIGN KEY(brief_id) REFERENCES web_content_briefs(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_variants (
                id TEXT PRIMARY KEY,
                brief_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                title TEXT NOT NULL,
                content_text TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                source_kind TEXT NOT NULL DEFAULT 'manual',
                source_brief_revision INTEGER NOT NULL DEFAULT 1,
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(brief_id, ordinal),
                FOREIGN KEY(brief_id) REFERENCES web_content_briefs(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_variant_versions (
                id TEXT PRIMARY KEY,
                variant_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(variant_id, revision),
                FOREIGN KEY(variant_id) REFERENCES web_content_variants(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_studio_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                brief_id TEXT NOT NULL,
                variant_id TEXT,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(brief_id) REFERENCES web_content_briefs(id),
                FOREIGN KEY(variant_id) REFERENCES web_content_variants(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_briefs_account_state_updated ON web_content_briefs(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_briefs_project_account_updated ON web_content_briefs(project_id, account_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_brief_versions_brief_revision ON web_content_brief_versions(brief_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_variants_brief_account_updated ON web_content_variants(brief_id, account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_variant_versions_variant_revision ON web_content_variant_versions(variant_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_events_account_created ON web_content_studio_events(account_id, created_at DESC, id DESC)"
        )
        # Channel Strategy is the Web-owned, revisioned replacement for the
        # Bot's lightweight ``channel_profiles`` conversation.  These tables
        # deliberately store only account-authored profile metadata and small
        # snapshots: never Bot IDs/state, social tokens, remote URL fetches,
        # platform analytics, provider handles, jobs, payments, Xu/PayOS,
        # media outputs or publication receipts.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_channel_strategy_profiles (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel_url TEXT NOT NULL DEFAULT '',
                niche TEXT NOT NULL,
                target_audience TEXT NOT NULL,
                content_style TEXT NOT NULL,
                tone TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT 'vi',
                allowed_topics_json TEXT NOT NULL DEFAULT '[]',
                blocked_topics_json TEXT NOT NULL DEFAULT '[]',
                brand_keywords_json TEXT NOT NULL DEFAULT '[]',
                cta_default TEXT NOT NULL DEFAULT '',
                affiliate_allowed INTEGER NOT NULL DEFAULT 0,
                product_categories_json TEXT NOT NULL DEFAULT '[]',
                posting_frequency TEXT NOT NULL DEFAULT '',
                preferred_aspect_ratio TEXT NOT NULL DEFAULT '9:16',
                preferred_duration_seconds INTEGER NOT NULL DEFAULT 18,
                primary_goal TEXT NOT NULL DEFAULT 'content',
                notes TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_channel_strategy_profile_versions (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(profile_id, revision),
                FOREIGN KEY(profile_id) REFERENCES web_channel_strategy_profiles(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_channel_strategy_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES web_channel_strategy_profiles(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_channel_strategy_profiles_account_state_updated ON web_channel_strategy_profiles(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_channel_strategy_versions_profile_revision ON web_channel_strategy_profile_versions(profile_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_channel_strategy_events_profile_created ON web_channel_strategy_events(profile_id, account_id, created_at DESC, id DESC)"
        )
        # Voice Studio is an independently owned authoring surface.  The
        # tables intentionally store only text/metadata, version snapshots
        # and audit-friendly state.  They must never grow Bot voice profile
        # IDs, provider references, raw audio, preview URLs, jobs, Xu, PayOS
        # or payment columns without a separate reviewed integration.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_voice_vaults (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                content_brief_id TEXT,
                title TEXT NOT NULL,
                vault_kind TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'vi',
                style_notes TEXT NOT NULL DEFAULT '',
                use_context TEXT NOT NULL DEFAULT '',
                consent_status TEXT NOT NULL DEFAULT 'not_required',
                consent_note TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                policy_marker TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                is_default INTEGER NOT NULL DEFAULT 0,
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id),
                FOREIGN KEY(content_brief_id) REFERENCES web_content_briefs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_voice_vault_versions (
                id TEXT PRIMARY KEY,
                vault_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(vault_id, revision),
                FOREIGN KEY(vault_id) REFERENCES web_voice_vaults(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_voice_scripts (
                id TEXT PRIMARY KEY,
                vault_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                title TEXT NOT NULL,
                script_kind TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'vi',
                audience TEXT NOT NULL DEFAULT '',
                pace_wpm INTEGER NOT NULL DEFAULT 145,
                script_text TEXT NOT NULL,
                delivery_notes TEXT NOT NULL DEFAULT '',
                pronunciation_notes TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                policy_marker TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT 'manual',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(vault_id, ordinal),
                FOREIGN KEY(vault_id) REFERENCES web_voice_vaults(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_voice_script_versions (
                id TEXT PRIMARY KEY,
                script_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(script_id, revision),
                FOREIGN KEY(script_id) REFERENCES web_voice_scripts(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_voice_studio_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                vault_id TEXT NOT NULL,
                script_id TEXT,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(vault_id) REFERENCES web_voice_vaults(id),
                FOREIGN KEY(script_id) REFERENCES web_voice_scripts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_voice_vaults_account_state_updated ON web_voice_vaults(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_voice_vaults_project_account_updated ON web_voice_vaults(project_id, account_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_voice_vault_versions_vault_revision ON web_voice_vault_versions(vault_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_voice_scripts_vault_account_updated ON web_voice_scripts(vault_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_voice_script_versions_script_revision ON web_voice_script_versions(script_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_voice_events_account_created ON web_voice_studio_events(account_id, created_at DESC, id DESC)"
        )
        # Video Production Studio is a Web-owned planning surface.  It keeps
        # only authored plan/scene text, sequence metadata and immutable
        # revisions.  In particular, it deliberately has no media bytes,
        # file references, render identifiers, external runtime state,
        # wallet, payment or delivery columns.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_plans (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                title TEXT NOT NULL,
                video_format TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'vi',
                aspect_ratio TEXT NOT NULL DEFAULT '9:16',
                target_duration_seconds INTEGER NOT NULL DEFAULT 30,
                objective TEXT NOT NULL DEFAULT '',
                audience TEXT NOT NULL DEFAULT '',
                brief TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                lifecycle TEXT NOT NULL DEFAULT 'draft',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_plan_versions (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(plan_id, revision),
                FOREIGN KEY(plan_id) REFERENCES web_video_plans(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_scenes (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                title TEXT NOT NULL,
                scene_type TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL DEFAULT 5,
                visual_direction TEXT NOT NULL DEFAULT '',
                narration TEXT NOT NULL DEFAULT '',
                on_screen_text TEXT NOT NULL DEFAULT '',
                shot_notes TEXT NOT NULL DEFAULT '',
                transition TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(plan_id, ordinal),
                FOREIGN KEY(plan_id) REFERENCES web_video_plans(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_scene_versions (
                id TEXT PRIMARY KEY,
                scene_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(scene_id, revision),
                FOREIGN KEY(scene_id) REFERENCES web_video_scenes(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_studio_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                scene_id TEXT,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(plan_id) REFERENCES web_video_plans(id),
                FOREIGN KEY(scene_id) REFERENCES web_video_scenes(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_plans_account_lifecycle_updated ON web_video_plans(account_id, lifecycle, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_plans_project_account_updated ON web_video_plans(project_id, account_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_plan_versions_plan_revision ON web_video_plan_versions(plan_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_scenes_plan_account_ordinal ON web_video_scenes(plan_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_scene_versions_scene_revision ON web_video_scene_versions(scene_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_events_account_created ON web_video_studio_events(account_id, created_at DESC, id DESC)"
        )
        # Subtitle Studio is a deliberately text-only Web workspace.  It
        # persists user-authored cues, optional bilingual drafts and immutable
        # revisions, never raw uploads/media paths/provider IDs/ASR or dubbing
        # output/job/payment/delivery references.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_subtitle_projects (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                linked_project_id TEXT,
                title TEXT NOT NULL,
                source_language TEXT NOT NULL DEFAULT 'vi',
                target_language TEXT NOT NULL DEFAULT '',
                caption_format TEXT NOT NULL DEFAULT 'srt',
                context TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                intent TEXT NOT NULL DEFAULT 'subtitle',
                lifecycle TEXT NOT NULL DEFAULT 'draft',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(linked_project_id) REFERENCES web_projects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_subtitle_project_versions (
                id TEXT PRIMARY KEY,
                subtitle_project_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(subtitle_project_id, revision),
                FOREIGN KEY(subtitle_project_id) REFERENCES web_subtitle_projects(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_subtitle_cues (
                id TEXT PRIMARY KEY,
                subtitle_project_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                speaker TEXT NOT NULL DEFAULT '',
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(subtitle_project_id, ordinal),
                FOREIGN KEY(subtitle_project_id) REFERENCES web_subtitle_projects(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_subtitle_cue_versions (
                id TEXT PRIMARY KEY,
                cue_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(cue_id, revision),
                FOREIGN KEY(cue_id) REFERENCES web_subtitle_cues(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_subtitle_workspace_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                subtitle_project_id TEXT NOT NULL,
                cue_id TEXT,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(subtitle_project_id) REFERENCES web_subtitle_projects(id),
                FOREIGN KEY(cue_id) REFERENCES web_subtitle_cues(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_projects_account_lifecycle_updated ON web_subtitle_projects(account_id, lifecycle, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_projects_linked_account_updated ON web_subtitle_projects(linked_project_id, account_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_project_versions_project_revision ON web_subtitle_project_versions(subtitle_project_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_cues_project_account_ordinal ON web_subtitle_cues(subtitle_project_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_cue_versions_cue_revision ON web_subtitle_cue_versions(cue_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_events_account_created ON web_subtitle_workspace_events(account_id, created_at DESC, id DESC)"
        )
        # Image Creative Studio is a signed-account art-direction workspace.
        # It stores only text/metadata and UUID references to already-owned
        # Asset Vault image metadata.  There are intentionally no media
        # bytes, browser URLs, engine/provider identifiers, jobs, wallet,
        # payment or delivery columns in this Web-owned schema.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_artboards (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                title TEXT NOT NULL,
                image_intent TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'vi',
                aspect_ratio TEXT NOT NULL DEFAULT '1:1',
                output_format TEXT NOT NULL DEFAULT 'png',
                creative_brief TEXT NOT NULL DEFAULT '',
                style_direction TEXT NOT NULL DEFAULT '',
                negative_direction TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                lifecycle TEXT NOT NULL DEFAULT 'draft',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_artboard_versions (
                id TEXT PRIMARY KEY,
                artboard_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(artboard_id, revision),
                FOREIGN KEY(artboard_id) REFERENCES web_image_artboards(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_directions (
                id TEXT PRIMARY KEY,
                artboard_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                title TEXT NOT NULL,
                operation TEXT NOT NULL,
                prompt_text TEXT NOT NULL DEFAULT '',
                edit_instructions TEXT NOT NULL DEFAULT '',
                composition_notes TEXT NOT NULL DEFAULT '',
                negative_direction TEXT NOT NULL DEFAULT '',
                asset_id TEXT,
                reference_asset_id TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(artboard_id, ordinal),
                FOREIGN KEY(artboard_id) REFERENCES web_image_artboards(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(asset_id) REFERENCES web_asset_files(id),
                FOREIGN KEY(reference_asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_direction_versions (
                id TEXT PRIMARY KEY,
                direction_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(direction_id, revision),
                FOREIGN KEY(direction_id) REFERENCES web_image_directions(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_studio_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                artboard_id TEXT NOT NULL,
                direction_id TEXT,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(artboard_id) REFERENCES web_image_artboards(id),
                FOREIGN KEY(direction_id) REFERENCES web_image_directions(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_artboards_account_lifecycle_updated ON web_image_artboards(account_id, lifecycle, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_artboards_project_account_updated ON web_image_artboards(project_id, account_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_artboard_versions_artboard_revision ON web_image_artboard_versions(artboard_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_directions_artboard_account_ordinal ON web_image_directions(artboard_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_direction_versions_direction_revision ON web_image_direction_versions(direction_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_image_events_account_created ON web_image_studio_events(account_id, created_at DESC, id DESC)"
        )
        # Document & PDF Workspace is an authoring-only signed-account
        # surface.  It records customer planning text and opaque UUID
        # references to existing Asset Vault metadata; it never stores source
        # blobs, file paths, provider/Bot handles, OCR/translation payloads,
        # jobs, wallet/PayOS state or generated-output data.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_workspaces (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                title TEXT NOT NULL,
                document_type TEXT NOT NULL DEFAULT 'mixed',
                source_summary TEXT NOT NULL DEFAULT '',
                objective TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT 'vi',
                target_language TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                lifecycle TEXT NOT NULL DEFAULT 'draft',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_workspace_versions (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(workspace_id, revision),
                FOREIGN KEY(workspace_id) REFERENCES web_document_workspaces(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_plans (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                title TEXT NOT NULL,
                operation TEXT NOT NULL,
                instructions TEXT NOT NULL DEFAULT '',
                source_asset_id TEXT,
                reference_asset_id TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(workspace_id, ordinal),
                FOREIGN KEY(workspace_id) REFERENCES web_document_workspaces(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id),
                FOREIGN KEY(reference_asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_plan_versions (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(plan_id, revision),
                FOREIGN KEY(plan_id) REFERENCES web_document_plans(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_workspace_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                plan_id TEXT,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(workspace_id) REFERENCES web_document_workspaces(id),
                FOREIGN KEY(plan_id) REFERENCES web_document_plans(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_workspaces_account_lifecycle_updated ON web_document_workspaces(account_id, lifecycle, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_workspaces_project_account_updated ON web_document_workspaces(project_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_workspace_versions_workspace_revision ON web_document_workspace_versions(workspace_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_plans_workspace_account_ordinal ON web_document_plans(workspace_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_plan_versions_plan_revision ON web_document_plan_versions(plan_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_document_workspace_events_account_created ON web_document_workspace_events(account_id, created_at DESC, id DESC)"
        )
        # Conversation Workspace is a private Web-owned planning surface.
        # It stores only human-authored prompt/context/decision text and
        # compact metadata history.  Do not reuse Telegram conversations or
        # Bot modes, provider transcripts, tool calls, jobs, output, wallet,
        # payment, attachment or delivery state here.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_threads (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                prompt_template_id TEXT,
                title TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'focus',
                system_context TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                state TEXT NOT NULL DEFAULT 'draft',
                pinned INTEGER NOT NULL DEFAULT 0,
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id),
                FOREIGN KEY(prompt_template_id) REFERENCES web_prompt_templates(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_thread_versions (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(thread_id, revision),
                FOREIGN KEY(thread_id) REFERENCES web_chat_threads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_context_cards (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(thread_id, ordinal),
                FOREIGN KEY(thread_id) REFERENCES web_chat_threads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_turns (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                kind TEXT NOT NULL,
                body TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(thread_id, ordinal),
                FOREIGN KEY(thread_id) REFERENCES web_chat_threads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_workspace_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(thread_id) REFERENCES web_chat_threads(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_threads_account_state_updated ON web_chat_threads(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_threads_account_pinned_updated ON web_chat_threads(account_id, pinned DESC, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_thread_versions_thread_revision ON web_chat_thread_versions(thread_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_context_cards_thread_ordinal ON web_chat_context_cards(thread_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_turns_thread_ordinal ON web_chat_turns(thread_id, account_id, state, ordinal ASC, created_at ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_workspace_events_account_created ON web_chat_workspace_events(account_id, created_at DESC, id DESC)"
        )
        # Chat Runs represent a Web-native execution request contract.  They
        # are intentionally separate from the authoring turns above: a run
        # can truthfully be guarded before any model/provider is contacted,
        # and an assistant message is impossible to create without a future
        # reviewed adapter.  Do not put provider payloads, credentials,
        # wallet/payment/job fields or delivery URLs in these tables.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                run_id TEXT,
                ordinal INTEGER NOT NULL,
                role TEXT NOT NULL,
                body TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(thread_id, ordinal),
                FOREIGN KEY(thread_id) REFERENCES web_chat_threads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_runs (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                request_message_id TEXT NOT NULL,
                assistant_message_id TEXT,
                state TEXT NOT NULL DEFAULT 'draft',
                revision INTEGER NOT NULL,
                provider_execution_enabled INTEGER NOT NULL DEFAULT 0,
                error_code TEXT,
                requested_at TEXT NOT NULL,
                queued_at TEXT,
                processing_at TEXT,
                completed_at TEXT,
                failed_at TEXT,
                guarded_at TEXT,
                cancelled_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(thread_id) REFERENCES web_chat_threads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(request_message_id) REFERENCES web_chat_messages(id),
                FOREIGN KEY(assistant_message_id) REFERENCES web_chat_messages(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_chat_run_events (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                state TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, sequence),
                FOREIGN KEY(run_id) REFERENCES web_chat_runs(id),
                FOREIGN KEY(thread_id) REFERENCES web_chat_threads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_messages_thread_account_ordinal ON web_chat_messages(thread_id, account_id, ordinal ASC, created_at ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_runs_thread_account_updated ON web_chat_runs(thread_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_runs_account_state_updated ON web_chat_runs(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_chat_run_events_run_sequence ON web_chat_run_events(run_id, account_id, sequence ASC)"
        )
        # Analytics Workspace is an independent signed-account surface for
        # user-supplied metrics and deterministic local comparisons.  These
        # tables deliberately exclude social/platform API identifiers,
        # provider/Bot state, revenue, wallet/Xu, payment, job, publish,
        # attachment and delivery fields.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_reports (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                campaign_plan_id TEXT,
                title TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                context_label TEXT NOT NULL DEFAULT '',
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                summary_note TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                state TEXT NOT NULL DEFAULT 'draft',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id),
                FOREIGN KEY(campaign_plan_id) REFERENCES web_campaign_plans(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_report_versions (
                id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(report_id, revision),
                FOREIGN KEY(report_id) REFERENCES web_analytics_reports(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_metrics (
                id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'count',
                direction TEXT NOT NULL DEFAULT 'neutral',
                description TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(report_id, ordinal),
                FOREIGN KEY(report_id) REFERENCES web_analytics_reports(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_metric_versions (
                id TEXT PRIMARY KEY,
                metric_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(metric_id, revision),
                FOREIGN KEY(metric_id) REFERENCES web_analytics_metrics(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_snapshots (
                id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                metric_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                observed_on TEXT NOT NULL,
                value_decimal TEXT NOT NULL,
                source_label TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(report_id) REFERENCES web_analytics_reports(id),
                FOREIGN KEY(metric_id) REFERENCES web_analytics_metrics(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_snapshot_versions (
                id TEXT PRIMARY KEY,
                snapshot_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(snapshot_id, revision),
                FOREIGN KEY(snapshot_id) REFERENCES web_analytics_snapshots(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_findings (
                id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                kind TEXT NOT NULL,
                body TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(report_id, ordinal),
                FOREIGN KEY(report_id) REFERENCES web_analytics_reports(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_finding_versions (
                id TEXT PRIMARY KEY,
                finding_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(finding_id, revision),
                FOREIGN KEY(finding_id) REFERENCES web_analytics_findings(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_analytics_workspace_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                report_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(report_id) REFERENCES web_analytics_reports(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_reports_account_state_updated ON web_analytics_reports(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_reports_project_account_updated ON web_analytics_reports(project_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_reports_campaign_account_updated ON web_analytics_reports(campaign_plan_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_report_versions_report_revision ON web_analytics_report_versions(report_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_metrics_report_ordinal ON web_analytics_metrics(report_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_metric_versions_metric_revision ON web_analytics_metric_versions(metric_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_snapshots_report_metric_date ON web_analytics_snapshots(report_id, metric_id, account_id, state, observed_on DESC, updated_at DESC)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_web_analytics_snapshots_active_metric_date ON web_analytics_snapshots(metric_id, observed_on) WHERE state='active'"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_snapshot_versions_snapshot_revision ON web_analytics_snapshot_versions(snapshot_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_findings_report_ordinal ON web_analytics_findings(report_id, account_id, state, ordinal ASC, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_finding_versions_finding_revision ON web_analytics_finding_versions(finding_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_analytics_workspace_events_account_created ON web_analytics_workspace_events(account_id, created_at DESC, id DESC)"
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
        # A Starter Kit is an explicit, one-time Web-owned launch receipt.
        # It deliberately records only the reviewed kit digest and the local
        # Project/Document/Workboard counts.  It must never become a shadow
        # Bot job, provider operation, wallet ledger, payment record or media
        # delivery table.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workspace_starter_kit_installs (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                kit_key TEXT NOT NULL,
                kit_version INTEGER NOT NULL CHECK(kit_version > 0),
                kit_digest TEXT NOT NULL CHECK(length(kit_digest) = 64),
                setup_profile_revision INTEGER NOT NULL CHECK(setup_profile_revision >= 0),
                project_id TEXT NOT NULL UNIQUE,
                document_count INTEGER NOT NULL CHECK(document_count >= 0),
                work_item_count INTEGER NOT NULL CHECK(work_item_count >= 0),
                created_at TEXT NOT NULL,
                UNIQUE(account_id, kit_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
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
                lifecycle_revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        # Older Asset Vault databases predate the explicit lifecycle token.
        # Keep this additive: archive/restore use it as an optimistic
        # concurrency guard rather than treating a generic timestamp as one.
        asset_file_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_asset_files)").fetchall()}
        if "lifecycle_revision" not in asset_file_columns:
            conn.execute("ALTER TABLE web_asset_files ADD COLUMN lifecycle_revision INTEGER NOT NULL DEFAULT 1")
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
        # Subtitle Asset Operations are deliberately distinct from the
        # authored Subtitle Studio and from document/image executors. A row
        # carries only immutable source/output evidence and safe metadata;
        # it never stores cue text, paths, Bot/provider handles, wallet/Xu or
        # PayOS data.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_subtitle_asset_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                project_id TEXT,
                kind TEXT NOT NULL,
                target_format TEXT,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_lifecycle_revision INTEGER NOT NULL,
                source_format TEXT NOT NULL,
                cue_count INTEGER,
                timed_duration_ms INTEGER,
                semantic_sha256 TEXT,
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
            CREATE TABLE IF NOT EXISTS web_subtitle_asset_operation_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_subtitle_asset_operations(id)
            )
            """
        )
        subtitle_asset_event_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(web_subtitle_asset_operation_events)").fetchall()
        }
        if "sequence" not in subtitle_asset_event_columns:
            conn.execute("ALTER TABLE web_subtitle_asset_operation_events ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0")

        # Audio Asset Operations are a separate local execution boundary from
        # Audio Library metadata, Video operations and Bot/provider media
        # workflows. Rows keep only immutable source/output evidence plus
        # bounded probe fields; raw audio, local paths, FFmpeg argv, provider
        # handles, wallet/Xu and PayOS data never enter this table.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_audio_asset_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                project_id TEXT,
                kind TEXT NOT NULL,
                target_format TEXT,
                normalization_profile TEXT,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_lifecycle_revision INTEGER NOT NULL,
                source_format TEXT NOT NULL,
                source_duration_ms INTEGER,
                source_channels INTEGER,
                source_sample_rate INTEGER,
                source_codec TEXT,
                output_duration_ms INTEGER,
                output_channels INTEGER,
                output_sample_rate INTEGER,
                output_codec TEXT,
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
            CREATE TABLE IF NOT EXISTS web_audio_asset_operation_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_audio_asset_operations(id)
            )
            """
        )
        audio_asset_event_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(web_audio_asset_operation_events)").fetchall()
        }
        if "sequence" not in audio_asset_event_columns:
            conn.execute("ALTER TABLE web_audio_asset_operation_events ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0")

        # Storyboard Grid keeps its bounded scene cuts in a purpose-specific
        # table instead of overloading Web image transforms.  A completed
        # operation delivers one verified private JPEG-scene ZIP/manifest;
        # its per-cell evidence remains append-only and never becomes a Bot
        # job, provider artifact, Asset Vault source, wallet/Xu or PayOS row.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_storyboard_grid_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                project_id TEXT,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_width INTEGER NOT NULL,
                source_height INTEGER NOT NULL,
                rows INTEGER NOT NULL,
                cols INTEGER NOT NULL,
                episode INTEGER NOT NULL,
                start_scene INTEGER NOT NULL,
                trim_percent REAL NOT NULL,
                scene_count INTEGER NOT NULL,
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
                UNIQUE(account_id, idempotency_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id),
                FOREIGN KEY(project_id) REFERENCES web_projects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_storyboard_grid_cells (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                scene_no INTEGER NOT NULL,
                row_index INTEGER NOT NULL,
                column_index INTEGER NOT NULL,
                crop_x INTEGER NOT NULL,
                crop_y INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                UNIQUE(operation_id, scene_no),
                UNIQUE(operation_id, row_index, column_index),
                FOREIGN KEY(operation_id) REFERENCES web_storyboard_grid_operations(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_storyboard_grid_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_storyboard_grid_operations(id)
            )
            """
        )
        # Video Operations is the first bounded Web-native media execution
        # boundary.  It is deliberately separate from Video Studio plans,
        # Bot jobs and Asset Vault sources: one immutable owner-scoped source
        # can produce only a verified private artifact after local runtime
        # validation.  Attempt rows make an interrupted in-request executor
        # auditable and leave a durable seam for a future worker lease.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_extension TEXT NOT NULL,
                source_content_type TEXT NOT NULL,
                poster_position TEXT NOT NULL,
                source_duration_ms INTEGER,
                source_width INTEGER,
                source_height INTEGER,
                frame_timestamp_ms INTEGER,
                output_width INTEGER,
                output_height INTEGER,
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
                revision INTEGER NOT NULL DEFAULT 1,
                UNIQUE(account_id, kind, idempotency_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_operation_attempts (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                state TEXT NOT NULL,
                fence_token TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                failure_code TEXT,
                UNIQUE(operation_id, attempt_no),
                UNIQUE(operation_id, fence_token),
                FOREIGN KEY(operation_id) REFERENCES web_video_operations(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_operation_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_video_operations(id)
            )
            """
        )
        # Frame Video Lab is intentionally independent from single-video
        # Poster extraction.  It stores an immutable ordered source snapshot
        # and only a verified private H.264 output receipt; paths, URLs,
        # FFmpeg arguments, provider handles, wallet/Xu and PayOS state never
        # belong in these records.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_frame_video_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                aspect_ratio TEXT NOT NULL,
                seconds_per_image REAL NOT NULL,
                effect TEXT NOT NULL,
                source_count INTEGER NOT NULL,
                source_total_bytes INTEGER NOT NULL,
                output_duration_ms INTEGER,
                output_width INTEGER,
                output_height INTEGER,
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
                revision INTEGER NOT NULL DEFAULT 1,
                UNIQUE(account_id, kind, idempotency_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_frame_video_operation_sources (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                source_index INTEGER NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_extension TEXT NOT NULL,
                source_content_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(operation_id, source_index),
                UNIQUE(operation_id, source_asset_id),
                FOREIGN KEY(operation_id) REFERENCES web_frame_video_operations(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_frame_video_operation_attempts (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                state TEXT NOT NULL,
                fence_token TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                failure_code TEXT,
                UNIQUE(operation_id, attempt_no),
                UNIQUE(operation_id, fence_token),
                FOREIGN KEY(operation_id) REFERENCES web_frame_video_operations(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_frame_video_operation_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_frame_video_operations(id)
            )
            """
        )
        # Video Finishing is a separate, bounded local video transform.  It
        # records an immutable Asset Vault snapshot plus a closed transform
        # receipt, never an input/output path, FFmpeg filter graph, provider
        # handle, Bot job, wallet/Xu state, payment state or remote URL.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_transform_operations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_asset_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued',
                idempotency_key TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_byte_size INTEGER NOT NULL,
                source_extension TEXT NOT NULL,
                source_content_type TEXT NOT NULL,
                target_ratio TEXT NOT NULL,
                fit_mode TEXT NOT NULL,
                preset TEXT NOT NULL,
                sharpen INTEGER NOT NULL DEFAULT 0,
                preserve_audio INTEGER NOT NULL DEFAULT 1,
                source_duration_ms INTEGER,
                source_width INTEGER,
                source_height INTEGER,
                output_duration_ms INTEGER,
                output_width INTEGER,
                output_height INTEGER,
                output_has_audio INTEGER,
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
                revision INTEGER NOT NULL DEFAULT 1,
                UNIQUE(account_id, kind, idempotency_key),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(source_asset_id) REFERENCES web_asset_files(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_transform_operation_attempts (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                state TEXT NOT NULL,
                fence_token TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                failure_code TEXT,
                UNIQUE(operation_id, attempt_no),
                UNIQUE(operation_id, fence_token),
                FOREIGN KEY(operation_id) REFERENCES web_video_transform_operations(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_transform_operation_events (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                state TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(operation_id) REFERENCES web_video_transform_operations(id)
            )
            """
        )
        # Workboard is a private, Web-native planning surface.  These tables
        # never store remote URLs, Bot/provider handles, execution output,
        # wallet/payment data or notification-delivery state.  A reference is
        # deliberately an opaque UUID plus a closed source type; the router
        # validates that the referenced Project/Campaign/Analytics/Note/Draft
        # belongs to the same signed account before every write.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workboard_items (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'normal',
                due_at TEXT,
                state TEXT NOT NULL DEFAULT 'backlog',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workboard_item_references (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ref_type TEXT NOT NULL,
                ref_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(item_id, ref_type, ref_id),
                UNIQUE(item_id, ordinal),
                FOREIGN KEY(item_id) REFERENCES web_workboard_items(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workboard_checklist_items (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                body TEXT NOT NULL,
                is_done INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(item_id, ordinal),
                FOREIGN KEY(item_id) REFERENCES web_workboard_items(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Snapshots are append-only evidence for an item as a whole.  They
        # include the active and archived checklist/reference set at the
        # revision, allowing a recovery action to create a new revision
        # without ever overwriting history.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workboard_item_versions (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(item_id, revision),
                FOREIGN KEY(item_id) REFERENCES web_workboard_items(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Checklist snapshots remain independently append-only as well.  An
        # item snapshot is sufficient to restore the complete board card,
        # while this table gives a checklist row its own traceable history.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workboard_checklist_versions (
                id TEXT PRIMARY KEY,
                checklist_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(checklist_id, revision),
                FOREIGN KEY(checklist_id) REFERENCES web_workboard_checklist_items(id),
                FOREIGN KEY(item_id) REFERENCES web_workboard_items(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Events deliberately contain only operation metadata and IDs, never
        # private descriptions/checklist text.  This makes the board timeline
        # auditable without duplicating sensitive authoring content.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workboard_events (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                action TEXT NOT NULL,
                item_revision INTEGER NOT NULL,
                entity_revision INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(item_id) REFERENCES web_workboard_items(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # A Workboard schedule intent is an explicit, account-owned request
        # to create one future *in-app* Inbox record.  It stores only opaque
        # item coordinates and a snapshot hash; title, description,
        # checklist, references and all delivery/provider data deliberately
        # stay out of this table.  The Notification tick must re-check the
        # revision and snapshot before it can materialize anything.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_workboard_schedule_intents (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                source_revision INTEGER NOT NULL,
                source_snapshot_hash TEXT NOT NULL,
                trigger_local_at TEXT NOT NULL,
                timezone TEXT NOT NULL,
                trigger_at TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'active',
                revision INTEGER NOT NULL DEFAULT 1,
                created_by_account_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                dispatched_at TEXT,
                guarded_at TEXT,
                guard_code TEXT,
                cancelled_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(created_by_account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(item_id) REFERENCES web_workboard_items(id)
            )
            """
        )
        # Notification Center owns only durable, in-app inbox metadata. It is
        # deliberately separate from Browser/Telegram/email/web-push delivery
        # and stores no source title/body, provider/payment/job payload,
        # external URL, credential or raw support narrative.  A scheduler can
        # materialize an allow-listed occurrence while a signed account owns
        # the read/dismiss lifecycle.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_notification_nonces (
                nonce_hash TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                key_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_notification_leases (
                name TEXT PRIMARY KEY,
                owner_run_id TEXT NOT NULL,
                fence_token INTEGER NOT NULL,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_notification_runs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                trigger TEXT NOT NULL,
                schedule_slot TEXT NOT NULL,
                state TEXT NOT NULL,
                fence_token INTEGER NOT NULL,
                policy_version INTEGER NOT NULL,
                input_hash TEXT NOT NULL,
                action_count INTEGER NOT NULL DEFAULT 0,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                deadline_at TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                error_code TEXT,
                receipt_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_notification_run_steps (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                playbook TEXT NOT NULL,
                state TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                input_hash TEXT NOT NULL,
                result_code TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                finished_at TEXT,
                UNIQUE(run_id, sequence),
                FOREIGN KEY(run_id) REFERENCES web_notification_runs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_notification_items (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_revision INTEGER NOT NULL,
                occurrence_at TEXT NOT NULL,
                severity TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'unread',
                revision INTEGER NOT NULL DEFAULT 1,
                dedupe_fingerprint TEXT NOT NULL UNIQUE,
                created_by_run_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                read_at TEXT,
                dismissed_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(created_by_run_id) REFERENCES web_notification_runs(id)
            )
            """
        )
        # Tombstones retain only an opaque occurrence fingerprint and source
        # coordinates after an explicitly dismissed Inbox row ages out. They
        # prevent an unchanged overdue reminder from being re-materialized
        # forever while allowing the UI/event payload itself to stay bounded.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_notification_dedupes (
                dedupe_fingerprint TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_revision INTEGER NOT NULL,
                occurrence_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """INSERT OR IGNORE INTO web_notification_dedupes
               (dedupe_fingerprint, account_id, source_kind, source_id, source_revision, occurrence_at, created_at)
               SELECT dedupe_fingerprint, account_id, source_kind, source_id, source_revision, occurrence_at, created_at
               FROM web_notification_items"""
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_notification_events (
                id TEXT PRIMARY KEY,
                notification_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                actor_account_id TEXT,
                action TEXT NOT NULL,
                state TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(notification_id) REFERENCES web_notification_items(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Operations Autopilot is intentionally an append-oriented, Web-only
        # observability surface.  It records signed scheduler receipts,
        # deterministic support triage and operator approval metadata, but
        # never persists provider payloads, payment records, wallet state,
        # Bot jobs, customer secrets or raw exception narratives.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_nonces (
                nonce_hash TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                key_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_leases (
                name TEXT PRIMARY KEY,
                owner_run_id TEXT NOT NULL,
                fence_token INTEGER NOT NULL,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_runs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                trigger TEXT NOT NULL,
                schedule_slot TEXT NOT NULL,
                state TEXT NOT NULL,
                fence_token INTEGER NOT NULL,
                policy_version INTEGER NOT NULL,
                input_hash TEXT NOT NULL,
                action_count INTEGER NOT NULL DEFAULT 0,
                triaged_case_count INTEGER NOT NULL DEFAULT 0,
                incident_count INTEGER NOT NULL DEFAULT 0,
                deadline_at TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                error_code TEXT,
                receipt_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        # This row is deliberately separate from Operations run history.  A
        # heartbeat is armed only from a run that has already completed under
        # the current Web-process/configuration snapshot; historical rows
        # must never become an implicit baseline when the optional feature is
        # first enabled or the process is redeployed.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_heartbeat_baselines (
                scope TEXT PRIMARY KEY,
                config_fingerprint TEXT NOT NULL,
                process_epoch TEXT NOT NULL,
                last_completed_run_id TEXT,
                last_completed_at TEXT,
                armed_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(last_completed_run_id) REFERENCES web_ops_runs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_run_steps (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                playbook TEXT NOT NULL,
                state TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                result_code TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                finished_at TEXT,
                UNIQUE(run_id, sequence),
                UNIQUE(idempotency_key),
                FOREIGN KEY(run_id) REFERENCES web_ops_runs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_incidents (
                id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                scope_kind TEXT NOT NULL,
                account_id TEXT,
                support_case_id TEXT,
                state TEXT NOT NULL,
                severity TEXT NOT NULL,
                auto_close_eligible INTEGER NOT NULL DEFAULT 0,
                healthy_streak INTEGER NOT NULL DEFAULT 0,
                observation_count INTEGER NOT NULL DEFAULT 0,
                last_failure_at TEXT,
                first_observed_at TEXT NOT NULL,
                last_observed_at TEXT NOT NULL,
                resolved_at TEXT,
                closed_at TEXT,
                revision INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(support_case_id) REFERENCES web_support_cases(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_incident_observations (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                observation TEXT NOT NULL,
                result_code TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(incident_id) REFERENCES web_ops_incidents(id),
                FOREIGN KEY(run_id) REFERENCES web_ops_runs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_playbook_runs (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                incident_id TEXT,
                playbook TEXT NOT NULL,
                state TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 1,
                idempotency_key TEXT NOT NULL UNIQUE,
                input_hash TEXT NOT NULL,
                result_code TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY(run_id) REFERENCES web_ops_runs(id),
                FOREIGN KEY(incident_id) REFERENCES web_ops_incidents(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_approvals (
                id TEXT PRIMARY KEY,
                proposal_fingerprint TEXT NOT NULL UNIQUE,
                action_type TEXT NOT NULL,
                account_id TEXT,
                support_case_id TEXT,
                incident_id TEXT,
                risk TEXT NOT NULL,
                required_role TEXT NOT NULL,
                state TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                payload_hash TEXT NOT NULL,
                proposed_by_run_id TEXT,
                proposed_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                decided_at TEXT,
                decided_by_account_id TEXT,
                decision_code TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(support_case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(incident_id) REFERENCES web_ops_incidents(id),
                FOREIGN KEY(proposed_by_run_id) REFERENCES web_ops_runs(id),
                FOREIGN KEY(decided_by_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_approval_events (
                id TEXT PRIMARY KEY,
                approval_id TEXT NOT NULL,
                actor_account_id TEXT,
                action TEXT NOT NULL,
                state TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(approval_id) REFERENCES web_ops_approvals(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_triage (
                case_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_revision INTEGER NOT NULL,
                policy_version INTEGER NOT NULL,
                input_hash TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                case_state TEXT NOT NULL,
                risk TEXT NOT NULL,
                disposition TEXT NOT NULL,
                required_role TEXT NOT NULL,
                sla_minutes INTEGER NOT NULL,
                sla_status TEXT NOT NULL,
                last_run_id TEXT,
                first_classified_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(last_run_id) REFERENCES web_ops_runs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_support_triage_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                action TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(case_id, input_hash),
                FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
                FOREIGN KEY(run_id) REFERENCES web_ops_runs(id)
            )
            """
        )
        # Runtime Reliability Follow-up records only opaque, route-family
        # aggregate signals from explicitly allowed Web-native private APIs.
        # They deliberately omit raw request paths, query strings, account
        # input, exception text, credentials and provider/Bot/payment state.
        # A follow-up is a human-review work item, never evidence of an
        # automatic repair or a permission to take a high-risk action.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_runtime_signal_buckets (
                id TEXT PRIMARY KEY,
                bucket_fingerprint TEXT NOT NULL UNIQUE,
                route_family TEXT NOT NULL,
                signal_code TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0 CHECK(count >= 0),
                revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # A route-family total is separate from five-minute buckets so its
        # revision stays monotonic when a resolved follow-up sees a new error
        # in a later bucket.  The aggregate has no URL, request identity or
        # diagnostic payload and remains useful even after old buckets expire.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_runtime_signal_totals (
                route_family TEXT NOT NULL,
                signal_code TEXT NOT NULL,
                occurrence_count INTEGER NOT NULL DEFAULT 0 CHECK(occurrence_count >= 0),
                revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(route_family, signal_code)
            )
            """
        )
        # Backfill only aggregate counts for installations created before the
        # total table existed. ``MAX`` makes this additive migration monotonic
        # when schema checks run again after new buckets have been observed.
        conn.execute(
            """
            INSERT INTO web_ops_runtime_signal_totals
                (route_family, signal_code, occurrence_count, revision, first_seen_at, last_seen_at, updated_at)
            SELECT route_family, signal_code, SUM(count), MAX(1, SUM(count)), MIN(first_seen_at), MAX(last_seen_at), MAX(updated_at)
            FROM web_ops_runtime_signal_buckets
            GROUP BY route_family, signal_code
            ON CONFLICT(route_family, signal_code) DO UPDATE SET
                occurrence_count=MAX(web_ops_runtime_signal_totals.occurrence_count, excluded.occurrence_count),
                revision=MAX(web_ops_runtime_signal_totals.revision, excluded.revision),
                first_seen_at=MIN(web_ops_runtime_signal_totals.first_seen_at, excluded.first_seen_at),
                last_seen_at=MAX(web_ops_runtime_signal_totals.last_seen_at, excluded.last_seen_at),
                updated_at=MAX(web_ops_runtime_signal_totals.updated_at, excluded.updated_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_followups (
                id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL UNIQUE,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                account_id TEXT,
                required_role TEXT NOT NULL,
                severity TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'open'
                    CHECK(state IN ('open', 'acknowledged', 'resolved', 'superseded')),
                source_revision INTEGER NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
                created_by_run_id TEXT,
                opened_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                acknowledged_at TEXT,
                resolved_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(created_by_run_id) REFERENCES web_ops_runs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_ops_followup_events (
                id TEXT PRIMARY KEY,
                followup_id TEXT NOT NULL,
                actor_account_id TEXT,
                action TEXT NOT NULL,
                state TEXT NOT NULL
                    CHECK(state IN ('open', 'acknowledged', 'resolved', 'superseded')),
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(followup_id) REFERENCES web_ops_followups(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Privacy & Data Control stores only a staged customer request and a
        # compact lifecycle receipt.  There is intentionally no destructive
        # migration, account deletion cascade, export-file blob, Bot identity,
        # provider/payment/job field or free-text reason in this schema.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_data_control_requests (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                request_kind TEXT NOT NULL CHECK(request_kind IN ('erasure')),
                scope_key TEXT NOT NULL CHECK(scope_key IN ('web_authoring_only')),
                state TEXT NOT NULL CHECK(state IN ('awaiting_review', 'identity_verification_pending', 'cancelled', 'closed')),
                policy_version TEXT NOT NULL,
                blocker_summary_json TEXT NOT NULL DEFAULT '{}',
                requested_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                cancelled_at TEXT,
                closed_at TEXT,
                revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_data_control_request_events (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('requested', 'cancelled', 'reviewed', 'closed')),
                state TEXT NOT NULL CHECK(state IN ('awaiting_review', 'identity_verification_pending', 'cancelled', 'closed')),
                revision INTEGER NOT NULL CHECK(revision >= 1),
                created_at TEXT NOT NULL,
                FOREIGN KEY(request_id) REFERENCES web_data_control_requests(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Governance Documents are Web-native internal drafts/review records.
        # They do not mirror Bot ``internal_documents`` and deliberately have
        # no Telegram file reference, path, bridge, wallet, payment, provider,
        # job, customer, finance, HR or contract field.  No FK uses CASCADE:
        # a lifecycle/version/event record must never vanish as a side effect
        # of an unrelated account/document operation.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_governance_documents (
                id TEXT PRIMARY KEY,
                owner_account_id TEXT NOT NULL,
                department TEXT NOT NULL
                    CHECK(department IN ('marketing', 'tech_codex', 'legal_policy')),
                document_type TEXT NOT NULL
                    CHECK(document_type IN (
                        'campaign_plan', 'content_caption', 'posting_schedule', 'kpi_report', 'brand_asset',
                        'codex_task', 'deployment_note', 'bug_report', 'architecture_doc',
                        'terms', 'privacy', 'data_policy', 'ip_policy', 'customer_notice'
                    )),
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                retention_label TEXT NOT NULL DEFAULT 'manual_review'
                    CHECK(retention_label IN ('manual_review', '3_years', '5_years', 'permanent')),
                confidentiality_level TEXT NOT NULL DEFAULT 'internal'
                    CHECK(confidentiality_level IN ('internal', 'confidential', 'restricted')),
                state TEXT NOT NULL DEFAULT 'draft'
                    CHECK(state IN ('draft', 'in_review', 'approved', 'archived')),
                review_note TEXT NOT NULL DEFAULT '',
                reviewer_account_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                submitted_at TEXT,
                reviewed_at TEXT,
                archived_at TEXT,
                revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
                FOREIGN KEY(owner_account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(reviewer_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        governance_document_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_governance_documents)").fetchall()}
        if "retention_label" not in governance_document_columns:
            conn.execute("ALTER TABLE web_governance_documents ADD COLUMN retention_label TEXT NOT NULL DEFAULT 'manual_review'")
        if "confidentiality_level" not in governance_document_columns:
            conn.execute("ALTER TABLE web_governance_documents ADD COLUMN confidentiality_level TEXT NOT NULL DEFAULT 'internal'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_governance_document_versions (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK(revision >= 1),
                actor_account_id TEXT NOT NULL,
                action TEXT NOT NULL
                    CHECK(action IN ('created', 'updated', 'submitted', 'approved', 'rejected', 'archived', 'restored')),
                state TEXT NOT NULL
                    CHECK(state IN ('draft', 'in_review', 'approved', 'archived')),
                department TEXT NOT NULL,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                retention_label TEXT NOT NULL DEFAULT 'manual_review',
                confidentiality_level TEXT NOT NULL DEFAULT 'internal',
                review_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(document_id, revision),
                FOREIGN KEY(document_id) REFERENCES web_governance_documents(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        governance_version_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_governance_document_versions)").fetchall()}
        if "retention_label" not in governance_version_columns:
            conn.execute("ALTER TABLE web_governance_document_versions ADD COLUMN retention_label TEXT NOT NULL DEFAULT 'manual_review'")
        if "confidentiality_level" not in governance_version_columns:
            conn.execute("ALTER TABLE web_governance_document_versions ADD COLUMN confidentiality_level TEXT NOT NULL DEFAULT 'internal'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_governance_document_events (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                actor_account_id TEXT NOT NULL,
                action TEXT NOT NULL
                    CHECK(action IN ('created', 'updated', 'submitted', 'approved', 'rejected', 'archived', 'restored')),
                from_state TEXT,
                to_state TEXT NOT NULL
                    CHECK(to_state IN ('draft', 'in_review', 'approved', 'archived')),
                revision INTEGER NOT NULL CHECK(revision >= 1),
                created_at TEXT NOT NULL,
                UNIQUE(document_id, revision, action),
                FOREIGN KEY(document_id) REFERENCES web_governance_documents(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        # Admin Internal Document Archive owns immutable private file versions
        # in a separate root.  It intentionally does not mirror the Bot's
        # ``internal_documents`` table, Telegram file references, customer
        # Asset Vault, finance/customer/provider fields or bridge authority.
        # No FK uses CASCADE: archive history must remain auditable rather than
        # disappearing after an unrelated account or lifecycle operation.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_admin_archive_documents (
                id TEXT PRIMARY KEY,
                owner_account_id TEXT NOT NULL,
                department TEXT NOT NULL,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                description TEXT NOT NULL DEFAULT '',
                retention_label TEXT NOT NULL DEFAULT 'manual_review'
                    CHECK(retention_label IN ('manual_review', '3_years', '5_years', '10_years', 'permanent')),
                confidentiality_level TEXT NOT NULL DEFAULT 'internal'
                    CHECK(confidentiality_level IN ('internal', 'confidential', 'restricted')),
                state TEXT NOT NULL DEFAULT 'active'
                    CHECK(state IN ('active', 'archived', 'unavailable')),
                current_version_id TEXT,
                lifecycle_revision INTEGER NOT NULL DEFAULT 1 CHECK(lifecycle_revision >= 1),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(owner_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_admin_archive_versions (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                version_number INTEGER NOT NULL CHECK(version_number >= 1),
                uploader_account_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                display_name TEXT NOT NULL,
                extension TEXT NOT NULL,
                content_type TEXT NOT NULL,
                byte_size INTEGER NOT NULL CHECK(byte_size >= 1),
                sha256 TEXT NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                availability TEXT NOT NULL DEFAULT 'available'
                    CHECK(availability IN ('available', 'unavailable')),
                created_at TEXT NOT NULL,
                UNIQUE(document_id, version_number),
                FOREIGN KEY(document_id) REFERENCES web_admin_archive_documents(id),
                FOREIGN KEY(uploader_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_admin_archive_events (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                actor_account_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('created', 'version_added', 'metadata_updated', 'archived', 'restored', 'unavailable')),
                from_state TEXT,
                to_state TEXT NOT NULL CHECK(to_state IN ('active', 'archived', 'unavailable')),
                lifecycle_revision INTEGER NOT NULL CHECK(lifecycle_revision >= 1),
                version_number INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES web_admin_archive_documents(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_sessions_account ON web_sessions(account_id)"
        )
        # Account Security reads/revokes only active, unexpired sessions in
        # newest-first order. This additive index keeps that owner-scoped
        # projection bounded without changing the signed-session schema.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_sessions_account_active_recent ON web_sessions(account_id, revoked_at, expires_at, last_seen_at DESC, id)"
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
            "CREATE INDEX IF NOT EXISTS idx_web_workspace_starter_kit_installs_account_created ON web_workspace_starter_kit_installs(account_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_asset_files_account_state_updated ON web_asset_files(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_asset_files_owner_state_lifecycle ON web_asset_files(account_id, state, lifecycle_revision, id)"
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
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_asset_operations_account_updated ON web_subtitle_asset_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_asset_operations_source_account ON web_subtitle_asset_operations(source_asset_id, account_id, updated_at DESC, id DESC)"
        )
        # Startup reconciliation scans terminal/active operation states, and
        # per-account conversion quotas read only completed conversion rows.
        # Keep both reads indexed so growing validation history cannot turn a
        # restart or a small conversion into an unbounded table scan.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_asset_operations_state_kind_updated ON web_subtitle_asset_operations(state, kind, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_asset_operations_account_kind_state ON web_subtitle_asset_operations(account_id, kind, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_subtitle_asset_operation_events_operation_sequence ON web_subtitle_asset_operation_events(operation_id, sequence ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audio_asset_operations_account_updated ON web_audio_asset_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audio_asset_operations_source_account ON web_audio_asset_operations(source_asset_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audio_asset_operations_state_kind_updated ON web_audio_asset_operations(state, kind, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audio_asset_operations_account_kind_state ON web_audio_asset_operations(account_id, kind, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_audio_asset_operation_events_operation_sequence ON web_audio_asset_operation_events(operation_id, sequence ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_operations_account_updated ON web_video_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_operations_source_account ON web_video_operations(source_asset_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_operation_attempts_operation_attempt ON web_video_operation_attempts(operation_id, attempt_no DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_operation_events_operation_sequence ON web_video_operation_events(operation_id, sequence ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_frame_video_operations_account_updated ON web_frame_video_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_frame_video_operations_account_state_updated ON web_frame_video_operations(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_frame_video_operation_sources_operation_order ON web_frame_video_operation_sources(operation_id, source_index ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_frame_video_operation_sources_asset ON web_frame_video_operation_sources(source_asset_id, operation_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_frame_video_operation_attempts_operation_attempt ON web_frame_video_operation_attempts(operation_id, attempt_no DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_frame_video_operation_events_operation_sequence ON web_frame_video_operation_events(operation_id, sequence ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_transform_operations_account_updated ON web_video_transform_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_transform_operations_source_account ON web_video_transform_operations(source_asset_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_transform_operations_account_state_updated ON web_video_transform_operations(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_transform_operation_attempts_operation_attempt ON web_video_transform_operation_attempts(operation_id, attempt_no DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_video_transform_operation_events_operation_sequence ON web_video_transform_operation_events(operation_id, sequence ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_storyboard_grid_operations_account_updated ON web_storyboard_grid_operations(account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_storyboard_grid_operations_source_account ON web_storyboard_grid_operations(source_asset_id, account_id, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_storyboard_grid_cells_operation_scene ON web_storyboard_grid_cells(operation_id, scene_no ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_storyboard_grid_cells_operation_grid ON web_storyboard_grid_cells(operation_id, row_index ASC, column_index ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_storyboard_grid_events_operation_sequence ON web_storyboard_grid_events(operation_id, sequence ASC, id ASC)"
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
        # Calendar month reads always begin with the signed Web account and a
        # local ``scheduled_for`` range. This additive index keeps the
        # read-only agenda bounded without reusing or migrating any Bot
        # campaign/calendar schema.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_campaign_plans_account_schedule_window ON web_campaign_plans(account_id, scheduled_for, approval_status, platform, id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_campaign_plans_account_updated ON web_campaign_plans(account_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_campaign_schedule_intents_account_plan_state_trigger ON web_campaign_schedule_intents(account_id, plan_id, state, trigger_at ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_campaign_schedule_intents_dispatch_window ON web_campaign_schedule_intents(state, trigger_at ASC, id ASC)"
        )
        # One explicit active request may materialize only one in-app record
        # for the same owner, Campaign revision and normalized UTC trigger.
        # A cancellation or guarded record does not prevent a later explicit
        # owner choice from being recorded.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_web_campaign_schedule_intents_active_source_trigger ON web_campaign_schedule_intents(account_id, plan_id, source_revision, trigger_at) WHERE state='active'"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_items_account_state_updated ON web_workboard_items(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_items_account_priority_due ON web_workboard_items(account_id, priority, due_at, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_refs_account_type_id ON web_workboard_item_references(account_id, ref_type, ref_id, item_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_refs_item_ordinal ON web_workboard_item_references(item_id, account_id, ordinal ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_checklist_item_state_ordinal ON web_workboard_checklist_items(item_id, account_id, state, ordinal ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_item_versions_item_revision ON web_workboard_item_versions(item_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_checklist_versions_item_revision ON web_workboard_checklist_versions(item_id, checklist_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_events_account_created ON web_workboard_events(account_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_events_item_created ON web_workboard_events(item_id, account_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_schedule_intents_account_item_state_trigger ON web_workboard_schedule_intents(account_id, item_id, state, trigger_at ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_workboard_schedule_intents_dispatch_window ON web_workboard_schedule_intents(state, trigger_at ASC, id ASC)"
        )
        # A user can cancel and later make a new explicit choice, but an
        # active source revision/time combination can never fan out into two
        # independent in-app records.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_web_workboard_schedule_intents_active_source_trigger ON web_workboard_schedule_intents(account_id, item_id, source_revision, trigger_at) WHERE state='active'"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_nonces_expiry ON web_notification_nonces(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_runs_started ON web_notification_runs(started_at DESC, id DESC)"
        )
        # Bounded Inbox scheduler retention selects only old terminal receipts
        # and must quickly exclude active/current rows. Provenance lookup keeps
        # any run that created a durable customer Inbox item.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_runs_terminal_finished ON web_notification_runs(state, finished_at ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_steps_run_sequence ON web_notification_run_steps(run_id, sequence ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_items_account_state_created ON web_notification_items(account_id, state, created_at DESC, id DESC)"
        )
        # The signed Inbox scheduler reads only opaque overdue unread warnings
        # for bounded, account-round-robin urgency maintenance. This additive
        # index does not change row ownership, state or delivery behavior.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_items_unread_warning_occurrence ON web_notification_items(state, severity, account_id, occurrence_at ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_items_account_source ON web_notification_items(account_id, source_kind, source_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_items_source_occurrence ON web_notification_items(account_id, source_kind, source_id, source_revision, occurrence_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_items_created_by_run ON web_notification_items(created_by_run_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_dedupes_source_occurrence ON web_notification_dedupes(account_id, source_kind, source_id, source_revision, occurrence_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_notification_events_item_created ON web_notification_events(notification_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_nonces_expiry ON web_ops_nonces(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_runs_started ON web_ops_runs(started_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_runs_state_started ON web_ops_runs(state, started_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_steps_run_sequence ON web_ops_run_steps(run_id, sequence ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_incidents_state_seen ON web_ops_incidents(state, last_observed_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_incidents_account_case ON web_ops_incidents(account_id, support_case_id, last_observed_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_observations_incident_created ON web_ops_incident_observations(incident_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_playbook_runs_run ON web_ops_playbook_runs(run_id, started_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_approvals_state_expiry ON web_ops_approvals(state, expires_at ASC, proposed_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_approvals_case_state ON web_ops_approvals(support_case_id, state, proposed_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_approval_events_approval_created ON web_ops_approval_events(approval_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_triage_account_updated ON web_support_triage(account_id, updated_at DESC, case_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_triage_sla_status ON web_support_triage(sla_status, updated_at DESC, case_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_support_triage_events_case_created ON web_support_triage_events(case_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_runtime_signals_family_seen ON web_ops_runtime_signal_buckets(route_family, signal_code, last_seen_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_runtime_signals_seen ON web_ops_runtime_signal_buckets(last_seen_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_runtime_signal_totals_seen ON web_ops_runtime_signal_totals(last_seen_at DESC, route_family)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_followups_state_severity_updated ON web_ops_followups(state, severity, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_followups_source_updated ON web_ops_followups(source_kind, source_id, source_revision, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_followups_account_state_updated ON web_ops_followups(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_ops_followup_events_followup_created ON web_ops_followup_events(followup_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_data_control_requests_account_state_updated ON web_data_control_requests(account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_data_control_events_request_created ON web_data_control_request_events(request_id, account_id, created_at DESC, id DESC)"
        )
        # Governance list/review projections are all bounded and admin-scoped.
        # Keep their fixed filters/select order indexed without introducing a
        # cross-domain relationship or changing historical data.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_governance_documents_state_department_updated ON web_governance_documents(state, department, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_governance_documents_owner_state_updated ON web_governance_documents(owner_account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_governance_documents_type_updated ON web_governance_documents(document_type, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_governance_versions_document_revision ON web_governance_document_versions(document_id, revision DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_governance_events_document_created ON web_governance_document_events(document_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_admin_archive_documents_owner_state_updated ON web_admin_archive_documents(owner_account_id, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_admin_archive_documents_department_state_updated ON web_admin_archive_documents(department, state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_admin_archive_documents_type_updated ON web_admin_archive_documents(document_type, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_admin_archive_versions_document_version ON web_admin_archive_versions(document_id, version_number DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_admin_archive_events_document_created ON web_admin_archive_events(document_id, created_at DESC, id DESC)"
        )


def as_row(row: sqlite3.Row | tuple | None, columns: tuple[str, ...]) -> dict | None:
    if row is None:
        return None
    return dict(zip(columns, row))
