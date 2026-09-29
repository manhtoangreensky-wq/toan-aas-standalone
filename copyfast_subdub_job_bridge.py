"""SubDub Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.SUBDUB.CANONICAL.DURABLE.JOB_BRIDGE.R1 (WEB_R2)
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Parent Task: P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1

Connects the Web customer flow (/subdub) for SubDub operations
(subtitle_create, subtitle_translate, dub, subtitle_plus_dub) to a canonical
Bot-compatible durable job bridge contract without executing paid provider
calls, unauthorized runtime renders, or wallet balance mutations.

Invariants:
- Fail-Closed Admission: zero provider calls until Owner-authorized runtime execution.
- Truthful Status: initial status is 'queued', status_reason is
  'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'. Zero fake output, zero fake completion.
- Upload ID Authority: must match CANONICAL_IDENTIFIER_PATTERN, strictly reject local
  filesystem paths and unverified remote URLs.
- Four Canonical Lanes: subtitle_create, subtitle_translate, dub, subtitle_plus_dub.
- Output Format Reconciliation: dubbing overrides client-side srt-only restriction to
  canonical media output ("video" / "audio" / "video_subtitle").
- Idempotency & Conflict: replay existing job on identical payload hash, reject with 409
  on same request_id/idempotency_key with differing payload.
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

CANONICAL_PRODUCT_KEY = "subdub"
CANONICAL_ROUTING_KEY = "subdub_canonical"
CANONICAL_ROUTE_ID = "subdub_canonical_v1"
CANONICAL_ENGINE_ADAPTER = "b13_r18c_subdub_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/subdub"

SUPPORTED_CANONICAL_JOB_ADAPTERS = frozenset({
    "subdub",
    "video_dub",
    "subtitle_create",
    "subtitle_translate",
    "subtitle_plus_dub",
    "dubbing",
    "subtitle_plus_dubbing",
    "subtitle_asr",
    "asr",
})

CANONICAL_SUBDUB_MODES = frozenset({
    "subtitle_create",
    "subtitle_translate",
    "dub",
    "subtitle_plus_dub",
})

STATUS_QUEUED = "queued"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED = frozenset({
    "id", "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "providertaskid", "apikey", "apitoken", "token",
    "secret", "jobid", "jobstatus", "status", "statusreason", "output", "outputurl",
    "assetid", "downloadurl", "role", "balance", "xu", "wallet", "walletid", "authority",
    "accountid", "ownerid", "userid", "user_id", "account_id", "owner_id", "refund", "refund_status",
    "bridgeenvelope", "outputmetadata", "providervoiceid", "providervoice", "voiceid",
    "chargedxu", "estimatedxu", "providerspendxu", "fakeoutputurl",
})

CANONICAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
SAFE_HOSTNAME_PATTERN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
FORBIDDEN_OUTPUT_URL_SCHEMES = frozenset({"javascript:", "vbscript:", "data:", "file:", "blob:", "about:"})


def is_safe_subdub_output_url(url: Any) -> bool:
    """Validate that a candidate SubDub output URL is safe to deliver."""
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


def normalize_subdub_mode(mode: str) -> str:
    """Map legacy and user-facing mode names to canonical 4 lanes."""
    clean = str(mode or "").strip().lower()
    mapping = {
        "subtitle_create": "subtitle_create",
        "subtitle_asr": "subtitle_create",
        "asr": "subtitle_create",
        "subtitle_translate": "subtitle_translate",
        "translate": "subtitle_translate",
        "dub": "dub",
        "dubbing": "dub",
        "video_dub": "dub",
        "subtitle_plus_dub": "subtitle_plus_dub",
        "subtitle_plus_dubbing": "subtitle_plus_dub",
        "combo": "subtitle_plus_dub",
    }
    return mapping.get(clean, "")


def validate_subdub_input(values: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Validate input payload for SubDub job bridge.

    Returns:
        (is_valid, error_code, normalized_values)
    """
    if _contains_authority_field(values):
        return False, "authority_field_not_allowed", {}

    # 1. Validate upload_id (required, canonical opaque identifier)
    raw_upload = (
        values.get("upload_id")
        or values.get("source")
        or values.get("file_id")
        or values.get("staged_upload_id")
    )
    if raw_upload is None:
        return False, "UPLOAD_ID_REQUIRED", {}
    upload_id = str(raw_upload).strip()
    if not upload_id:
        return False, "UPLOAD_ID_REQUIRED", {}

    # Reject local file paths and remote URLs as upload authority
    if (
        "/" in upload_id
        or "\\" in upload_id
        or upload_id.startswith(".")
        or ".." in upload_id
        or upload_id.lower().startswith("http:")
        or upload_id.lower().startswith("https:")
        or upload_id.lower().startswith("file:")
    ):
        return False, "INVALID_UPLOAD_ID", {}

    if not CANONICAL_IDENTIFIER_PATTERN.fullmatch(upload_id):
        return False, "INVALID_UPLOAD_ID", {}

    # 2. Validate and normalize mode
    raw_mode = values.get("mode") or values.get("subdub_mode") or "subtitle_create"
    canonical_mode = normalize_subdub_mode(raw_mode)
    if not canonical_mode:
        return False, "INVALID_SUBDUB_MODE", {}

    # 3. Target language validation
    target_lang = str(values.get("target_language") or "").strip().lower()
    if canonical_mode in ("subtitle_translate", "dub", "subtitle_plus_dub"):
        if not target_lang:
            return False, "TARGET_LANGUAGE_REQUIRED", {}
        if not re.fullmatch(r"^[a-z]{2,5}(?:-[a-z0-9]{2,5})?$", target_lang):
            return False, "INVALID_TARGET_LANGUAGE", {}

    # 4. Source language
    source_lang = str(values.get("source_language") or "auto").strip().lower() or "auto"

    # 5. Voice profile (for dubbing lanes)
    voice_profile_id = str(values.get("voice_profile_id") or "").strip()[:80]

    # 6. Speed multiplier (0.7 to 1.8)
    speed_raw = values.get("speed", 1.0)
    try:
        speed = float(speed_raw)
        if speed < 0.5 or speed > 2.0:
            speed = 1.0
    except (TypeError, ValueError):
        speed = 1.0

    # 7. Output format reconciliation (override client srt-only on dubbing; burn on video subtitle)
    is_video = str(values.get("source_media_type") or "").strip().lower() == "video" or bool(values.get("is_video_source"))
    if canonical_mode == "dub":
        output_format = "audio" if str(values.get("source_media_type") or "").lower() == "audio" else "video"
    elif canonical_mode == "subtitle_plus_dub":
        output_format = "audio" if str(values.get("source_media_type") or "").lower() == "audio" else "video_subtitle"
    else:
        req_fmt = str(values.get("output_format") or "srt").strip().lower()
        if req_fmt in ("burn", "both"):
            output_format = "burn"
        elif req_fmt in ("srt", "vtt"):
            output_format = "burn" if is_video else req_fmt
        else:
            output_format = "burn" if is_video else "srt"

    normalized = {
        "upload_id": upload_id,
        "subdub_mode": canonical_mode,
        "mode": canonical_mode,
        "source_language": source_lang,
        "target_language": target_lang,
        "voice_profile_id": voice_profile_id,
        "output_format": output_format,
        "speed": speed,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
    }
    return True, "", normalized


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 digest of normalized payload for idempotency & conflict detection."""
    core = {
        "upload_id": str(payload.get("upload_id") or "").strip(),
        "subdub_mode": str(payload.get("subdub_mode") or "").strip(),
        "source_language": str(payload.get("source_language") or "auto").strip(),
        "target_language": str(payload.get("target_language") or "").strip(),
        "voice_profile_id": str(payload.get("voice_profile_id") or "").strip(),
        "output_format": str(payload.get("output_format") or "srt").strip(),
        "speed": round(float(payload.get("speed") or 1.0), 2),
        "product_key": str(payload.get("product_key") or CANONICAL_PRODUCT_KEY),
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
    return f"SDB-{date_part}-{random_part}"


def generate_subdub_job_id() -> str:
    return f"sdj_{uuid.uuid4().hex}"


def ensure_subdub_schema() -> None:
    """Initialize dedicated web_subdub_jobs SQLite table and indexes."""
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_subdub_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'subdub',
                subdub_mode TEXT NOT NULL DEFAULT 'subtitle_create',
                upload_id TEXT NOT NULL,
                source_language TEXT DEFAULT 'auto',
                target_language TEXT DEFAULT '',
                voice_profile_id TEXT DEFAULT '',
                output_format TEXT NOT NULL DEFAULT 'srt',
                speed REAL DEFAULT 1.0,
                status TEXT NOT NULL DEFAULT 'queued',
                status_reason TEXT NOT NULL DEFAULT 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope TEXT NOT NULL,
                output_metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                output_url TEXT,
                worker_id TEXT,
                claimed_at TEXT,
                lease_expires_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_account_created ON web_subdub_jobs(account_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_request ON web_subdub_jobs(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_account_idempotency ON web_subdub_jobs(account_id, idempotency_key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_status_created ON web_subdub_jobs(status, created_at ASC)")


def create_or_replay_subdub_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new canonical SubDub job or replay existing one idempotently.

    Raises:
        HTTPException(400) on validation error
        HTTPException(401) on missing account
        HTTPException(409) on request_id/idempotency conflict with differing payload
    """
    ensure_subdub_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Xác thực tài khoản Web là bắt buộc")

    is_valid, error_code, normalized = validate_subdub_input(payload)
    if not is_valid:
        error_messages = {
            "authority_field_not_allowed": "Yêu cầu chứa trường authority bị cấm.",
            "UPLOAD_ID_REQUIRED": "Tệp phương tiện nguồn (upload_id) là bắt buộc.",
            "INVALID_UPLOAD_ID": "Mã tệp phương tiện upload_id không hợp lệ hoặc từ chối đường dẫn cục bộ/URL ngoài.",
            "INVALID_SUBDUB_MODE": "Chế độ SubDub không hợp lệ (subtitle_create, subtitle_translate, dub, subtitle_plus_dub).",
            "TARGET_LANGUAGE_REQUIRED": "Ngôn ngữ đích là bắt buộc đối với dịch phụ đề hoặc lồng tiếng.",
            "INVALID_TARGET_LANGUAGE": "Mã ngôn ngữ đích không hợp lệ.",
        }
        raise HTTPException(status_code=400, detail=error_messages.get(error_code, error_code))

    payload_hash = compute_payload_hash(normalized)
    effective_req_id = str(request_id or payload.get("request_id") or "").strip()
    effective_idem_key = str(idempotency_key or payload.get("idempotency_key") or "").strip()
    idem_hash = compute_idempotency_hash(effective_idem_key) if effective_idem_key else ""

    with transaction() as conn:
        query = """
            SELECT id, request_id, account_id, product_key, subdub_mode,
                   upload_id, source_language, target_language, voice_profile_id,
                   output_format, speed, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_subdub_jobs
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
            existing_payload_hash = str(row[14])
            if not hmac.compare_digest(existing_payload_hash, payload_hash):
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột mã yêu cầu: request_id hoặc idempotency_key đã gắn với payload khác.",
                )
            return _format_public_job(row, idempotent_replay=True)

        job_id = generate_subdub_job_id()
        final_req_id = effective_req_id or generate_canonical_request_id()
        now = utc_now()

        bridge_envelope = {
            "version": "p0.subdub.canonical-bridge.v1",
            "route_id": CANONICAL_ROUTE_ID,
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "product_family": "subdub",
            "flow_owner": "subdub",
            "engine_route": CANONICAL_ROUTING_KEY,
            "executor_product_type": CANONICAL_PRODUCT_KEY,
            "subdub_mode": normalized["subdub_mode"],
            "upload_id": normalized["upload_id"],
            "source_language": normalized["source_language"],
            "target_language": normalized["target_language"],
            "voice_profile_id": normalized["voice_profile_id"],
            "output_format": normalized["output_format"],
            "speed": normalized["speed"],
            "request_id": final_req_id,
            "job_id": job_id,
            "account_id": owner_id,
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_AWAITING,
            "created_at": now,
            "output": None,
            "output_url": None,
        }
        envelope_json = json.dumps(bridge_envelope, ensure_ascii=True, sort_keys=True)

        conn.execute(
            """
            INSERT INTO web_subdub_jobs (
                id, request_id, account_id, product_key, subdub_mode,
                upload_id, source_language, target_language, voice_profile_id,
                output_format, speed, status, status_reason,
                idempotency_key_hash, payload_hash, bridge_envelope,
                output_metadata, created_at, updated_at, output_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL)
            """,
            (
                job_id,
                final_req_id,
                owner_id,
                CANONICAL_PRODUCT_KEY,
                normalized["subdub_mode"],
                normalized["upload_id"],
                normalized["source_language"],
                normalized["target_language"],
                normalized["voice_profile_id"],
                normalized["output_format"],
                normalized["speed"],
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
            "subdub_mode": normalized["subdub_mode"],
            "mode": normalized["subdub_mode"],
            "upload_id": normalized["upload_id"],
            "source_language": normalized["source_language"],
            "target_language": normalized["target_language"],
            "voice_profile_id": normalized["voice_profile_id"],
            "output_format": normalized["output_format"],
            "speed": normalized["speed"],
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


def _is_runtime_execution_active(feature: str = "subdub") -> bool:
    try:
        import sys
        copyfast_api = sys.modules.get("copyfast_api")
        if copyfast_api is None:
            import copyfast_api
        return feature in getattr(copyfast_api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset())
    except Exception:
        return False


def _format_public_job(row: tuple, *, idempotent_replay: bool = False) -> dict[str, Any]:
    try:
        env = json.loads(str(row[15])) if len(row) > 15 and row[15] else {}
    except Exception:
        env = {}
    try:
        output_meta = json.loads(str(row[16])) if len(row) > 16 and row[16] else None
    except Exception:
        output_meta = None

    status_str = str(row[11])
    is_completed = status_str == STATUS_COMPLETED
    is_terminal_failure = status_str in ("failed", "cancelled", "rejected")
    is_non_terminal = not is_completed and not is_terminal_failure
    runtime_active = _is_runtime_execution_active("subdub")

    if is_non_terminal and not runtime_active:
        projected_status_reason = "RUNTIME_EXECUTION_NOT_ACTIVATED"
        output_available = False
        download_ready = False
        delivery_ready = False
        output_url_val = None
    else:
        projected_status_reason = str(row[12])
        raw_output_url = str(row[19]) if len(row) > 19 and row[19] is not None else None
        is_safe_url = bool(raw_output_url and is_safe_subdub_output_url(raw_output_url))
        has_real_output = bool(is_completed and is_safe_url)
        output_available = has_real_output
        download_ready = has_real_output
        delivery_ready = has_real_output
        output_url_val = raw_output_url if has_real_output else None

    return {
        "id": str(row[0]),
        "request_id": str(row[1]),
        "account_id": str(row[2]),
        "product_key": str(row[3]),
        "subdub_mode": str(row[4]),
        "mode": str(row[4]),
        "upload_id": str(row[5]),
        "source_language": str(row[6]),
        "target_language": str(row[7]),
        "voice_profile_id": str(row[8]),
        "output_format": str(row[9]),
        "speed": float(row[10]),
        "status": status_str,
        "status_reason": projected_status_reason,
        "output_available": output_available,
        "download_ready": download_ready,
        "delivery_ready": delivery_ready,
        "output": output_url_val,
        "output_url": output_url_val,
        "output_metadata": output_meta,
        "created_at": str(row[17]),
        "updated_at": str(row[18]),
        "bridge_envelope": env,
        "idempotent_replay": idempotent_replay,
    }


def get_subdub_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    """Retrieve a single SubDub job for the authenticated owner."""
    ensure_subdub_schema()
    owner_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not owner_id or not clean_job_id:
        return None

    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, subdub_mode,
                   upload_id, source_language, target_language, voice_profile_id,
                   output_format, speed, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_subdub_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1
            """,
            (clean_job_id, owner_id),
        ).fetchone()

        if row is None:
            return None
        return _format_public_job(row)


def is_subdub_job_other_account(job_id: str, account_id: str) -> bool:
    """Check if a job exists but belongs to a different account (cross-user security)."""
    ensure_subdub_schema()
    owner_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not clean_job_id:
        return False

    with read_transaction() as conn:
        row = conn.execute(
            "SELECT account_id FROM web_subdub_jobs WHERE id = ? LIMIT 1",
            (clean_job_id,),
        ).fetchone()
        if row is None:
            return False
        return str(row[0]) != owner_id


def list_subdub_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """List recent SubDub jobs for the authenticated owner."""
    ensure_subdub_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        return []

    safe_limit = max(1, min(int(limit), 200))
    with read_transaction() as conn:
        rows = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, subdub_mode,
                   upload_id, source_language, target_language, voice_profile_id,
                   output_format, speed, status, status_reason,
                   idempotency_key_hash, payload_hash, bridge_envelope, output_metadata,
                   created_at, updated_at, output_url
            FROM web_subdub_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (owner_id, safe_limit),
        ).fetchall()

        return [_format_public_job(row) for row in rows]


def subdub_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Transform public SubDub job dict into generic Jobs list compatibility item."""
    return {
        "id": job["id"],
        "job_id": job["id"],
        "request_id": job["request_id"],
        "product_key": job.get("product_key", CANONICAL_PRODUCT_KEY),
        "feature": "subdub",
        "title": f"SubDub ({job.get('subdub_mode', 'subtitle')})",
        "status": job["status"],
        "status_reason": job["status_reason"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "output_available": job.get("output_available", False),
        "output_url": job.get("output_url"),
        "read_model": "jobs",
        "canonical_available": False,
    }
