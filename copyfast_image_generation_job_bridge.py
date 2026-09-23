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

ALLOWED_IMAGE_ASPECT_RATIOS: frozenset[str] = frozenset({
    "1:1",
    "1:4",
    "1:8",
    "2:3",
    "3:2",
    "3:4",
    "4:1",
    "4:3",
    "4:5",
    "5:4",
    "8:1",
    "9:16",
    "16:9",
    "21:9",
})

MAX_PROMPT_LENGTH = 2000

ALLOWED_INPUT_FIELDS: frozenset[str] = frozenset({
    "prompt",
    "text",
    "request",
    "description",
    "tier",
    "quality_tier",
    "tier_key",
    "aspect_ratio",
    "format",
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
FORBIDDEN_IMAGE_EXTENSIONS = frozenset({
    ".json", ".html", ".htm", ".txt", ".js", ".css", ".exe", ".sh", ".php",
    ".py", ".bin", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav",
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
    - Port must be None or 443.
    - Rejects error markers in URL path/query.
    - Rejects non-image file extensions.
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

    if parsed.port not in (None, 443):
        return False

    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in FORBIDDEN_IMAGE_EXTENSIONS):
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
    if "aspect_ratio" in normalized_payload and normalized_payload["aspect_ratio"] is not None:
        core["aspect_ratio"] = normalized_payload["aspect_ratio"]
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
    - Optional aspect_ratio; if provided, must be in ALLOWED_IMAGE_ASPECT_RATIOS.
    - Zero invented defaults: aspect_ratio omitted means None, not defaulted to 1:1.

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

    # 5. Aspect ratio validation (optional: no invented defaults)
    raw_ratio = payload.get("aspect_ratio") if "aspect_ratio" in payload else payload.get("format")
    normalized_ratio: str | None = None
    if raw_ratio is not None and str(raw_ratio).strip() != "":
        ratio_candidate = str(raw_ratio).strip().lower().replace("x", ":").replace(" ", "")
        if ratio_candidate not in ALLOWED_IMAGE_ASPECT_RATIOS:
            return False, "INVALID_ASPECT_RATIO", {}
        normalized_ratio = ratio_candidate

    normalized_payload: dict[str, Any] = {
        "prompt": prompt,
        "tier_key": tier_str,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
    }
    if normalized_ratio is not None:
        normalized_payload["aspect_ratio"] = normalized_ratio

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
                aspect_ratio TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                status_reason TEXT NOT NULL DEFAULT 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope_json TEXT NOT NULL,
                output_url TEXT,
                output_metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
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
                product_key, routing_product_key, prompt, tier_key, aspect_ratio,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope_json, output_url, output_metadata_json,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
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
                normalized_payload.get("aspect_ratio"),
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
        "status_reason": job.get("status_reason"),
        "tier_key": job.get("tier_key"),
        "aspect_ratio": job.get("aspect_ratio"),
        "output_available": output_available,
        "download_ready": output_available,
        "delivery_ready": output_available,
        "output": clean_output,
        "output_url": clean_output,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


def _format_image_generation_job_record(row: dict[str, Any]) -> dict[str, Any]:
    """Format raw database row into clean owner-scoped API dictionary."""
    output_url = row.get("output_url")
    is_safe_artifact = is_safe_image_output_url(output_url)
    output_available = bool(is_safe_artifact and row.get("status") == STATUS_COMPLETED)

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

    clean_output = output_url if output_available else None

    return {
        "id": row.get("id"),
        "canonical_job_id": row.get("canonical_job_id"),
        "request_id": row.get("request_id"),
        "account_id": row.get("account_id"),
        "product_key": row.get("product_key"),
        "routing_product_key": row.get("routing_product_key"),
        "prompt": row.get("prompt"),
        "tier_key": row.get("tier_key"),
        "aspect_ratio": row.get("aspect_ratio"),
        "status": row.get("status"),
        "status_reason": row.get("status_reason"),
        "output": clean_output,
        "output_url": clean_output,
        "output_available": output_available,
        "download_ready": output_available,
        "delivery_ready": output_available,
        "output_metadata": output_metadata if output_available else None,
        "bridge_envelope": envelope,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
