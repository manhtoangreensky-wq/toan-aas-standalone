"""Redacted Web-owned audit explorer for the canonical Admin ERP.

This router intentionally exposes a compact, read-only projection of the
standalone Web App's append-only ``web_audit_events`` table.  It is not a
replacement for the Bot audit trail and it never returns account IDs,
canonical IDs, request IDs, targets, free-form details, secrets, provider
payloads, payment references, or raw security decisions.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from copyfast_auth import envelope, require_canonical_admin
from copyfast_db import ensure_copyfast_schema, transaction


router = APIRouter(prefix="/api/v1/admin", tags=["COPYFAST Admin Audit"])


_CATEGORIES: dict[str, tuple[str, ...]] = {
    "auth": ("auth.",),
    "support": ("web.support.",),
    "operations": ("web.operations.", "web.reliability."),
    "workspace": ("web.workspace.", "web.project.", "web.workboard.", "web.memory."),
    "content": ("web.content.", "web.channel_strategy.", "web.prompt_library."),
    "asset": ("web.asset.", "web.document_operation.", "web.image_operation."),
    "admin": ("web.admin.",),
    "security": ("web.security.",),
}

_CATEGORY_LABELS = {
    "auth": "Xác thực",
    "support": "CSKH",
    "operations": "Vận hành",
    "workspace": "Workspace",
    "content": "Nội dung",
    "asset": "Tài sản & tài liệu",
    "admin": "Quản trị",
    "security": "Bảo mật",
    "other": "Sự kiện Web",
}

_ACTION_LABELS = {
    "auth.login": "Đăng nhập Web",
    "auth.logout": "Đăng xuất Web",
    "auth.telegram_login_confirm": "Xác minh đăng nhập Telegram",
    "auth.telegram_link_confirm": "Liên kết Telegram",
    "web.support.case.create": "Tạo case CSKH",
    "web.support.case.reply": "Khách phản hồi case",
    "web.support.admin.reply": "Nhân sự phản hồi case",
    "web.support.admin.update": "Cập nhật case CSKH",
    "web.operations.approval.recorded": "Ghi nhận quyết định Operations",
    "web.reliability.followup.update": "Cập nhật Reliability follow-up",
}


def _enabled(name: str, *, default: bool = True) -> bool:
    return os.environ.get(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}


def _category_for(action: str) -> str:
    normalized = str(action or "").strip().lower()
    for category, prefixes in _CATEGORIES.items():
        if any(normalized.startswith(prefix) for prefix in prefixes):
            return category
    return "other"


def _event_label(action: str, category: str) -> str:
    normalized = str(action or "").strip().lower()
    if normalized in _ACTION_LABELS:
        return _ACTION_LABELS[normalized]
    # Do not echo an unknown raw action name. It may reveal an internal route,
    # workflow convention or security event that has not been reviewed for UI.
    return f"{_CATEGORY_LABELS.get(category, _CATEGORY_LABELS['other'])} · sự kiện đã redaction"


def _event_state(outcome: str) -> tuple[str, str]:
    normalized = str(outcome or "").strip().lower()
    if normalized == "ok":
        return "completed", "Đã ghi nhận"
    if normalized in {"denied", "blocked", "guarded"}:
        return "guarded", "Bị chặn an toàn"
    return "read_only", "Đã ghi nhận trạng thái"


def _public_event(row: tuple[Any, ...]) -> dict[str, str]:
    """Project only reviewed fields from a raw audit row."""
    action = str(row[0] or "")
    category = _category_for(action)
    state, outcome_label = _event_state(str(row[1] or ""))
    return {
        "category": category,
        "category_label": _CATEGORY_LABELS.get(category, _CATEGORY_LABELS["other"]),
        "event_label": _event_label(action, category),
        "state": state,
        "outcome_label": outcome_label,
        "created_at": str(row[2] or ""),
        "source": "web_audit_events_redacted",
    }


def _where_for_category(category: str) -> tuple[str, list[str]]:
    if category == "all":
        return "", []
    prefixes = _CATEGORIES[category]
    clauses = " OR ".join("action LIKE ?" for _ in prefixes)
    return f" WHERE ({clauses})", [f"{prefix}%" for prefix in prefixes]


@router.get("/audit-events")
async def audit_events(
    request: Request,
    category: str = Query("all", pattern="^(all|auth|support|operations|workspace|content|asset|admin|security)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
) -> dict[str, Any]:
    """Read a bounded redacted audit projection for a live canonical admin."""
    await require_canonical_admin(request)
    if not _enabled("WEBAPP_ADMIN_ERP_ENABLED"):
        return envelope(
            True,
            "Admin ERP đang được bảo trì; Audit Explorer được giữ guarded.",
            data={
                "events": [],
                "summary": {"returned": 0, "completed": 0, "guarded": 0, "read_only": 0, "category": category},
                "has_more": False,
                "next_offset": None,
                "source": "web_audit_events_redacted",
            },
            status_name="guarded",
        )

    ensure_copyfast_schema()
    where, parameters = _where_for_category(category)
    # Select only the three columns used by the redacted projection. Account,
    # canonical identity, request ID, target and detail never enter Python.
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT action, outcome, created_at
                   FROM web_audit_events{where}
                   ORDER BY created_at DESC, id DESC
                   LIMIT ? OFFSET ?""",
            [*parameters, int(limit) + 1, int(offset)],
        ).fetchall()
    has_more = len(rows) > int(limit)
    page_rows = rows[: int(limit)]
    events = [_public_event(tuple(row)) for row in page_rows]
    counts = Counter(event["state"] for event in events)
    return envelope(
        True,
        "Đã nạp Audit Explorer Web-native đã redaction.",
        data={
            "events": events,
            "has_more": has_more,
            "next_offset": int(offset) + int(limit) if has_more else None,
            "summary": {
                "returned": len(events),
                "completed": int(counts.get("completed", 0)),
                "guarded": int(counts.get("guarded", 0)),
                "read_only": int(counts.get("read_only", 0)),
                "category": category,
            },
            "source": "web_audit_events_redacted",
            "boundaries": [
                "Không trả account ID, canonical Telegram ID, request ID, target hoặc detail audit.",
                "Không thay thế audit Bot/Core Bridge; chỉ xem metadata Web-owned đã redaction.",
                "Không có write, provider, payment, wallet, refund, job, deploy hoặc notification action.",
            ],
        },
        status_name="read_only",
    )
