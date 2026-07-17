"""Private, Web-native Inbox and bounded notification materialization.

The scheduler only creates durable *in-app records* for an allow-listed Web
reminder occurrence.  It never sends Telegram/email/SMS/web-push, calls a
provider or Bot, changes money/jobs/deployments, or advances/completes the
source reminder.  A signed account can later read or dismiss its own record.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_campaign_schedule import campaign_source_hash
from copyfast_db import (
    ensure_copyfast_schema,
    notification_automation_enabled,
    notification_center_enabled,
    read_transaction,
    session_database_path,
    transaction,
    utc_now,
    web_scheduler_persistence_ready,
    workboard_enabled,
)
from copyfast_notification_protocol import (
    KEY_ID_PATTERN,
    NONCE_PATTERN,
    PROTOCOL_VERSION,
    TICK_PATH,
    canonical_json,
    sign_tick,
    valid_request_id,
)


router = APIRouter(tags=["Web Notification Center"])

POLICY_VERSION = 2
TICK_MAX_BODY_BYTES = 8 * 1024
TICK_MAX_CLOCK_SKEW_SECONDS = 300
TICK_NONCE_TTL_SECONDS = 600
TICK_LEASE_NAME = "web_notification_center_tick"
MAX_TICK_SECONDS = 25
MAX_ACTIONS_PER_RUN = 20
MAX_CANDIDATES_PER_RUN = 100
# Tick writes use a deadline-aware connection rather than the general 30-second
# application transaction.  Keep a little time for the scheduler to close a
# started receipt after the last materialization attempt.
TICK_DB_DEADLINE_MARGIN_SECONDS = 0.05
TICK_FINISH_RESERVE_SECONDS = 0.25
TICK_MIN_DB_TIMEOUT_SECONDS = 0.001
# Keep source reads bounded, but let a single account contribute only enough
# candidates to consume one safe run.  The final fair selector below then
# gives each represented account a turn before it takes a second item from an
# account.  This avoids one long-overdue Inbox starving everyone else.
FAIR_CANDIDATES_PER_ACCOUNT = MAX_ACTIONS_PER_RUN
MAX_SOURCE_CANDIDATES_PER_RUN = MAX_CANDIDATES_PER_RUN * 3
MAX_ITEMS_PER_ACCOUNT = 500
DISMISSED_RETENTION_DAYS = 30
# An unread Inbox record is still a private Web record after this threshold.
# The scheduler may only raise its local urgency metadata; it never creates a
# new record, mutates the originating reminder/intent or delivers externally.
OVERDUE_WARNING_AFTER = timedelta(hours=24)
# Scheduler receipts are audit metadata, not a permanent event ledger. Keep
# terminal unreferenced rows for a bounded window, then trim only a small
# batch while the scheduler already owns its lease. This never deletes an
# Inbox item, dedupe, nonce or active replay/lease state.
NOTIFICATION_RUN_RETENTION_DAYS = 30
NOTIFICATION_RUN_PRUNE_BATCH_SIZE = 50
MIN_NOTIFICATION_RUN_RETENTION_DAYS = 7
MAX_NOTIFICATION_RUN_RETENTION_DAYS = 3650
MIN_NOTIFICATION_RUN_PRUNE_BATCH_SIZE = 1
MAX_NOTIFICATION_RUN_PRUNE_BATCH_SIZE = 100
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
TOPOLOGY_SQLITE_SINGLE_REPLICA = "sqlite_single_replica"
REPLICA_COUNT_ENV_NAMES = ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
SIGNATURE_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
ITEM_STATES = frozenset({"unread", "read", "dismissed"})
ITEM_KINDS = frozenset({"reminder_due", "workboard_schedule_due", "campaign_schedule_due"})
SEVERITIES = frozenset({"warning", "urgent"})


class _TickGuarded(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _TickLeaseLost(RuntimeError):
    """Raised before a stale Notification scheduler writes another row."""


class _TickDeadlineExceeded(RuntimeError):
    """Raised when an isolated tick cannot obtain SQLite before its budget."""


def _tick_db_timeout_seconds(*, deadline: datetime, reserve_seconds: float = 0.0) -> float:
    """Return the only SQLite wait budget permitted for a scheduler operation.

    The normal Web transaction intentionally permits a 30-second busy wait for
    interactive work.  An Inbox tick promises a much smaller (at most
    25-second) wall-clock run, so it must never borrow that general timeout.
    The tiny margin covers rollback/response bookkeeping after SQLite returns.
    """
    try:
        remaining = (deadline - datetime.now(timezone.utc)).total_seconds() - max(0.0, reserve_seconds)
    except (TypeError, ValueError, OverflowError):
        remaining = 0.0
    timeout = remaining - TICK_DB_DEADLINE_MARGIN_SECONDS
    if timeout <= 0:
        raise _TickDeadlineExceeded()
    return max(TICK_MIN_DB_TIMEOUT_SECONDS, min(float(timeout), float(MAX_TICK_SECONDS)))


def _sqlite_busy(exc: sqlite3.OperationalError) -> bool:
    """Keep only contention failures on the guarded scheduler path."""
    message = str(exc).strip().lower()
    return "database is locked" in message or "database is busy" in message or "database schema is locked" in message


@contextmanager
def _tick_sqlite_transaction(
    *, deadline: datetime, writable: bool, reserve_seconds: float = 0.0,
):
    """Open a SQLite transaction bounded by the signed tick's real deadline.

    On write contention this deliberately raises ``_TickDeadlineExceeded``
    instead of falling back to the service-wide 30-second transaction helper.
    A failed acquisition creates no nonce, lease, dedupe tombstone or Inbox
    item.  A post-start failure leaves the existing lease intact, which fences
    retries until normal lease expiry rather than risking duplicate delivery.
    """
    timeout = _tick_db_timeout_seconds(deadline=deadline, reserve_seconds=reserve_seconds)
    path = session_database_path()
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(path, timeout=timeout)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={max(1, int(timeout * 1000))}")
        if writable:
            conn.execute("BEGIN IMMEDIATE")
        else:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
        # A lock may have been released immediately before BEGIN.  Do not use
        # the now-expired transaction merely because acquisition succeeded.
        _tick_db_timeout_seconds(deadline=deadline, reserve_seconds=reserve_seconds)
        yield conn
        if writable:
            commit_timeout = _tick_db_timeout_seconds(deadline=deadline, reserve_seconds=reserve_seconds)
            conn.execute(f"PRAGMA busy_timeout={max(1, int(commit_timeout * 1000))}")
            conn.commit()
        else:
            conn.rollback()
    except _TickDeadlineExceeded:
        if conn is not None:
            conn.rollback()
        raise
    except sqlite3.OperationalError as exc:
        if conn is not None:
            conn.rollback()
        if _sqlite_busy(exc):
            raise _TickDeadlineExceeded() from None
        raise
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()


@contextmanager
def _tick_write_transaction(*, deadline: datetime, reserve_seconds: float = 0.0):
    """Deadline-aware transaction for scheduler-owned local metadata writes."""
    with _tick_sqlite_transaction(deadline=deadline, writable=True, reserve_seconds=reserve_seconds) as conn:
        yield conn


@contextmanager
def _tick_read_transaction(*, deadline: datetime, reserve_seconds: float = 0.0):
    """Deadline-aware source snapshot read for the bounded scheduler run."""
    with _tick_sqlite_transaction(deadline=deadline, writable=False, reserve_seconds=reserve_seconds) as conn:
        yield conn


def _enabled() -> bool:
    return notification_center_enabled()


def _automation_enabled() -> bool:
    return notification_automation_enabled()


def _production_like() -> bool:
    values = (
        os.environ.get("APP_ENV", ""),
        os.environ.get("ENVIRONMENT", ""),
        os.environ.get("RAILWAY_ENVIRONMENT", ""),
    )
    return any(value.strip().lower() in {"production", "prod", "live"} for value in values if value)


def _replica_attestation_required() -> bool | None:
    """Return whether an explicit `=1` replica attestation is mandatory.

    Local/test SQLite remains usable without Railway metadata. Production-like
    environments always attest a single replica; a local/test override may
    request stricter attestation, but may never relax the production guard. A
    topology string alone is not proof that SQLite nonce/lease state is safe
    under horizontal scaling.
    """
    raw = os.environ.get("WEBAPP_NOTIFICATION_REQUIRE_REPLICA_ATTESTATION", "").strip().lower()
    if _production_like():
        # ``false`` is useful for isolated local/test fixtures only.  Letting
        # it bypass production would turn a typo or copied development value
        # into unsafe multi-replica SQLite scheduling.
        if raw and raw not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
            return None
        return True
    if not raw:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def _configured_int(name: str, *, default: int, minimum: int, maximum: int) -> int | None:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if minimum <= value <= maximum else None


def _tick_limits() -> tuple[tuple[int, int] | None, str | None]:
    run_seconds = _configured_int(
        "WEBAPP_NOTIFICATION_MAX_RUN_SECONDS", default=20, minimum=1, maximum=MAX_TICK_SECONDS,
    )
    if run_seconds is None:
        return None, "NOTIFY_MAX_RUN_SECONDS_UNVERIFIED"
    max_actions = _configured_int(
        "WEBAPP_NOTIFICATION_MAX_ACTIONS_PER_RUN", default=20, minimum=1, maximum=MAX_ACTIONS_PER_RUN,
    )
    if max_actions is None:
        return None, "NOTIFY_MAX_ACTIONS_UNVERIFIED"
    return (run_seconds, max_actions), None


def _run_retention_limits() -> tuple[int, int] | None:
    """Return bounded terminal-receipt retention settings, or disable prune.

    Retention is strictly best effort. Unlike run/action limits, a malformed
    retention variable must not make a signed Inbox tick fail or re-run; it
    only leaves old audit receipts in place until an operator fixes config.
    """

    retention_days = _configured_int(
        "WEBAPP_NOTIFICATION_RUN_RETENTION_DAYS",
        default=NOTIFICATION_RUN_RETENTION_DAYS,
        minimum=MIN_NOTIFICATION_RUN_RETENTION_DAYS,
        maximum=MAX_NOTIFICATION_RUN_RETENTION_DAYS,
    )
    batch_size = _configured_int(
        "WEBAPP_NOTIFICATION_RUN_PRUNE_BATCH_SIZE",
        default=NOTIFICATION_RUN_PRUNE_BATCH_SIZE,
        minimum=MIN_NOTIFICATION_RUN_PRUNE_BATCH_SIZE,
        maximum=MAX_NOTIFICATION_RUN_PRUNE_BATCH_SIZE,
    )
    if retention_days is None or batch_size is None:
        return None
    return retention_days, batch_size


def _scheduler_preflight_code() -> str | None:
    limits, limit_code = _tick_limits()
    if limit_code or limits is None:
        return limit_code or "NOTIFY_LIMITS_UNVERIFIED"
    if not web_scheduler_persistence_ready():
        return "NOTIFY_PERSISTENT_STORE_UNVERIFIED"
    topology = os.environ.get("WEBAPP_NOTIFICATION_TOPOLOGY", "").strip().lower()
    if topology != TOPOLOGY_SQLITE_SINGLE_REPLICA:
        return "NOTIFY_TOPOLOGY_UNVERIFIED"
    require_attestation = _replica_attestation_required()
    if require_attestation is None:
        return "NOTIFY_REPLICA_COUNT_UNVERIFIED"
    attested = False
    for name in REPLICA_COUNT_ENV_NAMES:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        attested = True
        try:
            replicas = int(raw)
        except ValueError:
            return "NOTIFY_REPLICA_COUNT_UNVERIFIED"
        if replicas != 1:
            return "NOTIFY_MULTI_REPLICA_BLOCKED"
    if require_attestation and not attested:
        return "NOTIFY_REPLICA_COUNT_UNVERIFIED"
    return None


def _boundary(**extra: Any) -> dict[str, Any]:
    if not _enabled():
        preflight = "NOTIFY_CENTER_DISABLED"
    elif not _automation_enabled():
        preflight = "NOTIFY_AUTOMATION_DISABLED"
    else:
        preflight = _scheduler_preflight_code()
    return {
        "execution": "web_native_in_app_record_materialization_and_urgency_maintenance_only",
        "data_origin": "signed_web_records_and_authenticated_notification_scheduler_only",
        "policy_version": POLICY_VERSION,
        "notification_center_enabled": _enabled(),
        "notification_automation_enabled": _automation_enabled(),
        "scheduler_topology": os.environ.get("WEBAPP_NOTIFICATION_TOPOLOGY", "").strip() or "unverified",
        "scheduler_ready": preflight is None,
        "in_app_record_created": False,
        "in_app_urgency_maintained": False,
        "urgency_escalation_count": 0,
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


def _require_center() -> None:
    if not _enabled():
        raise HTTPException(status_code=503, detail="Inbox Automation đang tắt an toàn. WEBAPP_NOTIFICATION_CENTER_ENABLED chưa được bật.")


def _tick_secret() -> str:
    value = os.environ.get("WEBAPP_NOTIFICATION_TICK_SECRET", "")
    if len(value.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="Inbox Automation chưa có scheduler secret hợp lệ.")
    return value


def _tick_key_id() -> str:
    value = os.environ.get("WEBAPP_NOTIFICATION_TICK_KEY_ID", "primary").strip().lower()
    if not KEY_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=503, detail="Cấu hình Inbox Automation chưa hợp lệ.")
    return value


def _as_utc(value: Any) -> datetime:
    raw = str(value or "").strip()
    if not raw or len(raw) > 80:
        raise ValueError("timestamp invalid")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError("timestamp timezone missing")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _opaque_uuid(value: Any) -> bool:
    """Accept only the canonical opaque IDs created by the Web app.

    Scheduler rows are local metadata, but a corrupted identifier must never
    be used to look up a different source.  The owner-facing workflow creates
    lower-case UUIDs, so anything else is intentionally fail-closed.
    """
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except (TypeError, ValueError, AttributeError):
        return False


def _schedule_intent_validation_code(row: tuple[Any, ...], *, prefix: str) -> str | None:
    """Return a non-sensitive guard code for malformed schedule metadata.

    The Notification scheduler normally receives only the eight opaque intent
    coordinates plus a SQLite rowid fence.  Validate those coordinates before
    attempting a source lookup: an invalid timestamp or digest otherwise
    cannot become due and would remain active forever.  No source title,
    content, URL, account email, provider or payment detail is included in the
    result.
    """
    try:
        if len(row) < 8:
            return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
        intent_id, account_id, source_id, source_revision, source_hash, trigger_at, revision, state = row[:8]
        if str(state) != "active":
            return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
        if not all(_opaque_uuid(value) for value in (intent_id, account_id, source_id)):
            return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
        if type(source_revision) is not int or source_revision < 1:
            return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
        if type(revision) is not int or revision < 1:
            return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
        if not isinstance(source_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_hash):
            return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
        if not isinstance(trigger_at, str) or _time_text(_as_utc(trigger_at)) != trigger_at:
            return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
    except (IndexError, TypeError, ValueError, OverflowError):
        return f"{prefix}_SCHEDULE_SOURCE_UNVERIFIED"
    return None


def _time_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")


def _nonce_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key Inbox không hợp lệ")
    return key


def _safe_public_message(code: str) -> str:
    messages = {
        "NOTIFY_CENTER_DISABLED": "Inbox Automation đang tắt an toàn; scheduler không tạo bản ghi mới.",
        "NOTIFY_AUTOMATION_DISABLED": "Inbox Automation đang ở chế độ quan sát; scheduler không tạo bản ghi mới.",
        "NOTIFY_TICK_REPLAYED": "Lần quét Inbox này đã được ghi nhận trước đó; không chạy lại.",
        "NOTIFY_TICK_LEASE_HELD": "Một lần quét Inbox khác đang chạy; không tạo bản ghi trùng lặp.",
        "NOTIFY_TICK_LEASE_LOST": "Quyền chạy Inbox đã đổi; lần quét cũ không được ghi thêm dữ liệu.",
        "NOTIFY_TICK_DEADLINE_REACHED": "Inbox scheduler đã dừng an toàn vì SQLite không sẵn sàng trong giới hạn thời gian của lần quét.",
        "NOTIFY_PERSISTENT_STORE_UNVERIFIED": "Inbox scheduler đang bị khóa vì SQLite nonce/lease chưa được xác nhận trên persistent volume.",
        "NOTIFY_TOPOLOGY_UNVERIFIED": "Inbox scheduler đang bị khóa cho đến khi topology SQLite một replica được xác nhận.",
        "NOTIFY_REPLICA_COUNT_UNVERIFIED": "Inbox scheduler đang bị khóa vì cấu hình replica chưa hợp lệ.",
        "NOTIFY_MULTI_REPLICA_BLOCKED": "Inbox scheduler không chạy với nhiều replica khi state vẫn ở SQLite.",
        "NOTIFY_MAX_RUN_SECONDS_UNVERIFIED": "Inbox scheduler đang bị khóa vì giới hạn thời gian chạy chưa hợp lệ.",
        "NOTIFY_MAX_ACTIONS_UNVERIFIED": "Inbox scheduler đang bị khóa vì giới hạn bản ghi mỗi lần quét chưa hợp lệ.",
        "NOTIFY_ACTION_BUDGET_REACHED": "Inbox scheduler đã chạm giới hạn bản ghi an toàn của lần quét này.",
        "NOTIFY_ACCOUNT_CAP_REACHED": "Một hoặc nhiều Inbox Web đã chạm giới hạn lưu trữ an toàn; không tạo thêm bản ghi.",
        "WORKBOARD_SCHEDULE_SOURCE_CHANGED": "Lịch nhắc Workboard đã được giữ lại vì source revision hoặc snapshot đã thay đổi; cần owner xác nhận lại.",
        "WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED": "Lịch nhắc Workboard chưa có source snapshot xác minh nên không materialize Inbox record.",
        "WORKBOARD_SCHEDULE_WORKBOARD_DISABLED": "Workboard đang tắt an toàn; lịch nhắc không materialize Inbox record.",
        "CAMPAIGN_SCHEDULE_SOURCE_CHANGED": "Lịch nhắc Campaign đã được giữ lại vì source revision hoặc snapshot đã thay đổi; cần owner xác nhận lại.",
        "CAMPAIGN_SCHEDULE_SOURCE_UNVERIFIED": "Lịch nhắc Campaign chưa có source snapshot xác minh nên không materialize Inbox record.",
    }
    return messages.get(code, "Inbox Automation đã giữ trạng thái bảo vệ an toàn.")


def _require_json_header(request: Request) -> None:
    values = request.headers.getlist("content-type")
    if len(values) != 1 or values[0].split(";", 1)[0].strip().lower() != "application/json":
        raise HTTPException(status_code=415, detail="Yêu cầu Inbox nội bộ phải dùng JSON hợp lệ")


def _single_header(request: Request, name: str) -> str:
    values = request.headers.getlist(name)
    if len(values) != 1:
        raise HTTPException(status_code=401, detail="Xác thực Inbox nội bộ không hợp lệ")
    value = values[0].strip()
    if not value:
        raise HTTPException(status_code=401, detail="Xác thực Inbox nội bộ không hợp lệ")
    return value


def _tick_headers(request: Request, body: bytes) -> tuple[str, str, str, str, datetime]:
    _require_json_header(request)
    timestamp = _single_header(request, "x-notify-timestamp")
    nonce = _single_header(request, "x-notify-nonce")
    request_id = _single_header(request, "x-notify-request-id")
    signature = _single_header(request, "x-notify-signature").lower()
    key_id = _single_header(request, "x-notify-key-id").lower()
    if key_id != _tick_key_id() or not NONCE_PATTERN.fullmatch(nonce) or not valid_request_id(request_id) or not SIGNATURE_PATTERN.fullmatch(signature):
        raise HTTPException(status_code=401, detail="Xác thực Inbox nội bộ không hợp lệ")
    try:
        timestamp_value = _as_utc(timestamp)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Xác thực Inbox nội bộ không hợp lệ") from None
    if abs((datetime.now(timezone.utc) - timestamp_value).total_seconds()) > TICK_MAX_CLOCK_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="Xác thực Inbox nội bộ không hợp lệ")
    expected = sign_tick(
        secret=_tick_secret(), timestamp=timestamp, nonce=nonce, request_id=request_id, key_id=key_id, body=body,
    )
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Xác thực Inbox nội bộ không hợp lệ")
    return timestamp, nonce, request_id, key_id, timestamp_value


def _tick_payload(body: bytes, *, timestamp: str) -> dict[str, Any]:
    if not body or len(body) > TICK_MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Dữ liệu Inbox nội bộ vượt giới hạn an toàn")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="Dữ liệu Inbox nội bộ không hợp lệ") from None
    if (
        not isinstance(parsed, dict)
        or set(parsed) != {"protocol_version", "trigger", "requested_at"}
        or parsed.get("protocol_version") != PROTOCOL_VERSION
        or parsed.get("trigger") != "railway_cron"
        or parsed.get("requested_at") != timestamp
        or canonical_json(parsed) != body
    ):
        raise HTTPException(status_code=422, detail="Dữ liệu Inbox nội bộ không hợp lệ")
    return parsed


def _lease_current(conn: Any, *, run_id: str, fence_token: int, now: str) -> bool:
    row = conn.execute(
        "SELECT owner_run_id, fence_token, expires_at FROM web_notification_leases WHERE name=?",
        (TICK_LEASE_NAME,),
    ).fetchone()
    return bool(row and str(row[0]) == run_id and int(row[1]) == fence_token and str(row[2]) > now)


def _record_guarded_tick(
    *, request_id: str, key_id: str, nonce: str, timestamp: datetime, body: bytes, guarded_code: str,
    deadline: datetime,
) -> str:
    """Persist a compact replay receipt without acquiring the scheduler lease."""
    # Schema ownership stays with app startup/migrations.  A scheduler tick
    # must not trigger an unbounded DDL transaction while it is trying to make
    # a short, signed decision under its own wall-clock deadline.
    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
    now = _time_text(now_dt)
    run_id = str(uuid.uuid4())
    with _tick_write_transaction(deadline=deadline) as conn:
        conn.execute("DELETE FROM web_notification_nonces WHERE expires_at<?", (now,))
        if conn.execute("SELECT id FROM web_notification_runs WHERE request_id=?", (request_id,)).fetchone():
            raise _TickGuarded("NOTIFY_TICK_REPLAYED")
        try:
            conn.execute(
                """INSERT INTO web_notification_nonces (nonce_hash, request_id, key_id, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (_nonce_hash(nonce), request_id, key_id, now, _time_text(now_dt + timedelta(seconds=TICK_NONCE_TTL_SECONDS))),
            )
        except sqlite3.IntegrityError as exc:
            raise _TickGuarded("NOTIFY_TICK_REPLAYED") from exc
        conn.execute(
            """INSERT INTO web_notification_runs
               (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                action_count, candidate_count, deadline_at, started_at, finished_at, error_code, receipt_json)
               VALUES (?, ?, 'railway_cron', ?, 'guarded', 0, ?, ?, 0, 0, ?, ?, ?, ?, ?)""",
            (
                run_id, request_id, _time_text(timestamp)[:16], POLICY_VERSION, hashlib.sha256(body).hexdigest(),
                now, now, now, guarded_code,
                json.dumps({"request_id": request_id, "guarded_code": guarded_code}, separators=(",", ":")),
            ),
        )
    return run_id


def _start_run(
    *, request_id: str, key_id: str, nonce: str, timestamp: datetime, body: bytes, run_seconds: int,
    deadline: datetime,
) -> tuple[str, int, datetime, str | None]:
    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
    now = _time_text(now_dt)
    lease_expiry = now_dt + timedelta(seconds=max(60, run_seconds + 30))
    run_id = str(uuid.uuid4())
    try:
        with _tick_write_transaction(deadline=deadline) as conn:
            conn.execute("DELETE FROM web_notification_nonces WHERE expires_at<?", (now,))
            if conn.execute("SELECT id FROM web_notification_runs WHERE request_id=?", (request_id,)).fetchone():
                raise _TickGuarded("NOTIFY_TICK_REPLAYED")
            try:
                conn.execute(
                    """INSERT INTO web_notification_nonces (nonce_hash, request_id, key_id, created_at, expires_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (_nonce_hash(nonce), request_id, key_id, now, _time_text(now_dt + timedelta(seconds=TICK_NONCE_TTL_SECONDS))),
                )
            except sqlite3.IntegrityError as exc:
                raise _TickGuarded("NOTIFY_TICK_REPLAYED") from exc
            current = conn.execute(
                "SELECT owner_run_id, fence_token, expires_at FROM web_notification_leases WHERE name=?",
                (TICK_LEASE_NAME,),
            ).fetchone()
            if current and str(current[2]) > now:
                fence = int(current[1])
                conn.execute(
                    """INSERT INTO web_notification_runs
                       (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                        action_count, candidate_count, deadline_at, started_at, finished_at, error_code, receipt_json)
                       VALUES (?, ?, 'railway_cron', ?, 'guarded', ?, ?, ?, 0, 0, ?, ?, ?, ?, ?)""",
                    (
                        run_id, request_id, _time_text(timestamp)[:16], fence, POLICY_VERSION,
                        hashlib.sha256(body).hexdigest(), _time_text(deadline), now, now, "NOTIFY_TICK_LEASE_HELD",
                        json.dumps({"request_id": request_id, "guarded_code": "NOTIFY_TICK_LEASE_HELD"}, separators=(",", ":")),
                    ),
                )
                return run_id, fence, deadline, "NOTIFY_TICK_LEASE_HELD"
            fence = int(current[1]) + 1 if current else 1
            if current:
                # A prior process may have died after it marked its run
                # `started`. Once its lease has expired, close that stale
                # receipt before fencing it out so it can never look alive
                # forever in an audit or future operator view.
                conn.execute(
                    """UPDATE web_notification_runs
                       SET state='guarded', finished_at=?, error_code=?, receipt_json=?
                       WHERE id=? AND fence_token=? AND state='started' AND finished_at IS NULL""",
                    (
                        now, "NOTIFY_TICK_LEASE_LOST",
                        json.dumps({"guarded_code": "NOTIFY_TICK_LEASE_LOST", "reconciled_by": "expired_lease"}, separators=(",", ":")),
                        str(current[0]), int(current[1]),
                    ),
                )
                conn.execute(
                    """UPDATE web_notification_leases SET owner_run_id=?, fence_token=?, acquired_at=?, expires_at=?, updated_at=?
                       WHERE name=?""",
                    (run_id, fence, now, _time_text(lease_expiry), now, TICK_LEASE_NAME),
                )
            else:
                conn.execute(
                    """INSERT INTO web_notification_leases (name, owner_run_id, fence_token, acquired_at, expires_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (TICK_LEASE_NAME, run_id, fence, now, _time_text(lease_expiry), now),
                )
            conn.execute(
                """INSERT INTO web_notification_runs
                   (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                    action_count, candidate_count, deadline_at, started_at, receipt_json)
                   VALUES (?, ?, 'railway_cron', ?, 'started', ?, ?, ?, 0, 0, ?, ?, '{}')""",
                (run_id, request_id, _time_text(timestamp)[:16], fence, POLICY_VERSION, hashlib.sha256(body).hexdigest(), _time_text(deadline), now),
            )
    except _TickGuarded:
        raise
    return run_id, fence, deadline, None


def _finish_run(
    *, run_id: str, fence_token: int, state: str, action_count: int, candidate_count: int,
    receipt: dict[str, Any], deadline: datetime, error_code: str = "",
) -> bool:
    now = utc_now()
    with _tick_write_transaction(deadline=deadline) as conn:
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now):
            guarded_receipt = {
                "request_id": str(receipt.get("request_id") or ""),
                "guarded_code": "NOTIFY_TICK_LEASE_LOST",
                "action_count": max(0, int(action_count)),
                "candidate_count": max(0, int(candidate_count)),
            }
            conn.execute(
                """UPDATE web_notification_runs SET state='guarded', finished_at=?, error_code=?, receipt_json=?
                   WHERE id=? AND fence_token=? AND state='started'""",
                (
                    now, "NOTIFY_TICK_LEASE_LOST",
                    json.dumps(guarded_receipt, separators=(",", ":")),
                    run_id, fence_token,
                ),
            )
            return False
        updated = conn.execute(
            """UPDATE web_notification_runs SET state=?, action_count=?, candidate_count=?, finished_at=?, error_code=?, receipt_json=?
               WHERE id=? AND fence_token=? AND state='started'""",
            (
                state, action_count, candidate_count, now, error_code[:80] or None,
                json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")), run_id, fence_token,
            ),
        )
        conn.execute(
            "DELETE FROM web_notification_leases WHERE name=? AND owner_run_id=? AND fence_token=?",
            (TICK_LEASE_NAME, run_id, fence_token),
        )
        return int(updated.rowcount or 0) == 1


def _prune_finished_run_history(
    conn: Any,
    *,
    current_run_id: str,
    deadline: datetime,
) -> int:
    """Best-effort bounded cleanup of terminal, unreferenced scheduler rows.

    This runs only while the active tick already owns its fence, and only if
    there is still time reserved to finish the current receipt.  It never
    changes an Inbox row, dedupe tombstone, nonce, lease or replay receipt.
    A savepoint makes an unexpected prune error a no-op instead of turning a
    successful materialization into a failed scheduler run.
    """

    limits = _run_retention_limits()
    if limits is None:
        return 0
    try:
        _tick_db_timeout_seconds(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS)
    except _TickDeadlineExceeded:
        return 0
    retention_days, batch_size = limits
    cutoff = _time_text(datetime.now(timezone.utc) - timedelta(days=retention_days))
    savepoint_open = False
    try:
        conn.execute("SAVEPOINT web_notification_run_retention")
        savepoint_open = True
        # Do not compact any live/leased/current row, guarded replay receipt,
        # or run that is still the provenance for an Inbox item. Selecting IDs
        # first makes both the step and parent deletes demonstrably bounded.
        rows = conn.execute(
            """SELECT run.id
               FROM web_notification_runs AS run
               WHERE run.id!=?
                 AND run.state IN ('completed', 'failed', 'guarded')
                 AND run.finished_at IS NOT NULL
                 AND run.finished_at<?
                 AND COALESCE(run.error_code, '')!='NOTIFY_TICK_REPLAYED'
                 AND NOT EXISTS (
                     SELECT 1 FROM web_notification_leases AS lease
                     WHERE lease.owner_run_id=run.id
                 )
                 AND NOT EXISTS (
                     SELECT 1 FROM web_notification_items AS item
                     WHERE item.created_by_run_id=run.id
                 )
               ORDER BY run.finished_at ASC, run.id ASC
               LIMIT ?""",
            (current_run_id, cutoff, batch_size),
        ).fetchall()
        run_ids = [str(row[0]) for row in rows if row and isinstance(row[0], str)]
        if not run_ids:
            conn.execute("RELEASE SAVEPOINT web_notification_run_retention")
            return 0
        placeholders = ",".join("?" for _ in run_ids)
        # Re-apply every safety predicate on the parent delete. The write lock
        # makes a race unlikely, but this retains the no-active/no-provenance
        # invariant even if the helper is reused from another transaction.
        conn.execute(
            f"DELETE FROM web_notification_run_steps WHERE run_id IN ({placeholders})",
            run_ids,
        )
        deleted = conn.execute(
            f"""DELETE FROM web_notification_runs
                WHERE id IN ({placeholders})
                  AND id!=?
                  AND state IN ('completed', 'failed', 'guarded')
                  AND finished_at IS NOT NULL
                  AND finished_at<?
                  AND COALESCE(error_code, '')!='NOTIFY_TICK_REPLAYED'
                  AND NOT EXISTS (
                      SELECT 1 FROM web_notification_leases AS lease
                      WHERE lease.owner_run_id=web_notification_runs.id
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM web_notification_items AS item
                      WHERE item.created_by_run_id=web_notification_runs.id
                  )""",
            [*run_ids, current_run_id, cutoff],
        )
        conn.execute("RELEASE SAVEPOINT web_notification_run_retention")
        return max(0, int(deleted.rowcount or 0))
    except (sqlite3.Error, TypeError, ValueError, OverflowError):
        if savepoint_open:
            try:
                conn.execute("ROLLBACK TO SAVEPOINT web_notification_run_retention")
                conn.execute("RELEASE SAVEPOINT web_notification_run_retention")
            except sqlite3.Error:
                # The outer scheduler transaction remains the authority for
                # receipt completion. Never surface a cleanup-only failure.
                pass
        return 0


def _insert_step(
    conn: Any,
    *,
    run_id: str,
    sequence: int,
    state: str,
    input_hash: str,
    result_code: str,
    playbook: str = "private_in_app_record_materialization",
) -> None:
    now = utc_now()
    conn.execute(
        """INSERT INTO web_notification_run_steps
           (id, run_id, sequence, playbook, state, idempotency_key, input_hash, result_code, started_at, finished_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), run_id, sequence, playbook, state,
            f"notification-step:{run_id}:{sequence}:{playbook}", input_hash, result_code, now, now,
        ),
    )


def _reminder_snapshots(now: str, *, deadline: datetime) -> list[tuple[Any, ...]]:
    with _tick_read_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        rows = conn.execute(
            """SELECT id, account_id, state, revision, next_run_at
               FROM (
                   SELECT reminder.id AS id, reminder.account_id AS account_id,
                          reminder.state AS state, reminder.revision AS revision,
                          reminder.next_run_at AS next_run_at,
                          ROW_NUMBER() OVER (
                              PARTITION BY reminder.account_id
                              ORDER BY reminder.next_run_at ASC, reminder.id ASC
                          ) AS account_rank
                   FROM web_memory_reminders AS reminder
                   WHERE reminder.state='active' AND reminder.next_run_at<=?
                     AND NOT EXISTS (
                        SELECT 1 FROM web_notification_dedupes AS dedupe
                        WHERE dedupe.account_id=reminder.account_id
                          AND dedupe.source_kind='memory_reminder'
                          AND dedupe.source_id=reminder.id
                          AND dedupe.source_revision=reminder.revision
                          AND dedupe.occurrence_at=reminder.next_run_at
                     )
               ) AS ranked
               WHERE account_rank<=?
               ORDER BY next_run_at ASC, id ASC LIMIT ?""",
             (now, FAIR_CANDIDATES_PER_ACCOUNT, MAX_SOURCE_CANDIDATES_PER_RUN),
        ).fetchall()
    return [tuple(row) for row in rows]


def _workboard_schedule_snapshots(now: str, *, deadline: datetime) -> list[tuple[Any, ...]]:
    """Return only opaque, due Workboard intent coordinates.

    The scheduler deliberately does not read the card's title, description,
    checklist or references here.  It gets the immutable snapshot hash only
    so dispatch can fail closed if the owner changed the Workboard source.
    """
    with _tick_read_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        rows = conn.execute(
            """SELECT id, account_id, item_id, source_revision, source_snapshot_hash,
                      trigger_at, revision, state, intent_rowid
               FROM (
                   SELECT intent.id AS id, intent.account_id AS account_id,
                          intent.item_id AS item_id, intent.source_revision AS source_revision,
                          intent.source_snapshot_hash AS source_snapshot_hash,
                          intent.trigger_at AS trigger_at, intent.revision AS revision,
                          intent.state AS state, intent.rowid AS intent_rowid,
                          ROW_NUMBER() OVER (
                              PARTITION BY intent.account_id
                              ORDER BY intent.trigger_at ASC, intent.id ASC
                          ) AS account_rank
                   FROM web_workboard_schedule_intents AS intent
                   WHERE intent.state='active'
                     AND (
                        (
                            intent.trigger_at<=?
                            AND NOT EXISTS (
                                SELECT 1 FROM web_notification_dedupes AS dedupe
                                WHERE dedupe.account_id=intent.account_id
                                  AND dedupe.source_kind='workboard_schedule_intent'
                                  AND dedupe.source_id=intent.id
                                  AND dedupe.source_revision=intent.revision
                                  AND dedupe.occurrence_at=intent.trigger_at
                            )
                        )
                        OR typeof(intent.id)!='text' OR length(intent.id)!=36
                        OR length(replace(intent.id, '-', ''))!=32
                        OR replace(intent.id, '-', '') GLOB '*[^0-9A-Fa-f]*'
                        OR typeof(intent.account_id)!='text' OR length(intent.account_id)!=36
                        OR length(replace(intent.account_id, '-', ''))!=32
                        OR replace(intent.account_id, '-', '') GLOB '*[^0-9A-Fa-f]*'
                        OR typeof(intent.item_id)!='text' OR length(intent.item_id)!=36
                        OR length(replace(intent.item_id, '-', ''))!=32
                        OR replace(intent.item_id, '-', '') GLOB '*[^0-9A-Fa-f]*'
                        OR typeof(intent.source_revision)!='integer' OR intent.source_revision<1
                        OR typeof(intent.revision)!='integer' OR intent.revision<1
                        OR typeof(intent.source_snapshot_hash)!='text'
                        OR length(intent.source_snapshot_hash)!=64
                        OR intent.source_snapshot_hash GLOB '*[^0-9a-f]*'
                        OR typeof(intent.trigger_at)!='text' OR length(intent.trigger_at)!=25
                        OR substr(intent.trigger_at, 11, 1)!='T'
                        OR substr(intent.trigger_at, 20, 1)!='+'
                        OR substr(intent.trigger_at, 23, 1)!=':'
                        OR datetime(intent.trigger_at) IS NULL
                     )
               ) AS ranked
               WHERE account_rank<=?
               ORDER BY trigger_at ASC, id ASC LIMIT ?""",
            (now, FAIR_CANDIDATES_PER_ACCOUNT, MAX_SOURCE_CANDIDATES_PER_RUN),
        ).fetchall()
    return [tuple(row) for row in rows]


def _campaign_schedule_snapshots(now: str, *, deadline: datetime) -> list[tuple[Any, ...]]:
    """Return only opaque due Campaign intent coordinates.

    A Campaign title, destination URL, review note, publishing state, provider
    handle and canonical Bot data stay out of the scheduler query.  The
    source digest is rechecked only to fail closed if the owner changed the
    Web plan after explicitly requesting this one in-app record.
    """
    with _tick_read_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        rows = conn.execute(
            """SELECT id, account_id, plan_id, source_revision, source_snapshot_hash,
                      trigger_at, revision, state, intent_rowid
               FROM (
                   SELECT intent.id AS id, intent.account_id AS account_id,
                          intent.plan_id AS plan_id, intent.source_revision AS source_revision,
                          intent.source_snapshot_hash AS source_snapshot_hash,
                          intent.trigger_at AS trigger_at, intent.revision AS revision,
                          intent.state AS state, intent.rowid AS intent_rowid,
                          ROW_NUMBER() OVER (
                              PARTITION BY intent.account_id
                              ORDER BY intent.trigger_at ASC, intent.id ASC
                          ) AS account_rank
                   FROM web_campaign_schedule_intents AS intent
                   WHERE intent.state='active'
                     AND (
                        (
                            intent.trigger_at<=?
                            AND NOT EXISTS (
                                SELECT 1 FROM web_notification_dedupes AS dedupe
                                WHERE dedupe.account_id=intent.account_id
                                  AND dedupe.source_kind='campaign_schedule_intent'
                                  AND dedupe.source_id=intent.id
                                  AND dedupe.source_revision=intent.revision
                                  AND dedupe.occurrence_at=intent.trigger_at
                            )
                        )
                        OR typeof(intent.id)!='text' OR length(intent.id)!=36
                        OR length(replace(intent.id, '-', ''))!=32
                        OR replace(intent.id, '-', '') GLOB '*[^0-9A-Fa-f]*'
                        OR typeof(intent.account_id)!='text' OR length(intent.account_id)!=36
                        OR length(replace(intent.account_id, '-', ''))!=32
                        OR replace(intent.account_id, '-', '') GLOB '*[^0-9A-Fa-f]*'
                        OR typeof(intent.plan_id)!='text' OR length(intent.plan_id)!=36
                        OR length(replace(intent.plan_id, '-', ''))!=32
                        OR replace(intent.plan_id, '-', '') GLOB '*[^0-9A-Fa-f]*'
                        OR typeof(intent.source_revision)!='integer' OR intent.source_revision<1
                        OR typeof(intent.revision)!='integer' OR intent.revision<1
                        OR typeof(intent.source_snapshot_hash)!='text'
                        OR length(intent.source_snapshot_hash)!=64
                        OR intent.source_snapshot_hash GLOB '*[^0-9a-f]*'
                        OR typeof(intent.trigger_at)!='text' OR length(intent.trigger_at)!=25
                        OR substr(intent.trigger_at, 11, 1)!='T'
                        OR substr(intent.trigger_at, 20, 1)!='+'
                        OR substr(intent.trigger_at, 23, 1)!=':'
                        OR datetime(intent.trigger_at) IS NULL
                     )
               ) AS ranked
               WHERE account_rank<=?
               ORDER BY trigger_at ASC, id ASC LIMIT ?""",
            (now, FAIR_CANDIDATES_PER_ACCOUNT, MAX_SOURCE_CANDIDATES_PER_RUN),
        ).fetchall()
    return [tuple(row) for row in rows]


def _overdue_warning_snapshots(now: datetime, *, deadline: datetime) -> list[tuple[Any, ...]]:
    """Return bounded, opaque unread warnings that may need local escalation.

    SQL is only a bounded prefilter.  The Python validator below is the
    authority for timezone-aware 24-hour eligibility, so malformed metadata
    is never guessed into an urgent state.  This reads no source content and
    contains no source/reminder/intent lookup.
    """

    cutoff = now - OVERDUE_WARNING_AFTER
    cutoff_text = _time_text(cutoff)
    with _tick_read_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        rows = conn.execute(
            """SELECT id, account_id, state, severity, revision, occurrence_at
               FROM (
                   SELECT item.id AS id, item.account_id AS account_id,
                          item.state AS state, item.severity AS severity,
                          item.revision AS revision, item.occurrence_at AS occurrence_at,
                          ROW_NUMBER() OVER (
                              PARTITION BY item.account_id
                              ORDER BY item.occurrence_at ASC, item.id ASC
                          ) AS account_rank
                   FROM web_notification_items AS item
                   WHERE item.state='unread' AND item.severity='warning'
                     AND typeof(item.occurrence_at)='text'
                     AND length(item.occurrence_at) BETWEEN 1 AND 80
                     AND datetime(item.occurrence_at) IS NOT NULL
                     AND datetime(item.occurrence_at)<=datetime(?)
               ) AS ranked
               WHERE account_rank<=?
               ORDER BY occurrence_at ASC, id ASC LIMIT ?""",
            (cutoff_text, FAIR_CANDIDATES_PER_ACCOUNT, MAX_SOURCE_CANDIDATES_PER_RUN),
        ).fetchall()
    snapshots = [tuple(row) for row in rows]
    return [
        snapshot for snapshot in snapshots
        if _overdue_warning_item_is_eligible(snapshot, cutoff=cutoff)
    ]


def _workboard_schedule_is_due(row: tuple[Any, ...], *, now: datetime) -> bool:
    try:
        return (
            _schedule_intent_validation_code(row, prefix="WORKBOARD") is None
            and _as_utc(row[5]) <= now
        )
    except (IndexError, TypeError, ValueError):
        return False


def _campaign_schedule_is_due(row: tuple[Any, ...], *, now: datetime) -> bool:
    try:
        return (
            _schedule_intent_validation_code(row, prefix="CAMPAIGN") is None
            and _as_utc(row[5]) <= now
        )
    except (IndexError, TypeError, ValueError):
        return False


def _workboard_schedule_dedupe_fingerprint(
    *, account_id: str, intent_id: str, intent_revision: int, occurrence_at: str,
) -> str:
    material = (
        f"v1\nworkboard_schedule_due\n{account_id}\n{intent_id}\n{intent_revision}\n{occurrence_at}"
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _campaign_schedule_dedupe_fingerprint(
    *, account_id: str, intent_id: str, intent_revision: int, occurrence_at: str,
) -> str:
    material = (
        f"v1\ncampaign_schedule_due\n{account_id}\n{intent_id}\n{intent_revision}\n{occurrence_at}"
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _guard_workboard_schedule_intent(
    conn: Any,
    *,
    snapshot: tuple[Any, ...],
    code: str,
    now_text: str,
) -> tuple[str, bool]:
    """Fence a mismatched source; never edit the Workboard item itself."""
    intent_id, account_id = str(snapshot[0]), str(snapshot[1])
    expected_revision = int(snapshot[6])
    updated = conn.execute(
        """UPDATE web_workboard_schedule_intents
           SET state='guarded', revision=revision+1, updated_at=?, guarded_at=?, guard_code=?
           WHERE id=? AND account_id=? AND state='active' AND revision=?
             AND item_id=? AND source_revision=? AND source_snapshot_hash=? AND trigger_at=?""",
        (
            now_text, now_text, code, intent_id, account_id, expected_revision,
            str(snapshot[2]), int(snapshot[3]), str(snapshot[4]), str(snapshot[5]),
        ),
    )
    return ("source_guarded", int(updated.rowcount or 0) == 1)


def _guard_campaign_schedule_intent(
    conn: Any,
    *,
    snapshot: tuple[Any, ...],
    code: str,
    now_text: str,
) -> tuple[str, bool]:
    """Fence a mismatched Campaign source without editing the Campaign itself."""
    intent_id, account_id = str(snapshot[0]), str(snapshot[1])
    expected_revision = int(snapshot[6])
    updated = conn.execute(
        """UPDATE web_campaign_schedule_intents
           SET state='guarded', revision=revision+1, updated_at=?, guarded_at=?, guard_code=?
           WHERE id=? AND account_id=? AND state='active' AND revision=?
             AND plan_id=? AND source_revision=? AND source_snapshot_hash=? AND trigger_at=?""",
        (
            now_text, now_text, code, intent_id, account_id, expected_revision,
            str(snapshot[2]), int(snapshot[3]), str(snapshot[4]), str(snapshot[5]),
        ),
    )
    return ("source_guarded", int(updated.rowcount or 0) == 1)


def _guard_malformed_workboard_schedule_intent(
    conn: Any,
    *,
    snapshot: tuple[Any, ...],
    code: str,
    now_text: str,
) -> bool:
    """Fail closed on an invalid Workboard intent with a row-level fence.

    A malformed field can make the normal id/account/revision fence unusable.
    The SQLite rowid plus an ``IS`` comparison of every scheduler coordinate
    prevents a stale tick from guarding a subsequently repaired intent.
    """
    try:
        intent_rowid = int(snapshot[8])
    except (IndexError, TypeError, ValueError, OverflowError):
        return False
    updated = conn.execute(
        """UPDATE web_workboard_schedule_intents
           SET state='guarded',
               revision=CASE WHEN typeof(revision)='integer' AND revision>=1 THEN revision+1 ELSE 1 END,
               updated_at=?, guarded_at=?, guard_code=?
           WHERE rowid=? AND state='active'
             AND id IS ? AND account_id IS ? AND item_id IS ?
             AND source_revision IS ? AND source_snapshot_hash IS ?
             AND trigger_at IS ? AND revision IS ?""",
        (
            now_text, now_text, code, intent_rowid,
            snapshot[0], snapshot[1], snapshot[2], snapshot[3], snapshot[4], snapshot[5], snapshot[6],
        ),
    )
    return int(updated.rowcount or 0) == 1


def _guard_malformed_campaign_schedule_intent(
    conn: Any,
    *,
    snapshot: tuple[Any, ...],
    code: str,
    now_text: str,
) -> bool:
    """Fail closed on an invalid Campaign intent with a row-level fence."""
    try:
        intent_rowid = int(snapshot[8])
    except (IndexError, TypeError, ValueError, OverflowError):
        return False
    updated = conn.execute(
        """UPDATE web_campaign_schedule_intents
           SET state='guarded',
               revision=CASE WHEN typeof(revision)='integer' AND revision>=1 THEN revision+1 ELSE 1 END,
               updated_at=?, guarded_at=?, guard_code=?
           WHERE rowid=? AND state='active'
             AND id IS ? AND account_id IS ? AND plan_id IS ?
             AND source_revision IS ? AND source_snapshot_hash IS ?
             AND trigger_at IS ? AND revision IS ?""",
        (
            now_text, now_text, code, intent_rowid,
            snapshot[0], snapshot[1], snapshot[2], snapshot[3], snapshot[4], snapshot[5], snapshot[6],
        ),
    )
    return int(updated.rowcount or 0) == 1


def _workboard_schedule_source_code(conn: Any, *, snapshot: tuple[Any, ...]) -> str | None:
    """Verify the current Workboard revision and immutable snapshot hash."""
    if not workboard_enabled():
        return "WORKBOARD_SCHEDULE_WORKBOARD_DISABLED"
    item = conn.execute(
        """SELECT state, revision FROM web_workboard_items
           WHERE id=? AND account_id=?""",
        (str(snapshot[2]), str(snapshot[1])),
    ).fetchone()
    if not item or str(item[0]) == "archived" or int(item[1]) != int(snapshot[3]):
        return "WORKBOARD_SCHEDULE_SOURCE_CHANGED"
    version = conn.execute(
        """SELECT snapshot_json FROM web_workboard_item_versions
           WHERE item_id=? AND account_id=? AND revision=?""",
        (str(snapshot[2]), str(snapshot[1]), int(snapshot[3])),
    ).fetchone()
    if not version:
        return "WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED"
    try:
        parsed = json.loads(str(version[0]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return "WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED"
    if not isinstance(parsed, dict):
        return "WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED"
    canonical = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    current_hash = hashlib.sha256(canonical).hexdigest()
    return None if hmac.compare_digest(current_hash, str(snapshot[4])) else "WORKBOARD_SCHEDULE_SOURCE_CHANGED"


def _campaign_schedule_source_code(conn: Any, *, snapshot: tuple[Any, ...]) -> str | None:
    """Verify Campaign ownership, revision and semantic source digest."""
    plan = conn.execute(
        """SELECT title, destination_url, platform, objective, scheduled_for, approval_status, review_note, revision
           FROM web_campaign_plans WHERE id=? AND account_id=?""",
        (str(snapshot[2]), str(snapshot[1])),
    ).fetchone()
    if not plan or str(plan[5]) == "archived" or int(plan[7]) != int(snapshot[3]):
        return "CAMPAIGN_SCHEDULE_SOURCE_CHANGED"
    current_hash = campaign_source_hash(
        title=plan[0],
        destination_url=plan[1],
        platform=plan[2],
        objective=plan[3],
        scheduled_for=plan[4],
        approval_status=plan[5],
        review_note=plan[6],
    )
    if not re.fullmatch(r"[0-9a-f]{64}", current_hash):
        return "CAMPAIGN_SCHEDULE_SOURCE_UNVERIFIED"
    return None if hmac.compare_digest(current_hash, str(snapshot[4])) else "CAMPAIGN_SCHEDULE_SOURCE_CHANGED"


def _reminder_is_due(row: tuple[Any, ...], *, now: datetime) -> bool:
    try:
        return str(row[2]) == "active" and _as_utc(row[4]) <= now
    except (IndexError, TypeError, ValueError):
        return False


def _severity_for_reminder(occurrence_at: str, *, now: datetime) -> str:
    try:
        return "urgent" if now - _as_utc(occurrence_at) >= OVERDUE_WARNING_AFTER else "warning"
    except ValueError:
        return "warning"


def _overdue_warning_item_is_eligible(snapshot: tuple[Any, ...], *, cutoff: datetime) -> bool:
    """Validate the only existing Inbox rows eligible for local urgency upkeep.

    This accepts opaque item/account IDs and timestamp metadata only.  A
    malformed timestamp, ID or revision is skipped rather than guessed into an
    urgent state.  The same predicate is re-run under the scheduler write
    transaction before any update.
    """

    try:
        if len(snapshot) < 6:
            return False
        item_id, account_id, state, severity, revision, occurrence_at = snapshot[:6]
        return bool(
            _opaque_uuid(str(item_id))
            and _opaque_uuid(str(account_id))
            and str(state) == "unread"
            and str(severity) == "warning"
            and isinstance(revision, int)
            and 1 <= revision <= 1_000_000
            and _as_utc(occurrence_at) <= cutoff
        )
    except (TypeError, ValueError, OverflowError):
        return False


def _dedupe_fingerprint(*, account_id: str, reminder_id: str, revision: int, occurrence_at: str) -> str:
    # IDs/timestamps are opaque Web metadata.  Do not include reminder title,
    # body, linked note content, identity provider data or any external handle.
    material = f"v1\nreminder_due\n{account_id}\n{reminder_id}\n{revision}\n{occurrence_at}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _prune_dismissed_items(conn: Any, *, account_id: str, now: datetime) -> None:
    """Bound acknowledged Inbox retention without deleting unread/read work.

    A dismissed record is an explicit user acknowledgement. We retain it for
    a short audit window, then remove its dependent non-financial event rows
    in the same transaction. Unread/read records never get auto-deleted and
    therefore continue to count toward the protective account cap.
    """
    cutoff = _time_text(now - timedelta(days=DISMISSED_RETENTION_DAYS))
    stale_rows = conn.execute(
        """SELECT id FROM web_notification_items
           WHERE account_id=? AND state='dismissed' AND dismissed_at IS NOT NULL AND dismissed_at<?
           LIMIT 100""",
        (account_id, cutoff),
    ).fetchall()
    stale_ids = [str(row[0]) for row in stale_rows]
    if stale_ids:
        placeholders = ",".join("?" for _ in stale_ids)
        conn.execute(
            f"DELETE FROM web_notification_events WHERE account_id=? AND notification_id IN ({placeholders})",
            (account_id, *stale_ids),
        )
        conn.execute(
            f"DELETE FROM web_notification_items WHERE account_id=? AND id IN ({placeholders}) AND state='dismissed'",
            (account_id, *stale_ids),
        )
    # A tombstone remains only while its source is still the same active,
    # overdue occurrence. Once the reminder advances, is completed/cancelled
    # or gets a revision, the opaque dedupe coordinate is no longer useful.
    conn.execute(
        """DELETE FROM web_notification_dedupes
           WHERE account_id=? AND source_kind='memory_reminder'
             AND NOT EXISTS (
               SELECT 1 FROM web_memory_reminders AS reminder
               WHERE reminder.id=web_notification_dedupes.source_id
                 AND reminder.account_id=web_notification_dedupes.account_id
                 AND reminder.state='active'
                 AND reminder.revision=web_notification_dedupes.source_revision
                 AND reminder.next_run_at=web_notification_dedupes.occurrence_at
             )""",
        (account_id,),
    )


def _materialize_reminder(
    *, run_id: str, fence_token: int, snapshot: tuple[Any, ...], now: datetime, deadline: datetime,
) -> tuple[str, bool]:
    """Re-read one source and insert at most one owner-scoped inbox record."""
    now_text = _time_text(now)
    with _tick_write_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now_text):
            raise _TickLeaseLost()
        row = conn.execute(
            """SELECT id, account_id, state, revision, next_run_at
               FROM web_memory_reminders WHERE id=? AND account_id=?""",
            (str(snapshot[0]), str(snapshot[1])),
        ).fetchone()
        current = tuple(row) if row else None
        if not current or not _reminder_is_due(current, now=now):
            return "source_changed", False
        account_id = str(current[1])
        _prune_dismissed_items(conn, account_id=account_id, now=now)
        total = conn.execute(
            "SELECT COUNT(*) FROM web_notification_items WHERE account_id=? AND state!='dismissed'", (account_id,),
        ).fetchone()
        if int(total[0] or 0) >= MAX_ITEMS_PER_ACCOUNT:
            return "account_cap", False
        reminder_id = str(current[0])
        revision = int(current[3])
        occurrence = str(current[4])
        fingerprint = _dedupe_fingerprint(
            account_id=account_id, reminder_id=reminder_id, revision=revision, occurrence_at=occurrence,
        )
        item_id = str(uuid.uuid4())
        dedupe = conn.execute(
            """INSERT OR IGNORE INTO web_notification_dedupes
               (dedupe_fingerprint, account_id, source_kind, source_id, source_revision, occurrence_at, created_at)
               VALUES (?, ?, 'memory_reminder', ?, ?, ?, ?)""",
            (fingerprint, account_id, reminder_id, revision, occurrence, now_text),
        )
        if int(dedupe.rowcount or 0) != 1:
            return "duplicate", False
        inserted = conn.execute(
            """INSERT INTO web_notification_items
               (id, account_id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state,
                revision, dedupe_fingerprint, created_by_run_id, created_at, updated_at)
               VALUES (?, ?, 'reminder_due', 'memory_reminder', ?, ?, ?, ?, 'unread', 1, ?, ?, ?, ?)""",
            (
                item_id, account_id, reminder_id, revision, occurrence, _severity_for_reminder(occurrence, now=now),
                fingerprint, run_id, now_text, now_text,
            ),
        )
        if int(inserted.rowcount or 0) != 1:
            return "duplicate", False
        conn.execute(
            """INSERT INTO web_notification_events
               (id, notification_id, account_id, actor_account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, NULL, 'materialized', 'unread', 1, ?)""",
            (str(uuid.uuid4()), item_id, account_id, now_text),
        )
        return "materialized", True


def _materialize_workboard_schedule(
    *, run_id: str, fence_token: int, snapshot: tuple[Any, ...], now: datetime, deadline: datetime,
) -> tuple[str, bool, bool]:
    """Materialize one verified intent or guard it for explicit owner review.

    ``created`` means a private Inbox row was inserted. ``changed`` counts a
    bounded schedule-state write (either dispatch or guard) for the run
    budget.  This function never writes the Workboard card, its checklist,
    version history or event timeline.
    """
    now_text = _time_text(now)
    with _tick_write_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now_text):
            raise _TickLeaseLost()
        try:
            intent_rowid = int(snapshot[8])
        except (IndexError, TypeError, ValueError, OverflowError):
            return "intent_changed", False, False
        row = conn.execute(
            """SELECT id, account_id, item_id, source_revision, source_snapshot_hash, trigger_at, revision, state,
                      rowid AS intent_rowid
               FROM web_workboard_schedule_intents WHERE rowid=?""",
            (intent_rowid,),
        ).fetchone()
        current = tuple(row) if row else None
        if not current or current != snapshot:
            return "intent_changed", False, False
        validation_code = _schedule_intent_validation_code(current, prefix="WORKBOARD")
        if validation_code:
            changed = _guard_malformed_workboard_schedule_intent(
                conn, snapshot=current, code=validation_code, now_text=now_text,
            )
            return validation_code.lower(), False, changed
        if not _workboard_schedule_is_due(current, now=now):
            return "intent_changed", False, False
        source_code = _workboard_schedule_source_code(conn, snapshot=current)
        if source_code:
            outcome, changed = _guard_workboard_schedule_intent(
                conn, snapshot=current, code=source_code, now_text=now_text,
            )
            return source_code.lower(), False, changed
        account_id = str(current[1])
        _prune_dismissed_items(conn, account_id=account_id, now=now)
        total = conn.execute(
            "SELECT COUNT(*) FROM web_notification_items WHERE account_id=? AND state!='dismissed'", (account_id,),
        ).fetchone()
        if int(total[0] or 0) >= MAX_ITEMS_PER_ACCOUNT:
            return "account_cap", False, False
        intent_id = str(current[0])
        intent_revision = int(current[6])
        occurrence = str(current[5])
        fingerprint = _workboard_schedule_dedupe_fingerprint(
            account_id=account_id, intent_id=intent_id, intent_revision=intent_revision, occurrence_at=occurrence,
        )
        item_id = str(uuid.uuid4())
        dedupe = conn.execute(
            """INSERT OR IGNORE INTO web_notification_dedupes
               (dedupe_fingerprint, account_id, source_kind, source_id, source_revision, occurrence_at, created_at)
               VALUES (?, ?, 'workboard_schedule_intent', ?, ?, ?, ?)""",
            (fingerprint, account_id, intent_id, intent_revision, occurrence, now_text),
        )
        if int(dedupe.rowcount or 0) != 1:
            # An earlier transaction may have materialized the row just before
            # a process died.  Mark only this exact still-active intent as
            # dispatched; do not re-open or mutate its Workboard source.
            updated = conn.execute(
                """UPDATE web_workboard_schedule_intents
                   SET state='dispatched', revision=revision+1, updated_at=?, dispatched_at=?
                   WHERE id=? AND account_id=? AND state='active' AND revision=?""",
                (now_text, now_text, intent_id, account_id, intent_revision),
            )
            return "duplicate", False, int(updated.rowcount or 0) == 1
        inserted = conn.execute(
            """INSERT OR IGNORE INTO web_notification_items
               (id, account_id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state,
                revision, dedupe_fingerprint, created_by_run_id, created_at, updated_at)
               VALUES (?, ?, 'workboard_schedule_due', 'workboard_schedule_intent', ?, ?, ?, ?, 'unread', 1, ?, ?, ?, ?)""",
            (
                item_id, account_id, intent_id, intent_revision, occurrence,
                _severity_for_reminder(occurrence, now=now), fingerprint, run_id, now_text, now_text,
            ),
        )
        if int(inserted.rowcount or 0) != 1:
            raise RuntimeError("Workboard schedule Inbox insert was not acknowledged")
        updated = conn.execute(
            """UPDATE web_workboard_schedule_intents
               SET state='dispatched', revision=revision+1, updated_at=?, dispatched_at=?
               WHERE id=? AND account_id=? AND state='active' AND revision=?""",
            (now_text, now_text, intent_id, account_id, intent_revision),
        )
        if int(updated.rowcount or 0) != 1:
            # This cannot safely be retried: the Inbox record has an atomic
            # dedupe tombstone, so leave the scheduler receipt guarded rather
            # than fabricate a source transition.
            raise _TickLeaseLost()
        conn.execute(
            """INSERT INTO web_notification_events
               (id, notification_id, account_id, actor_account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, NULL, 'materialized', 'unread', 1, ?)""",
            (str(uuid.uuid4()), item_id, account_id, now_text),
        )
        return "materialized", True, True


def _materialize_campaign_schedule(
    *, run_id: str, fence_token: int, snapshot: tuple[Any, ...], now: datetime, deadline: datetime,
) -> tuple[str, bool, bool]:
    """Materialize one verified Campaign intent or guard it for owner review.

    The only permitted state writes are the intent's own `guarded` or
    `dispatched` transition plus one private Inbox item/dedupe tombstone.  It
    never changes the Campaign plan, its inert ``scheduled_for`` field,
    Calendar, publication state, Bot, provider, payment, wallet or job.
    """
    now_text = _time_text(now)
    with _tick_write_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now_text):
            raise _TickLeaseLost()
        try:
            intent_rowid = int(snapshot[8])
        except (IndexError, TypeError, ValueError, OverflowError):
            return "intent_changed", False, False
        row = conn.execute(
            """SELECT id, account_id, plan_id, source_revision, source_snapshot_hash, trigger_at, revision, state,
                      rowid AS intent_rowid
               FROM web_campaign_schedule_intents WHERE rowid=?""",
            (intent_rowid,),
        ).fetchone()
        current = tuple(row) if row else None
        if not current or current != snapshot:
            return "intent_changed", False, False
        validation_code = _schedule_intent_validation_code(current, prefix="CAMPAIGN")
        if validation_code:
            changed = _guard_malformed_campaign_schedule_intent(
                conn, snapshot=current, code=validation_code, now_text=now_text,
            )
            return validation_code.lower(), False, changed
        if not _campaign_schedule_is_due(current, now=now):
            return "intent_changed", False, False
        source_code = _campaign_schedule_source_code(conn, snapshot=current)
        if source_code:
            _outcome, changed = _guard_campaign_schedule_intent(
                conn, snapshot=current, code=source_code, now_text=now_text,
            )
            return source_code.lower(), False, changed
        account_id = str(current[1])
        _prune_dismissed_items(conn, account_id=account_id, now=now)
        total = conn.execute(
            "SELECT COUNT(*) FROM web_notification_items WHERE account_id=? AND state!='dismissed'", (account_id,),
        ).fetchone()
        if int(total[0] or 0) >= MAX_ITEMS_PER_ACCOUNT:
            return "account_cap", False, False
        intent_id = str(current[0])
        intent_revision = int(current[6])
        occurrence = str(current[5])
        fingerprint = _campaign_schedule_dedupe_fingerprint(
            account_id=account_id, intent_id=intent_id, intent_revision=intent_revision, occurrence_at=occurrence,
        )
        item_id = str(uuid.uuid4())
        dedupe = conn.execute(
            """INSERT OR IGNORE INTO web_notification_dedupes
               (dedupe_fingerprint, account_id, source_kind, source_id, source_revision, occurrence_at, created_at)
               VALUES (?, ?, 'campaign_schedule_intent', ?, ?, ?, ?)""",
            (fingerprint, account_id, intent_id, intent_revision, occurrence, now_text),
        )
        if int(dedupe.rowcount or 0) != 1:
            # A previous transaction can have created the Inbox item before a
            # process died. Mark only this exact still-active intent as
            # dispatched; never attempt a second customer-visible record.
            updated = conn.execute(
                """UPDATE web_campaign_schedule_intents
                   SET state='dispatched', revision=revision+1, updated_at=?, dispatched_at=?
                   WHERE id=? AND account_id=? AND state='active' AND revision=?""",
                (now_text, now_text, intent_id, account_id, intent_revision),
            )
            return "duplicate", False, int(updated.rowcount or 0) == 1
        inserted = conn.execute(
            """INSERT OR IGNORE INTO web_notification_items
               (id, account_id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state,
                revision, dedupe_fingerprint, created_by_run_id, created_at, updated_at)
               VALUES (?, ?, 'campaign_schedule_due', 'campaign_schedule_intent', ?, ?, ?, ?, 'unread', 1, ?, ?, ?, ?)""",
            (
                item_id, account_id, intent_id, intent_revision, occurrence,
                _severity_for_reminder(occurrence, now=now), fingerprint, run_id, now_text, now_text,
            ),
        )
        if int(inserted.rowcount or 0) != 1:
            raise RuntimeError("Campaign schedule Inbox insert was not acknowledged")
        updated = conn.execute(
            """UPDATE web_campaign_schedule_intents
               SET state='dispatched', revision=revision+1, updated_at=?, dispatched_at=?
               WHERE id=? AND account_id=? AND state='active' AND revision=?""",
            (now_text, now_text, intent_id, account_id, intent_revision),
        )
        if int(updated.rowcount or 0) != 1:
            # The Inbox row has an atomic dedupe tombstone at this point. A
            # retry could not safely recreate its intent transition, so fence
            # the old scheduler instead of inventing success.
            raise _TickLeaseLost()
        conn.execute(
            """INSERT INTO web_notification_events
               (id, notification_id, account_id, actor_account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, NULL, 'materialized', 'unread', 1, ?)""",
            (str(uuid.uuid4()), item_id, account_id, now_text),
        )
        return "materialized", True, True


def _escalate_overdue_warning_item(
    *, run_id: str, fence_token: int, snapshot: tuple[Any, ...], now: datetime, deadline: datetime,
) -> tuple[str, bool]:
    """Raise only a still-unread warning record's private urgency metadata.

    The candidate contains no source body/title/payload.  It is re-read under
    the same HMAC lease/fence and deadline as materialization, then updated
    with an optimistic predicate so a concurrent signed owner read/dismiss
    cannot be overwritten.  No item, dedupe or source record is created or
    changed.
    """

    now_text = _time_text(now)
    cutoff = now - OVERDUE_WARNING_AFTER
    with _tick_write_transaction(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS) as conn:
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now_text):
            raise _TickLeaseLost()
        try:
            item_id, account_id = str(snapshot[0]), str(snapshot[1])
        except (IndexError, TypeError, ValueError):
            return "item_changed", False
        row = conn.execute(
            """SELECT id, account_id, state, severity, revision, occurrence_at
               FROM web_notification_items WHERE id=? AND account_id=?""",
            (item_id, account_id),
        ).fetchone()
        current = tuple(row) if row else None
        if not current or not _overdue_warning_item_is_eligible(current, cutoff=cutoff):
            return "item_changed", False
        expected_revision = int(current[4])
        updated = conn.execute(
            """UPDATE web_notification_items
               SET severity='urgent', revision=revision+1, updated_at=?
               WHERE id=? AND account_id=? AND revision=?
                 AND state='unread' AND severity='warning'""",
            (now_text, item_id, account_id, expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            return "item_changed", False
        next_revision = expected_revision + 1
        conn.execute(
            """INSERT INTO web_notification_events
               (id, notification_id, account_id, actor_account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, NULL, 'overdue_escalated', 'unread', ?, ?)""",
            (str(uuid.uuid4()), item_id, account_id, next_revision, now_text),
        )
        return "overdue_escalated", True


def _fair_candidate_selection(
    candidates: list[tuple[str, str, tuple[Any, ...]]], *, limit: int,
) -> list[tuple[str, str, tuple[Any, ...]]]:
    """Take deterministic account rounds from an already bounded scan.

    The old global sort could place the first ``limit`` overdue rows from one
    account ahead of every other account forever, especially when the first
    account had hit its Inbox cap.  A round takes one oldest candidate per
    account, ordered by the same stable occurrence/source/id key, then starts
    the next round.  It has no persisted cursor or hidden priority and keeps
    the existing source-order tie break deterministic.
    """
    if limit < 1:
        return []
    ordered = sorted(candidates, key=lambda value: (value[0], value[1], str(value[2][0])))
    queues: dict[str, list[tuple[str, str, tuple[Any, ...]]]] = {}
    for candidate in ordered:
        snapshot = candidate[2]
        account_id = str(snapshot[1]) if len(snapshot) > 1 else ""
        queues.setdefault(account_id, []).append(candidate)
    selected: list[tuple[str, str, tuple[Any, ...]]] = []
    while len(selected) < limit:
        turns = [
            (queue[0][0], queue[0][1], str(queue[0][2][0]), account_id)
            for account_id, queue in queues.items()
            if queue
        ]
        if not turns:
            break
        turns.sort()
        for _occurrence, _source_kind, _source_id, account_id in turns:
            selected.append(queues[account_id].pop(0))
            if len(selected) >= limit:
                break
    return selected


def _materialization_candidates(now: datetime, *, deadline: datetime) -> list[tuple[str, str, tuple[Any, ...]]]:
    """Merge allow-listed sources and existing Inbox upkeep fairly and bounded."""
    now_text = _time_text(now)
    reminders = _reminder_snapshots(now_text, deadline=deadline)
    workboard_schedules = _workboard_schedule_snapshots(now_text, deadline=deadline)
    campaign_schedules = _campaign_schedule_snapshots(now_text, deadline=deadline)
    overdue_warnings = _overdue_warning_snapshots(now, deadline=deadline)
    candidates = [(str(row[4]), "memory_reminder", row) for row in reminders]
    candidates.extend((str(row[5]), "workboard_schedule", row) for row in workboard_schedules)
    candidates.extend((str(row[5]), "campaign_schedule", row) for row in campaign_schedules)
    candidates.extend((str(row[5]), "overdue_warning", row) for row in overdue_warnings)
    return _fair_candidate_selection(candidates, limit=MAX_CANDIDATES_PER_RUN)


def _run_materialization(
    *, run_id: str, fence_token: int, deadline: datetime, max_actions: int, progress: dict[str, int] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    candidates = _materialization_candidates(now, deadline=deadline)
    actions = 0
    in_app_records = 0
    urgency_escalations = 0
    guarded_sources = 0
    account_cap = False
    capped = False
    deadline_reached = False
    if progress is not None:
        progress.update(
            action_count=0,
            candidate_count=len(candidates),
            in_app_record_count=0,
            urgency_escalation_count=0,
            guarded_source_count=0,
        )
    for _occurrence, source_kind, snapshot in candidates:
        if actions >= max_actions:
            capped = True
            break
        try:
            _tick_db_timeout_seconds(deadline=deadline, reserve_seconds=TICK_FINISH_RESERVE_SECONDS)
        except _TickDeadlineExceeded:
            capped = True
            deadline_reached = True
            break
        if source_kind == "memory_reminder":
            outcome, created = _materialize_reminder(
                run_id=run_id, fence_token=fence_token, snapshot=snapshot,
                now=datetime.now(timezone.utc).replace(microsecond=0),
                deadline=deadline,
            )
            changed = created
        elif source_kind == "workboard_schedule":
            outcome, created, changed = _materialize_workboard_schedule(
                run_id=run_id, fence_token=fence_token, snapshot=snapshot,
                now=datetime.now(timezone.utc).replace(microsecond=0),
                deadline=deadline,
            )
        elif source_kind == "campaign_schedule":
            outcome, created, changed = _materialize_campaign_schedule(
                run_id=run_id, fence_token=fence_token, snapshot=snapshot,
                now=datetime.now(timezone.utc).replace(microsecond=0),
                deadline=deadline,
            )
        elif source_kind == "overdue_warning":
            outcome, changed = _escalate_overdue_warning_item(
                run_id=run_id, fence_token=fence_token, snapshot=snapshot,
                now=datetime.now(timezone.utc).replace(microsecond=0),
                deadline=deadline,
            )
            created = False
        else:
            outcome, created, changed = "unknown_candidate", False, False
        if outcome == "account_cap":
            account_cap = True
        if outcome.startswith(("workboard_schedule_", "campaign_schedule_")):
            guarded_sources += 1
        if changed:
            actions += 1
        if created:
            in_app_records += 1
        if outcome == "overdue_escalated":
            urgency_escalations += 1
        if progress is not None:
            progress.update(
                action_count=actions,
                candidate_count=len(candidates),
                in_app_record_count=in_app_records,
                urgency_escalation_count=urgency_escalations,
                guarded_source_count=guarded_sources,
            )
    state = "guarded" if capped or account_cap else "completed"
    code = (
        "NOTIFY_TICK_DEADLINE_REACHED" if deadline_reached
        else "NOTIFY_ACTION_BUDGET_REACHED" if capped
        else "NOTIFY_ACCOUNT_CAP_REACHED" if account_cap
        else ""
    )
    with _tick_write_transaction(deadline=deadline) as conn:
        now_text = utc_now()
        if not _lease_current(conn, run_id=run_id, fence_token=fence_token, now=now_text):
            raise _TickLeaseLost()
        _insert_step(
            conn, run_id=run_id, sequence=1, state=state,
            input_hash=_json_hash({
                "candidate_count": len(candidates), "actions": actions, "in_app_records": in_app_records,
                "urgency_escalations": urgency_escalations, "guarded_sources": guarded_sources,
                "policy_version": POLICY_VERSION,
            }),
            result_code=code or (
                "IN_APP_RECORDS_AND_URGENCY_MAINTAINED" if in_app_records and urgency_escalations
                else "IN_APP_RECORDS_MATERIALIZED" if in_app_records
                else "IN_APP_URGENCY_MAINTAINED" if urgency_escalations
                else "NO_IN_APP_RECORDS_OR_URGENCY_CHANGES"
            ),
        )
        # History retention is deliberately after the current run's step is
        # durable and under the same fenced/deadline-aware transaction. It is
        # best effort and cannot change this tick's materialization result.
        _prune_finished_run_history(
            conn,
            current_run_id=run_id,
            deadline=deadline,
        )
    return {
        "state": state,
        "action_count": actions,
        "in_app_record_count": in_app_records,
        "urgency_escalation_count": urgency_escalations,
        "guarded_source_count": guarded_sources,
        "candidate_count": len(candidates),
        "code": code,
    }


def _run_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]), "request_id": str(row[1]), "trigger": str(row[2]), "schedule_slot": str(row[3]),
        "state": str(row[4]), "policy_version": int(row[6]), "action_count": int(row[8]),
        "candidate_count": int(row[9]), "deadline_at": str(row[10]), "started_at": str(row[11]),
        "finished_at": str(row[12]) if row[12] else None, "error_code": str(row[13]) if row[13] else None,
    }


def _item_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]), "kind": str(row[1]), "source_kind": str(row[2]), "source_id": str(row[3]),
        "source_revision": int(row[4]), "occurrence_at": str(row[5]), "severity": str(row[6]),
        "state": str(row[7]), "revision": int(row[8]), "created_at": str(row[9]), "updated_at": str(row[10]),
        "read_at": str(row[11]) if row[11] else None, "dismissed_at": str(row[12]) if row[12] else None,
        "delivery": "in_app_record_only",
    }


class InboxMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    confirm: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


def _idempotent(
    *, account_id: str, scope: str, key: str, request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        cutoff = _time_text(datetime.now(timezone.utc) - timedelta(days=30))
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at<?", (f"web-notification:{account_id}:%", cutoff))
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[1] or ""), request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu Inbox khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Inbox không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Inbox không hợp lệ")
            return receipt
        response = operation(conn)
        conn.execute(
            """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
        )
    return response


@router.post("/internal/v1/notifications/tick", include_in_schema=False)
async def tick(request: Request):
    """Accept a signed isolated scheduler invocation for private inbox rows."""
    content_length = request.headers.get("content-length", "").strip()
    if content_length:
        try:
            if int(content_length) > TICK_MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Dữ liệu Inbox nội bộ vượt giới hạn an toàn")
        except ValueError:
            raise HTTPException(status_code=422, detail="Dữ liệu Inbox nội bộ không hợp lệ") from None
    body = await request.body()
    timestamp, nonce, request_id, key_id, timestamp_value = _tick_headers(request, body)
    _tick_payload(body, timestamp=timestamp)
    limits, limit_code = _tick_limits()
    run_seconds = int(limits[0]) if limits else MAX_TICK_SECONDS
    # This is the scheduler's single wall-clock ceiling.  Every scheduler
    # SQLite read/write below receives this same deadline instead of the
    # general application's 30-second busy timeout.
    deadline = datetime.now(timezone.utc) + timedelta(seconds=run_seconds)
    guard = (
        "NOTIFY_CENTER_DISABLED" if not _enabled()
        else "NOTIFY_AUTOMATION_DISABLED" if not _automation_enabled()
        else limit_code or _scheduler_preflight_code()
    )
    if guard:
        try:
            _record_guarded_tick(
                request_id=request_id, key_id=key_id, nonce=nonce, timestamp=timestamp_value, body=body,
                guarded_code=guard, deadline=deadline,
            )
        except _TickGuarded as exc:
            return envelope(True, _safe_public_message(exc.code), data=_boundary(request_id=request_id, run_started=False, guarded_code=exc.code), status_name="guarded")
        except _TickDeadlineExceeded:
            return envelope(
                True, _safe_public_message("NOTIFY_TICK_DEADLINE_REACHED"),
                data=_boundary(request_id=request_id, run_started=False, guarded_code="NOTIFY_TICK_DEADLINE_REACHED"),
                status_name="guarded",
            )
        return envelope(True, _safe_public_message(guard), data=_boundary(request_id=request_id, run_started=False, guarded_code=guard), status_name="guarded")
    try:
        run_id, fence, deadline, guarded_code = _start_run(
            request_id=request_id, key_id=key_id, nonce=nonce, timestamp=timestamp_value, body=body,
            run_seconds=run_seconds, deadline=deadline,
        )
    except _TickGuarded as exc:
        return envelope(True, _safe_public_message(exc.code), data=_boundary(request_id=request_id, run_started=False, guarded_code=exc.code), status_name="guarded")
    except _TickDeadlineExceeded:
        return envelope(
            True, _safe_public_message("NOTIFY_TICK_DEADLINE_REACHED"),
            data=_boundary(request_id=request_id, run_started=False, guarded_code="NOTIFY_TICK_DEADLINE_REACHED"),
            status_name="guarded",
        )
    if guarded_code:
        return envelope(True, _safe_public_message(guarded_code), data=_boundary(request_id=request_id, run_started=False, guarded_code=guarded_code), status_name="guarded")
    started = time.monotonic()
    progress = {
        "action_count": 0,
        "candidate_count": 0,
        "in_app_record_count": 0,
        "urgency_escalation_count": 0,
        "guarded_source_count": 0,
    }

    def current_receipt(*, guarded_code: str = "", failure: str = "") -> dict[str, Any]:
        receipt = {
            "request_id": request_id,
            "run_started": True,
            "action_count": max(0, int(progress.get("action_count") or 0)),
            "candidate_count": max(0, int(progress.get("candidate_count") or 0)),
            "in_app_record_count": max(0, int(progress.get("in_app_record_count") or 0)),
            "urgency_escalation_count": max(0, int(progress.get("urgency_escalation_count") or 0)),
            "guarded_source_count": max(0, int(progress.get("guarded_source_count") or 0)),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
        receipt["in_app_record_created"] = receipt["in_app_record_count"] > 0
        receipt["in_app_urgency_maintained"] = receipt["urgency_escalation_count"] > 0
        if guarded_code:
            receipt["guarded_code"] = guarded_code
        if failure:
            receipt["failure"] = failure
        return receipt

    try:
        result = _run_materialization(
            run_id=run_id, fence_token=fence, deadline=deadline, max_actions=int(limits[1]) if limits else 0,
            progress=progress,
        )
        progress.update(
            action_count=int(result["action_count"]),
            candidate_count=int(result["candidate_count"]),
            in_app_record_count=int(result.get("in_app_record_count") or 0),
            urgency_escalation_count=int(result.get("urgency_escalation_count") or 0),
            guarded_source_count=int(result.get("guarded_source_count") or 0),
        )
        receipt = current_receipt()
        if result.get("code"):
            receipt["guarded_code"] = str(result["code"])
        if not _finish_run(
            run_id=run_id, fence_token=fence, state=str(result["state"]), action_count=int(result["action_count"]),
            candidate_count=int(result["candidate_count"]), receipt=receipt, deadline=deadline,
            error_code=str(result.get("code") or ""),
        ):
            return envelope(True, _safe_public_message("NOTIFY_TICK_LEASE_LOST"), data=_boundary(request_id=request_id, run_started=True, guarded_code="NOTIFY_TICK_LEASE_LOST"), status_name="guarded")
        message = _safe_public_message(str(result["code"])) if result.get("code") else "Inbox Automation đã rà soát metadata in-app an toàn."
        return envelope(True, message, data=_boundary(**receipt), status_name=str(result["state"]))
    except _TickLeaseLost:
        receipt = current_receipt(guarded_code="NOTIFY_TICK_LEASE_LOST")
        try:
            _finish_run(
                run_id=run_id, fence_token=fence, state="guarded", action_count=receipt["action_count"],
                candidate_count=receipt["candidate_count"], receipt=receipt, deadline=deadline,
                error_code="NOTIFY_TICK_LEASE_LOST",
            )
        except _TickDeadlineExceeded:
            receipt["guarded_code"] = "NOTIFY_TICK_DEADLINE_REACHED"
            return envelope(True, _safe_public_message("NOTIFY_TICK_DEADLINE_REACHED"), data=_boundary(**receipt), status_name="guarded")
        return envelope(True, _safe_public_message("NOTIFY_TICK_LEASE_LOST"), data=_boundary(**receipt), status_name="guarded")
    except _TickDeadlineExceeded:
        receipt = current_receipt(guarded_code="NOTIFY_TICK_DEADLINE_REACHED")
        try:
            _finish_run(
                run_id=run_id, fence_token=fence, state="guarded", action_count=receipt["action_count"],
                candidate_count=receipt["candidate_count"], receipt=receipt, deadline=deadline,
                error_code="NOTIFY_TICK_DEADLINE_REACHED",
            )
        except _TickDeadlineExceeded:
            # Do not drop the active lease merely because the database is
            # still busy.  Its normal expiry fences a retry from creating a
            # duplicate row after a partially completed materialization.
            pass
        return envelope(True, _safe_public_message("NOTIFY_TICK_DEADLINE_REACHED"), data=_boundary(**receipt), status_name="guarded")
    except Exception:
        receipt = current_receipt(failure="internal_guarded")
        try:
            _finish_run(
                run_id=run_id, fence_token=fence, state="failed", action_count=receipt["action_count"],
                candidate_count=receipt["candidate_count"], receipt=receipt, deadline=deadline,
                error_code="NOTIFY_TICK_INTERNAL_FAILURE",
            )
        except _TickDeadlineExceeded:
            receipt["guarded_code"] = "NOTIFY_TICK_DEADLINE_REACHED"
            return envelope(True, _safe_public_message("NOTIFY_TICK_DEADLINE_REACHED"), data=_boundary(**receipt), status_name="guarded")
        raise HTTPException(status_code=500, detail="Inbox Automation không thể hoàn tất lần quét an toàn") from None


@router.get("/api/v1/inbox/policy")
async def policy(account: dict = Depends(require_account)):
    _require_center()
    preflight = _scheduler_preflight_code() if _automation_enabled() else "NOTIFY_AUTOMATION_DISABLED"
    return envelope(
        True,
        "Inbox Automation chỉ materialize bản ghi in-app cho nguồn Web được allow-list và có thể nâng urgency của record chưa đọc quá 24 giờ; không có delivery bên ngoài.",
        data=_boundary(
            account_id_present=bool(account.get("id")),
            scheduler_preflight=preflight or "ready",
            auto_sources=[
                "reminder_due_in_app_record",
                "workboard_schedule_due_in_app_record",
                "campaign_schedule_due_in_app_record",
            ],
            auto_maintenance=["unread_warning_to_urgent_after_24h"],
            in_app_urgency_maintenance=True,
            never_external=["telegram", "email", "sms", "web_push", "bot", "provider", "wallet", "payment", "job", "deploy"],
        ),
        status_name="guarded" if preflight else "read_only",
    )


@router.get("/api/v1/inbox/summary")
async def summary(account: dict = Depends(require_account)):
    _require_center()
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        counts = conn.execute(
            "SELECT state, severity, COUNT(*) FROM web_notification_items WHERE account_id=? GROUP BY state, severity",
            (account_id,),
        ).fetchall()
        latest_materialized = conn.execute(
            "SELECT MAX(created_at) FROM web_notification_items WHERE account_id=?",
            (account_id,),
        ).fetchone()
    state_counts = {state: 0 for state in ITEM_STATES}
    severity_counts = {severity: 0 for severity in SEVERITIES}
    unread = 0
    for state, severity, count in counts:
        if str(state) in state_counts:
            state_counts[str(state)] += int(count)
        if str(state) == "unread" and str(severity) in severity_counts:
            severity_counts[str(severity)] += int(count)
            unread += int(count)
    preflight = _scheduler_preflight_code() if _automation_enabled() else "NOTIFY_AUTOMATION_DISABLED"
    return envelope(
        True,
        "Tổng quan Inbox riêng của Web account hiện tại.",
        data=_boundary(
            counts=state_counts,
            unread_count=unread,
            unread_by_severity=severity_counts,
            # Scheduler receipts are service-global and may contain metadata
            # for other accounts. A customer sees only the time of their own
            # latest in-app materialization, never request IDs/run counters.
            last_materialized_at=str(latest_materialized[0]) if latest_materialized and latest_materialized[0] else None,
            scheduler_preflight=preflight or "ready",
            delivery="in_app_record_only",
        ),
        status_name="guarded" if preflight else "read_only",
    )


@router.get("/api/v1/inbox/items")
async def items(limit: int = 50, offset: int = 0, state: str = "all", account: dict = Depends(require_account)):
    _require_center()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = max(0, min(int(offset), MAX_LIST_OFFSET))
    state_filter = str(state or "all").strip().lower()
    if state_filter not in {*ITEM_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái Inbox không hợp lệ")
    clauses = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if state_filter != "all":
        clauses.append("state=?")
        params.append(state_filter)
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state, revision,
                       created_at, updated_at, read_at, dismissed_at
                FROM web_notification_items WHERE {' AND '.join(clauses)}
                ORDER BY CASE state WHEN 'unread' THEN 0 WHEN 'read' THEN 1 ELSE 2 END,
                         CASE severity WHEN 'urgent' THEN 0 ELSE 1 END, created_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    page_rows = rows[:bounded]
    has_more = len(rows) > bounded
    return envelope(
        True,
        "Bản ghi Inbox chỉ thuộc signed Web account hiện tại.",
        data=_boundary(
            items=[_item_public(tuple(row)) for row in page_rows],
            has_more=has_more,
            next_offset=bounded_offset + bounded if has_more else None,
            filters={"state": state_filter},
            pagination={"limit": bounded, "offset": bounded_offset, "returned": len(page_rows)},
            delivery="in_app_record_only",
        ),
        status_name="read_only",
    )


def _mutate_item(
    *, item_id: str, payload: InboxMutationRequest, request: Request, account: dict, action: str,
) -> dict[str, Any]:
    _require_center()
    item_id = _uuid(item_id, label="Mã Inbox")
    key = _idempotency_key(payload.idempotency_key)
    if action == "dismiss" and not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi dismiss bản ghi Inbox")
    fingerprint = _json_hash({"item_id": item_id, "expected_revision": payload.expected_revision, "action": action, "confirm": bool(payload.confirm)})
    account_id = str(account["id"])
    scope = f"web-notification:{account_id}:item:{item_id}:{action}"

    def operation(conn: Any) -> dict[str, Any]:
        row = conn.execute(
            """SELECT id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state, revision,
                      created_at, updated_at, read_at, dismissed_at
               FROM web_notification_items WHERE id=? AND account_id=?""",
            (item_id, account_id),
        ).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy bản ghi Inbox thuộc Web account hiện tại.", data=_boundary(), status_name="guarded", error_code="WEB_INBOX_ITEM_NOT_FOUND")
        current = tuple(row)
        if int(current[8]) != payload.expected_revision:
            return envelope(False, "Bản ghi Inbox đã có revision mới. Hãy tải lại trước khi tiếp tục.", data=_boundary(item=_item_public(current)), status_name="guarded", error_code="WEB_INBOX_ITEM_CONFLICT")
        current_state = str(current[7])
        if action == "read" and current_state == "dismissed":
            return envelope(False, "Bản ghi Inbox đã dismissed và không thể đánh dấu đã đọc.", data=_boundary(item=_item_public(current)), status_name="guarded", error_code="WEB_INBOX_ITEM_DISMISSED")
        if action == "dismiss" and current_state == "dismissed":
            return envelope(True, "Bản ghi Inbox đã được dismiss trước đó.", data=_boundary(item=_item_public(current)), status_name="completed")
        next_state = "read" if action == "read" else "dismissed"
        if current_state == next_state:
            return envelope(True, "Bản ghi Inbox đã ở trạng thái yêu cầu.", data=_boundary(item=_item_public(current)), status_name="completed")
        now = utc_now()
        next_revision = int(current[8]) + 1
        read_at = now if next_state == "read" else current[11]
        dismissed_at = now if next_state == "dismissed" else current[12]
        updated = conn.execute(
            """UPDATE web_notification_items SET state=?, revision=?, updated_at=?, read_at=?, dismissed_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (next_state, next_revision, now, read_at, dismissed_at, item_id, account_id, payload.expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            refreshed = conn.execute(
                """SELECT id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state, revision,
                          created_at, updated_at, read_at, dismissed_at
                   FROM web_notification_items WHERE id=? AND account_id=?""",
                (item_id, account_id),
            ).fetchone()
            return envelope(False, "Bản ghi Inbox đã thay đổi đồng thời. Hãy tải lại trước khi tiếp tục.", data=_boundary(item=_item_public(tuple(refreshed)) if refreshed else None), status_name="guarded", error_code="WEB_INBOX_ITEM_CONFLICT")
        conn.execute(
            """INSERT INTO web_notification_events
               (id, notification_id, account_id, actor_account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), item_id, account_id, account_id, action, next_state, next_revision, now),
        )
        _record_audit(
            conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action=f"web.inbox.item.{action}", request_id=_request_id(request), target=item_id,
            detail="web-owned in-app inbox state changed; no external notification or source mutation",
        )
        refreshed = conn.execute(
            """SELECT id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state, revision,
                      created_at, updated_at, read_at, dismissed_at
               FROM web_notification_items WHERE id=? AND account_id=?""",
            (item_id, account_id),
        ).fetchone()
        return envelope(True, "Đã cập nhật bản ghi Inbox riêng tư trong Web.", data=_boundary(item=_item_public(tuple(refreshed))), status_name="completed")

    return _idempotent(account_id=account_id, scope=scope, key=key, request_fingerprint=fingerprint, operation=operation)


@router.post("/api/v1/inbox/items/{item_id}/read")
async def read_item(item_id: str, payload: InboxMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    return _mutate_item(item_id=item_id, payload=payload, request=request, account=account, action="read")


@router.post("/api/v1/inbox/items/{item_id}/dismiss")
async def dismiss_item(item_id: str, payload: InboxMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    return _mutate_item(item_id=item_id, payload=payload, request=request, account=account, action="dismiss")
