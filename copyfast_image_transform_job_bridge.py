"""Image Transform (Image-to-Image) Canonical Job Bridge Adapter.

Task: WEBAPP_R24B2_IMAGE_TRANSFORM_VISIBLE_JOB_BRIDGE_AND_RESULT_RETENTION_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: image_transform
Customer Entrypoint: /image/transform
Web API Family: /api/v1/features/image_transform/*

Connects the Web customer flow (/image/transform) to a durable, owner-scoped
canonical job bridge and result-retention contract without executing real paid
provider calls, background subprocesses, or wallet mutations.

Invariants:
- Fail-Closed Admission: zero provider calls until explicit Owner spend/entitlement authorization.
- Truthful Initial Status: status='queued', status_reason='AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE'.
- Asset Vault Ownership: source image must exist in web_asset_files and be owned by the authenticated Web account.
- Cross-Owner Isolation: cross-account asset access is rejected.
- Idempotency & Conflict: exact replay returns existing job with `idempotent_replay=True`;
  differing payload on the same idempotency key raises HTTP 409 Conflict.
- Result Retention: finalized output persists into canonical Asset Vault with owner scoping
  and safe download/preview paths.
- Provider Dispatch Disabled: dispatch boundary exists but throws RuntimeError if invoked in R24B2.
- Key4U Public Gate: KEY4U_PUBLIC_ENABLED remains False.
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

CANONICAL_PRODUCT_KEY = "image_transform"
CANONICAL_ROUTING_KEY = "image_transform"
CANONICAL_ROUTE_ID = "image_transform_canonical_v1"
CANONICAL_CUSTOMER_ENTRYPOINT = "/image/transform"
CANONICAL_ALIAS_ENTRYPOINTS = ("/image/image-to-image",)

SUPPORTED_IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp",
})
SAFE_IMAGE_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS

SUPPORTED_IMAGE_MIME_TYPES: frozenset[str] = frozenset({
    "image/png",
    "image/jpeg",
    "image/webp",
})

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_REASON_AWAITING = "EXTERNAL_PROVIDER_AUTHORITY_AND_ENTITLEMENT_UNPROVEN"
STATUS_REASON_LEGACY = "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE"
STATUS_REASON_COMPLETED = "COMPLETED"

SUPPORTED_FORMATS: frozenset[str] = frozenset({"1:1", "4:5", "16:9", "9:16"})
SUPPORTED_ASPECT_RATIOS: frozenset[str] = SUPPORTED_FORMATS
DEFAULT_FORMAT = "1:1"
DEFAULT_ASPECT_RATIO = "1:1"

# External provider dispatch flags — strictly disabled in R24B2 / R24E3B
IMAGE_TRANSFORM_PROVIDER_DISPATCH_ENABLED: bool = False
KEY4U_PUBLIC_ENABLED: bool = False

_RAW_FORBIDDEN_AUTHORITY_KEYS = (
    "amount", "amount_vnd", "amount_xu", "price", "cost", "currency", "payment_id", "order_code",
    "checkout_url", "webhook", "provider", "provider_name", "provider_id", "provider_task_id",
    "provider_job_id", "provider_route", "model", "model_name", "tier", "quality_tier",
    "quota_xu", "charged_xu", "xu", "xu_cost", "xu_charge", "fee", "credits",
    "wallet", "wallet_id", "wallet_balance", "balance", "api_key", "api_token", "token", "secret",
    "job_id", "job_status", "status", "status_reason", "output", "output_url", "asset_id", "download_url",
    "role", "file_path", "local_path", "storage_key", "account_id", "user_id", "canonical_user_id",
    "actor_id", "is_paid_job", "confirm_paid", "paid", "owner_id",
    "upload_id", "bot_upload_id", "bridge_envelope", "bot_prepare_status", "result",
)
FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset(
    "".join(ch for ch in str(k or "").lower() if ch.isalnum()) for k in _RAW_FORBIDDEN_AUTHORITY_KEYS
)

UNSAFE_URL_PREFIXES = ("javascript:", "data:", "file:", "http://127.0.0.1", "http://localhost", "http://0.0.0.0")

SENSITIVE_KEY_SUBSTRINGS: tuple[str, ...] = (
    "api_key", "apikey", "token", "authorization", "secret",
    "credential", "cookie", "password", "signed_url_secret",
    "local_path", "localpath", "file_path", "filepath", "filesystem_path",
    "raw_authorization", "bearer", "hmac",
)


def sanitize_external_metadata(meta: Any) -> Any:
    """Recursively sanitizes and strips sensitive secret fields from metadata."""
    if isinstance(meta, dict):
        clean = {}
        for k, v in meta.items():
            norm_k = "".join(ch for ch in str(k or "").lower() if ch.isalnum() or ch == "_")
            if any(sub in norm_k for sub in SENSITIVE_KEY_SUBSTRINGS):
                continue  # strip secret field to prevent secret persistence
            clean[k] = sanitize_external_metadata(v)
        return clean
    elif isinstance(meta, list):
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


def ensure_image_transform_schema() -> None:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_transform_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'image_transform',
                routing_product_key TEXT NOT NULL DEFAULT 'image_transform',
                image_asset_id TEXT NOT NULL,
                image_name TEXT NOT NULL,
                transform_instruction TEXT NOT NULL,
                aspect_ratio TEXT NOT NULL DEFAULT '1:1',
                tier TEXT,
                model_name TEXT,
                xu_cost INTEGER DEFAULT NULL,
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
            "CREATE INDEX IF NOT EXISTS idx_web_img_transform_jobs_account_created "
            "ON web_image_transform_jobs(account_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_transform_jobs_request "
            "ON web_image_transform_jobs(request_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_transform_jobs_account_idempotency "
            "ON web_image_transform_jobs(account_id, idempotency_key_hash)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_transform_jobs_status_created "
            "ON web_image_transform_jobs(status, created_at ASC)"
        )


def validate_image_transform_input(
    account_id: str,
    payload: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return False, "Payload phải là JSON object.", {}

    if _contains_authority_field(payload):
        return False, "Payload chứa trường không được phép (authority field injection).", {}

    asset_id = str(
        payload.get("image_asset_id")
        or payload.get("source_asset_id")
        or payload.get("source")
        or payload.get("asset_id")
        or ""
    ).strip()
    if not asset_id:
        return False, "Thiếu mã tài sản ảnh nguồn (image_asset_id).", {}

    instruction = str(
        payload.get("transform_instruction")
        or payload.get("prompt")
        or payload.get("instruction")
        or ""
    ).strip()
    if not instruction:
        return False, "Thiếu câu lệnh biến đổi ảnh (transform_instruction/prompt).", {}

    fmt = str(payload.get("format") or payload.get("aspect_ratio") or DEFAULT_FORMAT).strip()
    if fmt not in SUPPORTED_FORMATS:
        valid_fmts = ", ".join(sorted(SUPPORTED_FORMATS))
        return False, f"Tỷ lệ khung hình không hợp lệ: '{fmt}'. Hỗ trợ: {valid_fmts}.", {}

    # Verify asset exists, is owned by account_id, and is an approved image format
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

    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        valid_exts = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        return False, f"Định dạng tệp không được hỗ trợ để biến thể. Chỉ hỗ trợ: {valid_exts}.", {}

    if mime and mime not in SUPPORTED_IMAGE_MIME_TYPES:
        return False, "MIME type của tệp không được hỗ trợ để biến thể. Chỉ hỗ trợ ảnh .png, .jpg, .jpeg, .webp.", {}

    clean_payload = {
        "image_asset_id": asset_id,
        "image_name": orig_name,
        "transform_instruction": instruction,
        "aspect_ratio": fmt,
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

    output_asset_id = row.get("output_asset_id")
    output_url = row.get("output_url")
    preview_url = None
    download_url = None
    if output_asset_id:
        preview_url = f"/api/v1/assets/{output_asset_id}/preview"
        download_url = f"/api/v1/assets/{output_asset_id}/download"

    return {
        "id": row["id"],
        "job_id": row["id"],
        "request_id": row["request_id"],
        "account_id": row["account_id"],
        "product_key": row.get("product_key") or CANONICAL_PRODUCT_KEY,
        "routing_product_key": row.get("routing_product_key") or CANONICAL_ROUTING_KEY,
        "image_asset_id": row["image_asset_id"],
        "image_name": row["image_name"],
        "transform_instruction": row.get("transform_instruction") or "",
        "aspect_ratio": row.get("aspect_ratio") or DEFAULT_FORMAT,
        "tier": row.get("tier"),
        "model_name": row.get("model_name"),
        "xu_cost": row.get("xu_cost"),
        "status": row["status"],
        "status_reason": row.get("status_reason") or STATUS_REASON_AWAITING,
        "provider_name": row.get("provider_name"),
        "provider_task_id": row.get("provider_task_id"),
        "output_asset_id": output_asset_id,
        "output_url": output_url,
        "output_available": bool(output_asset_id or output_url),
        "preview_url": preview_url,
        "download_url": download_url,
        "output_metadata": output_meta,
        "cost_metadata": cost_meta,
        "bridge_envelope": bridge_envelope,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row.get("completed_at"),
        "source": "web_native_image_transform",
    }


def create_or_replay_image_transform_job(
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    ensure_image_transform_schema()
    ok, err_msg, clean_input = validate_image_transform_input(account_id, payload)
    if not ok:
        raise HTTPException(status_code=400, detail=err_msg)

    payload_hash = _hash_payload(clean_input)
    req_id = request_id.strip() or f"req_imgxf_{uuid.uuid4().hex[:16]}"
    clean_input["request_id"] = req_id
    idem_hash = _hash_key(idempotency_key)
    now = utc_now()

    with transaction() as conn:
        conn.row_factory = sqlite3.Row

        # Check existing job by idempotency key
        if idem_hash:
            existing = conn.execute(
                """
                SELECT * FROM web_image_transform_jobs
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
            SELECT * FROM web_image_transform_jobs
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

        job_id = f"imgxf_{uuid.uuid4().hex[:20]}"
        bridge_envelope = {
            "canonical_product_key": CANONICAL_PRODUCT_KEY,
            "canonical_route_id": CANONICAL_ROUTE_ID,
            "customer_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
            "created_via": "web_native_image_transform_bridge",
            "account_id": account_id,
            "provider_calls_made": 0,
            "paid_calls_made": 0,
            "admission_status": "queued",
            "admission_reason": STATUS_REASON_AWAITING,
            "key4u_public_enabled": False,
        }

        conn.execute(
            """
            INSERT INTO web_image_transform_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                image_asset_id, image_name, transform_instruction, aspect_ratio,
                tier, model_name, xu_cost, status, status_reason,
                idempotency_key_hash, payload_hash, bridge_envelope,
                provider_name, provider_task_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                job_id,
                req_id,
                account_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                clean_input["image_asset_id"],
                clean_input["image_name"],
                clean_input["transform_instruction"],
                clean_input["aspect_ratio"],
                None,
                None,
                None,
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                idem_hash if idem_hash else None,
                payload_hash,
                json.dumps(bridge_envelope, ensure_ascii=False),
                None,
                None,
                now,
                now,
            ),
        )

        row = conn.execute(
            "SELECT * FROM web_image_transform_jobs WHERE id = ?;", (job_id,)
        ).fetchone()

    formatted = _format_job_dict(dict(row))
    formatted["idempotent_replay"] = False
    return formatted


def get_image_transform_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    ensure_image_transform_schema()
    clean_id = str(job_id or "").strip()
    if not clean_id:
        return None

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM web_image_transform_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1;
            """,
            (clean_id, account_id),
        ).fetchone()

    return _format_job_dict(dict(row)) if row else None


def is_image_transform_job_other_account(job_id: str, account_id: str) -> bool:
    ensure_image_transform_schema()
    clean_id = str(job_id or "").strip()
    if not clean_id:
        return False

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id FROM web_image_transform_jobs
            WHERE id = ? AND account_id != ?
            LIMIT 1;
            """,
            (clean_id, account_id),
        ).fetchone()

    return row is not None


def list_image_transform_jobs(
    account_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    ensure_image_transform_schema()
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM web_image_transform_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
            """,
            (account_id, safe_limit, safe_offset),
        ).fetchall()

    return [_format_job_dict(dict(r)) for r in rows]


def list_admin_image_transform_jobs(
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    ensure_image_transform_schema()
    safe_limit = max(1, min(limit, 500))
    safe_offset = max(0, offset)

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM web_image_transform_jobs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
            """,
            (safe_limit, safe_offset),
        ).fetchall()

    return [_format_job_dict(dict(r)) for r in rows]


def get_admin_image_transform_job(job_id: str) -> dict[str, Any] | None:
    ensure_image_transform_schema()
    clean_id = str(job_id or "").strip()
    if not clean_id:
        return None

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM web_image_transform_jobs
            WHERE id = ?
            LIMIT 1;
            """,
            (clean_id,),
        ).fetchone()

    return _format_job_dict(dict(row)) if row else None


def image_transform_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Projects an image transform job into the generic /jobs read model format."""
    job_id = str(job.get("id") or job.get("job_id") or "")
    status = str(job.get("status") or STATUS_QUEUED)
    output_asset_id = job.get("output_asset_id")
    output_url = job.get("output_url")
    is_completed = status == STATUS_COMPLETED and bool(output_asset_id)

    instruction_preview = str(job.get("transform_instruction") or "")[:40]
    title = f"Biến thể: {job.get('image_name') or 'Ảnh'}"
    if instruction_preview:
        title += f" ({instruction_preview}...)"

    return {
        "id": job_id,
        "job_id": job_id,
        "request_id": job.get("request_id"),
        "account_id": job.get("account_id"),
        "product_key": CANONICAL_PRODUCT_KEY,
        "product": CANONICAL_PRODUCT_KEY,
        "product_family": "image",
        "title": title,
        "kind": "image_transform",
        "status": status,
        "status_reason": job.get("status_reason") or STATUS_REASON_AWAITING,
        "provider_name": job.get("provider_name"),
        "model_name": job.get("model_name"),
        "xu_cost": job.get("xu_cost"),
        "output_available": is_completed,
        "output_asset_id": output_asset_id,
        "output_url": output_url,
        "preview_url": job.get("preview_url"),
        "download_url": job.get("download_url"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "completed_at": job.get("completed_at"),
        "source": "web_native_image_transform",
    }


def finalize_image_transform_job_result(
    job_id: str,
    *,
    provider_task_id: str | None = None,
    provider_name: str | None = None,
    model_name: str | None = None,
    output_asset_id: str = "",
    output_metadata: dict[str, Any] | None = None,
    cost_metadata: dict[str, Any] | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Finalizes an image transform job by attaching a verified, owner-scoped Asset Vault item.

    Enforces:
    1. The job exists.
    2. Output asset must NOT be the same as source image_asset_id (distinct artifact).
    3. Output asset exists in web_asset_files, belongs to the SAME account, and is active.
    4. Output asset is a verified supported image format (.png, .jpg, .jpeg, .webp).
    5. Provider and model metadata are neutral: omitted parameters remain NULL without fake defaults.
    6. External metadata (output_metadata, cost_metadata) is sanitized against secret leakage.
    7. Updates job status to 'completed' with canonical download/preview paths.
    """
    ensure_image_transform_schema()
    clean_job_id = str(job_id).strip()
    clean_asset_id = str(output_asset_id).strip()

    if not clean_job_id:
        raise ValueError("Thiếu mã job (job_id).")
    if not clean_asset_id:
        raise ValueError("Thiếu mã tài sản kết quả (output_asset_id).")

    with transaction() as conn:
        conn.row_factory = sqlite3.Row
        job_row = conn.execute(
            "SELECT * FROM web_image_transform_jobs WHERE id = ? LIMIT 1;",
            (clean_job_id,),
        ).fetchone()

        if not job_row:
            raise HTTPException(status_code=404, detail="Không tìm thấy job Image Transform.")

        job_dict = dict(job_row)
        account_id = str(job_dict["account_id"])
        source_asset_id = str(job_dict.get("image_asset_id") or "")

        # Distinct artifact requirement: output_asset_id != source image_asset_id
        if clean_asset_id == source_asset_id:
            raise HTTPException(
                status_code=400,
                detail="Tài sản kết quả không được trùng với tài sản ảnh nguồn (phải là tạo tác biến đổi riêng biệt).",
            )

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

        # Verify output asset is a supported image type
        out_orig = str(asset_dict.get("original_filename") or "").strip()
        out_ext = str(asset_dict.get("extension") or "").strip().lower()
        if not out_ext and "." in out_orig:
            out_ext = ("." + out_orig.rsplit(".", 1)[-1].lower())
        out_mime = str(asset_dict.get("content_type") or "").strip().lower()

        if out_ext not in SUPPORTED_IMAGE_EXTENSIONS:
            valid_exts = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng tệp kết quả không được hỗ trợ. Chỉ chấp nhận: {valid_exts}.",
            )
        if out_mime and out_mime not in SUPPORTED_IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail="MIME type của tệp kết quả không được hỗ trợ. Chỉ chấp nhận ảnh .png, .jpg, .jpeg, .webp.",
            )

        now = completed_at or utc_now()

        # Defect B: Do NOT fabricate fallback provider (e.g. 'key4u') or model
        resolved_provider = (str(provider_name).strip() if provider_name and str(provider_name).strip() else None) or job_dict.get("provider_name")
        resolved_model = (str(model_name).strip() if model_name and str(model_name).strip() else None) or job_dict.get("model_name")
        resolved_task_id = (str(provider_task_id).strip() if provider_task_id and str(provider_task_id).strip() else None) or job_dict.get("provider_task_id")

        output_url = f"/api/v1/assets/{clean_asset_id}/download"
        if not _validate_safe_url(output_url):
            raise HTTPException(status_code=400, detail="Đường dẫn kết quả không an toàn.")

        # Defect F: Sanitize metadata against secret leakage
        clean_out_meta = sanitize_external_metadata(output_metadata or {})
        clean_cost_meta = sanitize_external_metadata(cost_metadata or {})

        conn.execute(
            """
            UPDATE web_image_transform_jobs
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
            "SELECT * FROM web_image_transform_jobs WHERE id = ?;", (clean_job_id,)
        ).fetchone()

    return _format_job_dict(dict(updated_row))


def dispatch_image_transform_provider(job_id: str) -> None:
    """Provider dispatch boundary.

    In R24B2, provider dispatch is strictly disabled.
    Any attempt to invoke an external provider raises RuntimeError without network calls.
    """
    raise RuntimeError(
        "IMAGE_TRANSFORM_PROVIDER_DISPATCH_DISABLED: Requires explicit Owner external entitlement and spend authorization."
    )
