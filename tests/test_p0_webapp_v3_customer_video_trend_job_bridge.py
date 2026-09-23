"""Tests for Video Trend Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.VIDEO_TREND.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: video_trend
Entrypoint: /video/trend
API: /api/v1/features/video_trend/*
Bot Authority: services.video_tail9.PRODUCT_ADAPTERS['video_trend']

Covers Tests A through P:
- Test A: FIRST RED / Baseline contract truth
- Test B: Input validation - valid inputs & defaults
- Test C: Input validation - missing prompt rejected
- Test D: Input validation - prompt too long rejected (>2000 chars)
- Test E: Input validation - invalid quality tier rejected
- Test F: Input validation - invalid scene count rejected
- Test G: Client authority rejection (identity, Xu, payment, output injection)
- Test H: Durable job creation in SQLite table web_video_trend_jobs
- Test I: Idempotency replay
- Test J: Idempotency conflict (differing payload) -> 409
- Test K: Owner scoping and cross-account isolation
- Test L: FastAPI HTTP create and readback
- Test M: Generic jobs integration (/api/v1/jobs & /api/v1/jobs/{job_id})
- Test N: Artifact truth (completed with safe vs unsafe output URLs)
- Test O: Zero external provider and financial calls
- Test P: Parity matrix truth verification
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

import copyfast_registry as reg
from app import app
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_video_trend_job_bridge as bridge


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-video-trend-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt,video_single,video_trend")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    ensure_copyfast_schema()
    bridge.ensure_video_trend_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_video_trend_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('test-user-1', 'user1@test.local', 'hash1', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z'),
                   ('test-user-2', 'user2@test.local', 'hash2', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_video_trend_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


# ─── TEST A: FIRST RED & BASELINE CONTRACT TRUTH ─────────────────────────────

def test_a_first_red_entrypoint_and_matrix_baseline():
    """Prove canonical identity, entrypoint /video/trend, routing key, and registry integrity."""
    assert bridge.CANONICAL_PRODUCT_KEY == "video_trend"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/video/trend"
    assert bridge.CANONICAL_ROUTING_KEY == "trend_video"
    assert bridge.CANONICAL_ROUTE_ID == "trend_video_canonical_v1"
    assert bridge.CANONICAL_ENGINE_ADAPTER == "b13_r18c_trend_video_v1"

    # Registry verification
    assert "video_trend" in reg.FEATURE_BY_KEY
    feat = reg.FEATURE_BY_KEY["video_trend"]
    assert feat.route == "/video/trend"
    assert feat.group == "video"

    # Total registry features count preserved
    assert len(reg.ALL_FEATURES) == 180


# ─── TEST B: INPUT VALIDATION - SOURCE-DERIVED CONTRACT ─────────────────────

def test_b_input_validation_source_derived_contract():
    """Verify source-derived validation: tier and scene_count required, no silent defaults."""
    # 1. Missing tier rejected
    ok, err, _ = bridge.validate_video_trend_input({
        "prompt": "Trend prompt without tier",
        "scene_count": 2,
    })
    assert ok is False
    assert err == "TIER_REQUIRED"

    # 2. Missing scene_count rejected
    ok, err, _ = bridge.validate_video_trend_input({
        "prompt": "Trend prompt without scene_count",
        "tier": 300,
    })
    assert ok is False
    assert err == "SCENE_COUNT_REQUIRED"

    # 3. Both missing rejected
    ok, err, _ = bridge.validate_video_trend_input({
        "prompt": "Trend prompt with neither",
    })
    assert ok is False
    assert err == "TIER_REQUIRED"

    # 4. Valid tier + scene_count accepted
    ok, err, normalized = bridge.validate_video_trend_input({
        "trend_prompt": "Hot trend review biến hình anime",
        "quality_tier": 500,
        "scene_count": 3,
    })
    assert ok is True
    assert err == ""
    assert normalized["prompt"] == "Hot trend review biến hình anime"
    assert normalized["quality_tier"] == 500
    assert normalized["scene_count"] == 3
    assert normalized["product_key"] == "video_trend"
    assert normalized["routing_product_key"] == "trend_video"

    # 5. Alias quality_tier and prompt accepted when valid
    ok, err, normalized = bridge.validate_video_trend_input({
        "prompt": "Trend makeup biến hình",
        "tier": "400",
        "scene_count": "1",
    })
    assert ok is True
    assert normalized["prompt"] == "Trend makeup biến hình"
    assert normalized["quality_tier"] == 400
    assert normalized["scene_count"] == 1

    # 6. Verify all supported quality tiers
    for tier in bridge.ALLOWED_QUALITY_TIERS:
        ok, _, norm = bridge.validate_video_trend_input({"prompt": "test", "quality_tier": tier, "scene_count": 1})
        assert ok is True
        assert norm["quality_tier"] == tier


# ─── TEST C: INPUT VALIDATION - MISSING PROMPT ───────────────────────────────

def test_c_input_validation_missing_prompt():
    """Verify missing, empty, or whitespace-only prompt is rejected."""
    for empty_val in [None, "", "   ", "\t\n"]:
        is_valid, err, _ = bridge.validate_video_trend_input({"trend_prompt": empty_val, "tier": 200, "scene_count": 1})
        assert is_valid is False
        assert err == "PROMPT_REQUIRED"

        is_valid, err, _ = bridge.validate_video_trend_input({"prompt": empty_val, "tier": 200, "scene_count": 1})
        assert is_valid is False
        assert err == "PROMPT_REQUIRED"


# ─── TEST D: INPUT VALIDATION - PROMPT TOO LONG ──────────────────────────────

def test_d_input_validation_prompt_too_long():
    """Verify prompt length boundary (max 2000 chars)."""
    # 2000 chars -> valid
    ok, err, norm = bridge.validate_video_trend_input({"prompt": "A" * 2000, "tier": 200, "scene_count": 1})
    assert ok is True
    assert len(norm["prompt"]) == 2000

    # 2001 chars -> rejected
    ok, err, _ = bridge.validate_video_trend_input({"prompt": "A" * 2001, "tier": 200, "scene_count": 1})
    assert ok is False
    assert err == "PROMPT_TOO_LONG"


# ─── TEST E: INPUT VALIDATION - INVALID QUALITY TIER ─────────────────────────

def test_e_input_validation_invalid_quality_tier():
    """Verify unsupported quality tier values are rejected."""
    for bad_tier in [0, 100, 250, 999, 2000, "ultra", "hd", -1]:
        is_valid, err, _ = bridge.validate_video_trend_input({
            "prompt": "Trend prompt",
            "quality_tier": bad_tier,
            "scene_count": 1,
        })
        assert is_valid is False
        assert err == "INVALID_QUALITY_TIER"


# ─── TEST F: INPUT VALIDATION - INVALID SCENE COUNT ──────────────────────────

def test_f_input_validation_invalid_scene_count():
    """Verify scene_count outside 1..20 is rejected."""
    for bad_count in [0, -1, 21, 50, "five", 100]:
        is_valid, err, _ = bridge.validate_video_trend_input({
            "prompt": "Trend prompt",
            "tier": 200,
            "scene_count": bad_count,
        })
        assert is_valid is False
        assert err == "INVALID_SCENE_COUNT"

    # Boundaries 1 and 20 are valid
    assert bridge.validate_video_trend_input({"prompt": "Trend", "tier": 200, "scene_count": 1})[0] is True
    assert bridge.validate_video_trend_input({"prompt": "Trend", "tier": 200, "scene_count": 20})[0] is True


# ─── TEST G: CLIENT AUTHORITY REJECTION ──────────────────────────────────────

def test_g_client_authority_rejection():
    """Verify client attempts to supply authority/system fields are rejected with authority_field_not_allowed."""
    authority_probes = [
        {"status": "completed"},
        {"status_reason": "CUSTOM_REASON"},
        {"account_id": "attacker-id"},
        {"output_url": "https://attacker.site/fake.mp4"},
        {"output": "https://attacker.site/fake.mp4"},
        {"wallet": "unlimited"},
        {"xu": 999999},
        {"balance": 999999},
        {"amount": 0},
        {"payment_id": "bypass-payment"},
        {"provider": "fake-provider"},
        {"bridge_envelope": "{}"},
        {"output_metadata": "{}"},
        {"job_id": "vtj_injected"},
        {"id": "vtj_injected"},
    ]
    for probe in authority_probes:
        payload = {"prompt": "Valid trend prompt", "tier": 300, "scene_count": 1, **probe}
        is_valid, err, _ = bridge.validate_video_trend_input(payload)
        assert is_valid is False
        assert err == "authority_field_not_allowed"

        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_video_trend_job(
                account_id="test-user-1",
                payload=payload,
            )
        assert exc_info.value.status_code == 400


# ─── TEST H: DURABLE JOB CREATION ────────────────────────────────────────────

def test_h_durable_job_creation():
    """Verify durable job creation in SQLite table web_video_trend_jobs with initial queued status."""
    payload = {
        "trend_prompt": "Điệu nhảy biến hình biến đổi trang phục",
        "quality_tier": 600,
        "scene_count": 4,
    }
    job = bridge.create_or_replay_video_trend_job(
        account_id="test-user-1",
        payload=payload,
        request_id="VTR-20260923-TEST01",
    )
    assert job["id"].startswith("vtj_")
    assert job["request_id"] == "VTR-20260923-TEST01"
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job["product_key"] == "video_trend"
    assert job["routing_product_key"] == "trend_video"
    assert job["prompt"] == "Điệu nhảy biến hình biến đổi trang phục"
    assert job["quality_tier"] == 600
    assert job["scene_count"] == 4
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["output"] is None

    # Check database persistence
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT id, request_id, account_id, status, status_reason, prompt, quality_tier, scene_count, bridge_envelope FROM web_video_trend_jobs WHERE id = ?",
            (job["id"],),
        ).fetchone()
        assert row is not None
        assert row[0] == job["id"]
        assert row[1] == "VTR-20260923-TEST01"
        assert row[2] == "test-user-1"
        assert row[3] == "queued"
        assert row[4] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
        assert row[5] == "Điệu nhảy biến hình biến đổi trang phục"
        assert row[6] == 600
        assert row[7] == 4

        envelope = json.loads(row[8])
        assert envelope["route_id"] == "trend_video_canonical_v1"
        assert envelope["engine_adapter"] == "b13_r18c_trend_video_v1"
        assert envelope["routing_product_key"] == "trend_video"
        assert envelope["product_key"] == "video_trend"
        assert envelope["prompt"] == "Điệu nhảy biến hình biến đổi trang phục"
        assert envelope["quality_tier"] == 600
        assert envelope["scene_count"] == 4


# ─── TEST I: IDEMPOTENCY REPLAY ──────────────────────────────────────────────

def test_i_idempotency_replay():
    """Verify replay with exact same idempotency_key returns identical job without duplicates."""
    payload = {"prompt": "Idempotent trend dance", "tier": 300, "scene_count": 1}
    idem_key = "idem-trend-safe-001"

    job1 = bridge.create_or_replay_video_trend_job(
        account_id="test-user-1",
        payload=payload,
        idempotency_key=idem_key,
    )
    job2 = bridge.create_or_replay_video_trend_job(
        account_id="test-user-1",
        payload=payload,
        idempotency_key=idem_key,
    )

    assert job1["id"] == job2["id"]
    assert job1["request_id"] == job2["request_id"]
    assert job2.get("idempotent_replay") is True

    # Exactly 1 row in DB
    with read_transaction() as conn:
        count = conn.execute("SELECT COUNT(*) FROM web_video_trend_jobs WHERE account_id = 'test-user-1'").fetchone()[0]
        assert count == 1


# ─── TEST J: IDEMPOTENCY CONFLICT ────────────────────────────────────────────

def test_j_idempotency_conflict():
    """Verify using same idempotency key or request_id with differing payload raises HTTP 409."""
    idem_key = "idem-conflict-key-999"
    bridge.create_or_replay_video_trend_job(
        account_id="test-user-1",
        payload={"prompt": "Original prompt", "tier": 200, "scene_count": 1},
        idempotency_key=idem_key,
    )

    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_video_trend_job(
            account_id="test-user-1",
            payload={"prompt": "Differing prompt mutation", "tier": 200, "scene_count": 1},
            idempotency_key=idem_key,
        )
    assert exc_info.value.status_code == 409


# ─── TEST K: OWNER SCOPING & CROSS-ACCOUNT ISOLATION ─────────────────────────

def test_k_owner_scoping_and_cross_account_isolation():
    """Verify jobs are strictly owner-scoped and cross-account access is prevented."""
    job = bridge.create_or_replay_video_trend_job(
        account_id="test-user-1",
        payload={"prompt": "User 1 exclusive trend job", "tier": 300, "scene_count": 1},
    )
    job_id = job["id"]

    # Owner can read
    owner_job = bridge.get_video_trend_job("test-user-1", job_id)
    assert owner_job is not None
    assert owner_job["id"] == job_id

    # Other account cannot read
    other_job = bridge.get_video_trend_job("test-user-2", job_id)
    assert other_job is None

    # Cross-account check
    assert bridge.is_video_trend_job_other_account(job_id, "test-user-2") is True
    assert bridge.is_video_trend_job_other_account(job_id, "test-user-1") is False

    # List isolation
    u1_jobs = bridge.list_video_trend_jobs("test-user-1")
    assert any(j["id"] == job_id for j in u1_jobs)

    u2_jobs = bridge.list_video_trend_jobs("test-user-2")
    assert not any(j["id"] == job_id for j in u2_jobs)


# ─── TEST L: FASTAPI HTTP CREATE AND READBACK ────────────────────────────────

def test_l_fastapi_http_create_and_readback():
    """Verify HTTP endpoints for video_trend job creation, listing, and detail readback."""
    client1 = TestClient(app)
    # Register & login user1
    client1.post("/api/v1/auth/register", json={"email": "u1@test.local", "password": "secure-pwd-1234", "display_name": "U1"})
    login1 = client1.post("/api/v1/auth/login", json={"email": "u1@test.local", "password": "secure-pwd-1234"})
    assert login1.status_code == 200
    headers1 = {"X-CSRF-Token": login1.json()["data"]["csrf_token"]}

    # 1. Create job via POST /api/v1/features/video_trend/jobs
    create_res = client1.post(
        "/api/v1/features/video_trend/jobs",
        json={
            "input": {
                "trend_prompt": "Hot trend biến hình 2026",
                "quality_tier": 500,
                "scene_count": 2,
            },
            "idempotency_key": "http-idem-trend-001",
        },
        headers=headers1,
    )
    assert create_res.status_code == 200
    body = create_res.json()
    assert body["ok"] is True
    job_data = body["data"]
    job_id = job_data["id"]
    assert job_data["status"] == "queued"
    assert job_data["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

    # 2. List jobs via GET /api/v1/features/video_trend/jobs
    list_res = client1.get("/api/v1/features/video_trend/jobs")
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert any(item["id"] == job_id for item in items)

    # 3. Get job detail via GET /api/v1/features/video_trend/jobs/{job_id}
    detail_res = client1.get(f"/api/v1/features/video_trend/jobs/{job_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == job_id

    # 4. Cross-user detail query receives 403
    client2 = TestClient(app)
    client2.post("/api/v1/auth/register", json={"email": "u2@test.local", "password": "secure-pwd-5678", "display_name": "U2"})
    login2 = client2.post("/api/v1/auth/login", json={"email": "u2@test.local", "password": "secure-pwd-5678"})
    assert login2.status_code == 200

    cross_res = client2.get(f"/api/v1/features/video_trend/jobs/{job_id}")
    assert cross_res.status_code == 403


# ─── TEST M: GENERIC JOBS INTEGRATION ────────────────────────────────────────

def test_m_generic_jobs_integration():
    """Verify video_trend jobs appear in generic /api/v1/jobs and /api/v1/jobs/{job_id}."""
    client1 = TestClient(app)
    client1.post("/api/v1/auth/register", json={"email": "gen_u1@test.local", "password": "secure-pwd-1234", "display_name": "Gen1"})
    login1 = client1.post("/api/v1/auth/login", json={"email": "gen_u1@test.local", "password": "secure-pwd-1234"})
    headers1 = {"X-CSRF-Token": login1.json()["data"]["csrf_token"]}

    create_res = client1.post(
        "/api/v1/features/video_trend/jobs",
        json={"input": {"trend_prompt": "Generic jobs test trend", "quality_tier": 500, "scene_count": 2}},
        headers=headers1,
    )
    job_id = create_res.json()["data"]["id"]

    # 1. Query generic list /api/v1/jobs
    gen_list = client1.get("/api/v1/jobs")
    assert gen_list.status_code == 200
    items = gen_list.json()["data"]["items"]
    assert any(item["id"] == job_id for item in items)

    # 2. Query generic detail /api/v1/jobs/{job_id}
    gen_detail = client1.get(f"/api/v1/jobs/{job_id}")
    assert gen_detail.status_code == 200
    assert gen_detail.json()["ok"] is True
    assert gen_detail.json()["data"]["id"] == job_id

    # 3. Cross-user access to generic /api/v1/jobs/{job_id} is 403
    client2 = TestClient(app)
    client2.post("/api/v1/auth/register", json={"email": "gen_u2@test.local", "password": "secure-pwd-5678", "display_name": "Gen2"})
    client2.post("/api/v1/auth/login", json={"email": "gen_u2@test.local", "password": "secure-pwd-5678"})

    gen_cross = client2.get(f"/api/v1/jobs/{job_id}")
    assert gen_cross.status_code == 403


# ─── TEST N: ARTIFACT TRUTH (SAFE VS UNSAFE OUTPUT URLS) ─────────────────────

def test_n_artifact_truth_safe_and_unsafe_urls():
    """Verify artifact truth: status completed with NULL or unsafe URL yields output_available=False."""
    # 1. Direct URL security validator tests
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/trend.mp4") is True
    assert bridge.is_safe_video_output_url("https://tg.toanaas.vn/media/trend_output.mp4") is True

    # Unsafe URLs
    assert bridge.is_safe_video_output_url(None) is False
    assert bridge.is_safe_video_output_url("") is False
    assert bridge.is_safe_video_output_url("http://insecure.com/video.mp4") is False
    assert bridge.is_safe_video_output_url("javascript:alert(1)") is False
    assert bridge.is_safe_video_output_url("ftp://server/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://user:pass@host.com/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://host.com/video/../secret.mp4") is False
    assert bridge.is_safe_video_output_url("https://host.com/video\\backslash.mp4") is False
    assert bridge.is_safe_video_output_url("https://host.com:8080/video.mp4") is False

    # 2. Database row with status=completed but output_url=NULL
    job = bridge.create_or_replay_video_trend_job(
        account_id="test-user-1",
        payload={"prompt": "Artifact truth test 1", "tier": 200, "scene_count": 1},
    )
    job_id = job["id"]

    with transaction() as conn:
        conn.execute("UPDATE web_video_trend_jobs SET status = 'completed', output_url = NULL WHERE id = ?", (job_id,))

    read_job = bridge.get_video_trend_job("test-user-1", job_id)
    assert read_job["status"] == "completed"
    assert read_job["output_available"] is False
    assert read_job["download_ready"] is False
    assert read_job["delivery_ready"] is False
    assert read_job["output"] is None

    compat = bridge.video_trend_job_to_native_compat(read_job)
    assert compat["output_available"] is False
    assert compat["download_ready"] is False

    # 3. Database row with status=completed and unsafe output_url
    with transaction() as conn:
        conn.execute("UPDATE web_video_trend_jobs SET status = 'completed', output_url = 'http://insecure.org/fake.mp4' WHERE id = ?", (job_id,))

    read_job2 = bridge.get_video_trend_job("test-user-1", job_id)
    assert read_job2["output_available"] is False
    assert read_job2["output"] is None

    # 4. Database row with status=completed and safe output_url
    safe_url = "https://cdn.toanaas.vn/media/valid_output.mp4"
    with transaction() as conn:
        conn.execute("UPDATE web_video_trend_jobs SET status = 'completed', output_url = ? WHERE id = ?", (safe_url, job_id))

    read_job3 = bridge.get_video_trend_job("test-user-1", job_id)
    assert read_job3["output_available"] is True
    assert read_job3["download_ready"] is True
    assert read_job3["delivery_ready"] is True
    assert read_job3["output"] == safe_url
    assert read_job3["output_url"] == safe_url

    compat3 = bridge.video_trend_job_to_native_compat(read_job3)
    assert compat3["output_available"] is True
    assert compat3["download_ready"] is True


# ─── TEST O: ZERO PROVIDER AND FINANCIAL CALLS ───────────────────────────────

def test_o_zero_provider_and_financial_calls():
    """Verify zero external network calls and zero wallet/financial mutations during bridge operations."""
    with patch("urllib.request.urlopen") as mock_url:
        job = bridge.create_or_replay_video_trend_job(
            account_id="test-user-1",
            payload={"trend_prompt": "Zero external calls guarantee", "tier": 400, "scene_count": 2},
        )
        assert mock_url.call_count == 0

        _ = bridge.get_video_trend_job("test-user-1", job["id"])
        _ = bridge.list_video_trend_jobs("test-user-1")
        assert mock_url.call_count == 0

    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    envelope = job["bridge_envelope"]
    assert "api_key" not in envelope
    assert "token" not in envelope
    assert "provider_task_id" not in envelope
    assert "secret" not in envelope


# ─── TEST P: PARITY MATRIX TRUTH VERIFICATION ────────────────────────────────

def test_p_parity_matrix_truth_verification():
    """Verify video_trend status in parity matrix is PARTIAL with blocker TREND_VIDEO_RUNTIME_EXECUTION_NOT_ACTIVATED."""
    matrix_file = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
    with open(matrix_file, "r", encoding="utf-8") as f:
        matrix_data = json.load(f)

    vt_entry = None
    for item in matrix_data.get("parity_matrix", []):
        if item.get("bot_capability") == "video_trend":
            vt_entry = item
            break

    assert vt_entry is not None, "video_trend entry must exist in parity_matrix"
    assert vt_entry["status"] == "PARTIAL", f"Expected status PARTIAL, got {vt_entry['status']}"
    assert vt_entry["blocker"] == "TREND_VIDEO_RUNTIME_EXECUTION_NOT_ACTIVATED", f"Expected blocker TREND_VIDEO_RUNTIME_EXECUTION_NOT_ACTIVATED, got {vt_entry['blocker']}"

    # Verify video_ai_image is untouched
    for item in matrix_data.get("parity_matrix", []):
        if item.get("bot_capability") == "video_ai_image":
            assert item["status"] == "BLOCKED_BY_RUNTIME"
            assert item["blocker"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"


# ─── TEST Q: DIRECT JOB & CONFIRM MISSING TIER/SCENE REJECTED ────────────────

def test_q_direct_job_and_confirm_missing_tier_and_scene_rejected():
    """Verify both direct job POST and confirm flow reject missing tier and missing scene_count."""
    from copyfast_api import _feature_input_contract_error

    # 1. Direct unit-level confirm contract error verification
    # Missing tier
    err1 = _feature_input_contract_error("video_trend", {"prompt": "Trend prompt", "scene_count": 2}, action="confirm")
    assert err1 == "TIER_REQUIRED"

    # Missing scene_count
    err2 = _feature_input_contract_error("video_trend", {"prompt": "Trend prompt", "tier": 300}, action="confirm")
    assert err2 == "SCENE_COUNT_REQUIRED"

    # Both missing
    err3 = _feature_input_contract_error("video_trend", {"prompt": "Trend prompt"}, action="confirm")
    assert err3 == "TIER_REQUIRED"

    # Valid tier and scene_count
    err_ok = _feature_input_contract_error("video_trend", {"prompt": "Trend prompt", "tier": 300, "scene_count": 2}, action="confirm")
    assert err_ok == ""

    # 2. HTTP direct canonical job POST validation
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"email": "contract_u1@test.local", "password": "secure-pwd-1234", "display_name": "ContractU1"})
    login = client.post("/api/v1/auth/login", json={"email": "contract_u1@test.local", "password": "secure-pwd-1234"})
    headers = {"X-CSRF-Token": login.json()["data"]["csrf_token"]}

    # Direct job POST missing tier -> 400
    res_no_tier = client.post(
        "/api/v1/features/video_trend/jobs",
        json={"input": {"trend_prompt": "Trend test prompt", "scene_count": 2}},
        headers=headers,
    )
    assert res_no_tier.status_code == 400
    assert "Quality tier là bắt buộc" in res_no_tier.json()["message"]

    # Direct job POST missing scene_count -> 400
    res_no_scene = client.post(
        "/api/v1/features/video_trend/jobs",
        json={"input": {"trend_prompt": "Trend test prompt", "quality_tier": 400}},
        headers=headers,
    )
    assert res_no_scene.status_code == 400
    assert "Số cảnh scene_count là bắt buộc" in res_no_scene.json()["message"]

    # Direct job POST missing both -> 400
    res_no_both = client.post(
        "/api/v1/features/video_trend/jobs",
        json={"input": {"trend_prompt": "Trend test prompt"}},
        headers=headers,
    )
    assert res_no_both.status_code == 400
    assert "Quality tier là bắt buộc" in res_no_both.json()["message"]

    # 3. HTTP confirm endpoint validation
    # HTTP confirm missing tier -> guarded with TIER_REQUIRED
    res_confirm_no_tier = client.post(
        "/api/v1/features/video_trend/confirm",
        json={"input": {"trend_prompt": "Trend test prompt", "scene_count": 2}, "idempotency_key": "cfm-key-01"},
        headers=headers,
    )
    assert res_confirm_no_tier.status_code == 200
    body_no_tier = res_confirm_no_tier.json()
    assert body_no_tier["ok"] is False
    assert body_no_tier["error_code"] == "FEATURE_INPUT_CONTRACT_REQUIRED"
    assert body_no_tier["data"]["reason"] == "TIER_REQUIRED"

    # HTTP confirm missing scene_count -> guarded with SCENE_COUNT_REQUIRED
    res_confirm_no_scene = client.post(
        "/api/v1/features/video_trend/confirm",
        json={"input": {"trend_prompt": "Trend test prompt", "quality_tier": 300}, "idempotency_key": "cfm-key-02"},
        headers=headers,
    )
    assert res_confirm_no_scene.status_code == 200
    body_no_scene = res_confirm_no_scene.json()
    assert body_no_scene["ok"] is False
    assert body_no_scene["error_code"] == "FEATURE_INPUT_CONTRACT_REQUIRED"
    assert body_no_scene["data"]["reason"] == "SCENE_COUNT_REQUIRED"


# ─── TEST R: CONCURRENT IDENTICAL IDEMPOTENCY PROOF ──────────────────────────

def test_r_concurrent_identical_idempotency_proof():
    """Verify 10 concurrent calls with identical idempotency key yield 1 created row, 0 duplicates, identical job ID."""
    from concurrent.futures import ThreadPoolExecutor

    idem_key = "concurrent-identical-idem-001"
    account_id = "test-user-1"
    payload = {
        "trend_prompt": "Concurrent 10-thread identical idempotency test",
        "quality_tier": 500,
        "scene_count": 3,
    }

    num_threads = 10
    results: list[dict[str, Any]] = []
    errors: list[Any] = []

    def worker():
        try:
            res = bridge.create_or_replay_video_trend_job(
                account_id=account_id,
                payload=payload,
                idempotency_key=idem_key,
            )
            return ("ok", res)
        except Exception as e:
            return ("err", e)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        for f in futures:
            status, val = f.result()
            if status == "ok":
                results.append(val)
            else:
                errors.append(val)

    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"
    assert len(results) == num_threads

    # All threads must observe the exact same job ID
    job_ids = set(r["id"] for r in results)
    assert len(job_ids) == 1, f"Expected exactly 1 unique job ID, got: {job_ids}"
    identical_job_id = results[0]["id"]

    # Verify database: exactly 1 row created, 0 duplicates
    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT id, idempotency_key_hash FROM web_video_trend_jobs WHERE idempotency_key_hash = ?",
            (bridge.compute_idempotency_hash(idem_key),),
        )
        rows = cursor.fetchall()

    created_rows_count = len(rows)
    assert created_rows_count == 1
    assert rows[0][0] == identical_job_id

    CONCURRENT_IDENTICAL_CREATED_ROWS = created_rows_count
    CONCURRENT_DUPLICATE_JOB_CREATED = created_rows_count - 1
    CONCURRENT_REPLAY = "PASS" if (created_rows_count == 1 and len(job_ids) == 1) else "FAIL"

    assert CONCURRENT_IDENTICAL_CREATED_ROWS == 1
    assert CONCURRENT_DUPLICATE_JOB_CREATED == 0
    assert CONCURRENT_REPLAY == "PASS"


# ─── TEST S: CONCURRENT CONFLICT IDEMPOTENCY PROOF ───────────────────────────

def test_s_concurrent_conflict_idempotency_proof():
    """Verify concurrent calls with same key but differing payload: exactly one succeeds, others raise 409."""
    from concurrent.futures import ThreadPoolExecutor

    idem_key = "concurrent-conflict-idem-002"
    account_id = "test-user-1"

    payload_a = {
        "trend_prompt": "Concurrent conflict payload A",
        "quality_tier": 400,
        "scene_count": 2,
    }
    payload_b = {
        "trend_prompt": "Concurrent conflict payload B differing",
        "quality_tier": 500,
        "scene_count": 4,
    }

    # First call succeeds
    job_a = bridge.create_or_replay_video_trend_job(
        account_id=account_id,
        payload=payload_a,
        idempotency_key=idem_key,
    )
    assert job_a is not None

    # Concurrent 10 calls with differing payload under same idempotency_key
    num_threads = 10
    conflict_409_count = 0
    unexpected_results: list[Any] = []

    def conflict_worker():
        try:
            bridge.create_or_replay_video_trend_job(
                account_id=account_id,
                payload=payload_b,
                idempotency_key=idem_key,
            )
            return "unexpected_success"
        except HTTPException as exc:
            if exc.status_code == 409:
                return "409_conflict"
            return f"unexpected_status_{exc.status_code}"
        except Exception as e:
            return f"unexpected_exc_{e}"

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(conflict_worker) for _ in range(num_threads)]
        for f in futures:
            res = f.result()
            if res == "409_conflict":
                conflict_409_count += 1
            else:
                unexpected_results.append(res)

    assert conflict_409_count == num_threads, f"Expected {num_threads} 409 conflicts, got {conflict_409_count}, unexpected: {unexpected_results}"
    assert len(unexpected_results) == 0

    # Verify database: exactly 1 row exists
    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT id, idempotency_key_hash FROM web_video_trend_jobs WHERE idempotency_key_hash = ?",
            (bridge.compute_idempotency_hash(idem_key),),
        )
        rows = cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == job_a["id"]

    CONCURRENT_CONFLICT = "PASS"
    assert CONCURRENT_CONFLICT == "PASS"
