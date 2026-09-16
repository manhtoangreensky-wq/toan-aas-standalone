"""Pure policy and synthesis engine for Operations Jobs (SPEC-05).

Canonical Authorities:
- JOB_AUTHORITY = BOT_CORE
- WEB_ROLE = READ_THROUGH_OR_PROJECTION
- WEB_DIRECT_BOT_DB_WRITE = False
- JOB_MUTATION_AVAILABLE = False

Safety Invariants:
- RETRY_ACTIONS = 0
- CANCEL_ACTIONS = 0
- REQUEUE_ACTIONS = 0
- FORCE_COMPLETE_ACTIONS = 0
- PROVIDER_ACTIONS = 0
- UNKNOWN != 0, UNAVAILABLE != HEALTHY, EMPTY != UNKNOWN
- FAKE_ZERO_JOB_COUNT = 0
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Canonical Authorities
JOB_AUTHORITY = "BOT_CORE"
WEB_ROLE = "READ_THROUGH_OR_PROJECTION"
WEB_DIRECT_BOT_DB_WRITE = False
JOB_MUTATION_AVAILABLE = False

# Safety Invariants (Read Model Only)
RETRY_ACTIONS = 0
CANCEL_ACTIONS = 0
REQUEUE_ACTIONS = 0
FORCE_COMPLETE_ACTIONS = 0
PROVIDER_ACTIONS = 0
FAKE_ZERO_JOB_COUNT = 0

# Operational Status Semantics
STATUS_EMPTY = "EMPTY"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_HEALTHY = "HEALTHY"
STATUS_ERROR = "ERROR"
STATUS_GUARDED = "guarded"

# Standardized Business States
JOB_STATE_QUEUED = "QUEUED"
JOB_STATE_RUNNING = "RUNNING"
JOB_STATE_BLOCKED = "BLOCKED"
JOB_STATE_SUCCEEDED = "SUCCEEDED"
JOB_STATE_FAILED = "FAILED"
JOB_STATE_UNKNOWN = "UNKNOWN"

VALID_BUSINESS_STATES = frozenset({
    JOB_STATE_QUEUED,
    JOB_STATE_RUNNING,
    JOB_STATE_BLOCKED,
    JOB_STATE_SUCCEEDED,
    JOB_STATE_FAILED,
    JOB_STATE_UNKNOWN,
})

# Raw-to-Business State Mapping
RAW_TO_BUSINESS_STATE: dict[str, str] = {
    # Queued / Pending
    "queued": JOB_STATE_QUEUED,
    "pending": JOB_STATE_QUEUED,
    "submitted": JOB_STATE_QUEUED,
    "wait": JOB_STATE_QUEUED,
    "waiting": JOB_STATE_QUEUED,
    # Running / Processing
    "processing": JOB_STATE_RUNNING,
    "running": JOB_STATE_RUNNING,
    "in_progress": JOB_STATE_RUNNING,
    "rendering": JOB_STATE_RUNNING,
    "generating": JOB_STATE_RUNNING,
    # Succeeded / Completed
    "completed": JOB_STATE_SUCCEEDED,
    "succeeded": JOB_STATE_SUCCEEDED,
    "success": JOB_STATE_SUCCEEDED,
    "done": JOB_STATE_SUCCEEDED,
    "delivered": JOB_STATE_SUCCEEDED,
    # Failed / Error
    "failed": JOB_STATE_FAILED,
    "failed_no_charge": JOB_STATE_FAILED,
    "error": JOB_STATE_FAILED,
    "timeout": JOB_STATE_FAILED,
    # Blocked / Guarded / Cancelled / Refunded
    "cancelled": JOB_STATE_BLOCKED,
    "canceled": JOB_STATE_BLOCKED,
    "refunded": JOB_STATE_BLOCKED,
    "guarded": JOB_STATE_BLOCKED,
    "awaiting_confirm": JOB_STATE_BLOCKED,
    "draft": JOB_STATE_BLOCKED,
    "blocked": JOB_STATE_BLOCKED,
    "hold": JOB_STATE_BLOCKED,
}


def map_job_state(raw_state: Any) -> str:
    """Standardize any raw job state string into the canonical business state taxonomy.
    
    Returns 'UNKNOWN' if raw_state is empty, null, or unrecognized.
    """
    if raw_state is None:
        return JOB_STATE_UNKNOWN
    normalized = str(raw_state).strip().lower()
    if not normalized:
        return JOB_STATE_UNKNOWN
    return RAW_TO_BUSINESS_STATE.get(normalized, JOB_STATE_UNKNOWN)


def evaluate_job_attention(job: dict[str, Any]) -> tuple[bool, list[str]]:
    """Evaluates whether a job requires operator attention based solely on concrete facts.
    
    A job requires attention ONLY if:
    - Business state is FAILED (with error details)
    - Business state is BLOCKED (cancelled, refunded, awaiting confirmation, guarded)
    - Delivery output is missing despite completed state
    - Explicit manual review or dispute flag is present
    - Refund is pending
    
    A job does NOT require attention if:
    - Normal running state within operational window
    - Normal queued state
    - Normal succeeded state
    - State is UNKNOWN (do not invent attention reasons)
    """
    reasons: list[str] = []
    raw_status = str(job.get("status") or job.get("raw_state") or "").strip().lower()
    business_state = map_job_state(raw_status)

    if business_state == JOB_STATE_FAILED:
        err_cat = str(job.get("error_category") or "").strip()
        err_msg = str(job.get("error_message") or "").strip()
        if err_cat:
            reasons.append(f"Tác vụ thất bại ({err_cat})")
        elif err_msg:
            reasons.append(f"Tác vụ thất bại: {err_msg[:60]}")
        else:
            reasons.append("Tác vụ thất bại")

    elif business_state == JOB_STATE_BLOCKED:
        if raw_status in ("cancelled", "canceled"):
            reasons.append("Tác vụ đã hủy")
        elif raw_status == "refunded":
            reasons.append("Tác vụ đã hoàn tiền")
        elif raw_status == "awaiting_confirm":
            reasons.append("Chờ người dùng hoặc quản trị viên xác nhận")
        else:
            reasons.append("Tác vụ bị tạm dừng hoặc chặn bởi guard hệ thống")

    # Delivery verification: if succeeded but delivery / output explicitly flagged unavailable
    if business_state == JOB_STATE_SUCCEEDED:
        output_avail = job.get("output_available")
        download_ready = job.get("download_ready")
        if output_avail is False and download_ready is False:
            reasons.append("Tác vụ hoàn thành nhưng thiếu tệp đầu ra (output unavailable)")

    # Manual review flag
    if bool(job.get("manual_review")) or bool(job.get("review_required")):
        reasons.append("Yêu cầu quản trị viên đối soát thủ công")

    # Refund pending
    refund_status = str(job.get("refund_status") or "").strip().lower()
    if refund_status in ("pending", "reviewing", "requested"):
        reasons.append("Yêu cầu hoàn phí đang chờ giải quyết")

    needs_attention = len(reasons) > 0
    return needs_attention, reasons


def synthesize_operations_job_record(
    raw_job: dict[str, Any],
    *,
    source_system: str = JOB_AUTHORITY,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Synthesize an authoritative, safe Operations Job record for ERP consumption."""
    raw = raw_job if isinstance(raw_job, dict) else {}
    raw_status = str(raw.get("status") or raw.get("raw_state") or "").strip()
    business_state = map_job_state(raw_status)

    needs_attention, attention_reasons = evaluate_job_attention(raw)

    job_id = str(raw.get("id") or raw.get("job_id") or "").strip()
    canonical_user_id = str(raw.get("user_id") or raw.get("canonical_user_id") or "").strip() or None
    cust_id = customer_id or str(raw.get("customer_id") or raw.get("account_id") or "").strip() or None
    feature = str(raw.get("feature") or raw.get("job_type") or raw.get("kind") or "operation").strip()
    project_id = str(raw.get("project_id") or "").strip() or None

    return {
        "job_id": job_id,
        "source": source_system,
        "customer_id": cust_id,
        "canonical_user_id": canonical_user_id,
        "project_id": project_id,
        "service_context": feature,
        "job_type": str(raw.get("job_type") or feature),
        "raw_state": raw_status or "unknown",
        "state": business_state,
        "attention_required": needs_attention,
        "attention_reasons": attention_reasons,
        "created_at": str(raw.get("created_at") or "") or None,
        "updated_at": str(raw.get("updated_at") or "") or None,
        "finished_at": str(raw.get("finished_at") or "") or None,
        "freshness": str(raw.get("freshness") or "realtime"),
        "data_source_authority": source_system,
        "charged_xu": raw.get("charged_xu") if isinstance(raw.get("charged_xu"), int) else None,
        "estimated_xu": raw.get("estimated_xu") if isinstance(raw.get("estimated_xu"), int) else None,
        "output_available": bool(raw.get("output_available", False)),
        "download_ready": bool(raw.get("download_ready", False)),
        "error_category": str(raw.get("error_category") or "") or None,
        "refund_status": str(raw.get("refund_status") or "") or None,
        "mutation_available": False,
    }


def synthesize_operations_jobs_summary(
    bridge_payload: dict[str, Any] | None = None,
    *,
    bridge_available: bool = False,
    bridge_error: str | None = None,
    jobs_list: list[dict[str, Any]] | None = None,
    filter_state: str | None = None,
) -> dict[str, Any]:
    """Synthesize the truthful Operations Jobs read model envelope.
    
    Guarantees:
    - If bridge is UNAVAILABLE: status='UNAVAILABLE', counts={'total': None, ...}, FAKE_ZERO_JOB_COUNT=0
    - If bridge is AVAILABLE but empty: status='EMPTY', counts={'total': 0, ...}, items=[]
    - If bridge is AVAILABLE with items: status='HEALTHY', counts={...}, items=[synthesized...]
    """
    if not bridge_available:
        return {
            "status": STATUS_UNAVAILABLE,
            "job_authority": JOB_AUTHORITY,
            "web_role": WEB_ROLE,
            "counts": {
                "total": None,
                "queued": None,
                "running": None,
                "failed": None,
                "succeeded": None,
                "blocked": None,
                "attention": None,
            },
            "items": [],
            "freshness": None,
            "fake_zero_job_count": FAKE_ZERO_JOB_COUNT,
            "mutation_available": JOB_MUTATION_AVAILABLE,
            "error_code": bridge_error or "CORE_BRIDGE_NOT_CONFIGURED",
        }

    raw_items = jobs_list
    if raw_items is None and isinstance(bridge_payload, dict):
        raw_items = bridge_payload.get("items")
        if raw_items is None and isinstance(bridge_payload.get("data"), dict):
            raw_items = bridge_payload["data"].get("items")

    items = [
        synthesize_operations_job_record(item, source_system=JOB_AUTHORITY)
        for item in (raw_items or [])
        if isinstance(item, dict)
    ]

    total_count = len(items)
    queued_count = sum(1 for item in items if item["state"] == JOB_STATE_QUEUED)
    running_count = sum(1 for item in items if item["state"] == JOB_STATE_RUNNING)
    failed_count = sum(1 for item in items if item["state"] == JOB_STATE_FAILED)
    succeeded_count = sum(1 for item in items if item["state"] == JOB_STATE_SUCCEEDED)
    blocked_count = sum(1 for item in items if item["state"] == JOB_STATE_BLOCKED)
    attention_count = sum(1 for item in items if item["attention_required"])

    filtered_items = items
    if filter_state and filter_state.upper() != "ALL":
        target = filter_state.upper()
        if target == "ATTENTION":
            filtered_items = [item for item in items if item["attention_required"]]
        else:
            filtered_items = [item for item in items if item["state"] == target]

    status_name = STATUS_EMPTY if total_count == 0 else STATUS_HEALTHY

    return {
        "status": status_name,
        "job_authority": JOB_AUTHORITY,
        "web_role": WEB_ROLE,
        "counts": {
            "total": total_count,
            "queued": queued_count,
            "running": running_count,
            "failed": failed_count,
            "succeeded": succeeded_count,
            "blocked": blocked_count,
            "attention": attention_count,
        },
        "items": filtered_items,
        "freshness": utc_now(),
        "fake_zero_job_count": FAKE_ZERO_JOB_COUNT,
        "mutation_available": JOB_MUTATION_AVAILABLE,
        "error_code": None,
    }
