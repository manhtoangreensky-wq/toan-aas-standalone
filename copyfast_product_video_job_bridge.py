"""Product Video Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.CANONICAL.JOB_BRIDGE.ADAPTER.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Master Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Connects the Web customer flow (/video/create) for `video_ai_prompt`
to a canonical Bot-compatible job bridge contract without executing real video
renders, paid provider calls, or wallet balance mutations.

Invariants:
- Fail-Closed Admission: zero provider calls until Owner-authorized runtime execution.
- Truthful Status: initial status is 'queued', status_reason is
  'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'. Zero fake output, zero fake completion.
- Idempotency & Conflict: replay existing job on identical payload hash, reject with 409
  on same request_id with differing payload.
- Zero Other Video Generator Bridges: only `video_ai_prompt` is bridged in this task.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any
import uuid

from fastapi import HTTPException
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now

CANONICAL_PRODUCT_KEY = "video_ai_prompt"
CANONICAL_ROUTING_KEY = "video_ai_canonical"
CANONICAL_ROUTE_ID = "product_video_one_scene_v1"
CANONICAL_ENGINE_ADAPTER = "b13_r18c_product_one_scene_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/video/create"

# Only video_ai_prompt is supported in this bounded adapter.
# All other 9 video generators remain unbridged and fail-closed.
SUPPORTED_CANONICAL_JOB_ADAPTERS = frozenset({"video_ai_prompt"})

ALLOWED_ASPECT_RATIOS = frozenset({"9:16", "16:9", "1:1"})
ALLOWED_DURATIONS = frozenset({5, 10, 15})
ALLOWED_QUALITY_TIERS = frozenset({200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500})
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_DURATION_SECONDS = 5
DEFAULT_QUALITY_TIER = 200
MAX_PROMPT_LENGTH = 2000

STATUS_QUEUED = "queued"
STATUS_BLOCKED = "blocked"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED = frozenset({
    "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "apikey", "apitoken", "token",
    "secret", "jobid", "jobstatus", "status", "statusreason", "output", "outputurl",
    "assetid", "downloadurl", "role", "balance", "xu", "wallet",
})


def _contains_authority_field(value: Any) -> bool:
    """Find forged authority fields in incoming client input."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(ch for ch in str(key or "").lower() if ch.isalnum())
            if normalized in FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED:
                return True
            if _contains_authority_field(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_authority_field(child) for child in value)
    return False


def validate_product_video_input(values: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Validate input payload for Product Video (video_ai_prompt) job bridge.

    Returns:
        (is_valid, error_code, normalized_values)
    """
    if _contains_authority_field(values):
        return False, "authority_field_not_allowed", {}

    # Extract & validate prompt (required, 1..2000 chars)
    prompt = str(values.get("prompt") or values.get("text") or values.get("brief") or "").strip()
    if not prompt:
        return False, "PROMPT_REQUIRED", {}
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, "PROMPT_TOO_LONG", {}

    # Extract & validate quality tier (200..1500)
    tier_raw = values.get("quality_tier") if "quality_tier" in values else values.get("tier")
    if tier_raw is None:
        return False, "TIER_REQUIRED", {}
    try:
        tier = int(tier_raw)
    except (TypeError, ValueError):
        return False, "INVALID_QUALITY_TIER", {}
    if tier not in ALLOWED_QUALITY_TIERS:
        return False, "INVALID_QUALITY_TIER", {}

    # Extract & validate aspect ratio ("9:16", "16:9", "1:1")
    ratio_raw = str(values.get("aspect_ratio") or values.get("aspectRatio") or values.get("ratio") or "").strip()
    if not ratio_raw:
        return False, "ASPECT_RATIO_REQUIRED", {}
    if ratio_raw not in ALLOWED_ASPECT_RATIOS:
        return False, "INVALID_ASPECT_RATIO", {}

    # Extract & validate duration (5, 10, 15)
    dur_raw = values.get("duration_seconds") if "duration_seconds" in values else values.get("duration")
    if dur_raw is None:
        return False, "DURATION_REQUIRED", {}
    try:
        dur = int(dur_raw)
    except (TypeError, ValueError):
        return False, "INVALID_DURATION", {}
    if dur not in ALLOWED_DURATIONS:
        return False, "INVALID_DURATION", {}

    normalized = {
        "prompt": prompt,
        "aspect_ratio": ratio_raw,
        "duration_seconds": dur,
        "quality_tier": tier,
        "scene_count": 1,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
    }
    return True, "", normalized


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 digest of normalized payload for idempotency & conflict detection."""
    core = {
        "aspect_ratio": str(payload.get("aspect_ratio") or ""),
        "duration_seconds": int(payload.get("duration_seconds") or 0),
        "product_key": str(payload.get("product_key") or CANONICAL_PRODUCT_KEY),
        "prompt": str(payload.get("prompt") or "").strip(),
        "quality_tier": int(payload.get("quality_tier") or 0),
        "scene_count": int(payload.get("scene_count") or 1),
    }
    serialized = json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def compute_idempotency_hash(key: str) -> str:
    cleaned = str(key or "").strip()
    if not cleaned:
        return ""
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def generate_canonical_request_id() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:6].upper()
    return f"VID-{date_part}-{random_part}"


def generate_product_video_job_id() -> str:
    return f"pvj_{uuid.uuid4().hex}"


def create_or_replay_product_video_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new canonical Product Video job or replay existing one idempotently.

    Raises:
        HTTPException(400) on validation error
        HTTPException(409) on request_id conflict with differing payload
    """
    ensure_copyfast_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Xác thực tài khoản Web là bắt buộc")

    is_valid, error_code, normalized = validate_product_video_input(payload)
    if not is_valid:
        error_messages = {
            "authority_field_not_allowed": "Yêu cầu chứa trường authority bị cấm.",
            "PROMPT_REQUIRED": "Prompt là bắt buộc đối với Video AI Prompt.",
            "PROMPT_TOO_LONG": f"Prompt không được vượt quá {MAX_PROMPT_LENGTH} ký tự.",
            "TIER_REQUIRED": "Quality tier là bắt buộc (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500).",
            "INVALID_QUALITY_TIER": "Quality tier không hợp lệ. Phải thuộc (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500).",
            "ASPECT_RATIO_REQUIRED": "Aspect ratio là bắt buộc ('9:16', '16:9', '1:1').",
            "INVALID_ASPECT_RATIO": "Aspect ratio không hợp lệ. Phải thuộc ('9:16', '16:9', '1:1').",
            "DURATION_REQUIRED": "Thời lượng duration_seconds là bắt buộc (5, 10, 15).",
            "INVALID_DURATION": "Thời lượng không hợp lệ. Phải thuộc (5, 10, 15) giây.",
        }
        raise HTTPException(status_code=400, detail=error_messages.get(error_code, error_code))

    payload_hash = compute_payload_hash(normalized)
    effective_req_id = str(request_id or payload.get("request_id") or "").strip()
    effective_idem_key = str(idempotency_key or payload.get("idempotency_key") or "").strip()
    idem_hash = compute_idempotency_hash(effective_idem_key) if effective_idem_key else ""

    with transaction() as conn:
        # Check for existing job by account_id and (request_id or idempotency_key_hash)
        query = """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, created_at, updated_at,
                   worker_id, claimed_at, lease_expires_at, attempts, output_url
            FROM web_product_video_jobs
            WHERE account_id = ? AND (
                (? != '' AND request_id = ?)
                OR (? != '' AND idempotency_key_hash = ?)
            )
            ORDER BY created_at DESC LIMIT 1
        """
        row = conn.execute(
            query,
            (owner_id, effective_req_id, effective_req_id, idem_hash, idem_hash),
        ).fetchone()

        if row is not None:
            existing_payload_hash = str(row[13])
            if not hmac.compare_digest(existing_payload_hash, payload_hash):
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột mã yêu cầu: request_id hoặc idempotency_key đã gắn với payload khác.",
                )
            return _format_public_job(row, idempotent_replay=True)

        job_id = generate_product_video_job_id()
        final_req_id = effective_req_id or generate_canonical_request_id()
        now = utc_now()

        bridge_envelope = {
            "version": "p0.product-video.canonical-bridge.v1",
            "route_id": CANONICAL_ROUTE_ID,
            "product_family": "product_video",
            "mode": "one_scene",
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "request_id": final_req_id,
            "job_id": job_id,
            "account_id": owner_id,
            "prompt": normalized["prompt"],
            "aspect_ratio": normalized["aspect_ratio"],
            "duration_seconds": normalized["duration_seconds"],
            "quality_tier": normalized["quality_tier"],
            "scene_count": normalized["scene_count"],
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_AWAITING,
            "created_at": now,
            "output": None,
        }
        envelope_json = json.dumps(bridge_envelope, ensure_ascii=True, sort_keys=True)

        conn.execute(
            """
            INSERT INTO web_product_video_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope, output_metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                job_id,
                final_req_id,
                owner_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                normalized["prompt"],
                normalized["aspect_ratio"],
                normalized["duration_seconds"],
                normalized["quality_tier"],
                normalized["scene_count"],
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                idem_hash or None,
                payload_hash,
                envelope_json,
                now,
                now,
            ),
        )

        return {
            "id": job_id,
            "request_id": final_req_id,
            "account_id": owner_id,
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "prompt": normalized["prompt"],
            "aspect_ratio": normalized["aspect_ratio"],
            "duration_seconds": normalized["duration_seconds"],
            "quality_tier": normalized["quality_tier"],
            "scene_count": normalized["scene_count"],
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_AWAITING,
            "output_available": False,
            "download_ready": False,
            "delivery_ready": False,
            "output": None,
            "output_metadata": None,
            "created_at": now,
            "updated_at": now,
            "bridge_envelope": bridge_envelope,
            "idempotent_replay": False,
        }


def _format_public_job(row: tuple, *, idempotent_replay: bool = False) -> dict[str, Any]:
    try:
        env = json.loads(str(row[14])) if row[14] else {}
    except Exception:
        env = {}
    try:
        output_meta = json.loads(str(row[15])) if row[15] else None
    except Exception:
        output_meta = None

    status_str = str(row[10])
    is_completed = status_str == "completed"
    output_url_val = (
        str(row[22])
        if len(row) > 22 and row[22]
        else (f"/api/v1/assets/{row[0]}/download" if is_completed else None)
    )

    return {
        "id": str(row[0]),
        "request_id": str(row[1]),
        "account_id": str(row[2]),
        "product_key": str(row[3]),
        "routing_product_key": str(row[4]),
        "prompt": str(row[5]),
        "aspect_ratio": str(row[6]),
        "duration_seconds": int(row[7]),
        "quality_tier": int(row[8]),
        "scene_count": int(row[9]),
        "status": status_str,
        "status_reason": str(row[11]),
        "output_available": is_completed,
        "download_ready": is_completed,
        "delivery_ready": is_completed,
        "output": output_url_val if is_completed else None,
        "output_metadata": output_meta,
        "created_at": str(row[16]),
        "updated_at": str(row[17]),
        "bridge_envelope": env,
        "idempotent_replay": idempotent_replay,
        "worker_id": str(row[18]) if len(row) > 18 and row[18] else None,
        "claimed_at": str(row[19]) if len(row) > 19 and row[19] else None,
        "lease_expires_at": str(row[20]) if len(row) > 20 and row[20] else None,
        "attempts": int(row[21]) if len(row) > 21 and row[21] is not None else 0,
        "output_url": output_url_val if is_completed else None,
    }


def get_product_video_job(account_id: str, job_id_or_request_id: str) -> dict[str, Any] | None:
    """Fetch one product video job owned by the authenticated account."""
    owner_id = str(account_id or "").strip()
    target_id = str(job_id_or_request_id or "").strip()
    if not owner_id or not target_id:
        return None

    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, created_at, updated_at,
                   worker_id, claimed_at, lease_expires_at, attempts, output_url
            FROM web_product_video_jobs
            WHERE account_id = ? AND (id = ? OR request_id = ?)
            LIMIT 1
            """,
            (owner_id, target_id, target_id),
        ).fetchone()

        if row is None:
            return None
        return _format_public_job(row)


def is_product_video_job_other_account(job_id_or_request_id: str, account_id: str) -> bool:
    """Check if the job exists but belongs to a different user (for cross-user rejection)."""
    target_id = str(job_id_or_request_id or "").strip()
    owner_id = str(account_id or "").strip()
    if not target_id:
        return False

    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM web_product_video_jobs
            WHERE (id = ? OR request_id = ?) AND account_id != ?
            LIMIT 1
            """,
            (target_id, target_id, owner_id),
        ).fetchone()
        return row is not None


def list_product_video_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """List product video jobs for the authenticated account."""
    owner_id = str(account_id or "").strip()
    if not owner_id:
        return []
    bounded_limit = max(1, min(int(limit or 100), 100))

    with read_transaction() as conn:
        rows = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, created_at, updated_at,
                   worker_id, claimed_at, lease_expires_at, attempts, output_url
            FROM web_product_video_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (owner_id, bounded_limit),
        ).fetchall()

        return [_format_public_job(r) for r in rows]


def product_video_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Adapt a Product Video job record for inclusion in generic GET /api/v1/jobs."""
    is_completed = job.get("status") == "completed"
    is_processing = job.get("status") == "processing"
    source_state = "completed" if is_completed else ("processing_by_worker" if is_processing else "queued_locally")
    return {
        "id": job["id"],
        "feature": "video_ai_prompt",
        "job_type": "product_video_one_scene",
        "status": job["status"],
        "status_reason": job["status_reason"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "output_available": is_completed,
        "download_ready": is_completed,
        "delivery_ready": is_completed,
        "source": "web_canonical_bridge",
        "source_state": source_state,
        "native_kind": "product-video-job",
        "output": job.get("output") if is_completed else None,
        "output_metadata": job.get("output_metadata"),
        "summary": {
            "prompt": job.get("prompt", "")[:100],
            "aspect_ratio": job.get("aspect_ratio", ""),
            "duration_seconds": job.get("duration_seconds", 0),
            "quality_tier": job.get("quality_tier", 0),
        },
    }
