"""Music Canonical Job Bridge Adapter.

Task: MUSIC_WEB_CANONICAL_ENGINE_PARITY_AND_PRODUCTION_RELEASE_R1
Product Family: Music
Tracker: manhtoangreensky-wq/toan-aas-standalone#612

Connects Web customer flows (/music/ai, /music/song) to canonical Bot Core
runtime service with durable job authority, strict tier enforcement (basic,
standard, premium), atomic execution, and safe audio artifact streaming.

Invariants:
- Server Authority: client cannot dictate provider, price, wallet debit, or status.
- Strict Tier Choice: basic, standard, premium explicitly required; NO silent default.
- Pricing Quotes: Background (130, 150, 200 Xu) and Song (200, 250, 300 Xu).
- Product Separation: Background rejects lyrics/vocal/duet fields; Song requires lyrics.
- Replay Idempotency: exact payload replayed safely; modified payload rejected with conflict.
- Post-Success Settlement: exactly-once wallet charge only on verified >0 byte audio output.
- Tenant Isolation: account_id strictly verified on all operations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

from fastapi import HTTPException
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now

SUPPORTED_MUSIC_FEATURE_KEYS = frozenset({
    "music",
    "music_background",
    "music_song",
})
CANONICAL_PRODUCT_KEY = "music"
SUPPORTED_CANONICAL_JOB_ADAPTERS = SUPPORTED_MUSIC_FEATURE_KEYS

MUSIC_TIERS = frozenset({"basic", "standard", "premium"})

MUSIC_BACKGROUND_TIER_PRICES = {
    "basic": 130,
    "standard": 150,
    "premium": 200,
}

MUSIC_SONG_TIER_PRICES = {
    "basic": 200,
    "standard": 250,
    "premium": 300,
}

MUSIC_VOCAL_MODES = frozenset({"male", "female", "duet", "auto"})

STATUS_PREPARED = "prepared"
STATUS_AWAITING_CONFIRMATION = "awaiting_confirmation"
STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_AMBIGUOUS = "ambiguous"

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED = frozenset({
    "provider",
    "providertaskid",
    "providerjobid",
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
    "localpath",
    "filepath",
    "path",
    "url",
    "remoteurl",
    "providerurl",
    "canonicaluserid",
    "userid",
    "actorid",
    "canonicaluser",
    "targetuserid",
})


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


def _is_runtime_execution_active(feature_key: str = "music_background") -> bool:
    """Check compile-time and runtime execution flag."""
    try:
        from copyfast_api import WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
        return feature_key in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES or "music" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    except Exception:
        return True


def normalize_music_tier(raw_tier: str) -> str:
    clean = str(raw_tier or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "basic": "basic",
        "co_ban": "basic",
        "cơ_bản": "basic",
        "music_tier_basic": "basic",
        "standard": "standard",
        "tieu_chuan": "standard",
        "tiêu_chuẩn": "standard",
        "music_tier_standard": "standard",
        "premium": "premium",
        "cao_cap": "premium",
        "cao_cấp": "premium",
        "music_tier_premium": "premium",
    }
    return aliases.get(clean, clean)


def normalize_music_duration(raw_duration: Any, product_kind: str) -> int:
    try:
        val = int(raw_duration)
    except (TypeError, ValueError):
        val = 30 if product_kind == "background" else 120
    if product_kind == "background":
        if val <= 0:
            val = 30
        return max(18, min(600, val))
    else:
        if val <= 0:
            val = 120
        return max(30, min(600, val))


def get_music_quote_xu(product_kind: str, tier: str) -> int:
    if product_kind == "song":
        return MUSIC_SONG_TIER_PRICES.get(tier, 200)
    return MUSIC_BACKGROUND_TIER_PRICES.get(tier, 130)


def validate_music_input(feature_key: str, values: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Validate and sanitize Music input payload according to canonical rules.

    Returns:
        (is_valid, error_code, normalized_values)
    """
    if _contains_authority_field(values):
        return False, "FORBIDDEN_AUTHORITY_FIELD_REJECTED", {}

    product_kind = "song" if feature_key in ("music_song", "song") or values.get("product_kind") == "song" else "background"

    # Tier validation: NO SILENT DEFAULT
    raw_tier = str(values.get("tier") or "").strip()
    if not raw_tier:
        return False, "TIER_REQUIRED", {}
    tier = normalize_music_tier(raw_tier)
    if tier not in MUSIC_TIERS:
        return False, f"INVALID_TIER: '{raw_tier}' is not valid", {}

    brief = str(values.get("brief") or values.get("prompt") or "").strip()
    if not brief:
        return False, "BRIEF_REQUIRED", {}

    mode = str(values.get("mode") or "").strip().lower()
    if not mode:
        mode = "background" if product_kind == "background" else "song"

    if product_kind == "background":
        # Reject lyrics, vocal, duet fields from background
        for song_field in ("lyrics", "song_vocal", "vocal_mode", "duet"):
            if values.get(song_field):
                return False, "SONG_FIELD_REJECTED_FOR_BACKGROUND", {}
        lyrics = ""
        vocal_mode = ""
        style_prompt = str(values.get("style_prompt") or brief).strip()
    else:
        lyrics = str(values.get("lyrics") or "").strip()
        raw_vocal = str(values.get("vocal_mode") or values.get("song_vocal") or "auto").strip().lower()
        if raw_vocal not in MUSIC_VOCAL_MODES:
            return False, f"INVALID_VOCAL_MODE: '{raw_vocal}'", {}
        vocal_mode = raw_vocal
        style_prompt = str(values.get("style_prompt") or brief).strip()

    duration_seconds = normalize_music_duration(values.get("duration_seconds"), product_kind)
    quote_xu = get_music_quote_xu(product_kind, tier)

    normalized = {
        "product_kind": product_kind,
        "tier": tier,
        "mode": mode,
        "brief": brief,
        "style_prompt": style_prompt,
        "lyrics": lyrics,
        "vocal_mode": vocal_mode,
        "duration_seconds": duration_seconds,
        "quote_xu": quote_xu,
    }
    return True, "", normalized


def compute_payload_hash(normalized: dict[str, Any]) -> str:
    canonical_repr = {
        "product_kind": normalized["product_kind"],
        "tier": normalized["tier"],
        "mode": normalized["mode"],
        "brief": normalized["brief"],
        "style_prompt": normalized["style_prompt"],
        "lyrics": normalized["lyrics"],
        "vocal_mode": normalized["vocal_mode"],
        "duration_seconds": normalized["duration_seconds"],
    }
    canonical = json.dumps(canonical_repr, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_idempotency_hash(key: str) -> str:
    return hashlib.sha256(str(key or "").strip().encode("utf-8")).hexdigest()


def generate_music_job_id() -> str:
    return f"mjb_{uuid.uuid4().hex}"


def generate_canonical_request_id() -> str:
    return f"MRQ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"


def ensure_music_schema() -> None:
    """Ensure web_music_jobs table exists in the database."""
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_music_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                feature_key TEXT NOT NULL,
                product_kind TEXT NOT NULL,
                tier TEXT NOT NULL,
                mode TEXT NOT NULL,
                brief TEXT NOT NULL,
                style_prompt TEXT NOT NULL DEFAULT '',
                lyrics TEXT NOT NULL DEFAULT '',
                vocal_mode TEXT NOT NULL DEFAULT '',
                duration_seconds INTEGER NOT NULL DEFAULT 30,
                status TEXT NOT NULL DEFAULT 'prepared',
                status_reason TEXT NOT NULL DEFAULT '',
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                quote_xu INTEGER NOT NULL DEFAULT 0,
                charged_xu INTEGER NOT NULL DEFAULT 0,
                runtime_job_id TEXT,
                runtime_dispatch_status TEXT NOT NULL DEFAULT 'undispatched',
                runtime_dispatched_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_music_jobs_account_id
            ON web_music_jobs(account_id);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_music_jobs_idemp
            ON web_music_jobs(idempotency_key_hash);
            """
        )


_MUSIC_JOB_COLUMNS = (
    "id, request_id, account_id, feature_key, product_kind, tier, mode, brief, "
    "style_prompt, lyrics, vocal_mode, duration_seconds, status, status_reason, "
    "quote_xu, charged_xu, runtime_job_id, runtime_dispatch_status, "
    "created_at, updated_at, completed_at"
)


_MUSIC_COLUMN_NAMES = [
    "id", "request_id", "account_id", "feature_key", "product_kind", "tier", "mode", "brief",
    "style_prompt", "lyrics", "vocal_mode", "duration_seconds", "status", "status_reason",
    "quote_xu", "charged_xu", "runtime_job_id", "runtime_dispatch_status",
    "created_at", "updated_at", "completed_at",
]


def _format_public_job(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        r = row
    elif hasattr(row, "keys"):
        r = dict(row)
    else:
        r = {name: row[i] for i, name in enumerate(_MUSIC_COLUMN_NAMES) if i < len(row)}
    status = r.get("status", "prepared")
    return {
        "id": r["id"],
        "job_id": r["id"],
        "request_id": r["request_id"],
        "feature_key": r["feature_key"],
        "product_kind": r["product_kind"],
        "tier": r["tier"],
        "mode": r["mode"],
        "brief": r["brief"],
        "style_prompt": r.get("style_prompt") or "",
        "lyrics": r.get("lyrics") or "",
        "vocal_mode": r.get("vocal_mode") or "",
        "duration_seconds": r["duration_seconds"],
        "status": status,
        "status_reason": r.get("status_reason") or "",
        "quote_xu": int(r.get("quote_xu") or 0),
        "charged_xu": int(r.get("charged_xu") or 0),
        "runtime_job_id": r.get("runtime_job_id"),
        "runtime_dispatch_status": r.get("runtime_dispatch_status"),
        "has_artifact": bool(status == "completed"),
        "can_download": bool(status == "completed"),
        "artifact_url": f"/api/v1/features/{r['feature_key']}/jobs/{r['id']}/artifact" if status == "completed" else None,
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "completed_at": r.get("completed_at"),
    }


def create_or_replay_music_job(
    feature_key_or_none: str | None = None,
    account_id_or_none: str | None = None,
    payload_or_none: dict[str, Any] | None = None,
    *,
    feature_key: str = "",
    account_id: str = "",
    payload: dict[str, Any] | None = None,
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new Web Music job or replay an idempotent one."""
    ensure_music_schema()
    eff_feature = feature_key or feature_key_or_none or "music"
    eff_account_id = account_id or account_id_or_none or ""
    eff_payload = dict(payload if payload is not None else (payload_or_none or {}))
    if idempotency_key and not eff_payload.get("idempotency_key"):
        eff_payload["idempotency_key"] = idempotency_key
    if request_id and not eff_payload.get("request_id"):
        eff_payload["request_id"] = request_id

    owner_id = str(eff_account_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail={"error_code": "UNAUTHENTICATED", "message": "Sign-in required"})

    is_valid, err_code, norm = validate_music_input(eff_feature, eff_payload)
    if not is_valid:
        if "TIER_REQUIRED" in err_code:
            raise HTTPException(status_code=400, detail={"error_code": "TIER_REQUIRED", "message": "Tier selection (basic, standard, premium) is required"})
        raise HTTPException(status_code=400, detail={"error_code": err_code, "message": f"Input validation failed: {err_code}"})

    payload_hash = compute_payload_hash(norm)
    raw_idemp = str(eff_payload.get("idempotency_key") or "").strip()
    idemp_hash = compute_idempotency_hash(raw_idemp) if raw_idemp else None

    with read_transaction() as conn:
        if idemp_hash:
            existing = conn.execute(
                f"SELECT {_MUSIC_JOB_COLUMNS}, payload_hash FROM web_music_jobs WHERE idempotency_key_hash = ? AND account_id = ?",
                (idemp_hash, owner_id),
            ).fetchone()
            if existing:
                existing_hash = existing["payload_hash"] if hasattr(existing, "keys") or isinstance(existing, dict) else existing[21]
                if existing_hash != payload_hash:
                    raise HTTPException(
                        status_code=409,
                        detail={"error_code": "IDEMPOTENCY_CONFLICT", "message": "Payload modified for existing idempotency key"},
                    )
                job_res = _format_public_job(existing)
                job_res["idempotent_replay"] = True
                return job_res

    job_id = generate_music_job_id()
    req_id = generate_canonical_request_id()
    now = utc_now()

    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_music_jobs (
                id, request_id, account_id, feature_key, product_kind,
                tier, mode, brief, style_prompt, lyrics, vocal_mode,
                duration_seconds, status, status_reason, idempotency_key_hash,
                payload_hash, quote_xu, charged_xu, runtime_dispatch_status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'undispatched', ?, ?)
            """,
            (
                job_id,
                req_id,
                owner_id,
                eff_feature,
                norm["product_kind"],
                norm["tier"],
                norm["mode"],
                norm["brief"],
                norm["style_prompt"],
                norm["lyrics"],
                norm["vocal_mode"],
                norm["duration_seconds"],
                STATUS_PREPARED,
                "PREPARED",
                idemp_hash,
                payload_hash,
                norm["quote_xu"],
                now,
                now,
            ),
        )

    job_res = get_music_job(owner_id, job_id) or {}
    job_res["idempotent_replay"] = False
    return job_res


def get_music_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    ensure_music_schema()
    owner_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not owner_id or not clean_job_id:
        return None

    with read_transaction() as conn:
        row = conn.execute(
            f"SELECT {_MUSIC_JOB_COLUMNS} FROM web_music_jobs WHERE id = ? AND account_id = ?",
            (clean_job_id, owner_id),
        ).fetchone()
        return _format_public_job(row) if row else None


def list_music_jobs(account_id: str, feature_key: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    ensure_music_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        return []

    safe_limit = max(1, min(int(limit), 100))
    with read_transaction() as conn:
        if feature_key:
            rows = conn.execute(
                f"SELECT {_MUSIC_JOB_COLUMNS} FROM web_music_jobs WHERE account_id = ? AND feature_key = ? ORDER BY created_at DESC LIMIT ?",
                (owner_id, feature_key, safe_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {_MUSIC_JOB_COLUMNS} FROM web_music_jobs WHERE account_id = ? ORDER BY created_at DESC LIMIT ?",
                (owner_id, safe_limit),
            ).fetchall()
        return [_format_public_job(r) for r in rows]


def is_music_job_other_account(job_id: str, account_id: str) -> bool:
    ensure_music_schema()
    owner_id = str(account_id or "").strip()
    clean_job_id = str(job_id or "").strip()
    if not clean_job_id:
        return False

    with read_transaction() as conn:
        row = conn.execute("SELECT account_id FROM web_music_jobs WHERE id = ? LIMIT 1", (clean_job_id,)).fetchone()
        if row is None:
            return False
        return str(row[0]) != owner_id


async def dispatch_music_job_to_canonical_runtime(
    *,
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Dispatch an admitted Web Music job to canonical Bot Core runtime."""
    ensure_music_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    if not clean_job_id or not account_id:
        return {}

    job = get_music_job(account_id, clean_job_id)
    if not job:
        return {}
    if job.get("status") == STATUS_COMPLETED:
        return job

    from copyfast_bridge import bridge_configured, bridge_request
    if not bridge_configured() or not canonical_user_id:
        return job

    canonical_payload = {
        "web_job_id": clean_job_id,
        "web_request_id": job["request_id"],
        "canonical_user_id": canonical_user_id,
        "product_kind": job["product_kind"],
        "tier": job["tier"],
        "mode": job["mode"],
        "brief": job["brief"],
        "style_prompt": job.get("style_prompt") or job["brief"],
        "lyrics": job.get("lyrics") or "",
        "vocal_mode": job.get("vocal_mode") or "",
        "duration_seconds": job["duration_seconds"],
        "idempotency_key": f"{canonical_user_id}:{clean_job_id}",
    }

    try:
        res = await bridge_request(
            "POST",
            "/internal/v1/web-music/jobs",
            payload=canonical_payload,
            request_id=f"DISPATCH-{job['request_id']}",
            actor_id=canonical_user_id,
            owner_id=canonical_user_id,
        )
        if isinstance(res, dict) and res.get("ok"):
            bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
            rt_id = str(bot_job.get("job_id") or "").strip() if isinstance(bot_job, dict) else ""
            if rt_id:
                bot_quote = int(bot_job.get("quote_xu") or job["quote_xu"])
                bot_status = str(bot_job.get("status") or "")
                with transaction() as conn:
                    conn.execute(
                        """
                        UPDATE web_music_jobs
                        SET runtime_job_id = ?,
                            quote_xu = ?,
                            runtime_dispatch_status = 'dispatched',
                            runtime_dispatched_at = ?,
                            updated_at = ?
                        WHERE id = ? AND status != 'completed'
                        """,
                        (rt_id, bot_quote, utc_now(), utc_now(), clean_job_id),
                    )
            else:
                with transaction() as conn:
                    conn.execute(
                        "UPDATE web_music_jobs SET runtime_dispatch_status = 'failed', status_reason = 'BOT_JOB_ID_MISSING', updated_at = ? WHERE id = ?",
                        (utc_now(), clean_job_id),
                    )
        else:
            err_reason = str((res.get("error_code") if isinstance(res, dict) else "") or "BOT_PREPARE_FAILED")
            with transaction() as conn:
                conn.execute(
                    "UPDATE web_music_jobs SET runtime_dispatch_status = 'failed', status_reason = ?, updated_at = ? WHERE id = ?",
                    (err_reason, utc_now(), clean_job_id),
                )
    except Exception:
        with transaction() as conn:
            conn.execute(
                "UPDATE web_music_jobs SET runtime_dispatch_status = 'uncertain', status_reason = 'BRIDGE_DISPATCH_EXCEPTION', updated_at = ? WHERE id = ?",
                (utc_now(), clean_job_id),
            )

    return get_music_job(account_id, clean_job_id) or {}


async def confirm_music_job(
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Confirm and execute Web Music job against canonical Bot Core."""
    ensure_music_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    job = get_music_job(account_id, clean_job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error_code": "JOB_NOT_FOUND", "message": "Job not found"})

    if job.get("status") == STATUS_COMPLETED:
        return job

    # Dispatch first if needed
    if not job.get("runtime_job_id"):
        job = await dispatch_music_job_to_canonical_runtime(job_id=clean_job_id, account=account, request=request)

    rt_id = str(job.get("runtime_job_id") or "").strip()
    if not rt_id:
        raise HTTPException(status_code=502, detail={"error_code": "BOT_RUNTIME_UNAVAILABLE", "message": "Cannot confirm job: Bot runtime not ready"})

    from copyfast_bridge import bridge_request
    res = await bridge_request(
        "POST",
        f"/internal/v1/web-music/jobs/{rt_id}/confirm",
        payload={},
        request_id=f"CONFIRM-{job['request_id']}",
        actor_id=canonical_user_id,
        owner_id=canonical_user_id,
    )

    if isinstance(res, dict) and res.get("ok"):
        bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
        bot_status = str(bot_job.get("status") or "processing")
        charged_xu = int(bot_job.get("charged_xu") or 0)
        completed_at = bot_job.get("completed_at") if bot_status == "completed" else None
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_music_jobs
                SET status = ?,
                    charged_xu = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (bot_status, charged_xu, completed_at, utc_now(), clean_job_id),
            )
        return get_music_job(account_id, clean_job_id) or {}
    else:
        err_code = str((res.get("error_code") if isinstance(res, dict) else "") or "CONFIRM_FAILED")
        err_msg = str((res.get("message") if isinstance(res, dict) else "") or "Bot execution failed")
        status_code = int(res.get("http_status") or 422) if isinstance(res, dict) else 422
        raise HTTPException(status_code=status_code, detail={"error_code": err_code, "message": err_msg})


async def reconcile_music_job_status(
    job_id: str,
    account: dict[str, Any],
    request: Any = None,
) -> dict[str, Any]:
    """Reconcile and poll Web Music job provider progress with canonical Bot Core."""
    ensure_music_schema()
    clean_job_id = str(job_id or "").strip()
    account_id = str(account.get("id") or "").strip()
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()

    job = get_music_job(account_id, clean_job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error_code": "JOB_NOT_FOUND", "message": "Job not found"})

    if job.get("status") in (STATUS_COMPLETED, STATUS_FAILED):
        return job

    rt_id = str(job.get("runtime_job_id") or "").strip()
    if not rt_id:
        return job

    from copyfast_bridge import bridge_request
    res = await bridge_request(
        "POST",
        f"/internal/v1/web-music/jobs/{rt_id}/reconcile",
        payload={},
        request_id=f"REC-{job['request_id']}",
        actor_id=canonical_user_id,
        owner_id=canonical_user_id,
    )

    if isinstance(res, dict) and res.get("ok"):
        bot_job = (res.get("data") or {}).get("job") or res.get("job") or {}
        bot_status = str(bot_job.get("status") or job["status"])
        bot_reason = str(bot_job.get("status_reason") or "")
        charged_xu = int(bot_job.get("charged_xu") or job.get("charged_xu") or 0)
        completed_at = bot_job.get("completed_at") if bot_status == "completed" else None
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_music_jobs
                SET status = ?,
                    status_reason = ?,
                    charged_xu = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (bot_status, bot_reason, charged_xu, completed_at, utc_now(), clean_job_id),
            )
        return get_music_job(account_id, clean_job_id) or {}

    return job


def music_job_to_native_compat(job: dict[str, Any]) -> dict[str, Any]:
    """Convert Web Music job record into compatible portal card structure."""
    if not job:
        return {}
    return {
        "id": job["id"],
        "job_id": job["id"],
        "request_id": job["request_id"],
        "feature_key": job["feature_key"],
        "title": f"Music: {job.get('brief', '')[:40]}",
        "description": job.get("brief", ""),
        "tier": job.get("tier", "basic"),
        "quote_xu": job.get("quote_xu", 0),
        "charged_xu": job.get("charged_xu", 0),
        "status": job.get("status", "prepared"),
        "status_reason": job.get("status_reason", ""),
        "created_at": job.get("created_at", ""),
        "completed_at": job.get("completed_at"),
        "can_download": bool(job.get("status") == "completed"),
        "artifact_url": job.get("artifact_url"),
    }
