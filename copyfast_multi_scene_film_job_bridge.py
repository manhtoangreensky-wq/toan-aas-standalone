"""Dedicated Canonical Durable Job Bridge for Multi-Scene Film (multi_scene_film / video_multiscene).

Task: P0.WEBAPP.V3.CUSTOMER.MULTI_SCENE_FILM.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: multi_scene_film
Web Feature Key: video_multiscene
Customer Entrypoint: /video/multiscene
Web API Family: /api/v1/features/video_multiscene/*
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: c0d9aec4620db6cf436966045557ab080b0f071c
Bot Adapter: services.video_tail9.PRODUCT_ADAPTERS["multi_scene_film"]
Bot Runtime Engine: services.product_video_multiscene_engine

Bot Contract Truth:
- flow_owner: scene3
- engine_route: multi_scene_film
- executor_product_type: multi_scene_film
- required_capability: text_to_video
- input_type: long_form_plan
- worker_owner: product_video
- scene_duration_seconds: 300
- maximum_scene_count: 20
- supported_quality_tiers: (300, 200, 1000, 400, 500, 600, 1200, 800, 1500, 700)
- execution_enabled: False
- execution_blocker: multi_scene_film_under_upgrade

Zero Client Authority Injection:
- Browser never chooses identity, job ID, status, provider, wallet, Xu, cost, charge plan,
  checkpoint, receipt, delivery or output URLs.
- Authenticated Web account is strictly the owner authority.

Artifact Truth:
- Never infer output availability from status alone.
- status == 'completed' without a verified safe HTTPS artifact fails closed:
  output_available=False, download_ready=False, delivery_ready=False, output=None.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import secrets
from typing import Any

from fastapi import HTTPException

from copyfast_db import read_transaction, transaction
from copyfast_video_long_job_bridge import is_safe_video_output_url


# ─── CANONICAL CONSTANTS ─────────────────────────────────────────────────────

CANONICAL_PRODUCT_KEY = "video_multiscene"
CANONICAL_ROUTING_KEY = "multi_scene_film"
CANONICAL_ROUTE_ID = "product_video_multiscene_v1"
CANONICAL_ENGINE_ADAPTER = "b13_r18c_product_multiscene_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/video/multiscene"
CANONICAL_EXECUTOR_PRODUCT_TYPE = "multi_scene_film"
CANONICAL_INPUT_TYPE = "long_form_plan"
CANONICAL_WORKER_OWNER = "product_video"
CANONICAL_FLOW_OWNER = "scene3"

STATUS_QUEUED = "queued"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
SUPPORTED_CANONICAL_JOB_ADAPTERS: frozenset[str] = frozenset({
    CANONICAL_PRODUCT_KEY,
    CANONICAL_ROUTING_KEY,
})

ALLOWED_QUALITY_TIERS: tuple[int, ...] = (
    200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500,
)
MIN_SCENE_COUNT = 1
MAX_SCENE_COUNT = 20
MAX_PROMPT_LENGTH = 2000

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    # Video Trend and common canonical financial/job authority fields
    "id", "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "providertaskid", "autoprovider",
    "apikey", "apitoken", "token", "secret", "jobid", "jobstatus", "status", "statusreason",
    "output", "outputurl", "downloadurl", "finalartifactpath", "outputsha256",
    "assetid", "role", "balance", "xu", "amountxu", "wallet", "authority",
    "accountid", "ownerid", "userid", "user_id", "account_id", "owner_id",
    "refund", "refundstatus", "refund_status", "bridgeenvelope", "outputmetadata",
    # Multi-scene runtime authority fields
    "chargeplan", "adminnocharge", "receipt", "delivery", "deliverymessageid",
    "checkpoint", "lease", "workerowner", "flowowner", "engineroute",
    "executorproducttype", "inputtype", "customerid", "xucharged", "workerid", "walletid",
    "createdat", "updatedat",
})
FORBIDDEN_CLIENT_AUTHORITY_KEYS: frozenset[str] = FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED


def _contains_authority_field(value: Any) -> bool:
    """Recursively find forged authority fields in incoming client input.

    Recursively walks dicts and lists/tuples.
    Normalizes keys (lower-case alphanumeric only) to block camelCase, snake_case,
    UPPERCASE, or delimiter-spaced authority aliases.
    """
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


# ─── ID & HASH GENERATORS ────────────────────────────────────────────────────

def generate_multi_scene_film_job_id() -> str:
    """Generate a collision-resistant canonical job identifier."""
    return f"msf_{secrets.token_hex(16)}"


def generate_canonical_request_id() -> str:
    """Generate a collision-resistant canonical request identifier."""
    return f"req_msfilm_{secrets.token_hex(12)}"


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
            "scenes": normalized_payload.get("scenes"),
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_key": CANONICAL_ROUTING_KEY,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable_repr.encode("utf-8")).hexdigest()


# ─── INPUT VALIDATOR ─────────────────────────────────────────────────────────

def validate_multi_scene_film_input(payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Validate client input payload for Multi-Scene Film (video_multiscene / multi_scene_film).

    Fail-closed security contract:
    - Rejects forged client authority fields recursively.
    - Requires prompt/brief/script text with 1 <= len <= MAX_PROMPT_LENGTH (2000).
    - Requires quality_tier in ALLOWED_QUALITY_TIERS (no silent defaults).
    - Requires scene_count in MIN_SCENE_COUNT..MAX_SCENE_COUNT (1..20, no silent defaults).
    - If scenes list is provided, enforces ordering semantics (scene_index consecutive 1..N)
      and max scene count 20.

    Returns:
        (is_valid, error_code, normalized_payload)
    """
    if not isinstance(payload, dict):
        return False, "invalid_payload_format", {}

    # 1. Recursive normalized client authority rejection
    if _contains_authority_field(payload):
        return False, "authority_field_not_allowed", {}

    # 2. Text / prompt extraction
    raw_prompt = (
        payload.get("brief")
        or payload.get("long_form_plan")
        or payload.get("prompt")
        or payload.get("script")
        or payload.get("text")
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

    # 4. Scene count validation (strict: no silent default)
    raw_scenes = payload.get("scenes")
    parsed_scenes: list[dict[str, Any]] | None = None
    if raw_scenes is not None:
        if not isinstance(raw_scenes, (list, tuple)):
            return False, "INVALID_SCENE_PLAN", {}
        if len(raw_scenes) < MIN_SCENE_COUNT or len(raw_scenes) > MAX_SCENE_COUNT:
            return False, "INVALID_SCENE_COUNT", {}
        parsed_scenes = []
        for expected_idx, item in enumerate(raw_scenes, start=1):
            if isinstance(item, dict):
                idx = item.get("scene_index")
                if idx is not None:
                    try:
                        parsed_idx = int(idx)
                    except (ValueError, TypeError):
                        return False, "multiscene_scene_order_invalid", {}
                    if parsed_idx != expected_idx:
                        return False, "multiscene_scene_order_invalid", {}
                scene_desc = str(item.get("description") or item.get("prompt") or item.get("scene_specification") or "").strip()
                parsed_scenes.append({
                    "scene_index": expected_idx,
                    "scene_specification": scene_desc[:MAX_PROMPT_LENGTH],
                })
            elif isinstance(item, str):
                parsed_scenes.append({
                    "scene_index": expected_idx,
                    "scene_specification": str(item).strip()[:MAX_PROMPT_LENGTH],
                })
            else:
                return False, "INVALID_SCENE_PLAN", {}

    raw_scene_count = payload.get("scene_count")
    if raw_scene_count is None or str(raw_scene_count).strip() == "":
        if parsed_scenes is not None:
            scene_count_val = len(parsed_scenes)
        else:
            return False, "SCENE_COUNT_REQUIRED", {}
    else:
        try:
            scene_count_val = int(raw_scene_count)
        except (ValueError, TypeError):
            return False, "INVALID_SCENE_COUNT", {}

    if scene_count_val < MIN_SCENE_COUNT or scene_count_val > MAX_SCENE_COUNT:
        return False, "INVALID_SCENE_COUNT", {}

    if parsed_scenes is not None and len(parsed_scenes) != scene_count_val:
        return False, "INVALID_SCENE_COUNT", {}

    normalized_payload = {
        "prompt": prompt,
        "quality_tier": tier_val,
        "scene_count": scene_count_val,
        "scenes": parsed_scenes,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_key": CANONICAL_ROUTING_KEY,
    }
    return True, "", normalized_payload


# ─── DURABLE STORAGE AND IDEMPOTENCY ─────────────────────────────────────────

def ensure_multi_scene_film_schema(conn: Any = None) -> None:
    """Ensure the web_multi_scene_film_jobs table and indexes exist."""
    def _create(c: Any) -> None:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS web_multi_scene_film_jobs (
                id TEXT PRIMARY KEY,
                canonical_job_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'video_multiscene',
                routing_product_key TEXT NOT NULL DEFAULT 'multi_scene_film',
                flow_owner TEXT NOT NULL DEFAULT 'scene3',
                worker_owner TEXT NOT NULL DEFAULT 'product_video',
                executor_product_type TEXT NOT NULL DEFAULT 'multi_scene_film',
                engine_route TEXT NOT NULL DEFAULT 'multi_scene_film',
                input_type TEXT NOT NULL DEFAULT 'long_form_plan',
                prompt TEXT NOT NULL,
                quality_tier INTEGER NOT NULL,
                scene_count INTEGER NOT NULL,
                cost_xu INTEGER NOT NULL DEFAULT 0,
                scenes_json TEXT,
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_multi_scene_film_jobs_account_created ON web_multi_scene_film_jobs(account_id, created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_multi_scene_film_jobs_request ON web_multi_scene_film_jobs(request_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_multi_scene_film_jobs_account_idempotency ON web_multi_scene_film_jobs(account_id, idempotency_key_hash)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_web_multi_scene_film_jobs_status_created ON web_multi_scene_film_jobs(status, created_at ASC)")

    if conn is not None:
        _create(conn)
    else:
        with transaction() as c:
            _create(c)


def create_or_replay_multi_scene_film_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Atomically create a new multi_scene_film job or replay an identical existing job.

    Enforces fail-closed serializable semantics:
    - Same account + same key + identical payload -> replay existing job record.
    - Same account + same key + differing payload -> HTTP 409 Conflict.
    - Initial status is queued with AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION.
    - Zero provider calls, zero video renders, zero wallet mutations.
    """
    clean_account_id = str(account_id or "").strip()
    if not clean_account_id:
        raise HTTPException(status_code=401, detail="account_id_required")

    is_valid, error_code, normalized_payload = validate_multi_scene_film_input(payload)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=error_code,
        )

    clean_key = str(idempotency_key or "").strip()
    key_hash = compute_idempotency_hash(clean_key) if clean_key else ""
    payload_hash = compute_payload_hash(normalized_payload)

    cost_xu = normalized_payload["quality_tier"] * normalized_payload["scene_count"]

    with transaction() as conn:
        ensure_multi_scene_film_schema(conn)
        # 1. Check idempotency replay within transaction
        if key_hash:
            cursor = conn.execute(
                "SELECT * FROM web_multi_scene_film_jobs WHERE account_id = ? AND idempotency_key_hash = ?",
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
                return _format_multi_scene_film_job_record(existing_job)

        # 2. Insert new canonical queued job
        job_id = generate_multi_scene_film_job_id()
        request_id = generate_canonical_request_id()
        now_ts = utc_now()

        bridge_envelope = {
            "route_id": CANONICAL_ROUTE_ID,
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "flow_owner": CANONICAL_FLOW_OWNER,
            "worker_owner": CANONICAL_WORKER_OWNER,
            "executor_product_type": CANONICAL_EXECUTOR_PRODUCT_TYPE,
            "engine_route": CANONICAL_ROUTING_KEY,
            "input_type": CANONICAL_INPUT_TYPE,
            "product_family": "product_video",
            "execution_enabled": False,
            "execution_blocker": "multi_scene_film_under_upgrade",
            "scene_duration_seconds": 300,
            "maximum_scene_count": MAX_SCENE_COUNT,
            "canonical_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
        }

        conn.execute(
            """
            INSERT INTO web_multi_scene_film_jobs (
                id, canonical_job_id, request_id, account_id,
                product_key, routing_product_key, flow_owner, worker_owner,
                executor_product_type, engine_route, input_type,
                prompt, quality_tier, scene_count, cost_xu, scenes_json,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope_json, output_url, output_metadata_json,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
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
                CANONICAL_FLOW_OWNER,
                CANONICAL_WORKER_OWNER,
                CANONICAL_EXECUTOR_PRODUCT_TYPE,
                CANONICAL_ROUTING_KEY,
                CANONICAL_INPUT_TYPE,
                normalized_payload["prompt"],
                normalized_payload["quality_tier"],
                normalized_payload["scene_count"],
                cost_xu,
                json.dumps(normalized_payload.get("scenes")) if normalized_payload.get("scenes") else None,
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
            "SELECT * FROM web_multi_scene_film_jobs WHERE id = ?",
            (job_id,),
        )
        row = cursor.fetchone()
        col_names = [col[0] for col in cursor.description]
        return _format_multi_scene_film_job_record(dict(zip(col_names, row)))


def get_multi_scene_film_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    """Retrieve an owner-scoped multi_scene_film job by canonical job ID."""
    clean_account_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not clean_account_id or not clean_job_id:
        return None

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM web_multi_scene_film_jobs WHERE id = ? AND account_id = ?",
            (clean_job_id, clean_account_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        col_names = [col[0] for col in cursor.description]
        return _format_multi_scene_film_job_record(dict(zip(col_names, row)))


def list_multi_scene_film_jobs(account_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """List owner-scoped multi_scene_film jobs ordered newest first."""
    clean_account_id = str(account_id or "").strip()
    if not clean_account_id:
        return []

    safe_limit = max(1, min(limit, 100))
    with read_transaction() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM web_multi_scene_film_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (clean_account_id, safe_limit),
        )
        rows = cursor.fetchall()
        col_names = [col[0] for col in cursor.description]
        return [_format_multi_scene_film_job_record(dict(zip(col_names, r))) for r in rows]


def is_multi_scene_film_job_other_account(job_id: str, requester_account_id: str) -> bool:
    """Return True if job exists but belongs to a different owner."""
    clean_job_id = str(job_id or "").strip()
    clean_requester = str(requester_account_id or "").strip()
    if not clean_job_id or not clean_requester:
        return False

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT account_id FROM web_multi_scene_film_jobs WHERE id = ?",
            (clean_job_id,),
        )
        row = cursor.fetchone()
        if not row:
            return False
        owner_id = str(row[0] or "").strip()
        return owner_id != clean_requester


# ─── NATIVE WEB COMPATIBILITY PROJECTION ─────────────────────────────────────

def multi_scene_film_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Map multi_scene_film job to standard Web job contract.

    Enforces fail-closed output truth:
    - Never project output availability from status == 'completed' alone.
    - Requires verified safe HTTPS output_url.
    """
    output_url = job.get("output_url")
    is_safe = is_safe_video_output_url(output_url)

    output_available = bool(is_safe and job.get("status") == "completed")
    clean_output = output_url if output_available else None

    return {
        "id": job.get("id"),
        "job_id": job.get("id"),
        "canonical_job_id": job.get("canonical_job_id"),
        "kind": "video_multiscene",
        "job_type": "video_multiscene",
        "product_type": "multi_scene_film",
        "feature": "video_multiscene",
        "service_context": "video_multiscene",
        "canonical_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
        "status": job.get("status"),
        "status_reason": job.get("status_reason"),
        "flow_owner": CANONICAL_FLOW_OWNER,
        "worker_owner": CANONICAL_WORKER_OWNER,
        "quality_tier": job.get("quality_tier"),
        "scene_count": job.get("scene_count"),
        "cost_xu": job.get("cost_xu"),
        "scenes": job.get("scenes"),
        "output_available": output_available,
        "download_ready": output_available,
        "delivery_ready": output_available,
        "output": clean_output,
        "output_url": clean_output,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


def _format_multi_scene_film_job_record(row: dict[str, Any]) -> dict[str, Any]:
    """Format raw database row into clean owner-scoped API dictionary."""
    output_url = row.get("output_url")
    is_safe_artifact = is_safe_video_output_url(output_url)
    output_available = bool(is_safe_artifact and row.get("status") == "completed")

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

    scenes: list[dict[str, Any]] | None = None
    if row.get("scenes_json"):
        try:
            scenes = json.loads(row["scenes_json"])
        except Exception:
            scenes = None

    clean_output = output_url if output_available else None

    return {
        "id": row.get("id"),
        "canonical_job_id": row.get("canonical_job_id"),
        "request_id": row.get("request_id"),
        "account_id": row.get("account_id"),
        "product_key": row.get("product_key"),
        "routing_product_key": row.get("routing_product_key"),
        "flow_owner": row.get("flow_owner"),
        "worker_owner": row.get("worker_owner"),
        "executor_product_type": row.get("executor_product_type"),
        "engine_route": row.get("engine_route"),
        "input_type": row.get("input_type"),
        "prompt": row.get("prompt"),
        "quality_tier": row.get("quality_tier"),
        "scene_count": row.get("scene_count"),
        "cost_xu": row.get("cost_xu"),
        "scenes": scenes,
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
