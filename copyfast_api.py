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
TELEGRAM_BOT_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{5,32}$")
CANONICAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
CONTIGUOUS_PAGE_RANGE_PATTERN = re.compile(r"^\d+(?:-\d+)?$")
MAX_FEATURE_UPLOADS = 8
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


def _payment_topup_catalog_available() -> bool:
    """Whether the bot bridge exposes a verified Web top-up catalog.

    The frozen P0 bridge only exposes service-package catalog data, which is
    deliberately not interchangeable with the bot's PayOS top-up
    denominations. Keep this fail-closed until a dedicated bot read adapter is
    added and tested; an environment flag alone must not invent payment SKUs.
    """
    return False


def _safe_input(value: dict[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Dữ liệu đầu vào không hợp lệ") from exc
    if len(encoded.encode("utf-8")) > 64_000:
        raise HTTPException(status_code=413, detail="Dữ liệu đầu vào quá lớn")
    return value


def _contains_feature_authority_field(value: Any) -> bool:
    """Find forged authority fields without logging their contents.

    Feature payloads are forwarded to a separate, private Bot authority.  A
    nested object must not become a side channel for browser-provided wallet,
    provider, job or delivery state when a future feature adapter is added.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key or "").strip().lower() in FEATURE_AUTHORITY_FIELDS:
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


@router.get("/payments/options")
async def payment_options(account: dict = Depends(require_account)):
    """Publish safe payment-entry metadata without creating a payment.

    This endpoint is deliberately local/read-only.  It makes no PayOS call,
    does not read a wallet ledger and does not duplicate the bot's webhook.
    """
    _linked(account)
    topup_catalog_available = _payment_topup_catalog_available()
    payos_available = bool(_flags()["payment_enabled"] and bridge_configured())
    bot_chat_url = _telegram_bot_chat_url()
    return envelope(
        True,
        "Các lựa chọn thanh toán luôn do bot canonical xác minh.",
        status_name="read_only",
        data={
            "payos": {
                # This only confirms that Web may send a signed request to the
                # bridge. The bot remains the only authority that may return a
                # checkout URL, so it is intentionally not called `available`.
                "request_enabled": payos_available,
                # The local P0 bridge has no read-only top-up denomination
                # catalog yet. Do not present the unrelated service-package
                # catalog as Xu top-up choices in the browser.
                "topup_catalog_available": topup_catalog_available,
                "topup_packages": [],
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
    if not _payment_topup_catalog_available():
        return envelope(False, "Danh mục mệnh giá nạp canonical chưa được bridge cấp cho Web.", status_name="guarded", error_code="PAYMENT_TOPUP_CATALOG_REQUIRED")
    package_id = str(payload.package_id or "").strip()
    if not package_id:
        return envelope(False, "Hãy chọn gói từ catalog canonical trước khi tạo yêu cầu thanh toán.", status_name="failed", error_code="PAYMENT_PACKAGE_REQUIRED")
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
