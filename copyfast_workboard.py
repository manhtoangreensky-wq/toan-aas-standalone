"""Private Web-native Workboard & Review Queue.

This module is deliberately an account-owned coordination surface.  It does
not import the Telegram Bot or its bridge, and it never reaches a provider,
wallet, payment, job, publishing or notification authority.  A card is useful
Web metadata, not evidence that external work has happened.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import sqlite3
import uuid
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now, workboard_enabled


router = APIRouter(prefix="/api/v1/workboard", tags=["Web Workboard"])

ITEM_STATES = frozenset({"backlog", "planned", "in_progress", "review", "done", "archived"})
ACTIVE_ITEM_STATES = frozenset(ITEM_STATES - {"archived"})
PRIORITIES = frozenset({"low", "normal", "high", "urgent"})
REFERENCE_TYPES = frozenset({"project", "campaign", "analytics", "note", "draft"})
REFERENCE_ALIASES = {
    "project": "project",
    "campaign": "campaign",
    "campaign_plan": "campaign",
    "analytics": "analytics",
    "analytics_report": "analytics",
    "note": "note",
    "memory_note": "note",
    "draft": "draft",
    "workspace_draft": "draft",
}
# Kanban cards may be deliberately re-prioritized between lanes.  The server
# still validates the closed vocabulary and blocks `done` while active
# checklist rows remain incomplete; no transition means publish/job approval.
TRANSITIONS = {state: frozenset(ITEM_STATES) for state in ITEM_STATES}

IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|"
    r"password|passphrase|authorization|otp|cvv|cvc|private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{12}|github_pat_[A-Za-z0-9_]{12}|"
    r"gh[pousr]_[A-Za-z0-9]{12}|xox[bpars]-[A-Za-z0-9-]{12}|AIza[0-9A-Za-z_-]{20}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:txid|transaction\s+(?:hash|id|reference)|mã\s*(?:giao\s*)?(?:dịch|thanh\s*toán)|"
    r"bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|qr\s*(?:code|thanh\s*toán)|"
    r"nạp\s*(?:tiền|xu)|chuyển\s*khoản|manual\s*topup)\b",
    re.IGNORECASE,
)
EXTERNAL_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|render|job|media|asset|file|worker|engine|platform|channel)[ _-]*(?:id|ref(?:erence)?|token|handle)|"
    r"(?:telegram[ _-]*)?bot[ _-]*(?:id|ref(?:erence)?|token|secret|handle))\b\s*(?::|=|\bis\b)\s*\S+",
    re.IGNORECASE,
)
MARKUP_EXECUTION_PATTERN = re.compile(
    r"<\s*/?\s*(?:script|svg|img|iframe|object|embed|style|link|meta|base|form|input|video|audio)\b|\bon[a-z]+\s*=",
    re.IGNORECASE,
)
URL_OR_PATH_PATTERN = re.compile(
    r"(?:\bhttps?://|\bwww\.|\b(?:file|data|javascript|blob):|(?:^|[\s\"'])"
    r"(?:[A-Za-z]:[\\/]|/[^\s]+|\\\\[^\s]+))",
    re.IGNORECASE,
)
FORMULA_PREFIX_PATTERN = re.compile(r"^\s*[=+@]", re.IGNORECASE)
CARD_LIKE_PATTERN = re.compile(r"\b(?:\d[ .\-/]?){13,19}\b")

MAX_ITEMS_PER_ACCOUNT = 500
MAX_CHECKLIST_PER_ITEM = 40
MAX_REFERENCES_PER_ITEM = 8
MAX_LIST_LIMIT = 100
MAX_EVENT_LIMIT = 100
MAX_VERSION_LIMIT = 100
# Page history with a bounded offset.  This deliberately stays separate from
# item/list limits so an old work item can retain a long audit trail without
# turning any client-supplied offset into an unbounded database scan.
MAX_LIST_OFFSET = 10_000
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
ARCHIVED_ORDINAL_BASE = 1_000_000
SCHEDULE_INTENT_STATES = frozenset({"active", "dispatched", "guarded", "cancelled"})
MAX_SCHEDULE_INTENTS_PER_ACCOUNT = 200
MAX_ACTIVE_SCHEDULE_INTENTS_PER_ACCOUNT = 50
MAX_SCHEDULE_INTENTS_PER_ITEM = 20
SCHEDULE_MIN_LEAD_SECONDS = 60
SCHEDULE_MAX_AHEAD = timedelta(days=366)
IANA_TIMEZONE_PATTERN = re.compile(r"^(?:UTC|[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)+)$")
LOCAL_TRIGGER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$")
SNAPSHOT_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_enabled() -> None:
    if not workboard_enabled():
        raise HTTPException(
            status_code=503,
            detail="Workboard & Review Queue đang tạm dừng để bảo trì. WEBAPP_WORKBOARD_ENABLED chưa được bật.",
        )


def _boundary(**extra: Any) -> dict[str, Any]:
    """Expose the exact Web-only contract with every Workboard response."""
    return {
        "execution": "web_native_coordination_only",
        "data_origin": "signed_account_web_records_only",
        "deterministic_local_state": True,
        "bot_called": False,
        "provider_called": False,
        "social_api_called": False,
        "platform_data_connected": False,
        "ai_recommendation_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "payment_processed": False,
        "job_created": False,
        "publish_action_created": False,
        "notification_sent": False,
        "browser_file_upload": False,
        "external_url_import": False,
        "output_delivery": "not_applicable",
        **extra,
    }


def _guarded(message: str, code: str, *, status_name: str = "guarded") -> dict[str, Any]:
    return envelope(False, message, data=_boundary(), status_name=status_name, error_code=code)


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


def _sensitive_text(value: str) -> bool:
    return bool(
        SECRET_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or PAYMENT_PATTERN.search(value)
        or EXTERNAL_HANDLE_PATTERN.search(value)
        or MARKUP_EXECUTION_PATTERN.search(value)
        or URL_OR_PATH_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or "-----begin" in value.lower()
    )


def _line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and (FORMULA_PREFIX_PATTERN.search(text) or _sensitive_text(text)):
        raise ValueError(f"{label} không nhận công thức, secret, URL/đường dẫn, Bot/provider hoặc chứng từ thanh toán")
    return text


def _body(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum:,} ký tự hợp lệ".replace(",", "."))
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận secret, URL/đường dẫn, Bot/provider hoặc chứng từ thanh toán")
    return text


def _due_at(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip()
    if len(raw) > 32 or raw.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", raw):
        raise ValueError("Hạn xử lý phải là thời điểm cục bộ YYYY-MM-DDTHH:MM, không kèm timezone")
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Hạn xử lý phải có dạng YYYY-MM-DDTHH:MM") from exc
    if parsed.tzinfo is not None or parsed.microsecond:
        raise ValueError("Hạn xử lý phải là thời điểm cục bộ YYYY-MM-DDTHH:MM")
    return parsed.replace(second=0).isoformat(timespec="minutes")


def _schedule_trigger(value: Any, timezone_name: Any) -> tuple[str, str, str]:
    """Validate an owner-selected IANA wall time without guessing DST.

    A ``datetime-local`` value has no offset.  We intentionally reject both
    ambiguous and nonexistent local times instead of silently choosing a
    ``fold`` or shifting the reminder.  The returned trigger is normalized to
    a UTC ISO timestamp while retaining the declared IANA zone for review.
    """
    local = str(value or "").strip()
    zone_name = str(timezone_name or "").strip()
    if len(local) > 32 or not LOCAL_TRIGGER_PATTERN.fullmatch(local):
        raise ValueError("Thời điểm nhắc cần có dạng YYYY-MM-DDTHH:MM theo giờ địa phương")
    if len(zone_name) > 64 or not IANA_TIMEZONE_PATTERN.fullmatch(zone_name) or ".." in zone_name:
        raise ValueError("Timezone cần là IANA hợp lệ, ví dụ Asia/Ho_Chi_Minh")
    try:
        local_naive = datetime.fromisoformat(local)
    except (TypeError, ValueError) as exc:
        raise ValueError("Thời điểm nhắc không hợp lệ") from exc
    if local_naive.tzinfo is not None or local_naive.microsecond:
        raise ValueError("Thời điểm nhắc phải là giờ địa phương không kèm timezone")
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Timezone IANA chưa được máy chủ hỗ trợ") from exc
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = local_naive.replace(tzinfo=zone, fold=fold)
        round_trip = candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
        if round_trip == local_naive:
            candidates.append(candidate)
    offsets = {candidate.utcoffset() for candidate in candidates}
    if not candidates:
        raise ValueError("Thời điểm này không tồn tại trong timezone đã chọn; hãy chọn giờ khác")
    if len(offsets) > 1:
        raise ValueError("Thời điểm này bị trùng khi đổi giờ mùa hè; hãy chọn giờ khác")
    trigger = candidates[0].astimezone(timezone.utc).replace(microsecond=0)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if trigger <= now + timedelta(seconds=SCHEDULE_MIN_LEAD_SECONDS):
        raise ValueError("Thời điểm nhắc cần cách hiện tại ít nhất 1 phút")
    if trigger > now + SCHEDULE_MAX_AHEAD:
        raise ValueError("Thời điểm nhắc chỉ được đặt tối đa 366 ngày")
    return (
        local_naive.replace(microsecond=0).isoformat(timespec="seconds"),
        zone.key,
        trigger.isoformat(timespec="seconds"),
    )


def _reference_type(value: Any) -> str:
    normalized = _line(value, label="Loại reference", minimum=2, maximum=32).lower()
    resolved = REFERENCE_ALIASES.get(normalized)
    if resolved not in REFERENCE_TYPES:
        raise ValueError("Loại reference Workboard chưa được hỗ trợ")
    return resolved


def _query_text(value: str | None) -> str:
    if value is None:
        return ""
    return _line(value, label="Từ khóa tìm kiếm", minimum=0, maximum=120, allow_empty=True)


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


class ReferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_type: str
    ref_id: str

    @field_validator("ref_type")
    @classmethod
    def _type(cls, value: str) -> str:
        return _reference_type(value)

    @field_validator("ref_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return _uuid(value, label="Reference ID")


class ChecklistInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str
    is_done: bool = False

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return _line(value, label="Checklist", minimum=2, maximum=360)


class ItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str = ""
    priority: str = "normal"
    due_at: str | None = None
    references: list[ReferenceInput] = Field(default_factory=list)
    checklist: list[ChecklistInput] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên công việc", minimum=3, maximum=180)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return _body(value, label="Mô tả công việc", maximum=5_000, allow_empty=True)

    @field_validator("priority")
    @classmethod
    def _priority(cls, value: str) -> str:
        normalized = _line(value, label="Ưu tiên", minimum=2, maximum=16).lower()
        if normalized not in PRIORITIES:
            raise ValueError("Ưu tiên Workboard không hợp lệ")
        return normalized

    @field_validator("due_at")
    @classmethod
    def _due(cls, value: str | None) -> str | None:
        return _due_at(value)

    @field_validator("references")
    @classmethod
    def _references(cls, value: list[ReferenceInput]) -> list[ReferenceInput]:
        if len(value) > MAX_REFERENCES_PER_ITEM:
            raise ValueError(f"Tối đa {MAX_REFERENCES_PER_ITEM} reference cho mỗi work item")
        seen: set[tuple[str, str]] = set()
        for item in value:
            marker = (item.ref_type, item.ref_id)
            if marker in seen:
                raise ValueError("Reference Workboard bị lặp")
            seen.add(marker)
        return value

    @field_validator("checklist")
    @classmethod
    def _checklist(cls, value: list[ChecklistInput]) -> list[ChecklistInput]:
        if len(value) > MAX_CHECKLIST_PER_ITEM:
            raise ValueError(f"Tối đa {MAX_CHECKLIST_PER_ITEM} checklist cho mỗi work item")
        return value


class ItemCreateRequest(ItemPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    priority: str | None = None
    due_at: str | None = None
    references: list[ReferenceInput] | None = None
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        return _line(value, label="Tên công việc", minimum=3, maximum=180) if value is not None else None

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return _body(value, label="Mô tả công việc", maximum=5_000, allow_empty=True) if value is not None else None

    @field_validator("priority")
    @classmethod
    def _priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _line(value, label="Ưu tiên", minimum=2, maximum=16).lower()
        if normalized not in PRIORITIES:
            raise ValueError("Ưu tiên Workboard không hợp lệ")
        return normalized

    @field_validator("due_at")
    @classmethod
    def _due(cls, value: str | None) -> str | None:
        return _due_at(value)

    @field_validator("references")
    @classmethod
    def _references(cls, value: list[ReferenceInput] | None) -> list[ReferenceInput] | None:
        if value is None:
            return None
        return ItemPayload._references(value)

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)

    @model_validator(mode="after")
    def _changed(self) -> "ItemUpdateRequest":
        if not ({"title", "description", "priority", "due_at", "references"} & self.model_fields_set):
            raise ValueError("Cần có ít nhất một trường Workboard để cập nhật")
        return self


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ScheduleIntentCreateRequest(BaseModel):
    """An explicit owner opt-in for one private, future Inbox record."""

    model_config = ConfigDict(extra="forbid")

    trigger_local_at: str = Field(min_length=16, max_length=32)
    timezone: str = Field(min_length=1, max_length=64)
    expected_item_revision: int = Field(ge=1, le=1_000_000)
    opt_in: bool = False
    confirm: bool = False
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ScheduleIntentCancelRequest(RevisionRequest):
    confirm: bool = False


class ScheduleIntentReconfirmRequest(RevisionRequest):
    expected_item_revision: int = Field(ge=1, le=1_000_000)
    confirm: bool = False


class ItemStateRequest(RevisionRequest):
    state: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái Workboard", minimum=2, maximum=24).lower()
        if normalized not in ITEM_STATES:
            raise ValueError("Trạng thái Workboard không hợp lệ")
        return normalized


class ChecklistCreateRequest(RevisionRequest):
    body: str
    is_done: bool = False

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return _line(value, label="Checklist", minimum=2, maximum=360)


class ChecklistUpdateRequest(RevisionRequest):
    body: str | None = None
    is_done: bool | None = None
    expected_checklist_revision: int = Field(ge=1)

    @field_validator("body")
    @classmethod
    def _body(cls, value: str | None) -> str | None:
        return _line(value, label="Checklist", minimum=2, maximum=360) if value is not None else None

    @model_validator(mode="after")
    def _changed(self) -> "ChecklistUpdateRequest":
        if not ({"body", "is_done"} & self.model_fields_set):
            raise ValueError("Cần có nội dung hoặc trạng thái checklist để cập nhật")
        return self


def _item_row(conn: Any, *, item_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, account_id, title, description, priority, due_at, state, revision,
                  created_at, updated_at, archived_at
           FROM web_workboard_items WHERE id=? AND account_id=?""",
        (item_id, account_id),
    ).fetchone()


def _schedule_actor_allowed(account: dict[str, Any]) -> bool:
    """Use only the server-resolved signed-account role, never browser input."""
    return bool(str(account.get("id") or "").strip()) and str(account.get("role") or "user").strip().lower() in {"user", "admin"}


def _snapshot_hash(value: Any) -> str | None:
    """Hash a semantic item snapshot without retaining its private body."""
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    canonical = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _schedule_source_snapshot(conn: Any, *, item: tuple[Any, ...], account_id: str) -> tuple[int, str] | None:
    """Return immutable source coordinates only when the current revision exists."""
    if str(item[6]) == "archived":
        return None
    revision = int(item[7])
    row = conn.execute(
        """SELECT snapshot_json FROM web_workboard_item_versions
           WHERE item_id=? AND account_id=? AND revision=?""",
        (str(item[0]), account_id, revision),
    ).fetchone()
    snapshot_hash = _snapshot_hash(row[0]) if row else None
    return (revision, snapshot_hash) if snapshot_hash and SNAPSHOT_HASH_PATTERN.fullmatch(snapshot_hash) else None


def _schedule_intent_row(conn: Any, *, intent_id: str, item_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, account_id, item_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                  trigger_at, state, revision, created_at, updated_at, dispatched_at, guarded_at, guard_code,
                  cancelled_at, created_by_account_id
           FROM web_workboard_schedule_intents
           WHERE id=? AND item_id=? AND account_id=?""",
        (intent_id, item_id, account_id),
    ).fetchone()


def _schedule_intent_public(row: tuple[Any, ...]) -> dict[str, Any]:
    """Return review metadata, never the hashed snapshot or source content."""
    state = str(row[8])
    return {
        "id": str(row[0]), "item_id": str(row[2]), "source_revision": int(row[3]),
        "trigger_local_at": str(row[5]), "timezone": str(row[6]), "trigger_at": str(row[7]),
        "state": state, "revision": int(row[9]), "created_at": str(row[10]), "updated_at": str(row[11]),
        "dispatched_at": str(row[12]) if row[12] else None,
        "guarded_at": str(row[13]) if row[13] else None,
        "guard_code": str(row[14]) if row[14] else None,
        "cancelled_at": str(row[15]) if row[15] else None,
        "reconfirmation_required": state == "guarded",
        "delivery": "in_app_record_only",
    }


def _checklist_rows(conn: Any, *, item_id: str, account_id: str, include_archived: bool = False) -> list[tuple[Any, ...]]:
    predicate = "" if include_archived else "AND state='active'"
    return conn.execute(
        f"""SELECT id, item_id, ordinal, body, is_done, state, revision, completed_at,
                   created_at, updated_at, archived_at
            FROM web_workboard_checklist_items
            WHERE item_id=? AND account_id=? {predicate}
            ORDER BY ordinal ASC, created_at ASC, id ASC""",
        (item_id, account_id),
    ).fetchall()


def _reference_rows(conn: Any, *, item_id: str, account_id: str) -> list[tuple[Any, ...]]:
    return conn.execute(
        """SELECT ref_type, ref_id, ordinal FROM web_workboard_item_references
           WHERE item_id=? AND account_id=? ORDER BY ordinal ASC, id ASC""",
        (item_id, account_id),
    ).fetchall()


def _references_public(rows: list[tuple[Any, ...]]) -> list[dict[str, str]]:
    return [{"ref_type": str(row[0]), "ref_id": str(row[1])} for row in rows]


def _checklist_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]), "item_id": str(row[1]), "ordinal": int(row[2]),
        "body": str(row[3]), "is_done": bool(row[4]), "state": str(row[5]),
        "revision": int(row[6]), "completed_at": str(row[7]) if row[7] else None,
        "created_at": str(row[8]), "updated_at": str(row[9]),
        "archived_at": str(row[10]) if row[10] else None,
    }


def _item_public(
    row: tuple[Any, ...],
    *,
    references: list[dict[str, str]] | None = None,
    checklist_total: int = 0,
    checklist_done: int = 0,
    include_description: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(row[0]), "title": str(row[2]), "priority": str(row[4]),
        "due_at": str(row[5]) if row[5] else None, "state": str(row[6]),
        "revision": int(row[7]), "created_at": str(row[8]), "updated_at": str(row[9]),
        "archived_at": str(row[10]) if row[10] else None,
        "checklist_total": int(checklist_total), "checklist_done": int(checklist_done),
    }
    if include_description:
        result["description"] = str(row[3])
    else:
        compact = re.sub(r"\s+", " ", str(row[3] or "")).strip()
        result["description_excerpt"] = compact[:240] + ("…" if len(compact) > 240 else "")
    if references is not None:
        result["references"] = references
    return result


def _snapshot_from_rows(
    item: tuple[Any, ...],
    checklist: list[tuple[Any, ...]],
    references: list[tuple[Any, ...]],
) -> dict[str, Any]:
    return {
        "title": str(item[2]), "description": str(item[3]), "priority": str(item[4]),
        "due_at": str(item[5]) if item[5] else None, "state": str(item[6]),
        "references": _references_public(references),
        "checklist": [
            {"ordinal": int(row[2]), "body": str(row[3]), "is_done": bool(row[4]), "state": str(row[5])}
            for row in checklist
        ],
        "restore_scope": "item_metadata_and_checklist_only",
    }


def _insert_item_version(
    conn: Any,
    *,
    item: tuple[Any, ...],
    account_id: str,
    checklist: list[tuple[Any, ...]] | None = None,
    references: list[tuple[Any, ...]] | None = None,
) -> None:
    checklist = checklist if checklist is not None else _checklist_rows(conn, item_id=str(item[0]), account_id=account_id, include_archived=True)
    references = references if references is not None else _reference_rows(conn, item_id=str(item[0]), account_id=account_id)
    snapshot = _snapshot_from_rows(item, checklist, references)
    conn.execute(
        """INSERT INTO web_workboard_item_versions (id, item_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), str(item[0]), account_id, int(item[7]), json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), utc_now()),
    )
    old = conn.execute(
        """SELECT id FROM web_workboard_item_versions WHERE item_id=? AND account_id=?
           ORDER BY revision DESC, created_at DESC LIMIT -1 OFFSET ?""",
        (str(item[0]), account_id, MAX_VERSION_LIMIT),
    ).fetchall()
    if old:
        conn.executemany("DELETE FROM web_workboard_item_versions WHERE id=?", [(str(row[0]),) for row in old])


def _insert_checklist_version(conn: Any, *, row: tuple[Any, ...], account_id: str) -> None:
    snapshot = {
        "ordinal": int(row[2]), "body": str(row[3]), "is_done": bool(row[4]),
        "state": str(row[5]), "completed_at": str(row[7]) if row[7] else None,
    }
    conn.execute(
        """INSERT INTO web_workboard_checklist_versions
           (id, checklist_id, item_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), str(row[0]), str(row[1]), account_id, int(row[6]), json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), utc_now()),
    )


def _event(
    conn: Any,
    *,
    account_id: str,
    item_id: str,
    entity_type: str,
    action: str,
    item_revision: int,
    entity_id: str | None = None,
    entity_revision: int | None = None,
) -> None:
    conn.execute(
        """INSERT INTO web_workboard_events
           (id, account_id, item_id, entity_type, entity_id, action, item_revision, entity_revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, item_id, entity_type, entity_id, action, item_revision, entity_revision, utc_now()),
    )
    stale = conn.execute(
        """SELECT id FROM web_workboard_events WHERE item_id=? AND account_id=?
           ORDER BY created_at DESC, id DESC LIMIT -1 OFFSET 500""",
        (item_id, account_id),
    ).fetchall()
    if stale:
        conn.executemany("DELETE FROM web_workboard_events WHERE id=?", [(str(row[0]),) for row in stale])


def _source_table(reference_type: str) -> tuple[str, str, str]:
    mapping = {
        "project": ("web_projects", "state", "active"),
        "campaign": ("web_campaign_plans", "approval_status", ""),
        "analytics": ("web_analytics_reports", "state", "archived"),
        "note": ("web_memory_notes", "state", "active"),
        "draft": ("web_workspace_drafts", "state", "active"),
    }
    return mapping[reference_type]


def _validate_reference(conn: Any, *, reference: ReferenceInput, account_id: str) -> bool:
    table, state_column, state_value = _source_table(reference.ref_type)
    if reference.ref_type == "analytics":
        row = conn.execute(
            f"SELECT id FROM {table} WHERE id=? AND account_id=? AND {state_column}!=?",
            (reference.ref_id, account_id, state_value),
        ).fetchone()
    elif state_value:
        row = conn.execute(
            f"SELECT id FROM {table} WHERE id=? AND account_id=? AND {state_column}=?",
            (reference.ref_id, account_id, state_value),
        ).fetchone()
    else:
        row = conn.execute(f"SELECT id FROM {table} WHERE id=? AND account_id=?", (reference.ref_id, account_id)).fetchone()
    return bool(row)


def _references_are_owned(conn: Any, *, account_id: str, references: list[ReferenceInput]) -> bool:
    return all(_validate_reference(conn, reference=reference, account_id=account_id) for reference in references)


def _write_references(conn: Any, *, item_id: str, account_id: str, references: list[ReferenceInput]) -> None:
    """Replace the current relation set after caller owner-validation.

    Immutable item snapshots retain every former relation, so replacing this
    compact current projection does not erase recoverable card history.
    """
    conn.execute("DELETE FROM web_workboard_item_references WHERE item_id=? AND account_id=?", (item_id, account_id))
    now = utc_now()
    for ordinal, reference in enumerate(references, start=1):
        conn.execute(
            """INSERT INTO web_workboard_item_references (id, item_id, account_id, ref_type, ref_id, ordinal, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), item_id, account_id, reference.ref_type, reference.ref_id, ordinal, now),
        )


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Persist a replay-safe receipt without authoring text or reference labels."""
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary()
    item = source.get("item")
    if isinstance(item, dict) and isinstance(item.get("id"), str):
        data["item"] = {
            "id": str(item["id"]), "revision": int(item.get("revision") or 0),
            "state": str(item.get("state") or ""),
        }
    checklist = source.get("checklist")
    if isinstance(checklist, dict) and isinstance(checklist.get("id"), str):
        data["checklist"] = {
            "id": str(checklist["id"]), "item_id": str(checklist.get("item_id") or ""),
            "revision": int(checklist.get("revision") or 0), "state": str(checklist.get("state") or ""),
        }
    schedule_intent = source.get("schedule_intent")
    if isinstance(schedule_intent, dict) and isinstance(schedule_intent.get("id"), str):
        # Replay receipts retain no source title/body/snapshot.  The signed
        # owner must re-read the item route to review the current card.
        data["schedule_intent"] = {
            "id": str(schedule_intent["id"]),
            "item_id": str(schedule_intent.get("item_id") or ""),
            "source_revision": int(schedule_intent.get("source_revision") or 0),
            "trigger_at": str(schedule_intent.get("trigger_at") or ""),
            "timezone": str(schedule_intent.get("timezone") or ""),
            "state": str(schedule_intent.get("state") or ""),
            "revision": int(schedule_intent.get("revision") or 0),
            "delivery": "in_app_record_only",
        }
    for key in ("version_recorded", "checklist_total", "checklist_done"):
        if key in source:
            data[key] = source[key]
    return envelope(True, str(response.get("message") or "Đã lưu Workboard."), data=data, status_name=str(response.get("status") or "completed"))


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-workboard:%", _idempotency_cutoff()))
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
                raise HTTPException(status_code=409, detail="Receipt Workboard không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Workboard không hợp lệ")
            return receipt
        count = conn.execute("SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?", (f"web-workboard:{account_id}:%",)).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded("Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_WORKBOARD_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _item_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy work item thuộc Web account hiện tại.", "WEB_WORKBOARD_ITEM_NOT_FOUND")


def _active_item_or_guard(conn: Any, *, item_id: str, account_id: str) -> tuple[Any, ...] | dict[str, Any]:
    item = _item_row(conn, item_id=item_id, account_id=account_id)
    if not item:
        return _item_not_found()
    return item


def _refresh_item(conn: Any, *, item_id: str, account_id: str) -> tuple[Any, ...]:
    row = _item_row(conn, item_id=item_id, account_id=account_id)
    if not row:
        raise RuntimeError("Workboard item disappeared in its own transaction")
    return row


def _item_counts(conn: Any, *, item_id: str, account_id: str) -> tuple[int, int]:
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(CASE WHEN is_done=1 THEN 1 ELSE 0 END), 0)
           FROM web_workboard_checklist_items
           WHERE item_id=? AND account_id=? AND state='active'""",
        (item_id, account_id),
    ).fetchone()
    return int(row[0] or 0), int(row[1] or 0)


def _item_receipt(conn: Any, *, item_id: str, account_id: str, include_description: bool = False) -> dict[str, Any]:
    item = _refresh_item(conn, item_id=item_id, account_id=account_id)
    total, done = _item_counts(conn, item_id=item_id, account_id=account_id)
    references = _references_public(_reference_rows(conn, item_id=item_id, account_id=account_id))
    return _item_public(item, references=references, checklist_total=total, checklist_done=done, include_description=include_description)


def _item_snapshot_for_fingerprint(payload: ItemPayload) -> dict[str, Any]:
    return {
        "title": payload.title, "description": payload.description, "priority": payload.priority, "due_at": payload.due_at,
        "references": [{"ref_type": value.ref_type, "ref_id": value.ref_id} for value in payload.references],
        "checklist": [{"body": value.body, "is_done": value.is_done} for value in payload.checklist],
    }


@router.get("/policy")
async def policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Workboard Web-native chỉ điều phối metadata riêng tư của account hiện tại.",
        data=_boundary(
            enabled=True,
            item_states=sorted(ITEM_STATES), priorities=sorted(PRIORITIES), reference_types=sorted(REFERENCE_TYPES),
            max_references_per_item=MAX_REFERENCES_PER_ITEM, max_checklist_per_item=MAX_CHECKLIST_PER_ITEM,
            schedule_intents={
                "owner_opt_in_required": True,
                "timezone": "iana_required",
                "utc_trigger_normalized": True,
                "source_snapshot_must_match_at_dispatch": True,
                "reconfirmation_required_after_source_change": True,
                "delivery": "in_app_record_only",
                "max_active_per_account": MAX_ACTIVE_SCHEDULE_INTENTS_PER_ACCOUNT,
                "max_active_per_item": MAX_SCHEDULE_INTENTS_PER_ITEM,
            },
        ),
        status_name="read_only",
    )


@router.get("/summary")
async def summary(account: dict = Depends(require_account)):
    _require_enabled()
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT state, COUNT(*) FROM web_workboard_items
               WHERE account_id=? GROUP BY state""",
            (account_id,),
        ).fetchall()
        counts = {state: 0 for state in sorted(ITEM_STATES)}
        for state, count in rows:
            if str(state) in counts:
                counts[str(state)] = int(count or 0)
        checklist = conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(CASE WHEN c.is_done=1 THEN 1 ELSE 0 END), 0)
               FROM web_workboard_checklist_items c
               JOIN web_workboard_items i ON i.id=c.item_id AND i.account_id=c.account_id
               WHERE c.account_id=? AND c.state='active' AND i.state!='archived'""",
            (account_id,),
        ).fetchone()
        now_local = datetime.now().strftime("%Y-%m-%dT%H:%M")
        due = conn.execute(
            """SELECT COUNT(*) FROM web_workboard_items
               WHERE account_id=? AND state NOT IN ('done', 'archived') AND due_at IS NOT NULL AND due_at < ?""",
            (account_id, now_local),
        ).fetchone()
    return envelope(
        True,
        "Tổng quan Workboard của Web account hiện tại.",
        data=_boundary(
            counts=counts,
            active_total=sum(counts[name] for name in ACTIVE_ITEM_STATES),
            overdue=int(due[0] or 0),
            checklist_total=int(checklist[0] or 0),
            checklist_done=int(checklist[1] or 0),
        ),
        status_name="read_only",
    )


@router.get("/references")
async def references(limit: int = 30, account: dict = Depends(require_account)):
    """List small owner-scoped choices; labels are never stored in a card."""
    _require_enabled()
    account_id = str(account["id"])
    bounded = max(1, min(int(limit), 60))
    ensure_copyfast_schema()
    with read_transaction() as conn:
        groups = {
            "project": conn.execute("SELECT id, title FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT ?", (account_id, bounded)).fetchall(),
            "campaign": conn.execute("SELECT id, title FROM web_campaign_plans WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ?", (account_id, bounded)).fetchall(),
            "analytics": conn.execute("SELECT id, title FROM web_analytics_reports WHERE account_id=? AND state!='archived' ORDER BY updated_at DESC, id DESC LIMIT ?", (account_id, bounded)).fetchall(),
            "note": conn.execute("SELECT id, title FROM web_memory_notes WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT ?", (account_id, bounded)).fetchall(),
            "draft": conn.execute("SELECT id, title FROM web_workspace_drafts WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT ?", (account_id, bounded)).fetchall(),
        }
    data = {
        ref_type: [{"ref_type": ref_type, "ref_id": str(row[0]), "label": str(row[1])[:180]} for row in rows]
        for ref_type, rows in groups.items()
    }
    return envelope(True, "Reference Web-owned có thể liên kết vào Workboard.", data=_boundary(references=data), status_name="read_only")


@router.get("/items")
async def list_items(
    state: str | None = None,
    priority: str | None = None,
    ref_type: str | None = None,
    ref_id: str | None = None,
    q: str | None = None,
    include_archived: bool = False,
    limit: int = 30,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    _require_enabled()
    account_id = str(account["id"])
    bounded_limit = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = max(0, min(int(offset), 10_000))
    requested_state = _line(state, label="Trạng thái lọc", minimum=2, maximum=24).lower() if state else ""
    if requested_state and requested_state not in ITEM_STATES:
        raise HTTPException(status_code=422, detail="Trạng thái lọc Workboard không hợp lệ")
    requested_priority = _line(priority, label="Ưu tiên lọc", minimum=2, maximum=16).lower() if priority else ""
    if requested_priority and requested_priority not in PRIORITIES:
        raise HTTPException(status_code=422, detail="Ưu tiên lọc Workboard không hợp lệ")
    requested_ref_type = _reference_type(ref_type) if ref_type else ""
    requested_ref_id = _uuid(ref_id, label="Reference ID lọc") if ref_id else ""
    if bool(requested_ref_type) != bool(requested_ref_id):
        raise HTTPException(status_code=422, detail="Lọc reference cần đủ loại và ID")
    needle = _query_text(q)
    where = ["i.account_id=?"]
    params: list[Any] = [account_id]
    if not include_archived and not requested_state:
        where.append("i.state!='archived'")
    if requested_state:
        where.append("i.state=?")
        params.append(requested_state)
    if requested_priority:
        where.append("i.priority=?")
        params.append(requested_priority)
    if needle:
        where.append("(i.title LIKE ? ESCAPE '\\' OR i.description LIKE ? ESCAPE '\\')")
        escaped = "".join("\\" + character if character in {"%", "_", "\\"} else character for character in needle)
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    if requested_ref_type:
        where.append("EXISTS (SELECT 1 FROM web_workboard_item_references r WHERE r.item_id=i.id AND r.account_id=i.account_id AND r.ref_type=? AND r.ref_id=?)")
        params.extend([requested_ref_type, requested_ref_id])
    predicate = " AND ".join(where)
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT i.id, i.account_id, i.title, i.description, i.priority, i.due_at, i.state, i.revision,
                       i.created_at, i.updated_at, i.archived_at,
                       COUNT(c.id) AS checklist_total,
                       COALESCE(SUM(CASE WHEN c.is_done=1 THEN 1 ELSE 0 END), 0) AS checklist_done
                FROM web_workboard_items i
                LEFT JOIN web_workboard_checklist_items c
                  ON c.item_id=i.id AND c.account_id=i.account_id AND c.state='active'
                WHERE {predicate}
                GROUP BY i.id
                ORDER BY CASE i.state WHEN 'in_progress' THEN 0 WHEN 'review' THEN 1 WHEN 'planned' THEN 2 WHEN 'backlog' THEN 3 WHEN 'done' THEN 4 ELSE 5 END,
                         CASE i.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                         CASE WHEN i.due_at IS NULL THEN 1 ELSE 0 END, i.due_at ASC, i.updated_at DESC, i.id DESC
                LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
        page_rows = rows[:bounded_limit]
        item_ids = [str(row[0]) for row in page_rows]
        ref_map: dict[str, list[dict[str, str]]] = {item_id: [] for item_id in item_ids}
        if item_ids:
            placeholders = ",".join("?" for _ in item_ids)
            ref_rows = conn.execute(
                f"""SELECT item_id, ref_type, ref_id FROM web_workboard_item_references
                    WHERE account_id=? AND item_id IN ({placeholders}) ORDER BY item_id ASC, ordinal ASC, id ASC""",
                (account_id, *item_ids),
            ).fetchall()
            for ref_row in ref_rows:
                ref_map.setdefault(str(ref_row[0]), []).append({"ref_type": str(ref_row[1]), "ref_id": str(ref_row[2])})
    items = [
        _item_public(tuple(row[:11]), references=ref_map.get(str(row[0]), []), checklist_total=int(row[11] or 0), checklist_done=int(row[12] or 0))
        for row in page_rows
    ]
    return envelope(
        True,
        "Danh sách Workboard của Web account hiện tại.",
        data=_boundary(items=items, has_more=len(rows) > bounded_limit, next_offset=bounded_offset + len(items) if len(rows) > bounded_limit else None),
        status_name="read_only",
    )


@router.post("/items")
async def create_item(payload: ItemCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    scope = f"web-workboard:{account_id}:item:create"
    fingerprint = _fingerprint(_item_snapshot_for_fingerprint(payload))

    def operation(conn: Any) -> dict[str, Any]:
        active_count = conn.execute("SELECT COUNT(*) FROM web_workboard_items WHERE account_id=? AND state!='archived'", (account_id,)).fetchone()
        if int(active_count[0] or 0) >= MAX_ITEMS_PER_ACCOUNT:
            return _guarded("Bạn đã đạt giới hạn work item đang hoạt động.", "WEB_WORKBOARD_ITEM_LIMIT")
        if not _references_are_owned(conn, account_id=account_id, references=payload.references):
            return _guarded("Reference Workboard không tồn tại hoặc không thuộc Web account hiện tại.", "WEB_WORKBOARD_REFERENCE_NOT_FOUND")
        item_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_workboard_items
               (id, account_id, title, description, priority, due_at, state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, 'backlog', 1, ?, ?, NULL)""",
            (item_id, account_id, payload.title, payload.description, payload.priority, payload.due_at, now, now),
        )
        _write_references(conn, item_id=item_id, account_id=account_id, references=payload.references)
        for ordinal, entry in enumerate(payload.checklist, start=1):
            completed_at = now if entry.is_done else None
            conn.execute(
                """INSERT INTO web_workboard_checklist_items
                   (id, item_id, account_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, ?, NULL)""",
                (str(uuid.uuid4()), item_id, account_id, ordinal, entry.body, int(entry.is_done), completed_at, now, now),
            )
        item = _refresh_item(conn, item_id=item_id, account_id=account_id)
        rows = _checklist_rows(conn, item_id=item_id, account_id=account_id, include_archived=True)
        for row in rows:
            _insert_checklist_version(conn, row=row, account_id=account_id)
        _insert_item_version(conn, item=item, account_id=account_id, checklist=rows)
        _event(conn, account_id=account_id, item_id=item_id, entity_type="item", action="item_created", item_revision=1)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.workboard.item.create", request_id=_request_id(request), target=item_id, outcome="ok", detail="web-native workboard item created")
        receipt = _item_receipt(conn, item_id=item_id, account_id=account_id)
        return envelope(True, "Đã tạo work item trong Workboard Web-native.", data=_boundary(item=receipt, checklist_total=len(rows), checklist_done=sum(1 for row in rows if bool(row[4])), version_recorded=True), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/items/{item_id}/schedule-intents")
async def list_schedule_intents(item_id: str, account: dict = Depends(require_account)):
    """Read bounded, opaque intent metadata for one owner-scoped work item."""
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        if not _item_row(conn, item_id=item_id, account_id=account_id):
            return _item_not_found()
        rows = conn.execute(
            """SELECT id, account_id, item_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                      trigger_at, state, revision, created_at, updated_at, dispatched_at, guarded_at, guard_code,
                      cancelled_at, created_by_account_id
               FROM web_workboard_schedule_intents
               WHERE item_id=? AND account_id=?
               ORDER BY CASE state WHEN 'active' THEN 0 WHEN 'guarded' THEN 1 WHEN 'dispatched' THEN 2 ELSE 3 END,
                        trigger_at ASC, created_at DESC, id DESC
               LIMIT ?""",
            (item_id, account_id, MAX_SCHEDULE_INTENTS_PER_ITEM),
        ).fetchall()
    intents = [_schedule_intent_public(tuple(row)) for row in rows]
    return envelope(
        True,
        "Lịch nhắc Workboard chỉ hiển thị metadata owner-scoped của work item hiện tại.",
        data=_boundary(
            schedule_intents=intents,
            max_schedule_intents_per_item=MAX_SCHEDULE_INTENTS_PER_ITEM,
            delivery="in_app_record_only",
            source_content_copied=False,
        ),
        status_name="read_only",
    )


@router.post("/items/{item_id}/schedule-intents")
async def create_schedule_intent(
    item_id: str,
    payload: ScheduleIntentCreateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Register one explicit, future in-app reminder intent for a card."""
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    if not _schedule_actor_allowed(account):
        return _guarded("Phiên Web chưa có role account hợp lệ để tạo lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_ROLE_REQUIRED")
    if not payload.opt_in or not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần bật opt-in và xác nhận rõ ràng trước khi tạo lịch nhắc Workboard")
    try:
        trigger_local_at, zone_name, trigger_at = _schedule_trigger(payload.trigger_local_at, payload.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "item_id": item_id,
        "expected_item_revision": payload.expected_item_revision,
        "trigger_local_at": trigger_local_at,
        "timezone": zone_name,
        "trigger_at": trigger_at,
        "opt_in": bool(payload.opt_in),
        "confirm": bool(payload.confirm),
    })
    scope = f"web-workboard:{account_id}:item:{item_id}:schedule:create"

    def operation(conn: Any) -> dict[str, Any]:
        current = _active_item_or_guard(conn, item_id=item_id, account_id=account_id)
        if isinstance(current, dict):
            return current
        if str(current[6]) == "archived":
            return _guarded("Work item đã archived nên không thể tạo lịch nhắc mới.", "WEB_WORKBOARD_SCHEDULE_ITEM_ARCHIVED")
        if int(current[7]) != payload.expected_item_revision:
            return _guarded("Work item đã có revision mới. Hãy tải lại và xác nhận lại lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_SOURCE_CONFLICT")
        source = _schedule_source_snapshot(conn, item=current, account_id=account_id)
        if not source:
            return _guarded("Snapshot revision Workboard chưa được xác minh nên không thể tạo lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED")
        total = conn.execute(
            "SELECT COUNT(*) FROM web_workboard_schedule_intents WHERE account_id=?", (account_id,),
        ).fetchone()
        active_account = conn.execute(
            "SELECT COUNT(*) FROM web_workboard_schedule_intents WHERE account_id=? AND state='active'", (account_id,),
        ).fetchone()
        active_item = conn.execute(
            "SELECT COUNT(*) FROM web_workboard_schedule_intents WHERE account_id=? AND item_id=? AND state='active'", (account_id, item_id),
        ).fetchone()
        if int(total[0] or 0) >= MAX_SCHEDULE_INTENTS_PER_ACCOUNT:
            return _guarded("Kho lịch nhắc Workboard đã đạt giới hạn an toàn của account.", "WEB_WORKBOARD_SCHEDULE_ACCOUNT_LIMIT")
        if int(active_account[0] or 0) >= MAX_ACTIVE_SCHEDULE_INTENTS_PER_ACCOUNT:
            return _guarded("Account đã có quá nhiều lịch nhắc đang hoạt động. Hãy cancel hoặc xử lý lịch cũ trước.", "WEB_WORKBOARD_SCHEDULE_ACTIVE_LIMIT")
        if int(active_item[0] or 0) >= MAX_SCHEDULE_INTENTS_PER_ITEM:
            return _guarded("Work item này đã có đủ lịch nhắc đang hoạt động.", "WEB_WORKBOARD_SCHEDULE_ITEM_LIMIT")
        intent_id = str(uuid.uuid4())
        now = utc_now()
        try:
            conn.execute(
                """INSERT INTO web_workboard_schedule_intents
                   (id, account_id, item_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                    trigger_at, state, revision, created_by_account_id, created_at, updated_at,
                    dispatched_at, guarded_at, guard_code, cancelled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, ?, NULL, NULL, NULL, NULL)""",
                (intent_id, account_id, item_id, source[0], source[1], trigger_local_at, zone_name, trigger_at,
                 account_id, now, now),
            )
        except sqlite3.IntegrityError:
            existing = conn.execute(
                """SELECT id, account_id, item_id, source_revision, source_snapshot_hash, trigger_local_at, timezone,
                          trigger_at, state, revision, created_at, updated_at, dispatched_at, guarded_at, guard_code,
                          cancelled_at, created_by_account_id
                   FROM web_workboard_schedule_intents
                   WHERE account_id=? AND item_id=? AND source_revision=? AND trigger_at=? AND state='active'""",
                (account_id, item_id, source[0], trigger_at),
            ).fetchone()
            return _guarded(
                "Đã có một lịch nhắc đang hoạt động cho revision và thời điểm này.",
                "WEB_WORKBOARD_SCHEDULE_DUPLICATE",
                status_name="guarded",
            ) if not existing else envelope(
                False,
                "Đã có một lịch nhắc đang hoạt động cho revision và thời điểm này.",
                data=_boundary(schedule_intent=_schedule_intent_public(tuple(existing)), delivery="in_app_record_only"),
                status_name="guarded",
                error_code="WEB_WORKBOARD_SCHEDULE_DUPLICATE",
            )
        created = _schedule_intent_row(conn, intent_id=intent_id, item_id=item_id, account_id=account_id)
        if not created:
            raise RuntimeError("Schedule intent missing after insert")
        _event(
            conn, account_id=account_id, item_id=item_id, entity_type="schedule_intent", entity_id=intent_id,
            action="schedule_intent_created", item_revision=int(current[7]), entity_revision=1,
        )
        _record_audit(
            conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.workboard.schedule.create", request_id=_request_id(request), target=intent_id,
            outcome="ok", detail="explicit owner opt-in for one private in-app workboard schedule record",
        )
        return envelope(
            True,
            "Đã lưu lịch nhắc riêng tư. Chỉ scheduler đã xác thực mới có thể tạo record Inbox in-app khi source vẫn khớp.",
            data=_boundary(schedule_intent=_schedule_intent_public(created), schedule_intent_recorded=True, delivery="in_app_record_only"),
            status_name="completed",
        )

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/items/{item_id}/schedule-intents/{intent_id}/cancel")
async def cancel_schedule_intent(
    item_id: str,
    intent_id: str,
    payload: ScheduleIntentCancelRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    intent_id = _uuid(intent_id, label="Mã lịch nhắc")
    if not _schedule_actor_allowed(account):
        return _guarded("Phiên Web chưa có role account hợp lệ để quản lý lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_ROLE_REQUIRED")
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi cancel lịch nhắc Workboard")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"item_id": item_id, "intent_id": intent_id, "expected_revision": payload.expected_revision, "confirm": True})
    scope = f"web-workboard:{account_id}:item:{item_id}:schedule:{intent_id}:cancel"

    def operation(conn: Any) -> dict[str, Any]:
        if not _item_row(conn, item_id=item_id, account_id=account_id):
            return _item_not_found()
        current = _schedule_intent_row(conn, intent_id=intent_id, item_id=item_id, account_id=account_id)
        if not current:
            return _guarded("Không tìm thấy lịch nhắc thuộc work item và account hiện tại.", "WEB_WORKBOARD_SCHEDULE_NOT_FOUND")
        if int(current[9]) != payload.expected_revision:
            return _guarded("Lịch nhắc đã có revision mới. Hãy tải lại trước khi cancel.", "WEB_WORKBOARD_SCHEDULE_CONFLICT")
        if str(current[8]) == "dispatched":
            return _guarded("Lịch nhắc đã tạo record Inbox; không thể rút lại record đã materialize.", "WEB_WORKBOARD_SCHEDULE_DISPATCHED")
        if str(current[8]) == "cancelled":
            return envelope(True, "Lịch nhắc đã được cancel trước đó.", data=_boundary(schedule_intent=_schedule_intent_public(current), delivery="in_app_record_only"), status_name="completed")
        now = utc_now()
        next_revision = int(current[9]) + 1
        updated = conn.execute(
            """UPDATE web_workboard_schedule_intents
               SET state='cancelled', revision=?, updated_at=?, cancelled_at=?
               WHERE id=? AND item_id=? AND account_id=? AND revision=? AND state IN ('active', 'guarded')""",
            (next_revision, now, now, intent_id, item_id, account_id, payload.expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            return _guarded("Lịch nhắc đã thay đổi đồng thời. Hãy tải lại trước khi cancel.", "WEB_WORKBOARD_SCHEDULE_CONFLICT")
        refreshed = _schedule_intent_row(conn, intent_id=intent_id, item_id=item_id, account_id=account_id)
        if not refreshed:
            raise RuntimeError("Schedule intent disappeared after cancel")
        item = _item_row(conn, item_id=item_id, account_id=account_id)
        _event(
            conn, account_id=account_id, item_id=item_id, entity_type="schedule_intent", entity_id=intent_id,
            action="schedule_intent_cancelled", item_revision=int(item[7]) if item else 0, entity_revision=next_revision,
        )
        _record_audit(
            conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.workboard.schedule.cancel", request_id=_request_id(request), target=intent_id,
            outcome="ok", detail="owner cancelled a web-only in-app schedule intent",
        )
        return envelope(True, "Đã cancel lịch nhắc. Không có Inbox record mới hoặc thông báo ngoài Web được gửi.", data=_boundary(schedule_intent=_schedule_intent_public(refreshed), delivery="in_app_record_only"), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/items/{item_id}/schedule-intents/{intent_id}/reconfirm")
async def reconfirm_schedule_intent(
    item_id: str,
    intent_id: str,
    payload: ScheduleIntentReconfirmRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Explicitly bind a guarded intent to the current item snapshot again."""
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    intent_id = _uuid(intent_id, label="Mã lịch nhắc")
    if not _schedule_actor_allowed(account):
        return _guarded("Phiên Web chưa có role account hợp lệ để xác nhận lại lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_ROLE_REQUIRED")
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi bind lại lịch nhắc với revision mới")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "item_id": item_id, "intent_id": intent_id, "expected_revision": payload.expected_revision,
        "expected_item_revision": payload.expected_item_revision, "confirm": True,
    })
    scope = f"web-workboard:{account_id}:item:{item_id}:schedule:{intent_id}:reconfirm"

    def operation(conn: Any) -> dict[str, Any]:
        current_item = _active_item_or_guard(conn, item_id=item_id, account_id=account_id)
        if isinstance(current_item, dict):
            return current_item
        if str(current_item[6]) == "archived":
            return _guarded("Work item đã archived nên không thể xác nhận lại lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_ITEM_ARCHIVED")
        intent = _schedule_intent_row(conn, intent_id=intent_id, item_id=item_id, account_id=account_id)
        if not intent:
            return _guarded("Không tìm thấy lịch nhắc thuộc work item và account hiện tại.", "WEB_WORKBOARD_SCHEDULE_NOT_FOUND")
        if int(intent[9]) != payload.expected_revision:
            return _guarded("Lịch nhắc đã có revision mới. Hãy tải lại trước khi xác nhận lại.", "WEB_WORKBOARD_SCHEDULE_CONFLICT")
        if str(intent[8]) != "guarded":
            return _guarded("Chỉ lịch nhắc đang guarded mới cần xác nhận lại source snapshot.", "WEB_WORKBOARD_SCHEDULE_RECONFIRM_NOT_REQUIRED")
        if int(current_item[7]) != payload.expected_item_revision:
            return _guarded("Work item đã có revision mới. Hãy tải lại trước khi bind lại lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_SOURCE_CONFLICT")
        try:
            _local, _zone, normalized_trigger = _schedule_trigger(intent[5], intent[6])
        except ValueError:
            return _guarded("Thời điểm lịch nhắc đã qua hoặc không còn xác minh được. Hãy tạo lịch mới rõ ràng.", "WEB_WORKBOARD_SCHEDULE_TRIGGER_EXPIRED")
        if not hmac.compare_digest(normalized_trigger, str(intent[7])):
            return _guarded("Thời điểm UTC của lịch nhắc không còn khớp với timezone đã lưu. Hãy tạo lịch mới.", "WEB_WORKBOARD_SCHEDULE_TRIGGER_UNVERIFIED")
        source = _schedule_source_snapshot(conn, item=current_item, account_id=account_id)
        if not source:
            return _guarded("Snapshot revision Workboard chưa được xác minh nên chưa thể bind lại lịch nhắc.", "WEB_WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED")
        next_revision = int(intent[9]) + 1
        now = utc_now()
        try:
            updated = conn.execute(
                """UPDATE web_workboard_schedule_intents
                   SET source_revision=?, source_snapshot_hash=?, state='active', revision=?, updated_at=?,
                       guarded_at=NULL, guard_code=NULL, cancelled_at=NULL
                   WHERE id=? AND item_id=? AND account_id=? AND revision=? AND state='guarded'""",
                (source[0], source[1], next_revision, now, intent_id, item_id, account_id, payload.expected_revision),
            )
        except sqlite3.IntegrityError:
            return _guarded("Đã có lịch nhắc active khác cho revision và thời điểm này.", "WEB_WORKBOARD_SCHEDULE_DUPLICATE")
        if int(updated.rowcount or 0) != 1:
            return _guarded("Lịch nhắc đã thay đổi đồng thời. Hãy tải lại trước khi xác nhận lại.", "WEB_WORKBOARD_SCHEDULE_CONFLICT")
        refreshed = _schedule_intent_row(conn, intent_id=intent_id, item_id=item_id, account_id=account_id)
        if not refreshed:
            raise RuntimeError("Schedule intent disappeared after reconfirm")
        _event(
            conn, account_id=account_id, item_id=item_id, entity_type="schedule_intent", entity_id=intent_id,
            action="schedule_intent_reconfirmed", item_revision=int(current_item[7]), entity_revision=next_revision,
        )
        _record_audit(
            conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.workboard.schedule.reconfirm", request_id=_request_id(request), target=intent_id,
            outcome="ok", detail="owner explicitly rebound a guarded schedule intent to the current workboard snapshot",
        )
        return envelope(True, "Đã xác nhận lại source snapshot. Thời điểm cũ được giữ nguyên, không tự reschedule.", data=_boundary(schedule_intent=_schedule_intent_public(refreshed), delivery="in_app_record_only"), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/items/{item_id}/events")
async def item_events(
    item_id: str,
    limit: int = Query(default=60, ge=1, le=MAX_EVENT_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_LIST_OFFSET),
    account: dict = Depends(require_account),
):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    account_id = str(account["id"])
    bounded = min(limit, MAX_EVENT_LIMIT)
    ensure_copyfast_schema()
    with read_transaction() as conn:
        if not _item_row(conn, item_id=item_id, account_id=account_id):
            return _item_not_found()
        rows = conn.execute(
            """SELECT entity_type, entity_id, action, item_revision, entity_revision, created_at
               FROM web_workboard_events WHERE item_id=? AND account_id=?
               ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?""",
            (item_id, account_id, bounded + 1, offset),
        ).fetchall()
    has_more = len(rows) > bounded
    page_rows = rows[:bounded]
    events = [{"entity_type": str(row[0]), "entity_id": str(row[1]) if row[1] else None, "action": str(row[2]), "item_revision": int(row[3]), "entity_revision": int(row[4]) if row[4] is not None else None, "created_at": str(row[5])} for row in page_rows]
    return envelope(
        True,
        "Nhật ký Workboard không chứa nội dung riêng tư.",
        data=_boundary(
            # Keep the existing `events` key for established clients while
            # exposing `items` for the shared bounded-paging reader.
            items=events,
            events=events,
            pagination={"limit": bounded, "offset": offset, "returned": len(events)},
            has_more=has_more,
            next_offset=offset + len(events) if has_more else None,
            previous_offset=max(0, offset - bounded) if offset > 0 else None,
        ),
        status_name="read_only",
    )


@router.get("/items/{item_id}/versions")
async def item_versions(
    item_id: str,
    limit: int = Query(default=60, ge=1, le=MAX_VERSION_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_LIST_OFFSET),
    account: dict = Depends(require_account),
):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    account_id = str(account["id"])
    bounded = min(limit, MAX_VERSION_LIMIT)
    ensure_copyfast_schema()
    with read_transaction() as conn:
        if not _item_row(conn, item_id=item_id, account_id=account_id):
            return _item_not_found()
        rows = conn.execute(
            """SELECT revision, created_at FROM web_workboard_item_versions
               WHERE item_id=? AND account_id=? ORDER BY revision DESC LIMIT ? OFFSET ?""",
            (item_id, account_id, bounded + 1, offset),
        ).fetchall()
    has_more = len(rows) > bounded
    page_rows = rows[:bounded]
    versions = [{"revision": int(row[0]), "created_at": str(row[1])} for row in page_rows]
    return envelope(
        True,
        "Danh sách revision Workboard.",
        data=_boundary(
            items=versions,
            versions=versions,
            pagination={"limit": bounded, "offset": offset, "returned": len(versions)},
            has_more=has_more,
            next_offset=offset + len(versions) if has_more else None,
            previous_offset=max(0, offset - bounded) if offset > 0 else None,
        ),
        status_name="read_only",
    )


@router.get("/items/{item_id}")
async def item_detail(item_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        item = _item_row(conn, item_id=item_id, account_id=account_id)
        if not item:
            return _item_not_found()
        checklist_rows = _checklist_rows(conn, item_id=item_id, account_id=account_id)
        total, done = _item_counts(conn, item_id=item_id, account_id=account_id)
        references = _references_public(_reference_rows(conn, item_id=item_id, account_id=account_id))
        versions = conn.execute("SELECT revision, created_at FROM web_workboard_item_versions WHERE item_id=? AND account_id=? ORDER BY revision DESC LIMIT 60", (item_id, account_id)).fetchall()
        events = conn.execute("SELECT entity_type, entity_id, action, item_revision, entity_revision, created_at FROM web_workboard_events WHERE item_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT 60", (item_id, account_id)).fetchall()
    return envelope(
        True,
        "Work item đã được nạp từ Web Workspace.",
        data=_boundary(
            item=_item_public(item, references=references, checklist_total=total, checklist_done=done, include_description=True),
            checklist=[_checklist_public(row) for row in checklist_rows],
            versions=[{"revision": int(row[0]), "created_at": str(row[1])} for row in versions],
            events=[{"entity_type": str(row[0]), "entity_id": str(row[1]) if row[1] else None, "action": str(row[2]), "item_revision": int(row[3]), "entity_revision": int(row[4]) if row[4] is not None else None, "created_at": str(row[5])} for row in events],
        ),
        status_name="read_only",
    )


@router.patch("/items/{item_id}")
async def update_item(item_id: str, payload: ItemUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    account_id = str(account["id"])
    changes = payload.model_dump(exclude={"expected_revision", "idempotency_key"}, exclude_unset=True)
    fingerprint = _fingerprint({"item_id": item_id, "expected_revision": payload.expected_revision, "changes": changes})
    scope = f"web-workboard:{account_id}:item:{item_id}:update"

    def operation(conn: Any) -> dict[str, Any]:
        current = _active_item_or_guard(conn, item_id=item_id, account_id=account_id)
        if isinstance(current, dict):
            return current
        if str(current[6]) == "archived":
            return _guarded("Work item đã lưu trữ chỉ có thể đổi trạng thái để khôi phục.", "WEB_WORKBOARD_ITEM_ARCHIVED")
        if int(current[7]) != payload.expected_revision:
            return _guarded("Work item đã có revision mới. Hãy tải lại trước khi lưu.", "WEB_WORKBOARD_REVISION_CONFLICT")
        title = changes.get("title", str(current[2]))
        description = changes.get("description", str(current[3]))
        priority = changes.get("priority", str(current[4]))
        due_at = changes["due_at"] if "due_at" in changes else (str(current[5]) if current[5] else None)
        if "references" in changes and not _references_are_owned(conn, account_id=account_id, references=changes["references"]):
            return _guarded("Reference Workboard không tồn tại hoặc không thuộc Web account hiện tại.", "WEB_WORKBOARD_REFERENCE_NOT_FOUND")
        next_revision = int(current[7]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_workboard_items SET title=?, description=?, priority=?, due_at=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (title, description, priority, due_at, next_revision, now, item_id, account_id, payload.expected_revision),
        )
        if "references" in changes:
            _write_references(conn, item_id=item_id, account_id=account_id, references=changes["references"])
        current = _refresh_item(conn, item_id=item_id, account_id=account_id)
        _insert_item_version(conn, item=current, account_id=account_id)
        _event(conn, account_id=account_id, item_id=item_id, entity_type="item", action="item_updated", item_revision=int(current[7]))
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.workboard.item.update", request_id=_request_id(request), target=item_id, outcome="ok", detail=f"web-native workboard revision:{current[7]}")
        return envelope(True, "Đã lưu revision Workboard mới.", data=_boundary(item=_item_receipt(conn, item_id=item_id, account_id=account_id), version_recorded=True), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/items/{item_id}/state")
async def update_state(item_id: str, payload: ItemStateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"item_id": item_id, "expected_revision": payload.expected_revision, "state": payload.state})
    scope = f"web-workboard:{account_id}:item:{item_id}:state"

    def operation(conn: Any) -> dict[str, Any]:
        current = _active_item_or_guard(conn, item_id=item_id, account_id=account_id)
        if isinstance(current, dict):
            return current
        current_state = str(current[6])
        if int(current[7]) != payload.expected_revision:
            return _guarded("Work item đã có revision mới. Hãy tải lại trước khi đổi trạng thái.", "WEB_WORKBOARD_REVISION_CONFLICT")
        if payload.state not in TRANSITIONS.get(current_state, frozenset()):
            return _guarded("Chuyển trạng thái Workboard không hợp lệ.", "WEB_WORKBOARD_TRANSITION_INVALID")
        total, done = _item_counts(conn, item_id=item_id, account_id=account_id)
        if payload.state == "done" and total and done < total:
            return _guarded("Hoàn tất checklist đang hoạt động trước khi đánh dấu work item hoàn tất.", "WEB_WORKBOARD_CHECKLIST_INCOMPLETE")
        next_revision = int(current[7]) + 1
        now = utc_now()
        archived_at = now if payload.state == "archived" else None
        conn.execute(
            """UPDATE web_workboard_items SET state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (payload.state, next_revision, now, archived_at, item_id, account_id, payload.expected_revision),
        )
        current = _refresh_item(conn, item_id=item_id, account_id=account_id)
        _insert_item_version(conn, item=current, account_id=account_id)
        _event(conn, account_id=account_id, item_id=item_id, entity_type="item", action=f"state_{payload.state}", item_revision=int(current[7]))
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.workboard.item.state", request_id=_request_id(request), target=item_id, outcome="ok", detail=f"web-native workboard state:{payload.state}")
        return envelope(True, "Đã cập nhật trạng thái Workboard. Đây không phải publish, job hoặc admin approval.", data=_boundary(item=_item_receipt(conn, item_id=item_id, account_id=account_id), version_recorded=True), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/items/{item_id}/checklist")
async def create_checklist(item_id: str, payload: ChecklistCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"item_id": item_id, "expected_revision": payload.expected_revision, "body": payload.body, "is_done": payload.is_done})
    scope = f"web-workboard:{account_id}:item:{item_id}:checklist:create"

    def operation(conn: Any) -> dict[str, Any]:
        current = _active_item_or_guard(conn, item_id=item_id, account_id=account_id)
        if isinstance(current, dict):
            return current
        if str(current[6]) == "archived":
            return _guarded("Work item đã lưu trữ không thể thêm checklist.", "WEB_WORKBOARD_ITEM_ARCHIVED")
        if int(current[7]) != payload.expected_revision:
            return _guarded("Work item đã có revision mới. Hãy tải lại trước khi thêm checklist.", "WEB_WORKBOARD_REVISION_CONFLICT")
        total, _ = _item_counts(conn, item_id=item_id, account_id=account_id)
        if total >= MAX_CHECKLIST_PER_ITEM:
            return _guarded("Work item đã đạt giới hạn checklist.", "WEB_WORKBOARD_CHECKLIST_LIMIT")
        ordinal_row = conn.execute("SELECT COALESCE(MAX(ordinal), 0) FROM web_workboard_checklist_items WHERE item_id=? AND account_id=? AND ordinal<?", (item_id, account_id, ARCHIVED_ORDINAL_BASE)).fetchone()
        ordinal = int(ordinal_row[0] or 0) + 1
        now = utc_now()
        checklist_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_workboard_checklist_items
               (id, item_id, account_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, ?, NULL)""",
            (checklist_id, item_id, account_id, ordinal, payload.body, int(payload.is_done), now if payload.is_done else None, now, now),
        )
        conn.execute("UPDATE web_workboard_items SET revision=?, updated_at=? WHERE id=? AND account_id=? AND revision=?", (int(current[7]) + 1, now, item_id, account_id, payload.expected_revision))
        checklist_row = conn.execute("SELECT id, item_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at FROM web_workboard_checklist_items WHERE id=? AND item_id=? AND account_id=?", (checklist_id, item_id, account_id)).fetchone()
        _insert_checklist_version(conn, row=checklist_row, account_id=account_id)
        item = _refresh_item(conn, item_id=item_id, account_id=account_id)
        _insert_item_version(conn, item=item, account_id=account_id)
        _event(conn, account_id=account_id, item_id=item_id, entity_type="checklist", entity_id=checklist_id, action="checklist_created", item_revision=int(item[7]), entity_revision=1)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.workboard.checklist.create", request_id=_request_id(request), target=item_id, outcome="ok", detail="web-native workboard checklist created")
        return envelope(True, "Đã thêm checklist vào Workboard.", data=_boundary(item=_item_receipt(conn, item_id=item_id, account_id=account_id), checklist=_checklist_public(checklist_row), version_recorded=True), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/items/{item_id}/checklist/{checklist_id}")
async def update_checklist(item_id: str, checklist_id: str, payload: ChecklistUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    checklist_id = _uuid(checklist_id, label="Checklist ID")
    account_id = str(account["id"])
    changes = payload.model_dump(exclude={"expected_revision", "expected_checklist_revision", "idempotency_key"}, exclude_unset=True)
    fingerprint = _fingerprint({"item_id": item_id, "checklist_id": checklist_id, "expected_revision": payload.expected_revision, "expected_checklist_revision": payload.expected_checklist_revision, "changes": changes})
    scope = f"web-workboard:{account_id}:item:{item_id}:checklist:{checklist_id}:update"

    def operation(conn: Any) -> dict[str, Any]:
        current = _active_item_or_guard(conn, item_id=item_id, account_id=account_id)
        if isinstance(current, dict):
            return current
        if str(current[6]) == "archived":
            return _guarded("Work item đã lưu trữ không thể đổi checklist.", "WEB_WORKBOARD_ITEM_ARCHIVED")
        if int(current[7]) != payload.expected_revision:
            return _guarded("Work item đã có revision mới. Hãy tải lại trước khi đổi checklist.", "WEB_WORKBOARD_REVISION_CONFLICT")
        checklist = conn.execute("SELECT id, item_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at FROM web_workboard_checklist_items WHERE id=? AND item_id=? AND account_id=?", (checklist_id, item_id, account_id)).fetchone()
        if not checklist or str(checklist[5]) != "active":
            return _guarded("Không tìm thấy checklist đang hoạt động thuộc work item hiện tại.", "WEB_WORKBOARD_CHECKLIST_NOT_FOUND")
        if int(checklist[6]) != payload.expected_checklist_revision:
            return _guarded("Checklist đã có revision mới. Hãy tải lại trước khi lưu.", "WEB_WORKBOARD_CHECKLIST_CONFLICT")
        body = changes.get("body", str(checklist[3]))
        is_done = bool(changes["is_done"]) if "is_done" in changes else bool(checklist[4])
        now = utc_now()
        next_checklist_revision = int(checklist[6]) + 1
        conn.execute(
            """UPDATE web_workboard_checklist_items SET body=?, is_done=?, revision=?, completed_at=?, updated_at=?
               WHERE id=? AND item_id=? AND account_id=? AND revision=? AND state='active'""",
            (body, int(is_done), next_checklist_revision, now if is_done else None, now, checklist_id, item_id, account_id, payload.expected_checklist_revision),
        )
        conn.execute("UPDATE web_workboard_items SET revision=?, updated_at=? WHERE id=? AND account_id=? AND revision=?", (int(current[7]) + 1, now, item_id, account_id, payload.expected_revision))
        checklist = conn.execute("SELECT id, item_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at FROM web_workboard_checklist_items WHERE id=? AND item_id=? AND account_id=?", (checklist_id, item_id, account_id)).fetchone()
        _insert_checklist_version(conn, row=checklist, account_id=account_id)
        item = _refresh_item(conn, item_id=item_id, account_id=account_id)
        _insert_item_version(conn, item=item, account_id=account_id)
        _event(conn, account_id=account_id, item_id=item_id, entity_type="checklist", entity_id=checklist_id, action="checklist_completed" if is_done else "checklist_updated", item_revision=int(item[7]), entity_revision=int(checklist[6]))
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.workboard.checklist.update", request_id=_request_id(request), target=item_id, outcome="ok", detail=f"web-native checklist revision:{checklist[6]}")
        return envelope(True, "Đã cập nhật checklist Workboard.", data=_boundary(item=_item_receipt(conn, item_id=item_id, account_id=account_id), checklist=_checklist_public(checklist), version_recorded=True), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/items/{item_id}/restore/{revision}")
async def restore_item_version(item_id: str, revision: int, payload: RevisionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    item_id = _uuid(item_id, label="Work item ID")
    if revision < 1 or revision > 1_000_000:
        raise HTTPException(status_code=422, detail="Revision Workboard không hợp lệ")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"item_id": item_id, "target_revision": revision, "expected_revision": payload.expected_revision})
    scope = f"web-workboard:{account_id}:item:{item_id}:restore:{revision}"

    def operation(conn: Any) -> dict[str, Any]:
        current = _active_item_or_guard(conn, item_id=item_id, account_id=account_id)
        if isinstance(current, dict):
            return current
        if int(current[7]) != payload.expected_revision:
            return _guarded("Work item đã có revision mới. Hãy tải lại trước khi khôi phục.", "WEB_WORKBOARD_REVISION_CONFLICT")
        row = conn.execute("SELECT snapshot_json FROM web_workboard_item_versions WHERE item_id=? AND account_id=? AND revision=?", (item_id, account_id, revision)).fetchone()
        if not row:
            return _guarded("Không tìm thấy revision Workboard để khôi phục.", "WEB_WORKBOARD_VERSION_NOT_FOUND")
        try:
            snapshot = json.loads(str(row[0]))
        except (TypeError, ValueError, json.JSONDecodeError):
            return _guarded("Snapshot Workboard không hợp lệ.", "WEB_WORKBOARD_VERSION_INVALID")
        if not isinstance(snapshot, dict):
            return _guarded("Snapshot Workboard không hợp lệ.", "WEB_WORKBOARD_VERSION_INVALID")
        try:
            title = _line(snapshot.get("title"), label="Tên công việc", minimum=3, maximum=180)
            description = _body(snapshot.get("description"), label="Mô tả công việc", maximum=5_000, allow_empty=True)
            priority = _line(snapshot.get("priority"), label="Ưu tiên", minimum=2, maximum=16).lower()
            due_at = _due_at(snapshot.get("due_at"))
            state = _line(snapshot.get("state"), label="Trạng thái Workboard", minimum=2, maximum=24).lower()
            if priority not in PRIORITIES or state not in ITEM_STATES:
                raise ValueError("Snapshot Workboard chứa trạng thái không hỗ trợ")
            references = [ReferenceInput.model_validate(value) for value in snapshot.get("references", [])]
            checklist_values = [
                ChecklistInput.model_validate({"body": value.get("body"), "is_done": value.get("is_done", False)})
                for value in snapshot.get("checklist", [])
                if isinstance(value, dict)
            ]
            if not isinstance(snapshot.get("checklist", []), list) or len(checklist_values) != len(snapshot.get("checklist", [])):
                raise ValueError("Snapshot Workboard chứa checklist không hợp lệ")
            if len(references) > MAX_REFERENCES_PER_ITEM or len(checklist_values) > MAX_CHECKLIST_PER_ITEM:
                raise ValueError("Snapshot Workboard vượt giới hạn an toàn")
        except (TypeError, ValueError) as exc:
            return _guarded(str(exc), "WEB_WORKBOARD_VERSION_INVALID")
        for reference in references:
            if not _validate_reference(conn, reference=reference, account_id=account_id):
                return _guarded("Reference trong revision không còn thuộc Web account hiện tại.", "WEB_WORKBOARD_REFERENCE_NOT_FOUND")
        now = utc_now()
        next_revision = int(current[7]) + 1
        conn.execute("UPDATE web_workboard_items SET title=?, description=?, priority=?, due_at=?, state=?, revision=?, updated_at=?, archived_at=? WHERE id=? AND account_id=? AND revision=?", (title, description, priority, due_at, state, next_revision, now, now if state == "archived" else None, item_id, account_id, payload.expected_revision))
        _write_references(conn, item_id=item_id, account_id=account_id, references=references)
        active = _checklist_rows(conn, item_id=item_id, account_id=account_id)
        desired_ordinals = {index for index, _ in enumerate(checklist_values, start=1)}
        for row_checklist in active:
            if int(row_checklist[2]) not in desired_ordinals:
                conn.execute("UPDATE web_workboard_checklist_items SET state='archived', ordinal=?, revision=?, archived_at=?, updated_at=? WHERE id=? AND item_id=? AND account_id=?", (ARCHIVED_ORDINAL_BASE + int(row_checklist[2]), int(row_checklist[6]) + 1, now, now, str(row_checklist[0]), item_id, account_id))
        for ordinal, entry in enumerate(checklist_values, start=1):
            existing = conn.execute("SELECT id, item_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at FROM web_workboard_checklist_items WHERE item_id=? AND account_id=? AND ordinal=?", (item_id, account_id, ordinal)).fetchone()
            if existing:
                conn.execute("UPDATE web_workboard_checklist_items SET body=?, is_done=?, state='active', revision=?, completed_at=?, updated_at=?, archived_at=NULL WHERE id=? AND item_id=? AND account_id=?", (entry.body, int(entry.is_done), int(existing[6]) + 1, now if entry.is_done else None, now, str(existing[0]), item_id, account_id))
                changed = conn.execute("SELECT id, item_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at FROM web_workboard_checklist_items WHERE id=?", (str(existing[0]),)).fetchone()
            else:
                check_id = str(uuid.uuid4())
                conn.execute("INSERT INTO web_workboard_checklist_items (id, item_id, account_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at) VALUES (?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, ?, NULL)", (check_id, item_id, account_id, ordinal, entry.body, int(entry.is_done), now if entry.is_done else None, now, now))
                changed = conn.execute("SELECT id, item_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at FROM web_workboard_checklist_items WHERE id=?", (check_id,)).fetchone()
            _insert_checklist_version(conn, row=changed, account_id=account_id)
        item = _refresh_item(conn, item_id=item_id, account_id=account_id)
        _insert_item_version(conn, item=item, account_id=account_id)
        _event(conn, account_id=account_id, item_id=item_id, entity_type="item", action=f"restored_from_{revision}", item_revision=int(item[7]))
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.workboard.item.restore", request_id=_request_id(request), target=item_id, outcome="ok", detail=f"web-native workboard restore:{revision}")
        return envelope(True, "Đã khôi phục revision Workboard thành revision mới. Không có automation bên ngoài nào được chạy.", data=_boundary(item=_item_receipt(conn, item_id=item_id, account_id=account_id), version_recorded=True), status_name="completed")

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/events")
async def events(
    limit: int = Query(default=60, ge=1, le=MAX_EVENT_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_LIST_OFFSET),
    account: dict = Depends(require_account),
):
    _require_enabled()
    account_id = str(account["id"])
    bounded = min(limit, MAX_EVENT_LIMIT)
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            "SELECT item_id, entity_type, entity_id, action, item_revision, entity_revision, created_at FROM web_workboard_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (account_id, bounded + 1, offset),
        ).fetchall()
    has_more = len(rows) > bounded
    page_rows = rows[:bounded]
    activity = [{"item_id": str(row[0]), "entity_type": str(row[1]), "entity_id": str(row[2]) if row[2] else None, "action": str(row[3]), "item_revision": int(row[4]), "entity_revision": int(row[5]) if row[5] is not None else None, "created_at": str(row[6])} for row in page_rows]
    return envelope(
        True,
        "Hoạt động Workboard không chứa nội dung riêng tư.",
        data=_boundary(
            items=activity,
            events=activity,
            pagination={"limit": bounded, "offset": offset, "returned": len(activity)},
            has_more=has_more,
            next_offset=offset + len(activity) if has_more else None,
            previous_offset=max(0, offset - bounded) if offset > 0 else None,
        ),
        status_name="read_only",
    )
