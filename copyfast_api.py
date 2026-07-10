"""Authenticated Web API that adapts the private bot core to the portal."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from copyfast_auth import (
    envelope,
    require_account,
    require_canonical_admin,
    require_canonical_admin_csrf,
    require_admin_csrf,
    require_csrf,
)
from copyfast_bridge import bridge_configured, bridge_request
from copyfast_db import transaction, utc_now
from copyfast_registry import FEATURE_BY_KEY, catalog


router = APIRouter(prefix="/api/v1", tags=["COPYFAST Core"])
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
IDEMPOTENCY_PENDING_SECONDS = 90
_PENDING_IDEMPOTENCY_KEY = "_web_idempotency_pending"
_RETRYABLE_BRIDGE_CODES = frozenset({"CORE_BRIDGE_UNAVAILABLE", "CORE_BRIDGE_RATE_LIMITED", "CORE_BRIDGE_NOT_CONFIGURED"})
UPLOAD_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm",
    ".mp3", ".wav", ".m4a", ".ogg", ".pdf", ".txt", ".srt", ".vtt", ".docx",
})
UPLOAD_MIME_TYPES = frozenset({
    "image/jpeg", "image/png", "image/webp", "video/mp4", "video/quicktime", "video/webm",
    "audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/ogg", "application/ogg",
    "application/pdf", "text/plain", "text/vtt", "application/x-subrip", "application/octet-stream",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", "")[:80]


def _flags() -> dict[str, bool]:
    def enabled(name: str, default: bool = False) -> bool:
        return os.environ.get(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}
    return {
        "copyfast_enabled": enabled("WEBAPP_COPYFAST_ENABLED", True),
        "provider_calls_enabled": enabled("WEBAPP_PROVIDER_CALLS_ENABLED", False),
        "payment_enabled": enabled("WEBAPP_PAYMENT_ENABLED", False),
        "admin_erp_enabled": enabled("WEBAPP_ADMIN_ERP_ENABLED", True),
        # Admin ERP is intentionally read-only until a separate canonical
        # write adapter is reviewed.  Keeping this false prevents direct API
        # callers from bypassing the presentation shell's read-only posture.
        "admin_writes_enabled": enabled("WEBAPP_ADMIN_WRITES_ENABLED", False),
        "pwa_enabled": enabled("WEBAPP_PWA_ENABLED", False),
    }


def _linked(account: dict) -> str:
    user_id = str(account.get("canonical_user_id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=409, detail="Hãy liên kết Telegram trước khi dùng dữ liệu hoặc tính năng bot")
    return user_id


def _safe_input(value: dict[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Dữ liệu đầu vào không hợp lệ") from exc
    if len(encoded.encode("utf-8")) > 64_000:
        raise HTTPException(status_code=413, detail="Dữ liệu đầu vào quá lớn")
    return value


def _upload_max_bytes() -> int:
    raw_bytes = os.environ.get("WEBAPP_UPLOAD_MAX_BYTES", "").strip()
    raw_mb = os.environ.get("WEBAPP_UPLOAD_MAX_MB", "12").strip()
    try:
        requested = int(raw_bytes) if raw_bytes else int(raw_mb) * 1024 * 1024
    except ValueError:
        requested = 12 * 1024 * 1024
    return max(1 * 1024 * 1024, min(requested, 50 * 1024 * 1024))


def _validate_upload_name(file_name: str | None) -> tuple[str, str]:
    name = str(file_name or "").strip()
    if not name or len(name) > 180 or "\x00" in name or "/" in name or "\\" in name or name.startswith("."):
        raise HTTPException(status_code=422, detail="Tên tệp không hợp lệ")
    extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Định dạng tệp chưa được hỗ trợ")
    return name, extension


async def _read_validated_upload(file: UploadFile) -> tuple[str, str, bytes, str]:
    name, extension = _validate_upload_name(file.filename)
    media_type = str(file.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if media_type not in UPLOAD_MIME_TYPES:
        raise HTTPException(status_code=415, detail="MIME của tệp không được hỗ trợ")
    chunks: list[bytes] = []
    total = 0
    limit = _upload_max_bytes()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail="Tệp vượt quá giới hạn an toàn")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=422, detail="Tệp không có dữ liệu")
    # Apply cheap signature checks before the bytes ever cross into the bot.
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="PDF không hợp lệ")
    if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail="PNG không hợp lệ")
    if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=422, detail="JPEG không hợp lệ")
    return name, media_type, content, hashlib.sha256(content).hexdigest()


class FeatureRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(default="", max_length=160)


class PaymentRequest(BaseModel):
    package_id: str = Field(default="", max_length=120)
    payment_type: str = Field(default="topup_xu", max_length=80)
    idempotency_key: str = Field(min_length=12, max_length=160)


class FreezeRequest(BaseModel):
    frozen: bool
    note: str = Field(default="", max_length=300)
    idempotency_key: str = Field(min_length=12, max_length=160)


class TicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=180)
    detail: str = Field(min_length=3, max_length=4000)
    idempotency_key: str = Field(min_length=12, max_length=160)


def _require_key(key: str) -> str:
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _pending_marker() -> str:
    return json.dumps({_PENDING_IDEMPOTENCY_KEY: str(uuid.uuid4())}, separators=(",", ":"))


def _pending_response(value: str) -> bool:
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return False
    return isinstance(decoded, dict) and isinstance(decoded.get(_PENDING_IDEMPOTENCY_KEY), str)


def _pending_is_stale(created_at: str) -> bool:
    try:
        created = datetime.fromisoformat(created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - created > timedelta(seconds=IDEMPOTENCY_PENDING_SECONDS)
    except (TypeError, ValueError):
        return True


def _reserve_idempotency(scope: str, key: str) -> tuple[str, dict | None, str]:
    """Atomically reserve a write key before the bridge can observe it.

    The old check-then-call-then-insert sequence let two concurrent Web
    requests create two bridge calls before either response was saved.  A
    short-lived pending record gives exactly one request ownership; a stale
    record can be safely reclaimed after a process crash because the bot also
    receives the same canonical idempotency key.
    """
    marker = _pending_marker()
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT response_json, created_at FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if row:
            stored, created_at = str(row[0] or ""), str(row[1] or "")
            if _pending_response(stored):
                if not _pending_is_stale(created_at):
                    return "pending", None, ""
                conn.execute(
                    "UPDATE web_idempotency SET response_json=?, created_at=? WHERE scope=? AND key=? AND response_json=?",
                    (marker, now, scope, key, stored),
                )
                return "owner", None, marker
            try:
                cached = json.loads(stored)
            except (TypeError, ValueError):
                cached = None
            if isinstance(cached, dict):
                return "cached", cached, ""
            conn.execute(
                "UPDATE web_idempotency SET response_json=?, created_at=? WHERE scope=? AND key=?",
                (marker, now, scope, key),
            )
            return "owner", None, marker
        conn.execute(
            "INSERT INTO web_idempotency (scope, key, response_json, created_at) VALUES (?, ?, ?, ?)",
            (scope, key, marker, now),
        )
    return "owner", None, marker


def _complete_idempotency(scope: str, key: str, marker: str, response: dict) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE web_idempotency SET response_json=?, created_at=? WHERE scope=? AND key=? AND response_json=?",
            (json.dumps(response, ensure_ascii=False, separators=(",", ":")), utc_now(), scope, key, marker),
        )


def _release_idempotency(scope: str, key: str, marker: str) -> None:
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope=? AND key=? AND response_json=?",
            (scope, key, marker),
        )


def _retryable_bridge_response(response: dict) -> bool:
    return not bool(response.get("ok")) and str(response.get("error_code") or "") in _RETRYABLE_BRIDGE_CODES


async def _run_idempotent(scope: str, key: str, operation) -> dict:
    state, cached, marker = _reserve_idempotency(scope, key)
    if state == "cached" and cached is not None:
        return cached
    if state == "pending":
        return envelope(
            False,
            "Yêu cầu cùng mã idempotency đang được xử lý. Vui lòng chờ phản hồi canonical.",
            status_name="guarded",
            error_code="IDEMPOTENCY_IN_PROGRESS",
        )
    try:
        result = await operation()
    except Exception:
        _release_idempotency(scope, key, marker)
        raise
    if _retryable_bridge_response(result):
        _release_idempotency(scope, key, marker)
    else:
        _complete_idempotency(scope, key, marker, result)
    return result


async def _bridge(method: str, path: str, *, account: dict, request: Request, payload: dict | None = None, params: dict | None = None) -> dict:
    flags = _flags()
    if not flags["copyfast_enabled"]:
        return envelope(False, "Web App đang tạm khóa theo feature flag COPYFAST.", status_name="guarded", error_code="WEBAPP_COPYFAST_DISABLED")
    if path.startswith("/internal/v1/admin/") and not flags["admin_erp_enabled"]:
        return envelope(False, "Admin ERP trên Web đang tạm khóa theo feature flag.", status_name="guarded", error_code="WEBAPP_ADMIN_ERP_DISABLED")
    user_id = _linked(account)
    enriched = dict(payload or {})
    # The browser must never be able to choose the canonical target identity.
    # Do not use setdefault here: a forged outer payload could otherwise
    # override the signed session's Telegram identity on POST requests.
    enriched["user_id"] = user_id
    query = None
    if method.upper() == "GET":
        # A route may add safe filters (for example an admin record ID), but
        # it must never replace the canonical target identity supplied by the
        # signed Web session.
        query = dict(params or {})
        query["user_id"] = user_id
    return await bridge_request(method, path, payload=enriched if method.upper() != "GET" else None, params=query, request_id=_request_id(request), actor_id=user_id)


@router.get("/catalog")
async def feature_catalog():
    return envelope(True, "Danh mục tính năng Web App", data={"features": catalog(), "flags": _flags(), "bridge_configured": bridge_configured()})


@router.get("/core/status")
async def core_status():
    return envelope(True, "Trạng thái kết nối", data={"bridge_configured": bridge_configured(), "flags": _flags()})


@router.get("/core/me")
async def core_me(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/me", account=account, request=request)


@router.get("/wallet")
async def wallet(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/wallet", account=account, request=request)


@router.get("/wallet/history")
async def wallet_history(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/wallet/history", account=account, request=request)


@router.get("/pricing")
async def pricing(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/pricing", account=account, request=request)


@router.get("/packages")
async def packages(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/packages", account=account, request=request)


@router.post("/payments/create")
async def create_payment(payload: PaymentRequest, request: Request, account: dict = Depends(require_csrf)):
    if not _flags()["payment_enabled"]:
        return envelope(False, "Nạp Xu trên Web đang chờ xác minh core payment.", status_name="guarded", error_code="WEBAPP_PAYMENT_DISABLED")
    key = _require_key(payload.idempotency_key)
    scope = f"payment:{account['id']}"
    return await _run_idempotent(
        scope,
        key,
        lambda: _bridge(
            "POST", "/internal/v1/payments/create", account=account, request=request,
            payload={"package_id": payload.package_id, "payment_type": payload.payment_type, "idempotency_key": key},
        ),
    )


@router.get("/payments/{payment_id}")
async def payment_status(payment_id: str, request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", f"/internal/v1/payments/{payment_id}", account=account, request=request)


@router.get("/jobs")
async def list_jobs(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/jobs", account=account, request=request)


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str, request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", f"/internal/v1/jobs/{job_id}", account=account, request=request)


@router.get("/assets")
async def assets(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/assets", account=account, request=request)


@router.get("/assets/{asset_id}/download")
async def asset_download(asset_id: str, request: Request, account: dict = Depends(require_account)):
    # The core either returns a short-lived, ownership-checked delivery URL or
    # stays guarded. The Web App must never reconstruct provider URLs itself.
    return await _bridge("GET", f"/internal/v1/assets/{asset_id}/download", account=account, request=request)


@router.get("/voice/profiles")
async def voice_profiles(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/voice/profiles", account=account, request=request)


@router.post("/uploads")
async def upload_to_canonical_staging(
    request: Request,
    file: UploadFile = File(...),
    account: dict = Depends(require_csrf),
):
    """Validate browser bytes then transfer them only to bot-owned staging.

    The standalone Web DB records neither raw file bytes nor provider paths.
    A temporary/retried browser upload is idempotent at both Web and bot layers.
    """
    if not _flags()["copyfast_enabled"]:
        return envelope(False, "Web App đang tạm khóa theo feature flag COPYFAST.", status_name="guarded", error_code="WEBAPP_COPYFAST_DISABLED")
    key = _require_key(request.headers.get("Idempotency-Key", ""))
    scope = f"upload:{account['id']}"
    try:
        name, media_type, content, checksum = await _read_validated_upload(file)
    finally:
        await file.close()
    return await _run_idempotent(
        scope,
        key,
        lambda: _bridge(
            "POST",
            "/internal/v1/uploads",
            account=account,
            request=request,
            payload={
                "file_name": name,
                "content_type": media_type,
                "content_base64": base64.b64encode(content).decode("ascii"),
                "sha256": checksum,
                "idempotency_key": key,
            },
        ),
    )


@router.get("/support/tickets")
async def support_tickets(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/support/tickets", account=account, request=request)


@router.post("/support/tickets")
async def create_support_ticket(payload: TicketRequest, request: Request, account: dict = Depends(require_csrf)):
    key = _require_key(payload.idempotency_key)
    scope = f"ticket:{account['id']}"
    return await _run_idempotent(
        scope,
        key,
        lambda: _bridge(
            "POST",
            "/internal/v1/support/tickets",
            account=account,
            request=request,
            payload={"subject": payload.subject, "detail": payload.detail, "idempotency_key": key},
        ),
    )


@router.get("/features/status")
async def feature_status(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/features/status", account=account, request=request)


async def _feature_action(action: str, feature: str, payload: FeatureRequest, request: Request, account: dict) -> dict:
    if feature not in FEATURE_BY_KEY:
        raise HTTPException(status_code=404, detail="Tính năng chưa có trong parity registry")
    if not _flags()["copyfast_enabled"]:
        return envelope(False, "Web App đang tạm khóa theo feature flag COPYFAST.", status_name="guarded", error_code="WEBAPP_COPYFAST_DISABLED")
    # Keep the feature input as a distinct object in the bot contract.  The
    # private bridge consumes `user_id` and `idempotency_key` at the envelope
    # level; treating form fields as that envelope silently discarded drafts
    # and estimates on the bot side.
    values = _safe_input(dict(payload.input))
    key = payload.idempotency_key or request.headers.get("Idempotency-Key", "")
    if action == "confirm":
        if not _flags()["provider_calls_enabled"]:
            return envelope(False, "Tính năng đang ở chế độ an toàn và chưa gọi engine từ Web.", status_name="guarded", error_code="WEBAPP_PROVIDER_CALLS_DISABLED")
        key = _require_key(key)
        scope = f"feature:{account['id']}:{feature}:confirm"
        return await _run_idempotent(
            scope,
            key,
            lambda: _bridge(
                "POST",
                f"/internal/v1/features/{feature}/{action}",
                account=account,
                request=request,
                payload={"input": values, "idempotency_key": key},
            ),
        )
    return await _bridge(
        "POST",
        f"/internal/v1/features/{feature}/{action}",
        account=account,
        request=request,
        payload={"input": values, "idempotency_key": key if key else None},
    )


@router.post("/features/{feature}/draft")
async def feature_draft(feature: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_csrf)):
    return await _feature_action("draft", feature, payload, request, account)


@router.post("/features/{feature}/estimate")
async def feature_estimate(feature: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_csrf)):
    return await _feature_action("estimate", feature, payload, request, account)


@router.post("/features/{feature}/confirm")
async def feature_confirm(feature: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_csrf)):
    return await _feature_action("confirm", feature, payload, request, account)


@router.get("/admin/summary")
async def admin_summary(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/summary", account=account, request=request)


@router.get("/admin/users")
async def admin_users(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/users", account=account, request=request)


@router.get("/admin/jobs")
async def admin_jobs(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/jobs", account=account, request=request)


@router.get("/admin/payments")
async def admin_payments(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/payments", account=account, request=request)


@router.get("/admin/providers")
async def admin_providers(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/providers", account=account, request=request)


@router.get("/admin/tickets")
async def admin_tickets(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/tickets", account=account, request=request)


@router.get("/admin/modules/{module}")
async def admin_module(module: str, request: Request, account: dict = Depends(require_canonical_admin)):
    record_id = str(request.query_params.get("record_id") or "").strip()
    params = {"record_id": record_id} if record_id else None
    return await _bridge("GET", f"/internal/v1/admin/modules/{module}", account=account, request=request, params=params)


@router.post("/admin/jobs/{job_id}/retry")
async def admin_retry_job(job_id: str, payload: FeatureRequest, request: Request):
    # Retain local session/CSRF/admin protection even while the write gate is
    # disabled, but do not contact the bot authority unless a separately
    # reviewed write adapter has been explicitly enabled.
    account = require_admin_csrf(request)
    if not _flags()["admin_writes_enabled"]:
        return envelope(False, "Admin ERP Web hiện chỉ đọc; retry job chưa được bật.", status_name="guarded", error_code="WEBAPP_ADMIN_WRITES_DISABLED")
    account = await require_canonical_admin_csrf(request)
    key = _require_key(payload.idempotency_key or request.headers.get("Idempotency-Key", ""))
    return await _run_idempotent(
        f"admin:{account['id']}:retry:{job_id}",
        key,
        lambda: _bridge("POST", f"/internal/v1/admin/jobs/{job_id}/retry", account=account, request=request, payload={"idempotency_key": key}),
    )


@router.post("/admin/jobs/{job_id}/refund")
async def admin_refund_job(job_id: str, payload: FeatureRequest, request: Request):
    account = require_admin_csrf(request)
    if not _flags()["admin_writes_enabled"]:
        return envelope(False, "Admin ERP Web hiện chỉ đọc; refund chưa được bật.", status_name="guarded", error_code="WEBAPP_ADMIN_WRITES_DISABLED")
    account = await require_canonical_admin_csrf(request)
    key = _require_key(payload.idempotency_key or request.headers.get("Idempotency-Key", ""))
    return await _run_idempotent(
        f"admin:{account['id']}:refund:{job_id}",
        key,
        lambda: _bridge("POST", f"/internal/v1/admin/jobs/{job_id}/refund", account=account, request=request, payload={"idempotency_key": key}),
    )


@router.post("/admin/features/{feature}/freeze")
async def admin_freeze_feature(feature: str, payload: FreezeRequest, request: Request):
    account = require_admin_csrf(request)
    if not _flags()["admin_writes_enabled"]:
        return envelope(False, "Admin ERP Web hiện chỉ đọc; freeze feature chưa được bật.", status_name="guarded", error_code="WEBAPP_ADMIN_WRITES_DISABLED")
    account = await require_canonical_admin_csrf(request)
    key = _require_key(payload.idempotency_key)
    return await _run_idempotent(
        f"admin:{account['id']}:freeze:{feature}",
        key,
        lambda: _bridge(
            "POST",
            f"/internal/v1/admin/features/{feature}/freeze",
            account=account,
            request=request,
            payload={"frozen": payload.frozen, "note": payload.note, "idempotency_key": key},
        ),
    )
