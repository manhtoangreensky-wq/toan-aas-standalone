"""Read-only ERP monitor for the Web-native Inbox scheduler.

This module deliberately exposes a *redacted* operational view of durable
``web_notification_runs`` receipts.  It is not a scheduler control plane:
there is no tick trigger, lease/nonce access, provider/Bot bridge, payment,
wallet, job, deploy, secret or self-repair action here.

The notification scheduler owns its own authenticated execution protocol in
``copyfast_notification_center``.  This monitor reads only five reviewed
columns after the signed Web administrator has been checked server-side.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

import copyfast_notification_center
from copyfast_auth import envelope, require_admin
from copyfast_db import notification_automation_enabled, notification_center_enabled, read_transaction


router = APIRouter(prefix="/api/v1/admin/automation", tags=["Web Admin Automation Monitor"])


POLICY_VERSION = "web_admin_automation_monitor_v1"
MAX_LIST_LIMIT = 50
MAX_LIST_OFFSET = 10_000
# The monitor is an admin observability read, not a bulk export. Validate at
# most this many receipts per request; a larger retained history remains
# guarded rather than producing an unverified aggregate.
MAX_INTEGRITY_SCAN_ROWS = 100_000
RUN_STATES = frozenset({"started", "completed", "failed", "guarded"})
SCHEDULER_STATES = frozenset(
    {
        "ready",
        "center_disabled",
        "automation_disabled",
        "persistent_store_unverified",
        "topology_unverified",
        "single_replica_required",
        "limits_unverified",
        "guarded",
    }
)
_PREFLIGHT_STATES = {
    None: "ready",
    "NOTIFY_CENTER_DISABLED": "center_disabled",
    "NOTIFY_AUTOMATION_DISABLED": "automation_disabled",
    "NOTIFY_PERSISTENT_STORE_UNVERIFIED": "persistent_store_unverified",
    "NOTIFY_TOPOLOGY_UNVERIFIED": "topology_unverified",
    "NOTIFY_REPLICA_COUNT_UNVERIFIED": "single_replica_required",
    "NOTIFY_MULTI_REPLICA_BLOCKED": "single_replica_required",
    "NOTIFY_MAX_RUN_SECONDS_UNVERIFIED": "limits_unverified",
    "NOTIFY_MAX_ACTIONS_UNVERIFIED": "limits_unverified",
    "NOTIFY_LIMITS_UNVERIFIED": "limits_unverified",
}


def _enabled(name: str, *, default: bool) -> bool:
    return os.environ.get(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}


def _admin_erp_enabled() -> bool:
    """Return the shared ERP directory kill switch without trusting a client."""

    return _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True)


def _scheduler_state() -> str:
    """Project scheduler readiness to a closed, configuration-free enum."""

    if not notification_center_enabled():
        return "center_disabled"
    if not notification_automation_enabled():
        return "automation_disabled"
    state = _PREFLIGHT_STATES.get(copyfast_notification_center._scheduler_preflight_code(), "guarded")
    return state if state in SCHEDULER_STATES else "guarded"


def _boundary(**extra: Any) -> dict[str, Any]:
    """Return only stable public metadata for this intentionally narrow read."""

    return {
        "source": "web_notification_runs_redacted",
        "policy_version": POLICY_VERSION,
        "read_only": True,
        "boundaries": [
            "Chỉ đọc metadata receipt scheduler đã được redact; không có thao tác chạy, retry hoặc tự sửa.",
            "Không trả run/request ID, nonce, HMAC, lease, receipt JSON, source, account hoặc nội dung khách hàng.",
            "Không gọi Bot, provider, wallet/Xu, PayOS, job, delivery, secret, deployment hoặc external notification.",
        ],
        **extra,
    }


def _safe_timestamp(value: Any, *, optional: bool) -> str | None:
    """Normalize only timezone-aware receipt timestamps; never echo malformed DB text."""

    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) > 48:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _safe_count(value: Any, *, maximum: int) -> int | None:
    """Accept only bounded integer counters produced by the scheduler."""

    # SQLite permits REAL values in INTEGER-affinity columns.  A coercion with
    # ``int(value)`` would silently turn a malformed ``1.9`` receipt into 1,
    # which makes an operational record appear trustworthy.  Scheduler counters
    # and SQLite COUNT(*) are native integers, so fail closed for every other
    # representation (including bool and numeric-looking strings).
    if type(value) is not int:
        return None
    number = value
    if number < 0 or number > maximum:
        return None
    return number


def _run_projection(row: Any) -> dict[str, Any] | None:
    """Return the exact reviewed receipt subset, or fail closed for one row."""

    try:
        state, action_count, candidate_count, started_at, finished_at = tuple(row)
    except (TypeError, ValueError):
        return None
    normalized_state = str(state or "").strip().lower()
    actions = _safe_count(action_count, maximum=copyfast_notification_center.MAX_ACTIONS_PER_RUN)
    candidates = _safe_count(candidate_count, maximum=copyfast_notification_center.MAX_CANDIDATES_PER_RUN)
    started = _safe_timestamp(started_at, optional=False)
    finished = _safe_timestamp(finished_at, optional=True)
    if normalized_state not in RUN_STATES or actions is None or candidates is None or started is None:
        return None
    # A terminal receipt without its terminal time, or a still-started receipt
    # carrying one, would make the operational view misleading.  Guard it
    # rather than filling a value from a different record.
    if (normalized_state == "started" and finished is not None) or (normalized_state != "started" and finished is None):
        return None
    return {
        "state": normalized_state,
        "action_count": actions,
        "candidate_count": candidates,
        "started_at": started,
        "finished_at": finished,
    }


def _scheduler_payload(*, state: str) -> dict[str, Any]:
    return {
        "center_enabled": notification_center_enabled(),
        "automation_enabled": notification_automation_enabled(),
        "state": state if state in SCHEDULER_STATES else "guarded",
    }


def _empty_summary(*, state: str) -> dict[str, Any]:
    return _boundary(
        scheduler=_scheduler_payload(state=state),
        latest_run=None,
        run_counts=None,
        integrity_guarded=False,
    )


def _empty_runs(*, state: str, limit: int, offset: int) -> dict[str, Any]:
    return _boundary(
        scheduler=_scheduler_payload(state=state),
        items=[],
        returned=0,
        limit=int(limit),
        offset=int(offset),
        has_more=False,
        next_offset=None,
    )


def _monitor_status(*, scheduler_state: str, malformed: bool = False) -> str:
    return "read_only" if scheduler_state == "ready" and not malformed else "guarded"


def _monitor_message(*, scheduler_state: str, has_history: bool) -> str:
    if scheduler_state == "ready":
        return "Đã nạp Automation Monitor chỉ đọc với receipt scheduler đã được redaction."
    if scheduler_state == "automation_disabled":
        return "Inbox Automation đang ở chế độ quan sát; lịch sử receipt chỉ đọc vẫn được giữ riêng tư."
    if scheduler_state == "center_disabled":
        return "Inbox Automation đang tắt an toàn; Automation Monitor không đọc receipt cũ."
    if has_history:
        return "Automation Monitor đang bảo vệ scheduler; lịch sử receipt đã được redaction."
    return "Automation Monitor đang bảo vệ scheduler; chưa có receipt nào được hiển thị."


def _monitor_error_code(*, scheduler_state: str, malformed: bool = False) -> str | None:
    if malformed:
        return "ADMIN_AUTOMATION_MONITOR_DATA_GUARDED"
    return None if scheduler_state == "ready" else "ADMIN_AUTOMATION_MONITOR_GUARDED"


def _integrity_guarded(conn: Any) -> bool:
    """Validate every reviewed receipt shape, or remain guarded.

    A SQL affinity/GLOB check is not enough: a semantically invalid timestamp
    can look like ISO text. Iterate the same five-column projection used for
    the page itself, without selecting private fields. A history beyond the
    fixed server bound is deliberately treated as unverified rather than
    presenting a partial aggregate as healthy.
    """

    rows = conn.execute(
        """SELECT state, action_count, candidate_count, started_at, finished_at
           FROM web_notification_runs
           LIMIT ?""",
        (MAX_INTEGRITY_SCAN_ROWS + 1,),
    )
    for index, row in enumerate(rows):
        if index >= MAX_INTEGRITY_SCAN_ROWS or _run_projection(row) is None:
            return True
    return False


@router.get("/summary")
async def summary(request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Return a redacted aggregate without touching scheduler control tables."""

    del request, account
    if not _admin_erp_enabled():
        return envelope(
            True,
            "Admin ERP trên Web đang tạm khóa; Automation Monitor không đọc receipt.",
            data=_empty_summary(state="guarded"),
            status_name="guarded",
            error_code="WEBAPP_ADMIN_ERP_DISABLED",
        )
    scheduler_state = _scheduler_state()
    if scheduler_state == "center_disabled":
        return envelope(
            True,
            "Inbox Automation đang tắt an toàn; Automation Monitor không đọc receipt cũ.",
            data=_empty_summary(state=scheduler_state),
            status_name="guarded",
            error_code="ADMIN_AUTOMATION_MONITOR_GUARDED",
        )

    # App startup owns schema creation.  This read surface must never issue
    # DDL or a scheduler transaction just to render an ERP card.
    with read_transaction() as conn:
        latest_row = conn.execute(
            """SELECT state, action_count, candidate_count, started_at, finished_at
               FROM web_notification_runs
               ORDER BY started_at DESC, finished_at DESC, state DESC, action_count DESC, candidate_count DESC, id DESC
               LIMIT 1"""
        ).fetchone()
        count_rows = conn.execute("SELECT state, COUNT(*) FROM web_notification_runs GROUP BY state").fetchall()
        integrity_guarded = _integrity_guarded(conn)

    latest = _run_projection(latest_row) if latest_row else None
    malformed = integrity_guarded or bool(latest_row and latest is None)
    counts = {state: 0 for state in sorted(RUN_STATES)}
    counts["unknown"] = 0
    for row_state, count in count_rows:
        normalized_state = str(row_state or "").strip().lower()
        safe_count = _safe_count(count, maximum=1_000_000_000)
        if safe_count is None:
            malformed = True
            counts["unknown"] += 1
        elif normalized_state in RUN_STATES:
            counts[normalized_state] += safe_count
        else:
            counts["unknown"] += safe_count
            malformed = True
    status_name = _monitor_status(scheduler_state=scheduler_state, malformed=malformed)
    return envelope(
        True,
        _monitor_message(scheduler_state=scheduler_state, has_history=latest is not None),
        data=_boundary(
            scheduler=_scheduler_payload(state=scheduler_state),
            latest_run=latest,
            run_counts=counts,
            # Aggregate SQL can count state buckets but cannot make every
            # persisted receipt trustworthy.  Keep that uncertainty explicit
            # so Portal hides numeric aggregates instead of presenting a
            # partial bucket as a verified operational total.
            integrity_guarded=malformed,
        ),
        status_name=status_name,
        error_code=_monitor_error_code(scheduler_state=scheduler_state, malformed=malformed),
    )


@router.get("/runs")
async def runs(
    request: Request,
    limit: int = Query(25, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """List only redacted scheduler receipt summaries with bounded pagination."""

    del request, account
    if not _admin_erp_enabled():
        return envelope(
            True,
            "Admin ERP trên Web đang tạm khóa; Automation Monitor không đọc receipt.",
            data=_empty_runs(state="guarded", limit=limit, offset=offset),
            status_name="guarded",
            error_code="WEBAPP_ADMIN_ERP_DISABLED",
        )
    scheduler_state = _scheduler_state()
    if scheduler_state == "center_disabled":
        return envelope(
            True,
            "Inbox Automation đang tắt an toàn; Automation Monitor không đọc receipt cũ.",
            data=_empty_runs(state=scheduler_state, limit=limit, offset=offset),
            status_name="guarded",
            error_code="ADMIN_AUTOMATION_MONITOR_GUARDED",
        )

    with read_transaction() as conn:
        integrity_guarded = _integrity_guarded(conn)
        rows = conn.execute(
            """SELECT state, action_count, candidate_count, started_at, finished_at
               FROM web_notification_runs
               ORDER BY started_at DESC, finished_at DESC, state DESC, action_count DESC, candidate_count DESC, id DESC
               LIMIT ? OFFSET ?""",
            (int(limit) + 1, int(offset)),
        ).fetchall()
    has_more = len(rows) > int(limit) and int(offset) + int(limit) <= MAX_LIST_OFFSET
    items: list[dict[str, Any]] = []
    malformed = integrity_guarded
    for row in rows[: int(limit)]:
        projected = _run_projection(row)
        if projected is None:
            malformed = True
            continue
        items.append(projected)
    status_name = _monitor_status(scheduler_state=scheduler_state, malformed=malformed)
    return envelope(
        True,
        _monitor_message(scheduler_state=scheduler_state, has_history=bool(items)),
        data=_boundary(
            scheduler=_scheduler_payload(state=scheduler_state),
            items=items,
            returned=len(items),
            limit=int(limit),
            offset=int(offset),
            has_more=has_more,
            next_offset=int(offset) + int(limit) if has_more else None,
        ),
        status_name=status_name,
        error_code=_monitor_error_code(scheduler_state=scheduler_state, malformed=malformed),
    )
