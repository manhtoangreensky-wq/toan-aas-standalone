"""Redacted read-only directory for standalone Web App customer accounts."""

from __future__ import annotations

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from copyfast_auth import (
    OAUTH_ONLY_EMAIL_DOMAIN,
    TELEGRAM_ONLY_EMAIL_DOMAIN,
    envelope,
    normalize_interface_locale,
    require_admin,
)
from copyfast_customer_crm_policy import synthesize_customer_crm_context
from copyfast_db import read_transaction


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

        if view == "crm":
            return _build_crm_detail_response(conn, row, normalized_id)

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
        return _build_crm_detail_response(conn, row, normalized_id)


def _build_crm_detail_response(conn: Any, row: Any, account_id: str) -> dict[str, Any]:
    customer_proj = _customer_projection(tuple(row[:12]))
    canonical_user_id = str(row[12] or "").strip() or None
    customer_proj["canonical_user_id"] = canonical_user_id

    # Workspace setup
    setup_row = conn.execute(
        "SELECT setup_state, role, goal, experience FROM web_workspace_setup_profiles WHERE account_id=? LIMIT 1",
        (account_id,),
    ).fetchone()
    setup_data = {
        "setup_state": str(setup_row[0]) if setup_row else "not_started",
        "role": str(setup_row[1]) if setup_row else "",
        "goal": str(setup_row[2]) if setup_row else "",
        "experience": str(setup_row[3]) if setup_row else "",
    } if setup_row else None

    # Support cases
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

    # Manual topups
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

    # Telegram link evidence
    link_row = conn.execute(
        """SELECT canonical_user_id, bot_confirmed_at, confirmed_display_name, created_at
           FROM telegram_link_codes
           WHERE account_id=? AND consumed_at IS NOT NULL
           ORDER BY bot_confirmed_at DESC LIMIT 1""",
        (account_id,),
    ).fetchone()
    link_evidence = {
        "canonical_user_id": str(link_row[0] or ""),
        "bot_confirmed_at": str(link_row[1] or ""),
        "confirmed_display_name": str(link_row[2] or ""),
        "created_at": str(link_row[3] or ""),
    } if link_row else None

    crm_context = synthesize_customer_crm_context(
        customer_proj,
        profile=customer_proj.get("profile"),
        workspace_setup=setup_data,
        support_cases=support_cases,
        topup_requests=topup_requests,
        link_evidence=link_evidence,
    )
    return envelope(
        True,
        "Đã nạp ngữ cảnh CRM khách hàng Web.",
        data=crm_context,
        status_name="read_only",
    )
