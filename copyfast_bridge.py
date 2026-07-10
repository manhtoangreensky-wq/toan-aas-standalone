"""Server-side client for the private Telegram-bot core bridge.

No browser receives a provider credential, a bridge secret, a provider task id,
or a raw exception.  When the bridge is absent, callers get a guarded response
instead of a locally fabricated result.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any

import httpx


PUBLIC_GUARD = "Hệ thống đang bảo trì/nâng cấp. TOAN AAS chưa xử lý và chưa trừ Xu. Vui lòng thử lại sau."


def envelope(ok: bool, message: str, *, data: dict | None = None, status_name: str = "completed", error_code: str | None = None) -> dict:
    return {"ok": ok, "status": status_name, "message": message, "data": data or {}, "error_code": error_code}


def _base_url() -> str:
    return os.environ.get("CORE_BRIDGE_BASE_URL", "").strip().rstrip("/")


def _token() -> str:
    return os.environ.get("CORE_BRIDGE_TOKEN", "").strip()


def _hmac_secret() -> str:
    return os.environ.get("CORE_BRIDGE_HMAC_SECRET", "").strip()


def bridge_configured() -> bool:
    return bool(_base_url() and _token() and _hmac_secret())


def _safe_error_code(status_code: int) -> str:
    if status_code == 401:
        return "CORE_BRIDGE_UNAUTHORIZED"
    if status_code == 403:
        return "CORE_BRIDGE_FORBIDDEN"
    if status_code == 404:
        return "CORE_BRIDGE_NOT_AVAILABLE"
    if status_code == 429:
        return "CORE_BRIDGE_RATE_LIMITED"
    return "CORE_BRIDGE_UNAVAILABLE"


class CoreBridgeClient:
    def __init__(self, *, base_url: str | None = None, token: str | None = None, hmac_secret: str | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = (base_url if base_url is not None else _base_url()).rstrip("/")
        self.token = token if token is not None else _token()
        self.hmac_secret = hmac_secret if hmac_secret is not None else _hmac_secret()
        self.transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token and self.hmac_secret)

    def _headers(self, method: str, path: str, body: bytes, *, request_id: str, actor_id: str = "") -> dict[str, str]:
        timestamp = str(int(time.time()))
        digest = hashlib.sha256(body).hexdigest()
        message = f"{timestamp}.{request_id}.{method.upper()}.{path}.{digest}".encode("utf-8")
        signature = hmac.new(self.hmac_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-TOAN-AAS-Timestamp": timestamp,
            "X-TOAN-AAS-Request-ID": request_id,
            "X-TOAN-AAS-Signature": signature,
            "Accept": "application/json",
        }
        if actor_id:
            headers["X-TOAN-AAS-Actor-ID"] = actor_id[:128]
        if body:
            headers["Content-Type"] = "application/json"
        return headers

    async def request(self, method: str, path: str, *, payload: dict | None = None, params: dict | None = None, request_id: str | None = None, actor_id: str = "") -> dict:
        if not self.configured:
            return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_NOT_CONFIGURED")
        normalized_path = "/" + path.lstrip("/")
        request_id = request_id or str(uuid.uuid4())
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8") if payload is not None else b""
        headers = self._headers(method, normalized_path, body, request_id=request_id, actor_id=actor_id)
        # Retrying an unsafe write could create a duplicate payment, credit or
        # job. GET is safe to retry; POST is retried only when callers supply
        # the canonical idempotency key enforced by both bridge layers.
        retry_safe = method.upper() == "GET" or bool((payload or {}).get("idempotency_key"))
        attempts = 2 if retry_safe else 1
        response: httpx.Response | None = None
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(12.0, connect=4.0), transport=self.transport) as client:
                    response = await client.request(method.upper(), normalized_path, content=body or None, params=params, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError):
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05)
                    continue
                return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_UNAVAILABLE")
            if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                await asyncio.sleep(0.05)
                continue
            break
        if response is None:
            return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_UNAVAILABLE")
        try:
            data: Any = response.json()
        except ValueError:
            data = None
        if response.status_code >= 400:
            if isinstance(data, dict) and {"ok", "status", "message"}.issubset(data):
                return _sanitize_envelope(data, fallback_code=_safe_error_code(response.status_code))
            return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code=_safe_error_code(response.status_code))
        if not isinstance(data, dict):
            return envelope(False, PUBLIC_GUARD, status_name="failed", error_code="CORE_BRIDGE_INVALID_RESPONSE")
        return _sanitize_envelope(data)


def _sanitize_envelope(value: dict, *, fallback_code: str | None = None) -> dict:
    """Keep bridge contract while preventing raw/debug keys from escaping."""
    safe_data = value.get("data") if isinstance(value.get("data"), dict) else {}
    forbidden = {"token", "secret", "api_key", "authorization", "traceback", "stack", "output_path", "filesystem_path", "provider_task_id", "raw_response"}
    filtered = {key: item for key, item in safe_data.items() if key.lower() not in forbidden}
    status_name = str(value.get("status") or "failed")
    allowed_statuses = {"draft", "awaiting_confirm", "queued", "processing", "completed", "failed", "failed_no_charge", "guarded", "cancelled", "refunded", "read_only"}
    if status_name not in allowed_statuses:
        status_name = "failed"
    return envelope(
        bool(value.get("ok")),
        str(value.get("message") or ("Hoàn tất" if value.get("ok") else PUBLIC_GUARD))[:500],
        data=filtered,
        status_name=status_name,
        error_code=str(value.get("error_code") or fallback_code or "") or None,
    )


async def bridge_request(method: str, path: str, *, payload: dict | None = None, params: dict | None = None, request_id: str | None = None, actor_id: str = "") -> dict:
    return await CoreBridgeClient().request(method, path, payload=payload, params=params, request_id=request_id, actor_id=actor_id)
