"""Private, Web-native Video Production Studio.

This router owns planning metadata only: a video brief, ordered scene board,
self-review lifecycle and immutable revision history for the signed Web
account.  It deliberately does not accept media, source URLs, engine
configuration, delivery records or any execution request.  A saved plan is
never evidence that a video exists.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now, video_studio_enabled


router = APIRouter(prefix="/api/v1/video-studio", tags=["Web Video Production Studio"])

PLAN_STATES = frozenset({"draft", "review", "approved", "archived"})
WRITABLE_PLAN_STATES = frozenset({"draft", "review"})
PLAN_FORMATS = frozenset({"short_form", "product_demo", "explainer", "ugc", "campaign", "custom"})
ASPECT_RATIOS = frozenset({"9:16", "16:9", "1:1", "4:5", "custom"})
SCENE_TYPES = frozenset({"hook", "problem", "solution", "product", "proof", "cta", "transition", "custom"})
SCENE_STATES = frozenset({"active", "archived"})

IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Deliberately reject URL/scheme markers wherever they occur.  A boundary
# such as ``(^|\\s)`` is too weak here because a source URL is commonly
# enclosed in punctuation, e.g. ``(https://...)`` or ``<file:...>``.
URL_PATTERN = re.compile(r"(?:https?://|www\.|file:|data:|javascript:)", re.IGNORECASE)
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|password|passphrase|authorization|otp|cvv|cvc|"
    r"private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?"
    r"[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|"
    r"xox[bpars]-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:txid|transaction\s+(?:hash|id|reference)|mã\s*(?:giao\s*)?(?:dịch|thanh\s*toán)|"
    r"bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|qr\s*(?:code|thanh\s*toán))\b",
    re.IGNORECASE,
)
# Video Studio has no execution authority and deliberately stores no opaque
# provider/Bot/job/media handles.  Block identifier-shaped references in the
# authoring fields rather than allowing an accidental second integration
# contract to form inside free text.
EXTERNAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:(?:provider|render|job|media)[ _-]*(?:id|ref(?:erence)?|token)|telegram[ _-]*file[ _-]*id|file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+",
    re.IGNORECASE,
)

MAX_PLANS_PER_ACCOUNT = 300
MAX_SCENES_PER_PLAN = 250
MAX_VERSIONS_PER_ENTITY = 100
MAX_EVENT_LIMIT = 50
MAX_LIST_LIMIT = 100
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1024
# ``web_video_scenes`` intentionally keeps a single ``UNIQUE(plan_id,
# ordinal)`` constraint.  Archived scenes therefore live in a disjoint range
# so active scenes can always be reordered to 1..N without colliding with an
# archived middle scene.  The temporary reorder range remains separate from
# both ranges for the duration of an atomic SQLite transaction.
ARCHIVED_ORDINAL_BASE = 1_000_000
REORDER_TEMPORARY_ORDINAL_BASE = 2_000_000


def _require_enabled() -> None:
    if not video_studio_enabled():
        raise HTTPException(
            status_code=503,
            detail="Video Production Studio đang tạm dừng để bảo trì. WEBAPP_VIDEO_STUDIO_ENABLED chưa được bật.",
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
        or EXTERNAL_REFERENCE_PATTERN.search(value)
        or "-----begin" in value.lower()
    )


def _line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu provider hoặc chứng từ thanh toán")
    return text


def _body(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu provider hoặc chứng từ thanh toán")
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
    return text if len(text) <= limit else f"{text[: max(1, limit - 1)].rstrip()}…"


class PlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    format: str = "short_form"
    language: str = "vi"
    aspect_ratio: str = "9:16"
    target_duration_seconds: int = Field(ge=1, le=7200)
    objective: str = ""
    audience: str = ""
    brief: str
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên video plan", minimum=2, maximum=180)

    @field_validator("format")
    @classmethod
    def _format(cls, value: str) -> str:
        normalized = _line(value, label="Loại video plan", minimum=1, maximum=32).lower()
        if normalized not in PLAN_FORMATS:
            raise ValueError("Loại video plan không hợp lệ")
        return normalized

    @field_validator("language")
    @classmethod
    def _language(cls, value: str) -> str:
        return _line(value, label="Ngôn ngữ", minimum=1, maximum=100)

    @field_validator("aspect_ratio")
    @classmethod
    def _ratio(cls, value: str) -> str:
        normalized = _line(value, label="Tỷ lệ khung hình", minimum=1, maximum=32)
        if normalized not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ khung hình không hợp lệ")
        return normalized

    @field_validator("objective")
    @classmethod
    def _objective(cls, value: str) -> str:
        return _body(value, label="Mục tiêu", maximum=1200, allow_empty=True)

    @field_validator("audience")
    @classmethod
    def _audience(cls, value: str) -> str:
        return _body(value, label="Đối tượng", maximum=1200, allow_empty=True)

    @field_validator("brief")
    @classmethod
    def _brief(cls, value: str) -> str:
        return _body(value, label="Creative brief", maximum=12000)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Project ID")


class PlanCreateRequest(PlanPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class PlanUpdateRequest(PlanPayload):
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


class RestoreVersionRequest(RevisionRequest):
    target_revision: int = Field(ge=1)


class LifecycleRequest(RevisionRequest):
    state: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái", minimum=1, maximum=20).lower()
        if normalized not in PLAN_STATES:
            raise ValueError("Trạng thái video plan không hợp lệ")
        return normalized


class ScenePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    scene_type: str = "custom"
    duration_seconds: int = Field(ge=1, le=1800)
    visual_direction: str = ""
    narration: str = ""
    on_screen_text: str = ""
    shot_notes: str = ""
    transition: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên scene", minimum=2, maximum=180)

    @field_validator("scene_type")
    @classmethod
    def _kind(cls, value: str) -> str:
        normalized = _line(value, label="Vai trò scene", minimum=1, maximum=32).lower()
        if normalized not in SCENE_TYPES:
            raise ValueError("Vai trò scene không hợp lệ")
        return normalized

    @field_validator("visual_direction")
    @classmethod
    def _visual(cls, value: str) -> str:
        return _body(value, label="Visual direction", maximum=5000, allow_empty=True)

    @field_validator("narration")
    @classmethod
    def _narration(cls, value: str) -> str:
        return _body(value, label="Narration", maximum=5000, allow_empty=True)

    @field_validator("on_screen_text")
    @classmethod
    def _screen_text(cls, value: str) -> str:
        return _body(value, label="Text trên màn hình", maximum=3000, allow_empty=True)

    @field_validator("shot_notes")
    @classmethod
    def _shot_notes(cls, value: str) -> str:
        return _body(value, label="Ghi chú quay dựng", maximum=5000, allow_empty=True)

    @field_validator("transition")
    @classmethod
    def _transition(cls, value: str) -> str:
        return _line(value, label="Chuyển cảnh", minimum=0, maximum=500, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)


class SceneCreateRequest(ScenePayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class SceneUpdateRequest(ScenePayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ReorderRequest(RevisionRequest):
    scene_ids: list[str] = Field(min_length=1, max_length=MAX_SCENES_PER_PLAN)

    @field_validator("scene_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        values = [_uuid(item, label="Scene ID") for item in value]
        if len(values) != len(set(values)):
            raise ValueError("Scene ID không được trùng")
        return values


def _boundary(**extra: Any) -> dict[str, Any]:
    return {
        "execution": "authoring_only",
        "provider_called": False,
        "video_created": False,
        "media_uploads": False,
        "preview_available": False,
        "output_delivery": "guarded",
        **extra,
    }


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary()
    plan = source.get("plan")
    if isinstance(plan, dict) and isinstance(plan.get("id"), str):
        data["plan"] = {
            "id": str(plan["id"]),
            "revision": int(plan.get("revision") or 0),
            "state": str(plan.get("state") or ""),
        }
    scene = source.get("scene")
    if isinstance(scene, dict) and isinstance(scene.get("id"), str):
        data["scene"] = {
            "id": str(scene["id"]),
            "plan_id": str(scene.get("plan_id") or ""),
            "revision": int(scene.get("revision") or 0),
            "state": str(scene.get("state") or ""),
        }
    for field in ("history_snapshot_recorded", "scene_count", "reordered"):
        if field in source:
            data[field] = source[field]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Video Production Studio."),
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
            ("web-video-studio:%", _idempotency_cutoff()),
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
                replay = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Video Studio không hợp lệ") from exc
            if not isinstance(replay, dict):
                raise HTTPException(status_code=409, detail="Receipt Video Studio không hợp lệ")
            return replay
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-video-studio:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(
                False,
                "Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.",
                status_name="guarded",
                error_code="WEB_VIDEO_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
    return response


def _plan_row(conn: Any, *, plan_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, title, video_format, language, aspect_ratio, target_duration_seconds,
                  objective, audience, brief, tags_json, lifecycle, revision, created_at, updated_at, archived_at
           FROM web_video_plans WHERE id=? AND account_id=?""",
        (plan_id, account_id),
    ).fetchone()


def _scene_row(conn: Any, *, plan_id: str, scene_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, plan_id, ordinal, title, scene_type, duration_seconds, visual_direction, narration,
                  on_screen_text, shot_notes, transition, tags_json, state, revision, created_at, updated_at, archived_at
           FROM web_video_scenes WHERE id=? AND plan_id=? AND account_id=?""",
        (scene_id, plan_id, account_id),
    ).fetchone()


def _plan_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy video plan thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_VIDEO_PLAN_NOT_FOUND")


def _scene_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy scene thuộc video plan hiện tại.", status_name="guarded", error_code="WEB_VIDEO_SCENE_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return envelope(False, "Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại trước khi lưu tiếp.", status_name="guarded", error_code="WEB_VIDEO_REVISION_CONFLICT")


def _plan_archived() -> dict[str, Any]:
    return envelope(False, "Video plan đã archive; hãy khôi phục về Draft trước khi tiếp tục.", status_name="guarded", error_code="WEB_VIDEO_PLAN_ARCHIVED")


def _plan_approved() -> dict[str, Any]:
    return envelope(False, "Video plan đã self-review. Hãy chuyển về Draft trước khi chỉnh sửa plan hoặc scene.", status_name="guarded", error_code="WEB_VIDEO_PLAN_APPROVED")


def _scene_archived() -> dict[str, Any]:
    return envelope(False, "Scene đã archive và không thể chỉnh sửa trước khi khôi phục.", status_name="guarded", error_code="WEB_VIDEO_SCENE_ARCHIVED")


def _plan_writable(plan: tuple[Any, ...]) -> dict[str, Any] | None:
    lifecycle = str(plan[11])
    if lifecycle == "archived":
        return _plan_archived()
    if lifecycle == "approved":
        return _plan_approved()
    if lifecycle not in WRITABLE_PLAN_STATES:
        return envelope(False, "Trạng thái video plan không cho phép authoring.", status_name="guarded", error_code="WEB_VIDEO_PLAN_GUARDED")
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


def _plan_snapshot(payload: PlanPayload, *, lifecycle: str = "draft") -> dict[str, Any]:
    return {
        "title": payload.title,
        "format": payload.format,
        "language": payload.language,
        "aspect_ratio": payload.aspect_ratio,
        "target_duration_seconds": int(payload.target_duration_seconds),
        "objective": payload.objective,
        "audience": payload.audience,
        "brief": payload.brief,
        "tags": list(payload.tags),
        "project_id": payload.project_id,
        "lifecycle": lifecycle,
    }


def _plan_snapshot_from_row(row: tuple[Any, ...], *, lifecycle: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[2]),
        "format": str(row[3]),
        "language": str(row[4]),
        "aspect_ratio": str(row[5]),
        "target_duration_seconds": int(row[6]),
        "objective": str(row[7]),
        "audience": str(row[8]),
        "brief": str(row[9]),
        "tags": _decode_tags(row[10]),
        "project_id": str(row[1]) if row[1] else None,
        "lifecycle": lifecycle or str(row[11]),
    }


def _plan_payload_from_snapshot(snapshot: dict[str, Any]) -> PlanPayload:
    return PlanPayload.model_validate(
        {
            "title": snapshot.get("title", ""),
            "format": snapshot.get("format", "short_form"),
            "language": snapshot.get("language", "vi"),
            "aspect_ratio": snapshot.get("aspect_ratio", "9:16"),
            "target_duration_seconds": snapshot.get("target_duration_seconds", 30),
            "objective": snapshot.get("objective", ""),
            "audience": snapshot.get("audience", ""),
            "brief": snapshot.get("brief", ""),
            "tags": snapshot.get("tags", []),
            "project_id": snapshot.get("project_id"),
        }
    )


def _scene_snapshot(payload: ScenePayload, *, state: str = "active") -> dict[str, Any]:
    return {
        "title": payload.title,
        "scene_type": payload.scene_type,
        "duration_seconds": int(payload.duration_seconds),
        "visual_direction": payload.visual_direction,
        "narration": payload.narration,
        "on_screen_text": payload.on_screen_text,
        "shot_notes": payload.shot_notes,
        "transition": payload.transition,
        "tags": list(payload.tags),
        "state": state,
    }


def _scene_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[3]),
        "scene_type": str(row[4]),
        "duration_seconds": int(row[5]),
        "visual_direction": str(row[6]),
        "narration": str(row[7]),
        "on_screen_text": str(row[8]),
        "shot_notes": str(row[9]),
        "transition": str(row[10]),
        "tags": _decode_tags(row[11]),
        "state": state or str(row[12]),
    }


def _scene_payload_from_snapshot(snapshot: dict[str, Any]) -> ScenePayload:
    return ScenePayload.model_validate(
        {
            "title": snapshot.get("title", ""),
            "scene_type": snapshot.get("scene_type", "custom"),
            "duration_seconds": snapshot.get("duration_seconds", 5),
            "visual_direction": snapshot.get("visual_direction", ""),
            "narration": snapshot.get("narration", ""),
            "on_screen_text": snapshot.get("on_screen_text", ""),
            "shot_notes": snapshot.get("shot_notes", ""),
            "transition": snapshot.get("transition", ""),
            "tags": snapshot.get("tags", []),
        }
    )


def _plan_public(row: tuple[Any, ...], *, scene_count: int = 0, include_content: bool = False) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "title": str(row[2]),
        "format": str(row[3]),
        "language": str(row[4]),
        "aspect_ratio": str(row[5]),
        "target_duration_seconds": int(row[6]),
        "objective": str(row[7]),
        "audience_excerpt": _excerpt(row[8], 180),
        "brief_excerpt": _excerpt(row[9], 360),
        "tags": _decode_tags(row[10]),
        "state": str(row[11]),
        "revision": int(row[12]),
        "created_at": str(row[13]),
        "updated_at": str(row[14]),
        "archived_at": str(row[15]) if row[15] else None,
        "scene_count": int(scene_count),
        **_boundary(),
    }
    if include_content:
        value.update({"audience": str(row[8]), "brief": str(row[9])})
    return value


def _scene_public(row: tuple[Any, ...], *, include_content: bool = False, versions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "plan_id": str(row[1]),
        "ordinal": int(row[2]),
        "title": str(row[3]),
        "scene_type": str(row[4]),
        "duration_seconds": int(row[5]),
        "visual_excerpt": _excerpt(row[6], 260),
        "narration_excerpt": _excerpt(row[7], 260),
        "on_screen_text_excerpt": _excerpt(row[8], 200),
        "shot_notes_excerpt": _excerpt(row[9], 260),
        "transition": str(row[10]),
        "tags": _decode_tags(row[11]),
        "state": str(row[12]),
        "revision": int(row[13]),
        "created_at": str(row[14]),
        "updated_at": str(row[15]),
        "archived_at": str(row[16]) if row[16] else None,
        **_boundary(),
    }
    if include_content:
        value.update(
            {
                "visual_direction": str(row[6]),
                "narration": str(row[7]),
                "on_screen_text": str(row[8]),
                "shot_notes": str(row[9]),
            }
        )
    if versions is not None:
        value["versions"] = versions
    return value


def _plan_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Video plan"),
        "format": str(snapshot.get("format") or "short_form"),
        "state": str(snapshot.get("lifecycle") or "draft"),
        "brief_excerpt": _excerpt(snapshot.get("brief"), 280),
        "created_at": str(row[2]),
    }


def _scene_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Scene"),
        "scene_type": str(snapshot.get("scene_type") or "custom"),
        "state": str(snapshot.get("state") or "active"),
        "visual_excerpt": _excerpt(snapshot.get("visual_direction"), 220),
        "created_at": str(row[2]),
    }


def _insert_plan(conn: Any, *, plan_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_video_plans
           (id, account_id, project_id, title, video_format, language, aspect_ratio, target_duration_seconds,
            objective, audience, brief, tags_json, lifecycle, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            plan_id, account_id, snapshot.get("project_id"), snapshot["title"], snapshot["format"], snapshot["language"],
            snapshot["aspect_ratio"], snapshot["target_duration_seconds"], snapshot["objective"], snapshot["audience"],
            snapshot["brief"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["lifecycle"], revision, now, now, now if snapshot["lifecycle"] == "archived" else None,
        ),
    )


def _write_plan(conn: Any, *, plan_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_video_plans
           SET project_id=?, title=?, video_format=?, language=?, aspect_ratio=?, target_duration_seconds=?,
               objective=?, audience=?, brief=?, tags_json=?, lifecycle=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            snapshot.get("project_id"), snapshot["title"], snapshot["format"], snapshot["language"],
            snapshot["aspect_ratio"], snapshot["target_duration_seconds"], snapshot["objective"], snapshot["audience"],
            snapshot["brief"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["lifecycle"], revision, now, archived_at, plan_id, account_id,
        ),
    )


def _insert_plan_version(conn: Any, *, plan_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_video_plan_versions (id, plan_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), plan_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _insert_scene(conn: Any, *, scene_id: str, plan_id: str, account_id: str, ordinal: int, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_video_scenes
           (id, plan_id, account_id, ordinal, title, scene_type, duration_seconds, visual_direction, narration,
            on_screen_text, shot_notes, transition, tags_json, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            scene_id, plan_id, account_id, ordinal, snapshot["title"], snapshot["scene_type"],
            snapshot["duration_seconds"], snapshot["visual_direction"], snapshot["narration"],
            snapshot["on_screen_text"], snapshot["shot_notes"], snapshot["transition"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"],
            revision, now, now, now if snapshot["state"] == "archived" else None,
        ),
    )


def _write_scene(conn: Any, *, scene_id: str, plan_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_video_scenes
           SET title=?, scene_type=?, duration_seconds=?, visual_direction=?, narration=?, on_screen_text=?,
               shot_notes=?, transition=?, tags_json=?, state=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND plan_id=? AND account_id=?""",
        (
            snapshot["title"], snapshot["scene_type"], snapshot["duration_seconds"], snapshot["visual_direction"],
            snapshot["narration"], snapshot["on_screen_text"], snapshot["shot_notes"], snapshot["transition"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"],
            revision, now, archived_at, scene_id, plan_id, account_id,
        ),
    )


def _insert_scene_version(conn: Any, *, scene_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_video_scene_versions (id, scene_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), scene_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _can_add_version(conn: Any, *, table: str, entity_column: str, entity_id: str, account_id: str) -> bool:
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {entity_column}=? AND account_id=?",
        (entity_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _next_active_ordinal(conn: Any, *, plan_id: str, account_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
        (plan_id, account_id),
    ).fetchone()
    return int(row[0] or 0) + 1


def _next_archived_ordinal(conn: Any, *, plan_id: str, account_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='archived'",
        (plan_id, account_id),
    ).fetchone()
    return max(ARCHIVED_ORDINAL_BASE, int(row[0] or 0) + 1)


def _normalise_archived_ordinals(conn: Any, *, plan_id: str, account_id: str) -> None:
    """Put every archived scene into the non-active ordinal range.

    This also safely repairs any legacy archived row whose ordinal predates
    the range policy.  The negative temporary pass prevents a unique-index
    collision while two archived rows exchange their old positions.
    """

    rows = conn.execute(
        "SELECT id FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='archived' ORDER BY archived_at ASC, id ASC",
        (plan_id, account_id),
    ).fetchall()
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
            (-index, str(row[0]), plan_id, account_id),
        )
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
            (ARCHIVED_ORDINAL_BASE + index - 1, str(row[0]), plan_id, account_id),
        )


def _event(conn: Any, *, account_id: str, plan_id: str, action: str, revision: int, scene_id: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_video_studio_events
           (id, account_id, plan_id, scene_id, entity_type, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, plan_id, scene_id, "scene" if scene_id else "plan", action, revision, utc_now()),
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


def _advance_plan_for_scene_change(conn: Any, *, plan: tuple[Any, ...], account_id: str, now: str, event: str, scene_id: str | None = None) -> tuple[Any, ...]:
    """Record a plan revision around a child change and reopen review if needed."""

    plan_id = str(plan[0])
    if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=plan_id, account_id=account_id):
        raise HTTPException(status_code=409, detail="Video plan đã đạt giới hạn lịch sử phiên bản")
    lifecycle = "draft" if str(plan[11]) == "review" else str(plan[11])
    snapshot = _plan_snapshot_from_row(plan, lifecycle=lifecycle)
    revision = int(plan[12]) + 1
    _write_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
    _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
    _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action=event, revision=revision)
    changed = _plan_row(conn, plan_id=plan_id, account_id=account_id)
    if not changed:
        raise HTTPException(status_code=500, detail="Không thể đọc lại video plan")
    return changed


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    counts = {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT lifecycle, COUNT(*) FROM web_video_plans WHERE account_id=? GROUP BY lifecycle",
            (account_id,),
        ).fetchall()
    }
    scenes = conn.execute("SELECT COUNT(*) FROM web_video_scenes WHERE account_id=? AND state='active'", (account_id,)).fetchone()
    return {
        "plans": {
            "draft": counts.get("draft", 0),
            "review": counts.get("review", 0),
            "approved": counts.get("approved", 0),
            "archived": counts.get("archived", 0),
            "total": sum(counts.values()),
            "limit_per_account": MAX_PLANS_PER_ACCOUNT,
        },
        "scenes": {"active": int(scenes[0] or 0), "limit_per_plan": MAX_SCENES_PER_PLAN},
        **_boundary(),
    }


def _references_listing(conn: Any, *, account_id: str) -> dict[str, Any]:
    projects = conn.execute(
        "SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100",
        (account_id,),
    ).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in projects],
        **_boundary(),
    }


def _scene_versions(conn: Any, *, scene_id: str, account_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_video_scene_versions WHERE scene_id=? AND account_id=? ORDER BY revision DESC LIMIT 20",
        (scene_id, account_id),
    ).fetchall()
    return [_scene_version_public(row) for row in rows]


def _plan_detail(conn: Any, *, plan_id: str, account_id: str) -> dict[str, Any] | None:
    plan = _plan_row(conn, plan_id=plan_id, account_id=account_id)
    if not plan:
        return None
    scene_count = conn.execute(
        "SELECT COUNT(*) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
        (plan_id, account_id),
    ).fetchone()
    versions = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_video_plan_versions WHERE plan_id=? AND account_id=? ORDER BY revision DESC LIMIT ?",
        (plan_id, account_id, MAX_VERSIONS_PER_ENTITY),
    ).fetchall()
    scenes = conn.execute(
        """SELECT id, plan_id, ordinal, title, scene_type, duration_seconds, visual_direction, narration,
                  on_screen_text, shot_notes, transition, tags_json, state, revision, created_at, updated_at, archived_at
           FROM web_video_scenes WHERE plan_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, updated_at DESC, id DESC LIMIT ?""",
        (plan_id, account_id, MAX_SCENES_PER_PLAN),
    ).fetchall()
    events = conn.execute(
        "SELECT action, entity_type, scene_id, revision, created_at FROM web_video_studio_events WHERE plan_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
        (plan_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    references = _project_reference(conn, account_id=account_id, project_id=str(plan[1]) if plan[1] else None, active=False)
    return {
        "plan": _plan_public(plan, scene_count=int(scene_count[0] or 0), include_content=True),
        "versions": [_plan_version_public(row) for row in versions],
        "scenes": [
            _scene_public(row, include_content=True, versions=_scene_versions(conn, scene_id=str(row[0]), account_id=account_id))
            for row in scenes
        ],
        "events": [
            {
                "action": str(row[0]),
                "entity_type": str(row[1]),
                "scene_id": str(row[2]) if row[2] else None,
                "revision": int(row[3]),
                "created_at": str(row[4]),
            }
            for row in events
        ],
        "references": references,
        **_boundary(),
    }


def _estimate(conn: Any, *, plan: tuple[Any, ...], account_id: str) -> dict[str, Any]:
    if str(plan[11]) == "archived":
        return _plan_archived()
    scenes = conn.execute(
        "SELECT id, ordinal, title, scene_type, duration_seconds FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC",
        (str(plan[0]), account_id),
    ).fetchall()
    total = sum(max(0, int(row[4] or 0)) for row in scenes)
    target = int(plan[6])
    return envelope(
        True,
        "Đã tính runtime estimate cục bộ cho plan.",
        data={
            "plan_id": str(plan[0]),
            "target_duration_seconds": target,
            "scene_duration_seconds": total,
            "difference_seconds": total - target,
            "scene_count": len(scenes),
            "items": [
                {
                    "scene_id": str(row[0]),
                    "ordinal": int(row[1]),
                    "title": str(row[2]),
                    "scene_type": str(row[3]),
                    "duration_seconds": int(row[4]),
                }
                for row in scenes
            ],
            "notice": "Estimate chỉ dùng để review nhịp cảnh; không phải render, preview hoặc kết quả media.",
            **_boundary(),
        },
        status_name="completed",
    )


@router.get("/summary")
async def video_studio_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Video Production Studio đã sẵn sàng cho authoring Web-native.", data=data, status_name="completed")


@router.get("/policy")
async def video_studio_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Boundary Video Production Studio đã được công bố.",
        data={
            **_boundary(),
            "render": "guarded",
            "media_generation": "guarded",
            "delivery": "guarded",
            "self_review": "metadata_only",
        },
        status_name="read_only",
    )


@router.get("/references")
async def video_studio_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _references_listing(conn, account_id=str(account["id"]))
    return envelope(True, "Đã nạp Project reference thuộc Web account hiện tại.", data=data, status_name="completed")


@router.get("/plans")
async def list_plans(
    q: str = "",
    state: str = "all",
    limit: int = 100,
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    query = _line(q, label="Từ khoá", minimum=0, maximum=100, allow_empty=True)
    state_value = str(state or "all").strip().lower()
    if state_value not in {"all", *PLAN_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    bounded = max(1, min(MAX_LIST_LIMIT, int(limit)))
    where = ["p.account_id=?"]
    params: list[Any] = [str(account["id"])]
    if state_value != "all":
        where.append("p.lifecycle=?")
        params.append(state_value)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(p.title LIKE ? ESCAPE '\\' OR p.objective LIKE ? ESCAPE '\\' OR p.brief LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"])
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT p.id, p.project_id, p.title, p.video_format, p.language, p.aspect_ratio, p.target_duration_seconds,
                       p.objective, p.audience, p.brief, p.tags_json, p.lifecycle, p.revision, p.created_at, p.updated_at, p.archived_at,
                       (SELECT COUNT(*) FROM web_video_scenes s WHERE s.plan_id=p.id AND s.account_id=p.account_id AND s.state='active')
                FROM web_video_plans p WHERE {' AND '.join(where)}
                ORDER BY CASE p.lifecycle WHEN 'draft' THEN 0 WHEN 'review' THEN 1 WHEN 'approved' THEN 2 ELSE 3 END,
                         p.updated_at DESC, p.id DESC LIMIT ?""",
            (*params, bounded),
        ).fetchall()
    items = [_plan_public(tuple(row[:16]), scene_count=int(row[16] or 0)) for row in rows]
    return envelope(True, "Đã nạp video plan riêng tư.", data={"items": items, "limit": bounded, **_boundary()}, status_name="completed")


@router.post("/plans")
async def create_plan(payload: PlanCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-create", **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute("SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(False, "Video Production Studio đã đạt giới hạn plan đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_PLAN_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=payload.project_id, active=True)
        plan_id = str(uuid.uuid4())
        now = utc_now()
        snapshot = _plan_snapshot(payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)
        _audit(conn, request=request, account=account, action="web.video.plan.create", target=plan_id, detail=f"format={payload.format};revision=1")
        row = _plan_row(conn, plan_id=plan_id, account_id=account_id)
        return envelope(True, "Đã tạo video plan Web-native.", data={"plan": _plan_public(row) if row else {}, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        detail = _plan_detail(conn, plan_id=resolved, account_id=str(account["id"]))
    return envelope(True, "Đã nạp video plan riêng tư.", data=detail, status_name="completed") if detail else _plan_not_found()


@router.patch("/plans/{plan_id}")
async def update_plan(plan_id: str, payload: PlanUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-update", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not existing:
            return _plan_not_found()
        blocked = _plan_writable(existing)
        if blocked:
            return blocked
        if int(existing[12]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=payload.project_id, active=True)
        now = utc_now()
        lifecycle = "draft" if str(existing[11]) == "review" else str(existing[11])
        snapshot = _plan_snapshot(payload, lifecycle=lifecycle)
        revision = int(existing[12]) + 1
        _write_plan(conn, plan_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_plan_version(conn, plan_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=resolved, action="plan_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.video.plan.update", target=resolved, detail=f"revision={revision};state={lifecycle}")
        row = _plan_row(conn, plan_id=resolved, account_id=account_id)
        return envelope(True, "Đã lưu revision video plan mới.", data={"plan": _plan_public(row) if row else {}, "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _allowed_transition(current: str, target: str) -> bool:
    allowed = {
        "draft": {"review", "archived"},
        "review": {"draft", "approved", "archived"},
        "approved": {"draft", "archived"},
        "archived": {"draft"},
    }
    return target in allowed.get(current, set())


@router.post("/plans/{plan_id}/lifecycle")
async def set_plan_lifecycle(plan_id: str, payload: LifecycleRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-lifecycle", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not existing:
            return _plan_not_found()
        if int(existing[12]) != payload.expected_revision:
            return _revision_conflict()
        current = str(existing[11])
        if not _allowed_transition(current, payload.state):
            return envelope(False, "Chuyển trạng thái self-review này không hợp lệ.", status_name="guarded", error_code="WEB_VIDEO_LIFECYCLE_GUARD")
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        snapshot = _plan_snapshot_from_row(existing, lifecycle=payload.state)
        now = utc_now()
        revision = int(existing[12]) + 1
        _write_plan(conn, plan_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=now if payload.state == "archived" else None)
        _insert_plan_version(conn, plan_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=resolved, action="plan_state_changed", revision=revision)
        _audit(conn, request=request, account=account, action="web.video.plan.lifecycle", target=resolved, detail=f"{current}->{payload.state};revision={revision}")
        row = _plan_row(conn, plan_id=resolved, account_id=account_id)
        return envelope(True, "Đã cập nhật trạng thái self-review.", data={"plan": _plan_public(row) if row else {}, "history_snapshot_recorded": True, **_boundary()}, status_name=payload.state)

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:lifecycle:{payload.state}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/plans/{plan_id}/restore-version")
async def restore_plan_version(plan_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-restore-version", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not existing:
            return _plan_not_found()
        blocked = _plan_writable(existing)
        if blocked:
            return blocked
        if int(existing[12]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        source = conn.execute(
            "SELECT snapshot_json FROM web_video_plan_versions WHERE plan_id=? AND account_id=? AND revision=?",
            (resolved, account_id, payload.target_revision),
        ).fetchone()
        if not source:
            return envelope(False, "Không tìm thấy version video plan cần khôi phục.", status_name="guarded", error_code="WEB_VIDEO_VERSION_NOT_FOUND")
        try:
            saved = json.loads(str(source[0]))
            restored = _plan_payload_from_snapshot(saved if isinstance(saved, dict) else {})
        except (TypeError, ValueError, json.JSONDecodeError):
            return envelope(False, "Version video plan không hợp lệ.", status_name="guarded", error_code="WEB_VIDEO_VERSION_INVALID")
        _project_reference(conn, account_id=account_id, project_id=restored.project_id, active=True)
        snapshot = _plan_snapshot(restored, lifecycle="draft")
        now = utc_now()
        revision = int(existing[12]) + 1
        _write_plan(conn, plan_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_plan_version(conn, plan_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=resolved, action="plan_version_restored", revision=revision)
        _audit(conn, request=request, account=account, action="web.video.plan.restore_version", target=resolved, detail=f"source={payload.target_revision};revision={revision}")
        row = _plan_row(conn, plan_id=resolved, account_id=account_id)
        return envelope(True, "Đã khôi phục version video plan thành revision mới.", data={"plan": _plan_public(row) if row else {}, "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:restore-version:{payload.target_revision}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/plans/{plan_id}/scenes")
async def create_scene(plan_id: str, payload: SceneCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "scene-create", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        if int(plan[12]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
            (resolved, account_id),
        ).fetchone()
        if int(count[0] or 0) >= MAX_SCENES_PER_PLAN:
            return envelope(False, "Video plan đã đạt giới hạn scene đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_SCENE_LIMIT")
        scene_id = str(uuid.uuid4())
        now = utc_now()
        snapshot = _scene_snapshot(payload)
        _insert_scene(
            conn,
            scene_id=scene_id,
            plan_id=resolved,
            account_id=account_id,
            ordinal=_next_active_ordinal(conn, plan_id=resolved, account_id=account_id),
            snapshot=snapshot,
            revision=1,
            now=now,
        )
        _insert_scene_version(conn, scene_id=scene_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event="scene_created", scene_id=scene_id)
        _audit(conn, request=request, account=account, action="web.video.scene.create", target=scene_id, detail=f"plan={resolved};plan_revision={changed_plan[12]}")
        row = _scene_row(conn, plan_id=resolved, scene_id=scene_id, account_id=account_id)
        return envelope(True, "Đã thêm scene riêng tư vào video plan.", data={"scene": _scene_public(row) if row else {}, "plan": _plan_public(changed_plan), **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:scene:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/plans/{plan_id}/scenes/{scene_id}")
async def update_scene(plan_id: str, scene_id: str, payload: SceneUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved_plan = _uuid(plan_id, label="Video plan ID")
    resolved_scene = _uuid(scene_id, label="Scene ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "scene-update", "plan_id": resolved_plan, "scene_id": resolved_scene, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved_plan, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        scene = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        if not scene:
            return _scene_not_found()
        if str(scene[12]) != "active":
            return _scene_archived()
        if int(scene[13]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_scene_versions", entity_column="scene_id", entity_id=resolved_scene, account_id=account_id):
            return envelope(False, "Scene đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        now = utc_now()
        snapshot = _scene_snapshot(payload)
        revision = int(scene[13]) + 1
        _write_scene(conn, scene_id=resolved_scene, plan_id=resolved_plan, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_scene_version(conn, scene_id=resolved_scene, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event="scene_updated", scene_id=resolved_scene)
        _audit(conn, request=request, account=account, action="web.video.scene.update", target=resolved_scene, detail=f"plan={resolved_plan};revision={revision}")
        row = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        return envelope(True, "Đã lưu revision scene mới.", data={"scene": _scene_public(row) if row else {}, "plan": _plan_public(changed_plan), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved_plan}:scene:{resolved_scene}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _scene_state_mutation(plan_id: str, scene_id: str, payload: RevisionRequest | RestoreVersionRequest, request: Request, account: dict, *, action: str) -> dict[str, Any]:
    account_id = str(account["id"])
    resolved_plan = _uuid(plan_id, label="Video plan ID")
    resolved_scene = _uuid(scene_id, label="Scene ID")
    source_revision = payload.target_revision if isinstance(payload, RestoreVersionRequest) else None
    fingerprint = _fingerprint(
        {
            "operation": f"scene-{action}",
            "plan_id": resolved_plan,
            "scene_id": resolved_scene,
            "expected_revision": payload.expected_revision,
            "target_revision": source_revision,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved_plan, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        scene = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        if not scene:
            return _scene_not_found()
        if int(scene[13]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_scene_versions", entity_column="scene_id", entity_id=resolved_scene, account_id=account_id):
            return envelope(False, "Scene đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        current = str(scene[12])
        next_ordinal: int | None = None
        if action == "archive":
            if current != "active":
                return _scene_archived()
            snapshot = _scene_snapshot_from_row(scene, state="archived")
            next_ordinal = _next_archived_ordinal(conn, plan_id=resolved_plan, account_id=account_id)
            event = "scene_archived"
        elif action == "restore":
            if current != "archived":
                return envelope(False, "Scene đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_SCENE_ACTIVE")
            count = conn.execute(
                "SELECT COUNT(*) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
                (resolved_plan, account_id),
            ).fetchone()
            if int(count[0] or 0) >= MAX_SCENES_PER_PLAN:
                return envelope(False, "Video plan đã đạt giới hạn scene đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_SCENE_LIMIT")
            snapshot = _scene_snapshot_from_row(scene, state="active")
            next_ordinal = _next_active_ordinal(conn, plan_id=resolved_plan, account_id=account_id)
            event = "scene_restored"
        elif action == "restore-version":
            if current != "active":
                return _scene_archived()
            saved = conn.execute(
                "SELECT snapshot_json FROM web_video_scene_versions WHERE scene_id=? AND account_id=? AND revision=?",
                (resolved_scene, account_id, source_revision),
            ).fetchone()
            if not saved:
                return envelope(False, "Không tìm thấy version scene cần khôi phục.", status_name="guarded", error_code="WEB_VIDEO_VERSION_NOT_FOUND")
            try:
                parsed = json.loads(str(saved[0]))
                restored = _scene_payload_from_snapshot(parsed if isinstance(parsed, dict) else {})
            except (TypeError, ValueError, json.JSONDecodeError):
                return envelope(False, "Version scene không hợp lệ.", status_name="guarded", error_code="WEB_VIDEO_VERSION_INVALID")
            snapshot = _scene_snapshot(restored, state="active")
            event = "scene_version_restored"
        else:
            raise HTTPException(status_code=500, detail="Thao tác scene không hỗ trợ")
        now = utc_now()
        revision = int(scene[13]) + 1
        _write_scene(
            conn,
            scene_id=resolved_scene,
            plan_id=resolved_plan,
            account_id=account_id,
            snapshot=snapshot,
            revision=revision,
            now=now,
            archived_at=now if snapshot["state"] == "archived" else None,
        )
        if next_ordinal is not None:
            conn.execute(
                "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
                (next_ordinal, resolved_scene, resolved_plan, account_id),
            )
        _insert_scene_version(conn, scene_id=resolved_scene, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event=event, scene_id=resolved_scene)
        _audit(conn, request=request, account=account, action=f"web.video.scene.{action}", target=resolved_scene, detail=f"plan={resolved_plan};revision={revision}")
        row = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        return envelope(True, "Đã cập nhật trạng thái scene.", data={"scene": _scene_public(row) if row else {}, "plan": _plan_public(changed_plan), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    suffix = f":{source_revision}" if source_revision else ""
    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved_plan}:scene:{resolved_scene}:{action}{suffix}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/plans/{plan_id}/scenes/{scene_id}/archive")
async def archive_scene(plan_id: str, scene_id: str, payload: RevisionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _scene_state_mutation(plan_id, scene_id, payload, request, account, action="archive")


@router.post("/plans/{plan_id}/scenes/{scene_id}/restore")
async def restore_scene(plan_id: str, scene_id: str, payload: RevisionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _scene_state_mutation(plan_id, scene_id, payload, request, account, action="restore")


@router.post("/plans/{plan_id}/scenes/{scene_id}/restore-version")
async def restore_scene_version(plan_id: str, scene_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _scene_state_mutation(plan_id, scene_id, payload, request, account, action="restore-version")


@router.post("/plans/{plan_id}/scenes/reorder")
async def reorder_scenes(plan_id: str, payload: ReorderRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "scenes-reorder", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        if int(plan[12]) != payload.expected_revision:
            return _revision_conflict()
        rows = conn.execute(
            "SELECT id, ordinal FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC",
            (resolved, account_id),
        ).fetchall()
        current = [str(row[0]) for row in rows]
        proposed = list(payload.scene_ids)
        if len(current) != len(proposed) or set(current) != set(proposed):
            return envelope(False, "Thứ tự scene phải chứa đúng mỗi scene đang hoạt động của plan.", status_name="guarded", error_code="WEB_VIDEO_REORDER_INVALID")
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        now = utc_now()
        # An archived scene is kept for history but must never reserve an
        # active ordinal.  Normalise first so both freshly archived and any
        # older low-ordinal rows cannot collide with the active 1..N order.
        _normalise_archived_ordinals(conn, plan_id=resolved, account_id=account_id)
        # The unique (plan_id, ordinal) constraint requires a temporary,
        # disjoint ordinal range before writing the final one-based sequence.
        for index, scene_id in enumerate(proposed, start=1):
            conn.execute(
                "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
                (REORDER_TEMPORARY_ORDINAL_BASE + index, scene_id, resolved, account_id),
            )
        for index, scene_id in enumerate(proposed, start=1):
            conn.execute(
                "UPDATE web_video_scenes SET ordinal=?, updated_at=? WHERE id=? AND plan_id=? AND account_id=?",
                (index, now, scene_id, resolved, account_id),
            )
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event="scenes_reordered")
        _audit(conn, request=request, account=account, action="web.video.scene.reorder", target=resolved, detail=f"count={len(proposed)};revision={changed_plan[12]}")
        return envelope(True, "Đã cập nhật thứ tự scene.", data={"plan": _plan_public(changed_plan), "scene_count": len(proposed), "reordered": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:scenes:reorder", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/plans/{plan_id}/estimate")
async def plan_estimate(plan_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        plan = _plan_row(conn, plan_id=resolved, account_id=str(account["id"]))
        if not plan:
            return _plan_not_found()
        return _estimate(conn, plan=plan, account_id=str(account["id"]))


@router.get("/events")
async def list_events(limit: int = 50, account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    bounded = max(1, min(MAX_EVENT_LIMIT, int(limit)))
    with read_transaction() as conn:
        rows = conn.execute(
            "SELECT plan_id, scene_id, entity_type, action, revision, created_at FROM web_video_studio_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
            (str(account["id"]), bounded),
        ).fetchall()
    return envelope(
        True,
        "Đã nạp hoạt động Video Production Studio.",
        data={
            "items": [
                {
                    "plan_id": str(row[0]),
                    "scene_id": str(row[1]) if row[1] else None,
                    "entity_type": str(row[2]),
                    "action": str(row[3]),
                    "revision": int(row[4]),
                    "created_at": str(row[5]),
                }
                for row in rows
            ],
            "limit": bounded,
            **_boundary(),
        },
        status_name="completed",
    )
