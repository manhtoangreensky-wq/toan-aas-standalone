"""Dedicated Canonical Durable Job Bridge for Video Long (video_long).

Task: P0.WEBAPP.V3.CUSTOMER.VIDEO_LONG.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: video_long
Entrypoint: /video/long
API: /api/v1/features/video_long/*
Bot Runtime Authority: services.video_tail9.PRODUCT_ADAPTERS['video_long']
(aliased by services.video_tail9.PRODUCT_ADAPTER_ALIASES['long_video'] = 'video_long')

Bot Contract Truth:
- flow_owner: video_long
- engine_route: video_long
- executor_product_type: multi_scene_film
- required_capability: text_to_video
- input_type: long_form_plan
- worker_owner: product_video
- scene_duration_seconds: 600
- maximum_scene_count: 20
- supported_quality_tiers: (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500)
- execution_enabled: False
- execution_blocker: long_video_under_upgrade

Zero Client Authority Injection:
- Browser never chooses identity, job ID, status, provider, wallet, Xu, cost, or output URLs.
- Authenticated Web account is strictly the owner authority.

Artifact Truth:
- Never infer output availability from status alone.
- status == 'completed' without a verified safe HTTPS artifact fails closed:
  output_available=False, download_ready=False, delivery_ready=False, output=None.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException

from copyfast_db import read_transaction, transaction


# ─── CANONICAL CONSTANTS ─────────────────────────────────────────────────────

CANONICAL_PRODUCT_KEY = "video_long"
CANONICAL_ROUTING_KEY = "video_long"
CANONICAL_ROUTE_ID = "video_long_canonical_v1"
CANONICAL_ENGINE_ADAPTER = "b01_tail9_video_long_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/video/long"
CANONICAL_EXECUTOR_PRODUCT_TYPE = "multi_scene_film"
CANONICAL_INPUT_TYPE = "long_form_plan"
CANONICAL_WORKER_OWNER = "product_video"
CANONICAL_FLOW_OWNER = "video_long"

STATUS_QUEUED = "queued"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
SUPPORTED_CANONICAL_JOB_ADAPTERS: frozenset[str] = frozenset({CANONICAL_PRODUCT_KEY})

ALLOWED_QUALITY_TIERS: tuple[int, ...] = (
    200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500,
)
MIN_SCENE_COUNT = 1
MAX_SCENE_COUNT = 20
MAX_PROMPT_LENGTH = 2000

FORBIDDEN_CLIENT_AUTHORITY_KEYS: frozenset[str] = frozenset({
    "account_id",
    "owner_id",
    "user_id",
    "canonical_user_id",
    "job_id",
    "id",
    "status",
    "status_reason",
    "provider",
    "provider_id",
    "provider_task_id",
    "output",
    "output_url",
    "download_url",
    "wallet",
    "wallet_id",
    "balance",
    "xu",
    "xu_charged",
    "price",
    "cost",
    "amount",
    "payment",
    "payment_id",
    "refund",
    "worker_id",
    "worker_owner",
    "bridge_envelope",
    "output_metadata",
})

SAFE_VIDEO_EXTENSIONS: frozenset[str] = frozenset({".mp4", ".webm", ".mov"})


# ─── SAFE OUTPUT URL VALIDATOR ───────────────────────────────────────────────

def is_safe_video_output_url(url: str | None) -> bool:
    """Validate that an output URL meets strict safety constraints.

    Must be:
    - Non-empty string <= 2048 chars
    - Scheme must be HTTPS
    - Hostname must be present and not contain credentials (@)
    - Port must be standard 443 (or None)
    - No relative path traversal ('..') or backslashes
    - Path must end in an allowed safe video extension (.mp4, .webm, .mov)
    """
    if not url or not isinstance(url, str):
        return False
    clean_url = url.strip()
    if len(clean_url) > 2048 or len(clean_url) < 8:
        return False
    try:
        parts = urlsplit(clean_url)
    except Exception:
        return False

    if parts.scheme.lower() != "https":
        return False
    if not parts.netloc or "@" in parts.netloc:
        return False
    if parts.port is not None and parts.port != 443:
        return False
    hostname = parts.hostname or ""
    if not hostname or "." not in hostname:
        return False

    path = parts.path
    if ".." in path or "\\" in path:
        return False

    lower_path = path.lower()
    return any(lower_path.endswith(ext) for ext in SAFE_VIDEO_EXTENSIONS)


# ─── ID & HASH GENERATORS ────────────────────────────────────────────────────

def generate_video_long_job_id() -> str:
    """Generate a collision-resistant canonical job identifier."""
    return f"vlj_{secrets.token_hex(16)}"


def generate_canonical_request_id() -> str:
    """Generate a collision-resistant canonical request identifier."""
    return f"req_vlong_{secrets.token_hex(12)}"


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
    stable_repr = json.dumps(
        {
            "prompt": normalized_payload.get("prompt", ""),
            "quality_tier": normalized_payload.get("quality_tier"),
            "scene_count": normalized_payload.get("scene_count"),
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(stable_repr.encode("utf-8")).hexdigest()


# ─── INPUT VALIDATOR ─────────────────────────────────────────────────────────

def validate_video_long_input(
    payload: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    """Validate client input according to source-derived video_long contract.

    Rules:
    - Zero client authority injection: rejects forbidden keys.
    - Requires text/prompt/script/long_form_plan (max 2000 chars).
    - Requires tier / quality_tier in ALLOWED_QUALITY_TIERS (no silent defaults).
    - Requires scene_count in MIN_SCENE_COUNT..MAX_SCENE_COUNT (1..20, no silent defaults).

    Returns:
        (is_valid, error_code, normalized_payload)
    """
    if not isinstance(payload, dict):
        return False, "invalid_payload_format", {}

    # 1. Client authority rejection
    for key in payload:
        clean_key = key.strip().lower()
        if clean_key in FORBIDDEN_CLIENT_AUTHORITY_KEYS:
            return False, "authority_field_not_allowed", {}

    # Check nested values for authority injection
    for v in payload.values():
        if isinstance(v, dict):
            for nested_k in v:
                if nested_k.strip().lower() in FORBIDDEN_CLIENT_AUTHORITY_KEYS:
                    return False, "authority_field_not_allowed", {}

    # 2. Text / prompt extraction
    raw_prompt = (
        payload.get("script")
        or payload.get("prompt")
        or payload.get("long_form_plan")
        or payload.get("text")
        or payload.get("brief")
        or ""
    )
    prompt = str(raw_prompt).strip()
    if not prompt:
        return False, "PROMPT_REQUIRED", {}
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, "PROMPT_TOO_LONG", {}

    # 3. Quality tier validation (strict: no silent default)
    raw_tier = payload.get("quality_tier") if "quality_tier" in payload else payload.get("tier")
    if raw_tier is None or str(raw_tier).strip() == "":
        return False, "TIER_REQUIRED", {}
    try:
        tier_val = int(raw_tier)
    except (ValueError, TypeError):
        return False, "INVALID_QUALITY_TIER", {}
    if tier_val not in ALLOWED_QUALITY_TIERS:
        return False, "INVALID_QUALITY_TIER", {}

    # 4. Scene count validation (strict: no silent default, 1..20)
    raw_scene_count = payload.get("scene_count")
    if raw_scene_count is None or str(raw_scene_count).strip() == "":
        return False, "SCENE_COUNT_REQUIRED", {}
    try:
        scene_count_val = int(raw_scene_count)
    except (ValueError, TypeError):
        return False, "INVALID_SCENE_COUNT", {}
    if not (MIN_SCENE_COUNT <= scene_count_val <= MAX_SCENE_COUNT):
        return False, "INVALID_SCENE_COUNT", {}

    normalized = {
        "prompt": prompt,
        "script": prompt,
        "long_form_plan": prompt,
        "quality_tier": tier_val,
        "scene_count": scene_count_val,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
    }
    return True, "", normalized


# ─── SCHEMA & PERSISTENCE ────────────────────────────────────────────────────

def ensure_video_long_schema() -> None:
    """Initialize dedicated web_video_long_jobs SQLite table and indexes."""
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_video_long_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'video_long',
                routing_product_key TEXT NOT NULL DEFAULT 'video_long',
                prompt TEXT NOT NULL,
                quality_tier INTEGER NOT NULL,
                scene_count INTEGER NOT NULL,
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_long_jobs_account_created ON web_video_long_jobs(account_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_long_jobs_request ON web_video_long_jobs(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_long_jobs_account_idempotency ON web_video_long_jobs(account_id, idempotency_key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_video_long_jobs_status_created ON web_video_long_jobs(status, created_at ASC)")


def create_or_replay_video_long_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new canonical Video Long job or replay existing one idempotently.

    Raises:
        HTTPException(400) on validation error
        HTTPException(401) on missing account
        HTTPException(409) on request_id/idempotency conflict with differing payload
    """
    ensure_video_long_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Xác thực tài khoản Web là bắt buộc")

    is_valid, error_code, normalized = validate_video_long_input(payload)
    if not is_valid:
        error_messages = {
            "authority_field_not_allowed": "Yêu cầu video_long có trường hệ thống không được phép; Web không nhận identity, Xu, provider, job hoặc output từ browser.",
            "PROMPT_REQUIRED": "Prompt hoặc script là bắt buộc đối với Video dài.",
            "PROMPT_TOO_LONG": f"Prompt không được vượt quá {MAX_PROMPT_LENGTH} ký tự.",
            "TIER_REQUIRED": "Quality tier là bắt buộc (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500).",
            "INVALID_QUALITY_TIER": "Quality tier không hợp lệ. Phải thuộc (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500).",
            "SCENE_COUNT_REQUIRED": "Số cảnh scene_count là bắt buộc (1..20).",
            "INVALID_SCENE_COUNT": "Số cảnh không hợp lệ. Phải thuộc từ 1 đến 20 cảnh.",
        }
        detail = error_messages.get(error_code, f"Dữ liệu đầu vào không hợp lệ: {error_code}")
        raise HTTPException(status_code=400, detail=detail)

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
            FROM web_video_long_jobs
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

        job_id = generate_video_long_job_id()
        final_req_id = effective_req_id or generate_canonical_request_id()
        now = utc_now()

        bridge_envelope = {
            "version": "p0.video-long.canonical-bridge.v1",
            "route_id": CANONICAL_ROUTE_ID,
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "product_family": "product_video",
            "flow_owner": CANONICAL_FLOW_OWNER,
            "engine_route": CANONICAL_ROUTING_KEY,
            "executor_product_type": CANONICAL_EXECUTOR_PRODUCT_TYPE,
            "required_capability": "text_to_video",
            "input_type": CANONICAL_INPUT_TYPE,
            "worker_owner": CANONICAL_WORKER_OWNER,
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "request_id": final_req_id,
            "job_id": job_id,
            "account_id": owner_id,
            "prompt": normalized["prompt"],
            "script": normalized["script"],
            "long_form_plan": normalized["long_form_plan"],
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
            INSERT INTO web_video_long_jobs (
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

        created_row = (
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
            None,
            now,
            now,
            None,
        )
        return _format_public_job(created_row, idempotent_replay=False)


def _format_public_job(row: Any, idempotent_replay: bool = False) -> dict[str, Any]:
    """Project SQLite tuple into truthful public API schema."""
    (
        job_id,
        request_id,
        account_id,
        product_key,
        routing_product_key,
        prompt,
        quality_tier,
        scene_count,
        status,
        status_reason,
        idem_hash,
        payload_hash,
        envelope_str,
        metadata_str,
        created_at,
        updated_at,
        output_url,
    ) = row

    envelope_dict: dict[str, Any] = {}
    if envelope_str:
        try:
            envelope_dict = json.loads(envelope_str)
        except Exception:
            envelope_dict = {}

    metadata_dict: dict[str, Any] = {}
    if metadata_str:
        try:
            metadata_dict = json.loads(metadata_str)
        except Exception:
            metadata_dict = {}

    # Strict safe artifact verification
    is_safe_artifact = is_safe_video_output_url(output_url)
    effective_output = output_url if (status == "completed" and is_safe_artifact) else None
    output_ready = bool(status == "completed" and is_safe_artifact)

    return {
        "id": job_id,
        "request_id": request_id,
        "account_id": account_id,
        "product_key": product_key,
        "routing_product_key": routing_product_key,
        "prompt": prompt,
        "script": prompt,
        "long_form_plan": prompt,
        "quality_tier": quality_tier,
        "scene_count": scene_count,
        "status": status,
        "status_reason": status_reason,
        "created_at": created_at,
        "updated_at": updated_at,
        "output": effective_output,
        "output_url": effective_output,
        "output_available": output_ready,
        "download_ready": output_ready,
        "delivery_ready": output_ready,
        "output_metadata": metadata_dict if is_safe_artifact else {},
        "bridge_envelope": envelope_dict,
        "idempotent_replay": idempotent_replay,
    }


def get_video_long_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    """Retrieve single job owned strictly by account_id."""
    ensure_video_long_schema()
    owner_id = str(account_id or "").strip()
    jid = str(job_id or "").strip()
    if not owner_id or not jid:
        return None

    with read_transaction() as conn:
        query = """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, quality_tier, scene_count, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_video_long_jobs
            WHERE account_id = ? AND id = ?
            LIMIT 1
        """
        row = conn.execute(query, (owner_id, jid)).fetchone()
        if row is None:
            return None
        return _format_public_job(row)


def is_video_long_job_other_account(job_id: str, account_id: str) -> bool:
    """Check if job exists under a different account for strict 403 isolation."""
    ensure_video_long_schema()
    jid = str(job_id or "").strip()
    owner_id = str(account_id or "").strip()
    if not jid:
        return False

    with read_transaction() as conn:
        row = conn.execute(
            "SELECT account_id FROM web_video_long_jobs WHERE id = ? LIMIT 1",
            (jid,),
        ).fetchone()
        if row is None:
            return False
        return str(row[0]) != owner_id


def list_video_long_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """List jobs owned by account_id ordered by created_at DESC."""
    ensure_video_long_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        return []

    safe_limit = max(1, min(limit, 200))
    with read_transaction() as conn:
        query = """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, quality_tier, scene_count, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_video_long_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = conn.execute(query, (owner_id, safe_limit)).fetchall()
        return [_format_public_job(row) for row in rows]


def video_long_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Project video_long job into generic /api/v1/jobs format with safe artifact truth."""
    is_safe = is_safe_video_output_url(job.get("output_url"))
    status = job.get("status", STATUS_QUEUED)
    effective_output = job.get("output_url") if (status == "completed" and is_safe) else None
    output_ready = bool(status == "completed" and is_safe)

    return {
        "id": job["id"],
        "kind": "video_long",
        "job_type": "video_long",
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
        "status": status,
        "status_reason": job.get("status_reason", STATUS_REASON_AWAITING),
        "prompt": job.get("prompt", ""),
        "script": job.get("script", ""),
        "long_form_plan": job.get("long_form_plan", ""),
        "quality_tier": job.get("quality_tier"),
        "scene_count": job.get("scene_count"),
        "created_at": job.get("created_at", ""),
        "updated_at": job.get("updated_at", ""),
        "output": effective_output,
        "output_url": effective_output,
        "output_available": output_ready,
        "download_ready": output_ready,
        "delivery_ready": output_ready,
        "canonical_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
    }
