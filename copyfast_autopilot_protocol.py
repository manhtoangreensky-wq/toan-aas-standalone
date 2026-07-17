"""Small, dependency-free protocol shared by the Operations Cron and API.

This module intentionally contains no database, FastAPI, Bot, bridge,
provider, wallet or payment integration.  It gives the later internal tick
endpoint and its short-lived Railway Cron invoker one exact HMAC format so a
change cannot silently weaken authentication on either side.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any


TICK_METHOD = "POST"
TICK_PATH = "/internal/v1/operations/tick"
PROTOCOL_VERSION = 1
NONCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
REQUEST_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
KEY_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


def canonical_json(value: dict[str, Any]) -> bytes:
    """Return the only supported UTF-8 serialization for signed tick bodies."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def body_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def signature_material(
    *, method: str, path: str, timestamp: str, nonce: str, request_id: str, key_id: str, body: bytes,
) -> bytes:
    normalized_method = str(method or "").upper()
    normalized_path = str(path or "")
    normalized_timestamp = str(timestamp or "")
    normalized_nonce = str(nonce or "")
    normalized_request_id = str(request_id or "").lower()
    normalized_key_id = str(key_id or "").strip().lower()
    if normalized_method != TICK_METHOD or normalized_path != TICK_PATH:
        raise ValueError("Internal tick method hoặc path không hợp lệ")
    if (
        not normalized_timestamp
        or not NONCE_PATTERN.fullmatch(normalized_nonce)
        or not valid_request_id(normalized_request_id)
        or not KEY_ID_PATTERN.fullmatch(normalized_key_id)
    ):
        raise ValueError("Internal tick timestamp, nonce, request ID hoặc key ID không hợp lệ")
    # Bind every audit/idempotency header to the signature.  Without this, an
    # intermediary could change the request ID or key label while leaving a
    # valid body signature intact.
    return "\n".join((
        normalized_method, normalized_path, normalized_timestamp, normalized_nonce,
        normalized_request_id, normalized_key_id, body_sha256(body),
    )).encode("utf-8")


def sign_tick(*, secret: str, timestamp: str, nonce: str, request_id: str, key_id: str, body: bytes) -> str:
    key = str(secret or "").encode("utf-8")
    if len(key) < 32:
        raise ValueError("WEBAPP_AUTOPILOT_TICK_SECRET phải có ít nhất 32 ký tự")
    return hmac.new(
        key,
        signature_material(
            method=TICK_METHOD, path=TICK_PATH, timestamp=timestamp, nonce=nonce,
            request_id=request_id, key_id=key_id, body=body,
        ),
        hashlib.sha256,
    ).hexdigest()


def valid_request_id(value: str) -> bool:
    return bool(REQUEST_ID_PATTERN.fullmatch(str(value or "")))
