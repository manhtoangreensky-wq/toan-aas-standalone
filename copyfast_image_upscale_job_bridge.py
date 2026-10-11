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
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now

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

# Future provider dispatch flags — strictly disabled in R24B1
IMAGE_UPSCALE_PROVIDER_DISPATCH_ENABLED: bool = False
REPLICATE_REAL_ESRGAN_DISPATCH_AUTHORIZED: bool = False
STABILITY_UPSCALE_DISPATCH_AUTHORIZED: bool = False

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
                str(provider_task_id or ""),
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


def dispatch_image_upscale_provider(job_id: str) -> None:
    """Provider dispatch boundary.

    In R24B1, provider dispatch is strictly disabled.
    Any attempt to invoke an external provider raises RuntimeError without network calls.
    """
    raise RuntimeError(
        "IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED: Requires explicit Owner live-paid spend authorization."
    )
