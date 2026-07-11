"""Authenticated Web API that adapts the private bot core to the portal."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
import re
import uuid
from io import BytesIO
from typing import Any
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from copyfast_auth import (
    _record_audit,
    envelope,
    require_account,
    require_canonical_admin,
    require_canonical_admin_csrf,
    require_admin_csrf,
    require_csrf,
)
from copyfast_bridge import bridge_configured, bridge_request
from copyfast_db import ensure_copyfast_schema, transaction, utc_now
from copyfast_registry import FEATURE_BY_KEY, catalog


router = APIRouter(prefix="/api/v1", tags=["COPYFAST Core"])
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
TELEGRAM_BOT_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{5,32}$")
CANONICAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
CONTIGUOUS_PAGE_RANGE_PATTERN = re.compile(r"^\d+(?:-\d+)?$")
TICKET_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)"
    r"\b\s*(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
TICKET_BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE)
TICKET_KEY_PATTERN = re.compile(r"\b(?:sk|pk|rk)_[A-Za-z0-9_-]{16,}\b", re.IGNORECASE)
TICKET_VERIFICATION_PATTERN = re.compile(
    r"\b(?:otp|mã\s*xác\s*thực|ma\s*xac\s*thuc|cvv|cvc)\s*[:=]?\s*\d{3,8}\b",
    re.IGNORECASE,
)
TICKET_CARD_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
MAX_FEATURE_UPLOADS = 8
IDEMPOTENCY_PENDING_SECONDS = 90
_PENDING_IDEMPOTENCY_KEY = "_web_idempotency_pending"
_RETRYABLE_BRIDGE_CODES = frozenset({"CORE_BRIDGE_UNAVAILABLE", "CORE_BRIDGE_RATE_LIMITED", "CORE_BRIDGE_NOT_CONFIGURED"})
UPLOAD_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm",
    ".mp3", ".wav", ".m4a", ".ogg", ".pdf", ".txt", ".srt", ".vtt", ".docx",
})
UPLOAD_CANONICAL_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg",
    ".pdf": "application/pdf", ".txt": "text/plain", ".srt": "application/x-subrip", ".vtt": "text/vtt",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
UPLOAD_ACCEPTED_MIME_BY_EXTENSION = {
    ".jpg": frozenset({"image/jpeg"}), ".jpeg": frozenset({"image/jpeg"}),
    ".png": frozenset({"image/png"}), ".webp": frozenset({"image/webp"}),
    ".mp4": frozenset({"video/mp4"}), ".mov": frozenset({"video/quicktime"}),
    ".webm": frozenset({"video/webm"}), ".mp3": frozenset({"audio/mpeg"}),
    ".wav": frozenset({"audio/wav", "audio/x-wav"}), ".m4a": frozenset({"audio/mp4"}),
    ".ogg": frozenset({"audio/ogg", "application/ogg"}), ".pdf": frozenset({"application/pdf"}),
    ".txt": frozenset({"text/plain"}), ".srt": frozenset({"application/x-subrip", "text/plain"}),
    ".vtt": frozenset({"text/vtt", "text/plain"}),
    ".docx": frozenset({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
}
TEXT_UPLOAD_EXTENSIONS = frozenset({".txt", ".srt", ".vtt"})
MAX_DOCX_ARCHIVE_MEMBERS = 2_000
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
ASSET_DELIVERY_MAX_URL_LENGTH = 2_048
ASSET_DELIVERY_MAX_TTL_SECONDS = 60 * 60

# Browser forms must never be able to attach a value that looks like a bot
# authority decision.  Identity, provider settings, wallet/payment fields,
# job lifecycle and output/delivery metadata belong to the canonical Bot only.
# This is deliberately a deny-list of authority fields, not a provider schema:
# normal product metadata can still evolve through the private bridge.
FEATURE_AUTHORITY_FIELDS = frozenset({
    "user_id", "canonical_user_id", "telegram_id", "chat_id", "account_id", "wallet_id",
    "balance", "balance_xu", "credit", "credits", "xu", "charged_xu", "estimated_xu",
    "amount", "amount_vnd", "price", "cost", "currency", "payment_id", "order_code",
    "checkout_url", "webhook", "provider", "provider_id", "api_key", "api_token", "token",
    "secret", "job_id", "job_status", "status", "output", "output_url", "asset_id", "download_url",
})
FEATURE_AUTHORITY_FIELDS_NORMALIZED = frozenset(
    "".join(character for character in field.lower() if character.isalnum())
    for field in FEATURE_AUTHORITY_FIELDS
)
FEATURE_TEXT_KEYS = ("request", "prompt", "brief", "script", "text", "topic", "description", "instructions", "notes")
FEATURE_TEXT_REQUIRED = frozenset({
    "chat", "prompt_studio", "caption", "hashtag", "hook", "script", "storyboard", "content_pack",
    "image_create", "image_transform", "video_single", "video_product", "video_trend",
    "video_text_to_video", "video_quick", "video_image_to_video", "video_multiscene", "video_long",
    "voice_tts", "voice_saved_tts", "music_background", "music_song", "music_sfx",
})
FEATURE_UPLOAD_REQUIRED = frozenset({
    "image_edit", "image_upscale", "image_transform", "image_remove_background", "video_image_to_video",
    "voice_clone", "music_upload", "subtitle_asr", "subtitle_create", "asr", "subtitle_translate",
    "video_dub", "documents", "documents_pdf", "documents_ocr", "documents_merge", "documents_split",
    "documents_compress", "documents_translate",
})
FEATURE_TARGET_LANGUAGE_REQUIRED = frozenset({"subtitle_translate", "video_dub", "documents_translate"})
CANONICAL_TARGET_LANGUAGE_CODES = frozenset({
    "vi", "en", "zh", "zh_cn", "zh_tw", "ja", "ko", "th", "fr", "de", "es",
    "id", "ms", "pt", "ru", "ar", "hi", "lo", "km", "my", "fil", "auto",
})
MUSIC_PROMPT_MODES = frozenset({"background", "lyrics", "script", "melody", "custom"})
MUSIC_SONG_LENGTH_MODES = frozenset({"seconds", "half", "full"})
# The canonical Telegram identity is an internal bridge routing key, not
# browser-facing profile metadata.  Redact it consistently from every bridge
# response, including nested wallet and admin structures.
BROWSER_IDENTITY_KEY_NORMALIZED = frozenset({
    "userid", "canonicaluserid", "telegramid", "chatid", "username", "telegramusername",
})
BROWSER_PRIVATE_KEY_NORMALIZED = frozenset({
    "email", "emailaddress", "phone", "phonenumber", "mobile", "address", "bank", "bankaccount",
    "accountnumber", "accountname", "qrcode", "qr", "txid", "transactionid", "receipt", "bill",
    "paymentproof", "cardnumber", "cvv", "cvc", "otp", "authorization", "cookie", "password",
    "secret", "token", "apikey", "rawresponse", "traceback", "stack", "filesystempath", "outputpath",
    "provider", "providertask", "providerid", "telegramfileid", "fileid", "checkouturl", "paymenturl",
    "downloadurl", "outputurl", "publicurl",
})
BROWSER_PRIVATE_KEY_PARTS = (
    "email", "phone", "mobile", "address", "bank", "txid", "transaction", "receipt", "bill", "card",
    "cvv", "cvc", "otp", "authorization", "cookie", "password", "secret", "token", "apikey", "provider",
    "telegramfile", "fileid", "checkouturl", "paymenturl", "downloadurl", "outputurl", "publicurl", "filesystem",
    "outputpath", "rawresponse", "traceback", "stack",
)
# Feature planning results are intentionally rich enough to render a
# provider-free draft/estimate, but they are not a delivery channel.  Keep a
# stricter field policy for this surface than the generic bridge redactor so
# a future Bot adapter cannot accidentally put an output, a signed URL, a
# job/provider handle, or payment/ledger metadata inside a planning object.
FEATURE_RESPONSE_PRIVATE_KEY_PARTS = (
    "url", "uri", "link", "path", "file", "attachment", "media", "artifact", "preview",
    "output", "delivery", "download", "job", "provider", "payment", "checkout", "invoice",
    "wallet", "ledger", "transaction", "refund", "charge", "webhook", "token", "secret",
    "signature", "nonce", "session", "cookie", "password", "email", "phone", "address",
    "telegram", "canonicaluser", "chatid", "accountid", "userid", "bank", "card", "otp",
)
_PUBLIC_BRIDGE_STATUSES = frozenset({
    "draft", "awaiting_confirm", "queued", "processing", "completed", "failed", "failed_no_charge",
    "guarded", "cancelled", "refunded", "read_only",
})
_PUBLIC_BRIDGE_MESSAGES = {
    "draft": "Bản nháp canonical đã được cập nhật.",
    "awaiting_confirm": "Dữ liệu canonical đang chờ bước xác nhận phù hợp.",
    "queued": "Yêu cầu đã được canonical queue ghi nhận.",
    "processing": "Core Bridge đang cập nhật trạng thái canonical.",
    "completed": "Dữ liệu canonical đã được cập nhật.",
    "failed": "Core Bridge chưa thể cấp dữ liệu an toàn.",
    "failed_no_charge": "Yêu cầu không tạo kết quả; ledger canonical không bị browser thay đổi.",
    "guarded": "Khả năng này đang được Core Bridge bảo vệ.",
    "cancelled": "Yêu cầu đã được canonical hủy.",
    "refunded": "Core Bridge đã ghi nhận trạng thái hoàn Xu canonical.",
    "read_only": "Dữ liệu canonical chỉ được hiển thị ở chế độ đọc.",
}
# Error codes produced inside this Web bridge client are already generic and
# do not expose Bot implementation details. Any other code coming from an
# evolving Bot adapter is collapsed before it reaches the browser.
_PUBLIC_BRIDGE_ERROR_CODES = frozenset({
    "CORE_BRIDGE_NOT_CONFIGURED", "CORE_BRIDGE_UNAVAILABLE", "CORE_BRIDGE_UNAUTHORIZED",
    "CORE_BRIDGE_FORBIDDEN", "CORE_BRIDGE_NOT_AVAILABLE", "CORE_BRIDGE_RATE_LIMITED",
    "CORE_BRIDGE_INVALID_RESPONSE",
})
ADMIN_BRIDGE_MODULES = frozenset({
    "overview", "summary", "users", "user", "wallet", "payments", "topups", "revenue", "refunds",
    "jobs", "failed-jobs", "providers", "provider-cost", "workers", "features", "freezes", "pricing",
    "packages", "promos", "leads", "tickets", "support", "audit", "reports", "runtime", "system",
    "backups", "security", "access",
})
ADMIN_BRIDGE_MODULE_ALIASES = {"backup": "backups", "export": "reports"}


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


def _web_feature_execution_available() -> bool:
    """Whether a reviewed Web-to-canonical-job adapter exists for confirms.

    Bot/provider readiness is not enough. The frozen P0 bridge deliberately
    has no Web job-creation adapter, so keep confirm fail-closed even if a
    future environment accidentally enables provider calls in this Web App.
    """
    return False


def _linked(account: dict) -> str:
    user_id = str(account.get("canonical_user_id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=409, detail="Hãy liên kết Telegram trước khi dùng dữ liệu hoặc tính năng bot")
    return user_id


def _telegram_bot_chat_url() -> str:
    """Return a public bot-chat URL only when the configured username is safe.

    Manual-payment details, receipt handling and approval remain exclusively in
    the already-linked Telegram bot.  The Web App intentionally exposes no
    bank account, QR image, payment secret or user identity in this helper.
    """
    username = os.environ.get("BOT_USERNAME", "").strip().lstrip("@")
    if not TELEGRAM_BOT_USERNAME_PATTERN.fullmatch(username):
        return ""
    return f"https://t.me/{username}"


def _payment_topup_catalog() -> tuple[dict[str, Any], ...]:
    """Return raw canonical top-up SKUs when a reviewed bridge read exists.

    The frozen P0 bridge only exposes service-package catalog data, which is
    deliberately not interchangeable with the bot's PayOS top-up
    denominations. Keep this empty and fail-closed until a dedicated bot read
    adapter is added and tested; an environment flag alone must not invent
    payment SKUs or make a browser checkout available.
    """
    return ()


def _payment_topup_packages() -> list[dict[str, int | str | bool]]:
    """Project only selectable, well-formed canonical PayOS top-up SKUs.

    This boundary is intentionally local and strict: a future bridge adapter
    may supply raw data through ``_payment_topup_catalog``, but neither a
    browser-supplied code nor an empty/partial catalog can unlock checkout.
    """
    raw = _payment_topup_catalog()
    if not isinstance(raw, (list, tuple)):
        return []
    packages: list[dict[str, int | str | bool]] = []
    seen: set[str] = set()
    for item in raw[:80]:
        if not isinstance(item, dict) or item.get("available") is False:
            continue
        code = str(item.get("code") or "").strip()
        label = str(item.get("label") or "").strip()
        amount_vnd = item.get("amount_vnd")
        xu = item.get("xu")
        if (
            not CANONICAL_IDENTIFIER_PATTERN.fullmatch(code)
            or not label
            or len(label) > 120
            or isinstance(amount_vnd, bool)
            or isinstance(xu, bool)
            or not isinstance(amount_vnd, int)
            or not isinstance(xu, int)
            or amount_vnd <= 0
            or xu <= 0
            or code in seen
        ):
            continue
        seen.add(code)
        packages.append({"code": code, "label": label, "amount_vnd": amount_vnd, "xu": xu, "available": True})
    return packages


def _safe_input(value: dict[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Dữ liệu đầu vào không hợp lệ") from exc
    if len(encoded.encode("utf-8")) > 64_000:
        raise HTTPException(status_code=413, detail="Dữ liệu đầu vào quá lớn")
    return value


def _canonical_route_identifier(value: Any, label: str) -> str:
    identifier = str(value or "").strip()
    if not CANONICAL_IDENTIFIER_PATTERN.fullmatch(identifier):
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ")
    return identifier


def _canonical_admin_module(value: Any) -> str:
    module = str(value or "").strip().lower().replace("_", "-")
    module = ADMIN_BRIDGE_MODULE_ALIASES.get(module, module)
    if module not in ADMIN_BRIDGE_MODULES:
        raise HTTPException(status_code=404, detail="Module Admin chưa được công bố")
    return module


_MISSING = object()


def _redact_browser_identity(value: Any, *, allow_admin_user_refs: bool = False, depth: int = 0) -> Any:
    """Bound and redact values before any bridge result reaches a browser.

    The Bot is authoritative but its response shape can evolve. This generic
    pass removes raw identity plus common payment/provider/PII fields even
    when a future adapter nests or changes their spelling. Surface-specific
    projections below then reduce high-risk responses further.
    """
    if depth > 6:
        return None
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 100:
                break
            name = str(key)[:160]
            normalized = "".join(character for character in name.lower() if character.isalnum())
            # A canonical-admin read may show only the Bot's user reference
            # and public username. It still never receives a canonical
            # session identity, Telegram chat ID, or payment/provider PII.
            if normalized in BROWSER_PRIVATE_KEY_NORMALIZED or any(part in normalized for part in BROWSER_PRIVATE_KEY_PARTS):
                continue
            if normalized in BROWSER_IDENTITY_KEY_NORMALIZED and not (
                allow_admin_user_refs and normalized in {"userid", "username"}
            ):
                continue
            safe[name] = _redact_browser_identity(item, allow_admin_user_refs=allow_admin_user_refs, depth=depth + 1)
        return safe
    if isinstance(value, (list, tuple)):
        return [_redact_browser_identity(item, allow_admin_user_refs=allow_admin_user_refs, depth=depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return value[:2_000]
    if isinstance(value, (bool, int)) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return None


def _browser_scalar(value: Any, *, maximum: int = 200) -> str | int | float | bool | None | object:
    if isinstance(value, str):
        return value.strip()[:maximum]
    if isinstance(value, (bool, int)) or value is None:
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return _MISSING


def _project_record(value: Any, fields: tuple[str, ...], *, text_limit: int = 200) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for field in fields:
        if field not in value:
            continue
        item = _browser_scalar(value.get(field), maximum=text_limit)
        if item is not _MISSING:
            result[field] = item
    return result


def _project_items(value: Any, fields: tuple[str, ...], *, allow_admin_user_refs: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:100]:
        record = _project_record(item, fields)
        if allow_admin_user_refs and isinstance(item, dict):
            for field in ("user_id", "username"):
                safe = _browser_scalar(item.get(field), maximum=120)
                if safe is not _MISSING:
                    record[field] = safe
        if record:
            result.append(record)
    return result


def _project_readiness(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    fields = ("configured", "public_ready", "guarded", "reason", "adapter", "alias_of")
    for key, item in list(value.items())[:120]:
        name = str(key)
        if not CANONICAL_IDENTIFIER_PATTERN.fullmatch(name):
            continue
        record = _project_record(item, fields, text_limit=160)
        if isinstance(item, dict) and isinstance(item.get("missing"), list):
            record["missing"] = [str(part).strip()[:80] for part in item["missing"][:20] if isinstance(part, str) and part.strip()]
        if record:
            result[name] = record
    return result


def _safe_payos_checkout(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return ""
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443} or (hostname != "pay.payos.vn" and not hostname.endswith(".payos.vn")):
        return ""
    return value[:1_000]


def _asset_delivery_allowed_hosts() -> frozenset[str]:
    """Read an explicit allowlist for signed-file delivery origins.

    A signed URL is intentionally not a generic bridge field. Operations must
    nominate its CDN/object-store hostname through Railway before the Web App
    will redirect a customer. Wildcards, schemes and paths are rejected so a
    future adapter cannot turn a broad configuration string into an open
    redirect.
    """
    raw = os.environ.get("WEBAPP_ASSET_DELIVERY_ALLOWED_HOSTS", "")
    hosts: set[str] = set()
    for item in raw.split(","):
        host = item.strip().lower().rstrip(".")
        if not host or "/" in host or ":" in host or "@" in host:
            continue
        if not re.fullmatch(r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,62}", host):
            continue
        hosts.add(host)
    return frozenset(hosts)


def _valid_asset_delivery_expiry(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 80:
        return False
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expiry.tzinfo is None:
        return False
    remaining = (expiry.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds()
    return 0 < remaining <= ASSET_DELIVERY_MAX_TTL_SECONDS


def _safe_asset_delivery_url(value: Any, expires_at: Any) -> str:
    """Accept only a configured, still-valid temporary HTTPS delivery URL."""
    if not isinstance(value, str) or not value or len(value) > ASSET_DELIVERY_MAX_URL_LENGTH:
        return ""
    if not _valid_asset_delivery_expiry(expires_at):
        return ""
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.fragment
        or hostname not in _asset_delivery_allowed_hosts()
    ):
        return ""
    return value


def _asset_delivery_guarded(error_code: str) -> dict:
    return envelope(
        False,
        "Tệp đang chờ delivery URL ký hợp lệ từ Core Bridge. Web không tự dựng link tải.",
        status_name="guarded",
        error_code=error_code,
    )


def _record_asset_delivery_audit(account: dict, request: Request, asset_id: str, *, outcome: str, detail: str) -> None:
    """Audit an asset-delivery decision without persisting a signed URL."""
    ensure_copyfast_schema()
    with transaction() as conn:
        _record_audit(
            conn,
            account_id=str(account.get("id") or "") or None,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="asset.delivery",
            request_id=_request_id(request) or str(uuid.uuid4()),
            target=asset_id,
            outcome=outcome,
            detail=detail,
        )


def _project_feature_document(value: Any, *, depth: int = 0) -> Any:
    """Project a provider-free planning document for a feature response.

    Draft/estimate content is intentionally flexible because the Bot's
    provider-free planners produce different structured briefs.  This small
    recursive projector preserves public text, costs and choices while
    refusing any field that could act as a delivery, identity, job, provider
    or payment side channel.  Actual files remain available only through a
    separately reviewed private-delivery adapter.
    """
    if depth > 5:
        return None
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 80:
                break
            name = str(key)[:120]
            normalized = "".join(character for character in name.lower() if character.isalnum())
            if any(part in normalized for part in FEATURE_RESPONSE_PRIVATE_KEY_PARTS):
                continue
            projected = _project_feature_document(item, depth=depth + 1)
            if projected is not _MISSING:
                result[name] = projected
        return result
    if isinstance(value, (list, tuple)):
        return [
            projected
            for item in value[:80]
            if (projected := _project_feature_document(item, depth=depth + 1)) is not _MISSING
        ]
    if isinstance(value, str):
        return value.strip()[:2_000]
    if isinstance(value, (bool, int)) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return _MISSING


def _project_feature_response(value: dict[str, Any]) -> dict[str, Any]:
    """Expose only planning and staging metadata needed by the Portal."""
    result = _project_record(
        value,
        ("feature", "requires_confirm", "quote_expires_at", "quote_valid_until", "status"),
        text_limit=160,
    )
    for field in ("draft", "estimate"):
        document = _project_feature_document(value.get(field))
        if isinstance(document, dict):
            result[field] = document
    if isinstance(value.get("uploads"), list):
        result["uploads"] = _project_items(
            value.get("uploads"),
            ("id", "upload_id", "stage_id", "file_name", "content_size", "status", "created_at"),
        )
    return result


def _project_surface_data(data: Any, surface: str, *, allow_admin_user_refs: bool = False) -> dict[str, Any]:
    value = _redact_browser_identity(data, allow_admin_user_refs=allow_admin_user_refs)
    if not isinstance(value, dict):
        return {}
    if surface == "wallet":
        result = _project_record(value, ("balance_xu", "total_spent_xu", "is_vip", "source"))
        plan = _project_record(value.get("plan"), ("current_plan", "plan_name", "plan_status", "plan_expires_at", "plan_xu_remaining"))
        if plan:
            result["plan"] = plan
        return result
    if surface == "pricing":
        result = _project_record(value, ("available", "billing_mode", "price_table_source", "trend_workflow_content_total_cost_xu"))
        tier_fields = ("code", "label", "cost_xu", "note", "retry_warranty_count")
        combo_fields = ("code", "label", "price_vnd", "display_price", "summary")
        result["image_tiers"] = _project_items(value.get("image_tiers"), tier_fields)
        result["video_tiers"] = _project_items(value.get("video_tiers"), tier_fields)
        result["video_combos"] = _project_items(value.get("video_combos"), combo_fields)
        return result
    if surface == "packages":
        result = _project_record(value, ("available",))
        package_fields = ("code", "type", "label", "note", "default_days", "price_vnd", "manual")
        for group in ("monthly", "combos"):
            rows: list[dict[str, Any]] = []
            raw_rows = value.get(group) if isinstance(value.get(group), list) else []
            for source in raw_rows[:100]:
                row = _project_record(source, package_fields)
                if not row:
                    continue
                source = source if isinstance(source, dict) else {}
                raw_items = source.get("items") if isinstance(source.get("items"), dict) else {}
                row["items"] = {
                    str(key)[:80]: amount
                    for key, amount in list(raw_items.items())[:40]
                    if isinstance(key, str) and isinstance(amount, int) and not isinstance(amount, bool) and amount >= 0
                }
                rows.append(row)
            result[group] = rows
        return result
    if surface == "payment":
        result = _project_record(value, ("payment_id", "order_code", "id", "status", "amount_vnd", "xu", "created_at", "paid_at"))
        checkout = _safe_payos_checkout(value.get("checkout_url") or value.get("payment_url") or value.get("url"))
        if checkout:
            result["checkout_url"] = checkout
        return result
    if surface == "job":
        fields = ("id", "feature", "job_type", "status", "created_at", "updated_at", "estimated_xu", "charged_xu", "refund_status", "output_available", "error_category", "download_ready")
        if isinstance(value.get("items"), list):
            return {"items": _project_items(value.get("items"), fields)}
        return _project_record(value, fields)
    if surface == "asset":
        # `delivery_ready` is an explicit Bot signal that the asset may ask
        # the private delivery endpoint for a fresh URL. `download_ready`
        # alone only proves output validation and must not create a browser
        # link by itself.
        fields = ("id", "feature", "status", "created_at", "output_available", "download_ready", "delivery_ready")
        return {"items": _project_items(value.get("items"), fields)} if isinstance(value.get("items"), list) else _project_record(value, fields)
    if surface == "voice":
        fields = ("id", "display_name", "status", "is_default", "consent_status", "tts_ready", "preview_ready", "created_at", "updated_at")
        return {"items": _project_items(value.get("items"), fields)}
    if surface == "tickets":
        fields = ("id", "category", "related_tool", "subject", "status", "created_at", "updated_at")
        return {"items": _project_items(value.get("items"), fields)}
    if surface == "readiness":
        return {"features": _project_readiness(value.get("features"))}
    if surface == "feature":
        return _project_feature_response(value)
    if surface == "admin":
        result = _project_record(value, ("module", "read_only", "message"))
        counts = value.get("counts") if isinstance(value.get("counts"), dict) else {}
        safe_counts = {str(key)[:80]: amount for key, amount in list(counts.items())[:40] if isinstance(amount, int) and not isinstance(amount, bool) and amount >= 0}
        if safe_counts:
            result["counts"] = safe_counts
        if "readiness" in value:
            result["readiness"] = _project_readiness(value.get("readiness"))
        fields = ("id", "feature", "job_type", "status", "created_at", "updated_at", "balance_xu", "total_spent_xu", "is_vip", "amount_vnd", "xu", "type", "paid_at", "refund_status", "output_available", "error_category", "download_ready", "reason", "action", "priority", "category", "related_tool", "has_attachment")
        if isinstance(value.get("items"), list):
            result["items"] = _project_items(value.get("items"), fields, allow_admin_user_refs=allow_admin_user_refs)
        return result
    if surface == "upload":
        return _project_record(value, ("id", "upload_id", "stage_id", "status", "created_at"))
    if surface == "delivery":
        # A delivery URL requires its own reviewed adapter. Do not let a
        # future bridge response smuggle a URL or file reference here.
        return _project_record(value, ("id", "status", "download_ready"))
    return value


def _browser_safe_bridge_response(response: dict, *, allow_admin_user_refs: bool = False, surface: str = "generic") -> dict:
    source = response if isinstance(response, dict) else {}
    status = str(source.get("status") or "guarded")
    if status not in _PUBLIC_BRIDGE_STATUSES:
        status = "guarded"
    raw_error_code = str(source.get("error_code") or "")
    if raw_error_code in _PUBLIC_BRIDGE_ERROR_CODES:
        error_code = raw_error_code
    elif raw_error_code:
        # Do not allow an adapter-specific code to become an oracle for
        # provider/runtime state. Its status and public message above remain
        # enough for a customer to understand that the request is guarded.
        error_code = "CORE_BRIDGE_RESPONSE_GUARDED"
    else:
        error_code = ""
    return envelope(
        bool(source.get("ok")),
        _PUBLIC_BRIDGE_MESSAGES[status],
        data=_project_surface_data(source.get("data"), surface, allow_admin_user_refs=allow_admin_user_refs),
        status_name=status,
        error_code=error_code or None,
    )


def _browser_safe_wallet_history_response(response: dict) -> dict:
    """Allowlist the small ledger projection the wallet UI actually renders.

    Bot event IDs, notes and references may contain a payment reference or
    other operational context. The Web wallet needs only time, event type,
    delta and post-event balance to render canonical history. Keeping this as
    an allowlist prevents future bridge fields from silently reaching browsers.
    """
    data = response.get("data") if isinstance(response, dict) else {}
    raw_items = data.get("items") if isinstance(data, dict) else []
    safe_items: list[dict[str, int | float | str]] = []
    if isinstance(raw_items, list):
        for item in raw_items[:100]:
            if not isinstance(item, dict):
                continue
            safe_item: dict[str, int | float | str] = {}
            for field in ("created_at", "event_type"):
                value = item.get(field)
                if isinstance(value, str) and value.strip():
                    safe_item[field] = value.strip()[:160]
            for field in ("delta_xu", "balance_after_xu"):
                value = item.get(field)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    safe_item[field] = value
            if safe_item:
                safe_items.append(safe_item)
    status = str(response.get("status") or "guarded") if isinstance(response, dict) else "guarded"
    if status not in {"draft", "awaiting_confirm", "queued", "processing", "completed", "failed", "failed_no_charge", "guarded", "cancelled", "refunded", "read_only"}:
        status = "guarded"
    message = response.get("message") if isinstance(response, dict) else ""
    error_code = response.get("error_code") if isinstance(response, dict) else None
    return envelope(
        bool(response.get("ok")) if isinstance(response, dict) else False,
        message[:500] if isinstance(message, str) and message else "Lịch sử ví đang chờ dữ liệu canonical.",
        data={"items": safe_items},
        status_name=status,
        error_code=error_code[:120] if isinstance(error_code, str) else None,
    )


def _looks_like_payment_card(candidate: str) -> bool:
    digits = "".join(character for character in candidate if character.isdigit())
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    for index, character in enumerate(reversed(digits)):
        number = int(character)
        if index % 2:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def _ticket_contains_sensitive_data(subject: str, detail: str) -> bool:
    """Fail closed before a support ticket can persist a credential or card.

    This is intentionally conservative: it catches explicit credential
    assignments, bearer/JWT-style keys, OTP/CVV disclosures and Luhn-valid
    card numbers without treating an ordinary support sentence as a secret.
    """
    text = f"{subject}\n{detail}"
    if any(pattern.search(text) for pattern in (
        TICKET_SECRET_ASSIGNMENT_PATTERN,
        TICKET_BEARER_PATTERN,
        TICKET_KEY_PATTERN,
        TICKET_VERIFICATION_PATTERN,
    )):
        return True
    return any(_looks_like_payment_card(match.group(0)) for match in TICKET_CARD_CANDIDATE_PATTERN.finditer(text))


def _assert_safe_ticket_content(subject: str, detail: str) -> None:
    if _ticket_contains_sensitive_data(subject, detail):
        raise HTTPException(
            status_code=422,
            detail="Ticket không nhận API key, token, mật khẩu, OTP/CVV hoặc số thẻ. Hãy xóa dữ liệu nhạy cảm trước khi gửi.",
        )


def _contains_feature_authority_field(value: Any) -> bool:
    """Find forged authority fields without logging their contents.

    Feature payloads are forwarded to a separate, private Bot authority.  A
    nested object must not become a side channel for browser-provided wallet,
    provider, job or delivery state when a future feature adapter is added.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(character for character in str(key or "").lower() if character.isalnum())
            if normalized in FEATURE_AUTHORITY_FIELDS_NORMALIZED:
                return True
            if _contains_feature_authority_field(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_feature_authority_field(child) for child in value)
    return False


def _canonical_upload_ids(value: Any) -> list[str] | None:
    """Accept only opaque bot staging identifiers, never paths or handles."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_FEATURE_UPLOADS:
        return None
    identifiers = [item.strip() for item in value if isinstance(item, str)]
    if len(identifiers) != len(value) or len(set(identifiers)) != len(identifiers):
        return None
    if any(not CANONICAL_IDENTIFIER_PATTERN.fullmatch(item) for item in identifiers):
        return None
    return identifiers


def _has_feature_text(values: dict[str, Any]) -> bool:
    return any(isinstance(values.get(key), str) and values[key].strip() for key in FEATURE_TEXT_KEYS)


def _affirmed(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "on"})


def _whole_number_in_range(value: Any, minimum: int, maximum: int) -> bool:
    if isinstance(value, bool):
        return False
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return False
    return parsed.is_integer() and minimum <= int(parsed) <= maximum


def _feature_input_contract_error(feature: str, values: dict[str, Any]) -> str:
    """Mirror the safe Web intake promises before the request reaches Bot.

    This is not a replacement for Bot ownership/MIME/provider checks.  It
    stops direct API callers from bypassing the same minimum semantic contract
    that the browser forms enforce, while Bot stays authoritative for upload
    ownership, pricing, jobs, Xu and delivery.
    """
    if _contains_feature_authority_field(values):
        return "authority_field_not_allowed"
    raw_upload_ids = values.get("upload_ids")
    if isinstance(raw_upload_ids, list) and len(raw_upload_ids) > MAX_FEATURE_UPLOADS:
        return "too_many_uploads"
    upload_ids = _canonical_upload_ids(raw_upload_ids)
    if upload_ids is None:
        return "upload_ids_invalid"
    if feature in FEATURE_TEXT_REQUIRED and not _has_feature_text(values):
        return "text_required"
    if feature in FEATURE_UPLOAD_REQUIRED and not upload_ids:
        return "upload_required"
    if feature == "documents_merge" and len(upload_ids) < 2:
        return "multiple_uploads_required"
    if feature == "voice_clone" and not _affirmed(values.get("consent")):
        return "voice_clone_consent_required"
    if feature == "voice_saved_tts" and not str(values.get("voice_profile_id") or "").strip():
        return "voice_profile_required"
    if feature == "music_song":
        prompt_mode = str(values.get("mode") or "").strip().lower()
        if prompt_mode and prompt_mode not in MUSIC_PROMPT_MODES:
            return "music_prompt_mode_invalid"
        length_mode = str(values.get("song_length_mode") or "").strip().lower()
        if length_mode not in MUSIC_SONG_LENGTH_MODES:
            return "song_length_mode_required"
        if length_mode == "seconds" and not _whole_number_in_range(values.get("duration_seconds"), 1, 600):
            return "song_duration_required"
    if feature in FEATURE_TARGET_LANGUAGE_REQUIRED:
        target_language = str(values.get("target_language") or "").strip().lower()
        if not target_language:
            return "target_language_required"
        if target_language not in CANONICAL_TARGET_LANGUAGE_CODES:
            return "target_language_invalid"
        # Forward one canonical spelling even if a direct caller used casing
        # different from the select control. Subtitle/dub helpers consume the
        # raw value, unlike the document helper which normalizes it itself.
        values["target_language"] = target_language
    if feature == "documents_split" and not CONTIGUOUS_PAGE_RANGE_PATTERN.fullmatch(str(values.get("page_range") or "").strip()):
        return "page_range_invalid"
    return ""


def _feature_input_contract_response(feature: str, reason: str) -> dict:
    messages = {
        "authority_field_not_allowed": "Yêu cầu feature có trường hệ thống không được phép; Web không nhận identity, Xu, provider, job hoặc output từ browser.",
        "upload_ids_invalid": "Tham chiếu tệp staging không hợp lệ. Hãy chọn lại tệp để Web gửi qua luồng canonical.",
        "too_many_uploads": f"Mỗi workflow chỉ nhận tối đa {MAX_FEATURE_UPLOADS} tệp đã vào staging canonical.",
        "text_required": "Hãy nhập mô tả chính trước khi tạo draft hoặc estimate canonical.",
        "upload_required": "Workflow này cần tệp đã vào staging canonical trước khi tiếp tục.",
        "multiple_uploads_required": "Gộp PDF cần ít nhất hai tệp đã vào staging canonical.",
        "voice_clone_consent_required": "Voice Clone cần mẫu audio thuộc tài khoản và xác nhận quyền sử dụng.",
        "voice_profile_required": "Hãy chọn một Voice Vault profile đã sẵn sàng.",
        "music_prompt_mode_invalid": "Kiểu sáng tác nhạc chưa thuộc mode canonical của bot.",
        "song_length_mode_required": "Hãy chọn dạng bài hát canonical trước khi tạo draft hoặc estimate.",
        "song_duration_required": "Khi chọn bài hát theo số giây, hãy nhập thời lượng nguyên từ 1 đến 600 giây.",
        "target_language_required": "Hãy chọn ngôn ngữ đích trước khi tiếp tục workflow canonical.",
        "target_language_invalid": "Ngôn ngữ đích chưa thuộc danh sách canonical Bot P0 hỗ trợ.",
        "page_range_invalid": "Khoảng trang chỉ nhận một trang hoặc dải liên tiếp, ví dụ 2 hoặc 2-5.",
    }
    return envelope(
        False,
        messages.get(reason, "Input chưa đáp ứng contract an toàn của workflow."),
        status_name="guarded",
        data={"feature": feature, "reason": reason},
        error_code="FEATURE_INPUT_CONTRACT_REQUIRED",
    )


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


def _canonical_upload_media_type(extension: str, supplied: str) -> str:
    """Verify MIME/extension consistency and return a server-owned MIME type.

    Browsers often provide ``application/octet-stream`` for a local file with
    no type association.  That fallback is accepted only after the structural
    content checks below succeed; a non-generic MIME must match the extension.
    The bridge always receives this canonical value, never the browser header.
    """
    canonical = UPLOAD_CANONICAL_MIME_BY_EXTENSION.get(extension)
    accepted = UPLOAD_ACCEPTED_MIME_BY_EXTENSION.get(extension)
    if not canonical or not accepted:
        raise HTTPException(status_code=415, detail="Định dạng tệp chưa được hỗ trợ")
    if supplied != "application/octet-stream" and supplied not in accepted:
        raise HTTPException(status_code=415, detail="MIME không khớp với định dạng tệp")
    return canonical


def _validate_docx_container(content: bytes) -> None:
    """Accept only a bounded Office Open XML document package, never a raw ZIP."""
    if not content.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        raise HTTPException(status_code=422, detail="DOCX không hợp lệ")
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_DOCX_ARCHIVE_MEMBERS:
                raise HTTPException(status_code=422, detail="DOCX có cấu trúc không an toàn")
            total_uncompressed = 0
            names: set[str] = set()
            for member in members:
                name = str(member.filename or "")
                if not name or name.startswith("/") or "\\" in name or any(part == ".." for part in name.split("/")):
                    raise HTTPException(status_code=422, detail="DOCX có đường dẫn không an toàn")
                total_uncompressed += max(0, int(member.file_size))
                if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise HTTPException(status_code=413, detail="DOCX vượt quá giới hạn giải nén an toàn")
                names.add(name)
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise HTTPException(status_code=422, detail="DOCX không có cấu trúc tài liệu hợp lệ")
    except BadZipFile as exc:
        raise HTTPException(status_code=422, detail="DOCX không hợp lệ") from exc


def _validate_upload_content(extension: str, content: bytes) -> None:
    """Perform bounded format checks before untrusted bytes enter Bot staging.

    These guards intentionally validate only the container/signature boundary;
    the Bot remains responsible for ownership and any feature-specific media
    decoding before a worker or provider consumes the staged object.
    """
    if extension == ".pdf":
        valid = content.startswith(b"%PDF-")
    elif extension == ".png":
        valid = content.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension in {".jpg", ".jpeg"}:
        valid = content.startswith(b"\xff\xd8\xff")
    elif extension == ".webp":
        valid = len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    elif extension in {".mp4", ".mov", ".m4a"}:
        valid = len(content) >= 12 and content[4:8] == b"ftyp"
    elif extension == ".webm":
        valid = content.startswith(b"\x1a\x45\xdf\xa3")
    elif extension == ".mp3":
        valid = content.startswith(b"ID3") or (len(content) >= 2 and content[0] == 0xFF and content[1] in {0xE2, 0xE3, 0xF2, 0xF3, 0xFA, 0xFB})
    elif extension == ".wav":
        valid = len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WAVE"
    elif extension == ".ogg":
        valid = content.startswith(b"OggS")
    elif extension == ".docx":
        _validate_docx_container(content)
        return
    elif extension in TEXT_UPLOAD_EXTENSIONS:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="Tệp văn bản phải dùng UTF-8") from exc
        valid = bool(text.strip()) and "\x00" not in text
    else:
        valid = False
    if not valid:
        raise HTTPException(status_code=422, detail="Nội dung tệp không khớp với định dạng đã chọn")


async def _read_validated_upload(file: UploadFile) -> tuple[str, str, bytes, str]:
    name, extension = _validate_upload_name(file.filename)
    media_type = str(file.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    canonical_media_type = _canonical_upload_media_type(extension, media_type)
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
    _validate_upload_content(extension, content)
    return name, canonical_media_type, content, hashlib.sha256(content).hexdigest()


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


def _bridge_surface(path: str) -> str:
    normalized = "/" + str(path or "").lstrip("/")
    if normalized == "/internal/v1/wallet":
        return "wallet"
    if normalized == "/internal/v1/pricing":
        return "pricing"
    if normalized == "/internal/v1/packages":
        return "packages"
    if normalized.startswith("/internal/v1/payments/"):
        return "payment"
    if normalized == "/internal/v1/jobs" or normalized.startswith("/internal/v1/jobs/"):
        return "job"
    if normalized == "/internal/v1/assets":
        return "asset"
    if normalized.startswith("/internal/v1/assets/"):
        return "delivery"
    if normalized == "/internal/v1/voice/profiles":
        return "voice"
    if normalized == "/internal/v1/support/tickets":
        return "tickets"
    if normalized == "/internal/v1/features/status":
        return "readiness"
    if normalized.startswith("/internal/v1/features/"):
        return "feature"
    if normalized.startswith("/internal/v1/admin/"):
        return "admin"
    if normalized == "/internal/v1/uploads":
        return "upload"
    return "generic"


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


async def _bridge(
    method: str,
    path: str,
    *,
    account: dict,
    request: Request,
    payload: dict | None = None,
    params: dict | None = None,
    admin_read: bool = False,
) -> dict:
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
    response = await bridge_request(
        method,
        path,
        payload=enriched if method.upper() != "GET" else None,
        params=query,
        request_id=_request_id(request),
        actor_id=user_id,
    )
    allow_admin_user_refs = bool(
        admin_read
        and path.startswith("/internal/v1/admin/")
        and account.get("role") == "admin"
    )
    return _browser_safe_bridge_response(
        response,
        allow_admin_user_refs=allow_admin_user_refs,
        surface=_bridge_surface(path),
    )


async def _asset_delivery_redirect(asset_id: str, request: Request, account: dict) -> RedirectResponse | dict:
    """Mint one ownership-checked redirect from an explicit Bot contract.

    The browser never receives the raw bridge envelope as JSON on success. It
    only follows a same-origin, signed-session request that the Bot binds to
    the canonical Telegram identity. This endpoint intentionally has no
    fallback URL, local file path, provider lookup, or generated delivery
    token: the Bot remains the delivery and ownership authority.
    """
    if not _flags()["copyfast_enabled"]:
        return _asset_delivery_guarded("WEBAPP_COPYFAST_DISABLED")
    user_id = _linked(account)
    raw = await bridge_request(
        "GET",
        f"/internal/v1/assets/{asset_id}/download",
        params={"user_id": user_id},
        request_id=_request_id(request),
        actor_id=user_id,
    )
    if not isinstance(raw, dict) or not raw.get("ok"):
        _record_asset_delivery_audit(account, request, asset_id, outcome="denied", detail="canonical bridge rejected delivery")
        return _browser_safe_bridge_response(raw if isinstance(raw, dict) else {}, surface="delivery")
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    delivery = data.get("delivery") if isinstance(data.get("delivery"), dict) else {}
    if (
        str(raw.get("status") or "") != "completed"
        or data.get("asset_id") != asset_id
        or data.get("download_ready") is not True
        or data.get("delivery_ready") is not True
    ):
        _record_asset_delivery_audit(account, request, asset_id, outcome="denied", detail="canonical delivery contract not ready")
        return _asset_delivery_guarded("ASSET_DELIVERY_NOT_READY")
    delivery_url = _safe_asset_delivery_url(delivery.get("url"), delivery.get("expires_at"))
    if not delivery_url:
        _record_asset_delivery_audit(account, request, asset_id, outcome="denied", detail="delivery URL failed local contract validation")
        return _asset_delivery_guarded("ASSET_DELIVERY_CONTRACT_INVALID")
    _record_asset_delivery_audit(account, request, asset_id, outcome="ok", detail="issued temporary canonical delivery redirect")
    response = RedirectResponse(delivery_url, status_code=307)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@router.get("/catalog")
async def feature_catalog():
    return envelope(True, "Danh mục tính năng Web App", data={"features": catalog(), "flags": _flags(), "bridge_configured": bridge_configured()})


@router.get("/core/status")
async def core_status():
    return envelope(
        True,
        "Trạng thái kết nối",
        data={
            "bridge_configured": bridge_configured(),
            "flags": _flags(),
            "web_feature_execution_available": _web_feature_execution_available(),
        },
    )


@router.get("/core/me")
async def core_me(request: Request, account: dict = Depends(require_account)):
    _linked(account)
    return envelope(
        False,
        "Danh tính Telegram canonical chỉ được dùng trong server để xác thực Core Bridge.",
        data={"telegram_linked": True},
        status_name="guarded",
        error_code="BROWSER_IDENTITY_NOT_EXPOSED",
    )


@router.get("/wallet")
async def wallet(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/wallet", account=account, request=request)


@router.get("/wallet/history")
async def wallet_history(request: Request, account: dict = Depends(require_account)):
    response = await _bridge("GET", "/internal/v1/wallet/history", account=account, request=request)
    return _browser_safe_wallet_history_response(response)


@router.get("/pricing")
async def pricing(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/pricing", account=account, request=request)


@router.get("/packages")
async def packages(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/packages", account=account, request=request)


@router.get("/payments/options")
async def payment_options(account: dict = Depends(require_account)):
    """Publish safe payment-entry metadata without creating a payment.

    This endpoint is deliberately local/read-only.  It makes no PayOS call,
    does not read a wallet ledger and does not duplicate the bot's webhook.
    """
    _linked(account)
    topup_packages = _payment_topup_packages()
    topup_catalog_available = bool(topup_packages)
    # Do not advertise a Web payment request unless the same dedicated top-up
    # catalog that protects POST /payments/create is available. An enabled
    # flag alone cannot turn service packages into payment denominations.
    payos_available = bool(
        _flags()["payment_enabled"] and bridge_configured() and topup_catalog_available
    )
    bot_chat_url = _telegram_bot_chat_url()
    return envelope(
        True,
        "Các lựa chọn thanh toán luôn do bot canonical xác minh.",
        status_name="read_only",
        data={
            "payos": {
                # This only confirms that Web may send a signed request to the
                # bridge *and* render a validated dedicated top-up SKU. The
                # bot remains the only authority that may return a checkout
                # URL, so it is intentionally not called `available`.
                "request_enabled": payos_available,
                # The local P0 bridge has no read-only top-up denomination
                # catalog yet. Do not present the unrelated service-package
                # catalog as Xu top-up choices in the browser.
                "topup_catalog_available": topup_catalog_available,
                "topup_packages": topup_packages,
                "telegram_url": bot_chat_url,
                "command": "/naptien",
                "status": "awaiting_confirm" if payos_available else "guarded",
                "checkout_owner": "canonical_bot",
            },
            "manual": {
                "available": bool(bot_chat_url),
                "telegram_url": bot_chat_url,
                "command": "/thucong",
                "receipt_channel": "telegram_bot",
                # The frozen P0 bridge can read owner-scoped PayOS orders,
                # but intentionally has no sanitized pending-deposit history
                # adapter. Do not imply that a browser can look up a manual
                # bill/TXID or admin-review request.
                "payment_lookup_available": False,
                "wallet_history_signal_available": True,
                # Manual receipt history remains a user-owned Bot view. These
                # presentation-only fields prevent a future Web page from
                # mistaking the wallet ledger for a second receipt system.
                "history_in_web": False,
                "history_channel": "telegram_bot",
                "history_command": "/thucong",
                "history_menu_label": "Lịch sử nạp thủ công",
            },
        },
    )


@router.post("/payments/create")
async def create_payment(payload: PaymentRequest, request: Request, account: dict = Depends(require_csrf)):
    if not _flags()["payment_enabled"]:
        return envelope(False, "Nạp Xu trên Web đang chờ xác minh core payment.", status_name="guarded", error_code="WEBAPP_PAYMENT_DISABLED")
    payment_type = str(payload.payment_type or "").strip().lower()
    if payment_type != "topup_xu":
        return envelope(False, "Loại thanh toán này chưa có adapter canonical được phê duyệt cho Web.", status_name="guarded", error_code="PAYMENT_TYPE_NOT_ALLOWED")
    topup_packages = _payment_topup_packages()
    if not topup_packages:
        return envelope(False, "Danh mục mệnh giá nạp canonical chưa được bridge cấp cho Web.", status_name="guarded", error_code="PAYMENT_TOPUP_CATALOG_REQUIRED")
    package_id = str(payload.package_id or "").strip()
    if not package_id:
        return envelope(False, "Hãy chọn gói từ catalog canonical trước khi tạo yêu cầu thanh toán.", status_name="failed", error_code="PAYMENT_PACKAGE_REQUIRED")
    if package_id not in {str(item["code"]) for item in topup_packages}:
        return envelope(False, "Mệnh giá nạp không còn thuộc catalog canonical hiện hành.", status_name="failed", error_code="PAYMENT_PACKAGE_NOT_IN_CATALOG")
    key = _require_key(payload.idempotency_key)
    scope = f"payment:{account['id']}"
    return await _run_idempotent(
        scope,
        key,
        lambda: _bridge(
            "POST", "/internal/v1/payments/create", account=account, request=request,
            payload={"package_id": package_id, "payment_type": payment_type, "idempotency_key": key},
        ),
    )


@router.get("/payments/{payment_id}")
async def payment_status(payment_id: str, request: Request, account: dict = Depends(require_account)):
    payment_id = _canonical_route_identifier(payment_id, "Mã payment")
    return await _bridge("GET", f"/internal/v1/payments/{payment_id}", account=account, request=request)


@router.get("/jobs")
async def list_jobs(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/jobs", account=account, request=request)


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str, request: Request, account: dict = Depends(require_account)):
    job_id = _canonical_route_identifier(job_id, "Mã job")
    return await _bridge("GET", f"/internal/v1/jobs/{job_id}", account=account, request=request)


@router.get("/assets")
async def assets(request: Request, account: dict = Depends(require_account)):
    return await _bridge("GET", "/internal/v1/assets", account=account, request=request)


@router.get("/assets/{asset_id}/download")
async def asset_download(asset_id: str, request: Request, account: dict = Depends(require_account)):
    # The core either returns an explicit short-lived, ownership-checked
    # delivery contract or stays guarded. The Web App never reconstructs a
    # provider URL from asset/job metadata.
    asset_id = _canonical_route_identifier(asset_id, "Mã tài sản")
    return await _asset_delivery_redirect(asset_id, request, account)


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
    _assert_safe_ticket_content(payload.subject, payload.detail)
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
        if not _web_feature_execution_available():
            return envelope(False, "Web App chưa có adapter tạo job canonical đã được phê duyệt; chỉ draft và estimate đang khả dụng.", status_name="guarded", error_code="WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED")
        contract_error = _feature_input_contract_error(feature, values)
        if contract_error:
            return _feature_input_contract_response(feature, contract_error)
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
    contract_error = _feature_input_contract_error(feature, values)
    if contract_error:
        return _feature_input_contract_response(feature, contract_error)
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
    return await _bridge("GET", "/internal/v1/admin/summary", account=account, request=request, admin_read=True)


@router.get("/admin/users")
async def admin_users(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/users", account=account, request=request, admin_read=True)


@router.get("/admin/jobs")
async def admin_jobs(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/jobs", account=account, request=request, admin_read=True)


@router.get("/admin/payments")
async def admin_payments(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/payments", account=account, request=request, admin_read=True)


@router.get("/admin/providers")
async def admin_providers(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/providers", account=account, request=request, admin_read=True)


@router.get("/admin/tickets")
async def admin_tickets(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/tickets", account=account, request=request, admin_read=True)


@router.get("/admin/modules/{module}")
async def admin_module(module: str, request: Request, account: dict = Depends(require_canonical_admin)):
    module = _canonical_admin_module(module)
    record_id = str(request.query_params.get("record_id") or "").strip()
    if record_id:
        record_id = _canonical_route_identifier(record_id, "ID bản ghi")
    params = {"record_id": record_id} if record_id else None
    return await _bridge(
        "GET",
        f"/internal/v1/admin/modules/{module}",
        account=account,
        request=request,
        params=params,
        admin_read=True,
    )


@router.post("/admin/jobs/{job_id}/retry")
async def admin_retry_job(job_id: str, payload: FeatureRequest, request: Request):
    # Retain local session/CSRF/admin protection even while the write gate is
    # disabled, but do not contact the bot authority unless a separately
    # reviewed write adapter has been explicitly enabled.
    account = require_admin_csrf(request)
    job_id = _canonical_route_identifier(job_id, "Mã job")
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
    job_id = _canonical_route_identifier(job_id, "Mã job")
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
    if feature not in FEATURE_BY_KEY:
        raise HTTPException(status_code=404, detail="Tính năng chưa có trong parity registry")
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
