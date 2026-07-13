"""Professional, Web-owned Support Desk for signed TOAN AAS accounts.

This module deliberately improves the useful ticket/feedback workflows from
the frozen Telegram Bot without copying its database or conversation state.
It never reads or writes Bot ticket tables, sends Telegram/email, calls a
provider, changes a payment, wallet/Xu, refund, or job.  Every case, message
and event is private to a signed Web account and every operator write has a
server-side role, CSRF, confirmation, idempotency and audit trail.
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
from copyfast_db import ensure_copyfast_schema, support_desk_enabled, transaction, utc_now


router = APIRouter(prefix="/api/v1/support", tags=["Web Support Desk"])

CASE_CATEGORIES = frozenset({
    "payment_topup", "image_error", "video_error", "document_pdf",
    "package_combo", "refund", "feature_request", "lead_consulting",
    "general_support", "service_consulting", "premium_lead",
    "custom_bot_lead", "other",
})
CASE_PRIORITIES = frozenset({"low", "normal", "high", "urgent"})
CASE_STATES = frozenset({
    "new", "reviewing", "waiting_user", "waiting_provider",
    "refund_pending", "resolved", "closed",
})
VISIBLE_MESSAGE_ROLES = frozenset({"customer", "operator"})
MESSAGE_VISIBILITIES = frozenset({"public", "internal"})
# Customer timelines disclose only customer actions and a public operator
# reply.  Internal notes/triage events remain available to staff in the
# separate admin view, even though the customer can always see the current
# case state itself.
CUSTOMER_VISIBLE_EVENT_ACTIONS = frozenset({
    "case_created", "customer_replied", "customer_close", "customer_reopen",
    "operator_replied_public",
})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"token|client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)"
    r"\b\s*(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE)
KNOWN_SECRET_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|"
    r"gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|"
    r"xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|"
    r"AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|"
    r"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
VERIFICATION_PATTERN = re.compile(
    r"\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|"
    r"ma\s*(?:xac\s*(?:minh|thuc)|otp)|verification\s+(?:code|token)|"
    r"one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b",
    re.IGNORECASE,
)
MANUAL_PAYMENT_PATTERN = re.compile(
    r"\b(?:tx(?:id|n)?|transaction\s+(?:hash|id|reference|no\.?|number)|"
    r"mã\s*(?:(?:giao\s*)?(?:dịch|gd)|tham\s*chiếu|thanh\s*toán)|"
    r"ma\s*(?:(?:giao\s*)?(?:dich|gd)|tham\s*chieu|thanh\s*toan)|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|"
    r"số\s*tài\s*khoản|so\s*tai\s*khoan|stk|"
    r"tài\s*khoản\s*(?:ngân\s*hàng|bank)|tai\s*khoan\s*(?:ngan\s*hang|bank)|"
    r"bank\s+account|account\s+(?:number|no|id)|qr\s*(?:code|thanh\s*toán|thanh\s*toan)?)\b",
    re.IGNORECASE,
)
# Card-shaped numbers arrive with copy/paste separators as well as spaces and
# hyphens.  Permit only separators between digits so unrelated numbers from a
# prose sentence cannot be joined into a false candidate.
CARD_CANDIDATE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
MAX_ACTIVE_CASES = 100
MAX_MESSAGES_PER_CASE = 500
MAX_SUBJECT = 180
MAX_DETAIL = 4_000
MAX_REPLY = 4_000
MAX_OPERATION_NOTE = 360


def _require_support_enabled() -> None:
    if not support_desk_enabled():
        raise HTTPException(
            status_code=503,
            detail="Web Support Desk đang tạm dừng để bảo trì. WEBAPP_SUPPORT_DESK_ENABLED chưa được bật.",
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


def _contains_sensitive(value: str) -> bool:
    text = str(value or "")
    if any(pattern.search(text) for pattern in (
        SECRET_ASSIGNMENT_PATTERN,
        BEARER_PATTERN,
        KNOWN_SECRET_TOKEN_PATTERN,
        VERIFICATION_PATTERN,
    )):
        return True
    # A support narrative never needs a card-shaped 13–19 digit sequence.
    # Reject it before deciding whether it happens to pass a Luhn check; that
    # avoids retaining a mistyped or partial card number in a private ticket.
    return bool(CARD_CANDIDATE_PATTERN.search(text))


def _safe_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if "\x00" in text or (not text and not allow_empty) or len(text) < minimum or len(text) > maximum:
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _contains_sensitive(text):
        raise ValueError(f"{label} không nhận secret, token, OTP/CVV hoặc số thẻ")
    if text and MANUAL_PAYMENT_PATTERN.search(text):
        raise ValueError("Web Support Desk không nhận bill, TXID, số tài khoản hoặc QR thanh toán")
    return text


def _safe_text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if "\x00" in text or (not text and not allow_empty) or len(text) < minimum or len(text) > maximum:
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _contains_sensitive(text):
        raise ValueError(f"{label} không nhận secret, token, OTP/CVV hoặc số thẻ")
    if text and MANUAL_PAYMENT_PATTERN.search(text):
        raise ValueError("Web Support Desk không nhận bill, TXID, số tài khoản hoặc QR thanh toán")
    return text


def _validated_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    try:
        return _safe_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _category(value: Any) -> str:
    normalized = str(value or "general_support").strip().lower()
    if normalized not in CASE_CATEGORIES:
        raise ValueError("Nhóm yêu cầu hỗ trợ không hợp lệ")
    return normalized


def _priority(value: Any) -> str:
    normalized = str(value or "normal").strip().lower()
    if normalized not in CASE_PRIORITIES:
        raise ValueError("Mức ưu tiên không hợp lệ")
    return normalized


def _state(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in CASE_STATES:
        raise ValueError("Trạng thái hỗ trợ không hợp lệ")
    return normalized


def _visibility(value: Any) -> str:
    normalized = str(value or "public").strip().lower()
    if normalized not in MESSAGE_VISIBILITIES:
        raise ValueError("Phạm vi phản hồi không hợp lệ")
    return normalized


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _content_hash(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _idempotent(scope: str, key: str, request_fingerprint: str, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored = str(existing[1] or "")
            if not stored or not hmac.compare_digest(stored, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                response = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Support Desk không hợp lệ") from exc
            if isinstance(response, dict):
                return response
            raise HTTPException(status_code=409, detail="Bản ghi idempotency Support Desk không hợp lệ")
        response = operation(conn)
        conn.execute(
            """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
        )
    return response


def _event(conn: Any, *, case_id: str, account_id: str, actor_account_id: str | None, action: str, state: str) -> None:
    conn.execute(
        """INSERT INTO web_support_events (id, case_id, account_id, actor_account_id, action, state, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), case_id, account_id, actor_account_id or None, action, state, utc_now()),
    )


def _state_timestamps(current: tuple[Any, ...], next_state: str, now: str) -> tuple[str | None, str | None]:
    """Return truthful resolved/closed timestamps for a Support transition."""
    current_state = str(current[6])
    if next_state == "resolved":
        # A same-state internal note/priority change must not rewrite the
        # original resolution moment.  A real transition into `resolved`
        # receives the current timestamp instead.
        resolved_at = str(current[11]) if current_state == "resolved" and current[11] else now
        return resolved_at, None
    if next_state == "closed":
        # Closing a previously resolved case preserves the resolution moment;
        # closing an unresolved case never manufactures one. Repeating a
        # no-op close leaves the closed moment untouched.
        closed_at = str(current[12]) if current_state == "closed" and current[12] else now
        return (str(current[11]) if current[11] else None), closed_at
    # Any active/review/pending state is not resolved or closed.  This also
    # clears stale timestamps when staff/customer reopens a prior case.
    return None, None


def _case_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy yêu cầu thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_SUPPORT_CASE_NOT_FOUND")


def _case_row(conn: Any, *, case_id: str, account_id: str | None = None) -> tuple[Any, ...] | None:
    clauses = ["c.id=?"]
    params: list[Any] = [case_id]
    if account_id:
        clauses.append("c.account_id=?")
        params.append(account_id)
    row = conn.execute(
        f"""SELECT c.id, c.account_id, c.category, c.priority, c.subject, c.initial_detail, c.state, c.revision,
                   c.created_at, c.updated_at, c.last_public_message_at, c.resolved_at, c.closed_at,
                   a.display_name, a.email
              FROM web_support_cases c JOIN web_accounts a ON a.id=c.account_id
              WHERE {' AND '.join(clauses)}""",
        tuple(params),
    ).fetchone()
    return tuple(row) if row else None


def _excerpt(value: str, length: int = 200) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:length] + ("…" if len(text) > length else "")


def _mask_email(value: str) -> str:
    email = str(value or "").strip()
    if "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[:1]}***@{domain}"


def _case_public(row: tuple[Any, ...], *, include_detail: bool = False, admin: bool = False) -> dict[str, Any]:
    result = {
        "id": str(row[0]),
        "category": str(row[2]),
        "priority": str(row[3]),
        "subject": str(row[4]),
        "state": str(row[6]),
        "revision": int(row[7]),
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "last_public_message_at": str(row[10]),
        "resolved_at": str(row[11]) if row[11] else None,
        "closed_at": str(row[12]) if row[12] else None,
        "excerpt": _excerpt(str(row[5])),
    }
    if include_detail:
        result["detail"] = str(row[5])
    if admin:
        result["customer"] = {"display_name": str(row[13] or "Khách hàng"), "email_masked": _mask_email(str(row[14] or ""))}
    return result


def _event_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {"id": str(row[0]), "action": str(row[1]), "state": str(row[2]), "created_at": str(row[3])}


def _message_public(row: tuple[Any, ...], *, admin: bool) -> dict[str, Any]:
    result = {
        "id": str(row[0]),
        "author_role": str(row[1]),
        "visibility": str(row[2]),
        "body": str(row[3]),
        "created_at": str(row[4]),
    }
    if admin:
        result["author_display_name"] = str(row[5] or "")
    return result


def _staff_role(account: dict) -> str:
    role = str(account.get("role") or "").strip().lower()
    # `role` is read from the server-side signed-session account record. It
    # never accepts a browser-supplied admin ID, body field or an email/env
    # allowlist: password registration does not itself prove email ownership.
    # Support roles must be provisioned directly in the protected Web account
    # store by an approved administrator/deployment process.
    if role in {"admin", "support_manager"}:
        return "manager"
    if role == "support_operator":
        return "operator"
    return ""


def _require_staff(account: dict) -> str:
    role = _staff_role(account)
    if not role:
        raise HTTPException(status_code=403, detail="Quyền Support Desk chưa được cấp cho signed Web account này")
    return role


def require_support_staff(account: dict) -> str:
    """Public HTML/API guard for the Web-owned support operator surface.

    This intentionally does not ask the Bot core for a Telegram role.  Staff
    access is derived only from the signed Web account's server-side role or
    a protected, server-side role value, keeping the Support Desk independent
    while preserving the stricter canonical guard for all other Admin ERP
    routes. Email strings and browser inputs can never grant this role.
    """
    return _require_staff(account)


class SupportRequestModel(BaseModel):
    """Strict request envelope: ignored browser fields are never a feature."""
    model_config = ConfigDict(extra="forbid")


class CaseCreateRequest(SupportRequestModel):
    category: str = Field(default="general_support", max_length=48)
    priority: str = Field(default="normal", max_length=16)
    subject: str = Field(min_length=3, max_length=MAX_SUBJECT)
    detail: str = Field(min_length=3, max_length=MAX_DETAIL)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _category(value)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return _priority(value)

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        return _safe_line(value, label="Chủ đề", minimum=3, maximum=MAX_SUBJECT)

    @field_validator("detail")
    @classmethod
    def validate_detail(cls, value: str) -> str:
        return _safe_text(value, label="Nội dung", minimum=3, maximum=MAX_DETAIL)


class CaseReplyRequest(SupportRequestModel):
    body: str = Field(min_length=1, max_length=MAX_REPLY)
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        return _safe_text(value, label="Phản hồi", minimum=1, maximum=MAX_REPLY)


class CaseTransitionRequest(SupportRequestModel):
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)
    confirm: bool = False


class AdminReplyRequest(CaseReplyRequest):
    visibility: str = Field(default="public", max_length=16)
    next_state: str = Field(default="", max_length=32)
    confirm: bool = False

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        return _visibility(value)

    @field_validator("next_state")
    @classmethod
    def validate_next_state(cls, value: str) -> str:
        return _state(value) if str(value or "").strip() else ""


class AdminUpdateRequest(SupportRequestModel):
    expected_revision: int = Field(ge=1, le=1_000_000)
    state: str = Field(max_length=32)
    priority: str = Field(max_length=16)
    operation_note: str = Field(min_length=3, max_length=MAX_OPERATION_NOTE)
    idempotency_key: str = Field(min_length=12, max_length=160)
    confirm: bool = False

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        return _state(value)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return _priority(value)

    @field_validator("operation_note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _safe_text(value, label="Lý do thao tác", minimum=3, maximum=MAX_OPERATION_NOTE)


@router.get("/summary")
async def support_summary(account: dict = Depends(require_account)):
    """Return only owner-scoped counters; never claim an external notification."""
    _require_support_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with transaction() as conn:
        rows = conn.execute(
            "SELECT state, COUNT(*) FROM web_support_cases WHERE account_id=? GROUP BY state",
            (account_id,),
        ).fetchall()
    states = {state: 0 for state in sorted(CASE_STATES)}
    for state, count in rows:
        if str(state) in states:
            states[str(state)] = int(count)
    active = sum(states[state] for state in ("new", "reviewing", "waiting_user", "waiting_provider", "refund_pending"))
    return envelope(
        True,
        "Tổng quan Web Support Desk của account hiện tại.",
        data={"states": states, "active": active, "delivery": "web_view_only"},
        status_name="read_only",
    )


@router.get("/cases")
async def list_cases(
    limit: int = 30,
    offset: int = 0,
    state: str = "all",
    category: str = "",
    q: str = "",
    account: dict = Depends(require_account),
):
    """List private Web cases without falling back to Bot ticket history."""
    _require_support_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    if int(offset) < 0 or int(offset) > 10_000:
        raise HTTPException(status_code=422, detail="Offset danh sách không hợp lệ")
    bounded_offset = int(offset)
    state_filter = str(state or "all").strip().lower()
    if state_filter not in {*CASE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    category_filter = str(category or "").strip().lower()
    if category_filter and category_filter not in CASE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Bộ lọc nhóm yêu cầu không hợp lệ")
    query = _validated_line(q, label="Từ khóa tìm kiếm", minimum=0, maximum=80, allow_empty=True)
    account_id = str(account["id"])
    clauses = ["c.account_id=?"]
    params: list[Any] = [account_id]
    if state_filter != "all":
        clauses.append("c.state=?")
        params.append(state_filter)
    if category_filter:
        clauses.append("c.category=?")
        params.append(category_filter)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(c.subject LIKE ? ESCAPE '\\' OR c.initial_detail LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT c.id, c.account_id, c.category, c.priority, c.subject, c.initial_detail, c.state, c.revision,
                       c.created_at, c.updated_at, c.last_public_message_at, c.resolved_at, c.closed_at,
                       a.display_name, a.email
                  FROM web_support_cases c JOIN web_accounts a ON a.id=c.account_id
                  WHERE {' AND '.join(clauses)}
                  ORDER BY c.updated_at DESC, c.rowid DESC LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Danh sách yêu cầu riêng của Web Support Desk.",
        data={
            "items": [_case_public(tuple(row)) for row in rows[:bounded_limit]],
            "has_more": len(rows) > bounded_limit,
            "next_offset": bounded_offset + bounded_limit if len(rows) > bounded_limit else None,
            "delivery": "web_view_only",
        },
        status_name="read_only",
    )


@router.post("/cases")
async def create_case(payload: CaseCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create a case and initial public message in one Web-owned transaction."""
    _require_support_enabled()
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "category": payload.category, "priority": payload.priority, "subject": payload.subject,
        "detail_sha256": _content_hash(payload.detail),
    })

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_support_cases WHERE account_id=? AND state NOT IN ('resolved', 'closed')",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_ACTIVE_CASES:
            return envelope(False, "Đã đạt giới hạn yêu cầu đang mở của Web Support Desk.", status_name="guarded", error_code="WEB_SUPPORT_CASE_LIMIT")
        case_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_support_cases
               (id, account_id, category, priority, subject, initial_detail, state, revision, created_at, updated_at, last_public_message_at, resolved_at, closed_at)
               VALUES (?, ?, ?, ?, ?, ?, 'new', 1, ?, ?, ?, NULL, NULL)""",
            (case_id, account_id, payload.category, payload.priority, payload.subject, payload.detail, now, now, now),
        )
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'customer', 'public', ?, ?)""",
            (message_id, case_id, account_id, account_id, payload.detail, now),
        )
        _event(conn, case_id=case_id, account_id=account_id, actor_account_id=account_id, action="case_created", state="new")
        _record_audit(
            conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.support.case.create", request_id=_request_id(request), target=case_id,
            detail="web-owned support case created; no external delivery",
        )
        row = _case_row(conn, case_id=case_id, account_id=account_id)
        return envelope(True, "Đã ghi nhận yêu cầu trong Web Support Desk. Chưa gửi Telegram, email hoặc thông báo bên ngoài.", data={"case": _case_public(row or (), include_detail=False)}, status_name="completed")

    return _idempotent(f"web-support:{account_id}:case:create", key, fingerprint, operation)


def _case_detail(conn: Any, *, case_id: str, account_id: str | None, admin: bool) -> dict[str, Any] | None:
    row = _case_row(conn, case_id=case_id, account_id=account_id)
    if not row:
        return None
    message_clauses = ["m.case_id=?"]
    message_params: list[Any] = [case_id]
    if not admin:
        message_clauses.append("m.visibility='public'")
    messages = conn.execute(
        f"""SELECT m.id, m.author_role, m.visibility, m.body, m.created_at, a.display_name
              FROM web_support_messages m JOIN web_accounts a ON a.id=m.author_account_id
              WHERE {' AND '.join(message_clauses)} ORDER BY m.created_at ASC, m.rowid ASC LIMIT 500""",
        tuple(message_params),
    ).fetchall()
    event_clauses = ["case_id=?"]
    event_params: list[Any] = [case_id]
    if not admin:
        event_clauses.append("action IN ({})".format(",".join("?" for _ in CUSTOMER_VISIBLE_EVENT_ACTIONS)))
        event_params.extend(sorted(CUSTOMER_VISIBLE_EVENT_ACTIONS))
    events = conn.execute(
        f"""SELECT id, action, state, created_at FROM web_support_events
            WHERE {' AND '.join(event_clauses)} ORDER BY created_at ASC, rowid ASC LIMIT 300""",
        tuple(event_params),
    ).fetchall()
    return {
        "case": _case_public(row, include_detail=True, admin=admin),
        "messages": [_message_public(tuple(item), admin=admin) for item in messages],
        "events": [_event_public(tuple(item)) for item in events],
        "delivery": "web_view_only",
    }


@router.get("/cases/{case_id}")
async def get_case(case_id: str, account: dict = Depends(require_account)):
    _require_support_enabled()
    case_id = _uuid(case_id, label="Mã yêu cầu")
    ensure_copyfast_schema()
    with transaction() as conn:
        data = _case_detail(conn, case_id=case_id, account_id=str(account["id"]), admin=False)
    if not data:
        return _case_not_found()
    return envelope(True, "Đã nạp yêu cầu riêng từ Web Support Desk.", data=data, status_name="read_only")


@router.post("/cases/{case_id}/reply")
async def reply_case(case_id: str, payload: CaseReplyRequest, request: Request, account: dict = Depends(require_csrf)):
    """Append an owner message; a closed case must be explicitly reopened."""
    _require_support_enabled()
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "body_sha256": _content_hash(payload.body)})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id, account_id=account_id)
        if not current:
            return _case_not_found()
        if str(current[6]) == "closed":
            return envelope(False, "Yêu cầu đã đóng. Hãy mở lại trước khi gửi phản hồi.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi phản hồi.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        message_count = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()
        if int(message_count[0] or 0) >= MAX_MESSAGES_PER_CASE:
            return envelope(False, "Yêu cầu đã đạt giới hạn phản hồi an toàn.", status_name="guarded", error_code="WEB_SUPPORT_MESSAGE_LIMIT")
        next_state = "reviewing" if str(current[6]) in {"waiting_user", "resolved"} else str(current[6])
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, next_state, now)
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'customer', 'public', ?, ?)""",
            (str(uuid.uuid4()), case_id, account_id, account_id, payload.body, now),
        )
        conn.execute(
            """UPDATE web_support_cases SET state=?, revision=?, updated_at=?, last_public_message_at=?, resolved_at=?, closed_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (next_state, revision, now, now, resolved_at, closed_at, case_id, account_id, int(current[7])),
        )
        _event(conn, case_id=case_id, account_id=account_id, actor_account_id=account_id, action="customer_replied", state=next_state)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.support.case.reply", request_id=_request_id(request), target=case_id, detail="web support customer reply appended")
        row = _case_row(conn, case_id=case_id, account_id=account_id)
        return envelope(True, "Đã thêm phản hồi trong Web Support Desk; không có thông báo ngoài Web.", data={"case": _case_public(row or ())}, status_name="completed")

    return _idempotent(f"web-support:{account_id}:case:{case_id}:reply", key, fingerprint, operation)


def _customer_transition(*, case_id: str, payload: CaseTransitionRequest, request: Request, account: dict, action: str) -> dict[str, Any]:
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận thao tác Support Desk")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "action": action})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id, account_id=account_id)
        if not current:
            return _case_not_found()
        state = str(current[6])
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi tiếp tục.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        if action == "close":
            if state == "closed":
                return envelope(False, "Yêu cầu đã đóng trước đó.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
            next_state = "closed"
        elif action == "reopen":
            if state not in {"resolved", "closed"}:
                return envelope(False, "Chỉ yêu cầu đã giải quyết hoặc đã đóng mới có thể mở lại.", status_name="guarded", error_code="WEB_SUPPORT_CASE_STATE_INVALID")
            next_state = "reviewing"
        else:
            raise RuntimeError("Unknown Web Support customer transition")
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, next_state, now)
        conn.execute(
            """UPDATE web_support_cases SET state=?, revision=?, updated_at=?, closed_at=?, resolved_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (next_state, revision, now, closed_at, resolved_at, case_id, account_id, int(current[7])),
        )
        _event(conn, case_id=case_id, account_id=account_id, actor_account_id=account_id, action=f"customer_{action}", state=next_state)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action=f"web.support.case.{action}", request_id=_request_id(request), target=case_id, detail="web support customer state changed")
        row = _case_row(conn, case_id=case_id, account_id=account_id)
        message = "Đã đóng yêu cầu trong Web Support Desk." if action == "close" else "Đã mở lại yêu cầu để Web Support Desk rà soát."
        return envelope(True, message, data={"case": _case_public(row or ())}, status_name="completed")

    return _idempotent(f"web-support:{account_id}:case:{case_id}:{action}", key, fingerprint, operation)


@router.post("/cases/{case_id}/close")
async def close_case(case_id: str, payload: CaseTransitionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    return _customer_transition(case_id=_uuid(case_id, label="Mã yêu cầu"), payload=payload, request=request, account=account, action="close")


@router.post("/cases/{case_id}/reopen")
async def reopen_case(case_id: str, payload: CaseTransitionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    return _customer_transition(case_id=_uuid(case_id, label="Mã yêu cầu"), payload=payload, request=request, account=account, action="reopen")


@router.get("/events")
async def support_events(limit: int = 40, account: dict = Depends(require_account)):
    _require_support_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    ensure_copyfast_schema()
    with transaction() as conn:
        actions = sorted(CUSTOMER_VISIBLE_EVENT_ACTIONS)
        rows = conn.execute(
            f"""SELECT id, action, state, created_at FROM web_support_events
                WHERE account_id=? AND action IN ({','.join('?' for _ in actions)})
                ORDER BY created_at DESC, rowid DESC LIMIT ?""",
            (str(account["id"]), *actions, bounded_limit),
        ).fetchall()
    return envelope(True, "Hoạt động Web Support Desk của account hiện tại.", data={"items": [_event_public(tuple(row)) for row in rows]}, status_name="read_only")


@router.get("/admin/summary")
async def admin_summary(account: dict = Depends(require_account)):
    _require_support_enabled()
    role = require_support_staff(account)
    ensure_copyfast_schema()
    cutoff_one_day = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    cutoff_three_days = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat(timespec="seconds")
    with transaction() as conn:
        rows = conn.execute("SELECT state, COUNT(*) FROM web_support_cases GROUP BY state").fetchall()
        overdue = conn.execute(
            """SELECT COUNT(*) FROM web_support_cases
               WHERE (state IN ('new','reviewing','refund_pending') AND updated_at<?)
                  OR (state='waiting_provider' AND updated_at<?)""",
            (cutoff_one_day, cutoff_three_days),
        ).fetchone()
    states = {state: 0 for state in sorted(CASE_STATES)}
    for state, count in rows:
        if str(state) in states:
            states[str(state)] = int(count)
    return envelope(True, "Tổng quan Web Support Desk cho operator.", data={"states": states, "overdue": int(overdue[0] or 0) if overdue else 0, "operator_role": role, "delivery": "web_view_only"}, status_name="read_only")


@router.get("/admin/cases")
async def admin_list_cases(
    limit: int = 50,
    offset: int = 0,
    state: str = "all",
    category: str = "",
    q: str = "",
    account: dict = Depends(require_account),
):
    _require_support_enabled()
    require_support_staff(account)
    bounded_limit = max(1, min(int(limit), 100))
    if int(offset) < 0 or int(offset) > 10_000:
        raise HTTPException(status_code=422, detail="Offset danh sách không hợp lệ")
    bounded_offset = int(offset)
    state_filter = str(state or "all").strip().lower()
    if state_filter not in {*CASE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    category_filter = str(category or "").strip().lower()
    if category_filter and category_filter not in CASE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Bộ lọc nhóm yêu cầu không hợp lệ")
    query = _validated_line(q, label="Từ khóa tìm kiếm", minimum=0, maximum=80, allow_empty=True)
    clauses = ["1=1"]
    params: list[Any] = []
    if state_filter != "all":
        clauses.append("c.state=?")
        params.append(state_filter)
    if category_filter:
        clauses.append("c.category=?")
        params.append(category_filter)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(c.subject LIKE ? ESCAPE '\\' OR c.initial_detail LIKE ? ESCAPE '\\' OR a.display_name LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"])
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT c.id, c.account_id, c.category, c.priority, c.subject, c.initial_detail, c.state, c.revision,
                       c.created_at, c.updated_at, c.last_public_message_at, c.resolved_at, c.closed_at,
                       a.display_name, a.email
                  FROM web_support_cases c JOIN web_accounts a ON a.id=c.account_id
                  WHERE {' AND '.join(clauses)}
                  ORDER BY CASE c.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                           c.updated_at DESC, c.rowid DESC LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Danh sách yêu cầu Web Support Desk cho operator.",
        data={
            "items": [_case_public(tuple(row), admin=True) for row in rows[:bounded_limit]],
            "has_more": len(rows) > bounded_limit,
            "next_offset": bounded_offset + bounded_limit if len(rows) > bounded_limit else None,
        },
        status_name="read_only",
    )


@router.get("/admin/cases/{case_id}")
async def admin_get_case(case_id: str, account: dict = Depends(require_account)):
    _require_support_enabled()
    require_support_staff(account)
    case_id = _uuid(case_id, label="Mã yêu cầu")
    ensure_copyfast_schema()
    with transaction() as conn:
        data = _case_detail(conn, case_id=case_id, account_id=None, admin=True)
    if not data:
        return _case_not_found()
    return envelope(True, "Đã nạp yêu cầu Web Support Desk cho operator.", data=data, status_name="read_only")


@router.post("/admin/cases/{case_id}/reply")
async def admin_reply_case(case_id: str, payload: AdminReplyRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    staff_role = require_support_staff(account)
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Operator cần xác nhận trước khi gửi phản hồi")
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "body_sha256": _content_hash(payload.body), "visibility": payload.visibility, "next_state": payload.next_state})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id)
        if not current:
            return _case_not_found()
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi phản hồi.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        if str(current[6]) == "closed":
            return envelope(False, "Yêu cầu đã đóng; hãy dùng cập nhật trạng thái có xác nhận để mở lại trước.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
        message_count = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()
        if int(message_count[0] or 0) >= MAX_MESSAGES_PER_CASE:
            return envelope(False, "Yêu cầu đã đạt giới hạn phản hồi an toàn.", status_name="guarded", error_code="WEB_SUPPORT_MESSAGE_LIMIT")
        next_state = payload.next_state or ("waiting_user" if payload.visibility == "public" else str(current[6]))
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, next_state, now)
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'operator', ?, ?, ?)""",
            (str(uuid.uuid4()), case_id, str(current[1]), str(account["id"]), payload.visibility, payload.body, now),
        )
        conn.execute(
            """UPDATE web_support_cases SET state=?, revision=?, updated_at=?, last_public_message_at=?, resolved_at=?, closed_at=?
               WHERE id=? AND revision=?""",
            (next_state, revision, now, now if payload.visibility == "public" else current[10], resolved_at, closed_at, case_id, int(current[7])),
        )
        _event(conn, case_id=case_id, account_id=str(current[1]), actor_account_id=str(account["id"]), action="operator_replied_public" if payload.visibility == "public" else "operator_noted_internal", state=next_state)
        _record_audit(conn, account_id=str(account["id"]), canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.support.admin.reply", request_id=_request_id(request), target=case_id, detail=f"web support operator reply visibility:{payload.visibility} role:{staff_role}")
        row = _case_row(conn, case_id=case_id)
        return envelope(True, "Đã lưu phản hồi trong Web Support Desk. Chưa gửi Telegram, email hoặc thông báo bên ngoài.", data={"case": _case_public(row or (), admin=True)}, status_name="completed")

    return _idempotent(f"web-support:admin:{account['id']}:case:{case_id}:reply", key, fingerprint, operation)


@router.post("/admin/cases/{case_id}/update")
async def admin_update_case(case_id: str, payload: AdminUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    staff_role = require_support_staff(account)
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Operator cần xác nhận trước khi cập nhật yêu cầu")
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "state": payload.state, "priority": payload.priority, "operation_note_sha256": _content_hash(payload.operation_note)})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id)
        if not current:
            return _case_not_found()
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi thay đổi.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        message_count = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()
        if int(message_count[0] or 0) >= MAX_MESSAGES_PER_CASE:
            return envelope(False, "Yêu cầu đã đạt giới hạn phản hồi an toàn.", status_name="guarded", error_code="WEB_SUPPORT_MESSAGE_LIMIT")
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, payload.state, now)
        conn.execute(
            """UPDATE web_support_cases SET state=?, priority=?, revision=?, updated_at=?, resolved_at=?, closed_at=?
               WHERE id=? AND revision=?""",
            (payload.state, payload.priority, revision, now, resolved_at, closed_at, case_id, int(current[7])),
        )
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'operator', 'internal', ?, ?)""",
            (str(uuid.uuid4()), case_id, str(current[1]), str(account["id"]), payload.operation_note, now),
        )
        _event(conn, case_id=case_id, account_id=str(current[1]), actor_account_id=str(account["id"]), action="operator_updated", state=payload.state)
        # Preserve the operator's safe narrative as a staff-only message so a
        # later shift can understand the decision, but never copy it into the
        # generally accessible audit trail.
        _record_audit(conn, account_id=str(account["id"]), canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.support.admin.update", request_id=_request_id(request), target=case_id, detail=f"web support operator state:{payload.state} priority:{payload.priority} role:{staff_role}; internal_note_saved")
        row = _case_row(conn, case_id=case_id)
        return envelope(True, "Đã cập nhật trạng thái Web Support Desk; không có external delivery.", data={"case": _case_public(row or (), admin=True)}, status_name="completed")

    return _idempotent(f"web-support:admin:{account['id']}:case:{case_id}:update", key, fingerprint, operation)
