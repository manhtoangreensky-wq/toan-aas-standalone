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

PAID_SUBDUB_MODES = frozenset({
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
    """Initialize dedicated web_subdub_jobs SQLite table, indexes, and runtime linkage columns."""
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
                runtime_job_id TEXT,
                runtime_dispatch_status TEXT DEFAULT 'pending',
                runtime_dispatched_at TEXT,
                runtime_request_id TEXT,
                runtime_last_error TEXT,
                settlement_status TEXT DEFAULT 'pending',
                settlement_id TEXT,
                charged_xu INTEGER DEFAULT 0,
                settled_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(web_subdub_jobs)").fetchall()}
        runtime_cols = [
            ("runtime_job_id", "TEXT"),
            ("runtime_dispatch_status", "TEXT DEFAULT 'pending'"),
            ("runtime_dispatched_at", "TEXT"),
            ("runtime_request_id", "TEXT"),
            ("runtime_last_error", "TEXT"),
            ("settlement_status", "TEXT DEFAULT 'pending'"),
            ("settlement_id", "TEXT"),
            ("charged_xu", "INTEGER DEFAULT 0"),
            ("settled_at", "TEXT"),
        ]
        for col_name, col_def in runtime_cols:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE web_subdub_jobs ADD COLUMN {col_name} {col_def}")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_account_created ON web_subdub_jobs(account_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_request ON web_subdub_jobs(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_account_idempotency ON web_subdub_jobs(account_id, idempotency_key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_status_created ON web_subdub_jobs(status, created_at ASC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_runtime_job ON web_subdub_jobs(runtime_job_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_subdub_jobs_settlement ON web_subdub_jobs(settlement_status)")


_SUBDUB_JOB_COLUMNS = (
    "id, request_id, account_id, product_key, subdub_mode, "
    "upload_id, source_language, target_language, voice_profile_id, "
    "output_format, speed, status, status_reason, "
    "idempotency_key_hash, payload_hash, bridge_envelope, output_metadata, "
    "created_at, updated_at, output_url, "
    "runtime_job_id, runtime_dispatch_status, runtime_dispatched_at, runtime_request_id, runtime_last_error, "
    "settlement_status, settlement_id, charged_xu, settled_at"
)


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
        query = f"""
            SELECT {_SUBDUB_JOB_COLUMNS}
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
                output_metadata, created_at, updated_at, output_url,
                runtime_job_id, runtime_dispatch_status, runtime_dispatched_at,
                runtime_request_id, runtime_last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL, NULL, 'pending', NULL, NULL, NULL)
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
            "runtime_job_id": None,
            "runtime_dispatch_status": "pending",
            "runtime_dispatched_at": None,
            "runtime_request_id": None,
            "runtime_last_error": None,
            "settlement_status": "pending",
            "settlement_id": None,
            "charged_xu": 0,
            "settled_at": None,
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

    subdub_mode = str(row[4] or "subtitle_create").strip()
    is_paid_lane = subdub_mode in PAID_SUBDUB_MODES
    settlement_status_str = str(row[25]) if len(row) > 25 and row[25] else "pending"

    if is_non_terminal and not runtime_active:
        projected_status_reason = "RUNTIME_EXECUTION_NOT_ACTIVATED"
        output_available = False
        download_ready = False
        delivery_ready = False
        output_url_val = None
        public_output_meta = None
    else:
        projected_status_reason = str(row[12])
        if is_paid_lane and settlement_status_str == "insufficient_funds":
            projected_status_reason = "SETTLEMENT_PAYMENT_REQUIRED"

        raw_output_url = str(row[19]) if len(row) > 19 and row[19] is not None else None
        is_safe_url = bool(raw_output_url and is_safe_subdub_output_url(raw_output_url))

        # Delivery Gate:
        # - Free lane (subtitle_create): completed + safe URL
        # - Paid lanes: completed + safe URL + settlement_status == 'settled'
        if is_paid_lane:
            has_real_output = bool(is_completed and is_safe_url and settlement_status_str == "settled")
        else:
            has_real_output = bool(is_completed and is_safe_url)

        output_available = has_real_output
        download_ready = has_real_output
        delivery_ready = has_real_output
        output_url_val = raw_output_url if has_real_output else None
        public_output_meta = output_meta if has_real_output else None

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
        "output_metadata": public_output_meta,
        "created_at": str(row[17]),
        "updated_at": str(row[18]),
        "bridge_envelope": env,
        "idempotent_replay": idempotent_replay,
        "runtime_job_id": str(row[20]) if len(row) > 20 and row[20] else None,
        "runtime_dispatch_status": str(row[21]) if len(row) > 21 and row[21] else "pending",
        "runtime_dispatched_at": str(row[22]) if len(row) > 22 and row[22] else None,
        "runtime_request_id": str(row[23]) if len(row) > 23 and row[23] else None,
        "runtime_last_error": str(row[24]) if len(row) > 24 and row[24] else None,
        "settlement_status": settlement_status_str,
        "settlement_id": str(row[26]) if len(row) > 26 and row[26] else None,
        "charged_xu": int(row[27] or 0) if len(row) > 27 and row[27] is not None else 0,
        "settled_at": str(row[28]) if len(row) > 28 and row[28] else None,
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
            f"""
            SELECT {_SUBDUB_JOB_COLUMNS}
            FROM web_subdub_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1
            """,
            (clean_job_id, owner_id),
        ).fetchone()

        if row is None:
            return None
        return _format_public_job(row)


def get_internal_subdub_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    """Retrieve raw internal SubDub job state with unmasked artifact truth for server authority."""
    ensure_subdub_schema()
    owner_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not owner_id or not clean_job_id:
        return None

    with read_transaction() as conn:
        row = conn.execute(
            f"""
            SELECT {_SUBDUB_JOB_COLUMNS}
            FROM web_subdub_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1
            """,
            (clean_job_id, owner_id),
        ).fetchone()

        if row is None:
            return None

    try:
        env = json.loads(str(row[15])) if len(row) > 15 and row[15] else {}
    except Exception:
        env = {}
    try:
        output_meta = json.loads(str(row[16])) if len(row) > 16 and row[16] else None
    except Exception:
        output_meta = None

    raw_output_url = str(row[19]) if len(row) > 19 and row[19] is not None else None

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
        "status": str(row[11]),
        "status_reason": str(row[12]),
        "output_url": raw_output_url,
        "raw_output_url": raw_output_url,
        "output_metadata": output_meta,
        "created_at": str(row[17]),
        "updated_at": str(row[18]),
        "bridge_envelope": env,
        "runtime_job_id": str(row[20]) if len(row) > 20 and row[20] else None,
        "runtime_dispatch_status": str(row[21]) if len(row) > 21 and row[21] else "pending",
        "runtime_dispatched_at": str(row[22]) if len(row) > 22 and row[22] else None,
        "runtime_request_id": str(row[23]) if len(row) > 23 and row[23] else None,
        "runtime_last_error": str(row[24]) if len(row) > 24 and row[24] else None,
        "settlement_status": str(row[25]) if len(row) > 25 and row[25] else "pending",
        "settlement_id": str(row[26]) if len(row) > 26 and row[26] else None,
        "charged_xu": int(row[27] or 0) if len(row) > 27 and row[27] is not None else 0,
        "settled_at": str(row[28]) if len(row) > 28 and row[28] else None,
    }


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
            f"""
            SELECT {_SUBDUB_JOB_COLUMNS}
            FROM web_subdub_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (owner_id, safe_limit),
        ).fetchall()

        return [_format_public_job(row) for row in rows]


HISTORICAL_R7_FAILED_JOB_ID = "sdj_0058b35d35ff42b2823ddf9c0068645c"


async def dispatch_subdub_job_to_canonical_runtime(
    *,
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Dispatch an admitted SubDub job to canonical Bot Core runtime.

    Invariants:
    - Bounded execution: exactly one dispatch attempt per job.
    - Preconditions: _is_runtime_execution_active('subdub') and bridge_configured() and canonical_user_id.
    - Historical R7 job sdj_0058b35d35ff42b2823ddf9c0068645c is preserved and NEVER dispatched.
    - Signed call: binds actor_id and owner_id to canonical Telegram user ID.
    - Zero provider credentials, zero local financial mutation.
    - Ambiguous network outcome: records 'uncertain' status, NO BLIND RETRY.
    """
    ensure_subdub_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        return {}

    # Historical failed R7 job invariant: do not mutate or dispatch
    if clean_job_id == HISTORICAL_R7_FAILED_JOB_ID:
        return get_subdub_job(account_id, clean_job_id) or {}

    # Precondition 1: Runtime execution gate
    if not _is_runtime_execution_active("subdub"):
        return get_subdub_job(account_id, clean_job_id) or {}

    # Precondition 2: Bridge configured
    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured():
        return get_subdub_job(account_id, clean_job_id) or {}

    # Precondition 3: Canonical actor linkage exists
    if not canonical_user_id:
        return get_subdub_job(account_id, clean_job_id) or {}

    # Precondition 4: Job exists, belongs to account, and has not yet been dispatched
    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT id, request_id, account_id, subdub_mode, upload_id,
                   source_language, target_language, voice_profile_id, output_format, speed,
                   runtime_job_id, runtime_dispatch_status
            FROM web_subdub_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1
            """,
            (clean_job_id, account_id),
        ).fetchone()

    if not row:
        return {}

    existing_rt_id = str(row[10]) if len(row) > 10 and row[10] else None
    existing_dispatch_status = str(row[11]) if len(row) > 11 and row[11] else "pending"

    # Idempotent guard: already dispatched
    if existing_rt_id or existing_dispatch_status in ("dispatched", "uncertain"):
        return get_subdub_job(account_id, clean_job_id) or {}

    # Prepare canonical payload strictly from server-validated fields
    req_id = str(row[1])
    dispatch_req_id = f"DISPATCH-{req_id}"
    canonical_payload = {
        "mode": str(row[3]),
        "payload": {
            "upload_id": str(row[4]),
            "source_language": str(row[5] or "auto"),
            "target_language": str(row[6] or ""),
            "voice_profile_id": str(row[7] or ""),
            "output_format": str(row[8] or "vtt"),
            "speed": float(row[9] or 1.0),
            "web_job_id": clean_job_id,
            "request_id": req_id,
        },
        "max_attempts": 1,
    }

    try:
        res = await bridge_request(
            "POST",
            "/internal/v1/subdub/jobs",
            payload=canonical_payload,
            request_id=dispatch_req_id,
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
    except (TypeError, ValueError, AttributeError, KeyError):
        raise
    except Exception as exc:
        # Ambiguous network outcome: fail-closed without blind retry
        now_ts = utc_now()
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_dispatch_status='uncertain',
                    runtime_last_error=?,
                    updated_at=?
                WHERE id=? AND (runtime_job_id IS NULL OR runtime_job_id='')
                """,
                (f"NETWORK_TIMEOUT_OR_ERROR:{type(exc).__name__}", now_ts, clean_job_id),
            )
        return get_subdub_job(account_id, clean_job_id) or {}

    now_ts = utc_now()
    if res.get("ok"):
        rt_job = (res.get("data") or {}).get("job") or res.get("job") or {}
        rt_job_id = str(rt_job.get("job_id") or "").strip()
        rt_status = str(rt_job.get("status") or "queued").strip().lower()
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_job_id=?,
                    runtime_dispatch_status='dispatched',
                    runtime_dispatched_at=?,
                    runtime_request_id=?,
                    status=?,
                    status_reason='DISPATCHED_TO_CANONICAL_RUNTIME',
                    updated_at=?
                WHERE id=?
                """,
                (rt_job_id, now_ts, dispatch_req_id, rt_status, now_ts, clean_job_id),
            )
    else:
        err_msg = str(res.get("error_code") or res.get("message") or "BRIDGE_DISPATCH_REJECTED")
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_dispatch_status='failed',
                    runtime_last_error=?,
                    updated_at=?
                WHERE id=?
                """,
                (err_msg, now_ts, clean_job_id),
            )

    return get_subdub_job(account_id, clean_job_id) or {}


async def reconcile_subdub_job_status(
    job_id: str,
    *,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any] | None:
    """Reconcile local SubDub job status against canonical Bot Core runtime on read.

    If job has a valid runtime_job_id and is currently non-terminal, queries
    GET /internal/v1/subdub/jobs/{runtime_job_id} and reconciles state and artifact.
    """
    ensure_subdub_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        return None

    # Retrieve current local state
    job = get_subdub_job(account_id, clean_job_id)
    if not job:
        return None

    # Historical job is never reconciled from remote
    if clean_job_id == HISTORICAL_R7_FAILED_JOB_ID:
        return job

    rt_job_id = str(job.get("runtime_job_id") or "").strip()
    current_status = str(job.get("status") or "").strip().lower()

    # Reconcile only if dispatched to runtime and currently non-terminal
    if not rt_job_id or current_status in ("completed", "failed", "cancelled", "rejected"):
        return job

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured() or not canonical_user_id:
        return job

    recon_req_id = f"RECON-{clean_job_id}-{uuid.uuid4().hex[:6]}"
    try:
        res = await bridge_request(
            "GET",
            f"/internal/v1/subdub/jobs/{rt_job_id}",
            request_id=recon_req_id,
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
    except (TypeError, ValueError, AttributeError, KeyError):
        raise
    except Exception:
        # On read-timeout, keep existing local state fail-closed
        return job

    if not res.get("ok"):
        return job

    rt_job = (res.get("data") or {}).get("job") or res.get("job") or {}
    rt_status = str(rt_job.get("status") or "").strip().lower()
    now_ts = utc_now()

    if rt_status == "processing":
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET status='processing',
                    status_reason='CANONICAL_RUNTIME_PROCESSING',
                    updated_at=?
                WHERE id=? AND status != 'completed'
                """,
                (now_ts, clean_job_id),
            )
    elif rt_status == "completed":
        result = rt_job.get("result") if isinstance(rt_job.get("result"), dict) else {}
        raw_url = str(result.get("output_url") or result.get("download_url") or result.get("url") or "").strip()
        if raw_url and is_safe_subdub_output_url(raw_url):
            with transaction() as conn:
                conn.execute(
                    """
                    UPDATE web_subdub_jobs
                    SET status='completed',
                        status_reason='COMPLETED',
                        output_url=?,
                        output_metadata=?,
                        updated_at=?
                    WHERE id=?
                    """,
                    (raw_url, json.dumps(result, ensure_ascii=False), now_ts, clean_job_id),
                )
        else:
            # Completed without valid/safe artifact: fail-closed, do NOT mark completed, do NOT settle
            with transaction() as conn:
                conn.execute(
                    """
                    UPDATE web_subdub_jobs
                    SET status_reason='COMPLETED_WITHOUT_SAFE_ARTIFACT',
                        settlement_status='cancelled_unsafe_artifact',
                        charged_xu=0,
                        updated_at=?
                    WHERE id=?
                    """,
                    (now_ts, clean_job_id),
                )
    elif rt_status in ("failed", "error"):
        err_msg = str(rt_job.get("last_error") or rt_job.get("error_code") or "CANONICAL_RUNTIME_FAILED").strip()
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET status='failed',
                    status_reason=?,
                    settlement_status='cancelled_job_failed',
                    charged_xu=0,
                    updated_at=?
                WHERE id=?
                """,
                (err_msg, now_ts, clean_job_id),
            )

    return get_subdub_job(account_id, clean_job_id)


async def settle_subdub_job_completion(
    job_id: str,
    *,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any] | None:
    """Execute canonical financial settlement for a completed SubDub job.

    Invariants:
    - Server-authoritative mutation transition only, never invoked by GET routes.
    - Exact canonical wire schema:
        {
            "web_job_id": "...",
            "web_request_id": "...",
            "canonical_user_id": "...",
            "subdub_mode": "...",
            "output_url": "https://...",
            "validated_output_metadata": {...},
            "idempotency_key": "..."
        }
    - 0 debits for subtitle_create (exempt_free).
    - 0 debits on failed job, unsafe artifact, or missing output.
    - Exactly 1 debit for completed paid lane.
    - Idempotent: duplicate settlement returns existing receipt with duplicate=True.
    - Insufficient funds: maps to settlement_status='insufficient_funds', 402, 0 wallet debit.
    """
    ensure_subdub_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        return None

    # Historical job is never settled
    if clean_job_id == HISTORICAL_R7_FAILED_JOB_ID:
        return get_subdub_job(account_id, clean_job_id)

    # Use internal job authority so server accesses real artifact truth
    internal_job = get_internal_subdub_job(account_id, clean_job_id)
    if not internal_job:
        return None

    status_str = str(internal_job.get("status") or "").strip().lower()
    raw_url = str(internal_job.get("output_url") or "").strip()
    has_safe_url = bool(raw_url and is_safe_subdub_output_url(raw_url))

    # Invariant: Must be completed with safe output URL
    if status_str != "completed" or not has_safe_url:
        return get_subdub_job(account_id, clean_job_id)

    subdub_mode = str(internal_job.get("subdub_mode") or "subtitle_create")
    current_settlement = str(internal_job.get("settlement_status") or "pending")
    now_ts = utc_now()

    # Free helper lane: mark exempt_free with 0 Xu
    if subdub_mode == "subtitle_create":
        if current_settlement != "exempt_free":
            with transaction() as conn:
                conn.execute(
                    """
                    UPDATE web_subdub_jobs
                    SET settlement_status='exempt_free',
                        charged_xu=0,
                        settled_at=?,
                        updated_at=?
                    WHERE id=?
                    """,
                    (now_ts, now_ts, clean_job_id),
                )
        return get_subdub_job(account_id, clean_job_id)

    # Idempotent replay: already settled
    if current_settlement == "settled":
        return get_subdub_job(account_id, clean_job_id)

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured() or not canonical_user_id:
        return get_subdub_job(account_id, clean_job_id)

    validated_metadata = internal_job.get("output_metadata") if isinstance(internal_job.get("output_metadata"), dict) else {}
    if not validated_metadata:
        validated_metadata = {"output_url": raw_url, "mode": subdub_mode}

    # EXACT CANONICAL SETTLEMENT WIRE SCHEMA
    settle_payload = {
        "web_job_id": clean_job_id,
        "web_request_id": str(internal_job.get("request_id") or ""),
        "canonical_user_id": canonical_user_id,
        "subdub_mode": subdub_mode,
        "output_url": raw_url,
        "validated_output_metadata": validated_metadata,
        "idempotency_key": f"subdub_settle:{clean_job_id}:{subdub_mode}",
    }

    try:
        settle_res = await bridge_request(
            "POST",
            "/internal/v1/web-subdub/settle",
            payload=settle_payload,
            request_id=f"SETTLE-{clean_job_id}",
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
    except Exception:
        # Ambiguous network outcome: fail-closed, keep settlement pending for idempotent retry
        return get_subdub_job(account_id, clean_job_id)

    if isinstance(settle_res, dict) and settle_res.get("ok"):
        s_data = settle_res.get("data") if isinstance(settle_res.get("data"), dict) else settle_res
        settle_id = str(s_data.get("settlement_id") or f"stl_{clean_job_id}")
        amount_xu = int(s_data.get("amount_xu") or 0)
        settled_ts = str(s_data.get("settled_at") or now_ts)
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET settlement_status='settled',
                    settlement_id=?,
                    charged_xu=?,
                    settled_at=?,
                    updated_at=?
                WHERE id=?
                """,
                (settle_id, amount_xu, settled_ts, now_ts, clean_job_id),
            )
    elif isinstance(settle_res, dict) and settle_res.get("error_code") == "INSUFFICIENT_FUNDS":
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET settlement_status='insufficient_funds',
                    status_reason='SETTLEMENT_PAYMENT_REQUIRED',
                    charged_xu=0,
                    updated_at=?
                WHERE id=?
                """,
                (now_ts, clean_job_id),
            )

    return get_subdub_job(account_id, clean_job_id)


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
        "settlement_status": job.get("settlement_status", "pending"),
        "charged_xu": job.get("charged_xu", 0),
        "read_model": "jobs",
        "canonical_available": False,
    }
