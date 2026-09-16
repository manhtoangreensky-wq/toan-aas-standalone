"""Pure policy and synthesis engine for Customer CRM and Support (SPEC-04).

Canonical Authorities:
- CUSTOMER_MASTER = WEB_SQLITE
- SUPPORT_CASE_AUTHORITY = WEB_SQLITE
- TELEGRAM_IDENTITY = FEDERATED_IDENTITY_LINK
- WALLET_AUTHORITY = BOT_CORE
- JOB_AUTHORITY = BOT_CORE / CORE_BRIDGE_READ_MODEL
- PAYMENT_GATEWAY_AUTHORITY = PAYOS

Safety Invariants:
- WEB_DIRECT_WALLET_MUTATION = False
- WEB_DIRECT_BOT_DB_WRITE = False
- WEB_DIRECT_PAYOS_SETTLEMENT = False
- IDENTITY_RELINK_WRITE_ACTIONS = 0
- MANUAL_PAYMENT_SETTLEMENT_ACTIONS = 0
- UNKNOWN != 0, UNAVAILABLE != HEALTHY, EMPTY != UNKNOWN
"""

from __future__ import annotations

from typing import Any


from copyfast_finance_policy import (
    CUSTOMER_FINANCE_STATE_MAPPING_SHARED,
    PAYMENT_GATEWAY_AUTHORITY as FINANCE_PAYMENT_GATEWAY_AUTHORITY,
    TOPUP_REQUEST_AUTHORITY,
    WALLET_AUTHORITY as FINANCE_WALLET_AUTHORITY,
)

# Canonical Authorities
CUSTOMER_MASTER = "WEB_SQLITE"
SUPPORT_CASE_AUTHORITY = "WEB_SQLITE"
TELEGRAM_IDENTITY = "FEDERATED_IDENTITY_LINK"
WALLET_AUTHORITY = FINANCE_WALLET_AUTHORITY
JOB_AUTHORITY = "BOT_CORE / CORE_BRIDGE_READ_MODEL"
PAYMENT_GATEWAY_AUTHORITY = FINANCE_PAYMENT_GATEWAY_AUTHORITY
TOPUP_AUTHORITY = TOPUP_REQUEST_AUTHORITY

# Safety Invariants
WEB_DIRECT_WALLET_MUTATION = False
WEB_DIRECT_BOT_DB_WRITE = False
WEB_DIRECT_PAYOS_SETTLEMENT = False
IDENTITY_RELINK_WRITE_ACTIONS = 0
MANUAL_PAYMENT_SETTLEMENT_ACTIONS = 0

# Identity Link States
LINK_STATE_LINKED = "LINKED"
LINK_STATE_UNLINKED = "UNLINKED"
LINK_STATE_UNKNOWN = "UNKNOWN"
LINK_STATE_CONFLICT = "CONFLICT"
VALID_LINK_STATES = frozenset({
    LINK_STATE_LINKED,
    LINK_STATE_UNLINKED,
    LINK_STATE_UNKNOWN,
    LINK_STATE_CONFLICT,
})

# Operational Status Semantics
STATUS_EMPTY = "EMPTY"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_HEALTHY = "HEALTHY"
STATUS_ERROR = "ERROR"

# Support Constants
SUPPORT_CASE_STATUSES = frozenset({
    "new", "reviewing", "waiting_user", "waiting_provider",
    "refund_pending", "resolved", "closed",
})
SUPPORT_OPEN_STATUSES = frozenset({
    "new", "reviewing", "waiting_user", "waiting_provider", "refund_pending",
})
SUPPORT_PRIORITY_VALUES = frozenset({"low", "normal", "high", "urgent"})
CARE_TEAM_QUEUES = frozenset({
    "general", "technical", "account", "creative", "document", "product",
})

BANNED_TECHNICAL_PATTERNS = frozenset({
    "clean envelope",
    "sqlite authority",
    "core bridge",
    "toandaas_system.db",
    "web_session_secret",
    "webapp_autopilot_tick_secret",
})


def evaluate_federated_link_status(
    canonical_user_id: Any,
    *,
    has_conflict: bool = False,
    is_unknown: bool = False,
) -> str:
    """Evaluate canonical federated identity link status.

    - CONFLICT: incongruent or conflicting identity claims.
    - UNKNOWN: insufficient or unverified information.
    - LINKED: authoritative Telegram identity linked.
    - UNLINKED: no Telegram identity linked.
    """
    if has_conflict:
        return LINK_STATE_CONFLICT
    if is_unknown:
        return LINK_STATE_UNKNOWN
    val = str(canonical_user_id or "").strip()
    if val:
        return LINK_STATE_LINKED
    return LINK_STATE_UNLINKED


def synthesize_customer_crm_context(
    account: dict[str, Any],
    *,
    profile: dict[str, Any] | None = None,
    workspace_setup: dict[str, Any] | None = None,
    support_cases: list[dict[str, Any]] | None = None,
    topup_requests: list[dict[str, Any]] | None = None,
    link_evidence: dict[str, Any] | None = None,
    identity_conflict: bool = False,
    jobs_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesizes the bounded, truthful Customer CRM context answering the 7 canonical sections."""
    cases = support_cases or []
    topups = topup_requests or []
    prof = profile or {}
    setup = workspace_setup or {}

    canonical_uid = str(account.get("canonical_user_id") or "").strip() or None
    link_status = evaluate_federated_link_status(
        canonical_uid,
        has_conflict=identity_conflict,
    )

    # 1. OVERVIEW
    overview = {
        "customer_id": str(account.get("id") or ""),
        "display_name": str(account.get("display_name") or ""),
        "email": str(account.get("email") or ""),
        "status": "active" if bool(account.get("is_active", True)) else "locked",
        "account_type": str(account.get("account_type") or "standard"),
        "role": str(account.get("role") or "user"),
        "role_label": str(account.get("role_label") or "Khách hàng"),
        "password_login_enabled": bool(account.get("password_login_enabled", True)),
        "created_at": str(account.get("created_at") or ""),
        "updated_at": str(account.get("updated_at") or ""),
    }

    # 2. IDENTITY (Federated)
    identity = {
        "model": TELEGRAM_IDENTITY,
        "link_status": link_status,
        "telegram_user_id": canonical_uid,
        "link_evidence": link_evidence,
        "relink_write_actions": IDENTITY_RELINK_WRITE_ACTIONS,
    }

    # 3. SERVICE CONTEXT
    service_context = {
        "locale": str(prof.get("locale") or "vi"),
        "timezone": str(prof.get("timezone") or "Asia/Ho_Chi_Minh"),
        "avatar_style": str(prof.get("avatar_style") or "gradient"),
        "workspace_setup_state": str(setup.get("setup_state") or "not_started"),
        "workspace_role": str(setup.get("role") or ""),
        "workspace_goal": str(setup.get("goal") or ""),
    }

    # 4. SUPPORT
    open_cases = [c for c in cases if str(c.get("state") or "") in SUPPORT_OPEN_STATUSES]
    support = {
        "authority": SUPPORT_CASE_AUTHORITY,
        "total_cases": len(cases),
        "open_cases_count": len(open_cases),
        "recent_cases": cases[:5],
    }

    # 5. PAYMENTS / TOPUPS SUMMARY
    pending_topups = [t for t in topups if str(t.get("status") or "") == "pending_admin_review"]
    payments_topups = {
        "authority": TOPUP_REQUEST_AUTHORITY,
        "total_topup_requests": len(topups),
        "pending_review_count": len(pending_topups),
        "manual_settlement_actions": MANUAL_PAYMENT_SETTLEMENT_ACTIONS,
        "recent_requests": topups[:5],
        "share_canonical_authority": True,
        "customer_finance_state_mapping_shared": True,
    }

    # 6. WALLET SUMMARY (Read-through, never fake zero)
    wallet = {
        "data_source": WALLET_AUTHORITY,
        "status": STATUS_UNAVAILABLE,
        "balance_xu": None,
        "freshness": None,
        "direct_mutation_available": WEB_DIRECT_WALLET_MUTATION,
        "fake_zero_wallet_balance": 0,
    }

    # 7. JOBS SUMMARY (Read-through)
    if jobs_summary is not None:
        jobs = jobs_summary
    else:
        jobs = {
            "data_source": JOB_AUTHORITY,
            "status_authority": WALLET_AUTHORITY,
            "status": STATUS_UNAVAILABLE,
            "recent_jobs": [],
            "freshness": None,
            "mutation_available": False,
        }

    # 8. AUDIT / ACTION REQUIRED (Derived from concrete facts only)
    action_reasons: list[str] = []
    if identity_conflict:
        action_reasons.append("Xung đột định danh Telegram cần kiểm tra")
    if len(open_cases) > 0:
        action_reasons.append(f"{len(open_cases)} yêu cầu hỗ trợ đang mở")
    if len(pending_topups) > 0:
        action_reasons.append(f"{len(pending_topups)} yêu cầu nạp tiền chờ đối soát")
    if isinstance(jobs, dict):
        jobs_counts = jobs.get("counts") if isinstance(jobs.get("counts"), dict) else {}
        jobs_attention = jobs_counts.get("attention")
        if isinstance(jobs_attention, int) and jobs_attention > 0:
            action_reasons.append(f"{jobs_attention} tác vụ cần người vận hành xử lý")

    action_required = {
        "has_action": len(action_reasons) > 0,
        "action_count": len(action_reasons),
        "reasons": action_reasons,
    }

    return {
        "customer_id": str(account.get("id") or ""),
        "overview": overview,
        "identity": identity,
        "service_context": service_context,
        "support": support,
        "payments_topups": payments_topups,
        "wallet": wallet,
        "jobs": jobs,
        "action_required": action_required,
        "source": "web_accounts_redacted",
    }
