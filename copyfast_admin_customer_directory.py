"""Redacted read-only directory for standalone Web App customer accounts."""

from __future__ import annotations

from typing import Any
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import (
    OAUTH_ONLY_EMAIL_DOMAIN,
    TELEGRAM_ONLY_EMAIL_DOMAIN,
    _password_hash,
    _record_audit,
    _request_id,
    envelope,
    normalize_interface_locale,
    require_admin,
    require_canonical_admin_csrf,
)
from copyfast_customer_crm_policy import synthesize_customer_crm_context
from copyfast_db import (
    _allocate_web_topup_code,
    get_or_create_web_topup_code,
    read_transaction,
    transaction,
    utc_now,
)


router = APIRouter(prefix="/api/v1/admin/customers", tags=["COPYFAST Admin Customers"])

MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
ROLE_LABELS = {
    "admin": "Quản trị viên",
    "support_manager": "Quản lý hỗ trợ",
    "support_operator": "Nhân viên hỗ trợ",
    "user": "Khách hàng",
}
INTERNAL_EMAIL_SUFFIXES = (
    f"@{TELEGRAM_ONLY_EMAIL_DOMAIN}".lower(),
    f"@{OAUTH_ONLY_EMAIL_DOMAIN}".lower(),
)


def _is_internal_email(value: Any) -> bool:
    return str(value or "").strip().lower().endswith(INTERNAL_EMAIL_SUFFIXES)


def _safe_email(value: Any) -> str:
    email = str(value or "").strip()
    return "" if _is_internal_email(email) else email


def _account_type(email: Any, password_login_enabled: Any) -> str:
    normalized = str(email or "").strip().lower()
    if normalized.endswith(f"@{TELEGRAM_ONLY_EMAIL_DOMAIN}".lower()):
        return "telegram"
    if normalized.endswith(f"@{OAUTH_ONLY_EMAIL_DOMAIN}".lower()) or not bool(password_login_enabled):
        return "oauth_only"
    return "standard"


def _role(value: Any) -> tuple[str, str]:
    normalized = str(value or "user").strip().lower()
    role = normalized if normalized in ROLE_LABELS else "other"
    return role, ROLE_LABELS.get(role, "Vai trò khác")


def _customer_projection(row: tuple[Any, ...]) -> dict[str, Any]:
    role, role_label = _role(row[3])
    return {
        "id": str(row[0]),
        "display_name": str(row[2] or ""),
        "email": _safe_email(row[1]),
        "account_type": _account_type(row[1], row[5]),
        "role": role,
        "role_label": role_label,
        "status": "active" if bool(row[4]) else "locked",
        "password_login_enabled": bool(row[5]),
        "telegram_linked": bool(row[6]),
        "profile": {
            "locale": normalize_interface_locale(row[7]),
            "timezone": str(row[8] or "Asia/Ho_Chi_Minh"),
            "avatar_style": str(row[9] or "gradient"),
        },
        "created_at": str(row[10] or ""),
        "updated_at": str(row[11] or ""),
    }


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filters(q: str | None, status: str) -> tuple[str, list[Any], str]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if status == "active":
        clauses.append("a.is_active=1")
    elif status == "locked":
        clauses.append("a.is_active=0")

    normalized_query = str(q or "").strip().lower()
    if normalized_query:
        needle = f"%{_escape_like(normalized_query)}%"
        clauses.append(
            "(LOWER(COALESCE(a.display_name, '')) LIKE ? ESCAPE '\\' "
            "OR LOWER(COALESCE(a.id, '')) LIKE ? ESCAPE '\\' "
            "OR LOWER(COALESCE(a.canonical_user_id, '')) LIKE ? ESCAPE '\\' "
            "OR (LOWER(a.email) NOT LIKE ? AND LOWER(a.email) NOT LIKE ? "
            "AND LOWER(a.email) LIKE ? ESCAPE '\\'))"
        )
        parameters.extend(
            [
                needle,
                needle,
                needle,
                f"%@{TELEGRAM_ONLY_EMAIL_DOMAIN}".lower(),
                f"%@{OAUTH_ONLY_EMAIL_DOMAIN}".lower(),
                needle,
            ]
        )
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, parameters, normalized_query


def _account_id(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value or "").strip()))
    except (AttributeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Mã tài khoản khách hàng không hợp lệ") from exc


SELECT_CUSTOMER = """SELECT a.id, a.email, a.display_name, a.role_cache,
                             a.is_active, a.password_login_enabled,
                             a.canonical_user_id IS NOT NULL,
                             p.locale, p.timezone, p.avatar_style,
                             a.created_at, a.updated_at,
                             a.canonical_user_id
                      FROM web_accounts a
                      LEFT JOIN web_account_profiles p ON p.account_id=a.id"""


@router.get("")
async def list_customers(
    q: str | None = Query(None, max_length=120),
    status: str = Query("all", pattern="^(all|active|locked)$"),
    limit: int = Query(50, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    _account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    where, parameters, normalized_query = _filters(q, status)
    with read_transaction() as conn:
        rows = conn.execute(
            f"""{SELECT_CUSTOMER}{where}
                 ORDER BY a.created_at DESC, a.id DESC
                 LIMIT ? OFFSET ?""",
            [*parameters, int(limit) + 1, int(offset)],
        ).fetchall()
    has_more = len(rows) > int(limit) and int(offset) + int(limit) <= MAX_LIST_OFFSET
    customers = [_customer_projection(tuple(row[:12])) for row in rows[: int(limit)]]
    return envelope(
        True,
        "Đã nạp danh sách khách hàng Web.",
        data={
            "customers": customers,
            "returned": len(customers),
            "limit": int(limit),
            "offset": int(offset),
            "has_more": has_more,
            "next_offset": int(offset) + int(limit) if has_more else None,
            "filters": {"q": normalized_query, "status": status},
            "source": "web_accounts_redacted",
        },
        status_name="read_only",
    )


class CustomerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=254)
    display_name: str = Field(default="", max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str = Field(default="user")
    is_active: bool = True
    canonical_user_id: str | None = Field(default=None, max_length=64)

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str) -> str:
        cleaned = str(value or "").strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Email không đúng định dạng")
        if _is_internal_email(cleaned):
            raise ValueError("Không được dùng domain email nội bộ của hệ thống")
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role_name(cls, value: str) -> str:
        cleaned = str(value or "user").strip().lower()
        if cleaned not in ROLE_LABELS:
            raise ValueError(f"Vai trò không hợp lệ. Cho phép: {', '.join(ROLE_LABELS.keys())}")
        return cleaned


class CustomerUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str | None = Field(default=None, pattern="^(ban|unban|update)$")
    reason: str | None = Field(default=None, max_length=500)
    display_name: str | None = Field(default=None, max_length=120)
    role: str | None = None
    is_active: bool | None = None
    password_login_enabled: bool | None = None
    canonical_user_id: str | None = Field(default=None, max_length=64)

    @field_validator("role")
    @classmethod
    def validate_role_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        if cleaned not in ROLE_LABELS:
            raise ValueError(f"Vai trò không hợp lệ. Cho phép: {', '.join(ROLE_LABELS.keys())}")
        return cleaned

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Lý do không được để trống")
        return cleaned


@router.post("", status_code=201)
async def create_customer(
    payload: CustomerCreateRequest,
    _account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    email = payload.email.strip().lower()
    raw_password = payload.password or secrets.token_urlsafe(16)
    password_hash = _password_hash(raw_password)
    now = utc_now()
    account_id = str(uuid.uuid4())
    display_name = payload.display_name.strip() or email.split("@")[0]
    canonical_user_id = str(payload.canonical_user_id).strip() if payload.canonical_user_id else None

    with transaction() as conn:
        existing = conn.execute(
            "SELECT id FROM web_accounts WHERE LOWER(email)=?",
            (email,),
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Email này đã được sử dụng")

        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id,
                role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (
                account_id,
                email,
                password_hash,
                display_name,
                canonical_user_id,
                payload.role,
                1 if payload.is_active else 0,
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO web_account_profiles
               (account_id, locale, timezone, avatar_style, created_at, updated_at)
               VALUES (?, 'vi', 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)""",
            (account_id, now, now),
        )
        conn.execute(
            """INSERT INTO web_audit_events
               (id, account_id, canonical_user_id, action, request_id,
                target, outcome, detail, created_at)
               VALUES (?, ?, NULL, 'admin.customer.create', ?, ?, 'completed', ?, ?)""",
            (
                str(uuid.uuid4()),
                str(_account.get("id") or ""),
                str(uuid.uuid4()),
                account_id,
                f"email={email};role={payload.role}",
                now,
            ),
        )
        topup_code = _allocate_web_topup_code(conn, account_id)

        row = conn.execute(
            f"{SELECT_CUSTOMER} WHERE a.id=? LIMIT 1",
            (account_id,),
        ).fetchone()

    assert row is not None
    created = _customer_projection(tuple(row[:12]))
    created["topup_code"] = topup_code
    return envelope(
        True,
        "Đã tạo tài khoản khách hàng thành công.",
        data={**created, "customer": created, "topup_code": topup_code, "temporary_password": raw_password if not payload.password else None},
        status_name="created",
    )


@router.patch("/{account_id}")
async def update_customer(
    account_id: str,
    payload: CustomerUpdateRequest,
    request: Request,
    _account: dict[str, Any] = Depends(require_canonical_admin_csrf),
) -> dict[str, Any]:
    normalized_id = _account_id(account_id)
    actor_id = str(_account.get("id") or "").strip()
    now = utc_now()

    # Dedicated Account Safety Actions (Ban / Unban)
    if payload.action == "ban":
        reason = (payload.reason or "").strip()
        if not reason:
            raise HTTPException(status_code=422, detail="Lý do khóa tài khoản không được để trống")

        with transaction() as conn:
            target_row = conn.execute(
                "SELECT id, role_cache, is_active FROM web_accounts WHERE id=?",
                (normalized_id,),
            ).fetchone()
            if target_row is None:
                raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản khách hàng")

            target_role = str(target_row[1] or "user").strip().lower()
            target_is_active = int(target_row[2])

            if normalized_id == actor_id:
                raise HTTPException(status_code=403, detail="Không thể tự khóa tài khoản của chính mình")
            if target_role == "admin":
                raise HTTPException(status_code=403, detail="Không được phép khóa tài khoản Quản trị viên")

            if target_is_active == 0:
                return envelope(
                    True,
                    "Tài khoản khách hàng đã ở trạng thái bị khóa.",
                    data={
                        "account_id": normalized_id,
                        "status": "locked",
                        "is_active": False,
                        "idempotent_replay": True,
                        "revoked_sessions": 0,
                    },
                    status_name="ok",
                )

            conn.execute(
                "UPDATE web_accounts SET is_active=0, updated_at=? WHERE id=?",
                (now, normalized_id),
            )
            cur = conn.execute(
                "UPDATE web_sessions SET revoked_at=? WHERE account_id=? AND revoked_at IS NULL",
                (now, normalized_id),
            )
            revoked_count = cur.rowcount if cur and cur.rowcount is not None else 0

            _record_audit(
                conn,
                account_id=actor_id or None,
                canonical_user_id=str(_account.get("canonical_user_id") or "").strip() or None,
                action="admin.customer.ban",
                request_id=_request_id(request),
                target=normalized_id,
                outcome="ok",
                detail=f"reason={reason};revoked_sessions={revoked_count}",
            )

        return envelope(
            True,
            "Đã khóa tài khoản khách hàng và thu hồi phiên đăng nhập thành công.",
            data={
                "account_id": normalized_id,
                "status": "locked",
                "is_active": False,
                "idempotent_replay": False,
                "revoked_sessions": revoked_count,
            },
            status_name="ok",
        )

    if payload.action == "unban":
        reason = (payload.reason or "").strip()
        if not reason:
            raise HTTPException(status_code=422, detail="Lý do mở khóa tài khoản không được để trống")

        with transaction() as conn:
            target_row = conn.execute(
                "SELECT id, role_cache, is_active FROM web_accounts WHERE id=?",
                (normalized_id,),
            ).fetchone()
            if target_row is None:
                raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản khách hàng")

            target_role = str(target_row[1] or "user").strip().lower()
            target_is_active = int(target_row[2])

            if target_role == "admin":
                raise HTTPException(status_code=403, detail="Không áp dụng cho tài khoản Quản trị viên")

            if target_is_active == 1:
                return envelope(
                    True,
                    "Tài khoản khách hàng đã ở trạng thái hoạt động.",
                    data={
                        "account_id": normalized_id,
                        "status": "active",
                        "is_active": True,
                        "idempotent_replay": True,
                    },
                    status_name="ok",
                )

            conn.execute(
                "UPDATE web_accounts SET is_active=1, updated_at=? WHERE id=?",
                (now, normalized_id),
            )
            # CRITICAL: Old revoked sessions remain revoked! Do not reactivate sessions.

            _record_audit(
                conn,
                account_id=actor_id or None,
                canonical_user_id=str(_account.get("canonical_user_id") or "").strip() or None,
                action="admin.customer.unban",
                request_id=_request_id(request),
                target=normalized_id,
                outcome="ok",
                detail=f"reason={reason}",
            )

        return envelope(
            True,
            "Đã mở khóa tài khoản khách hàng thành công.",
            data={
                "account_id": normalized_id,
                "status": "active",
                "is_active": True,
                "idempotent_replay": False,
            },
            status_name="ok",
        )

    # Standard customer attribute updates
    updates: list[str] = []
    params: list[Any] = []

    if payload.display_name is not None:
        updates.append("display_name=?")
        params.append(payload.display_name.strip())
    if payload.role is not None:
        updates.append("role_cache=?")
        params.append(payload.role)
    if payload.is_active is not None:
        updates.append("is_active=?")
        params.append(1 if payload.is_active else 0)
    if payload.password_login_enabled is not None:
        updates.append("password_login_enabled=?")
        params.append(1 if payload.password_login_enabled else 0)
    if payload.canonical_user_id is not None:
        val = payload.canonical_user_id.strip() or None
        updates.append("canonical_user_id=?")
        params.append(val)

    if not updates:
        raise HTTPException(status_code=422, detail="Không có thông tin thay đổi")

    updates.append("updated_at=?")
    params.append(now)
    params.append(normalized_id)

    with transaction() as conn:
        existing = conn.execute("SELECT id FROM web_accounts WHERE id=?", (normalized_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản khách hàng")

        conn.execute(
            f"UPDATE web_accounts SET {', '.join(updates)} WHERE id=?",
            params,
        )
        conn.execute(
            """INSERT INTO web_audit_events
               (id, account_id, canonical_user_id, action, request_id,
                target, outcome, detail, created_at)
               VALUES (?, ?, NULL, 'admin.customer.update', ?, ?, 'completed', ?, ?)""",
            (
                str(uuid.uuid4()),
                actor_id,
                _request_id(request),
                normalized_id,
                f"updates={','.join(updates)}",
                now,
            ),
        )
        row = conn.execute(
            f"{SELECT_CUSTOMER} WHERE a.id=? LIMIT 1",
            (normalized_id,),
        ).fetchone()

    assert row is not None
    updated = _customer_projection(tuple(row[:12]))
    return envelope(
        True,
        "Đã cập nhật tài khoản khách hàng thành công.",
        data={**updated, "customer": updated},
        status_name="updated",
    )


@router.get("/{account_id}")
async def get_customer(
    account_id: str,
    view: str | None = Query(None),
    _account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    normalized_id = _account_id(account_id)
    with read_transaction() as conn:
        row = conn.execute(
            f"{SELECT_CUSTOMER} WHERE a.id=? LIMIT 1",
            (normalized_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản khách hàng")

        if view in ("crm", "360"):
            return _build_crm_detail_response(conn, row, normalized_id, admin_account=_account)

    return envelope(
        True,
        "Đã nạp chi tiết khách hàng Web.",
        data={"customer": _customer_projection(tuple(row[:12])), "source": "web_accounts_redacted"},
        status_name="read_only",
    )


@router.get("/{account_id}/crm")
async def get_customer_crm(
    account_id: str,
    _account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    normalized_id = _account_id(account_id)
    with read_transaction() as conn:
        row = conn.execute(
            f"{SELECT_CUSTOMER} WHERE a.id=? LIMIT 1",
            (normalized_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản khách hàng")
        return _build_crm_detail_response(conn, row, normalized_id, admin_account=_account)



def _build_crm_detail_response(
    conn: Any,
    row: Any,
    account_id: str,
    admin_account: dict[str, Any] | None = None,
) -> dict[str, Any]:
    customer_proj = _customer_projection(tuple(row[:12]))
    canonical_user_id = str(row[12] or "").strip() or None
    customer_proj["canonical_user_id"] = canonical_user_id

    # Workspace setup
    setup_data = None
    try:
        setup_row = conn.execute(
            "SELECT setup_state, role, goal, experience FROM web_workspace_setup_profiles WHERE account_id=? LIMIT 1",
            (account_id,),
        ).fetchone()
        if setup_row:
            setup_data = {
                "setup_state": str(setup_row[0]) if setup_row else "not_started",
                "role": str(setup_row[1]) if setup_row else "",
                "goal": str(setup_row[2]) if setup_row else "",
                "experience": str(setup_row[3]) if setup_row else "",
            }
    except Exception:
        pass

    # Support cases
    support_cases: list[dict[str, Any]] = []
    try:
        case_rows = conn.execute(
            """SELECT id, category, priority, subject, state, created_at, updated_at
               FROM web_support_cases
               WHERE account_id=?
               ORDER BY updated_at DESC, id DESC LIMIT 10""",
            (account_id,),
        ).fetchall()
        support_cases = [
            {
                "id": str(r[0]),
                "category": str(r[1]),
                "priority": str(r[2]),
                "subject": str(r[3]),
                "state": str(r[4]),
                "created_at": str(r[5]),
                "updated_at": str(r[6]),
            }
            for r in case_rows
        ]
    except Exception:
        pass

    # Manual topups
    topup_requests: list[dict[str, Any]] = []
    try:
        topup_rows = conn.execute(
            """SELECT id, amount_vnd, currency, method, reference, status, submitted_at, updated_at
               FROM web_manual_topup_requests
               WHERE account_id=?
               ORDER BY submitted_at DESC, id DESC LIMIT 10""",
            (account_id,),
        ).fetchall()
        topup_requests = [
            {
                "id": int(r[0]),
                "amount_vnd": int(r[1]),
                "currency": str(r[2]),
                "method": str(r[3]),
                "reference": str(r[4]),
                "status": str(r[5]),
                "submitted_at": str(r[6]),
                "updated_at": str(r[7]),
            }
            for r in topup_rows
        ]
    except Exception:
        pass

    # Telegram link evidence
    link_evidence = None
    try:
        link_row = conn.execute(
            """SELECT canonical_user_id, bot_confirmed_at, confirmed_display_name, created_at
               FROM telegram_link_codes
               WHERE account_id=? AND consumed_at IS NOT NULL
               ORDER BY bot_confirmed_at DESC LIMIT 1""",
            (account_id,),
        ).fetchone()
        if link_row:
            link_evidence = {
                "canonical_user_id": str(link_row[0] or ""),
                "bot_confirmed_at": str(link_row[1] or ""),
                "confirmed_display_name": str(link_row[2] or ""),
                "created_at": str(link_row[3] or ""),
            }
    except Exception:
        pass

    # Active web sessions count
    active_sessions_count = 0
    try:
        active_sess_row = conn.execute(
            "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL AND expires_at > ?",
            (account_id, utc_now()),
        ).fetchone()
        if active_sess_row:
            active_sessions_count = int(active_sess_row[0])
    except Exception:
        pass

    # Recent audit trail
    audit_events: list[dict[str, Any]] = []
    try:
        audit_rows = conn.execute(
            """SELECT id, action, account_id, outcome, detail, created_at
               FROM web_audit_events
               WHERE target=? OR account_id=?
               ORDER BY created_at DESC, id DESC LIMIT 10""",
            (account_id, account_id),
        ).fetchall()
        audit_events = [
            {
                "id": str(r[0]),
                "action": str(r[1]),
                "actor_id": str(r[2] or ""),
                "outcome": str(r[3] or ""),
                "detail": str(r[4] or ""),
                "created_at": str(r[5] or ""),
            }
            for r in audit_rows
        ]
    except Exception:
        pass

    # Total approved topup VND
    total_approved_vnd = sum(
        int(t["amount_vnd"]) for t in topup_requests
        if str(t.get("status") or "") in ("approved", "confirmed", "completed")
    )

    admin_actor_id = str(admin_account.get("id") or "").strip() if admin_account else None

    crm_context = synthesize_customer_crm_context(
        customer_proj,
        profile=customer_proj.get("profile"),
        workspace_setup=setup_data,
        support_cases=support_cases,
        topup_requests=topup_requests,
        link_evidence=link_evidence,
        active_sessions_count=active_sessions_count,
        audit_events=audit_events,
        total_approved_topup_vnd=total_approved_vnd,
        admin_actor_id=admin_actor_id,
    )
    return envelope(
        True,
        "Đã nạp ngữ cảnh CRM khách hàng Web.",
        data=crm_context,
        status_name="read_only",
    )
