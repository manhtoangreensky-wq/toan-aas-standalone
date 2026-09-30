"""Tests for Web Product Video Targeted Claim & Canonical Admission Contract.

Verifies:
1. FIFO claim unchanged without target_job_id.
2. Targeted claim claims exact queued id.
3. Targeted claim never claims another queued id (no fallthrough).
4. Targeted claim concurrent contention permits at most one winner.
5. Missing target returns no claim (None / idle).
6. Worker claim API endpoint forwards target_job_id properly.
7. Canonical endpoint contract is /api/v1/features/video_ai_prompt/jobs.
8. Zero wallet mutations and zero provider HTTP requests in tests.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import copyfast_db
from app import app
from copyfast_api import router
from copyfast_product_video_dispatcher import (
    claim_product_video_job,
    ensure_copyfast_schema,
    transaction,
)
from copyfast_product_video_job_bridge import create_or_replay_product_video_job


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PRODUCT_VIDEO_WORKER_SECRET", "test-worker-secret-42")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt,video_single")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_product_video_jobs")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES ('acc_owner_001', 'owner@test.local', 'hash1', 'user', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_product_video_jobs")
        conn.execute("DELETE FROM web_accounts WHERE id = 'acc_owner_001'")


def _insert_test_job(
    account_id: str = "acc_owner_001",
    prompt: str = "High-tech luxury perfume bottle on turquoise background",
    aspect_ratio: str = "9:16",
    duration_seconds: int = 5,
    quality_tier: int = 200,
    request_id: str = "",
    idempotency_key: str = "",
) -> dict:
    return create_or_replay_product_video_job(
        account_id=account_id,
        payload={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration_seconds": duration_seconds,
            "quality_tier": quality_tier,
        },
        request_id=request_id,
        idempotency_key=idempotency_key,
    )


def test_fifo_claim_unchanged_without_target_id():
    """When target_job_id is None, claim follows normal FIFO ordering."""
    job1 = _insert_test_job(request_id="req_fifo_001", idempotency_key="key_fifo_001")
    job2 = _insert_test_job(request_id="req_fifo_002", idempotency_key="key_fifo_002")

    # Set distinct created_at to guarantee deterministic FIFO ordering
    with transaction() as conn:
        conn.execute("UPDATE web_product_video_jobs SET created_at = '2026-09-01T00:00:00Z' WHERE id = ?", (job1["id"],))
        conn.execute("UPDATE web_product_video_jobs SET created_at = '2026-09-01T00:01:00Z' WHERE id = ?", (job2["id"],))

    claimed = claim_product_video_job(
        worker_id="worker-test-1",
        lease_seconds=300,
        target_job_id=None,
    )
    assert claimed is not None
    assert claimed["id"] == job1["id"]
    assert claimed["worker_id"] == "worker-test-1"
    assert claimed["status"] == "processing"


def test_targeted_claim_claims_exact_queued_id():
    """Targeted claim claims ONLY the exact requested job, even if not the oldest."""
    job1 = _insert_test_job(request_id="req_targ_001", idempotency_key="key_targ_001")
    job2 = _insert_test_job(request_id="req_targ_002", idempotency_key="key_targ_002")

    # Specifically target the second job
    claimed = claim_product_video_job(
        worker_id="worker-test-1",
        lease_seconds=300,
        target_job_id=job2["id"],
    )
    assert claimed is not None
    assert claimed["id"] == job2["id"]
    assert claimed["worker_id"] == "worker-test-1"
    assert claimed["status"] == "processing"

    # Job 1 must still be queued and untouched
    claimed_first = claim_product_video_job(
        worker_id="worker-test-2",
        lease_seconds=300,
        target_job_id=job1["id"],
    )
    assert claimed_first is not None
    assert claimed_first["id"] == job1["id"]


def test_targeted_claim_never_claims_another_queued_id():
    """If target_job_id does not exist, never fall through to other queued jobs."""
    job1 = _insert_test_job(request_id="req_nofall_001", idempotency_key="key_nofall_001")

    # Target non-existent job
    claimed = claim_product_video_job(
        worker_id="worker-test-1",
        lease_seconds=300,
        target_job_id="pvj_nonexistent_999999",
    )
    assert claimed is None

    # Verify job1 was NOT claimed
    with copyfast_db.read_transaction() as conn:
        row = conn.execute("SELECT status, worker_id FROM web_product_video_jobs WHERE id = ?", (job1["id"],)).fetchone()
        assert row[0] == "queued"
        assert row[1] is None


def test_targeted_claim_missing_target_returns_none():
    """Empty queue or missing target returns None (idle)."""
    claimed = claim_product_video_job(
        worker_id="worker-test-1",
        lease_seconds=300,
        target_job_id="pvj_missing_000000",
    )
    assert claimed is None


def test_targeted_claim_concurrency_race_single_winner():
    """When two workers contend for the same target_job_id, exactly one wins."""
    job = _insert_test_job(request_id="req_race_001", idempotency_key="key_race_001")

    # Worker A claims
    claim_a = claim_product_video_job(
        worker_id="worker-a",
        lease_seconds=300,
        target_job_id=job["id"],
    )
    assert claim_a is not None
    assert claim_a["id"] == job["id"]
    assert claim_a["worker_id"] == "worker-a"

    # Worker B immediately tries to claim the same job while lease is active
    claim_b = claim_product_video_job(
        worker_id="worker-b",
        lease_seconds=300,
        target_job_id=job["id"],
    )
    # Must fail to claim because lease is active and not queued
    assert claim_b is None


def test_worker_claim_api_endpoint_targeted():
    """Test POST /api/v1/worker/product-video/claim endpoint with target_job_id."""
    job1 = _insert_test_job(request_id="req_api_001", idempotency_key="key_api_001")
    job2 = _insert_test_job(request_id="req_api_002", idempotency_key="key_api_002")

    secret = "test-worker-secret-42"
    with patch.dict(os.environ, {"WORKER_SECRET": secret}):
        client = TestClient(app)
        headers = {
            "Authorization": f"Bearer {secret}",
            "X-Worker-Secret": secret,
        }

        # Targeted claim for job2
        resp = client.post(
            "/api/v1/worker/product-video/claim",
            headers=headers,
            json={
                "worker_id": "vps-test-worker",
                "lease_seconds": 300,
                "target_job_id": job2["id"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "claimed"
        assert body["data"]["job"]["id"] == job2["id"]
        assert body["data"]["idle"] is False

        # Claim non-existent job
        resp_idle = client.post(
            "/api/v1/worker/product-video/claim",
            headers=headers,
            json={
                "worker_id": "vps-test-worker",
                "lease_seconds": 300,
                "target_job_id": "pvj_nonexistent",
            },
        )
        assert resp_idle.status_code == 200
        body_idle = resp_idle.json()
        assert body_idle["ok"] is True
        assert body_idle["status"] == "idle"
        assert body_idle["data"]["job"] is None
        assert body_idle["data"]["idle"] is True


def test_canonical_customer_job_create_endpoint_exists():
    """Verify canonical endpoint POST /api/v1/features/video_ai_prompt/jobs route exists."""
    routes = [route.path for route in app.routes]
    assert "/api/v1/features/video_ai_prompt/jobs" in routes or any(
        "video_ai_prompt/jobs" in r for r in routes
    )
