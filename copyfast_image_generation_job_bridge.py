"""Image Generation Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.IMAGE_GENERATION.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Master Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Connects the Web customer flow (/image/create) for `image_create`
to a canonical Bot-compatible job bridge contract without executing real image
generations, paid provider calls, or wallet balance mutations.

Runtime Authority Reference:
- services.video_ai_real_pricing.public_image_quality_catalog
- services.video_ai_real_pricing.public_image_quality_by_tier
- bot_capability: image_generation
- web_feature_key: image_create
- web_customer_entrypoint: /image/create
- web_api_family: /api/v1/features/image_create/*
- bot_authority_repo: manhtoangreensky-wq/bot
- bot_authority_sha: c0d9aec4620db6cf436966045557ab080b0f071c

Invariants:
- Fail-Closed Admission: zero provider calls until Owner-authorized runtime execution.
- Truthful Status: initial status is 'queued', status_reason is
  'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'. Zero fake output, zero fake completion.
- Output Fail-Closed: output_available=False, download_ready=False, delivery_ready=False,
  output=None until verifiable safe artifact URL exists.
- Idempotency & Conflict: replay existing job on identical payload hash, reject with 409
  on same account/idempotency_key with differing payload.
- Isolated Adapter: bounded specifically to `image_create` / `image_generation`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
import secrets
from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException

from copyfast_db import read_transaction, transaction


# ─── CANONICAL CONSTANTS ─────────────────────────────────────────────────────

CANONICAL_PRODUCT_KEY = "image_create"
CANONICAL_ROUTING_KEY = "image_generation"
CANONICAL_CUSTOMER_ENTRYPOINT = "/image/create"
CANONICAL_API_FAMILY = "/api/v1/features/image_create/*"
CANONICAL_BOT_CAPABILITY = "image_generation"
CANONICAL_CATEGORY = "image_ai"
CANONICAL_RUNTIME_REFERENCE = "services.video_ai_real_pricing.public_image_quality_catalog"

STATUS_QUEUED = "queued"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

SUPPORTED_CANONICAL_JOB_ADAPTERS: frozenset[str] = frozenset({
    CANONICAL_PRODUCT_KEY,
    CANONICAL_ROUTING_KEY,
})

ALLOWED_IMAGE_TIER_KEYS: tuple[str, ...] = (
    "low",
    "standard",
    "standard_warranty",
    "common",
    "common_warranty",
    "high",
    "high_warranty",
)

MAX_PROMPT_LENGTH = 2000

ALLOWED_INPUT_FIELDS: frozenset[str] = frozenset({
    "prompt",
    "text",
    "request",
    "description",
    "tier",
    "quality_tier",
    "tier_key",
})

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "id", "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "providertaskid", "autoprovider",
    "apikey", "apitoken", "token", "secret", "jobid", "jobstatus", "status", "statusreason",
    "output", "outputurl", "downloadurl", "finalartifactpath", "outputsha256",
    "assetid", "role", "balance", "xu", "amountxu", "unitxu", "costxu", "wallet", "authority",
    "accountid", "ownerid", "userid", "user_id", "account_id", "owner_id",
    "refund", "refundstatus", "refund_status", "bridgeenvelope", "outputmetadata",
    "model", "modelname", "modelkey", "retrycount", "retrywarrantycount",
    "delivery", "deliverymessageid", "chargeplan", "adminnocharge", "receipt",
    "createdat", "updatedat",
})
FORBIDDEN_CLIENT_AUTHORITY_KEYS: frozenset[str] = FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED

SAFE_HOSTNAME_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
FORBIDDEN_OUTPUT_URL_SCHEMES = frozenset({
    "javascript:", "vbscript:", "data:", "file:", "blob:", "about:", "http:",
})
SAFE_IMAGE_EXTENSIONS = frozenset({
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
})
FORBIDDEN_IMAGE_ERROR_MARKERS = (
    "/error", "error=", "failed=", "status=fail", "status=error",
)


# ─── URL VALIDATOR ───────────────────────────────────────────────────────────

def is_safe_image_output_url(url: Any) -> bool:
    """Validate that candidate image output/artifact URL is safe to deliver.

    Fail-closed security contract:
    - Must be a non-empty string with len <= 2048 and no leading/trailing whitespace.
    - Zero control characters.
    - Zero backslashes.
    - Zero directory traversal sequences ('..' or '%2e').
    - Strict scheme check: must be 'https'.
    - Rejects dangerous schemes.
    - Rejects embedded credentials ('@').
    - Hostname must match SAFE_HOSTNAME_PATTERN (at least two labels, valid characters).
    - Port must be None or 443 (fails closed on ValueError/out-of-range port).
    - Rejects error markers in URL path/query.
    - Path must have an extension belonging strictly to SAFE_IMAGE_EXTENSIONS (.jpg, .jpeg, .png, .webp).
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
    if any(lowered.startswith(scheme) for scheme in FORBIDDEN_OUTPUT_URL_SCHEMES):
        return False
    if not lowered.startswith("https://"):
        return False
    parts = lowered.split("/", 3)
    if len(parts) > 2 and "@" in parts[2]:
        return False
    if any(marker in lowered for marker in FORBIDDEN_IMAGE_ERROR_MARKERS):
        return False

    try:
        parsed = urlsplit(url)
    except Exception:
        return False

    if parsed.scheme.lower() != "https":
        return False
    if parsed.username or parsed.password:
        return False
    if not parsed.hostname:
        return False

    hostname = parsed.hostname.lower()
    if not SAFE_HOSTNAME_PATTERN.fullmatch(hostname):
        return False

    try:
        port = parsed.port
    except ValueError:
        return False

    if port not in (None, 443):
        return False

    path_lower = parsed.path.lower()
    if not any(path_lower.endswith(ext) for ext in SAFE_IMAGE_EXTENSIONS):
        return False

    return True


# ─── AUTHORITY CHECK ─────────────────────────────────────────────────────────

def _contains_authority_field(value: Any) -> bool:
    """Recursively find forged authority fields in incoming client input."""
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


# ─── IDENTITY AND HASHES ─────────────────────────────────────────────────────

def generate_image_generation_job_id() -> str:
    """Generate server-side cryptographically secure job identifier."""
    return f"img_{secrets.token_hex(12)}"


def generate_canonical_request_id() -> str:
    """Generate server-side request tracking identity."""
    return f"req_img_{secrets.token_hex(12)}"


def utc_now() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def compute_idempotency_hash(idempotency_key: str) -> str:
    """Compute SHA-256 hash of idempotency key for indexed lookup."""
    clean_key = str(idempotency_key or "").strip()
    if not clean_key:
        return ""
    return hashlib.sha256(clean_key.encode("utf-8")).hexdigest()


def compute_payload_hash(normalized_payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash over canonical normalized inputs."""
    core = {
        "product_key": CANONICAL_PRODUCT_KEY,
        "prompt": normalized_payload.get("prompt", ""),
        "routing_key": CANONICAL_ROUTING_KEY,
        "tier_key": normalized_payload.get("tier_key"),
    }
    stable_repr = json.dumps(
        core,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable_repr.encode("utf-8")).hexdigest()


# ─── INPUT VALIDATOR ─────────────────────────────────────────────────────────

def validate_image_generation_input(payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Validate client input payload for Image Generation (image_create / image_generation).

    Fail-closed security contract:
    - Rejects forged client authority fields recursively.
    - Rejects unknown unproven input fields (unsupported_input_field).
    - Requires prompt/text with 1 <= len <= MAX_PROMPT_LENGTH (2000).
    - Requires tier_key in ALLOWED_IMAGE_TIER_KEYS (no silent defaults, rejects numeric video tiers).
    - Aspect ratio has no committed Web authority enum and is rejected fail-closed (unsupported_input_field).

    Returns:
        (is_valid, error_code, normalized_payload)
    """
    if not isinstance(payload, dict):
        return False, "invalid_payload_format", {}

    # 1. Recursive normalized client authority rejection
    if _contains_authority_field(payload):
        return False, "authority_field_not_allowed", {}

    # 2. Strict allowlist: reject unknown unproven input fields
    for key in payload.keys():
        if key not in ALLOWED_INPUT_FIELDS:
            return False, "unsupported_input_field", {}

    # 3. Prompt extraction and validation
    raw_prompt = (
        payload.get("prompt")
        or payload.get("text")
        or payload.get("request")
        or payload.get("description")
        or ""
    )
    prompt = str(raw_prompt).strip()
    if not prompt:
        return False, "PROMPT_REQUIRED", {}
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, "PROMPT_TOO_LONG", {}

    # 4. Quality tier validation (strict: no silent default, rejects numeric tiers)
    raw_tier = (
        payload.get("tier_key")
        if "tier_key" in payload
        else (payload.get("tier") if "tier" in payload else payload.get("quality_tier"))
    )
    if raw_tier is None or str(raw_tier).strip() == "":
        return False, "TIER_REQUIRED", {}
    tier_str = str(raw_tier).strip().lower()
    if tier_str not in ALLOWED_IMAGE_TIER_KEYS:
        return False, "INVALID_IMAGE_TIER", {}

    normalized_payload: dict[str, Any] = {
        "prompt": prompt,
        "tier_key": tier_str,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
    }

    return True, "", normalized_payload


# ─── DURABLE STORAGE AND IDEMPOTENCY ─────────────────────────────────────────

def ensure_image_generation_schema(conn: Any = None) -> None:
    """Ensure the web_image_generation_jobs table and indexes exist."""
    def _create(c: Any) -> None:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_generation_jobs (
                id TEXT PRIMARY KEY,
                canonical_job_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'image_create',
                routing_product_key TEXT NOT NULL DEFAULT 'image_generation',
                prompt TEXT NOT NULL,
                tier_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                status_reason TEXT NOT NULL DEFAULT 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope_json TEXT NOT NULL,
                output_url TEXT,
                output_metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                runtime_job_id TEXT,
                quote_xu INTEGER NOT NULL DEFAULT 0,
                charged_xu INTEGER NOT NULL DEFAULT 0,
                runtime_dispatch_status TEXT NOT NULL DEFAULT 'undispatched',
                runtime_dispatched_at TEXT,
                completed_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        for col, col_def in [
            ("runtime_job_id", "TEXT"),
            ("quote_xu", "INTEGER NOT NULL DEFAULT 0"),
            ("charged_xu", "INTEGER NOT NULL DEFAULT 0"),
            ("runtime_dispatch_status", "TEXT NOT NULL DEFAULT 'undispatched'"),
            ("runtime_dispatched_at", "TEXT"),
            ("completed_at", "TEXT"),
        ]:
            try:
                c.execute(f"ALTER TABLE web_image_generation_jobs ADD COLUMN {col} {col_def}")
            except Exception:
                pass
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_image_generation_jobs_account_created ON web_image_generation_jobs(account_id, created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_image_generation_jobs_request ON web_image_generation_jobs(request_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_image_generation_jobs_account_idempotency ON web_image_generation_jobs(account_id, idempotency_key_hash)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_image_generation_jobs_status_created ON web_image_generation_jobs(status, created_at ASC)")

    if conn is not None:
        _create(conn)
    else:
        with transaction() as c:
            _create(c)


def create_or_replay_image_generation_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Atomically create a new image_generation job or replay an identical existing job.

    Enforces fail-closed serializable semantics:
    - Same account + same key + identical payload -> replay existing job record.
    - Same account + same key + differing payload -> HTTP 409 Conflict.
    - Initial status is queued with AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION.
    - Zero provider calls, zero image generations, zero wallet mutations.
    """
    clean_account_id = str(account_id or "").strip()
    if not clean_account_id:
        raise HTTPException(status_code=401, detail="account_id_required")

    is_valid, error_code, normalized_payload = validate_image_generation_input(payload)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=error_code,
        )

    clean_key = str(idempotency_key or "").strip()
    key_hash = compute_idempotency_hash(clean_key) if clean_key else ""
    payload_hash = compute_payload_hash(normalized_payload)

    with transaction() as conn:
        ensure_image_generation_schema(conn)
        # 1. Check idempotency replay within transaction
        if key_hash:
            cursor = conn.execute(
                "SELECT * FROM web_image_generation_jobs WHERE account_id = ? AND idempotency_key_hash = ?",
                (clean_account_id, key_hash),
            )
            existing_row = cursor.fetchone()
            if existing_row:
                col_names = [col[0] for col in cursor.description]
                existing_job = dict(zip(col_names, existing_row))
                if existing_job.get("payload_hash") != payload_hash:
                    raise HTTPException(
                        status_code=409,
                        detail="IDEMPOTENCY_CONFLICT: differing payload submitted for identical idempotency key",
                    )
                return _format_image_generation_job_record(existing_job)

        # 2. Insert new canonical queued job
        job_id = generate_image_generation_job_id()
        request_id = generate_canonical_request_id()
        now_ts = utc_now()

        bridge_envelope = {
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "bot_capability": CANONICAL_BOT_CAPABILITY,
            "category": CANONICAL_CATEGORY,
            "canonical_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
            "runtime_reference": CANONICAL_RUNTIME_REFERENCE,
            "execution_enabled": False,
            "execution_blocker": "IMAGE_GENERATION_RUNTIME_EXECUTION_NOT_ACTIVATED",
        }

        conn.execute(
            """
            INSERT INTO web_image_generation_jobs (
                id, canonical_job_id, request_id, account_id,
                product_key, routing_product_key, prompt, tier_key,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope_json, output_url, output_metadata_json,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?
            )
            """,
            (
                job_id,
                job_id,
                request_id,
                clean_account_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                normalized_payload["prompt"],
                normalized_payload["tier_key"],
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                key_hash if key_hash else None,
                payload_hash,
                json.dumps(bridge_envelope),
                None,
                None,
                now_ts,
                now_ts,
            ),
        )

        cursor = conn.execute(
            "SELECT * FROM web_image_generation_jobs WHERE id = ?",
            (job_id,),
        )
        row = cursor.fetchone()
        col_names = [col[0] for col in cursor.description]
        return _format_image_generation_job_record(dict(zip(col_names, row)))


def get_image_generation_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    """Retrieve an owner-scoped image_generation job by canonical job ID."""
    clean_account_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not clean_account_id or not clean_job_id:
        return None

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM web_image_generation_jobs WHERE id = ? AND account_id = ?",
            (clean_job_id, clean_account_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        col_names = [col[0] for col in cursor.description]
        return _format_image_generation_job_record(dict(zip(col_names, row)))


def list_image_generation_jobs(account_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """List owner-scoped image_generation jobs ordered newest first."""
    clean_account_id = str(account_id or "").strip()
    if not clean_account_id:
        return []

    safe_limit = max(1, min(limit, 100))
    with read_transaction() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM web_image_generation_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (clean_account_id, safe_limit),
        )
        rows = cursor.fetchall()
        col_names = [col[0] for col in cursor.description]
        return [_format_image_generation_job_record(dict(zip(col_names, r))) for r in rows]


def is_image_generation_job_other_account(job_id: str, requester_account_id: str) -> bool:
    """Return True if job exists but belongs to a different owner."""
    clean_job_id = str(job_id or "").strip()
    clean_requester = str(requester_account_id or "").strip()
    if not clean_job_id or not clean_requester:
        return False

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT account_id FROM web_image_generation_jobs WHERE id = ?",
            (clean_job_id,),
        )
        row = cursor.fetchone()
        if not row:
            return False
        owner_id = str(row[0] or "").strip()
        return owner_id != clean_requester


# ─── NATIVE WEB COMPATIBILITY PROJECTION ─────────────────────────────────────

def image_generation_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Map image_generation job to standard Web job contract.

    Enforces fail-closed output truth:
    - Never project output availability from status == 'completed' alone.
    - Requires verified safe HTTPS output_url.
    """
    output_url = job.get("output_url")
    is_safe = is_safe_image_output_url(output_url)

    output_available = bool(is_safe and job.get("status") == STATUS_COMPLETED)
    clean_output = output_url if output_available else None
    is_queued = job.get("status") not in (STATUS_COMPLETED, "processing")
    runtime_active = _is_runtime_execution_active("image_create")
    if is_queued and not runtime_active:
        source_state = "guarded_runtime_unavailable"
        status_reason = "RUNTIME_EXECUTION_NOT_ACTIVATED"
        runtime_active = False
    else:
        source_state = job.get("source_state") or ("completed" if job.get("status") == STATUS_COMPLETED else ("processing_by_worker" if job.get("status") == "processing" else "queued_locally"))
        status_reason = job.get("status_reason")

    return {
        "id": job.get("id"),
        "job_id": job.get("id"),
        "canonical_job_id": job.get("canonical_job_id"),
        "kind": "image",
        "job_type": "image",
        "product_type": "image_create",
        "feature": "image_create",
        "service_context": "image_create",
        "canonical_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
        "status": job.get("status"),
        "status_reason": status_reason,
        "tier_key": job.get("tier_key"),
        "output_available": output_available,
        "download_ready": output_available,
        "delivery_ready": output_available,
        "output": clean_output,
        "output_url": clean_output,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "source_state": source_state,
        "runtime_execution_active": runtime_active,
    }


def _is_runtime_execution_active(feature: str = "image_create") -> bool:
    try:
        import sys
        copyfast_api = sys.modules.get("copyfast_api")
        if copyfast_api is None:
            import copyfast_api
        return feature in getattr(copyfast_api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset())
    except Exception:
        return False


def _format_image_generation_job_record(row: dict[str, Any]) -> dict[str, Any]:
    """Format raw database row into clean owner-scoped API dictionary."""
    status_str = str(row.get("status") or "")
    is_completed = status_str == STATUS_COMPLETED
    is_terminal_failure = status_str in ("failed", "cancelled", "rejected")
    is_non_terminal = not is_completed and not is_terminal_failure
    runtime_active = _is_runtime_execution_active("image_create")

    if is_non_terminal and not runtime_active:
        runtime_execution_active = False
        projected_status_reason = "RUNTIME_EXECUTION_NOT_ACTIVATED"
        source_state = "guarded_runtime_unavailable"
        output_available = False
        download_ready = False
        delivery_ready = False
        clean_output = None
    else:
        runtime_execution_active = runtime_active
        projected_status_reason = row.get("status_reason")
        source_state = "completed" if is_completed else ("failed" if is_terminal_failure else "queued_locally")
        output_url = row.get("output_url")
        is_safe_artifact = is_safe_image_output_url(output_url)
        output_available = bool(is_safe_artifact and is_completed)
        download_ready = output_available
        delivery_ready = output_available
        clean_output = output_url if output_available else None

    envelope: dict[str, Any] = {}
    if row.get("bridge_envelope_json"):
        try:
            envelope = json.loads(row["bridge_envelope_json"])
        except Exception:
            envelope = {}

    output_metadata: dict[str, Any] | None = None
    if row.get("output_metadata_json"):
        try:
            output_metadata = json.loads(row["output_metadata_json"])
        except Exception:
            output_metadata = None

    job_id = str(row.get("id") or "")
    artifact_url = f"/api/v1/features/image_create/jobs/{job_id}/artifact" if is_completed else None

    return {
        "id": job_id,
        "canonical_job_id": row.get("canonical_job_id"),
        "request_id": row.get("request_id"),
        "account_id": row.get("account_id"),
        "product_key": row.get("product_key"),
        "routing_product_key": row.get("routing_product_key"),
        "prompt": row.get("prompt"),
        "tier_key": row.get("tier_key"),
        "status": status_str,
        "status_reason": projected_status_reason,
        "source_state": source_state,
        "runtime_execution_active": runtime_execution_active,
        "quote_xu": int(row.get("quote_xu") or 0),
        "charged_xu": int(row.get("charged_xu") or 0),
        "runtime_job_id": row.get("runtime_job_id"),
        "runtime_dispatch_status": row.get("runtime_dispatch_status") or "undispatched",
        "has_artifact": bool(is_completed),
        "can_download": bool(is_completed),
        "artifact_url": artifact_url,
        "output": clean_output,
        "output_url": clean_output,
        "output_available": output_available,
        "download_ready": download_ready,
        "delivery_ready": delivery_ready,
        "output_metadata": output_metadata if output_available else None,
        "bridge_envelope": envelope,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "completed_at": row.get("completed_at"),
    }


# ─── CANONICAL RUNTIME DISPATCH & CONFIRM ────────────────────────────────────

async def dispatch_image_generation_job_to_canonical_runtime(
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Dispatch an admitted Web Image Generation job to canonical Bot Core runtime."""
    ensure_image_generation_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        return {}

    job = get_image_generation_job(account_id, clean_job_id)
    if not job:
        return {}
    if job.get("status") == STATUS_COMPLETED:
        return job

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured() or not canonical_user_id:
        return job

    canonical_payload = {
        "prompt": job["prompt"],
        "tier_key": job["tier_key"],
        "aspect_ratio": "1:1",
        "idempotency_key": f"{canonical_user_id}:{clean_job_id}",
        "web_request_id": job.get("request_id") or clean_job_id,
    }

    try:
        res = await bridge_request(
            "POST",
            "/internal/v1/web-image/jobs",
            payload=canonical_payload,
            request_id=f"DISPATCH-{job['request_id']}",
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
        if isinstance(res, dict) and res.get("ok"):
            bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
            rt_id = str(bot_job.get("job_id") or "").strip() if isinstance(bot_job, dict) else ""
            if rt_id:
                bot_quote = int(bot_job.get("quote_xu") or 0)
                bot_status = str(bot_job.get("status") or "")
                with transaction() as conn:
                    conn.execute(
                        """
                        UPDATE web_image_generation_jobs
                        SET runtime_job_id = ?,
                            quote_xu = ?,
                            runtime_dispatch_status = 'dispatched',
                            runtime_dispatched_at = ?,
                            updated_at = ?
                        WHERE id = ? AND status != 'completed'
                        """,
                        (rt_id, bot_quote, utc_now(), utc_now(), clean_job_id),
                    )
            else:
                with transaction() as conn:
                    conn.execute(
                        """
                        UPDATE web_image_generation_jobs
                        SET runtime_dispatch_status = 'failed',
                            status_reason = 'BOT_JOB_ID_MISSING',
                            updated_at = ?
                        WHERE id = ? AND status != 'completed'
                        """,
                        (utc_now(), clean_job_id),
                    )
        else:
            err_reason = str((res.get("error_code") if isinstance(res, dict) else "") or "BOT_PREPARE_FAILED")
            with transaction() as conn:
                conn.execute(
                    """
                    UPDATE web_image_generation_jobs
                    SET runtime_dispatch_status = 'failed',
                        status_reason = ?,
                        updated_at = ?
                    WHERE id = ? AND status != 'completed'
                    """,
                    (err_reason, utc_now(), clean_job_id),
                )
    except Exception:
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_image_generation_jobs
                SET runtime_dispatch_status = 'uncertain',
                    status_reason = 'BRIDGE_DISPATCH_EXCEPTION',
                    updated_at = ?
                WHERE id = ? AND status != 'completed'
                """,
                (utc_now(), clean_job_id),
            )

    return get_image_generation_job(account_id, clean_job_id) or {}


async def confirm_image_generation_job(
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Confirm and execute Web Image Generation job against canonical Bot Core."""
    ensure_image_generation_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    job = get_image_generation_job(account_id, clean_job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error_code": "JOB_NOT_FOUND", "message": "Không tìm thấy job Tạo ảnh AI của tài khoản"})

    if job.get("status") == STATUS_COMPLETED:
        return job

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured():
        raise HTTPException(status_code=503, detail={"error_code": "BRIDGE_NOT_CONFIGURED", "message": "Core Bridge chưa được cấu hình"})
    if not canonical_user_id:
        raise HTTPException(status_code=403, detail={"error_code": "TELEGRAM_LINK_REQUIRED", "message": "Tài khoản chưa liên kết Telegram"})

    # Dispatch first if needed
    if not job.get("runtime_job_id"):
        job = await dispatch_image_generation_job_to_canonical_runtime(job_id=clean_job_id, account=account, request=request)

    rt_id = str(job.get("runtime_job_id") or "").strip()
    if not rt_id:
        raise HTTPException(status_code=502, detail={"error_code": "BOT_RUNTIME_UNAVAILABLE", "message": "Cannot confirm job: Bot runtime not ready"})

    res = await bridge_request(
        "POST",
        f"/internal/v1/web-image/jobs/{rt_id}/confirm",
        payload={},
        request_id=f"CONFIRM-{job['request_id']}",
        actor_id=canonical_user_id,
        owner_id=canonical_user_id,
    )

    if isinstance(res, dict) and res.get("ok"):
        bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
        bot_status = str(bot_job.get("status") or "completed")
        charged_xu = int(bot_job.get("charged_xu") or 0)
        completed_at = bot_job.get("completed_at") if bot_status == "completed" else None
        output_url = str(bot_job.get("output_url") or "").strip() or None
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_image_generation_jobs
                SET status = ?,
                    charged_xu = ?,
                    output_url = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (bot_status, charged_xu, output_url, completed_at, utc_now(), clean_job_id),
            )
        return get_image_generation_job(account_id, clean_job_id) or {}
    else:
        err_code = str((res.get("error_code") if isinstance(res, dict) else "") or "CONFIRM_FAILED")
        err_msg = str((res.get("message") if isinstance(res, dict) else "") or "Bot execution failed")
        status_code = int(res.get("http_status") or 422) if isinstance(res, dict) else 422
        raise HTTPException(status_code=status_code, detail={"error_code": err_code, "message": err_msg})


async def reconcile_image_generation_job_status(
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Reconcile and sync Web Image Generation job status from Bot Core."""
    ensure_image_generation_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    job = get_image_generation_job(account_id, clean_job_id)
    if not job:
        return {}

    if job.get("status") == STATUS_COMPLETED:
        return job

    rt_id = str(job.get("runtime_job_id") or "").strip()
    if not rt_id:
        return job

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured() or not canonical_user_id:
        return job

    try:
        res = await bridge_request(
            "GET",
            f"/internal/v1/web-image/jobs/{rt_id}",
            payload={},
            request_id=f"RECONCILE-{job['request_id']}",
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
        if isinstance(res, dict) and res.get("ok"):
            bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
            bot_status = str(bot_job.get("status") or "")
            charged_xu = int(bot_job.get("charged_xu") or 0)
            completed_at = bot_job.get("completed_at") if bot_status == "completed" else None
            bot_output = str(bot_job.get("output_url") or "").strip() or None
            with transaction() as conn:
                conn.execute(
                    """
                    UPDATE web_image_generation_jobs
                    SET status = ?,
                        charged_xu = ?,
                        output_url = CASE WHEN ? IS NOT NULL THEN ? ELSE output_url END,
                        completed_at = CASE WHEN ? IS NOT NULL THEN ? ELSE completed_at END,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (bot_status, charged_xu, bot_output, bot_output, completed_at, completed_at, utc_now(), clean_job_id),
                )
    except Exception:
        pass

    return get_image_generation_job(account_id, clean_job_id) or {}
