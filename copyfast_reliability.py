"""Private Web Reliability Follow-up with bounded, sanitized metadata only.

This module turns a small allow-list of *unexpected* Web-native 5xx responses
and deterministic Support Desk triage into an internal staff follow-up queue.
It is deliberately not a diagnostic log, auto-repair agent, deployment tool
or customer-contact system.  It never stores a raw URL/query/body, exception
text, client identity, credential, payment/provider/Bot data or stack trace.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import threading
import time
from typing import Any, Callable
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_autopilot_policy import incident_fingerprint
from copyfast_db import (
    autopilot_enabled,
    autopilot_safe_remediation_enabled,
    best_effort_transaction,
    ensure_copyfast_schema,
    read_transaction,
    reliability_followup_enabled,
    transaction,
    utc_now,
)
from copyfast_reliability_policy import (
    FOLLOWUP_SEVERITIES,
    FOLLOWUP_STATES,
    normalize_route_family,
    parse_signal_threshold,
    signal_code_for_status,
    utc_five_minute_bucket_key,
)
from copyfast_support import require_support_staff


router = APIRouter(tags=["Web Reliability Follow-up"])

POLICY_VERSION = 2
MAX_SIGNAL_COUNT = 10_000
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
MAX_SIGNAL_BUCKETS_PER_RUN = 100
MAX_COMPLAINTS_PER_RUN = 100
MAX_RUNTIME_BUCKET_PRUNES_PER_RUN = 200
RUNTIME_SIGNAL_RETENTION_DAYS = 30
RUNTIME_CAPTURE_LOCK_TIMEOUT_SECONDS = 0.05
RUNTIME_CAPTURE_DEFAULT_INTERVAL_SECONDS = 0.25
MAX_CAPTURE_RATE_KEYS = 256
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
# An unverified semantic customer-waiting clock is a reason for a human to
# inspect an otherwise ordinary Web Support case, never evidence of an SLA
# breach.  Financial/external/unclassified cases are independently actionable
# through their ``awaiting_operator`` disposition.
ACTIONABLE_TRIAGE_SLA_STATUSES = frozenset({"at_risk", "breached", "unverified"})

# Process-local throttling stores only fixed policy route labels and a monotonic
# deadline. It never contains a request id, URL, query, account, payload or
# client identifier. Durable counts remain in SQLite only when the small,
# best-effort write lock is immediately available.
_capture_rate_lock = threading.Lock()
_capture_next_allowed: dict[tuple[str, str], float] = {}


class ReliabilityLeaseLost(RuntimeError):
    """Raised when a scheduler fence changes before a metadata write."""


def _incident_secret() -> str | None:
    value = os.environ.get("WEBAPP_AUTOPILOT_INCIDENT_SECRET", "")
    return value if len(value.encode("utf-8")) >= 32 else None


def _threshold() -> int | None:
    return parse_signal_threshold(os.environ.get("WEBAPP_RELIABILITY_SIGNAL_THRESHOLD"))


def _capture_interval_seconds() -> float | None:
    """Return a bounded local write limiter without widening feature scope."""
    raw = os.environ.get("WEBAPP_RELIABILITY_CAPTURE_MIN_INTERVAL_MS", "").strip()
    if not raw:
        return RUNTIME_CAPTURE_DEFAULT_INTERVAL_SECONDS
    try:
        milliseconds = int(raw)
    except ValueError:
        return None
    if milliseconds < 0 or milliseconds > 5_000:
        return None
    return milliseconds / 1_000


def _capture_allowed(*, route_family: str, bucket: str) -> bool:
    interval = _capture_interval_seconds()
    if interval is None:
        return False
    if interval <= 0:
        return True
    now = time.monotonic()
    key = (route_family, bucket)
    with _capture_rate_lock:
        next_allowed = _capture_next_allowed.get(key, 0.0)
        if next_allowed > now:
            return False
        _capture_next_allowed[key] = now + interval
        if len(_capture_next_allowed) > MAX_CAPTURE_RATE_KEYS:
            expired = [candidate for candidate, deadline in _capture_next_allowed.items() if deadline <= now]
            for candidate in expired[:MAX_CAPTURE_RATE_KEYS]:
                _capture_next_allowed.pop(candidate, None)
            if len(_capture_next_allowed) > MAX_CAPTURE_RATE_KEYS:
                # A bounded map is preferable to retaining even fixed labels
                # indefinitely in a long-lived worker process.
                oldest = min(_capture_next_allowed, key=_capture_next_allowed.get)
                _capture_next_allowed.pop(oldest, None)
    return True


def reliability_preflight_code() -> str | None:
    """Return a stable guard code without exposing configuration contents."""
    if not reliability_followup_enabled():
        return "OPS_RELIABILITY_FOLLOWUP_DISABLED"
    if not _incident_secret():
        return "OPS_RELIABILITY_INCIDENT_SECRET_UNAVAILABLE"
    if _threshold() is None:
        return "OPS_RELIABILITY_THRESHOLD_UNVERIFIED"
    return None


def _boundary(**extra: Any) -> dict[str, Any]:
    preflight = reliability_preflight_code()
    return {
        "execution": "web_native_reliability_metadata_only",
        "data_origin": "sanitized_web_response_metadata_and_signed_operations_scheduler_only",
        "policy_version": POLICY_VERSION,
        "reliability_followup_enabled": reliability_followup_enabled(),
        "safe_remediation_enabled": autopilot_safe_remediation_enabled(),
        # This speaks only for Reliability's own key/threshold config. The
        # Operations tick has separate persistence/topology/lease preflight;
        # never turn this field into a claim that the scheduler is runnable.
        "reliability_config_ready": preflight is None,
        "bot_called": False,
        "provider_called": False,
        "wallet_mutated": False,
        "payment_mutated": False,
        "payment_processed": False,
        "customer_reply_sent": False,
        "external_notification_sent": False,
        "telegram_sent": False,
        "email_sent": False,
        "sms_sent": False,
        "web_push_sent": False,
        "job_retried": False,
        "asset_delivery_changed": False,
        "role_changed": False,
        "secret_changed": False,
        "deployment_changed": False,
        "self_modifying_code": False,
        "dangerous_action_executed": False,
        **extra,
    }


def _require_reliability() -> None:
    if not autopilot_enabled():
        raise HTTPException(status_code=503, detail="Operations Autopilot chưa được bật cho Reliability Follow-up.")
    if not reliability_followup_enabled():
        raise HTTPException(status_code=503, detail="Reliability Follow-up đang tắt an toàn.")
    code = reliability_preflight_code()
    if code:
        raise HTTPException(status_code=503, detail="Reliability Follow-up chưa có cấu hình an toàn.")


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key Reliability không hợp lệ")
    return key


def _json_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _followup_fingerprint(*, source_kind: str, source_id: str, secret: str) -> str:
    # The HMAC avoids turning a support-case UUID or fixed route label into a
    # reusable lookup oracle in the follow-up table.
    return incident_fingerprint(
        kind="reliability_followup",
        scope=f"{source_kind}:{source_id}",
        error_code="",
        secret=secret,
    )


def _runtime_severity(*, count: int, threshold: int) -> str:
    if count >= max(threshold * 4, threshold + 9):
        return "critical"
    if count >= max(threshold * 2, threshold + 3):
        return "high"
    return "medium"


def _complaint_severity(*, sla_status: str, risk: str) -> str:
    if sla_status == "breached" or risk == "financial":
        return "critical"
    if sla_status == "at_risk" or risk in {"external_dependency", "unclassified"}:
        return "high"
    return "medium"


def _triage_is_actionable(*, disposition: str, sla_status: str) -> bool:
    """Return narrow local follow-up eligibility, never a resolution claim."""
    return disposition == "awaiting_operator" or sla_status in ACTIONABLE_TRIAGE_SLA_STATUSES


def record_runtime_failure(request: Request, *, status_code: int, occurred_at: datetime | None = None) -> None:
    """Best-effort, non-interfering capture for a sanitized unexpected 5xx.

    This intentionally reads only ``request.url.path``.  Query string,
    headers, cookies, client address, body, session, exception and response
    payload are never accessed.  Every failure is swallowed because
    observability must not turn a customer response into a second failure.
    """
    try:
        if not autopilot_enabled() or not reliability_followup_enabled():
            return
        signal_code = signal_code_for_status(status_code)
        path = str(request.url.path)
        route_family = normalize_route_family(path)
        secret = _incident_secret()
        if not signal_code or not route_family or not secret or _threshold() is None:
            return
        if occurred_at is not None:
            if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None:
                return
            now_dt = occurred_at.astimezone(timezone.utc).replace(microsecond=0)
        else:
            now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        now = now_dt.isoformat(timespec="seconds")
        bucket = utc_five_minute_bucket_key(now_dt)
        if not _capture_allowed(route_family=route_family, bucket=bucket):
            return
        fingerprint = incident_fingerprint(
            kind="runtime_signal",
            scope=f"{route_family}:{bucket}",
            error_code=signal_code,
            secret=secret,
        )
        # Schema is initialized during app lifespan. Never call the broad
        # additive migration from a failing request path, and never wait for
        # the normal 30-second SQLite writer timeout to capture telemetry.
        with best_effort_transaction(timeout_seconds=RUNTIME_CAPTURE_LOCK_TIMEOUT_SECONDS) as conn:
            conn.execute(
                """INSERT INTO web_ops_runtime_signal_buckets
                   (id, bucket_fingerprint, route_family, signal_code, count, revision,
                    first_seen_at, last_seen_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                   ON CONFLICT(bucket_fingerprint) DO UPDATE SET
                     count=web_ops_runtime_signal_buckets.count + 1,
                     revision=web_ops_runtime_signal_buckets.revision + 1,
                     last_seen_at=excluded.last_seen_at,
                     updated_at=excluded.updated_at
                   WHERE web_ops_runtime_signal_buckets.count < ?""",
                (str(uuid.uuid4()), fingerprint, route_family, signal_code, now, now, now, now, MAX_SIGNAL_COUNT),
            )
            conn.execute(
                """INSERT INTO web_ops_runtime_signal_totals
                   (route_family, signal_code, occurrence_count, revision, first_seen_at, last_seen_at, updated_at)
                   VALUES (?, ?, 1, 1, ?, ?, ?)
                   ON CONFLICT(route_family, signal_code) DO UPDATE SET
                     occurrence_count=web_ops_runtime_signal_totals.occurrence_count + 1,
                     revision=web_ops_runtime_signal_totals.revision + 1,
                     last_seen_at=excluded.last_seen_at,
                     updated_at=excluded.updated_at
                   WHERE web_ops_runtime_signal_totals.occurrence_count < ?""",
                (route_family, signal_code, now, now, now, MAX_SIGNAL_COUNT),
            )
    except Exception:
        # Never log raw request context from this signal path and never change
        # the original request's response or exception behavior.
        return


def _event(
    conn: Any, *, followup_id: str, actor_account_id: str | None, action: str, state: str, revision: int, now: str,
) -> None:
    conn.execute(
        """INSERT INTO web_ops_followup_events
           (id, followup_id, actor_account_id, action, state, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), followup_id, actor_account_id or None, action, state, revision, now),
    )


def _upsert_followup(
    conn: Any,
    *,
    run_id: str,
    source_kind: str,
    source_id: str,
    account_id: str | None,
    required_role: str,
    severity: str,
    source_revision: int,
    secret: str,
    now: str,
) -> tuple[str, bool]:
    """Create/update one deduped metadata follow-up without external work."""
    fingerprint = _followup_fingerprint(source_kind=source_kind, source_id=source_id, secret=secret)
    row = conn.execute(
        """SELECT id, source_kind, source_id, account_id, required_role, severity, state,
                  source_revision, revision, opened_at, updated_at, acknowledged_at, resolved_at
           FROM web_ops_followups WHERE fingerprint=?""",
        (fingerprint,),
    ).fetchone()
    if not row:
        followup_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_ops_followups
               (id, fingerprint, source_kind, source_id, account_id, required_role, severity, state,
                source_revision, revision, created_by_run_id, opened_at, updated_at, acknowledged_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, 1, ?, ?, ?, NULL, NULL)""",
            (followup_id, fingerprint, source_kind, source_id, account_id, required_role, severity,
             source_revision, run_id, now, now),
        )
        _event(conn, followup_id=followup_id, actor_account_id=None, action="opened", state="open", revision=1, now=now)
        return "opened", True

    current = tuple(row)
    followup_id = str(current[0])
    current_state = str(current[6])
    current_source_revision = int(current[7])
    current_revision = int(current[8])
    incoming_account = account_id or ""
    existing_account = str(current[3] or "")
    source_changed = source_revision > current_source_revision
    metadata_changed = (
        source_changed
        or str(current[4]) != required_role
        or str(current[5]) != severity
        or existing_account != incoming_account
    )
    can_reopen_superseded = (
        current_state == "superseded"
        and source_kind == "support_triage"
        and source_revision > current_source_revision
    )
    if current_state == "superseded" and not can_reopen_superseded:
        # A stale scheduler snapshot must never resurrect a complaint that
        # was already made non-actionable.  A Support triage can re-open only
        # from a newer, freshly classified source revision.
        return "noop", False
    if current_state == "resolved" and not source_changed:
        return "noop", False
    next_state = "open" if (current_state == "resolved" and source_changed) or can_reopen_superseded else current_state
    if not metadata_changed and next_state == current_state:
        return "noop", False
    next_revision = current_revision + 1
    action = "opened" if next_state == "open" and current_state in {"resolved", "superseded"} else "updated"
    updated = conn.execute(
        """UPDATE web_ops_followups
           SET account_id=?, required_role=?, severity=?, state=?, source_revision=?, revision=?, updated_at=?,
               acknowledged_at=CASE WHEN ?='open' THEN NULL ELSE acknowledged_at END,
               resolved_at=CASE WHEN ?='open' THEN NULL ELSE resolved_at END
           WHERE id=? AND revision=?""",
        (account_id, required_role, severity, next_state, max(source_revision, current_source_revision), next_revision,
         now, next_state, next_state, followup_id, current_revision),
    )
    if int(updated.rowcount or 0) != 1:
        return "noop", False
    _event(conn, followup_id=followup_id, actor_account_id=None, action=action, state=next_state, revision=next_revision, now=now)
    return action, True


def _supersede_non_actionable_complaints(
    conn: Any, *, now: str, action_budget: int, actions_used: int,
) -> tuple[int, bool]:
    """Close stale/non-actionable complaint metadata without touching Support.

    A follow-up is only actionable while its source case and its triage agree
    on the exact revision that created it.  This keeps an old queue item from
    handing staff into a ticket whose state, role or SLA disposition changed
    after the scheduler's prior pass.  The transition is local metadata only:
    it does not edit the Support case, triage, customer message or assignment.
    """
    if action_budget <= actions_used:
        return 0, True
    remaining = max(0, action_budget - actions_used)
    rows = conn.execute(
        """SELECT followup.id, followup.revision
           FROM web_ops_followups AS followup
           LEFT JOIN web_support_cases AS support_case ON support_case.id=followup.source_id
           LEFT JOIN web_support_triage AS triage ON triage.case_id=followup.source_id
           WHERE followup.source_kind='support_triage'
             AND followup.state IN ('open', 'acknowledged')
             AND (
                 support_case.id IS NULL
                 OR triage.case_id IS NULL
                 OR support_case.state IN ('resolved', 'closed')
                 OR support_case.revision<>followup.source_revision
                 OR triage.source_revision<>followup.source_revision
                 OR (triage.disposition<>'awaiting_operator' AND triage.sla_status NOT IN ('at_risk', 'breached', 'unverified'))
                 OR followup.required_role<>CASE WHEN triage.required_role='support_manager' THEN 'manager' ELSE 'operator' END
             )
           ORDER BY followup.updated_at ASC, followup.id ASC LIMIT ?""",
        (remaining + 1,),
    ).fetchall()
    changed = 0
    for row in rows[:remaining]:
        followup_id = str(row[0])
        revision = int(row[1]) + 1
        updated = conn.execute(
            """UPDATE web_ops_followups
               SET state='superseded', revision=?, updated_at=?, resolved_at=?
               WHERE id=? AND revision=? AND state IN ('open', 'acknowledged')""",
            (revision, now, now, followup_id, int(row[1])),
        )
        if int(updated.rowcount or 0) != 1:
            continue
        _event(conn, followup_id=followup_id, actor_account_id=None, action="superseded", state="superseded", revision=revision, now=now)
        changed += 1
    capped = len(rows) > remaining
    return changed, capped


def _prune_runtime_buckets(conn: Any, *, now: str) -> int:
    """Bound retention of bucket rows after totals have preserved continuity."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RUNTIME_SIGNAL_RETENTION_DAYS)).replace(microsecond=0).isoformat(timespec="seconds")
    rows = conn.execute(
        """SELECT id FROM web_ops_runtime_signal_buckets
           WHERE last_seen_at<? ORDER BY last_seen_at ASC, id ASC LIMIT ?""",
        (cutoff, MAX_RUNTIME_BUCKET_PRUNES_PER_RUN),
    ).fetchall()
    if not rows:
        return 0
    conn.executemany(
        "DELETE FROM web_ops_runtime_signal_buckets WHERE id=?",
        [(str(row[0]),) for row in rows],
    )
    return len(rows)


def reconcile_followups(
    *,
    run_id: str,
    deadline: datetime,
    action_budget: int,
    secret: str,
    lease_current: Callable[[Any], bool],
) -> dict[str, Any]:
    """Materialize bounded local follow-ups under the caller's live fence.

    The Operations scheduler owns HMAC/replay/lease control.  This module
    receives only its current run identity and a lease predicate; it cannot
    start a job, contact anyone, retry a provider or repair application code.
    """
    if not reliability_followup_enabled():
        return {"runtime_followup_count": 0, "complaint_followup_count": 0, "superseded_count": 0, "capped": False, "code": ""}
    threshold = _threshold()
    if threshold is None or not secret:
        return {"runtime_followup_count": 0, "complaint_followup_count": 0, "superseded_count": 0, "capped": False, "code": "OPS_RELIABILITY_THRESHOLD_UNVERIFIED"}
    if action_budget <= 0 or datetime.now(timezone.utc) >= deadline:
        return {"runtime_followup_count": 0, "complaint_followup_count": 0, "superseded_count": 0, "capped": True, "code": "OPS_ACTION_BUDGET_REACHED"}

    runtime_count = 0
    complaint_count = 0
    superseded_count = 0
    actions = 0
    capped = False
    with transaction() as conn:
        if not lease_current(conn):
            raise ReliabilityLeaseLost()
        now = utc_now()
        _prune_runtime_buckets(conn, now=now)
        runtime_rows = conn.execute(
            """SELECT route_family, signal_code, occurrence_count, revision
               FROM web_ops_runtime_signal_totals
               WHERE occurrence_count>=?
               ORDER BY last_seen_at ASC, route_family ASC LIMIT ?""",
            (threshold, MAX_SIGNAL_BUCKETS_PER_RUN),
        ).fetchall()
        for row in runtime_rows:
            if datetime.now(timezone.utc) >= deadline or actions >= action_budget:
                capped = True
                break
            if not lease_current(conn):
                raise ReliabilityLeaseLost()
            route_family, _signal_code, count, revision = (str(row[0]), str(row[1]), int(row[2]), int(row[3]))
            _outcome, changed = _upsert_followup(
                conn, run_id=run_id, source_kind="runtime_signal", source_id=route_family, account_id=None,
                required_role="operator", severity=_runtime_severity(count=count, threshold=threshold),
                source_revision=revision, secret=secret, now=now,
            )
            if changed:
                runtime_count += 1
                actions += 1

        complaint_rows: list[Any] = []
        if not capped and actions < action_budget:
            complaint_rows = conn.execute(
                """SELECT triage.case_id, triage.account_id, triage.source_revision, triage.risk,
                          triage.disposition, triage.required_role, triage.sla_status
                   FROM web_support_triage AS triage
                   JOIN web_support_cases AS support_case ON support_case.id=triage.case_id
                   WHERE support_case.state NOT IN ('resolved', 'closed')
                     AND triage.source_revision=support_case.revision
                     AND (triage.disposition='awaiting_operator' OR triage.sla_status IN ('at_risk', 'breached', 'unverified'))
                   ORDER BY CASE triage.sla_status
                       WHEN 'breached' THEN 0 WHEN 'at_risk' THEN 1 WHEN 'unverified' THEN 2 ELSE 3 END,
                            triage.updated_at ASC, triage.case_id ASC LIMIT ?""",
                (MAX_COMPLAINTS_PER_RUN,),
            ).fetchall()
            for row in complaint_rows:
                if datetime.now(timezone.utc) >= deadline or actions >= action_budget:
                    capped = True
                    break
                if not lease_current(conn):
                    raise ReliabilityLeaseLost()
                case_id, _account_id, source_revision, risk, _disposition, required_role, sla_status = (
                    str(row[0]), str(row[1]), int(row[2]), str(row[3]), str(row[4]), str(row[5]), str(row[6]),
                )
                role = "manager" if required_role == "support_manager" else "operator"
                _outcome, changed = _upsert_followup(
                    # The follow-up needs only an opaque private case reference
                    # for terminal-state convergence. It does not retain the
                    # customer's Web account identity.
                    conn, run_id=run_id, source_kind="support_triage", source_id=case_id, account_id=None,
                    required_role=role, severity=_complaint_severity(sla_status=sla_status, risk=risk),
                    source_revision=source_revision, secret=secret, now=now,
                )
                if changed:
                    complaint_count += 1
                    actions += 1

        if not capped and actions < action_budget:
            if not lease_current(conn):
                raise ReliabilityLeaseLost()
            superseded_count, non_actionable_capped = _supersede_non_actionable_complaints(
                conn, now=now, action_budget=action_budget, actions_used=actions,
            )
            actions += superseded_count
            capped = capped or non_actionable_capped
    return {
        "runtime_followup_count": runtime_count,
        "complaint_followup_count": complaint_count,
        "superseded_count": superseded_count,
        "capped": capped,
        "code": "OPS_ACTION_BUDGET_REACHED" if capped else "",
    }


def _signal_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "route_family": str(row[0]),
        "signal_code": str(row[1]),
        "count": int(row[2]),
        "revision": int(row[3]),
        "first_seen_at": str(row[4]),
        "last_seen_at": str(row[5]),
    }


def _followup_public(row: tuple[Any, ...]) -> dict[str, Any]:
    source_kind = str(row[1])
    return {
        "id": str(row[0]),
        "source_kind": source_kind,
        # Do not return the source reference even to staff list views. A
        # support case UUID or route label is useful for scheduler dedupe but
        # not required to acknowledge/resolve this queue, and keeping it
        # server-only prevents the queue from becoming a correlation surface.
        "required_role": str(row[4]),
        "severity": str(row[5]),
        "state": str(row[6]),
        "source_revision": int(row[7]),
        "occurrence_count": int(row[7]) if source_kind == "runtime_signal" else 1,
        "revision": int(row[8]),
        "opened_at": str(row[9]),
        "updated_at": str(row[10]),
        "acknowledged_at": str(row[11]) if row[11] else None,
        "resolved_at": str(row[12]) if row[12] else None,
        "execution": "staff_followup_metadata_only",
    }


def _idempotent(
    *, account_id: str, scope: str, key: str, request_fingerprint: str, operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[1] or ""), request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu Reliability khác")
            try:
                stored = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Reliability không hợp lệ") from exc
            if not isinstance(stored, dict):
                raise HTTPException(status_code=409, detail="Receipt Reliability không hợp lệ")
            return stored
        response = operation(conn)
        conn.execute(
            """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
        )
    return response


class FollowupMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    confirm: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


@router.get("/api/v1/operations/admin/reliability/summary")
async def summary(account: dict = Depends(require_account)):
    _require_reliability()
    role = require_support_staff(account)
    visibility, _ = _followup_visibility_clause(role)
    ensure_copyfast_schema()
    with read_transaction() as conn:
        state_rows = conn.execute(
            f"SELECT state, COUNT(*) FROM web_ops_followups WHERE {visibility} GROUP BY state"
        ).fetchall()
        signal = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(occurrence_count), 0), MAX(last_seen_at) FROM web_ops_runtime_signal_totals"
        ).fetchone()
        signal_rows = conn.execute(
            """SELECT route_family, signal_code, count, revision, first_seen_at, last_seen_at
               FROM web_ops_runtime_signal_buckets ORDER BY last_seen_at DESC, id DESC LIMIT 12"""
        ).fetchall()
    counts = {state: 0 for state in FOLLOWUP_STATES}
    for row in state_rows:
        if str(row[0]) in counts:
            counts[str(row[0])] = int(row[1])
    return envelope(
        True,
        "Tổng quan Reliability Follow-up chỉ gồm metadata Web đã được sanitize.",
        data=_boundary(
            operator_role=role,
            counts=counts,
            signal_groups=int(signal[0] or 0) if signal else 0,
            signal_occurrences=int(signal[1] or 0) if signal else 0,
            last_signal_at=str(signal[2]) if signal and signal[2] else None,
            recent_signals=[_signal_public(tuple(row)) for row in signal_rows],
            reliability_preflight=reliability_preflight_code() or "ready",
        ),
        status_name="read_only",
    )


@router.get("/api/v1/operations/admin/followups")
async def list_followups(
    state: str = "all", severity: str = "all", limit: int = 50, offset: int = 0, account: dict = Depends(require_account),
):
    _require_reliability()
    staff_role = require_support_staff(account)
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset Reliability Follow-up không hợp lệ")
    state_filter = str(state or "all").strip().lower()
    severity_filter = str(severity or "all").strip().lower()
    if state_filter not in {*FOLLOWUP_STATES, "all"} or severity_filter not in {*FOLLOWUP_SEVERITIES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc Reliability Follow-up không hợp lệ")
    visibility, _ = _followup_visibility_clause(staff_role)
    clauses: list[str] = [visibility]
    params: list[Any] = []
    if state_filter != "all":
        clauses.append("state=?")
        params.append(state_filter)
    if severity_filter != "all":
        clauses.append("severity=?")
        params.append(severity_filter)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, source_kind, source_id, account_id, required_role, severity, state,
                       source_revision, revision, opened_at, updated_at, acknowledged_at, resolved_at
                FROM web_ops_followups {where}
                ORDER BY CASE state WHEN 'open' THEN 0 WHEN 'acknowledged' THEN 1 WHEN 'resolved' THEN 2 ELSE 3 END,
                         CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                         updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Hàng chờ Reliability chỉ dành cho Support staff đã được server xác minh.",
        data=_boundary(
            items=[_followup_public(tuple(row)) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


def _can_change(*, staff_role: str, required_role: str) -> bool:
    # Unknown persisted values must fail closed. Only a canonical Manager may
    # override a Manager-required record; an Operator may mutate records that
    # explicitly require the Operator role.
    return required_role in {"operator", "manager"} and (staff_role == "manager" or required_role == "operator")


def _followup_visibility_clause(staff_role: str, *, table_alias: str | None = None) -> tuple[str, tuple[Any, ...]]:
    """Return a server-owned, fail-closed predicate for Reliability reads.

    The UI never receives a role filter it can influence.  An Operator can
    only read records explicitly assigned to the Operator role; a Manager can
    read canonical assigned records.  Unknown persisted roles stay hidden so a
    malformed row cannot become visible merely because a caller is staff.
    """

    column = f"{table_alias}.required_role" if table_alias else "required_role"
    if staff_role == "manager":
        return f"{column} IN ('operator', 'manager')", ()
    if staff_role == "operator":
        return f"{column}='operator'", ()
    return "1=0", ()


@router.get("/api/v1/operations/admin/followups/{followup_id}/handoff")
async def support_handoff(followup_id: str, request: Request, account: dict = Depends(require_account)):
    """Resolve one fresh triage follow-up into a protected Support Desk route.

    The Reliability queue deliberately hides source references in its list.
    This read-only handoff performs that lookup only after the signed staff
    role and source freshness checks pass.  It returns a tightly constrained
    local route, never source content, customer identity, messages or a
    generic redirect supplied by the browser.
    """
    _require_reliability()
    staff_role = require_support_staff(account)
    followup_id = _uuid(followup_id, label="Mã Reliability Follow-up")
    visibility, _ = _followup_visibility_clause(staff_role, table_alias="followup")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            f"""SELECT followup.required_role, followup.source_revision,
                      support_case.id, support_case.revision, support_case.state,
                      triage.source_revision, triage.disposition, triage.required_role, triage.sla_status
               FROM web_ops_followups AS followup
               JOIN web_support_cases AS support_case ON support_case.id=followup.source_id
               JOIN web_support_triage AS triage ON triage.case_id=support_case.id
               WHERE followup.id=?
                 AND followup.source_kind='support_triage'
                 AND followup.state IN ('open', 'acknowledged')
                 AND {visibility}""",
            (followup_id,),
        ).fetchone()
        if not row:
            return envelope(
                False,
                "Không tìm thấy Reliability Follow-up đang có quyền truy cập.",
                data=_boundary(),
                status_name="guarded",
                error_code="OPS_RELIABILITY_FOLLOWUP_NOT_FOUND",
            )
        current = tuple(row)
        required_role = str(current[0])
        if not _can_change(staff_role=staff_role, required_role=required_role):
            return envelope(
                False,
                "Follow-up này cần Support Manager mở Support Desk.",
                data=_boundary(),
                status_name="guarded",
                error_code="OPS_RELIABILITY_FOLLOWUP_ROLE_REQUIRED",
            )
        case_id = str(current[2])
        source_revision = int(current[1])
        case_revision = int(current[3])
        case_state = str(current[4])
        triage_revision = int(current[5])
        disposition = str(current[6])
        triage_required_role = str(current[7])
        sla_status = str(current[8])
        mapped_role = "manager" if triage_required_role == "support_manager" else "operator"
        actionable = _triage_is_actionable(disposition=disposition, sla_status=sla_status)
        fresh = (
            source_revision == case_revision == triage_revision
            and case_state not in {"resolved", "closed"}
            and required_role == mapped_role
            and actionable
        )
        if not fresh:
            return envelope(
                False,
                "Follow-up đã có nguồn Support mới hơn hoặc không còn cần xử lý. Hãy làm mới hàng chờ.",
                data=_boundary(),
                status_name="guarded",
                error_code="OPS_RELIABILITY_HANDOFF_SOURCE_STALE",
            )
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.operations.reliability_followup.handoff_read",
            request_id=_request_id(request),
            target=followup_id,
            detail="staff opened a fresh protected Support Desk handoff from local Reliability metadata; no source content copied, case mutated, customer contact or external action",
        )
    return envelope(
        True,
        "Đã xác minh follow-up hiện tại. Bạn có thể mở yêu cầu Support Desk được bảo vệ.",
        data=_boundary(
            handoff={
                "execution": "protected_support_case_navigation_only",
                "target_route": f"/admin/support/{case_id}",
                "source_content_copied": False,
                "support_case_mutated": False,
            },
        ),
        status_name="read_only",
    )


def _mutate_followup(
    *, followup_id: str, payload: FollowupMutationRequest, request: Request, account: dict, action: str,
) -> dict[str, Any]:
    _require_reliability()
    staff_role = require_support_staff(account)
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi đổi trạng thái Reliability Follow-up")
    followup_id = _uuid(followup_id, label="Mã Reliability Follow-up")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _json_hash({"followup_id": followup_id, "expected_revision": payload.expected_revision, "action": action})
    scope = f"web-reliability:{account['id']}:followup:{followup_id}:{action}"
    visibility, _ = _followup_visibility_clause(staff_role)

    def operation(conn: Any) -> dict[str, Any]:
        row = conn.execute(
            f"""SELECT id, source_kind, source_id, account_id, required_role, severity, state,
                      source_revision, revision, opened_at, updated_at, acknowledged_at, resolved_at
               FROM web_ops_followups WHERE id=? AND {visibility}""",
            (followup_id,),
        ).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy Reliability Follow-up.", data=_boundary(), status_name="guarded", error_code="OPS_RELIABILITY_FOLLOWUP_NOT_FOUND")
        current = tuple(row)
        if not _can_change(staff_role=staff_role, required_role=str(current[4])):
            return envelope(False, "Follow-up này cần Support Manager xác nhận.", data=_boundary(followup=_followup_public(current)), status_name="guarded", error_code="OPS_RELIABILITY_FOLLOWUP_ROLE_REQUIRED")
        if int(current[8]) != payload.expected_revision:
            return envelope(False, "Reliability Follow-up đã có revision mới. Hãy tải lại trước khi tiếp tục.", data=_boundary(followup=_followup_public(current)), status_name="guarded", error_code="OPS_RELIABILITY_FOLLOWUP_CONFLICT")
        state = str(current[6])
        permitted = {
            "acknowledge": ({"open"}, "acknowledged"),
            "resolve": ({"open", "acknowledged"}, "resolved"),
            "reopen": ({"resolved"}, "open"),
        }
        allowed, next_state = permitted[action]
        if state == next_state:
            return envelope(True, "Reliability Follow-up đã ở trạng thái yêu cầu.", data=_boundary(followup=_followup_public(current)), status_name="completed")
        if state not in allowed:
            return envelope(False, "Chuyển trạng thái Reliability Follow-up không hợp lệ.", data=_boundary(followup=_followup_public(current)), status_name="guarded", error_code="OPS_RELIABILITY_FOLLOWUP_STATE_INVALID")
        now = utc_now()
        next_revision = int(current[8]) + 1
        acknowledged_at = now if action == "acknowledge" else (None if action == "reopen" else current[11])
        resolved_at = now if action == "resolve" else None if action == "reopen" else current[12]
        updated = conn.execute(
            """UPDATE web_ops_followups
               SET state=?, revision=?, updated_at=?, acknowledged_at=?, resolved_at=?
               WHERE id=? AND revision=?""",
            (next_state, next_revision, now, acknowledged_at, resolved_at, followup_id, payload.expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            refreshed = conn.execute(
                f"""SELECT id, source_kind, source_id, account_id, required_role, severity, state,
                          source_revision, revision, opened_at, updated_at, acknowledged_at, resolved_at
                   FROM web_ops_followups WHERE id=? AND {visibility}""",
                (followup_id,),
            ).fetchone()
            return envelope(False, "Reliability Follow-up đã thay đổi đồng thời. Hãy tải lại trước khi tiếp tục.", data=_boundary(followup=_followup_public(tuple(refreshed)) if refreshed else None), status_name="guarded", error_code="OPS_RELIABILITY_FOLLOWUP_CONFLICT")
        _event(conn, followup_id=followup_id, actor_account_id=str(account["id"]), action=action, state=next_state, revision=next_revision, now=now)
        _record_audit(
            conn, account_id=str(account["id"]), canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action=f"web.operations.reliability_followup.{action}", request_id=_request_id(request), target=followup_id,
            detail="staff changed local reliability follow-up metadata only; no repair, deployment, money, provider, Bot or customer contact",
        )
        refreshed = conn.execute(
            f"""SELECT id, source_kind, source_id, account_id, required_role, severity, state,
                      source_revision, revision, opened_at, updated_at, acknowledged_at, resolved_at
               FROM web_ops_followups WHERE id=? AND {visibility}""",
            (followup_id,),
        ).fetchone()
        return envelope(True, "Đã cập nhật hàng chờ Reliability nội bộ. Không có sửa hệ thống hoặc hành động ngoài Web.", data=_boundary(followup=_followup_public(tuple(refreshed))), status_name="completed")

    return _idempotent(account_id=str(account["id"]), scope=scope, key=key, request_fingerprint=fingerprint, operation=operation)


@router.post("/api/v1/operations/admin/followups/{followup_id}/acknowledge")
async def acknowledge(followup_id: str, payload: FollowupMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    return _mutate_followup(followup_id=followup_id, payload=payload, request=request, account=account, action="acknowledge")


@router.post("/api/v1/operations/admin/followups/{followup_id}/resolve")
async def resolve(followup_id: str, payload: FollowupMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    return _mutate_followup(followup_id=followup_id, payload=payload, request=request, account=account, action="resolve")


@router.post("/api/v1/operations/admin/followups/{followup_id}/reopen")
async def reopen(followup_id: str, payload: FollowupMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    return _mutate_followup(followup_id=followup_id, payload=payload, request=request, account=account, action="reopen")
