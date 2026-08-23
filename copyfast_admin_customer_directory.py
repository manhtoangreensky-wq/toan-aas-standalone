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
            "OR (LOWER(a.email) NOT LIKE ? AND LOWER(a.email) NOT LIKE ? "
            "AND LOWER(a.email) LIKE ? ESCAPE '\\'))"
        )
        parameters.extend(
            [
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
                             a.created_at, a.updated_at
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
    customers = [_customer_projection(tuple(row)) for row in rows[: int(limit)]]
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
    return envelope(
        True,
        "Đã nạp chi tiết khách hàng Web.",
        data={"customer": _customer_projection(tuple(row)), "source": "web_accounts_redacted"},
        status_name="read_only",
    )
