"""Private Web-native Subtitle, Transcript & Language Workspace.

This router owns only signed-account authored caption text and its revisions.
It deliberately has no upload, media path, source URL, ASR, translation, TTS,
dubbing, provider, Bot, job, payment or delivery capability.  SRT/VTT import
and export are bounded text transformations, not file or engine operations.
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
from copyfast_db import ensure_copyfast_schema, read_transaction, subtitle_studio_enabled, transaction, utc_now


router = APIRouter(prefix="/api/v1/subtitle-studio", tags=["Web Subtitle Studio"])

PROJECT_STATES = frozenset({"draft", "review", "approved", "archived"})
# Review is a deliberate freeze, not a soft state.  The owner must use the
# lifecycle endpoint to reopen Draft before any project/cue/import/reorder
# content changes can be made.
WRITABLE_PROJECT_STATES = frozenset({"draft"})
INTENTS = frozenset({"subtitle", "translation", "asr_review", "dubbing_direction"})
CAPTION_FORMATS = frozenset({"srt", "vtt"})
CUE_STATES = frozenset({"active", "archived"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URL_PATTERN = re.compile(r"(?:https?://|www\.|file:|data:|javascript:)", re.IGNORECASE)
UNSAFE_CUE_URI_PATTERN = re.compile(r"(?:file:|data:|javascript:)", re.IGNORECASE)
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
EXTERNAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:(?:provider|render|job|media|asset|file)[ _-]*(?:id|ref(?:erence)?|token)|"
    r"telegram[ _-]*file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+",
    re.IGNORECASE,
)
SRT_TIMING_PATTERN = re.compile(
    r"^(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})(?:\s+[^\r\n]+)?$"
)
VTT_TIMING_PATTERN = re.compile(
    r"^(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}[.]\d{3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}[.]\d{3})(?:\s+[^\r\n]+)?$"
)

MAX_PROJECTS_PER_ACCOUNT = 300
MAX_CUES_PER_PROJECT = 500
MAX_VERSIONS_PER_ENTITY = 100
MAX_EVENT_LIMIT = 50
MAX_LIST_LIMIT = 100
MAX_IMPORT_CHARS = 120_000
MAX_IMPORT_UTF8_BYTES = 96 * 1024
MAX_CUE_TEXT = 5_000
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1024
ARCHIVED_ORDINAL_BASE = 1_000_000
REORDER_TEMPORARY_ORDINAL_BASE = 2_000_000


def _require_enabled() -> None:
    if not subtitle_studio_enabled():
        raise HTTPException(status_code=503, detail="Subtitle Studio đang tạm dừng để bảo trì. WEBAPP_SUBTITLE_STUDIO_ENABLED chưa được bật.")


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _optional_uuid(value: Any, *, label: str) -> str | None:
    raw = str(value or "").strip()
    return _uuid(raw, label=label) if raw else None


def _idempotency_key(value: Any) -> str:
    value = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(value):
        raise ValueError("Idempotency key không hợp lệ")
    return value


def _sensitive_text(value: str) -> bool:
    return bool(SECRET_PATTERN.search(value) or KNOWN_SECRET_PATTERN.search(value) or PAYMENT_PATTERN.search(value) or "-----begin" in value.lower())


def _metadata_text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and (URL_PATTERN.search(text) or EXTERNAL_REFERENCE_PATTERN.search(text) or _sensitive_text(text)):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu provider/media hoặc chứng từ thanh toán")
    return text


def _cue_text(value: Any, *, label: str, allow_empty: bool = False) -> str:
    """Validate display text while retaining spoken/displayed URLs as plain text.

    URLs inside a caption can be what the user literally said or wants shown.
    The client must render this field escaped as text, never as an anchor.  We
    still reject credentials/payment data and markup-like execution vectors.
    """
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > MAX_CUE_TEXT or (not allow_empty and not text):
        raise ValueError(f"{label} cần từ 1 đến {MAX_CUE_TEXT:,} ký tự hợp lệ".replace(",", "."))
    if "<script" in text.lower() or UNSAFE_CUE_URI_PATTERN.search(text) or _sensitive_text(text):
        raise ValueError(f"{label} không nhận script, secret, mã xác thực hoặc chứng từ thanh toán")
    return text


def _cue_note(value: Any) -> str:
    """Directions are metadata, not transcript text, so never accept links/handles."""
    return _metadata_text(value, label="Ghi chú phát âm/hướng dẫn", minimum=1, maximum=2_000, allow_empty=True)


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Tags phải là danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        tag = _metadata_text(item, label="Tag", minimum=1, maximum=48)
        marker = tag.casefold()
        if marker not in seen:
            result.append(tag)
            seen.add(marker)
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


class ProjectPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    source_language: str = "vi"
    target_language: str = ""
    caption_format: str = "srt"
    context: str = ""
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    intent: str = "subtitle"

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _metadata_text(value, label="Tên subtitle project", minimum=2, maximum=180)

    @field_validator("source_language")
    @classmethod
    def _source_language(cls, value: str) -> str:
        return _metadata_text(value, label="Ngôn ngữ nguồn", minimum=1, maximum=64)

    @field_validator("target_language")
    @classmethod
    def _target_language(cls, value: str) -> str:
        return _metadata_text(value, label="Ngôn ngữ đích", minimum=1, maximum=64, allow_empty=True)

    @field_validator("caption_format")
    @classmethod
    def _caption_format(cls, value: str) -> str:
        normalized = _metadata_text(value, label="Định dạng subtitle", minimum=1, maximum=12).lower()
        if normalized not in CAPTION_FORMATS:
            raise ValueError("Chỉ hỗ trợ SRT hoặc VTT")
        return normalized

    @field_validator("context")
    @classmethod
    def _context(cls, value: str) -> str:
        return _metadata_text(value, label="Bối cảnh", minimum=1, maximum=8_000, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Project ID")

    @field_validator("intent")
    @classmethod
    def _intent(cls, value: str) -> str:
        normalized = _metadata_text(value, label="Mục đích workspace", minimum=1, maximum=32).lower()
        if normalized not in INTENTS:
            raise ValueError("Mục đích subtitle workspace không hợp lệ")
        return normalized


class ProjectCreateRequest(ProjectPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ProjectUpdateRequest(ProjectPayload):
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
        normalized = _metadata_text(value, label="Trạng thái", minimum=1, maximum=20).lower()
        if normalized not in PROJECT_STATES:
            raise ValueError("Trạng thái subtitle project không hợp lệ")
        return normalized


class RestoreVersionRequest(RevisionRequest):
    target_revision: int = Field(ge=1, le=MAX_VERSIONS_PER_ENTITY)


class CuePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_ms: int = Field(ge=0, le=86_399_999)
    end_ms: int = Field(ge=1, le=86_400_000)
    speaker: str = ""
    source_text: str
    translated_text: str = ""
    notes: str = ""

    @field_validator("speaker")
    @classmethod
    def _speaker(cls, value: str) -> str:
        return _metadata_text(value, label="Người nói", minimum=1, maximum=120, allow_empty=True)

    @field_validator("source_text")
    @classmethod
    def _source(cls, value: str) -> str:
        return _cue_text(value, label="Nội dung cue")

    @field_validator("translated_text")
    @classmethod
    def _translation(cls, value: str) -> str:
        return _cue_text(value, label="Bản dịch nháp", allow_empty=True)

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str) -> str:
        return _cue_note(value)

    def model_post_init(self, __context: Any) -> None:
        if self.end_ms <= self.start_ms:
            raise ValueError("Thời điểm kết thúc cue phải lớn hơn thời điểm bắt đầu")


class CueCreateRequest(CuePayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class CueUpdateRequest(CuePayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ReorderRequest(RevisionRequest):
    cue_ids: list[str] = Field(min_length=0, max_length=MAX_CUES_PER_PROJECT)

    @field_validator("cue_ids")
    @classmethod
    def _cue_ids(cls, value: list[str]) -> list[str]:
        return [_uuid(item, label="Cue ID") for item in value]


class ImportRequest(RevisionRequest):
    format: str
    content: str = Field(min_length=1, max_length=MAX_IMPORT_CHARS)

    @field_validator("format")
    @classmethod
    def _format(cls, value: str) -> str:
        normalized = _metadata_text(value, label="Định dạng import", minimum=1, maximum=12).lower()
        if normalized not in CAPTION_FORMATS:
            raise ValueError("Chỉ nhận nội dung SRT hoặc VTT")
        return normalized

    @field_validator("content")
    @classmethod
    def _content(cls, value: str) -> str:
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").strip()
        if UNSAFE_CONTROL_PATTERN.search(text) or not text or len(text) > MAX_IMPORT_CHARS or len(text.encode("utf-8")) > MAX_IMPORT_UTF8_BYTES:
            raise ValueError("Nội dung import không hợp lệ hoặc vượt giới hạn")
        return text


def _boundary(**extra: Any) -> dict[str, Any]:
    return {
        "execution": "authoring_only",
        "provider_called": False,
        "asr_called": False,
        "tts_called": False,
        "dubbing_called": False,
        "translation_called": False,
        "output_created": False,
        "media_uploads": False,
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
    project = source.get("project")
    if isinstance(project, dict) and isinstance(project.get("id"), str):
        data["project"] = {"id": str(project["id"]), "revision": int(project.get("revision") or 0), "state": str(project.get("state") or "")}
    cue = source.get("cue")
    if isinstance(cue, dict) and isinstance(cue.get("id"), str):
        data["cue"] = {"id": str(cue["id"]), "project_id": str(cue.get("project_id") or ""), "revision": int(cue.get("revision") or 0), "state": str(cue.get("state") or "")}
    for field in ("reordered", "imported_count", "replaced_count", "history_snapshot_recorded"):
        if field in source:
            data[field] = source[field]
    return envelope(True, str(response.get("message") or "Đã lưu Subtitle Studio."), data=data, status_name=str(response.get("status") or "draft"))


def _idempotent(scope: str, account_id: str, key: str, request_fingerprint: str, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-subtitle-studio:%", _idempotency_cutoff()))
        existing = conn.execute("SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?", (scope, key)).fetchone()
        if existing:
            if not str(existing[1] or "") or not hmac.compare_digest(str(existing[1]), request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Subtitle Studio không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Subtitle Studio không hợp lệ")
            return receipt
        count = conn.execute("SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?", (f"web-subtitle-studio:{account_id}:%",)).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded("Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_SUBTITLE_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _project_row(conn: Any, *, project_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, linked_project_id, title, source_language, target_language, caption_format, context, tags_json,
                  intent, lifecycle, revision, created_at, updated_at, archived_at
           FROM web_subtitle_projects WHERE id=? AND account_id=?""",
        (project_id, account_id),
    ).fetchone()


def _cue_row(conn: Any, *, project_id: str, cue_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, subtitle_project_id, ordinal, start_ms, end_ms, speaker, source_text, translated_text,
                  notes, state, revision, created_at, updated_at, archived_at
           FROM web_subtitle_cues WHERE id=? AND subtitle_project_id=? AND account_id=?""",
        (cue_id, project_id, account_id),
    ).fetchone()


def _project_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy subtitle project thuộc Web account hiện tại.", "WEB_SUBTITLE_PROJECT_NOT_FOUND")


def _cue_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy cue thuộc subtitle project hiện tại.", "WEB_SUBTITLE_CUE_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return _guarded("Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại trước khi lưu tiếp.", "WEB_SUBTITLE_REVISION_CONFLICT")


def _project_writable(project: tuple[Any, ...]) -> dict[str, Any] | None:
    state = str(project[9])
    if state == "archived":
        return _guarded("Subtitle project đã archive; hãy khôi phục về Draft trước khi tiếp tục.", "WEB_SUBTITLE_PROJECT_ARCHIVED")
    if state == "approved":
        return _guarded("Subtitle project đã self-review. Hãy chuyển về Draft trước khi chỉnh sửa cue.", "WEB_SUBTITLE_PROJECT_APPROVED")
    if state == "review":
        return _guarded("Subtitle project đang self-review. Hãy chuyển về Draft trước khi chỉnh sửa nội dung hoặc cue.", "WEB_SUBTITLE_PROJECT_REVIEW_LOCKED")
    if state not in WRITABLE_PROJECT_STATES:
        return _guarded("Trạng thái subtitle project không cho phép authoring.", "WEB_SUBTITLE_PROJECT_GUARDED")
    return None


def _project_reference(conn: Any, *, account_id: str, linked_project_id: str | None, active: bool = True) -> dict[str, Any]:
    if not linked_project_id:
        return {}
    clause = "AND state='active'" if active else ""
    row = conn.execute(f"SELECT id, title, state FROM web_projects WHERE id=? AND account_id=? {clause}", (linked_project_id, account_id)).fetchone()
    if not row:
        raise HTTPException(status_code=422, detail="Project liên kết không hợp lệ hoặc không còn hoạt động")
    return {"project": {"id": str(row[0]), "title": str(row[1]), "state": str(row[2])}}


def _project_snapshot(payload: ProjectPayload, *, lifecycle: str = "draft") -> dict[str, Any]:
    return {"title": payload.title, "source_language": payload.source_language, "target_language": payload.target_language,
            "caption_format": payload.caption_format, "context": payload.context, "tags": list(payload.tags),
            "project_id": payload.project_id, "intent": payload.intent, "lifecycle": lifecycle}


def _project_snapshot_from_row(row: tuple[Any, ...], *, lifecycle: str | None = None) -> dict[str, Any]:
    return {"title": str(row[2]), "source_language": str(row[3]), "target_language": str(row[4]),
            "caption_format": str(row[5]), "context": str(row[6]), "tags": _decode_tags(row[7]),
            "project_id": str(row[1]) if row[1] else None, "intent": str(row[8]), "lifecycle": lifecycle or str(row[9])}


def _project_payload_from_snapshot(snapshot: dict[str, Any]) -> ProjectPayload:
    return ProjectPayload.model_validate({"title": snapshot.get("title", ""), "source_language": snapshot.get("source_language", "vi"),
        "target_language": snapshot.get("target_language", ""), "caption_format": snapshot.get("caption_format", "srt"),
        "context": snapshot.get("context", ""), "tags": snapshot.get("tags", []), "project_id": snapshot.get("project_id"),
        "intent": snapshot.get("intent", "subtitle")})


def _cue_snapshot(payload: CuePayload, *, state: str = "active") -> dict[str, Any]:
    return {"start_ms": int(payload.start_ms), "end_ms": int(payload.end_ms), "speaker": payload.speaker,
            "source_text": payload.source_text, "translated_text": payload.translated_text, "notes": payload.notes, "state": state}


def _cue_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {"start_ms": int(row[3]), "end_ms": int(row[4]), "speaker": str(row[5]), "source_text": str(row[6]),
            "translated_text": str(row[7]), "notes": str(row[8]), "state": state or str(row[9])}


def _cue_payload_from_snapshot(snapshot: dict[str, Any]) -> CuePayload:
    return CuePayload.model_validate({"start_ms": snapshot.get("start_ms", 0), "end_ms": snapshot.get("end_ms", 1),
        "speaker": snapshot.get("speaker", ""), "source_text": snapshot.get("source_text", ""),
        "translated_text": snapshot.get("translated_text", ""), "notes": snapshot.get("notes", "")})


def _project_public(row: tuple[Any, ...], *, cue_count: int = 0, include_content: bool = False) -> dict[str, Any]:
    value = {"id": str(row[0]), "project_id": str(row[1]) if row[1] else None, "title": str(row[2]),
             "source_language": str(row[3]), "target_language": str(row[4]), "caption_format": str(row[5]),
             "context_excerpt": _excerpt(row[6], 360), "tags": _decode_tags(row[7]), "intent": str(row[8]),
             "state": str(row[9]), "revision": int(row[10]), "created_at": str(row[11]), "updated_at": str(row[12]),
             "archived_at": str(row[13]) if row[13] else None, "cue_count": int(cue_count), **_boundary()}
    if include_content:
        value["context"] = str(row[6])
    return value


def _cue_public(row: tuple[Any, ...], *, include_content: bool = False, versions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    value = {"id": str(row[0]), "project_id": str(row[1]), "ordinal": int(row[2]), "start_ms": int(row[3]),
             "end_ms": int(row[4]), "speaker": str(row[5]), "source_excerpt": _excerpt(row[6], 280),
             "translated_excerpt": _excerpt(row[7], 280), "notes_excerpt": _excerpt(row[8], 220), "state": str(row[9]),
             "revision": int(row[10]), "created_at": str(row[11]), "updated_at": str(row[12]),
             "archived_at": str(row[13]) if row[13] else None, **_boundary()}
    if include_content:
        value.update({"source_text": str(row[6]), "translated_text": str(row[7]), "notes": str(row[8])})
    if versions is not None:
        value["versions"] = versions
    return value


def _project_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {"revision": int(row[0]), "title": str(snapshot.get("title") or "Subtitle project"),
            "caption_format": str(snapshot.get("caption_format") or "srt"), "intent": str(snapshot.get("intent") or "subtitle"),
            "state": str(snapshot.get("lifecycle") or "draft"), "context_excerpt": _excerpt(snapshot.get("context"), 280),
            "created_at": str(row[2])}


def _cue_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {"revision": int(row[0]), "state": str(snapshot.get("state") or "active"),
            "start_ms": int(snapshot.get("start_ms") or 0), "end_ms": int(snapshot.get("end_ms") or 0),
            "source_excerpt": _excerpt(snapshot.get("source_text"), 220), "translated_excerpt": _excerpt(snapshot.get("translated_text"), 220),
            "created_at": str(row[2])}


def _insert_project(conn: Any, *, project_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_subtitle_projects
           (id, account_id, linked_project_id, title, source_language, target_language, caption_format, context,
            tags_json, intent, lifecycle, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, account_id, snapshot.get("project_id"), snapshot["title"], snapshot["source_language"],
         snapshot["target_language"], snapshot["caption_format"], snapshot["context"],
         json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["intent"], snapshot["lifecycle"],
         revision, now, now, now if snapshot["lifecycle"] == "archived" else None),
    )


def _write_project(conn: Any, *, project_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_subtitle_projects
           SET linked_project_id=?, title=?, source_language=?, target_language=?, caption_format=?, context=?,
               tags_json=?, intent=?, lifecycle=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (snapshot.get("project_id"), snapshot["title"], snapshot["source_language"], snapshot["target_language"],
         snapshot["caption_format"], snapshot["context"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
         snapshot["intent"], snapshot["lifecycle"], revision, now, archived_at, project_id, account_id),
    )


def _insert_project_version(conn: Any, *, project_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_subtitle_project_versions (id, subtitle_project_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _insert_cue(conn: Any, *, cue_id: str, project_id: str, account_id: str, ordinal: int, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_subtitle_cues
           (id, subtitle_project_id, account_id, ordinal, start_ms, end_ms, speaker, source_text, translated_text,
            notes, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (cue_id, project_id, account_id, ordinal, snapshot["start_ms"], snapshot["end_ms"], snapshot["speaker"],
         snapshot["source_text"], snapshot["translated_text"], snapshot["notes"], snapshot["state"], revision,
         now, now, now if snapshot["state"] == "archived" else None),
    )


def _write_cue(conn: Any, *, cue_id: str, project_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_subtitle_cues
           SET start_ms=?, end_ms=?, speaker=?, source_text=?, translated_text=?, notes=?, state=?, revision=?,
               updated_at=?, archived_at=? WHERE id=? AND subtitle_project_id=? AND account_id=?""",
        (snapshot["start_ms"], snapshot["end_ms"], snapshot["speaker"], snapshot["source_text"],
         snapshot["translated_text"], snapshot["notes"], snapshot["state"], revision, now, archived_at,
         cue_id, project_id, account_id),
    )


def _insert_cue_version(conn: Any, *, cue_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_subtitle_cue_versions (id, cue_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), cue_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _can_add_version(conn: Any, *, table: str, entity_column: str, entity_id: str, account_id: str) -> bool:
    row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {entity_column}=? AND account_id=?", (entity_id, account_id)).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _next_active_ordinal(conn: Any, *, project_id: str, account_id: str) -> int:
    row = conn.execute("SELECT COALESCE(MAX(ordinal), 0) FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='active'", (project_id, account_id)).fetchone()
    return int(row[0] or 0) + 1


def _normalise_archived_ordinals(conn: Any, *, project_id: str, account_id: str) -> None:
    """Move archives to a disjoint ordinal range before active reorder/restore."""
    rows = conn.execute(
        "SELECT id FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='archived' ORDER BY archived_at ASC, id ASC",
        (project_id, account_id),
    ).fetchall()
    for index, row in enumerate(rows, start=1):
        conn.execute("UPDATE web_subtitle_cues SET ordinal=? WHERE id=? AND subtitle_project_id=? AND account_id=?", (-index, str(row[0]), project_id, account_id))
    for index, row in enumerate(rows, start=1):
        conn.execute("UPDATE web_subtitle_cues SET ordinal=? WHERE id=? AND subtitle_project_id=? AND account_id=?", (ARCHIVED_ORDINAL_BASE + index - 1, str(row[0]), project_id, account_id))


def _event(conn: Any, *, account_id: str, project_id: str, action: str, revision: int, cue_id: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_subtitle_workspace_events
           (id, account_id, subtitle_project_id, cue_id, entity_type, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, project_id, cue_id, "cue" if cue_id else "project", action, revision, utc_now()),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(conn, account_id=str(account["id"]), canonical_user_id=None, action=action,
                  request_id=_request_id(request), target=target, detail=detail[:320])


def _advance_project_for_cue_change(conn: Any, *, project: tuple[Any, ...], account_id: str, now: str, action: str, cue_id: str | None = None) -> tuple[Any, ...]:
    project_id = str(project[0])
    if not _can_add_version(conn, table="web_subtitle_project_versions", entity_column="subtitle_project_id", entity_id=project_id, account_id=account_id):
        raise HTTPException(status_code=409, detail="Subtitle project đã đạt giới hạn lịch sử phiên bản")
    snapshot = _project_snapshot_from_row(project, lifecycle=str(project[9]))
    revision = int(project[10]) + 1
    _write_project(conn, project_id=project_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
    _insert_project_version(conn, project_id=project_id, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
    _event(conn, account_id=account_id, project_id=project_id, cue_id=cue_id, action=action, revision=revision)
    changed = _project_row(conn, project_id=project_id, account_id=account_id)
    if not changed:
        raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle project")
    return changed


def _parse_timestamp(value: str) -> int:
    part = value.strip().replace(",", ".")
    match = re.fullmatch(r"(?:(\d{1,2}):)?(\d{2}):(\d{2})\.(\d{3})", part)
    if not match:
        raise ValueError("Mốc thời gian subtitle không hợp lệ")
    hours = int(match.group(1) or 0)
    minutes, seconds, milliseconds = (int(item) for item in match.groups()[1:])
    if minutes >= 60 or seconds >= 60:
        raise ValueError("Mốc thời gian subtitle không hợp lệ")
    return (((hours * 60 + minutes) * 60 + seconds) * 1000) + milliseconds


def _parse_caption_text(fmt: str, content: str) -> list[dict[str, Any]]:
    """Parse bounded, plain SRT/VTT text without touching filesystem or media."""
    text = content.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").strip()
    if fmt == "vtt":
        lines = text.split("\n")
        if not lines or lines[0].strip() != "WEBVTT":
            raise HTTPException(status_code=422, detail="VTT phải bắt đầu bằng WEBVTT")
        text = "\n".join(lines[1:]).strip()
    blocks = [block.strip() for block in re.split(r"\n[ \t]*\n", text) if block.strip()]
    result: list[dict[str, Any]] = []
    pattern = VTT_TIMING_PATTERN if fmt == "vtt" else SRT_TIMING_PATTERN
    before_first_vtt_cue = True
    for block in blocks:
        lines = [line.rstrip() for line in block.split("\n")]
        if not lines:
            continue
        if fmt == "vtt" and re.match(r"^(?:NOTE|STYLE|REGION)(?:\s|$)", lines[0].strip(), re.IGNORECASE):
            # VTT metadata is deliberately not persisted or interpreted.
            continue
        if fmt == "vtt" and before_first_vtt_cue and not any("-->" in line for line in lines):
            # Header metadata (for example ``Kind: captions`` or
            # ``X-TIMESTAMP-MAP``) is not a cue and is never persisted or
            # interpreted as configuration.
            continue
        timing_index = 0
        if not pattern.fullmatch(lines[0].strip()):
            # SRT counter and VTT cue identifier are metadata, never stored.
            timing_index = 1
        if timing_index >= len(lines):
            raise HTTPException(status_code=422, detail="Mỗi cue phải có dòng thời gian hợp lệ")
        timing = pattern.fullmatch(lines[timing_index].strip())
        if not timing:
            raise HTTPException(status_code=422, detail="Dòng thời gian SRT/VTT không hợp lệ")
        caption_lines = lines[timing_index + 1:]
        caption = "\n".join(caption_lines).strip()
        try:
            cue = CuePayload(start_ms=_parse_timestamp(timing.group("start")), end_ms=_parse_timestamp(timing.group("end")), source_text=caption)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        result.append(_cue_snapshot(cue))
        before_first_vtt_cue = False
        if len(result) > MAX_CUES_PER_PROJECT:
            raise HTTPException(status_code=422, detail=f"Import tối đa {MAX_CUES_PER_PROJECT} cues")
    if not result:
        raise HTTPException(status_code=422, detail="Không tìm thấy cue SRT/VTT hợp lệ")
    return result


def _format_timestamp(milliseconds: int, *, fmt: str) -> str:
    total = max(0, int(milliseconds))
    hours, remainder = divmod(total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milli = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{'.' if fmt == 'vtt' else ','}{milli:03d}"


def _export_caption_text(fmt: str, cues: list[tuple[Any, ...]], *, track: str) -> str:
    items: list[str] = ["WEBVTT", ""] if fmt == "vtt" else []
    for index, row in enumerate(cues, start=1):
        content = str(row[7] if track == "translation" else row[6]).strip()
        if fmt == "srt":
            items.append(str(index))
        items.append(f"{_format_timestamp(int(row[3]), fmt=fmt)} --> {_format_timestamp(int(row[4]), fmt=fmt)}")
        items.append(content)
        items.append("")
    return "\n".join(items).rstrip() + "\n"


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    counts = {str(row[0]): int(row[1]) for row in conn.execute(
        "SELECT lifecycle, COUNT(*) FROM web_subtitle_projects WHERE account_id=? GROUP BY lifecycle", (account_id,)
    ).fetchall()}
    cue_counts = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(CASE WHEN translated_text<>'' THEN 1 ELSE 0 END), 0)
           FROM web_subtitle_cues WHERE account_id=? AND state='active'""", (account_id,)
    ).fetchone()
    return {"projects": {"draft": counts.get("draft", 0), "review": counts.get("review", 0),
             "approved": counts.get("approved", 0), "archived": counts.get("archived", 0),
             "total": sum(counts.values()), "limit_per_account": MAX_PROJECTS_PER_ACCOUNT},
            "cues": {"active": int(cue_counts[0] or 0), "translation_draft": int(cue_counts[1] or 0),
                     "limit_per_project": MAX_CUES_PER_PROJECT}, **_boundary()}


def _references_listing(conn: Any, *, account_id: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100",
        (account_id,),
    ).fetchall()
    return {"projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in rows], **_boundary()}


def _cue_versions(conn: Any, *, cue_id: str, account_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_subtitle_cue_versions WHERE cue_id=? AND account_id=? ORDER BY revision DESC LIMIT 20",
        (cue_id, account_id),
    ).fetchall()
    return [_cue_version_public(row) for row in rows]


def _project_detail(conn: Any, *, project_id: str, account_id: str) -> dict[str, Any] | None:
    project = _project_row(conn, project_id=project_id, account_id=account_id)
    if not project:
        return None
    cue_count = conn.execute(
        "SELECT COUNT(*) FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='active'", (project_id, account_id)
    ).fetchone()
    project_versions = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_subtitle_project_versions WHERE subtitle_project_id=? AND account_id=? ORDER BY revision DESC LIMIT ?",
        (project_id, account_id, MAX_VERSIONS_PER_ENTITY),
    ).fetchall()
    cues = conn.execute(
        """SELECT id, subtitle_project_id, ordinal, start_ms, end_ms, speaker, source_text, translated_text,
                  notes, state, revision, created_at, updated_at, archived_at
           FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, updated_at DESC, id DESC LIMIT ?""",
        (project_id, account_id, MAX_CUES_PER_PROJECT),
    ).fetchall()
    events = conn.execute(
        """SELECT action, entity_type, cue_id, revision, created_at FROM web_subtitle_workspace_events
           WHERE subtitle_project_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (project_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    refs = _project_reference(conn, account_id=account_id, linked_project_id=str(project[1]) if project[1] else None, active=False)
    return {"project": _project_public(project, cue_count=int(cue_count[0] or 0), include_content=True),
            "versions": [_project_version_public(row) for row in project_versions],
            "cues": [_cue_public(row, include_content=True, versions=_cue_versions(conn, cue_id=str(row[0]), account_id=account_id)) for row in cues],
            "events": [{"action": str(row[0]), "entity_type": str(row[1]), "cue_id": str(row[2]) if row[2] else None,
                        "revision": int(row[3]), "created_at": str(row[4])} for row in events],
            "references": refs, **_boundary()}


def _estimate(conn: Any, *, project: tuple[Any, ...], account_id: str) -> dict[str, Any]:
    if str(project[9]) == "archived":
        return _guarded("Subtitle project đã archive; estimate bị khóa cho đến khi khôi phục về Draft.", "WEB_SUBTITLE_PROJECT_ARCHIVED")
    rows = conn.execute(
        """SELECT id, ordinal, start_ms, end_ms, source_text, translated_text FROM web_subtitle_cues
           WHERE subtitle_project_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC""",
        (str(project[0]), account_id),
    ).fetchall()
    duration = sum(max(0, int(row[3]) - int(row[2])) for row in rows)
    complete_translation = sum(1 for row in rows if str(row[5]).strip())
    translation_requested = bool(str(project[4]).strip())
    return envelope(True, "Đã tính bản kiểm tra cue cục bộ.", data={
        "project_id": str(project[0]), "cue_count": len(rows), "duration_ms": duration, "timed_duration_ms": duration, "overlap_count": 0,
        "translation_requested": translation_requested, "translation_draft_cues": complete_translation,
        "translation_pending_cues": len(rows) - complete_translation if translation_requested else 0,
        "items": [{"cue_id": str(row[0]), "ordinal": int(row[1]), "start_ms": int(row[2]), "end_ms": int(row[3]),
                   "has_source_text": bool(str(row[4]).strip()), "has_translated_text": bool(str(row[5]).strip())} for row in rows],
        "notice": "Đây là kiểm tra cue do người dùng soạn; không chạy ASR, dịch, TTS, dubbing, media hoặc delivery.",
        **_boundary()}, status_name="read_only")


def _validate_no_overlap(conn: Any, *, project_id: str, account_id: str, candidates: list[dict[str, Any]], exclude_cue_id: str | None = None, include_existing: bool = True) -> None:
    """Require a deterministic non-overlapping cue timeline in one transaction.

    This keeps manual subtitle review unambiguous and avoids an import or
    concurrent edit creating ambiguous overlapping display windows. Adjacent
    windows are allowed (`end_ms == next.start_ms`).
    """
    rows = conn.execute(
        "SELECT id, start_ms, end_ms FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='active'",
        (project_id, account_id),
    ).fetchall() if include_existing else []
    intervals: list[tuple[int, int, str]] = [
        (int(row[1]), int(row[2]), str(row[0])) for row in rows if str(row[0]) != str(exclude_cue_id or "")
    ]
    intervals.extend((int(item["start_ms"]), int(item["end_ms"]), "new") for item in candidates)
    intervals.sort(key=lambda item: (item[0], item[1], item[2]))
    previous_end = -1
    for start, end, _ in intervals:
        if start < previous_end:
            raise HTTPException(status_code=422, detail="Các cue không được chồng lấp thời gian")
        previous_end = max(previous_end, end)


def _allowed_transition(current: str, target: str) -> bool:
    return target in {
        "draft": {"review", "archived"},
        "review": {"draft", "approved", "archived"},
        "approved": {"draft", "archived"},
        "archived": {"draft"},
    }.get(current, set())


@router.get("/summary")
async def subtitle_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        return envelope(True, "Đã tải tổng quan Subtitle Studio.", data=_summary_data(conn, account_id=str(account["id"])), status_name="read_only")


@router.get("/policy")
async def subtitle_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(True, "Subtitle Studio chỉ quản lý cue text do Web account tự soạn.", data={
        "allowed": ["manual_cues", "bounded_srt_vtt_text_import", "text_export", "self_review", "revision_history"],
        "guarded": ["file_upload", "media_path", "media_url", "asr", "translation", "tts", "dubbing", "provider", "bot", "jobs", "payment", "delivery"],
        **_boundary()}, status_name="read_only")


@router.get("/references")
async def subtitle_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        return envelope(True, "Đã tải Project liên kết có thể chọn.", data=_references_listing(conn, account_id=str(account["id"])), status_name="read_only")


@router.get("/projects")
async def subtitle_projects(
    state: str = Query(default="active", max_length=20), q: str = Query(default="", max_length=180),
    limit: int = Query(default=30, ge=1, le=MAX_LIST_LIMIT), account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    normalized_state = state.strip().lower()
    if normalized_state not in {"active", *PROJECT_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    needle = re.sub(r"\s+", " ", q).strip()
    if UNSAFE_CONTROL_PATTERN.search(needle):
        raise HTTPException(status_code=422, detail="Từ khóa tìm kiếm không hợp lệ")
    where = ["p.account_id=?"]
    values: list[Any] = [account_id]
    if normalized_state == "active":
        where.append("p.lifecycle<>'archived'")
    else:
        where.append("p.lifecycle=?")
        values.append(normalized_state)
    if needle:
        where.append("(p.title LIKE ? ESCAPE '\\' OR p.context LIKE ? ESCAPE '\\')")
        wildcard = "%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        values.extend([wildcard, wildcard])
    values.append(limit)
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT p.id, p.linked_project_id, p.title, p.source_language, p.target_language, p.caption_format,
                       p.context, p.tags_json, p.intent, p.lifecycle, p.revision, p.created_at, p.updated_at, p.archived_at,
                       (SELECT COUNT(*) FROM web_subtitle_cues c WHERE c.subtitle_project_id=p.id AND c.account_id=p.account_id AND c.state='active')
                FROM web_subtitle_projects p WHERE {' AND '.join(where)} ORDER BY p.updated_at DESC, p.id DESC LIMIT ?""", values
        ).fetchall()
        return envelope(True, "Đã tải subtitle projects.", data={"items": [_project_public(row[:14], cue_count=int(row[14] or 0)) for row in rows], **_boundary()}, status_name="read_only")


@router.get("/projects/{project_id}")
async def subtitle_project_detail(project_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _project_detail(conn, project_id=resolved, account_id=str(account["id"]))
        if not data:
            return _project_not_found()
        return envelope(True, "Đã tải subtitle project.", data=data, status_name=str(data["project"]["state"]))


@router.post("/projects")
async def subtitle_project_create(payload: ProjectCreateRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    snapshot = _project_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_project", "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute("SELECT COUNT(*) FROM web_subtitle_projects WHERE account_id=? AND lifecycle<>'archived'", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_PROJECTS_PER_ACCOUNT:
            return _guarded("Đã đạt giới hạn subtitle projects đang hoạt động.", "WEB_SUBTITLE_PROJECT_LIMIT")
        _project_reference(conn, account_id=account_id, linked_project_id=snapshot.get("project_id"))
        now = utc_now()
        project_id = str(uuid.uuid4())
        _insert_project(conn, project_id=project_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_project_version(conn, project_id=project_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, project_id=project_id, action="project_created", revision=1)
        row = _project_row(conn, project_id=project_id, account_id=account_id)
        if not row:
            raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle project")
        _audit(conn, request=request, account=account, action="subtitle_project_created", target=project_id, detail="Created manual subtitle project")
        return envelope(True, "Đã tạo subtitle project ở trạng thái Draft.", data={"project": _project_public(row, include_content=False), **_boundary()}, status_name="draft")

    return _idempotent(f"web-subtitle-studio:{account_id}:create_project", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/projects/{project_id}")
async def subtitle_project_update(project_id: str, payload: ProjectUpdateRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    account_id = str(account["id"])
    snapshot = _project_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_project", "project_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        row = _project_row(conn, project_id=resolved, account_id=account_id)
        if not row:
            return _project_not_found()
        blocked = _project_writable(row)
        if blocked:
            return blocked
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        _project_reference(conn, account_id=account_id, linked_project_id=snapshot.get("project_id"))
        if not _can_add_version(conn, table="web_subtitle_project_versions", entity_column="subtitle_project_id", entity_id=resolved, account_id=account_id):
            return _guarded("Subtitle project đã đạt giới hạn lịch sử phiên bản.", "WEB_SUBTITLE_VERSION_LIMIT")
        snapshot["lifecycle"] = str(row[9])
        now = utc_now()
        revision = int(row[10]) + 1
        _write_project(conn, project_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_project_version(conn, project_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, project_id=resolved, action="project_updated", revision=revision)
        changed = _project_row(conn, project_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle project")
        _audit(conn, request=request, account=account, action="subtitle_project_updated", target=resolved, detail="Updated manual subtitle project")
        return envelope(True, "Đã lưu revision subtitle project mới.", data={"project": _project_public(changed, include_content=False), **_boundary()}, status_name=str(changed[9]))

    return _idempotent(f"web-subtitle-studio:{account_id}:update_project:{resolved}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/projects/{project_id}/lifecycle")
async def subtitle_project_lifecycle(project_id: str, payload: LifecycleRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "project_lifecycle", "project_id": resolved, "expected_revision": payload.expected_revision, "state": payload.state})

    def operation(conn: Any) -> dict[str, Any]:
        row = _project_row(conn, project_id=resolved, account_id=account_id)
        if not row:
            return _project_not_found()
        current = str(row[9])
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        if not _allowed_transition(current, payload.state):
            return _guarded("Chuyển trạng thái subtitle project không hợp lệ.", "WEB_SUBTITLE_TRANSITION_INVALID")
        if not _can_add_version(conn, table="web_subtitle_project_versions", entity_column="subtitle_project_id", entity_id=resolved, account_id=account_id):
            return _guarded("Subtitle project đã đạt giới hạn lịch sử phiên bản.", "WEB_SUBTITLE_VERSION_LIMIT")
        snapshot = _project_snapshot_from_row(row, lifecycle=payload.state)
        now = utc_now()
        revision = int(row[10]) + 1
        _write_project(conn, project_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=now if payload.state == "archived" else None)
        _insert_project_version(conn, project_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, project_id=resolved, action="project_state_changed", revision=revision)
        changed = _project_row(conn, project_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle project")
        _audit(conn, request=request, account=account, action="subtitle_project_lifecycle", target=resolved, detail=f"Changed lifecycle to {payload.state}")
        return envelope(True, "Đã cập nhật self-review lifecycle của subtitle project.", data={"project": _project_public(changed, include_content=False), **_boundary()}, status_name=payload.state)

    return _idempotent(f"web-subtitle-studio:{account_id}:project_lifecycle:{resolved}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/projects/{project_id}/restore-version")
async def subtitle_project_restore_version(project_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "restore_project_version", "project_id": resolved, "expected_revision": payload.expected_revision, "target_revision": payload.target_revision})

    def operation(conn: Any) -> dict[str, Any]:
        row = _project_row(conn, project_id=resolved, account_id=account_id)
        if not row:
            return _project_not_found()
        blocked = _project_writable(row)
        if blocked:
            return blocked
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        version = conn.execute("SELECT snapshot_json FROM web_subtitle_project_versions WHERE subtitle_project_id=? AND account_id=? AND revision=?", (resolved, account_id, payload.target_revision)).fetchone()
        if not version:
            return _guarded("Không tìm thấy revision subtitle project cần khôi phục.", "WEB_SUBTITLE_VERSION_NOT_FOUND")
        if not _can_add_version(conn, table="web_subtitle_project_versions", entity_column="subtitle_project_id", entity_id=resolved, account_id=account_id):
            return _guarded("Subtitle project đã đạt giới hạn lịch sử phiên bản.", "WEB_SUBTITLE_VERSION_LIMIT")
        try:
            source = json.loads(str(version[0]))
            restored = _project_payload_from_snapshot(source if isinstance(source, dict) else {})
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Revision subtitle project không hợp lệ") from exc
        snapshot = _project_snapshot(restored, lifecycle="draft")
        _project_reference(conn, account_id=account_id, linked_project_id=snapshot.get("project_id"))
        now = utc_now()
        revision = int(row[10]) + 1
        _write_project(conn, project_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_project_version(conn, project_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, project_id=resolved, action="project_version_restored", revision=revision)
        changed = _project_row(conn, project_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle project")
        _audit(conn, request=request, account=account, action="subtitle_project_version_restored", target=resolved, detail=f"Restored revision {payload.target_revision}")
        return envelope(True, "Đã khôi phục revision thành Draft mới.", data={"project": _project_public(changed, include_content=False), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-subtitle-studio:{account_id}:restore_project:{resolved}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/projects/{project_id}/cues")
async def subtitle_cue_create(project_id: str, payload: CueCreateRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    account_id = str(account["id"])
    snapshot = _cue_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_cue", "project_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        project = _project_row(conn, project_id=resolved, account_id=account_id)
        if not project:
            return _project_not_found()
        blocked = _project_writable(project)
        if blocked:
            return blocked
        if int(project[10]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute("SELECT COUNT(*) FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='active'", (resolved, account_id)).fetchone()
        if int(count[0] or 0) >= MAX_CUES_PER_PROJECT:
            return _guarded("Đã đạt giới hạn cues đang hoạt động cho subtitle project.", "WEB_SUBTITLE_CUE_LIMIT")
        _validate_no_overlap(conn, project_id=resolved, account_id=account_id, candidates=[snapshot])
        now = utc_now()
        cue_id = str(uuid.uuid4())
        _insert_cue(conn, cue_id=cue_id, project_id=resolved, account_id=account_id, ordinal=_next_active_ordinal(conn, project_id=resolved, account_id=account_id), snapshot=snapshot, revision=1, now=now)
        _insert_cue_version(conn, cue_id=cue_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        changed_project = _advance_project_for_cue_change(conn, project=project, account_id=account_id, now=now, action="cue_created", cue_id=cue_id)
        cue = _cue_row(conn, project_id=resolved, cue_id=cue_id, account_id=account_id)
        if not cue:
            raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle cue")
        _audit(conn, request=request, account=account, action="subtitle_cue_created", target=cue_id, detail="Created manual subtitle cue")
        return envelope(True, "Đã thêm cue do người dùng soạn.", data={"project": _project_public(changed_project, include_content=False), "cue": _cue_public(cue, include_content=True), **_boundary()}, status_name=str(changed_project[9]))

    return _idempotent(f"web-subtitle-studio:{account_id}:create_cue:{resolved}", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/projects/{project_id}/cues/{cue_id}")
async def subtitle_cue_update(project_id: str, cue_id: str, payload: CueUpdateRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    resolved_project = _uuid(project_id, label="Subtitle project ID")
    resolved_cue = _uuid(cue_id, label="Cue ID")
    account_id = str(account["id"])
    snapshot = _cue_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_cue", "project_id": resolved_project, "cue_id": resolved_cue, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        project = _project_row(conn, project_id=resolved_project, account_id=account_id)
        if not project:
            return _project_not_found()
        blocked = _project_writable(project)
        if blocked:
            return blocked
        cue = _cue_row(conn, project_id=resolved_project, cue_id=resolved_cue, account_id=account_id)
        if not cue:
            return _cue_not_found()
        if str(cue[9]) == "archived":
            return _guarded("Cue đã archive và không thể chỉnh sửa trước khi khôi phục.", "WEB_SUBTITLE_CUE_ARCHIVED")
        if int(cue[10]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_subtitle_cue_versions", entity_column="cue_id", entity_id=resolved_cue, account_id=account_id):
            return _guarded("Cue đã đạt giới hạn lịch sử phiên bản.", "WEB_SUBTITLE_VERSION_LIMIT")
        _validate_no_overlap(conn, project_id=resolved_project, account_id=account_id, candidates=[snapshot], exclude_cue_id=resolved_cue)
        now = utc_now()
        revision = int(cue[10]) + 1
        _write_cue(conn, cue_id=resolved_cue, project_id=resolved_project, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_cue_version(conn, cue_id=resolved_cue, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_project = _advance_project_for_cue_change(conn, project=project, account_id=account_id, now=now, action="cue_updated", cue_id=resolved_cue)
        changed = _cue_row(conn, project_id=resolved_project, cue_id=resolved_cue, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle cue")
        _audit(conn, request=request, account=account, action="subtitle_cue_updated", target=resolved_cue, detail="Updated manual subtitle cue")
        return envelope(True, "Đã lưu revision cue mới.", data={"project": _project_public(changed_project, include_content=False), "cue": _cue_public(changed, include_content=True), **_boundary()}, status_name=str(changed_project[9]))

    return _idempotent(f"web-subtitle-studio:{account_id}:update_cue:{resolved_project}:{resolved_cue}", account_id, payload.idempotency_key, fingerprint, operation)


def _cue_state_mutation(project_id: str, cue_id: str, payload: RevisionRequest | RestoreVersionRequest, request: Request, account: dict, *, action: str) -> dict[str, Any]:
    resolved_project = _uuid(project_id, label="Subtitle project ID")
    resolved_cue = _uuid(cue_id, label="Cue ID")
    account_id = str(account["id"])
    target_revision = payload.target_revision if isinstance(payload, RestoreVersionRequest) else None
    fingerprint = _fingerprint({"action": action, "project_id": resolved_project, "cue_id": resolved_cue,
                                "expected_revision": payload.expected_revision, "target_revision": target_revision})

    def operation(conn: Any) -> dict[str, Any]:
        project = _project_row(conn, project_id=resolved_project, account_id=account_id)
        if not project:
            return _project_not_found()
        blocked = _project_writable(project)
        if blocked:
            return blocked
        cue = _cue_row(conn, project_id=resolved_project, cue_id=resolved_cue, account_id=account_id)
        if not cue:
            return _cue_not_found()
        if int(cue[10]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_subtitle_cue_versions", entity_column="cue_id", entity_id=resolved_cue, account_id=account_id):
            return _guarded("Cue đã đạt giới hạn lịch sử phiên bản.", "WEB_SUBTITLE_VERSION_LIMIT")
        now = utc_now()
        current_state = str(cue[9])
        snapshot = _cue_snapshot_from_row(cue)
        archived_at: str | None = None
        ordinal: int | None = None
        if action == "cue_archived":
            if current_state != "active":
                return _guarded("Cue đã archive.", "WEB_SUBTITLE_CUE_ARCHIVED")
            snapshot["state"] = "archived"
            archived_at = now
            _normalise_archived_ordinals(conn, project_id=resolved_project, account_id=account_id)
            last = conn.execute("SELECT COALESCE(MAX(ordinal), ?) FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='archived'", (ARCHIVED_ORDINAL_BASE - 1, resolved_project, account_id)).fetchone()
            ordinal = max(ARCHIVED_ORDINAL_BASE, int(last[0] or ARCHIVED_ORDINAL_BASE - 1) + 1)
        elif action == "cue_restored":
            if current_state != "archived":
                return _guarded("Cue đang hoạt động, không cần khôi phục.", "WEB_SUBTITLE_CUE_ACTIVE")
            snapshot["state"] = "active"
            _validate_no_overlap(conn, project_id=resolved_project, account_id=account_id, candidates=[snapshot])
            ordinal = _next_active_ordinal(conn, project_id=resolved_project, account_id=account_id)
        elif action == "cue_version_restored":
            if current_state != "active":
                return _guarded("Cue đã archive; hãy khôi phục cue trước khi khôi phục phiên bản.", "WEB_SUBTITLE_CUE_ARCHIVED")
            version = conn.execute("SELECT snapshot_json FROM web_subtitle_cue_versions WHERE cue_id=? AND account_id=? AND revision=?", (resolved_cue, account_id, target_revision)).fetchone()
            if not version:
                return _guarded("Không tìm thấy revision cue cần khôi phục.", "WEB_SUBTITLE_VERSION_NOT_FOUND")
            try:
                source = json.loads(str(version[0]))
                restored = _cue_payload_from_snapshot(source if isinstance(source, dict) else {})
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Revision cue không hợp lệ") from exc
            snapshot = _cue_snapshot(restored, state="active")
            _validate_no_overlap(conn, project_id=resolved_project, account_id=account_id, candidates=[snapshot], exclude_cue_id=resolved_cue)
        else:
            raise HTTPException(status_code=422, detail="Thao tác cue không hợp lệ")
        revision = int(cue[10]) + 1
        _write_cue(conn, cue_id=resolved_cue, project_id=resolved_project, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=archived_at)
        if ordinal is not None:
            conn.execute("UPDATE web_subtitle_cues SET ordinal=? WHERE id=? AND subtitle_project_id=? AND account_id=?", (ordinal, resolved_cue, resolved_project, account_id))
        _insert_cue_version(conn, cue_id=resolved_cue, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_project = _advance_project_for_cue_change(conn, project=project, account_id=account_id, now=now, action=action, cue_id=resolved_cue)
        changed = _cue_row(conn, project_id=resolved_project, cue_id=resolved_cue, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại subtitle cue")
        _audit(conn, request=request, account=account, action=f"subtitle_{action}", target=resolved_cue, detail=action)
        return envelope(True, "Đã cập nhật trạng thái cue.", data={"project": _project_public(changed_project, include_content=False), "cue": _cue_public(changed, include_content=True), "history_snapshot_recorded": action == "cue_version_restored", **_boundary()}, status_name=str(changed_project[9]))

    return _idempotent(f"web-subtitle-studio:{account_id}:{action}:{resolved_project}:{resolved_cue}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/projects/{project_id}/cues/{cue_id}/archive")
async def subtitle_cue_archive(project_id: str, cue_id: str, payload: RevisionRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    return _cue_state_mutation(project_id, cue_id, payload, request, account, action="cue_archived")


@router.post("/projects/{project_id}/cues/{cue_id}/restore")
async def subtitle_cue_restore(project_id: str, cue_id: str, payload: RevisionRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    return _cue_state_mutation(project_id, cue_id, payload, request, account, action="cue_restored")


@router.post("/projects/{project_id}/cues/{cue_id}/restore-version")
async def subtitle_cue_restore_version(project_id: str, cue_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    return _cue_state_mutation(project_id, cue_id, payload, request, account, action="cue_version_restored")


@router.post("/projects/{project_id}/cues/reorder")
async def subtitle_cue_reorder(project_id: str, payload: ReorderRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "reorder_cues", "project_id": resolved, "expected_revision": payload.expected_revision, "cue_ids": payload.cue_ids})

    def operation(conn: Any) -> dict[str, Any]:
        project = _project_row(conn, project_id=resolved, account_id=account_id)
        if not project:
            return _project_not_found()
        blocked = _project_writable(project)
        if blocked:
            return blocked
        if int(project[10]) != payload.expected_revision:
            return _revision_conflict()
        if len(payload.cue_ids) != len(set(payload.cue_ids)):
            return _guarded("Danh sách cue sắp xếp không được chứa ID trùng lặp.", "WEB_SUBTITLE_REORDER_INVALID")
        rows = conn.execute(
            "SELECT id FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC",
            (resolved, account_id),
        ).fetchall()
        active_ids = [str(row[0]) for row in rows]
        if set(payload.cue_ids) != set(active_ids) or len(payload.cue_ids) != len(active_ids):
            return _guarded("Thứ tự mới phải chứa chính xác mọi cue đang hoạt động của subtitle project.", "WEB_SUBTITLE_REORDER_INVALID")
        if not _can_add_version(conn, table="web_subtitle_project_versions", entity_column="subtitle_project_id", entity_id=resolved, account_id=account_id):
            return _guarded("Subtitle project đã đạt giới hạn lịch sử phiên bản.", "WEB_SUBTITLE_VERSION_LIMIT")
        now = utc_now()
        # Temporary values are disjoint from active (1..N) and archived
        # (1,000,000+) ranges; the unique constraint cannot observe a swap.
        for index, cue_id_value in enumerate(payload.cue_ids, start=1):
            conn.execute("UPDATE web_subtitle_cues SET ordinal=? WHERE id=? AND subtitle_project_id=? AND account_id=?", (REORDER_TEMPORARY_ORDINAL_BASE + index, cue_id_value, resolved, account_id))
        for index, cue_id_value in enumerate(payload.cue_ids, start=1):
            conn.execute("UPDATE web_subtitle_cues SET ordinal=?, updated_at=? WHERE id=? AND subtitle_project_id=? AND account_id=?", (index, now, cue_id_value, resolved, account_id))
        changed_project = _advance_project_for_cue_change(conn, project=project, account_id=account_id, now=now, action="cues_reordered")
        _audit(conn, request=request, account=account, action="subtitle_cues_reordered", target=resolved, detail=f"Reordered {len(payload.cue_ids)} manual cues")
        return envelope(True, "Đã cập nhật thứ tự cues.", data={"project": _project_public(changed_project, include_content=False), "reordered": True, **_boundary()}, status_name=str(changed_project[9]))

    return _idempotent(f"web-subtitle-studio:{account_id}:reorder_cues:{resolved}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/projects/{project_id}/import")
async def subtitle_import(project_id: str, payload: ImportRequest, request: Request, account: dict = Depends(require_account), _csrf: None = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    account_id = str(account["id"])
    imported = _parse_caption_text(payload.format, payload.content)
    # Fingerprint the text but never persist it in an idempotency receipt.
    fingerprint = _fingerprint({"action": "import_cues", "project_id": resolved, "expected_revision": payload.expected_revision,
                                "format": payload.format, "content_hash": hashlib.sha256(payload.content.encode("utf-8")).hexdigest()})

    def operation(conn: Any) -> dict[str, Any]:
        project = _project_row(conn, project_id=resolved, account_id=account_id)
        if not project:
            return _project_not_found()
        blocked = _project_writable(project)
        if blocked:
            return blocked
        if int(project[10]) != payload.expected_revision:
            return _revision_conflict()
        active_rows = conn.execute(
            """SELECT id, subtitle_project_id, ordinal, start_ms, end_ms, speaker, source_text, translated_text,
                      notes, state, revision, created_at, updated_at, archived_at
               FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC""",
            (resolved, account_id),
        ).fetchall()
        if len(imported) > MAX_CUES_PER_PROJECT:
            return _guarded(f"Import vượt giới hạn {MAX_CUES_PER_PROJECT} cues đang hoạt động.", "WEB_SUBTITLE_CUE_LIMIT")
        # Import replaces the active cue set. Validate its entire timeline
        # before moving any existing active cue, so the operation is atomic.
        _validate_no_overlap(conn, project_id=resolved, account_id=account_id, candidates=imported, include_existing=False)
        if not _can_add_version(conn, table="web_subtitle_project_versions", entity_column="subtitle_project_id", entity_id=resolved, account_id=account_id):
            return _guarded("Subtitle project đã đạt giới hạn lịch sử phiên bản.", "WEB_SUBTITLE_VERSION_LIMIT")
        for row in active_rows:
            if not _can_add_version(conn, table="web_subtitle_cue_versions", entity_column="cue_id", entity_id=str(row[0]), account_id=account_id):
                return _guarded("Một cue cũ đã đạt giới hạn lịch sử phiên bản; import chưa thay đổi dữ liệu.", "WEB_SUBTITLE_VERSION_LIMIT")
        now = utc_now()
        _normalise_archived_ordinals(conn, project_id=resolved, account_id=account_id)
        for index, row in enumerate(active_rows, start=1):
            old_snapshot = _cue_snapshot_from_row(row, state="archived")
            old_revision = int(row[10]) + 1
            _write_cue(conn, cue_id=str(row[0]), project_id=resolved, account_id=account_id, snapshot=old_snapshot, revision=old_revision, now=now, archived_at=now)
            conn.execute("UPDATE web_subtitle_cues SET ordinal=? WHERE id=? AND subtitle_project_id=? AND account_id=?", (REORDER_TEMPORARY_ORDINAL_BASE + index, str(row[0]), resolved, account_id))
            _insert_cue_version(conn, cue_id=str(row[0]), account_id=account_id, revision=old_revision, snapshot=old_snapshot, now=now)
            _event(conn, account_id=account_id, project_id=resolved, cue_id=str(row[0]), action="cue_replaced_archived", revision=old_revision)
        _normalise_archived_ordinals(conn, project_id=resolved, account_id=account_id)
        ordinal = 1
        for item in imported:
            cue_id_value = str(uuid.uuid4())
            _insert_cue(conn, cue_id=cue_id_value, project_id=resolved, account_id=account_id, ordinal=ordinal, snapshot=item, revision=1, now=now)
            _insert_cue_version(conn, cue_id=cue_id_value, account_id=account_id, revision=1, snapshot=item, now=now)
            _event(conn, account_id=account_id, project_id=resolved, cue_id=cue_id_value, action="cue_imported", revision=1)
            ordinal += 1
        changed_project = _advance_project_for_cue_change(conn, project=project, account_id=account_id, now=now, action="cues_imported")
        _audit(conn, request=request, account=account, action="subtitle_cues_imported", target=resolved, detail=f"Replaced {len(active_rows)} and imported {len(imported)} bounded {payload.format.upper()} text cues")
        return envelope(True, "Đã thay thế cues đang hoạt động bằng văn bản SRT/VTT; cues cũ được archive cùng history. Không có tệp, media hoặc transcript engine nào được chạy.", data={"project": _project_public(changed_project, include_content=False), "imported_count": len(imported), "replaced_count": len(active_rows), **_boundary()}, status_name=str(changed_project[9]))

    return _idempotent(f"web-subtitle-studio:{account_id}:import:{resolved}", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/projects/{project_id}/export")
async def subtitle_export(
    project_id: str, format: str = Query(default="srt", max_length=12), track: str = Query(default="source", max_length=16),
    account: dict = Depends(require_account),
):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    normalized_format = format.strip().lower()
    normalized_track = track.strip().lower()
    if normalized_format not in CAPTION_FORMATS or normalized_track not in {"source", "translation"}:
        raise HTTPException(status_code=422, detail="Định dạng export hoặc track không hợp lệ")
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        project = _project_row(conn, project_id=resolved, account_id=account_id)
        if not project:
            return _project_not_found()
        if str(project[9]) == "archived":
            return _guarded("Subtitle project đã archive; export bị khóa cho đến khi khôi phục về Draft.", "WEB_SUBTITLE_PROJECT_ARCHIVED")
        rows = conn.execute(
            """SELECT id, subtitle_project_id, ordinal, start_ms, end_ms, speaker, source_text, translated_text,
                      notes, state, revision, created_at, updated_at, archived_at
               FROM web_subtitle_cues WHERE subtitle_project_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC""",
            (resolved, account_id),
        ).fetchall()
        if normalized_track == "translation":
            if not str(project[4]).strip() or any(not str(row[7]).strip() for row in rows):
                return _guarded("Bản dịch vẫn là draft thủ công và chưa đủ cue để export track dịch.", "WEB_SUBTITLE_TRANSLATION_DRAFT_INCOMPLETE")
        text = _export_caption_text(normalized_format, rows, track=normalized_track)
        return envelope(True, "Đã tạo văn bản SRT/VTT từ cues do bạn soạn. Đây không phải output ASR, dịch, TTS hoặc dubbing.", data={
            "project_id": resolved, "format": normalized_format, "track": normalized_track, "cue_count": len(rows),
            "text": text, "notice": "Nội dung chỉ là export text riêng tư; browser phải render escaped plain text, không tạo media hay delivery.",
            **_boundary()}, status_name="read_only")


@router.get("/projects/{project_id}/estimate")
async def subtitle_estimate(project_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(project_id, label="Subtitle project ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        project = _project_row(conn, project_id=resolved, account_id=str(account["id"]))
        if not project:
            return _project_not_found()
        return _estimate(conn, project=project, account_id=str(account["id"]))


@router.get("/events")
async def subtitle_events(limit: int = Query(default=30, ge=1, le=MAX_EVENT_LIMIT), account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT subtitle_project_id, cue_id, entity_type, action, revision, created_at
               FROM web_subtitle_workspace_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
            (str(account["id"]), limit),
        ).fetchall()
        return envelope(True, "Đã tải audit timeline Subtitle Studio.", data={"items": [
            {"project_id": str(row[0]), "cue_id": str(row[1]) if row[1] else None, "entity_type": str(row[2]),
             "action": str(row[3]), "revision": int(row[4]), "created_at": str(row[5])} for row in rows], **_boundary()}, status_name="read_only")
