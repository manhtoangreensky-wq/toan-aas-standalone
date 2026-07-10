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

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import copyfast_api
import copyfast_auth
from copyfast_auth import envelope, require_canonical_admin
from copyfast_db import ensure_copyfast_schema
from copyfast_pages import ROOT, render_portal


def _origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "https://app.toanaas.vn,https://toanaas.vn")
    return [item.strip() for item in raw.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_copyfast_schema()
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")[:80] or str(uuid.uuid4())
    request.state.request_id = request_id
    # Small in-process gate; production should additionally rate-limit at the edge.
    auth_limits = {
        "/api/v1/auth/login": 8,
        "/api/v1/auth/register": 4,
    }
    if request.url.path in auth_limits and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        rate_key = f"{request.url.path}:{client_ip}"
        window = [value for value in _auth_rate_windows.get(rate_key, []) if now - value < 60]
        if len(window) >= auth_limits[request.url.path]:
            response = JSONResponse(envelope(False, "Vui lòng thử lại sau ít phút.", status_name="guarded", error_code="AUTH_RATE_LIMITED"), status_code=429)
            response.headers["X-Request-ID"] = request_id
            return response
        window.append(now)
        _auth_rate_windows[rate_key] = window
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; connect-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; frame-ancestors 'none'"
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
    return RedirectResponse("/admin/campaigns", status_code=307)


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
    # The portal renderer is intentionally generic for parity routes, so this
    # explicit guard is necessary before it can render any /admin/* surface.
    # It verifies both the signed web session and the bot's current canonical
    # admin role; browser-supplied IDs never influence this decision.
    if normalized == "/admin" or normalized.startswith("/admin/"):
        await require_canonical_admin(request)
    return render_portal(page_path)
