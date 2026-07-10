"""Authenticated Web API that adapts the private bot core to the portal."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from copyfast_auth import envelope, require_account, require_admin, require_admin_csrf, require_csrf
from copyfast_bridge import bridge_configured, bridge_request
from copyfast_db import transaction, utc_now
from copyfast_registry import FEATURE_BY_KEY, catalog


router = APIRouter(prefix="/api/v1", tags=["COPYFAST Core"])
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")


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


def _idempotency(scope: str, key: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute("SELECT response_json FROM web_idempotency WHERE scope=? AND key=?", (scope, key)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except (TypeError, ValueError):
        return None


def _remember_idempotency(scope: str, key: str, response: dict) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO web_idempotency (scope, key, response_json, created_at) VALUES (?, ?, ?, ?)",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), utc_now()),
        )


async def _bridge(method: str, path: str, *, account: dict, request: Request, payload: dict | None = None, params: dict | None = None) -> dict:
    user_id = _linked(account)
    enriched = dict(payload or {})
    enriched.setdefault("user_id", user_id)
    return await bridge_request(method, path, payload=enriched if method.upper() != "GET" else None, params=params or ({"user_id": user_id} if method.upper() == "GET" else None), request_id=_request_id(request), actor_id=user_id)


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


@router.post("/payments/create")
async def create_payment(payload: PaymentRequest, request: Request, account: dict = Depends(require_csrf)):
    if not _flags()["payment_enabled"]:
        return envelope(False, "Nạp Xu trên Web đang chờ xác minh core payment.", status_name="guarded", error_code="WEBAPP_PAYMENT_DISABLED")
    key = _require_key(payload.idempotency_key)
    scope = f"payment:{account['id']}"
    if prior := _idempotency(scope, key):
        return prior
    response = await _bridge(
        "POST", "/internal/v1/payments/create", account=account, request=request,
        payload={"package_id": payload.package_id, "payment_type": payload.payment_type, "idempotency_key": key},
    )
    _remember_idempotency(scope, key, response)
    return response


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


@router.get("/support/tickets")
async def support_tickets(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/support/tickets", account=account, request=request)


@router.post("/support/tickets")
async def create_support_ticket(payload: TicketRequest, request: Request, account: dict = Depends(require_csrf)):
    key = _require_key(payload.idempotency_key)
    scope = f"ticket:{account['id']}"
    if prior := _idempotency(scope, key):
        return prior
    result = await _bridge("POST", "/internal/v1/support/tickets", account=account, request=request, payload={"subject": payload.subject, "detail": payload.detail, "idempotency_key": key})
    _remember_idempotency(scope, key, result)
    return result


@router.get("/features/status")
async def feature_status(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/features/status", account=account, request=request)


async def _feature_action(action: str, feature: str, payload: FeatureRequest, request: Request, account: dict) -> dict:
    if feature not in FEATURE_BY_KEY:
        raise HTTPException(status_code=404, detail="Tính năng chưa có trong parity registry")
    values = _safe_input(payload.input)
    key = payload.idempotency_key or request.headers.get("Idempotency-Key", "")
    if action == "confirm":
        key = _require_key(key)
        scope = f"feature:{account['id']}:{feature}:confirm"
        if prior := _idempotency(scope, key):
            return prior
    if action == "confirm" and not _flags()["provider_calls_enabled"]:
        return envelope(False, "Tính năng đang ở chế độ an toàn và chưa gọi engine từ Web.", status_name="guarded", error_code="WEBAPP_PROVIDER_CALLS_DISABLED")
    values["idempotency_key"] = key if key else None
    result = await _bridge("POST", f"/internal/v1/features/{feature}/{action}", account=account, request=request, payload=values)
    if action == "confirm":
        _remember_idempotency(scope, key, result)
    return result


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
async def admin_summary(request: Request, account: dict = Depends(require_admin)):
    return await _bridge("GET", "/internal/v1/admin/summary", account=account, request=request)


@router.get("/admin/users")
async def admin_users(request: Request, account: dict = Depends(require_admin)):
    return await _bridge("GET", "/internal/v1/admin/users", account=account, request=request)


@router.get("/admin/jobs")
async def admin_jobs(request: Request, account: dict = Depends(require_admin)):
    return await _bridge("GET", "/internal/v1/admin/jobs", account=account, request=request)


@router.get("/admin/payments")
async def admin_payments(request: Request, account: dict = Depends(require_admin)):
    return await _bridge("GET", "/internal/v1/admin/payments", account=account, request=request)


@router.get("/admin/providers")
async def admin_providers(request: Request, account: dict = Depends(require_admin)):
    return await _bridge("GET", "/internal/v1/admin/providers", account=account, request=request)


@router.get("/admin/tickets")
async def admin_tickets(request: Request, account: dict = Depends(require_admin)):
    return await _bridge("GET", "/internal/v1/admin/tickets", account=account, request=request)


@router.post("/admin/jobs/{job_id}/retry")
async def admin_retry_job(job_id: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_admin_csrf)):
    key = _require_key(payload.idempotency_key or request.headers.get("Idempotency-Key", ""))
    return await _bridge("POST", f"/internal/v1/admin/jobs/{job_id}/retry", account=account, request=request, payload={"idempotency_key": key})


@router.post("/admin/jobs/{job_id}/refund")
async def admin_refund_job(job_id: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_admin_csrf)):
    key = _require_key(payload.idempotency_key or request.headers.get("Idempotency-Key", ""))
    return await _bridge("POST", f"/internal/v1/admin/jobs/{job_id}/refund", account=account, request=request, payload={"idempotency_key": key})


@router.post("/admin/features/{feature}/freeze")
async def admin_freeze_feature(feature: str, payload: FreezeRequest, request: Request, account: dict = Depends(require_admin_csrf)):
    key = _require_key(payload.idempotency_key)
    return await _bridge("POST", f"/internal/v1/admin/features/{feature}/freeze", account=account, request=request, payload={"frozen": payload.frozen, "note": payload.note, "idempotency_key": key})
