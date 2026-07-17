"""Controlled Operations Autopilot for the standalone Web App.

The module provides a narrowly scoped, authenticated scheduler endpoint and
owner/staff read models for Web-native support operations.  It intentionally
does not invoke external delivery systems, alter account money, run customer
work, alter deployment state or modify application code.  Its only automatic
writes are bounded local observations, deterministic complaint triage,
incident deduplication and approval *records* that still require a human.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from typing import Any, Callable
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_autopilot_policy import (
    complaint_triage,
    incident_fingerprint,
    may_auto_close_incident,
    safe_playbook_allowed,
)
from copyfast_autopilot_protocol import (
    NONCE_PATTERN,
    PROTOCOL_VERSION,
    TICK_PATH,
    canonical_json,
    sign_tick,
    valid_request_id,
)
import copyfast_reliability
from copyfast_db import (
    autopilot_enabled,
    autopilot_heartbeat_followup_enabled,
    autopilot_safe_remediation_enabled,
    ensure_copyfast_schema,
    is_production_like_environment,
    operations_autopilot_persistence_ready,
    read_transaction,
    transaction,
    utc_now,
)
from copyfast_support import require_support_staff


router = APIRouter(tags=["Operations Autopilot"])

POLICY_VERSION = 1
TICK_MAX_BODY_BYTES = 8 * 1024
TICK_MAX_CLOCK_SKEW_SECONDS = 300
TICK_NONCE_TTL_SECONDS = 600
TICK_LEASE_NAME = "operations_autopilot_tick"
MAX_TICK_SECONDS = 25
MAX_ACTIONS_PER_RUN = 20
MAX_CASES_PER_TICK = 100
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
INCIDENT_RECOVERY_PLAYBOOK = "incident_recovery_reconciliation"
INCIDENT_RECOVERY_STREAK_ENV = "WEBAPP_AUTOPILOT_INCIDENT_RECOVERY_STREAK"
INCIDENT_RECOVERY_DEFAULT_STREAK = 3
INCIDENT_RECOVERY_MAX_STREAK = 10
HEARTBEAT_FOLLOWUP_PLAYBOOK = "scheduler_heartbeat_followup"
HEARTBEAT_INCIDENT_KIND = "scheduler_heartbeat_late"
HEARTBEAT_SCOPE_KIND = "scheduler"
HEARTBEAT_BASELINE_SCOPE = "railway_cron"
# A Web-process restart intentionally re-arms the persisted heartbeat rather
# than comparing the first tick after a deploy to a stale pre-deploy receipt.
HEARTBEAT_PROCESS_EPOCH = str(uuid.uuid4())
HEARTBEAT_EXPECTED_SECONDS_ENV = "WEBAPP_AUTOPILOT_HEARTBEAT_EXPECTED_SECONDS"
HEARTBEAT_GRACE_SECONDS_ENV = "WEBAPP_AUTOPILOT_HEARTBEAT_GRACE_SECONDS"
HEARTBEAT_MIN_EXPECTED_SECONDS = 300
HEARTBEAT_MAX_EXPECTED_SECONDS = 86_400
HEARTBEAT_DEFAULT_GRACE_SECONDS = 120
HEARTBEAT_MAX_GRACE_SECONDS = 3_600
AUTOPILOT_TOPOLOGY_SQLITE_SINGLE_REPLICA = "sqlite_single_replica"
REPLICA_COUNT_ENV_NAMES = ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
KEY_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
SIGNATURE_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
DECISION_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,80}$")

APPROVAL_ACTION_BY_CATEGORY = {
    "payment_topup": "payment_finalize",
    "refund": "payment_refund",
    "package_combo": "wallet_adjustment",
    "image_error": "provider_retry",
    "video_error": "provider_retry",
    "document_pdf": "provider_retry",
}
APPROVAL_DECISION_CODES = {
    "approved": "manager_approved",
    "rejected": "manager_rejected",
}


class _TickGuarded(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _TickLeaseLost(RuntimeError):
    """Raised before a stale scheduler can write after its lease changed."""


def _boundary(**extra: Any) -> dict[str, Any]:
    """State the exact automation boundary on every Operations response."""
    preflight_code = _scheduler_preflight_code() if autopilot_enabled() else "OPS_AUTOPILOT_DISABLED"
    heartbeat_enabled = autopilot_heartbeat_followup_enabled()
    heartbeat_limits = _heartbeat_limits() if heartbeat_enabled else None
    return {
        "execution": "controlled_web_operations_only",
        "data_origin": "signed_web_records_and_authenticated_scheduler_only",
        "policy_version": POLICY_VERSION,
        "autopilot_enabled": autopilot_enabled(),
        "safe_remediation_enabled": autopilot_safe_remediation_enabled(),
        "reliability_followup_enabled": copyfast_reliability.reliability_followup_enabled(),
        "heartbeat_followup_enabled": heartbeat_enabled,
        "heartbeat_followup_configured": bool(heartbeat_limits),
        "scheduler_topology": os.environ.get("WEBAPP_AUTOPILOT_TOPOLOGY", "").strip() or "unverified",
        "scheduler_ready": preflight_code is None,
        "bot_called": False,
        "provider_called": False,
        "wallet_mutated": False,
        "payment_mutated": False,
        "payment_processed": False,
        "customer_reply_sent": False,
        "external_notification_sent": False,
        "job_retried": False,
        "asset_delivery_changed": False,
        "role_changed": False,
        "secret_changed": False,
        "deployment_changed": False,
        "self_modifying_code": False,
        "dangerous_action_executed": False,
        **extra,
    }


def _require_enabled() -> None:
    if not autopilot_enabled():
        raise HTTPException(
            status_code=503,
            detail="Operations Autopilot đang ở chế độ tắt an toàn. WEBAPP_AUTOPILOT_ENABLED chưa được bật.",
        )


def _configured_int(name: str, *, default: int, minimum: int, maximum: int) -> int | None:
    """Parse a bounded scheduler value without raising on a Cron request."""
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < minimum or value > maximum:
        return None
    return value


def _scheduler_limits() -> tuple[int, int] | None:
    run_seconds = _configured_int(
        "WEBAPP_AUTOPILOT_MAX_RUN_SECONDS", default=20, minimum=1, maximum=MAX_TICK_SECONDS,
    )
    max_actions = _configured_int(
        "WEBAPP_AUTOPILOT_MAX_ACTIONS_PER_RUN", default=20, minimum=1, maximum=MAX_ACTIONS_PER_RUN,
    )
    if run_seconds is None or max_actions is None:
        return None
    return run_seconds, max_actions


def _incident_recovery_required_streak() -> int | None:
    """Read a deliberately small, fail-closed healthy-tick threshold.

    One observation can be a transient clock/data race, so recovery never
    accepts a one-tick close.  This is a Web-only scheduler configuration; it
    is not a browser option and it never grants an external capability.
    """
    return _configured_int(
        INCIDENT_RECOVERY_STREAK_ENV,
        default=INCIDENT_RECOVERY_DEFAULT_STREAK,
        minimum=2,
        maximum=INCIDENT_RECOVERY_MAX_STREAK,
    )


def _heartbeat_limits() -> tuple[int, int] | None:
    """Read an explicitly configured, bounded Cron heartbeat window.

    A missing expected interval is never guessed from Railway scheduling.  The
    follow-up is optional and defaults off; once enabled it requires an exact
    local expectation so it cannot manufacture a missed-Cron incident from a
    deployment delay, an unknown schedule or browser-provided input.
    """
    if not autopilot_heartbeat_followup_enabled():
        return None
    expected = _configured_int(
        HEARTBEAT_EXPECTED_SECONDS_ENV,
        default=0,
        minimum=HEARTBEAT_MIN_EXPECTED_SECONDS,
        maximum=HEARTBEAT_MAX_EXPECTED_SECONDS,
    )
    grace = _configured_int(
        HEARTBEAT_GRACE_SECONDS_ENV,
        default=HEARTBEAT_DEFAULT_GRACE_SECONDS,
        minimum=0,
        maximum=HEARTBEAT_MAX_GRACE_SECONDS,
    )
    if expected is None or grace is None:
        return None
    return expected, grace


def _heartbeat_config_fingerprint() -> str | None:
    """Return a non-secret identity for one explicit heartbeat policy."""
    limits = _heartbeat_limits()
    if limits is None:
        return None
    expected_seconds, grace_seconds = limits
    return hashlib.sha256(
        canonical_json({
            "playbook": HEARTBEAT_FOLLOWUP_PLAYBOOK,
            "policy_version": POLICY_VERSION,
            "expected_seconds": expected_seconds,
            "grace_seconds": grace_seconds,
        })
    ).hexdigest()


def _heartbeat_preflight_code() -> str | None:
    """Fail closed only when the separately enabled heartbeat is malformed."""
    if not autopilot_safe_remediation_enabled() or not autopilot_heartbeat_followup_enabled():
        return None
    return None if _heartbeat_limits() is not None else "OPS_HEARTBEAT_CONFIG_UNVERIFIED"


def _tick_secret() -> str:
    value = os.environ.get("WEBAPP_AUTOPILOT_TICK_SECRET", "")
    if len(value.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="Operations Autopilot chưa có scheduler secret hợp lệ.")
    return value


def _incident_secret() -> str:
    value = os.environ.get("WEBAPP_AUTOPILOT_INCIDENT_SECRET", "")
    if len(value.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="Operations Autopilot chưa có incident secret hợp lệ.")
    return value


def _tick_key_id() -> str:
    value = os.environ.get("WEBAPP_AUTOPILOT_TICK_KEY_ID", "primary").strip().lower()
    if not KEY_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=503, detail="Cấu hình Operations Autopilot chưa hợp lệ.")
    return value


def _topology_guarded_code() -> str | None:
    """Require an explicit single-replica acknowledgement for SQLite state.

    Nonces and leases live in this application's SQLite database.  They are
    correct only while all Operations requests share that one database, so a
    deployed scheduler must fail closed until the operator attests to the
    one-replica topology.  A future shared transactional store gets a new
    implementation and topology value rather than silently reusing this one.
    """
    topology = os.environ.get("WEBAPP_AUTOPILOT_TOPOLOGY", "").strip().lower()
    if topology != AUTOPILOT_TOPOLOGY_SQLITE_SINGLE_REPLICA:
        return "OPS_TOPOLOGY_UNVERIFIED"
    attested = False
    for name in REPLICA_COUNT_ENV_NAMES:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        attested = True
        try:
            replica_count = int(raw)
        except ValueError:
            return "OPS_REPLICA_COUNT_UNVERIFIED"
        if replica_count != 1:
            return "OPS_MULTI_REPLICA_BLOCKED"
    if is_production_like_environment() and not attested:
        return "OPS_REPLICA_COUNT_UNVERIFIED"
    return None


def _scheduler_preflight_code() -> str | None:
    if not operations_autopilot_persistence_ready():
        return "OPS_PERSISTENT_STORE_UNVERIFIED"
    if _configured_int("WEBAPP_AUTOPILOT_MAX_RUN_SECONDS", default=20, minimum=1, maximum=MAX_TICK_SECONDS) is None:
        return "OPS_MAX_RUN_SECONDS_UNVERIFIED"
    if _configured_int("WEBAPP_AUTOPILOT_MAX_ACTIONS_PER_RUN", default=20, minimum=1, maximum=MAX_ACTIONS_PER_RUN) is None:
        return "OPS_MAX_ACTIONS_UNVERIFIED"
    topology_code = _topology_guarded_code()
    if topology_code:
        return topology_code
    if autopilot_safe_remediation_enabled() and len(os.environ.get("WEBAPP_AUTOPILOT_INCIDENT_SECRET", "").encode("utf-8")) < 32:
        return "OPS_INCIDENT_SECRET_UNAVAILABLE"
    if autopilot_safe_remediation_enabled() and _incident_recovery_required_streak() is None:
        return "OPS_INCIDENT_RECOVERY_STREAK_UNVERIFIED"
    heartbeat_code = _heartbeat_preflight_code()
    if heartbeat_code:
        return heartbeat_code
    # Signal intake can remain observation-only while safe remediation is
    # off. The scheduler needs Reliability's secret/threshold only once it
    # is actually permitted to materialize local follow-up metadata.
    if autopilot_safe_remediation_enabled() and copyfast_reliability.reliability_followup_enabled():
        reliability_code = copyfast_reliability.reliability_preflight_code()
        if reliability_code:
            return reliability_code
    return None


def _as_utc(value: Any) -> datetime:
    raw = str(value or "").strip()
    if not raw or len(raw) > 40:
        raise ValueError("timestamp invalid")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError("timestamp timezone missing")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _time_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")


def _json_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _nonce_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key Operations không hợp lệ")
    return key


def _decision_code(value: Any) -> str:
    code = str(value or "").strip().lower()
    if not DECISION_CODE_PATTERN.fullmatch(code):
        raise HTTPException(status_code=422, detail="Mã lý do phê duyệt không hợp lệ")
    return code


def _safe_public_message(code: str) -> str:
    messages = {
        "OPS_AUTOPILOT_DISABLED": "Operations Autopilot đang tắt an toàn; lần gọi scheduler đã được ghi nhận là guarded và không chạy thao tác nào.",
        "OPS_TICK_REPLAYED": "Lần quét này đã được ghi nhận trước đó; không chạy lại.",
        "OPS_TICK_LEASE_HELD": "Một lần quét Operations khác đang chạy; không tạo thao tác trùng lặp.",
        "OPS_TICK_LEASE_LOST": "Quyền chạy Operations đã đổi; lần quét cũ không được ghi thêm dữ liệu.",
        "OPS_TICK_LEASE_EXPIRED": "Một lượt Operations cũ đã hết lease và được đóng receipt an toàn; không có thao tác bên ngoài nào được thực hiện.",
        "OPS_SAFE_REMEDIATION_DISABLED": "Operations đang quan sát an toàn; remediation cục bộ chưa được bật.",
        "OPS_ACTION_BUDGET_REACHED": "Operations đã chạm giới hạn thao tác an toàn của lần quét này.",
        "OPS_TOPOLOGY_UNVERIFIED": "Operations scheduler đang bị khóa an toàn cho đến khi topology SQLite một replica được xác nhận.",
        "OPS_PERSISTENT_STORE_UNVERIFIED": "Operations scheduler đang bị khóa vì SQLite lease/nonce chưa được xác nhận nằm trên persistent volume.",
        "OPS_MAX_RUN_SECONDS_UNVERIFIED": "Operations scheduler đang bị khóa vì giới hạn thời gian chạy chưa hợp lệ.",
        "OPS_MAX_ACTIONS_UNVERIFIED": "Operations scheduler đang bị khóa vì giới hạn thao tác chưa hợp lệ.",
        "OPS_REPLICA_COUNT_UNVERIFIED": "Operations scheduler đang bị khóa vì cấu hình replica chưa hợp lệ.",
        "OPS_MULTI_REPLICA_BLOCKED": "Operations scheduler không chạy với nhiều replica khi state vẫn ở SQLite.",
        "OPS_INCIDENT_SECRET_UNAVAILABLE": "Operations đang quan sát an toàn; remediation cục bộ chờ cấu hình incident key riêng.",
        "OPS_RELIABILITY_FOLLOWUP_DISABLED": "Reliability Follow-up đang tắt an toàn; scheduler không tạo hàng chờ runtime.",
        "OPS_RELIABILITY_INCIDENT_SECRET_UNAVAILABLE": "Reliability Follow-up đang bị khóa vì chưa có incident key Web-only hợp lệ.",
        "OPS_RELIABILITY_THRESHOLD_UNVERIFIED": "Reliability Follow-up đang bị khóa vì ngưỡng signal chưa hợp lệ.",
        "OPS_HEARTBEAT_CONFIG_UNVERIFIED": "Heartbeat Operations đang bị khóa vì khoảng Cron kỳ vọng chưa được cấu hình hợp lệ.",
        "OPS_HEARTBEAT_HISTORY_INVALID": "Heartbeat Operations đang giữ trạng thái bảo vệ vì lịch sử tick không hợp lệ.",
    }
    return messages.get(code, "Operations Autopilot đã giữ trạng thái bảo vệ an toàn.")


def _require_json_header(request: Request) -> None:
    values = request.headers.getlist("content-type")
    if len(values) != 1 or values[0].split(";", 1)[0].strip().lower() != "application/json":
        raise HTTPException(status_code=415, detail="Yêu cầu Operations nội bộ phải dùng JSON hợp lệ")


def _single_header(request: Request, name: str) -> str:
    values = request.headers.getlist(name)
    if len(values) != 1:
        raise HTTPException(status_code=401, detail="Xác thực Operations nội bộ không hợp lệ")
    value = values[0].strip()
    if not value:
        raise HTTPException(status_code=401, detail="Xác thực Operations nội bộ không hợp lệ")
    return value


def _tick_headers(request: Request, body: bytes) -> tuple[str, str, str, str, datetime]:
    _require_json_header(request)
    timestamp = _single_header(request, "x-ops-timestamp")
    nonce = _single_header(request, "x-ops-nonce")
    request_id = _single_header(request, "x-ops-request-id")
    signature = _single_header(request, "x-ops-signature").lower()
    key_id = _single_header(request, "x-ops-key-id").lower()
    if key_id != _tick_key_id() or not NONCE_PATTERN.fullmatch(nonce) or not valid_request_id(request_id) or not SIGNATURE_PATTERN.fullmatch(signature):
        raise HTTPException(status_code=401, detail="Xác thực Operations nội bộ không hợp lệ")
    try:
        timestamp_value = _as_utc(timestamp)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Xác thực Operations nội bộ không hợp lệ") from None
    if abs((datetime.now(timezone.utc) - timestamp_value).total_seconds()) > TICK_MAX_CLOCK_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="Xác thực Operations nội bộ không hợp lệ")
    expected = sign_tick(
        secret=_tick_secret(), timestamp=timestamp, nonce=nonce, request_id=request_id, key_id=key_id, body=body,
    )
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Xác thực Operations nội bộ không hợp lệ")
    return timestamp, nonce, request_id, key_id, timestamp_value


def _tick_payload(body: bytes, *, timestamp: str) -> dict[str, Any]:
    if not body or len(body) > TICK_MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Dữ liệu Operations nội bộ vượt giới hạn an toàn")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="Dữ liệu Operations nội bộ không hợp lệ") from None
    if (
        not isinstance(parsed, dict)
        or set(parsed) != {"protocol_version", "trigger", "requested_at"}
        or parsed.get("protocol_version") != PROTOCOL_VERSION
        or parsed.get("trigger") != "railway_cron"
        or parsed.get("requested_at") != timestamp
        or canonical_json(parsed) != body
    ):
        raise HTTPException(status_code=422, detail="Dữ liệu Operations nội bộ không hợp lệ")
    return parsed


def _lease_current(conn: Any, *, run_id: str, fence_token: int, now: str) -> bool:
    row = conn.execute(
        "SELECT owner_run_id, fence_token, expires_at FROM web_ops_leases WHERE name=?",
        (TICK_LEASE_NAME,),
    ).fetchone()
    return bool(row and str(row[0]) == run_id and int(row[1]) == fence_token and str(row[2]) > now)


def _guard_expired_lease_run(conn: Any, *, owner_run_id: Any, fence_token: Any, now: str) -> bool:
    """Close exactly one abandoned run before its expired lease is replaced.

    A process can crash after creating a ``started`` run. The next signed tick
    fences that old receipt before taking over, so the Web-only Operations
    timeline never claims that it is still executing forever. This changes no
    Support Desk row, provider/Bot/job, payment/wallet, deployment or message.
    """
    try:
        token = int(fence_token)
    except (TypeError, ValueError):
        return False
    run_id = str(owner_run_id or "").strip()
    if not run_id or token < 1:
        return False
    row = conn.execute(
        "SELECT request_id FROM web_ops_runs WHERE id=? AND fence_token=? AND state='started'",
        (run_id, token),
    ).fetchone()
    if not row:
        return False
    receipt = {"request_id": str(row[0] or ""), "guarded_code": "OPS_TICK_LEASE_EXPIRED"}
    updated = conn.execute(
        """UPDATE web_ops_runs SET state='guarded', finished_at=?, error_code=?, receipt_json=?
           WHERE id=? AND fence_token=? AND state='started'""",
        (
            now,
            "OPS_TICK_LEASE_EXPIRED",
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            run_id,
            token,
        ),
    )
    return int(updated.rowcount or 0) == 1


def _start_run(
    *, request_id: str, key_id: str, nonce: str, timestamp: datetime, body: bytes, deadline_seconds: int,
) -> tuple[str, int, datetime, str | None]:
    """Consume a verified nonce and acquire the short exclusive scheduler lease."""
    ensure_copyfast_schema()
    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
    now = _time_text(now_dt)
    deadline = now_dt + timedelta(seconds=deadline_seconds)
    lease_expiry = now_dt + timedelta(seconds=max(60, deadline_seconds + 30))
    run_id = str(uuid.uuid4())
    input_hash = hashlib.sha256(body).hexdigest()
    nonce_hash = _nonce_hash(nonce)
    try:
        with transaction() as conn:
            conn.execute("DELETE FROM web_ops_nonces WHERE expires_at<?", (now,))
            previous = conn.execute("SELECT id FROM web_ops_runs WHERE request_id=?", (request_id,)).fetchone()
            if previous:
                raise _TickGuarded("OPS_TICK_REPLAYED")
            try:
                conn.execute(
                    """INSERT INTO web_ops_nonces (nonce_hash, request_id, key_id, created_at, expires_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (nonce_hash, request_id, key_id, now, _time_text(now_dt + timedelta(seconds=TICK_NONCE_TTL_SECONDS))),
                )
            except sqlite3.IntegrityError as exc:
                raise _TickGuarded("OPS_TICK_REPLAYED") from exc
            current = conn.execute(
                "SELECT owner_run_id, fence_token, expires_at FROM web_ops_leases WHERE name=?",
                (TICK_LEASE_NAME,),
            ).fetchone()
            if current and str(current[2]) > now:
                # A concurrent signed request is still consumed.  Persist a
                # compact guarded run so the same nonce/request cannot be
                # replayed after the active lease expires.
                fence_token = int(current[1])
                conn.execute(
                    """INSERT INTO web_ops_runs
                       (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                        action_count, triaged_case_count, incident_count, deadline_at, started_at, finished_at,
                        error_code, receipt_json)
                       VALUES (?, ?, 'railway_cron', ?, 'guarded', ?, ?, ?, 0, 0, 0, ?, ?, ?, ?, ?)""",
                    (
                        run_id, request_id, _time_text(timestamp)[:16], fence_token, POLICY_VERSION, input_hash,
                        _time_text(deadline), now, now, "OPS_TICK_LEASE_HELD",
                        json.dumps({"request_id": request_id, "guarded_code": "OPS_TICK_LEASE_HELD"}, separators=(",", ":")),
                    ),
                )
                return run_id, fence_token, deadline, "OPS_TICK_LEASE_HELD"
            fence_token = int(current[1]) + 1 if current else 1
            if current:
                # This branch is reachable only after the old lease has
                # expired. Fence its exact run before reuse so a crash cannot
                # leave a permanent `started` receipt or write after takeover.
                _guard_expired_lease_run(
                    conn,
                    owner_run_id=current[0],
                    fence_token=current[1],
                    now=now,
                )
                conn.execute(
                    """UPDATE web_ops_leases SET owner_run_id=?, fence_token=?, acquired_at=?, expires_at=?, updated_at=?
                       WHERE name=?""",
                    (run_id, fence_token, now, _time_text(lease_expiry), now, TICK_LEASE_NAME),
                )
            else:
                conn.execute(
                    """INSERT INTO web_ops_leases (name, owner_run_id, fence_token, acquired_at, expires_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (TICK_LEASE_NAME, run_id, fence_token, now, _time_text(lease_expiry), now),
                )
            conn.execute(
                """INSERT INTO web_ops_runs
                   (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                    action_count, triaged_case_count, incident_count, deadline_at, started_at, receipt_json)
                   VALUES (?, ?, 'railway_cron', ?, 'started', ?, ?, ?, 0, 0, 0, ?, ?, '{}')""",
                (run_id, request_id, _time_text(timestamp)[:16], fence_token, POLICY_VERSION, input_hash, _time_text(deadline), now),
            )
    except _TickGuarded:
        raise
    return run_id, fence_token, deadline, None


def _record_guarded_tick(
    *, request_id: str, key_id: str, nonce: str, timestamp: datetime, body: bytes, guarded_code: str,
) -> str:
    """Consume every valid signed identity even when no run may start.

    A topology/configuration/feature-flag guard is not a license to replay a
    verified cron request later after an environment change.  Keep a minimal,
    non-sensitive guarded receipt (and the nonce hash) so the exact HMAC
    request can never turn into a later remediation run.  No lease or
    playbook is acquired here.
    """
    ensure_copyfast_schema()
    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
    now = _time_text(now_dt)
    run_id = str(uuid.uuid4())
    input_hash = hashlib.sha256(body).hexdigest()
    nonce_hash = _nonce_hash(nonce)
    with transaction() as conn:
        conn.execute("DELETE FROM web_ops_nonces WHERE expires_at<?", (now,))
        previous = conn.execute("SELECT id FROM web_ops_runs WHERE request_id=?", (request_id,)).fetchone()
        if previous:
            raise _TickGuarded("OPS_TICK_REPLAYED")
        try:
            conn.execute(
                """INSERT INTO web_ops_nonces (nonce_hash, request_id, key_id, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (nonce_hash, request_id, key_id, now, _time_text(now_dt + timedelta(seconds=TICK_NONCE_TTL_SECONDS))),
            )
        except sqlite3.IntegrityError as exc:
            raise _TickGuarded("OPS_TICK_REPLAYED") from exc
        conn.execute(
            """INSERT INTO web_ops_runs
               (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                action_count, triaged_case_count, incident_count, deadline_at, started_at, finished_at,
                error_code, receipt_json)
               VALUES (?, ?, 'railway_cron', ?, 'guarded', 0, ?, ?, 0, 0, 0, ?, ?, ?, ?, ?)""",
            (
                run_id, request_id, _time_text(timestamp)[:16], POLICY_VERSION, input_hash,
                now, now, now, guarded_code,
                json.dumps({"request_id": request_id, "guarded_code": guarded_code}, separators=(",", ":")),
            ),
        )
    return run_id


def _advance_heartbeat_baseline(
    conn: Any,
    *,
    run_id: str,
    config_fingerprint: str,
    completed_at: str,
) -> None:
    """Arm the optional heartbeat from this exact completed scheduler run.

    Run history is intentionally *not* a baseline.  Only a live-fenced tick
    that this transaction just transitioned to ``completed`` may advance the
    baseline.  The configuration fingerprint and process epoch make a newly
    enabled feature, policy change, or redeploy establish one fresh baseline
    before it can assess any interval.
    """
    completed = conn.execute(
        """SELECT 1 FROM web_ops_runs
           WHERE id=? AND trigger='railway_cron' AND state='completed'""",
        (run_id,),
    ).fetchone()
    if not completed:
        # `_finish_run` performs this transition immediately before calling
        # us.  Keeping the guard makes the local metadata path fail closed if
        # a future caller ever changes that ordering.
        return
    conn.execute(
        """INSERT INTO web_ops_heartbeat_baselines
           (scope, config_fingerprint, process_epoch, last_completed_run_id,
            last_completed_at, armed_at, updated_at, revision)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1)
           ON CONFLICT(scope) DO UPDATE SET
             config_fingerprint=excluded.config_fingerprint,
             process_epoch=excluded.process_epoch,
             last_completed_run_id=excluded.last_completed_run_id,
             last_completed_at=excluded.last_completed_at,
             armed_at=CASE
               WHEN web_ops_heartbeat_baselines.config_fingerprint<>excluded.config_fingerprint
                 OR web_ops_heartbeat_baselines.process_epoch<>excluded.process_epoch
                 OR web_ops_heartbeat_baselines.last_completed_run_id IS NULL
               THEN excluded.armed_at
               ELSE web_ops_heartbeat_baselines.armed_at
             END,
             updated_at=excluded.updated_at,
             revision=web_ops_heartbeat_baselines.revision+1""",
        (
            HEARTBEAT_BASELINE_SCOPE,
            config_fingerprint,
            HEARTBEAT_PROCESS_EPOCH,
            run_id,
            completed_at,
            completed_at,
            completed_at,
        ),
    )


def _finish_run(
    *,
    run_id: str,
    fence_token: int,
    state: str,
    action_count: int,
    triaged_case_count: int,
    incident_count: int,
    receipt: dict[str, Any],
    error_code: str = "",
    heartbeat_config_fingerprint: str | None = None,
) -> bool:
    now = utc_now()
    with transaction() as conn:
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            # The run may have lost its lease to a newer scheduler instance.
            # Close only *this exact fenced row* and never delete/update the
            # new owner's lease.  Leaving it as `started` would make the
            # operations history misleading and complicate later triage.
            stale_receipt = {
                "request_id": str(receipt.get("request_id") or ""),
                "guarded_code": "OPS_TICK_LEASE_LOST",
            }
            conn.execute(
                """UPDATE web_ops_runs SET state='guarded', finished_at=?, error_code=?, receipt_json=?
                   WHERE id=? AND fence_token=? AND state='started'""",
                (
                    now, "OPS_TICK_LEASE_LOST",
                    json.dumps(stale_receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    run_id, fence_token,
                ),
            )
            return False
        updated = conn.execute(
            """UPDATE web_ops_runs SET state=?, action_count=?, triaged_case_count=?, incident_count=?,
               finished_at=?, error_code=?, receipt_json=? WHERE id=? AND fence_token=? AND state='started'""",
            (
                state, action_count, triaged_case_count, incident_count, now, error_code[:80] or None,
                json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")), run_id, fence_token,
            ),
        )
        if int(updated.rowcount or 0) != 1:
            conn.execute(
                "DELETE FROM web_ops_leases WHERE name=? AND owner_run_id=? AND fence_token=?",
                (TICK_LEASE_NAME, run_id, fence_token),
            )
            return False
        if state == "completed" and heartbeat_config_fingerprint:
            # The row is completed and the exact lease is still owned inside
            # this transaction.  This is the only place a heartbeat baseline
            # may move, so a started/current/stale run cannot arm it.
            _advance_heartbeat_baseline(
                conn,
                run_id=run_id,
                config_fingerprint=heartbeat_config_fingerprint,
                completed_at=now,
            )
        conn.execute(
            "DELETE FROM web_ops_leases WHERE name=? AND owner_run_id=? AND fence_token=?",
            (TICK_LEASE_NAME, run_id, fence_token),
        )
    return True


def _insert_step(
    conn: Any,
    *,
    run_id: str,
    sequence: int,
    playbook: str,
    state: str,
    input_hash: str,
    result_code: str,
) -> None:
    now = utc_now()
    conn.execute(
        """INSERT INTO web_ops_run_steps
           (id, run_id, sequence, playbook, state, idempotency_key, input_hash, result_code, started_at, finished_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), run_id, sequence, playbook, state,
            f"ops-step:{run_id}:{sequence}:{playbook}", input_hash, result_code[:80], now, now,
        ),
    )


def _case_sla_age_minutes(value: Any, *, now: datetime) -> int | None:
    """Read only the semantic customer-waiting clock for SLA decisions.

    Generic ``updated_at`` is deliberately not a fallback.  Staff may update
    routing, ownership, escalation or private notes without responding to the
    customer; treating any of those as service would silently reset SLA age.
    Missing, malformed or future clocks therefore fail closed as unverified.
    """
    if value is None or not str(value).strip():
        return None
    try:
        waiting_since = _as_utc(value)
    except (TypeError, ValueError):
        return None
    if waiting_since > now:
        return None
    age = int((now - waiting_since).total_seconds() // 60)
    return max(0, min(age, 10_000_000))


def _case_triage(case: tuple[Any, ...], *, now: datetime) -> dict[str, Any]:
    """Classify a case while preserving the semantic SLA-clock boundary."""
    age_minutes = _case_sla_age_minutes(case[8] if len(case) > 8 else None, now=now)
    triage = complaint_triage(
        category=case[2],
        priority=case[3],
        state=case[4],
        age_minutes=age_minutes if age_minutes is not None else 0,
    )
    if str(case[4]) not in {"resolved", "closed"} and age_minutes is None:
        # The policy remains useful for risk/role classification, but the
        # absence of a trustworthy customer-waiting moment can never mean
        # healthy.  It cannot trigger a breach or close a prior incident.
        triage = dict(triage)
        triage["sla_status"] = "unverified"
    return triage


def _triage_input(case: tuple[Any, ...], triage: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": str(case[0]),
        "revision": int(case[6]),
        "category": triage["category"],
        "priority": triage["priority"],
        "state": triage["state"],
        "risk": triage["risk"],
        "disposition": triage["disposition"],
        "required_role": triage["required_role"],
        "sla_minutes": triage["sla_minutes"],
        "sla_status": triage["sla_status"],
        "policy_version": POLICY_VERSION,
    }


def _upsert_triage(
    conn: Any,
    *,
    run_id: str,
    case: tuple[Any, ...],
    triage: dict[str, Any],
    now: str,
) -> bool:
    """Store only policy metadata; the support narrative never enters this table."""
    input_hash = _json_hash(_triage_input(case, triage))
    existing = conn.execute(
        "SELECT source_revision, policy_version, input_hash FROM web_support_triage WHERE case_id=?",
        (str(case[0]),),
    ).fetchone()
    if existing and int(existing[0]) == int(case[6]) and int(existing[1]) == POLICY_VERSION and hmac.compare_digest(str(existing[2]), input_hash):
        return False
    if existing:
        conn.execute(
            """UPDATE web_support_triage SET account_id=?, source_revision=?, policy_version=?, input_hash=?,
               category=?, priority=?, case_state=?, risk=?, disposition=?, required_role=?, sla_minutes=?,
               sla_status=?, last_run_id=?, updated_at=? WHERE case_id=?""",
            (
                str(case[1]), int(case[6]), POLICY_VERSION, input_hash, triage["category"], triage["priority"],
                triage["state"], triage["risk"], triage["disposition"], triage["required_role"],
                int(triage["sla_minutes"]), triage["sla_status"], run_id, now, str(case[0]),
            ),
        )
        action = "triage_reclassified"
    else:
        conn.execute(
            """INSERT INTO web_support_triage
               (case_id, account_id, source_revision, policy_version, input_hash, category, priority, case_state,
                risk, disposition, required_role, sla_minutes, sla_status, last_run_id, first_classified_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(case[0]), str(case[1]), int(case[6]), POLICY_VERSION, input_hash, triage["category"],
                triage["priority"], triage["state"], triage["risk"], triage["disposition"],
                triage["required_role"], int(triage["sla_minutes"]), triage["sla_status"], run_id, now, now,
            ),
        )
        action = "triage_classified"
    conn.execute(
        """INSERT INTO web_support_triage_events (id, case_id, run_id, action, input_hash, created_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(case_id, input_hash) DO NOTHING""",
        (str(uuid.uuid4()), str(case[0]), run_id, action, input_hash, now),
    )
    return True


def _severity(priority: str) -> str:
    return "critical" if priority == "urgent" else "high" if priority == "high" else "normal"


def _upsert_breach_incident(
    conn: Any,
    *,
    run_id: str,
    case: tuple[Any, ...],
    triage: dict[str, Any],
    incident_secret: str,
    now: str,
) -> tuple[bool, str]:
    fingerprint = incident_fingerprint(
        kind="support_sla_breach",
        scope=f"support_case:{case[0]}",
        error_code=str(triage["sla_status"]),
        secret=incident_secret,
    )
    existing = conn.execute(
        "SELECT id, revision FROM web_ops_incidents WHERE fingerprint=?",
        (fingerprint,),
    ).fetchone()
    if existing:
        incident_id = str(existing[0])
        conn.execute(
            """UPDATE web_ops_incidents SET state='investigating', severity=?, auto_close_eligible=0, healthy_streak=0,
               observation_count=observation_count+1, last_failure_at=?, last_observed_at=?, resolved_at=NULL,
               closed_at=NULL, revision=? WHERE id=?""",
            (str(_severity(str(triage["priority"]))), now, now, int(existing[1]) + 1, incident_id),
        )
        created = False
    else:
        incident_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_ops_incidents
               (id, fingerprint, kind, scope_kind, account_id, support_case_id, state, severity,
                auto_close_eligible, healthy_streak, observation_count, last_failure_at, first_observed_at,
                last_observed_at, revision)
               VALUES (?, ?, 'support_sla_breach', 'support_case', ?, ?, 'open', ?, 0, 0, 1, ?, ?, ?, 1)""",
            (incident_id, fingerprint, str(case[1]), str(case[0]), str(_severity(str(triage["priority"]))), now, now, now),
        )
        created = True
    conn.execute(
        """INSERT INTO web_ops_incident_observations
           (id, incident_id, run_id, observation, result_code, created_at)
           VALUES (?, ?, ?, 'advisory', 'SLA_BREACHED', ?)""",
        (str(uuid.uuid4()), incident_id, run_id, now),
    )
    return created, incident_id


def _active_incident_for_case(conn: Any, case_id: str) -> str | None:
    """Return local incident linkage without creating a fresh observation."""
    row = conn.execute(
        """SELECT id FROM web_ops_incidents
           WHERE support_case_id=? AND state NOT IN ('resolved', 'closed')
           ORDER BY last_observed_at DESC, id DESC LIMIT 1""",
        (case_id,),
    ).fetchone()
    return str(row[0]) if row else None


def _proposal_action(triage: dict[str, Any]) -> str:
    if triage["risk"] == "external_dependency" and str(triage["state"]) == "waiting_provider":
        return "provider_retry"
    return APPROVAL_ACTION_BY_CATEGORY.get(str(triage["category"]), "")


def _propose_approval(
    conn: Any,
    *,
    run_id: str,
    case: tuple[Any, ...],
    triage: dict[str, Any],
    incident_id: str | None,
    incident_secret: str,
    now: str,
) -> bool:
    action_type = _proposal_action(triage)
    if not action_type or triage["state"] in {"resolved", "closed"}:
        return False
    # Each support revision gets one immutable proposal. It does not execute
    # the named action; it only asks a staff member to investigate it.
    proposal_fingerprint = incident_fingerprint(
        kind="approval_proposal",
        scope=f"support_case:{case[0]}:revision:{case[6]}:action:{action_type}",
        error_code=str(triage["risk"]),
        secret=incident_secret,
    )
    existing = conn.execute(
        "SELECT id FROM web_ops_approvals WHERE proposal_fingerprint=?",
        (proposal_fingerprint,),
    ).fetchone()
    if existing:
        return False
    payload_hash = incident_fingerprint(
        kind="approval_payload",
        scope=f"case:{case[0]}:revision:{case[6]}",
        error_code=f"{action_type}:{triage['required_role']}",
        secret=incident_secret,
    )
    approval_id = str(uuid.uuid4())
    expires = _time_text(datetime.now(timezone.utc) + timedelta(days=7))
    conn.execute(
        """INSERT INTO web_ops_approvals
           (id, proposal_fingerprint, action_type, account_id, support_case_id, incident_id, risk, required_role,
            state, revision, payload_hash, proposed_by_run_id, proposed_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'awaiting_approval', 1, ?, ?, ?, ?)""",
        (
            approval_id, proposal_fingerprint, action_type, str(case[1]), str(case[0]), incident_id,
            str(triage["risk"]), str(triage["required_role"]), payload_hash, run_id, now, expires,
        ),
    )
    conn.execute(
        """INSERT INTO web_ops_approval_events
           (id, approval_id, actor_account_id, action, state, revision, created_at)
           VALUES (?, ?, NULL, 'approval_proposed', 'awaiting_approval', 1, ?)""",
        (str(uuid.uuid4()), approval_id, now),
    )
    return True


def _read_cases() -> list[tuple[Any, ...]]:
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, account_id, category, priority, state, created_at, revision, updated_at,
                      customer_waiting_since
               FROM web_support_cases
               WHERE state NOT IN ('resolved', 'closed')
               ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                        CASE WHEN customer_waiting_since IS NULL THEN 1 ELSE 0 END,
                        customer_waiting_since ASC, updated_at ASC, rowid ASC LIMIT ?""",
            (MAX_CASES_PER_TICK,),
        ).fetchall()
    return [tuple(row) for row in rows]


def _read_terminal_case_ids() -> list[str]:
    """Return only terminal cases that already have Operations metadata.

    This is a bounded reconciliation queue, not a scan of support narratives.
    It lets local incidents/proposals converge when a human/customer closes a
    case, without treating that as a provider, payment or customer-delivery
    action.
    """
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT c.id
               FROM web_support_cases AS c
               INNER JOIN web_support_triage AS t ON t.case_id=c.id
               WHERE c.state IN ('resolved', 'closed')
               ORDER BY c.updated_at ASC, c.rowid ASC LIMIT ?""",
            (MAX_CASES_PER_TICK,),
        ).fetchall()
    return [str(row[0]) for row in rows]


def _current_case(conn: Any, case_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        """SELECT id, account_id, category, priority, state, created_at, revision, updated_at,
                  customer_waiting_since
           FROM web_support_cases WHERE id=?""",
        (case_id,),
    ).fetchone()
    return tuple(row) if row else None


def _reconcile_terminal_cases(
    *, run_id: str, fence_token: int, deadline: datetime, action_budget: int,
) -> dict[str, int | bool]:
    """Close only local Operations metadata for terminal Support Desk cases."""
    actions = 0
    triaged = 0
    reconciled = 0
    capped = False
    for case_id in _read_terminal_case_ids():
        if datetime.now(timezone.utc) >= deadline or actions >= action_budget:
            capped = True
            break
        with transaction() as conn:
            now = utc_now()
            if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
                raise _TickLeaseLost()
            # Re-read inside the write transaction. A case can be reopened
            # between queue discovery and mutation; never reconcile stale state.
            case = _current_case(conn, case_id)
            if not case or str(case[4]) not in {"resolved", "closed"}:
                continue
            triage = _case_triage(case, now=datetime.now(timezone.utc))
            if _upsert_triage(conn, run_id=run_id, case=case, triage=triage, now=now):
                actions += 1
                triaged += 1
            if actions >= action_budget:
                capped = True
                continue
            incident_rows = conn.execute(
                """SELECT id, revision FROM web_ops_incidents
                   WHERE support_case_id=? AND state NOT IN ('resolved', 'closed')
                   ORDER BY last_observed_at ASC, id ASC LIMIT ?""",
                (case_id, max(0, action_budget - actions)),
            ).fetchall()
            for incident in incident_rows:
                incident_id = str(incident[0])
                revision = int(incident[1]) + 1
                updated = conn.execute(
                    """UPDATE web_ops_incidents SET state='closed', closed_at=?, healthy_streak=0,
                       revision=? WHERE id=? AND revision=? AND state NOT IN ('resolved', 'closed')""",
                    (now, revision, incident_id, int(incident[1])),
                )
                if int(updated.rowcount or 0) == 1:
                    conn.execute(
                        """INSERT INTO web_ops_incident_observations
                           (id, incident_id, run_id, observation, result_code, created_at)
                           VALUES (?, ?, ?, 'terminal_case_reconciliation', 'SUPPORT_CASE_TERMINAL', ?)""",
                        (str(uuid.uuid4()), incident_id, run_id, now),
                    )
                    actions += 1
                    reconciled += 1
                if actions >= action_budget:
                    capped = True
                    break
            if actions >= action_budget:
                continue
            approval_rows = conn.execute(
                """SELECT id, revision FROM web_ops_approvals
                   WHERE support_case_id=? AND state='awaiting_approval'
                   ORDER BY proposed_at ASC, id ASC LIMIT ?""",
                (case_id, max(0, action_budget - actions)),
            ).fetchall()
            for approval in approval_rows:
                approval_id = str(approval[0])
                revision = int(approval[1]) + 1
                updated = conn.execute(
                    """UPDATE web_ops_approvals SET state='superseded', revision=?, decided_at=?, decision_code='case_terminal'
                       WHERE id=? AND revision=? AND state='awaiting_approval'""",
                    (revision, now, approval_id, int(approval[1])),
                )
                if int(updated.rowcount or 0) == 1:
                    conn.execute(
                        """INSERT INTO web_ops_approval_events
                           (id, approval_id, actor_account_id, action, state, revision, created_at)
                           VALUES (?, ?, NULL, 'approval_superseded', 'superseded', ?, ?)""",
                        (str(uuid.uuid4()), approval_id, revision, now),
                    )
                    actions += 1
                    reconciled += 1
                if actions >= action_budget:
                    capped = True
                    break
    return {"action_count": actions, "triaged_case_count": triaged, "reconciled_count": reconciled, "capped": capped}


def _reconcile_expired_approvals(
    *, run_id: str, fence_token: int, deadline: datetime, action_budget: int,
) -> dict[str, int | bool]:
    """Materialize expiry only on Web-owned approval *records*.

    Expiry was already enforced at decision time.  This bounded reconciliation
    makes that fact visible in the queue while retaining the immutable event
    trail.  It neither executes nor cancels a payment, provider request, Bot
    job, delivery, notification or any action named by an approval.
    """
    if action_budget <= 0:
        return {"action_count": 0, "expired_count": 0, "capped": False}
    if datetime.now(timezone.utc) >= deadline:
        return {"action_count": 0, "expired_count": 0, "capped": True}
    actions = 0
    expired = 0
    capped = False
    with transaction() as conn:
        now = utc_now()
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            raise _TickLeaseLost()
        rows = conn.execute(
            """SELECT id, revision FROM web_ops_approvals
               WHERE state='awaiting_approval' AND expires_at<=?
               ORDER BY expires_at ASC, proposed_at ASC, id ASC LIMIT ?""",
            (now, action_budget),
        ).fetchall()
        for row in rows:
            if datetime.now(timezone.utc) >= deadline:
                capped = True
                break
            approval_id = str(row[0])
            revision = int(row[1]) + 1
            updated = conn.execute(
                """UPDATE web_ops_approvals
                   SET state='expired', revision=?, decided_at=?, decision_code='approval_expired'
                   WHERE id=? AND revision=? AND state='awaiting_approval' AND expires_at<=?""",
                (revision, now, approval_id, int(row[1]), now),
            )
            if int(updated.rowcount or 0) != 1:
                continue
            conn.execute(
                """INSERT INTO web_ops_approval_events
                   (id, approval_id, actor_account_id, action, state, revision, created_at)
                   VALUES (?, ?, NULL, 'approval_expired', 'expired', ?, ?)""",
                (str(uuid.uuid4()), approval_id, revision, now),
            )
            actions += 1
            expired += 1
        if len(rows) >= action_budget and actions >= action_budget:
            capped = True
    return {"action_count": actions, "expired_count": expired, "capped": capped}


def _append_incident_recovery_observation(
    conn: Any,
    *,
    incident_id: str,
    run_id: str,
    observation: str,
    result_code: str,
    now: str,
) -> None:
    """Append compact local evidence without retaining case narrative/data."""
    conn.execute(
        """INSERT INTO web_ops_incident_observations
           (id, incident_id, run_id, observation, result_code, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), incident_id, run_id, observation, result_code[:80], now),
    )


def _recovery_streak(value: Any, *, required_streak: int) -> int | None:
    """Return only a non-terminal persisted streak; corrupt values fail closed."""
    try:
        observed = int(value)
    except (TypeError, ValueError):
        return None
    return observed if 0 <= observed < required_streak else None


def _incident_recovery_reset_needed(*, healthy_streak: Any, auto_close_eligible: Any) -> bool:
    try:
        observed = int(healthy_streak)
        eligible = int(auto_close_eligible)
    except (TypeError, ValueError):
        return True
    return observed != 0 or eligible != 0


def _reset_incident_recovery_streak(
    conn: Any,
    *,
    incident_id: str,
    expected_revision: int,
    healthy_streak: Any,
    auto_close_eligible: Any,
    run_id: str,
    result_code: str,
    now: str,
) -> bool:
    """Clear an interrupted recovery streak with revision fencing only."""
    if not _incident_recovery_reset_needed(
        healthy_streak=healthy_streak,
        auto_close_eligible=auto_close_eligible,
    ):
        return False
    updated = conn.execute(
        """UPDATE web_ops_incidents
           SET auto_close_eligible=0, healthy_streak=0, revision=?
           WHERE id=? AND revision=? AND kind='support_sla_breach' AND scope_kind='support_case'
             AND state NOT IN ('resolved', 'closed')""",
        (expected_revision + 1, incident_id, expected_revision),
    )
    if int(updated.rowcount or 0) != 1:
        return False
    _append_incident_recovery_observation(
        conn,
        incident_id=incident_id,
        run_id=run_id,
        observation="recovery_streak_reset",
        result_code=result_code,
        now=now,
    )
    return True


def _fresh_recovery_triage(case: tuple[Any, ...], *, now: datetime) -> tuple[dict[str, Any] | None, str]:
    """Evaluate the current case inside the write transaction, never a stale row.

    This deliberately uses only category, priority, state and the semantic
    customer-waiting timestamp from Support triage. A missing, malformed or
    future clock is not interpreted as a healthy case; it can only reset/hold
    local incident metadata until a genuine customer-facing case mutation
    produces valid state.
    """
    if str(case[4]) in {"resolved", "closed"}:
        return None, "SUPPORT_CASE_TERMINAL"
    triage = _case_triage(case, now=now)
    if triage["sla_status"] == "unverified":
        return None, "SUPPORT_SLA_CLOCK_UNVERIFIED"
    if triage["risk"] != "web_support":
        return None, "SUPPORT_CASE_NOT_WEB_SUPPORT"
    if triage["sla_status"] != "within_target":
        return None, "SUPPORT_SLA_NOT_WITHIN_TARGET"
    return triage, "SUPPORT_SLA_WITHIN_TARGET"


def _case_has_pending_approval(conn: Any, case_id: str) -> bool:
    row = conn.execute(
        """SELECT 1 FROM web_ops_approvals
           WHERE support_case_id=? AND state='awaiting_approval' LIMIT 1""",
        (case_id,),
    ).fetchone()
    return bool(row)


def _reconcile_incident_recovery(
    *, run_id: str, fence_token: int, deadline: datetime, action_budget: int,
) -> dict[str, int | bool | str]:
    """Close only safe, Web-owned SLA incidents after consecutive healthy ticks.

    The source Support Desk case is read again inside the same fenced SQLite
    transaction.  This function never writes that case, its messages or any
    non-Operations authority.  Financial, provider-dependent, unclassified,
    terminal, stale, mismatched or approval-pending cases can only clear a
    partial local recovery streak; they can never become automatic closes.
    """
    required_streak = _incident_recovery_required_streak()
    if required_streak is None:
        return {
            "action_count": 0,
            "reconciled_count": 0,
            "healthy_observation_count": 0,
            "reset_count": 0,
            "required_streak": 0,
            "capped": False,
            "code": "OPS_INCIDENT_RECOVERY_STREAK_UNVERIFIED",
        }
    if not safe_playbook_allowed(
        INCIDENT_RECOVERY_PLAYBOOK,
        feature_enabled=autopilot_enabled(),
        remediation_enabled=autopilot_safe_remediation_enabled(),
    ):
        return {
            "action_count": 0,
            "reconciled_count": 0,
            "healthy_observation_count": 0,
            "reset_count": 0,
            "required_streak": required_streak,
            "capped": False,
            "code": "OPS_SAFE_REMEDIATION_DISABLED",
        }
    if action_budget <= 0:
        return {
            "action_count": 0,
            "reconciled_count": 0,
            "healthy_observation_count": 0,
            "reset_count": 0,
            "required_streak": required_streak,
            "capped": False,
            "code": "",
        }

    actions = 0
    reconciled = 0
    healthy_observations = 0
    resets = 0
    capped = False
    with transaction() as conn:
        now = utc_now()
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            raise _TickLeaseLost()
        rows = conn.execute(
            """SELECT id, account_id, support_case_id, auto_close_eligible, healthy_streak, revision
               FROM web_ops_incidents
               WHERE kind='support_sla_breach' AND scope_kind='support_case'
                 AND support_case_id IS NOT NULL AND state NOT IN ('resolved', 'closed')
               ORDER BY last_observed_at ASC, id ASC LIMIT ?""",
            (MAX_CASES_PER_TICK,),
        ).fetchall()
        for row in rows:
            if datetime.now(timezone.utc) >= deadline or actions >= action_budget:
                capped = True
                break
            now = utc_now()
            if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
                raise _TickLeaseLost()
            now_dt = _as_utc(now)
            incident_id = str(row[0])
            incident_account_id = str(row[1] or "")
            case_id = str(row[2] or "")
            auto_close_eligible = row[3]
            healthy_streak = row[4]
            revision = int(row[5])
            case = _current_case(conn, case_id) if case_id else None

            reset_code = ""
            triage: dict[str, Any] | None = None
            if not case:
                reset_code = "SUPPORT_CASE_NOT_FOUND"
            elif str(case[1]) != incident_account_id:
                reset_code = "SUPPORT_CASE_ACCOUNT_MISMATCH"
            else:
                triage, triage_code = _fresh_recovery_triage(case, now=now_dt)
                if not triage:
                    reset_code = triage_code
                elif _case_has_pending_approval(conn, str(case[0])):
                    reset_code = "SUPPORT_APPROVAL_PENDING"

            if reset_code:
                if _reset_incident_recovery_streak(
                    conn,
                    incident_id=incident_id,
                    expected_revision=revision,
                    healthy_streak=healthy_streak,
                    auto_close_eligible=auto_close_eligible,
                    run_id=run_id,
                    result_code=reset_code,
                    now=now,
                ):
                    actions += 1
                    resets += 1
                continue

            # A nonzero eligibility marker on an active incident or a streak
            # at/above the terminal threshold is inconsistent persisted state.
            # Restart rather than trusting it toward an automatic close.
            current_streak = _recovery_streak(healthy_streak, required_streak=required_streak)
            try:
                eligibility_clear = int(auto_close_eligible) == 0
            except (TypeError, ValueError):
                eligibility_clear = False
            if current_streak is None or not eligibility_clear:
                if _reset_incident_recovery_streak(
                    conn,
                    incident_id=incident_id,
                    expected_revision=revision,
                    healthy_streak=healthy_streak,
                    auto_close_eligible=auto_close_eligible,
                    run_id=run_id,
                    result_code="INCIDENT_RECOVERY_STATE_INVALID",
                    now=now,
                ):
                    actions += 1
                    resets += 1
                continue

            next_streak = current_streak + 1
            close_now = may_auto_close_incident(
                healthy_streak=next_streak,
                required_streak=required_streak,
                has_pending_approval=False,
            )
            next_revision = revision + 1
            if close_now:
                updated = conn.execute(
                    """UPDATE web_ops_incidents
                       SET state='closed', auto_close_eligible=1, healthy_streak=?, closed_at=?, revision=?
                       WHERE id=? AND revision=? AND kind='support_sla_breach' AND scope_kind='support_case'
                         AND state NOT IN ('resolved', 'closed')""",
                    (next_streak, now, next_revision, incident_id, revision),
                )
                observation = "recovery_reconciled"
                result_code = "SUPPORT_SLA_RECOVERY_STREAK"
            else:
                updated = conn.execute(
                    """UPDATE web_ops_incidents
                       SET auto_close_eligible=0, healthy_streak=?, revision=?
                       WHERE id=? AND revision=? AND kind='support_sla_breach' AND scope_kind='support_case'
                         AND state NOT IN ('resolved', 'closed')""",
                    (next_streak, next_revision, incident_id, revision),
                )
                observation = "recovery_healthy_tick"
                result_code = "SUPPORT_SLA_WITHIN_TARGET"
            if int(updated.rowcount or 0) != 1:
                continue
            _append_incident_recovery_observation(
                conn,
                incident_id=incident_id,
                run_id=run_id,
                observation=observation,
                result_code=result_code,
                now=now,
            )
            actions += 1
            healthy_observations += 1
            reconciled += 1 if close_now else 0
    return {
        "action_count": actions,
        "reconciled_count": reconciled,
        "healthy_observation_count": healthy_observations,
        "reset_count": resets,
        "required_streak": required_streak,
        "capped": capped,
        "code": "OPS_ACTION_BUDGET_REACHED" if capped else "",
    }


def _heartbeat_snapshot(
    conn: Any,
    *,
    now: datetime,
) -> dict[str, Any]:
    """Read one bounded scheduler-heartbeat state without changing anything.

    A heartbeat is evidence that a signed Cron request reached this Web App,
    not proof that a provider, Bot, job or deployment is healthy.  It uses an
    explicitly armed persisted baseline, never a generic historical run: the
    first valid tick after enablement, policy change, or Web-process restart
    therefore cannot turn old run history into a false late-Cron incident.
    """
    if not autopilot_heartbeat_followup_enabled():
        return {"state": "disabled", "late": False, "previous_tick_seen": False, "code": ""}
    fingerprint = _heartbeat_config_fingerprint()
    if fingerprint is None:
        return {"state": "guarded", "late": False, "previous_tick_seen": False, "code": "OPS_HEARTBEAT_CONFIG_UNVERIFIED"}
    limits = _heartbeat_limits()
    if limits is None:
        return {"state": "guarded", "late": False, "previous_tick_seen": False, "code": "OPS_HEARTBEAT_CONFIG_UNVERIFIED"}
    expected_seconds, grace_seconds = limits
    baseline = conn.execute(
        """SELECT config_fingerprint, process_epoch, last_completed_run_id, last_completed_at
           FROM web_ops_heartbeat_baselines WHERE scope=?""",
        (HEARTBEAT_BASELINE_SCOPE,),
    ).fetchone()
    # Do not query historical run rows until a matching process/configuration
    # has armed a completed baseline.  This is the critical false-positive
    # fence for a newly enabled heartbeat and for a redeployed Web process.
    if (
        not baseline
        or str(baseline[0]) != fingerprint
        or str(baseline[1]) != HEARTBEAT_PROCESS_EPOCH
        or not str(baseline[2] or "").strip()
        or not str(baseline[3] or "").strip()
    ):
        return {"state": "baseline_pending", "late": False, "previous_tick_seen": False, "code": ""}
    row = conn.execute(
        """SELECT id, started_at FROM web_ops_runs
           WHERE id=? AND trigger='railway_cron' AND state='completed'""",
        (str(baseline[2]),),
    ).fetchone()
    if not row:
        return {"state": "guarded", "late": False, "previous_tick_seen": False, "code": "OPS_HEARTBEAT_HISTORY_INVALID"}
    try:
        previous = _as_utc(row[1])
        completed_at = _as_utc(baseline[3])
        elapsed_seconds = int((now - previous).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return {"state": "guarded", "late": False, "previous_tick_seen": True, "code": "OPS_HEARTBEAT_HISTORY_INVALID"}
    if elapsed_seconds < 0 or completed_at < previous or completed_at > now:
        return {"state": "guarded", "late": False, "previous_tick_seen": True, "code": "OPS_HEARTBEAT_HISTORY_INVALID"}
    late = elapsed_seconds > expected_seconds + grace_seconds
    return {
        "state": "late" if late else "within_window",
        "late": late,
        "previous_tick_seen": True,
        "previous_run_id": str(row[0]),
        "code": "",
    }


def _reconcile_scheduler_heartbeat(
    *, run_id: str, fence_token: int, deadline: datetime, action_budget: int, incident_secret: str | None,
) -> dict[str, Any]:
    """Record one local follow-up only when a signed Cron tick arrived late.

    The playbook is intentionally one-directional: it observes the interval
    only when a new, already-authenticated tick holds the lease and records a
    Web-only incident for staff review.  It does not invoke, restart, repair,
    reschedule or otherwise touch Railway/Cron, and it never calls Bot, a
    bridge, provider, wallet, PayOS, jobs, deployment or notifications.
    """
    result = {
        "action_count": 0,
        "late_count": 0,
        "state": "disabled",
        "previous_tick_seen": False,
        "capped": False,
        "code": "",
    }
    if not autopilot_safe_remediation_enabled() or not autopilot_heartbeat_followup_enabled():
        return result
    limits = _heartbeat_limits()
    if limits is None:
        result.update(state="guarded", code="OPS_HEARTBEAT_CONFIG_UNVERIFIED")
        return result
    if not incident_secret:
        result.update(state="guarded", code="OPS_INCIDENT_SECRET_UNAVAILABLE")
        return result
    with transaction() as conn:
        now = utc_now()
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            raise _TickLeaseLost()
        snapshot = _heartbeat_snapshot(conn, now=_as_utc(now))
        result.update(
            state=str(snapshot["state"]),
            previous_tick_seen=bool(snapshot["previous_tick_seen"]),
            code=str(snapshot["code"]),
        )
        if not bool(snapshot["late"]):
            return result
        if datetime.now(timezone.utc) >= deadline or action_budget <= 0:
            result.update(capped=True, code="OPS_ACTION_BUDGET_REACHED")
            return result
        # The same live fence is checked immediately before the only write.
        # A concurrently replaced lease can therefore never create a late-Cron
        # follow-up on behalf of a stale scheduler run.
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            raise _TickLeaseLost()
        fingerprint = incident_fingerprint(
            kind=HEARTBEAT_INCIDENT_KIND,
            scope="scheduler:railway_cron",
            error_code="late",
            secret=incident_secret,
        )
        gap_marker = incident_fingerprint(
            kind="scheduler_heartbeat_gap",
            scope=f"completed_run:{str(snapshot.get('previous_run_id') or '')}",
            error_code="late",
            secret=incident_secret,
        )
        observation_code = f"OPS_HEARTBEAT_LATE:{gap_marker[:48]}"
        existing = conn.execute(
            "SELECT id, revision FROM web_ops_incidents WHERE fingerprint=?",
            (fingerprint,),
        ).fetchone()
        if existing:
            already_recorded = conn.execute(
                """SELECT 1 FROM web_ops_incident_observations
                   WHERE incident_id=? AND observation='scheduler_heartbeat_late' AND result_code=? LIMIT 1""",
                (str(existing[0]), observation_code),
            ).fetchone()
            if already_recorded:
                # A stale request/retry must not append a second incident
                # observation for the same completed-to-current gap.
                result.update(state="late")
                return result
        if existing:
            incident_id = str(existing[0])
            next_revision = int(existing[1]) + 1
            updated = conn.execute(
                """UPDATE web_ops_incidents
                   SET state='investigating', severity='high', auto_close_eligible=0, healthy_streak=0,
                       observation_count=observation_count+1, last_failure_at=?, last_observed_at=?,
                       resolved_at=NULL, closed_at=NULL, revision=?
                   WHERE id=? AND fingerprint=? AND revision=?""",
                (now, now, next_revision, incident_id, fingerprint, int(existing[1])),
            )
            if int(updated.rowcount or 0) != 1:
                result.update(state="guarded", code="OPS_HEARTBEAT_WRITE_CONFLICT")
                return result
        else:
            incident_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO web_ops_incidents
                   (id, fingerprint, kind, scope_kind, account_id, support_case_id, state, severity,
                    auto_close_eligible, healthy_streak, observation_count, last_failure_at, first_observed_at,
                    last_observed_at, revision)
                   VALUES (?, ?, ?, ?, NULL, NULL, 'open', 'high', 0, 0, 1, ?, ?, ?, 1)""",
                (incident_id, fingerprint, HEARTBEAT_INCIDENT_KIND, HEARTBEAT_SCOPE_KIND, now, now, now),
            )
        _append_incident_recovery_observation(
            conn,
            incident_id=incident_id,
            run_id=run_id,
            observation="scheduler_heartbeat_late",
            result_code=observation_code,
            now=now,
        )
        result.update(action_count=1, late_count=1, state="late")
    return result


def _run_safe_triage(
    *, run_id: str, fence_token: int, deadline: datetime, incident_secret: str | None, max_actions: int,
) -> dict[str, Any]:
    """Run only deterministic, local actions while the matching lease is live."""
    with read_transaction() as conn:
        conn.execute("SELECT 1").fetchone()
    health_hash = _json_hash({"playbook": "health_probe", "policy_version": POLICY_VERSION})
    with transaction() as conn:
        now = utc_now()
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            raise _TickLeaseLost()
        _insert_step(
            conn, run_id=run_id, sequence=1, playbook="health_probe", state="completed",
            input_hash=health_hash, result_code="LOCAL_DATABASE_READY",
        )
    if not safe_playbook_allowed(
        "support_triage_metadata",
        feature_enabled=autopilot_enabled(),
        remediation_enabled=autopilot_safe_remediation_enabled(),
    ):
        with transaction() as conn:
            now = utc_now()
            if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
                raise _TickLeaseLost()
            _insert_step(
                conn, run_id=run_id, sequence=2, playbook="support_triage_metadata", state="guarded",
                input_hash=_json_hash({"playbook": "support_triage_metadata", "enabled": False}),
                result_code="OPS_SAFE_REMEDIATION_DISABLED",
            )
        return {
            "state": "guarded", "action_count": 0, "triaged_case_count": 0, "incident_count": 0,
            "code": "OPS_SAFE_REMEDIATION_DISABLED", "capped": False,
        }

    if not incident_secret:
        # This should have been returned as a guarded preflight response before
        # the run started. Keep the runtime defensive if environment mutation
        # occurs while a process is alive.
        return {
            "state": "guarded", "action_count": 0, "triaged_case_count": 0, "incident_count": 0,
            "approval_count": 0, "code": "OPS_INCIDENT_SECRET_UNAVAILABLE", "capped": False,
        }
    # Heartbeat is evaluated only after this run owns the live fence. It
    # compares with a *completed* predecessor, never the just-created run.
    heartbeat = _reconcile_scheduler_heartbeat(
        run_id=run_id,
        fence_token=fence_token,
        deadline=deadline,
        action_budget=max_actions,
        incident_secret=incident_secret,
    )
    actions = int(heartbeat["action_count"])
    reconciliation = _reconcile_terminal_cases(
        run_id=run_id, fence_token=fence_token, deadline=deadline, action_budget=max(0, max_actions - actions),
    )
    actions += int(reconciliation["action_count"])
    triaged = int(reconciliation["triaged_case_count"])
    expiry = _reconcile_expired_approvals(
        run_id=run_id,
        fence_token=fence_token,
        deadline=deadline,
        action_budget=max(0, max_actions - actions),
    )
    actions += int(expiry["action_count"])
    incidents = int(heartbeat["late_count"])
    approvals = 0
    expired_approvals = int(expiry["expired_count"])
    changed = int(reconciliation["triaged_case_count"])
    terminal_reconciled = int(reconciliation["reconciled_count"])
    capped = bool(heartbeat["capped"] or reconciliation["capped"] or expiry["capped"])
    for snapshot in _read_cases():
        if datetime.now(timezone.utc) >= deadline or actions >= max_actions:
            capped = True
            break
        now = utc_now()
        with transaction() as conn:
            if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
                raise _TickLeaseLost()
            # The queue snapshot is advisory only. Re-read the case in the
            # same transaction as the triage/incident/proposal writes so a
            # concurrent customer close/reopen cannot create stale work.
            case = _current_case(conn, str(snapshot[0]))
            if not case or str(case[4]) in {"resolved", "closed"}:
                continue
            triage = _case_triage(case, now=datetime.now(timezone.utc))
            was_changed = _upsert_triage(conn, run_id=run_id, case=case, triage=triage, now=now)
            if was_changed:
                changed += 1
                triaged += 1
                actions += 1
            # A previous run may have spent its action budget after recording
            # triage but before creating its incident/proposal.  Reconcile
            # only those missing follow-ups on later ticks; do not churn an
            # already-linked incident or create repeat observations.
            incident_id = _active_incident_for_case(conn, str(case[0]))
            if triage["sla_status"] == "breached" and actions < max_actions:
                if was_changed or not incident_id:
                    created, incident_id = _upsert_breach_incident(
                        conn, run_id=run_id, case=case, triage=triage, incident_secret=incident_secret, now=now,
                    )
                    incidents += 1 if created else 0
                    actions += 1
            if triage["disposition"] == "awaiting_operator" and actions < max_actions:
                if _propose_approval(
                    conn, run_id=run_id, case=case, triage=triage, incident_id=incident_id,
                    incident_secret=incident_secret, now=now,
                ):
                    approvals += 1
                    actions += 1
        if actions >= max_actions:
            capped = True
            break

    # Recovery is deliberately after current-case triage. It re-reads every
    # candidate case again inside its own fenced write transaction, so neither
    # a stale queue snapshot nor a previous healthy observation can close an
    # incident on its own.
    recovery = _reconcile_incident_recovery(
        run_id=run_id,
        fence_token=fence_token,
        deadline=deadline,
        action_budget=max(0, max_actions - actions),
    )
    actions += int(recovery["action_count"])
    capped = bool(capped or recovery["capped"])

    # Reliability uses the same signed run, deadline, action budget and
    # fencing token. It can only create/update a local follow-up metadata
    # row; it cannot repair code, restart Railway, call a provider/Bot, touch
    # payment/wallet or contact a customer.
    reliability = {
        "runtime_followup_count": 0,
        "complaint_followup_count": 0,
        "superseded_count": 0,
        "capped": False,
        "code": "",
    }
    if copyfast_reliability.reliability_followup_enabled() and incident_secret:
        reliability = copyfast_reliability.reconcile_followups(
            run_id=run_id,
            deadline=deadline,
            action_budget=max(0, max_actions - actions),
            secret=incident_secret,
            lease_current=lambda conn: _lease_current(
                conn, run_id=run_id, fence_token=fence_token, now=utc_now(),
            ),
        )
        actions += (
            int(reliability["runtime_followup_count"])
            + int(reliability["complaint_followup_count"])
            + int(reliability["superseded_count"])
        )
        capped = bool(capped or reliability["capped"])

    state = "guarded" if capped or heartbeat["code"] or recovery["code"] or reliability["code"] else "completed"
    code = str(heartbeat["code"] or recovery["code"] or reliability["code"] or ("OPS_ACTION_BUDGET_REACHED" if capped else ""))
    with transaction() as conn:
        now = utc_now()
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            raise _TickLeaseLost()
        _insert_step(
            conn, run_id=run_id, sequence=2, playbook="support_triage_metadata", state=state,
            input_hash=_json_hash({
                "changed": changed, "terminal_reconciled": terminal_reconciled, "policy_version": POLICY_VERSION,
            }),
            result_code=code or "TRIAGE_METADATA_RECORDED",
        )
        _insert_step(
            conn, run_id=run_id, sequence=3, playbook="terminal_case_metadata_reconciliation", state=state,
            input_hash=_json_hash({"terminal_reconciled": terminal_reconciled, "policy_version": POLICY_VERSION}),
            result_code=code or "TERMINAL_CASE_METADATA_RECONCILED",
        )
        _insert_step(
            conn, run_id=run_id, sequence=4, playbook="approval_expiry_reconciliation", state=state,
            input_hash=_json_hash({"expired_approvals": expired_approvals, "policy_version": POLICY_VERSION}),
            result_code=code or "APPROVAL_EXPIRY_RECONCILED",
        )
        _insert_step(
            conn, run_id=run_id, sequence=5, playbook=INCIDENT_RECOVERY_PLAYBOOK, state=state,
            input_hash=_json_hash({
                "reconciled": int(recovery["reconciled_count"]),
                "healthy_observations": int(recovery["healthy_observation_count"]),
                "resets": int(recovery["reset_count"]),
                "required_streak": int(recovery["required_streak"]),
                "policy_version": POLICY_VERSION,
            }),
            result_code=code or "INCIDENT_RECOVERY_RECONCILED",
        )
        if copyfast_reliability.reliability_followup_enabled():
            _insert_step(
                conn, run_id=run_id, sequence=6, playbook="reliability_followup_metadata", state=state,
                input_hash=_json_hash({
                    "runtime_followups": int(reliability["runtime_followup_count"]),
                    "complaint_followups": int(reliability["complaint_followup_count"]),
                    "superseded": int(reliability["superseded_count"]),
                    "policy_version": POLICY_VERSION,
                }),
                result_code=code or "RELIABILITY_FOLLOWUPS_RECONCILED",
            )
        if autopilot_heartbeat_followup_enabled():
            _insert_step(
                conn, run_id=run_id, sequence=7, playbook=HEARTBEAT_FOLLOWUP_PLAYBOOK, state=state,
                input_hash=_json_hash({
                    "late": int(heartbeat["late_count"]),
                    "previous_tick_seen": bool(heartbeat["previous_tick_seen"]),
                    "policy_version": POLICY_VERSION,
                }),
                result_code=code or "SCHEDULER_HEARTBEAT_RECORDED",
            )
        conn.execute(
            """INSERT INTO web_ops_playbook_runs
               (id, run_id, incident_id, playbook, state, attempt, idempotency_key, input_hash, result_code, started_at, finished_at)
               VALUES (?, ?, NULL, 'support_triage_metadata', ?, 1, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), run_id, state, f"ops-playbook:{run_id}:support_triage_metadata",
                _json_hash({
                    "changed": changed, "terminal_reconciled": terminal_reconciled, "policy_version": POLICY_VERSION,
                }), code or "TRIAGE_METADATA_RECORDED", now, now,
            ),
        )
        conn.execute(
            """INSERT INTO web_ops_playbook_runs
               (id, run_id, incident_id, playbook, state, attempt, idempotency_key, input_hash, result_code, started_at, finished_at)
               VALUES (?, ?, NULL, 'approval_expiry_reconciliation', ?, 1, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), run_id, state, f"ops-playbook:{run_id}:approval_expiry_reconciliation",
                _json_hash({"expired_approvals": expired_approvals, "policy_version": POLICY_VERSION}),
                code or "APPROVAL_EXPIRY_RECONCILED", now, now,
            ),
        )
        conn.execute(
            """INSERT INTO web_ops_playbook_runs
               (id, run_id, incident_id, playbook, state, attempt, idempotency_key, input_hash, result_code, started_at, finished_at)
               VALUES (?, ?, NULL, ?, ?, 1, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), run_id, INCIDENT_RECOVERY_PLAYBOOK, state,
                f"ops-playbook:{run_id}:{INCIDENT_RECOVERY_PLAYBOOK}",
                _json_hash({
                    "reconciled": int(recovery["reconciled_count"]),
                    "healthy_observations": int(recovery["healthy_observation_count"]),
                    "resets": int(recovery["reset_count"]),
                    "required_streak": int(recovery["required_streak"]),
                    "policy_version": POLICY_VERSION,
                }), code or "INCIDENT_RECOVERY_RECONCILED", now, now,
            ),
        )
        if copyfast_reliability.reliability_followup_enabled():
            conn.execute(
                """INSERT INTO web_ops_playbook_runs
                   (id, run_id, incident_id, playbook, state, attempt, idempotency_key, input_hash, result_code, started_at, finished_at)
                   VALUES (?, ?, NULL, 'reliability_followup_metadata', ?, 1, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), run_id, state, f"ops-playbook:{run_id}:reliability_followup_metadata",
                    _json_hash({
                        "runtime_followups": int(reliability["runtime_followup_count"]),
                        "complaint_followups": int(reliability["complaint_followup_count"]),
                        "superseded": int(reliability["superseded_count"]),
                        "policy_version": POLICY_VERSION,
                    }), code or "RELIABILITY_FOLLOWUPS_RECONCILED", now, now,
                ),
            )
        if autopilot_heartbeat_followup_enabled():
            conn.execute(
                """INSERT INTO web_ops_playbook_runs
                   (id, run_id, incident_id, playbook, state, attempt, idempotency_key, input_hash, result_code, started_at, finished_at)
                   VALUES (?, ?, NULL, ?, ?, 1, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), run_id, HEARTBEAT_FOLLOWUP_PLAYBOOK, state,
                    f"ops-playbook:{run_id}:{HEARTBEAT_FOLLOWUP_PLAYBOOK}",
                    _json_hash({
                        "late": int(heartbeat["late_count"]),
                        "previous_tick_seen": bool(heartbeat["previous_tick_seen"]),
                        "policy_version": POLICY_VERSION,
                    }), code or "SCHEDULER_HEARTBEAT_RECORDED", now, now,
                ),
            )
    return {
        "state": state, "action_count": actions, "triaged_case_count": triaged,
        "incident_count": incidents, "approval_count": approvals, "terminal_reconciled_count": terminal_reconciled,
        "approval_expired_count": expired_approvals,
        "incident_recovery_reconciled_count": int(recovery["reconciled_count"]),
        "incident_recovery_healthy_observation_count": int(recovery["healthy_observation_count"]),
        "incident_recovery_reset_count": int(recovery["reset_count"]),
        "incident_recovery_required_streak": int(recovery["required_streak"]),
        "scheduler_heartbeat_late_count": int(heartbeat["late_count"]),
        "scheduler_heartbeat_previous_tick_seen": bool(heartbeat["previous_tick_seen"]),
        "scheduler_heartbeat_state": str(heartbeat["state"]),
        "runtime_followup_count": int(reliability["runtime_followup_count"]),
        "complaint_followup_count": int(reliability["complaint_followup_count"]),
        "followup_superseded_count": int(reliability["superseded_count"]),
        "code": code, "capped": capped,
    }


def _run_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]), "request_id": str(row[1]), "trigger": str(row[2]), "schedule_slot": str(row[3]),
        "state": str(row[4]), "policy_version": int(row[6]), "action_count": int(row[8]),
        "triaged_case_count": int(row[9]), "incident_count": int(row[10]), "deadline_at": str(row[11]),
        "started_at": str(row[12]), "finished_at": str(row[13]) if row[13] else None,
        "error_code": str(row[14]) if row[14] else None,
    }


def _incident_public(row: tuple[Any, ...], *, staff: bool) -> dict[str, Any]:
    result = {
        "id": str(row[0]), "kind": str(row[1]), "scope_kind": str(row[2]), "state": str(row[5]),
        "severity": str(row[6]), "auto_close_eligible": bool(row[7]), "healthy_streak": int(row[8]),
        "observation_count": int(row[9]), "first_observed_at": str(row[11]), "last_observed_at": str(row[12]),
        "resolved_at": str(row[13]) if row[13] else None, "closed_at": str(row[14]) if row[14] else None,
        "revision": int(row[15]),
    }
    if staff:
        result["support_case_id"] = str(row[4]) if row[4] else None
    return result


def _triage_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "case_id": str(row[0]), "source_revision": int(row[1]), "policy_version": int(row[2]),
        "category": str(row[3]), "priority": str(row[4]), "state": str(row[5]), "risk": str(row[6]),
        "disposition": str(row[7]), "required_role": str(row[8]), "sla_minutes": int(row[9]),
        "sla_status": str(row[10]), "updated_at": str(row[11]),
        "automation": "metadata_only_no_customer_reply_or_external_execution",
    }


def _approval_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]), "action_type": str(row[1]), "support_case_id": str(row[2]) if row[2] else None,
        "incident_id": str(row[3]) if row[3] else None, "risk": str(row[4]), "required_role": str(row[5]),
        "state": str(row[6]), "revision": int(row[7]), "proposed_at": str(row[8]),
        "expires_at": str(row[9]), "decided_at": str(row[10]) if row[10] else None,
        "decision_code": str(row[11]) if row[11] else None,
        "execution": "approval_record_only",
    }


def _idempotent(
    *,
    scope: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[1] or ""), request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu Operations khác")
            try:
                stored = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Operations không hợp lệ") from exc
            if not isinstance(stored, dict):
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Operations không hợp lệ")
            return stored
        response = operation(conn)
        conn.execute(
            """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
        )
    return response


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    confirm: bool = False
    decision_code: str = Field(min_length=3, max_length=80)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("decision_code")
    @classmethod
    def _decision(cls, value: str) -> str:
        return _decision_code(value)

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


@router.post("/internal/v1/operations/tick", include_in_schema=False)
async def tick(request: Request):
    """Accept one HMAC-signed, replay-protected scheduler invocation."""
    content_length = request.headers.get("content-length", "").strip()
    if content_length:
        try:
            if int(content_length) > TICK_MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Dữ liệu Operations nội bộ vượt giới hạn an toàn")
        except ValueError:
            raise HTTPException(status_code=422, detail="Dữ liệu Operations nội bộ không hợp lệ") from None
    body = await request.body()
    timestamp, nonce, request_id, key_id, _timestamp_value = _tick_headers(request, body)
    _tick_payload(body, timestamp=timestamp)
    # A configured Cron must not be reported as a failed Railway job merely
    # because an operator deliberately paused Autopilot.  Authenticate the
    # request first, then answer truthfully with a successful guarded receipt
    # without acquiring a lease or touching any customer/support metadata.
    if not autopilot_enabled():
        try:
            _record_guarded_tick(
                request_id=request_id, key_id=key_id, nonce=nonce, timestamp=_timestamp_value,
                body=body, guarded_code="OPS_AUTOPILOT_DISABLED",
            )
        except _TickGuarded as exc:
            return envelope(
                True, _safe_public_message(exc.code),
                data=_boundary(request_id=request_id, run_started=False, guarded_code=exc.code),
                status_name="guarded",
            )
        return envelope(
            True, _safe_public_message("OPS_AUTOPILOT_DISABLED"),
            data=_boundary(request_id=request_id, run_started=False, guarded_code="OPS_AUTOPILOT_DISABLED"),
            status_name="guarded",
        )
    preflight_code = _scheduler_preflight_code()
    if preflight_code:
        try:
            _record_guarded_tick(
                request_id=request_id, key_id=key_id, nonce=nonce, timestamp=_timestamp_value,
                body=body, guarded_code=preflight_code,
            )
        except _TickGuarded as exc:
            return envelope(
                True, _safe_public_message(exc.code),
                data=_boundary(request_id=request_id, run_started=False, guarded_code=exc.code),
                status_name="guarded",
            )
        return envelope(
            True, _safe_public_message(preflight_code),
            data=_boundary(request_id=request_id, run_started=False, guarded_code=preflight_code),
            status_name="guarded",
        )
    limits = _scheduler_limits()
    if limits is None:
        # Defensive against a process environment mutation between preflight
        # and execution. The authenticated nonce is still consumed so Railway
        # cannot retry the same bad configuration into an error loop.
        guarded_code = "OPS_MAX_RUN_SECONDS_UNVERIFIED"
        try:
            _record_guarded_tick(
                request_id=request_id, key_id=key_id, nonce=nonce, timestamp=_timestamp_value,
                body=body, guarded_code=guarded_code,
            )
        except _TickGuarded as exc:
            guarded_code = exc.code
        return envelope(
            True, _safe_public_message(guarded_code),
            data=_boundary(request_id=request_id, run_started=False, guarded_code=guarded_code),
            status_name="guarded",
        )
    deadline_seconds, max_actions = limits
    incident_secret = _incident_secret() if autopilot_safe_remediation_enabled() else None
    # Capture the policy snapshot that this signed tick is allowed to arm.
    # If configuration changes while it is running, the next tick sees a
    # fingerprint mismatch and safely establishes a new baseline instead of
    # comparing intervals across two policies.
    heartbeat_config_fingerprint = (
        _heartbeat_config_fingerprint()
        if autopilot_safe_remediation_enabled() and autopilot_heartbeat_followup_enabled()
        else None
    )
    try:
        run_id, fence_token, deadline, guarded_code = _start_run(
            request_id=request_id, key_id=key_id, nonce=nonce, timestamp=_timestamp_value, body=body,
            deadline_seconds=deadline_seconds,
        )
    except _TickGuarded as exc:
        return envelope(
            True, _safe_public_message(exc.code),
            data=_boundary(request_id=request_id, run_started=False, guarded_code=exc.code),
            status_name="guarded",
        )
    if guarded_code:
        return envelope(
            True, _safe_public_message(guarded_code),
            data=_boundary(request_id=request_id, run_started=False, guarded_code=guarded_code),
            status_name="guarded",
        )

    started = time.monotonic()
    try:
        result = _run_safe_triage(
            run_id=run_id, fence_token=fence_token, deadline=deadline, incident_secret=incident_secret,
            max_actions=max_actions,
        )
        state = str(result["state"])
        receipt = {
            "request_id": request_id, "run_started": True, "action_count": int(result["action_count"]),
            "triaged_case_count": int(result["triaged_case_count"]), "incident_count": int(result["incident_count"]),
            "approval_count": int(result.get("approval_count", 0)), "duration_ms": int((time.monotonic() - started) * 1000),
            "terminal_reconciled_count": int(result.get("terminal_reconciled_count", 0)),
            "approval_expired_count": int(result.get("approval_expired_count", 0)),
            "incident_recovery_reconciled_count": int(result.get("incident_recovery_reconciled_count", 0)),
            "incident_recovery_healthy_observation_count": int(result.get("incident_recovery_healthy_observation_count", 0)),
            "incident_recovery_reset_count": int(result.get("incident_recovery_reset_count", 0)),
            "incident_recovery_required_streak": int(result.get("incident_recovery_required_streak", 0)),
            "scheduler_heartbeat_late_count": int(result.get("scheduler_heartbeat_late_count", 0)),
            "scheduler_heartbeat_previous_tick_seen": bool(result.get("scheduler_heartbeat_previous_tick_seen", False)),
            "scheduler_heartbeat_state": str(result.get("scheduler_heartbeat_state", "disabled")),
            "runtime_followup_count": int(result.get("runtime_followup_count", 0)),
            "complaint_followup_count": int(result.get("complaint_followup_count", 0)),
            "followup_superseded_count": int(result.get("followup_superseded_count", 0)),
            "safe_remediation": bool(autopilot_safe_remediation_enabled()),
        }
        if result.get("code"):
            receipt["guarded_code"] = str(result["code"])
        if not _finish_run(
            run_id=run_id, fence_token=fence_token, state=state, action_count=int(result["action_count"]),
            triaged_case_count=int(result["triaged_case_count"]), incident_count=int(result["incident_count"]),
            receipt=receipt, error_code=str(result.get("code") or ""),
            heartbeat_config_fingerprint=heartbeat_config_fingerprint,
        ):
            return envelope(
                True, _safe_public_message("OPS_TICK_LEASE_LOST"),
                data=_boundary(request_id=request_id, run_started=True, guarded_code="OPS_TICK_LEASE_LOST"),
                status_name="guarded",
            )
        message = _safe_public_message(str(result["code"])) if result.get("code") else "Operations Autopilot đã ghi nhận kết quả quan sát an toàn."
        return envelope(True, message, data=_boundary(**receipt), status_name=state)
    except (_TickLeaseLost, copyfast_reliability.ReliabilityLeaseLost):
        _finish_run(
            run_id=run_id, fence_token=fence_token, state="guarded", action_count=0, triaged_case_count=0,
            incident_count=0, receipt={"request_id": request_id, "guarded_code": "OPS_TICK_LEASE_LOST"},
            error_code="OPS_TICK_LEASE_LOST",
        )
        return envelope(
            True, _safe_public_message("OPS_TICK_LEASE_LOST"),
            data=_boundary(request_id=request_id, run_started=True, guarded_code="OPS_TICK_LEASE_LOST"),
            status_name="guarded",
        )
    except Exception:
        _finish_run(
            run_id=run_id, fence_token=fence_token, state="failed", action_count=0, triaged_case_count=0,
            incident_count=0, receipt={"request_id": request_id, "failure": "internal_guarded"},
            error_code="OPS_TICK_INTERNAL_FAILURE",
        )
        raise HTTPException(status_code=500, detail="Operations Autopilot không thể hoàn tất lần quét an toàn") from None


@router.get("/api/v1/operations/policy")
async def policy(account: dict = Depends(require_account)):
    _require_enabled()
    preflight_code = _scheduler_preflight_code()
    return envelope(
        True, "Chính sách Operations Autopilot chỉ cho phép quan sát và remediation metadata cục bộ đã allow-list.",
        data=_boundary(
            account_id_present=bool(account.get("id")),
            scheduler_preflight=preflight_code or "ready",
            auto_playbooks=[
                "health_probe", "support_triage_metadata", "terminal_case_metadata_reconciliation",
                "approval_expiry_reconciliation", INCIDENT_RECOVERY_PLAYBOOK,
                *([HEARTBEAT_FOLLOWUP_PLAYBOOK] if autopilot_heartbeat_followup_enabled() else []),
            ],
            approval_only=["wallet_adjustment", "payment_finalize", "payment_refund", "provider_retry", "customer_reply", "deploy"],
        ),
        status_name="guarded" if preflight_code else "read_only",
    )


@router.get("/api/v1/operations/status")
async def status(account: dict = Depends(require_account)):
    _require_enabled()
    preflight_code = _scheduler_preflight_code()
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        run = conn.execute(
            """SELECT id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                      action_count, triaged_case_count, incident_count, deadline_at, started_at, finished_at, error_code
               FROM web_ops_runs ORDER BY started_at DESC, id DESC LIMIT 1"""
        ).fetchone()
        triage_counts = conn.execute(
            "SELECT sla_status, COUNT(*) FROM web_support_triage WHERE account_id=? GROUP BY sla_status",
            (account_id,),
        ).fetchall()
        incident_count = conn.execute(
            "SELECT COUNT(*) FROM web_ops_incidents WHERE account_id=? AND state NOT IN ('resolved', 'closed')",
            (account_id,),
        ).fetchone()
        recovery_reconciled = conn.execute(
            """SELECT COUNT(*)
               FROM web_ops_incident_observations AS observation
               INNER JOIN web_ops_incidents AS incident ON incident.id=observation.incident_id
               WHERE incident.account_id=? AND observation.observation='recovery_reconciled'""",
            (account_id,),
        ).fetchone()
    counts = {"within_target": 0, "at_risk": 0, "breached": 0, "terminal": 0, "unverified": 0}
    for row in triage_counts:
        if str(row[0]) in counts:
            counts[str(row[0])] = int(row[1])
    return envelope(
        True, "Trạng thái Operations Autopilot của Web account hiện tại.",
        data=_boundary(
            last_run=_run_public(tuple(run)) if run else None,
            account_triage=counts,
            account_open_incidents=int(incident_count[0] or 0) if incident_count else 0,
            incident_recovery_policy=INCIDENT_RECOVERY_PLAYBOOK,
            incident_recovery_required_streak=_incident_recovery_required_streak(),
            incident_recovery_reconciled_count=int(recovery_reconciled[0] or 0) if recovery_reconciled else 0,
            status_truth="observability_and_safe_triage_only",
            scheduler_preflight=preflight_code or "ready",
        ),
        status_name="guarded" if preflight_code else "read_only",
    )


@router.get("/api/v1/operations/incidents")
async def incidents(limit: int = 30, offset: int = 0, account: dict = Depends(require_account)):
    _require_enabled()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset incident Operations không hợp lệ")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, kind, scope_kind, account_id, support_case_id, state, severity, auto_close_eligible,
                      healthy_streak, observation_count, last_failure_at, first_observed_at, last_observed_at,
                      resolved_at, closed_at, revision
               FROM web_ops_incidents WHERE account_id=? ORDER BY last_observed_at DESC, id DESC LIMIT ? OFFSET ?""",
            (str(account["id"]), bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True, "Sự cố Operations liên quan tới Web account hiện tại.",
        data=_boundary(
            items=[_incident_public(tuple(row), staff=False) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


@router.get("/api/v1/support/cases/{case_id}/triage")
async def case_triage(case_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    case_id = _uuid(case_id, label="Mã yêu cầu")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        owner = conn.execute("SELECT id FROM web_support_cases WHERE id=? AND account_id=?", (case_id, str(account["id"]))).fetchone()
        if not owner:
            return envelope(False, "Không tìm thấy yêu cầu thuộc Web account hiện tại.", data=_boundary(), status_name="guarded", error_code="WEB_SUPPORT_CASE_NOT_FOUND")
        row = conn.execute(
            """SELECT case_id, source_revision, policy_version, category, priority, case_state, risk, disposition,
                      required_role, sla_minutes, sla_status, updated_at
               FROM web_support_triage WHERE case_id=? AND account_id=?""",
            (case_id, str(account["id"])),
        ).fetchone()
    if not row:
        return envelope(
            True, "Yêu cầu đang chờ Operations Autopilot phân loại; chưa có kết luận hay phản hồi tự động.",
            data=_boundary(triage=None, classification_state="not_classified_yet"), status_name="read_only",
        )
    return envelope(
        True, "Phân loại Operations chỉ là tư vấn nội bộ, không phải kết quả hoàn tiền hay provider.",
        data=_boundary(triage=_triage_public(tuple(row)), classification_state="classified"), status_name="read_only",
    )


def _require_manager(account: dict) -> str:
    role = require_support_staff(account)
    if role != "manager":
        raise HTTPException(status_code=403, detail="Chỉ Support Manager hoặc Admin Web mới được quyết định approval Operations")
    return role


@router.get("/api/v1/operations/admin/summary")
async def admin_summary(account: dict = Depends(require_account)):
    _require_enabled()
    role = require_support_staff(account)
    approvals_access = "full" if role == "manager" else "manager_only"
    preflight_code = _scheduler_preflight_code()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        latest = conn.execute("SELECT state, started_at, finished_at FROM web_ops_runs ORDER BY started_at DESC, id DESC LIMIT 1").fetchone()
        incidents_open = conn.execute("SELECT COUNT(*) FROM web_ops_incidents WHERE state NOT IN ('resolved', 'closed')").fetchone()
        approval_pending = (
            conn.execute(
                "SELECT COUNT(*) FROM web_ops_approvals WHERE state='awaiting_approval' AND expires_at>?",
                (utc_now(),),
            ).fetchone()
            if role == "manager"
            else None
        )
        triage_rows = conn.execute("SELECT sla_status, COUNT(*) FROM web_support_triage GROUP BY sla_status").fetchall()
        recovery_reconciled = conn.execute(
            "SELECT COUNT(*) FROM web_ops_incident_observations WHERE observation='recovery_reconciled'"
        ).fetchone()
        heartbeat = _heartbeat_snapshot(conn, now=datetime.now(timezone.utc))
        heartbeat_open = conn.execute(
            """SELECT COUNT(*) FROM web_ops_incidents
               WHERE kind=? AND scope_kind=? AND state NOT IN ('resolved', 'closed')""",
            (HEARTBEAT_INCIDENT_KIND, HEARTBEAT_SCOPE_KIND),
        ).fetchone()
    sla = {"within_target": 0, "at_risk": 0, "breached": 0, "terminal": 0, "unverified": 0}
    for row in triage_rows:
        if str(row[0]) in sla:
            sla[str(row[0])] = int(row[1])
    return envelope(
        True, "Tổng quan Operations Autopilot cho Support staff.",
        data=_boundary(
            operator_role=role,
            last_run={"state": str(latest[0]), "started_at": str(latest[1]), "finished_at": str(latest[2]) if latest[2] else None} if latest else None,
            open_incidents=int(incidents_open[0] or 0) if incidents_open else 0,
            # Do not make a hidden Manager queue look empty for an Operator,
            # and do not disclose its volume through a dashboard count.
            pending_approvals=int(approval_pending[0] or 0) if approval_pending else None,
            approvals_access=approvals_access,
            sla=sla,
            incident_recovery_policy=INCIDENT_RECOVERY_PLAYBOOK,
            incident_recovery_required_streak=_incident_recovery_required_streak(),
            incident_recovery_reconciled_count=int(recovery_reconciled[0] or 0) if recovery_reconciled else 0,
            scheduler_heartbeat={
                "state": str(heartbeat["state"]),
                "previous_tick_seen": bool(heartbeat["previous_tick_seen"]),
                "late": bool(heartbeat["late"]),
                "code": str(heartbeat["code"]),
                "open_followups": int(heartbeat_open[0] or 0) if heartbeat_open else 0,
            },
            scheduler_preflight=preflight_code or "ready",
        ),
        status_name="guarded" if preflight_code else "read_only",
    )


@router.get("/api/v1/operations/admin/runs")
async def admin_runs(limit: int = 40, offset: int = 0, account: dict = Depends(require_account)):
    _require_enabled()
    require_support_staff(account)
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset lịch sử Operations không hợp lệ")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                      action_count, triaged_case_count, incident_count, deadline_at, started_at, finished_at, error_code
               FROM web_ops_runs ORDER BY started_at DESC, id DESC LIMIT ? OFFSET ?""",
            (bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Lịch sử Operations không chứa payload hay log nhạy cảm.",
        data=_boundary(
            items=[_run_public(tuple(row)) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


@router.get("/api/v1/operations/admin/incidents")
async def admin_incidents(limit: int = 50, offset: int = 0, account: dict = Depends(require_account)):
    _require_enabled()
    require_support_staff(account)
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset incident Operations quản trị không hợp lệ")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, kind, scope_kind, account_id, support_case_id, state, severity, auto_close_eligible,
                      healthy_streak, observation_count, last_failure_at, first_observed_at, last_observed_at,
                      resolved_at, closed_at, revision
               FROM web_ops_incidents ORDER BY last_observed_at DESC, id DESC LIMIT ? OFFSET ?""",
            (bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Danh sách incident Operations cho Support staff.",
        data=_boundary(
            items=[_incident_public(tuple(row), staff=True) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


@router.get("/api/v1/operations/admin/approvals")
async def admin_approvals(limit: int = 50, offset: int = 0, account: dict = Depends(require_account)):
    _require_enabled()
    _require_manager(account)
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset approval Operations không hợp lệ")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, action_type, support_case_id, incident_id, risk, required_role, state, revision,
                      proposed_at, expires_at, decided_at, decision_code
               FROM web_ops_approvals ORDER BY CASE state WHEN 'awaiting_approval' THEN 0 ELSE 1 END,
               proposed_at DESC, id DESC LIMIT ? OFFSET ?""",
            (bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Approval Operations chỉ là hàng chờ quyết định, chưa chạy hành động ngoài Web.",
        data=_boundary(
            items=[_approval_public(tuple(row)) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


def _decide_approval(
    *,
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
    account: dict,
    next_state: str,
) -> dict[str, Any]:
    _require_enabled()
    _require_manager(account)
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi quyết định approval Operations")
    expected_code = APPROVAL_DECISION_CODES.get(next_state)
    if not expected_code or payload.decision_code != expected_code:
        raise HTTPException(status_code=422, detail="Mã quyết định approval không khớp hành động được phép")
    approval_id = _uuid(approval_id, label="Mã approval")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _json_hash({
        "approval_id": approval_id, "expected_revision": payload.expected_revision,
        "next_state": next_state, "decision_code": payload.decision_code,
    })
    scope = f"web-operations:{account['id']}:approval:{approval_id}:{next_state}"

    def operation(conn: Any) -> dict[str, Any]:
        row = conn.execute(
            """SELECT id, action_type, support_case_id, incident_id, risk, required_role, state, revision,
                      proposed_at, expires_at, decided_at, decision_code
               FROM web_ops_approvals WHERE id=?""",
            (approval_id,),
        ).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy approval Operations.", data=_boundary(), status_name="guarded", error_code="OPS_APPROVAL_NOT_FOUND")
        current = tuple(row)
        if str(current[6]) != "awaiting_approval":
            return envelope(False, "Approval này đã được quyết định trước đó.", data=_boundary(approval=_approval_public(current)), status_name="guarded", error_code="OPS_APPROVAL_ALREADY_DECIDED")
        if str(current[9]) <= utc_now():
            return envelope(False, "Approval đã hết hạn và không thể chạy tiếp.", data=_boundary(approval=_approval_public(current)), status_name="guarded", error_code="OPS_APPROVAL_EXPIRED")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Approval đã có revision mới. Hãy tải lại trước khi quyết định.", data=_boundary(approval=_approval_public(current)), status_name="guarded", error_code="OPS_APPROVAL_CONFLICT")
        now = utc_now()
        next_revision = int(current[7]) + 1
        updated_count = conn.execute(
            """UPDATE web_ops_approvals SET state=?, revision=?, decided_at=?, decided_by_account_id=?, decision_code=?
               WHERE id=? AND state='awaiting_approval' AND revision=?""",
            (next_state, next_revision, now, str(account["id"]), payload.decision_code, approval_id, payload.expected_revision),
        )
        if int(updated_count.rowcount or 0) != 1:
            refreshed = conn.execute(
                """SELECT id, action_type, support_case_id, incident_id, risk, required_role, state, revision,
                          proposed_at, expires_at, decided_at, decision_code
                   FROM web_ops_approvals WHERE id=?""",
                (approval_id,),
            ).fetchone()
            return envelope(
                False,
                "Approval đã có thay đổi đồng thời. Hãy tải lại trước khi quyết định.",
                data=_boundary(approval=_approval_public(tuple(refreshed)) if refreshed else None),
                status_name="guarded",
                error_code="OPS_APPROVAL_CONFLICT",
            )
        conn.execute(
            """INSERT INTO web_ops_approval_events
               (id, approval_id, actor_account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), approval_id, str(account["id"]), f"approval_{next_state}", next_state, next_revision, now),
        )
        _record_audit(
            conn, account_id=str(account["id"]), canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action=f"web.operations.approval.{next_state}", request_id=_request_id(request), target=approval_id,
            detail=f"operations approval recorded only; action:{current[1]}; no external execution",
        )
        updated = conn.execute(
            """SELECT id, action_type, support_case_id, incident_id, risk, required_role, state, revision,
                      proposed_at, expires_at, decided_at, decision_code
               FROM web_ops_approvals WHERE id=?""",
            (approval_id,),
        ).fetchone()
        message = "Đã ghi nhận phê duyệt. Chưa gọi money/provider/job/deploy hay gửi phản hồi khách hàng." if next_state == "approved" else "Đã từ chối approval. Không có hành động ngoài Web được chạy."
        return envelope(True, message, data=_boundary(approval=_approval_public(tuple(updated))), status_name="completed")

    return _idempotent(scope=scope, key=key, request_fingerprint=fingerprint, operation=operation)


@router.post("/api/v1/operations/admin/approvals/{approval_id}/approve")
async def approve(approval_id: str, payload: ApprovalDecisionRequest, request: Request, account: dict = Depends(require_csrf)):
    return _decide_approval(approval_id=approval_id, payload=payload, request=request, account=account, next_state="approved")


@router.post("/api/v1/operations/admin/approvals/{approval_id}/reject")
async def reject(approval_id: str, payload: ApprovalDecisionRequest, request: Request, account: dict = Depends(require_csrf)):
    return _decide_approval(approval_id=approval_id, payload=payload, request=request, account=account, next_state="rejected")
