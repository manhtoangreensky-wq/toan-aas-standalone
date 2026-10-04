"""Voice TTS Canonical Job Bridge Adapter.

Task: VOICE_TTS_WEB_RUNTIME_PARITY_SOURCE_REMEDIATION_R1
Product Family: Voice TTS
Tracker: manhtoangreensky-wq/toan-aas-standalone#612

Connects the Web customer flow (/voice/create, /voice/saved) for Voice TTS operations
to a canonical Bot-compatible durable job bridge contract without executing unauthorized
runtime renders, client price fabrication, or direct wallet balance mutations.

Invariants:
- Server Authority: default_voice_gender required ("female" or "male") for default voice (no silent fallback).
- Saved Voice: requires voice_profile_id with server-side ownership.
- Speed/Volume: bound to canonical Bot authority (parse_voice_tts_speed_input, parse_voice_tts_volume_input).
- Language: fixed to 'vi' (server-owned).
- Pricing/Charging: quote computed canonically by Bot; 0 Xu for default free, strictly charged post-generation.
- Safe Delivery: audio artifact delivered via authenticated Web route (/api/v1/features/voice_tts/jobs/{job_id}/artifact).
- Zero-Trust: forbidden fields rejected immediately.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import re
from typing import Any
import uuid

from fastapi import HTTPException
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now

CANONICAL_PRODUCT_KEY = "voice_tts"
CANONICAL_ROUTING_KEY = "voice_tts_canonical"
CANONICAL_ROUTE_ID = "voice_tts_canonical_v1"
CANONICAL_ENGINE_ADAPTER = "bot_voice_tts_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/voice/create"

SUPPORTED_CANONICAL_JOB_ADAPTERS = frozenset({
    "voice_tts",
    "voice_saved_tts",
})

STATUS_PREPARED = "prepared"
STATUS_AWAITING_CONFIRMATION = "awaiting_confirmation"
STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_AMBIGUOUS = "ambiguous"

DEFAULT_VOICE_GENDERS = frozenset({"female", "male"})
VOICE_TTS_DEFAULT_SPEED = "1.0"
VOICE_TTS_DEFAULT_VOLUME_PERCENT = 100
VOICE_TTS_LANGUAGE = "vi"

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED = frozenset({
    "provider",
    "providervoiceid",
    "providervoice",
    "providerid",
    "amount",
    "amountxu",
    "price",
    "cost",
    "walletbalance",
    "balance",
    "wallet",
    "walletid",
    "outputurl",
    "chargedxu",
    "quotexu",
    "ispaidjob",
    "confirmpaid",
    "status",
    "statusreason",
})

CANONICAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")


def parse_voice_tts_speed_input(value: Any) -> str:
    """Canonical speed input parser bound to Bot authority."""
    try:
        import bot
        if hasattr(bot, "parse_voice_tts_speed_input"):
            return bot.parse_voice_tts_speed_input(value)
    except Exception:
        pass
    raw = str(value if value is not None else "").strip().lower().replace(",", ".")
    aliases = {
        "": VOICE_TTS_DEFAULT_SPEED,
        "default": VOICE_TTS_DEFAULT_SPEED,
        "normal": VOICE_TTS_DEFAULT_SPEED,
        "slow": "0.85",
        "fast": "1.2",
    }
    raw = aliases.get(raw, raw)
    if raw.endswith("x"):
        raw = raw[:-1].strip()
    try:
        number = float(raw)
    except Exception as exc:
        raise ValueError("invalid_speed") from exc
    if number < 0.5 or number > 2.0:
        raise ValueError("speed_out_of_range")
    normalized = f"{number:.2f}".rstrip("0").rstrip(".")
    return "1.0" if normalized == "1" else normalized


def parse_voice_tts_volume_input(value: Any) -> int:
    """Canonical volume input parser bound to Bot authority."""
    try:
        import bot
        if hasattr(bot, "parse_voice_tts_volume_input"):
            return bot.parse_voice_tts_volume_input(value)
    except Exception:
        pass
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("volume_integer_required")
    raw = str(value if value is not None else "").strip().lower().replace(" ", "")
    if raw.endswith("%"):
        raw = raw[:-1].strip()
    if "." in raw or "," in raw:
        raise ValueError("volume_integer_required")
    if not re.fullmatch(r"\d+", raw or ""):
        raise ValueError("invalid_volume")
    percent = int(raw)
    if percent < 0 or percent > 200:
        raise ValueError("volume_out_of_range")
    return percent


# Exported authorities for testing contract
VOICE_TTS_SPEED_AUTHORITY = parse_voice_tts_speed_input
VOICE_TTS_SPEED_DEFAULT_AUTHORITY = VOICE_TTS_DEFAULT_SPEED
VOICE_TTS_VOLUME_AUTHORITY = parse_voice_tts_volume_input
VOICE_TTS_VOLUME_DEFAULT_AUTHORITY = VOICE_TTS_DEFAULT_VOLUME_PERCENT


def _contains_authority_field(value: Any) -> bool:
    """Scan nested structure for forbidden client-supplied authority fields."""
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


def _is_runtime_execution_active(feature_key: str = "voice_tts") -> bool:
    """Check compile-time and runtime execution flag."""
    from copyfast_api import WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    return feature_key in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES


def validate_voice_tts_input(values: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Validate and sanitize Voice TTS input payload according to canonical rules.

    Returns:
        (is_valid, error_code, normalized_values)
    """
    if _contains_authority_field(values):
        return False, "authority_field_not_allowed", {}

    script = str(values.get("script") or values.get("text") or "").strip()
    if not script:
        return False, "SCRIPT_REQUIRED", {}

    # Determine voice source
    raw_source = str(values.get("voice_source") or "").strip().lower()
    voice_profile_id_val = values.get("voice_profile_id")
    if not raw_source:
        if voice_profile_id_val:
            raw_source = "saved"
        else:
            raw_source = "default"

    if raw_source not in ("default", "saved"):
        return False, "INVALID_VOICE_SOURCE", {}

    default_gender = ""
    voice_profile_id = ""

    if raw_source == "default":
        gender = str(values.get("default_voice_gender") or "").strip().lower()
        if gender not in DEFAULT_VOICE_GENDERS:
            # Silent fallback is strictly forbidden!
            return False, "DEFAULT_VOICE_GENDER_REQUIRED", {}
        default_gender = gender
    else:  # saved voice
        if not voice_profile_id_val:
            return False, "VOICE_PROFILE_ID_REQUIRED", {}
        vpid_str = str(voice_profile_id_val).strip()
        # Reject raw provider voice IDs
        if not vpid_str.isdigit():
            return False, "RAW_PROVIDER_VOICE_ID_REJECTED", {}
        try:
            vpid_int = int(vpid_str)
            if vpid_int <= 0:
                return False, "VOICE_PROFILE_ID_REQUIRED", {}
        except Exception:
            return False, "VOICE_PROFILE_ID_REQUIRED", {}
        voice_profile_id = str(vpid_int)

    # Validate speed
    raw_speed = values.get("speed", VOICE_TTS_DEFAULT_SPEED)
    try:
        speed_str = parse_voice_tts_speed_input(raw_speed)
    except Exception:
        return False, "INVALID_SPEED", {}

    # Validate volume
    raw_vol = values.get("volume_percent", values.get("volume", VOICE_TTS_DEFAULT_VOLUME_PERCENT))
    try:
        volume_int = parse_voice_tts_volume_input(raw_vol)
    except Exception:
        return False, "INVALID_VOLUME", {}

    normalized = {
        "script": script,
        "voice_source": raw_source,
        "default_voice_gender": default_gender,
        "voice_profile_id": voice_profile_id,
        "speed": speed_str,
        "volume_percent": volume_int,
        "language": VOICE_TTS_LANGUAGE,
    }
    return True, "", normalized


def compute_payload_hash(normalized: dict[str, Any]) -> str:
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_idempotency_hash(key: str) -> str:
    return hashlib.sha256(str(key or "").strip().encode("utf-8")).hexdigest()


def generate_voice_tts_job_id() -> str:
    return f"vtj_{uuid.uuid4().hex}"


def generate_canonical_request_id() -> str:
    return f"VTR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"


def ensure_voice_tts_schema() -> None:
    """Ensure web_voice_tts_jobs table exists in the database."""
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_voice_tts_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'voice_tts',
                voice_source TEXT NOT NULL,
                script TEXT NOT NULL,
                default_voice_gender TEXT,
                voice_profile_id TEXT,
                speed TEXT NOT NULL DEFAULT '1.0',
                volume_percent INTEGER NOT NULL DEFAULT 100,
                language TEXT NOT NULL DEFAULT 'vi',
                status TEXT NOT NULL DEFAULT 'prepared',
                status_reason TEXT NOT NULL DEFAULT '',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                quote_xu INTEGER NOT NULL DEFAULT 0,
                charged_xu INTEGER NOT NULL DEFAULT 0,
                output_url TEXT,
                bridge_envelope TEXT NOT NULL,
                runtime_job_id TEXT,
                runtime_dispatch_status TEXT DEFAULT 'pending',
                runtime_dispatched_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_tts_jobs_account_created ON web_voice_tts_jobs(account_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_tts_jobs_request ON web_voice_tts_jobs(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_tts_jobs_account_idempotency ON web_voice_tts_jobs(account_id, idempotency_key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_web_voice_tts_jobs_status ON web_voice_tts_jobs(status)")


_VOICE_TTS_JOB_COLUMNS = (
    "id, request_id, account_id, product_key, voice_source, "
    "script, default_voice_gender, voice_profile_id, "
    "speed, volume_percent, language, status, status_reason, "
    "idempotency_key_hash, payload_hash, quote_xu, charged_xu, "
    "output_url, bridge_envelope, runtime_job_id, runtime_dispatch_status, "
    "runtime_dispatched_at, created_at, updated_at, completed_at"
)


def _format_public_job(row: Any, idempotent_replay: bool = False) -> dict[str, Any]:
    job_id = str(row[0])
    status_str = str(row[11])
    is_completed = status_str == STATUS_COMPLETED
    has_artifact = is_completed and bool(row[17])

    try:
        env = json.loads(str(row[18])) if row[18] else {}
    except Exception:
        env = {}

    public_output_url = f"/api/v1/features/voice_tts/jobs/{job_id}/artifact" if has_artifact else None

    return {
        "id": job_id,
        "request_id": str(row[1]),
        "account_id": str(row[2]),
        "product_key": str(row[3]),
        "voice_source": str(row[4]),
        "script": str(row[5]),
        "default_voice_gender": str(row[6] or ""),
        "voice_profile_id": str(row[7] or ""),
        "speed": str(row[8]),
        "volume_percent": int(row[9] or 100),
        "language": str(row[10]),
        "status": status_str,
        "status_reason": str(row[12] or ""),
        "quote_xu": int(row[15] or 0),
        "charged_xu": int(row[16] or 0),
        "output": public_output_url,
        "output_url": public_output_url,
        "has_artifact": has_artifact,
        "runtime_job_id": str(row[19] or ""),
        "runtime_dispatch_status": str(row[20] or ""),
        "created_at": str(row[22]),
        "updated_at": str(row[23]),
        "completed_at": str(row[24] or ""),
        "bridge_envelope": env,
        "idempotent_replay": idempotent_replay,
    }


def create_or_replay_voice_tts_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new canonical Voice TTS job or replay existing one idempotently."""
    ensure_voice_tts_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Xác thực tài khoản Web là bắt buộc")

    is_valid, error_code, normalized = validate_voice_tts_input(payload)
    if not is_valid:
        error_messages = {
            "authority_field_not_allowed": "Yêu cầu chứa trường authority bị cấm.",
            "SCRIPT_REQUIRED": "Nội dung lời thoại (script) là bắt buộc.",
            "INVALID_VOICE_SOURCE": "voice_source phải là 'default' hoặc 'saved'.",
            "DEFAULT_VOICE_GENDER_REQUIRED": "default_voice_gender phải là 'female' hoặc 'male'; không được tự ý chọn ngầm.",
            "VOICE_PROFILE_ID_REQUIRED": "voice_profile_id là bắt buộc đối với giọng đã lưu.",
            "RAW_PROVIDER_VOICE_ID_REJECTED": "Từ chối mã định danh provider voice trực tiếp.",
            "INVALID_SPEED": "Tốc độ đọc không hợp lệ (0.5 đến 2.0).",
            "INVALID_VOLUME": "Âm lượng không hợp lệ (0% đến 200%).",
        }
        raise HTTPException(status_code=400, detail=error_messages.get(error_code, error_code))

    payload_hash = compute_payload_hash(normalized)
    effective_req_id = str(request_id or payload.get("request_id") or "").strip()
    effective_idem_key = str(idempotency_key or payload.get("idempotency_key") or "").strip()
    idem_hash = compute_idempotency_hash(effective_idem_key) if effective_idem_key else ""

    with transaction() as conn:
        query = f"""
            SELECT {_VOICE_TTS_JOB_COLUMNS}
            FROM web_voice_tts_jobs
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

        job_id = generate_voice_tts_job_id()
        final_req_id = effective_req_id or generate_canonical_request_id()
        now = utc_now()

        # Blocker 1: Zero Web-local price formula (WEB_LOCAL_VOICE_TTS_PRICE_FORMULA_COUNT=0).
        # Default voice is always 0 Xu (free).
        # Saved voice quote is strictly hydrated from Bot canonical authority.
        quote_xu = 0
        initial_status = STATUS_PREPARED
        status_reason = "PREPARED"

        bridge_envelope = {
            "version": "p0.voice_tts.canonical-bridge.v1",
            "route_id": CANONICAL_ROUTE_ID,
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "product_family": "voice_tts",
            "voice_source": normalized["voice_source"],
            "script": normalized["script"],
            "default_voice_gender": normalized["default_voice_gender"],
            "voice_profile_id": normalized["voice_profile_id"],
            "speed": normalized["speed"],
            "volume_percent": normalized["volume_percent"],
            "language": normalized["language"],
            "request_id": final_req_id,
            "job_id": job_id,
            "account_id": owner_id,
            "status": initial_status,
            "quote_xu": quote_xu,
        }

        conn.execute(
            """
            INSERT INTO web_voice_tts_jobs (
                id, request_id, account_id, product_key, voice_source,
                script, default_voice_gender, voice_profile_id,
                speed, volume_percent, language, status, status_reason,
                idempotency_key_hash, payload_hash, quote_xu, charged_xu,
                output_url, bridge_envelope, runtime_job_id, runtime_dispatch_status,
                runtime_dispatched_at, created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                final_req_id,
                owner_id,
                CANONICAL_PRODUCT_KEY,
                normalized["voice_source"],
                normalized["script"],
                normalized["default_voice_gender"] or None,
                normalized["voice_profile_id"] or None,
                normalized["speed"],
                normalized["volume_percent"],
                normalized["language"],
                initial_status,
                status_reason,
                idem_hash or None,
                payload_hash,
                quote_xu,
                0,
                None,
                json.dumps(bridge_envelope, ensure_ascii=False),
                None,
                "pending",
                None,
                now,
                now,
                None,
            ),
        )

        inserted = conn.execute(
            f"SELECT {_VOICE_TTS_JOB_COLUMNS} FROM web_voice_tts_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        return _format_public_job(inserted, idempotent_replay=False)


def get_voice_tts_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    """Retrieve a single Voice TTS job for the authenticated owner."""
    ensure_voice_tts_schema()
    owner_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not owner_id or not clean_job_id:
        return None

    with read_transaction() as conn:
        row = conn.execute(
            f"SELECT {_VOICE_TTS_JOB_COLUMNS} FROM web_voice_tts_jobs WHERE id = ? AND account_id = ? LIMIT 1",
            (clean_job_id, owner_id),
        ).fetchone()
        if row is None:
            return None
        return _format_public_job(row)


def list_voice_tts_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """List recent Voice TTS jobs for the authenticated owner."""
    ensure_voice_tts_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        return []

    safe_limit = max(1, min(int(limit), 200))
    with read_transaction() as conn:
        rows = conn.execute(
            f"SELECT {_VOICE_TTS_JOB_COLUMNS} FROM web_voice_tts_jobs WHERE account_id = ? ORDER BY created_at DESC LIMIT ?",
            (owner_id, safe_limit),
        ).fetchall()
        return [_format_public_job(row) for row in rows]


def is_voice_tts_job_other_account(job_id: str, account_id: str) -> bool:
    """Check if a job exists but belongs to another account (cross-user isolation)."""
    ensure_voice_tts_schema()
    owner_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not clean_job_id:
        return False

    with read_transaction() as conn:
        row = conn.execute(
            "SELECT account_id FROM web_voice_tts_jobs WHERE id = ? LIMIT 1",
            (clean_job_id,),
        ).fetchone()
        if row is None:
            return False
        return str(row[0]) != owner_id


async def dispatch_voice_tts_job_to_canonical_runtime(
    *,
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Dispatch an admitted Voice TTS job to canonical Bot Core runtime."""
    ensure_voice_tts_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        return {}

    if not _is_runtime_execution_active("voice_tts"):
        return get_voice_tts_job(account_id, clean_job_id) or {}

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured() or not canonical_user_id:
        return get_voice_tts_job(account_id, clean_job_id) or {}

    job = get_voice_tts_job(account_id, clean_job_id)
    if not job:
        return {}

    # Prepare canonical payload strictly from server-validated fields
    canonical_payload = {
        "web_job_id": clean_job_id,
        "web_request_id": job["request_id"],
        "canonical_user_id": canonical_user_id,
        "voice_source": job["voice_source"],
        "script": job["script"],
        "default_voice_gender": job["default_voice_gender"],
        "voice_profile_id": job["voice_profile_id"] if job["voice_source"] == "saved" else None,
        "speed": job["speed"],
        "volume_percent": job["volume_percent"],
        "language": job["language"],
        "idempotency_key": f"{canonical_user_id}:{clean_job_id}",
    }

    try:
        res = await bridge_request(
            "POST",
            "/internal/v1/web-voice-tts/jobs",
            payload=canonical_payload,
            request_id=f"DISPATCH-{job['request_id']}",
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
        if res.get("ok"):
            bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
            rt_id = bot_job.get("job_id") or clean_job_id
            bot_quote = int(bot_job.get("quote_xu") or 0)
            bot_status = str(bot_job.get("status") or "")
            bot_reason = str(bot_job.get("status_reason") or "")
            with transaction() as conn:
                conn.execute(
                    """
                    UPDATE web_voice_tts_jobs
                    SET runtime_job_id = ?,
                        quote_xu = ?,
                        status = CASE WHEN ? != '' THEN ? ELSE status END,
                        status_reason = CASE WHEN ? != '' THEN ? ELSE status_reason END,
                        runtime_dispatch_status = 'dispatched',
                        runtime_dispatched_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (rt_id, bot_quote, bot_status, bot_status, bot_reason, bot_reason, utc_now(), utc_now(), clean_job_id),
                )
    except Exception:
        with transaction() as conn:
            conn.execute(
                "UPDATE web_voice_tts_jobs SET runtime_dispatch_status = 'uncertain', updated_at = ? WHERE id = ?",
                (utc_now(), clean_job_id),
            )

    return get_voice_tts_job(account_id, clean_job_id) or {}


async def confirm_voice_tts_job(
    job_id: str,
    *,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Execute customer confirmation & trigger audio generation + charge in Bot Core."""
    ensure_voice_tts_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        raise HTTPException(status_code=400, detail="Mã job hoặc tài khoản không hợp lệ")

    if is_voice_tts_job_other_account(clean_job_id, account_id):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập job của tài khoản khác")

    job = get_voice_tts_job(account_id, clean_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job Voice TTS của tài khoản")

    if job.get("status") == STATUS_COMPLETED:
        return job

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured():
        raise HTTPException(status_code=503, detail="Core Bridge chưa được cấu hình")

    if not canonical_user_id:
        raise HTTPException(status_code=403, detail="Tài khoản chưa liên kết Telegram canonical user ID")

    # Blocker 1: Paid confirm strictly requires canonical Bot quote
    if job.get("voice_source") == "saved":
        if job.get("runtime_dispatch_status") != "dispatched" or int(job.get("quote_xu") or 0) <= 0:
            dispatched = await dispatch_voice_tts_job_to_canonical_runtime(job_id=clean_job_id, account=account, request=request)
            if not dispatched or dispatched.get("runtime_dispatch_status") != "dispatched":
                raise HTTPException(
                    status_code=502,
                    detail="Chưa nhận được báo giá chính thức từ Bot Core runtime. Không được phép xác nhận (PAID_CONFIRM_ALLOWED_BEFORE_CANONICAL_QUOTE=NO).",
                )
            job = dispatched
            if int(job.get("quote_xu") or 0) <= 0:
                raise HTTPException(
                    status_code=502,
                    detail="Báo giá chính thức từ Bot Core runtime không hợp lệ.",
                )

    # Update local status to processing
    with transaction() as conn:
        conn.execute(
            "UPDATE web_voice_tts_jobs SET status = 'processing', status_reason = 'PROCESSING', updated_at = ? WHERE id = ?",
            (utc_now(), clean_job_id),
        )

    # Now call confirm endpoint on Bot Core
    try:
        res = await bridge_request(
            "POST",
            f"/internal/v1/web-voice-tts/jobs/{clean_job_id}/confirm",
            payload={},
            request_id=f"CONFIRM-{job['request_id']}",
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
    except Exception as exc:
        with transaction() as conn:
            conn.execute(
                "UPDATE web_voice_tts_jobs SET status = 'ambiguous', status_reason = 'NETWORK_UNCERTAIN', updated_at = ? WHERE id = ?",
                (utc_now(), clean_job_id),
            )
        raise HTTPException(status_code=502, detail=f"Lỗi kết nối tới Bot Core: {exc}")

    if not res.get("ok"):
        err_code = res.get("error_code") or "PROVIDER_EXECUTION_FAILED"
        new_status = "payment_required" if err_code == "INSUFFICIENT_FUNDS" else "failed"
        with transaction() as conn:
            conn.execute(
                "UPDATE web_voice_tts_jobs SET status = ?, status_reason = ?, updated_at = ? WHERE id = ?",
                (new_status, err_code, utc_now(), clean_job_id),
            )
        msg = res.get("message") or "Tạo âm thanh thất bại"
        raise HTTPException(status_code=402 if err_code == "INSUFFICIENT_FUNDS" else 422, detail=msg)

    bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
    charged_xu = int(bot_job.get("charged_xu") or 0)
    has_artifact = bool(bot_job.get("has_artifact"))
    safe_output_url = f"/api/v1/features/voice_tts/jobs/{clean_job_id}/artifact" if has_artifact else None

    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_voice_tts_jobs
            SET status = 'completed', status_reason = 'COMPLETED',
                charged_xu = ?, output_url = ?, completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (charged_xu, safe_output_url, utc_now(), utc_now(), clean_job_id),
        )

    return get_voice_tts_job(account_id, clean_job_id) or {}


async def reconcile_voice_tts_job_status(
    job_id: str,
    *,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any] | None:
    """Reconcile job status from Bot Core without financial side effects (read-only)."""
    ensure_voice_tts_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        return None

    if is_voice_tts_job_other_account(clean_job_id, account_id):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập job của tài khoản khác")

    job = get_voice_tts_job(account_id, clean_job_id)
    if not job:
        return None

    if job.get("status") in (STATUS_COMPLETED, STATUS_FAILED):
        return job

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured() or not canonical_user_id:
        return job

    try:
        res = await bridge_request(
            "GET",
            f"/internal/v1/web-voice-tts/jobs/{clean_job_id}",
            request_id=f"STATUS-{job['request_id']}",
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
        if res.get("ok"):
            bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
            rt_status = bot_job.get("status")
            if rt_status and rt_status != job.get("status"):
                has_artifact = bool(bot_job.get("has_artifact"))
                safe_output_url = f"/api/v1/features/voice_tts/jobs/{clean_job_id}/artifact" if has_artifact else None
                charged_xu = int(bot_job.get("charged_xu") or 0)
                with transaction() as conn:
                    conn.execute(
                        """
                        UPDATE web_voice_tts_jobs
                        SET status = ?, status_reason = ?, charged_xu = ?,
                            output_url = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (rt_status, bot_job.get("status_reason", ""), charged_xu, safe_output_url, utc_now(), clean_job_id),
                    )
    except Exception:
        pass

    return get_voice_tts_job(account_id, clean_job_id)


def voice_tts_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Convert Voice TTS job record into Job Center / Web-native compatible structure."""
    job_id = job.get("id", "")
    status_str = job.get("status", "queued")
    has_artifact = bool(job.get("has_artifact"))
    safe_output_url = f"/api/v1/features/voice_tts/jobs/{job_id}/artifact" if has_artifact else None

    return {
        "id": job_id,
        "job_id": job_id,
        "request_id": job.get("request_id", ""),
        "account_id": job.get("account_id", ""),
        "feature_key": "voice_tts",
        "product_key": "voice_tts",
        "action": "create",
        "title": f"Tạo giọng nói AI ({job.get('voice_source', 'default')})",
        "status": status_str,
        "status_name": status_str,
        "status_reason": job.get("status_reason", ""),
        "created_at": job.get("created_at", ""),
        "updated_at": job.get("updated_at", ""),
        "quote_xu": job.get("quote_xu", 0),
        "charged_xu": job.get("charged_xu", 0),
        "output": safe_output_url,
        "output_url": safe_output_url,
        "has_artifact": has_artifact,
        "download_ready": has_artifact,
        "delivery_ready": has_artifact,
    }
