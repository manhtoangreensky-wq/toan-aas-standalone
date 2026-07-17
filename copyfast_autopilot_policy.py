"""Deterministic, side-effect-free policy for Operations Autopilot.

This module deliberately decides only *metadata*: SLA, risk and whether an
action is eligible for a later safe playbook.  It never changes a support
case, replies to a customer, invokes any external system, handles money or
claims that an issue is resolved.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any


CASE_CATEGORIES = frozenset({
    "payment_topup", "image_error", "video_error", "document_pdf",
    "package_combo", "refund", "feature_request", "lead_consulting",
    "general_support", "service_consulting", "premium_lead",
    "custom_bot_lead", "other",
})
CASE_PRIORITIES = frozenset({"low", "normal", "high", "urgent"})
CASE_STATES = frozenset({
    "new", "reviewing", "waiting_user", "waiting_provider",
    "refund_pending", "resolved", "closed",
})

FINANCIAL_CATEGORIES = frozenset({"payment_topup", "refund", "package_combo"})
EXTERNAL_DEPENDENCY_CATEGORIES = frozenset({"image_error", "video_error", "document_pdf"})
AUTO_PLAYBOOKS = frozenset({
    "health_probe", "support_triage_metadata", "terminal_case_metadata_reconciliation",
    # This only moves a Web-owned approval record past its already persisted
    # expiry timestamp.  It cannot perform the action named by that record.
    "approval_expiry_reconciliation",
    # Runtime Reliability only materializes a bounded internal follow-up row
    # from already-sanitized Web signals / Support triage. It is not a repair,
    # notification, provider retry or customer-contact executor.
    "reliability_followup_metadata",
    # A bounded Web-only convergence pass can close a previously breached
    # *ordinary Web support* incident after several fresh healthy scheduler
    # observations. It cannot close the source case or any financial/external
    # dependency incident, and it never contacts a customer.
    "incident_recovery_reconciliation",
})
APPROVAL_ONLY_PLAYBOOKS = frozenset({
    "wallet_adjustment", "payment_finalize", "payment_refund", "provider_retry",
    "bot_job_retry", "customer_reply", "external_notification", "publish",
    "role_change", "secret_change", "delete_data", "backup_restore", "deploy",
})
PRIORITY_SLA_MINUTES = {"low": 1_440, "normal": 480, "high": 120, "urgent": 30}
INCIDENT_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


def _enum(value: Any, permitted: frozenset[str], *, fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in permitted else fallback


def complaint_triage(*, category: Any, priority: Any, state: Any, age_minutes: Any) -> dict[str, Any]:
    """Classify a Support Desk case without looking at/storing its narrative."""
    resolved_category = _enum(category, CASE_CATEGORIES, fallback="other")
    resolved_priority = _enum(priority, CASE_PRIORITIES, fallback="normal")
    resolved_state = _enum(state, CASE_STATES, fallback="new")
    try:
        age = max(0, min(int(age_minutes), 10_000_000))
    except (TypeError, ValueError):
        age = 0
    sla_minutes = PRIORITY_SLA_MINUTES[resolved_priority]
    terminal = resolved_state in {"resolved", "closed"}
    if resolved_category in FINANCIAL_CATEGORIES or resolved_state == "refund_pending":
        risk = "financial"
        required_role = "support_manager"
        disposition = "awaiting_operator"
    elif resolved_category in EXTERNAL_DEPENDENCY_CATEGORIES or resolved_state == "waiting_provider":
        risk = "external_dependency"
        required_role = "support_operator"
        disposition = "awaiting_operator"
    elif resolved_category == "other":
        # An unclassified complaint is never silently treated as ordinary
        # support.  Preserve a conservative human-review posture until a
        # staff member selects a known, audited category.
        risk = "unclassified"
        required_role = "support_operator"
        disposition = "awaiting_operator"
    else:
        risk = "web_support"
        required_role = "support_operator"
        disposition = "monitored"
    if terminal:
        disposition = "terminal_monitoring"
    if terminal:
        sla_status = "terminal"
    elif age >= sla_minutes:
        sla_status = "breached"
    elif age * 4 >= sla_minutes * 3:
        sla_status = "at_risk"
    else:
        sla_status = "within_target"
    return {
        "category": resolved_category,
        "priority": resolved_priority,
        "state": resolved_state,
        "age_minutes": age,
        "sla_minutes": sla_minutes,
        "sla_status": sla_status,
        "risk": risk,
        "disposition": disposition,
        "required_role": required_role,
        "eligible_playbook": "support_triage_metadata",
        "changes_case_state": False,
        "creates_customer_reply": False,
        "calls_external_system": False,
        "mutates_money": False,
    }


def incident_fingerprint(*, kind: Any, scope: Any, error_code: Any = "", secret: str) -> str:
    """Return a keyed opaque fingerprint without retaining raw diagnostics.

    A plain digest of a low-entropy support ID or status code can be guessed
    offline.  Requiring an operations-only HMAC key makes the stored marker
    useful for deduplication without turning it into a lookup oracle.
    """
    normalized_kind = str(kind or "").strip().lower()
    if not INCIDENT_KIND_PATTERN.fullmatch(normalized_kind):
        raise ValueError("Loại incident không hợp lệ")
    normalized_scope = re.sub(r"\s+", " ", str(scope or "")).strip().lower()[:160]
    normalized_code = re.sub(r"\s+", " ", str(error_code or "")).strip().lower()[:160]
    if not normalized_scope:
        raise ValueError("Scope incident không hợp lệ")
    key = str(secret or "").encode("utf-8")
    if len(key) < 32:
        raise ValueError("Autopilot incident secret phải có ít nhất 32 ký tự")
    return hmac.new(
        key,
        f"{normalized_kind}\n{normalized_scope}\n{normalized_code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def safe_playbook_allowed(playbook: Any, *, feature_enabled: bool, remediation_enabled: bool) -> bool:
    name = str(playbook or "").strip().lower()
    return bool(feature_enabled and remediation_enabled and name in AUTO_PLAYBOOKS and name not in APPROVAL_ONLY_PLAYBOOKS)


def retry_delay_seconds(attempt: Any) -> int:
    """Capped deterministic backoff; attempt one waits one minute."""
    try:
        number = int(attempt)
    except (TypeError, ValueError):
        number = 1
    number = max(1, min(number, 10))
    return min(60 * (2 ** (number - 1)), 900)


def may_auto_close_incident(*, healthy_streak: Any, required_streak: Any, has_pending_approval: bool) -> bool:
    try:
        observed = int(healthy_streak)
        required = int(required_streak)
    except (TypeError, ValueError):
        return False
    return bool(not has_pending_approval and required >= 1 and observed >= required)
