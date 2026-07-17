"""Read-only, Web-native ERP Operations Desk.

This is a narrow aggregation layer for already persisted Web-owned queues. It
does not replace Support Desk, Operations Autopilot, Reliability Follow-up or
Content Handoff; it only gives authorised Customer Care staff one safe place
to see their current queue shape.  The router never calls a bridge, Bot,
provider, payment, wallet, job or delivery API, and it deliberately does not
return row identifiers or customer/content/audit data.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from copyfast_auth import envelope, require_account
from copyfast_autopilot_policy import CASE_STATES as AUTOPILOT_CASE_STATES
from copyfast_content_handoff import HANDOFF_STATUSES, content_handoff_enabled
from copyfast_db import autopilot_enabled, read_transaction, reliability_followup_enabled, support_desk_enabled
from copyfast_reliability import reliability_preflight_code
from copyfast_reliability_policy import FOLLOWUP_SEVERITIES, FOLLOWUP_STATES
from copyfast_support import CASE_PRIORITIES, CASE_STATES, require_support_staff


router = APIRouter(prefix="/api/v1/admin/operations-desk", tags=["ERP Operations Desk"])


# These kinds, routes and actions are server-owned constants.  A database row
# and a browser query parameter can never turn into a redirect or action name.
KIND_ORDER = (
    "support_case",
    "operations_incident",
    "operations_approval",
    "reliability_followup",
    "content_handoff",
)
_KIND_INDEX = {kind: index for index, kind in enumerate(KIND_ORDER)}
_TARGET_ROUTES = {
    "support_case": "/admin/support",
    "operations_incident": "/admin/operations",
    "operations_approval": "/admin/operations",
    "reliability_followup": "/admin/reliability",
    "content_handoff": "/admin/content-handoffs",
}
_ACTION_LABELS = {
    "support_case": ("Mở Support Desk đã bảo vệ",),
    "operations_incident": ("Xem theo dõi Operations",),
    "operations_approval": ("Xem bản ghi phê duyệt Operations",),
    "reliability_followup": ("Xem theo dõi Reliability",),
    "content_handoff": ("Xem hàng chờ Content Handoff",),
}
_TABLE_BY_KIND = {
    "support_case": "web_support_cases",
    "operations_incident": "web_ops_incidents",
    "operations_approval": "web_ops_approvals",
    "reliability_followup": "web_ops_followups",
    "content_handoff": "web_content_handoff_records",
}

_INCIDENT_STATES = frozenset({"open", "investigating", "resolved", "closed"})
_APPROVAL_STATES = frozenset({"awaiting_approval", "approved", "rejected", "expired", "superseded"})
_INCIDENT_SEVERITIES = frozenset({"low", "normal", "high", "critical"})
_APPROVAL_RISKS = frozenset({"web_support", "external_dependency", "unclassified", "financial"})
_APPROVAL_RISK_BY_SEVERITY = {
    "normal": ("web_support",),
    "high": ("external_dependency", "unclassified"),
    "critical": ("financial",),
}
_STATES_BY_KIND = {
    "support_case": CASE_STATES,
    "operations_incident": _INCIDENT_STATES,
    "operations_approval": _APPROVAL_STATES,
    "reliability_followup": FOLLOWUP_STATES,
    "content_handoff": HANDOFF_STATUSES,
}
_ALL_STATES = frozenset({"guarded"}.union(*_STATES_BY_KIND.values()))
_ALL_SEVERITIES = frozenset({"guarded", "low", "normal", "medium", "high", "urgent", "critical"})
_WORK_ITEM_VIEWS = frozenset({"all", "attention"})
_TIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


def _enabled(name: str, *, default: bool = True) -> bool:
    """Read a boolean kill switch without exposing its configured value."""

    return os.environ.get(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}


def _admin_erp_enabled() -> bool:
    """Match the existing Admin ERP umbrella-gate semantics."""

    return _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True)


def _normalize_kind(value: str) -> tuple[str, ...]:
    normalized = str(value or "").strip().lower()
    if normalized in {"", "all"}:
        return KIND_ORDER
    if normalized not in _KIND_INDEX:
        raise HTTPException(status_code=422, detail="Bộ lọc loại hàng Operations Desk không hợp lệ")
    return (normalized,)


def _normalize_filter(value: str, *, allowed: frozenset[str], label: str) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"", "all"}:
        return None
    if normalized not in allowed:
        raise HTTPException(status_code=422, detail=f"Bộ lọc {label} Operations Desk không hợp lệ")
    return normalized


def _normalize_view(value: str) -> str:
    """Accept only the two server-owned Operations Desk list views."""

    normalized = str(value or "").strip().lower() or "all"
    if normalized not in _WORK_ITEM_VIEWS:
        raise HTTPException(status_code=422, detail="Chế độ xem Operations Desk không hợp lệ")
    return normalized


def _source_availability(kind: str, *, staff_role: str) -> str:
    """Return only a public readiness state; never an environment detail."""

    if kind == "support_case":
        return "available" if support_desk_enabled() else "guarded"
    if kind == "operations_incident":
        return "available" if autopilot_enabled() else "guarded"
    if kind == "operations_approval":
        # Approval metadata can disclose operational risk, incident and
        # support references.  It is a Manager-only queue, not an empty queue
        # for Operators, so preserve the unknown/guarded state in the Desk.
        if staff_role != "manager":
            return "guarded"
        return "available" if autopilot_enabled() else "guarded"
    if kind == "reliability_followup":
        if not autopilot_enabled() or not reliability_followup_enabled():
            return "guarded"
        # The Reliability API itself requires this preflight.  Treat an
        # unconfigured source as guarded instead of showing stale rows as a
        # healthy live queue.
        return "available" if reliability_preflight_code() is None else "guarded"
    if kind == "content_handoff":
        return "available" if content_handoff_enabled() else "guarded"
    return "unavailable"


def _table_exists(conn: Any, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return bool(row)


def _enum_clause(column: str, requested: str | None, allowed: frozenset[str]) -> tuple[str | None, list[str]]:
    """Build a static allowlisted SQLite predicate for one persisted enum."""

    if requested is None:
        return None, []
    if requested in allowed:
        return f"{column}=?", [requested]
    if requested == "guarded":
        placeholders = ", ".join("?" for _ in allowed)
        return f"{column} NOT IN ({placeholders})", sorted(allowed)
    return "1=0", []


def _approval_severity_clause(requested: str | None) -> tuple[str | None, list[str]]:
    if requested is None:
        return None, []
    risks = _APPROVAL_RISK_BY_SEVERITY.get(requested)
    if risks:
        if len(risks) == 1:
            return "risk=?", [risks[0]]
        return f"risk IN ({', '.join('?' for _ in risks)})", list(risks)
    if requested == "guarded":
        placeholders = ", ".join("?" for _ in _APPROVAL_RISKS)
        return f"risk NOT IN ({placeholders})", sorted(_APPROVAL_RISKS)
    return "1=0", []


def _attention_clause(kind: str, view: str) -> tuple[str | None, list[str]]:
    """Return the fixed, metadata-only exception policy for the Desk.

    ``attention`` is deliberately a server-side, per-source policy rather
    than a browser filter.  It has no record ID, account, text, assignment,
    provider or payment input and applies before count/pagination so the
    returned page is complete for the selected safe view.
    """

    if view == "all":
        return None, []
    if kind == "support_case":
        # Terminal support cases stay out even if they once carried a high
        # priority.  Active cases need attention when their priority is high
        # or urgent, or when their state signals direct staff/refund work.
        return (
            "state NOT IN ('resolved', 'closed') AND "
            "(priority IN ('high', 'urgent') OR state IN ('new', 'reviewing', 'refund_pending'))",
            [],
        )
    if kind == "operations_incident":
        return "state IN ('open', 'investigating')", []
    if kind == "operations_approval":
        return "state='awaiting_approval'", []
    if kind == "reliability_followup":
        return "state IN ('open', 'acknowledged')", []
    if kind == "content_handoff":
        return "handoff_status IN ('review', 'approved_for_handoff', 'blocked')", []
    raise ValueError("Loại nguồn Operations Desk không xác định")


def _staff_scope_clause(kind: str, staff_role: str) -> tuple[str | None, list[str]]:
    """Return a static, fail-closed staff predicate before count/pagination."""

    if kind == "reliability_followup":
        if staff_role == "manager":
            return "required_role IN ('operator', 'manager')", []
        if staff_role == "operator":
            return "required_role='operator'", []
        return "1=0", []
    if kind == "operations_approval" and staff_role != "manager":
        # This remains a defence in depth rule even though availability hides
        # the source for an Operator before any query is attempted.
        return "1=0", []
    return None, []


def _query_for(
    kind: str,
    *,
    view: str,
    state: str | None,
    severity: str | None,
    include_rows: bool,
    row_limit: int,
    staff_role: str,
) -> tuple[str, list[Any]]:
    """Return a fully server-authored query for one narrow source projection."""

    clauses: list[str] = []
    params: list[Any] = []
    if kind == "support_case":
        state_clause, state_params = _enum_clause("state", state, CASE_STATES)
        level_clause, level_params = _enum_clause("priority", severity, CASE_PRIORITIES)
        select = "id, state, priority, updated_at"
        table = "web_support_cases"
        order = "updated_at DESC, id ASC"
    elif kind == "operations_incident":
        state_clause, state_params = _enum_clause("state", state, _INCIDENT_STATES)
        level_clause, level_params = _enum_clause("severity", severity, _INCIDENT_SEVERITIES)
        select = "id, state, severity, last_observed_at"
        table = "web_ops_incidents"
        order = "last_observed_at DESC, id ASC"
    elif kind == "operations_approval":
        state_clause, state_params = _enum_clause("state", state, _APPROVAL_STATES)
        level_clause, level_params = _approval_severity_clause(severity)
        select = "id, state, risk, COALESCE(decided_at, proposed_at)"
        table = "web_ops_approvals"
        order = "COALESCE(decided_at, proposed_at) DESC, id ASC"
    elif kind == "reliability_followup":
        state_clause, state_params = _enum_clause("state", state, FOLLOWUP_STATES)
        level_clause, level_params = _enum_clause("severity", severity, FOLLOWUP_SEVERITIES)
        select = "id, state, severity, updated_at"
        table = "web_ops_followups"
        order = "updated_at DESC, id ASC"
    elif kind == "content_handoff":
        state_clause, state_params = _enum_clause("handoff_status", state, HANDOFF_STATUSES)
        if severity is None or severity == "normal":
            level_clause, level_params = None, []
        else:
            # Handoff records do not own a severity field.  A non-normal
            # filter therefore has no matching row rather than inventing a
            # priority from a title, staff note or customer record.
            level_clause, level_params = "1=0", []
        select = "id, handoff_status, 'normal', updated_at"
        table = "web_content_handoff_records"
        order = "updated_at DESC, id ASC"
        clauses.append("record_state='active'")
    else:  # Defensive only: callers already use _normalize_kind.
        raise ValueError("Loại nguồn Operations Desk không xác định")

    attention_clause, attention_params = _attention_clause(kind, view)
    staff_clause, staff_params = _staff_scope_clause(kind, staff_role)
    for clause, values in (
        (staff_clause, staff_params),
        (state_clause, state_params),
        (level_clause, level_params),
        (attention_clause, attention_params),
    ):
        if clause:
            clauses.append(clause)
            params.extend(values)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    if not include_rows:
        return f"SELECT COUNT(*) FROM {table}{where}", params
    params.append(int(row_limit))
    return f"SELECT {select} FROM {table}{where} ORDER BY {order} LIMIT ?", params


def _canonical_enum(value: Any, allowed: frozenset[str]) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else "guarded"


def _approval_severity(risk: Any) -> str:
    normalized = str(risk or "").strip().lower()
    if normalized == "financial":
        return "critical"
    if normalized in {"external_dependency", "unclassified"}:
        return "high"
    if normalized == "web_support":
        return "normal"
    return "guarded"


def _safe_timestamp(value: Any) -> str:
    candidate = str(value or "")
    return candidate if _TIME_PATTERN.fullmatch(candidate) else "unavailable"


def _project_item(kind: str, row: tuple[Any, ...], *, staff_role: str) -> dict[str, Any]:
    """Create an identifier-free, reviewed work-item projection."""

    raw_id, raw_state, raw_level, raw_updated_at = row
    state = _canonical_enum(raw_state, _STATES_BY_KIND[kind])
    if kind == "support_case":
        level_name = "priority"
        level = _canonical_enum(raw_level, CASE_PRIORITIES)
    elif kind == "operations_incident":
        level_name = "severity"
        level = _canonical_enum(raw_level, _INCIDENT_SEVERITIES)
    elif kind == "operations_approval":
        level_name = "severity"
        level = _approval_severity(raw_level)
    elif kind == "reliability_followup":
        level_name = "severity"
        level = _canonical_enum(raw_level, FOLLOWUP_SEVERITIES)
    else:
        level_name = "severity"
        level = "normal"

    actions = _ACTION_LABELS[kind]
    if kind == "operations_approval" and staff_role != "manager":
        actions = ("Chờ Support Manager quyết định",)
    updated_at = _safe_timestamp(raw_updated_at)
    result: dict[str, Any] = {
        "kind": kind,
        "target_route": _TARGET_ROUTES[kind],
        "state": state,
        level_name: level,
        "updated_at": updated_at,
        "available_actions": list(actions),
        # These fields are intentionally kept private until sorting and are
        # removed by _public_item before a response is produced.
        "_sort_id": str(raw_id or ""),
        "_sort_updated_at": updated_at if updated_at != "unavailable" else "",
    }
    return result


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    keys = ("kind", "target_route", "state", "priority", "severity", "updated_at", "available_actions")
    return {key: item[key] for key in keys if key in item}


def _source_status(kind: str, availability: str, count: int | None) -> dict[str, Any]:
    return {"kind": kind, "availability": availability, "count": count}


def _load_sources(
    *,
    kinds: tuple[str, ...],
    view: str,
    state: str | None,
    severity: str | None,
    row_limit: int,
    staff_role: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read selected sources under one query-only transaction.

    The count is a complete count for each source, while the item slice is
    bounded to the largest possible requested page.  Taking that bounded top
    slice from every source is sufficient to construct a correct global page
    after their deterministic merge.
    """

    statuses: list[dict[str, Any]] = [
        _source_status(kind, _source_availability(kind, staff_role=staff_role), None) for kind in kinds
    ]
    items: list[dict[str, Any]] = []
    try:
        with read_transaction() as conn:
            for status in statuses:
                if status["availability"] != "available":
                    continue
                kind = str(status["kind"])
                if not _table_exists(conn, _TABLE_BY_KIND[kind]):
                    status["availability"] = "unavailable"
                    continue
                try:
                    count_sql, count_params = _query_for(
                        kind, view=view, state=state, severity=severity, include_rows=False, row_limit=0,
                        staff_role=staff_role,
                    )
                    count_row = conn.execute(count_sql, count_params).fetchone()
                    status["count"] = int(count_row[0] or 0) if count_row else 0
                    if row_limit <= 0:
                        continue
                    row_sql, row_params = _query_for(
                        kind, view=view, state=state, severity=severity, include_rows=True, row_limit=row_limit,
                        staff_role=staff_role,
                    )
                    rows = conn.execute(row_sql, row_params).fetchall()
                    items.extend(
                        _project_item(kind, tuple(row), staff_role=staff_role) for row in rows
                    )
                except sqlite3.Error:
                    # A missing/old schema is not a healthy empty source and
                    # must not leak its SQL error to staff or a browser.
                    status["availability"] = "unavailable"
                    status["count"] = None
    except sqlite3.Error:
        for status in statuses:
            if status["availability"] == "available":
                status["availability"] = "unavailable"
                status["count"] = None
        return [], statuses

    # Stable two-pass sorting makes ties deterministic without returning the
    # private primary key used solely as the server-side tiebreaker.
    items.sort(key=lambda item: (_KIND_INDEX[str(item["kind"])], str(item["_sort_id"])))
    items.sort(key=lambda item: str(item["_sort_updated_at"]), reverse=True)
    return items, statuses


def _desk_payload(
    *,
    items: list[dict[str, Any]],
    statuses: list[dict[str, Any]],
    limit: int | None = None,
    offset: int | None = None,
) -> tuple[dict[str, Any], bool]:
    complete = all(status["availability"] == "available" for status in statuses)
    available_sources = [status for status in statuses if status["availability"] == "available"]
    # If no source could be read, even a scoped zero would be easy for a UI to
    # misread as a healthy empty queue.  Preserve the unknown as null instead.
    available_total = (
        sum(int(status["count"] or 0) for status in available_sources) if available_sources else None
    )
    total = available_total if complete else None
    if limit is None or offset is None:
        return {
            "summary": {
                "total": total,
                "available_total": available_total,
                "counts_by_kind": {str(status["kind"]): status["count"] for status in statuses},
            },
            "sources": statuses,
            "partial": not complete,
        }, complete

    page = [_public_item(item) for item in items[offset: offset + limit]]
    has_more = (offset + len(page)) < int(total) if complete and total is not None else None
    return {
        "items": page,
        "returned": len(page),
        "total": total,
        "available_total": available_total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": offset + limit if has_more else None,
        "sources": statuses,
        "partial": not complete,
        "boundaries": [
            "Không trả ID, account/canonical identity, email, tiêu đề, nội dung, audit detail hay payload nguồn.",
            "Không có write, bridge, Bot, provider, payment, wallet, job, delivery hoặc deploy action.",
            "target_route là allowlist do máy chủ đặt; không nhận redirect hoặc ID từ trình duyệt.",
        ],
    }, complete


def _erp_disabled_payload(kinds: tuple[str, ...], *, limit: int | None = None, offset: int | None = None) -> dict[str, Any]:
    statuses = [_source_status(kind, "guarded", None) for kind in kinds]
    if limit is None or offset is None:
        return {
            "summary": {"total": None, "available_total": None, "counts_by_kind": {kind: None for kind in kinds}},
            "sources": statuses,
            "partial": True,
        }
    return {
        "items": [],
        "returned": 0,
        "total": None,
        "available_total": None,
        "limit": limit,
        "offset": offset,
        "has_more": None,
        "next_offset": None,
        "sources": statuses,
        "partial": True,
        "boundaries": ["Admin ERP đang guarded; không truy vấn hoặc thực hiện hành động nguồn."],
    }


@router.get("/summary")
async def summary(account: dict = Depends(require_account)) -> dict[str, Any]:
    """Return only aggregate source readiness/counts for signed support staff."""

    staff_role = require_support_staff(account)
    if not _admin_erp_enabled():
        return envelope(
            False,
            "Admin ERP đang guarded; Operations Desk không truy vấn nguồn.",
            data=_erp_disabled_payload(KIND_ORDER),
            status_name="guarded",
            error_code="WEBAPP_ADMIN_ERP_DISABLED",
        )
    _items, statuses = _load_sources(
        kinds=KIND_ORDER,
        view="all",
        state=None,
        severity=None,
        row_limit=0,
        staff_role=staff_role,
    )
    data, complete = _desk_payload(items=[], statuses=statuses)
    return envelope(
        complete,
        "Đã nạp tổng quan Operations Desk." if complete else "Một hoặc nhiều nguồn Operations Desk đang guarded hoặc unavailable.",
        data=data,
        status_name="read_only" if complete else "guarded",
        error_code=None if complete else "WEBAPP_OPERATIONS_DESK_SOURCE_GUARDED",
    )


@router.get("/work-items")
async def work_items(
    view: str = Query("all", max_length=24),
    kind: str = Query("all", max_length=48),
    state: str = Query("all", max_length=40),
    severity: str = Query("all", max_length=24),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10_000),
    account: dict = Depends(require_account),
) -> dict[str, Any]:
    """Return a deterministic, identifier-free page across selected sources."""

    staff_role = require_support_staff(account)
    requested_view = _normalize_view(view)
    kinds = _normalize_kind(kind)
    requested_state = _normalize_filter(state, allowed=_ALL_STATES, label="trạng thái")
    requested_severity = _normalize_filter(severity, allowed=_ALL_SEVERITIES, label="mức ưu tiên")
    if not _admin_erp_enabled():
        return envelope(
            False,
            "Admin ERP đang guarded; Operations Desk không truy vấn nguồn.",
            data=_erp_disabled_payload(kinds, limit=limit, offset=offset),
            status_name="guarded",
            error_code="WEBAPP_ADMIN_ERP_DISABLED",
        )
    # Every source yields at most the largest possible global page.  This is
    # bounded by validated limit/offset (10,100 rows maximum per source).
    source_window = int(limit) + int(offset)
    items, statuses = _load_sources(
        kinds=kinds,
        view=requested_view,
        state=requested_state,
        severity=requested_severity,
        row_limit=source_window,
        staff_role=staff_role,
    )
    data, complete = _desk_payload(items=items, statuses=statuses, limit=limit, offset=offset)
    return envelope(
        complete,
        (
            "Đã nạp hàng cần xử lý Operations Desk đã redaction."
            if requested_view == "attention" and complete
            else "Đã nạp hàng Operations Desk đã redaction."
            if complete
            else "Một hoặc nhiều nguồn Operations Desk đang guarded hoặc unavailable."
        ),
        data=data,
        status_name="read_only" if complete else "guarded",
        error_code=None if complete else "WEBAPP_OPERATIONS_DESK_SOURCE_GUARDED",
    )
