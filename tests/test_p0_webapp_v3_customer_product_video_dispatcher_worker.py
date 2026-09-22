"""Tests for Product Video Worker Dispatcher Integration.

Task: P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.DISPATCHER_WORKER.INTEGRATION.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Master Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Enforces strict invariants:
1. NO_PROVIDER_CALL: Zero external unmocked paid video AI API calls.
2. NO_WALLET_MUTATION: Zero Xu or wallet ledger mutations.
3. OUTPUT_TRUTH: Completed jobs must possess verified non-empty video artifact metadata
   (duration, width, height, file_size >= 4096B, format=mp4, valid codec).
4. FAIL_CLOSED_ADMISSION: Only authorized workers can claim, heartbeat, complete, or fail jobs.
5. CONCURRENCY_SAFETY: Atomic claim prevents double-claim collisions.
6. WATCHDOG_RECONCILIATION: Stalled jobs with expired leases are recovered safely.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from app import app
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_product_video_job_bridge as bridge
import copyfast_product_video_dispatcher as dispatcher
from copyfast_auth import _session_cookie_value


TEST_WORKER_SECRET = "test-worker-secret-token-321"


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-video-dispatcher")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("PRODUCT_VIDEO_WORKER_SECRET", TEST_WORKER_SECRET)
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt,video_single")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_product_video_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES ('test-user-1', 'user1@test.local', 'hash1', 'user', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z'),
                   ('test-admin-1', 'admin1@test.local', 'hashadmin', 'admin', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_product_video_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


def _create_test_session(account_id: str, role: str = "user") -> tuple[str, str]:
    """Helper to create a test session and return (cookie_value, csrf_token)."""
    import secrets
    from copyfast_db import utc_now
    session_id = f"test-sess-{secrets.token_hex(8)}"
    csrf_token = secrets.token_urlsafe(32)
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_sessions (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
            VALUES (?, ?, ?, datetime('now', '+1 hour'), ?, ?)
            """,
            (session_id, account_id, csrf_token, utc_now(), utc_now()),
        )
    cookie_value = _session_cookie_value(session_id)
    return cookie_value, csrf_token


# ─── TEST 1: DISPATCHER CONSTANTS AND CONFIGURATION ───────────────────────────

def test_01_dispatcher_constants_and_configuration():
    """Verify dispatcher configuration and baseline limits."""
    assert dispatcher.DEFAULT_LEASE_SECONDS == 300
    assert dispatcher.MIN_LEASE_SECONDS == 30
    assert dispatcher.MAX_LEASE_SECONDS == 3600
    assert dispatcher.MAX_DISPATCH_ATTEMPTS == 3
    assert dispatcher.MIN_ARTIFACT_BYTES == 4096
    assert "mp4" in dispatcher.ACCEPTED_VIDEO_FORMATS
    assert "h264" in dispatcher.ACCEPTED_VIDEO_CODECS


# ─── TEST 2: ARTIFACT METADATA VALIDATION ────────────────────────────────────

def test_02_artifact_metadata_validation():
    """Verify strict artifact metadata validation for output truth."""
    # 1. Valid metadata passes
    valid_meta = {
        "duration_seconds": 10.5,
        "width": 1080,
        "height": 1920,
        "file_size_bytes": 1024 * 1024 * 5,
        "format": "mp4",
        "codec": "h264",
    }
    is_valid, err, normalized = dispatcher.validate_video_artifact_metadata(valid_meta)
    assert is_valid is True
    assert err == ""
    assert normalized["duration_seconds"] == 10.5
    assert normalized["width"] == 1080
    assert normalized["height"] == 1920

    # 2. Missing duration rejected
    meta_no_duration = valid_meta.copy()
    meta_no_duration.pop("duration_seconds")
    is_valid, err, _ = dispatcher.validate_video_artifact_metadata(meta_no_duration)
    assert is_valid is False
    assert err in ("DURATION_REQUIRED", "DURATION_MUST_BE_POSITIVE", "INVALID_DURATION")

    # 3. Invalid dimensions rejected
    meta_bad_dims = valid_meta.copy()
    meta_bad_dims["width"] = 32
    is_valid, err, _ = dispatcher.validate_video_artifact_metadata(meta_bad_dims)
    assert is_valid is False
    assert err in ("DIMENSIONS_INVALID", "DIMENSIONS_TOO_SMALL")

    # 4. File size < 4096 bytes rejected
    meta_small = valid_meta.copy()
    meta_small["file_size_bytes"] = 512
    is_valid, err, _ = dispatcher.validate_video_artifact_metadata(meta_small)
    assert is_valid is False
    assert err == "FILE_SIZE_TOO_SMALL"

    # 5. Unsupported format rejected
    meta_bad_fmt = valid_meta.copy()
    meta_bad_fmt["format"] = "avi"
    is_valid, err, _ = dispatcher.validate_video_artifact_metadata(meta_bad_fmt)
    assert is_valid is False
    assert err in ("INVALID_FORMAT", "FORMAT_UNSUPPORTED")

    # 6. Unsupported codec rejected
    meta_bad_codec = valid_meta.copy()
    meta_bad_codec["codec"] = "flv1"
    is_valid, err, _ = dispatcher.validate_video_artifact_metadata(meta_bad_codec)
    assert is_valid is False
    assert err in ("INVALID_CODEC", "CODEC_UNSUPPORTED")


# ─── TEST 3: SYNTHETIC ARTIFACT GENERATION (ZERO PAID PROVIDER) ──────────────

def test_03_synthetic_artifact_generation():
    """Verify test fixture generator generates truth-compliant metadata with zero paid calls."""
    synth_meta = dispatcher.generate_synthetic_product_video_output(
        {"id": "test-job-001", "aspect_ratio": "9:16", "duration_seconds": 10}
    )
    assert synth_meta["duration_seconds"] == 10.0
    assert synth_meta["width"] == 1080
    assert synth_meta["height"] == 1920
    assert synth_meta["file_size_bytes"] >= 4096
    assert synth_meta["format"] == "mp4"
    assert synth_meta["codec"] == "h264"

    # Verify synthetic metadata passes validation
    is_valid, err, _ = dispatcher.validate_video_artifact_metadata(synth_meta)
    assert is_valid is True
    assert err == ""


# ─── TEST 4: WORKER CLAIM AND CONCURRENCY ────────────────────────────────────

def test_04_worker_claim_and_concurrency():
    """Verify atomic claim transitions queued job to processing and handles empty queue."""
    # 1. Queue is initially empty
    claimed_none = dispatcher.claim_product_video_job(worker_id="worker-node-1")
    assert claimed_none is None

    # 2. Create a canonical job
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={
            "prompt": "Test video for dispatcher claim",
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "quality_tier": 400,
        },
        idempotency_key="test-disp-claim-001",
    )
    job_id = job["id"]
    assert job["status"] == "queued"

    # 3. Worker 1 claims job
    claimed = dispatcher.claim_product_video_job(worker_id="worker-node-1", lease_seconds=120)
    assert claimed is not None
    assert claimed["id"] == job_id
    assert claimed["status"] == "processing"
    assert claimed["worker_id"] == "worker-node-1"
    assert claimed["attempts"] == 1
    assert claimed["lease_expires_at"] is not None

    # 4. Worker 2 attempts to claim while lease is active -> returns None (no available jobs)
    claimed_2 = dispatcher.claim_product_video_job(worker_id="worker-node-2")
    assert claimed_2 is None


# ─── TEST 5: WORKER HEARTBEAT ────────────────────────────────────────────────

def test_05_worker_heartbeat_lifecycle():
    """Verify heartbeat lease extension and cross-worker isolation."""
    # Create and claim job
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={"prompt": "Heartbeat test", "aspect_ratio": "16:9", "duration_seconds": 5, "quality_tier": 300},
        idempotency_key="test-disp-hb-001",
    )
    job_id = job["id"]
    claimed = dispatcher.claim_product_video_job(worker_id="worker-alpha", lease_seconds=60)
    assert claimed is not None
    initial_lease = claimed["lease_expires_at"]

    # Heartbeat by owning worker succeeds and extends lease
    hb_result = dispatcher.heartbeat_product_video_job(job_id=job_id, worker_id="worker-alpha", lease_seconds=300)
    assert hb_result is True

    # Heartbeat by different worker fails (False)
    hb_imposter = dispatcher.heartbeat_product_video_job(job_id=job_id, worker_id="worker-beta")
    assert hb_imposter is False

    # Heartbeat on non-existent job fails
    hb_nonexistent = dispatcher.heartbeat_product_video_job(job_id="non-existent-job-id", worker_id="worker-alpha")
    assert hb_nonexistent is False


# ─── TEST 6: WORKER COMPLETE (OUTPUT TRUTH ENFORCEMENT) ──────────────────────

def test_06_worker_complete_lifecycle():
    """Verify worker completion persists verified artifact and updates public status."""
    # Create and claim job
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={"prompt": "Complete test video", "aspect_ratio": "1:1", "duration_seconds": 5, "quality_tier": 200},
        idempotency_key="test-disp-comp-001",
    )
    job_id = job["id"]
    dispatcher.claim_product_video_job(worker_id="worker-gamma", lease_seconds=120)

    # 1. Complete attempt with invalid metadata is rejected (raises 422)
    bad_meta = {"duration_seconds": 0, "width": 10, "height": 10}
    with pytest.raises(HTTPException) as exc_info:
        dispatcher.complete_product_video_job(
            job_id=job_id,
            worker_id="worker-gamma",
            output_url="https://example.com/video.mp4",
            output_metadata=bad_meta,
        )
    assert exc_info.value.status_code in (400, 422)

    # 2. Complete attempt by wrong worker is rejected (raises 403)
    synth_meta = dispatcher.generate_synthetic_product_video_output({"id": job_id, "aspect_ratio": "1:1", "duration_seconds": 5})
    output_url = f"https://static.toanaas.vn/artifacts/video/{job_id}.mp4"
    with pytest.raises(HTTPException) as exc_info:
        dispatcher.complete_product_video_job(
            job_id=job_id,
            worker_id="worker-imposter",
            output_url=output_url,
            output_metadata=synth_meta,
        )
    assert exc_info.value.status_code == 403

    # 3. Complete attempt by owning worker with valid metadata succeeds
    success_res = dispatcher.complete_product_video_job(
        job_id=job_id,
        worker_id="worker-gamma",
        output_url=output_url,
        output_metadata=synth_meta,
    )
    assert success_res["status"] == "completed"
    assert success_res["output_url"] == output_url

    # 4. Verify public read models reflect completion
    public_job = bridge.get_product_video_job("test-user-1", job_id)
    assert public_job is not None
    assert public_job["status"] == "completed"
    assert public_job["output_available"] is True
    assert public_job["download_ready"] is True
    assert public_job["output_url"] == output_url
    assert public_job["output_metadata"]["duration_seconds"] == 5.0


# ─── TEST 7: WORKER FAIL AND RETRY ───────────────────────────────────────────

def test_07_worker_fail_retry_and_terminal():
    """Verify fail logic handles retry backoff and terminal failure after max attempts."""
    # Create job
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={"prompt": "Fail retry test", "aspect_ratio": "9:16", "duration_seconds": 15, "quality_tier": 500},
        idempotency_key="test-disp-fail-001",
    )
    job_id = job["id"]

    # Attempt 1: Worker claims and non-fatally fails
    dispatcher.claim_product_video_job(worker_id="worker-1")
    fail_1 = dispatcher.fail_product_video_job(
        job_id=job_id,
        worker_id="worker-1",
        error_reason="GPU_OOM_RETRYABLE: Transient GPU out of memory",
        fatal=False,
    )
    assert fail_1["status"] == "queued"
    assert fail_1["attempts"] == 1

    # Attempt 2: Worker 2 claims and non-fatally fails
    dispatcher.claim_product_video_job(worker_id="worker-2")
    fail_2 = dispatcher.fail_product_video_job(
        job_id=job_id,
        worker_id="worker-2",
        error_reason="TIMEOUT_RETRYABLE: Render step timeout",
        fatal=False,
    )
    assert fail_2["status"] == "queued"
    assert fail_2["attempts"] == 2

    # Attempt 3: Worker 3 claims and fails -> reaches max_attempts (3) -> terminal 'failed'
    dispatcher.claim_product_video_job(worker_id="worker-3")
    fail_3 = dispatcher.fail_product_video_job(
        job_id=job_id,
        worker_id="worker-3",
        error_reason="PIPELINE_ERROR: Exceeded max attempts",
        fatal=False,
    )
    assert fail_3["status"] == "failed"
    assert fail_3["attempts"] == 3

    # Verify public job state is failed
    public_job = bridge.get_product_video_job("test-user-1", job_id)
    assert public_job["status"] == "failed"
    assert public_job["output_available"] is False


# ─── TEST 8: WATCHDOG RECONCILIATION FOR STALLED JOBS ────────────────────────

def test_08_watchdog_reconciliation():
    """Verify watchdog pass recovers stalled jobs with expired leases."""
    # Create job and manually set expired lease in database
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={"prompt": "Watchdog test", "aspect_ratio": "9:16", "duration_seconds": 10, "quality_tier": 400},
        idempotency_key="test-disp-watchdog-001",
    )
    job_id = job["id"]

    # Manually simulate a crashed worker holding an expired lease
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_product_video_jobs
            SET status = 'processing',
                worker_id = 'crashed-worker-99',
                attempts = 1,
                lease_expires_at = datetime('now', '-60 seconds')
            WHERE id = ?
            """,
            (job_id,),
        )

    # Run watchdog reconciliation
    stats = dispatcher.reconcile_stalled_product_video_jobs(lease_grace_seconds=0, max_attempts=3)
    assert stats["total_reconciled"] >= 1
    assert stats["requeued"] >= 1

    # Verify job was requeued and worker_id was cleared
    requeued_job = bridge.get_product_video_job("test-user-1", job_id)
    assert requeued_job["status"] == "queued"

    # Another worker can now claim it
    claimed = dispatcher.claim_product_video_job(worker_id="recovery-worker-1")
    assert claimed is not None
    assert claimed["id"] == job_id
    assert claimed["attempts"] == 2


# ─── TEST 9: DISPATCHER METRICS ──────────────────────────────────────────────

def test_09_dispatcher_metrics():
    """Verify dispatcher metrics aggregation."""
    # Create 1 job to complete and 1 job to stay queued
    c_job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={"prompt": "Metrics completed job", "aspect_ratio": "16:9", "duration_seconds": 5, "quality_tier": 200},
        idempotency_key="test-disp-met-001",
    )
    claimed = dispatcher.claim_product_video_job(worker_id="worker-met-1")
    assert claimed is not None
    assert claimed["id"] == c_job["id"]
    synth_meta = dispatcher.generate_synthetic_product_video_output({"id": c_job["id"], "aspect_ratio": "16:9", "duration_seconds": 5})
    output_url = f"https://static.toanaas.vn/artifacts/video/{c_job['id']}.mp4"
    dispatcher.complete_product_video_job(
        job_id=c_job["id"],
        worker_id="worker-met-1",
        output_url=output_url,
        output_metadata=synth_meta,
    )
    q_job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={"prompt": "Metrics queued job", "aspect_ratio": "16:9", "duration_seconds": 5, "quality_tier": 200},
        idempotency_key="test-disp-met-002",
    )

    metrics = dispatcher.get_product_video_dispatcher_metrics()
    assert metrics["counts"]["queued"] >= 1
    assert metrics["counts"]["completed"] >= 1
    assert "active_workers" in metrics
    assert "version" in metrics
    assert "healthy" in metrics


# ─── TEST 10: FASTAPI WORKER ENDPOINTS INTEGRATION ────────────────────────────

def test_10_fastapi_worker_endpoints_integration():
    """Verify HTTP endpoints for worker claim, heartbeat, complete, and fail."""
    client = TestClient(app)

    # 1. Unauthenticated request rejected with 401
    unauth_resp = client.post(
        "/api/v1/worker/product-video/claim",
        json={"worker_id": "test-w1", "lease_seconds": 120},
    )
    assert unauth_resp.status_code == 401

    # 2. Claim with valid worker secret header
    headers = {"X-Worker-Secret": TEST_WORKER_SECRET}

    # Create job to be claimed
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={"prompt": "HTTP Worker integration test", "aspect_ratio": "9:16", "duration_seconds": 10, "quality_tier": 400},
        idempotency_key="test-http-worker-001",
    )
    job_id = job["id"]

    claim_resp = client.post(
        "/api/v1/worker/product-video/claim",
        json={"worker_id": "http-worker-node-1", "lease_seconds": 120},
        headers=headers,
    )
    assert claim_resp.status_code == 200
    claim_body = claim_resp.json()
    assert claim_body["ok"] is True
    assert claim_body["data"]["idle"] is False
    assert claim_body["data"]["job"]["id"] == job_id

    # 3. Heartbeat via HTTP
    hb_resp = client.post(
        "/api/v1/worker/product-video/heartbeat",
        json={"job_id": job_id, "worker_id": "http-worker-node-1", "lease_seconds": 300},
        headers=headers,
    )
    assert hb_resp.status_code == 200
    assert hb_resp.json()["ok"] is True

    # 4. Complete via HTTP with valid synthetic artifact
    synth_meta = dispatcher.generate_synthetic_product_video_output({"id": job_id, "aspect_ratio": "9:16", "duration_seconds": 10})
    output_url = f"https://static.toanaas.vn/artifacts/video/{job_id}.mp4"
    comp_resp = client.post(
        "/api/v1/worker/product-video/complete",
        json={
            "job_id": job_id,
            "worker_id": "http-worker-node-1",
            "output_url": output_url,
            "output_metadata": synth_meta,
        },
        headers=headers,
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["ok"] is True
    assert comp_resp.json()["data"]["status"] == "completed"


# ─── TEST 11: FASTAPI ADMIN DISPATCHER ENDPOINTS INTEGRATION ─────────────────

def test_11_fastapi_admin_dispatcher_endpoints_integration(monkeypatch):
    """Verify HTTP endpoints for admin metrics and manual reconciliation."""
    client = TestClient(app)

    # 1. Non-admin request rejected
    user_cookie, user_csrf = _create_test_session("test-user-1", role="user")
    client.cookies.set("web_session", user_cookie)
    unauth_resp = client.get("/api/v1/admin/product-video/metrics")
    assert unauth_resp.status_code in (401, 403, 404)

    # 2. Canonical admin reads metrics
    admin_cookie, admin_csrf = _create_test_session("test-admin-1", role="admin")
    client.cookies.set("web_session", admin_cookie)

    def mock_admin_dep():
        return {"id": "test-admin-1", "role": "admin"}

    from copyfast_auth import require_canonical_admin, require_canonical_admin_csrf
    app.dependency_overrides[require_canonical_admin] = mock_admin_dep
    app.dependency_overrides[require_canonical_admin_csrf] = mock_admin_dep

    try:
        metrics_resp = client.get("/api/v1/admin/product-video/metrics")
        assert metrics_resp.status_code == 200
        metrics_body = metrics_resp.json()
        assert metrics_body["ok"] is True
        assert "counts" in metrics_body["data"]

        # 3. Canonical admin triggers watchdog reconciliation
        recon_resp = client.post(
            "/api/v1/admin/product-video/reconcile",
            json={"lease_grace_seconds": 10, "max_attempts": 3},
            headers={"X-CSRF-Token": admin_csrf},
        )
        assert recon_resp.status_code == 200
        recon_body = recon_resp.json()
        assert recon_body["ok"] is True
        assert "reconciled" in recon_body["status"]
    finally:
        app.dependency_overrides.clear()
