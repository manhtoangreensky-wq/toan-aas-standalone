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
from copyfast_db import ensure_copyfast_schema, image_studio_enabled, read_transaction, transaction, utc_now


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
MAX_EVENT_LIMIT = 50
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
ARCHIVED_ORDINAL_BASE = 1_000_000


def _require_enabled() -> None:
    if not image_studio_enabled():
        raise HTTPException(
            status_code=503,
            detail="Image Creative Studio đang tạm dừng để bảo trì. WEBAPP_IMAGE_STUDIO_ENABLED chưa được bật.",
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
    for name in ("reordered", "history_snapshot_recorded", "direction_count"):
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


@router.get("/artboards")
async def image_artboards(
    state: str = Query(default="active", max_length=20),
    q: str = Query(default="", max_length=180),
    limit: int = Query(default=30, ge=1, le=MAX_LIST_LIMIT),
    account: dict = Depends(require_account),
):
    _require_enabled()
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
    values.append(limit)
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT a.id, a.project_id, a.title, a.image_intent, a.language, a.aspect_ratio, a.output_format,
                       a.creative_brief, a.style_direction, a.negative_direction, a.tags_json, a.lifecycle,
                       a.revision, a.created_at, a.updated_at, a.archived_at,
                       (SELECT COUNT(*) FROM web_image_directions d WHERE d.artboard_id=a.id AND d.account_id=a.account_id AND d.state='active')
                FROM web_image_artboards a WHERE {' AND '.join(where)} ORDER BY a.updated_at DESC, a.id DESC LIMIT ?""",
            values,
        ).fetchall()
        items = [_artboard_public(row[:16], direction_count=int(row[16] or 0)) for row in rows]
    return envelope(True, "Đã tải artboards.", data={"items": items, **_boundary()}, status_name="read_only")


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
