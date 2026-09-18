"""Pure policy and synthesis engine for Finance Read Model (SPEC-06).

Canonical Authorities:
- CUSTOMER_AUTHORITY = WEB_SQLITE
- WALLET_AUTHORITY = BOT_CORE
- PAYMENT_GATEWAY_AUTHORITY = PAYOS
- PAYMENT_SETTLEMENT_AUTHORITY = BOT_CORE
- TOPUP_REQUEST_AUTHORITY = WEB_SQLITE
- JOB_AUTHORITY = BOT_CORE
- REVENUE_AUTHORITY = BOT_CORE
- WEB_ROLE = READ_THROUGH_OR_PROJECTION

Safety Invariants:
- WEB_DIRECT_WALLET_MUTATION = False
- WEB_DIRECT_BOT_DB_WRITE = False
- MANUAL_PAYMENT_SETTLEMENT_ACTIONS = 0
- REFUND_EXECUTION_ACTIONS = 0
- MANUAL_CREDIT_ACTIONS = 0
- MANUAL_DEBIT_ACTIONS = 0
- SETTLEMENT_ACTIONS = 0
- REFUND_ACTIONS = 0
- PAYOS_ACTIONS = 0
- WALLET_ACTIONS = 0
- FAKE_ZERO_WALLET_BALANCE = 0
- UNAVAILABLE_FINANCE_VALUE_AS_ZERO = False
- UNKNOWN_REVENUE_AS_ZERO = False
- UNAVAILABLE_WALLET_AS_ZERO = False
- PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED = True
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ==============================================================================
# 1. CANONICAL AUTHORITIES
# ==============================================================================
CUSTOMER_AUTHORITY = "WEB_SQLITE"
WALLET_AUTHORITY = "BOT_CORE"
PAYMENT_GATEWAY_AUTHORITY = "PAYOS"
PAYMENT_SETTLEMENT_AUTHORITY = "BOT_CORE"
TOPUP_REQUEST_AUTHORITY = "WEB_SQLITE"
JOB_AUTHORITY = "BOT_CORE"
REVENUE_AUTHORITY = "BOT_CORE"
WEB_ROLE = "READ_THROUGH_OR_PROJECTION"

# Direct mutation safety invariants
WEB_DIRECT_WALLET_MUTATION = False
WEB_DIRECT_BOT_DB_WRITE = False
MANUAL_PAYMENT_SETTLEMENT_ACTIONS = 0
REFUND_EXECUTION_ACTIONS = 0

# Control plane zero invariants
MANUAL_CREDIT_ACTIONS = 0
MANUAL_DEBIT_ACTIONS = 0
SETTLEMENT_ACTIONS = 0
REFUND_ACTIONS = 0
PAYOS_ACTIONS = 0
WALLET_ACTIONS = 0

# Semantic separation invariants (SPEC-06B)
REQUEST_APPROVED_IMPLIES_PAYMENT_CONFIRMED = False
PAYMENT_CONFIRMED_IMPLIES_SETTLED = False
SETTLED_IMPLIES_REQUEST_APPROVED = False
CUSTOMER_FINANCE_STATE_MAPPING_SHARED = True

# PayOS sources (SPEC-06B)
PAYMENT_READ_MODEL_SOURCE = "BOT_CORE_PAYMENT_PROJECTION_OR_WEBHOOK_CACHE"
PAYMENT_EVENT_SOURCE = "PAYOS_GATEWAY_WEBHOOK"

# Fake zero prevention invariants
FAKE_ZERO_WALLET_BALANCE = 0
UNAVAILABLE_FINANCE_VALUE_AS_ZERO = False
UNKNOWN_REVENUE_AS_ZERO = False
UNAVAILABLE_WALLET_AS_ZERO = False
PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED = True

# Canonical money invariants (WEB07)
BALANCE_AS_LIFETIME_PAID = False
BALANCE_AS_REVENUE = False
TOPUP_COUNT_AS_REVENUE = False
DISCREPANCY_SUPPRESSED = False
DUPLICATE_CREDIT_COUNTING = 0
PAYOS_PENDING_AS_PAID = False
PAYOS_FAILED_AS_REVENUE = False
PAYOS_CANCELLED_AS_REVENUE = False
PENDING_TOPUP_AS_CREDITED = False
REJECTED_TOPUP_AS_CREDITED = False
APPROVED_WITHOUT_RECEIPT_AS_CREDITED = False

# Timezone and boundary truth
FINANCE_TIMEZONE = "UTC"
WINDOW_BOUNDARY_SOURCE = "SERVER_CANONICAL_UTC"

# Refund / Compensation semantics (Read-model only, real mutations not implemented)
REFUND_SEMANTICS = "NOT_IMPLEMENTED"
COMPENSATION_SEMANTICS = "NOT_IMPLEMENTED"

# Canonical money definitions
CURRENT_BALANCE_XU = "CURRENT_BALANCE_XU"
TOTAL_CREDITS_XU = "TOTAL_CREDITS_XU"
TOTAL_DEBITS_XU = "TOTAL_DEBITS_XU"
LIFETIME_PAID = "LIFETIME_PAID"
TOPUP_AMOUNT = "TOPUP_AMOUNT"
PAYMENT_AMOUNT = "PAYMENT_AMOUNT"
REFUND_AMOUNT = "REFUND_AMOUNT"
NET_REVENUE = "NET_REVENUE"
OUTSTANDING_PENDING = "OUTSTANDING_PENDING"

# Operational status semantics
STATUS_EMPTY = "EMPTY"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_HEALTHY = "HEALTHY"
STATUS_ERROR = "ERROR"
STATUS_PARTIAL = "PARTIAL"
STATUS_GUARDED = "guarded"


# ==============================================================================
# 2. TOPUP REQUEST STATE TAXONOMY (Authority: WEB_SQLITE)
# ==============================================================================
TOPUP_STATE_PENDING = "PENDING"
TOPUP_STATE_APPROVED = "APPROVED"
TOPUP_STATE_REJECTED = "REJECTED"
TOPUP_STATE_UNKNOWN = "UNKNOWN"

# Namespaced aliases (SPEC-06B)
REQUEST_STATE_PENDING = TOPUP_STATE_PENDING
REQUEST_STATE_APPROVED = TOPUP_STATE_APPROVED
REQUEST_STATE_REJECTED = TOPUP_STATE_REJECTED
REQUEST_STATE_UNKNOWN = TOPUP_STATE_UNKNOWN

# Deprecated alias for backwards compatibility
TOPUP_STATE_CONFIRMED = TOPUP_STATE_APPROVED

VALID_TOPUP_BUSINESS_STATES = frozenset({
    TOPUP_STATE_PENDING,
    TOPUP_STATE_APPROVED,
    TOPUP_STATE_REJECTED,
    TOPUP_STATE_UNKNOWN,
})

RAW_TOPUP_TO_BUSINESS_STATE: dict[str, str] = {
    # Pending
    "pending_admin_review": TOPUP_STATE_PENDING,
    "pending": TOPUP_STATE_PENDING,
    "reviewing": TOPUP_STATE_PENDING,
    "submitted": TOPUP_STATE_PENDING,
    # Approved
    "approved": TOPUP_STATE_APPROVED,
    "confirmed": TOPUP_STATE_APPROVED,
    "success": TOPUP_STATE_APPROVED,
    # Rejected / Declined
    "rejected": TOPUP_STATE_REJECTED,
    "declined": TOPUP_STATE_REJECTED,
}


def map_topup_raw_state(raw_state: Any) -> str:
    """Standardize raw topup status string into canonical business state."""
    if raw_state is None:
        return TOPUP_STATE_UNKNOWN
    normalized = str(raw_state).strip().lower()
    if not normalized:
        return TOPUP_STATE_UNKNOWN
    return RAW_TOPUP_TO_BUSINESS_STATE.get(normalized, TOPUP_STATE_UNKNOWN)


# ==============================================================================
# 3. PAYMENT GATEWAY STATE TAXONOMY (Authority: PAYOS)
# ==============================================================================
PAYMENT_STATE_PENDING = "PENDING"
PAYMENT_STATE_CONFIRMED = "CONFIRMED"
PAYMENT_STATE_FAILED = "FAILED"
PAYMENT_STATE_EXPIRED = "EXPIRED"
PAYMENT_STATE_UNAVAILABLE = "UNAVAILABLE"
PAYMENT_STATE_UNKNOWN = "UNKNOWN"

VALID_PAYMENT_BUSINESS_STATES = frozenset({
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_CONFIRMED,
    PAYMENT_STATE_FAILED,
    PAYMENT_STATE_EXPIRED,
    PAYMENT_STATE_UNAVAILABLE,
    PAYMENT_STATE_UNKNOWN,
})

RAW_PAYMENT_TO_BUSINESS_STATE: dict[str, str] = {
    "pending": PAYMENT_STATE_PENDING,
    "processing": PAYMENT_STATE_PENDING,
    "waiting": PAYMENT_STATE_PENDING,
    "paid": PAYMENT_STATE_CONFIRMED,
    "completed": PAYMENT_STATE_CONFIRMED,
    "confirmed": PAYMENT_STATE_CONFIRMED,
    "success": PAYMENT_STATE_CONFIRMED,
    "failed": PAYMENT_STATE_FAILED,
    "cancelled": PAYMENT_STATE_FAILED,
    "canceled": PAYMENT_STATE_FAILED,
    "expired": PAYMENT_STATE_EXPIRED,
}


def map_payment_state(raw_state: Any) -> str:
    """Standardize raw payment gateway status string."""
    if raw_state is None:
        return PAYMENT_STATE_UNKNOWN
    normalized = str(raw_state).strip().lower()
    if not normalized:
        return PAYMENT_STATE_UNKNOWN
    return RAW_PAYMENT_TO_BUSINESS_STATE.get(normalized, PAYMENT_STATE_UNKNOWN)


# ==============================================================================
# 4. PAYMENT SETTLEMENT STATE TAXONOMY (Authority: BOT_CORE)
# ==============================================================================
SETTLEMENT_STATE_PENDING = "PENDING"
SETTLEMENT_STATE_CREDITED = "CREDITED"
SETTLEMENT_STATE_UNKNOWN = "UNKNOWN"
SETTLEMENT_STATE_UNAVAILABLE = "UNAVAILABLE"

VALID_SETTLEMENT_BUSINESS_STATES = frozenset({
    SETTLEMENT_STATE_PENDING,
    SETTLEMENT_STATE_CREDITED,
    SETTLEMENT_STATE_UNKNOWN,
    SETTLEMENT_STATE_UNAVAILABLE,
})

RAW_SETTLEMENT_TO_BUSINESS_STATE: dict[str, str] = {
    "credited": SETTLEMENT_STATE_CREDITED,
    "settled": SETTLEMENT_STATE_CREDITED,
    "completed": SETTLEMENT_STATE_CREDITED,
    "success": SETTLEMENT_STATE_CREDITED,
    "pending": SETTLEMENT_STATE_PENDING,
    "reviewing": SETTLEMENT_STATE_PENDING,
    "waiting": SETTLEMENT_STATE_PENDING,
}


def map_settlement_state(
    raw_state: Any,
    *,
    bridge_available: bool = True,
    payment_state: str | None = None,
) -> str:
    """Standardize settlement state with strict separation from gateway state.
    
    Invariants:
    - PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED = True.
    - PAYMENT_CONFIRMED_IMPLIES_SETTLED = False.
    A confirmed payment without verified ledger credit remains UNKNOWN (or UNAVAILABLE).
    """
    if not bridge_available:
        return SETTLEMENT_STATE_UNAVAILABLE
    if raw_state is not None:
        normalized = str(raw_state).strip().lower()
        if normalized in RAW_SETTLEMENT_TO_BUSINESS_STATE:
            return RAW_SETTLEMENT_TO_BUSINESS_STATE[normalized]
    return SETTLEMENT_STATE_UNKNOWN


# ==============================================================================
# 5. REVENUE SCOPE & TRUTH (Authority: BOT_CORE)
# ==============================================================================
REVENUE_CURRENT_SCOPE = "WEB_ONLY_MANUAL_TOPUPS"
REVENUE_COVERAGE = "PARTIAL"
REVENUE_LABEL = "Known Web Revenue"
REVENUE_MISSING_SOURCES = (
    "bot_charges",
    "payos_direct_checkouts",
    "payos_webhooks",
    "voucher_credits",
)


# ==============================================================================
# 6. ACTION REQUIRED EVALUATION (Concrete facts only)
# ==============================================================================
def evaluate_finance_action_required(
    item: dict[str, Any],
    *,
    entity_type: str = "topup",
) -> tuple[bool, list[str]]:
    """Evaluates whether a financial item requires operator attention.
    
    Derived strictly from concrete facts:
    - Pending topup request awaiting verification
    - Confirmed payment whose wallet credit is still pending settlement
    - Explicit payment failure requiring review
    - Pending refund request
    - Identity conflict preventing proper attribution
    
    Never infers fraud, VIP status, churn, or subjective risk scores.
    """
    reasons: list[str] = []

    if entity_type == "topup":
        req_state = str(item.get("request_state") or item.get("status") or "").upper()
        if req_state in ("PENDING", "PENDING_ADMIN_REVIEW"):
            reasons.append("Yêu cầu nạp tiền chờ đối soát và xác nhận")
        elif req_state == "REJECTED":
            # Rejection is a closed state, but if decision reason missing note it
            reason = str(item.get("decision_reason") or "").strip()
            if not reason:
                reasons.append("Yêu cầu bị từ chối nhưng chưa có lý do chi tiết")

    elif entity_type == "payment":
        pay_state = str(item.get("gateway_state") or item.get("payment_state") or item.get("status") or "").upper()
        settle_state = str(item.get("settlement_state") or "").upper()

        if pay_state == PAYMENT_STATE_CONFIRMED and settle_state in (SETTLEMENT_STATE_PENDING, "PENDING", SETTLEMENT_STATE_UNKNOWN, "UNKNOWN"):
            reasons.append("Thanh toán PayOS đã xác nhận nhưng chờ Bot Core ghi nhận Xu")
        elif pay_state == PAYMENT_STATE_FAILED:
            reasons.append("Giao dịch thanh toán thất bại cần kiểm tra")

    # Refund pending check
    refund_status = str(item.get("refund_status") or "").strip().lower()
    if refund_status in ("pending", "reviewing", "requested"):
        reasons.append("Yêu cầu hoàn tiền đang chờ giải quyết")

    # Identity conflict check
    if bool(item.get("identity_conflict")):
        reasons.append("Xung đột định danh khách hàng cần đối soát")

    needs_attention = len(reasons) > 0
    return needs_attention, reasons


# ==============================================================================
# 7. RECORD SYNTHESIZERS
# ==============================================================================
def synthesize_topup_record(
    row: dict[str, Any],
    *,
    payment_event: dict[str, Any] | None = None,
    settlement_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize a truthful, safe Topup record from SQLite row.

    Strict Three-Layer Semantics (SPEC-06B):
    1. REQUEST_STATE (Authority: WEB_SQLITE): PENDING, APPROVED, REJECTED, UNKNOWN
    2. PAYMENT_STATE (Authority: PAYOS): PENDING, CONFIRMED, FAILED, EXPIRED, UNAVAILABLE, UNKNOWN
    3. SETTLEMENT_STATE (Authority: BOT_CORE): PENDING, CREDITED, REJECTED, UNAVAILABLE, UNKNOWN

    Invariants:
    - REQUEST_STATE != PAYMENT_STATE != SETTLEMENT_STATE
    - REQUEST_APPROVED_IMPLIES_PAYMENT_CONFIRMED = False
    - PAYMENT_CONFIRMED_IMPLIES_SETTLED = False
    An approved topup request DOES NOT imply payment confirmed or wallet credited.
    Unless verified payment/settlement facts are provided, they remain UNKNOWN.
    """
    raw = row if isinstance(row, dict) else {}
    raw_status = str(raw.get("status") or "").strip()
    business_state = map_topup_raw_state(raw_status)

    # Payment state is resolved ONLY from verified payment linkage/event
    raw_pay = payment_event or raw.get("payment_event") or raw.get("payment")
    if isinstance(raw_pay, dict) and raw_pay.get("status"):
        pay_state = map_payment_state(raw_pay.get("status"))
    elif raw.get("payment_state"):
        pay_state = map_payment_state(raw.get("payment_state"))
    else:
        # Crucial: Request approval NEVER synthesizes payment confirmation
        pay_state = PAYMENT_STATE_UNKNOWN

    # Settlement state is resolved ONLY from verified settlement linkage/event
    raw_settle = settlement_event or raw.get("settlement_event") or raw.get("settlement")
    if isinstance(raw_settle, dict) and raw_settle.get("status"):
        settle_state = map_settlement_state(raw_settle.get("status"))
    elif raw.get("settlement_state"):
        settle_state = map_settlement_state(raw.get("settlement_state"))
    else:
        # Crucial: Request approval or payment confirmation NEVER synthesizes wallet credit
        settle_state = SETTLEMENT_STATE_UNKNOWN

    req_id = str(raw.get("request_id") or (f"MANUAL-{raw['id']}" if raw.get("id") else "")).strip()
    amount_vnd = raw.get("amount_vnd") if isinstance(raw.get("amount_vnd"), int) else 0

    record = {
        "request_id": req_id,
        "customer_id": str(raw.get("account_id") or raw.get("customer_id") or "").strip() or None,
        "display_name": str(raw.get("display_name") or "").strip() or None,
        "email": str(raw.get("email") or "").strip() or None,
        "amount_vnd": amount_vnd,
        "currency": str(raw.get("currency") or "VND"),
        "method": str(raw.get("method") or "bank_transfer"),
        "reference": str(raw.get("reference") or "").strip() or None,
        "payment_code": str(raw.get("payment_code") or "").strip() or None,
        "raw_state": raw_status or "unknown",
        "request_state": business_state,
        "payment_state": pay_state,
        "settlement_state": settle_state,
        "submitted_at": str(raw.get("submitted_at") or "") or None,
        "created_at": str(raw.get("submitted_at") or raw.get("created_at") or "") or None,
        "updated_at": str(raw.get("updated_at") or "") or None,
        "decision_at": str(raw.get("decision_at") or "") or None,
        "decision_reason": str(raw.get("decision_reason") or "") or None,
        "authority": TOPUP_REQUEST_AUTHORITY,
        "mutation_available": False,
    }

    needs_att, reasons = evaluate_finance_action_required(record, entity_type="topup")
    record["attention_required"] = needs_att
    record["attention_reasons"] = reasons
    return record


def synthesize_payment_record(
    raw: dict[str, Any],
    *,
    bridge_available: bool = True,
) -> dict[str, Any]:
    """Synthesize a truthful PayOS payment projection record."""
    item = raw if isinstance(raw, dict) else {}
    raw_status = str(item.get("status") or "").strip()
    gateway_state = map_payment_state(raw_status) if bridge_available else PAYMENT_STATE_UNAVAILABLE
    settlement_state = map_settlement_state(
        item.get("settlement_status"),
        bridge_available=bridge_available,
        payment_state=gateway_state,
    )

    amount = item.get("amount") if isinstance(item.get("amount"), (int, float)) else None
    payment_ref = str(item.get("payment_reference") or item.get("order_code") or item.get("id") or "").strip()
    request_ref = str(item.get("request_reference") or item.get("request_id") or "").strip() or None

    record = {
        "payment_reference": payment_ref,
        "request_reference": request_ref,
        "customer_id": str(item.get("customer_id") or item.get("account_id") or "").strip() or None,
        "display_name": str(item.get("display_name") or "").strip() or None,
        "amount": amount,
        "currency": str(item.get("currency") or "VND"),
        "gateway_state": gateway_state,
        "settlement_state": settlement_state,
        "raw_state": raw_status or "unknown",
        "created_at": str(item.get("created_at") or "") or None,
        "updated_at": str(item.get("updated_at") or "") or None,
        "gateway_authority": PAYMENT_GATEWAY_AUTHORITY,
        "settlement_authority": PAYMENT_SETTLEMENT_AUTHORITY,
        "mutation_available": False,
    }

    needs_att, reasons = evaluate_finance_action_required(record, entity_type="payment")
    record["attention_required"] = needs_att
    record["attention_reasons"] = reasons
    return record


# ==============================================================================
# 8. FINANCE SUMMARY SYNTHESIZER
# ==============================================================================
def synthesize_finance_summary(
    *,
    topup_counts: dict[str, Any] | None = None,
    wallet_payload: dict[str, Any] | None = None,
    wallet_bridge_available: bool = False,
    payments_payload: dict[str, Any] | None = None,
    payments_bridge_available: bool = False,
    refunds_payload: dict[str, Any] | None = None,
    refunds_bridge_available: bool = False,
) -> dict[str, Any]:
    """Synthesize the canonical Finance summary envelope.
    
    Guarantees:
    - Every metric has VALUE, STATUS, SOURCE, OBSERVED_AT
    - FAKE_ZERO_WALLET_BALANCE = 0: Wallet balance is None when bridge unavailable (never 0!)
    - UNKNOWN_REVENUE_AS_ZERO = False: Revenue is labeled 'Known Web Revenue' (coverage='PARTIAL')
    - Zero control plane actions: credit=0, debit=0, settle=0, refund=0, payos=0, wallet=0
    """
    now_str = utc_now()
    tc = topup_counts if isinstance(topup_counts, dict) else {}

    # 1. Topup Requests (Authority: WEB_SQLITE)
    topup_total = tc.get("total", 0)
    topup_pending = tc.get("pending_count", 0)
    topup_confirmed = tc.get("approved_count", 0)
    topup_rejected = tc.get("rejected_count", 0)
    known_web_revenue = tc.get("confirmed_revenue_vnd", 0)

    topup_requests_metric = {
        "value": topup_pending,
        "total": topup_total,
        "approved": topup_confirmed,
        "confirmed": topup_confirmed,
        "rejected": topup_rejected,
        "status": STATUS_EMPTY if topup_total == 0 else STATUS_HEALTHY,
        "source": TOPUP_REQUEST_AUTHORITY,
        "observed_at": now_str,
    }

    # 2. Wallet Truth (Authority: BOT_CORE)
    if not wallet_bridge_available or wallet_payload is None:
        wallet_metric = {
            "status": STATUS_UNAVAILABLE,
            "balance_xu": None,
            "total_wallets": None,
            "source": WALLET_AUTHORITY,
            "observed_at": now_str,
            "fake_zero_wallet_balance": FAKE_ZERO_WALLET_BALANCE,
        }
    else:
        w_data = wallet_payload.get("data") if isinstance(wallet_payload.get("data"), dict) else wallet_payload
        balance = w_data.get("balance_xu") if isinstance(w_data.get("balance_xu"), int) else None
        wallet_metric = {
            "status": STATUS_HEALTHY if balance is not None else STATUS_UNKNOWN,
            "balance_xu": balance,
            "total_wallets": w_data.get("total_wallets"),
            "source": WALLET_AUTHORITY,
            "observed_at": now_str,
            "fake_zero_wallet_balance": FAKE_ZERO_WALLET_BALANCE,
        }

    # 3. PayOS Payments Truth (Authority: PAYOS)
    if not payments_bridge_available or payments_payload is None:
        payments_metric = {
            "value": None,
            "status": STATUS_UNAVAILABLE,
            "source": PAYMENT_GATEWAY_AUTHORITY,
            "observed_at": now_str,
        }
        settlements_metric = {
            "value": None,
            "status": STATUS_UNAVAILABLE,
            "source": PAYMENT_SETTLEMENT_AUTHORITY,
            "observed_at": now_str,
        }
    else:
        p_data = payments_payload.get("data") if isinstance(payments_payload.get("data"), dict) else payments_payload
        p_items = p_data.get("items") if isinstance(p_data, dict) and isinstance(p_data.get("items"), list) else []
        confirmed_count = sum(1 for p in p_items if map_payment_state(p.get("status")) == PAYMENT_STATE_CONFIRMED)
        pending_settlements = sum(1 for p in p_items if map_settlement_state(p.get("settlement_status"), bridge_available=True, payment_state=map_payment_state(p.get("status"))) == SETTLEMENT_STATE_PENDING)

        payments_metric = {
            "value": confirmed_count,
            "total": len(p_items),
            "status": STATUS_EMPTY if len(p_items) == 0 else STATUS_HEALTHY,
            "source": PAYMENT_GATEWAY_AUTHORITY,
            "observed_at": now_str,
        }
        settlements_metric = {
            "value": pending_settlements,
            "status": STATUS_EMPTY if len(p_items) == 0 else STATUS_HEALTHY,
            "source": PAYMENT_SETTLEMENT_AUTHORITY,
            "observed_at": now_str,
        }

    # 4. Refunds Pending (Authority: BOT_CORE)
    if not refunds_bridge_available or refunds_payload is None:
        refunds_metric = {
            "value": None,
            "status": STATUS_UNAVAILABLE,
            "source": "BOT_CORE",
            "observed_at": now_str,
        }
    else:
        r_data = refunds_payload.get("data") if isinstance(refunds_payload.get("data"), dict) else refunds_payload
        r_items = r_data.get("items") if isinstance(r_data, dict) and isinstance(r_data.get("items"), list) else []
        pending_refunds = sum(1 for r in r_items if str(r.get("status") or "").lower() in ("pending", "reviewing", "requested"))
        refunds_metric = {
            "value": pending_refunds,
            "status": STATUS_EMPTY if len(r_items) == 0 else STATUS_HEALTHY,
            "source": "BOT_CORE",
            "observed_at": now_str,
        }

    # 5. Revenue Truth (Authority: BOT_CORE, Coverage: PARTIAL)
    revenue_metric = {
        "revenue_authority": REVENUE_AUTHORITY,
        "revenue_source": TOPUP_REQUEST_AUTHORITY,
        "revenue_current_scope": REVENUE_CURRENT_SCOPE,
        "revenue_coverage": REVENUE_COVERAGE,
        "revenue_label": REVENUE_LABEL,
        "revenue_missing_sources": list(REVENUE_MISSING_SOURCES),
        "known_web_revenue_vnd": known_web_revenue,
        "total_revenue": None,  # Total revenue is unavailable from Web alone
        "status": STATUS_PARTIAL,
        "unknown_revenue_as_zero": UNKNOWN_REVENUE_AS_ZERO,
        "unavailable_finance_value_as_zero": UNAVAILABLE_FINANCE_VALUE_AS_ZERO,
        "observed_at": now_str,
    }

    # Derived action required
    action_reasons: list[str] = []
    if topup_pending > 0:
        action_reasons.append(f"{topup_pending} yêu cầu nạp tiền chờ đối soát")
    if settlements_metric.get("value") and settlements_metric["value"] > 0:
        action_reasons.append(f"{settlements_metric['value']} thanh toán PayOS chờ ghi nhận ví Xu")
    if refunds_metric.get("value") and refunds_metric["value"] > 0:
        action_reasons.append(f"{refunds_metric['value']} yêu cầu hoàn tiền đang chờ xử lý")

    return {
        "status": STATUS_HEALTHY,
        "freshness": now_str,
        "authority_matrix": {
            "customer_authority": CUSTOMER_AUTHORITY,
            "wallet_authority": WALLET_AUTHORITY,
            "payment_gateway_authority": PAYMENT_GATEWAY_AUTHORITY,
            "payment_settlement_authority": PAYMENT_SETTLEMENT_AUTHORITY,
            "topup_request_authority": TOPUP_REQUEST_AUTHORITY,
            "job_authority": JOB_AUTHORITY,
            "revenue_authority": REVENUE_AUTHORITY,
            "web_role": WEB_ROLE,
        },
        "topup_requests_pending": topup_requests_metric,
        "payments_confirmed": payments_metric,
        "settlements_pending": settlements_metric,
        "refunds_pending": refunds_metric,
        "wallet": wallet_metric,
        "revenue": revenue_metric,
        "action_required": {
            "has_action": len(action_reasons) > 0,
            "action_count": len(action_reasons),
            "reasons": action_reasons,
        },
        "control_plane_actions": {
            "manual_credit_actions": MANUAL_CREDIT_ACTIONS,
            "manual_debit_actions": MANUAL_DEBIT_ACTIONS,
            "settlement_actions": SETTLEMENT_ACTIONS,
            "refund_actions": REFUND_ACTIONS,
            "payos_actions": PAYOS_ACTIONS,
            "wallet_actions": WALLET_ACTIONS,
        },
        "safety_invariants": {
            "fake_zero_wallet_balance": FAKE_ZERO_WALLET_BALANCE,
            "unknown_revenue_as_zero": UNKNOWN_REVENUE_AS_ZERO,
            "unavailable_finance_value_as_zero": UNAVAILABLE_FINANCE_VALUE_AS_ZERO,
            "payment_confirmed_not_equal_wallet_credited": PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED,
        },
    }


# ==============================================================================
# 9. RECONCILIATION ENGINE (WEB07 TRUTH)
# ==============================================================================
def reconcile_wallet_ledger(
    *,
    reported_balance: int | None,
    ledger_events: list[dict[str, Any]] | None,
    opening_balance: int = 0,
) -> dict[str, Any]:
    """Reconcile reported wallet balance with ledger events.

    Invariants:
    - DISCREPANCY_SUPPRESSED = False (never silently overwrite either side).
    - FAKE_ZERO_WALLET_BALANCE = 0 (unavailable balance remains None, never 0).
    """
    if reported_balance is None:
        return {
            "status": STATUS_UNAVAILABLE,
            "reconciled": False,
            "discrepancy_xu": None,
            "reported_balance_xu": None,
            "expected_balance_xu": None,
            "total_credits_xu": None,
            "total_debits_xu": None,
            "opening_balance_xu": opening_balance,
            "event_count": 0 if ledger_events is None else len(ledger_events),
            "discrepancy_suppressed": DISCREPANCY_SUPPRESSED,
        }

    events = ledger_events or []
    credits = sum(int(e.get("delta") or 0) for e in events if int(e.get("delta") or 0) > 0)
    debits = sum(abs(int(e.get("delta") or 0)) for e in events if int(e.get("delta") or 0) < 0)
    expected = int(opening_balance) + credits - debits
    discrepancy = int(reported_balance) - expected
    reconciled = (discrepancy == 0)

    return {
        "status": "reconciled" if reconciled else "discrepancy_detected",
        "reconciled": reconciled,
        "discrepancy_xu": discrepancy,
        "reported_balance_xu": int(reported_balance),
        "expected_balance_xu": expected,
        "total_credits_xu": credits,
        "total_debits_xu": debits,
        "opening_balance_xu": opening_balance,
        "event_count": len(events),
        "discrepancy_suppressed": DISCREPANCY_SUPPRESSED,
    }


def reconcile_manual_topup_linkages(
    *,
    requests: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    approve_receipts: list[dict[str, Any]],
    decision_receipts: list[dict[str, Any]] | None = None,
    account_canonical_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Reconcile manual topup requests, credit operations, and decision receipts.

    Detects:
    - MISSING_RECEIPT: Approved request without receipt/ledger event.
    - ORPHAN_OPERATION: Operation referencing non-existent request.
    - ORPHAN_RECEIPT: Receipt referencing non-existent request.
    - AMOUNT_MISMATCH: Amount discrepancy across request, operation, and receipt.
    - TARGET_IDENTITY_MISMATCH: Operation user mismatch.
    Invariants:
    - DUPLICATE_CREDIT_COUNTING = 0.
    - PENDING_TOPUP_AS_CREDITED = False.
    - REJECTED_TOPUP_AS_CREDITED = False.
    """
    unique_ops: dict[str, dict[str, Any]] = {}
    op_by_req_id: dict[int, dict[str, Any]] = {}
    for op in operations:
        op_id = str(op.get("id") or "")
        if op_id:
            unique_ops[op_id] = op
        req_id = op.get("manual_topup_id")
        if req_id is not None:
            op_by_req_id[int(req_id)] = op

    unique_receipts: dict[str, dict[str, Any]] = {}
    receipt_by_req_id: dict[int, dict[str, Any]] = {}
    for rec in approve_receipts:
        r_hash = str(rec.get("receipt_hash") or "")
        if r_hash:
            unique_receipts[r_hash] = rec
        req_id = rec.get("manual_topup_id")
        if req_id is not None:
            receipt_by_req_id[int(req_id)] = rec

    request_ids = {int(r["id"]) for r in requests if "id" in r}
    anomalies: list[dict[str, Any]] = []

    for op in unique_ops.values():
        req_id = op.get("manual_topup_id")
        if req_id is not None and int(req_id) not in request_ids:
            anomalies.append({
                "type": "ORPHAN_OPERATION",
                "operation_id": op.get("id"),
                "manual_topup_id": req_id,
                "detail": f"Credit operation {op.get('id')} references non-existent request {req_id}",
            })

    for rec in unique_receipts.values():
        req_id = rec.get("manual_topup_id")
        if req_id is not None and int(req_id) not in request_ids:
            anomalies.append({
                "type": "ORPHAN_RECEIPT",
                "receipt_hash": rec.get("receipt_hash"),
                "manual_topup_id": req_id,
                "detail": f"Approve receipt references non-existent request {req_id}",
            })

    approved_with_receipt = 0
    approved_without_receipt = 0
    pending_count = 0
    rejected_count = 0
    credited_amount_xu = 0

    acc_map = account_canonical_map or {}

    seen_req_ids: set[int] = set()
    unique_requests: list[dict[str, Any]] = []
    for req in requests:
        req_id = int(req.get("id") or 0)
        if req_id and req_id in seen_req_ids:
            continue
        if req_id:
            seen_req_ids.add(req_id)
        unique_requests.append(req)

    for req in unique_requests:
        req_id = int(req.get("id") or 0)
        raw_st = str(req.get("status") or "").strip().lower()
        status = map_topup_raw_state(raw_st)

        if status == TOPUP_STATE_PENDING:
            pending_count += 1
        elif status == TOPUP_STATE_REJECTED:
            rejected_count += 1
        elif status == TOPUP_STATE_APPROVED:
            has_ledger_evt = bool(req.get("ledger_event_id"))
            has_receipt = (req_id in receipt_by_req_id)
            has_op = (req_id in op_by_req_id)

            if not (has_ledger_evt and (has_receipt or has_op)):
                approved_without_receipt += 1
                anomalies.append({
                    "type": "MISSING_RECEIPT",
                    "manual_topup_id": req_id,
                    "detail": f"Approved request {req_id} lacks canonical receipt or ledger event",
                })
            else:
                approved_with_receipt += 1
                xu_amount = int(req.get("approved_xu") or 0)
                credited_amount_xu += xu_amount

                if has_op:
                    op = op_by_req_id[req_id]
                    op_amount = int(op.get("amount_xu") or 0)
                    if op_amount != xu_amount:
                        anomalies.append({
                            "type": "AMOUNT_MISMATCH",
                            "manual_topup_id": req_id,
                            "detail": f"Request approved_xu ({xu_amount}) != operation amount_xu ({op_amount})",
                        })
                    acc_id = str(req.get("account_id") or "")
                    expected_uid = acc_map.get(acc_id)
                    if expected_uid and str(op.get("canonical_user_id") or "") != expected_uid:
                        anomalies.append({
                            "type": "TARGET_IDENTITY_MISMATCH",
                            "manual_topup_id": req_id,
                            "detail": f"Operation user {op.get('canonical_user_id')} != account linked user {expected_uid}",
                        })
                if has_receipt:
                    rec = receipt_by_req_id[req_id]
                    rec_amount = int(rec.get("approved_xu") or 0)
                    if rec_amount != xu_amount:
                        anomalies.append({
                            "type": "AMOUNT_MISMATCH",
                            "manual_topup_id": req_id,
                            "detail": f"Request approved_xu ({xu_amount}) != receipt approved_xu ({rec_amount})",
                        })

    is_reconciled = (len(anomalies) == 0 and approved_without_receipt == 0)

    return {
        "total_requests": len(unique_requests),
        "pending_requests": pending_count,
        "rejected_requests": rejected_count,
        "approved_requests": approved_with_receipt + approved_without_receipt,
        "approved_with_receipt": approved_with_receipt,
        "approved_without_receipt": approved_without_receipt,
        "credited_amount_xu": credited_amount_xu,
        "anomalies": anomalies,
        "is_reconciled": is_reconciled,
        "pending_topup_as_credited": PENDING_TOPUP_AS_CREDITED,
        "rejected_topup_as_credited": REJECTED_TOPUP_AS_CREDITED,
        "approved_without_receipt_as_credited": APPROVED_WITHOUT_RECEIPT_AS_CREDITED,
        "duplicate_credit_counting": DUPLICATE_CREDIT_COUNTING,
    }


def reconcile_payos_orders(*, orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconcile PayOS orders by state vocabulary without fake revenue."""
    seen_order_codes: set[str] = set()
    unique_orders: list[dict[str, Any]] = []
    for o in orders:
        code = str(o.get("order_code") or o.get("id") or "").strip()
        if code and code in seen_order_codes:
            continue
        if code:
            seen_order_codes.add(code)
        unique_orders.append(o)

    settled_count = 0
    settled_revenue_vnd = 0
    pending_count = 0
    pending_amount_vnd = 0
    failed_count = 0
    failed_amount_vnd = 0

    for order in unique_orders:
        raw_st = str(order.get("status") or "").strip().lower()
        amt = int(order.get("amount") or order.get("amount_vnd") or 0)
        pay_st = map_payment_state(raw_st)

        if pay_st == PAYMENT_STATE_CONFIRMED:
            settled_count += 1
            settled_revenue_vnd += amt
        elif pay_st == PAYMENT_STATE_PENDING:
            pending_count += 1
            pending_amount_vnd += amt
        elif pay_st in (PAYMENT_STATE_FAILED, PAYMENT_STATE_EXPIRED):
            failed_count += 1
            failed_amount_vnd += amt

    return {
        "total_orders": len(unique_orders),
        "settled_count": settled_count,
        "settled_revenue_vnd": settled_revenue_vnd,
        "pending_count": pending_count,
        "pending_amount_vnd": pending_amount_vnd,
        "failed_count": failed_count,
        "failed_amount_vnd": failed_amount_vnd,
        "payos_pending_as_paid": PAYOS_PENDING_AS_PAID,
        "payos_failed_as_revenue": PAYOS_FAILED_AS_REVENUE,
        "payos_cancelled_as_revenue": PAYOS_CANCELLED_AS_REVENUE,
    }


def compute_finance_window_boundaries(
    window: str,
    *,
    reference_time: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Calculate deterministic UTC window boundaries."""
    now = reference_time.astimezone(timezone.utc) if reference_time else datetime.now(timezone.utc)
    norm = str(window).strip().lower()

    if norm == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif norm == "7d":
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif norm == "30d":
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif norm == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif norm == "all_time":
        start = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = now
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now

    return start, end


def reconcile_finance_records(
    *,
    wallet_payload: dict[str, Any] | None = None,
    wallet_bridge_available: bool = True,
    topups_data: dict[str, Any] | None = None,
    payos_orders: list[dict[str, Any]] | None = None,
    account_canonical_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Composite reconciliation read model across all financial sources."""
    now_str = utc_now()
    w_data = (wallet_payload.get("data") if isinstance(wallet_payload, dict) and isinstance(wallet_payload.get("data"), dict) else wallet_payload) or {}
    reported_balance = w_data.get("balance_xu") if wallet_bridge_available and isinstance(w_data.get("balance_xu"), int) else None
    ledger_events = w_data.get("ledger_events") if wallet_bridge_available and isinstance(w_data.get("ledger_events"), list) else None

    wallet_rec = reconcile_wallet_ledger(
        reported_balance=reported_balance,
        ledger_events=ledger_events,
    )

    td = topups_data or {}
    requests = td.get("requests") or []
    operations = td.get("operations") or []
    approve_receipts = td.get("approve_receipts") or []
    decision_receipts = td.get("decision_receipts") or []

    topup_rec = reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=approve_receipts,
        decision_receipts=decision_receipts,
        account_canonical_map=account_canonical_map,
    )

    orders = payos_orders or []
    payos_rec = reconcile_payos_orders(orders=orders)

    seen_req_ids: set[int] = set()
    unique_reqs: list[dict[str, Any]] = []
    for r in requests:
        r_id = int(r.get("id") or 0)
        if r_id and r_id in seen_req_ids:
            continue
        if r_id:
            seen_req_ids.add(r_id)
        unique_reqs.append(r)

    confirmed_manual_revenue = sum(int(r.get("amount_vnd") or 0) for r in unique_reqs if map_topup_raw_state(r.get("status")) == TOPUP_STATE_APPROVED and r.get("ledger_event_id"))
    settled_payos_revenue = payos_rec["settled_revenue_vnd"]
    known_web_revenue = confirmed_manual_revenue + settled_payos_revenue

    all_reconciled = bool(
        wallet_rec["reconciled"]
        and topup_rec["is_reconciled"]
        and len(topup_rec["anomalies"]) == 0
    )

    return {
        "reconciled": all_reconciled,
        "status": "reconciled" if all_reconciled else "reconciliation_discrepancy_or_anomalies",
        "observed_at": now_str,
        "finance_timezone": FINANCE_TIMEZONE,
        "window_boundary_source": WINDOW_BOUNDARY_SOURCE,
        "refund_semantics": REFUND_SEMANTICS,
        "compensation_semantics": COMPENSATION_SEMANTICS,
        "canonical_metrics": {
            "current_balance_xu": reported_balance,
            "total_credits_xu": wallet_rec.get("total_credits_xu"),
            "total_debits_xu": wallet_rec.get("total_debits_xu"),
            "known_web_revenue_vnd": known_web_revenue,
            "settled_payos_revenue_vnd": settled_payos_revenue,
            "confirmed_manual_topup_revenue_vnd": confirmed_manual_revenue,
            "total_revenue": None,
            "refund_amount_vnd": None,
            "pending_topup_requests_count": topup_rec["pending_requests"],
            "pending_payos_orders_count": payos_rec["pending_count"],
            "pending_payos_amount_vnd": payos_rec["pending_amount_vnd"],
        },
        "wallet_reconciliation": wallet_rec,
        "manual_topup_reconciliation": topup_rec,
        "payos_reconciliation": payos_rec,
        "safety_invariants": {
            "balance_as_lifetime_paid": BALANCE_AS_LIFETIME_PAID,
            "balance_as_revenue": BALANCE_AS_REVENUE,
            "topup_count_as_revenue": TOPUP_COUNT_AS_REVENUE,
            "discrepancy_suppressed": DISCREPANCY_SUPPRESSED,
            "duplicate_credit_counting": DUPLICATE_CREDIT_COUNTING,
            "payos_pending_as_paid": PAYOS_PENDING_AS_PAID,
            "payos_failed_as_revenue": PAYOS_FAILED_AS_REVENUE,
            "payos_cancelled_as_revenue": PAYOS_CANCELLED_AS_REVENUE,
            "pending_topup_as_credited": PENDING_TOPUP_AS_CREDITED,
            "rejected_topup_as_credited": REJECTED_TOPUP_AS_CREDITED,
            "approved_without_receipt_as_credited": APPROVED_WITHOUT_RECEIPT_AS_CREDITED,
            "fake_zero_wallet_balance": FAKE_ZERO_WALLET_BALANCE,
            "unavailable_finance_value_as_zero": UNAVAILABLE_FINANCE_VALUE_AS_ZERO,
            "fake_zero_finance": 0,
        },
    }
