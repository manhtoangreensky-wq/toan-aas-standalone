"""Voice Clone Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.VOICE_CLONE.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Master Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Connects the Web customer flow (/voice/clone) for `voice_clone`
to a canonical Bot-compatible job bridge contract without executing real voice
clones, provider file uploads, paid provider calls, or wallet balance mutations.

Runtime Authority Reference:
- bot.get_minimax_voice_clone_readiness
- services.minimax_voice_adapter
- services.voice_clone_pipeline
- bot_capability: voice_clone
- web_feature_key: voice_clone
- web_customer_entrypoint: /voice/clone
- web_api_family: /api/v1/features/voice_clone/*
- bot_authority_repo: manhtoangreensky-wq/bot
- bot_authority_sha: a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932

Invariants:
- Fail-Closed Admission: zero provider calls until Owner-authorized runtime execution.
- Truthful Status: initial status is 'queued', status_reason is
  'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'. Zero fake output, zero fake completion.
- Output Fail-Closed: output_available=False, download_ready=False, delivery_ready=False,
  preview_ready=False, tts_ready=False, output=None.
- Staged Upload & Owner Binding: references signed-owner staged upload. Rejects cross-account
  sample reference, zero-byte samples, oversized (>20MB) samples, unsupported extensions.
- Supported Sample Extensions: .mp3, .m4a, .wav derived strictly from Bot authority.
- Exactly One Sample: requires exactly one staged upload.
- Explicit Customer Consent: mandatory affirmed boolean; missing/false consent fails closed.
- Display Name: optional customer label, max 120 chars, zero invented defaults.
- Server-Only Provider Voice ID: provider_voice_id / provider_file_id never accepted from browser.
- Idempotency & Conflict: replay existing job on identical payload hash, reject with 409
  on same account/idempotency_key with differing payload.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
from typing import Any
import uuid

from fastapi import HTTPException

from copyfast_db import read_transaction, transaction, utc_now


# ─── CANONICAL CONSTANTS ─────────────────────────────────────────────────────

CANONICAL_PRODUCT_KEY = "voice_clone"
CANONICAL_ROUTING_KEY = "voice_clone"
CANONICAL_CUSTOMER_ENTRYPOINT = "/voice/clone"
CANONICAL_API_FAMILY = "/api/v1/features/voice_clone/*"
CANONICAL_BOT_CAPABILITY = "voice_clone"
CANONICAL_CATEGORY = "voice_ai"
CANONICAL_BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
CANONICAL_BOT_AUTHORITY_SHA = "a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932"
CANONICAL_RUNTIME_REFERENCE = "bot.get_minimax_voice_clone_readiness"

STATUS_QUEUED = "queued"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

VOICE_CLONE_SAMPLE_COUNT_MIN = 1
VOICE_CLONE_SAMPLE_COUNT_MAX = 1

VOICE_CLONE_SAMPLE_EXTENSIONS: frozenset[str] = frozenset({".mp3", ".m4a", ".wav"})
CUSTOM_VOICE_MAX_SAMPLE_BYTES: int = 20 * 1024 * 1024  # 20 MB
CUSTOM_VOICE_MIN_DETECTABLE_SECONDS: float = 10.0

MAX_DISPLAY_NAME_LENGTH: int = 120

CANONICAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")

ALLOWED_INPUT_FIELDS: frozenset[str] = frozenset({
    "upload_ids",
    "sample",
    "upload_id",
    "consent",
    "display_name",
})

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "id", "requestid", "idempotencykey", "accountid", "ownerid", "userid",
    "jobid", "status", "statusreason",
    "provider", "providerid", "providername",
    "providertaskid", "providerfileid", "providervoiceid",
    "voiceid", "customvoiceid", "profileid", "voiceprofileid", "activationstatus",
    "samplepath", "filepath", "localpath", "outputpath",
    "audiourl", "sampleurl", "previewurl", "previewaudioref",
    "url", "remoteurl",
    "wallet", "xu", "price", "cost", "unitxu", "costxu", "pricexu", "amount", "currency",
    "payment", "paymentid", "refund", "refundstatus",
    "ordercode", "checkouturl", "webhook", "apikey", "apitoken", "token", "secret",
    "model", "cloneendpoint",
    "role", "balance", "authority", "bridgeenvelope", "outputmetadata",
    "consentstatus", "consentat", "approvalstatus", "verifiedconsent", "providerconsent",
})


def _contains_authority_field(value: Any) -> bool:
    """Recursively search for client-forged authority or provider fields."""
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


def _affirmed(value: Any) -> bool:
    """Return whether a value represents affirmative user consent."""
    return value is True or (isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "on"})


# ─── SCHEMA & STORAGE ────────────────────────────────────────────────────────

def ensure_voice_clone_schema() -> None:
    """Initialize dedicated web_staged_uploads and web_voice_clone_jobs tables and indexes."""
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_staged_uploads (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                extension TEXT NOT NULL,
                content_type TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                staging_state TEXT NOT NULL DEFAULT 'staged' CHECK(staging_state IN ('staged', 'consumed', 'expired')),
                storage_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_staged_uploads_account ON web_staged_uploads(account_id, created_at DESC)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_voice_clone_jobs (
                id TEXT PRIMARY KEY,
                canonical_job_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'voice_clone',
                routing_product_key TEXT NOT NULL DEFAULT 'voice_clone',
                source_upload_id TEXT NOT NULL,
                consent_affirmed INTEGER NOT NULL DEFAULT 1,
                display_name TEXT,
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_clone_jobs_account_created ON web_voice_clone_jobs(account_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_clone_jobs_request ON web_voice_clone_jobs(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_clone_jobs_account_idempotency ON web_voice_clone_jobs(account_id, idempotency_key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_clone_jobs_status_created ON web_voice_clone_jobs(status, created_at ASC)")


def stage_upload_for_account(
    *,
    account_id: str,
    filename: str,
    content_type: str,
    byte_size: int,
    sha256: str,
    extension: str = "",
    storage_path: str = "",
    upload_id: str = "",
) -> dict[str, Any]:
    """Record an owner-bound upload into canonical staging without copying raw bytes."""
    ensure_voice_clone_schema()
    clean_account = str(account_id or "").strip()
    if not clean_account:
        raise HTTPException(status_code=401, detail="Xác thực tài khoản Web là bắt buộc")
    clean_id = str(upload_id or "").strip() or f"stg_{uuid.uuid4().hex}"
    ext = str(extension or Path(filename).suffix or "").lower()
    now_ts = utc_now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_staged_uploads (
                id, account_id, filename, extension, content_type,
                byte_size, sha256, staging_state, storage_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'staged', ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                account_id=excluded.account_id,
                filename=excluded.filename,
                extension=excluded.extension,
                content_type=excluded.content_type,
                byte_size=excluded.byte_size,
                sha256=excluded.sha256,
                staging_state='staged',
                storage_path=excluded.storage_path,
                updated_at=excluded.updated_at
            """,
            (
                clean_id, clean_account, filename, ext, content_type,
                int(byte_size), sha256, storage_path, now_ts, now_ts
            ),
        )
    return {
        "id": clean_id,
        "account_id": clean_account,
        "filename": filename,
        "extension": ext,
        "content_type": content_type,
        "byte_size": int(byte_size),
        "sha256": sha256,
        "staging_state": "staged",
        "created_at": now_ts,
        "updated_at": now_ts,
    }


def get_staged_upload(upload_id: str) -> dict[str, Any] | None:
    """Retrieve a staged upload record by its opaque identifier."""
    clean_id = str(upload_id or "").strip()
    if not clean_id:
        return None
    ensure_voice_clone_schema()
    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM web_staged_uploads WHERE id = ?",
            (clean_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        col_names = [col[0] for col in cursor.description]
        return dict(zip(col_names, row))


def validate_source_upload_for_clone(upload_id: str, account_id: str) -> tuple[bool, str, dict[str, Any]]:
    """Prove that candidate upload belongs to current account and satisfies format constraints.

    Returns:
        (is_valid, error_code, upload_record)
    """
    clean_upload_id = str(upload_id or "").strip()
    clean_account_id = str(account_id or "").strip()
    if not clean_upload_id or not clean_account_id:
        return False, "upload_not_found", {}

    ensure_voice_clone_schema()
    upload = get_staged_upload(clean_upload_id)
    if not upload:
        return False, "upload_not_found", {}

    # Owner binding: cross-account staging use strictly rejected
    if upload.get("account_id") != clean_account_id:
        return False, "cross_account_upload_forbidden", {}

    # Staging state check
    if upload.get("staging_state") != "staged":
        return False, "upload_state_invalid", {}

    # Byte size check: zero-byte rejection
    byte_size = int(upload.get("byte_size") or 0)
    if byte_size <= 0:
        return False, "zero_byte_sample", {}

    # Byte size check: oversized rejection (20 MB limit)
    if byte_size > CUSTOM_VOICE_MAX_SAMPLE_BYTES:
        return False, "sample_too_large", {}

    # Extension check: must be in .mp3, .m4a, .wav
    ext = str(upload.get("extension") or "").lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext not in VOICE_CLONE_SAMPLE_EXTENSIONS:
        return False, "unsupported_audio_extension", {}

    return True, "", upload


# ─── INPUT VALIDATION & IDEMPOTENCY ──────────────────────────────────────────

def validate_voice_clone_input(payload: dict[str, Any], account_id: str) -> tuple[bool, str, dict[str, Any]]:
    """Validate incoming business input for voice_clone durable job admission.

    Returns:
        (is_valid, error_code, normalized_values)
    """
    clean_account = str(account_id or "").strip()
    if not clean_account:
        return False, "account_required", {}

    if _contains_authority_field(payload):
        return False, "authority_field_not_allowed", {}

    # Reject unproven/unknown fields fail-closed
    for key in payload:
        if key not in ALLOWED_INPUT_FIELDS:
            return False, "unknown_input_field", {}

    # 1. upload_ids: exactly one required
    raw_uploads = payload.get("upload_ids")
    if raw_uploads is None:
        if "sample" in payload:
            sample_val = payload.get("sample")
            raw_uploads = [sample_val] if isinstance(sample_val, str) else sample_val
        elif "upload_id" in payload:
            upload_val = payload.get("upload_id")
            raw_uploads = [upload_val] if isinstance(upload_val, str) else upload_val

    if raw_uploads is None:
        return False, "upload_required", {}
    if not isinstance(raw_uploads, list) or len(raw_uploads) == 0:
        return False, "upload_required", {}
    if len(raw_uploads) > VOICE_CLONE_SAMPLE_COUNT_MAX:
        return False, "multiple_samples_not_supported", {}

    upload_id = str(raw_uploads[0] or "").strip()
    if not upload_id or not CANONICAL_IDENTIFIER_PATTERN.fullmatch(upload_id):
        return False, "upload_identifier_invalid", {}

    # Validate source upload ownership, existence, size, and extension
    is_upload_valid, upload_err, upload_record = validate_source_upload_for_clone(upload_id, clean_account)
    if not is_upload_valid:
        return False, upload_err, {}

    # 2. consent: mandatory explicit affirmation
    raw_consent = payload.get("consent")
    if not _affirmed(raw_consent):
        return False, "voice_clone_consent_required", {}

    # 3. display_name: optional, max 120 chars, no invented defaults
    raw_display_name = payload.get("display_name")
    display_name = ""
    if raw_display_name is not None:
        if not isinstance(raw_display_name, str):
            return False, "invalid_display_name", {}
        cleaned_name = raw_display_name.strip()
        if len(cleaned_name) > MAX_DISPLAY_NAME_LENGTH:
            return False, "display_name_too_long", {}
        display_name = cleaned_name

    normalized = {
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
        "source_upload_id": upload_id,
        "consent_affirmed": True,
        "display_name": display_name,
    }
    return True, "", normalized


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 digest of normalized payload for idempotency & conflict detection."""
    core = {
        "product_key": str(payload.get("product_key") or CANONICAL_PRODUCT_KEY),
        "routing_product_key": str(payload.get("routing_product_key") or CANONICAL_ROUTING_KEY),
        "source_upload_id": str(payload.get("source_upload_id") or "").strip(),
        "consent_affirmed": bool(payload.get("consent_affirmed")),
        "display_name": str(payload.get("display_name") or "").strip(),
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
    random_part = secrets.token_hex(3).upper()
    return f"VCL-{date_part}-{random_part}"


def generate_voice_clone_job_id() -> str:
    return f"vcj_{uuid.uuid4().hex}"


# ─── ADAPTER LIFECYCLE ───────────────────────────────────────────────────────

def create_or_replay_voice_clone_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new canonical Voice Clone job or replay existing one idempotently.

    Raises:
        HTTPException(401) on missing account
        HTTPException(403) on cross-account sample reference
        HTTPException(409) on idempotency conflict with differing payload
        HTTPException(422) on input validation error
    """
    ensure_voice_clone_schema()
    clean_account = str(account_id or "").strip()
    if not clean_account:
        raise HTTPException(status_code=401, detail="account_id_required")

    is_valid, error_code, normalized = validate_voice_clone_input(payload, clean_account)
    if not is_valid:
        if error_code == "cross_account_upload_forbidden":
            raise HTTPException(status_code=403, detail=error_code)
        raise HTTPException(status_code=422, detail=error_code)

    payload_hash = compute_payload_hash(normalized)
    idempotency_key_clean = str(idempotency_key or "").strip()
    idempotency_key_hash = compute_idempotency_hash(idempotency_key_clean) if idempotency_key_clean else None

    with transaction() as conn:
        if idempotency_key_hash:
            cursor = conn.execute(
                """
                SELECT * FROM web_voice_clone_jobs
                WHERE account_id = ? AND idempotency_key_hash = ?
                """,
                (clean_account, idempotency_key_hash),
            )
            row = cursor.fetchone()
            if row:
                col_names = [col[0] for col in cursor.description]
                existing = dict(zip(col_names, row))
                if existing["payload_hash"] == payload_hash:
                    return _format_voice_clone_job_record(existing)
                raise HTTPException(
                    status_code=409,
                    detail="IDEMPOTENCY_CONFLICT",
                )

        job_id = generate_voice_clone_job_id()
        canonical_job_id = job_id
        req_id = str(request_id or "").strip() or generate_canonical_request_id()
        now_ts = utc_now()
        envelope = {
            "route": CANONICAL_CUSTOMER_ENTRYPOINT,
            "created_at": now_ts,
            "version": "v1",
            "source_upload_id": normalized["source_upload_id"],
            "consent_affirmed": True,
            "display_name": normalized["display_name"],
            "sample_duration_validation_pending": True,
        }

        conn.execute(
            """
            INSERT INTO web_voice_clone_jobs (
                id, canonical_job_id, request_id, account_id,
                product_key, routing_product_key, source_upload_id,
                consent_affirmed, display_name, status, status_reason,
                idempotency_key_hash, payload_hash, bridge_envelope_json,
                output_url, output_metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (
                job_id,
                canonical_job_id,
                req_id,
                clean_account,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                normalized["source_upload_id"],
                1,
                normalized["display_name"],
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                idempotency_key_hash,
                payload_hash,
                json.dumps(envelope),
                now_ts,
                now_ts,
            ),
        )

        cursor = conn.execute(
            "SELECT * FROM web_voice_clone_jobs WHERE id = ?",
            (job_id,),
        )
        row = cursor.fetchone()
        col_names = [col[0] for col in cursor.description]
        return _format_voice_clone_job_record(dict(zip(col_names, row)))


def get_voice_clone_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    """Retrieve an owner-scoped voice_clone job by canonical job ID."""
    clean_account_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not clean_account_id or not clean_job_id:
        return None

    ensure_voice_clone_schema()
    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM web_voice_clone_jobs WHERE id = ? AND account_id = ?",
            (clean_job_id, clean_account_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        col_names = [col[0] for col in cursor.description]
        return _format_voice_clone_job_record(dict(zip(col_names, row)))


def list_voice_clone_jobs(account_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """List owner-scoped voice_clone jobs ordered newest first."""
    clean_account_id = str(account_id or "").strip()
    if not clean_account_id:
        return []

    ensure_voice_clone_schema()
    safe_limit = max(1, min(limit, 100))
    with read_transaction() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM web_voice_clone_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (clean_account_id, safe_limit),
        )
        rows = cursor.fetchall()
        col_names = [col[0] for col in cursor.description]
        return [_format_voice_clone_job_record(dict(zip(col_names, r))) for r in rows]


def is_voice_clone_job_other_account(job_id: str, requester_account_id: str) -> bool:
    """Return True if job exists but belongs to a different owner."""
    clean_job_id = str(job_id or "").strip()
    clean_requester = str(requester_account_id or "").strip()
    if not clean_job_id or not clean_requester:
        return False

    ensure_voice_clone_schema()
    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT account_id FROM web_voice_clone_jobs WHERE id = ?",
            (clean_job_id,),
        )
        row = cursor.fetchone()
        if not row:
            return False
        owner_id = str(row[0] or "").strip()
        return owner_id != clean_requester


# ─── COMPATIBILITY PROJECTION ────────────────────────────────────────────────

def voice_clone_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Map voice_clone job to standard Web job contract.

    Enforces fail-closed output truth:
    - Never project cloned voice or output availability from status alone.
    """
    return {
        "id": job.get("id"),
        "job_id": job.get("id"),
        "canonical_job_id": job.get("canonical_job_id"),
        "kind": "voice",
        "job_type": "voice",
        "product_type": "voice_clone",
        "feature": "voice_clone",
        "service_context": "voice_clone",
        "canonical_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
        "status": job.get("status"),
        "status_reason": job.get("status_reason"),
        "display_name": job.get("display_name") or "",
        "source_upload_id": job.get("source_upload_id"),
        "consent_affirmed": bool(job.get("consent_affirmed")),
        "output_available": False,
        "download_ready": False,
        "delivery_ready": False,
        "preview_ready": False,
        "tts_ready": False,
        "output": None,
        "output_url": None,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


def _format_voice_clone_job_record(row: dict[str, Any]) -> dict[str, Any]:
    """Format raw database row into clean owner-scoped API dictionary."""
    envelope: dict[str, Any] = {}
    if row.get("bridge_envelope_json"):
        try:
            envelope = json.loads(row["bridge_envelope_json"])
        except Exception:
            envelope = {}

    return {
        "id": row.get("id"),
        "canonical_job_id": row.get("canonical_job_id"),
        "request_id": row.get("request_id"),
        "account_id": row.get("account_id"),
        "product_key": row.get("product_key"),
        "routing_product_key": row.get("routing_product_key"),
        "source_upload_id": row.get("source_upload_id"),
        "consent_affirmed": bool(row.get("consent_affirmed")),
        "display_name": row.get("display_name") or "",
        "status": row.get("status"),
        "status_reason": row.get("status_reason"),
        "output": None,
        "output_url": None,
        "output_available": False,
        "download_ready": False,
        "delivery_ready": False,
        "preview_ready": False,
        "tts_ready": False,
        "output_metadata": None,
        "bridge_envelope": envelope,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
