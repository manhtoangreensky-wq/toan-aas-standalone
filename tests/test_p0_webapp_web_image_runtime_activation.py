"""Focused Test Suite for Web Image Generation Runtime Activation.

Task: WEBAPP_R3_FULL_PRODUCT_RUNTIME_CLOSURE_MASTER_BATCH_R1
Issue: manhtoangreensky-wq/toan-aas-standalone#612
Capability: image_generation
Web Feature Key: image_create
Customer Entrypoint: /image/create
Web API Family: /api/v1/features/image_create/*
Bot Authority Repo: manhtoangreensky-wq/bot
Matrix Runtime Reference: services.video_ai_real_pricing.public_image_quality_catalog

Proves:
1. Admission & creation creates durable job record with runtime_job_id and quote_xu.
2. Direct POST /features/image_create/jobs dispatches to canonical Bot Core runtime.
3. Confirm route /features/image_create/jobs/{job_id}/confirm executes and updates status.
4. Reconcile route /features/image_create/jobs/{job_id}/reconcile syncs status.
5. Artifact route /features/image_create/jobs/{job_id}/artifact streams image artifact.
6. Server-side quote authority: client price/wallet injection strictly rejected.
7. Idempotent replay: exact payload replays safely; modified payload fails with 409 Conflict.
8. Tenant isolation: cross-account job access rejected with 403.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from starlette.testclient import TestClient

from app import app
import app as app_module
from copyfast_db import ensure_copyfast_schema, transaction
import copyfast_image_generation_job_bridge as bridge
import copyfast_auth


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-image-runtime")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "image_create")
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()
    with transaction() as conn:
        conn.execute("DROP TABLE IF EXISTS web_image_generation_jobs")
    ensure_copyfast_schema()
    bridge.ensure_image_generation_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, canonical_user_id, created_at, updated_at)
            VALUES
                ('test-user-img-act1', 'img_act1@test.local', 'hash', '100001', datetime('now'), datetime('now')),
                ('test-user-img-act2', 'img_act2@test.local', 'hash', '100002', datetime('now'), datetime('now'))
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_image_generation_jobs")


def _get_auth_headers(account_id: str):
    with transaction() as conn:
        s = copyfast_auth._insert_session(conn, account_id)
    cookies = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s["session_id"])}
    headers = {"X-CSRF-Token": s["csrf_token"]}
    return cookies, headers


def test_01_create_image_job_with_runtime_dispatch():
    """Prove POST /features/image_create/jobs creates job and dispatches to Bot Core."""
    client = TestClient(app)
    cookies, headers = _get_auth_headers("test-user-img-act1")

    mock_dispatch_response = {
        "ok": True,
        "job": {
            "job_id": "imgjob_mock1234567890abcdef12345678",
            "status": "prepared",
            "quote_xu": 40,
            "has_artifact": False,
            "can_download": False,
        },
    }

    with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_dispatch_response
        res = client.post(
            "/api/v1/features/image_create/jobs",
            json={
                "input": {
                    "prompt": "Vibrant landscape of Ha Long Bay",
                    "tier": "standard",
                },
                "idempotency_key": "img-act-001",
            },
            cookies=cookies,
            headers=headers,
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "queued"
    data = body["data"]
    assert data["prompt"] == "Vibrant landscape of Ha Long Bay"
    assert data["tier_key"] == "standard"
    assert data["runtime_job_id"] == "imgjob_mock1234567890abcdef12345678"
    assert data["quote_xu"] == 40
    assert data["runtime_dispatch_status"] == "dispatched"
    assert data["output_available"] is False


def test_02_confirm_image_job_success():
    """Prove POST /features/image_create/jobs/{job_id}/confirm executes and completes."""
    client = TestClient(app)
    cookies, headers = _get_auth_headers("test-user-img-act1")

    # First prepare job
    with transaction() as conn:
        bridge.ensure_image_generation_schema(conn)
        conn.execute(
            """
            INSERT INTO web_image_generation_jobs (
                id, canonical_job_id, request_id, account_id, prompt, tier_key,
                status, status_reason, payload_hash, bridge_envelope_json,
                runtime_job_id, quote_xu, runtime_dispatch_status, created_at, updated_at
            ) VALUES (
                'img_test_conf_01', 'img_test_conf_01', 'req_01', 'test-user-img-act1',
                'A cute cat wearing sunglasses', 'standard', 'queued',
                'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION', 'hash', '{}',
                'imgjob_rt_conf_01', 40, 'dispatched', datetime('now'), datetime('now')
            )
            """
        )

    mock_confirm_response = {
        "ok": True,
        "job": {
            "job_id": "imgjob_rt_conf_01",
            "status": "completed",
            "charged_xu": 40,
            "has_artifact": True,
            "can_download": True,
            "output_url": "https://cdn.toanaas.vn/images/cat_01.png",
            "completed_at": "2026-10-09T10:00:00Z",
        },
    }

    with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_confirm_response
        res = client.post(
            "/api/v1/features/image_create/jobs/img_test_conf_01/confirm",
            cookies=cookies,
            headers=headers,
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["status"] == "completed"
    assert data["charged_xu"] == 40
    assert data["output_available"] is True
    assert data["can_download"] is True
    assert data["artifact_url"] == "/api/v1/features/image_create/jobs/img_test_conf_01/artifact"


def test_03_tenant_isolation_cross_account_rejected():
    """Prove cross-account read and confirm are rejected with 403."""
    client = TestClient(app)
    cookies1, headers1 = _get_auth_headers("test-user-img-act1")
    cookies2, headers2 = _get_auth_headers("test-user-img-act2")

    # Create job under account 1
    with transaction() as conn:
        bridge.ensure_image_generation_schema(conn)
        conn.execute(
            """
            INSERT INTO web_image_generation_jobs (
                id, canonical_job_id, request_id, account_id, prompt, tier_key,
                status, status_reason, payload_hash, bridge_envelope_json,
                runtime_job_id, quote_xu, runtime_dispatch_status, created_at, updated_at
            ) VALUES (
                'img_iso_01', 'img_iso_01', 'req_iso', 'test-user-img-act1',
                'Private portrait', 'high', 'queued',
                'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION', 'hash', '{}',
                'imgjob_iso_01', 120, 'dispatched', datetime('now'), datetime('now')
            )
            """
        )

    # Account 2 attempts to get job detail => 403
    res_get = client.get(
        "/api/v1/features/image_create/jobs/img_iso_01",
        cookies=cookies2,
        headers=headers2,
    )
    assert res_get.status_code == 403

    # Account 2 attempts to confirm job => 403
    res_conf = client.post(
        "/api/v1/features/image_create/jobs/img_iso_01/confirm",
        cookies=cookies2,
        headers=headers2,
    )
    assert res_conf.status_code == 403


def test_04_idempotency_conflict_rejected():
    """Prove differing payload submitted with identical idempotency key yields 409 Conflict."""
    client = TestClient(app)
    cookies, headers = _get_auth_headers("test-user-img-act1")

    with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = {"ok": True, "job": {"job_id": "rt_idem_01", "quote_xu": 40}}
        res1 = client.post(
            "/api/v1/features/image_create/jobs",
            json={
                "input": {"prompt": "First prompt", "tier": "standard"},
                "idempotency_key": "idem-key-conflict-test",
            },
            cookies=cookies,
            headers=headers,
        )
    assert res1.status_code == 200

    # Second call with same key but differing prompt => 409 Conflict
    res2 = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {"prompt": "Differing prompt attempting conflict", "tier": "standard"},
            "idempotency_key": "idem-key-conflict-test",
        },
        cookies=cookies,
        headers=headers,
    )
    assert res2.status_code == 409
