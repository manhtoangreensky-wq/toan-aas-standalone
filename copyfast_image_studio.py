"""Private Web-native Image Creative Studio.

This router is a signed-account creative-direction workspace.  It records
artboards, bounded text directions, revisions and UUID references to existing
owned image metadata.  It intentionally does not accept image bytes, remote
media URLs or execute an image operation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, image_studio_enabled, memory_center_enabled, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/image-studio", tags=["Web Image Creative Studio"])

ARTBOARD_STATES = frozenset({"draft", "review", "approved", "archived"})
WRITABLE_ARTBOARD_STATES = frozenset({"draft"})
DIRECTION_STATES = frozenset({"active", "archived"})
IMAGE_INTENTS = frozenset({"create", "edit", "upscale", "image_to_image", "remove_background"})
OPERATIONS = IMAGE_INTENTS
ASPECT_RATIOS = frozenset({"1:1", "4:5", "3:4", "16:9", "9:16", "3:2", "2:3", "custom"})
OUTPUT_FORMATS = frozenset({"png", "jpg", "webp"})
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp"})
IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
PROMPT_COMPOSER_GOAL_CODES = frozenset({"product", "ad", "cinematic", "custom"})
PROMPT_COMPOSER_RATIOS = frozenset({"1:1", "9:16", "16:9", "4:5", "3:4", "4:3", "3:2", "2:3", "21:9"})
PROMPT_COMPOSER_LANGUAGES = frozenset({"vi", "en"})
PROMPT_COMPOSER_RATIO_ALIASES = {
    "1:1": "1:1", "1x1": "1:1", "square": "1:1", "vuong": "1:1", "vuông": "1:1",
    "9:16": "9:16", "9x16": "9:16", "vertical": "9:16", "doc": "9:16", "dọc": "9:16", "reels": "9:16", "tiktok": "9:16",
    "16:9": "16:9", "16x9": "16:9", "horizontal": "16:9", "ngang": "16:9", "youtube": "16:9",
    "4:5": "4:5", "4x5": "4:5", "post": "4:5",
    "3:4": "3:4", "3x4": "3:4", "portrait": "3:4",
    "4:3": "4:3", "4x3": "4:3", "slide": "4:3",
    "3:2": "3:2", "3x2": "3:2", "landscape": "3:2",
    "2:3": "2:3", "2x3": "2:3",
    "21:9": "21:9", "21x9": "21:9", "ultrawide": "21:9",
}
# This is a narrow imitation guard only.  It cannot establish ownership or
# copyright clearance; it merely keeps explicit author/artist-style requests
# out of the request-only prompt composer until a reviewed policy workflow is
# available.
PROMPT_COMPOSER_ORIGINALITY_MARKERS = (
    "giống nghệ sĩ", "giống ca sĩ", "giống bài", "như bài", "cover bài", "remix bài",
    "style của", "phong cách của", "nhái giọng", "bắt chước giọng", "sound like",
    "sounds like", "in the style of", "copy melody", "cover song", "remix song",
    "artist style", "same melody",
)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URL_PATTERN = re.compile(r"(?:https?://|www\.|file:|data:|javascript:)", re.IGNORECASE)
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|"
    r"password|passphrase|authorization|otp|cvv|cvc|private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{12,}|github_pat_[A-Za-z0-9_]{12,}|"
    r"gh[pousr]_[A-Za-z0-9]{12,}|xox[bpars]-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:txid|transaction\s+(?:hash|id|reference)|mã\s*(?:giao\s*)?(?:dịch|thanh\s*toán)|"
    r"bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|qr\s*(?:code|thanh\s*toán))\b",
    re.IGNORECASE,
)
EXTERNAL_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|render|job|media|asset|file)[ _-]*(?:id|ref(?:erence)?|token)|"
    r"telegram[ _-]*file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+",
    re.IGNORECASE,
)
# Authoring text is rendered as escaped text by the Portal, but reject the
# narrow family of markup/execution-shaped payloads at the API boundary too.
MARKUP_EXECUTION_PATTERN = re.compile(
    r"<\s*/?\s*(?:script|svg|img|iframe|object|embed|style|link|meta|base|form|input|video|audio)\b|\bon[a-z]+\s*=",
    re.IGNORECASE,
)

MAX_ARTBOARDS_PER_ACCOUNT = 300
MAX_DIRECTIONS_PER_ARTBOARD = 120
MAX_VERSIONS_PER_ENTITY = 100
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
MAX_EVENT_LIMIT = 50
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
ARCHIVED_ORDINAL_BASE = 1_000_000
MAX_PROMPT_COMPOSER_SUBJECT = 260
MAX_PROMPT_COMPOSER_STYLE = 180
MAX_PROMPT_COMPOSER_CUSTOM_GOAL = 180
MAX_PROMPT_COMPOSER_TEXT = 3_200
# Keep this explicit handoff compatible with Memory Center's durable storage
# envelope without importing that router.  The save action remains owned by
# Image Studio and has no runtime dependency on a second API module.
MAX_MEMORY_NOTE_TITLE = 160
MAX_MEMORY_NOTE_CONTENT = 12_000
MAX_MEMORY_NOTES_PER_ACCOUNT = 1_000


def _require_enabled() -> None:
    if not image_studio_enabled():
        raise HTTPException(
            status_code=503,
            detail="Image Creative Studio đang tạm dừng để bảo trì. WEBAPP_IMAGE_STUDIO_ENABLED chưa được bật.",
        )


def _require_memory_handoff_enabled() -> None:
    """Require the separate Web-owned Memory Center capability for a save.

    Prompt composition remains available as a request-only Image Studio tool.
    The explicit durable handoff must not bypass Memory Center maintenance or
    silently turn a private Web note into Image Studio runtime state.
    """

    if not memory_center_enabled():
        raise HTTPException(
            status_code=503,
            detail="Memory Center đang tạm dừng để bảo trì. WEBAPP_MEMORY_CENTER_ENABLED chưa được bật.",
        )


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _optional_uuid(value: Any, *, label: str) -> str | None:
    raw = str(value or "").strip()
    return _uuid(raw, label=label) if raw else None


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


def _sensitive_text(value: str) -> bool:
    return bool(
        URL_PATTERN.search(value)
        or SECRET_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or PAYMENT_PATTERN.search(value)
        or EXTERNAL_HANDLE_PATTERN.search(value)
        or MARKUP_EXECUTION_PATTERN.search(value)
        or "-----begin" in value.lower()
    )


def _line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu ngoài hoặc chứng từ thanh toán")
    return text


def _body(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu ngoài hoặc chứng từ thanh toán")
    return text


def _prompt_composer_ratio(value: Any) -> str:
    """Canonicalize only the short, local aspect-ratio vocabulary.

    This deliberately does not accept an arbitrary custom ratio: unlike the
    durable Image Studio artboard, the stateless composer must have a compact
    browser contract that can be validated before any draft text is rendered.
    """

    raw = _line(value, label="Tỷ lệ prompt ảnh", minimum=1, maximum=32).lower()
    normalized = raw.replace("×", "x").replace(" ", "").replace("x", ":")
    ratio = PROMPT_COMPOSER_RATIO_ALIASES.get(normalized)
    if ratio not in PROMPT_COMPOSER_RATIOS:
        raise ValueError("Tỷ lệ prompt ảnh không hợp lệ")
    return ratio


def _prompt_composer_marker(*parts: Any) -> str:
    normalized = re.sub(r"\s+", " ", "\n".join(str(part or "") for part in parts)).strip().lower()[:10_000]
    for marker in PROMPT_COMPOSER_ORIGINALITY_MARKERS:
        if marker in normalized:
            return marker
    return ""


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Tags phải là danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        tag = _line(raw, label="Tag", minimum=1, maximum=48)
        marker = tag.casefold()
        if marker not in seen:
            seen.add(marker)
            result.append(tag)
    if len(result) > 20:
        raise ValueError("Tối đa 20 tags")
    return result


def _decode_tags(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed if isinstance(item, str)][:20] if isinstance(parsed, list) else []


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _excerpt(value: Any, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[:max(1, limit - 1)].rstrip()}…"


class ArtboardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    image_intent: str = "create"
    language: str = "vi"
    aspect_ratio: str = "1:1"
    output_format: str = "png"
    creative_brief: str = ""
    style_direction: str = ""
    negative_direction: str = ""
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên artboard", minimum=2, maximum=180)

    @field_validator("image_intent")
    @classmethod
    def _intent(cls, value: str) -> str:
        normalized = _line(value, label="Mục đích ảnh", minimum=1, maximum=32).lower()
        if normalized not in IMAGE_INTENTS:
            raise ValueError("Mục đích Image Studio không hợp lệ")
        return normalized

    @field_validator("language")
    @classmethod
    def _language(cls, value: str) -> str:
        return _line(value, label="Ngôn ngữ", minimum=1, maximum=100)

    @field_validator("aspect_ratio")
    @classmethod
    def _ratio(cls, value: str) -> str:
        normalized = _line(value, label="Tỷ lệ khung hình", minimum=1, maximum=16)
        if normalized not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ khung hình không hợp lệ")
        return normalized

    @field_validator("output_format")
    @classmethod
    def _format(cls, value: str) -> str:
        normalized = _line(value, label="Định dạng dự kiến", minimum=1, maximum=16).lower()
        if normalized not in OUTPUT_FORMATS:
            raise ValueError("Định dạng dự kiến không hợp lệ")
        return normalized

    @field_validator("creative_brief")
    @classmethod
    def _brief(cls, value: str) -> str:
        return _body(value, label="Creative brief", maximum=12_000)

    @field_validator("style_direction")
    @classmethod
    def _style(cls, value: str) -> str:
        return _body(value, label="Style direction", maximum=6_000, allow_empty=True)

    @field_validator("negative_direction")
    @classmethod
    def _negative(cls, value: str) -> str:
        return _body(value, label="Điều cần tránh", maximum=4_000, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Project ID")


class ArtboardCreateRequest(ArtboardPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ArtboardUpdateRequest(ArtboardPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class LifecycleRequest(RevisionRequest):
    state: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái", minimum=1, maximum=20).lower()
        if normalized not in ARTBOARD_STATES:
            raise ValueError("Trạng thái artboard không hợp lệ")
        return normalized


class RestoreVersionRequest(RevisionRequest):
    target_revision: int = Field(ge=1, le=MAX_VERSIONS_PER_ENTITY)


class DirectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    operation: str = "create"
    prompt_text: str = ""
    edit_instructions: str = ""
    composition_notes: str = ""
    negative_direction: str = ""
    asset_id: str | None = None
    reference_asset_id: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên creative direction", minimum=2, maximum=180)

    @field_validator("operation")
    @classmethod
    def _operation(cls, value: str) -> str:
        normalized = _line(value, label="Workflow ảnh", minimum=1, maximum=32).lower()
        if normalized not in OPERATIONS:
            raise ValueError("Workflow Image Studio không hợp lệ")
        return normalized

    @field_validator("prompt_text")
    @classmethod
    def _prompt(cls, value: str) -> str:
        return _body(value, label="Prompt direction", maximum=12_000, allow_empty=True)

    @field_validator("edit_instructions")
    @classmethod
    def _edit(cls, value: str) -> str:
        return _body(value, label="Hướng dẫn chỉnh sửa", maximum=8_000, allow_empty=True)

    @field_validator("composition_notes")
    @classmethod
    def _composition(cls, value: str) -> str:
        return _body(value, label="Bố cục", maximum=6_000, allow_empty=True)

    @field_validator("negative_direction")
    @classmethod
    def _negative(cls, value: str) -> str:
        return _body(value, label="Điều cần tránh", maximum=4_000, allow_empty=True)

    @field_validator("asset_id")
    @classmethod
    def _asset(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Asset ID")

    @field_validator("reference_asset_id")
    @classmethod
    def _reference(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Reference Asset ID")

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    def model_post_init(self, __context: Any) -> None:
        if self.asset_id and self.asset_id == self.reference_asset_id:
            raise ValueError("Asset ID và Reference Asset ID phải khác nhau")
        if self.operation == "create" and not self.prompt_text:
            raise ValueError("Workflow create cần Prompt direction")
        if self.operation in {"edit", "image_to_image"} and not (self.prompt_text or self.edit_instructions):
            raise ValueError("Workflow này cần Prompt direction hoặc hướng dẫn chỉnh sửa")
        if self.operation != "create" and not self.asset_id:
            raise ValueError("Workflow này cần Asset Vault image reference")


class DirectionCreateRequest(DirectionPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class DirectionUpdateRequest(DirectionPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ReorderRequest(RevisionRequest):
    direction_ids: list[str] = Field(min_length=0, max_length=MAX_DIRECTIONS_PER_ARTBOARD)

    @field_validator("direction_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        values = [_uuid(item, label="Direction ID") for item in value]
        if len(values) != len(set(values)):
            raise ValueError("Direction ID không được trùng")
        return values


class ImagePromptComposerRequest(BaseModel):
    """Bounded, non-persistent request for a deterministic image prompt draft.

    No image, URL, asset reference, project, provider/model selection, job,
    payment, wallet, idempotency or publish field is accepted.  This endpoint
    composes text only; a customer must explicitly create and review a durable
    Image Studio artboard later if they want to retain creative direction.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    goal_code: str
    custom_goal: str = ""
    subject: str
    style: str = ""
    ratio: str = "1:1"
    language: str = "vi"

    @field_validator("goal_code")
    @classmethod
    def validate_goal_code(cls, value: str) -> str:
        normalized = _line(value, label="Mục tiêu prompt ảnh", minimum=1, maximum=32).lower()
        if normalized not in PROMPT_COMPOSER_GOAL_CODES:
            raise ValueError("Mục tiêu prompt ảnh không hợp lệ")
        return normalized

    @field_validator("custom_goal")
    @classmethod
    def validate_custom_goal(cls, value: str) -> str:
        normalized = _line(value, label="Mục tiêu tùy chỉnh", minimum=2, maximum=MAX_PROMPT_COMPOSER_CUSTOM_GOAL, allow_empty=True)
        if normalized and len(normalized) < 2:
            raise ValueError("Mục tiêu tùy chỉnh cần từ 2 đến 180 ký tự hợp lệ")
        return normalized

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        return _line(value, label="Chủ thể", minimum=2, maximum=MAX_PROMPT_COMPOSER_SUBJECT)

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: str) -> str:
        normalized = _line(value, label="Phong cách", minimum=2, maximum=MAX_PROMPT_COMPOSER_STYLE, allow_empty=True)
        if normalized and len(normalized) < 2:
            raise ValueError("Phong cách cần từ 2 đến 180 ký tự hợp lệ")
        return normalized

    @field_validator("ratio")
    @classmethod
    def validate_ratio(cls, value: str) -> str:
        return _prompt_composer_ratio(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = _line(value, label="Ngôn ngữ", minimum=2, maximum=8).lower()
        if normalized not in PROMPT_COMPOSER_LANGUAGES:
            raise ValueError("Ngôn ngữ prompt ảnh chỉ hỗ trợ vi hoặc en")
        return normalized

    def model_post_init(self, __context: Any) -> None:
        if self.goal_code == "custom" and not self.custom_goal:
            raise ValueError("Mục tiêu tùy chỉnh là bắt buộc khi chọn custom")
        if self.goal_code != "custom" and self.custom_goal:
            raise ValueError("Mục tiêu tùy chỉnh chỉ dùng khi chọn custom")


class ImagePromptComposerMemorySaveRequest(ImagePromptComposerRequest):
    """Narrow, explicit handoff of a reviewed composer selection to Memory.

    The browser may provide only the bounded ingredients necessary to recreate
    the deterministic draft.  It cannot send a rendered prompt/body/title,
    pick an account, use an asset, or point at a Bot pending result.
    """

    destination: str
    idempotency_key: str

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        if _line(value, label="Đích lưu", minimum=1, maximum=32).lower() != "memory_note":
            raise ValueError("Image Prompt Composer hiện chỉ hỗ trợ lưu vào Memory Center")
        return "memory_note"

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


class ImagePromptComposerResult(BaseModel):
    """Strict display schema for the stateless prompt-composer response."""

    model_config = ConfigDict(extra="forbid")

    title: str
    goal_code: str
    goal_label: str
    custom_goal: str
    subject: str
    style: str
    ratio: str
    language: str
    short_prompt: str
    detailed_prompt: str
    negative_prompt: str
    variants: list[str] = Field(min_length=3, max_length=3)
    review_before_use: list[str] = Field(min_length=1, max_length=6)

    @field_validator("title", "goal_label")
    @classmethod
    def validate_result_label(cls, value: str) -> str:
        return _line(value, label="Nhãn kết quả", minimum=1, maximum=320)

    @field_validator("goal_code")
    @classmethod
    def validate_result_goal_code(cls, value: str) -> str:
        if value not in PROMPT_COMPOSER_GOAL_CODES:
            raise ValueError("Mục tiêu kết quả không hợp lệ")
        return value

    @field_validator("custom_goal")
    @classmethod
    def validate_result_custom_goal(cls, value: str) -> str:
        normalized = _line(value, label="Mục tiêu tùy chỉnh kết quả", minimum=2, maximum=MAX_PROMPT_COMPOSER_CUSTOM_GOAL, allow_empty=True)
        if normalized and len(normalized) < 2:
            raise ValueError("Mục tiêu tùy chỉnh kết quả cần từ 2 đến 180 ký tự hợp lệ")
        return normalized

    @field_validator("subject")
    @classmethod
    def validate_result_subject(cls, value: str) -> str:
        return _line(value, label="Chủ thể kết quả", minimum=2, maximum=MAX_PROMPT_COMPOSER_SUBJECT)

    @field_validator("style")
    @classmethod
    def validate_result_style(cls, value: str) -> str:
        return _line(value, label="Phong cách kết quả", minimum=2, maximum=MAX_PROMPT_COMPOSER_STYLE)

    @field_validator("ratio")
    @classmethod
    def validate_result_ratio(cls, value: str) -> str:
        return _prompt_composer_ratio(value)

    @field_validator("language")
    @classmethod
    def validate_result_language(cls, value: str) -> str:
        if value not in PROMPT_COMPOSER_LANGUAGES:
            raise ValueError("Ngôn ngữ kết quả không hợp lệ")
        return value

    @field_validator("short_prompt", "detailed_prompt", "negative_prompt")
    @classmethod
    def validate_result_prompt(cls, value: str) -> str:
        return _body(value, label="Prompt kết quả", maximum=MAX_PROMPT_COMPOSER_TEXT)

    @field_validator("variants")
    @classmethod
    def validate_result_variants(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("Kết quả cần đúng ba biến thể prompt")
        return [_body(item, label="Biến thể prompt", maximum=MAX_PROMPT_COMPOSER_TEXT) for item in value]

    @field_validator("review_before_use")
    @classmethod
    def validate_review_before_use(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list) or not value:
            raise ValueError("Kết quả cần có checklist review")
        return [_line(item, label="Ghi chú review", minimum=2, maximum=320) for item in value]

    def model_post_init(self, __context: Any) -> None:
        if self.goal_code == "custom" and not self.custom_goal:
            raise ValueError("Kết quả custom phải có mục tiêu tùy chỉnh")
        if self.goal_code != "custom" and self.custom_goal:
            raise ValueError("Kết quả không được có mục tiêu tùy chỉnh ngoài custom")


def _prompt_composer_boundary() -> dict[str, Any]:
    """The complete execution boundary for the stateless prompt composer."""

    return {
        "execution": "web_native_deterministic_prompt_only",
        "input_persisted": False,
        "source_image_inspected": False,
        "provider_called": False,
        "image_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _prompt_composer_guard(marker: str) -> dict[str, Any] | None:
    if not marker:
        return None
    return envelope(
        False,
        "Mô tả cần được viết lại theo hướng nguyên bản, không mô phỏng tác giả, nghệ sĩ hoặc phong cách cụ thể.",
        data=_prompt_composer_boundary(),
        status_name="guarded",
        error_code="WEB_IMAGE_PROMPT_ORIGINALITY_GUARD",
    )


def _prompt_composer_goal_label(goal_code: str, custom_goal: str, language: str) -> str:
    if goal_code == "custom":
        return custom_goal
    labels = {
        "vi": {
            "product": "Ảnh sản phẩm",
            "ad": "Ảnh quảng cáo",
            "cinematic": "Ảnh cinematic / key visual video",
        },
        "en": {
            "product": "Product image",
            "ad": "Advertising image",
            "cinematic": "Cinematic / video key visual",
        },
    }
    return labels[language][goal_code]


def _prompt_composer_default_style(goal_code: str, language: str) -> str:
    catalog = {
        "vi": {
            "product": "studio sạch đẹp",
            "ad": "thương hiệu rõ lợi ích",
            "cinematic": "cinematic ánh sáng mạnh",
            "custom": "tối giản, hiện đại",
        },
        "en": {
            "product": "clean studio",
            "ad": "benefit-led brand",
            "cinematic": "strong cinematic lighting",
            "custom": "minimal and contemporary",
        },
    }
    return catalog[language][goal_code]


def _compose_image_prompt(payload: ImagePromptComposerRequest) -> dict[str, Any]:
    """Adapt the Bot's pure image-prompt text recipes into Web-native drafts.

    The Bot source supplied goal labels, style defaults, ratio normalization,
    a short prompt, a detailed prompt, negative guidance and three variants.
    This adaptation intentionally omits its Telegram state, image/file state,
    save/use actions, provider selection and credit language.  It returns no
    media, does no model work and does not retain customer-authored text.
    """

    language = payload.language
    goal_label = _prompt_composer_goal_label(payload.goal_code, payload.custom_goal, language)
    style = payload.style or _prompt_composer_default_style(payload.goal_code, language)
    subject = payload.subject
    ratio = payload.ratio
    review = (
        [
            "Đây là bản nháp text có thể chỉnh sửa; chưa tạo, xem trước hoặc kiểm tra ảnh nào.",
            "Kiểm chứng mọi claim, số liệu, so sánh và nội dung chữ trước khi dùng bên ngoài.",
            "Xác nhận quyền sử dụng thương hiệu, logo, người, địa điểm và mọi reference trước khi dùng.",
            "Rà soát lại prompt theo công cụ bạn chọn; chất lượng, tính chính xác và quyền sử dụng chưa được xác minh.",
        ]
        if language == "vi"
        else [
            "This is an editable text draft; it has not created, inspected or previewed an image.",
            "Verify every claim, number, comparison and text element before external use.",
            "Confirm rights for brands, logos, people, locations and every reference before use.",
            "Review the prompt against the tool you choose; quality, accuracy and rights are not verified.",
        ]
    )

    if language == "vi":
        short_prompt = (
            f"{subject}, mục tiêu {goal_label}, phong cách {style}, tỷ lệ {ratio}, "
            "chủ thể rõ, bố cục sạch, ánh sáng chuyên nghiệp, màu sắc cân bằng, không watermark, không thêm chữ không được yêu cầu"
        )
        detailed_prompt = (
            f"Chủ thể: {subject}. Mục tiêu visual: {goal_label}. Phong cách: {style}. Tỷ lệ: {ratio}. "
            "Bố cục đặt chủ thể chính ở điểm nhìn rõ ràng, có khoảng thở phù hợp cho kênh sử dụng, "
            "ánh sáng nhất quán, màu sắc hài hòa và chi tiết có chủ đích. Giữ logo hoặc chữ quan trọng "
            "nếu đã được cấp quyền; không tự thêm claim, logo hoặc chữ thừa. Đây là hướng prompt để biên tập, không phải yêu cầu thực thi ảnh."
        )
        negative_prompt = (
            "chất lượng thấp, mờ, chủ thể hoặc khuôn mặt biến dạng, tay lỗi, logo hỏng, chữ sai hoặc thừa, "
            "watermark, nền rối, phơi sáng quá mức hoặc thiếu sáng"
        )
        variants = [
            f"{subject}, ảnh làm rõ sản phẩm hoặc thông điệp chính, phong cách {style}, {ratio}, bố cục hero sạch, ánh sáng premium, chi tiết có chủ đích, không watermark",
            f"{subject}, key visual thương hiệu tinh tế, phong cách {style}, {ratio}, điểm nhìn rõ, nền gọn, màu cân bằng, chỉ dùng logo/chữ đã được cấp quyền",
            f"{subject}, visual social nổi bật nhưng dễ đọc, phong cách {style}, {ratio}, chủ thể sạch, khoảng trống cho caption, không chữ tự phát hoặc watermark",
        ]
        title = f"Bản nháp prompt ảnh: {subject}"
    else:
        short_prompt = (
            f"{subject}, goal {goal_label}, style {style}, ratio {ratio}, "
            "clear subject, clean composition, professional lighting, balanced color, no watermark, no unrequested text"
        )
        detailed_prompt = (
            f"Subject: {subject}. Visual goal: {goal_label}. Style: {style}. Ratio: {ratio}. "
            "Place the primary subject at a clear focal point with suitable negative space for the intended channel, "
            "consistent lighting, balanced color and deliberate detail. Preserve important logo or text only when it is authorized; "
            "do not add claims, logos or extra text. This is an editable prompt direction, not an image-execution request."
        )
        negative_prompt = (
            "low quality, blur, distorted subject or face, broken hands, broken logo, wrong or extra text, watermark, "
            "messy background, overexposure, underexposure"
        )
        variants = [
            f"{subject}, product or message-led hero visual, {style}, {ratio}, clean focal composition, premium lighting, deliberate detail, no watermark",
            f"{subject}, refined brand key visual, {style}, {ratio}, clear focal point, tidy background, balanced color, authorized logo or text only",
            f"{subject}, eye-catching but legible social visual, {style}, {ratio}, clean subject, caption space, no invented text or watermark",
        ]
        title = f"Image prompt draft: {subject}"

    return ImagePromptComposerResult.model_validate(
        {
            "title": title,
            "goal_code": payload.goal_code,
            "goal_label": goal_label,
            "custom_goal": payload.custom_goal,
            "subject": subject,
            "style": style,
            "ratio": ratio,
            "language": language,
            "short_prompt": short_prompt,
            "detailed_prompt": detailed_prompt,
            "negative_prompt": negative_prompt,
            "variants": variants,
            "review_before_use": review,
        }
    ).model_dump()


def _image_prompt_composer_memory_note(composer: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Serialize a fresh deterministic composer result as one Web note.

    This is deliberately not a generic browser-authored note endpoint.  The
    full text is derived again from bounded composer inputs inside the write
    transaction, so a caller cannot substitute a different title, prompt,
    result object or private payload while reusing the visible save control.
    """

    try:
        result = ImagePromptComposerResult.model_validate(composer).model_dump()
        title = _line(
            "Image Prompt Composer",
            label="Tiêu đề ghi chú",
            minimum=3,
            maximum=MAX_MEMORY_NOTE_TITLE,
        )
        lines = [
            "Image Prompt Composer — bản nháp Web đã được dựng lại trên máy chủ.",
            f"Tiêu đề bản nháp: {result['title']}",
            f"Mục tiêu: {result['goal_label']}",
            f"Chủ thể: {result['subject']}",
            f"Phong cách: {result['style']}",
            f"Tỷ lệ: {result['ratio']}",
            f"Ngôn ngữ: {result['language']}",
            "",
            "## Prompt ngắn",
            result["short_prompt"],
            "",
            "## Prompt chi tiết",
            result["detailed_prompt"],
            "",
            "## Negative prompt",
            result["negative_prompt"],
            "",
            "## Ba biến thể",
        ]
        for ordinal, variant in enumerate(result["variants"], start=1):
            lines.append(f"### Biến thể {ordinal}")
            lines.append(str(variant))
        lines.extend(("", "## Kiểm tra trước khi sử dụng"))
        lines.extend(f"- {item}" for item in result["review_before_use"])
        lines.extend(
            (
                "",
                "Ghi chú này không tạo ảnh, output, job, tài sản, thanh toán, publish hay gửi Telegram.",
            )
        )
        content = _body(
            "\n".join(lines),
            label="Nội dung ghi chú Image Prompt Composer",
            maximum=MAX_MEMORY_NOTE_CONTENT,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return title, content, ["image-prompt-composer", f"image-goal-{result['goal_code']}"]


def _image_prompt_composer_memory_boundaries(
    *,
    draft_recomputed_on_server: bool = True,
    web_note_persisted: bool = True,
) -> dict[str, bool | str]:
    """Truthful facts for a Web-note handoff, not an image execution."""

    return {
        "execution": "web_native_memory_note_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_note_persisted": web_note_persisted,
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_image_inspected": False,
        "provider_called": False,
        "image_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _boundary(**extra: Any) -> dict[str, Any]:
    return {
        "execution": "authoring_only",
        "provider_called": False,
        "image_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "payment_processed": False,
        "media_uploads": False,
        "browser_media_url": False,
        "preview_available": False,
        "output_delivery": "guarded",
        **extra,
    }


def _guarded(message: str, code: str) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(), status_name="guarded", error_code=code)


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary()
    artboard = source.get("artboard")
    if isinstance(artboard, dict) and isinstance(artboard.get("id"), str):
        data["artboard"] = {
            "id": str(artboard["id"]),
            "revision": int(artboard.get("revision") or 0),
            "state": str(artboard.get("state") or ""),
        }
    direction = source.get("direction")
    if isinstance(direction, dict) and isinstance(direction.get("id"), str):
        data["direction"] = {
            "id": str(direction["id"]),
            "artboard_id": str(direction.get("artboard_id") or ""),
            "revision": int(direction.get("revision") or 0),
            "state": str(direction.get("state") or ""),
        }
    note = source.get("note")
    if isinstance(note, dict) and isinstance(note.get("id"), str):
        # The generic idempotency table is a short-lived replay mechanism, not
        # a second location for private composer text.  Keep its note receipt
        # strictly opaque; the signed owner can read the note through Memory
        # Center after the explicit handoff completed.
        data["note"] = {
            "id": str(note["id"]),
            "revision": int(note.get("revision") or 0),
            "state": str(note.get("state") or ""),
            "category": str(note.get("category") or ""),
            "priority": str(note.get("priority") or ""),
        }
    for name in (
        "execution",
        "reordered",
        "history_snapshot_recorded",
        "direction_count",
        "destination",
        "draft_recomputed_on_server",
        "web_note_persisted",
        "browser_result_persisted",
        "pending_bot_save_created",
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "source_image_inspected",
        "provider_called",
        "image_created",
        "output_created",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "asset_saved",
        "publish_action_created",
        "delivery_created",
        "fact_checked",
        "rights_verified",
    ):
        if name in source:
            data[name] = source[name]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Image Creative Studio."),
        data=data,
        status_name=str(response.get("status") or "draft"),
    )


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-image-studio:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            fingerprint = str(existing[1] or "")
            if not fingerprint or not hmac.compare_digest(fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Image Studio không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Image Studio không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-image-studio:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded("Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_IMAGE_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _artboard_row(conn: Any, *, artboard_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, title, image_intent, language, aspect_ratio, output_format,
                  creative_brief, style_direction, negative_direction, tags_json, lifecycle,
                  revision, created_at, updated_at, archived_at
           FROM web_image_artboards WHERE id=? AND account_id=?""",
        (artboard_id, account_id),
    ).fetchone()


def _direction_row(conn: Any, *, artboard_id: str, direction_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, artboard_id, ordinal, title, operation, prompt_text, edit_instructions,
                  composition_notes, negative_direction, asset_id, reference_asset_id, tags_json,
                  state, revision, created_at, updated_at, archived_at
           FROM web_image_directions WHERE id=? AND artboard_id=? AND account_id=?""",
        (direction_id, artboard_id, account_id),
    ).fetchone()


def _artboard_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy artboard thuộc Web account hiện tại.", "WEB_IMAGE_ARTBOARD_NOT_FOUND")


def _direction_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy creative direction thuộc artboard hiện tại.", "WEB_IMAGE_DIRECTION_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return _guarded("Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại trước khi lưu tiếp.", "WEB_IMAGE_REVISION_CONFLICT")


def _artboard_writable(row: tuple[Any, ...]) -> dict[str, Any] | None:
    state = str(row[11])
    if state == "archived":
        return _guarded("Artboard đã archive; hãy khôi phục về Draft trước khi tiếp tục.", "WEB_IMAGE_ARTBOARD_ARCHIVED")
    if state == "approved":
        return _guarded("Artboard đã self-review. Hãy chuyển về Draft trước khi chỉnh sửa.", "WEB_IMAGE_ARTBOARD_APPROVED")
    if state == "review":
        return _guarded("Artboard đang self-review. Hãy chuyển về Draft trước khi chỉnh sửa.", "WEB_IMAGE_ARTBOARD_REVIEW_LOCKED")
    if state not in WRITABLE_ARTBOARD_STATES:
        return _guarded("Trạng thái artboard không cho phép authoring.", "WEB_IMAGE_ARTBOARD_GUARDED")
    return None


def _project_reference(conn: Any, *, account_id: str, project_id: str | None, active: bool = True) -> dict[str, Any]:
    if not project_id:
        return {}
    state_clause = "AND state='active'" if active else ""
    row = conn.execute(
        f"SELECT id, title, state FROM web_projects WHERE id=? AND account_id=? {state_clause}",
        (project_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=422, detail="Project liên kết không hợp lệ hoặc không còn hoạt động")
    return {"project": {"id": str(row[0]), "title": str(row[1]), "state": str(row[2])}}


def _asset_row(conn: Any, *, asset_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, display_name, original_filename, extension, content_type, state, updated_at
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()


def _image_asset_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "display_name": str(row[1]),
        "extension": str(row[3]),
        "content_type": str(row[4]),
        "state": str(row[5]),
        "updated_at": str(row[6]),
    }


def _is_image_asset(row: tuple[Any, ...]) -> bool:
    return str(row[3]).lower() in IMAGE_EXTENSIONS and str(row[4]).lower() in IMAGE_CONTENT_TYPES


def _active_image_asset(conn: Any, *, asset_id: str | None, account_id: str, label: str) -> dict[str, Any] | None:
    if not asset_id:
        return None
    row = _asset_row(conn, asset_id=asset_id, account_id=account_id)
    if not row or str(row[5]) != "active" or not _is_image_asset(row):
        raise HTTPException(status_code=422, detail=f"{label} phải là ảnh JPEG, PNG hoặc WebP đang hoạt động thuộc Web account")
    return _image_asset_public(row)


def _validate_asset_refs(conn: Any, *, account_id: str, snapshot: dict[str, Any]) -> None:
    _active_image_asset(conn, asset_id=snapshot.get("asset_id"), account_id=account_id, label="Asset reference")
    _active_image_asset(conn, asset_id=snapshot.get("reference_asset_id"), account_id=account_id, label="Reference asset")


def _artboard_snapshot(payload: ArtboardPayload, *, lifecycle: str = "draft") -> dict[str, Any]:
    return {
        "title": payload.title,
        "image_intent": payload.image_intent,
        "language": payload.language,
        "aspect_ratio": payload.aspect_ratio,
        "output_format": payload.output_format,
        "creative_brief": payload.creative_brief,
        "style_direction": payload.style_direction,
        "negative_direction": payload.negative_direction,
        "tags": list(payload.tags),
        "project_id": payload.project_id,
        "lifecycle": lifecycle,
    }


def _artboard_snapshot_from_row(row: tuple[Any, ...], *, lifecycle: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[2]), "image_intent": str(row[3]), "language": str(row[4]),
        "aspect_ratio": str(row[5]), "output_format": str(row[6]), "creative_brief": str(row[7]),
        "style_direction": str(row[8]), "negative_direction": str(row[9]), "tags": _decode_tags(row[10]),
        "project_id": str(row[1]) if row[1] else None, "lifecycle": lifecycle or str(row[11]),
    }


def _artboard_payload_from_snapshot(snapshot: dict[str, Any]) -> ArtboardPayload:
    return ArtboardPayload.model_validate({
        "title": snapshot.get("title", ""), "image_intent": snapshot.get("image_intent", "create"),
        "language": snapshot.get("language", "vi"), "aspect_ratio": snapshot.get("aspect_ratio", "1:1"),
        "output_format": snapshot.get("output_format", "png"), "creative_brief": snapshot.get("creative_brief", ""),
        "style_direction": snapshot.get("style_direction", ""), "negative_direction": snapshot.get("negative_direction", ""),
        "tags": snapshot.get("tags", []), "project_id": snapshot.get("project_id"),
    })


def _direction_snapshot(payload: DirectionPayload, *, state: str = "active") -> dict[str, Any]:
    return {
        "title": payload.title, "operation": payload.operation, "prompt_text": payload.prompt_text,
        "edit_instructions": payload.edit_instructions, "composition_notes": payload.composition_notes,
        "negative_direction": payload.negative_direction, "asset_id": payload.asset_id,
        "reference_asset_id": payload.reference_asset_id, "tags": list(payload.tags), "state": state,
    }


def _direction_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[3]), "operation": str(row[4]), "prompt_text": str(row[5]),
        "edit_instructions": str(row[6]), "composition_notes": str(row[7]),
        "negative_direction": str(row[8]), "asset_id": str(row[9]) if row[9] else None,
        "reference_asset_id": str(row[10]) if row[10] else None, "tags": _decode_tags(row[11]),
        "state": state or str(row[12]),
    }


def _direction_payload_from_snapshot(snapshot: dict[str, Any]) -> DirectionPayload:
    return DirectionPayload.model_validate({
        "title": snapshot.get("title", ""), "operation": snapshot.get("operation", "create"),
        "prompt_text": snapshot.get("prompt_text", ""), "edit_instructions": snapshot.get("edit_instructions", ""),
        "composition_notes": snapshot.get("composition_notes", ""), "negative_direction": snapshot.get("negative_direction", ""),
        "asset_id": snapshot.get("asset_id"), "reference_asset_id": snapshot.get("reference_asset_id"),
        "tags": snapshot.get("tags", []),
    })


def _artboard_public(row: tuple[Any, ...], *, direction_count: int = 0, include_content: bool = False) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "title": str(row[2]),
        "image_intent": str(row[3]),
        "language": str(row[4]),
        "aspect_ratio": str(row[5]),
        "output_format": str(row[6]),
        "creative_brief_excerpt": _excerpt(row[7], 360),
        "style_direction_excerpt": _excerpt(row[8], 260),
        "negative_direction_excerpt": _excerpt(row[9], 220),
        "tags": _decode_tags(row[10]),
        "state": str(row[11]),
        "revision": int(row[12]),
        "created_at": str(row[13]),
        "updated_at": str(row[14]),
        "archived_at": str(row[15]) if row[15] else None,
        "direction_count": int(direction_count),
        **_boundary(),
    }
    if include_content:
        value.update({
            "creative_brief": str(row[7]),
            "style_direction": str(row[8]),
            "negative_direction": str(row[9]),
        })
    return value


def _asset_reference_public(conn: Any, *, asset_id: str | None, account_id: str) -> dict[str, Any] | None:
    if not asset_id:
        return None
    row = _asset_row(conn, asset_id=asset_id, account_id=account_id)
    if not row:
        # The UUID was originally owner-scoped.  Preserve history without
        # exposing a path, name or cross-account metadata after deletion.
        return {"id": str(asset_id), "available": False}
    public = _image_asset_public(row)
    public["available"] = str(row[5]) == "active" and _is_image_asset(row)
    return public


def _direction_public(
    conn: Any,
    row: tuple[Any, ...],
    *,
    account_id: str,
    include_content: bool = False,
    versions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "artboard_id": str(row[1]),
        "ordinal": int(row[2]),
        "title": str(row[3]),
        "operation": str(row[4]),
        "prompt_excerpt": _excerpt(row[5], 360),
        "edit_instructions_excerpt": _excerpt(row[6], 300),
        "composition_notes_excerpt": _excerpt(row[7], 260),
        "negative_direction_excerpt": _excerpt(row[8], 220),
        "asset_id": str(row[9]) if row[9] else None,
        "reference_asset_id": str(row[10]) if row[10] else None,
        "asset": _asset_reference_public(conn, asset_id=str(row[9]) if row[9] else None, account_id=account_id),
        "reference_asset": _asset_reference_public(conn, asset_id=str(row[10]) if row[10] else None, account_id=account_id),
        "tags": _decode_tags(row[11]),
        "state": str(row[12]),
        "revision": int(row[13]),
        "created_at": str(row[14]),
        "updated_at": str(row[15]),
        "archived_at": str(row[16]) if row[16] else None,
        **_boundary(),
    }
    if include_content:
        value.update({
            "prompt_text": str(row[5]),
            "edit_instructions": str(row[6]),
            "composition_notes": str(row[7]),
            "negative_direction": str(row[8]),
        })
    if versions is not None:
        value["versions"] = versions
    return value


def _artboard_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Artboard"),
        "image_intent": str(snapshot.get("image_intent") or "create"),
        "state": str(snapshot.get("lifecycle") or "draft"),
        "creative_brief_excerpt": _excerpt(snapshot.get("creative_brief"), 280),
        "created_at": str(row[2]),
    }


def _direction_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Creative direction"),
        "operation": str(snapshot.get("operation") or "create"),
        "state": str(snapshot.get("state") or "active"),
        "prompt_excerpt": _excerpt(snapshot.get("prompt_text"), 260),
        "created_at": str(row[2]),
    }


def _insert_artboard(conn: Any, *, artboard_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_image_artboards
           (id, account_id, project_id, title, image_intent, language, aspect_ratio, output_format,
            creative_brief, style_direction, negative_direction, tags_json, lifecycle, revision,
            created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            artboard_id, account_id, snapshot.get("project_id"), snapshot["title"], snapshot["image_intent"],
            snapshot["language"], snapshot["aspect_ratio"], snapshot["output_format"], snapshot["creative_brief"],
            snapshot["style_direction"], snapshot["negative_direction"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["lifecycle"], revision,
            now, now, now if snapshot["lifecycle"] == "archived" else None,
        ),
    )


def _write_artboard(
    conn: Any, *, artboard_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None
) -> None:
    conn.execute(
        """UPDATE web_image_artboards
           SET project_id=?, title=?, image_intent=?, language=?, aspect_ratio=?, output_format=?,
               creative_brief=?, style_direction=?, negative_direction=?, tags_json=?, lifecycle=?,
               revision=?, updated_at=?, archived_at=? WHERE id=? AND account_id=?""",
        (
            snapshot.get("project_id"), snapshot["title"], snapshot["image_intent"], snapshot["language"],
            snapshot["aspect_ratio"], snapshot["output_format"], snapshot["creative_brief"],
            snapshot["style_direction"], snapshot["negative_direction"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["lifecycle"],
            revision, now, archived_at, artboard_id, account_id,
        ),
    )


def _insert_artboard_version(conn: Any, *, artboard_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_image_artboard_versions (id, artboard_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), artboard_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _insert_direction(
    conn: Any, *, direction_id: str, artboard_id: str, account_id: str, ordinal: int, snapshot: dict[str, Any], revision: int, now: str
) -> None:
    conn.execute(
        """INSERT INTO web_image_directions
           (id, artboard_id, account_id, ordinal, title, operation, prompt_text, edit_instructions,
            composition_notes, negative_direction, asset_id, reference_asset_id, tags_json, state,
            revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            direction_id, artboard_id, account_id, ordinal, snapshot["title"], snapshot["operation"],
            snapshot["prompt_text"], snapshot["edit_instructions"], snapshot["composition_notes"],
            snapshot["negative_direction"], snapshot.get("asset_id"), snapshot.get("reference_asset_id"),
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"],
            revision, now, now, now if snapshot["state"] == "archived" else None,
        ),
    )


def _write_direction(
    conn: Any, *, direction_id: str, artboard_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str,
    archived_at: str | None, ordinal: int | None = None,
) -> None:
    updates = "title=?, operation=?, prompt_text=?, edit_instructions=?, composition_notes=?, negative_direction=?, asset_id=?, reference_asset_id=?, tags_json=?, state=?, revision=?, updated_at=?, archived_at=?"
    values: list[Any] = [
        snapshot["title"], snapshot["operation"], snapshot["prompt_text"], snapshot["edit_instructions"],
        snapshot["composition_notes"], snapshot["negative_direction"], snapshot.get("asset_id"), snapshot.get("reference_asset_id"),
        json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"], revision, now, archived_at,
    ]
    if ordinal is not None:
        updates = "ordinal=?, " + updates
        values.insert(0, ordinal)
    values.extend([direction_id, artboard_id, account_id])
    conn.execute(
        f"UPDATE web_image_directions SET {updates} WHERE id=? AND artboard_id=? AND account_id=?",
        values,
    )


def _insert_direction_version(conn: Any, *, direction_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_image_direction_versions (id, direction_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), direction_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _can_add_version(conn: Any, *, table: str, entity_column: str, entity_id: str, account_id: str) -> bool:
    row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {entity_column}=? AND account_id=?", (entity_id, account_id)).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _next_active_ordinal(conn: Any, *, artboard_id: str, account_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_image_directions WHERE artboard_id=? AND account_id=? AND state='active'",
        (artboard_id, account_id),
    ).fetchone()
    return int(row[0] or 0) + 1


def _normalise_archived_ordinals(conn: Any, *, artboard_id: str, account_id: str) -> None:
    rows = conn.execute(
        "SELECT id FROM web_image_directions WHERE artboard_id=? AND account_id=? AND state='archived' ORDER BY archived_at ASC, id ASC",
        (artboard_id, account_id),
    ).fetchall()
    for index, row in enumerate(rows, start=1):
        conn.execute("UPDATE web_image_directions SET ordinal=? WHERE id=? AND artboard_id=? AND account_id=?", (-index, str(row[0]), artboard_id, account_id))
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "UPDATE web_image_directions SET ordinal=? WHERE id=? AND artboard_id=? AND account_id=?",
            (ARCHIVED_ORDINAL_BASE + index - 1, str(row[0]), artboard_id, account_id),
        )


def _next_archived_ordinal(conn: Any, *, artboard_id: str, account_id: str) -> int:
    _normalise_archived_ordinals(conn, artboard_id=artboard_id, account_id=account_id)
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_image_directions WHERE artboard_id=? AND account_id=? AND state='archived'",
        (artboard_id, account_id),
    ).fetchone()
    return max(ARCHIVED_ORDINAL_BASE, int(row[0] or 0) + 1)


def _event(conn: Any, *, account_id: str, artboard_id: str, action: str, revision: int, direction_id: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_image_studio_events
           (id, account_id, artboard_id, direction_id, entity_type, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, artboard_id, direction_id, "direction" if direction_id else "artboard", action, revision, utc_now()),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account["id"]),
        canonical_user_id=None,
        action=action,
        request_id=_request_id(request),
        target=target,
        detail=detail[:320],
    )


def _advance_artboard_for_direction(
    conn: Any, *, artboard: tuple[Any, ...], account_id: str, now: str, event: str, direction_id: str | None = None
) -> tuple[Any, ...]:
    artboard_id = str(artboard[0])
    if not _can_add_version(conn, table="web_image_artboard_versions", entity_column="artboard_id", entity_id=artboard_id, account_id=account_id):
        raise HTTPException(status_code=409, detail="Artboard đã đạt giới hạn lịch sử phiên bản")
    snapshot = _artboard_snapshot_from_row(artboard, lifecycle="draft")
    revision = int(artboard[12]) + 1
    _write_artboard(conn, artboard_id=artboard_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
    _insert_artboard_version(conn, artboard_id=artboard_id, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
    _event(conn, account_id=account_id, artboard_id=artboard_id, direction_id=direction_id, action=event, revision=revision)
    changed = _artboard_row(conn, artboard_id=artboard_id, account_id=account_id)
    if not changed:
        raise HTTPException(status_code=500, detail="Không thể đọc lại artboard")
    return changed


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    counts = {str(row[0]): int(row[1]) for row in conn.execute(
        "SELECT lifecycle, COUNT(*) FROM web_image_artboards WHERE account_id=? GROUP BY lifecycle", (account_id,)
    ).fetchall()}
    directions = conn.execute(
        "SELECT COUNT(*) FROM web_image_directions WHERE account_id=? AND state='active'", (account_id,)
    ).fetchone()
    return {
        "artboards": {
            "draft": counts.get("draft", 0), "review": counts.get("review", 0), "approved": counts.get("approved", 0),
            "archived": counts.get("archived", 0), "total": sum(counts.values()), "limit_per_account": MAX_ARTBOARDS_PER_ACCOUNT,
        },
        "directions": {"active": int(directions[0] or 0), "limit_per_artboard": MAX_DIRECTIONS_PER_ARTBOARD},
        **_boundary(),
    }


def _references_listing(conn: Any, *, account_id: str) -> dict[str, Any]:
    projects = conn.execute(
        "SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100",
        (account_id,),
    ).fetchall()
    assets = conn.execute(
        """SELECT id, display_name, original_filename, extension, content_type, state, updated_at
           FROM web_asset_files WHERE account_id=? AND state='active'
             AND lower(extension) IN ('jpg', 'jpeg', 'png', 'webp')
             AND lower(content_type) IN ('image/jpeg', 'image/png', 'image/webp')
           ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in projects],
        "image_assets": [_image_asset_public(row) for row in assets],
        **_boundary(),
    }


def _direction_versions(conn: Any, *, direction_id: str, account_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_image_direction_versions WHERE direction_id=? AND account_id=? ORDER BY revision DESC LIMIT 20",
        (direction_id, account_id),
    ).fetchall()
    return [_direction_version_public(row) for row in rows]


def _artboard_detail(conn: Any, *, artboard_id: str, account_id: str) -> dict[str, Any] | None:
    artboard = _artboard_row(conn, artboard_id=artboard_id, account_id=account_id)
    if not artboard:
        return None
    direction_count = conn.execute(
        "SELECT COUNT(*) FROM web_image_directions WHERE artboard_id=? AND account_id=? AND state='active'",
        (artboard_id, account_id),
    ).fetchone()
    versions = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_image_artboard_versions WHERE artboard_id=? AND account_id=? ORDER BY revision DESC LIMIT ?",
        (artboard_id, account_id, MAX_VERSIONS_PER_ENTITY),
    ).fetchall()
    directions = conn.execute(
        """SELECT id, artboard_id, ordinal, title, operation, prompt_text, edit_instructions,
                  composition_notes, negative_direction, asset_id, reference_asset_id, tags_json,
                  state, revision, created_at, updated_at, archived_at
           FROM web_image_directions WHERE artboard_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, updated_at DESC, id DESC LIMIT ?""",
        (artboard_id, account_id, MAX_DIRECTIONS_PER_ARTBOARD),
    ).fetchall()
    events = conn.execute(
        "SELECT action, entity_type, direction_id, revision, created_at FROM web_image_studio_events WHERE artboard_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
        (artboard_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    refs = _project_reference(conn, account_id=account_id, project_id=str(artboard[1]) if artboard[1] else None, active=False)
    return {
        "artboard": _artboard_public(artboard, direction_count=int(direction_count[0] or 0), include_content=True),
        "versions": [_artboard_version_public(row) for row in versions],
        "directions": [
            _direction_public(conn, row, account_id=account_id, include_content=True, versions=_direction_versions(conn, direction_id=str(row[0]), account_id=account_id))
            for row in directions
        ],
        "events": [
            {"action": str(row[0]), "entity_type": str(row[1]), "direction_id": str(row[2]) if row[2] else None,
             "revision": int(row[3]), "created_at": str(row[4])}
            for row in events
        ],
        "references": refs,
        **_boundary(),
    }


def _estimate(conn: Any, *, artboard: tuple[Any, ...], account_id: str) -> dict[str, Any]:
    if str(artboard[11]) == "archived":
        return _guarded("Artboard đã archive; estimate bị khóa cho đến khi khôi phục về Draft.", "WEB_IMAGE_ARTBOARD_ARCHIVED")
    rows = conn.execute(
        "SELECT id, ordinal, title, operation, asset_id, reference_asset_id FROM web_image_directions WHERE artboard_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC",
        (str(artboard[0]), account_id),
    ).fetchall()
    source_required = sum(1 for row in rows if str(row[3]) != "create")
    source_attached = sum(1 for row in rows if row[4])
    reference_attached = sum(1 for row in rows if row[5])
    operations = {operation: sum(1 for row in rows if str(row[3]) == operation) for operation in sorted(OPERATIONS)}
    return envelope(
        True,
        "Đã tính checklist creative direction cục bộ.",
        data={
            "artboard_id": str(artboard[0]), "direction_count": len(rows), "operations": operations,
            "source_required_count": source_required, "source_attached_count": source_attached,
            "reference_attached_count": reference_attached,
            "items": [
                {"direction_id": str(row[0]), "ordinal": int(row[1]), "title": str(row[2]), "operation": str(row[3]),
                 "has_asset_reference": bool(row[4]), "has_reference_asset": bool(row[5])}
                for row in rows
            ],
            "notice": "Đây là checklist authoring; không tạo ảnh, không phát sinh output hoặc trạng thái thực thi.",
            **_boundary(),
        },
        status_name="read_only",
    )


def _allowed_transition(current: str, target: str) -> bool:
    return target in {
        "draft": {"review", "archived"},
        "review": {"draft", "approved", "archived"},
        "approved": {"draft", "archived"},
        "archived": {"draft"},
    }.get(current, set())


@router.post("/tools/prompt-composer")
async def compose_image_prompt(
    payload: ImagePromptComposerRequest,
    account: dict = Depends(require_csrf),
):
    """Return a deterministic, request-only image prompt draft.

    ``require_csrf`` also proves a signed Web session.  Do not add an audit
    event, database write, idempotency receipt, source-image pathway, asset
    save, provider/model call, image operation, job, wallet/payment mutation
    or publish action here: all customer text and every derived draft remain
    only in this request/response cycle.
    """

    _require_enabled()
    del account  # Auth/CSRF is the only account boundary for this stateless tool.
    guard = _prompt_composer_guard(
        _prompt_composer_marker(payload.custom_goal, payload.subject, payload.style)
    )
    if guard:
        return guard
    composer = _compose_image_prompt(payload)
    return envelope(
        True,
        "Đã tạo bản nháp prompt ảnh cục bộ để bạn biên tập. Không có ảnh, output, job, thanh toán hoặc hành động publish nào được tạo.",
        data={"composer": composer, **_prompt_composer_boundary()},
        status_name="draft",
    )


@router.post("/tools/prompt-composer/save")
async def save_image_prompt_composer_to_memory(
    payload: ImagePromptComposerMemorySaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Save a server-recomputed composer draft as a private Web memory note.

    This is deliberately separate from ``/tools/prompt-composer`` so the
    preview remains stateless.  The browser sends only the bounded original
    inputs, destination and idempotency key; it cannot submit a result object,
    free-form note body, title, account, Bot pending state, asset or provider
    reference.  The server recreates the full deterministic composer result
    in the same transaction that creates the owner-scoped Web note.
    """

    _require_enabled()
    _require_memory_handoff_enabled()
    marker = _prompt_composer_marker(payload.custom_goal, payload.subject, payload.style)
    if marker:
        return envelope(
            False,
            "Mô tả cần được viết lại theo hướng nguyên bản trước khi lưu vào Memory Center.",
            data={
                "destination": "memory_note",
                **_image_prompt_composer_memory_boundaries(
                    draft_recomputed_on_server=False,
                    web_note_persisted=False,
                ),
            },
            status_name="guarded",
            error_code="WEB_IMAGE_PROMPT_ORIGINALITY_GUARD",
        )

    account_id = str(account["id"])
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint(
        {
            "action": "image_prompt_composer_memory_save",
            "destination": payload.destination,
            "goal_code": payload.goal_code,
            "custom_goal": payload.custom_goal,
            "subject": payload.subject,
            "style": payload.style,
            "ratio": payload.ratio,
            "language": payload.language,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        # Repeat the local deterministic composition while the write
        # transaction is open.  No browser-authored generated result is ever
        # accepted or stored as part of this handoff.
        composer = _compose_image_prompt(payload)
        note_title, note_content, tags = _image_prompt_composer_memory_note(composer)
        active_count = conn.execute(
            "SELECT COUNT(*) FROM web_memory_notes WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        if int(active_count[0] or 0) >= MAX_MEMORY_NOTES_PER_ACCOUNT:
            return envelope(
                False,
                "Memory Center đã đạt giới hạn ghi chú đang hoạt động cho Web account này.",
                data={
                    "destination": "memory_note",
                    **_image_prompt_composer_memory_boundaries(
                        draft_recomputed_on_server=True,
                        web_note_persisted=False,
                    ),
                },
                status_name="guarded",
                error_code="WEB_MEMORY_NOTE_LIMIT",
            )
        note_id = str(uuid.uuid4())
        now = utc_now()
        category = "Image Prompt Composer"
        priority = "normal"
        tags_json = json.dumps(tags, ensure_ascii=False, separators=(",", ":"))
        conn.execute(
            """INSERT INTO web_memory_notes
               (id, account_id, title, content, tags_json, category, priority, state, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?)""",
            (note_id, account_id, note_title, note_content, tags_json, category, priority, now, now),
        )
        conn.execute(
            """INSERT INTO web_memory_note_versions
               (id, note_id, account_id, revision, title, content, tags_json, category, priority, created_at)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), note_id, account_id, note_title, note_content, tags_json, category, priority, now),
        )
        conn.execute(
            """INSERT INTO web_memory_events (id, account_id, note_id, reminder_id, action, created_at)
               VALUES (?, ?, ?, NULL, ?, ?)""",
            (str(uuid.uuid4()), account_id, note_id, "note_created", now),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.image_studio.prompt_composer.save_memory",
            request_id=_request_id(request),
            target=note_id,
            detail="server-recomputed image prompt composer saved as web-owned memory note",
        )
        return envelope(
            True,
            "Đã lưu bản nháp vào Memory Center của Web. Không tạo pending Telegram, ảnh, job, tài sản, thanh toán hay publish.",
            data={
                "note": {
                    "id": note_id,
                    "revision": 1,
                    "state": "active",
                    "category": category,
                    "priority": priority,
                },
                "destination": "memory_note",
                **_image_prompt_composer_memory_boundaries(),
            },
            status_name="completed",
        )

    return _idempotent(
        f"web-image-studio:{account_id}:prompt-composer:save-memory",
        account_id,
        key,
        fingerprint,
        operation,
    )


@router.get("/summary")
async def image_studio_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải tổng quan Image Creative Studio.", data=data, status_name="read_only")


@router.get("/policy")
async def image_studio_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Image Creative Studio chỉ lưu art direction và reference metadata thuộc Web account.",
        data={
            "allowed": ["creative_direction", "asset_reference_metadata", "revision_history", "self_review", "local_checklist"],
            "guarded": ["image_upload", "remote_media_url", "image_execution", "preview", "output_delivery"],
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/references")
async def image_studio_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _references_listing(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải Project và image reference thuộc Web account hiện tại.", data=data, status_name="read_only")


@router.get("/references/projects")
async def image_studio_project_references(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0),
    account: dict = Depends(require_account),
):
    """List only the caller's active Project metadata for the Web picker."""
    _require_enabled()
    bounded_offset = max(0, min(int(offset), MAX_LIST_OFFSET))
    needle = re.sub(r"\s+", " ", str(q or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(needle) or _sensitive_text(needle):
        raise HTTPException(status_code=422, detail="Từ khóa Project reference không hợp lệ")
    clauses = ["account_id=?", "state='active'"]
    values: list[Any] = [str(account["id"])]
    if needle:
        clauses.append("title LIKE ? ESCAPE '\\'")
        values.append("%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, title, updated_at FROM web_projects WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*values, limit + 1, bounded_offset),
        ).fetchall()
    page_rows = rows[:limit]
    has_more = len(rows) > limit
    return envelope(
        True,
        "Đã tải Project reference thuộc Web account hiện tại.",
        data={
            "items": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in page_rows],
            "has_more": has_more,
            "next_offset": bounded_offset + limit if has_more else None,
            "filters": {"q": needle},
            "pagination": {"limit": limit, "offset": bounded_offset, "returned": len(page_rows)},
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/references/image-assets")
async def image_studio_image_asset_references(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0),
    account: dict = Depends(require_account),
):
    """List owner-scoped image metadata without exposing a filename/path/blob."""
    _require_enabled()
    bounded_offset = max(0, min(int(offset), MAX_LIST_OFFSET))
    needle = re.sub(r"\s+", " ", str(q or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(needle) or _sensitive_text(needle):
        raise HTTPException(status_code=422, detail="Từ khóa image reference không hợp lệ")
    clauses = [
        "account_id=?", "state='active'",
        "lower(extension) IN ('jpg', 'jpeg', 'png', 'webp')",
        "lower(content_type) IN ('image/jpeg', 'image/png', 'image/webp')",
    ]
    values: list[Any] = [str(account["id"])]
    if needle:
        clauses.append("(display_name LIKE ? ESCAPE '\\' OR original_filename LIKE ? ESCAPE '\\')")
        wildcard = "%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        values.extend([wildcard, wildcard])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, display_name, original_filename, extension, content_type, state, updated_at
                FROM web_asset_files WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*values, limit + 1, bounded_offset),
        ).fetchall()
    page_rows = rows[:limit]
    has_more = len(rows) > limit
    return envelope(
        True,
        "Đã tải image Asset Vault reference thuộc Web account hiện tại.",
        data={
            "items": [_image_asset_public(row) for row in page_rows],
            "has_more": has_more,
            "next_offset": bounded_offset + limit if has_more else None,
            "filters": {"q": needle},
            "pagination": {"limit": limit, "offset": bounded_offset, "returned": len(page_rows)},
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/artboards")
async def image_artboards(
    state: str = Query(default="active", max_length=20),
    q: str = Query(default="", max_length=180),
    limit: int = Query(default=30, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0),
    account: dict = Depends(require_account),
):
    _require_enabled()
    bounded_offset = max(0, min(int(offset), MAX_LIST_OFFSET))
    normalized_state = str(state or "active").strip().lower()
    if normalized_state not in {"active", *ARTBOARD_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái artboard không hợp lệ")
    needle = re.sub(r"\s+", " ", str(q or "")).strip()
    # Search is owner-scoped and never fetched remotely, but apply the same
    # request-safety boundary as durable authoring fields so URL/secret/markup
    # probes are not accepted as a special read-only escape hatch.
    if UNSAFE_CONTROL_PATTERN.search(needle) or _sensitive_text(needle):
        raise HTTPException(status_code=422, detail="Từ khóa tìm kiếm không hợp lệ")
    where = ["a.account_id=?"]
    values: list[Any] = [str(account["id"])]
    if normalized_state == "active":
        where.append("a.lifecycle<>'archived'")
    else:
        where.append("a.lifecycle=?")
        values.append(normalized_state)
    if needle:
        where.append("(a.title LIKE ? ESCAPE '\\' OR a.creative_brief LIKE ? ESCAPE '\\' OR a.style_direction LIKE ? ESCAPE '\\')")
        wildcard = "%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        values.extend([wildcard, wildcard, wildcard])
    values.extend([limit + 1, bounded_offset])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT a.id, a.project_id, a.title, a.image_intent, a.language, a.aspect_ratio, a.output_format,
                       a.creative_brief, a.style_direction, a.negative_direction, a.tags_json, a.lifecycle,
                       a.revision, a.created_at, a.updated_at, a.archived_at,
                       (SELECT COUNT(*) FROM web_image_directions d WHERE d.artboard_id=a.id AND d.account_id=a.account_id AND d.state='active')
                FROM web_image_artboards a WHERE {' AND '.join(where)} ORDER BY a.updated_at DESC, a.id DESC LIMIT ? OFFSET ?""",
            values,
        ).fetchall()
        page_rows = rows[:limit]
        items = [_artboard_public(row[:16], direction_count=int(row[16] or 0)) for row in page_rows]
    has_more = len(rows) > limit
    return envelope(
        True,
        "Đã tải artboards.",
        data={
            "items": items,
            "has_more": has_more,
            "next_offset": bounded_offset + limit if has_more else None,
            "filters": {"state": normalized_state, "q": needle},
            "pagination": {"limit": limit, "offset": bounded_offset, "returned": len(items)},
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/artboards/{artboard_id}")
async def image_artboard_detail(artboard_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(artboard_id, label="Artboard ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _artboard_detail(conn, artboard_id=resolved, account_id=str(account["id"]))
    if not data:
        return _artboard_not_found()
    return envelope(True, "Đã tải artboard.", data=data, status_name=str(data["artboard"]["state"]))


@router.post("/artboards")
async def image_artboard_create(
    payload: ArtboardCreateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    account_id = str(account["id"])
    snapshot = _artboard_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_artboard", "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_image_artboards WHERE account_id=? AND lifecycle<>'archived'", (account_id,)
        ).fetchone()
        if int(count[0] or 0) >= MAX_ARTBOARDS_PER_ACCOUNT:
            return _guarded("Đã đạt giới hạn artboards đang hoạt động.", "WEB_IMAGE_ARTBOARD_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"))
        now = utc_now()
        artboard_id = str(uuid.uuid4())
        _insert_artboard(conn, artboard_id=artboard_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_artboard_version(conn, artboard_id=artboard_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, artboard_id=artboard_id, action="artboard_created", revision=1)
        row = _artboard_row(conn, artboard_id=artboard_id, account_id=account_id)
        if not row:
            raise HTTPException(status_code=500, detail="Không thể đọc lại artboard")
        _audit(conn, request=request, account=account, action="image_artboard_created", target=artboard_id, detail="Created image artboard")
        return envelope(True, "Đã tạo artboard ở trạng thái Draft.", data={"artboard": _artboard_public(row), **_boundary()}, status_name="draft")

    return _idempotent(f"web-image-studio:{account_id}:create_artboard", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/artboards/{artboard_id}")
async def image_artboard_update(
    artboard_id: str,
    payload: ArtboardUpdateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(artboard_id, label="Artboard ID")
    account_id = str(account["id"])
    snapshot = _artboard_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_artboard", "artboard_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        row = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not row:
            return _artboard_not_found()
        blocked = _artboard_writable(row)
        if blocked:
            return blocked
        if int(row[12]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_image_artboard_versions", entity_column="artboard_id", entity_id=resolved, account_id=account_id):
            return _guarded("Artboard đã đạt giới hạn lịch sử phiên bản.", "WEB_IMAGE_VERSION_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"))
        snapshot["lifecycle"] = str(row[11])
        now = utc_now()
        revision = int(row[12]) + 1
        _write_artboard(conn, artboard_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_artboard_version(conn, artboard_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, artboard_id=resolved, action="artboard_updated", revision=revision)
        changed = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại artboard")
        _audit(conn, request=request, account=account, action="image_artboard_updated", target=resolved, detail="Updated image artboard")
        return envelope(True, "Đã lưu revision artboard mới.", data={"artboard": _artboard_public(changed), **_boundary()}, status_name=str(changed[11]))

    return _idempotent(f"web-image-studio:{account_id}:update_artboard:{resolved}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/artboards/{artboard_id}/lifecycle")
async def image_artboard_lifecycle(
    artboard_id: str,
    payload: LifecycleRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(artboard_id, label="Artboard ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "artboard_lifecycle", "artboard_id": resolved, "expected_revision": payload.expected_revision, "state": payload.state})

    def operation(conn: Any) -> dict[str, Any]:
        row = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not row:
            return _artboard_not_found()
        if int(row[12]) != payload.expected_revision:
            return _revision_conflict()
        current = str(row[11])
        if not _allowed_transition(current, payload.state):
            return _guarded("Chuyển trạng thái artboard không hợp lệ.", "WEB_IMAGE_LIFECYCLE_INVALID")
        if not _can_add_version(conn, table="web_image_artboard_versions", entity_column="artboard_id", entity_id=resolved, account_id=account_id):
            return _guarded("Artboard đã đạt giới hạn lịch sử phiên bản.", "WEB_IMAGE_VERSION_LIMIT")
        snapshot = _artboard_snapshot_from_row(row, lifecycle=payload.state)
        now = utc_now()
        revision = int(row[12]) + 1
        _write_artboard(
            conn, artboard_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now,
            archived_at=now if payload.state == "archived" else None,
        )
        _insert_artboard_version(conn, artboard_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, artboard_id=resolved, action=f"artboard_{payload.state}", revision=revision)
        changed = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại artboard")
        _audit(conn, request=request, account=account, action="image_artboard_lifecycle", target=resolved, detail=f"Set artboard lifecycle {payload.state}")
        return envelope(True, "Đã cập nhật trạng thái self-review artboard.", data={"artboard": _artboard_public(changed), **_boundary()}, status_name=str(changed[11]))

    return _idempotent(f"web-image-studio:{account_id}:artboard:{resolved}:lifecycle:{payload.state}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/artboards/{artboard_id}/restore-version")
async def image_artboard_restore_version(
    artboard_id: str,
    payload: RestoreVersionRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(artboard_id, label="Artboard ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "artboard_restore_version", "artboard_id": resolved, "expected_revision": payload.expected_revision, "target_revision": payload.target_revision})

    def operation(conn: Any) -> dict[str, Any]:
        row = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not row:
            return _artboard_not_found()
        blocked = _artboard_writable(row)
        if blocked:
            return blocked
        if int(row[12]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_image_artboard_versions", entity_column="artboard_id", entity_id=resolved, account_id=account_id):
            return _guarded("Artboard đã đạt giới hạn lịch sử phiên bản.", "WEB_IMAGE_VERSION_LIMIT")
        version = conn.execute(
            "SELECT snapshot_json FROM web_image_artboard_versions WHERE artboard_id=? AND account_id=? AND revision=?",
            (resolved, account_id, payload.target_revision),
        ).fetchone()
        if not version:
            return _guarded("Không tìm thấy revision artboard cần khôi phục.", "WEB_IMAGE_VERSION_NOT_FOUND")
        try:
            decoded = json.loads(str(version[0]))
            restored_payload = _artboard_payload_from_snapshot(decoded if isinstance(decoded, dict) else {})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Revision artboard không hợp lệ") from exc
        snapshot = _artboard_snapshot(restored_payload, lifecycle="draft")
        _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"))
        now = utc_now()
        revision = int(row[12]) + 1
        _write_artboard(conn, artboard_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_artboard_version(conn, artboard_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, artboard_id=resolved, action="artboard_version_restored", revision=revision)
        changed = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại artboard")
        _audit(conn, request=request, account=account, action="image_artboard_version_restored", target=resolved, detail="Restored image artboard revision")
        return envelope(True, "Đã khôi phục revision artboard vào Draft.", data={"artboard": _artboard_public(changed), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-image-studio:{account_id}:artboard:{resolved}:restore-version:{payload.target_revision}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/artboards/{artboard_id}/directions")
async def image_direction_create(
    artboard_id: str,
    payload: DirectionCreateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(artboard_id, label="Artboard ID")
    account_id = str(account["id"])
    snapshot = _direction_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_direction", "artboard_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        artboard = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not artboard:
            return _artboard_not_found()
        blocked = _artboard_writable(artboard)
        if blocked:
            return blocked
        # Creation has no child revision yet, so it CASes the parent.
        if int(artboard[12]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute(
            "SELECT COUNT(*) FROM web_image_directions WHERE artboard_id=? AND account_id=? AND state='active'", (resolved, account_id)
        ).fetchone()
        if int(count[0] or 0) >= MAX_DIRECTIONS_PER_ARTBOARD:
            return _guarded("Đã đạt giới hạn creative directions đang hoạt động.", "WEB_IMAGE_DIRECTION_LIMIT")
        _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        direction_id = str(uuid.uuid4())
        _insert_direction(
            conn, direction_id=direction_id, artboard_id=resolved, account_id=account_id,
            ordinal=_next_active_ordinal(conn, artboard_id=resolved, account_id=account_id), snapshot=snapshot, revision=1, now=now,
        )
        _insert_direction_version(conn, direction_id=direction_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        changed_artboard = _advance_artboard_for_direction(
            conn, artboard=artboard, account_id=account_id, now=now, event="direction_created", direction_id=direction_id,
        )
        direction = _direction_row(conn, artboard_id=resolved, direction_id=direction_id, account_id=account_id)
        if not direction:
            raise HTTPException(status_code=500, detail="Không thể đọc lại creative direction")
        _audit(conn, request=request, account=account, action="image_direction_created", target=direction_id, detail="Created image creative direction")
        return envelope(
            True, "Đã tạo creative direction.",
            data={"artboard": _artboard_public(changed_artboard), "direction": _direction_public(conn, direction, account_id=account_id), **_boundary()},
            status_name="draft",
        )

    return _idempotent(f"web-image-studio:{account_id}:artboard:{resolved}:direction:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/artboards/{artboard_id}/directions/{direction_id}")
async def image_direction_update(
    artboard_id: str,
    direction_id: str,
    payload: DirectionUpdateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved_artboard = _uuid(artboard_id, label="Artboard ID")
    resolved_direction = _uuid(direction_id, label="Direction ID")
    account_id = str(account["id"])
    snapshot = _direction_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_direction", "artboard_id": resolved_artboard, "direction_id": resolved_direction, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        artboard = _artboard_row(conn, artboard_id=resolved_artboard, account_id=account_id)
        if not artboard:
            return _artboard_not_found()
        blocked = _artboard_writable(artboard)
        if blocked:
            return blocked
        direction = _direction_row(conn, artboard_id=resolved_artboard, direction_id=resolved_direction, account_id=account_id)
        if not direction:
            return _direction_not_found()
        # Child mutations CAS their own immutable direction revision.  The
        # parent revision is advanced under this same SQLite transaction.
        if int(direction[13]) != payload.expected_revision:
            return _revision_conflict()
        if str(direction[12]) != "active":
            return _guarded("Creative direction đã archive; hãy khôi phục trước khi chỉnh sửa.", "WEB_IMAGE_DIRECTION_ARCHIVED")
        if not _can_add_version(conn, table="web_image_direction_versions", entity_column="direction_id", entity_id=resolved_direction, account_id=account_id):
            return _guarded("Creative direction đã đạt giới hạn lịch sử phiên bản.", "WEB_IMAGE_VERSION_LIMIT")
        _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(direction[13]) + 1
        _write_direction(
            conn, direction_id=resolved_direction, artboard_id=resolved_artboard, account_id=account_id,
            snapshot=snapshot, revision=revision, now=now, archived_at=None,
        )
        _insert_direction_version(conn, direction_id=resolved_direction, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_artboard = _advance_artboard_for_direction(
            conn, artboard=artboard, account_id=account_id, now=now, event="direction_updated", direction_id=resolved_direction,
        )
        changed = _direction_row(conn, artboard_id=resolved_artboard, direction_id=resolved_direction, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại creative direction")
        _audit(conn, request=request, account=account, action="image_direction_updated", target=resolved_direction, detail="Updated image creative direction")
        return envelope(
            True, "Đã lưu revision creative direction mới.",
            data={"artboard": _artboard_public(changed_artboard), "direction": _direction_public(conn, changed, account_id=account_id), **_boundary()},
            status_name="draft",
        )

    return _idempotent(f"web-image-studio:{account_id}:artboard:{resolved_artboard}:direction:{resolved_direction}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _direction_state_mutation(
    artboard_id: str,
    direction_id: str,
    payload: RevisionRequest,
    request: Request,
    account: dict,
    *,
    action: str,
) -> dict[str, Any]:
    _require_enabled()
    resolved_artboard = _uuid(artboard_id, label="Artboard ID")
    resolved_direction = _uuid(direction_id, label="Direction ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": f"direction_{action}", "artboard_id": resolved_artboard, "direction_id": resolved_direction, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        artboard = _artboard_row(conn, artboard_id=resolved_artboard, account_id=account_id)
        if not artboard:
            return _artboard_not_found()
        blocked = _artboard_writable(artboard)
        if blocked:
            return blocked
        direction = _direction_row(conn, artboard_id=resolved_artboard, direction_id=resolved_direction, account_id=account_id)
        if not direction:
            return _direction_not_found()
        if int(direction[13]) != payload.expected_revision:
            return _revision_conflict()
        target_state = "archived" if action == "archive" else "active"
        if str(direction[12]) == target_state:
            return _guarded("Creative direction đã ở trạng thái yêu cầu.", "WEB_IMAGE_DIRECTION_STATE_UNCHANGED")
        if not _can_add_version(conn, table="web_image_direction_versions", entity_column="direction_id", entity_id=resolved_direction, account_id=account_id):
            return _guarded("Creative direction đã đạt giới hạn lịch sử phiên bản.", "WEB_IMAGE_VERSION_LIMIT")
        snapshot = _direction_snapshot_from_row(direction, state=target_state)
        if target_state == "active":
            _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
            ordinal = _next_active_ordinal(conn, artboard_id=resolved_artboard, account_id=account_id)
        else:
            ordinal = _next_archived_ordinal(conn, artboard_id=resolved_artboard, account_id=account_id)
        now = utc_now()
        revision = int(direction[13]) + 1
        _write_direction(
            conn, direction_id=resolved_direction, artboard_id=resolved_artboard, account_id=account_id,
            snapshot=snapshot, revision=revision, now=now, archived_at=now if target_state == "archived" else None, ordinal=ordinal,
        )
        _insert_direction_version(conn, direction_id=resolved_direction, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_artboard = _advance_artboard_for_direction(
            conn, artboard=artboard, account_id=account_id, now=now, event=f"direction_{action}d", direction_id=resolved_direction,
        )
        changed = _direction_row(conn, artboard_id=resolved_artboard, direction_id=resolved_direction, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại creative direction")
        _audit(conn, request=request, account=account, action=f"image_direction_{action}d", target=resolved_direction, detail=f"{action.title()}d image creative direction")
        return envelope(
            True, "Đã cập nhật trạng thái creative direction.",
            data={"artboard": _artboard_public(changed_artboard), "direction": _direction_public(conn, changed, account_id=account_id), **_boundary()},
            status_name="draft",
        )

    return _idempotent(f"web-image-studio:{account_id}:artboard:{resolved_artboard}:direction:{resolved_direction}:{action}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/artboards/{artboard_id}/directions/{direction_id}/archive")
async def image_direction_archive(
    artboard_id: str, direction_id: str, payload: RevisionRequest, request: Request,
    account: dict = Depends(require_account), _csrf: None = Depends(require_csrf),
):
    return _direction_state_mutation(artboard_id, direction_id, payload, request, account, action="archive")


@router.post("/artboards/{artboard_id}/directions/{direction_id}/restore")
async def image_direction_restore(
    artboard_id: str, direction_id: str, payload: RevisionRequest, request: Request,
    account: dict = Depends(require_account), _csrf: None = Depends(require_csrf),
):
    return _direction_state_mutation(artboard_id, direction_id, payload, request, account, action="restore")


@router.post("/artboards/{artboard_id}/directions/{direction_id}/restore-version")
async def image_direction_restore_version(
    artboard_id: str,
    direction_id: str,
    payload: RestoreVersionRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved_artboard = _uuid(artboard_id, label="Artboard ID")
    resolved_direction = _uuid(direction_id, label="Direction ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "action": "restore_direction_version", "artboard_id": resolved_artboard, "direction_id": resolved_direction,
        "expected_revision": payload.expected_revision, "target_revision": payload.target_revision,
    })

    def operation(conn: Any) -> dict[str, Any]:
        artboard = _artboard_row(conn, artboard_id=resolved_artboard, account_id=account_id)
        if not artboard:
            return _artboard_not_found()
        blocked = _artboard_writable(artboard)
        if blocked:
            return blocked
        direction = _direction_row(conn, artboard_id=resolved_artboard, direction_id=resolved_direction, account_id=account_id)
        if not direction:
            return _direction_not_found()
        if int(direction[13]) != payload.expected_revision:
            return _revision_conflict()
        if str(direction[12]) != "active":
            return _guarded("Creative direction đã archive; hãy khôi phục trước khi restore revision.", "WEB_IMAGE_DIRECTION_ARCHIVED")
        if not _can_add_version(conn, table="web_image_direction_versions", entity_column="direction_id", entity_id=resolved_direction, account_id=account_id):
            return _guarded("Creative direction đã đạt giới hạn lịch sử phiên bản.", "WEB_IMAGE_VERSION_LIMIT")
        version = conn.execute(
            "SELECT snapshot_json FROM web_image_direction_versions WHERE direction_id=? AND account_id=? AND revision=?",
            (resolved_direction, account_id, payload.target_revision),
        ).fetchone()
        if not version:
            return _guarded("Không tìm thấy revision creative direction cần khôi phục.", "WEB_IMAGE_VERSION_NOT_FOUND")
        try:
            decoded = json.loads(str(version[0]))
            restored_payload = _direction_payload_from_snapshot(decoded if isinstance(decoded, dict) else {})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Revision creative direction không hợp lệ") from exc
        snapshot = _direction_snapshot(restored_payload, state="active")
        _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(direction[13]) + 1
        _write_direction(
            conn, direction_id=resolved_direction, artboard_id=resolved_artboard, account_id=account_id,
            snapshot=snapshot, revision=revision, now=now, archived_at=None,
        )
        _insert_direction_version(conn, direction_id=resolved_direction, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_artboard = _advance_artboard_for_direction(
            conn, artboard=artboard, account_id=account_id, now=now, event="direction_version_restored", direction_id=resolved_direction,
        )
        changed = _direction_row(conn, artboard_id=resolved_artboard, direction_id=resolved_direction, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại creative direction")
        _audit(conn, request=request, account=account, action="image_direction_version_restored", target=resolved_direction, detail="Restored image direction revision")
        return envelope(
            True, "Đã khôi phục revision creative direction.",
            data={"artboard": _artboard_public(changed_artboard), "direction": _direction_public(conn, changed, account_id=account_id), "history_snapshot_recorded": True, **_boundary()},
            status_name="draft",
        )

    return _idempotent(f"web-image-studio:{account_id}:artboard:{resolved_artboard}:direction:{resolved_direction}:restore-version:{payload.target_revision}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/artboards/{artboard_id}/directions/reorder")
async def image_directions_reorder(
    artboard_id: str,
    payload: ReorderRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(artboard_id, label="Artboard ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "reorder_directions", "artboard_id": resolved, "expected_revision": payload.expected_revision, "direction_ids": payload.direction_ids})

    def operation(conn: Any) -> dict[str, Any]:
        artboard = _artboard_row(conn, artboard_id=resolved, account_id=account_id)
        if not artboard:
            return _artboard_not_found()
        blocked = _artboard_writable(artboard)
        if blocked:
            return blocked
        if int(artboard[12]) != payload.expected_revision:
            return _revision_conflict()
        active = conn.execute(
            "SELECT id FROM web_image_directions WHERE artboard_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC",
            (resolved, account_id),
        ).fetchall()
        active_ids = [str(row[0]) for row in active]
        if set(payload.direction_ids) != set(active_ids) or len(payload.direction_ids) != len(active_ids):
            return _guarded("Thứ tự phải chứa chính xác mọi creative direction đang hoạt động.", "WEB_IMAGE_REORDER_INVALID")
        _normalise_archived_ordinals(conn, artboard_id=resolved, account_id=account_id)
        # Move active rows outside their normal range before assigning final
        # ordinals, so a unique index cannot collide while two rows swap.
        for index, direction_key in enumerate(payload.direction_ids, start=1):
            conn.execute(
                "UPDATE web_image_directions SET ordinal=? WHERE id=? AND artboard_id=? AND account_id=? AND state='active'",
                (-index, direction_key, resolved, account_id),
            )
        for index, direction_key in enumerate(payload.direction_ids, start=1):
            conn.execute(
                "UPDATE web_image_directions SET ordinal=?, updated_at=? WHERE id=? AND artboard_id=? AND account_id=? AND state='active'",
                (index, utc_now(), direction_key, resolved, account_id),
            )
        now = utc_now()
        changed_artboard = _advance_artboard_for_direction(
            conn, artboard=artboard, account_id=account_id, now=now, event="directions_reordered",
        )
        _audit(conn, request=request, account=account, action="image_directions_reordered", target=resolved, detail="Reordered image creative directions")
        return envelope(
            True, "Đã cập nhật thứ tự creative directions.",
            data={"artboard": _artboard_public(changed_artboard), "reordered": len(payload.direction_ids), **_boundary()},
            status_name="draft",
        )

    return _idempotent(f"web-image-studio:{account_id}:artboard:{resolved}:directions:reorder", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/artboards/{artboard_id}/estimate")
async def image_artboard_estimate(artboard_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(artboard_id, label="Artboard ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        artboard = _artboard_row(conn, artboard_id=resolved, account_id=str(account["id"]))
        if not artboard:
            return _artboard_not_found()
        return _estimate(conn, artboard=artboard, account_id=str(account["id"]))


def _events_data(conn: Any, *, account_id: str, limit: int) -> dict[str, Any]:
    rows = conn.execute(
        """SELECT action, entity_type, artboard_id, direction_id, revision, created_at
           FROM web_image_studio_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (account_id, limit),
    ).fetchall()
    return {
        "items": [
            {"action": str(row[0]), "entity_type": str(row[1]), "artboard_id": str(row[2]),
             "direction_id": str(row[3]) if row[3] else None, "revision": int(row[4]), "created_at": str(row[5])}
            for row in rows
        ],
        **_boundary(),
    }


@router.get("/events")
async def image_studio_events(
    limit: int = Query(default=MAX_EVENT_LIMIT, ge=1, le=MAX_EVENT_LIMIT), account: dict = Depends(require_account)
):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _events_data(conn, account_id=str(account["id"]), limit=limit)
    return envelope(True, "Đã tải lịch sử Image Creative Studio.", data=data, status_name="read_only")


@router.get("/history")
async def image_studio_history(
    limit: int = Query(default=MAX_EVENT_LIMIT, ge=1, le=MAX_EVENT_LIMIT), account: dict = Depends(require_account)
):
    """Compatibility-friendly name for the same safe, owner-scoped history."""
    return await image_studio_events(limit=limit, account=account)
