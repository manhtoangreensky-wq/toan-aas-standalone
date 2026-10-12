"""Music SFX Canonical Job Bridge Adapter.

Task: WEBAPP_R24B3_MUSIC_SFX_VISIBLE_JOB_BRIDGE_AND_AUDIO_RESULT_RETENTION_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Product Family: MUSIC
Product: MUSIC_SFX
Customer Entrypoint: /music/sfx
Web API Family: /api/v1/features/music_sfx/*

Connects the Web customer flow (/music/sfx) to a durable, owner-scoped
canonical job bridge and audio result-retention contract without executing real
paid provider calls, background subprocesses, or wallet mutations.

Invariants:
- Fail-Closed Admission: zero provider calls until explicit Owner spend/entitlement authorization.
- Truthful Initial Status: status='queued', status_reason='AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE'.
- Audio Result Safety: finalized output must exist in web_asset_files, be active, owned by the job owner,
  and match supported audio formats (.mp3, .wav, .m4a, .ogg) and MIME types.
- Tenant Isolation: cross-account job and asset access is strictly rejected (403 Forbidden).
- Replay Idempotency: exact payload replayed safely; modified payload on same key raises HTTP 409 Conflict.
- Provider Neutrality: initial provider_name, provider_task_id, model_name, and xu_cost are NULL/None.
  Unknown pricing is NEVER encoded as zero.
- No Fabricated Identity: finalizer retains neutral provider metadata unless real execution provides it.
- Secret Sanitization: external metadata is recursively sanitized to prevent secret/token leakage.
- Dispatch Disabled: MUSIC_SFX_PROVIDER_DISPATCH_ENABLED remains False.
- SFX Library Separation: Freesound library search remains strictly separate from generative SFX jobs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
from typing import Any
import uuid

from fastapi import HTTPException
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now

# ─── CANONICAL CONSTANTS ─────────────────────────────────────────────────────

CANONICAL_PRODUCT_KEY = "music_sfx"
CANONICAL_ROUTING_KEY = "music_sfx"
CANONICAL_ROUTE_ID = "music_sfx_canonical_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/music/sfx"
CANONICAL_ALIAS_ENTRYPOINTS: tuple[str, ...] = ()

SUPPORTED_AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3", ".wav", ".m4a", ".ogg",
})
SAFE_AUDIO_EXTENSIONS = SUPPORTED_AUDIO_EXTENSIONS

SUPPORTED_AUDIO_MIME_TYPES: frozenset[str] = frozenset({
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/ogg",
    "application/ogg",
})

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE"
STATUS_REASON_COMPLETED = "COMPLETED"

# External provider dispatch flags — strictly disabled in R24B3
MUSIC_SFX_PROVIDER_DISPATCH_ENABLED: bool = False
ELEVENLABS_PUBLIC_ENABLED: bool = False

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providername", "providerid", "providertaskid", "providerjobid",
    "model", "modelname", "tier", "qualitytier", "quotexu", "chargedxu", "xu", "xucost",
    "xucharge", "fee", "credits", "wallet",
    "apikey", "apitoken", "token", "secret", "jobid", "jobstatus", "status", "statusreason",
    "output", "outputurl", "assetid", "downloadurl", "role", "balance", "filepath", "localpath",
    "accountid", "userid", "canonicaluserid",
})

UNPROVEN_SFX_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "durationseconds", "duration", "loop", "category",
    "sfxbrief", "prompt",
})

UNSAFE_URL_PREFIXES = ("javascript:", "data:", "file:", "http://127.0.0.1", "http://localhost", "http://0.0.0.0")

SENSITIVE_KEY_SUBSTRINGS: tuple[str, ...] = (
    "api_key", "apikey", "token", "authorization", "secret",
    "credential", "cookie", "password", "signed_url_secret", "session",
)


def sanitize_external_metadata(meta: Any) -> Any:
    """Recursively sanitizes and strips sensitive secret fields from metadata."""
    if isinstance(meta, dict):
        clean = {}
        for k, v in meta.items():
            norm_k = "".join(ch for ch in str(k or "").lower() if ch.isalnum() or ch == "_")
            if any(sub in norm_k for sub in SENSITIVE_KEY_SUBSTRINGS):
                continue
            clean[k] = sanitize_external_metadata(v)
        return clean
    if isinstance(meta, (list, tuple)):
        return [sanitize_external_metadata(item) for item in meta]
    return meta


def _contains_authority_field(value: Any) -> bool:
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


def _contains_unproven_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(ch for ch in str(key or "").lower() if ch.isalnum())
            if normalized in UNPROVEN_SFX_FIELDS_NORMALIZED:
                return True
            if _contains_unproven_field(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_unproven_field(child) for child in value)
    return False


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest() if key.strip() else ""


def _validate_safe_url(url: str | None) -> bool:
    if not url:
        return True
    clean = str(url).strip().lower()
    return not any(clean.startswith(prefix) for prefix in UNSAFE_URL_PREFIXES)


def ensure_music_sfx_schema() -> None:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_music_sfx_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'music_sfx',
                routing_product_key TEXT NOT NULL DEFAULT 'music_sfx',
                brief TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                status_reason TEXT NOT NULL DEFAULT 'AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope TEXT NOT NULL,
                provider_name TEXT,
                provider_task_id TEXT,
                model_name TEXT,
                xu_cost INTEGER DEFAULT NULL,
                output_asset_id TEXT,
                output_url TEXT,
                output_metadata TEXT,
                cost_metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_music_sfx_jobs_account_created "
            "ON web_music_sfx_jobs(account_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_music_sfx_jobs_request "
            "ON web_music_sfx_jobs(request_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_music_sfx_jobs_account_idempotency "
            "ON web_music_sfx_jobs(account_id, idempotency_key_hash)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_music_sfx_jobs_status_created "
            "ON web_music_sfx_jobs(status, created_at ASC)"
        )


PERMITTED_TOP_LEVEL_KEYS: frozenset[str] = frozenset({
    "input", "feature", "brief", "request_id", "idempotency_key",
})

PERMITTED_INPUT_KEYS: frozenset[str] = frozenset({
    "brief", "request_id", "idempotency_key", "feature",
})


def validate_music_sfx_input(
    account_id: str,
    payload: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    """Strictly validates incoming customer payload for Music SFX.

    Enforces:
    - Signed account
    - Canonical brief-only customer semantic contract
    - Rejection of unproven SFX semantics (duration_seconds, loop, category, sfx_brief, prompt)
    - Rejection of client authority injection (provider, model, tier, xu, status, wallet, etc.)
    - Bounded inputs (1-2000 chars)
    """
    if not account_id or not str(account_id).strip():
        return False, "Yêu cầu đăng nhập tài khoản Web hợp lệ.", {}

    if not isinstance(payload, dict):
        return False, "Dữ liệu yêu cầu phải là JSON object.", {}

    if _contains_authority_field(payload):
        return False, "Yêu cầu chứa trường quyền hạn máy chủ bị cấm (authority fields).", {}

    if _contains_unproven_field(payload):
        return False, "Yêu cầu chứa trường ngữ nghĩa SFX chưa được chứng minh (unproven SFX semantic field). Chỉ chấp nhận 'brief'.", {}

    for k in payload.keys():
        if k not in PERMITTED_TOP_LEVEL_KEYS:
            return False, f"Trường dữ liệu không hợp lệ ở cấp cao nhất: '{k}'.", {}

    # Extract input values (supports payload or nested under 'input')
    inner = payload.get("input") if isinstance(payload.get("input"), dict) else payload

    if _contains_authority_field(inner):
        return False, "Yêu cầu chứa trường quyền hạn máy chủ bị cấm trong khối input.", {}

    if _contains_unproven_field(inner):
        return False, "Yêu cầu chứa trường ngữ nghĩa SFX chưa được chứng minh trong khối input. Chỉ chấp nhận 'brief'.", {}

    for k in inner.keys():
        if k not in PERMITTED_INPUT_KEYS:
            return False, f"Trường dữ liệu không hợp lệ hoặc chưa được chứng minh cho Music SFX: '{k}'. Chỉ chấp nhận 'brief'.", {}

    # Canonical brief ONLY — aliases sfx_brief and prompt are explicitly rejected above
    raw_brief = inner.get("brief")
    if raw_brief is None or not str(raw_brief).strip():
        return False, "Thiếu mô tả brief hiệu ứng âm thanh (brief).", {}

    brief = str(raw_brief).strip()
    if len(brief) > 2000:
        return False, "Brief hiệu ứng âm thanh vượt quá độ dài tối đa 2000 ký tự.", {}

    clean_data: dict[str, Any] = {
        "brief": brief,
    }

    return True, "", clean_data


def create_or_replay_music_sfx_job(
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Creates a fail-closed, durable Music SFX job or returns an idempotent replay."""
    ensure_music_sfx_schema()
    ok, err_msg, clean_input = validate_music_sfx_input(account_id, payload)
    if not ok:
        raise HTTPException(status_code=400, detail=err_msg)

    payload_hash = _hash_payload(clean_input)
    req_id = request_id.strip() or f"req_msfx_{uuid.uuid4().hex[:16]}"
    clean_input["request_id"] = req_id
    idem_hash = _hash_key(idempotency_key)
    now = utc_now()

    with transaction() as conn:
        conn.row_factory = sqlite3.Row

        # Check existing job by idempotency key
        if idem_hash:
            existing = conn.execute(
                """
                SELECT * FROM web_music_sfx_jobs
                WHERE account_id = ? AND idempotency_key_hash = ?
                LIMIT 1;
                """,
                (account_id, idem_hash),
            ).fetchone()

            if existing:
                existing_dict = dict(existing)
                if existing_dict["payload_hash"] == payload_hash:
                    result = _format_job_dict(existing_dict)
                    result["idempotent_replay"] = True
                    return result
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột Idempotency-Key: Khóa này đã được sử dụng với nội dung yêu cầu khác.",
                )

        # Check replay by request_id
        existing_req = conn.execute(
            """
            SELECT * FROM web_music_sfx_jobs
            WHERE account_id = ? AND request_id = ?
            LIMIT 1;
            """,
            (account_id, req_id),
        ).fetchone()

        if existing_req:
            existing_dict = dict(existing_req)
            if existing_dict["payload_hash"] == payload_hash:
                result = _format_job_dict(existing_dict)
                result["idempotent_replay"] = True
                return result
            raise HTTPException(
                status_code=409,
                detail="Xung đột request_id: Mã yêu cầu này đã được sử dụng với nội dung khác.",
            )

        job_id = f"msfx_{uuid.uuid4().hex[:20]}"
        bridge_envelope = {
            "canonical_product_key": CANONICAL_PRODUCT_KEY,
            "canonical_route_id": CANONICAL_ROUTE_ID,
            "customer_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
            "created_via": "web_native_music_sfx_bridge",
            "account_id": account_id,
            "provider_calls_made": 0,
            "paid_calls_made": 0,
            "admission_status": "queued",
            "admission_reason": STATUS_REASON_AWAITING,
            "elevenlabs_public_enabled": False,
        }

        conn.execute(
            """
            INSERT INTO web_music_sfx_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                brief, status, status_reason,
                idempotency_key_hash, payload_hash, bridge_envelope,
                provider_name, provider_task_id, model_name, xu_cost,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                job_id,
                req_id,
                account_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                clean_input["brief"],
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                idem_hash if idem_hash else None,
                payload_hash,
                json.dumps(bridge_envelope, ensure_ascii=False),
                None,
                None,
                None,
                None,
                now,
                now,
            ),
        )

        row = conn.execute(
            "SELECT * FROM web_music_sfx_jobs WHERE id = ?;", (job_id,)
        ).fetchone()
        result = _format_job_dict(dict(row))
        result["idempotent_replay"] = False
        return result


def _format_job_dict(row: dict[str, Any]) -> dict[str, Any]:
    bridge_meta: dict[str, Any] = {}
    if row.get("bridge_envelope"):
        try:
            bridge_meta = json.loads(row["bridge_envelope"])
        except Exception:
            bridge_meta = {}

    out_meta = {}
    if row.get("output_metadata"):
        try:
            out_meta = json.loads(row["output_metadata"])
        except Exception:
            out_meta = {}

    cost_meta = {}
    if row.get("cost_metadata"):
        try:
            cost_meta = json.loads(row["cost_metadata"])
        except Exception:
            cost_meta = {}

    return {
        "id": row["id"],
        "job_id": row["id"],
        "request_id": row["request_id"],
        "account_id": row["account_id"],
        "product_key": row.get("product_key") or CANONICAL_PRODUCT_KEY,
        "routing_product_key": row.get("routing_product_key") or CANONICAL_ROUTING_KEY,
        "brief": row["brief"],
        "xu_cost": row.get("xu_cost"),
        "status": row["status"],
        "status_reason": row["status_reason"],
        "provider_name": row.get("provider_name"),
        "provider_task_id": row.get("provider_task_id"),
        "model_name": row.get("model_name"),
        "output_asset_id": row.get("output_asset_id"),
        "output_url": row.get("output_url"),
        "output_metadata": out_meta,
        "cost_metadata": cost_meta,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row.get("completed_at"),
        "bridge_envelope": bridge_meta,
    }


def get_music_sfx_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    ensure_music_sfx_schema()
    clean_job_id = str(job_id).strip()
    clean_account = str(account_id).strip()
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM web_music_sfx_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1;
            """,
            (clean_job_id, clean_account),
        ).fetchone()
        if not row:
            return None
        return _format_job_dict(dict(row))


def is_music_sfx_job_other_account(job_id: str, current_account_id: str) -> bool:
    ensure_music_sfx_schema()
    clean_job_id = str(job_id).strip()
    clean_current = str(current_account_id).strip()
    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT id FROM web_music_sfx_jobs
            WHERE id = ? AND account_id != ?
            LIMIT 1;
            """,
            (clean_job_id, clean_current),
        ).fetchone()
        return row is not None


def list_music_sfx_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    ensure_music_sfx_schema()
    clean_account = str(account_id).strip()
    bounded_limit = max(1, min(limit, 200))
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM web_music_sfx_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (clean_account, bounded_limit),
        ).fetchall()
        return [_format_job_dict(dict(r)) for r in rows]


def music_sfx_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Projects a music_sfx job to the generic /jobs view schema."""
    job_id = job.get("id") or job.get("job_id") or ""
    status = job.get("status") or STATUS_QUEUED
    state = "QUEUED" if status == STATUS_QUEUED else ("SUCCEEDED" if status == STATUS_COMPLETED else "FAILED")
    completed = status == STATUS_COMPLETED
    output_asset_id = job.get("output_asset_id")
    output_url = job.get("output_url")

    return {
        "id": job_id,
        "job_id": job_id,
        "kind": "music_sfx",
        "product": "music_sfx",
        "product_family": "music",
        "status": status,
        "status_name": status,
        "state": state,
        "status_reason": job.get("status_reason") or STATUS_REASON_AWAITING,
        "source_state": "queued_locally" if status == STATUS_QUEUED else status,
        "created_at": job.get("created_at") or "",
        "updated_at": job.get("updated_at") or "",
        "completed_at": job.get("completed_at"),
        "account_id": job.get("account_id") or "",
        "brief": job.get("brief") or "",
        "xu_cost": job.get("xu_cost"),
        "provider_name": job.get("provider_name"),
        "provider_task_id": job.get("provider_task_id"),
        "model_name": job.get("model_name"),
        "output_asset_id": output_asset_id,
        "output_url": output_url,
        "output_available": completed and bool(output_asset_id),
        "download_ready": completed and bool(output_asset_id),
        "delivery_ready": completed and bool(output_asset_id),
        "runtime_execution_active": False,
        "attention_required": False,
        "source_system": "web_native_music_sfx",
    }


def list_admin_music_sfx_jobs(limit: int = 100) -> list[dict[str, Any]]:
    ensure_music_sfx_schema()
    bounded_limit = max(1, min(limit, 500))
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM web_music_sfx_jobs
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (bounded_limit,),
        ).fetchall()
        return [_format_job_dict(dict(r)) for r in rows]


def get_admin_music_sfx_job(job_id: str) -> dict[str, Any] | None:
    ensure_music_sfx_schema()
    clean_job_id = str(job_id).strip()
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM web_music_sfx_jobs
            WHERE id = ?
            LIMIT 1;
            """,
            (clean_job_id,),
        ).fetchone()
        if not row:
            return None
        return _format_job_dict(dict(row))


def dispatch_music_sfx_provider(job_id: str, payload: dict[str, Any] | None = None) -> None:
    """Fail-closed provider dispatch boundary.

    Raises RuntimeError because provider dispatch is strictly disabled in R24B3.
    """
    if not MUSIC_SFX_PROVIDER_DISPATCH_ENABLED:
        raise RuntimeError(
            "MUSIC_SFX_PROVIDER_DISPATCH_DISABLED: Điều phối dịch vụ SFX bên ngoài hiện bị khóa an toàn (R24B3)."
        )
    raise NotImplementedError("Provider dispatch not implemented for music_sfx.")


def finalize_music_sfx_job_result(
    job_id: str,
    output_asset_id: str,
    provider_name: str | None = None,
    provider_task_id: str | None = None,
    model_name: str | None = None,
    output_metadata: dict[str, Any] | None = None,
    cost_metadata: dict[str, Any] | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Finalizes a music_sfx job result with strict audio Asset Vault verification.

    Enforces:
    - Job exists
    - Output asset exists in web_asset_files
    - Output asset belongs to the same owner (tenant isolation)
    - Output asset is active
    - Output asset format and MIME type match supported audio allowlist (.mp3, .wav, .m4a, .ogg)
    - Omitted provider/model fields remain None (no fabricated defaults)
    - Sanitizes metadata to strip sensitive credentials
    """
    ensure_music_sfx_schema()
    clean_job_id = str(job_id).strip()
    clean_asset_id = str(output_asset_id).strip()

    if not clean_job_id:
        raise HTTPException(status_code=400, detail="Thiếu mã tác vụ SFX (job_id).")
    if not clean_asset_id:
        raise HTTPException(status_code=400, detail="Thiếu mã tài sản kết quả (output_asset_id).")

    with transaction() as conn:
        conn.row_factory = sqlite3.Row

        job_row = conn.execute(
            "SELECT * FROM web_music_sfx_jobs WHERE id = ? LIMIT 1;",
            (clean_job_id,),
        ).fetchone()
        if not job_row:
            raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ SFX.")

        job_dict = dict(job_row)
        owner_id = job_dict["account_id"]

        asset_row = conn.execute(
            """
            SELECT * FROM web_asset_files
            WHERE id = ?
            LIMIT 1;
            """,
            (clean_asset_id,),
        ).fetchone()

        if not asset_row:
            raise HTTPException(
                status_code=404,
                detail="Tài sản kết quả âm thanh không tồn tại trong Asset Vault.",
            )

        asset_dict = dict(asset_row)

        # Cross-owner verification
        if asset_dict.get("account_id") != owner_id:
            raise HTTPException(
                status_code=403,
                detail="Tài sản kết quả âm thanh không thuộc sở hữu của chủ tác vụ (vi phạm cách ly tài khoản).",
            )

        # Active state verification
        if asset_dict.get("state") != "active":
            raise HTTPException(
                status_code=400,
                detail="Tài sản kết quả âm thanh chưa ở trạng thái active hợp lệ.",
            )

        # Audio format verification
        out_ext = str(asset_dict.get("extension") or "").strip().lower()
        out_orig = str(asset_dict.get("original_filename") or "").strip().lower()
        if not out_ext and "." in out_orig:
            out_ext = ("." + out_orig.rsplit(".", 1)[-1].lower())
        out_mime = str(asset_dict.get("content_type") or "").strip().lower()

        if out_ext not in SUPPORTED_AUDIO_EXTENSIONS:
            valid_exts = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng tệp âm thanh kết quả không được hỗ trợ. Chỉ chấp nhận: {valid_exts}.",
            )
        if out_mime and out_mime not in SUPPORTED_AUDIO_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail="MIME type của tệp âm thanh kết quả không được hỗ trợ. Chỉ chấp nhận audio/mpeg, audio/wav, audio/mp4, audio/ogg.",
            )

        now = completed_at or utc_now()

        # Provider authority neutrality: do not fabricate fallback provider/model
        resolved_provider = (str(provider_name).strip() if provider_name and str(provider_name).strip() else None) or job_dict.get("provider_name")
        resolved_model = (str(model_name).strip() if model_name and str(model_name).strip() else None) or job_dict.get("model_name")
        resolved_task_id = (str(provider_task_id).strip() if provider_task_id and str(provider_task_id).strip() else None) or job_dict.get("provider_task_id")

        output_url = f"/api/v1/assets/{clean_asset_id}/download"
        if not _validate_safe_url(output_url):
            raise HTTPException(status_code=400, detail="Đường dẫn kết quả không an toàn.")

        # Sanitize metadata against secret leakage
        clean_out_meta = sanitize_external_metadata(output_metadata or {})
        clean_cost_meta = sanitize_external_metadata(cost_metadata or {})

        conn.execute(
            """
            UPDATE web_music_sfx_jobs
            SET status = ?,
                status_reason = ?,
                provider_task_id = ?,
                provider_name = ?,
                model_name = ?,
                output_asset_id = ?,
                output_url = ?,
                output_metadata = ?,
                cost_metadata = ?,
                completed_at = ?,
                updated_at = ?
            WHERE id = ?;
            """,
            (
                STATUS_COMPLETED,
                STATUS_REASON_COMPLETED,
                resolved_task_id,
                resolved_provider,
                resolved_model,
                clean_asset_id,
                output_url,
                json.dumps(clean_out_meta, ensure_ascii=False),
                json.dumps(clean_cost_meta, ensure_ascii=False),
                now,
                now,
                clean_job_id,
            ),
        )

        updated_row = conn.execute(
            "SELECT * FROM web_music_sfx_jobs WHERE id = ?;", (clean_job_id,)
        ).fetchone()
        return _format_job_dict(dict(updated_row))
