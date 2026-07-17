"""Invoke one signed Inbox Automation tick and exit.

Designed for an isolated Railway Cron service.  It never opens the Web SQLite
database, imports the Web app/Bot, sends a notification, calls a provider, or
changes a reminder/source record.  Its only capability is a signed request to
materialize permitted private in-app inbox metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copyfast_notification_protocol import PROTOCOL_VERSION, TICK_METHOD, TICK_PATH, canonical_json, sign_tick  # noqa: E402


MAX_RUN_SECONDS = 25
TRANSPORT_GRACE_SECONDS = 5.0
MAX_RESPONSE_BYTES = 128 * 1024
KEY_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


class TickConfigurationError(RuntimeError):
    """Safe configuration failure for the one-shot Inbox runner."""


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802 - stdlib callback
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _timeout() -> float:
    raw = os.environ.get("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS", "20").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise TickConfigurationError("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS không hợp lệ") from exc
    if value < 1 or value > MAX_RUN_SECONDS:
        raise TickConfigurationError("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS phải từ 1 đến 25")
    return float(value) + TRANSPORT_GRACE_SECONDS


def _allow_local_http() -> bool:
    return os.environ.get("WEBAPP_NOTIFICATION_ALLOW_INSECURE_LOCAL", "").strip().lower() in {"1", "true", "yes", "on"}


def _origin(value: str, *, label: str) -> tuple[str, str, int | None]:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise TickConfigurationError(f"{label} có port không hợp lệ") from exc
    if (
        not value or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.path not in {"", "/"} or not parsed.hostname
    ):
        raise TickConfigurationError(f"{label} phải là origin thuần, không userinfo/query/path")
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()
    if scheme == "https":
        if port not in {None, 443}:
            raise TickConfigurationError(f"{label} không chấp nhận HTTPS port không chuẩn")
    elif not (_allow_local_http() and scheme == "http" and hostname in {"127.0.0.1", "localhost", "::1"}):
        raise TickConfigurationError("Notification tick chỉ dùng HTTPS; HTTP chỉ được phép cho localhost test rõ ràng")
    return scheme, hostname, port


def _tick_url() -> str:
    raw = os.environ.get("WEBAPP_NOTIFICATION_TICK_URL", "").strip()
    pinned = os.environ.get("WEBAPP_NOTIFICATION_TICK_ORIGIN", "").strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise TickConfigurationError("WEBAPP_NOTIFICATION_TICK_URL có port không hợp lệ") from exc
    if (
        not raw or parsed.username or parsed.password or parsed.path != TICK_PATH
        or parsed.query or parsed.fragment or not parsed.hostname
    ):
        raise TickConfigurationError("WEBAPP_NOTIFICATION_TICK_URL phải trỏ chính xác tới internal notification tick")
    expected_scheme, expected_host, expected_port = _origin(pinned, label="WEBAPP_NOTIFICATION_TICK_ORIGIN")
    if (parsed.scheme.lower(), parsed.hostname.lower(), port) != (expected_scheme, expected_host, expected_port):
        raise TickConfigurationError("WEBAPP_NOTIFICATION_TICK_URL không khớp origin Inbox đã pin")
    return raw


def _secret() -> str:
    value = os.environ.get("WEBAPP_NOTIFICATION_TICK_SECRET", "")
    if len(value.encode("utf-8")) < 32:
        raise TickConfigurationError("WEBAPP_NOTIFICATION_TICK_SECRET chưa được cấu hình đủ mạnh")
    return value


def _key_id() -> str:
    value = os.environ.get("WEBAPP_NOTIFICATION_TICK_KEY_ID", "primary").strip().lower()
    if not KEY_ID_PATTERN.fullmatch(value):
        raise TickConfigurationError("WEBAPP_NOTIFICATION_TICK_KEY_ID không hợp lệ")
    return value


def _opener():
    return build_opener(ProxyHandler({}), _RejectRedirect())


def build_request() -> tuple[str, Request, str]:
    url = _tick_url()
    secret = _secret()
    key_id = _key_id()
    timestamp = _utc_now()
    nonce = secrets.token_urlsafe(32)
    request_id = str(uuid.uuid4())
    body = canonical_json({"protocol_version": PROTOCOL_VERSION, "trigger": "railway_cron", "requested_at": timestamp})
    signature = sign_tick(secret=secret, timestamp=timestamp, nonce=nonce, request_id=request_id, key_id=key_id, body=body)
    request = Request(
        url,
        data=body,
        method=TICK_METHOD,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Notify-Timestamp": timestamp,
            "X-Notify-Nonce": nonce,
            "X-Notify-Request-Id": request_id,
            "X-Notify-Signature": signature,
            "X-Notify-Key-Id": key_id,
        },
    )
    return url, request, request_id


def invoke_once() -> dict[str, object]:
    _url, request, request_id = build_request()
    try:
        with _opener().open(request, timeout=_timeout()) as response:  # nosec B310 - configuration origin is pinned above
            status = int(response.getcode())
            content_type = str(response.headers.get("Content-Type", "")).lower()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise RuntimeError(f"Inbox tick bị Web service từ chối (HTTP {int(exc.code)})") from exc
    except URLError as exc:
        raise RuntimeError("Không kết nối được Web service Inbox tick") from exc
    if status != 200 or len(raw) > MAX_RESPONSE_BYTES or "application/json" not in content_type:
        raise RuntimeError("Phản hồi Inbox tick không đúng contract an toàn")
    try:
        response = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Phản hồi Inbox tick không phải JSON hợp lệ") from exc
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError("Inbox tick không xác nhận hoàn tất")
    status_name = str(response.get("status", ""))
    if status_name not in {"completed", "guarded", "read_only"}:
        raise RuntimeError("Inbox tick trả trạng thái không an toàn")
    receipt = response.get("data")
    if not isinstance(receipt, dict) or receipt.get("request_id") != request_id:
        raise RuntimeError("Phản hồi Inbox không khớp request đã ký")
    return {"ok": True, "status": status_name, "request_id": request_id}


def main() -> int:
    try:
        receipt = invoke_once()
    except TickConfigurationError as exc:
        print(json.dumps({"ok": False, "error": "configuration", "message": str(exc)}, ensure_ascii=False))
        return 2
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": "tick_failed", "message": str(exc)}, ensure_ascii=False))
        return 3
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
