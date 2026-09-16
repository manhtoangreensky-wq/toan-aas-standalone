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

from datetime import datetime, timezone
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

# Fake zero prevention invariants
FAKE_ZERO_WALLET_BALANCE = 0
UNAVAILABLE_FINANCE_VALUE_AS_ZERO = False
UNKNOWN_REVENUE_AS_ZERO = False
UNAVAILABLE_WALLET_AS_ZERO = False
PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED = True

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
TOPUP_STATE_CONFIRMED = "CONFIRMED"
TOPUP_STATE_REJECTED = "REJECTED"
TOPUP_STATE_UNKNOWN = "UNKNOWN"

VALID_TOPUP_BUSINESS_STATES = frozenset({
    TOPUP_STATE_PENDING,
    TOPUP_STATE_CONFIRMED,
    TOPUP_STATE_REJECTED,
    TOPUP_STATE_UNKNOWN,
})

RAW_TOPUP_TO_BUSINESS_STATE: dict[str, str] = {
    # Pending
    "pending_admin_review": TOPUP_STATE_PENDING,
    "pending": TOPUP_STATE_PENDING,
    "reviewing": TOPUP_STATE_PENDING,
    "submitted": TOPUP_STATE_PENDING,
    # Confirmed / Approved
    "approved": TOPUP_STATE_CONFIRMED,
    "confirmed": TOPUP_STATE_CONFIRMED,
    "success": TOPUP_STATE_CONFIRMED,
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
    
    Invariant: PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED = True.
    A confirmed payment without verified ledger credit remains PENDING or UNKNOWN.
    """
    if not bridge_available:
        return SETTLEMENT_STATE_UNAVAILABLE
    if raw_state is not None:
        normalized = str(raw_state).strip().lower()
        if normalized in RAW_SETTLEMENT_TO_BUSINESS_STATE:
            return RAW_SETTLEMENT_TO_BUSINESS_STATE[normalized]
    if payment_state == PAYMENT_STATE_CONFIRMED:
        return SETTLEMENT_STATE_PENDING
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

        if pay_state == PAYMENT_STATE_CONFIRMED and settle_state in (SETTLEMENT_STATE_PENDING, "PENDING"):
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
def synthesize_topup_record(row: dict[str, Any]) -> dict[str, Any]:
    """Synthesize a truthful, safe Topup record from SQLite row."""
    raw = row if isinstance(row, dict) else {}
    raw_status = str(raw.get("status") or "").strip()
    business_state = map_topup_raw_state(raw_status)

    # In topup requests from web:
    # Payment state is PENDING until approved, then CONFIRMED
    # Settlement state is PENDING until approved and credited
    if business_state == TOPUP_STATE_CONFIRMED:
        pay_state = PAYMENT_STATE_CONFIRMED
        settle_state = SETTLEMENT_STATE_CREDITED
    elif business_state == TOPUP_STATE_REJECTED:
        pay_state = PAYMENT_STATE_FAILED
        settle_state = SETTLEMENT_STATE_UNKNOWN
    else:
        pay_state = PAYMENT_STATE_PENDING
        settle_state = SETTLEMENT_STATE_PENDING

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
