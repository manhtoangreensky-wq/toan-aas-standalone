"""Video Trend Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.VIDEO_TREND.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Master Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Connects the Web customer flow (/video/trend) for `video_trend`
to a canonical Bot-compatible job bridge contract without executing real video
renders, external trend searches, paid provider calls, or wallet balance mutations.

Runtime Authority Reference:
- services.video_tail9.PRODUCT_ADAPTERS['video_trend']
- flow_owner: trend
- engine_route: trend_video
- executor_product_type: video_trend
- required_capability: text_to_video
- input_type: trend_prompt
- worker_owner: product_video
- supported_quality_tiers: TREND_QUALITY_TIERS (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500)

Invariants:
- Fail-Closed Admission: zero provider calls until Owner-authorized runtime execution.
- Truthful Status: initial status is 'queued', status_reason is
  'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'. Zero fake output, zero fake completion.
- Output Fail-Closed: output_available=False, download_ready=False, delivery_ready=False,
  output=None until verifiable safe artifact URL exists.
- Idempotency & Conflict: replay existing job on identical payload hash, reject with 409
  on same request_id/idempotency_key with differing payload.
- Isolated Adapter: bounded specifically to `video_trend`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from typing import Any
from urllib.parse import urlsplit
import uuid

from fastapi import HTTPException
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now

CANONICAL_PRODUCT_KEY = "video_trend"
CANONICAL_ROUTING_KEY = "trend_video"
CANONICAL_ROUTE_ID = "trend_video_canonical_v1"
CANONICAL_ENGINE_ADAPTER = "b13_r18c_trend_video_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/video/trend"

SUPPORTED_CANONICAL_JOB_ADAPTERS = frozenset({"video_trend"})

ALLOWED_QUALITY_TIERS = frozenset({200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500})
DEFAULT_QUALITY_TIER = 200
DEFAULT_SCENE_COUNT = 1
MAX_PROMPT_LENGTH = 2000

STATUS_QUEUED = "queued"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED = frozenset({
    "id", "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "providertaskid", "apikey", "apitoken", "token",
    "secret", "jobid", "jobstatus", "status", "statusreason", "output", "outputurl",
    "assetid", "downloadurl", "role", "balance", "xu", "wallet", "authority",
    "accountid", "ownerid", "userid", "user_id", "account_id", "owner_id", "refund", "refund_status",
    "bridgeenvelope", "outputmetadata",
})

SAFE_HOSTNAME_PATTERN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
FORBIDDEN_OUTPUT_URL_SCHEMES = frozenset({"javascript:", "vbscript:", "data:", "file:", "blob:", "about:"})


def is_safe_video_output_url(url: Any) -> bool:
    """Validate that a candidate video output/artifact URL is safe to deliver.

    Fail-closed security contract:
    - Must be a non-empty string with length <= 2048 and no leading/trailing whitespace.
    - Zero control characters (ASCII < 32 or ASCII == 127).
    - Zero backslashes (prevents authority/path confusion bypasses).
    - Zero directory traversal sequences ('..' or '%2e' / '%2E').
    - Strict scheme check: must be 'https' (lowercase).
    - Rejects dangerous schemes: javascript:, vbscript:, data:, file:, blob:, about:, etc.
    - Rejects embedded credentials (username, password, '@' in authority/netloc).
    - Hostname must be non-empty, valid domain/label characters without illegal punctuation/spaces.
    - Port must be None or 443.
    """
    if not isinstance(url, str):
        return False
    trimmed = url.strip()
    if not trimmed or len(trimmed) > 2048 or trimmed != url:
        return False
    if any(ord(c) < 32 or ord(c) == 127 for c in trimmed):
        return False
    if "\\" in trimmed:
        return False
    lowered = trimmed.lower()
    if ".." in lowered or "%2e" in lowered:
        return False
    if any(lowered.startswith(s) or s in lowered for s in FORBIDDEN_OUTPUT_URL_SCHEMES):
        return False
    try:
        parsed = urlsplit(trimmed)
    except Exception:
        return False
    if parsed.scheme.lower() != "https":
        return False
    if not parsed.netloc:
        return False
    if parsed.username or parsed.password or "@" in parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    if not hostname or not SAFE_HOSTNAME_PATTERN.fullmatch(hostname):
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port not in (None, 443):
        return False
    return True


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


def validate_video_trend_input(values: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Validate input payload for Video Trend (video_trend) job bridge.

    Returns:
        (is_valid, error_code, normalized_values)
    """
    if _contains_authority_field(values):
        return False, "authority_field_not_allowed", {}

    # Extract & validate prompt / trend_prompt (required, 1..2000 chars)
    raw_prompt = values.get("trend_prompt") or values.get("prompt") or values.get("brief") or values.get("text")
    if raw_prompt is None:
        return False, "PROMPT_REQUIRED", {}
    prompt = str(raw_prompt).strip()
    if not prompt:
        return False, "PROMPT_REQUIRED", {}
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, "PROMPT_TOO_LONG", {}

    # Extract & validate quality tier (200..1500) if supplied, else default
    tier_raw = values.get("quality_tier") if "quality_tier" in values else values.get("tier")
    if tier_raw is not None and str(tier_raw).strip() != "":
        try:
            tier = int(tier_raw)
        except (TypeError, ValueError):
            return False, "INVALID_QUALITY_TIER", {}
        if tier not in ALLOWED_QUALITY_TIERS:
            return False, "INVALID_QUALITY_TIER", {}
    else:
        tier = DEFAULT_QUALITY_TIER

    # Extract & validate scene_count (1..20) if supplied, else default 1
    scene_raw = values.get("scene_count")
    if scene_raw is not None and str(scene_raw).strip() != "":
        try:
            scene_count = int(scene_raw)
        except (TypeError, ValueError):
            return False, "INVALID_SCENE_COUNT", {}
        if scene_count < 1 or scene_count > 20:
            return False, "INVALID_SCENE_COUNT", {}
    else:
        scene_count = DEFAULT_SCENE_COUNT

    normalized = {
        "prompt": prompt,
        "trend_prompt": prompt,
        "quality_tier": tier,
        "scene_count": scene_count,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
    }
    return True, "", normalized


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 digest of normalized payload for idempotency & conflict detection."""
    core = {
        "product_key": str(payload.get("product_key") or CANONICAL_PRODUCT_KEY),
        "prompt": str(payload.get("prompt") or "").strip(),
        "quality_tier": int(payload.get("quality_tier") or DEFAULT_QUALITY_TIER),
        "scene_count": int(payload.get("scene_count") or DEFAULT_SCENE_COUNT),
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
    return f"VTR-{date_part}-{random_part}"


def generate_video_trend_job_id() -> str:
    return f"vtj_{uuid.uuid4().hex}"


def ensure_video_trend_schema() -> None:
    """Initialize dedicated web_video_trend_jobs SQLite table and indexes."""
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_trend_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'video_trend',
                routing_product_key TEXT NOT NULL DEFAULT 'trend_video',
                prompt TEXT NOT NULL,
                quality_tier INTEGER NOT NULL DEFAULT 200,
                scene_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'queued',
                status_reason TEXT NOT NULL DEFAULT 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope TEXT NOT NULL,
                output_metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                output_url TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_trend_jobs_account_created ON web_video_trend_jobs(account_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_trend_jobs_request ON web_video_trend_jobs(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_trend_jobs_account_idempotency ON web_video_trend_jobs(account_id, idempotency_key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_trend_jobs_status_created ON web_video_trend_jobs(status, created_at ASC)")


def create_or_replay_video_trend_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new canonical Video Trend job or replay existing one idempotently.

    Raises:
        HTTPException(400) on validation error
        HTTPException(401) on missing account
        HTTPException(409) on request_id/idempotency conflict with differing payload
    """
    ensure_video_trend_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Xác thực tài khoản Web là bắt buộc")

    is_valid, error_code, normalized = validate_video_trend_input(payload)
    if not is_valid:
        error_messages = {
            "authority_field_not_allowed": "Yêu cầu chứa trường authority bị cấm.",
            "PROMPT_REQUIRED": "Prompt hoặc trend_prompt là bắt buộc đối với Video theo trend.",
            "PROMPT_TOO_LONG": f"Prompt không được vượt quá {MAX_PROMPT_LENGTH} ký tự.",
            "INVALID_QUALITY_TIER": "Quality tier không hợp lệ. Phải thuộc (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500).",
            "INVALID_SCENE_COUNT": "Số cảnh không hợp lệ. Phải thuộc từ 1 đến 20 cảnh.",
        }
        raise HTTPException(status_code=400, detail=error_messages.get(error_code, error_code))

    payload_hash = compute_payload_hash(normalized)
    effective_req_id = str(request_id or payload.get("request_id") or "").strip()
    effective_idem_key = str(idempotency_key or payload.get("idempotency_key") or "").strip()
    idem_hash = compute_idempotency_hash(effective_idem_key) if effective_idem_key else ""

    with transaction() as conn:
        query = """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, quality_tier, scene_count, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_video_trend_jobs
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
            existing_payload_hash = str(row[11])
            if not hmac.compare_digest(existing_payload_hash, payload_hash):
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột mã yêu cầu: request_id hoặc idempotency_key đã gắn với payload khác.",
                )
            return _format_public_job(row, idempotent_replay=True)

        job_id = generate_video_trend_job_id()
        final_req_id = effective_req_id or generate_canonical_request_id()
        now = utc_now()

        bridge_envelope = {
            "version": "p0.video-trend.canonical-bridge.v1",
            "route_id": CANONICAL_ROUTE_ID,
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "product_family": "product_video",
            "flow_owner": "trend",
            "engine_route": CANONICAL_ROUTING_KEY,
            "executor_product_type": CANONICAL_PRODUCT_KEY,
            "required_capability": "text_to_video",
            "input_type": "trend_prompt",
            "worker_owner": "product_video",
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "request_id": final_req_id,
            "job_id": job_id,
            "account_id": owner_id,
            "prompt": normalized["prompt"],
            "trend_prompt": normalized["trend_prompt"],
            "quality_tier": normalized["quality_tier"],
            "scene_count": normalized["scene_count"],
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_AWAITING,
            "created_at": now,
            "output": None,
            "output_url": None,
        }
        envelope_json = json.dumps(bridge_envelope, ensure_ascii=True, sort_keys=True)

        conn.execute(
            """
            INSERT INTO web_video_trend_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                prompt, quality_tier, scene_count, status, status_reason,
                idempotency_key_hash, payload_hash, bridge_envelope,
                output_metadata, created_at, updated_at, output_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL)
            """,
            (
                job_id,
                final_req_id,
                owner_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                normalized["prompt"],
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
            "trend_prompt": normalized["trend_prompt"],
            "quality_tier": normalized["quality_tier"],
            "scene_count": normalized["scene_count"],
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_AWAITING,
            "output_available": False,
            "download_ready": False,
            "delivery_ready": False,
            "output": None,
            "output_url": None,
            "output_metadata": None,
            "created_at": now,
            "updated_at": now,
            "bridge_envelope": bridge_envelope,
            "idempotent_replay": False,
        }


def _format_public_job(row: tuple, *, idempotent_replay: bool = False) -> dict[str, Any]:
    try:
        env = json.loads(str(row[12])) if row[12] else {}
    except Exception:
        env = {}
    try:
        output_meta = json.loads(str(row[13])) if row[13] else None
    except Exception:
        output_meta = None

    status_str = str(row[8])
    is_completed = status_str == STATUS_COMPLETED
    raw_output_url = str(row[16]) if len(row) > 16 and row[16] is not None else None
    is_safe_url = bool(raw_output_url and is_safe_video_output_url(raw_output_url))
    has_real_output = bool(is_completed and is_safe_url)
    output_url_val = raw_output_url if has_real_output else None

    return {
        "id": str(row[0]),
        "request_id": str(row[1]),
        "account_id": str(row[2]),
        "product_key": str(row[3]),
        "routing_product_key": str(row[4]),
        "prompt": str(row[5]),
        "trend_prompt": str(row[5]),
        "quality_tier": int(row[6]),
        "scene_count": int(row[7]),
        "status": status_str,
        "status_reason": str(row[9]),
        "output_available": has_real_output,
        "download_ready": has_real_output,
        "delivery_ready": has_real_output,
        "output": output_url_val,
        "output_metadata": output_meta,
        "created_at": str(row[14]),
        "updated_at": str(row[15]),
        "bridge_envelope": env,
        "idempotent_replay": idempotent_replay,
        "output_url": output_url_val,
    }


def get_video_trend_job(account_id: str, job_id_or_request_id: str) -> dict[str, Any] | None:
    """Fetch one Video Trend job owned by the authenticated account."""
    owner_id = str(account_id or "").strip()
    target_id = str(job_id_or_request_id or "").strip()
    if not owner_id or not target_id:
        return None

    ensure_video_trend_schema()
    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, quality_tier, scene_count, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_video_trend_jobs
            WHERE account_id = ? AND (id = ? OR request_id = ?)
            LIMIT 1
            """,
            (owner_id, target_id, target_id),
        ).fetchone()

        if row is None:
            return None
        return _format_public_job(row)


def is_video_trend_job_other_account(job_id_or_request_id: str, account_id: str) -> bool:
    """Check if the job exists but belongs to a different user (for cross-user rejection)."""
    target_id = str(job_id_or_request_id or "").strip()
    owner_id = str(account_id or "").strip()
    if not target_id:
        return False

    ensure_video_trend_schema()
    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM web_video_trend_jobs
            WHERE (id = ? OR request_id = ?) AND account_id != ?
            LIMIT 1
            """,
            (target_id, target_id, owner_id),
        ).fetchone()
        return row is not None


def list_video_trend_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """List Video Trend jobs for the authenticated account."""
    owner_id = str(account_id or "").strip()
    if not owner_id:
        return []
    bounded_limit = max(1, min(int(limit or 100), 100))

    ensure_video_trend_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, quality_tier, scene_count, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_video_trend_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (owner_id, bounded_limit),
        ).fetchall()

        return [_format_public_job(r) for r in rows]


def video_trend_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Adapt a Video Trend job record for inclusion in generic GET /api/v1/jobs."""
    is_completed = job.get("status") == STATUS_COMPLETED
    is_processing = job.get("status") == "processing"
    source_state = "completed" if is_completed else ("processing_by_worker" if is_processing else "queued_locally")

    raw_output = job.get("output")
    is_safe_output = bool(raw_output and is_safe_video_output_url(str(raw_output)))

    canonical_output_available = bool(job.get("output_available")) and is_safe_output
    canonical_download_ready = bool(job.get("download_ready")) and is_safe_output
    canonical_delivery_ready = bool(job.get("delivery_ready")) and is_safe_output
    can_deliver = bool(canonical_output_available and canonical_delivery_ready)

    return {
        "id": job["id"],
        "feature": "video_trend",
        "job_type": "trend_video",
        "status": job["status"],
        "status_reason": job["status_reason"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "output_available": canonical_output_available,
        "download_ready": canonical_download_ready,
        "delivery_ready": canonical_delivery_ready,
        "source": "web_canonical_bridge",
        "source_state": source_state,
        "native_kind": "video-trend-job",
        "output": job.get("output") if can_deliver else None,
        "output_metadata": job.get("output_metadata"),
        "summary": {
            "prompt": job.get("prompt", "")[:100],
            "trend_prompt": job.get("trend_prompt", job.get("prompt", ""))[:100],
            "quality_tier": job.get("quality_tier", 0),
            "scene_count": job.get("scene_count", 1),
        },
    }
