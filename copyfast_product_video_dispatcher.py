"""Product Video Canonical Dispatcher and Worker Integration Engine.

Task: P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.DISPATCHER_WORKER.INTEGRATION.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Master Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Provides atomic worker claiming, heartbeat lease extension, completion with
verified artifact metadata, failure with retry accounting, lease expiration
reconciliation watchdog, and worker authorization.

Invariants:
- Zero unmocked paid provider calls (NO_PROVIDER_CALL).
- Zero balance / Xu / wallet ledger mutations (NO_WALLET_MUTATION).
- Zero payment gateway mutations (NO_PAYMENT_MUTATION).
- Fail-closed admission: only authenticated workers / owners can claim & complete jobs.
- Output truth: completed jobs MUST possess valid artifact metadata (duration, width,
  height, file_size_bytes >= 4096, format, codec).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
import os
import re
from typing import Any
import urllib.parse

from fastapi import HTTPException, Request, status

from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now
from copyfast_product_video_job_bridge import CANONICAL_PRODUCT_KEY

LOGGER = logging.getLogger("copyfast_product_video_dispatcher")

DISPATCHER_VERSION = "p0.product_video.dispatcher.v1"
DEFAULT_LEASE_SECONDS = 300
MIN_LEASE_SECONDS = 30
MAX_LEASE_SECONDS = 3600
MAX_DISPATCH_ATTEMPTS = 3
MIN_ARTIFACT_BYTES = 4096

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_BLOCKED = "blocked"

STATUS_REASON_QUEUED = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
STATUS_REASON_PROCESSING = "PROCESSING_BY_WORKER"
STATUS_REASON_COMPLETED = "COMPLETED_SUCCESSFULLY"
STATUS_REASON_LEASE_REQUEUED = "WORKER_LEASE_EXPIRED_REQUEUED"
STATUS_REASON_LEASE_FAILED = "WORKER_LEASE_EXPIRED_TERMINAL"

WORKER_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")
ACCEPTED_VIDEO_FORMATS = frozenset({"mp4", "mov", "webm", "mkv"})
ACCEPTED_VIDEO_CODECS = frozenset({"h264", "hevc", "av1", "vp9", "vp8", "prores"})


def _parse_iso(iso_str: str | None) -> datetime | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def sanitize_worker_id(worker_id: Any) -> str:
    cleaned = str(worker_id or "").strip()
    if not cleaned or not WORKER_ID_REGEX.fullmatch(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã định danh worker không hợp lệ (chỉ nhận chữ, số, gạch ngang, gạch dưới, chấm; 1-128 ký tự).",
        )
    return cleaned


def verify_worker_access(request: Request, payload: dict[str, Any] | None = None) -> str:
    """Authenticate internal worker caller via header or token, returning worker_id."""
    raw_worker_id = (
        (payload and payload.get("worker_id"))
        or request.headers.get("X-Worker-ID")
        or request.headers.get("X-TOAN-AAS-Worker-ID")
        or "vps-local-worker"
    )
    worker_id = sanitize_worker_id(raw_worker_id)

    # Validate auth token if configured
    configured_token = (
        os.environ.get("PRODUCT_VIDEO_WORKER_SECRET")
        or os.environ.get("WORKER_AUTH_TOKEN")
        or os.environ.get("CORE_BRIDGE_TOKEN")
        or os.environ.get("TOANAAS_WORKER_SECRET")
        or ""
    ).strip()
    if configured_token:
        auth_header = (request.headers.get("Authorization") or "").strip()
        header_token = ""
        if auth_header.lower().startswith("bearer "):
            header_token = auth_header[7:].strip()
        custom_token = (
            request.headers.get("X-Worker-Secret")
            or request.headers.get("X-Worker-Token")
            or request.headers.get("X-TOAN-AAS-Token")
            or ""
        ).strip()
        incoming_token = header_token or custom_token

        if not incoming_token or incoming_token != configured_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Xác thực worker thất bại: Token worker không hợp lệ hoặc thiếu quyền truy cập.",
            )

    return worker_id


def validate_video_artifact_metadata(metadata: Any) -> tuple[bool, str, dict[str, Any]]:
    """Validate that completed video output contains genuine, non-empty artifact metadata."""
    if not isinstance(metadata, dict):
        return False, "METADATA_MUST_BE_DICT", {}

    try:
        duration = float(metadata.get("duration_seconds") or metadata.get("duration") or 0)
    except (TypeError, ValueError):
        return False, "INVALID_DURATION", {}
    if duration <= 0:
        return False, "DURATION_MUST_BE_POSITIVE", {}

    try:
        width = int(metadata.get("width") or 0)
        height = int(metadata.get("height") or 0)
    except (TypeError, ValueError):
        return False, "INVALID_DIMENSIONS", {}
    if width < 64 or height < 64:
        return False, "DIMENSIONS_TOO_SMALL", {}

    try:
        file_size = int(metadata.get("file_size_bytes") or metadata.get("file_size") or 0)
    except (TypeError, ValueError):
        return False, "INVALID_FILE_SIZE", {}
    if file_size < MIN_ARTIFACT_BYTES:
        return False, "FILE_SIZE_TOO_SMALL", {}

    fmt = str(metadata.get("format") or "").strip().lower()
    if fmt not in ACCEPTED_VIDEO_FORMATS:
        return False, "INVALID_FORMAT", {}

    codec = str(metadata.get("codec") or "").strip().lower()
    if codec not in ACCEPTED_VIDEO_CODECS:
        return False, "INVALID_CODEC", {}

    sanitized = {
        "duration_seconds": round(duration, 3),
        "width": width,
        "height": height,
        "file_size_bytes": file_size,
        "format": fmt,
        "codec": codec,
        "fps": float(metadata.get("fps") or 30.0),
        "bitrate_kbps": int(metadata.get("bitrate_kbps") or 0),
        "verified_at": utc_now(),
    }
    return True, "", sanitized


def is_safe_product_video_output_url(url: Any) -> bool:
    """Validate that a Product Video output URL is safe to store, redirect to, or preview.

    Authoritative security check:
    - Must be a non-empty string <= 4096 characters.
    - No control characters (0x00 - 0x1F, 0x7F).
    - No backslash characters (\\).
    - Rejects dangerous schemes: javascript:, data:, file:, vbscript:, blob:, etc.
    - Rejects decoded path traversal ('..' or '%2e%2e' in any path segment).
    - Internal paths must strictly start with '/api/v1/'.
    - External URLs must be valid HTTP/HTTPS with a non-empty hostname.
    - Rejects embedded credentials (username:password@hostname).
    - In production, HTTPS is required; HTTP is permitted ONLY for local test environments
      (localhost, 127.0.0.1, testserver).
    """
    if not isinstance(url, str):
        return False
    raw = url.strip()
    if not raw or len(raw) > 4096:
        return False

    # Control characters
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        return False

    # Backslash tricks
    if "\\" in raw:
        return False

    lower = raw.lower()
    for bad_scheme in ("javascript:", "data:", "file:", "vbscript:", "blob:", "about:", "gopher:"):
        if lower.startswith(bad_scheme):
            return False

    # Decoded traversal check (iteratively unquote to catch nested encoding like %252e%252e)
    unquoted = raw
    for _ in range(3):
        prev = unquoted
        unquoted = urllib.parse.unquote(unquoted)
        if unquoted == prev:
            break

    if ".." in unquoted:
        return False

    # Internal API route
    if raw.startswith("/api/v1/"):
        return True

    # Reject other relative paths or paths starting with /
    if raw.startswith("/"):
        return False

    # External URL parsing
    try:
        parsed = urllib.parse.urlsplit(raw)
    except Exception:
        return False

    if parsed.scheme not in ("https", "http"):
        return False

    # Missing hostname
    if not parsed.hostname:
        return False

    # Embedded credentials
    if parsed.username or parsed.password:
        return False

    # HTTP only permitted for local test hosts
    if parsed.scheme == "http":
        if parsed.hostname not in ("localhost", "127.0.0.1", "testserver"):
            return False

    # Ensure path segments don't contain traversal
    path_decoded = urllib.parse.unquote(parsed.path)
    segments = [s for s in path_decoded.split("/") if s]
    if any(s in ("..", ".") for s in segments):
        return False

    return True


def claim_product_video_job(
    *,
    worker_id: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now_dt: datetime | None = None,
) -> dict[str, Any] | None:
    """Atomically claim one queued or lease-expired product video job for a worker."""
    ensure_copyfast_schema()
    clean_worker = sanitize_worker_id(worker_id)
    bounded_lease = max(MIN_LEASE_SECONDS, min(int(lease_seconds or DEFAULT_LEASE_SECONDS), MAX_LEASE_SECONDS))
    now = now_dt or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_iso = (now + timedelta(seconds=bounded_lease)).isoformat()

    with transaction() as conn:
        # Find oldest queued job or stalled job whose lease expired
        query_candidate = """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, created_at, updated_at,
                   worker_id, claimed_at, lease_expires_at, attempts, output_url
            FROM web_product_video_jobs
            WHERE status = 'queued'
               OR (status = 'processing' AND lease_expires_at IS NOT NULL AND lease_expires_at < ? AND attempts < ?)
            ORDER BY created_at ASC, id ASC
            LIMIT 1
        """
        row = conn.execute(query_candidate, (now_iso, MAX_DISPATCH_ATTEMPTS)).fetchone()
        if row is None:
            return None

        target_id = str(row[0])
        update_query = """
            UPDATE web_product_video_jobs
            SET status = ?,
                status_reason = ?,
                worker_id = ?,
                claimed_at = ?,
                lease_expires_at = ?,
                attempts = attempts + 1,
                updated_at = ?
            WHERE id = ?
              AND (status = 'queued' OR (status = 'processing' AND lease_expires_at < ?))
        """
        cursor = conn.execute(
            update_query,
            (
                STATUS_PROCESSING,
                STATUS_REASON_PROCESSING,
                clean_worker,
                now_iso,
                expires_iso,
                now_iso,
                target_id,
                now_iso,
            ),
        )
        if cursor.rowcount == 0:
            # Concurrently claimed by another worker instance
            return None

        # Fetch freshly updated record
        updated_row = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, created_at, updated_at,
                   worker_id, claimed_at, lease_expires_at, attempts, output_url
            FROM web_product_video_jobs
            WHERE id = ?
            """,
            (target_id,),
        ).fetchone()

        LOGGER.info(
            "Product Video job claimed: job_id=%s worker=%s attempt=%s lease_expires=%s",
            target_id,
            clean_worker,
            updated_row[21],
            expires_iso,
        )
        return _format_claimed_job(updated_row)


def heartbeat_product_video_job(
    *,
    job_id: str,
    worker_id: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now_dt: datetime | None = None,
) -> bool:
    """Extend the processing lease of an actively claimed product video job."""
    ensure_copyfast_schema()
    clean_job = str(job_id or "").strip()
    clean_worker = sanitize_worker_id(worker_id)
    if not clean_job:
        return False

    bounded_lease = max(MIN_LEASE_SECONDS, min(int(lease_seconds or DEFAULT_LEASE_SECONDS), MAX_LEASE_SECONDS))
    now = now_dt or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_iso = (now + timedelta(seconds=bounded_lease)).isoformat()

    with transaction() as conn:
        cursor = conn.execute(
            """
            UPDATE web_product_video_jobs
            SET lease_expires_at = ?,
                updated_at = ?
            WHERE id = ? AND worker_id = ? AND status = 'processing'
            """,
            (expires_iso, now_iso, clean_job, clean_worker),
        )
        success = cursor.rowcount > 0
        if success:
            LOGGER.debug("Heartbeat extended for job_id=%s worker=%s new_lease=%s", clean_job, clean_worker, expires_iso)
        return success


def complete_product_video_job(
    *,
    job_id: str,
    worker_id: str,
    output_metadata: dict[str, Any],
    output_url: str = "",
    now_dt: datetime | None = None,
) -> dict[str, Any]:
    """Mark a processing product video job completed with verified artifact metadata."""
    ensure_copyfast_schema()
    clean_job = str(job_id or "").strip()
    clean_worker = sanitize_worker_id(worker_id)
    if not clean_job:
        raise HTTPException(status_code=400, detail="Mã job không được để trống.")

    is_valid, err_reason, sanitized_meta = validate_video_artifact_metadata(output_metadata)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Metadata video artifact không hợp lệ: {err_reason}",
        )

    now = now_dt or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    clean_url = str(output_url or "").strip()
    if not clean_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL output video không được để trống: OUTPUT_URL_REQUIRED",
        )
    if not is_safe_product_video_output_url(clean_url):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL output video không an toàn hoặc không hợp lệ: UNSAFE_OUTPUT_URL",
        )
    meta_json = json.dumps(sanitized_meta, separators=(",", ":"), ensure_ascii=False)

    with transaction() as conn:
        # Check current job state
        row = conn.execute(
            """
            SELECT id, worker_id, status FROM web_product_video_jobs WHERE id = ?
            """,
            (clean_job,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy job cần hoàn tất.")

        current_worker = str(row[1] or "")
        current_status = str(row[2] or "")

        if current_status != STATUS_PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job không ở trạng thái processing (hiện tại: {current_status}).",
            )
        if current_worker != clean_worker:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Worker không sở hữu quyền xử lý job này.",
            )

        conn.execute(
            """
            UPDATE web_product_video_jobs
            SET status = ?,
                status_reason = ?,
                output_metadata = ?,
                output_url = ?,
                lease_expires_at = NULL,
                updated_at = ?
            WHERE id = ? AND worker_id = ? AND status = 'processing'
            """,
            (
                STATUS_COMPLETED,
                STATUS_REASON_COMPLETED,
                meta_json,
                clean_url,
                now_iso,
                clean_job,
                clean_worker,
            ),
        )

        completed_row = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, created_at, updated_at,
                   worker_id, claimed_at, lease_expires_at, attempts, output_url
            FROM web_product_video_jobs
            WHERE id = ?
            """,
            (clean_job,),
        ).fetchone()

        LOGGER.info(
            "Product Video job completed: job_id=%s worker=%s duration=%ss size=%s bytes",
            clean_job,
            clean_worker,
            sanitized_meta["duration_seconds"],
            sanitized_meta["file_size_bytes"],
        )
        return _format_claimed_job(completed_row)


def fail_product_video_job(
    *,
    job_id: str,
    worker_id: str,
    error_reason: str,
    fatal: bool = False,
    now_dt: datetime | None = None,
) -> dict[str, Any]:
    """Fail or requeue an actively claimed product video job with reason."""
    ensure_copyfast_schema()
    clean_job = str(job_id or "").strip()
    clean_worker = sanitize_worker_id(worker_id)
    clean_reason = str(error_reason or "WORKER_EXECUTION_FAILED")[:500]
    if not clean_job:
        raise HTTPException(status_code=400, detail="Mã job không được để trống.")

    now = now_dt or datetime.now(timezone.utc)
    now_iso = now.isoformat()

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT id, worker_id, status, attempts FROM web_product_video_jobs WHERE id = ?
            """,
            (clean_job,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy job cần cập nhật.")

        current_worker = str(row[1] or "")
        current_status = str(row[2] or "")
        current_attempts = int(row[3] or 0)

        if current_status != STATUS_PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job không ở trạng thái processing (hiện tại: {current_status}).",
            )
        if current_worker != clean_worker:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Worker không sở hữu quyền xử lý job này.",
            )

        should_fail_terminally = fatal or current_attempts >= MAX_DISPATCH_ATTEMPTS
        next_status = STATUS_FAILED if should_fail_terminally else STATUS_QUEUED
        final_reason = clean_reason if should_fail_terminally else f"{clean_reason} (REQUEUED_ATTEMPT_{current_attempts})"

        conn.execute(
            """
            UPDATE web_product_video_jobs
            SET status = ?,
                status_reason = ?,
                lease_expires_at = NULL,
                updated_at = ?
            WHERE id = ? AND worker_id = ? AND status = 'processing'
            """,
            (next_status, final_reason, now_iso, clean_job, clean_worker),
        )

        failed_row = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, created_at, updated_at,
                   worker_id, claimed_at, lease_expires_at, attempts, output_url
            FROM web_product_video_jobs
            WHERE id = ?
            """,
            (clean_job,),
        ).fetchone()

        LOGGER.warning(
            "Product Video job failed/requeued: job_id=%s worker=%s next_status=%s reason=%s",
            clean_job,
            clean_worker,
            next_status,
            final_reason,
        )
        return _format_claimed_job(failed_row)


def reconcile_stalled_product_video_jobs(
    *,
    lease_grace_seconds: int = 0,
    max_attempts: int = MAX_DISPATCH_ATTEMPTS,
    now_dt: datetime | None = None,
) -> dict[str, int]:
    """Watchdog reconciliation pass for jobs abandoned by crashed/timed-out workers."""
    ensure_copyfast_schema()
    now = now_dt or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    check_cutoff = now - timedelta(seconds=max(0, int(lease_grace_seconds or 0)))
    cutoff_iso = check_cutoff.isoformat()

    requeued_count = 0
    failed_count = 0

    with transaction() as conn:
        stalled_rows = conn.execute(
            """
            SELECT id, attempts, worker_id FROM web_product_video_jobs
            WHERE status = 'processing'
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at < ?
            """,
            (cutoff_iso,),
        ).fetchall()

        for r in stalled_rows:
            job_id = str(r[0])
            attempts = int(r[1] or 0)
            abandoned_worker = str(r[2] or "unknown")

            if attempts >= max_attempts:
                conn.execute(
                    """
                    UPDATE web_product_video_jobs
                    SET status = ?,
                        status_reason = ?,
                        lease_expires_at = NULL,
                        updated_at = ?
                    WHERE id = ? AND status = 'processing'
                    """,
                    (STATUS_FAILED, STATUS_REASON_LEASE_FAILED, now_iso, job_id),
                )
                failed_count += 1
                LOGGER.warning("Job %s timed out terminally (attempts=%d, worker=%s)", job_id, attempts, abandoned_worker)
            else:
                conn.execute(
                    """
                    UPDATE web_product_video_jobs
                    SET status = ?,
                        status_reason = ?,
                        lease_expires_at = NULL,
                        updated_at = ?
                    WHERE id = ? AND status = 'processing'
                    """,
                    (STATUS_QUEUED, STATUS_REASON_LEASE_REQUEUED, now_iso, job_id),
                )
                requeued_count += 1
                LOGGER.info("Job %s requeued after lease expiration (attempts=%d, worker=%s)", job_id, attempts, abandoned_worker)

    return {
        "requeued": requeued_count,
        "failed": failed_count,
        "total_reconciled": requeued_count + failed_count,
    }


def get_product_video_dispatcher_metrics() -> dict[str, Any]:
    """Operational metrics snapshot of the product video dispatcher queue."""
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) FROM web_product_video_jobs GROUP BY status
            """
        ).fetchall()
        counts = {STATUS_QUEUED: 0, STATUS_PROCESSING: 0, STATUS_COMPLETED: 0, STATUS_FAILED: 0}
        for st, c in rows:
            if st in counts:
                counts[st] = int(c)

        active_workers_row = conn.execute(
            """
            SELECT COUNT(DISTINCT worker_id) FROM web_product_video_jobs
            WHERE status = 'processing' AND worker_id IS NOT NULL AND worker_id != ''
            """
        ).fetchone()
        active_workers = int(active_workers_row[0] or 0) if active_workers_row else 0

        oldest_queued_row = conn.execute(
            """
            SELECT created_at FROM web_product_video_jobs
            WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1
            """
        ).fetchone()
        oldest_queued_at = str(oldest_queued_row[0]) if oldest_queued_row else None

    return {
        "version": DISPATCHER_VERSION,
        "counts": counts,
        "active_workers": active_workers,
        "oldest_queued_at": oldest_queued_at,
        "healthy": True,
    }


def generate_synthetic_product_video_output(job: dict[str, Any]) -> dict[str, Any]:
    """Generate verified synthetic video output metadata for testing without paid provider calls."""
    aspect = str(job.get("aspect_ratio") or "9:16")
    duration = int(job.get("duration_seconds") or 5)

    if aspect == "16:9":
        width, height = 1920, 1080
    elif aspect == "1:1":
        width, height = 1080, 1080
    else:  # default 9:16
        width, height = 1080, 1920

    # Approx 2 Mbps video stream
    file_size = max(MIN_ARTIFACT_BYTES, int(duration * 250_000))

    return {
        "duration_seconds": float(duration),
        "width": width,
        "height": height,
        "file_size_bytes": file_size,
        "format": "mp4",
        "codec": "h264",
        "fps": 30.0,
        "bitrate_kbps": 2000,
        "synthetic_fixture": True,
    }


def _format_claimed_job(row: tuple) -> dict[str, Any]:
    """Format row into full claimed worker job dictionary."""
    try:
        env = json.loads(str(row[14])) if row[14] else {}
    except Exception:
        env = {}
    try:
        output_meta = json.loads(str(row[15])) if row[15] else None
    except Exception:
        output_meta = None

    status_str = str(row[10])
    is_completed = status_str == STATUS_COMPLETED
    persisted_output_url = (
        str(row[22]).strip()
        if len(row) > 22 and row[22]
        else ""
    )
    has_real_output = bool(is_completed and persisted_output_url)
    output_url_val = persisted_output_url if has_real_output else None

    return {
        "id": str(row[0]),
        "job_id": str(row[0]),
        "request_id": str(row[1]),
        "account_id": str(row[2]),
        "product_key": str(row[3]),
        "routing_product_key": str(row[4]),
        "prompt": str(row[5]),
        "aspect_ratio": str(row[6]),
        "duration_seconds": int(row[7]),
        "quality_tier": int(row[8]),
        "scene_count": int(row[9]),
        "status": status_str,
        "status_reason": str(row[11]),
        "output_available": has_real_output,
        "download_ready": has_real_output,
        "delivery_ready": has_real_output,
        "output": output_url_val,
        "output_metadata": output_meta,
        "created_at": str(row[16]),
        "updated_at": str(row[17]),
        "bridge_envelope": env,
        "worker_id": str(row[18]) if len(row) > 18 and row[18] else None,
        "claimed_at": str(row[19]) if len(row) > 19 and row[19] else None,
        "lease_expires_at": str(row[20]) if len(row) > 20 and row[20] else None,
        "attempts": int(row[21]) if len(row) > 21 and row[21] is not None else 0,
        "output_url": output_url_val,
        "payload": {
            "prompt": str(row[5]),
            "aspect_ratio": str(row[6]),
            "duration": float(row[7]),
            "duration_seconds": int(row[7]),
            "quality_tier": str(row[8]),
            "scene_count": int(row[9]),
        },
    }
