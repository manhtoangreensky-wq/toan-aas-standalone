"""TOAN AAS standalone Web App — COPYFAST compatibility entrypoint.

The historical prototype modules remain in the repository for reference but
are intentionally not mounted here: they used a separate SQLite wallet/PayOS
implementation and browser-supplied identities.  This entrypoint exposes only
the signed-session web layer and its server-to-server bot bridge.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
import os
import time
import uuid
from urllib.parse import quote, urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import copyfast_api
import copyfast_admin_audit
import copyfast_admin_document_archive
import copyfast_admin_erp_navigation
import copyfast_analytics_workspace
import copyfast_autopilot
import copyfast_assets
import copyfast_auth
import copyfast_auth_throttle
import copyfast_channel_strategy
import copyfast_content_handoff
import copyfast_content_studio
import copyfast_chat_workspace
from copyfast_bridge import ensure_core_bridge_readiness
import copyfast_data_controls
import copyfast_document_operations
import copyfast_document_workspace
import copyfast_free_prompt_gallery
import copyfast_governance
import copyfast_growth_review
import copyfast_image_operations
import copyfast_image_studio
import copyfast_storyboard_grid
import copyfast_memory
import copyfast_media_factory
import copyfast_mfa
import copyfast_music_media
import copyfast_notification_center
import copyfast_operations_desk
import copyfast_partner_crm
import copyfast_prompt_library
import copyfast_prompt_studio
import copyfast_project_packages
import copyfast_projects
import copyfast_reliability
import copyfast_support
import copyfast_subtitle_workspace
import copyfast_trend_research
import copyfast_video_studio
import copyfast_voice_studio
import copyfast_workboard
from copyfast_auth import (
    current_session,
    ensure_auth_configuration,
    ensure_email_verification_configuration,
    ensure_password_recovery_configuration,
    ensure_oauth_configuration,
    envelope,
    require_canonical_admin,
)
from copyfast_mfa import ensure_totp_mfa_configuration
from copyfast_db import (
    ensure_admin_document_archive_persistence,
    ensure_asset_vault_persistence,
    ensure_copyfast_persistence,
    ensure_copyfast_schema,
    ensure_document_operations_persistence,
    ensure_image_operations_persistence,
    ensure_project_package_persistence,
    is_production_like_environment,
    utc_now,
)
from copyfast_pages import ROOT, render_portal


LOGGER = logging.getLogger(__name__)
STARTUP_RECONCILIATION_TASK_NAME = "copyfast-startup-reconciliation"
STARTUP_RECONCILIATION_STEPS = (
    ("admin_document_archive", copyfast_admin_document_archive.reconcile_admin_document_archive_storage),
    ("asset_vault", copyfast_assets.reconcile_asset_vault_storage),
    ("project_packages", copyfast_project_packages.reconcile_project_package_storage),
    ("document_operations", copyfast_document_operations.reconcile_document_operation_storage),
    ("image_operations", copyfast_image_operations.reconcile_image_operation_storage),
    ("storyboard_grid", copyfast_storyboard_grid.reconcile_storyboard_grid_storage),
)


def _origins() -> list[str]:
    # Credentialed Web APIs expose signed-session/CSRF metadata.  Keep the
    # default to the dedicated application origin; a marketing/root site may
    # opt in explicitly only after it is audited as the same trust boundary.
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "https://app.toanaas.vn")
    origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("CORS_ALLOW_ORIGINS phải là danh sách origin tường minh khi dùng cookie")
    production = is_production_like_environment()
    for origin in origins:
        parsed = urlparse(origin)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise RuntimeError("CORS_ALLOW_ORIGINS chứa origin không hợp lệ")
        if parsed.scheme != "https" and not (local_http and not production):
            raise RuntimeError("CORS_ALLOW_ORIGINS chỉ chấp nhận HTTPS, trừ localhost khi phát triển")
    return origins


async def _run_startup_reconciliation(application: FastAPI) -> None:
    """Reconcile private filesystem metadata without delaying readiness.

    All reconciliation functions may walk a private volume. They are
    useful integrity maintenance, not a prerequisite to authenticate a user
    or answer Railway's health check, so run them serially on a worker thread
    only after the ASGI lifespan has yielded.  Each failure is deliberately
    isolated: a later storage boundary still receives reconciliation and a
    failed scan cannot make a healthy service appear unavailable.
    """
    status = application.state.copyfast_startup_reconciliation
    status["status"] = "running"
    status["started_at_epoch"] = time.time()
    interrupted_before = str(status.get("interrupted_before") or "")
    for name, reconcile in STARTUP_RECONCILIATION_STEPS:
        status["current_step"] = name
        try:
            if name in {"image_operations", "storyboard_grid"} and interrupted_before:
                # Image transforms and storyboard splitting run synchronously
                # in a request and have no worker to resume them. The deferred
                # scan must only recover work that predates readiness;
                # otherwise a request accepted while earlier private roots
                # are being scanned can be mistaken for restart debris and
                # fail mid-render.
                await asyncio.to_thread(reconcile, interrupted_before=interrupted_before)
            else:
                await asyncio.to_thread(reconcile)
        except asyncio.CancelledError:
            status["status"] = "cancelled"
            status["current_step"] = None
            status["finished_at_epoch"] = time.time()
            LOGGER.info("Cancelled deferred startup reconciliation")
            raise
        except Exception:
            # Do not retain exception text in application state: it could
            # include a private storage path.  Operators still receive the
            # sanitized step name plus the traceback in server-only logs.
            status["failed_steps"].append(name)
            LOGGER.exception("Deferred startup reconciliation failed for step=%s", name)
        else:
            status["completed_steps"].append(name)
    status["current_step"] = None
    status["finished_at_epoch"] = time.time()
    status["status"] = "completed" if not status["failed_steps"] else "completed_with_errors"
    LOGGER.info(
        "Deferred startup reconciliation finished status=%s completed=%d failed=%d",
        status["status"],
        len(status["completed_steps"]),
        len(status["failed_steps"]),
    )


def _start_startup_reconciliation(application: FastAPI) -> asyncio.Task[None]:
    """Schedule volume scans after readiness without exposing a public API."""
    application.state.copyfast_startup_reconciliation = {
        "status": "scheduled",
        # Capture the fence before the app begins serving. Deferred storage
        # scans may begin after the first signed request, so they must not
        # classify that fresh request as an interrupted pre-startup operation.
        "interrupted_before": utc_now(),
        "current_step": None,
        "completed_steps": [],
        "failed_steps": [],
        "started_at_epoch": None,
        "finished_at_epoch": None,
    }
    task = asyncio.create_task(
        _run_startup_reconciliation(application), name=STARTUP_RECONCILIATION_TASK_NAME
    )
    application.state.copyfast_startup_reconciliation_task = task
    return task


async def _stop_startup_reconciliation(application: FastAPI) -> None:
    """Cancel a best-effort storage scan cleanly during ASGI shutdown."""
    task = getattr(application.state, "copyfast_startup_reconciliation_task", None)
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        # ``asyncio.to_thread`` cannot forcibly stop an already-running
        # synchronous syscall.  Cancellation detaches the task from ASGI
        # shutdown while every reconcile function remains independently safe.
        pass


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Optional release gate: normal Web-only deployments intentionally remain
    # usable without the canonical Bot bridge, but a release that explicitly
    # requires it must not advertise readiness with missing/unsafe credentials.
    ensure_core_bridge_readiness()
    ensure_auth_configuration()
    ensure_oauth_configuration()
    ensure_email_verification_configuration()
    ensure_password_recovery_configuration()
    ensure_totp_mfa_configuration()
    ensure_copyfast_persistence()
    ensure_copyfast_schema()
    # The Admin Internal Document Archive owns a separate private root and is
    # disabled by default. Its preflight stays beside the other storage gates
    # and cannot make an ordinary deployment require a volume while disabled.
    ensure_admin_document_archive_persistence()
    ensure_asset_vault_persistence()
    ensure_project_package_persistence()
    ensure_document_operations_persistence()
    ensure_image_operations_persistence()
    copyfast_document_operations.ensure_document_operations_runtime()
    copyfast_image_operations.ensure_image_operations_runtime()
    copyfast_storyboard_grid.ensure_storyboard_grid_runtime()
    _start_startup_reconciliation(application)
    try:
        yield
    finally:
        await _stop_startup_reconciliation(application)


app = FastAPI(title="TOAN AAS Web App", version="P0.WEBAPP.COPYFAST1", lifespan=lifespan)


_auth_rate_windows: dict[str, list[float]] = {}
RATE_WINDOW_SECONDS = 60.0
RATE_WINDOW_PRUNE_THRESHOLD = 512
RATE_WINDOW_MAX_KEYS = 4096
# Prompt recipes remain intentionally small, but imports can contain a
# bounded batch of Unicode-rich templates.  These limits are enforced on the
# raw ASGI stream *before* FastAPI/Pydantic buffers or parses JSON.
PROMPT_LIBRARY_BODY_MAX_BYTES = 512 * 1024
PROMPT_LIBRARY_IMPORT_BODY_MAX_BYTES = 6 * 1024 * 1024
# Prompt Blueprint Composer accepts only a compact, text-only editorial brief.
# Bound its raw stream before JSON/Pydantic parsing; this never enables a file,
# provider, Bot, job, wallet/payment or publishing payload.
PROMPT_STUDIO_BODY_MAX_BYTES = 16 * 1024
# Audio Workspace only accepts bounded metadata JSON (the largest server
# field is a 6,000-character brief).  Cap its raw stream separately before
# FastAPI buffers/parses a potentially chunked body.
MEDIA_WORKSPACE_BODY_MAX_BYTES = 64 * 1024
# Content Studio accepts authored metadata and text only.  Enforce a bounded
# raw JSON stream before FastAPI/Pydantic can parse a potentially chunked
# request; media/file uploads remain outside this route family.
CONTENT_STUDIO_BODY_MAX_BYTES = 128 * 1024
# Content Handoff accepts a short review purpose, opaque UUID references and
# an internal staff note only. Keep a narrow pre-parse cap; it never enables
# uploads, social publishing, external delivery or provider input.
CONTENT_HANDOFF_BODY_MAX_BYTES = 16 * 1024
# Channel Strategy stores only small, signed-account profile metadata and a
# revision receipt. Cap it before JSON parsing; this never enables channel
# connection, URL fetch, analytics, provider, Bot, job or publishing input.
CHANNEL_STRATEGY_BODY_MAX_BYTES = 32 * 1024
# Voice Studio accepts only bounded scripts/metadata; it has no audio-upload
# or provider payload contract.
VOICE_STUDIO_BODY_MAX_BYTES = 128 * 1024
# Video Production Studio accepts authored planning metadata only; it has no
# media upload or execution payload contract.
VIDEO_STUDIO_BODY_MAX_BYTES = 128 * 1024
# Subtitle Studio accepts bounded JSON/text only.  It has no multipart/raw
# media contract, so a route-family cap runs before JSON parsing.
SUBTITLE_STUDIO_BODY_MAX_BYTES = 128 * 1024
# Image Creative Studio stores bounded text/UUID references only.  No
# multipart/image-body route belongs to this API family.
IMAGE_STUDIO_BODY_MAX_BYTES = 128 * 1024
# Document & PDF Workspace accepts authored metadata and opaque UUID
# references only.  Cap the raw body before Pydantic/SQLite handling; this
# does not cover or enable the separate Document Operations executor.
DOCUMENT_WORKSPACE_BODY_MAX_BYTES = 128 * 1024
# Document Operations accept only compact JSON with Asset Vault UUIDs and
# bounded options.  A separate raw-stream cap protects private OCR/PDF
# executors before FastAPI parses a malicious chunked body.
DOCUMENT_OPERATION_BODY_MAX_BYTES = 16 * 1024
# Trend Research is a compact, text-only request with a 180-character topic.
# Retain a small raw-stream cap before Pydantic parses a chunked payload.
TREND_RESEARCH_BODY_MAX_BYTES = 16 * 1024
# Growth Review is a compact, numeric-only request. Apply a separate raw
# stream ceiling before Pydantic sees its JSON; it never permits platform
# data, Bot/bridge, AI/provider, revenue ledger, job or payment input.
GROWTH_REVIEW_BODY_MAX_BYTES = 16 * 1024
# Media Factory Blueprint is an equally small topic/language planning receipt.
# The early cap applies before Pydantic parsing and does not enable a media
# upload, source fetch, provider request, Bot call or execution engine.
MEDIA_FACTORY_BODY_MAX_BYTES = 16 * 1024
# Conversation Workspace accepts plain-text authoring data only.  Keep its
# raw JSON cap deliberately small before Pydantic or SQLite sees a request;
# it does not permit model streaming, file upload or provider input.
CHAT_WORKSPACE_BODY_MAX_BYTES = 64 * 1024
# Analytics Workspace accepts only bounded manual metric/report JSON.  This
# cap runs before Pydantic/SQLite and deliberately does not permit CSV/file
# import, platform connectors, Bot/provider traffic, payments or jobs.
ANALYTICS_WORKSPACE_BODY_MAX_BYTES = 128 * 1024
# Workboard accepts only bounded private task/checklist metadata. It has no
# file, URL-fetch, provider, Bot, wallet, payment, job or publish payload.
WORKBOARD_BODY_MAX_BYTES = 128 * 1024
# Partner & Lead CRM stores compact signed-account metadata and private notes;
# it has no attachment, payout, referral, provider or contact-delivery body.
PARTNER_CRM_BODY_MAX_BYTES = 16 * 1024
# The scheduler sends a fixed, signed JSON receipt only.  Cap it well below
# normal authoring routes before HMAC/JSON parsing so malformed chunked input
# cannot become a memory-amplification path.
AUTOPILOT_TICK_BODY_MAX_BYTES = 8 * 1024
# An Operations approval contains only a short decision receipt.  Bound it
# before FastAPI/Pydantic parse JSON so an authenticated manager endpoint does
# not become an unbounded request-body sink.
AUTOPILOT_APPROVAL_BODY_MAX_BYTES = 8 * 1024
# Reliability follow-up mutations contain only a revision, confirmation and
# idempotency receipt. Apply the same early raw-body boundary as Operations
# approvals before Pydantic/SQLite handling.
RELIABILITY_FOLLOWUP_BODY_MAX_BYTES = 8 * 1024
# Inbox scheduler and signed-account state mutations carry only compact
# metadata/idempotency receipts. Bound them before HMAC/Pydantic parsing.
NOTIFICATION_TICK_BODY_MAX_BYTES = 8 * 1024
INBOX_MUTATION_BODY_MAX_BYTES = 8 * 1024
# Data Control mutations contain only an explicit policy acknowledgement,
# revision and idempotency receipt. Keep the same compact raw-body boundary
# before JSON/SQLite work; exports remain a response-only direct attachment.
DATA_CONTROLS_BODY_MAX_BYTES = 8 * 1024
# Governance mutations carry an internal text document, bounded independently
# before Pydantic/SQLite sees it. This is not a file import, Bot document, or
# generic Admin write transport.
GOVERNANCE_BODY_MAX_BYTES = 96 * 1024
# A private archive payload may contain one validated 25 MiB file plus bounded
# multipart metadata.  Count the raw ASGI stream before multipart parsing so
# a chunked upload cannot bypass either the file contract or process memory.
ADMIN_DOCUMENT_ARCHIVE_UPLOAD_BODY_MAX_BYTES = 26 * 1024 * 1024
# Login and registration accept only a compact email/password/name JSON body.
# Bound it before FastAPI/Pydantic begins parsing so the durable route-level
# throttle below never has to inspect an arbitrary-size credential payload.
AUTH_CREDENTIAL_BODY_MAX_BYTES = 8 * 1024


class PromptLibraryBodyLimitMiddleware:
    """Reject oversized Prompt Library JSON before it reaches request parsing.

    A ``Content-Length`` check alone is not a complete boundary because a
    chunked client can omit or lie about that header.  Wrapping ``receive``
    therefore counts every ASGI body chunk too.  The middleware is kept
    narrow: uploads and other feature routes retain their own contracts.
    """

    def __init__(
        self,
        app,
        *,
        max_bytes: int,
        import_max_bytes: int,
        prompt_studio_max_bytes: int = PROMPT_STUDIO_BODY_MAX_BYTES,
        media_max_bytes: int = MEDIA_WORKSPACE_BODY_MAX_BYTES,
        content_studio_max_bytes: int = CONTENT_STUDIO_BODY_MAX_BYTES,
        content_handoff_max_bytes: int = CONTENT_HANDOFF_BODY_MAX_BYTES,
        channel_strategy_max_bytes: int = CHANNEL_STRATEGY_BODY_MAX_BYTES,
        voice_studio_max_bytes: int = VOICE_STUDIO_BODY_MAX_BYTES,
        video_studio_max_bytes: int = VIDEO_STUDIO_BODY_MAX_BYTES,
        subtitle_studio_max_bytes: int = SUBTITLE_STUDIO_BODY_MAX_BYTES,
        image_studio_max_bytes: int = IMAGE_STUDIO_BODY_MAX_BYTES,
        document_workspace_max_bytes: int = DOCUMENT_WORKSPACE_BODY_MAX_BYTES,
        document_operation_max_bytes: int = DOCUMENT_OPERATION_BODY_MAX_BYTES,
        trend_research_max_bytes: int = TREND_RESEARCH_BODY_MAX_BYTES,
        growth_review_max_bytes: int = GROWTH_REVIEW_BODY_MAX_BYTES,
        media_factory_max_bytes: int = MEDIA_FACTORY_BODY_MAX_BYTES,
        chat_workspace_max_bytes: int = CHAT_WORKSPACE_BODY_MAX_BYTES,
        analytics_workspace_max_bytes: int = ANALYTICS_WORKSPACE_BODY_MAX_BYTES,
        workboard_max_bytes: int = WORKBOARD_BODY_MAX_BYTES,
        partner_crm_max_bytes: int = PARTNER_CRM_BODY_MAX_BYTES,
        autopilot_tick_max_bytes: int = AUTOPILOT_TICK_BODY_MAX_BYTES,
        autopilot_approval_max_bytes: int = AUTOPILOT_APPROVAL_BODY_MAX_BYTES,
        reliability_followup_max_bytes: int = RELIABILITY_FOLLOWUP_BODY_MAX_BYTES,
        notification_tick_max_bytes: int = NOTIFICATION_TICK_BODY_MAX_BYTES,
        inbox_mutation_max_bytes: int = INBOX_MUTATION_BODY_MAX_BYTES,
        data_controls_max_bytes: int = DATA_CONTROLS_BODY_MAX_BYTES,
        governance_max_bytes: int = GOVERNANCE_BODY_MAX_BYTES,
        admin_document_archive_upload_max_bytes: int = ADMIN_DOCUMENT_ARCHIVE_UPLOAD_BODY_MAX_BYTES,
        auth_credential_max_bytes: int = AUTH_CREDENTIAL_BODY_MAX_BYTES,
    ):
        self.app = app
        self.max_bytes = int(max_bytes)
        self.import_max_bytes = int(import_max_bytes)
        self.prompt_studio_max_bytes = int(prompt_studio_max_bytes)
        self.media_max_bytes = int(media_max_bytes)
        self.content_studio_max_bytes = int(content_studio_max_bytes)
        self.content_handoff_max_bytes = int(content_handoff_max_bytes)
        self.channel_strategy_max_bytes = int(channel_strategy_max_bytes)
        self.voice_studio_max_bytes = int(voice_studio_max_bytes)
        self.video_studio_max_bytes = int(video_studio_max_bytes)
        self.subtitle_studio_max_bytes = int(subtitle_studio_max_bytes)
        self.image_studio_max_bytes = int(image_studio_max_bytes)
        self.document_workspace_max_bytes = int(document_workspace_max_bytes)
        self.document_operation_max_bytes = int(document_operation_max_bytes)
        self.trend_research_max_bytes = int(trend_research_max_bytes)
        self.growth_review_max_bytes = int(growth_review_max_bytes)
        self.media_factory_max_bytes = int(media_factory_max_bytes)
        self.chat_workspace_max_bytes = int(chat_workspace_max_bytes)
        self.analytics_workspace_max_bytes = int(analytics_workspace_max_bytes)
        self.workboard_max_bytes = int(workboard_max_bytes)
        self.partner_crm_max_bytes = int(partner_crm_max_bytes)
        self.autopilot_tick_max_bytes = int(autopilot_tick_max_bytes)
        self.autopilot_approval_max_bytes = int(autopilot_approval_max_bytes)
        self.reliability_followup_max_bytes = int(reliability_followup_max_bytes)
        self.notification_tick_max_bytes = int(notification_tick_max_bytes)
        self.inbox_mutation_max_bytes = int(inbox_mutation_max_bytes)
        self.data_controls_max_bytes = int(data_controls_max_bytes)
        self.governance_max_bytes = int(governance_max_bytes)
        self.admin_document_archive_upload_max_bytes = int(admin_document_archive_upload_max_bytes)
        self.auth_credential_max_bytes = int(auth_credential_max_bytes)

    @staticmethod
    def _is_admin_document_archive_upload_path(path: str) -> bool:
        """Match only the two multipart upload routes, never a broad admin path."""

        return path == "/api/v1/admin/internal-documents/documents/upload" or (
            path.startswith("/api/v1/admin/internal-documents/documents/")
            and path.endswith("/versions/upload")
        )

    @staticmethod
    def _is_bounded_write(scope) -> bool:
        path = str(scope.get("path") or "")
        return (
            scope.get("type") == "http"
            and str(scope.get("method") or "").upper() in {"POST", "PATCH"}
            and (
                path.startswith("/api/v1/prompt-library/")
                or path.startswith("/api/v1/prompt-studio/")
                or path.startswith("/api/v1/media-workspace/")
                or path.startswith("/api/v1/content-studio/")
                or path.startswith("/api/v1/content-handoffs/")
                or path.startswith("/api/v1/channel-strategy/")
                or path.startswith("/api/v1/voice-studio/")
                or path.startswith("/api/v1/video-studio/")
                or path.startswith("/api/v1/subtitle-studio/")
                or path.startswith("/api/v1/image-studio/")
                or path.startswith("/api/v1/document-workspace/")
                or path.startswith("/api/v1/document-operations/")
                or path.startswith("/api/v1/trend-research/")
                or path.startswith("/api/v1/growth-review/")
                or path.startswith("/api/v1/media-factory/")
                or path.startswith("/api/v1/chat-workspace/")
                or path.startswith("/api/v1/analytics-workspace/")
                or path.startswith("/api/v1/workboard/")
                or path.startswith("/api/v1/partner-crm/")
                or path == "/internal/v1/operations/tick"
                or path.startswith("/api/v1/operations/admin/approvals/")
                or path.startswith("/api/v1/operations/admin/followups/")
                or path == "/internal/v1/notifications/tick"
                or path.startswith("/api/v1/inbox/items/")
                or path.startswith("/api/v1/account/data-controls/")
                or path.startswith("/api/v1/admin/governance/")
                or PromptLibraryBodyLimitMiddleware._is_admin_document_archive_upload_path(path)
                or path in {
                    "/api/v1/auth/login",
                    "/api/v1/auth/register",
                    "/api/v1/auth/security/password",
                    "/api/v1/auth/security/email-verification/start",
                    "/api/v1/auth/password-recovery/start",
                    "/api/v1/auth/password-recovery/confirm",
                    "/api/v1/auth/login/mfa",
                    "/api/v1/auth/mfa/enrollment/start",
                    "/api/v1/auth/mfa/enrollment/confirm",
                    "/api/v1/auth/mfa/disable",
                }
            )
        )

    def _limit_for(self, scope) -> int:
        path = str(scope.get("path") or "")
        if self._is_admin_document_archive_upload_path(path):
            return self.admin_document_archive_upload_max_bytes
        if path.startswith("/api/v1/prompt-studio/"):
            return self.prompt_studio_max_bytes
        if path.startswith("/api/v1/content-studio/"):
            return self.content_studio_max_bytes
        if path.startswith("/api/v1/content-handoffs/"):
            return self.content_handoff_max_bytes
        if path.startswith("/api/v1/channel-strategy/"):
            return self.channel_strategy_max_bytes
        if path.startswith("/api/v1/voice-studio/"):
            return self.voice_studio_max_bytes
        if path.startswith("/api/v1/video-studio/"):
            return self.video_studio_max_bytes
        if path.startswith("/api/v1/subtitle-studio/"):
            return self.subtitle_studio_max_bytes
        if path.startswith("/api/v1/image-studio/"):
            return self.image_studio_max_bytes
        if path.startswith("/api/v1/document-operations/"):
            return self.document_operation_max_bytes
        if path.startswith("/api/v1/trend-research/"):
            return self.trend_research_max_bytes
        if path.startswith("/api/v1/growth-review/"):
            return self.growth_review_max_bytes
        if path.startswith("/api/v1/media-factory/"):
            return self.media_factory_max_bytes
        if path.startswith("/api/v1/document-workspace/"):
            return self.document_workspace_max_bytes
        if path.startswith("/api/v1/chat-workspace/"):
            return self.chat_workspace_max_bytes
        if path.startswith("/api/v1/analytics-workspace/"):
            return self.analytics_workspace_max_bytes
        if path.startswith("/api/v1/workboard/"):
            return self.workboard_max_bytes
        if path.startswith("/api/v1/partner-crm/"):
            return self.partner_crm_max_bytes
        if path == "/internal/v1/operations/tick":
            return self.autopilot_tick_max_bytes
        if path.startswith("/api/v1/operations/admin/approvals/"):
            return self.autopilot_approval_max_bytes
        if path.startswith("/api/v1/operations/admin/followups/"):
            return self.reliability_followup_max_bytes
        if path == "/internal/v1/notifications/tick":
            return self.notification_tick_max_bytes
        if path.startswith("/api/v1/inbox/items/"):
            return self.inbox_mutation_max_bytes
        if path.startswith("/api/v1/account/data-controls/"):
            return self.data_controls_max_bytes
        if path.startswith("/api/v1/admin/governance/"):
            return self.governance_max_bytes
        if path in {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/security/password",
            "/api/v1/auth/security/email-verification/start",
            "/api/v1/auth/password-recovery/start",
            "/api/v1/auth/password-recovery/confirm",
            "/api/v1/auth/login/mfa",
            "/api/v1/auth/mfa/enrollment/start",
            "/api/v1/auth/mfa/enrollment/confirm",
            "/api/v1/auth/mfa/disable",
        }:
            return self.auth_credential_max_bytes
        if path.startswith("/api/v1/media-workspace/"):
            return self.media_max_bytes
        return self.import_max_bytes if path == "/api/v1/prompt-library/import" else self.max_bytes

    async def _reject(self, scope, receive, send) -> None:
        # This class may be the outermost application middleware, so write the
        # private API security headers directly rather than relying on a later
        # function middleware to decorate a response that it never receives.
        path = str(scope.get("path") or "")
        is_prompt_studio = path.startswith("/api/v1/prompt-studio/")
        is_content_studio = path.startswith("/api/v1/content-studio/")
        is_content_handoff = path.startswith("/api/v1/content-handoffs/")
        is_channel_strategy = path.startswith("/api/v1/channel-strategy/")
        is_voice_studio = path.startswith("/api/v1/voice-studio/")
        is_video_studio = path.startswith("/api/v1/video-studio/")
        is_subtitle_studio = path.startswith("/api/v1/subtitle-studio/")
        is_image_studio = path.startswith("/api/v1/image-studio/")
        is_document_operation = path.startswith("/api/v1/document-operations/")
        is_trend_research = path.startswith("/api/v1/trend-research/")
        is_growth_review = path.startswith("/api/v1/growth-review/")
        is_media_factory = path.startswith("/api/v1/media-factory/")
        is_document_workspace = path.startswith("/api/v1/document-workspace/")
        is_chat_workspace = path.startswith("/api/v1/chat-workspace/")
        is_analytics_workspace = path.startswith("/api/v1/analytics-workspace/")
        is_workboard = path.startswith("/api/v1/workboard/")
        is_partner_crm = path.startswith("/api/v1/partner-crm/")
        is_autopilot_tick = path == "/internal/v1/operations/tick"
        is_autopilot_approval = path.startswith("/api/v1/operations/admin/approvals/")
        is_reliability_followup = path.startswith("/api/v1/operations/admin/followups/")
        is_notification_tick = path == "/internal/v1/notifications/tick"
        is_inbox_mutation = path.startswith("/api/v1/inbox/items/")
        is_data_controls = path.startswith("/api/v1/account/data-controls/")
        is_governance = path.startswith("/api/v1/admin/governance/")
        is_admin_document_archive_upload = self._is_admin_document_archive_upload_path(path)
        is_auth_credential = path in {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/security/password",
            "/api/v1/auth/security/email-verification/start",
            "/api/v1/auth/password-recovery/start",
            "/api/v1/auth/password-recovery/confirm",
            "/api/v1/auth/login/mfa",
            "/api/v1/auth/mfa/enrollment/start",
            "/api/v1/auth/mfa/enrollment/confirm",
            "/api/v1/auth/mfa/disable",
        }
        is_mailbox_confirmation = path in {
            "/api/v1/auth/email-verification/confirm",
            "/api/v1/auth/password-recovery/confirm",
        }
        is_media = path.startswith("/api/v1/media-workspace/")
        # This route family is authoring-only.  Include the explicit boundary
        # even on an early raw-body rejection, before its router can run.
        boundary = (
            copyfast_prompt_studio._boundary()
            if is_prompt_studio
            else copyfast_content_handoff._boundary(record_persisted=False)
            if is_content_handoff
            else copyfast_partner_crm._boundary(lead_persisted=False)
            if is_partner_crm
            else copyfast_channel_strategy._boundary(profile_persisted=False)
            if is_channel_strategy
            else copyfast_chat_workspace._boundary()
            if is_chat_workspace
            else copyfast_analytics_workspace._boundary()
            if is_analytics_workspace
            else copyfast_workboard._boundary()
            if is_workboard
            else copyfast_autopilot._boundary()
            if is_autopilot_tick or is_autopilot_approval
            else copyfast_reliability._boundary()
            if is_reliability_followup
            else copyfast_notification_center._boundary()
            if is_notification_tick or is_inbox_mutation
            else copyfast_growth_review._boundary()
            if is_growth_review
            else copyfast_data_controls._boundary()
            if is_data_controls
            else copyfast_admin_document_archive._boundary()
            if is_admin_document_archive_upload
            else copyfast_governance._boundary()
            if is_governance
            else copyfast_media_factory._boundary()
            if is_media_factory
            else copyfast_document_workspace._boundary() if is_document_workspace else None
        )
        response = JSONResponse(
            envelope(
                False,
                (
                    "Thông tin đăng nhập vượt giới hạn kích thước an toàn."
                    if is_auth_credential
                    else "Dữ liệu Prompt Studio vượt giới hạn kích thước an toàn."
                    if is_prompt_studio
                    else "Dữ liệu Content Handoff vượt giới hạn kích thước an toàn."
                    if is_content_handoff
                    else "Dữ liệu Partner & Lead CRM vượt giới hạn kích thước an toàn."
                    if is_partner_crm
                    else "Dữ liệu Creative Content Studio vượt giới hạn kích thước an toàn."
                    if is_content_studio
                    else "Dữ liệu Channel Strategy vượt giới hạn kích thước an toàn."
                    if is_channel_strategy
                    else "Dữ liệu Voice Studio vượt giới hạn kích thước an toàn."
                    if is_voice_studio
                    else "Dữ liệu Video Production Studio vượt giới hạn kích thước an toàn."
                    if is_video_studio
                    else "Dữ liệu Subtitle Studio vượt giới hạn kích thước an toàn."
                    if is_subtitle_studio
                    else "Dữ liệu Image Creative Studio vượt giới hạn kích thước an toàn."
                    if is_image_studio
                    else "Dữ liệu Document Operations vượt giới hạn kích thước an toàn."
                    if is_document_operation
                    else "Dữ liệu Trend Research vượt giới hạn kích thước an toàn."
                    if is_trend_research
                    else "Dữ liệu Growth Review vượt giới hạn kích thước an toàn."
                    if is_growth_review
                    else "Dữ liệu Media Factory Blueprint vượt giới hạn kích thước an toàn."
                    if is_media_factory
                    else "Dữ liệu Document & PDF Workspace vượt giới hạn kích thước an toàn."
                    if is_document_workspace
                    else "Dữ liệu AI Chat Workspace vượt giới hạn kích thước an toàn."
                    if is_chat_workspace
                    else "Dữ liệu Analytics Workspace vượt giới hạn kích thước an toàn."
                    if is_analytics_workspace
                    else "Dữ liệu Workboard & Review Queue vượt giới hạn kích thước an toàn."
                    if is_workboard
                    else "Dữ liệu Operations Autopilot nội bộ vượt giới hạn kích thước an toàn."
                    if is_autopilot_tick
                    else "Quyết định Operations Autopilot vượt giới hạn kích thước an toàn."
                    if is_autopilot_approval
                    else "Quyết định Reliability Follow-up vượt giới hạn kích thước an toàn."
                    if is_reliability_followup
                    else "Dữ liệu Inbox Automation nội bộ vượt giới hạn kích thước an toàn."
                    if is_notification_tick
                    else "Quyết định Inbox riêng tư vượt giới hạn kích thước an toàn."
                    if is_inbox_mutation
                    else "Yêu cầu Data Control vượt giới hạn kích thước an toàn."
                    if is_data_controls
                    else "Tệp kho hồ sơ nội bộ vượt giới hạn kích thước an toàn."
                    if is_admin_document_archive_upload
                    else "Dữ liệu Governance Documents vượt giới hạn kích thước an toàn."
                    if is_governance
                    else "Dữ liệu Audio Library & Briefing vượt giới hạn kích thước an toàn."
                    if is_media
                    else "Dữ liệu Prompt Library vượt giới hạn kích thước an toàn."
                ),
                data=boundary,
                status_name="guarded",
                error_code=(
                    "WEB_AUTH_CREDENTIAL_BODY_TOO_LARGE"
                    if is_auth_credential
                    else "WEB_PROMPT_STUDIO_BODY_TOO_LARGE"
                    if is_prompt_studio
                    else "WEB_CONTENT_HANDOFF_BODY_TOO_LARGE"
                    if is_content_handoff
                    else "WEB_PARTNER_CRM_BODY_TOO_LARGE"
                    if is_partner_crm
                    else "WEB_CONTENT_STUDIO_BODY_TOO_LARGE"
                    if is_content_studio
                    else "WEB_CHANNEL_STRATEGY_BODY_TOO_LARGE"
                    if is_channel_strategy
                    else "WEB_VOICE_STUDIO_BODY_TOO_LARGE"
                    if is_voice_studio
                    else "WEB_VIDEO_STUDIO_BODY_TOO_LARGE"
                    if is_video_studio
                    else "WEB_SUBTITLE_STUDIO_BODY_TOO_LARGE"
                    if is_subtitle_studio
                    else "WEB_IMAGE_STUDIO_BODY_TOO_LARGE"
                    if is_image_studio
                    else "WEB_DOCUMENT_OPERATION_BODY_TOO_LARGE"
                    if is_document_operation
                    else "WEB_TREND_RESEARCH_BODY_TOO_LARGE"
                    if is_trend_research
                    else "WEB_GROWTH_REVIEW_BODY_TOO_LARGE"
                    if is_growth_review
                    else "WEB_MEDIA_FACTORY_BODY_TOO_LARGE"
                    if is_media_factory
                    else "WEB_DOCUMENT_WORKSPACE_BODY_TOO_LARGE"
                    if is_document_workspace
                    else "WEB_CHAT_WORKSPACE_BODY_TOO_LARGE"
                    if is_chat_workspace
                    else "WEB_ANALYTICS_WORKSPACE_BODY_TOO_LARGE"
                    if is_analytics_workspace
                    else "WEB_WORKBOARD_BODY_TOO_LARGE"
                    if is_workboard
                    else "WEB_AUTOPILOT_TICK_BODY_TOO_LARGE"
                    if is_autopilot_tick
                    else "WEB_AUTOPILOT_APPROVAL_BODY_TOO_LARGE"
                    if is_autopilot_approval
                    else "WEB_RELIABILITY_FOLLOWUP_BODY_TOO_LARGE"
                    if is_reliability_followup
                    else "WEB_NOTIFICATION_TICK_BODY_TOO_LARGE"
                    if is_notification_tick
                    else "WEB_INBOX_MUTATION_BODY_TOO_LARGE"
                    if is_inbox_mutation
                    else "WEB_DATA_CONTROL_BODY_TOO_LARGE"
                    if is_data_controls
                    else "WEB_ADMIN_DOCUMENT_ARCHIVE_UPLOAD_BODY_TOO_LARGE"
                    if is_admin_document_archive_upload
                    else "WEB_GOVERNANCE_BODY_TOO_LARGE"
                    if is_governance
                    else "WEB_MEDIA_WORKSPACE_BODY_TOO_LARGE"
                    if is_media
                    else "WEB_PROMPT_LIBRARY_BODY_TOO_LARGE"
                ),
            ),
            status_code=413,
            headers={
                "X-Request-ID": str(uuid.uuid4()),
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store, private",
                "Referrer-Policy": "same-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Content-Security-Policy": "default-src 'self'; connect-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'",
            },
        )
        if is_mailbox_confirmation:
            # The email link carries a one-time proof in its query string.
            # Preserve the stricter browser boundary even when the body cap
            # rejects a malformed confirmation before the router runs.
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        elif is_admin_document_archive_upload:
            # An oversized private archive upload must receive the same
            # cross-origin boundary as a normal archive response even though
            # this early raw-body guard bypasses the post-route middleware.
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if not self._is_bounded_write(scope):
            await self.app(scope, receive, send)
            return

        maximum = self._limit_for(scope)
        content_lengths = [
            value
            for name, value in (scope.get("headers") or [])
            if (name.lower() if isinstance(name, bytes) else str(name).encode("latin-1", "ignore").lower()) == b"content-length"
        ]
        if len(content_lengths) > 1:
            await self._reject(scope, receive, send)
            return
        if content_lengths:
            try:
                raw_value = content_lengths[0]
                raw_bytes = raw_value if isinstance(raw_value, bytes) else str(raw_value).encode("latin-1", "ignore")
                declared = int(raw_bytes.strip() or b"0")
            except (TypeError, ValueError):
                declared = maximum + 1
            if declared < 0 or declared > maximum:
                await self._reject(scope, receive, send)
                return

        # FastAPI converts exceptions raised from its request ``receive``
        # callback into a generic 400.  Read and count this one bounded
        # feature stream ourselves, then replay a single safe request event.
        # This handles absent/chunked Content-Length without permitting JSON
        # parsing to start until the entire raw body is within the contract.
        chunks: list[bytes] = []
        received = 0
        disconnected = False
        while True:
            message = await receive()
            message_type = message.get("type")
            if message_type == "http.disconnect":
                disconnected = True
                break
            if message_type != "http.request":
                continue
            chunk = message.get("body") or b""
            received += len(chunk)
            if received > maximum:
                await self._reject(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        replayed = False
        body = b"".join(chunks)

        async def bounded_receive():
            nonlocal replayed
            if replayed or disconnected:
                return {"type": "http.disconnect"}
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, bounded_receive, send)


# Register before the function middleware below. FastAPI's middleware stack
# then lets the standard security/rate/header layer wrap an early 413 just as
# it wraps every other private API response.
app.add_middleware(
    PromptLibraryBodyLimitMiddleware,
    max_bytes=PROMPT_LIBRARY_BODY_MAX_BYTES,
    import_max_bytes=PROMPT_LIBRARY_IMPORT_BODY_MAX_BYTES,
    prompt_studio_max_bytes=PROMPT_STUDIO_BODY_MAX_BYTES,
    media_max_bytes=MEDIA_WORKSPACE_BODY_MAX_BYTES,
    content_studio_max_bytes=CONTENT_STUDIO_BODY_MAX_BYTES,
    content_handoff_max_bytes=CONTENT_HANDOFF_BODY_MAX_BYTES,
    channel_strategy_max_bytes=CHANNEL_STRATEGY_BODY_MAX_BYTES,
    voice_studio_max_bytes=VOICE_STUDIO_BODY_MAX_BYTES,
    video_studio_max_bytes=VIDEO_STUDIO_BODY_MAX_BYTES,
    subtitle_studio_max_bytes=SUBTITLE_STUDIO_BODY_MAX_BYTES,
    image_studio_max_bytes=IMAGE_STUDIO_BODY_MAX_BYTES,
    document_workspace_max_bytes=DOCUMENT_WORKSPACE_BODY_MAX_BYTES,
    document_operation_max_bytes=DOCUMENT_OPERATION_BODY_MAX_BYTES,
    trend_research_max_bytes=TREND_RESEARCH_BODY_MAX_BYTES,
    growth_review_max_bytes=GROWTH_REVIEW_BODY_MAX_BYTES,
    media_factory_max_bytes=MEDIA_FACTORY_BODY_MAX_BYTES,
    chat_workspace_max_bytes=CHAT_WORKSPACE_BODY_MAX_BYTES,
    analytics_workspace_max_bytes=ANALYTICS_WORKSPACE_BODY_MAX_BYTES,
    workboard_max_bytes=WORKBOARD_BODY_MAX_BYTES,
    partner_crm_max_bytes=PARTNER_CRM_BODY_MAX_BYTES,
    autopilot_tick_max_bytes=AUTOPILOT_TICK_BODY_MAX_BYTES,
    autopilot_approval_max_bytes=AUTOPILOT_APPROVAL_BODY_MAX_BYTES,
    reliability_followup_max_bytes=RELIABILITY_FOLLOWUP_BODY_MAX_BYTES,
    notification_tick_max_bytes=NOTIFICATION_TICK_BODY_MAX_BYTES,
    inbox_mutation_max_bytes=INBOX_MUTATION_BODY_MAX_BYTES,
    data_controls_max_bytes=DATA_CONTROLS_BODY_MAX_BYTES,
    governance_max_bytes=GOVERNANCE_BODY_MAX_BYTES,
    admin_document_archive_upload_max_bytes=ADMIN_DOCUMENT_ARCHIVE_UPLOAD_BODY_MAX_BYTES,
    auth_credential_max_bytes=AUTH_CREDENTIAL_BODY_MAX_BYTES,
)


# These files belonged to the first static prototype.  The production
# entrypoint does not mount that prototype, but old bookmarks must never lead
# a future static mount back to a localStorage/raw-ID flow.  Redirect every
# known root HTML shell to its signed-session Portal counterpart instead.
_legacy_html_redirects = {
    "/admin.html": "/admin",
    "/affiliate.html": "/admin/leads",
    "/auth.html": "/login",
    "/b2b.html": "/admin/users",
    "/campaign.html": "/campaigns",
    "/coach.html": "/chat",
    "/customer_app.html": "/dashboard",
    "/index.html": "/",
    "/login.html": "/login",
    "/media.html": "/assets",
    "/mobile_app.html": "/dashboard",
    "/mobile_chat.html": "/chat",
    "/video.html": "/video",
    "/wallet.html": "/wallet",
}


def _safe_onboarding_next(value: str | None) -> str:
    """Accept a route continuation only when it is a plain local Portal path.

    The path is created by our own route gate, but it may later be supplied in
    a query string by a browser.  Do not let a post-Telegram-link redirect
    become an open redirect or send a user back into an auth/onboarding loop.
    """
    candidate = str(value or "").strip()
    if not candidate or not candidate.startswith("/") or candidate.startswith("//") or "\\" in candidate or "\x00" in candidate:
        return ""
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc or parsed.params or parsed.query or parsed.fragment:
        return ""
    path = parsed.path.rstrip("/") or "/"
    if path in {"/login", "/register", "/password-recovery", "/onboarding"}:
        return ""
    return path


def _prune_rate_windows(now: float) -> None:
    """Keep the in-process pre-DB limiter bounded under path/IP churn."""
    if len(_auth_rate_windows) < RATE_WINDOW_PRUNE_THRESHOLD:
        return
    for key, values in list(_auth_rate_windows.items()):
        active = [value for value in values if now - value < RATE_WINDOW_SECONDS]
        if active:
            _auth_rate_windows[key] = active
        else:
            _auth_rate_windows.pop(key, None)
    if len(_auth_rate_windows) < RATE_WINDOW_MAX_KEYS:
        return
    overflow = len(_auth_rate_windows) - RATE_WINDOW_MAX_KEYS + 1
    oldest_keys = sorted(
        _auth_rate_windows,
        key=lambda key: _auth_rate_windows[key][-1] if _auth_rate_windows[key] else float("-inf"),
    )[:overflow]
    for key in oldest_keys:
        _auth_rate_windows.pop(key, None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")[:80] or str(uuid.uuid4())
    request.state.request_id = request_id
    # Small in-process gate; production should additionally rate-limit at the edge.
    auth_limits = {
        "/api/v1/auth/login": 8,
        "/api/v1/auth/register": 4,
        "/api/v1/auth/security/password": 6,
        # SMTP delivery is externally visible but never browser-authoritative.
        # Limit it before the signed-session/CSRF/database work so a stolen
        # cookie cannot become a mailbox-spam primitive.
        "/api/v1/auth/security/email-verification/start": 3,
        # The one-time mailbox proof has its own HMAC/expiry/consumption
        # checks. This early cap only filters malformed POST floods.
        "/api/v1/auth/email-verification/confirm": 30,
        # Password recovery always returns the same response. This small
        # public edge gate limits email-delivery abuse before account lookup;
        # account-specific limits stay inside the signed Web database.
        "/api/v1/auth/password-recovery/start": 5,
        "/api/v1/auth/password-recovery/confirm": 30,
        # Password-first TOTP completion receives a separate tight bucket.
        # The server additionally locks its opaque challenge after five bad
        # codes; neither limit creates or reveals a session.
        "/api/v1/auth/login/mfa": 8,
        "/api/v1/auth/mfa/enrollment/start": 6,
        "/api/v1/auth/mfa/enrollment/confirm": 8,
        "/api/v1/auth/mfa/disable": 6,
        "/api/v1/auth/telegram/login/start": 5,
        "/api/v1/auth/telegram/login/complete": 8,
        "/api/v1/auth/telegram/link/start": 5,
        "/api/v1/auth/telegram/link/complete": 8,
        # Private Bot callback is independently authenticated by bearer/HMAC,
        # but keeping a narrow in-process gate prevents unauthenticated JSON
        # floods from reaching deeper request processing. Production keeps an
        # additional edge rate limit in front of Railway.
        "/api/v1/auth/internal/telegram-link/confirm": 60,
        "/api/v1/auth/internal/telegram-link/confirm/": 60,
        # The Operations Cron is separately HMAC-authenticated. This small
        # pre-verification bucket limits malformed traffic before body/HMAC
        # work without treating a browser cookie as internal authority.
        "/internal/v1/operations/tick": 12,
        # Inbox has an isolated HMAC protocol and must receive the same
        # early malformed-request protection before JSON/HMAC processing.
        "/internal/v1/notifications/tick": 12,
        # Private Web Asset Vault blobs are deliberately rate-limited before
        # multipart parsing; this is separate from Bot upload staging.
        "/api/v1/asset-vault/upload": 20,
    }
    oauth_start = (
        request.method == "GET"
        and request.url.path.startswith("/api/v1/auth/oauth/")
        and request.url.path.endswith("/start")
    )
    asset_archive = request.method == "POST" and request.url.path.startswith("/api/v1/asset-vault/") and request.url.path.endswith("/archive")
    project_package_export = (
        request.method == "POST"
        and request.url.path.startswith("/api/v1/projects/")
        and request.url.path.endswith("/packages")
    )
    document_operation_run = (
        request.method == "POST"
        and request.url.path in {
            "/api/v1/document-operations/pdf-split",
            "/api/v1/document-operations/pdf-merge",
            "/api/v1/document-operations/pdf-optimize",
            "/api/v1/document-operations/image-to-pdf",
            "/api/v1/document-operations/pdf-to-images",
            "/api/v1/document-operations/pdf-to-word",
            "/api/v1/document-operations/ocr-image",
            "/api/v1/document-operations/ocr-pdf",
            "/api/v1/document-operations/pdf-ocr-to-word",
            "/api/v1/image-operations/resize",
            "/api/v1/image-operations/enhance",
        }
    )
    # Memory writes are tiny text/state mutations, but remain intentionally
    # rate limited before SQLite work.  GET views stay unthrottled here while
    # signed-session/ownership checks remain mandatory in the router.
    memory_write = request.method == "POST" and request.url.path.startswith("/api/v1/memory/")
    # Prompt Library writes are owner-scoped text/template mutations.  Keep an
    # early independent limit before SQLite work; this does not replace the
    # router's signed session, CSRF, revision, idempotency or ownership checks.
    prompt_library_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/prompt-library/")
    # Prompt Library reads include text search over a private SQLite vault.
    # Bound them by a fixed route family too, so arbitrary template UUIDs or
    # query strings cannot bypass the pre-DB gate or grow its in-memory map.
    prompt_library_read = request.method == "GET" and request.url.path.startswith("/api/v1/prompt-library/")
    # Audio Library & Briefing keeps owner-scoped metadata and Asset Vault
    # references only.  Its independent route-family caps protect SQLite
    # before CSRF/revision/idempotency/ownership work without making a music
    # provider, Bot job or delivery capability appear available.
    media_workspace_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/media-workspace/")
    media_workspace_read = request.method == "GET" and request.url.path.startswith("/api/v1/media-workspace/")
    # Creative Content Studio persists owner-scoped authored text and version
    # snapshots. Keep fixed route-family buckets before SQLite/CSRF work so
    # arbitrary UUIDs/query strings cannot bypass the pre-DB limit. This does
    # not imply an AI/provider, Bot, payment, job or publishing capability.
    content_studio_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/content-studio/")
    content_studio_read = request.method == "GET" and request.url.path.startswith("/api/v1/content-studio/")
    # Trend Research is request-only text planning, but it still receives an
    # independent early cap before session/CSRF/template work. This never
    # opens live search, scraping, a provider, Bot bridge, job or payment.
    trend_research_write = request.method == "POST" and request.url.path.startswith("/api/v1/trend-research/")
    # Growth Review is a manual rule calculation. Its own fixed bucket keeps
    # a repeated numeric request from bypassing the common API throttle; it
    # never opens platform analytics, Bot/bridge, AI/provider, Xu or PayOS.
    growth_review_write = request.method == "POST" and request.url.path.startswith("/api/v1/growth-review/")
    # Media Factory Blueprint is also a request-only deterministic plan. Its
    # own bucket prevents repeat template work before session/CSRF handling;
    # it does not open an engine, source fetch, Bot bridge, job or payment.
    media_factory_write = request.method == "POST" and request.url.path.startswith("/api/v1/media-factory/")
    # Voice Studio persists only owner-scoped text/metadata and immutable
    # versions.  These fixed route-family buckets do not imply TTS, clone,
    # preview, provider, Bot, wallet or payment execution.
    voice_studio_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/voice-studio/")
    voice_studio_read = request.method == "GET" and request.url.path.startswith("/api/v1/voice-studio/")
    # Video Production Studio persists only signed-account plans, scene text
    # and deterministic estimates; this bounded family does not enable media
    # execution or any external authority.
    video_studio_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/video-studio/")
    video_studio_read = request.method == "GET" and request.url.path.startswith("/api/v1/video-studio/")
    # Subtitle Studio owns only manually authored caption text.  Fixed family
    # buckets protect its owner-scoped SQLite reads/writes without implying an
    # ASR, translation, TTS, dubbing, provider or media capability.
    subtitle_studio_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/subtitle-studio/")
    subtitle_studio_read = request.method == "GET" and request.url.path.startswith("/api/v1/subtitle-studio/")
    # Image Creative Studio is a signed-account text/reference workspace.
    # Its fixed family buckets prevent repeated browser authoring requests
    # from reaching SQLite unchecked; they do not enable image processing.
    image_studio_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/image-studio/")
    image_studio_read = request.method == "GET" and request.url.path.startswith("/api/v1/image-studio/")
    # Document & PDF Workspace stores only owner-scoped authored text and
    # opaque reference UUIDs.  Its fixed pre-DB rate bucket does not enable
    # upload, parsing, OCR, translation, provider/Bot or output execution.
    document_workspace_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/document-workspace/")
    document_workspace_read = request.method == "GET" and request.url.path.startswith("/api/v1/document-workspace/")
    # Conversation Workspace stores only owner-scoped authored text. Fixed
    # family buckets protect its private SQLite surface before CSRF/revision
    # work and do not enable any model, Bot/Core Bridge, provider, wallet or
    # payment capability.
    chat_workspace_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/chat-workspace/")
    chat_workspace_read = request.method == "GET" and request.url.path.startswith("/api/v1/chat-workspace/")
    # Analytics Workspace stores only signed-account, human-entered metrics,
    # observations and findings. These fixed family buckets protect its
    # private SQLite data before CSRF/revision/idempotency work; they never
    # enable platform analytics, Bot/provider calls, wallet, PayOS, jobs,
    # publishing or generated reports.
    analytics_workspace_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/analytics-workspace/")
    analytics_workspace_read = request.method == "GET" and request.url.path.startswith("/api/v1/analytics-workspace/")
    # A finalized manual CSV is a bounded private attachment, not a generic
    # analytics write.  Give it a smaller fixed bucket before CSRF, owner
    # lookup, SQLite reads or attachment assembly; this never enables Bot
    # campaign reports, platform exports or stored delivery artifacts.
    analytics_workspace_manual_csv_export = (
        request.method == "POST"
        and request.url.path.startswith("/api/v1/analytics-workspace/reports/")
        and request.url.path.endswith("/export.csv")
    )
    # Data Control Center reads one owner-scoped inventory/history projection;
    # its two writes are either a staged erasure request or a bounded direct
    # JSON attachment. Fixed buckets protect that private data before CSRF,
    # idempotency and SQLite work without granting any external authority.
    data_controls_write = request.method == "POST" and request.url.path.startswith("/api/v1/account/data-controls/")
    data_controls_read = request.method == "GET" and request.url.path.startswith("/api/v1/account/data-controls/")
    data_controls_export = request.method == "POST" and request.url.path == "/api/v1/account/data-controls/export.json"
    # Governance Documents is a local-admin Web record surface. Dedicated
    # fixed family buckets protect read/review mutations before signed-admin,
    # CSRF, DLP, revision and idempotency checks; they do not imply a Bot,
    # bridge, wallet, payment, provider, job, publication or notification.
    governance_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/admin/governance/")
    governance_read = request.method == "GET" and request.url.path.startswith("/api/v1/admin/governance/")
    # Internal Document Archive is an independent Web-local admin service. Its
    # file writes have a distinctly tighter bucket than metadata transitions;
    # every route still repeats signed-session, CSRF, revision, confirmation,
    # idempotency, ownership and file-integrity checks inside the router.
    admin_document_archive_prefix = "/api/v1/admin/internal-documents/"
    admin_document_archive_upload = (
        request.method == "POST"
        and PromptLibraryBodyLimitMiddleware._is_admin_document_archive_upload_path(request.url.path)
    )
    admin_document_archive_write = (
        request.method in {"POST", "PATCH"}
        and request.url.path.startswith(admin_document_archive_prefix)
    )
    admin_document_archive_download = (
        request.method == "GET"
        and request.url.path.startswith(admin_document_archive_prefix)
        and request.url.path.endswith("/download")
    )
    admin_document_archive_read = (
        request.method == "GET"
        and request.url.path.startswith(admin_document_archive_prefix)
        and not request.url.path.endswith("/download")
    )
    # Workboard is a private Web-only coordination surface. Fixed route-family
    # gates protect owner-scoped SQLite reads/writes before CSRF, revision and
    # idempotency work; they do not enable any Bot, provider, job, payment,
    # publication or notification automation.
    workboard_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/workboard/")
    workboard_read = request.method == "GET" and request.url.path.startswith("/api/v1/workboard/")
    # Campaign schedule actions are anchored to a signed owner's Campaign
    # detail route.  The plan itself is the schedule source, so POST/PATCH
    # mutations and the detail/schedule GET views share fixed pre-DB buckets.
    # This gate only limits repeated Web requests; the router still enforces
    # signed session, CSRF, ownership, revision and idempotency independently.
    campaign_schedule_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/campaigns/")
    campaign_schedule_read = request.method == "GET" and request.url.path.startswith("/api/v1/campaigns/")
    # Web Support Desk writes are durable, owner-scoped customer/operator
    # mutations.  Keep a narrow pre-DB gate separate from generic auth and
    # memory activity; it does not relax the router's CSRF/role/idempotency
    # checks and does not affect the legacy Bot bridge ticket endpoint.
    support_write = request.method == "POST" and request.url.path.startswith("/api/v1/support/cases")
    support_admin_write = request.method == "POST" and request.url.path.startswith("/api/v1/support/admin/cases")
    operations_admin_write = request.method == "POST" and request.url.path.startswith("/api/v1/operations/admin/approvals/")
    reliability_followup_write = request.method == "POST" and request.url.path.startswith("/api/v1/operations/admin/followups/")
    reliability_followup_read = request.method == "GET" and (
        request.url.path.startswith("/api/v1/operations/admin/reliability/")
        or request.url.path == "/api/v1/operations/admin/followups"
    )
    operations_read = request.method == "GET" and request.url.path.startswith("/api/v1/operations/")
    notification_tick = request.method == "POST" and request.url.path == "/internal/v1/notifications/tick"
    inbox_write = request.method == "POST" and request.url.path.startswith("/api/v1/inbox/items/")
    inbox_read = request.method == "GET" and request.url.path.startswith("/api/v1/inbox/")
    rate_limit = auth_limits.get(request.url.path) if request.method == "POST" else (10 if oauth_start else None)
    if asset_archive:
        rate_limit = 30
    if project_package_export:
        # A package compiles a bounded ZIP from private authoring data. This
        # separate gate prevents repeated browser clicks from becoming a disk
        # amplification path even before the idempotency record is reached.
        rate_limit = 20
    if document_operation_run:
        # PDF parsing and bounded image decoding are further constrained by
        # source/page/pixel/output limits, while this early gate blocks repeat
        # work before the operation's idempotency record can be observed.
        rate_limit = 10
    if memory_write:
        rate_limit = 40
    if prompt_library_write:
        rate_limit = 40
    if prompt_library_read:
        rate_limit = 120
    if media_workspace_write:
        rate_limit = 40
    if media_workspace_read:
        rate_limit = 120
    if content_studio_write:
        rate_limit = 40
    if content_studio_read:
        rate_limit = 120
    if trend_research_write:
        rate_limit = 40
    if growth_review_write:
        rate_limit = 40
    if media_factory_write:
        rate_limit = 40
    if voice_studio_write:
        rate_limit = 40
    if voice_studio_read:
        rate_limit = 120
    if video_studio_write:
        rate_limit = 40
    if video_studio_read:
        rate_limit = 120
    if subtitle_studio_write:
        rate_limit = 40
    if subtitle_studio_read:
        rate_limit = 120
    if image_studio_write:
        rate_limit = 40
    if image_studio_read:
        rate_limit = 120
    if document_workspace_write:
        rate_limit = 40
    if document_workspace_read:
        rate_limit = 120
    if chat_workspace_write:
        rate_limit = 40
    if chat_workspace_read:
        rate_limit = 120
    if analytics_workspace_write:
        rate_limit = 40
    if analytics_workspace_manual_csv_export:
        rate_limit = 10
    if analytics_workspace_read:
        rate_limit = 120
    if data_controls_write:
        rate_limit = 20
    if data_controls_export:
        rate_limit = 10
    if data_controls_read:
        rate_limit = 120
    if governance_write:
        rate_limit = 20
    if governance_read:
        rate_limit = 120
    if admin_document_archive_write:
        rate_limit = 30
    if admin_document_archive_upload:
        rate_limit = 8
    if admin_document_archive_download:
        rate_limit = 20
    if admin_document_archive_read:
        rate_limit = 60
    if workboard_write:
        rate_limit = 40
    if workboard_read:
        rate_limit = 120
    if campaign_schedule_write:
        rate_limit = 40
    if campaign_schedule_read:
        rate_limit = 120
    if support_write:
        rate_limit = 20
    if support_admin_write:
        rate_limit = 30
    if operations_admin_write:
        rate_limit = 20
    if reliability_followup_write:
        rate_limit = 20
    if reliability_followup_read:
        rate_limit = 120
    if operations_read:
        rate_limit = 120
    if inbox_write:
        rate_limit = 40
    if inbox_read:
        rate_limit = 120
    if rate_limit is not None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        _prune_rate_windows(now)
        # Template actions include an opaque UUID in the path. A fixed
        # family bucket prevents arbitrary 404/405 suffixes from bypassing
        # the gate or allocating one in-memory key per requested path.
        rate_scope = (
            "prompt-library-write" if prompt_library_write
            else "prompt-library-read" if prompt_library_read
            else "media-workspace-write" if media_workspace_write
            else "media-workspace-read" if media_workspace_read
            else "content-studio-write" if content_studio_write
            else "content-studio-read" if content_studio_read
            else "trend-research-write" if trend_research_write
            else "growth-review-write" if growth_review_write
            else "media-factory-write" if media_factory_write
            else "voice-studio-write" if voice_studio_write
            else "voice-studio-read" if voice_studio_read
            else "video-studio-write" if video_studio_write
            else "video-studio-read" if video_studio_read
            else "subtitle-studio-write" if subtitle_studio_write
            else "subtitle-studio-read" if subtitle_studio_read
            else "image-studio-write" if image_studio_write
            else "image-studio-read" if image_studio_read
            else "document-workspace-write" if document_workspace_write
            else "document-workspace-read" if document_workspace_read
            else "chat-workspace-write" if chat_workspace_write
            else "chat-workspace-read" if chat_workspace_read
            else "analytics-workspace-manual-csv-export" if analytics_workspace_manual_csv_export
            else "analytics-workspace-write" if analytics_workspace_write
            else "analytics-workspace-read" if analytics_workspace_read
            else "data-controls-export" if data_controls_export
            else "data-controls-write" if data_controls_write
            else "data-controls-read" if data_controls_read
            else "admin-document-archive-upload" if admin_document_archive_upload
            else "admin-document-archive-download" if admin_document_archive_download
            else "admin-document-archive-write" if admin_document_archive_write
            else "admin-document-archive-read" if admin_document_archive_read
            else "governance-write" if governance_write
            else "governance-read" if governance_read
            else "workboard-write" if workboard_write
            else "workboard-read" if workboard_read
            else "campaign-schedule-write" if campaign_schedule_write
            else "campaign-schedule-read" if campaign_schedule_read
            else "operations-admin-write" if operations_admin_write
            else "reliability-followup-write" if reliability_followup_write
            else "reliability-followup-read" if reliability_followup_read
            else "operations-read" if operations_read
            else "notification-tick" if notification_tick
            else "inbox-write" if inbox_write
            else "inbox-read" if inbox_read
            else request.url.path
        )
        rate_key = f"{rate_scope}:{client_ip}"
        window = [value for value in _auth_rate_windows.get(rate_key, []) if now - value < RATE_WINDOW_SECONDS]
        if len(window) >= rate_limit:
            is_document_workspace_request = document_workspace_write or document_workspace_read
            is_trend_research_request = trend_research_write
            is_growth_review_request = growth_review_write
            is_media_factory_request = media_factory_write
            is_chat_workspace_request = chat_workspace_write or chat_workspace_read
            is_analytics_workspace_request = analytics_workspace_write or analytics_workspace_read
            is_data_controls_request = data_controls_write or data_controls_read
            is_governance_request = governance_write or governance_read
            is_admin_document_archive_request = (
                admin_document_archive_write
                or admin_document_archive_read
                or admin_document_archive_download
            )
            is_workboard_request = workboard_write or workboard_read
            is_campaign_schedule_request = campaign_schedule_write or campaign_schedule_read
            is_reliability_request = reliability_followup_write or reliability_followup_read
            is_inbox_request = inbox_write or inbox_read or notification_tick
            is_mailbox_confirmation = request.url.path in {
                "/api/v1/auth/email-verification/confirm",
                "/api/v1/auth/password-recovery/confirm",
            }
            response = JSONResponse(
                envelope(
                    False,
                    "Vui lòng thử lại sau ít phút.",
                    data=(
                        copyfast_chat_workspace._boundary()
                        if is_chat_workspace_request
                        else copyfast_analytics_workspace._boundary()
                        if is_analytics_workspace_request
                        else copyfast_data_controls._boundary()
                        if is_data_controls_request
                        else copyfast_admin_document_archive._boundary()
                        if is_admin_document_archive_request
                        else copyfast_governance._boundary()
                        if is_governance_request
                        else copyfast_workboard._boundary()
                        if is_workboard_request
                        else copyfast_api._campaign_schedule_boundary()
                        if is_campaign_schedule_request
                        else copyfast_reliability._boundary()
                        if is_reliability_request
                        else copyfast_notification_center._boundary()
                        if is_inbox_request
                        else copyfast_trend_research._boundary()
                        if is_trend_research_request
                        else copyfast_growth_review._boundary()
                        if is_growth_review_request
                        else copyfast_media_factory._boundary()
                        if is_media_factory_request
                        else copyfast_document_workspace._boundary() if is_document_workspace_request else None
                    ),
                    status_name="guarded",
                    error_code="AUTH_RATE_LIMITED",
                ),
                status_code=429,
                headers={
                    "Cache-Control": "no-store, private",
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "same-origin",
                    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                    "Content-Security-Policy": "default-src 'self'; connect-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'",
                },
            )
            if analytics_workspace_manual_csv_export or data_controls_export or admin_document_archive_download:
                # This early return bypasses the normal post-route header
                # decoration below. Keep every throttled private attachment
                # attempt inside the same boundary as a successful response.
                response.headers["Referrer-Policy"] = "no-referrer"
                response.headers["Content-Security-Policy"] = "sandbox"
                response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            elif is_governance_request or is_admin_document_archive_request:
                response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            elif is_mailbox_confirmation:
                response.headers["Referrer-Policy"] = "no-referrer"
                response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
                response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            response.headers["X-Request-ID"] = request_id
            return response
        window.append(now)
        _auth_rate_windows[rate_key] = window
    try:
        response = await call_next(request)
    except Exception:
        # An unhandled exception may be rendered by Starlette outside this
        # middleware. Capture only a fixed Web-native route family and a
        # sanitized 5xx aggregate; this helper never reads request input,
        # identity, diagnostics or response payload and cannot alter the
        # original exception path.
        copyfast_reliability.record_runtime_failure(request, status_code=500)
        raise
    if response.status_code >= 500 and not bool(getattr(request.state, "reliability_expected_failure", False)):
        # Deliberately do not record planned HTTPException maintenance/config
        # guards as runtime faults. The exception handler marks those paths
        # below; only unexpected 5xx response metadata reaches Reliability.
        copyfast_reliability.record_runtime_failure(request, status_code=int(response.status_code))
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    # A private attachment deliberately has a stricter per-response policy
    # than the portal shell.  Do not overwrite it after the endpoint chose
    # no-referrer / sandbox delivery headers.
    private_asset_download = request.url.path.startswith("/api/v1/asset-vault/") and request.url.path.endswith("/download")
    private_package_download = request.url.path.startswith("/api/v1/project-packages/") and request.url.path.endswith("/download")
    private_document_download = request.url.path.startswith("/api/v1/document-operations/") and request.url.path.endswith("/download")
    private_image_download = request.url.path.startswith("/api/v1/image-operations/") and request.url.path.endswith("/download")
    # Storyboard Grid owns a distinct verified ZIP/cell delivery route rather
    # than reusing Image Operations.  Its attachments need the exact same
    # no-referrer/sandbox/private-cache boundary, including per-cell JPEGs.
    private_storyboard_grid_download = request.url.path.startswith("/api/v1/storyboard-grid/") and request.url.path.endswith("/download")
    # Support evidence uses the same private attachment boundary as Asset
    # Vault. It has both owner and staff routes under `/api/v1/support/`, so
    # keep the check route-family based rather than trying to infer a case ID
    # from untrusted path segments.
    private_support_evidence_download = request.url.path.startswith("/api/v1/support/") and request.url.path.endswith("/download")
    private_prompt_export = request.method == "POST" and request.url.path == "/api/v1/prompt-library/export"
    private_manual_analytics_csv_export = (
        request.method == "POST"
        and request.url.path.startswith("/api/v1/analytics-workspace/reports/")
        and request.url.path.endswith("/export.csv")
    )
    private_data_controls_export = (
        request.method == "POST"
        and request.url.path == "/api/v1/account/data-controls/export.json"
    )
    # Archive files never receive a direct/public URL. Both the active-version
    # and historical-version delivery routes are descriptor-pinned by the
    # archive router, while this layer supplies the browser cache/CORP boundary
    # even for a guarded or malformed download request.
    private_admin_document_archive = request.url.path.startswith("/api/v1/admin/internal-documents/")
    private_admin_document_archive_download = (
        private_admin_document_archive
        and request.method == "GET"
        and request.url.path.endswith("/download")
    )
    # Both confirmation routes receive a proof in the URL and may render a
    # credential form. Their router intentionally emits a narrow no-referrer
    # CSP; keep middleware from widening it after the endpoint returns.
    mailbox_confirmation = request.url.path in {
        "/api/v1/auth/email-verification/confirm",
        "/api/v1/auth/password-recovery/confirm",
    }
    # Governance records, lifecycle history and local-admin audit projections
    # are private API data even though they are not downloadable attachments.
    # Keep their cross-origin resource boundary explicit; the generic API
    # no-store rule below keeps them out of browser/PWA caches.
    private_governance = request.url.path.startswith("/api/v1/admin/governance/")
    private_download = (
        private_asset_download or private_package_download or private_document_download
        or private_image_download or private_storyboard_grid_download or private_support_evidence_download or private_prompt_export
        or private_manual_analytics_csv_export or private_data_controls_export or private_admin_document_archive_download
    )
    response.headers["Referrer-Policy"] = "no-referrer" if private_download or mailbox_confirmation else "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "sandbox"
        if private_download
        else "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        if mailbox_confirmation
        else "default-src 'self'; connect-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'"
    )
    if private_download or private_governance or private_admin_document_archive or mailbox_confirmation:
        # Cover successful attachments and every normal post-route rejection
        # (CSRF, validation, feature flag, owner, revision or size). The
        # early rate-limit branch sets the same header before its return.
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    # A signed-out browser must never be able to resurrect an old dashboard
    # document from its HTTP cache.  The service worker deliberately caches
    # only fixed public assets, but HTML portal documents and their auth
    # redirects also need an explicit browser-cache boundary.
    is_portal_document = response.headers.get("content-type", "").lower().startswith("text/html")
    is_dynamic_redirect = (
        response.status_code in {301, 302, 303, 307, 308}
        and not request.url.path.startswith("/static/")
    )
    if (
        request.url.path.startswith("/api/v1/")
        or request.url.path.startswith("/internal/")
        or is_portal_document
        or is_dynamic_redirect
    ):
        response.headers["Cache-Control"] = "no-store, private"
    return response


# Keep CORS outermost among application middleware. In particular, a request
# rejected by the raw Prompt Library body cap still receives the configured
# credentialed CORS headers instead of becoming an opaque browser network
# failure for an explicitly allowed origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID", "Idempotency-Key"],
)


@app.exception_handler(HTTPException)
async def copyfast_http_exception(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        # A deliberate feature/configuration guard is not an application
        # runtime crash. Keep it out of the reliability signal intake while
        # preserving the existing truthful API response.
        request.state.reliability_expected_failure = True
    if request.url.path.startswith("/api/") or request.url.path.startswith("/internal/") or request.url.path == "/admin" or request.url.path.startswith("/admin/"):
        error = "REQUEST_DENIED" if exc.status_code in {401, 403} else "REQUEST_INVALID"
        is_document_workspace = request.url.path.startswith("/api/v1/document-workspace/")
        is_media_factory = request.url.path.startswith("/api/v1/media-factory/")
        is_chat_workspace = request.url.path.startswith("/api/v1/chat-workspace/")
        is_analytics_workspace = request.url.path.startswith("/api/v1/analytics-workspace/")
        is_growth_review = request.url.path.startswith("/api/v1/growth-review/")
        is_workboard = request.url.path.startswith("/api/v1/workboard/")
        is_governance = request.url.path.startswith("/api/v1/admin/governance/")
        is_admin_document_archive = request.url.path.startswith("/api/v1/admin/internal-documents/")
        is_reliability_followup = request.url.path.startswith("/api/v1/operations/admin/reliability/") or request.url.path.startswith("/api/v1/operations/admin/followups")
        is_notification_center = request.url.path.startswith("/api/v1/inbox/") or request.url.path.startswith("/internal/v1/notifications/")
        return JSONResponse(
            envelope(
                False,
                str(exc.detail),
                data=(
                    copyfast_chat_workspace._boundary()
                    if is_chat_workspace
                    else copyfast_analytics_workspace._boundary()
                    if is_analytics_workspace
                    else copyfast_growth_review._boundary()
                    if is_growth_review
                    else copyfast_workboard._boundary()
                    if is_workboard
                    else copyfast_admin_document_archive._boundary()
                    if is_admin_document_archive
                    else copyfast_governance._boundary()
                    if is_governance
                    else copyfast_reliability._boundary()
                    if is_reliability_followup
                    else copyfast_notification_center._boundary()
                    if is_notification_center
                    else copyfast_media_factory._boundary()
                    if is_media_factory
                    else copyfast_document_workspace._boundary() if is_document_workspace else None
                ),
                status_name="failed",
                error_code=error,
            ),
            status_code=exc.status_code,
        )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def copyfast_validation_exception(request: Request, _exc: RequestValidationError):
    if request.url.path.startswith("/api/") or request.url.path.startswith("/internal/"):
        is_reliability_followup = request.url.path.startswith("/api/v1/operations/admin/reliability/") or request.url.path.startswith("/api/v1/operations/admin/followups")
        is_notification_center = request.url.path.startswith("/api/v1/inbox/") or request.url.path.startswith("/internal/v1/notifications/")
        is_governance = request.url.path.startswith("/api/v1/admin/governance/")
        is_admin_document_archive = request.url.path.startswith("/api/v1/admin/internal-documents/")
        is_growth_review = request.url.path.startswith("/api/v1/growth-review/")
        return JSONResponse(
            envelope(
                False,
                "Dữ liệu yêu cầu không hợp lệ",
                data=(
                    copyfast_chat_workspace._boundary()
                    if request.url.path.startswith("/api/v1/chat-workspace/")
                    else copyfast_analytics_workspace._boundary()
                    if request.url.path.startswith("/api/v1/analytics-workspace/")
                    else copyfast_growth_review._boundary()
                    if is_growth_review
                    else copyfast_workboard._boundary()
                    if request.url.path.startswith("/api/v1/workboard/")
                    else copyfast_admin_document_archive._boundary()
                    if is_admin_document_archive
                    else copyfast_governance._boundary()
                    if is_governance
                    else copyfast_reliability._boundary()
                    if is_reliability_followup
                    else copyfast_notification_center._boundary()
                    if is_notification_center
                    else copyfast_media_factory._boundary()
                    if request.url.path.startswith("/api/v1/media-factory/")
                    else copyfast_document_workspace._boundary() if request.url.path.startswith("/api/v1/document-workspace/") else None
                ),
                status_name="failed",
                error_code="REQUEST_INVALID",
            ),
            status_code=422,
        )
    return JSONResponse({"detail": "Dữ liệu yêu cầu không hợp lệ"}, status_code=422)


static_dir = ROOT / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/service-worker.js", include_in_schema=False)
async def root_service_worker():
    """Serve the worker at the origin root so its scope can cover the PWA.

    The worker itself has a deliberately tiny, public-only cache policy.  It
    must be revalidated on every registration check: otherwise an old worker
    could keep an obsolete offline policy after a security fix is deployed.
    """

    return FileResponse(
        static_dir / "portal" / "service-worker.js",
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, max-age=0, must-revalidate",
            "Service-Worker-Allowed": "/",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _durable_auth_throttle_guard(payload_email: str, request: Request, *, action: str) -> JSONResponse | None:
    """Consume a post-validation credential slot without exposing identity.

    The model passed by FastAPI has already survived the raw 8 KiB cap and
    bounded field validation.  Invalid email-shaped input remains on the
    original auth route's existing validation path, so it cannot create an
    unbounded stream of durable HMAC rows.  The cheap middleware gate remains
    deliberately separate and executes before this function.
    """

    normalized_email = copyfast_auth_throttle.normalize_email(payload_email)
    if not copyfast_auth.EMAIL_PATTERN.fullmatch(normalized_email):
        return None
    decision = copyfast_auth_throttle.consume(request, action=action, email=normalized_email)
    if decision.allowed:
        return None
    unavailable = decision.reason == "unavailable"
    response = JSONResponse(
        envelope(
            False,
            "Dịch vụ đăng nhập đang được bảo vệ. Vui lòng thử lại sau ít phút.",
            status_name="guarded",
            error_code="AUTH_THROTTLE_UNAVAILABLE" if unavailable else "AUTH_RATE_LIMITED",
        ),
        status_code=503 if unavailable else 429,
        headers={
            "Cache-Control": "no-store, private",
            "Retry-After": str(max(1, min(3600, int(decision.retry_after_seconds or 60)))),
        },
    )
    return response


@app.post("/api/v1/auth/register", include_in_schema=False)
async def durable_register(
    payload: copyfast_auth.RegisterRequest,
    request: Request,
    response: Response,
):
    """Bounded, durable wrapper for the existing non-enumerating register flow."""

    guarded = _durable_auth_throttle_guard(payload.email, request, action="register")
    if guarded is not None:
        return guarded
    return await copyfast_auth.register(payload, request, response)


@app.post("/api/v1/auth/login", include_in_schema=False)
async def durable_login(
    payload: copyfast_auth.LoginRequest,
    request: Request,
    response: Response,
):
    """Bounded, durable wrapper for the existing constant-work login flow."""

    guarded = _durable_auth_throttle_guard(payload.email, request, action="login")
    if guarded is not None:
        return guarded
    return await copyfast_auth.login(payload, request, response)


@app.post("/api/v1/auth/security/password", include_in_schema=False)
async def durable_password_change(
    payload: copyfast_auth.PasswordChangeRequest,
    request: Request,
    response: Response,
    account: dict = Depends(copyfast_auth.require_csrf),
):
    """Throttle only a real Web password factor before its rotation flow.

    Telegram-first and OAuth-only aliases never feed the durable email
    throttle. They are not password factors and must not create a second
    recovery/login surface merely by visiting this route with a valid cookie.
    """

    email = str(account.get("email") or "")
    if copyfast_auth.password_login_factor_available(email, bool(account.get("password_login_enabled"))):
        guarded = _durable_auth_throttle_guard(email, request, action="password_change")
        if guarded is not None:
            return guarded
    return await copyfast_auth.change_password(payload, request, response, account=account)


app.include_router(copyfast_auth.router, prefix="/api/v1/auth")
app.include_router(copyfast_mfa.router)
app.include_router(copyfast_api.router)
app.include_router(copyfast_admin_erp_navigation.router)
app.include_router(copyfast_admin_audit.router)
app.include_router(copyfast_projects.router)
app.include_router(copyfast_assets.router)
app.include_router(copyfast_project_packages.router)
app.include_router(copyfast_document_operations.router)
app.include_router(copyfast_image_operations.router)
app.include_router(copyfast_storyboard_grid.router)
app.include_router(copyfast_memory.router)
app.include_router(copyfast_prompt_library.router)
app.include_router(copyfast_prompt_studio.router)
app.include_router(copyfast_music_media.router)
app.include_router(copyfast_content_studio.router)
app.include_router(copyfast_channel_strategy.router)
app.include_router(copyfast_content_handoff.router)
app.include_router(copyfast_free_prompt_gallery.router)
app.include_router(copyfast_trend_research.router)
app.include_router(copyfast_growth_review.router)
app.include_router(copyfast_media_factory.router)
app.include_router(copyfast_voice_studio.router)
app.include_router(copyfast_video_studio.router)
app.include_router(copyfast_subtitle_workspace.router)
app.include_router(copyfast_image_studio.router)
app.include_router(copyfast_document_workspace.router)
app.include_router(copyfast_chat_workspace.router)
app.include_router(copyfast_analytics_workspace.router)
app.include_router(copyfast_data_controls.router)
app.include_router(copyfast_governance.router)
app.include_router(copyfast_admin_document_archive.router)
app.include_router(copyfast_workboard.router)
app.include_router(copyfast_partner_crm.router)
app.include_router(copyfast_support.router)
app.include_router(copyfast_autopilot.router)
app.include_router(copyfast_reliability.router)
app.include_router(copyfast_operations_desk.router)
app.include_router(copyfast_notification_center.router)


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    return {"ok": True, "app": "TOAN AAS Web App", "entrypoint": "app.py", "version": "P0.WEBAPP.COPYFAST1"}


@app.get("/admin-app", include_in_schema=False)
async def legacy_admin_redirect():
    return RedirectResponse("/admin", status_code=307)


@app.get("/wallet-app", include_in_schema=False)
async def legacy_wallet_redirect():
    return RedirectResponse("/wallet", status_code=307)


@app.get("/video-app", include_in_schema=False)
async def legacy_video_redirect():
    return RedirectResponse("/video", status_code=307)


@app.get("/campaign-app", include_in_schema=False)
async def legacy_campaign_redirect():
    return RedirectResponse("/campaigns", status_code=307)


@app.get("/affiliate-app", include_in_schema=False)
async def legacy_affiliate_redirect():
    return RedirectResponse("/admin/leads", status_code=307)


@app.get("/media-app", include_in_schema=False)
async def legacy_media_redirect():
    return RedirectResponse("/assets", status_code=307)


@app.get("/coach-app", include_in_schema=False)
@app.get("/assistant-app", include_in_schema=False)
async def legacy_assistant_redirect():
    return RedirectResponse("/chat", status_code=307)


@app.get("/b2b-app", include_in_schema=False)
async def legacy_b2b_redirect():
    return RedirectResponse("/admin/users", status_code=307)


@app.get("/{page_path:path}", include_in_schema=False)
async def page(page_path: str, request: Request):
    normalized = ("/" + page_path.lstrip("/")) if page_path else "/"
    normalized = normalized.rstrip("/") or "/"
    # This is the final portal fallback.  It must never turn an unknown API or
    # internal endpoint into a login redirect or an HTML shell, because API
    # callers require the application's normal JSON error contract.
    if normalized in {"/api", "/internal"} or normalized.startswith("/api/") or normalized.startswith("/internal/"):
        raise HTTPException(status_code=404, detail="Không tìm thấy tài nguyên")
    legacy_target = _legacy_html_redirects.get(normalized)
    if legacy_target:
        return RedirectResponse(legacy_target, status_code=307)
    # Earlier registry builds pointed SFX Library to a query variant of the
    # Music Library. Keep that existing bookmark usable while routing it to
    # its own Web surface so it can have independent readiness and filtering.
    if normalized == "/music/library" and request.query_params.get("type") == "sfx":
        return RedirectResponse("/music/sfx-library", status_code=307)
    if normalized == "/admin/autopilot":
        return RedirectResponse("/admin/operations", status_code=307)
    # Support Desk, Operations and the internal Content Handoff queue are
    # separately owned Web services.  Their narrow, server-side Web roles
    # deliberately do not require a Telegram/Bot identity.  Every other Admin
    # ERP route retains the stricter live canonical Bot-admin verification.
    if (
        normalized == "/admin/support"
        or normalized.startswith("/admin/support/")
        or normalized == "/admin/operations"
        or normalized.startswith("/admin/operations/")
        or normalized == "/admin/autopilot"
        or normalized.startswith("/admin/autopilot/")
        or normalized == "/admin/reliability"
        or normalized.startswith("/admin/reliability/")
        # The ERP navigation manifest grants this exact queue to Web Support
        # staff.  Keep its HTML gate aligned with the queue API's own
        # ``require_support_staff`` check instead of accidentally promoting a
        # Web-native handoff review to a canonical Bot-admin route.  Do not
        # broaden this to a prefix: no other /admin/content-handoffs path has
        # been reviewed as a staff surface yet.
        or normalized == "/admin/content-handoffs"
        # Operations Desk is an exact, read-only Web-native staff surface.
        # Its API independently repeats this role check, and no nested route
        # has been reviewed as an inherited support route.
        or normalized == "/admin/work-queue"
    ):
        copyfast_support.require_support_staff(current_session(request)["account"])
    # This is deliberately an exact route rather than an `/admin/crm/*`
    # prefix.  The manager directory returns only identifier-free pipeline
    # metadata and its JSON endpoint independently requires the signed local
    # Web admin role.  No Bot bridge call is appropriate for this one
    # Web-native, read-only view.
    elif normalized == "/admin/crm/leads":
        copyfast_auth.require_admin(request)
    # Internal Document Archive is an independently flagged, signed-Web-admin
    # surface. It has its own owner, CSRF, confirmation, revision, audit and
    # immutable-file checks; this page guard must not accidentally require or
    # infer the separate canonical Telegram/Bot-admin authority.
    elif normalized == "/admin/internal-documents" or normalized.startswith("/admin/internal-documents/"):
        copyfast_auth.require_admin(request)
    # Governance Documents is an independently flagged, Web-native local
    # admin surface.  Its API repeats signed admin + CSRF/revision checks and
    # never grants access to the remaining canonical Bot-admin ERP routes.
    elif normalized == "/admin/governance" or normalized.startswith("/admin/governance/"):
        copyfast_auth.require_admin(request)
    # The portal renderer is intentionally generic for parity routes, so this
    # explicit guard is necessary before it can render any remaining /admin/*
    # surface. Browser-supplied IDs never influence this decision.
    elif normalized == "/admin" or normalized.startswith("/admin/"):
        await require_canonical_admin(request)
    # app.toanaas.vn is an application origin, not the marketing site. A
    # signed Web account owns an independent Workspace even before it chooses
    # to link Telegram, so root entry always opens that Workspace. Telegram is
    # an optional connector for companion/Bot capabilities, never a gate on
    # Web-owned projects, drafts, planning or account data.
    # `/welcome` is the explicit, optional product introduction route.
    if normalized in {"/", "/app"}:
        try:
            current_session(request)
        except HTTPException:
            return RedirectResponse("/login", status_code=307)
        return RedirectResponse("/dashboard", status_code=307)

    public_pages = {"/welcome", "/legal", "/privacy", "/password-recovery"}
    if normalized in {"/login", "/register"}:
        try:
            current_session(request)
        except HTTPException:
            return render_portal(page_path)
        return RedirectResponse("/dashboard", status_code=307)
    if normalized not in public_pages:
        try:
            session = current_session(request)
        except HTTPException:
            # A portal shell without a signed session is a dead end. Keep the
            # requested internal route so login can return safely after auth.
            return RedirectResponse(f"/login?next={quote(normalized, safe='/')}", status_code=307)
        account = session["account"]
        linked = bool(account.get("canonical_user_id"))
        if linked and normalized == "/onboarding":
            return RedirectResponse(_safe_onboarding_next(request.query_params.get("next")) or "/dashboard", status_code=307)
    return render_portal(page_path)
