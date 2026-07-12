"""TOAN AAS standalone Web App — COPYFAST compatibility entrypoint.

The historical prototype modules remain in the repository for reference but
are intentionally not mounted here: they used a separate SQLite wallet/PayOS
implementation and browser-supplied identities.  This entrypoint exposes only
the signed-session web layer and its server-to-server bot bridge.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
import time
import uuid
from urllib.parse import quote, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import copyfast_api
import copyfast_assets
import copyfast_auth
import copyfast_document_operations
import copyfast_project_packages
import copyfast_projects
from copyfast_auth import current_session, ensure_auth_configuration, ensure_oauth_configuration, envelope, require_canonical_admin
from copyfast_db import (
    ensure_asset_vault_persistence,
    ensure_copyfast_persistence,
    ensure_copyfast_schema,
    ensure_document_operations_persistence,
    ensure_project_package_persistence,
)
from copyfast_pages import ROOT, render_portal


def _origins() -> list[str]:
    # Credentialed Web APIs expose signed-session/CSRF metadata.  Keep the
    # default to the dedicated application origin; a marketing/root site may
    # opt in explicitly only after it is audited as the same trust boundary.
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "https://app.toanaas.vn")
    origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("CORS_ALLOW_ORIGINS phải là danh sách origin tường minh khi dùng cookie")
    environment_values = (os.environ.get("APP_ENV", ""), os.environ.get("ENVIRONMENT", ""), os.environ.get("RAILWAY_ENVIRONMENT", ""))
    production = any(value.strip().lower() in {"production", "prod"} for value in environment_values if value)
    for origin in origins:
        parsed = urlparse(origin)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise RuntimeError("CORS_ALLOW_ORIGINS chứa origin không hợp lệ")
        if parsed.scheme != "https" and not (local_http and not production):
            raise RuntimeError("CORS_ALLOW_ORIGINS chỉ chấp nhận HTTPS, trừ localhost khi phát triển")
    return origins


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_auth_configuration()
    ensure_oauth_configuration()
    ensure_copyfast_persistence()
    ensure_copyfast_schema()
    ensure_asset_vault_persistence()
    ensure_project_package_persistence()
    ensure_document_operations_persistence()
    copyfast_document_operations.ensure_document_operations_runtime()
    copyfast_assets.reconcile_asset_vault_storage()
    copyfast_project_packages.reconcile_project_package_storage()
    copyfast_document_operations.reconcile_document_operation_storage()
    yield


app = FastAPI(title="TOAN AAS Web App", version="P0.WEBAPP.COPYFAST1", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID", "Idempotency-Key"],
)


_auth_rate_windows: dict[str, list[float]] = {}


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
    if path in {"/login", "/register", "/onboarding"}:
        return ""
    return path


@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")[:80] or str(uuid.uuid4())
    request.state.request_id = request_id
    # Small in-process gate; production should additionally rate-limit at the edge.
    auth_limits = {
        "/api/v1/auth/login": 8,
        "/api/v1/auth/register": 4,
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
    document_operation_run = request.method == "POST" and request.url.path == "/api/v1/document-operations/pdf-split"
    rate_limit = auth_limits.get(request.url.path) if request.method == "POST" else (10 if oauth_start else None)
    if asset_archive:
        rate_limit = 30
    if project_package_export:
        # A package compiles a bounded ZIP from private authoring data. This
        # separate gate prevents repeated browser clicks from becoming a disk
        # amplification path even before the idempotency record is reached.
        rate_limit = 20
    if document_operation_run:
        # PDF parsing is bounded further by source/page/output limits, but an
        # explicit early rate gate also prevents repeated parser work before
        # the operation's idempotency record can be observed.
        rate_limit = 10
    if rate_limit is not None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        rate_key = f"{request.url.path}:{client_ip}"
        window = [value for value in _auth_rate_windows.get(rate_key, []) if now - value < 60]
        if len(window) >= rate_limit:
            response = JSONResponse(envelope(False, "Vui lòng thử lại sau ít phút.", status_name="guarded", error_code="AUTH_RATE_LIMITED"), status_code=429)
            response.headers["X-Request-ID"] = request_id
            return response
        window.append(now)
        _auth_rate_windows[rate_key] = window
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    # A private attachment deliberately has a stricter per-response policy
    # than the portal shell.  Do not overwrite it after the endpoint chose
    # no-referrer / sandbox delivery headers.
    private_asset_download = request.url.path.startswith("/api/v1/asset-vault/") and request.url.path.endswith("/download")
    private_package_download = request.url.path.startswith("/api/v1/project-packages/") and request.url.path.endswith("/download")
    private_document_download = request.url.path.startswith("/api/v1/document-operations/") and request.url.path.endswith("/download")
    private_download = private_asset_download or private_package_download or private_document_download
    response.headers["Referrer-Policy"] = "no-referrer" if private_download else "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "sandbox" if private_download else "default-src 'self'; connect-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'"
    if request.url.path.startswith("/api/v1/") or request.url.path.startswith("/internal/"):
        response.headers["Cache-Control"] = "no-store, private"
    return response


@app.exception_handler(HTTPException)
async def copyfast_http_exception(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/") or request.url.path.startswith("/internal/") or request.url.path == "/admin" or request.url.path.startswith("/admin/"):
        error = "REQUEST_DENIED" if exc.status_code in {401, 403} else "REQUEST_INVALID"
        return JSONResponse(envelope(False, str(exc.detail), status_name="failed", error_code=error), status_code=exc.status_code)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def copyfast_validation_exception(request: Request, _exc: RequestValidationError):
    if request.url.path.startswith("/api/") or request.url.path.startswith("/internal/"):
        return JSONResponse(
            envelope(False, "Dữ liệu yêu cầu không hợp lệ", status_name="failed", error_code="REQUEST_INVALID"),
            status_code=422,
        )
    return JSONResponse({"detail": "Dữ liệu yêu cầu không hợp lệ"}, status_code=422)


static_dir = ROOT / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(copyfast_auth.router, prefix="/api/v1/auth")
app.include_router(copyfast_api.router)
app.include_router(copyfast_projects.router)
app.include_router(copyfast_assets.router)
app.include_router(copyfast_project_packages.router)
app.include_router(copyfast_document_operations.router)


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
    legacy_target = _legacy_html_redirects.get(normalized)
    if legacy_target:
        return RedirectResponse(legacy_target, status_code=307)
    # Earlier registry builds pointed SFX Library to a query variant of the
    # Music Library. Keep that existing bookmark usable while routing it to
    # its own Web surface so it can have independent readiness and filtering.
    if normalized == "/music/library" and request.query_params.get("type") == "sfx":
        return RedirectResponse("/music/sfx-library", status_code=307)
    # The portal renderer is intentionally generic for parity routes, so this
    # explicit guard is necessary before it can render any /admin/* surface.
    # It verifies both the signed web session and the bot's current canonical
    # admin role; browser-supplied IDs never influence this decision.
    if normalized == "/admin" or normalized.startswith("/admin/"):
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

    public_pages = {"/welcome", "/legal", "/privacy"}
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
