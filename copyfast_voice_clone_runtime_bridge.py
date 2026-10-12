"""Voice Clone Canonical Runtime Bridge Adapter.

Task: WEBAPP_R24B4_VOICE_CLONE_AUTHORITY_RECONCILIATION_AND_CANONICAL_BOT_RUNTIME_BRIDGE_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Product Family: VOICE
Product: VOICE_CLONE
Current Route: /voice/clone
Feature Key: voice_clone

Connects the Web customer flow (/voice/clone) to the canonical Bot-owned Voice Clone
runtime via the private Core Bridge, without creating shadow database tables,
without local first-free/wallet calculations, and without executing external provider calls.

Invariants:
- Zero Shadow DB Tables: Web DB never creates web_voice_clone_jobs, web_staged_uploads,
  or web_voice_clone_first_free_entitlements. Bot is the sole state & commercial authority.
- Fail-Closed Admission: zero provider calls until authorized live acceptance.
- Single Upload: customer must supply exactly one staged upload ID (upload_ids=[upl_xxx]).
- Affirmative Consent: consent=True is mandatory. Missing or false consent is rejected.
- Display Name Contract: optional, maximum 120 characters, whitespace sanitized.
- Safe Projection: internal paths, provider secrets, tokens, HMAC, and raw DB details
  are strictly omitted before returning to callers.
- Replay Idempotency: exact payloads replay safely from Bot canonical source.
- Provider Neutrality & Incident Hold: VOICE_CLONE_EXTERNAL_PROVIDER_INCIDENT_HOLD=OPEN.
  External provider execution (MiniMax, ElevenLabs) is strictly disabled in Web.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException
from copyfast_bridge import bridge_configured, bridge_request, envelope

# ─── CANONICAL CONSTANTS ─────────────────────────────────────────────────────

CANONICAL_PRODUCT_KEY = "voice_clone"
CANONICAL_ROUTING_KEY = "voice_clone"
CANONICAL_ROUTE_ID = "voice_clone_canonical_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/voice/clone"
CANONICAL_FEATURE_KEY = "voice_clone"

SUPPORTED_CANONICAL_JOB_ADAPTERS: frozenset[str] = frozenset({
    "voice_clone",
})

STATUS_PREPARED = "prepared"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE"
STATUS_REASON_COMPLETED = "COMPLETED"

# External provider dispatch flags — strictly disabled in R24B4
VOICE_CLONE_PROVIDER_EXECUTION_ENABLED: bool = False
VOICE_CLONE_EXTERNAL_PROVIDER_INCIDENT_HOLD: str = "OPEN"
MINIMAX_PUBLIC_ENABLED: bool = False
ELEVENLABS_PUBLIC_ENABLED: bool = False

# Bot authority sample boundaries
CUSTOM_VOICE_ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".mp3", ".m4a", ".wav"})
CUSTOM_VOICE_MAX_SAMPLE_BYTES: int = 20 * 1024 * 1024
CUSTOM_VOICE_MIN_DETECTABLE_SECONDS: float = 10.0

# Forbidden authority and financial fields that clients must never supply
FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "amount", "amountvnd", "amountxu", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providername", "providerid", "providertaskid",
    "providerjobid", "providervoiceid", "providerfileid", "providerroute", "model", "modelname",
    "tier", "qualitytier", "quotexu", "chargedxu", "xu", "xucost", "xucharge", "fee", "credits",
    "wallet", "walletid", "walletbalance", "balance", "apikey", "apitoken", "token", "secret",
    "jobid", "jobstatus", "status", "statusreason", "output", "outputurl", "assetid", "downloadurl",
    "role", "filepath", "localpath", "previewaudiopath", "accountid", "userid", "canonicaluserid",
    "actorid", "telegramuserid", "profileid", "canonicalprofileid", "ispaidjob", "confirmpaid",
})

# Structural truth declarations
WEB_VOICE_CLONE_SHADOW_JOB_TABLE_CREATED: bool = False
WEB_VOICE_CLONE_SHADOW_UPLOAD_TABLE_CREATED: bool = False
WEB_VOICE_CLONE_SHADOW_FIRST_FREE_TABLE_CREATED: bool = False

VOICE_CLONE_CANONICAL_JOB_ADAPTER_PRESENT: bool = True
VOICE_CLONE_INPUT_CONTRACT_RESOLVED: bool = True
VOICE_CLONE_UPLOAD_AUTHORITY_LOOKUP_RESOLVED: bool = True
VOICE_CLONE_BOT_RUNTIME_AUTHORITY_RESOLVED: bool = True

SENSITIVE_KEY_SUBSTRINGS: tuple[str, ...] = (
    "api_key", "apikey", "token", "authorization", "secret",
    "credential", "cookie", "password", "signed_url_secret", "session",
    "local_path", "preview_audio_path", "provider_file_id", "provider_voice_id",
    "provider_task_id", "hmac",
)


def _normalize_key(key: str) -> str:
    """Normalize input key by stripping underscores and converting to lowercase."""
    return re.sub(r"[^a-zA-Z0-9]", "", str(key or "")).lower()


def contains_forbidden_authority_fields(payload: dict[str, Any]) -> tuple[bool, str]:
    """Check if client payload contains any forbidden authority, financial, or provider fields."""
    if not isinstance(payload, dict):
        return False, ""
    for k, v in payload.items():
        norm = _normalize_key(k)
        if norm in FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED:
            return True, str(k)
        if isinstance(v, dict):
            sub_forbidden, sub_k = contains_forbidden_authority_fields(v)
            if sub_forbidden:
                return True, sub_k
    return False, ""


def validate_voice_clone_input(payload: dict[str, Any]) -> tuple[bool, str | None, dict[str, Any]]:
    """Validate customer input for Voice Clone job preparation.

    Enforces:
    - Zero forbidden authority/provider/price/status fields.
    - Exactly one staged upload ID (upload_ids=[upl_xxx]).
    - Mandatory affirmative consent (consent=True).
    - Optional display_name up to 120 characters, sanitized.
    """
    if not isinstance(payload, dict):
        return False, "invalid_payload_format", {}

    is_forbidden, forbidden_field = contains_forbidden_authority_fields(payload)
    if is_forbidden:
        return False, f"forbidden_authority_field:{forbidden_field}", {}

    # Validate upload_ids: exactly one required
    raw_uploads = payload.get("upload_ids")
    if raw_uploads is None:
        raw_uploads = payload.get("upload_id")
    if raw_uploads is None:
        raw_uploads = payload.get("sample")

    if not raw_uploads:
        return False, "upload_required", {}

    clean_upload_id = ""
    if isinstance(raw_uploads, list):
        if len(raw_uploads) != 1 or not str(raw_uploads[0]).strip():
            return False, "single_upload_required", {}
        clean_upload_id = str(raw_uploads[0]).strip()
    elif isinstance(raw_uploads, str):
        clean_upload_id = raw_uploads.strip()
    else:
        return False, "single_upload_required", {}

    if not clean_upload_id:
        return False, "upload_required", {}

    # Validate consent: mandatory affirmative boolean
    consent_val = payload.get("consent")
    is_consented = False
    if isinstance(consent_val, bool) and consent_val is True:
        is_consented = True
    elif isinstance(consent_val, str) and consent_val.strip().lower() in ("true", "1", "yes"):
        is_consented = True
    elif isinstance(consent_val, (int, float)) and int(consent_val) == 1:
        is_consented = True

    if not is_consented:
        return False, "voice_clone_consent_required", {}

    # Validate display_name: optional, max 120 characters
    raw_display_name = str(payload.get("display_name") or "").strip()
    if len(raw_display_name) > 120:
        return False, "display_name_too_long", {}
    clean_display_name = re.sub(r"\s+", " ", raw_display_name)[:120]
    if not clean_display_name:
        clean_display_name = "Giọng clone mới"

    sanitized = {
        "upload_ids": [clean_upload_id],
        "upload_id": clean_upload_id,
        "consent": True,
        "display_name": clean_display_name,
    }
    return True, None, sanitized


def to_web_safe_voice_clone_job(job: dict[str, Any]) -> dict[str, Any]:
    """Sanitize Bot job response for external Web consumption.

    Strips any residual provider credentials, local paths, or internal tokens.
    """
    if not isinstance(job, dict):
        return {}

    status = str(job.get("status") or STATUS_PREPARED)
    profile_id = job.get("canonical_profile_id")
    expose_profile_id = int(profile_id) if profile_id and status in ("completed", "ready") else None

    # Filter out sensitive keys from any nested structures
    cleaned: dict[str, Any] = {
        "ok": True,
        "job_id": str(job.get("job_id") or job.get("id") or ""),
        "upload_id": str(job.get("upload_id") or ""),
        "display_name": str(job.get("display_name") or ""),
        "status": status,
        "status_reason": str(job.get("status_reason") or STATUS_REASON_AWAITING),
        "quote_xu": int(job.get("quote_xu") or 0),
        "charged_xu": int(job.get("charged_xu") or 0),
        "pricing_state": str(job.get("pricing_state") or "first_free"),
        "canonical_profile_id": expose_profile_id,
        "has_preview_audio": bool(int(job.get("preview_audio_bytes") or 0) > 0),
        "preview_audio_bytes": int(job.get("preview_audio_bytes") or 0),
        "created_at": str(job.get("created_at") or ""),
        "updated_at": str(job.get("updated_at") or ""),
        "completed_at": str(job.get("completed_at") or "") if job.get("completed_at") else None,
        "idempotent_replay": bool(job.get("idempotent_replay", False)),
    }
    return cleaned


def voice_clone_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Adapt one Voice Clone job record to the generic Jobs read shape."""
    public_id = str(job.get("job_id") or job.get("id") or "").strip()
    return {
        "id": public_id,
        "feature": CANONICAL_FEATURE_KEY,
        "product_key": CANONICAL_PRODUCT_KEY,
        "status": str(job.get("status") or STATUS_PREPARED),
        "status_reason": str(job.get("status_reason") or STATUS_REASON_AWAITING),
        "quote_xu": int(job.get("quote_xu") or 0),
        "charged_xu": int(job.get("charged_xu") or 0),
        "pricing_state": str(job.get("pricing_state") or "first_free"),
        "created_at": str(job.get("created_at") or ""),
        "updated_at": str(job.get("updated_at") or ""),
        "completed_at": job.get("completed_at"),
    }


async def create_or_prepare_voice_clone_job(
    *,
    account: dict[str, Any],
    payload: dict[str, Any],
    idempotency_key: str = "",
    request_id: str = "",
) -> dict[str, Any]:
    """Prepare a canonical Voice Clone job via Bot Core private bridge.

    Validates inputs, derives caller identity, verifies bridge readiness,
    and forwards request to Bot POST /internal/v1/web-voice-clone/jobs.
    """
    valid, err_msg, sanitized = validate_voice_clone_input(payload)
    if not valid:
        raise HTTPException(status_code=400, detail=err_msg or "Dữ liệu yêu cầu không hợp lệ")

    canonical_user_id = str(account.get("canonical_user_id") or "").strip()
    if not canonical_user_id:
        raise HTTPException(
            status_code=409,
            detail="Hãy liên kết Telegram trước khi dùng tính năng Voice Clone",
        )

    if not bridge_configured():
        return envelope(
            False,
            "Cầu nối Core Bridge chưa được cấu hình.",
            status_name="guarded",
            error_code="CORE_BRIDGE_NOT_CONFIGURED",
        )

    bot_payload = {
        "upload_ids": sanitized["upload_ids"],
        "consent": True,
        "display_name": sanitized["display_name"],
        "idempotency_key": idempotency_key,
    }

    req_id = request_id or f"vc_prep_{idempotency_key}"
    res = await bridge_request(
        "POST",
        "/internal/v1/web-voice-clone/jobs",
        payload=bot_payload,
        request_id=req_id,
        actor_id=canonical_user_id,
        owner_id=canonical_user_id,
    )

    if not isinstance(res, dict):
        raise HTTPException(status_code=502, detail="Phản hồi không hợp lệ từ Core Bridge")

    if not res.get("ok"):
        error_code = str(res.get("error_code") or "")
        msg = str(res.get("message") or "Lỗi khi chuẩn bị tác vụ Voice Clone")

        if error_code in ("FORBIDDEN_CROSS_OWNER", "CORE_BRIDGE_FORBIDDEN") or "Cross-owner" in msg:
            raise HTTPException(status_code=403, detail="Tệp tải lên không thuộc quyền sở hữu của bạn")
        if error_code in ("UPLOAD_REQUIRED", "SINGLE_UPLOAD_REQUIRED", "VOICE_CLONE_CONSENT_REQUIRED"):
            raise HTTPException(status_code=400, detail=msg)
        if error_code == "IDEMPOTENCY_CONFLICT":
            raise HTTPException(status_code=409, detail=msg)

        # Pass through error envelope safely
        return envelope(
            False,
            msg,
            status_name=str(res.get("status") or "failed"),
            error_code=error_code or "VOICE_CLONE_PREPARE_FAILED",
        )

    raw_job = res.get("data") if isinstance(res.get("data"), dict) and res.get("data") else res
    safe_job = to_web_safe_voice_clone_job(raw_job)
    return safe_job


async def get_voice_clone_job(
    *,
    job_id: str,
    account: dict[str, Any],
) -> dict[str, Any] | None:
    """Retrieve owner-bound Voice Clone job detail from Bot Core.

    Tenant isolation is enforced: callers only see their own jobs.
    """
    clean_job_id = str(job_id or "").strip()
    if not clean_job_id:
        return None

    canonical_user_id = str(account.get("canonical_user_id") or "").strip()
    if not canonical_user_id:
        raise HTTPException(
            status_code=409,
            detail="Hãy liên kết Telegram trước khi truy cập dữ liệu Voice Clone",
        )

    if not bridge_configured():
        return None

    res = await bridge_request(
        "GET",
        f"/internal/v1/web-voice-clone/jobs/{clean_job_id}",
        actor_id=canonical_user_id,
        owner_id=canonical_user_id,
    )

    if not isinstance(res, dict) or not res.get("ok"):
        error_code = str((res or {}).get("error_code") or "")
        if error_code == "CORE_BRIDGE_FORBIDDEN":
            raise HTTPException(status_code=403, detail="Không có quyền truy cập job của tài khoản khác")
        return None

    raw_job = res.get("data") if isinstance(res.get("data"), dict) and res.get("data") else res
    return to_web_safe_voice_clone_job(raw_job)


async def confirm_voice_clone_job(
    *,
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Fail-closed confirm handler for Voice Clone jobs.

    In R24B4, external provider calls are strictly disabled.
    When the runtime execution gate is off, this route fails closed without calling Bot.
    """
    clean_job_id = str(job_id or "").strip()
    if not clean_job_id:
        raise HTTPException(status_code=400, detail="Mã job không được để trống")

    # Invariant: FAIL CLOSED. No live provider call or balance debit in R24B4.
    if not VOICE_CLONE_PROVIDER_EXECUTION_ENABLED:
        return envelope(
            False,
            "Tính năng Voice Clone đang trong chế độ an toàn (Incident Hold). Chưa thực thi live và chưa trừ Xu.",
            status_name="guarded",
            error_code="WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED",
            data={
                "job_id": clean_job_id,
                "incident_hold": VOICE_CLONE_EXTERNAL_PROVIDER_INCIDENT_HOLD,
                "provider_called": False,
                "wallet_mutated": False,
            },
        )

    canonical_user_id = str(account.get("canonical_user_id") or "").strip()
    if not canonical_user_id:
        raise HTTPException(status_code=409, detail="Hãy liên kết Telegram trước khi xác nhận job")

    res = await bridge_request(
        "POST",
        f"/internal/v1/web-voice-clone/jobs/{clean_job_id}/confirm",
        actor_id=canonical_user_id,
        owner_id=canonical_user_id,
    )
    if not isinstance(res, dict):
        raise HTTPException(status_code=502, detail="Phản hồi không hợp lệ từ Core Bridge")

    raw_job = res.get("data") if isinstance(res.get("data"), dict) and res.get("data") else res
    return to_web_safe_voice_clone_job(raw_job)


async def reconcile_voice_clone_job_status(
    *,
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any] | None:
    """Reconcile Voice Clone job status via Bot Core private bridge."""
    clean_job_id = str(job_id or "").strip()
    if not clean_job_id:
        return None

    canonical_user_id = str(account.get("canonical_user_id") or "").strip()
    if not canonical_user_id:
        raise HTTPException(status_code=409, detail="Hãy liên kết Telegram trước khi reconcile job")

    if not bridge_configured():
        return None

    res = await bridge_request(
        "POST",
        f"/internal/v1/web-voice-clone/jobs/{clean_job_id}/reconcile",
        actor_id=canonical_user_id,
        owner_id=canonical_user_id,
    )
    if not isinstance(res, dict) or not res.get("ok"):
        return None

    raw_job = res.get("data") if isinstance(res.get("data"), dict) and res.get("data") else res
    return to_web_safe_voice_clone_job(raw_job)
