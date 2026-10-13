"""Image Transform Canonical Web-to-Bot Runtime Bridge Adapter.

Task: WEBAPP_R24E3B_IMAGE_TRANSFORM_WEB_TO_BOT_CANONICAL_STAGING_AND_PREPARE_BRIDGE_R1
Program: WEBAPP_R24_IMAGE_TRANSFORM_CLOSURE (#629)
Capability: image_transform
Customer Entrypoint: /image/transform

Connects Web Image Transform jobs and Asset Vault sources to the canonical Bot
Core Bridge private endpoints without executing Key4U, without provider dispatch,
and with strict fail-closed contract validation.

Invariants:
- Canonical Core Bridge Reused: uses copyfast_bridge.bridge_request with standard HMAC.
- Asset Vault Ownership: source asset must belong to the authenticated account and be active.
- Integrity: source SHA256 verified against physical bytes before staging.
- Safe Bot Staging: uploads to POST /internal/v1/uploads with opaque identifier.
- Provider-Free Prepare: calls POST /internal/v1/web-image-transform/prepare with minimal fields.
- Contract Validation: requires status=PREPARED_PROVIDER_DISABLED, provider_execution_allowed=False.
- Staging Idempotency: exact job replays reuse durable staging truth without second upload.
- Zero Spend / No Paid Execution: KEY4U_PROVIDER_CALLS=0, WALLET_MUTATIONS=0.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from fastapi import HTTPException

from copyfast_assets import (
    CANONICAL_MIME_BY_EXTENSION,
    STORAGE_KEY_PATTERN,
    _storage_path,
)
import copyfast_bridge
from copyfast_db import (
    asset_vault_directory,
    read_transaction,
    transaction,
    utc_now,
)
from copyfast_image_transform_job_bridge import (
    CANONICAL_CUSTOMER_ENTRYPOINT,
    CANONICAL_PRODUCT_KEY,
    CANONICAL_ROUTE_ID,
    STATUS_QUEUED,
    STATUS_REASON_AWAITING,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_IMAGE_MIME_TYPES,
    get_image_transform_job,
    is_image_transform_job_other_account,
    sanitize_external_metadata,
)

# ─── CANONICAL ROUTE CONSTANTS ───────────────────────────────────────────────
BOT_PRIVATE_UPLOAD_ROUTE = "/internal/v1/uploads"
BOT_PRIVATE_PREPARE_ROUTE = "/internal/v1/web-image-transform/prepare"

STATUS_REASON_UNPROVEN = "EXTERNAL_PROVIDER_AUTHORITY_AND_ENTITLEMENT_UNPROVEN"
STATUS_PREPARED_PROVIDER_DISABLED = "PREPARED_PROVIDER_DISABLED"

# ─── FAILURE CODES ───────────────────────────────────────────────────────────
CORE_BRIDGE_UNCONFIGURED = "CORE_BRIDGE_UNCONFIGURED"
SOURCE_ASSET_NOT_FOUND = "SOURCE_ASSET_NOT_FOUND"
SOURCE_ASSET_OWNER_MISMATCH = "SOURCE_ASSET_OWNER_MISMATCH"
SOURCE_ASSET_CORRUPT = "SOURCE_ASSET_CORRUPT"
BOT_UPLOAD_REJECTED = "BOT_UPLOAD_REJECTED"
BOT_UPLOAD_OWNER_MISMATCH = "BOT_UPLOAD_OWNER_MISMATCH"
BOT_PREPARE_REJECTED = "BOT_PREPARE_REJECTED"
BOT_PREPARE_CONTRACT_INVALID = "BOT_PREPARE_CONTRACT_INVALID"
BOT_DEPENDENCY_NOT_READY = "BOT_DEPENDENCY_NOT_READY"
PROVIDER_AUTHORITY_UNPROVEN = "PROVIDER_AUTHORITY_UNPROVEN"

# Structural / State Declarations
IMAGE_TRANSFORM_PROVIDER_DISPATCH_ENABLED: bool = False
WEB_PROVIDER_EXECUTOR_IMPLEMENTED: bool = False
BOT_PROVIDER_EXECUTOR_OWNER: bool = True
KEY4U_PUBLIC_ENABLED_MUTATION: bool = False


def _resolve_account_actor_id(account_id: str) -> str:
    """Resolve the canonical actor identifier from the authenticated Web account."""
    clean_account_id = str(account_id or "").strip()
    if not clean_account_id:
        return ""

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        acc_row = conn.execute(
            "SELECT id, canonical_user_id FROM web_accounts WHERE id = ? LIMIT 1;",
            (clean_account_id,),
        ).fetchone()

    if not acc_row:
        return clean_account_id

    canonical_user_id = acc_row["canonical_user_id"]
    if canonical_user_id and str(canonical_user_id).strip():
        return str(canonical_user_id).strip()
    return str(acc_row["id"]).strip()


def resolve_source_asset_bytes(account_id: str, asset_id: str) -> tuple[bytes, str, str, str]:
    """Resolve, validate, and verify physical bytes for a source asset in Asset Vault.

    Returns:
        (content_bytes, original_filename, content_type, sha256_digest)
    Raises:
        HTTPException with distinct failure classification.
    """
    clean_account = str(account_id or "").strip()
    clean_asset = str(asset_id or "").strip()

    if not clean_asset:
        raise HTTPException(status_code=400, detail=f"{SOURCE_ASSET_NOT_FOUND}: asset_id is required")

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, account_id, original_filename, extension, content_type, byte_size, sha256, storage_key, state
            FROM web_asset_files
            WHERE id = ?
            LIMIT 1;
            """,
            (clean_asset,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"{SOURCE_ASSET_NOT_FOUND}: asset does not exist")

    asset_dict = dict(row)
    if str(asset_dict.get("account_id") or "").strip() != clean_account:
        raise HTTPException(status_code=403, detail=f"{SOURCE_ASSET_OWNER_MISMATCH}: asset belongs to another account")

    if asset_dict.get("state") != "active":
        raise HTTPException(status_code=400, detail=f"{SOURCE_ASSET_NOT_FOUND}: asset is not in active state")

    ext = str(asset_dict.get("extension") or "").strip().lower()
    orig_name = str(asset_dict.get("original_filename") or "").strip()
    if not ext and "." in orig_name:
        ext = ("." + orig_name.rsplit(".", 1)[-1].lower())

    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"{SOURCE_ASSET_NOT_FOUND}: unsupported extension {ext}")

    mime = str(asset_dict.get("content_type") or "").strip().lower()
    if mime and mime not in SUPPORTED_IMAGE_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"{SOURCE_ASSET_NOT_FOUND}: unsupported MIME type {mime}")

    storage_key = str(asset_dict.get("storage_key") or "").strip()
    if not STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise HTTPException(status_code=400, detail=f"{SOURCE_ASSET_CORRUPT}: invalid storage_key pattern")

    vault_root = Path(asset_vault_directory())
    try:
        physical_path = _storage_path(vault_root, storage_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{SOURCE_ASSET_CORRUPT}: storage path violation: {exc}")

    if not physical_path.is_file():
        raise HTTPException(status_code=404, detail=f"{SOURCE_ASSET_NOT_FOUND}: physical object missing on disk")

    try:
        content_bytes = physical_path.read_bytes()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{SOURCE_ASSET_CORRUPT}: failed reading asset bytes: {exc}")

    # Integrity verification
    computed_sha = hashlib.sha256(content_bytes).hexdigest()
    recorded_sha = str(asset_dict.get("sha256") or "").strip().lower()
    if recorded_sha and computed_sha != recorded_sha:
        raise HTTPException(
            status_code=400,
            detail=f"{SOURCE_ASSET_CORRUPT}: SHA256 mismatch (recorded={recorded_sha}, computed={computed_sha})",
        )

    resolved_mime = mime or CANONICAL_MIME_BY_EXTENSION.get(ext) or "image/png"
    return content_bytes, orig_name, resolved_mime, computed_sha


async def prepare_image_transform_job_with_bot(
    account_id: str,
    job_id: str,
) -> dict[str, Any]:
    """Execute the canonical Web-to-Bot staging and prepare pipeline for an Image Transform job.

    Enforces:
    1. Replay Idempotency: exact job replay reuses existing durable staging truth.
    2. Owner Boundary: cross-owner job/asset access is strictly rejected.
    3. Asset Vault Source: physical content & SHA256 validated before staging.
    4. Minimal Core Bridge Staging: POST /internal/v1/uploads without client owner/authority injection.
    5. Provider-Free Prepare: POST /internal/v1/web-image-transform/prepare with only upload_id, instruction, aspect_ratio.
    6. Strict Response Validation: verifies PREPARED_PROVIDER_DISABLED, provider_execution_allowed=False, zero output.
    7. Durable Job Truth: persists bot_upload_id and blockers into bridge_envelope, keeping status=queued.
    """
    clean_account = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()

    if not clean_account:
        raise HTTPException(status_code=401, detail="account_id is required")
    if not clean_job_id:
        raise HTTPException(status_code=400, detail="job_id is required")

    # 1. Load canonical job
    job = get_image_transform_job(clean_account, clean_job_id)
    if not job:
        if is_image_transform_job_other_account(clean_job_id, clean_account):
            raise HTTPException(status_code=403, detail=f"{SOURCE_ASSET_OWNER_MISMATCH}: cross-owner job access denied")
        raise HTTPException(status_code=404, detail=f"{SOURCE_ASSET_NOT_FOUND}: image transform job not found")

    envelope_meta = dict(job.get("bridge_envelope") or {})

    # 2. Check if job has already been staged and prepared with Bot (Staging Idempotency)
    existing_bot_upload_id = str(envelope_meta.get("bot_upload_id") or "").strip()
    existing_prepare_status = str(envelope_meta.get("bot_prepare_status") or "").strip()
    if existing_bot_upload_id and existing_prepare_status == STATUS_PREPARED_PROVIDER_DISABLED:
        # Exact replay of an already-prepared Web job reuses durable staging truth
        return {
            "ok": True,
            "job_id": clean_job_id,
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_UNPROVEN,
            "bot_upload_id": existing_bot_upload_id,
            "bot_prepare_status": existing_prepare_status,
            "bot_prepare_reason": envelope_meta.get("bot_prepare_reason") or STATUS_REASON_UNPROVEN,
            "provider_execution_allowed": False,
            "blockers": envelope_meta.get("blockers") or [],
            "idempotent_replay": True,
            "job": job,
        }

    # 3. Check Core Bridge Configuration
    if not copyfast_bridge.bridge_configured():
        raise HTTPException(status_code=503, detail=f"{CORE_BRIDGE_UNCONFIGURED}: Core Bridge is not configured")

    # 4. Resolve source bytes from Asset Vault
    source_asset_id = str(job.get("image_asset_id") or "").strip()
    content_bytes, file_name, content_type, sha256_digest = resolve_source_asset_bytes(
        clean_account, source_asset_id
    )

    actor_id = _resolve_account_actor_id(clean_account)
    if not actor_id:
        raise HTTPException(status_code=401, detail="ACTOR_ID_REQUIRED: unable to resolve canonical actor")

    # 5. Bot Staging Request: POST /internal/v1/uploads
    # Reuses existing bot_upload_id if already staged (DUPLICATE_BOT_STAGING_ON_IDEMPOTENT_REPLAY=NO)
    bot_upload_id = str(envelope_meta.get("bot_upload_id") or "").strip()
    if not bot_upload_id or not bot_upload_id.startswith("upl_"):
        staging_idempotency_key = f"stage_imgxf_{clean_job_id}_{sha256_digest[:16]}"
        staging_payload = {
            "file_name": file_name,
            "content_type": content_type,
            "content_base64": base64.b64encode(content_bytes).decode("ascii"),
            "sha256": sha256_digest,
            "idempotency_key": staging_idempotency_key,
        }

        upload_res = await copyfast_bridge.bridge_request(
            "POST",
            BOT_PRIVATE_UPLOAD_ROUTE,
            payload=staging_payload,
            actor_id=actor_id,
        )

        if not upload_res.get("ok"):
            error_code = upload_res.get("error_code") or "BOT_UPLOAD_FAILED"
            msg = upload_res.get("message") or "Staged upload rejected by Bot"
            raise HTTPException(status_code=502, detail=f"{BOT_UPLOAD_REJECTED}: {error_code} - {msg}")

        upload_data = upload_res.get("data") if isinstance(upload_res.get("data"), dict) else {}
        bot_upload_id = str(upload_data.get("upload_id") or upload_res.get("upload_id") or "").strip()
        if not bot_upload_id or not bot_upload_id.startswith("upl_"):
            raise HTTPException(status_code=502, detail=f"{BOT_UPLOAD_REJECTED}: Bot response missing valid upload_id")

        # Verify WEB_TO_BOT_STAGED_BYTES_SHA_MATCH=YES
        bot_sha = str(upload_data.get("sha256") or upload_res.get("sha256") or "").strip().lower()
        if not bot_sha or bot_sha != sha256_digest.lower():
            raise HTTPException(
                status_code=502,
                detail=f"{BOT_UPLOAD_REJECTED}: SHA256 mismatch between Web bytes and Bot staging (web={sha256_digest}, bot={bot_sha})",
            )

        # Durably record staged upload_id immediately so that if prepare fails transiently,
        # subsequent retry does not duplicate staging.
        envelope_meta["bot_upload_id"] = bot_upload_id
        envelope_meta["source_asset_id"] = source_asset_id
        envelope_meta["source_sha256"] = sha256_digest
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_image_transform_jobs
                SET bridge_envelope = ?,
                    updated_at = ?
                WHERE id = ? AND account_id = ?;
                """,
                (
                    json.dumps(sanitize_external_metadata(envelope_meta), ensure_ascii=False),
                    utc_now(),
                    clean_job_id,
                    clean_account,
                ),
            )

    # 6. Bot Prepare Request: POST /internal/v1/web-image-transform/prepare
    prepare_payload = {
        "upload_id": bot_upload_id,
        "transform_instruction": str(job.get("transform_instruction") or ""),
        "aspect_ratio": str(job.get("aspect_ratio") or "1:1"),
    }

    prepare_res = await copyfast_bridge.bridge_request(
        "POST",
        BOT_PRIVATE_PREPARE_ROUTE,
        payload=prepare_payload,
        actor_id=actor_id,
    )

    if not prepare_res.get("ok"):
        error_code = prepare_res.get("error_code") or "BOT_PREPARE_FAILED"
        msg = prepare_res.get("message") or "Prepare rejected by Bot"
        raise HTTPException(status_code=502, detail=f"{BOT_PREPARE_REJECTED}: {error_code} - {msg}")

    prepare_data = prepare_res.get("data") if isinstance(prepare_res.get("data"), dict) else {}

    # 7. Validate Bot Prepare Response
    bot_status = str(prepare_data.get("status") or prepare_res.get("status") or "").strip()
    bot_status_reason = str(prepare_data.get("status_reason") or prepare_res.get("status_reason") or "").strip()
    bot_capability = str(prepare_data.get("capability") or prepare_res.get("capability") or "").strip()
    bot_executor_owner = str(prepare_data.get("executor_owner") or prepare_res.get("executor_owner") or "").strip()
    bot_provider_family = str(prepare_data.get("provider_family") or prepare_res.get("provider_family") or "").strip()
    bot_execution_allowed = bool(prepare_data.get("provider_execution_allowed", prepare_res.get("provider_execution_allowed", True)))
    bot_ret_upload_id = str(prepare_data.get("upload_id") or prepare_res.get("upload_id") or "").strip()
    bot_owner_id = str(prepare_data.get("owner_id") or prepare_res.get("owner_id") or "").strip()
    bot_blockers = list(prepare_data.get("blockers") or prepare_res.get("blockers") or [])

    # Contract Invariants:
    # - status must be PREPARED_PROVIDER_DISABLED
    # - provider_execution_allowed must be False
    # - capability must be image_transform
    # - executor_owner must be bot
    # - upload_id must match staged upload_id
    # - owner_id must match canonical actor_id
    if bot_status != STATUS_PREPARED_PROVIDER_DISABLED:
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_PREPARE_CONTRACT_INVALID}: unexpected status '{bot_status}', expected '{STATUS_PREPARED_PROVIDER_DISABLED}'",
        )
    if bot_execution_allowed is not False:
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_PREPARE_CONTRACT_INVALID}: provider_execution_allowed must be false",
        )
    if bot_capability != "image_transform":
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_PREPARE_CONTRACT_INVALID}: capability must be 'image_transform'",
        )
    if bot_executor_owner != "bot":
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_PREPARE_CONTRACT_INVALID}: executor_owner must be 'bot'",
        )
    if bot_ret_upload_id != bot_upload_id:
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_PREPARE_CONTRACT_INVALID}: upload_id mismatch (staged={bot_upload_id}, ret={bot_ret_upload_id})",
        )
    if bot_owner_id and bot_owner_id != actor_id:
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_UPLOAD_OWNER_MISMATCH}: owner_id mismatch (actor={actor_id}, ret={bot_owner_id})",
        )

    # Reject unexpected provider/execution artifacts
    unexpected_keys = {"provider_task_id", "output_url", "output", "result", "wallet", "xu_charged", "charged_xu", "local_path", "file_path"}
    found_unexpected = unexpected_keys.intersection(prepare_data.keys()).union(unexpected_keys.intersection(prepare_res.keys()))
    if found_unexpected:
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_PREPARE_CONTRACT_INVALID}: unexpected authority fields returned: {sorted(found_unexpected)}",
        )
    if prepare_data.get("paid") is True or prepare_res.get("paid") is True:
        raise HTTPException(
            status_code=502,
            detail=f"{BOT_PREPARE_CONTRACT_INVALID}: unexpected paid=True during prepare phase",
        )

    # 8. Persist durable Web bridge truth into SQLite
    now = utc_now()
    updated_envelope = dict(envelope_meta)
    updated_envelope.update({
        "canonical_product_key": CANONICAL_PRODUCT_KEY,
        "canonical_route_id": CANONICAL_ROUTE_ID,
        "customer_entrypoint": CANONICAL_CUSTOMER_ENTRYPOINT,
        "account_id": clean_account,
        "source_asset_id": source_asset_id,
        "source_sha256": sha256_digest,
        "bot_upload_id": bot_upload_id,
        "bot_prepare_status": bot_status,
        "bot_prepare_reason": bot_status_reason or STATUS_REASON_UNPROVEN,
        "bot_executor_owner": bot_executor_owner,
        "bot_provider_family": bot_provider_family,
        "blockers": bot_blockers,
        "prepared_at": now,
        "provider_calls_made": 0,
        "paid_calls_made": 0,
    })
    clean_envelope = sanitize_external_metadata(updated_envelope)

    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_image_transform_jobs
            SET status = ?,
                status_reason = ?,
                bridge_envelope = ?,
                updated_at = ?
            WHERE id = ? AND account_id = ?;
            """,
            (
                STATUS_QUEUED,
                STATUS_REASON_UNPROVEN,
                json.dumps(clean_envelope, ensure_ascii=False),
                now,
                clean_job_id,
                clean_account,
            ),
        )

    updated_job = get_image_transform_job(clean_account, clean_job_id)
    return {
        "ok": True,
        "job_id": clean_job_id,
        "status": STATUS_QUEUED,
        "status_reason": STATUS_REASON_UNPROVEN,
        "bot_upload_id": bot_upload_id,
        "bot_prepare_status": bot_status,
        "bot_prepare_reason": bot_status_reason or STATUS_REASON_UNPROVEN,
        "provider_execution_allowed": False,
        "blockers": bot_blockers,
        "idempotent_replay": False,
        "job": updated_job,
    }
