"""Image Remove Background Canonical Job Bridge Adapter.

Task: WEBAPP_R7_FINAL_RESIDUAL_ENGINE_AND_ROOT_GAP_CLOSURE_MASTER_BATCH_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: image_remove_background
Entrypoint: /image/remove-background
Web API Family: /api/v1/features/image_remove_background/*

Exposes the canonical Bot remove_bg engine (RemoveBG HD / Cutout.pro fallback)
to Web App customers with owner-scoped Asset Vault input validation, canonical
pricing (Standard: 80 Xu, Premium: 150 Xu), durable SQLite ledger, idempotency,
and zero paid provider calls during automated test verification.

Invariants:
- Fail-Closed Admission: zero provider calls until Owner-authorized runtime execution.
- Truthful Status: initial status is 'queued', status_reason is
  'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'. Zero fake output, zero fake PNG.
- Asset Vault Ownership: input image must be owned by authenticated Web account.
- Idempotency & Conflict: replay existing job on identical payload hash, reject with 409
  on same request_id / idempotency_key with differing payload.
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

CANONICAL_PRODUCT_KEY = "image_remove_background"
CANONICAL_ROUTING_KEY = "image_remove_background"
CANONICAL_ROUTE_ID = "image_remove_background_canonical_v1"
CANONICAL_ENGINE_ADAPTER = "b13_r18c_image_remove_background_v1"

SAFE_IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp",
})

SUPPORTED_PACKAGES: dict[str, int] = {
    "standard": 80,  # Cutout.pro fallback tier
    "cutout": 80,
    "premium": 150,  # RemoveBG HD tier
    "removebg_hd": 150,
    "removebg": 150,
}

DEFAULT_PACKAGE = "standard"

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "apikey", "apitoken", "token",
    "secret", "jobid", "jobstatus", "status", "statusreason", "output", "outputurl",
    "assetid", "downloadurl", "role", "balance", "xu", "wallet",
})


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


def ensure_image_remove_background_schema() -> None:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_image_remove_background_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'image_remove_background',
                routing_product_key TEXT NOT NULL DEFAULT 'image_remove_background',
                image_asset_id TEXT NOT NULL,
                image_name TEXT NOT NULL,
                package TEXT NOT NULL DEFAULT 'standard',
                xu_cost INTEGER NOT NULL DEFAULT 80,
                status TEXT NOT NULL DEFAULT 'queued',
                status_reason TEXT NOT NULL DEFAULT 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope TEXT NOT NULL,
                output_metadata TEXT,
                output_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_rmbg_jobs_account_created "
            "ON web_image_remove_background_jobs(account_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_rmbg_jobs_request "
            "ON web_image_remove_background_jobs(request_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_rmbg_jobs_account_idempotency "
            "ON web_image_remove_background_jobs(account_id, idempotency_key_hash)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_img_rmbg_jobs_status_created "
            "ON web_image_remove_background_jobs(status, created_at ASC)"
        )


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest() if key.strip() else ""


def validate_image_remove_background_input(
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

    package = str(payload.get("package") or payload.get("tier") or payload.get("mode") or DEFAULT_PACKAGE).strip().lower()
    if package not in SUPPORTED_PACKAGES:
        valid_packages = ", ".join(sorted(SUPPORTED_PACKAGES.keys()))
        return False, f"Gói tách nền không hợp lệ: '{package}'. Hỗ trợ: {valid_packages}.", {}

    xu_cost = SUPPORTED_PACKAGES[package]

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
        return False, f"Định dạng tệp không được hỗ trợ để tách nền. Hỗ trợ: {valid_exts}.", {}

    clean_payload = {
        "image_asset_id": asset_id,
        "image_name": orig_name,
        "package": package,
        "mode": package,
        "xu_cost": xu_cost,
    }
    return True, "", clean_payload


def create_or_replay_image_remove_background_job(
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    ensure_image_remove_background_schema()

    is_valid, err_msg, clean_payload = validate_image_remove_background_input(account_id, payload)
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
                SELECT * FROM web_image_remove_background_jobs
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
            SELECT * FROM web_image_remove_background_jobs
            WHERE request_id = ?
            LIMIT 1;
            """,
            (req_id,),
        ).fetchone()

        if existing_req:
            row_dict = dict(existing_req)
            if row_dict.get("account_id") != account_id:
                raise HTTPException(status_code=403, detail="Yêu cầu không thuộc tài khoản hiện tại.")
            if not hmac.compare_digest(row_dict.get("payload_hash", ""), current_payload_hash):
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột request_id: payload khác với yêu cầu trước đó.",
                )
            res = _format_job_dict(row_dict)
            res["idempotent_replay"] = True
            return res

        now = utc_now()
        job_id = f"irbj_{uuid.uuid4().hex[:16]}"
        envelope_data = {
            "route_id": CANONICAL_ROUTE_ID,
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "package": clean_payload["package"],
            "xu_cost": clean_payload["xu_cost"],
            "image_asset_id": clean_payload["image_asset_id"],
            "image_name": clean_payload["image_name"],
            "enqueued_at": now,
        }

        conn.execute(
            """
            INSERT INTO web_image_remove_background_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                image_asset_id, image_name, package, xu_cost,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                job_id,
                req_id,
                account_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                clean_payload["image_asset_id"],
                clean_payload["image_name"],
                clean_payload["package"],
                clean_payload["xu_cost"],
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                idempotency_hash or None,
                current_payload_hash,
                json.dumps(envelope_data, ensure_ascii=False),
                now,
                now,
            ),
        )

        created_row = conn.execute(
            "SELECT * FROM web_image_remove_background_jobs WHERE id = ?;", (job_id,)
        ).fetchone()

        res = _format_job_dict(dict(created_row))
        res["idempotent_replay"] = False
        return res


def list_image_remove_background_jobs(account_id: str, limit: int = 50) -> list[dict[str, Any]]:
    ensure_image_remove_background_schema()
    bounded_limit = max(1, min(limit, 200))
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM web_image_remove_background_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (account_id, bounded_limit),
        ).fetchall()
    return [_format_job_dict(dict(r)) for r in rows]


def get_image_remove_background_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    ensure_image_remove_background_schema()
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM web_image_remove_background_jobs
            WHERE id = ? AND account_id = ?
            LIMIT 1;
            """,
            (job_id, account_id),
        ).fetchone()
    return _format_job_dict(dict(row)) if row else None


def is_image_remove_background_job_other_account(job_id: str, account_id: str) -> bool:
    ensure_image_remove_background_schema()
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT account_id FROM web_image_remove_background_jobs WHERE id = ? LIMIT 1;",
            (job_id,),
        ).fetchone()
    if not row:
        return False
    return dict(row).get("account_id") != account_id


def image_remove_background_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(job, dict):
        return {}
    return {
        "id": job.get("id"),
        "job_id": job.get("id"),
        "type": "image_remove_background",
        "product_key": CANONICAL_PRODUCT_KEY,
        "status": job.get("status"),
        "status_reason": job.get("status_reason"),
        "package": job.get("package"),
        "xu_cost": job.get("xu_cost"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "output_available": bool(job.get("output_url")),
        "output_url": job.get("output_url"),
        "output_metadata": job.get("output_metadata"),
    }


def _format_job_dict(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out.pop("idempotency_key_hash", None)
    out.pop("payload_hash", None)
    out["mode"] = out.get("package")
    if "bridge_envelope" in out and isinstance(out["bridge_envelope"], str):
        try:
            out["bridge_envelope"] = json.loads(out["bridge_envelope"])
        except Exception:
            pass
    if "output_metadata" in out and isinstance(out["output_metadata"], str):
        try:
            out["output_metadata"] = json.loads(out["output_metadata"])
        except Exception:
            pass
    return out
