"""Image Upscale Canonical Job Bridge Adapter.

Task: WEBAPP_R24B1_IMAGE_UPSCALE_VISIBLE_JOB_BRIDGE_AND_RESULT_RETENTION_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: image_upscale
Customer Entrypoint: /image/upscale
Web API Family: /api/v1/features/image_upscale/*

Connects the Web customer flow (/image/upscale) to a durable, owner-scoped
canonical job bridge and result-retention contract without executing real paid
provider calls, background subprocesses, or wallet mutations.

Invariants:
- Fail-Closed Admission: zero provider calls until explicit Owner spend authorization.
- Truthful Initial Status: status='queued', status_reason='AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE'.
- Asset Vault Ownership: source image must exist in web_asset_files and be owned by the authenticated Web account.
- Cross-Owner Isolation: cross-account asset access is rejected.
- Idempotency & Conflict: exact replay returns existing job with `idempotent_replay=True`;
  differing payload on the same idempotency key raises HTTP 409 Conflict.
- Result Retention: finalized output persists into canonical Asset Vault with owner scoping
  and safe download/preview paths.
- Provider Dispatch Disabled: dispatch boundary exists but throws RuntimeError if invoked in R24B1.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
import sqlite3
from typing import Any
import uuid

from fastapi import HTTPException
from copyfast_assets import _private_asset_vault_child_directory, _storage_path
from copyfast_db import asset_vault_directory, ensure_copyfast_schema, read_transaction, transaction, utc_now
from copyfast_image_upscale_provider import (
    DEFAULT_CREATIVITY,
    DEFAULT_UPSCALE_PROMPT,
    MISSING_PROVIDER_CREDENTIAL_BEHAVIOR,
    PRODUCTION_FAKE_API_KEY_FALLBACK,
    STABILITY_UPSCALE_CAPABILITY_ID,
    STABILITY_UPSCALE_ENDPOINT,
    STABILITY_UPSCALE_MODEL_NAME,
    STABILITY_UPSCALE_PROVIDER_KEY,
    STABILITY_UPSCALE_PROVIDER_NAME,
    SYNTHETIC_PROVIDER_TASK_ID_ALLOWED,
    ImageUpscaleProviderError,
    ImageUpscaleProviderRequest,
    ImageUpscaleProviderResponseError,
    ImageUpscaleProviderResult,
    ImageUpscaleTransportProtocol,
    build_stability_upscale_request_payload,
    parse_stability_upscale_response,
)

# ─── CANONICAL CONSTANTS ─────────────────────────────────────────────────────

CANONICAL_PRODUCT_KEY = "image_upscale"
CANONICAL_ROUTING_KEY = "image_upscale"
CANONICAL_ROUTE_ID = "image_upscale_canonical_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/image/upscale"

SAFE_IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp",
})

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE"
STATUS_REASON_COMPLETED = "COMPLETED"

SUPPORTED_SCALE_FACTORS: frozenset[int] = frozenset({2, 4})
DEFAULT_SCALE_FACTOR = 2

SUPPORTED_MODELS: frozenset[str] = frozenset({
    "replicate_real_esrgan",
    "stability_conservative",
})
DEFAULT_MODEL = "replicate_real_esrgan"

# Dispatch & Blocker Constants (R24E1)
BLOCKER_PROVIDER_EXECUTOR_READY_BUT_DISPATCH_DISABLED: str = "PROVIDER_EXECUTOR_READY_BUT_DISPATCH_DISABLED"
BLOCKER_PROVIDER_ENTITLEMENT_UNPROVEN: str = "PROVIDER_ENTITLEMENT_UNPROVEN"
BLOCKER_OWNER_PAID_AUTHORIZATION_REQUIRED: str = "OWNER_PAID_AUTHORIZATION_REQUIRED"
BLOCKER_PROVIDER_CONTRACT_UNPROVEN: str = "PROVIDER_CONTRACT_UNPROVEN"

# Structural Truth Declarations (R24E1 & R24E1-FIX1)
IMAGE_UPSCALE_PROVIDER_EXECUTOR_IMPLEMENTED: bool = True
IMAGE_UPSCALE_PROVIDER_DISPATCH_ENABLED: bool = False
IMAGE_UPSCALE_PROVIDER_DISPATCH_CURRENTLY_ENABLED: bool = False
REPLICATE_REAL_ESRGAN_DISPATCH_AUTHORIZED: bool = False
STABILITY_UPSCALE_DISPATCH_AUTHORIZED: bool = False
STABILITY_UPSCALE_ENTITLEMENT_PROVEN: bool = False
OWNER_PAID_AUTHORIZATION_GRANTED: bool = False
DIRECT_OWNER_AUTHORIZATION_TO_LIVE_TEST_POSSIBLE: bool = False

# Security & Authority Boundaries (R24E1-FIX1)
ARBITRARY_TRANSPORT_OBJECT_IS_AUTHORITY: bool = False
DIRECT_TRANSPORT_GATE_BYPASS: bool = False

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "apikey", "apitoken", "token",
    "secret", "jobid", "jobstatus", "status", "statusreason", "output", "outputurl",
    "assetid", "downloadurl", "role", "balance", "xu", "wallet",
})

UNSAFE_URL_PREFIXES = ("javascript:", "data:", "file:", "http://127.0.0.1", "http://localhost", "http://0.0.0.0")


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


def ensure_image_upscale_schema() -> None:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_upscale_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'image_upscale',
                routing_product_key TEXT NOT NULL DEFAULT 'image_upscale',
                image_asset_id TEXT NOT NULL,
                image_name TEXT NOT NULL,
                scale_factor INTEGER NOT NULL DEFAULT 2,
                model_name TEXT NOT NULL DEFAULT 'replicate_real_esrgan',
                xu_cost INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'queued',
                status_reason TEXT NOT NULL DEFAULT 'AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope TEXT NOT NULL,
                provider_name TEXT,
                provider_task_id TEXT,
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
            "CREATE INDEX IF NOT EXISTS idx_web_img_upscale_jobs_account_created "
            "ON web_image_upscale_jobs(account_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_upscale_jobs_request "
            "ON web_image_upscale_jobs(request_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_upscale_jobs_account_idempotency "
            "ON web_image_upscale_jobs(account_id, idempotency_key_hash)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_upscale_jobs_status_created "
            "ON web_image_upscale_jobs(status, created_at ASC)"
        )


def validate_image_upscale_input(
    account_id: str,
    payload: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return False, "Payload phải là JSON object.", {}

    if _contains_authority_field(payload):
        return False, "Payload chứa trường không được phép (authority field injection).", {}

    asset_id = str(payload.get("image_asset_id") or payload.get("asset_id") or "").strip()
    if not asset_id:
        return False, "Thiếu mã tài sản ảnh (image_asset_id).", {}

    # Scale factor validation
    scale_raw = payload.get("scale_factor") or payload.get("scale") or DEFAULT_SCALE_FACTOR
    try:
        scale_factor = int(scale_raw)
    except (ValueError, TypeError):
        scale_factor = DEFAULT_SCALE_FACTOR
    if scale_factor not in SUPPORTED_SCALE_FACTORS:
        valid_scales = ", ".join(str(s) for s in sorted(SUPPORTED_SCALE_FACTORS))
        return False, f"Hệ số phóng đại không hợp lệ: {scale_factor}. Hỗ trợ: {valid_scales}.", {}

    # Model validation
    model = str(payload.get("model_name") or payload.get("model") or DEFAULT_MODEL).strip().lower()
    if model not in SUPPORTED_MODELS:
        valid_models = ", ".join(sorted(SUPPORTED_MODELS))
        return False, f"Mô hình upscale không hợp lệ: '{model}'. Hỗ trợ: {valid_models}.", {}

    # Verify asset exists, is owned by account_id, and is an image
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, original_filename, extension, content_type, byte_size, state
            FROM web_asset_files
            WHERE id = ? AND account_id = ?
            LIMIT 1;
            """,
            (asset_id, account_id),
        ).fetchone()

    if not row:
        return False, "Không tìm thấy tài sản ảnh trong Asset Vault hoặc bạn không có quyền truy cập.", {}

    asset_dict = dict(row)
    if asset_dict.get("state") != "active":
        return False, "Tài sản ảnh không ở trạng thái sẵn sàng (active).", {}

    orig_name = str(asset_dict.get("original_filename") or "").strip()
    ext = str(asset_dict.get("extension") or "").strip().lower()
    if not ext and "." in orig_name:
        ext = ("." + orig_name.rsplit(".", 1)[-1].lower())
    mime = str(asset_dict.get("content_type") or "").strip().lower()

    is_image = (ext in SAFE_IMAGE_EXTENSIONS) or mime.startswith("image/")
    if not is_image:
        valid_exts = ", ".join(sorted(SAFE_IMAGE_EXTENSIONS))
        return False, f"Định dạng tệp không được hỗ trợ để upscale. Hỗ trợ: {valid_exts}.", {}

    clean_payload = {
        "image_asset_id": asset_id,
        "image_name": orig_name,
        "scale_factor": scale_factor,
        "model_name": model,
        "xu_cost": 0,
    }
    return True, "", clean_payload


def _format_job_dict(row: dict[str, Any]) -> dict[str, Any]:
    bridge_envelope = {}
    if row.get("bridge_envelope"):
        try:
            bridge_envelope = json.loads(row["bridge_envelope"])
        except Exception:
            pass

    output_meta = {}
    if row.get("output_metadata"):
        try:
            output_meta = json.loads(row["output_metadata"])
        except Exception:
            pass

    cost_meta = {}
    if row.get("cost_metadata"):
        try:
            cost_meta = json.loads(row["cost_metadata"])
        except Exception:
            pass

    is_completed = row.get("status") == STATUS_COMPLETED
    output_asset_id = row.get("output_asset_id")

    return {
        "id": row.get("id"),
        "job_id": row.get("id"),
        "request_id": row.get("request_id"),
        "account_id": row.get("account_id"),
        "product_key": row.get("product_key") or CANONICAL_PRODUCT_KEY,
        "routing_product_key": row.get("routing_product_key") or CANONICAL_ROUTING_KEY,
        "customer_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
        "image_asset_id": row.get("image_asset_id"),
        "image_name": row.get("image_name"),
        "scale_factor": row.get("scale_factor", DEFAULT_SCALE_FACTOR),
        "model_name": row.get("model_name") or DEFAULT_MODEL,
        "xu_cost": row.get("xu_cost", 0),
        "status": row.get("status"),
        "status_reason": row.get("status_reason"),
        "provider_name": row.get("provider_name"),
        "provider_task_id": row.get("provider_task_id"),
        "output_available": is_completed and bool(output_asset_id),
        "output_asset_id": output_asset_id,
        "output_url": row.get("output_url"),
        "preview_url": f"/api/v1/assets/{output_asset_id}/preview" if output_asset_id else None,
        "download_url": f"/api/v1/assets/{output_asset_id}/download" if output_asset_id else None,
        "output_metadata": output_meta,
        "cost_metadata": cost_meta,
        "bridge_envelope": bridge_envelope,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "completed_at": row.get("completed_at"),
    }


def create_or_replay_image_upscale_job(
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    ensure_image_upscale_schema()

    is_valid, err_msg, clean_payload = validate_image_upscale_input(account_id, payload)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    req_id = request_id.strip() or str(uuid.uuid4())
    idempotency_hash = _hash_key(idempotency_key)
    current_payload_hash = _hash_payload(clean_payload)

    with transaction() as conn:
        conn.row_factory = sqlite3.Row

        # Check idempotency replay by idempotency key
        if idempotency_hash:
            existing = conn.execute(
                """
                SELECT * FROM web_image_upscale_jobs
                WHERE account_id = ? AND idempotency_key_hash = ?
                LIMIT 1;
                """,
                (account_id, idempotency_hash),
            ).fetchone()

            if existing:
                row_dict = dict(existing)
                if not hmac.compare_digest(row_dict.get("payload_hash", ""), current_payload_hash):
                    raise HTTPException(
                        status_code=409,
                        detail="Xung đột Idempotency-Key: payload khác với yêu cầu trước đó.",
                    )
                res = _format_job_dict(row_dict)
                res["idempotent_replay"] = True
                return res

        # Check replay by request_id
        existing_req = conn.execute(
            """
            SELECT * FROM web_image_upscale_jobs
            WHERE request_id = ?
            LIMIT 1;
            """,
            (req_id,),
        ).fetchone()

        if existing_req:
            row_dict = dict(existing_req)
            if row_dict.get("account_id") != account_id:
                raise HTTPException(status_code=403, detail="Không có quyền truy cập job của tài khoản khác.")
            if not hmac.compare_digest(row_dict.get("payload_hash", ""), current_payload_hash):
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột request_id: payload khác với yêu cầu trước đó.",
                )
            res = _format_job_dict(row_dict)
            res["idempotent_replay"] = True
            return res

        now = utc_now()
        job_id = f"upscale_{uuid.uuid4().hex[:16]}"
        envelope_data = {
            "route_id": CANONICAL_ROUTE_ID,
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_key": CANONICAL_ROUTING_KEY,
            "customer_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
            "request_id": req_id,
            "account_id": account_id,
            "image_asset_id": clean_payload["image_asset_id"],
            "image_name": clean_payload["image_name"],
            "scale_factor": clean_payload["scale_factor"],
            "model_name": clean_payload["model_name"],
            "xu_cost": clean_payload["xu_cost"],
            "created_at": now,
        }

        conn.execute(
            """
            INSERT INTO web_image_upscale_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                image_asset_id, image_name, scale_factor, model_name, xu_cost,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?
            );
            """,
            (
                job_id,
                req_id,
                account_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                clean_payload["image_asset_id"],
                clean_payload["image_name"],
                clean_payload["scale_factor"],
                clean_payload["model_name"],
                clean_payload["xu_cost"],
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                idempotency_hash if idempotency_hash else None,
                current_payload_hash,
                json.dumps(envelope_data, ensure_ascii=False),
                now,
                now,
            ),
        )

        row = conn.execute(
            "SELECT * FROM web_image_upscale_jobs WHERE id = ?;", (job_id,)
        ).fetchone()

    res = _format_job_dict(dict(row))
    res["idempotent_replay"] = False
    return res


def get_image_upscale_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    ensure_image_upscale_schema()
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM web_image_upscale_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1;
            """,
            (job_id, account_id),
        ).fetchone()
    if not row:
        return None
    return _format_job_dict(dict(row))


def is_image_upscale_job_other_account(job_id: str, account_id: str) -> bool:
    ensure_image_upscale_schema()
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT account_id FROM web_image_upscale_jobs WHERE id = ? LIMIT 1;",
            (job_id,),
        ).fetchone()
    if not row:
        return False
    return str(row[0]) != str(account_id)


def list_image_upscale_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    ensure_image_upscale_schema()
    safe_limit = max(1, min(int(limit), 200))
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM web_image_upscale_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (account_id, safe_limit),
        ).fetchall()
    return [_format_job_dict(dict(r)) for r in rows]


def get_admin_image_upscale_job(job_id: str) -> dict[str, Any] | None:
    ensure_image_upscale_schema()
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM web_image_upscale_jobs
            WHERE id = ?
            LIMIT 1;
            """,
            (job_id,),
        ).fetchone()
    if not row:
        return None
    return _format_job_dict(dict(row))


def list_admin_image_upscale_jobs(limit: int = 100) -> list[dict[str, Any]]:
    ensure_image_upscale_schema()
    safe_limit = max(1, min(int(limit), 200))
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM web_image_upscale_jobs
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (safe_limit,),
        ).fetchall()
    return [_format_job_dict(dict(r)) for r in rows]


def image_upscale_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Projects an image upscale job into the generic /jobs read model format."""
    job_id = str(job.get("id") or job.get("job_id") or "")
    status = str(job.get("status") or STATUS_QUEUED)
    output_asset_id = job.get("output_asset_id")
    output_url = job.get("output_url")
    is_completed = status == STATUS_COMPLETED and bool(output_asset_id)

    return {
        "id": job_id,
        "job_id": job_id,
        "request_id": job.get("request_id"),
        "account_id": job.get("account_id"),
        "product_key": CANONICAL_PRODUCT_KEY,
        "product": CANONICAL_PRODUCT_KEY,
        "product_family": "image",
        "title": f"Upscale: {job.get('image_name') or 'Ảnh'} ({job.get('scale_factor', 2)}x)",
        "kind": "image_upscale",
        "status": status,
        "status_reason": job.get("status_reason") or STATUS_REASON_AWAITING,
        "provider_name": job.get("provider_name"),
        "model_name": job.get("model_name"),
        "output_available": is_completed,
        "output_asset_id": output_asset_id,
        "output_url": output_url,
        "preview_url": job.get("preview_url"),
        "download_url": job.get("download_url"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "completed_at": job.get("completed_at"),
        "source": "web_native_image_upscale",
    }


def finalize_image_upscale_job_result(
    job_id: str,
    *,
    provider_task_id: str = "",
    provider_name: str = "",
    model_name: str = "",
    output_asset_id: str = "",
    output_metadata: dict[str, Any] | None = None,
    cost_metadata: dict[str, Any] | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Finalizes an image upscale job by attaching a verified, owner-scoped Asset Vault item.

    This function is called by the future authorized provider worker.
    It enforces:
    1. The job exists.
    2. The output_asset_id exists in web_asset_files and belongs to the SAME account.
    3. Rejects any unsafe URL scheme (SSRF prevention).
    4. Updates job status to 'completed' with canonical download/preview paths.
    """
    ensure_image_upscale_schema()
    clean_job_id = str(job_id).strip()
    clean_asset_id = str(output_asset_id).strip()

    if not clean_job_id:
        raise ValueError("Thiếu mã job (job_id).")
    if not clean_asset_id:
        raise ValueError("Thiếu mã tài sản kết quả (output_asset_id).")

    with transaction() as conn:
        conn.row_factory = sqlite3.Row
        job_row = conn.execute(
            "SELECT * FROM web_image_upscale_jobs WHERE id = ? LIMIT 1;",
            (clean_job_id,),
        ).fetchone()

        if not job_row:
            raise HTTPException(status_code=404, detail="Không tìm thấy job Image Upscale.")

        job_dict = dict(job_row)
        account_id = str(job_dict["account_id"])

        # Verify output asset exists and is owned by the SAME account
        asset_row = conn.execute(
            """
            SELECT id, original_filename, extension, content_type, byte_size, state
            FROM web_asset_files
            WHERE id = ? AND account_id = ?
            LIMIT 1;
            """,
            (clean_asset_id, account_id),
        ).fetchone()

        if not asset_row:
            raise HTTPException(
                status_code=403,
                detail="Tài sản kết quả không tồn tại hoặc không thuộc tài khoản của tác vụ (cross-owner violation).",
            )

        asset_dict = dict(asset_row)
        if asset_dict.get("state") != "active":
            raise HTTPException(status_code=400, detail="Tài sản kết quả không ở trạng thái sẵn sàng (active).")

        now = completed_at or utc_now()
        resolved_model = model_name or job_dict.get("model_name") or DEFAULT_MODEL
        resolved_provider = provider_name or "replicate"
        output_url = f"/api/v1/assets/{clean_asset_id}/download"
        clean_task_id = str(provider_task_id).strip() if provider_task_id else None

        if not _validate_safe_url(output_url):
            raise HTTPException(status_code=400, detail="Đường dẫn kết quả không an toàn.")

        conn.execute(
            """
            UPDATE web_image_upscale_jobs
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
                clean_task_id,
                resolved_provider,
                resolved_model,
                clean_asset_id,
                output_url,
                json.dumps(output_metadata or {}, ensure_ascii=False),
                json.dumps(cost_metadata or {}, ensure_ascii=False),
                now,
                now,
                clean_job_id,
            ),
        )

        updated_row = conn.execute(
            "SELECT * FROM web_image_upscale_jobs WHERE id = ?;", (clean_job_id,)
        ).fetchone()

    return _format_job_dict(dict(updated_row))


def resolve_source_asset_image(
    account_id: str,
    image_asset_id: str,
) -> tuple[bytes, str, str, str]:
    """Resolves and verifies the source image artifact from Asset Vault.

    Enforces:
    1. Asset exists in web_asset_files.
    2. Same account (cross-owner isolation).
    3. Active state.
    4. Supported image extension and MIME type.
    5. Real storage artifact exists on disk and is non-empty.
    6. Verifies digest integrity if recorded.

    Returns: (image_bytes, original_filename, extension, content_type)
    """
    clean_account_id = str(account_id).strip()
    clean_asset_id = str(image_asset_id).strip()
    if not clean_asset_id:
        raise ValueError("Thiếu mã tài sản ảnh nguồn (image_asset_id).")

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, account_id, original_filename, extension, content_type,
                   byte_size, sha256, storage_key, state
            FROM web_asset_files
            WHERE id = ?;
            """,
            (clean_asset_id,),
        ).fetchone()

    if not row:
        raise ValueError(f"Không tìm thấy tài sản ảnh nguồn: {clean_asset_id}")

    asset_dict = dict(row)
    if asset_dict.get("account_id") != clean_account_id:
        raise ValueError(
            f"Vi phạm cách ly tài khoản: tài sản {clean_asset_id} không thuộc về {clean_account_id}"
        )

    if asset_dict.get("state") != "active":
        raise ValueError(f"Tài sản ảnh {clean_asset_id} không ở trạng thái sẵn sàng (active)")

    orig_name = str(asset_dict.get("original_filename") or "image.png")
    ext = str(asset_dict.get("extension") or "").strip().lower()
    if not ext and "." in orig_name:
        ext = "." + orig_name.rsplit(".", 1)[-1].lower()
    mime = str(asset_dict.get("content_type") or "image/png").strip().lower()

    if ext not in SAFE_IMAGE_EXTENSIONS and not mime.startswith("image/"):
        raise ValueError(f"Định dạng tệp không được hỗ trợ để upscale: {ext}")

    storage_key = str(asset_dict.get("storage_key") or "")
    if not storage_key:
        raise ValueError(f"Tài sản {clean_asset_id} thiếu storage_key")

    root = asset_vault_directory()
    try:
        candidate_path = _storage_path(root, storage_key)
    except Exception as exc:
        raise ValueError(f"Đường dẫn lưu trữ không an toàn hoặc không hợp lệ: {exc}") from exc

    if not candidate_path.is_file() or candidate_path.stat().st_size == 0:
        raise ValueError(f"Tệp lưu trữ vật lý không tồn tại trên đĩa: {storage_key}")

    image_bytes = candidate_path.read_bytes()
    expected_digest = str(asset_dict.get("sha256") or "").strip()
    if expected_digest:
        actual_digest = hashlib.sha256(image_bytes).hexdigest()
        if not hmac.compare_digest(actual_digest, expected_digest):
            raise ValueError("Tính toàn vẹn của tệp nguồn không khớp (sha256 mismatch)")

    return image_bytes, orig_name, ext, mime


def store_image_upscale_output_asset(
    account_id: str,
    output_image_bytes: bytes,
    *,
    original_filename: str = "upscaled.png",
    extension: str = ".png",
    content_type: str = "image/png",
    display_name: str = "Ảnh phóng to (Upscale)",
) -> str:
    """Stores the upscaled image bytes into the canonical Asset Vault.

    Enforces:
    1. Writes to safe objects/ directory under asset_vault_directory().
    2. Hashes content with sha256.
    3. Inserts row into web_asset_files owned by account_id with state='active'.
    4. Returns output_asset_id.
    """
    if not output_image_bytes:
        raise ValueError("Dữ liệu ảnh kết quả rỗng.")

    root = asset_vault_directory()
    _private_asset_vault_child_directory(root, "objects")
    output_asset_id = str(uuid.uuid4())
    storage_key = f"objects/{uuid.uuid4().hex}.blob"
    final_path = _storage_path(root, storage_key)

    final_path.write_bytes(output_image_bytes)

    byte_size = len(output_image_bytes)
    digest = hashlib.sha256(output_image_bytes).hexdigest()
    now = utc_now()

    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, created_at, updated_at, archived_at
            ) VALUES (
                ?, ?, NULL, ?, ?,
                ?, ?, ?, ?, ?,
                'active', ?, ?, NULL
            );
            """,
            (
                output_asset_id,
                account_id,
                display_name,
                original_filename,
                extension,
                content_type,
                byte_size,
                digest,
                storage_key,
                now,
                now,
            ),
        )

    return output_asset_id


def transition_image_upscale_job_failed(job_id: str, reason: str) -> None:
    """Explicitly transitions a queued or processing job to failed."""
    now = utc_now()
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_image_upscale_jobs
            SET status = ?,
                status_reason = ?,
                updated_at = ?
            WHERE id = ? AND status IN (?, ?);
            """,
            (STATUS_FAILED, str(reason)[:500], now, job_id, STATUS_QUEUED, STATUS_PROCESSING),
        )


def check_image_upscale_runtime_dispatch_gates(job_id: str) -> dict[str, Any] | None:
    """Evaluates canonical runtime dispatch gates in strict priority order.

    Fails closed before any transport execution or network call:
    1. Model contract unproven -> BLOCKER_PROVIDER_CONTRACT_UNPROVEN.
    2. Account entitlement unproven -> BLOCKER_PROVIDER_ENTITLEMENT_UNPROVEN.
    3. Owner live-paid authorization ungranted -> BLOCKER_OWNER_PAID_AUTHORIZATION_REQUIRED.
    4. Provider dispatch disabled -> BLOCKER_PROVIDER_EXECUTOR_READY_BUT_DISPATCH_DISABLED.
    """
    clean_job_id = str(job_id).strip()
    if not clean_job_id:
        raise ValueError("Thiếu mã job (job_id).")

    job = get_admin_image_upscale_job(clean_job_id)
    if job and str(job.get("model_name") or DEFAULT_MODEL) != "stability_conservative":
        raise RuntimeError(
            f"IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED: {BLOCKER_PROVIDER_CONTRACT_UNPROVEN} "
            f"- Model '{job.get('model_name')}' lacks proven executable provider contract."
        )

    if not STABILITY_UPSCALE_ENTITLEMENT_PROVEN:
        raise RuntimeError(
            f"IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED: {BLOCKER_PROVIDER_ENTITLEMENT_UNPROVEN} "
            "- Stability AI upscale credit tier/balance is unproven in active account."
        )

    if not OWNER_PAID_AUTHORIZATION_GRANTED:
        raise RuntimeError(
            f"IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED: {BLOCKER_OWNER_PAID_AUTHORIZATION_REQUIRED} "
            "- Requires explicit Owner live-paid spend authorization."
        )

    if not IMAGE_UPSCALE_PROVIDER_DISPATCH_ENABLED or not IMAGE_UPSCALE_PROVIDER_DISPATCH_CURRENTLY_ENABLED:
        raise RuntimeError(
            f"IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED: {BLOCKER_PROVIDER_EXECUTOR_READY_BUT_DISPATCH_DISABLED} "
            "- Provider dispatch is currently disabled."
        )

    return job


def dispatch_image_upscale_provider(job_id: str) -> None:
    """Fail-closed provider dispatch boundary.

    In R24E1 & R24E1-FIX1, the provider executor foundation is implemented, but runtime provider
    dispatch remains strictly disabled until account entitlement and explicit Owner
    spend authorization are separately established.
    """
    clean_job_id = str(job_id).strip()
    if not clean_job_id:
        raise ValueError("Thiếu mã job (job_id).")

    # Enforce all runtime dispatch gates
    check_image_upscale_runtime_dispatch_gates(clean_job_id)

    raise RuntimeError("IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED")


def prepare_image_upscale_request(
    job_id: str,
    *,
    api_key: str,
) -> tuple[dict[str, Any], ImageUpscaleProviderRequest, tuple[str, dict[str, str], dict[str, tuple[str, bytes, str]], dict[str, Any]]]:
    """Pure request preparation and atomic FSM transition for Image Upscale.

    Invariants:
    1. Unknown job -> fails closed (ValueError).
    2. Completed job -> rejects duplicate submit (ValueError).
    3. Processing job -> rejects concurrent duplicate submit (ValueError).
    4. Failed job -> rejects blind automatic retry without new job (ValueError).
    5. Model contract must be proven ('stability_conservative').
    6. Resolves source image from Asset Vault (enforcing account ownership, format, disk existence).
    7. Constructs provider request and payload with explicit api_key. Missing key fails closed.
    """
    clean_job_id = str(job_id).strip()
    if not clean_job_id:
        raise ValueError("Thiếu mã job (job_id).")

    with transaction() as conn:
        conn.row_factory = sqlite3.Row
        job_row = conn.execute(
            "SELECT * FROM web_image_upscale_jobs WHERE id = ?;",
            (clean_job_id,),
        ).fetchone()

        if not job_row:
            raise ValueError(f"Không tìm thấy job Image Upscale: {clean_job_id}")

        job_dict = dict(job_row)
        current_status = job_dict.get("status")

        if current_status == STATUS_COMPLETED:
            raise ValueError(f"Job {clean_job_id} đã hoàn thành, không được submit lại nhà cung cấp.")
        if current_status == STATUS_PROCESSING:
            raise ValueError(f"Job {clean_job_id} đang được xử lý, không thể gửi trùng lặp.")
        if current_status == STATUS_FAILED:
            raise ValueError(f"Job {clean_job_id} đã thất bại. Cấm tự động retry mù quáng.")
        if current_status != STATUS_QUEUED:
            raise ValueError(f"Job {clean_job_id} có trạng thái không hợp lệ để thực thi: {current_status}")

        model_name = str(job_dict.get("model_name") or DEFAULT_MODEL)
        if model_name != "stability_conservative":
            now = utc_now()
            conn.execute(
                "UPDATE web_image_upscale_jobs SET status = ?, status_reason = ?, updated_at = ? WHERE id = ?;",
                (
                    STATUS_FAILED,
                    f"{BLOCKER_PROVIDER_CONTRACT_UNPROVEN}: Model '{model_name}' has no proven provider contract.",
                    now,
                    clean_job_id,
                ),
            )
            raise ValueError(
                f"{BLOCKER_PROVIDER_CONTRACT_UNPROVEN}: Model '{model_name}' lacks proven provider contract."
            )

        # Atomic FSM transition: queued -> processing
        now = utc_now()
        cursor = conn.execute(
            "UPDATE web_image_upscale_jobs SET status = ?, status_reason = ?, updated_at = ? WHERE id = ? AND status = ?;",
            (STATUS_PROCESSING, "PROCESSING_PROVIDER_SUBMIT", now, clean_job_id, STATUS_QUEUED),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Xung đột FSM: Job {clean_job_id} đã được nhận bởi tiến trình khác.")

    account_id = str(job_dict["account_id"])
    image_asset_id = str(job_dict["image_asset_id"])

    # Resolve source asset from Asset Vault
    try:
        source_bytes, orig_name, ext, mime = resolve_source_asset_image(account_id, image_asset_id)
    except Exception as exc:
        transition_image_upscale_job_failed(clean_job_id, f"SOURCE_ASSET_RESOLUTION_FAILED: {exc}")
        raise

    scale_factor = int(job_dict.get("scale_factor", DEFAULT_SCALE_FACTOR))

    # Build provider request
    req = ImageUpscaleProviderRequest(
        job_id=clean_job_id,
        account_id=account_id,
        source_asset_id=image_asset_id,
        image_bytes=source_bytes,
        filename=orig_name,
        content_type=mime,
        scale_factor=scale_factor,
        prompt=f"high resolution upscale {scale_factor}x, clean detailed",
        creativity=DEFAULT_CREATIVITY,
        output_format="png",
    )

    try:
        payload_tuple = build_stability_upscale_request_payload(req, api_key=api_key)
    except Exception as exc:
        transition_image_upscale_job_failed(clean_job_id, f"PROVIDER_REQUEST_BUILD_FAILED: {exc}")
        raise

    return job_dict, req, payload_tuple


def apply_image_upscale_result(
    job_id: str,
    result: ImageUpscaleProviderResult,
) -> dict[str, Any]:
    """Pure result application and output Asset Vault finalization for Image Upscale.

    Invariants:
    1. Validates finish_reason == 'SUCCESS' (non-success fails closed).
    2. Stores output image bytes in Asset Vault with owner scoping.
    3. Finalizes job record with provider_task_id (or None if absent).
    4. Records output_sha256 in metadata (never as synthetic provider_task_id).
    5. Returns finalized job dictionary.
    """
    clean_job_id = str(job_id).strip()
    if not clean_job_id:
        raise ValueError("Thiếu mã job (job_id).")

    if result.finish_reason.upper() != "SUCCESS":
        transition_image_upscale_job_failed(
            clean_job_id,
            f"PROVIDER_NON_SUCCESS_FINISH_REASON: {result.finish_reason}",
        )
        raise ValueError(f"Provider returned non-success finish_reason: {result.finish_reason}")

    job = get_admin_image_upscale_job(clean_job_id)
    if not job:
        raise ValueError(f"Không tìm thấy job Image Upscale: {clean_job_id}")

    account_id = str(job["account_id"])
    image_name = str(job.get("image_name") or "image.png")
    scale_factor = int(job.get("scale_factor", DEFAULT_SCALE_FACTOR))

    # Store output image into Asset Vault
    try:
        out_name = f"upscaled_{image_name.rsplit('.', 1)[0] if '.' in image_name else image_name}{result.output_extension}"
        output_asset_id = store_image_upscale_output_asset(
            account_id=account_id,
            output_image_bytes=result.output_image_bytes,
            original_filename=out_name,
            extension=result.output_extension,
            content_type=result.output_content_type,
            display_name=f"Upscale {scale_factor}x: {image_name}",
        )
    except Exception as exc:
        transition_image_upscale_job_failed(clean_job_id, f"OUTPUT_ASSET_STORAGE_FAILED: {exc}")
        raise

    metadata = dict(result.metadata)
    if result.output_sha256:
        metadata["output_sha256"] = result.output_sha256

    finalized = finalize_image_upscale_job_result(
        clean_job_id,
        provider_task_id=result.provider_task_id or "",
        provider_name=result.provider_name,
        model_name=result.model_name,
        output_asset_id=output_asset_id,
        output_metadata=metadata,
        cost_metadata={"test_cost": 0, "commercial_authority": False},
    )

    return finalized


def execute_image_upscale_job(
    job_id: str,
    *,
    transport: Any = None,
    api_key: str = "",
) -> dict[str, Any]:
    """Production executor entrypoint for Image Upscale.

    Invariants (R24E1-FIX1):
    1. ARBITRARY_TRANSPORT_OBJECT_IS_AUTHORITY = NO.
       Caller-supplied transport CANNOT bypass entitlement, owner auth, or dispatch gates.
    2. Enforces all runtime dispatch gates FIRST. Fails closed before any transport or network action.
    3. Direct hidden provider bypass is eliminated (DIRECT_HIDDEN_PROVIDER_PATH_AVAILABLE = NO).
    4. Production network transport remains unactivated (REAL_PROVIDER_NETWORK_CALL_COUNT = 0).
    """
    clean_job_id = str(job_id).strip()
    if not clean_job_id:
        raise ValueError("Thiếu mã job (job_id).")

    # 1. Verify job exists (unknown job fails closed with ValueError)
    job = get_admin_image_upscale_job(clean_job_id)
    if not job:
        raise ValueError(f"Không tìm thấy job Image Upscale: {clean_job_id}")

    # 2. Enforce all runtime dispatch gates FIRST
    check_image_upscale_runtime_dispatch_gates(clean_job_id)

    # 3. Enforce dependency injection is NOT authority
    if transport is not None:
        raise RuntimeError(
            "ARBITRARY_TRANSPORT_OBJECT_IS_AUTHORITY=NO: "
            "Caller-supplied transport cannot be used in production execution."
        )

    # 3. Production transport fail-closed
    raise RuntimeError("IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED: Production network transport not active.")
