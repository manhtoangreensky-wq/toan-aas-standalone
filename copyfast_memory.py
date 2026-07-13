"""Private, Web-owned notes and reminders for the professional portal.

This module intentionally evolves the useful local workflow behind Bot
``/notes``, ``/note`` and ``/reminders`` into a browser-first product surface.
It never reads Bot ``memory_*`` tables, sends Telegram messages, calls a
provider, creates a payment, mutates Xu, or claims that an off-browser
notification was delivered.  A signed Web account owns every row.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import calendar
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, memory_center_enabled, transaction, utc_now


router = APIRouter(prefix="/api/v1/memory", tags=["Web Memory Center"])

NOTE_STATES = frozenset({"active", "archived"})
PRIORITIES = frozenset({"low", "normal", "important", "urgent"})
REMINDER_STATES = frozenset({"active", "paused", "completed", "cancelled"})
REPEAT_RULES = frozenset({"none", "daily", "weekly", "monthly", "yearly"})
SUPPORTED_TIMEZONES = frozenset({"Asia/Ho_Chi_Minh", "UTC"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)"
    r"\b\s*(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE)
CARD_LIKE_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
MAX_NOTES_PER_ACCOUNT = 1_000
MAX_ACTIVE_REMINDERS_PER_ACCOUNT = 250
MAX_NOTE_TITLE = 160
MAX_NOTE_CONTENT = 12_000
MAX_REMINDER_TITLE = 160
MAX_REMINDER_BODY = 2_000
MAX_CATEGORY = 80
MAX_TAGS = 12
MAX_TAG_LENGTH = 40


def _require_memory_enabled() -> None:
    if not memory_center_enabled():
        raise HTTPException(
            status_code=503,
            detail="Memory Center đang tạm dừng để bảo trì. WEBAPP_MEMORY_CENTER_ENABLED chưa được bật.",
        )


def _uuid(value: str, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: str) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _single_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if "\x00" in text or (not text and not allow_empty) or len(text) < minimum or len(text) > maximum:
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    # Titles, categories and tags are rendered back into the account UI. Keep
    # the no-secret promise consistent across every user-owned text field,
    # rather than protecting only note bodies and reminder descriptions.
    if text and (SECRET_ASSIGNMENT_PATTERN.search(text) or BEARER_PATTERN.search(text) or CARD_LIKE_PATTERN.search(text)):
        raise ValueError(f"{label} không nhận secret, token, mật khẩu hoặc số thẻ")
    return text


def _validated_single_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    """Turn query-string validation into a controlled API error.

    Pydantic converts model validator ``ValueError`` values to 422 responses,
    but list filters are plain FastAPI query parameters. Keep invalid filter
    values from becoming an unhandled server error.
    """
    try:
        return _single_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _safe_content(value: Any, *, label: str, maximum: int) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if "\x00" in text or not text or len(text) > maximum:
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if SECRET_ASSIGNMENT_PATTERN.search(text) or BEARER_PATTERN.search(text) or CARD_LIKE_PATTERN.search(text):
        raise ValueError(f"{label} không nhận secret, token, mật khẩu hoặc số thẻ")
    return text


def _optional_content(value: Any, *, label: str, maximum: int) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if "\x00" in text or len(text) > maximum:
        raise ValueError(f"{label} tối đa {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and (SECRET_ASSIGNMENT_PATTERN.search(text) or BEARER_PATTERN.search(text) or CARD_LIKE_PATTERN.search(text)):
        raise ValueError(f"{label} không nhận secret, token, mật khẩu hoặc số thẻ")
    return text


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Tags phải là một danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        tag = _single_line(item, label="Tag", minimum=1, maximum=MAX_TAG_LENGTH)
        if SECRET_ASSIGNMENT_PATTERN.search(tag) or BEARER_PATTERN.search(tag) or CARD_LIKE_PATTERN.search(tag):
            raise ValueError("Tag không nhận secret, token, mật khẩu hoặc số thẻ")
        fingerprint = tag.casefold()
        if fingerprint not in seen:
            seen.add(fingerprint)
            result.append(tag)
    if len(result) > MAX_TAGS:
        raise ValueError(f"Tối đa {MAX_TAGS} tags cho một ghi chú")
    return result


def _priority(value: Any) -> str:
    normalized = str(value or "normal").strip().lower()
    if normalized not in PRIORITIES:
        raise ValueError("Priority không hợp lệ")
    return normalized


def _repeat_rule(value: Any) -> str:
    normalized = str(value or "none").strip().lower()
    if normalized not in REPEAT_RULES:
        raise ValueError("Chu kỳ lặp không hợp lệ")
    return normalized


def _timezone_name(value: Any) -> str:
    normalized = str(value or "Asia/Ho_Chi_Minh").strip()
    if normalized not in SUPPORTED_TIMEZONES:
        raise ValueError("Múi giờ reminder chưa được hỗ trợ")
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Múi giờ reminder chưa sẵn sàng") from exc
    return normalized


def _parse_utc(value: str) -> datetime:
    raw = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Mốc thời gian không hợp lệ") from exc
    if parsed.tzinfo is None:
        raise ValueError("Mốc thời gian phải có múi giờ server-side")
    return parsed.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _due_at(value: str, timezone_name: str, *, allow_past: bool = False) -> str:
    raw = str(value or "").strip()
    if not raw or len(raw) > 64 or "\x00" in raw:
        raise ValueError("Mốc reminder không hợp lệ")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Mốc reminder không hợp lệ") from exc
    zone = ZoneInfo(timezone_name)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    candidate = parsed.astimezone(timezone.utc)
    if not allow_past and candidate <= datetime.now(timezone.utc) + timedelta(seconds=30):
        raise ValueError("Mốc reminder phải ở tương lai")
    return _utc_text(candidate)


def _validated_due_at(value: str, timezone_name: str) -> str:
    """Translate user-supplied reminder time into a safe API validation error.

    The Pydantic shape validator intentionally permits local datetime input so
    customers can choose a declared timezone.  Its temporal validation occurs
    here, immediately before a write.  Never let an expired/invalid timestamp
    escape as an unhandled 500 response.
    """
    try:
        return _due_at(value, timezone_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _month_shift(value: datetime, months: int) -> datetime:
    year = value.year + ((value.month - 1 + months) // 12)
    month = ((value.month - 1 + months) % 12) + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _year_shift(value: datetime, years: int) -> datetime:
    year = value.year + years
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


def _next_repeat_after(next_run_at: str, repeat_rule: str, timezone_name: str, *, now: datetime | None = None) -> str:
    """Advance a recurring reminder in its declared local calendar timezone."""
    if repeat_rule not in REPEAT_RULES or repeat_rule == "none":
        raise ValueError("Reminder một lần không có chu kỳ lặp")
    reference = _parse_utc(next_run_at)
    zone = ZoneInfo(timezone_name)
    local = reference.astimezone(zone)
    now_utc = now or datetime.now(timezone.utc)
    candidate = local
    # A repeated reminder may be resumed after a long offline period.  Keep a
    # hard upper bound so corrupt input can never produce an endless loop.
    for _ in range(4_000):
        if repeat_rule == "daily":
            candidate += timedelta(days=1)
        elif repeat_rule == "weekly":
            candidate += timedelta(days=7)
        elif repeat_rule == "monthly":
            candidate = _month_shift(candidate, 1)
        else:
            candidate = _year_shift(candidate, 1)
        utc_candidate = candidate.astimezone(timezone.utc)
        if utc_candidate > now_utc:
            return _utc_text(utc_candidate)
    raise ValueError("Không thể tính chu kỳ reminder an toàn")


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _content_hash(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _idempotent(
    scope: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Run one private mutation once, rejecting a key reused for new input."""
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored_fingerprint = str(existing[1] or "")
            if not stored_fingerprint or not hmac.compare_digest(stored_fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                response = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Memory không hợp lệ") from exc
            if isinstance(response, dict):
                return response
            raise HTTPException(status_code=409, detail="Bản ghi idempotency Memory không hợp lệ")
        response = operation(conn)
        conn.execute(
            """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
        )
    return response


def _event(conn: Any, *, account_id: str, action: str, note_id: str | None = None, reminder_id: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_memory_events (id, account_id, note_id, reminder_id, action, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, note_id or None, reminder_id or None, action, utc_now()),
    )


def _decode_tags(value: Any) -> list[str]:
    try:
        raw = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str)][:MAX_TAGS]


def _excerpt(value: str, length: int = 240) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    return normalized[:length] + ("…" if len(normalized) > length else "")


def _note_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    result = {
        "id": str(row[0]),
        "title": str(row[1]),
        "tags": _decode_tags(row[3]),
        "category": str(row[4] or ""),
        "priority": str(row[5]),
        "state": str(row[6]),
        "revision": int(row[7]),
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "excerpt": _excerpt(str(row[2])),
    }
    if include_content:
        result["content"] = str(row[2])
    return result


def _reminder_public(row: tuple[Any, ...], *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    state = str(row[8])
    next_run_at = str(row[5])
    try:
        overdue = state == "active" and _parse_utc(next_run_at) < current
    except ValueError:
        overdue = False
    result = {
        "id": str(row[0]),
        "note_id": str(row[1]) if row[1] else None,
        "title": str(row[2]),
        "body": str(row[3] or ""),
        "due_at": str(row[4]),
        "next_run_at": next_run_at,
        "timezone": str(row[6]),
        "repeat_rule": str(row[7]),
        "state": state,
        "revision": int(row[9]),
        "last_completed_at": str(row[10]) if row[10] else None,
        "completed_at": str(row[11]) if row[11] else None,
        "created_at": str(row[12]),
        "updated_at": str(row[13]),
        "overdue": overdue,
    }
    if len(row) > 14:
        result["note_title"] = str(row[14]) if row[14] else ""
    return result


def _note_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy ghi chú thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_MEMORY_NOTE_NOT_FOUND",
    )


def _reminder_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy reminder thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_MEMORY_REMINDER_NOT_FOUND",
    )


def _note_row(conn: Any, *, note_id: str, account_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        """SELECT id, title, content, tags_json, category, priority, state, revision, created_at, updated_at
           FROM web_memory_notes WHERE id=? AND account_id=?""",
        (note_id, account_id),
    ).fetchone()
    return tuple(row) if row else None


def _reminder_row(conn: Any, *, reminder_id: str, account_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        """SELECT r.id, r.note_id, r.title, r.body, r.due_at, r.next_run_at, r.timezone, r.repeat_rule,
                  r.state, r.revision, r.last_completed_at, r.completed_at, r.created_at, r.updated_at, n.title
           FROM web_memory_reminders r
           LEFT JOIN web_memory_notes n ON n.id=r.note_id AND n.account_id=r.account_id
           WHERE r.id=? AND r.account_id=?""",
        (reminder_id, account_id),
    ).fetchone()
    return tuple(row) if row else None


def _linked_note_active(conn: Any, *, note_id: str | None, account_id: str) -> bool:
    if not note_id:
        return True
    return bool(
        conn.execute(
            "SELECT 1 FROM web_memory_notes WHERE id=? AND account_id=? AND state='active'",
            (note_id, account_id),
        ).fetchone()
    )


def _escaped_like(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class NoteCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=MAX_NOTE_TITLE)
    content: str = Field(min_length=1, max_length=MAX_NOTE_CONTENT)
    tags: list[str] = Field(default_factory=list)
    category: str = Field(default="", max_length=MAX_CATEGORY)
    priority: str = Field(default="normal", max_length=16)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tiêu đề ghi chú", minimum=3, maximum=MAX_NOTE_TITLE)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _safe_content(value, label="Nội dung ghi chú", maximum=MAX_NOTE_CONTENT)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _single_line(value, label="Danh mục", minimum=0, maximum=MAX_CATEGORY, allow_empty=True)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return _priority(value)


class NoteUpdateRequest(NoteCreateRequest):
    expected_revision: int = Field(ge=1, le=1_000_000)


class RevisionMutationRequest(BaseModel):
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)


class ReminderCreateRequest(BaseModel):
    note_id: str | None = Field(default=None, max_length=36)
    title: str = Field(min_length=3, max_length=MAX_REMINDER_TITLE)
    body: str = Field(default="", max_length=MAX_REMINDER_BODY)
    due_at: str = Field(min_length=16, max_length=64)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=64)
    repeat_rule: str = Field(default="none", max_length=16)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("note_id")
    @classmethod
    def validate_note_id(cls, value: str | None) -> str | None:
        return _uuid(value, label="Mã ghi chú") if value else None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tiêu đề reminder", minimum=3, maximum=MAX_REMINDER_TITLE)

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        return _optional_content(value, label="Nội dung reminder", maximum=MAX_REMINDER_BODY)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return _timezone_name(value)

    @field_validator("repeat_rule")
    @classmethod
    def validate_repeat_rule(cls, value: str) -> str:
        return _repeat_rule(value)


class ReminderUpdateRequest(ReminderCreateRequest):
    expected_revision: int = Field(ge=1, le=1_000_000)


@router.get("/summary")
async def memory_summary(account: dict = Depends(require_account)):
    """Return small owner-scoped counts without returning note/reminder content."""
    _require_memory_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    now = datetime.now(timezone.utc)
    now_text = _utc_text(now)
    soon_text = _utc_text(now + timedelta(hours=24))
    with transaction() as conn:
        note_rows = conn.execute(
            "SELECT state, priority, COUNT(*) FROM web_memory_notes WHERE account_id=? GROUP BY state, priority",
            (account_id,),
        ).fetchall()
        reminder_rows = conn.execute(
            "SELECT state, COUNT(*) FROM web_memory_reminders WHERE account_id=? GROUP BY state",
            (account_id,),
        ).fetchall()
        overdue = conn.execute(
            """SELECT COUNT(*) FROM web_memory_reminders
               WHERE account_id=? AND state='active' AND next_run_at<?""",
            (account_id, now_text),
        ).fetchone()
        due_soon = conn.execute(
            """SELECT COUNT(*) FROM web_memory_reminders
               WHERE account_id=? AND state='active' AND next_run_at>=? AND next_run_at<=?""",
            (account_id, now_text, soon_text),
        ).fetchone()
    notes_by_state = {str(row[0]): int(row[2]) for row in note_rows}
    priorities = {priority: 0 for priority in sorted(PRIORITIES)}
    for state, priority, count in note_rows:
        if str(state) == "active" and str(priority) in priorities:
            priorities[str(priority)] += int(count)
    reminders_by_state = {str(row[0]): int(row[1]) for row in reminder_rows}
    return envelope(
        True,
        "Tổng quan Memory Center của Web account hiện tại.",
        data={
            "notes": {"active": notes_by_state.get("active", 0), "archived": notes_by_state.get("archived", 0), "priorities": priorities},
            "reminders": {
                "active": reminders_by_state.get("active", 0),
                "paused": reminders_by_state.get("paused", 0),
                "completed": reminders_by_state.get("completed", 0),
                "cancelled": reminders_by_state.get("cancelled", 0),
                "overdue": int(overdue[0] or 0) if overdue else 0,
                "due_soon": int(due_soon[0] or 0) if due_soon else 0,
            },
            "notification_delivery": "web_view_only",
        },
        status_name="read_only",
    )


@router.get("/notes")
async def list_notes(
    limit: int = 30,
    state: str = "active",
    q: str = "",
    priority: str = "",
    category: str = "",
    account: dict = Depends(require_account),
):
    """Search/list bounded note metadata only for the signed Web owner."""
    _require_memory_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    state_filter = str(state or "active").strip().lower()
    if state_filter not in {*NOTE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái ghi chú không hợp lệ")
    priority_filter = str(priority or "").strip().lower()
    if priority_filter and priority_filter not in PRIORITIES:
        raise HTTPException(status_code=422, detail="Bộ lọc priority không hợp lệ")
    query = _validated_single_line(q, label="Từ khóa tìm kiếm", minimum=0, maximum=80, allow_empty=True)
    category_filter = _validated_single_line(category, label="Danh mục", minimum=0, maximum=MAX_CATEGORY, allow_empty=True)
    if query and (SECRET_ASSIGNMENT_PATTERN.search(query) or BEARER_PATTERN.search(query) or CARD_LIKE_PATTERN.search(query)):
        raise HTTPException(status_code=422, detail="Từ khóa tìm kiếm không nhận secret, token, mật khẩu hoặc số thẻ")
    account_id = str(account["id"])
    clauses = ["account_id=?"]
    params: list[Any] = [account_id]
    if state_filter != "all":
        clauses.append("state=?")
        params.append(state_filter)
    if priority_filter:
        clauses.append("priority=?")
        params.append(priority_filter)
    if category_filter:
        clauses.append("category LIKE ? ESCAPE '\\'")
        params.append(f"%{_escaped_like(category_filter)}%")
    if query:
        like = f"%{_escaped_like(query)}%"
        clauses.append("(title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\' OR tags_json LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\')")
        params.extend([like, like, like, like])
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, title, content, tags_json, category, priority, state, revision, created_at, updated_at
                FROM web_memory_notes WHERE {' AND '.join(clauses)}
                ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'important' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                         updated_at DESC, id DESC LIMIT ?""",
            (*params, bounded_limit + 1),
        ).fetchall()
        facet_rows = conn.execute(
            """SELECT tags_json, category FROM web_memory_notes
               WHERE account_id=? AND state='active' ORDER BY updated_at DESC LIMIT 300""",
            (account_id,),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    categories: dict[str, int] = {}
    tags: dict[str, int] = {}
    for tags_json, facet_category in facet_rows:
        if str(facet_category or ""):
            normalized_category = str(facet_category)
            categories[normalized_category] = categories.get(normalized_category, 0) + 1
        for tag in _decode_tags(tags_json):
            tags[tag] = tags.get(tag, 0) + 1
    return envelope(
        True,
        "Danh sách ghi chú riêng của Web account hiện tại.",
        data={
            "items": [_note_public(tuple(row)) for row in rows[:bounded_limit]],
            "has_more": has_more,
            "facets": {
                "categories": [{"name": name, "count": count} for name, count in sorted(categories.items(), key=lambda item: (-item[1], item[0].casefold()))[:20]],
                "tags": [{"name": name, "count": count} for name, count in sorted(tags.items(), key=lambda item: (-item[1], item[0].casefold()))[:30]],
            },
        },
        status_name="read_only",
    )


@router.post("/notes")
async def create_note(payload: NoteCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create an owner-scoped Web note without Bot/provider/payment state."""
    _require_memory_enabled()
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    tags_json = json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":"))
    fingerprint = _fingerprint({
        "title": payload.title,
        "content_sha256": _content_hash(payload.content),
        "tags": payload.tags,
        "category": payload.category,
        "priority": payload.priority,
    })

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_memory_notes WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_NOTES_PER_ACCOUNT:
            return envelope(False, "Đã đạt giới hạn ghi chú active của Web account. Hãy archive ghi chú cũ trước.", status_name="guarded", error_code="WEB_MEMORY_NOTE_LIMIT")
        note_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_memory_notes
               (id, account_id, title, content, tags_json, category, priority, state, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?)""",
            (note_id, account_id, payload.title, payload.content, tags_json, payload.category, payload.priority, now, now),
        )
        conn.execute(
            """INSERT INTO web_memory_note_versions
               (id, note_id, account_id, revision, title, content, tags_json, category, priority, created_at)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), note_id, account_id, payload.title, payload.content, tags_json, payload.category, payload.priority, now),
        )
        _event(conn, account_id=account_id, action="note_created", note_id=note_id)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.memory.note.create",
            request_id=_request_id(request),
            target=note_id,
            detail="web-owned memory note created",
        )
        note = _note_public((note_id, payload.title, payload.content, tags_json, payload.category, payload.priority, "active", 1, now, now))
        return envelope(True, "Đã lưu ghi chú trong Memory Center của Web.", data={"note": note}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:note:create", key, fingerprint, operation)


@router.get("/notes/{note_id}")
async def get_note(note_id: str, account: dict = Depends(require_account)):
    """Read one note, bounded version metadata and linked reminder summaries."""
    _require_memory_enabled()
    note_id = _uuid(note_id, label="Mã ghi chú")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _note_row(conn, note_id=note_id, account_id=account_id)
        if not row:
            return _note_not_found()
        versions = conn.execute(
            """SELECT revision, title, created_at FROM web_memory_note_versions
               WHERE note_id=? AND account_id=? ORDER BY revision DESC LIMIT 50""",
            (note_id, account_id),
        ).fetchall()
        reminders = conn.execute(
            """SELECT r.id, r.note_id, r.title, r.body, r.due_at, r.next_run_at, r.timezone, r.repeat_rule,
                      r.state, r.revision, r.last_completed_at, r.completed_at, r.created_at, r.updated_at, n.title
               FROM web_memory_reminders r
               LEFT JOIN web_memory_notes n ON n.id=r.note_id AND n.account_id=r.account_id
               WHERE r.note_id=? AND r.account_id=? ORDER BY r.updated_at DESC LIMIT 20""",
            (note_id, account_id),
        ).fetchall()
    return envelope(
        True,
        "Đã nạp ghi chú riêng từ Memory Center.",
        data={
            "note": _note_public(row, include_content=True),
            "versions": [{"revision": int(item[0]), "title": str(item[1]), "created_at": str(item[2])} for item in versions],
            "reminders": [_reminder_public(tuple(item)) for item in reminders],
        },
        status_name="read_only",
    )


@router.post("/notes/{note_id}/update")
async def update_note(note_id: str, payload: NoteUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Update a note with optimistic revision control and an immutable history."""
    _require_memory_enabled()
    note_id = _uuid(note_id, label="Mã ghi chú")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    tags_json = json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":"))
    fingerprint = _fingerprint({
        "expected_revision": payload.expected_revision,
        "title": payload.title,
        "content_sha256": _content_hash(payload.content),
        "tags": payload.tags,
        "category": payload.category,
        "priority": payload.priority,
    })

    def operation(conn: Any) -> dict[str, Any]:
        current = _note_row(conn, note_id=note_id, account_id=account_id)
        if not current:
            return _note_not_found()
        if str(current[6]) != "active":
            return envelope(False, "Ghi chú đã archive không thể chỉnh sửa. Hãy khôi phục trước.", status_name="guarded", error_code="WEB_MEMORY_NOTE_ARCHIVED")
        current_revision = int(current[7])
        if current_revision != payload.expected_revision:
            return envelope(False, "Ghi chú đã có phiên bản mới. Hãy tải lại trước khi lưu.", data={"current_revision": current_revision}, status_name="guarded", error_code="WEB_MEMORY_NOTE_CONFLICT")
        next_revision = current_revision + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_memory_notes
               SET title=?, content=?, tags_json=?, category=?, priority=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=? AND state='active'""",
            (payload.title, payload.content, tags_json, payload.category, payload.priority, next_revision, now, note_id, account_id, current_revision),
        )
        conn.execute(
            """INSERT INTO web_memory_note_versions
               (id, note_id, account_id, revision, title, content, tags_json, category, priority, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), note_id, account_id, next_revision, payload.title, payload.content, tags_json, payload.category, payload.priority, now),
        )
        _event(conn, account_id=account_id, action="note_updated", note_id=note_id)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.memory.note.update", request_id=_request_id(request), target=note_id, detail=f"web-owned memory note revision:{next_revision}")
        note = _note_public((note_id, payload.title, payload.content, tags_json, payload.category, payload.priority, "active", next_revision, current[8], now))
        return envelope(True, "Đã lưu phiên bản mới của ghi chú.", data={"note": note}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:note:{note_id}:update", key, fingerprint, operation)


@router.post("/notes/{note_id}/archive")
async def archive_note(note_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    """Soft-archive a note; linked reminders remain explicit and untouched."""
    _require_memory_enabled()
    note_id = _uuid(note_id, label="Mã ghi chú")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "action": "archive"})

    def operation(conn: Any) -> dict[str, Any]:
        current = _note_row(conn, note_id=note_id, account_id=account_id)
        if not current:
            return _note_not_found()
        if str(current[6]) == "archived":
            return envelope(False, "Ghi chú đã archive trước đó.", status_name="guarded", error_code="WEB_MEMORY_NOTE_ARCHIVED")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Ghi chú đã có phiên bản mới. Hãy tải lại trước khi archive.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_MEMORY_NOTE_CONFLICT")
        next_revision = int(current[7]) + 1
        now = utc_now()
        conn.execute("UPDATE web_memory_notes SET state='archived', revision=?, updated_at=? WHERE id=? AND account_id=?", (next_revision, now, note_id, account_id))
        _event(conn, account_id=account_id, action="note_archived", note_id=note_id)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.memory.note.archive", request_id=_request_id(request), target=note_id, detail="web-owned memory note archived")
        note = _note_public((note_id, current[1], current[2], current[3], current[4], current[5], "archived", next_revision, current[8], now))
        return envelope(True, "Đã archive ghi chú. Reminder đã liên kết không bị tự động thay đổi.", data={"note": note}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:note:{note_id}:archive", key, fingerprint, operation)


@router.post("/notes/{note_id}/restore")
async def restore_note(note_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    """Restore a soft-archived note, never recovering Bot-owned data."""
    _require_memory_enabled()
    note_id = _uuid(note_id, label="Mã ghi chú")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "action": "restore"})

    def operation(conn: Any) -> dict[str, Any]:
        current = _note_row(conn, note_id=note_id, account_id=account_id)
        if not current:
            return _note_not_found()
        if str(current[6]) != "archived":
            return envelope(False, "Ghi chú đang active nên không cần khôi phục.", status_name="guarded", error_code="WEB_MEMORY_NOTE_ACTIVE")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Ghi chú đã có phiên bản mới. Hãy tải lại trước khi khôi phục.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_MEMORY_NOTE_CONFLICT")
        next_revision = int(current[7]) + 1
        now = utc_now()
        conn.execute("UPDATE web_memory_notes SET state='active', revision=?, updated_at=? WHERE id=? AND account_id=?", (next_revision, now, note_id, account_id))
        _event(conn, account_id=account_id, action="note_restored", note_id=note_id)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.memory.note.restore", request_id=_request_id(request), target=note_id, detail="web-owned memory note restored")
        note = _note_public((note_id, current[1], current[2], current[3], current[4], current[5], "active", next_revision, current[8], now))
        return envelope(True, "Đã khôi phục ghi chú vào Memory Center.", data={"note": note}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:note:{note_id}:restore", key, fingerprint, operation)


@router.post("/notes/{note_id}/restore-version/{revision}")
async def restore_note_version(note_id: str, revision: int, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    """Restore an old note snapshot as a new version after conflict checking."""
    _require_memory_enabled()
    note_id = _uuid(note_id, label="Mã ghi chú")
    if not 1 <= int(revision) <= 1_000_000:
        raise HTTPException(status_code=422, detail="Phiên bản ghi chú không hợp lệ")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "restore_revision": int(revision)})

    def operation(conn: Any) -> dict[str, Any]:
        current = _note_row(conn, note_id=note_id, account_id=account_id)
        if not current:
            return _note_not_found()
        if str(current[6]) != "active":
            return envelope(False, "Ghi chú đã archive không thể khôi phục phiên bản. Hãy khôi phục ghi chú trước.", status_name="guarded", error_code="WEB_MEMORY_NOTE_ARCHIVED")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Ghi chú đã có phiên bản mới. Hãy tải lại trước khi khôi phục.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_MEMORY_NOTE_CONFLICT")
        source = conn.execute(
            """SELECT title, content, tags_json, category, priority FROM web_memory_note_versions
               WHERE note_id=? AND account_id=? AND revision=?""",
            (note_id, account_id, int(revision)),
        ).fetchone()
        if not source:
            return envelope(False, "Không tìm thấy phiên bản ghi chú thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_MEMORY_NOTE_VERSION_NOT_FOUND")
        next_revision = int(current[7]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_memory_notes SET title=?, content=?, tags_json=?, category=?, priority=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=? AND state='active'""",
            (str(source[0]), str(source[1]), str(source[2]), str(source[3]), str(source[4]), next_revision, now, note_id, account_id, int(current[7])),
        )
        conn.execute(
            """INSERT INTO web_memory_note_versions
               (id, note_id, account_id, revision, title, content, tags_json, category, priority, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), note_id, account_id, next_revision, str(source[0]), str(source[1]), str(source[2]), str(source[3]), str(source[4]), now),
        )
        _event(conn, account_id=account_id, action="note_version_restored", note_id=note_id)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.memory.note.restore_version", request_id=_request_id(request), target=note_id, detail=f"web-owned memory note restored_from:{int(revision)}")
        note = _note_public((note_id, str(source[0]), str(source[1]), str(source[2]), str(source[3]), str(source[4]), "active", next_revision, current[8], now))
        return envelope(True, "Đã khôi phục phiên bản ghi chú thành phiên bản mới.", data={"note": note}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:note:{note_id}:restore-version:{int(revision)}", key, fingerprint, operation)


@router.get("/reminders")
async def list_reminders(limit: int = 50, state: str = "active", account: dict = Depends(require_account)):
    """List reminders for one account; overdue is a UI state, not a delivery claim."""
    _require_memory_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    state_filter = str(state or "active").strip().lower()
    if state_filter not in {*REMINDER_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái reminder không hợp lệ")
    account_id = str(account["id"])
    clauses = ["r.account_id=?"]
    params: list[Any] = [account_id]
    if state_filter != "all":
        clauses.append("r.state=?")
        params.append(state_filter)
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT r.id, r.note_id, r.title, r.body, r.due_at, r.next_run_at, r.timezone, r.repeat_rule,
                      r.state, r.revision, r.last_completed_at, r.completed_at, r.created_at, r.updated_at, n.title
               FROM web_memory_reminders r
               LEFT JOIN web_memory_notes n ON n.id=r.note_id AND n.account_id=r.account_id
               WHERE {' AND '.join(clauses)}
               ORDER BY CASE r.state WHEN 'active' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END,
                        r.next_run_at ASC, r.updated_at DESC, r.id DESC LIMIT ?""",
            (*params, bounded_limit + 1),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    now = datetime.now(timezone.utc)
    return envelope(
        True,
        "Danh sách reminder riêng của Web account hiện tại.",
        data={"items": [_reminder_public(tuple(row), now=now) for row in rows[:bounded_limit]], "has_more": has_more, "notification_delivery": "web_view_only"},
        status_name="read_only",
    )


@router.post("/reminders")
async def create_reminder(payload: ReminderCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create a reminder without starting a background sender or Bot task."""
    _require_memory_enabled()
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    due_at = _validated_due_at(payload.due_at, payload.timezone)
    fingerprint = _fingerprint({
        "note_id": payload.note_id or "",
        "title": payload.title,
        "body_sha256": _content_hash(payload.body),
        "due_at": due_at,
        "timezone": payload.timezone,
        "repeat_rule": payload.repeat_rule,
    })

    def operation(conn: Any) -> dict[str, Any]:
        if not _linked_note_active(conn, note_id=payload.note_id, account_id=account_id):
            return envelope(False, "Ghi chú liên kết không tồn tại hoặc đã archive.", status_name="guarded", error_code="WEB_MEMORY_NOTE_NOT_FOUND")
        count = conn.execute(
            "SELECT COUNT(*) FROM web_memory_reminders WHERE account_id=? AND state IN ('active','paused')",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_ACTIVE_REMINDERS_PER_ACCOUNT:
            return envelope(False, "Đã đạt giới hạn reminder active/paused của Web account.", status_name="guarded", error_code="WEB_MEMORY_REMINDER_LIMIT")
        reminder_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_memory_reminders
               (id, account_id, note_id, title, body, due_at, next_run_at, timezone, repeat_rule, state,
                revision, last_completed_at, completed_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, NULL, NULL, ?, ?)""",
            (reminder_id, account_id, payload.note_id, payload.title, payload.body, due_at, due_at, payload.timezone, payload.repeat_rule, now, now),
        )
        _event(conn, account_id=account_id, action="reminder_created", note_id=payload.note_id, reminder_id=reminder_id)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.memory.reminder.create", request_id=_request_id(request), target=reminder_id, detail="web-owned reminder created; no external delivery")
        reminder = _reminder_public((reminder_id, payload.note_id, payload.title, payload.body, due_at, due_at, payload.timezone, payload.repeat_rule, "active", 1, None, None, now, now, ""))
        return envelope(True, "Đã tạo reminder trong Web Memory Center. Trang Web sẽ hiển thị đúng hạn; chưa gửi Telegram/email/push.", data={"reminder": reminder}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:reminder:create", key, fingerprint, operation)


@router.post("/reminders/{reminder_id}/update")
async def update_reminder(reminder_id: str, payload: ReminderUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Edit only active/paused reminders with optimistic revision protection."""
    _require_memory_enabled()
    reminder_id = _uuid(reminder_id, label="Mã reminder")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    due_at = _validated_due_at(payload.due_at, payload.timezone)
    fingerprint = _fingerprint({
        "expected_revision": payload.expected_revision,
        "note_id": payload.note_id or "",
        "title": payload.title,
        "body_sha256": _content_hash(payload.body),
        "due_at": due_at,
        "timezone": payload.timezone,
        "repeat_rule": payload.repeat_rule,
    })

    def operation(conn: Any) -> dict[str, Any]:
        current = _reminder_row(conn, reminder_id=reminder_id, account_id=account_id)
        if not current:
            return _reminder_not_found()
        if str(current[8]) not in {"active", "paused"}:
            return envelope(False, "Reminder đã hoàn tất hoặc hủy không thể chỉnh sửa.", status_name="guarded", error_code="WEB_MEMORY_REMINDER_TERMINAL")
        if int(current[9]) != payload.expected_revision:
            return envelope(False, "Reminder đã có phiên bản mới. Hãy tải lại trước khi lưu.", data={"current_revision": int(current[9])}, status_name="guarded", error_code="WEB_MEMORY_REMINDER_CONFLICT")
        if not _linked_note_active(conn, note_id=payload.note_id, account_id=account_id):
            return envelope(False, "Ghi chú liên kết không tồn tại hoặc đã archive.", status_name="guarded", error_code="WEB_MEMORY_NOTE_NOT_FOUND")
        next_revision = int(current[9]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_memory_reminders
               SET note_id=?, title=?, body=?, due_at=?, next_run_at=?, timezone=?, repeat_rule=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (payload.note_id, payload.title, payload.body, due_at, due_at, payload.timezone, payload.repeat_rule, next_revision, now, reminder_id, account_id, int(current[9])),
        )
        _event(conn, account_id=account_id, action="reminder_updated", note_id=payload.note_id, reminder_id=reminder_id)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.memory.reminder.update", request_id=_request_id(request), target=reminder_id, detail=f"web-owned reminder revision:{next_revision}")
        reminder = _reminder_public((reminder_id, payload.note_id, payload.title, payload.body, due_at, due_at, payload.timezone, payload.repeat_rule, str(current[8]), next_revision, current[10], current[11], current[12], now, ""))
        return envelope(True, "Đã cập nhật reminder trong Web Memory Center.", data={"reminder": reminder}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:reminder:{reminder_id}:update", key, fingerprint, operation)


def _reminder_state_mutation(
    *,
    reminder_id: str,
    payload: RevisionMutationRequest,
    request: Request,
    account: dict,
    action: str,
) -> dict[str, Any]:
    """Apply an explicit state transition with no hidden notification side effect."""
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "action": action})

    def operation(conn: Any) -> dict[str, Any]:
        current = _reminder_row(conn, reminder_id=reminder_id, account_id=account_id)
        if not current:
            return _reminder_not_found()
        current_state = str(current[8])
        current_revision = int(current[9])
        if current_revision != payload.expected_revision:
            return envelope(False, "Reminder đã có phiên bản mới. Hãy tải lại trước khi tiếp tục.", data={"current_revision": current_revision}, status_name="guarded", error_code="WEB_MEMORY_REMINDER_CONFLICT")
        now = utc_now()
        next_state = current_state
        next_run_at = str(current[5])
        last_completed_at = current[10]
        completed_at = current[11]
        if action == "complete":
            if current_state != "active":
                return envelope(False, "Chỉ reminder active mới có thể hoàn tất.", status_name="guarded", error_code="WEB_MEMORY_REMINDER_STATE_INVALID")
            last_completed_at = now
            if str(current[7]) == "none":
                next_state = "completed"
                completed_at = now
            else:
                try:
                    next_run_at = _next_repeat_after(str(current[5]), str(current[7]), str(current[6]))
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail="Không thể tính chu kỳ reminder an toàn") from exc
                next_state = "active"
                completed_at = None
        elif action == "pause":
            if current_state != "active":
                return envelope(False, "Chỉ reminder active mới có thể tạm dừng.", status_name="guarded", error_code="WEB_MEMORY_REMINDER_STATE_INVALID")
            next_state = "paused"
        elif action == "resume":
            if current_state != "paused":
                return envelope(False, "Chỉ reminder paused mới có thể tiếp tục.", status_name="guarded", error_code="WEB_MEMORY_REMINDER_STATE_INVALID")
            next_state = "active"
            try:
                if _parse_utc(next_run_at) <= datetime.now(timezone.utc):
                    next_run_at = _next_repeat_after(next_run_at, str(current[7]), str(current[6])) if str(current[7]) != "none" else _utc_text(datetime.now(timezone.utc) + timedelta(minutes=5))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Không thể tiếp tục reminder an toàn") from exc
        elif action == "cancel":
            if current_state not in {"active", "paused"}:
                return envelope(False, "Reminder đã ở trạng thái cuối.", status_name="guarded", error_code="WEB_MEMORY_REMINDER_STATE_INVALID")
            next_state = "cancelled"
        else:
            raise RuntimeError("Unknown memory reminder action")
        next_revision = current_revision + 1
        conn.execute(
            """UPDATE web_memory_reminders
               SET state=?, next_run_at=?, revision=?, last_completed_at=?, completed_at=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (next_state, next_run_at, next_revision, last_completed_at, completed_at, now, reminder_id, account_id, current_revision),
        )
        _event(conn, account_id=account_id, action=f"reminder_{action}", note_id=str(current[1]) if current[1] else None, reminder_id=reminder_id)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action=f"web.memory.reminder.{action}", request_id=_request_id(request), target=reminder_id, detail="web-owned reminder state changed; no external delivery")
        reminder = _reminder_public((reminder_id, current[1], current[2], current[3], current[4], next_run_at, current[6], current[7], next_state, next_revision, last_completed_at, completed_at, current[12], now, current[14]))
        message = {
            "complete": "Đã cập nhật trạng thái reminder.",
            "pause": "Đã tạm dừng reminder.",
            "resume": "Đã tiếp tục reminder.",
            "cancel": "Đã hủy reminder.",
        }[action]
        return envelope(True, message, data={"reminder": reminder}, status_name="completed")

    return _idempotent(f"web-memory:{account_id}:reminder:{reminder_id}:{action}", key, fingerprint, operation)


@router.post("/reminders/{reminder_id}/complete")
async def complete_reminder(reminder_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_memory_enabled()
    return _reminder_state_mutation(reminder_id=_uuid(reminder_id, label="Mã reminder"), payload=payload, request=request, account=account, action="complete")


@router.post("/reminders/{reminder_id}/pause")
async def pause_reminder(reminder_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_memory_enabled()
    return _reminder_state_mutation(reminder_id=_uuid(reminder_id, label="Mã reminder"), payload=payload, request=request, account=account, action="pause")


@router.post("/reminders/{reminder_id}/resume")
async def resume_reminder(reminder_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_memory_enabled()
    return _reminder_state_mutation(reminder_id=_uuid(reminder_id, label="Mã reminder"), payload=payload, request=request, account=account, action="resume")


@router.post("/reminders/{reminder_id}/cancel")
async def cancel_reminder(reminder_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_memory_enabled()
    return _reminder_state_mutation(reminder_id=_uuid(reminder_id, label="Mã reminder"), payload=payload, request=request, account=account, action="cancel")


@router.get("/events")
async def memory_events(limit: int = 40, account: dict = Depends(require_account)):
    """Return only high-level Web memory actions, never titles/content/audit detail."""
    _require_memory_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            """SELECT id, note_id, reminder_id, action, created_at FROM web_memory_events
               WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
            (account_id, bounded_limit),
        ).fetchall()
    return envelope(
        True,
        "Hoạt động Memory Center của Web account hiện tại.",
        data={"items": [{"id": str(row[0]), "note_id": str(row[1]) if row[1] else None, "reminder_id": str(row[2]) if row[2] else None, "action": str(row[3]), "created_at": str(row[4])} for row in rows]},
        status_name="read_only",
    )
