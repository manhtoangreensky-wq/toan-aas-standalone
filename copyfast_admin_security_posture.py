"""Redacted, read-only Security & Access Posture for the Web Admin ERP.

This is deliberately a narrow Web-owned observability surface.  It aggregates
only reviewed state columns from the standalone account/session security
tables after a signed local administrator is verified.  It never exposes an
account, session, factor, challenge, throttle, audit, identity, request or
credential record; only bounded counters and fixed configuration availability
states leave this module.

The posture is not a security control plane.  It has no role/session/MFA
mutations, no Bot or core-bridge call, and no provider, PayOS, wallet, job,
deployment or external-service operation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any

from fastapi import APIRouter, Depends, Request

from copyfast_auth import (
    email_verification_delivery_available,
    envelope,
    oauth_provider_status,
    require_admin,
)
from copyfast_db import read_transaction
from copyfast_mfa import totp_mfa_enabled, totp_mfa_runtime_available


router = APIRouter(prefix="/api/v1/admin/security-posture", tags=["Web Admin Security & Access Posture"])


POLICY_VERSION = "web_security_access_posture_v1"
MAX_INTEGRITY_SCAN_ROWS = 100_000
MAX_SAFE_COUNT = 1_000_000_000
# Unix epoch seconds are not record counters.  Keep the fixed bound beyond
# current production dates while rejecting a malformed SQLite REAL/text value
# or an implausibly distant expiry.
MAX_SAFE_EPOCH = 4_102_444_800  # 2100-01-01T00:00:00Z
ACTIVITY_WINDOW_HOURS = 24

_ACCOUNT_ROLES = frozenset({"admin", "support_manager", "support_operator", "user"})
_PRIVILEGED_ROLES = frozenset({"admin", "support_manager", "support_operator"})
_FACTOR_STATES = frozenset({"prepared", "active", "disabled", "superseded"})
_CHALLENGE_STATES = frozenset({"pending", "consumed", "locked", "superseded"})
_THROTTLE_ACTIONS = frozenset({"login", "register", "password_change"})
_AUDIT_OUTCOMES = frozenset({"ok", "denied", "failed", "guarded", "ignored", "noop"})
_AUDIT_COMPLETED_OUTCOMES = frozenset({"ok", "ignored", "noop"})
_AUDIT_GUARDED_OUTCOMES = frozenset({"denied", "failed", "guarded"})
_AUDIT_ACTION_GROUPS = {
    "auth.login": "sign_in",
    "auth.telegram_login_complete": "sign_in",
    "oauth.signin": "sign_in",
    "auth.mfa_enrollment_start": "mfa",
    "auth.mfa_enrollment_confirm": "mfa",
    "auth.mfa_login": "mfa",
    "auth.mfa_login_challenge": "mfa",
    "auth.mfa_disable": "mfa",
    "auth.security_password_change": "credential_change",
    "auth.password_recovery_confirm": "credential_change",
    "auth.email_verification_confirm": "credential_change",
    "auth.security_oauth_unlink": "credential_change",
    "auth.logout": "session_control",
    "auth.security_session_revoke": "session_control",
    "auth.security_sessions_revoke_others": "session_control",
}


def _enabled(name: str, *, default: bool) -> bool:
    return os.environ.get(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}


def _admin_erp_enabled() -> bool:
    """Honor the shared Web-admin discovery kill switch server-side."""

    return _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True)


def _safe_count(value: Any) -> int | None:
    """Accept only bounded native integer aggregate values."""

    if type(value) is not int or value < 0 or value > MAX_SAFE_COUNT:
        return None
    return value


def _safe_epoch(value: Any) -> int | None:
    """Accept a native, nonnegative UTC epoch in the reviewed time horizon."""

    if type(value) is not int or value < 0 or value > MAX_SAFE_EPOCH:
        return None
    return value


def _safe_flag(value: Any) -> bool | None:
    """SQLite booleans are stored as the exact integer values zero or one."""

    if type(value) is not int or value not in {0, 1}:
        return None
    return bool(value)


def _safe_state(value: Any, allowed: frozenset[str]) -> str | None:
    """Use closed persisted enums without normalizing or echoing malformed text."""

    return value if type(value) is str and value in allowed else None


def _safe_timestamp(value: Any, *, nullable: bool) -> datetime | None:
    """Validate stored timestamps without returning their raw representation."""

    if value is None:
        return None if nullable else None
    if type(value) is not str or not value or value != value.strip() or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _bounded_rows(conn: Any, query: str, params: tuple[Any, ...] = ()) -> tuple[list[Any], bool]:
    """Read a fixed reviewed projection, guarding rather than partially scanning."""

    rows = conn.execute(query, (*params, MAX_INTEGRITY_SCAN_ROWS + 1)).fetchall()
    return rows[:MAX_INTEGRITY_SCAN_ROWS], len(rows) > MAX_INTEGRITY_SCAN_ROWS


def _empty_access() -> dict[str, int | None]:
    return {
        "active_accounts": None,
        "inactive_accounts": None,
        "privileged_accounts": None,
        "admin_accounts": None,
        "support_manager_accounts": None,
        "support_operator_accounts": None,
        "unknown_role_accounts": None,
    }


def _empty_sessions() -> dict[str, int | None]:
    return {"active": None, "revoked_recent": None, "expired_unrevoked": None}


def _empty_mfa() -> dict[str, int | None]:
    return {
        "active_factors": None,
        "pending_enrollments": None,
        "locked_login_challenges": None,
        "pending_login_challenges": None,
        "active_recovery_codes": None,
    }


def _empty_throttle() -> dict[str, int | None]:
    return {
        "login_active_buckets": None,
        "register_active_buckets": None,
        "password_change_active_buckets": None,
    }


def _empty_activity() -> dict[str, int | None]:
    return {
        "window_hours": ACTIVITY_WINDOW_HOURS,
        "sign_in_completed": None,
        "sign_in_guarded": None,
        "mfa_completed": None,
        "mfa_guarded": None,
        "credential_change_completed": None,
        "credential_change_guarded": None,
        "session_control_completed": None,
        "session_control_guarded": None,
    }


def _mfa_runtime_state() -> str:
    """Expose a fixed MFA readiness state, never encryption configuration."""

    try:
        if not totp_mfa_enabled():
            return "disabled"
        return "enabled" if totp_mfa_runtime_available() else "misconfigured"
    except Exception:
        return "misconfigured"


def _email_delivery_state() -> str:
    """Report only whether the Web email-verification flow is safely available."""

    try:
        return "available" if email_verification_delivery_available() else "disabled_or_unavailable"
    except Exception:
        return "disabled_or_unavailable"


def _oauth_feature_flags() -> dict[str, bool]:
    """Project only the three supported browser OAuth feature booleans."""

    try:
        configured = oauth_provider_status()
    except Exception:
        configured = {}
    result: dict[str, bool] = {}
    for provider in ("google", "github", "apple"):
        value = configured.get(provider) if type(configured) is dict else None
        enabled = value.get("enabled") if type(value) is dict else None
        result[provider] = enabled is True
    return result


def _enforcement() -> dict[str, Any]:
    return {
        "mfa_runtime": _mfa_runtime_state(),
        "email_verification_delivery": _email_delivery_state(),
        "oauth_feature_flags": _oauth_feature_flags(),
    }


def _access_metrics(conn: Any) -> tuple[dict[str, int], bool]:
    rows, guarded = _bounded_rows(
        conn,
        "SELECT role_cache, is_active FROM web_accounts LIMIT ?",
    )
    metrics = {
        "active_accounts": 0,
        "inactive_accounts": 0,
        "privileged_accounts": 0,
        "admin_accounts": 0,
        "support_manager_accounts": 0,
        "support_operator_accounts": 0,
        "unknown_role_accounts": 0,
    }
    for row in rows:
        try:
            role, is_active = tuple(row)
        except (TypeError, ValueError):
            guarded = True
            continue
        safe_role = _safe_state(role, _ACCOUNT_ROLES)
        safe_active = _safe_flag(is_active)
        if safe_role is None or safe_active is None:
            guarded = True
            if safe_role is None:
                metrics["unknown_role_accounts"] += 1
            continue
        metrics["active_accounts" if safe_active else "inactive_accounts"] += 1
        if safe_role in _PRIVILEGED_ROLES:
            metrics["privileged_accounts"] += 1
            metrics[f"{safe_role}_accounts"] += 1
    return metrics, guarded


def _session_metrics(conn: Any, *, now: datetime) -> tuple[dict[str, int], bool]:
    rows, guarded = _bounded_rows(
        conn,
        "SELECT revoked_at, expires_at FROM web_sessions LIMIT ?",
    )
    metrics = {"active": 0, "revoked_recent": 0, "expired_unrevoked": 0}
    recent_cutoff = now - timedelta(hours=ACTIVITY_WINDOW_HOURS)
    for row in rows:
        try:
            revoked_at, expires_at = tuple(row)
        except (TypeError, ValueError):
            guarded = True
            continue
        expiry = _safe_timestamp(expires_at, nullable=False)
        revoked = _safe_timestamp(revoked_at, nullable=True)
        if expiry is None or (revoked_at is not None and revoked is None) or (revoked and revoked > now):
            guarded = True
            continue
        if revoked is not None:
            if revoked >= recent_cutoff:
                metrics["revoked_recent"] += 1
        elif expiry > now:
            metrics["active"] += 1
        else:
            metrics["expired_unrevoked"] += 1
    return metrics, guarded


def _mfa_metrics(conn: Any) -> tuple[dict[str, int], bool]:
    factor_rows, factors_guarded = _bounded_rows(
        conn,
        "SELECT state FROM web_totp_factors LIMIT ?",
    )
    recovery_rows, recovery_guarded = _bounded_rows(
        conn,
        "SELECT used_at, invalidated_at FROM web_totp_recovery_codes LIMIT ?",
    )
    challenge_rows, challenges_guarded = _bounded_rows(
        conn,
        "SELECT state, expires_at FROM web_totp_login_challenges LIMIT ?",
    )
    metrics = {
        "active_factors": 0,
        "pending_enrollments": 0,
        "locked_login_challenges": 0,
        "pending_login_challenges": 0,
        "active_recovery_codes": 0,
    }
    guarded = factors_guarded or recovery_guarded or challenges_guarded
    for row in factor_rows:
        try:
            (state,) = tuple(row)
        except (TypeError, ValueError):
            guarded = True
            continue
        safe_state = _safe_state(state, _FACTOR_STATES)
        if safe_state is None:
            guarded = True
            continue
        if safe_state == "active":
            metrics["active_factors"] += 1
        elif safe_state == "prepared":
            metrics["pending_enrollments"] += 1
    for row in recovery_rows:
        try:
            used_at, invalidated_at = tuple(row)
        except (TypeError, ValueError):
            guarded = True
            continue
        safe_used = _safe_timestamp(used_at, nullable=True)
        safe_invalidated = _safe_timestamp(invalidated_at, nullable=True)
        if (used_at is not None and safe_used is None) or (invalidated_at is not None and safe_invalidated is None):
            guarded = True
            continue
        if safe_used is None and safe_invalidated is None:
            metrics["active_recovery_codes"] += 1
    for row in challenge_rows:
        try:
            state, expires_at = tuple(row)
        except (TypeError, ValueError):
            guarded = True
            continue
        safe_state = _safe_state(state, _CHALLENGE_STATES)
        expiry = _safe_timestamp(expires_at, nullable=False)
        if safe_state is None or expiry is None:
            guarded = True
            continue
        if safe_state == "locked":
            metrics["locked_login_challenges"] += 1
        elif safe_state == "pending":
            metrics["pending_login_challenges"] += 1
    return metrics, guarded


def _throttle_metrics(conn: Any, *, now_epoch: int) -> tuple[dict[str, int], bool]:
    rows, guarded = _bounded_rows(
        conn,
        "SELECT action, expires_at_epoch FROM web_auth_throttle_buckets LIMIT ?",
    )
    metrics = {
        "login_active_buckets": 0,
        "register_active_buckets": 0,
        "password_change_active_buckets": 0,
    }
    for row in rows:
        try:
            action, expires_at_epoch = tuple(row)
        except (TypeError, ValueError):
            guarded = True
            continue
        safe_action = _safe_state(action, _THROTTLE_ACTIONS)
        expiry = _safe_epoch(expires_at_epoch)
        if safe_action is None or expiry is None:
            guarded = True
            continue
        if expiry > now_epoch:
            metrics[f"{safe_action}_active_buckets"] += 1
    return metrics, guarded


def _activity_metrics(conn: Any, *, now: datetime) -> tuple[dict[str, int], bool]:
    """Aggregate only known auth/MFA/session actions, never generic audit rows."""

    actions = tuple(sorted(_AUDIT_ACTION_GROUPS))
    placeholders = ", ".join("?" for _ in actions)
    rows, guarded = _bounded_rows(
        conn,
        f"SELECT action, outcome, created_at FROM web_audit_events WHERE action IN ({placeholders}) LIMIT ?",
        actions,
    )
    metrics = {
        "window_hours": ACTIVITY_WINDOW_HOURS,
        "sign_in_completed": 0,
        "sign_in_guarded": 0,
        "mfa_completed": 0,
        "mfa_guarded": 0,
        "credential_change_completed": 0,
        "credential_change_guarded": 0,
        "session_control_completed": 0,
        "session_control_guarded": 0,
    }
    cutoff = now - timedelta(hours=ACTIVITY_WINDOW_HOURS)
    tolerated_future = now + timedelta(minutes=5)
    for row in rows:
        try:
            action, outcome, created_at = tuple(row)
        except (TypeError, ValueError):
            guarded = True
            continue
        group = _AUDIT_ACTION_GROUPS.get(action) if type(action) is str else None
        safe_outcome = _safe_state(outcome, _AUDIT_OUTCOMES)
        occurred_at = _safe_timestamp(created_at, nullable=False)
        if group is None or safe_outcome is None or occurred_at is None or occurred_at > tolerated_future:
            guarded = True
            continue
        if occurred_at < cutoff:
            continue
        if safe_outcome in _AUDIT_COMPLETED_OUTCOMES:
            metrics[f"{group}_completed"] += 1
        elif safe_outcome in _AUDIT_GUARDED_OUTCOMES:
            metrics[f"{group}_guarded"] += 1
        else:
            guarded = True
    return metrics, guarded


def _boundaries() -> list[str]:
    return [
        "Chỉ hiển thị aggregate Web-native; không có account, email, session, token, secret, IP hoặc audit detail.",
        "Trang chỉ đọc; không cấp role, thu hồi session, reset MFA hoặc thay đổi credential.",
        "Không gọi Bot/Core Bridge, provider, PayOS, ví Xu, job, webhook hoặc deploy.",
    ]


def _payload(
    *,
    enforcement: dict[str, Any],
    access: dict[str, int | None],
    sessions: dict[str, int | None],
    mfa: dict[str, int | None],
    throttle: dict[str, int | None],
    activity: dict[str, int | None],
    integrity_guarded: bool,
) -> dict[str, Any]:
    return {
        "source": "web_security_access_posture_v1",
        "policy_version": POLICY_VERSION,
        "read_only": True,
        "integrity_guarded": bool(integrity_guarded),
        "enforcement": enforcement,
        "access": access,
        "sessions": sessions,
        "mfa": mfa,
        "throttle": throttle,
        "security_activity": activity,
        "boundaries": _boundaries(),
    }


def _guarded_payload() -> dict[str, Any]:
    return _payload(
        enforcement=_enforcement(),
        access=_empty_access(),
        sessions=_empty_sessions(),
        mfa=_empty_mfa(),
        throttle=_empty_throttle(),
        activity=_empty_activity(),
        integrity_guarded=True,
    )


def _posture_payload() -> tuple[dict[str, Any], bool]:
    """Read reviewed projections and hide all database metrics if any is unsafe."""

    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        with read_transaction() as conn:
            access, access_guarded = _access_metrics(conn)
            sessions, sessions_guarded = _session_metrics(conn, now=now)
            mfa, mfa_guarded = _mfa_metrics(conn)
            throttle, throttle_guarded = _throttle_metrics(conn, now_epoch=int(now.timestamp()))
            activity, activity_guarded = _activity_metrics(conn, now=now)
    except Exception:
        return _guarded_payload(), True
    integrity_guarded = any((access_guarded, sessions_guarded, mfa_guarded, throttle_guarded, activity_guarded))
    if integrity_guarded:
        return _guarded_payload(), True
    return (
        _payload(
            enforcement=_enforcement(),
            access=access,
            sessions=sessions,
            mfa=mfa,
            throttle=throttle,
            activity=activity,
            integrity_guarded=False,
        ),
        False,
    )


@router.get("/summary")
async def summary(request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Return the redacted Web-only security and access posture."""

    del request, account
    # Deliberately evaluate this gate before opening the database read.  A
    # disabled ERP directory must not disclose even aggregate account posture.
    if not _admin_erp_enabled():
        return envelope(
            True,
            "Admin ERP trên Web đang tạm khóa; Security & Access Posture không đọc dữ liệu.",
            data=_guarded_payload(),
            status_name="guarded",
            error_code="WEBAPP_ADMIN_ERP_DISABLED",
        )
    data, integrity_guarded = _posture_payload()
    if integrity_guarded:
        return envelope(
            True,
            "Security & Access Posture đang bảo vệ dữ liệu chưa xác minh; không hiển thị số liệu một phần.",
            data=data,
            status_name="guarded",
            error_code="ADMIN_SECURITY_ACCESS_POSTURE_DATA_GUARDED",
        )
    return envelope(
        True,
        "Đã nạp Security & Access Posture chỉ đọc với số liệu Web đã được tổng hợp và redaction.",
        data=data,
        status_name="read_only",
    )
