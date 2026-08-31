"""Server-side client for the private Telegram-bot core bridge.

No browser receives a provider credential, a bridge secret, a provider task id,
or a raw exception.  When the bridge is absent, callers get a guarded response
instead of a locally fabricated result.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

import anyio
import httpx


PUBLIC_GUARD = "Hệ thống đang bảo trì/nâng cấp. TOAN AAS chưa xử lý và chưa trừ Xu. Vui lòng thử lại sau."
_MAX_SAFE_DATA_DEPTH = 6
_MAX_SAFE_DATA_ITEMS = 80
_MAX_SAFE_STRING_LENGTH = 4_000
_ASSET_DELIVERY_ROUTE_RE = re.compile(r"^/internal/v1/assets/[^/]+/download$")
_TELEGRAM_OWNER_ID_RE = re.compile(r"^[1-9][0-9]{0,19}$")
_MANUAL_ADMIN_PATH_RE = re.compile(
    r"^/internal/v1/admin/payments/manual"
    r"(?:/MANUAL-[1-9][0-9]{0,18}(?:/(?:draft|confirm))?)?$"
)
_SENSITIVE_KEY_PARTS = frozenset({
    "token", "secret", "apikey", "authorization", "signature", "traceback", "stack",
    "outputpath", "filesystempath", "providertask", "rawresponse", "privatekey",
    "password", "cookie", "telegramfileid",
})
_REQUIRED_BRIDGE_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def envelope(ok: bool, message: str, *, data: Any = None, status_name: str = "completed", error_code: str | None = None) -> dict:
    return {"ok": ok, "status": status_name, "message": message, "data": {} if data is None else data, "error_code": error_code}


def _base_url() -> str:
    return os.environ.get("CORE_BRIDGE_BASE_URL", "").strip().rstrip("/")


def _token() -> str:
    return os.environ.get("CORE_BRIDGE_TOKEN", "").strip()


def _hmac_secret() -> str:
    return os.environ.get("CORE_BRIDGE_HMAC_SECRET", "").strip()


def _valid_base_url(value: str) -> bool:
    """Accept only a root HTTPS origin for the server-to-server bridge.

    The bridge signs requests with its bearer credential, so accepting a
    loosely shaped URL here could send that credential to an unintended
    location.  Keep the contract deliberately small: the canonical bridge is
    a secure origin and the request path is supplied separately below.
    """
    if not value or any(character.isspace() for character in value):
        return False
    try:
        parsed = urlsplit(value)
        # Accessing ``port`` validates malformed port strings too.
        _ = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme.lower() == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


def _configuration_error(base_url: str, token: str, hmac_secret: str) -> str | None:
    if not base_url or not token or not hmac_secret:
        return "CORE_BRIDGE_NOT_CONFIGURED"
    if not _valid_base_url(base_url):
        return "CORE_BRIDGE_INVALID_CONFIGURATION"
    return None


def bridge_configured() -> bool:
    return _configuration_error(_base_url(), _token(), _hmac_secret()) is None


def core_bridge_required() -> bool:
    """Whether this deployment explicitly opts into canonical bridge readiness."""
    return os.environ.get("WEBAPP_REQUIRE_CORE_BRIDGE", "").strip().lower() in _REQUIRED_BRIDGE_TRUE_VALUES


def ensure_core_bridge_readiness() -> None:
    """Fail startup only for an explicit release-readiness opt-in.

    Do not include a URL or credential-derived detail in this error: process
    startup logs are often retained more broadly than application secrets.
    """
    if core_bridge_required() and not bridge_configured():
        raise RuntimeError("WEBAPP_REQUIRE_CORE_BRIDGE requires a valid canonical Core Bridge configuration")


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
        return self.configuration_error is None

    @property
    def configuration_error(self) -> str | None:
        return _configuration_error(self.base_url, self.token, self.hmac_secret)

    def _headers(self, method: str, path: str, body: bytes, *, request_id: str, actor_id: str = "", owner_id: str = "") -> dict[str, str]:
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
        if owner_id:
            headers["X-TOAN-AAS-Telegram-User-ID"] = owner_id
        if body:
            headers["Content-Type"] = "application/json"
        return headers

    async def request(self, method: str, path: str, *, payload: dict | None = None, params: dict | None = None, request_id: str | None = None, actor_id: str = "", owner_id: str = "") -> dict:
        configuration_error = self.configuration_error
        if configuration_error:
            return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code=configuration_error)
        if owner_id and _TELEGRAM_OWNER_ID_RE.fullmatch(owner_id) is None:
            return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_OWNER_INVALID")
        normalized_path = "/" + path.lstrip("/")
        # ``request_id`` is a public Web correlation value.  The bot treats
        # X-TOAN-AAS-Request-ID as an HMAC nonce, so reusing a browser-supplied
        # value (or reusing it for a retry) makes the canonical bridge reject
        # a legitimate retry as a replay.  Keep the caller-facing argument for
        # API compatibility, but mint an opaque server-side nonce per attempt.
        _ = request_id
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8") if payload is not None else b""
        # Retrying an unsafe write could create a duplicate payment, credit or
        # job. Most read-only GETs are safe to retry, but an asset download GET
        # can mint a fresh short-lived signed delivery URL and write an audit
        # decision in the canonical Bot. Treat that route as a credential
        # issuance boundary rather than an idempotent read. POST is retried
        # only when callers supply the canonical idempotency key enforced by
        # both bridge layers.
        retry_safe = (
            (method.upper() == "GET" and not _ASSET_DELIVERY_ROUTE_RE.fullmatch(normalized_path))
            or bool((payload or {}).get("idempotency_key"))
        )
        attempts = 2 if retry_safe else 1
        response: httpx.Response | None = None
        for attempt in range(attempts):
            try:
                bridge_request_id = str(uuid.uuid4())
                headers = self._headers(
                    method,
                    normalized_path,
                    body,
                    request_id=bridge_request_id,
                    actor_id=actor_id,
                    owner_id=owner_id,
                )
                async with httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(12.0, connect=4.0), transport=self.transport) as client:
                    response = await client.request(method.upper(), normalized_path, content=body or None, params=params, headers=headers)
            except (httpx.HTTPError, httpx.InvalidURL, ValueError):
                # Invalid URLs and client/request construction errors must
                # stay on the same public guard as connectivity failures.  In
                # particular, never interpolate a URL, request, or exception:
                # either may contain the configured bridge credential.
                if attempt + 1 < attempts:
                    await anyio.sleep(0.05)
                    continue
                return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_UNAVAILABLE")
            if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                await anyio.sleep(0.05)
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


def _sensitive_key(value: object) -> bool:
    normalized = "".join(character for character in str(value).lower() if character.isalnum())
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _sanitize_data(value: Any, *, depth: int = 0) -> Any:
    """Recursively remove bridge/runtime details which never belong in a browser.

    Bridge payloads contain nested job and provider structures in several bot
    workflows.  Filtering only the top-level keys accidentally exposed nested
    provider task IDs, filesystem paths, raw responses and credentials.  Keep
    the public envelope flexible, but bound it and redact those values at every
    level before it crosses the Web boundary.
    """
    if depth > _MAX_SAFE_DATA_DEPTH:
        return "[Dữ liệu lồng quá sâu đã được ẩn]"
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= _MAX_SAFE_DATA_ITEMS:
                break
            if _sensitive_key(key):
                continue
            result[str(key)[:160]] = _sanitize_data(item, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [_sanitize_data(item, depth=depth + 1) for item in value[:_MAX_SAFE_DATA_ITEMS]]
    if isinstance(value, str):
        return value[:_MAX_SAFE_STRING_LENGTH]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    # Do not stringify arbitrary provider/runtime objects: their repr may
    # contain credentials or internal paths.
    return None


def _sanitize_envelope(value: dict, *, fallback_code: str | None = None) -> dict:
    """Keep bridge contract while preventing raw/debug keys from escaping."""
    raw_data = value.get("data")
    if not isinstance(raw_data, (dict, list)):
        raw_data = {}
    safe_data = _sanitize_data(raw_data)
    if not isinstance(safe_data, (dict, list)):
        safe_data = {}
    status_name = str(value.get("status") or "failed")
    allowed_statuses = {"draft", "awaiting_confirm", "queued", "processing", "completed", "failed", "failed_no_charge", "guarded", "cancelled", "refunded", "read_only", "pending_admin_review", "approved", "rejected"}
    if status_name not in allowed_statuses:
        status_name = "failed"
    return envelope(
        bool(value.get("ok")),
        str(value.get("message") or ("Hoàn tất" if value.get("ok") else PUBLIC_GUARD))[:500],
        data=safe_data,
        status_name=status_name,
        error_code=str(value.get("error_code") or fallback_code or "") or None,
    )


async def bridge_request(method: str, path: str, *, payload: dict | None = None, params: dict | None = None, request_id: str | None = None, actor_id: str = "", owner_id: str = "") -> dict:
    return await CoreBridgeClient().request(method, path, payload=payload, params=params, request_id=request_id, actor_id=actor_id, owner_id=owner_id)


def _manual_admin_token() -> str:
    return os.environ.get("INTERNAL_MANUAL_ADMIN_TOKEN", "").strip()


def _bridge_header_token(value: str) -> bytes | None:
    """Return one bounded printable ASCII bearer value, otherwise fail closed."""

    if not isinstance(value, str) or not 12 <= len(value) <= 4_096 or not value.isascii():
        return None
    if any(character.isspace() or ord(character) < 33 or ord(character) > 126 for character in value):
        return None
    return value.encode("ascii")


def manual_admin_bridge_configured() -> bool:
    """Check the Admin-scoped capability without exposing a configuration reason."""

    admin_token = _manual_admin_token()
    owner_token = _token()
    admin_bytes = _bridge_header_token(admin_token)
    owner_bytes = _bridge_header_token(owner_token) if owner_token else None
    if admin_bytes is None:
        return False
    if owner_bytes is not None and hmac.compare_digest(admin_bytes, owner_bytes):
        return False
    return _configuration_error(_base_url(), admin_token, _hmac_secret()) is None


def _manual_admin_bridge_route_allowed(method: str, path: str) -> bool:
    if _MANUAL_ADMIN_PATH_RE.fullmatch(path) is None:
        return False
    upper = method.upper()
    if upper == "GET":
        return not path.endswith(("/draft", "/confirm"))
    if upper == "POST":
        return path.endswith(("/draft", "/confirm"))
    return False


async def manual_admin_bridge_request(
    method: str,
    path: str,
    *,
    admin_id: str,
    payload: dict | None = None,
    params: dict | None = None,
    request_id: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[dict, str]:
    """Call the private manual-payment Admin bridge with a separate credential.

    The second tuple item is populated only for a valid draft response.  It is
    consumed by the server-side Web receipt vault and must never cross into a
    browser envelope.
    """

    if not manual_admin_bridge_configured():
        return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_ADMIN_NOT_CONFIGURED"), ""
    if _TELEGRAM_OWNER_ID_RE.fullmatch(str(admin_id or "")) is None:
        return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_ADMIN_INVALID"), ""
    normalized_path = "/" + str(path or "").lstrip("/")
    if not _manual_admin_bridge_route_allowed(method, normalized_path):
        return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_ADMIN_ROUTE_INVALID"), ""

    try:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8") if payload is not None else b""
    except (TypeError, ValueError):
        return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_INVALID_PAYLOAD"), ""

    admin_token = _manual_admin_token()
    hmac_secret = _hmac_secret()
    base_url = _base_url()
    response: httpx.Response | None = None
    # All four operations are safe to retry with identical input: GET and
    # draft are read-only; confirm is idempotent by its signed Bot token.
    for attempt in range(2):
        bridge_request_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        digest = hashlib.sha256(body).hexdigest()
        material = f"{timestamp}.{bridge_request_id}.{method.upper()}.{normalized_path}.{digest}".encode("utf-8")
        signature = hmac.new(hmac_secret.encode("utf-8"), material, hashlib.sha256).hexdigest()
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-TOAN-AAS-Timestamp": timestamp,
            "X-TOAN-AAS-Request-ID": bridge_request_id,
            "X-TOAN-AAS-Signature": signature,
            "X-TOAN-AAS-Admin-ID": str(admin_id),
            "Accept": "application/json",
        }
        if body:
            headers["Content-Type"] = "application/json"
        try:
            async with httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(12.0, connect=4.0),
                transport=transport,
            ) as client:
                response = await client.request(
                    method.upper(), normalized_path, content=body or None, params=params, headers=headers
                )
        except (httpx.HTTPError, httpx.InvalidURL, ValueError):
            if attempt == 0:
                await anyio.sleep(0.05)
                continue
            return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_UNAVAILABLE"), ""
        if response.status_code in {502, 503, 504} and attempt == 0:
            await anyio.sleep(0.05)
            continue
        break

    if response is None:
        return envelope(False, PUBLIC_GUARD, status_name="guarded", error_code="CORE_BRIDGE_UNAVAILABLE"), ""
    try:
        source: Any = response.json()
    except ValueError:
        source = None
    if not isinstance(source, dict):
        return envelope(False, PUBLIC_GUARD, status_name="failed", error_code="CORE_BRIDGE_INVALID_RESPONSE"), ""

    private_token = ""
    public_source = dict(source)
    raw_data = source.get("data")
    if isinstance(raw_data, dict):
        public_data = dict(raw_data)
        candidate = public_data.pop("confirmation_token", "")
        public_source["data"] = public_data
        if normalized_path.endswith("/draft") and source.get("ok") is True and source.get("status") == "awaiting_confirm":
            if (
                isinstance(candidate, str)
                and 32 <= len(candidate) <= 4_096
                and candidate.count(".") == 1
                and candidate.isascii()
            ):
                private_token = candidate

    sanitized = _sanitize_envelope(
        public_source,
        fallback_code=_safe_error_code(response.status_code) if response.status_code >= 400 else None,
    )
    return sanitized, private_token
