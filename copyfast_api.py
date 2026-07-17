"""Authenticated Web API that adapts the private bot core to the portal."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import secrets
import uuid
from io import BytesIO
from typing import Any, Callable
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import (
    _record_audit,
    _request_id,
    current_session,
    envelope,
    require_account,
    require_canonical_admin,
    require_canonical_admin_csrf,
    require_admin_csrf,
    require_csrf,
)
from copyfast_bridge import bridge_configured, bridge_request
from copyfast_capability_hub import capability_hub
from copyfast_campaign_schedule import (
    MAX_ACTIVE_SCHEDULE_INTENTS_PER_ACCOUNT,
    MAX_SCHEDULE_INTENTS_PER_ACCOUNT,
    MAX_SCHEDULE_INTENTS_PER_PLAN,
    SNAPSHOT_HASH_PATTERN,
    campaign_source_hash,
    canonical_json_hash,
    normalize_schedule_trigger,
)
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now
from copyfast_native_read_models import (
    get_native_job,
    list_native_assets,
    list_native_completed_outputs,
    list_native_jobs,
    parse_native_asset_id,
    parse_native_job_id,
)
from copyfast_registry import FEATURE_BY_KEY, catalog
from copyfast_web_engine import engine_descriptor


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
# Manual payment proof belongs to the Bot conversation.  These labels are
# intentionally caught even when the following value is not obviously secret:
# a ticket must never become an alternate bill/TXID/account-number inbox.
TICKET_MANUAL_PAYMENT_PROOF_PATTERN = re.compile(
    r"\b(?:txid|transaction(?:\s+(?:hash|id))?|mã\s*(?:giao\s*)?dịch|ma\s*(?:giao\s*)?dich|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|"
    r"(?:số|so)\s*tài\s*khoản|bank\s*account|"
    r"qr\s*(?:thanh\s*toán|payment|code)?)\b",
    re.IGNORECASE,
)
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
FEATURE_QUOTE_RECEIPT_TTL_SECONDS = 10 * 60
FEATURE_QUOTE_RECEIPT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,160}$")
FEATURE_CONFIRM_ACCEPTED_STATUSES = frozenset({"queued", "processing", "completed", "failed", "failed_no_charge", "cancelled", "refunded"})
CAMPAIGN_PLAN_PLATFORMS = frozenset({"facebook", "instagram", "tiktok", "youtube", "website", "other"})
CAMPAIGN_PLAN_OBJECTIVES = frozenset({"affiliate", "traffic", "conversion", "revenue", "community"})
CAMPAIGN_PLAN_STATUSES = frozenset({"draft", "review", "approved", "scheduled", "archived"})
CAMPAIGN_PLAN_TRANSITIONS = {
    "draft": frozenset({"review", "archived"}),
    "review": frozenset({"draft", "approved", "archived"}),
    "approved": frozenset({"draft", "scheduled", "archived"}),
    "scheduled": frozenset({"approved", "archived"}),
    "archived": frozenset({"draft"}),
}
CAMPAIGN_PLAN_STATUS_LABELS = {
    "draft": "bản nháp",
    "review": "đang tự rà soát",
    "approved": "đã sẵn sàng theo kế hoạch",
    "scheduled": "đã xếp lịch nội bộ",
    "archived": "đã lưu trữ",
}
CAMPAIGN_CALENDAR_MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")
# The Calendar is a read-only planning window. Keep one server-enforced cap
# instead of accepting an arbitrary browser limit so an unusually dense month
# cannot become an unbounded private-data response.
CAMPAIGN_CALENDAR_WINDOW_MAX_ITEMS = 200
CAMPAIGN_SCHEDULE_IDEMPOTENCY_RETENTION = timedelta(hours=24)
CAMPAIGN_SCHEDULE_MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024

# ``web_audit_events`` is intentionally an internal, append-only audit trail.
# Customers may inspect a bounded history of their *own Web activity*, but the
# browser must never receive its raw action name, request ID, target, detail,
# canonical Telegram identity, or a cross-account event.  Keep this projection
# separate from the Admin audit surface and from the Bot's canonical ledger,
# job, payment and provider histories.
ACCOUNT_ACTIVITY_LABELS = {
    "auth.register": ("Tạo hồ sơ Web", "Tài khoản"),
    "auth.login": ("Đăng nhập Web", "Bảo mật"),
    "auth.logout": ("Đăng xuất Web", "Bảo mật"),
    "auth.profile_update": ("Cập nhật hồ sơ Web", "Hồ sơ"),
    "auth.telegram_link_start": ("Bắt đầu liên kết Telegram", "Bảo mật"),
    "auth.telegram_link_confirm": ("Bot đã xác minh liên kết Telegram", "Bảo mật"),
    "auth.telegram_link_complete": ("Hoàn tất liên kết Telegram", "Bảo mật"),
    "auth.telegram_login_start": ("Bắt đầu đăng nhập Telegram", "Bảo mật"),
    "auth.telegram_login_confirm": ("Bot đã xác minh đăng nhập Telegram", "Bảo mật"),
    "auth.telegram_login_complete": ("Hoàn tất đăng nhập Telegram", "Bảo mật"),
    "auth.telegram_account_upgrade": ("Thêm phương thức Email", "Bảo mật"),
    "auth.mfa_login_challenge": ("Xác minh mật khẩu, chờ mã hai bước", "Bảo mật"),
    "auth.mfa_login": ("Xác thực hai bước khi đăng nhập", "Bảo mật"),
    "auth.mfa_enrollment_start": ("Bắt đầu thiết lập xác thực hai bước", "Bảo mật"),
    "auth.mfa_enrollment_confirm": ("Bật xác thực hai bước", "Bảo mật"),
    "auth.mfa_disable": ("Tắt xác thực hai bước", "Bảo mật"),
    "oauth.signin": ("Đăng nhập OAuth", "Bảo mật"),
    "oauth.link": ("Liên kết phương thức OAuth", "Bảo mật"),
    "oauth.link_start": ("Bắt đầu liên kết OAuth", "Bảo mật"),
    "oauth.start": ("Chuyển sang xác minh OAuth", "Bảo mật"),
    "oauth.callback": ("Hoàn tất xác minh OAuth", "Bảo mật"),
    "campaign.plan.create": ("Tạo kế hoạch Web", "Campaign Planner"),
    "campaign.plan.update": ("Cập nhật kế hoạch Web", "Campaign Planner"),
    "campaign.plan.review": ("Tự rà soát kế hoạch Web", "Campaign Planner"),
    "campaign.plan.status": ("Cập nhật trạng thái kế hoạch Web", "Campaign Planner"),
    "campaign.schedule.create": ("Tạo lịch nhắc Campaign", "Campaign Planner"),
    "campaign.schedule.cancel": ("Hủy lịch nhắc Campaign", "Campaign Planner"),
    "campaign.schedule.reconfirm": ("Xác nhận lại lịch nhắc Campaign", "Campaign Planner"),
    "workspace.draft.create": ("Lưu bản nháp Web", "AI Studio"),
    "workspace.draft.update": ("Cập nhật bản nháp Web", "AI Studio"),
    "workspace.draft.archive": ("Lưu trữ bản nháp Web", "AI Studio"),
    "web.project.create": ("Tạo Project Web", "Project Center"),
    "web.project.update": ("Cập nhật Project Web", "Project Center"),
    "web.studio_document.create": ("Tạo Studio Document", "Project Center"),
    "web.studio_document.update": ("Lưu phiên bản Studio Document", "Project Center"),
    "web.studio_document.restore": ("Khôi phục Studio Document", "Project Center"),
    "web.asset_vault.upload": ("Lưu tệp vào Asset Vault", "Web Workspace"),
    "web.asset_vault.archive": ("Lưu trữ tệp Asset Vault", "Web Workspace"),
    "web.project_package.export": ("Xuất Project Package", "Web Workspace"),
    "web.project_package.export_failed": ("Project Package chưa hoàn tất", "Web Workspace"),
    "web.document_operation.pdf_split": ("Tách PDF riêng tư", "Web Workspace"),
    "web.document_operation.pdf_split_failed": ("Tách PDF chưa hoàn tất", "Web Workspace"),
    "web.document_operation.pdf_merge": ("Gộp PDF riêng tư", "Web Workspace"),
    "web.document_operation.pdf_merge_failed": ("Gộp PDF chưa hoàn tất", "Web Workspace"),
    "web.document_operation.pdf_optimize": ("Tối ưu PDF riêng tư", "Web Workspace"),
    "web.document_operation.pdf_optimize_failed": ("Tối ưu PDF chưa hoàn tất", "Web Workspace"),
    "web.document_operation.pdf_optimize_guarded": ("PDF không có bản lossless nhỏ hơn", "Web Workspace"),
    # Memory Center is explicitly Web-owned.  Keep its customer-facing audit
    # labels separate from Bot `/note`/`/remind` state so activity history can
    # never imply that Telegram delivered or owns the Web record.
    "web.memory.note.create": ("Tạo ghi chú Memory Center", "Memory Center"),
    "web.memory.note.update": ("Lưu phiên bản ghi chú", "Memory Center"),
    "web.memory.note.archive": ("Lưu trữ ghi chú", "Memory Center"),
    "web.memory.note.restore": ("Khôi phục ghi chú", "Memory Center"),
    "web.memory.note.restore_version": ("Khôi phục phiên bản ghi chú", "Memory Center"),
    "web.memory.reminder.create": ("Tạo nhắc việc Web", "Memory Center"),
    "web.memory.reminder.update": ("Cập nhật nhắc việc Web", "Memory Center"),
    "web.memory.reminder.complete": ("Hoàn tất nhắc việc Web", "Memory Center"),
    "web.memory.reminder.pause": ("Tạm dừng nhắc việc Web", "Memory Center"),
    "web.memory.reminder.resume": ("Tiếp tục nhắc việc Web", "Memory Center"),
    "web.memory.reminder.cancel": ("Hủy nhắc việc Web", "Memory Center"),
    "web.prompt_library.create": ("Lưu template Prompt Library", "Prompt Library"),
    "web.prompt_library.update": ("Lưu phiên bản template", "Prompt Library"),
    "web.prompt_library.archive": ("Lưu trữ template", "Prompt Library"),
    "web.prompt_library.restore": ("Khôi phục template", "Prompt Library"),
    "web.prompt_library.purge": ("Xóa vĩnh viễn template", "Prompt Library"),
    "web.prompt_library.restore_version": ("Khôi phục phiên bản template", "Prompt Library"),
    "web.prompt_library.duplicate": ("Nhân bản template", "Prompt Library"),
    "web.prompt_library.import": ("Import template Prompt Library", "Prompt Library"),
    "web.prompt_library.gallery_save": ("Lưu seed Prompt Gallery", "Prompt Library"),
    "web.media.collection.create": ("Tạo Audio Library collection", "Audio Library"),
    "web.media.collection.update": ("Lưu phiên bản Audio Library", "Audio Library"),
    "web.media.collection.collection_archived": ("Lưu trữ Audio Library collection", "Audio Library"),
    "web.media.collection.collection_restored": ("Khôi phục Audio Library collection", "Audio Library"),
    "web.media.collection.duplicate": ("Nhân bản Audio Library collection", "Audio Library"),
    "web.media.collection.restore_version": ("Khôi phục phiên bản Audio Library", "Audio Library"),
    "web.media.item.item_attached": ("Gắn audio Asset Vault", "Audio Library"),
    "web.media.item.item_updated": ("Cập nhật audio reference", "Audio Library"),
    "web.media.item.item_detached": ("Gỡ audio reference", "Audio Library"),
    # Creative Content Studio is deliberately Web-native. Its events describe
    # signed-account authoring only; they never imply Bot, provider, payment,
    # Xu, job, publishing or delivery activity.
    "web.content.brief.create": ("Tạo Content Studio brief", "Content Studio"),
    "web.content.brief.update": ("Lưu phiên bản Content Studio brief", "Content Studio"),
    "web.content.brief.brief_archived": ("Lưu trữ Content Studio brief", "Content Studio"),
    "web.content.brief.brief_restored": ("Khôi phục Content Studio brief", "Content Studio"),
    "web.content.brief.duplicate": ("Nhân bản Content Studio brief", "Content Studio"),
    "web.content.brief.restore_version": ("Khôi phục phiên bản Content Studio brief", "Content Studio"),
    "web.content.brief.compose": ("Tạo khung nháp cục bộ", "Content Studio"),
    "web.content.brief.select_variant": ("Chọn content piece", "Content Studio"),
    "web.content.variant.create": ("Thêm content piece", "Content Studio"),
    "web.content.variant.update": ("Lưu phiên bản content piece", "Content Studio"),
    "web.content.variant.variant_archived": ("Lưu trữ content piece", "Content Studio"),
    "web.content.variant.variant_restored": ("Khôi phục content piece", "Content Studio"),
    "web.content.variant.duplicate": ("Nhân bản content piece", "Content Studio"),
    "web.content.variant.restore_version": ("Khôi phục phiên bản content piece", "Content Studio"),
    "asset.delivery": ("Kiểm tra delivery tài sản", "Tài sản"),
}

# Workspace drafts deliberately retain only scalar planning choices that the
# customer typed into a feature form.  File controls, Bot upload/profile IDs,
# quote receipts, idempotency keys and every authority/provider/payment/job
# field remain outside this local store and must be selected again through the
# canonical flow after a draft is resumed.
WORKSPACE_DRAFT_STATES = frozenset({"active", "archived"})
# Assigned once the feature execution candidate set has been declared below.
WORKSPACE_DRAFT_ALLOWED_FEATURES: frozenset[str]
WORKSPACE_DRAFT_ALLOWED_FIELDS = frozenset({
    "request", "prompt", "brief", "script", "instructions", "notes",
    "template", "platform", "format", "duration", "style", "goal",
    "tier", "scene_count", "duration_seconds", "display_name", "mode",
    "song_length_mode", "item_count", "output_format", "target_language",
    "operation", "page_count", "page_range", "speed",
})
WORKSPACE_DRAFT_FORBIDDEN_FIELDS = frozenset({
    "upload_ids", "upload_id", "source", "sample", "audio", "document",
    "documents", "file", "files", "attachment", "voice_profile_id",
    "web_quote_receipt", "quote_receipt", "idempotency_key", "consent",
})
WORKSPACE_DRAFT_FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
WORKSPACE_DRAFT_MAX_ITEMS = 100
WORKSPACE_DRAFT_MAX_INPUT_BYTES = 16_000
# Keep the old all-at-once response shape useful for existing callers while
# allowing the Portal to ask for smaller, bounded history pages.  Active
# drafts are capped at 100; archived history is intentionally pageable.
WORKSPACE_DRAFT_LIST_DEFAULT_LIMIT = 100
WORKSPACE_DRAFT_LIST_MAX_LIMIT = 100
WORKSPACE_DRAFT_LIST_MAX_OFFSET = 10_000


def _public_account_activity_item(row: tuple[Any, ...]) -> dict[str, str]:
    """Project one audit row into non-sensitive, owner-facing activity.

    The stored target/detail fields can reference opaque internal resources or
    security decisions.  They are deliberately never selected here, even for
    the owner, so this route cannot turn audit storage into an account-data or
    Bot-data disclosure API.
    """
    action = str(row[0] or "")
    outcome = str(row[1] or "").lower()
    created_at = str(row[2] or "")[:80]
    if action in ACCOUNT_ACTIVITY_LABELS:
        label, category = ACCOUNT_ACTIVITY_LABELS[action]
    elif action.startswith("admin."):
        label, category = "Thao tác quản trị Web", "Quản trị"
    elif action.startswith("feature."):
        label, category = "Cập nhật workflow Web", "AI Studio"
    elif action.startswith("support."):
        label, category = "Cập nhật hỗ trợ Web", "Hỗ trợ"
    else:
        label, category = "Hoạt động Web", "Tài khoản"
    status_name = "completed" if outcome == "ok" else "guarded" if outcome in {"denied", "failed"} else "read_only"
    return {
        "label": label,
        "category": category,
        "status": status_name,
        "created_at": created_at,
    }

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
# A Web confirm is never enabled merely because a key exists in the broad
# parity registry.  This exact set covers the customer workflows that have a
# draft/estimate/confirm input contract; account, wallet, admin and read-only
# parity routes can never be made executable by an environment typo.
FEATURE_EXECUTION_CANDIDATE_KEYS = frozenset(
    FEATURE_TEXT_REQUIRED | FEATURE_UPLOAD_REQUIRED | FEATURE_TARGET_LANGUAGE_REQUIRED
)
WORKSPACE_DRAFT_ALLOWED_FEATURES = FEATURE_EXECUTION_CANDIDATE_KEYS
FEATURE_TIER_REQUIRED_ON_CONFIRM = frozenset({
    "image_create", "image_edit", "image_upscale", "image_transform", "image_remove_background",
    "video_single", "video_product", "video_trend", "video_text_to_video", "video_quick",
    "video_image_to_video", "video_multiscene", "video_long",
})
FEATURE_VIDEO_SCENE_REQUIRED_ON_CONFIRM = frozenset({
    "video_single", "video_product", "video_trend", "video_text_to_video", "video_quick",
    "video_image_to_video", "video_multiscene", "video_long",
})
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
        # TOTP is a separate Web account-security factor. Its flag never
        # enables Telegram/Bot identity, provider OAuth, wallet/Xu, PayOS,
        # jobs, delivery, notifications or any external authority.
        "totp_mfa_enabled": enabled("WEBAPP_TOTP_MFA_ENABLED", False),
        # Admin ERP is intentionally read-only until a separate canonical
        # write adapter is reviewed.  Keeping this false prevents direct API
        # callers from bypassing the presentation shell's read-only posture.
        "admin_writes_enabled": enabled("WEBAPP_ADMIN_WRITES_ENABLED", False),
        # Creating a canonical job is a separate capability from rendering a
        # draft or estimate.  It stays off until the Bot bridge has a reviewed
        # confirm adapter; provider readiness alone must never unlock it.
        "feature_job_adapter_enabled": enabled("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", False),
        # Asset Vault is a Web-owned private file surface. It is disabled by
        # default until a dedicated persistent volume is configured.
        "asset_vault_enabled": enabled("WEBAPP_ASSET_VAULT_ENABLED", False),
        # Project Package creates a separate, immutable ZIP artifact from
        # Web-owned Project data. It has its own persistent storage boundary
        # and is never a Bot job, provider request, wallet or PayOS action.
        "project_package_enabled": enabled("WEBAPP_PROJECT_PACKAGE_ENABLED", False),
        # Web-native document operations remain off until both private input
        # storage and a separate generated-output volume boundary exist.
        "document_operations_enabled": enabled("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", False),
        # Image decoding is a distinct capability and stays disabled until
        # Pillow plus the bounded private storage contract are deployed.
        "image_to_pdf_enabled": enabled("WEBAPP_IMAGE_TO_PDF_ENABLED", False),
        # Local OCR has a Tesseract binary/language-pack boundary distinct from
        # generic document parsing or Pillow Image → PDF.
        "image_ocr_enabled": enabled("WEBAPP_DOCUMENT_OCR_IMAGE_ENABLED", False),
        # PDF text extraction creates a DOCX artifact with a separate writer
        # runtime. Keep it explicitly fail-closed; it is not OCR or a visual
        # PDF layout converter.
        "pdf_to_word_enabled": enabled("WEBAPP_PDF_TO_WORD_ENABLED", False),
        # Raster PDF delivery has its own PDFium renderer, pixel/ZIP limits
        # and private artifact contract; it must be explicitly enabled.
        "pdf_to_images_enabled": enabled("WEBAPP_PDF_TO_IMAGES_ENABLED", False),
        # Image transforms have their own private output root and bounded
        # decoder runtime. Neither flag grants generic image/bridge execution.
        "image_operations_enabled": enabled("WEBAPP_IMAGE_OPERATIONS_ENABLED", False),
        "image_resize_enabled": enabled("WEBAPP_IMAGE_RESIZE_ENABLED", False),
        # Local Image Enhance uses the same private output boundary but remains
        # independently guarded; it never implies provider-backed AI editing.
        "image_enhance_enabled": enabled("WEBAPP_IMAGE_ENHANCE_ENABLED", False),
        "image_brand_overlay_enabled": enabled("WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED", False),
        # Notes, versions and reminders live in the signed Web session
        # database.  This flag is intentionally independent of Bot, wallet,
        # payment, provider and persistent-file capability flags.
        "memory_center_enabled": enabled("WEBAPP_MEMORY_CENTER_ENABLED", True),
        # Privacy & Data Control is a separate, Web-only authoring-data
        # surface. It remains opt-in because it can create a private direct
        # export attachment and record staged review requests; it never grants
        # Bot/Telegram, wallet, PayOS, provider, job, Asset Vault or deletion
        # authority.
        "data_controls_enabled": enabled("WEBAPP_DATA_CONTROLS_ENABLED", False),
        # Governance Documents is a Web-local Admin ERP module. It requires
        # the existing umbrella switch and a second false-by-default opt-in so
        # a historic Admin navigation default never exposes a new durable
        # internal-record surface accidentally. It does not imply a Bot/Core
        # bridge, wallet/Xu, PayOS, provider, job, publication or notification
        # capability.
        "governance_documents_enabled": (
            enabled("WEBAPP_ADMIN_ERP_ENABLED", True)
            and enabled("WEBAPP_GOVERNANCE_DOCUMENTS_ENABLED", False)
        ),
        # Prompt templates and immutable revisions are owned by the signed
        # Web account. This flag has no Bot bridge, wallet, payment, provider
        # or job-runtime implication.
        "prompt_library_enabled": enabled("WEBAPP_PROMPT_LIBRARY_ENABLED", True),
        # Prompt Studio returns only a transient deterministic blueprint. It
        # does not persist templates or enable Bot/Core Bridge, provider,
        # model, job, wallet/Xu, PayOS, asset, publishing or delivery work.
        "prompt_studio_enabled": enabled("WEBAPP_PROMPT_STUDIO_ENABLED", True),
        # Audio Library & Briefing is a Web-owned organisation surface. It
        # stores only owner-scoped Asset Vault IDs and authored metadata;
        # enabling it never enables provider search, AI music, a Bot job, Xu,
        # PayOS, remote audio fetch or media delivery.
        "music_media_workspace_enabled": enabled("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", True),
        # Creative Content Studio keeps authoring data in the signed Web
        # account database. This independent maintenance switch does not
        # enable Bot execution, an AI/provider, payments, Xu, jobs, publish
        # automation or external delivery.
        "content_studio_enabled": enabled("WEBAPP_CONTENT_STUDIO_ENABLED", True),
        # Channel Strategy profiles are revisioned data owned by the signed
        # Web account. This flag never enables a social-account connection,
        # remote channel lookup, analytics import, Bot/provider execution,
        # job, Xu/PayOS, publishing or delivery.
        "channel_strategy_enabled": enabled("WEBAPP_CHANNEL_STRATEGY_ENABLED", True),
        # Content Handoff records are a private, Web-native coordination
        # ledger.  This maintenance switch does not enable a social account,
        # external recipient, Bot/provider action, job, wallet, payment or
        # publication; `handed_off` has only internal human-handoff meaning.
        "content_handoff_enabled": enabled("WEBAPP_CONTENT_HANDOFF_ENABLED", True),
        # Partner & Lead CRM is private Web-owned business metadata.  It is
        # intentionally not an affiliate/referral, payout, outreach, social
        # or payment capability, even when the switch is enabled.
        "partner_crm_enabled": enabled("WEBAPP_PARTNER_CRM_ENABLED", True),
        # Trend Research is a signed-session, request-only manual checklist.
        # This maintenance switch never enables live search, social scraping,
        # Bot/provider work, jobs, wallet/Xu, PayOS, assets or publishing.
        "trend_research_enabled": enabled("WEBAPP_TREND_RESEARCH_ENABLED", True),
        # Media Factory Blueprint is the signed, request-only Web conversion
        # of the Bot's static content/video-pack checklist. It does not enable
        # live search, provider/Bot execution, jobs, Xu/PayOS, output or
        # publishing.
        "media_factory_enabled": enabled("WEBAPP_MEDIA_FACTORY_ENABLED", True),
        # Voice Studio stores Web-owned profile/script metadata and local cue
        # sheets only.  This switch never enables bridge TTS/clone/preview,
        # provider calls, Bot jobs, Xu, PayOS or output delivery.
        "voice_studio_enabled": enabled("WEBAPP_VOICE_STUDIO_ENABLED", True),
        # Video Production Studio is a signed-account planning surface. This
        # switch never enables an execution engine, external runtime, wallet
        # or payment action.
        "video_studio_enabled": enabled("WEBAPP_VIDEO_STUDIO_ENABLED", True),
        "subtitle_studio_enabled": enabled("WEBAPP_SUBTITLE_STUDIO_ENABLED", True),
        # Image Creative Studio is authoring-only: it stores directions and
        # safe Asset Vault UUID references, never an image operation or
        # external execution capability.
        "image_studio_enabled": enabled("WEBAPP_IMAGE_STUDIO_ENABLED", True),
        # Document & PDF Workspace is authoring-only: it holds signed-account
        # briefs, plan metadata and safe Asset Vault UUID references.  This
        # flag never enables the separate document executor, OCR/translation,
        # Bot/provider calls, jobs, wallet, payment or output delivery.
        "document_workspace_enabled": enabled("WEBAPP_DOCUMENT_WORKSPACE_ENABLED", True),
        # Conversation Workspace persists only customer-authored local text
        # and revision metadata. This flag never exposes legacy Gemini, a
        # Bot/Core Bridge chat, provider stream, Xu, payment, job or output.
        "chat_workspace_enabled": enabled("WEBAPP_CHAT_WORKSPACE_ENABLED", True),
        # This is only the operator intent for a future reviewed Web-native
        # Chat adapter.  The Chat Run route still fails closed and records a
        # guarded receipt until such an adapter is separately implemented.
        "chat_execution_enabled": enabled("WEBAPP_CHAT_EXECUTION_ENABLED", False),
        # Analytics Workspace owns only signed-account, manually entered
        # observations and deterministic local comparisons. This independent
        # maintenance flag never enables platform data, Bot/provider calls,
        # wallet, PayOS, jobs, publishing, AI insight or report delivery.
        "analytics_workspace_enabled": enabled("WEBAPP_ANALYTICS_WORKSPACE_ENABLED", True),
        # A finalized manual CSV attachment is intentionally a second,
        # fail-closed switch.  It is not the Bot's canonical campaign report,
        # a platform export, a stored Asset Vault artifact or a delivery job.
        "analytics_workspace_export_enabled": enabled("WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED", False),
        # Workboard is an independent, signed-account coordination surface.
        # The flag can place that private Web-owned feature into maintenance
        # without enabling Bot work, providers, wallet/Xu, PayOS, jobs,
        # publishing, notifications or any external automation.
        "workboard_enabled": enabled("WEBAPP_WORKBOARD_ENABLED", True),
        # Support cases/messages are owned by signed Web accounts.  The flag
        # is independent from the Bot ticket bridge and makes a deliberate
        # maintenance posture observable to the Portal without hiding the
        # legacy bridge compatibility routes.
        "support_desk_enabled": enabled("WEBAPP_SUPPORT_DESK_ENABLED", True),
        # Controlled Operations Autopilot is independent of the Bot bridge.
        # These public booleans reveal only the maintenance posture, never a
        # scheduler endpoint, secret, incident fingerprint or approval data.
        "autopilot_enabled": enabled("WEBAPP_AUTOPILOT_ENABLED", False),
        "autopilot_safe_remediation_enabled": enabled("WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED", False),
        # Inbox records are private Web metadata.  Automation is a separate
        # opt-in scheduler and never means Telegram/email/web-push delivery.
        "notification_center_enabled": enabled("WEBAPP_NOTIFICATION_CENTER_ENABLED", True),
        "notification_automation_enabled": enabled("WEBAPP_NOTIFICATION_AUTOMATION_ENABLED", False),
        # Reliability Follow-up is a separately opt-in, Web-native metadata
        # queue. It never grants external repair/provider/payment authority.
        "reliability_followup_enabled": enabled("WEBAPP_RELIABILITY_FOLLOWUP_ENABLED", False),
        "pwa_enabled": enabled("WEBAPP_PWA_ENABLED", False),
    }


def _web_feature_job_adapter_keys() -> frozenset[str]:
    """Return the explicit, reviewed feature confirm adapters only.

    ``WEBAPP_FEATURE_JOB_ADAPTER_ENABLED`` is a global circuit breaker, not a
    blanket approval for all parity routes.  The companion comma-separated
    allowlist must name each canonical feature key whose Bot-owned confirm
    adapter has passed its quote, ledger, idempotency and delivery tests.
    Unknown/non-executable values fail closed instead of broadening access.
    """
    raw = os.environ.get("WEBAPP_FEATURE_JOB_ADAPTERS", "")
    requested = {item.strip().lower() for item in raw.split(",") if item.strip()}
    return frozenset(
        feature
        for feature in requested
        if feature in FEATURE_EXECUTION_CANDIDATE_KEYS and feature in FEATURE_BY_KEY
    )


def _web_feature_execution_available(feature: str | None = None) -> bool:
    """Whether a reviewed Web-to-canonical-job adapter exists for confirms.

    Each condition is deliberately required.  A provider flag only permits a
    reviewed server-to-server bridge call; it does not prove that this Bot
    deployment accepts Web confirms.  The adapter flag must therefore remain
    false until that endpoint independently verifies the canonical quote,
    owner, idempotency and charge/job lifecycle.
    """
    flags = _flags()
    common_ready = bool(
        flags["copyfast_enabled"]
        and flags["provider_calls_enabled"]
        and flags["feature_job_adapter_enabled"]
        and bridge_configured()
    )
    if not common_ready:
        return False
    adapter_keys = _web_feature_job_adapter_keys()
    if feature is None:
        return bool(adapter_keys)
    return str(feature or "").strip() in adapter_keys


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


def _feature_input_digest(values: dict[str, Any]) -> str:
    """Hash validated feature input without retaining prompt/file metadata.

    A receipt is a Web-session freshness check, not a Bot quote.  HMAC keeps
    even a low-entropy prompt from being reversible from the Web-only SQLite
    table while preserving a deterministic binding for the confirm request.
    """
    try:
        encoded = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Dữ liệu feature không thể tạo receipt an toàn") from exc
    secret = os.environ.get("WEB_FEATURE_QUOTE_HMAC_SECRET", os.environ.get("WEB_SESSION_SECRET", "")).encode("utf-8")
    if not secret:
        # App startup already requires a session secret. Keep this explicit
        # for isolated calls so a missing secret cannot downgrade to SHA-256.
        raise HTTPException(status_code=503, detail="Web chưa có secret để bảo vệ estimate receipt")
    return hmac.new(secret, encoded, hashlib.sha256).hexdigest()


def _feature_quote_expiry(response: dict) -> str:
    """Return a short, timezone-aware receipt expiry from a safe estimate.

    A reviewed Bot may include an explicit quote expiry.  The Web receipt can
    only shorten it, never extend it; absent an explicit value it is capped to
    a ten-minute browser-session freshness window and still has no pricing
    authority.
    """
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(seconds=FEATURE_QUOTE_RECEIPT_TTL_SECONDS)
    data = response.get("data") if isinstance(response, dict) and isinstance(response.get("data"), dict) else {}
    estimate = data.get("estimate") if isinstance(data.get("estimate"), dict) else {}
    supplied = [
        data.get("quote_valid_until"), data.get("quote_expires_at"),
        estimate.get("quote_valid_until"), estimate.get("quote_expires_at"), estimate.get("expires_at"),
    ]
    for value in supplied:
        if value is None or value == "":
            continue
        if not isinstance(value, str) or len(value) > 80:
            return ""
        try:
            candidate = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return ""
        if candidate.tzinfo is None:
            return ""
        candidate = candidate.astimezone(timezone.utc)
        if candidate <= now:
            return ""
        expiry = min(expiry, candidate)
    return expiry.isoformat(timespec="seconds")


def _estimate_can_issue_feature_receipt(response: dict) -> bool:
    data = response.get("data") if isinstance(response, dict) and isinstance(response.get("data"), dict) else {}
    estimate = data.get("estimate") if isinstance(data.get("estimate"), dict) else {}
    return bool(
        isinstance(response, dict)
        and response.get("ok") is True
        and response.get("status") == "awaiting_confirm"
        and estimate.get("available") is True
        # A quote that only lists canonical tiers/scenes is useful planning,
        # but it is not a confirmable quote. Do not mint a browser receipt
        # until the customer has selected the Bot-required input and asked for
        # a fresh estimate.
        and estimate.get("tier_required") is not True
        and estimate.get("scene_count_required") is not True
    )


def _issue_feature_quote_receipt(response: dict, *, account: dict, session_id: str, feature: str, values: dict[str, Any]) -> dict:
    """Attach one opaque, session-bound receipt after a canonical estimate.

    The raw token exists only in this API response and browser memory. SQLite
    holds its hash plus bindings/expiry; it never holds a prompt, quote, job,
    provider, payment, asset or output value.
    """
    if not _estimate_can_issue_feature_receipt(response):
        return response
    account_id = str(account.get("id") or "")
    canonical_user_id = str(account.get("canonical_user_id") or "")
    if not account_id or not session_id or not canonical_user_id:
        return response
    expiry = _feature_quote_expiry(response)
    if not expiry:
        return response
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    input_digest = _feature_input_digest(values)
    ensure_copyfast_schema()
    with transaction() as conn:
        now = utc_now()
        conn.execute("DELETE FROM web_feature_quote_receipts WHERE expires_at<=?", (now,))
        conn.execute(
            """INSERT INTO web_feature_quote_receipts
               (token_hash, account_id, session_id, canonical_user_id, feature_key, input_digest, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (token_hash, account_id, session_id, canonical_user_id, feature, input_digest, expiry, now),
        )
    result = dict(response)
    data = dict(response.get("data") or {})
    data["web_quote_receipt"] = token
    result["data"] = data
    return result


def _claim_feature_quote_receipt(*, receipt: str, account: dict, session_id: str, feature: str, values: dict[str, Any], idempotency_key: str) -> str:
    """Atomically bind an estimate receipt to exactly one confirm key.

    The same key may retry an ambiguous bridge call; any other key is refused
    so two browser requests cannot turn one estimate into two Bot jobs.
    """
    if not FEATURE_QUOTE_RECEIPT_PATTERN.fullmatch(receipt or ""):
        return "missing"
    account_id = str(account.get("id") or "")
    canonical_user_id = str(account.get("canonical_user_id") or "")
    if not account_id or not session_id or not canonical_user_id:
        return "missing"
    token_hash = hashlib.sha256(receipt.encode("utf-8")).hexdigest()
    input_digest = _feature_input_digest(values)
    key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    now = utc_now()
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_feature_quote_receipts WHERE expires_at<=?", (now,))
        row = conn.execute(
            """SELECT account_id, session_id, canonical_user_id, feature_key, input_digest,
                      expires_at, claimed_key_hash, consumed_at
                 FROM web_feature_quote_receipts WHERE token_hash=?""",
            (token_hash,),
        ).fetchone()
        if not row:
            return "missing"
        if (
            row[0] != account_id or row[1] != session_id or row[2] != canonical_user_id
            or row[3] != feature or not hmac.compare_digest(str(row[4] or ""), input_digest)
            or str(row[5] or "") <= now
        ):
            return "missing"
        claimed_key_hash = str(row[6] or "")
        if claimed_key_hash:
            return "claimed" if hmac.compare_digest(claimed_key_hash, key_hash) else "used"
        updated = conn.execute(
            """UPDATE web_feature_quote_receipts
               SET claimed_key_hash=?, claimed_at=?
               WHERE token_hash=? AND claimed_key_hash IS NULL AND consumed_at IS NULL AND expires_at>?""",
            (key_hash, now, token_hash, now),
        )
        return "claimed" if updated.rowcount == 1 else "used"


def _settle_feature_quote_receipt(*, receipt: str, idempotency_key: str, accepted: bool) -> None:
    """Consume an accepted confirm; release only a known rejected attempt."""
    if not FEATURE_QUOTE_RECEIPT_PATTERN.fullmatch(receipt or ""):
        return
    token_hash = hashlib.sha256(receipt.encode("utf-8")).hexdigest()
    key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    ensure_copyfast_schema()
    with transaction() as conn:
        if accepted:
            conn.execute(
                """UPDATE web_feature_quote_receipts SET consumed_at=?
                   WHERE token_hash=? AND claimed_key_hash=? AND consumed_at IS NULL""",
                (utc_now(), token_hash, key_hash),
            )
        else:
            conn.execute(
                """UPDATE web_feature_quote_receipts
                   SET claimed_key_hash=NULL, claimed_at=NULL
                   WHERE token_hash=? AND claimed_key_hash=? AND consumed_at IS NULL""",
                (token_hash, key_hash),
            )


def _feature_quote_required_response(state: str) -> dict:
    if state == "used":
        return envelope(
            False,
            "Estimate này đã được dùng cho một yêu cầu xác nhận khác. Hãy tạo estimate canonical mới.",
            status_name="guarded",
            error_code="FEATURE_ESTIMATE_ALREADY_USED",
        )
    return envelope(
        False,
        "Hãy tạo estimate canonical mới trong phiên hiện tại trước khi xác nhận. Web không chấp nhận xác nhận trực tiếp từ browser.",
        status_name="guarded",
        error_code="FEATURE_ESTIMATE_REQUIRED",
    )


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
    try:
        parsed = urlparse(value)
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except (TypeError, ValueError):
        return ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or port not in {None, 443}
        or parsed.fragment
        or (hostname != "pay.payos.vn" and not hostname.endswith(".payos.vn"))
    ):
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


def _record_admin_write_audit(account: dict, request: Request, action: str, target: str, result: dict) -> None:
    """Record a sanitized Web-side write decision alongside Bot-side audit.

    The target and coarse outcome are enough to correlate a Web intent with
    the canonical Bot audit trail. Never put bridge/provider responses,
    payment references, or customer data into this Web event.
    """
    status_name = str(result.get("status") or "guarded") if isinstance(result, dict) else "guarded"
    outcome = "ok" if isinstance(result, dict) and result.get("ok") is True else "denied"
    ensure_copyfast_schema()
    with transaction() as conn:
        _record_audit(
            conn,
            account_id=str(account.get("id") or "") or None,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action=action,
            request_id=_request_id(request) or str(uuid.uuid4()),
            target=target,
            outcome=outcome,
            detail=f"web admin write response: {status_name[:80]}",
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


def _project_feature_tracking(value: Any, *, canonical_feature: Any) -> dict[str, str]:
    """Allow one future Bot-issued job reference through the feature boundary.

    A successful canonical confirm may eventually return a tiny tracking
    reference.  It is deliberately *not* inferred from a response ID, draft,
    output, provider handle, or timestamp: the bridge must explicitly opt in
    with ``tracking`` and prove that it describes the same feature.  The
    customer can then navigate to the existing ownership-checked Job Center;
    no delivery URL or job metadata is exposed from this planning response.
    """
    if not isinstance(value, dict):
        return {}
    feature = str(value.get("feature") or "").strip()
    expected = str(canonical_feature or "").strip()
    tracking_id = str(value.get("id") or "").strip()
    status = str(value.get("status") or "").strip().lower()
    if (
        not feature
        or feature != expected
        or feature not in FEATURE_BY_KEY
        or not CANONICAL_IDENTIFIER_PATTERN.fullmatch(tracking_id)
        or status not in FEATURE_CONFIRM_ACCEPTED_STATUSES
    ):
        return {}
    return {"id": tracking_id, "status": status, "feature": feature}


def _project_feature_response(value: dict[str, Any]) -> dict[str, Any]:
    """Expose only planning, staging and explicit safe tracking metadata."""
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
    tracking = _project_feature_tracking(value.get("tracking"), canonical_feature=value.get("feature"))
    if tracking:
        result["tracking"] = tracking
    return result


def _project_surface_data(data: Any, surface: str, *, allow_admin_user_refs: bool = False) -> dict[str, Any]:
    # A Bot-issued checkout is the sole, narrow exception to generic response
    # redaction. Keep the original mapping only long enough to validate one
    # URL against the fixed PayOS allowlist; every other browser field still
    # comes from the recursively redacted representation below.
    raw_value = data if isinstance(data, dict) else {}
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
        checkout = _safe_payos_checkout(raw_value.get("checkout_url") or raw_value.get("payment_url") or raw_value.get("url"))
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
    text = f"{subject}\n{detail}"
    if TICKET_MANUAL_PAYMENT_PROOF_PATTERN.search(text):
        raise HTTPException(
            status_code=422,
            detail="Nạp thủ công không nhận bill, TXID, số tài khoản hoặc QR trong Web App. Hãy mở Bot đã liên kết và dùng /thucong để đối soát an toàn.",
        )
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


def _feature_input_contract_error(feature: str, values: dict[str, Any], *, action: str = "draft") -> str:
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
    # Image → PDF is now a Web-native private operation with a different
    # ownership/storage/output contract. Reject direct calls to the older
    # generic feature path before they can reach the bridge and accidentally
    # create a second customer journey or a Bot-owned artifact.
    document_operation = str(values.get("operation") or "").strip().lower().replace("-", "_")
    if feature in {"documents", "documents_pdf"} and document_operation == "image_to_pdf":
        return "web_native_image_to_pdf_required"
    if feature in {"documents", "documents_pdf"} and document_operation == "pdf_to_word":
        return "web_native_pdf_to_word_required"
    if feature in {"documents", "documents_pdf"} and document_operation == "pdf_to_images":
        return "web_native_pdf_to_images_required"
    # Resize & Aspect Studio owns an immutable Asset Vault → private PNG
    # contract. Never route a crafted generic image request to the bridge: it
    # would create a second lifecycle and could make a Bot/provider artifact
    # look like the bounded local Web-native resize operation.
    if feature == "image_resize" or (
        feature in {"image_create", "image_edit", "image_upscale", "image_transform", "image_remove_background"}
        and document_operation in {"image_resize", "resize", "aspect_resize"}
    ):
        return "web_native_image_resize_required"
    if feature == "image_edit":
        return "web_native_image_enhance_required"
    if feature == "image_brand_overlay":
        return "web_native_image_brand_overlay_required"
    if feature in {"documents", "documents_pdf"}:
        return "document_operation_invalid"
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
    if action == "confirm" and feature in FEATURE_TIER_REQUIRED_ON_CONFIRM:
        tier = str(values.get("tier") or "").strip()
        if not CANONICAL_IDENTIFIER_PATTERN.fullmatch(tier):
            return "tier_required"
    if action == "confirm" and feature in FEATURE_VIDEO_SCENE_REQUIRED_ON_CONFIRM:
        if not _whole_number_in_range(values.get("scene_count"), 1, 20):
            return "scene_count_required"
    return ""


def _feature_input_contract_response(feature: str, reason: str) -> dict:
    messages = {
        "authority_field_not_allowed": "Yêu cầu feature có trường hệ thống không được phép; Web không nhận identity, Xu, provider, job hoặc output từ browser.",
        "upload_ids_invalid": "Tham chiếu tệp staging không hợp lệ. Hãy chọn lại tệp để Web gửi qua luồng canonical.",
        "web_native_image_to_pdf_required": "Ảnh sang PDF là tiện ích Web-native riêng tư. Hãy dùng /documents/image-to-pdf để tạo output đã được kiểm tra.",
        "web_native_pdf_to_word_required": "PDF có text → Word là tiện ích Web-native riêng tư. Hãy dùng /documents/pdf-to-word; PDF scan hoặc layout ảnh không được giả OCR.",
        "web_native_pdf_to_images_required": "PDF → ảnh là tiện ích Web-native riêng tư. Hãy dùng /documents/pdf-to-images để nhận PNG hoặc ZIP đã được kiểm tra.",
        "web_native_image_resize_required": "Resize & Aspect Studio là tiện ích Web-native riêng tư. Hãy dùng /image/resize để tạo PNG đã được kiểm tra; không gọi Bot, provider hoặc AI upscale.",
        "web_native_image_enhance_required": "Image Enhance Studio là tiện ích Web-native riêng tư. Hãy dùng /image/edit để chỉnh màu/làm nét cơ bản trên Asset Vault; không gọi Bot, provider hoặc AI edit.",
        "web_native_image_brand_overlay_required": "Brand Overlay Studio là tiện ích Web-native riêng tư. Hãy dùng /image/brand-overlay để tạo PNG đã kiểm tra từ Asset Vault; không gọi Bot, provider hoặc AI edit.",
        "document_operation_invalid": "Công cụ PDF không hợp lệ. Hãy chọn workflow PDF private phù hợp trong Document Studio.",
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
        "tier_required": "Hãy chọn tier canonical rồi tạo estimate mới trước khi xác nhận job.",
        "scene_count_required": "Video cần số cảnh nguyên từ 1 đến 20 trước khi xác nhận job canonical.",
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
    # This opaque, session-bound nonce is generated by the Web server only
    # after a successful estimate.  It is never forwarded to Bot/provider
    # code and cannot set price, Xu, job, payment or output state.
    web_quote_receipt: str = Field(default="", max_length=160)


class PaymentRequest(BaseModel):
    package_id: str = Field(default="", max_length=120)
    payment_type: str = Field(default="topup_xu", max_length=80)
    idempotency_key: str = Field(min_length=12, max_length=160)


class FreezeRequest(BaseModel):
    frozen: bool
    note: str = Field(default="", max_length=300)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("note")
    @classmethod
    def require_operation_note(cls, value: str) -> str:
        """Keep an audit-worthy reason on the server, not just in portal JS."""
        note = str(value or "").strip()
        if not 5 <= len(note) <= 300:
            raise ValueError("Ghi chú vận hành cần từ 5 đến 300 ký tự")
        return note


class TicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=180)
    detail: str = Field(min_length=3, max_length=4000)
    idempotency_key: str = Field(min_length=12, max_length=160)


def _campaign_text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    """Normalize human planning text without turning it into HTML or an audit payload."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if "\x00" in text or any(ord(character) < 32 for character in text):
        raise ValueError(f"{label} chứa ký tự không hợp lệ")
    if allow_empty and not text:
        return ""
    if not minimum <= len(text) <= maximum:
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự")
    return text


def _campaign_destination_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not 8 <= len(raw) <= 1_024:
        raise ValueError("Liên kết đích cần từ 8 đến 1024 ký tự")
    try:
        parsed = urlparse(raw)
        hostname = (parsed.hostname or "").rstrip(".").lower()
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("Liên kết đích không hợp lệ") from exc
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or not hostname
        or parsed.username
        or parsed.password
        or port not in {None, 443}
    ):
        raise ValueError("Liên kết đích phải là HTTPS công khai, không kèm thông tin đăng nhập")
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise ValueError("Liên kết đích phải trỏ tới host công khai")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise ValueError("Liên kết đích phải trỏ tới host công khai")
    return raw


def _campaign_scheduled_for(value: Any) -> str:
    """Validate an inert local planning timestamp; it never schedules publishing."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?", raw):
        raise ValueError("Mốc lịch cần ở định dạng ngày giờ cục bộ hợp lệ")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Mốc lịch cần ở định dạng ngày giờ cục bộ hợp lệ") from exc
    if parsed.tzinfo is not None or not 2000 <= parsed.year <= 2100:
        raise ValueError("Mốc lịch cần ở định dạng ngày giờ cục bộ hợp lệ")
    return parsed.replace(second=0, microsecond=0).isoformat(timespec="minutes")


def _campaign_plan_id(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="Mã kế hoạch không hợp lệ") from exc


def _campaign_schedule_intent_id(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="Mã lịch nhắc Campaign không hợp lệ") from exc


def _campaign_plan_public(row: tuple[Any, ...]) -> dict[str, Any]:
    """Project only the signed account's Web-owned planning fields to the browser."""
    return {
        "id": str(row[0]),
        "title": str(row[1]),
        "destination_url": str(row[2]),
        "platform": str(row[3]),
        "objective": str(row[4]),
        "scheduled_for": str(row[5] or ""),
        "approval_status": str(row[6]),
        "review_note": str(row[7] or ""),
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "revision": max(1, int(row[10] or 1)),
    }


def _campaign_plan_source_row(conn: Any, *, plan_id: str, account_id: str) -> tuple[Any, ...] | None:
    """Read one owner-scoped source row for an explicit schedule intent.

    This projection is intentionally private to server-side source binding.
    The route never returns its title, URL or review text through the intent
    list/receipt and the Notification scheduler re-reads it independently at
    materialization time.
    """
    return conn.execute(
        """SELECT id, account_id, title, destination_url, platform, objective, scheduled_for,
                  approval_status, review_note, created_at, updated_at, revision
           FROM web_campaign_plans WHERE id=? AND account_id=?""",
        (plan_id, account_id),
    ).fetchone()


def _campaign_schedule_actor_allowed(account: dict[str, Any]) -> bool:
    """Only accept a server-resolved signed account role for local schedules."""
    return bool(str(account.get("id") or "").strip()) and str(account.get("role") or "user").strip().lower() in {"user", "admin"}


def _campaign_schedule_source_coordinates(plan: tuple[Any, ...] | None) -> tuple[int, str] | None:
    """Return only current revision + digest for an active local Campaign."""
    if not plan or str(plan[7]) == "archived":
        return None
    try:
        revision = int(plan[11])
    except (IndexError, TypeError, ValueError):
        return None
    if revision < 1:
        return None
    digest = campaign_source_hash(
        title=plan[2],
        destination_url=plan[3],
        platform=plan[4],
        objective=plan[5],
        scheduled_for=plan[6],
        approval_status=plan[7],
        review_note=plan[8],
    )
    return (revision, digest) if SNAPSHOT_HASH_PATTERN.fullmatch(digest) else None


def _guard_active_campaign_schedule_intents(
    conn: Any, *, plan_id: str, account_id: str, now: str,
) -> int:
    """Fence active private intents whenever their Campaign source changes.

    This runs in the same local transaction as a Campaign edit/status change.
    It gives the owner a truthful, actionable reconfirmation state while the
    original future trigger is still valid.  It never changes the Campaign,
    Calendar marker, trigger time, Inbox, publish state, Bot or any external
    system.  The notification tick retains its independent digest check as a
    defence against out-of-band database changes.
    """
    updated = conn.execute(
        """UPDATE web_campaign_schedule_intents
           SET state='guarded', revision=revision+1, updated_at=?, guarded_at=?,
               guard_code='CAMPAIGN_SCHEDULE_SOURCE_CHANGED'
           WHERE plan_id=? AND account_id=? AND state='active'""",
        (now, now, plan_id, account_id),
    )
    return max(0, int(updated.rowcount or 0))


def _campaign_schedule_intent_row(
    conn: Any, *, intent_id: str, plan_id: str, account_id: str,
) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, account_id, plan_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                  trigger_at, state, revision, created_at, updated_at, dispatched_at, guarded_at, guard_code,
                  cancelled_at, created_by_account_id
           FROM web_campaign_schedule_intents
           WHERE id=? AND plan_id=? AND account_id=?""",
        (intent_id, plan_id, account_id),
    ).fetchone()


def _campaign_schedule_intent_public(row: tuple[Any, ...]) -> dict[str, Any]:
    """Return intent metadata without a Campaign source copy or source hash."""
    state = str(row[8])
    return {
        "id": str(row[0]), "plan_id": str(row[2]), "source_revision": int(row[3]),
        "trigger_local_at": str(row[5]), "timezone": str(row[6]), "trigger_at": str(row[7]),
        "state": state, "revision": int(row[9]), "created_at": str(row[10]), "updated_at": str(row[11]),
        "dispatched_at": str(row[12]) if row[12] else None,
        "guarded_at": str(row[13]) if row[13] else None,
        "guard_code": str(row[14]) if row[14] else None,
        "cancelled_at": str(row[15]) if row[15] else None,
        "reconfirmation_required": state == "guarded",
        "delivery": "in_app_record_only",
    }


def _campaign_schedule_boundary(**extra: Any) -> dict[str, Any]:
    """State the narrow Web-only boundary for every schedule response."""
    return {
        "execution": "web_native_in_app_record_intent_only",
        "data_origin": "signed_account_campaign_plan_only",
        "source_content_copied": False,
        "scheduled_for_is_inert": True,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "publish_action_created": False,
        "wallet_mutated": False,
        "payment_processed": False,
        "job_created": False,
        "notification_sent": False,
        "delivery": "in_app_record_only",
        **extra,
    }


def _campaign_schedule_guarded(message: str, code: str) -> dict[str, Any]:
    return envelope(False, message, data=_campaign_schedule_boundary(), status_name="guarded", error_code=code)


def _campaign_schedule_safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Persist a replay-safe receipt without Campaign title/URL/review text."""
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _campaign_schedule_boundary()
    intent = source.get("schedule_intent")
    if isinstance(intent, dict) and isinstance(intent.get("id"), str):
        data["schedule_intent"] = {
            "id": str(intent["id"]),
            "plan_id": str(intent.get("plan_id") or ""),
            "source_revision": int(intent.get("source_revision") or 0),
            "trigger_at": str(intent.get("trigger_at") or ""),
            "timezone": str(intent.get("timezone") or ""),
            "state": str(intent.get("state") or ""),
            "revision": int(intent.get("revision") or 0),
            "delivery": "in_app_record_only",
        }
    for key in ("schedule_intent_recorded",):
        if key in source:
            data[key] = source[key]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu lịch nhắc Campaign."),
        data=data,
        status_name=str(response.get("status") or "completed"),
    )


def _campaign_schedule_idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Run a local schedule write exactly once for a matching request body."""
    ensure_copyfast_schema()
    cutoff = (datetime.now(timezone.utc) - CAMPAIGN_SCHEDULE_IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at<?", ("campaign-schedule:%", cutoff))
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored_fingerprint = str(existing[1] or "")
            if not stored_fingerprint or not hmac.compare_digest(stored_fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu lịch nhắc khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt lịch nhắc Campaign không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt lịch nhắc Campaign không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"campaign-schedule:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= CAMPAIGN_SCHEDULE_MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _campaign_schedule_guarded(
                "Kho receipt lịch nhắc tạm thời đang đầy. Vui lòng thử lại sau.",
                "CAMPAIGN_SCHEDULE_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _campaign_schedule_safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _campaign_calendar_month(value: Any) -> tuple[str, str, str]:
    """Return an explicit local planning-month range without timezone conversion.

    ``scheduled_for`` deliberately stores an inert, local planning timestamp
    (``YYYY-MM-DDTHH:MM``), rather than a publisher/reminder timestamp.  Its
    normalized lexical order is therefore also the correct SQLite range order.
    Requiring a narrow month value keeps the browser from requesting an
    accidental all-history calendar or a provider/canonical schedule.
    """
    raw = str(value or "").strip()
    match = CAMPAIGN_CALENDAR_MONTH_PATTERN.fullmatch(raw)
    if not match:
        raise HTTPException(status_code=422, detail="Tháng Calendar cần ở định dạng YYYY-MM")
    year, month = int(match.group(1)), int(match.group(2))
    if not 2000 <= year <= 2100 or not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="Tháng Calendar nằm ngoài phạm vi hợp lệ")
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return raw, start.isoformat(timespec="minutes"), end.isoformat(timespec="minutes")


def _campaign_calendar_filter(value: Any, *, label: str, allowed: frozenset[str]) -> str:
    normalized = str(value or "all").strip().lower()
    if normalized == "all":
        return normalized
    if normalized not in allowed:
        raise HTTPException(status_code=422, detail=f"Bộ lọc {label} Calendar không hợp lệ")
    return normalized


def _campaign_calendar_public(row: tuple[Any, ...]) -> dict[str, str]:
    """Return the narrow projection required by the private Calendar window.

    A Calendar card needs neither the CTA URL nor a self-review note. Keeping
    those fields off this list response makes the read-only agenda smaller and
    prevents it from becoming an alternate campaign-detail surface.
    """
    return {
        "id": str(row[0]),
        "title": str(row[1]),
        "platform": str(row[2]),
        "objective": str(row[3]),
        "scheduled_for": str(row[4]),
        "approval_status": str(row[5]),
        "updated_at": str(row[6]),
    }


def _workspace_draft_id(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="Mã bản nháp không hợp lệ") from exc


def _workspace_draft_feature(value: Any) -> str:
    feature = str(value or "").strip()
    if feature not in WORKSPACE_DRAFT_ALLOWED_FEATURES or feature not in FEATURE_BY_KEY:
        raise HTTPException(status_code=422, detail="Workflow này không hỗ trợ lưu bản nháp Web")
    return feature


def _workspace_draft_title(value: Any, feature: str) -> str:
    fallback = f"Bản nháp · {FEATURE_BY_KEY[feature].title}"
    title = re.sub(r"\s+", " ", str(value or "")).strip() or fallback
    if "\x00" in title or any(ord(character) < 32 for character in title) or not 3 <= len(title) <= 120:
        raise HTTPException(status_code=422, detail="Tên bản nháp cần từ 3 đến 120 ký tự hợp lệ")
    return title


def _workspace_draft_list_state(value: str | None, *, include_archived: bool) -> str:
    """Normalize the metadata-only list state without changing legacy reads."""
    if value is None:
        # Legacy callers used `include_archived=true`; keep that exact
        # behavior while allowing the newer explicit state filter to win.
        return "all" if include_archived else "active"
    state = str(value or "").strip().lower()
    if state not in {"all", *WORKSPACE_DRAFT_STATES}:
        raise HTTPException(status_code=422, detail="Trạng thái lọc bản nháp không hợp lệ")
    return state


def _workspace_draft_list_feature(value: str | None) -> str:
    """Accept only a known Web-draft workflow key as a list filter."""
    feature = str(value or "").strip()
    return _workspace_draft_feature(feature) if feature else ""


def _workspace_draft_list_query(value: str | None) -> str:
    """Keep an ephemeral list query small and safe for an HTTP request path."""
    query = re.sub(r"\s+", " ", str(value or "")).strip()
    if "\x00" in query or any(ord(character) < 32 for character in query) or len(query) > 100:
        raise HTTPException(status_code=422, detail="Từ khóa tìm bản nháp tối đa 100 ký tự hợp lệ")
    # The query is never persisted/audited, but reject credential/payment-like
    # text before it can become an accidental request-log disclosure.
    if query and TICKET_MANUAL_PAYMENT_PROOF_PATTERN.search(query):
        raise HTTPException(status_code=422, detail="Từ khóa tìm bản nháp không nhận chứng từ hoặc dữ liệu thanh toán")
    if query and _ticket_contains_sensitive_data(query, query):
        raise HTTPException(status_code=422, detail="Từ khóa tìm bản nháp không nhận secret, token hoặc số thẻ")
    return query


def _workspace_draft_input(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or not 1 <= len(value) <= 30:
        raise HTTPException(status_code=422, detail="Bản nháp cần từ 1 đến 30 trường planning an toàn")
    normalized: dict[str, str] = {}
    for raw_name, raw_value in value.items():
        name = str(raw_name or "").strip()
        if (
            not WORKSPACE_DRAFT_FIELD_PATTERN.fullmatch(name)
            or name not in WORKSPACE_DRAFT_ALLOWED_FIELDS
            or name in WORKSPACE_DRAFT_FORBIDDEN_FIELDS
            or "".join(character for character in name.lower() if character.isalnum()) in FEATURE_AUTHORITY_FIELDS_NORMALIZED
        ):
            raise HTTPException(status_code=422, detail="Bản nháp không nhận trường hệ thống, file, upload, quote, profile hoặc authority")
        if not isinstance(raw_value, str):
            raise HTTPException(status_code=422, detail="Bản nháp chỉ lưu giá trị văn bản/planning, không lưu object hoặc tệp")
        text = raw_value.strip()
        if not text:
            continue
        if "\x00" in text or len(text) > 4_000:
            raise HTTPException(status_code=422, detail="Một trường bản nháp chứa ký tự hoặc độ dài không hợp lệ")
        normalized[name] = text
    if not normalized:
        raise HTTPException(status_code=422, detail="Hãy nhập ít nhất một giá trị planning trước khi lưu bản nháp")
    encoded = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > WORKSPACE_DRAFT_MAX_INPUT_BYTES:
        raise HTTPException(status_code=413, detail="Bản nháp vượt quá giới hạn dữ liệu an toàn")
    return normalized


def _assert_safe_workspace_draft_content(title: str, values: dict[str, str]) -> None:
    content = "\n".join([title, *values.values()])
    if TICKET_MANUAL_PAYMENT_PROOF_PATTERN.search(content):
        raise HTTPException(status_code=422, detail="Bản nháp không nhận bill, TXID, số tài khoản hoặc QR thanh toán. Hãy giữ đối soát thủ công trong Bot.")
    if _ticket_contains_sensitive_data(title, content):
        raise HTTPException(status_code=422, detail="Bản nháp không nhận API key, token, mật khẩu, OTP/CVV hoặc số thẻ.")


def _workspace_draft_input_from_json(value: Any) -> dict[str, str]:
    try:
        decoded = json.loads(str(value or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(decoded, dict):
        return {}
    # Defensive re-projection protects an old/corrupted row from becoming a
    # browser path to a newly forbidden field after this contract evolves.
    result: dict[str, str] = {}
    for name, item in decoded.items():
        if name in WORKSPACE_DRAFT_ALLOWED_FIELDS and isinstance(item, str) and item.strip() and len(item) <= 4_000:
            result[name] = item
    return result


def _workspace_draft_public(row: tuple[Any, ...], *, include_input: bool = False) -> dict[str, Any]:
    """Expose only Web-owned scalar draft metadata to its signed owner."""
    feature = str(row[1])
    item = FEATURE_BY_KEY.get(feature)
    result: dict[str, Any] = {
        "id": str(row[0]),
        "feature_key": feature,
        "feature_title": item.title if item else "Workflow Web",
        "route": item.route.split("?", 1)[0] if item else "",
        "title": str(row[2]),
        "state": str(row[4] if include_input else row[3]),
        "created_at": str(row[5] if include_input else row[4]),
        "updated_at": str(row[6] if include_input else row[5]),
    }
    if include_input:
        result["input"] = _workspace_draft_input_from_json(row[3])
    return result


class CampaignPlanCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    destination_url: str = Field(min_length=8, max_length=1024)
    platform: str = Field(min_length=2, max_length=32)
    objective: str = Field(min_length=2, max_length=32)
    scheduled_for: str = Field(default="", max_length=64)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return _campaign_text(value, label="Tên kế hoạch", minimum=3, maximum=180)

    @field_validator("destination_url")
    @classmethod
    def validate_destination_url(cls, value: str) -> str:
        return _campaign_destination_url(value)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        platform = str(value or "").strip().lower()
        if platform not in CAMPAIGN_PLAN_PLATFORMS:
            raise ValueError("Nền tảng kế hoạch không hợp lệ")
        return platform

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, value: str) -> str:
        objective = str(value or "").strip().lower()
        if objective not in CAMPAIGN_PLAN_OBJECTIVES:
            raise ValueError("Mục tiêu kế hoạch không hợp lệ")
        return objective

    @field_validator("scheduled_for")
    @classmethod
    def validate_scheduled_for(cls, value: str) -> str:
        return _campaign_scheduled_for(value)


class CampaignPlanUpdateRequest(CampaignPlanCreateRequest):
    """The editable Web-owned planning fields; lifecycle remains a separate action."""


class CampaignPlanStatusRequest(BaseModel):
    approval_status: str = Field(min_length=4, max_length=32)
    review_note: str = Field(default="", max_length=1000)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("approval_status")
    @classmethod
    def validate_approval_status(cls, value: str) -> str:
        status_name = str(value or "").strip().lower()
        if status_name not in CAMPAIGN_PLAN_STATUSES:
            raise ValueError("Trạng thái kế hoạch không hợp lệ")
        return status_name

    @field_validator("review_note")
    @classmethod
    def normalize_review_note(cls, value: str) -> str:
        return _campaign_text(value, label="Ghi chú rà soát", minimum=0, maximum=1000, allow_empty=True)


class CampaignScheduleIntentCreateRequest(BaseModel):
    """Explicit opt-in for one private, future Campaign Inbox record."""

    model_config = ConfigDict(extra="forbid")

    trigger_local_at: str = Field(min_length=16, max_length=32)
    timezone: str = Field(min_length=1, max_length=64)
    expected_plan_revision: int = Field(ge=1, le=1_000_000)
    opt_in: bool = False
    confirm: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _require_key(value)


class CampaignScheduleIntentCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    confirm: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _require_key(value)


class CampaignScheduleIntentReconfirmRequest(CampaignScheduleIntentCancelRequest):
    expected_plan_revision: int = Field(ge=1, le=1_000_000)


class WorkspaceDraftCreateRequest(BaseModel):
    feature_key: str = Field(min_length=2, max_length=120)
    title: str = Field(default="", max_length=120)
    input: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=12, max_length=160)


class WorkspaceDraftUpdateRequest(BaseModel):
    title: str = Field(default="", max_length=120)
    input: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=12, max_length=160)


class WorkspaceDraftArchiveRequest(BaseModel):
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


def _reserve_transient_idempotency(scope: str, key: str) -> tuple[str, str]:
    """Reserve a short single-flight marker without retaining a business result.

    Payment order data and checkout URLs belong solely to the canonical Bot.
    The Web needs to suppress simultaneous duplicate POSTs, but must release
    its marker as soon as the bridge answers so it never becomes a secondary
    payment/order cache. A later retry with the same key is handled by the
    Bot's durable idempotency contract.
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
            if _pending_response(stored) and not _pending_is_stale(created_at):
                return "pending", ""
            # Drop any old cached response from a previous Web version rather
            # than letting it retain an order/payment/checkout payload.
            conn.execute("DELETE FROM web_idempotency WHERE scope=? AND key=?", (scope, key))
        conn.execute(
            "INSERT INTO web_idempotency (scope, key, response_json, created_at) VALUES (?, ?, ?, ?)",
            (scope, key, marker, now),
        )
    return "owner", marker


async def _run_transient_idempotent(scope: str, key: str, operation) -> dict:
    state, marker = _reserve_transient_idempotency(scope, key)
    if state == "pending":
        return envelope(
            False,
            "Yêu cầu cùng mã idempotency đang được xử lý. Vui lòng chờ phản hồi canonical.",
            status_name="guarded",
            error_code="IDEMPOTENCY_IN_PROGRESS",
        )
    try:
        return await operation()
    finally:
        # Never serialize a canonical payment response in the Web database.
        _release_idempotency(scope, key, marker)


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


def _native_job_compatibility_record(record: dict[str, Any]) -> dict[str, Any]:
    """Adapt one sealed Web-native record to the generic Jobs read shape."""

    public_id = str(record.get("id") or "").strip()
    if not CANONICAL_IDENTIFIER_PATTERN.fullmatch(public_id):
        return {}
    state = str(record.get("status") or record.get("state") or "guarded").strip()[:80] or "guarded"
    native_kind = str(record.get("kind") or "web-native").strip()[:80] or "web-native"
    operation_kind = str(record.get("operation_kind") or native_kind).strip()[:120] or native_kind
    raw_output = record.get("output") if isinstance(record.get("output"), dict) else None
    output = None
    if raw_output:
        filename = str(raw_output.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].strip()[:255]
        # Some otherwise-safe generated filenames include their private row
        # UUID.  The opaque public ID must be the only identifier exposed by
        # this generic compatibility surface.
        parsed_native_id = parse_native_job_id(public_id)
        internal_id = parsed_native_id[1] if parsed_native_id is not None else ""
        if internal_id and internal_id.lower() in filename.lower():
            suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            filename = f"web-native-{native_kind}{suffix}"
        content_type = str(raw_output.get("content_type") or "").strip()[:160]
        byte_size = raw_output.get("byte_size")
        if filename and content_type and isinstance(byte_size, int) and not isinstance(byte_size, bool) and byte_size > 0:
            output = {"filename": filename, "content_type": content_type, "byte_size": byte_size}
    return {
        "id": public_id,
        "feature": f"web_native_{native_kind.replace('-', '_')}",
        "job_type": operation_kind,
        # Preserve the exact stored lifecycle. A local operation never becomes
        # a fabricated canonical success record at this compatibility layer.
        "status": state,
        "created_at": str(record.get("created_at") or "")[:160],
        "updated_at": str(record.get("updated_at") or record.get("created_at") or "")[:160],
        "output_available": output is not None,
        "download_ready": output is not None,
        # The generic same-origin route delegates to the existing typed,
        # owner-scoped handler, which performs the final artifact check.
        "delivery_ready": output is not None,
        "source": "web_native",
        "source_state": "local_only",
        "native_kind": native_kind,
        "output": output,
    }


def _native_output_asset_record(job: dict[str, Any]) -> dict[str, Any] | None:
    """Expose one sealed local job output through the generic Assets list."""

    output = job.get("output") if isinstance(job.get("output"), dict) else None
    public_id = str(job.get("id") or "").strip()
    if not output or not CANONICAL_IDENTIFIER_PATTERN.fullmatch(public_id):
        return None
    return {
        "id": public_id,
        "feature": str(job.get("feature") or "web_native").strip()[:160],
        "status": str(job.get("status") or "guarded").strip()[:80] or "guarded",
        "created_at": str(job.get("created_at") or "")[:160],
        "output_available": True,
        "download_ready": True,
        "delivery_ready": True,
        "source": "web_native",
        "source_state": "local_only",
        "filename": str(output.get("filename") or "")[:255],
        "content_type": str(output.get("content_type") or "")[:160],
        "byte_size": output.get("byte_size"),
    }


def _native_asset_compatibility_record(record: dict[str, Any]) -> dict[str, Any]:
    """Show a Web-owned source file without calling it generated output."""

    public_id = str(record.get("id") or "").strip()
    if not CANONICAL_IDENTIFIER_PATTERN.fullmatch(public_id):
        return {}
    state = str(record.get("status") or record.get("state") or "guarded").strip()[:80] or "guarded"
    return {
        "id": public_id,
        "feature": "web_native_asset_vault",
        # Asset Vault lifecycle is intentionally not mapped to a job status.
        "status": state,
        "created_at": str(record.get("created_at") or "")[:160],
        "output_available": False,
        # Metadata alone never verifies a private Vault blob.  The opaque
        # generic route may still be called, but only the existing downloader
        # may attest to byte-level delivery readiness.
        "download_ready": False,
        "delivery_ready": False,
        "source": "web_native",
        "source_state": "local_only",
        "filename": str(record.get("filename") or record.get("name") or "")[:255],
        "content_type": str(record.get("content_type") or "")[:160],
        "byte_size": record.get("byte_size"),
    }


def _read_item_timestamp(item: dict[str, Any]) -> str:
    return str(item.get("updated_at") or item.get("created_at") or "")[:160]


def _merge_read_items(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge public server read models, bounded independently of browser input."""

    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group:
            if not isinstance(item, dict):
                continue
            identifier = str(item.get("id") or "").strip()
            if not CANONICAL_IDENTIFIER_PATTERN.fullmatch(identifier) or identifier in seen:
                continue
            seen.add(identifier)
            merged.append(item)
    merged.sort(key=lambda item: (_read_item_timestamp(item), str(item.get("id") or "")), reverse=True)
    return merged[:100]


def _native_jobs_for_account(account: dict) -> list[dict[str, Any]]:
    return [
        item
        for item in (
            _native_job_compatibility_record(record)
            for record in list_native_jobs(str(account.get("id") or ""), limit=100)
        )
        if item
    ]


def _native_assets_for_account(account: dict) -> list[dict[str, Any]]:
    # Read completed output rows independently. A busy account can have more
    # than one page of newer queued jobs, which must not hide an older sealed
    # output from the generic Assets compatibility view.
    jobs = [
        item
        for item in (
            _native_job_compatibility_record(record)
            for record in list_native_completed_outputs(str(account.get("id") or ""), limit=100)
        )
        if item
    ]
    outputs = [item for item in (_native_output_asset_record(job) for job in jobs) if item]
    sources = [
        item
        for item in (
            _native_asset_compatibility_record(record)
            for record in list_native_assets(str(account.get("id") or ""), limit=100)
        )
        if item
    ]
    return _merge_read_items(outputs, sources)


def _native_read_envelope(items: list[dict[str, Any]], *, kind: str, canonical_unavailable: bool) -> dict:
    message = (
        "Đã tải dữ liệu Web-native. Dữ liệu canonical đang tạm chưa sẵn sàng."
        if canonical_unavailable
        else "Đã tải dữ liệu Web-native của tài khoản hiện tại."
    )
    return envelope(
        True,
        message,
        data={
            "items": items,
            "source": "web_native",
            "source_state": "local_only",
            "read_model": kind,
            "canonical_available": False,
        },
        status_name="read_only",
    )


def _canonical_companion_ready(account: dict) -> bool:
    """Return local bridge/link readiness without exposing either value."""

    return bool(str(account.get("canonical_user_id") or "").strip()) and bridge_configured()


def _merge_bridge_list_with_native(response: dict, native_items: list[dict[str, Any]]) -> dict:
    """Add local records to a successful canonical list without rewriting it."""

    if not native_items or not isinstance(response, dict) or not response.get("ok"):
        return response
    source_data = response.get("data") if isinstance(response.get("data"), dict) else {}
    canonical_items = source_data.get("items") if isinstance(source_data.get("items"), list) else []
    result = dict(response)
    result["data"] = {
        **source_data,
        "items": _merge_read_items(canonical_items, native_items),
        "source": "canonical_and_web_native",
        "web_native_item_count": len(native_items),
    }
    return result


async def _native_asset_delivery(asset_id: str, account: dict):
    """Dispatch an opaque local record to its existing verified downloader."""

    native_job = parse_native_job_id(asset_id)
    if native_job is not None:
        source, internal_id = native_job
        record = get_native_job(str(account.get("id") or ""), asset_id)
        if not record or not isinstance(record.get("output"), dict):
            return envelope(False, "Tài sản Web-native chưa sẵn sàng để tải.", status_name="guarded", error_code="WEB_NATIVE_ASSET_UNAVAILABLE")
        if source == "project-package":
            from copyfast_project_packages import download_project_package
            return await download_project_package(internal_id, account)
        if source == "document-operation":
            from copyfast_document_operations import download_document_operation
            return await download_document_operation(internal_id, account)
        if source == "image-operation":
            from copyfast_image_operations import download_image_operation
            return await download_image_operation(internal_id, account)
        return envelope(False, "Tài sản Web-native chưa được hỗ trợ.", status_name="guarded", error_code="WEB_NATIVE_ASSET_UNAVAILABLE")

    native_asset_id = parse_native_asset_id(asset_id)
    if native_asset_id is not None:
        from copyfast_assets import download_asset
        # This direct call retains the Asset Vault handler's account/state and
        # integrity checks without exposing a decoded raw ID in a redirect.
        return await download_asset(native_asset_id, account)
    return None


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
    # The catalog is static, browser-safe route metadata.  Keep the local
    # Workspace Draft capability declared by this server-side allowlist so a
    # read-only/history surface never renders a save button which would later
    # be rejected by the owner-scoped API.
    flags = _flags()
    features = []
    for entry in catalog():
        item = dict(entry)
        item["web_workspace_draft_supported"] = str(item.get("key") or "") in WORKSPACE_DRAFT_ALLOWED_FEATURES
        # Display-only execution taxonomy.  It cannot grant a provider call,
        # canonical job, payment, output or delivery; every actionable route
        # still owns its signed-session, CSRF, ownership and engine checks.
        item["engine"] = engine_descriptor(str(item.get("key") or ""), flags)
        features.append(item)
    # The Capability Hub is an aggregate of the sanitized static migration
    # audit.  It deliberately has no raw Bot commands/callbacks, handlers,
    # source locations, admin entries or runtime readiness claim.  The
    # existing per-feature capability contract remains authoritative for every
    # executable button.
    return envelope(
        True,
        "Danh mục tính năng Web App",
        data={
            "features": features,
            "flags": flags,
            "bridge_configured": bridge_configured(),
            "capability_hub": capability_hub(),
        },
    )


@router.get("/core/status")
async def core_status():
    execution_ready = _web_feature_execution_available()
    return envelope(
        True,
        "Trạng thái kết nối",
        data={
            "bridge_configured": bridge_configured(),
            "flags": _flags(),
            "web_feature_execution_available": execution_ready,
            # Feature names are public registry metadata, not provider,
            # identity, ledger or secret data.  Withhold even that narrow
            # list unless all common server-side execution gates are true.
            "web_feature_execution_features": sorted(_web_feature_job_adapter_keys()) if execution_ready else [],
        },
    )


@router.get("/campaigns")
async def list_campaign_plans(account: dict = Depends(require_account)):
    """Return only local planning records owned by the signed Web account.

    These are deliberately not Bot campaigns: no canonical campaign ID,
    publish state, analytics, revenue, wallet/Xu or provider data can cross
    this boundary.
    """
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            """SELECT id, title, destination_url, platform, objective, scheduled_for,
                      approval_status, review_note, created_at, updated_at, revision
               FROM web_campaign_plans
               WHERE account_id=?
               ORDER BY CASE WHEN scheduled_for IS NULL OR scheduled_for='' THEN 1 ELSE 0 END,
                        scheduled_for ASC, updated_at DESC
               LIMIT 100""",
            (str(account["id"]),),
        ).fetchall()
    return envelope(
        True,
        "Danh sách kế hoạch Web của bạn.",
        data={"items": [_campaign_plan_public(tuple(row)) for row in rows]},
        status_name="read_only",
    )


@router.get("/campaign-calendar/window")
async def campaign_calendar_window(
    month: str,
    status: str = "all",
    platform: str = "all",
    account: dict = Depends(require_account),
):
    """Read one bounded, account-owned planning month for the Web Calendar.

    This route deliberately has its own narrow projection instead of adding
    query semantics to ``GET /campaigns``. Campaign Planner and Self-review
    retain their established list contract, while Calendar can safely browse a
    selected local month without fetching an account's entire plan history.
    It does not read Bot campaign/calendar tables, create reminders, enqueue
    publishing, call a provider, or touch wallet/payment state.
    """
    selected_month, start, end = _campaign_calendar_month(month)
    selected_status = _campaign_calendar_filter(
        status,
        label="trạng thái",
        allowed=CAMPAIGN_PLAN_STATUSES,
    )
    selected_platform = _campaign_calendar_filter(
        platform,
        label="nền tảng",
        allowed=CAMPAIGN_PLAN_PLATFORMS,
    )
    where = [
        "account_id=?",
        "scheduled_for IS NOT NULL",
        "scheduled_for!=''",
        "scheduled_for>=?",
        "scheduled_for<?",
    ]
    params: list[Any] = [str(account["id"]), start, end]
    if selected_status != "all":
        where.append("approval_status=?")
        params.append(selected_status)
    if selected_platform != "all":
        where.append("platform=?")
        params.append(selected_platform)
    predicate = " AND ".join(where)
    ensure_copyfast_schema()
    with transaction() as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*) FROM web_campaign_plans WHERE {predicate}",
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""SELECT id, title, platform, objective, scheduled_for,
                       approval_status, updated_at
                FROM web_campaign_plans
                WHERE {predicate}
                ORDER BY scheduled_for ASC, updated_at DESC, id ASC
                LIMIT ?""",
            (*params, CAMPAIGN_CALENDAR_WINDOW_MAX_ITEMS),
        ).fetchall()
    total = int(total_row[0] if total_row else 0)
    items = [_campaign_calendar_public(tuple(row)) for row in rows]
    return envelope(
        True,
        "Lịch nội dung Web của bạn trong tháng đã chọn.",
        data={
            "month": selected_month,
            "filters": {"status": selected_status, "platform": selected_platform},
            "items": items,
            "summary": {
                "total": total,
                "returned": len(items),
                "has_more": total > len(items),
                "limit": CAMPAIGN_CALENDAR_WINDOW_MAX_ITEMS,
            },
        },
        status_name="read_only",
    )


@router.get("/campaigns/{plan_id}/schedule-intents")
async def list_campaign_schedule_intents(plan_id: str, account: dict = Depends(require_account)):
    """List opaque schedule metadata for one signed owner's Campaign detail."""
    plan_id = _campaign_plan_id(plan_id)
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        if not _campaign_plan_source_row(conn, plan_id=plan_id, account_id=account_id):
            return _campaign_schedule_guarded(
                "Không tìm thấy kế hoạch thuộc tài khoản hiện tại.",
                "CAMPAIGN_SCHEDULE_PLAN_NOT_FOUND",
            )
        rows = conn.execute(
            """SELECT id, account_id, plan_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                      trigger_at, state, revision, created_at, updated_at, dispatched_at, guarded_at, guard_code,
                      cancelled_at, created_by_account_id
               FROM web_campaign_schedule_intents
               WHERE plan_id=? AND account_id=?
               ORDER BY CASE state WHEN 'active' THEN 0 WHEN 'guarded' THEN 1 WHEN 'dispatched' THEN 2 ELSE 3 END,
                        trigger_at ASC, created_at DESC, id DESC
               LIMIT ?""",
            (plan_id, account_id, MAX_SCHEDULE_INTENTS_PER_PLAN),
        ).fetchall()
    return envelope(
        True,
        "Lịch nhắc Campaign chỉ hiển thị metadata owner-scoped của kế hoạch hiện tại.",
        data=_campaign_schedule_boundary(
            schedule_intents=[_campaign_schedule_intent_public(tuple(row)) for row in rows],
            max_schedule_intents_per_plan=MAX_SCHEDULE_INTENTS_PER_PLAN,
        ),
        status_name="read_only",
    )


@router.post("/campaigns/{plan_id}/schedule-intents")
async def create_campaign_schedule_intent(
    plan_id: str,
    payload: CampaignScheduleIntentCreateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Record an explicit future in-app reminder for a Web Campaign only."""
    plan_id = _campaign_plan_id(plan_id)
    if not _campaign_schedule_actor_allowed(account):
        return _campaign_schedule_guarded(
            "Phiên Web chưa có role account hợp lệ để tạo lịch nhắc Campaign.",
            "CAMPAIGN_SCHEDULE_ROLE_REQUIRED",
        )
    if not payload.opt_in or not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần bật opt-in và xác nhận rõ ràng trước khi tạo lịch nhắc Campaign")
    try:
        trigger_local_at, zone_name, trigger_at = normalize_schedule_trigger(payload.trigger_local_at, payload.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    account_id = str(account["id"])
    fingerprint = canonical_json_hash(
        {
            "plan_id": plan_id,
            "expected_plan_revision": payload.expected_plan_revision,
            "trigger_local_at": trigger_local_at,
            "timezone": zone_name,
            "trigger_at": trigger_at,
            "opt_in": bool(payload.opt_in),
            "confirm": bool(payload.confirm),
        }
    )
    scope = f"campaign-schedule:{account_id}:plan:{plan_id}:create"

    def operation(conn: Any) -> dict[str, Any]:
        plan = _campaign_plan_source_row(conn, plan_id=plan_id, account_id=account_id)
        if not plan:
            return _campaign_schedule_guarded("Không tìm thấy kế hoạch thuộc tài khoản hiện tại.", "CAMPAIGN_SCHEDULE_PLAN_NOT_FOUND")
        if str(plan[7]) == "archived":
            return _campaign_schedule_guarded("Kế hoạch đã lưu trữ nên không thể tạo lịch nhắc mới.", "CAMPAIGN_SCHEDULE_PLAN_ARCHIVED")
        source = _campaign_schedule_source_coordinates(tuple(plan))
        if not source:
            return _campaign_schedule_guarded("Revision Campaign chưa được xác minh nên không thể tạo lịch nhắc.", "CAMPAIGN_SCHEDULE_SOURCE_UNVERIFIED")
        if source[0] != payload.expected_plan_revision:
            return _campaign_schedule_guarded(
                "Kế hoạch đã có revision mới. Hãy tải lại và xác nhận lại lịch nhắc.",
                "CAMPAIGN_SCHEDULE_SOURCE_CONFLICT",
            )
        total = conn.execute(
            "SELECT COUNT(*) FROM web_campaign_schedule_intents WHERE account_id=?", (account_id,),
        ).fetchone()
        active_account = conn.execute(
            "SELECT COUNT(*) FROM web_campaign_schedule_intents WHERE account_id=? AND state='active'", (account_id,),
        ).fetchone()
        active_plan = conn.execute(
            "SELECT COUNT(*) FROM web_campaign_schedule_intents WHERE account_id=? AND plan_id=? AND state='active'",
            (account_id, plan_id),
        ).fetchone()
        if int(total[0] or 0) >= MAX_SCHEDULE_INTENTS_PER_ACCOUNT:
            return _campaign_schedule_guarded("Kho lịch nhắc Campaign đã đạt giới hạn an toàn của account.", "CAMPAIGN_SCHEDULE_ACCOUNT_LIMIT")
        if int(active_account[0] or 0) >= MAX_ACTIVE_SCHEDULE_INTENTS_PER_ACCOUNT:
            return _campaign_schedule_guarded(
                "Account đã có quá nhiều lịch nhắc đang hoạt động. Hãy hủy hoặc xử lý lịch cũ trước.",
                "CAMPAIGN_SCHEDULE_ACTIVE_LIMIT",
            )
        if int(active_plan[0] or 0) >= MAX_SCHEDULE_INTENTS_PER_PLAN:
            return _campaign_schedule_guarded("Kế hoạch này đã có đủ lịch nhắc đang hoạt động.", "CAMPAIGN_SCHEDULE_PLAN_LIMIT")
        intent_id = str(uuid.uuid4())
        now = utc_now()
        try:
            conn.execute(
                """INSERT INTO web_campaign_schedule_intents
                   (id, account_id, plan_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                    trigger_at, state, revision, created_by_account_id, created_at, updated_at,
                    dispatched_at, guarded_at, guard_code, cancelled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, ?, NULL, NULL, NULL, NULL)""",
                (intent_id, account_id, plan_id, source[0], source[1], trigger_local_at, zone_name, trigger_at, account_id, now, now),
            )
        except sqlite3.IntegrityError:
            existing = conn.execute(
                """SELECT id, account_id, plan_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                          trigger_at, state, revision, created_at, updated_at, dispatched_at, guarded_at, guard_code,
                          cancelled_at, created_by_account_id
                   FROM web_campaign_schedule_intents
                   WHERE account_id=? AND plan_id=? AND source_revision=? AND trigger_at=? AND state='active'""",
                (account_id, plan_id, source[0], trigger_at),
            ).fetchone()
            data = _campaign_schedule_boundary(delivery="in_app_record_only")
            if existing:
                data["schedule_intent"] = _campaign_schedule_intent_public(tuple(existing))
            return envelope(
                False,
                "Đã có một lịch nhắc đang hoạt động cho revision và thời điểm này.",
                data=data,
                status_name="guarded",
                error_code="CAMPAIGN_SCHEDULE_DUPLICATE",
            )
        created = _campaign_schedule_intent_row(conn, intent_id=intent_id, plan_id=plan_id, account_id=account_id)
        if not created:
            raise RuntimeError("Campaign schedule intent missing after insert")
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="campaign.schedule.create",
            request_id=_request_id(request),
            target=intent_id,
            outcome="ok",
            detail="explicit owner opt-in for one private in-app campaign schedule record",
        )
        return envelope(
            True,
            "Đã lưu lịch nhắc riêng tư. Chỉ scheduler đã xác thực mới có thể tạo record Inbox in-app khi Campaign vẫn khớp.",
            data=_campaign_schedule_boundary(
                schedule_intent=_campaign_schedule_intent_public(created),
                schedule_intent_recorded=True,
            ),
            status_name="completed",
        )

    return _campaign_schedule_idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/campaigns/{plan_id}/schedule-intents/{intent_id}/cancel")
async def cancel_campaign_schedule_intent(
    plan_id: str,
    intent_id: str,
    payload: CampaignScheduleIntentCancelRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    plan_id = _campaign_plan_id(plan_id)
    intent_id = _campaign_schedule_intent_id(intent_id)
    if not _campaign_schedule_actor_allowed(account):
        return _campaign_schedule_guarded(
            "Phiên Web chưa có role account hợp lệ để quản lý lịch nhắc Campaign.",
            "CAMPAIGN_SCHEDULE_ROLE_REQUIRED",
        )
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi hủy lịch nhắc Campaign")
    account_id = str(account["id"])
    fingerprint = canonical_json_hash(
        {"plan_id": plan_id, "intent_id": intent_id, "expected_revision": payload.expected_revision, "confirm": True}
    )
    scope = f"campaign-schedule:{account_id}:plan:{plan_id}:intent:{intent_id}:cancel"

    def operation(conn: Any) -> dict[str, Any]:
        if not _campaign_plan_source_row(conn, plan_id=plan_id, account_id=account_id):
            return _campaign_schedule_guarded("Không tìm thấy kế hoạch thuộc tài khoản hiện tại.", "CAMPAIGN_SCHEDULE_PLAN_NOT_FOUND")
        current = _campaign_schedule_intent_row(conn, intent_id=intent_id, plan_id=plan_id, account_id=account_id)
        if not current:
            return _campaign_schedule_guarded("Không tìm thấy lịch nhắc thuộc kế hoạch và account hiện tại.", "CAMPAIGN_SCHEDULE_NOT_FOUND")
        if int(current[9]) != payload.expected_revision:
            return _campaign_schedule_guarded("Lịch nhắc đã có revision mới. Hãy tải lại trước khi hủy.", "CAMPAIGN_SCHEDULE_CONFLICT")
        state = str(current[8])
        if state == "dispatched":
            return _campaign_schedule_guarded("Lịch nhắc đã tạo record Inbox; không thể rút lại record đã materialize.", "CAMPAIGN_SCHEDULE_DISPATCHED")
        if state == "cancelled":
            return envelope(
                True,
                "Lịch nhắc đã được hủy trước đó.",
                data=_campaign_schedule_boundary(schedule_intent=_campaign_schedule_intent_public(current)),
                status_name="completed",
            )
        now = utc_now()
        next_revision = int(current[9]) + 1
        updated = conn.execute(
            """UPDATE web_campaign_schedule_intents
               SET state='cancelled', revision=?, updated_at=?, cancelled_at=?
               WHERE id=? AND plan_id=? AND account_id=? AND revision=? AND state IN ('active', 'guarded')""",
            (next_revision, now, now, intent_id, plan_id, account_id, payload.expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            return _campaign_schedule_guarded("Lịch nhắc đã thay đổi đồng thời. Hãy tải lại trước khi hủy.", "CAMPAIGN_SCHEDULE_CONFLICT")
        refreshed = _campaign_schedule_intent_row(conn, intent_id=intent_id, plan_id=plan_id, account_id=account_id)
        if not refreshed:
            raise RuntimeError("Campaign schedule intent disappeared after cancel")
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="campaign.schedule.cancel",
            request_id=_request_id(request),
            target=intent_id,
            outcome="ok",
            detail="owner cancelled a web-only in-app campaign schedule intent",
        )
        return envelope(
            True,
            "Đã hủy lịch nhắc. Không có Inbox record mới hoặc thông báo ngoài Web được gửi.",
            data=_campaign_schedule_boundary(schedule_intent=_campaign_schedule_intent_public(refreshed)),
            status_name="completed",
        )

    return _campaign_schedule_idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/campaigns/{plan_id}/schedule-intents/{intent_id}/reconfirm")
async def reconfirm_campaign_schedule_intent(
    plan_id: str,
    intent_id: str,
    payload: CampaignScheduleIntentReconfirmRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Bind a guarded Campaign intent to its current source without rescheduling."""
    plan_id = _campaign_plan_id(plan_id)
    intent_id = _campaign_schedule_intent_id(intent_id)
    if not _campaign_schedule_actor_allowed(account):
        return _campaign_schedule_guarded(
            "Phiên Web chưa có role account hợp lệ để xác nhận lại lịch nhắc Campaign.",
            "CAMPAIGN_SCHEDULE_ROLE_REQUIRED",
        )
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi bind lại lịch nhắc với revision mới")
    account_id = str(account["id"])
    fingerprint = canonical_json_hash(
        {
            "plan_id": plan_id,
            "intent_id": intent_id,
            "expected_revision": payload.expected_revision,
            "expected_plan_revision": payload.expected_plan_revision,
            "confirm": True,
        }
    )
    scope = f"campaign-schedule:{account_id}:plan:{plan_id}:intent:{intent_id}:reconfirm"

    def operation(conn: Any) -> dict[str, Any]:
        plan = _campaign_plan_source_row(conn, plan_id=plan_id, account_id=account_id)
        if not plan:
            return _campaign_schedule_guarded("Không tìm thấy kế hoạch thuộc tài khoản hiện tại.", "CAMPAIGN_SCHEDULE_PLAN_NOT_FOUND")
        if str(plan[7]) == "archived":
            return _campaign_schedule_guarded("Kế hoạch đã lưu trữ nên không thể xác nhận lại lịch nhắc.", "CAMPAIGN_SCHEDULE_PLAN_ARCHIVED")
        source = _campaign_schedule_source_coordinates(tuple(plan))
        if not source:
            return _campaign_schedule_guarded("Revision Campaign chưa được xác minh nên chưa thể bind lại lịch nhắc.", "CAMPAIGN_SCHEDULE_SOURCE_UNVERIFIED")
        if source[0] != payload.expected_plan_revision:
            return _campaign_schedule_guarded(
                "Kế hoạch đã có revision mới. Hãy tải lại trước khi bind lại lịch nhắc.",
                "CAMPAIGN_SCHEDULE_SOURCE_CONFLICT",
            )
        intent = _campaign_schedule_intent_row(conn, intent_id=intent_id, plan_id=plan_id, account_id=account_id)
        if not intent:
            return _campaign_schedule_guarded("Không tìm thấy lịch nhắc thuộc kế hoạch và account hiện tại.", "CAMPAIGN_SCHEDULE_NOT_FOUND")
        if int(intent[9]) != payload.expected_revision:
            return _campaign_schedule_guarded("Lịch nhắc đã có revision mới. Hãy tải lại trước khi xác nhận lại.", "CAMPAIGN_SCHEDULE_CONFLICT")
        if str(intent[8]) != "guarded":
            return _campaign_schedule_guarded("Chỉ lịch nhắc đang guarded mới cần xác nhận lại source snapshot.", "CAMPAIGN_SCHEDULE_RECONFIRM_NOT_REQUIRED")
        try:
            _local, _zone, normalized_trigger = normalize_schedule_trigger(intent[5], intent[6])
        except ValueError:
            return _campaign_schedule_guarded(
                "Thời điểm lịch nhắc đã qua hoặc không còn xác minh được. Hãy tạo lịch mới rõ ràng.",
                "CAMPAIGN_SCHEDULE_TRIGGER_EXPIRED",
            )
        if not hmac.compare_digest(normalized_trigger, str(intent[7])):
            return _campaign_schedule_guarded(
                "Thời điểm UTC của lịch nhắc không còn khớp với timezone đã lưu. Hãy tạo lịch mới.",
                "CAMPAIGN_SCHEDULE_TRIGGER_UNVERIFIED",
            )
        now = utc_now()
        next_revision = int(intent[9]) + 1
        try:
            updated = conn.execute(
                """UPDATE web_campaign_schedule_intents
                   SET source_revision=?, source_snapshot_hash=?, state='active', revision=?, updated_at=?,
                       guarded_at=NULL, guard_code=NULL, cancelled_at=NULL
                   WHERE id=? AND plan_id=? AND account_id=? AND revision=? AND state='guarded'""",
                (source[0], source[1], next_revision, now, intent_id, plan_id, account_id, payload.expected_revision),
            )
        except sqlite3.IntegrityError:
            return _campaign_schedule_guarded("Đã có lịch nhắc active khác cho revision và thời điểm này.", "CAMPAIGN_SCHEDULE_DUPLICATE")
        if int(updated.rowcount or 0) != 1:
            return _campaign_schedule_guarded("Lịch nhắc đã thay đổi đồng thời. Hãy tải lại trước khi xác nhận lại.", "CAMPAIGN_SCHEDULE_CONFLICT")
        refreshed = _campaign_schedule_intent_row(conn, intent_id=intent_id, plan_id=plan_id, account_id=account_id)
        if not refreshed:
            raise RuntimeError("Campaign schedule intent disappeared after reconfirm")
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="campaign.schedule.reconfirm",
            request_id=_request_id(request),
            target=intent_id,
            outcome="ok",
            detail="owner explicitly rebound a guarded schedule intent to the current campaign snapshot",
        )
        return envelope(
            True,
            "Đã xác nhận lại source snapshot. Thời điểm cũ được giữ nguyên, không tự đổi lịch.",
            data=_campaign_schedule_boundary(schedule_intent=_campaign_schedule_intent_public(refreshed)),
            status_name="completed",
        )

    return _campaign_schedule_idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/campaigns/{plan_id}")
async def get_campaign_plan(plan_id: str, account: dict = Depends(require_account)):
    """Return one Web-owned plan only when it belongs to the signed account.

    This deliberately does not turn a local plan ID into a Bot campaign ID or
    a cross-account lookup. The projection is the same bounded Web planning
    metadata used by the list, with no provider, wallet, PayOS or publishing
    state.
    """
    plan_id = _campaign_plan_id(plan_id)
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT id, title, destination_url, platform, objective, scheduled_for,
                      approval_status, review_note, created_at, updated_at, revision
               FROM web_campaign_plans
               WHERE id=? AND account_id=?""",
            (plan_id, str(account["id"])),
        ).fetchone()
    if not row:
        return envelope(
            False,
            "Không tìm thấy kế hoạch thuộc tài khoản hiện tại.",
            status_name="guarded",
            error_code="CAMPAIGN_PLAN_NOT_FOUND",
        )
    item = _campaign_plan_public(tuple(row))
    status_name = str(item["approval_status"])
    return envelope(
        True,
        "Chi tiết kế hoạch Web của bạn.",
        data={"item": item},
        status_name=status_name if status_name in CAMPAIGN_PLAN_STATUSES else "guarded",
    )


@router.post("/campaigns")
async def create_campaign_plan(payload: CampaignPlanCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create an account-owned plan without publishing or calling a provider."""
    key = _require_key(payload.idempotency_key)
    scope = f"campaign-plan:{account['id']}:create"

    async def operation() -> dict:
        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan = {
            "id": plan_id,
            "title": payload.title,
            "destination_url": payload.destination_url,
            "platform": payload.platform,
            "objective": payload.objective,
            "scheduled_for": payload.scheduled_for,
            "approval_status": "draft",
            "review_note": "",
            "created_at": now,
            "updated_at": now,
            "revision": 1,
        }
        ensure_copyfast_schema()
        with transaction() as conn:
            conn.execute(
                """INSERT INTO web_campaign_plans
                   (id, account_id, title, destination_url, platform, objective, scheduled_for,
                    approval_status, review_note, created_at, updated_at, revision)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan_id,
                    str(account["id"]),
                    payload.title,
                    payload.destination_url,
                    payload.platform,
                    payload.objective,
                    payload.scheduled_for or None,
                    "draft",
                    "",
                    now,
                    now,
                    1,
                ),
            )
            # The URL/title can contain affiliate/customer information.  The
            # audit trail records only the opaque local plan ID and outcome.
            _record_audit(
                conn,
                account_id=str(account["id"]),
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="campaign.plan.create",
                request_id=_request_id(request),
                target=plan_id,
                outcome="ok",
                detail="web-local planning record created",
            )
        return envelope(
            True,
            "Đã lưu bản nháp kế hoạch trên Web. Chưa có nội dung nào được xuất bản hoặc gửi sang Bot.",
            data={"item": plan},
            status_name="draft",
        )

    return await _run_idempotent(scope, key, operation)


@router.patch("/campaigns/{plan_id}")
async def update_campaign_plan(
    plan_id: str,
    payload: CampaignPlanUpdateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Edit account-owned planning details without changing canonical state."""
    plan_id = _campaign_plan_id(plan_id)
    key = _require_key(payload.idempotency_key)
    scope = f"campaign-plan:{account['id']}:{plan_id}:edit"

    async def operation() -> dict:
        ensure_copyfast_schema()
        with transaction() as conn:
            current = conn.execute(
                """SELECT approval_status FROM web_campaign_plans
                   WHERE id=? AND account_id=?""",
                (plan_id, str(account["id"])),
            ).fetchone()
            if not current:
                return envelope(
                    False,
                    "Không tìm thấy kế hoạch thuộc tài khoản hiện tại.",
                    status_name="guarded",
                    error_code="CAMPAIGN_PLAN_NOT_FOUND",
                )
            now = utc_now()
            conn.execute(
                """UPDATE web_campaign_plans
                   SET title=?, destination_url=?, platform=?, objective=?, scheduled_for=?, updated_at=?, revision=revision+1
                   WHERE id=? AND account_id=?""",
                (
                    payload.title,
                    payload.destination_url,
                    payload.platform,
                    payload.objective,
                    payload.scheduled_for or None,
                    now,
                    plan_id,
                    str(account["id"]),
                ),
            )
            guarded_schedule_intents = _guard_active_campaign_schedule_intents(
                conn, plan_id=plan_id, account_id=str(account["id"]), now=now,
            )
            updated = conn.execute(
                """SELECT id, title, destination_url, platform, objective, scheduled_for,
                          approval_status, review_note, created_at, updated_at, revision
                   FROM web_campaign_plans WHERE id=? AND account_id=?""",
                (plan_id, str(account["id"])),
            ).fetchone()
            _record_audit(
                conn,
                account_id=str(account["id"]),
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="campaign.plan.update",
                request_id=_request_id(request),
                target=plan_id,
                outcome="ok",
                detail=f"web-local planning fields updated; guarded_schedule_intents={guarded_schedule_intents}",
            )
        item = _campaign_plan_public(tuple(updated))
        status_name = str(item["approval_status"])
        return envelope(
            True,
            "Đã cập nhật chi tiết kế hoạch trên Web. Không có nội dung nào được publish hoặc gửi sang Bot.",
            data={"item": item},
            status_name=status_name if status_name in CAMPAIGN_PLAN_STATUSES else "guarded",
        )

    return await _run_idempotent(scope, key, operation)


@router.post("/campaigns/{plan_id}/status")
async def update_campaign_plan_status(
    plan_id: str,
    payload: CampaignPlanStatusRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Advance only the local review/calendar state of an owned plan."""
    plan_id = _campaign_plan_id(plan_id)
    key = _require_key(payload.idempotency_key)
    scope = f"campaign-plan:{account['id']}:{plan_id}:status"

    async def operation() -> dict:
        ensure_copyfast_schema()
        with transaction() as conn:
            row = conn.execute(
                """SELECT id, title, destination_url, platform, objective, scheduled_for,
                          approval_status, review_note, created_at, updated_at, revision
                   FROM web_campaign_plans WHERE id=? AND account_id=?""",
                (plan_id, str(account["id"])),
            ).fetchone()
            if not row:
                return envelope(
                    False,
                    "Không tìm thấy kế hoạch thuộc tài khoản hiện tại.",
                    status_name="guarded",
                    error_code="CAMPAIGN_PLAN_NOT_FOUND",
                )
            current = str(row[6])
            target = payload.approval_status
            if target != current and target not in CAMPAIGN_PLAN_TRANSITIONS.get(current, frozenset()):
                return envelope(
                    False,
                    "Không thể chuyển trạng thái kế hoạch theo luồng rà soát nội bộ này.",
                    status_name="guarded",
                    error_code="CAMPAIGN_STATUS_TRANSITION_DENIED",
                )
            now = utc_now()
            conn.execute(
                """UPDATE web_campaign_plans
                   SET approval_status=?, review_note=?, updated_at=?, revision=revision+1
                   WHERE id=? AND account_id=?""",
                (target, payload.review_note, now, plan_id, str(account["id"])),
            )
            guarded_schedule_intents = _guard_active_campaign_schedule_intents(
                conn, plan_id=plan_id, account_id=str(account["id"]), now=now,
            )
            updated = conn.execute(
                """SELECT id, title, destination_url, platform, objective, scheduled_for,
                          approval_status, review_note, created_at, updated_at, revision
                   FROM web_campaign_plans WHERE id=? AND account_id=?""",
                (plan_id, str(account["id"])),
            ).fetchone()
            _record_audit(
                conn,
                account_id=str(account["id"]),
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="campaign.plan.review" if current == target else "campaign.plan.status",
                request_id=_request_id(request),
                target=plan_id,
                outcome="ok",
                detail=f"web-local planning status:{current}->{target}; guarded_schedule_intents={guarded_schedule_intents}",
            )
        item = _campaign_plan_public(tuple(updated))
        return envelope(
            True,
            f"Đã cập nhật kế hoạch thành {CAMPAIGN_PLAN_STATUS_LABELS[target]}. Đây vẫn chỉ là trạng thái nội bộ trên Web.",
            data={"item": item},
            status_name=target,
        )

    return await _run_idempotent(scope, key, operation)


@router.get("/workspace/drafts")
async def list_workspace_drafts(
    include_archived: bool = False,
    state: str | None = None,
    feature_key: str | None = None,
    q: str | None = None,
    limit: int = WORKSPACE_DRAFT_LIST_DEFAULT_LIMIT,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    """List only Web-owned drafts belonging to the signed account.

    This intentionally does not ask the Bot to reconstruct a feature request,
    quote, upload, job or provider task. Listing keeps input bodies out of the
    response; a separate owner-scoped detail read is required to resume one.
    Search considers only safe list metadata (title/workflow), never a saved
    brief value.  Explicit `state` takes precedence over legacy
    `include_archived` when both are supplied.
    """
    bounded_limit = max(1, min(int(limit), WORKSPACE_DRAFT_LIST_MAX_LIMIT))
    bounded_offset = max(0, min(int(offset), WORKSPACE_DRAFT_LIST_MAX_OFFSET))
    requested_state = _workspace_draft_list_state(state, include_archived=include_archived)
    requested_feature = _workspace_draft_list_feature(feature_key)
    needle = _workspace_draft_list_query(q)
    where = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if requested_state != "all":
        where.append("state=?")
        params.append(requested_state)
    if requested_feature:
        where.append("feature_key=?")
        params.append(requested_feature)
    if needle:
        escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(title LIKE ? ESCAPE '\\' OR feature_key LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    predicate = " AND ".join(where)
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, feature_key, title, state, created_at, updated_at
                FROM web_workspace_drafts
                WHERE {predicate}
                ORDER BY CASE WHEN state='active' THEN 0 ELSE 1 END, updated_at DESC, id DESC
                LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
        summary = {"active": 0, "archived": 0}
        for count_row in conn.execute(
            """SELECT state, COUNT(*) FROM web_workspace_drafts
               WHERE account_id=? GROUP BY state""",
            (str(account["id"]),),
        ).fetchall():
            state_name = str(count_row[0])
            if state_name in summary:
                summary[state_name] = int(count_row[1])
    has_more = len(rows) > bounded_limit
    items = [_workspace_draft_public(tuple(row)) for row in rows[:bounded_limit]]
    return envelope(
        True,
        "Danh sách bản nháp Web của bạn.",
        data={
            "items": items,
            "has_more": has_more,
            "next_offset": bounded_offset + len(items) if has_more else None,
            "filters": {"state": requested_state, "feature_key": requested_feature, "q": needle},
            "pagination": {"limit": bounded_limit, "offset": bounded_offset, "returned": len(items)},
            "summary": summary,
        },
        status_name="read_only",
    )


@router.get("/workspace/drafts/{draft_id}")
async def get_workspace_draft(draft_id: str, account: dict = Depends(require_account)):
    """Read one safe scalar draft only for its signed Web owner."""
    draft_id = _workspace_draft_id(draft_id)
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT id, feature_key, title, input_json, state, created_at, updated_at
               FROM web_workspace_drafts WHERE id=? AND account_id=?""",
            (draft_id, str(account["id"])),
        ).fetchone()
    if not row:
        return envelope(
            False,
            "Không tìm thấy bản nháp thuộc tài khoản hiện tại.",
            status_name="guarded",
            error_code="WORKSPACE_DRAFT_NOT_FOUND",
        )
    item = _workspace_draft_public(tuple(row), include_input=True)
    return envelope(
        True,
        "Chi tiết bản nháp Web của bạn.",
        data={"item": item},
        status_name="draft" if item["state"] == "active" else "archived",
    )


@router.post("/workspace/drafts")
async def create_workspace_draft(
    payload: WorkspaceDraftCreateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist a safe Web-only authoring draft without a Bot bridge call."""
    feature = _workspace_draft_feature(payload.feature_key)
    title = _workspace_draft_title(payload.title, feature)
    values = _workspace_draft_input(payload.input)
    _assert_safe_workspace_draft_content(title, values)
    key = _require_key(payload.idempotency_key)
    scope = f"workspace-draft:{account['id']}:create"

    async def operation() -> dict:
        draft_id = str(uuid.uuid4())
        now = utc_now()
        encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        ensure_copyfast_schema()
        with transaction() as conn:
            active_count = conn.execute(
                "SELECT COUNT(*) FROM web_workspace_drafts WHERE account_id=? AND state='active'",
                (str(account["id"]),),
            ).fetchone()[0]
            if int(active_count) >= WORKSPACE_DRAFT_MAX_ITEMS:
                return envelope(
                    False,
                    f"Mỗi tài khoản chỉ giữ tối đa {WORKSPACE_DRAFT_MAX_ITEMS} bản nháp đang hoạt động. Hãy lưu trữ một bản cũ trước.",
                    status_name="guarded",
                    error_code="WORKSPACE_DRAFT_LIMIT_REACHED",
                )
            conn.execute(
                """INSERT INTO web_workspace_drafts
                   (id, account_id, feature_key, title, input_json, state, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
                (draft_id, str(account["id"]), feature, title, encoded, now, now),
            )
            _record_audit(
                conn,
                account_id=str(account["id"]),
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="workspace.draft.create",
                request_id=_request_id(request),
                target=draft_id,
                outcome="ok",
                detail=f"web-owned safe scalar draft created for feature:{feature}",
            )
        item = _workspace_draft_public((draft_id, feature, title, "active", now, now))
        return envelope(
            True,
            "Đã lưu bản nháp trên Web. Chưa gửi Bot, chưa estimate, chưa tạo job và chưa thay đổi Xu.",
            data={"item": item},
            status_name="draft",
        )

    return await _run_idempotent(scope, key, operation)


@router.patch("/workspace/drafts/{draft_id}")
async def update_workspace_draft(
    draft_id: str,
    payload: WorkspaceDraftUpdateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Replace only a signed owner's active Web draft with safe scalars."""
    draft_id = _workspace_draft_id(draft_id)
    key = _require_key(payload.idempotency_key)
    scope = f"workspace-draft:{account['id']}:{draft_id}:update"

    async def operation() -> dict:
        ensure_copyfast_schema()
        with transaction() as conn:
            current = conn.execute(
                """SELECT feature_key, state FROM web_workspace_drafts
                   WHERE id=? AND account_id=?""",
                (draft_id, str(account["id"])),
            ).fetchone()
            if not current:
                return envelope(False, "Không tìm thấy bản nháp thuộc tài khoản hiện tại.", status_name="guarded", error_code="WORKSPACE_DRAFT_NOT_FOUND")
            feature = _workspace_draft_feature(current[0])
            if str(current[1]) != "active":
                return envelope(False, "Bản nháp đã lưu trữ không thể chỉnh sửa. Hãy tạo bản mới khi cần tiếp tục.", status_name="guarded", error_code="WORKSPACE_DRAFT_ARCHIVED")
            title = _workspace_draft_title(payload.title, feature)
            values = _workspace_draft_input(payload.input)
            _assert_safe_workspace_draft_content(title, values)
            now = utc_now()
            conn.execute(
                """UPDATE web_workspace_drafts SET title=?, input_json=?, updated_at=?
                   WHERE id=? AND account_id=? AND state='active'""",
                (title, json.dumps(values, ensure_ascii=False, separators=(",", ":")), now, draft_id, str(account["id"])),
            )
            updated = conn.execute(
                """SELECT id, feature_key, title, state, created_at, updated_at
                   FROM web_workspace_drafts WHERE id=? AND account_id=?""",
                (draft_id, str(account["id"])),
            ).fetchone()
            _record_audit(
                conn,
                account_id=str(account["id"]),
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="workspace.draft.update",
                request_id=_request_id(request),
                target=draft_id,
                outcome="ok",
                detail=f"web-owned safe scalar draft updated for feature:{feature}",
            )
        return envelope(True, "Đã cập nhật bản nháp Web. Chưa gửi Bot hoặc tạo workflow canonical.", data={"item": _workspace_draft_public(tuple(updated))}, status_name="draft")

    return await _run_idempotent(scope, key, operation)


@router.post("/workspace/drafts/{draft_id}/archive")
async def archive_workspace_draft(
    draft_id: str,
    payload: WorkspaceDraftArchiveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Archive an owned Web draft without deleting or changing Bot state."""
    draft_id = _workspace_draft_id(draft_id)
    key = _require_key(payload.idempotency_key)
    scope = f"workspace-draft:{account['id']}:{draft_id}:archive"

    async def operation() -> dict:
        ensure_copyfast_schema()
        with transaction() as conn:
            current = conn.execute(
                """SELECT id, feature_key, title, state, created_at, updated_at
                   FROM web_workspace_drafts WHERE id=? AND account_id=?""",
                (draft_id, str(account["id"])),
            ).fetchone()
            if not current:
                return envelope(False, "Không tìm thấy bản nháp thuộc tài khoản hiện tại.", status_name="guarded", error_code="WORKSPACE_DRAFT_NOT_FOUND")
            if str(current[3]) == "active":
                now = utc_now()
                conn.execute(
                    """UPDATE web_workspace_drafts SET state='archived', updated_at=?
                       WHERE id=? AND account_id=? AND state='active'""",
                    (now, draft_id, str(account["id"])),
                )
                current = conn.execute(
                    """SELECT id, feature_key, title, state, created_at, updated_at
                       FROM web_workspace_drafts WHERE id=? AND account_id=?""",
                    (draft_id, str(account["id"])),
                ).fetchone()
                _record_audit(
                    conn,
                    account_id=str(account["id"]),
                    canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                    action="workspace.draft.archive",
                    request_id=_request_id(request),
                    target=draft_id,
                    outcome="ok",
                    detail="web-owned draft archived",
                )
        return envelope(True, "Đã lưu trữ bản nháp Web. Không có Bot, job, Xu hoặc tệp nào bị thay đổi.", data={"item": _workspace_draft_public(tuple(current))}, status_name="archived")

    return await _run_idempotent(scope, key, operation)


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


@router.get("/account/activity")
async def account_activity(account: dict = Depends(require_account)):
    """Return a bounded, sanitized history of Web-owned account activity.

    This endpoint intentionally remains available before Telegram linking. It
    reads only the signed account's rows from the standalone Web audit table;
    it neither calls the private bridge nor acts as a Bot wallet/job/payment
    history or an Admin audit export.
    """
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            """SELECT action, outcome, created_at
               FROM web_audit_events
               WHERE account_id=?
               ORDER BY created_at DESC, id DESC
               LIMIT 50""",
            (str(account["id"]),),
        ).fetchall()
    return envelope(
        True,
        "Nhật ký hoạt động Web riêng tư của bạn.",
        data={"items": [_public_account_activity_item(tuple(row)) for row in rows]},
        status_name="read_only",
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
    return await _run_transient_idempotent(
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
    # The generic Jobs view remains a canonical companion when the signed
    # account can reach that bridge, but it must not make Web-owned records
    # disappear merely because this account has not linked Telegram yet.
    native_items = _native_jobs_for_account(account)
    if not _flags()["copyfast_enabled"]:
        return await _bridge("GET", "/internal/v1/jobs", account=account, request=request)
    if not _canonical_companion_ready(account):
        return _native_read_envelope(native_items, kind="jobs", canonical_unavailable=True)
    canonical = await _bridge("GET", "/internal/v1/jobs", account=account, request=request)
    if canonical.get("ok"):
        return _merge_bridge_list_with_native(canonical, native_items)
    # A failed canonical read never becomes a fabricated canonical result.
    # Return the independently owner-scoped local model with its source
    # explicitly marked instead of suppressing real Web records.
    return _native_read_envelope(native_items, kind="jobs", canonical_unavailable=True)


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str, request: Request, account: dict = Depends(require_account)):
    native_job = parse_native_job_id(job_id)
    if native_job is not None:
        record = get_native_job(str(account.get("id") or ""), job_id)
        if record:
            item = _native_job_compatibility_record(record)
            if item:
                return envelope(
                    True,
                    "Đã tải dữ liệu Job Web-native của tài khoản hiện tại.",
                    data={**item, "read_model": "jobs", "canonical_available": False},
                    status_name="read_only",
                )
        return envelope(
            False,
            "Không tìm thấy Job Web-native thuộc tài khoản hiện tại.",
            status_name="guarded",
            error_code="WEB_NATIVE_JOB_NOT_FOUND",
        )
    # Reserve the typed namespace. A malformed/unknown native-shaped ID must
    # never be forwarded to the canonical bridge as if it were canonical.
    if str(job_id or "").strip().startswith(("wnj:", "wna:")):
        return envelope(
            False,
            "Không tìm thấy Job Web-native thuộc tài khoản hiện tại.",
            status_name="guarded",
            error_code="WEB_NATIVE_JOB_NOT_FOUND",
        )
    job_id = _canonical_route_identifier(job_id, "Mã job")
    if not _flags()["copyfast_enabled"] or _canonical_companion_ready(account):
        return await _bridge("GET", f"/internal/v1/jobs/{job_id}", account=account, request=request)
    return envelope(
        False,
        "Không tìm thấy Job Web-native thuộc tài khoản hiện tại.",
        status_name="guarded",
        error_code="WEB_NATIVE_JOB_NOT_FOUND",
    )


@router.get("/assets")
async def assets(request: Request, account: dict = Depends(require_account)):
    # Asset Vault source files and sealed Web-native job outputs remain
    # separate kinds, but the compatibility list can render both with opaque
    # IDs and the usual generic download fields.
    native_items = _native_assets_for_account(account)
    if not _flags()["copyfast_enabled"]:
        return await _bridge("GET", "/internal/v1/assets", account=account, request=request)
    if not _canonical_companion_ready(account):
        return _native_read_envelope(native_items, kind="assets", canonical_unavailable=True)
    canonical = await _bridge("GET", "/internal/v1/assets", account=account, request=request)
    if canonical.get("ok"):
        return _merge_bridge_list_with_native(canonical, native_items)
    return _native_read_envelope(native_items, kind="assets", canonical_unavailable=True)


@router.get("/assets/{asset_id}/download")
async def asset_download(asset_id: str, request: Request, account: dict = Depends(require_account)):
    # A typed local ID is never sent to the Bot. The delegated local handlers
    # recheck owner, lifecycle and the exact private artifact before bytes can
    # leave the server.
    native_response = await _native_asset_delivery(asset_id, account)
    if native_response is not None:
        return native_response
    if str(asset_id or "").strip().startswith(("wnj:", "wna:")):
        return envelope(
            False,
            "Tài sản Web-native chưa sẵn sàng để tải.",
            status_name="guarded",
            error_code="WEB_NATIVE_ASSET_UNAVAILABLE",
        )
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


async def _feature_action(action: str, feature: str, payload: FeatureRequest, request: Request, account: dict, *, session_id: str = "") -> dict:
    # Companion/account parity routes live in the public registry so they can
    # be discovered and handed back to Bot, but they are never generic engine
    # feature endpoints. Restrict the dynamic draft/estimate/confirm API to
    # the explicit intake-contract keys rather than letting a route name turn
    # notes, referral, wallet or Admin metadata into a Bot feature call.
    if feature not in FEATURE_BY_KEY or feature not in FEATURE_EXECUTION_CANDIDATE_KEYS:
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
        if not _web_feature_execution_available(feature):
            return envelope(False, "Web App chưa có adapter tạo job canonical đã được phê duyệt; chỉ draft và estimate đang khả dụng.", status_name="guarded", error_code="WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED")
        contract_error = _feature_input_contract_error(feature, values, action=action)
        if contract_error:
            return _feature_input_contract_response(feature, contract_error)
        key = _require_key(key)
        quote_state = _claim_feature_quote_receipt(
            receipt=payload.web_quote_receipt,
            account=account,
            session_id=session_id,
            feature=feature,
            values=values,
            idempotency_key=key,
        )
        if quote_state != "claimed":
            return _feature_quote_required_response(quote_state)
        scope = f"feature:{account['id']}:{feature}:confirm"
        result = await _run_idempotent(
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
        # An ambiguous outage retains the same receipt/key pairing for a safe
        # retry. A known rejected response releases it; a canonical lifecycle
        # acceptance permanently consumes it.
        if not _retryable_bridge_response(result):
            _settle_feature_quote_receipt(
                receipt=payload.web_quote_receipt,
                idempotency_key=key,
                accepted=bool(result.get("ok")) and str(result.get("status") or "") in FEATURE_CONFIRM_ACCEPTED_STATUSES,
            )
        return result
    contract_error = _feature_input_contract_error(feature, values, action=action)
    if contract_error:
        return _feature_input_contract_response(feature, contract_error)
    result = await _bridge(
        "POST",
        f"/internal/v1/features/{feature}/{action}",
        account=account,
        request=request,
        payload={"input": values, "idempotency_key": key if key else None},
    )
    if action == "estimate":
        return _issue_feature_quote_receipt(result, account=account, session_id=session_id, feature=feature, values=values)
    return result


def _feature_session_id(request: Request, account: dict) -> str:
    """Derive receipt binding from the signed cookie, never request input."""
    session = current_session(request)
    if str(session["account"].get("id") or "") != str(account.get("id") or ""):
        raise HTTPException(status_code=403, detail="Phiên feature không khớp với tài khoản đã xác thực")
    return str(session.get("session_id") or "")


@router.post("/features/{feature}/draft")
async def feature_draft(feature: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_csrf)):
    return await _feature_action("draft", feature, payload, request, account)


@router.post("/features/{feature}/estimate")
async def feature_estimate(feature: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_csrf)):
    return await _feature_action("estimate", feature, payload, request, account, session_id=_feature_session_id(request, account))


@router.post("/features/{feature}/confirm")
async def feature_confirm(feature: str, payload: FeatureRequest, request: Request, account: dict = Depends(require_csrf)):
    return await _feature_action("confirm", feature, payload, request, account, session_id=_feature_session_id(request, account))


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
    if not _flags()["admin_erp_enabled"]:
        result = envelope(False, "Admin ERP trên Web đang tạm khóa theo feature flag.", status_name="guarded", error_code="WEBAPP_ADMIN_ERP_DISABLED")
        _record_admin_write_audit(account, request, "admin.job.retry", job_id, result)
        return result
    if not _flags()["admin_writes_enabled"]:
        result = envelope(False, "Admin ERP Web hiện chỉ đọc; retry job chưa được bật.", status_name="guarded", error_code="WEBAPP_ADMIN_WRITES_DISABLED")
        _record_admin_write_audit(account, request, "admin.job.retry", job_id, result)
        return result
    account = await require_canonical_admin_csrf(request)
    key = _require_key(payload.idempotency_key or request.headers.get("Idempotency-Key", ""))
    result = await _run_idempotent(
        f"admin:{account['id']}:retry:{job_id}",
        key,
        lambda: _bridge("POST", f"/internal/v1/admin/jobs/{job_id}/retry", account=account, request=request, payload={"idempotency_key": key}),
    )
    _record_admin_write_audit(account, request, "admin.job.retry", job_id, result)
    return result


@router.post("/admin/jobs/{job_id}/refund")
async def admin_refund_job(job_id: str, payload: FeatureRequest, request: Request):
    account = require_admin_csrf(request)
    job_id = _canonical_route_identifier(job_id, "Mã job")
    if not _flags()["admin_erp_enabled"]:
        result = envelope(False, "Admin ERP trên Web đang tạm khóa theo feature flag.", status_name="guarded", error_code="WEBAPP_ADMIN_ERP_DISABLED")
        _record_admin_write_audit(account, request, "admin.job.refund", job_id, result)
        return result
    if not _flags()["admin_writes_enabled"]:
        result = envelope(False, "Admin ERP Web hiện chỉ đọc; refund chưa được bật.", status_name="guarded", error_code="WEBAPP_ADMIN_WRITES_DISABLED")
        _record_admin_write_audit(account, request, "admin.job.refund", job_id, result)
        return result
    account = await require_canonical_admin_csrf(request)
    key = _require_key(payload.idempotency_key or request.headers.get("Idempotency-Key", ""))
    result = await _run_idempotent(
        f"admin:{account['id']}:refund:{job_id}",
        key,
        lambda: _bridge("POST", f"/internal/v1/admin/jobs/{job_id}/refund", account=account, request=request, payload={"idempotency_key": key}),
    )
    _record_admin_write_audit(account, request, "admin.job.refund", job_id, result)
    return result


@router.post("/admin/features/{feature}/freeze")
async def admin_freeze_feature(feature: str, payload: FreezeRequest, request: Request):
    account = require_admin_csrf(request)
    if feature not in FEATURE_BY_KEY:
        raise HTTPException(status_code=404, detail="Tính năng chưa có trong parity registry")
    if not _flags()["admin_erp_enabled"]:
        result = envelope(False, "Admin ERP trên Web đang tạm khóa theo feature flag.", status_name="guarded", error_code="WEBAPP_ADMIN_ERP_DISABLED")
        _record_admin_write_audit(account, request, "admin.feature.freeze", feature, result)
        return result
    if not _flags()["admin_writes_enabled"]:
        result = envelope(False, "Admin ERP Web hiện chỉ đọc; freeze feature chưa được bật.", status_name="guarded", error_code="WEBAPP_ADMIN_WRITES_DISABLED")
        _record_admin_write_audit(account, request, "admin.feature.freeze", feature, result)
        return result
    account = await require_canonical_admin_csrf(request)
    key = _require_key(payload.idempotency_key)
    result = await _run_idempotent(
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
    _record_admin_write_audit(account, request, "admin.feature.freeze", feature, result)
    return result
