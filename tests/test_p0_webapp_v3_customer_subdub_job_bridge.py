"""Tests for SubDub Canonical Job Bridge Adapter (WEB_R2).

Task: P0.WEBAPP.V3.SUBDUB.CANONICAL.DURABLE.JOB_BRIDGE.R1 (WEB_R2)
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Parent Task: P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1

Enforces:
1. Product Identity: canonical key `subdub`, entrypoint `/subdub`.
2. 4 Canonical Lanes: subtitle_create, subtitle_translate, dub, subtitle_plus_dub.
3. Upload ID Authority: valid opaque ID accepted; paths and remote URLs rejected.
4. Input Validation: target language required on translation/dubbing lanes; authority fields rejected.
5. Output Format Reconciliation: overrides srt-only on dubbing to canonical media output.
6. Persistence: persists durable record in SQLite table `web_subdub_jobs` with status 'queued',
   status_reason 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION', zero fake output.
7. Idempotency & Conflict: exact replay returns existing job with idempotent_replay=True;
   different payload on same request_id returns 409 Conflict.
8. Query & Cross-User Security: owner can read job detail; other user rejected with 403.
9. Jobs Read Model Unification: GET /api/v1/jobs and GET /api/v1/jobs/{job_id} include SubDub jobs.
10. Invariants: zero external provider calls, zero wallet mutations, zero fake completion.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

import copyfast_registry as reg
from app import app
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_subdub_job_bridge as bridge


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-subdub-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "subdub,video_dub,subtitle_create,subtitle_translate")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    import app as app_module
    import copyfast_api
    monkeypatch.setattr(copyfast_api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub", "video_dub", "subtitle_create", "subtitle_translate"}))
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()
    ensure_copyfast_schema()
    bridge.ensure_subdub_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs")
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
        conn.execute("DELETE FROM web_subdub_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


# ─── TEST 1: PRODUCT IDENTITY AND ENTRYPOINT ─────────────────────────────────

def test_01_canonical_product_identity_and_entrypoint():
    """Prove canonical product identity, entrypoint, routing key, and registry integrity."""
    assert bridge.CANONICAL_PRODUCT_KEY == "subdub"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/subdub"
    assert bridge.CANONICAL_ROUTING_KEY == "subdub_canonical"
    assert bridge.CANONICAL_ROUTE_ID == "subdub_canonical_v1"
    assert bridge.CANONICAL_ENGINE_ADAPTER == "b13_r18c_subdub_v1"
    assert "subdub" in bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS
    assert "video_dub" in bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS
    assert "subtitle_create" in bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS
    assert "subtitle_translate" in bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS


# ─── TEST 2: UPLOAD ID VALIDATION & REJECTION OF PATHS/URLS ─────────────────

def test_02_upload_id_validation_and_path_url_rejection():
    """Verify upload_id must be canonical opaque ID and rejects local paths / URLs."""
    # 1. Missing upload_id rejected
    ok, err, _ = bridge.validate_subdub_input({"mode": "subtitle_create"})
    assert not ok
    assert err == "UPLOAD_ID_REQUIRED"

    # 2. Local unix path rejected
    ok, err, _ = bridge.validate_subdub_input({"upload_id": "/var/media/input.mp4", "mode": "subtitle_create"})
    assert not ok
    assert err == "INVALID_UPLOAD_ID"

    # 3. Local windows path rejected
    ok, err, _ = bridge.validate_subdub_input({"upload_id": "C:\\videos\\input.mp4", "mode": "subtitle_create"})
    assert not ok
    assert err == "INVALID_UPLOAD_ID"

    # 4. Traversal path rejected
    ok, err, _ = bridge.validate_subdub_input({"upload_id": "../secret.mp4", "mode": "subtitle_create"})
    assert not ok
    assert err == "INVALID_UPLOAD_ID"

    # 5. Remote URL rejected
    ok, err, _ = bridge.validate_subdub_input({"upload_id": "https://youtube.com/watch?v=xyz", "mode": "subtitle_create"})
    assert not ok
    assert err == "INVALID_UPLOAD_ID"

    # 6. Valid opaque Bot staging upload_id accepted
    ok, err, norm = bridge.validate_subdub_input({"upload_id": "upl_01h7abc123def456", "mode": "subtitle_create"})
    assert ok
    assert err == ""
    assert norm["upload_id"] == "upl_01h7abc123def456"


# ─── TEST 3: MODE NORMALIZATION TO 4 CANONICAL LANES ─────────────────────────

def test_03_mode_normalization_to_four_canonical_lanes():
    """Verify legacy and user-facing mode names normalize to canonical 4 lanes."""
    assert bridge.normalize_subdub_mode("subtitle_create") == "subtitle_create"
    assert bridge.normalize_subdub_mode("subtitle_asr") == "subtitle_create"
    assert bridge.normalize_subdub_mode("asr") == "subtitle_create"

    assert bridge.normalize_subdub_mode("subtitle_translate") == "subtitle_translate"
    assert bridge.normalize_subdub_mode("translate") == "subtitle_translate"

    assert bridge.normalize_subdub_mode("dub") == "dub"
    assert bridge.normalize_subdub_mode("dubbing") == "dub"
    assert bridge.normalize_subdub_mode("video_dub") == "dub"

    assert bridge.normalize_subdub_mode("subtitle_plus_dub") == "subtitle_plus_dub"
    assert bridge.normalize_subdub_mode("subtitle_plus_dubbing") == "subtitle_plus_dub"
    assert bridge.normalize_subdub_mode("combo") == "subtitle_plus_dub"

    assert bridge.normalize_subdub_mode("unknown_mode") == ""


# ─── TEST 4: TARGET LANGUAGE VALIDATION ──────────────────────────────────────

def test_04_target_language_validation_on_translation_and_dubbing():
    """Verify target_language is mandatory for subtitle_translate, dub, and subtitle_plus_dub."""
    # subtitle_create does not require target_language
    ok, _, norm = bridge.validate_subdub_input({"upload_id": "upl_test1", "mode": "subtitle_create"})
    assert ok
    assert norm["subdub_mode"] == "subtitle_create"

    # subtitle_translate requires target_language
    ok, err, _ = bridge.validate_subdub_input({"upload_id": "upl_test1", "mode": "subtitle_translate"})
    assert not ok
    assert err == "TARGET_LANGUAGE_REQUIRED"

    # dub requires target_language
    ok, err, _ = bridge.validate_subdub_input({"upload_id": "upl_test1", "mode": "dub"})
    assert not ok
    assert err == "TARGET_LANGUAGE_REQUIRED"

    # subtitle_plus_dub requires target_language
    ok, err, _ = bridge.validate_subdub_input({"upload_id": "upl_test1", "mode": "subtitle_plus_dub"})
    assert not ok
    assert err == "TARGET_LANGUAGE_REQUIRED"

    # With target_language, all pass
    ok, _, norm = bridge.validate_subdub_input({
        "upload_id": "upl_test1",
        "mode": "dub",
        "target_language": "vi",
    })
    assert ok
    assert norm["target_language"] == "vi"


# ─── TEST 5: OUTPUT FORMAT RECONCILIATION ────────────────────────────────────

def test_05_output_format_reconciliation_overrides_client_srt_only():
    """Verify dubbing overrides client-side srt-only restriction to canonical media output."""
    # Dubbing with client srt option -> overridden to video
    ok, _, norm = bridge.validate_subdub_input({
        "upload_id": "upl_test1",
        "mode": "dub",
        "target_language": "vi",
        "output_format": "srt",
    })
    assert ok
    assert norm["output_format"] == "video"

    # Subtitle plus dubbing with client srt option -> overridden to video_subtitle
    ok, _, norm = bridge.validate_subdub_input({
        "upload_id": "upl_test1",
        "mode": "subtitle_plus_dub",
        "target_language": "vi",
        "output_format": "srt",
    })
    assert ok
    assert norm["output_format"] == "video_subtitle"

    # Subtitle create preserves subtitle format
    ok, _, norm = bridge.validate_subdub_input({
        "upload_id": "upl_test1",
        "mode": "subtitle_create",
        "output_format": "vtt",
    })
    assert ok
    assert norm["output_format"] == "vtt"


# ─── TEST 6: FORBIDDEN AUTHORITY FIELD INJECTION REJECTION ───────────────────

def test_06_forbidden_authority_field_injection_rejected():
    """Verify forged authority fields are strictly rejected."""
    forged_fields = [
        {"role": "admin"},
        {"status": "completed"},
        {"balance": 1000},
        {"xu": 500},
        {"provider_voice_id": "elevenlabs_secret_id"},
        {"output_url": "https://cdn.example.com/fake.mp4"},
    ]
    for field_dict in forged_fields:
        payload = {"upload_id": "upl_test1", "mode": "subtitle_create", **field_dict}
        ok, err, _ = bridge.validate_subdub_input(payload)
        assert not ok
        assert err == "authority_field_not_allowed"


# ─── TEST 7: DURABLE JOB CREATION & TRUTHFUL QUEUED STATUS ───────────────────

def test_07_durable_job_creation_and_truthful_queued_status():
    """Verify job is created in web_subdub_jobs with status 'queued' and zero fake completion."""
    job = bridge.create_or_replay_subdub_job(
        account_id="test-user-1",
        payload={
            "upload_id": "upl_valid_test_01",
            "mode": "dub",
            "target_language": "vi",
            "voice_profile_id": "female_north_mai",
            "speed": 1.1,
        },
    )

    assert job["id"].startswith("sdj_")
    assert job["request_id"].startswith("SDB-")
    assert job["account_id"] == "test-user-1"
    assert job["product_key"] == "subdub"
    assert job["subdub_mode"] == "dub"
    assert job["upload_id"] == "upl_valid_test_01"
    assert job["target_language"] == "vi"
    assert job["voice_profile_id"] == "female_north_mai"
    assert job["output_format"] == "video"
    assert job["speed"] == 1.1
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False
    assert job["output"] is None
    assert job["output_url"] is None
    assert job["idempotent_replay"] is False

    # Verify directly in SQLite
    with read_transaction() as conn:
        row = conn.execute("SELECT status, status_reason, output_url FROM web_subdub_jobs WHERE id = ?", (job["id"],)).fetchone()
        assert row is not None
        assert row[0] == "queued"
        assert row[1] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
        assert row[2] is None


# ─── TEST 8: IDEMPOTENCY REPLAY & CONFLICT DETECTION ─────────────────────────

def test_08_idempotency_replay_and_conflict_detection():
    """Verify exact replay returns existing job, different payload on same request_id returns 409."""
    payload_a = {
        "upload_id": "upl_idem_test",
        "mode": "subtitle_create",
        "output_format": "srt",
        "request_id": "SDB-20260929-TEST01",
    }
    job1 = bridge.create_or_replay_subdub_job(
        account_id="test-user-1",
        payload=payload_a,
        request_id="SDB-20260929-TEST01",
    )
    assert job1["idempotent_replay"] is False

    # Exact replay returns existing job
    job2 = bridge.create_or_replay_subdub_job(
        account_id="test-user-1",
        payload=payload_a,
        request_id="SDB-20260929-TEST01",
    )
    assert job2["id"] == job1["id"]
    assert job2["idempotent_replay"] is True

    # Differing payload on same request_id raises 409 Conflict
    payload_diff = {
        "upload_id": "upl_different_upload",
        "mode": "subtitle_create",
        "output_format": "srt",
        "request_id": "SDB-20260929-TEST01",
    }
    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_subdub_job(
            account_id="test-user-1",
            payload=payload_diff,
            request_id="SDB-20260929-TEST01",
        )
    assert exc_info.value.status_code == 409


# ─── TEST 9: QUERY & CROSS-USER SECURITY ISOLATION ───────────────────────────

def test_09_query_and_cross_user_security():
    """Verify owner can retrieve job, but another account receives 403 Forbidden."""
    job = bridge.create_or_replay_subdub_job(
        account_id="test-user-1",
        payload={"upload_id": "upl_sec_test", "mode": "subtitle_create"},
    )
    job_id = job["id"]

    # Owner can get job
    fetched = bridge.get_subdub_job("test-user-1", job_id)
    assert fetched is not None
    assert fetched["id"] == job_id

    # Another account cannot get job (returns None)
    other_fetched = bridge.get_subdub_job("test-user-2", job_id)
    assert other_fetched is None

    # is_subdub_job_other_account detects foreign ownership
    assert bridge.is_subdub_job_other_account(job_id, "test-user-2") is True
    assert bridge.is_subdub_job_other_account(job_id, "test-user-1") is False

    # List jobs returns only user's jobs
    user1_jobs = bridge.list_subdub_jobs("test-user-1")
    assert len(user1_jobs) == 1
    assert user1_jobs[0]["id"] == job_id

    user2_jobs = bridge.list_subdub_jobs("test-user-2")
    assert len(user2_jobs) == 0


# ─── TEST 10: FASTAPI ROUTES INTEGRATION (CONFIRM, LIST, DETAIL) ─────────────

def _register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Test Account",
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def test_10_fastapi_routes_subdub_jobs_integration():
    """Verify FastAPI routes for SubDub jobs work cleanly via TestClient."""
    from app import app
    client = TestClient(app)

    # 1. Register and login test-user-1
    csrf1 = _register_and_login(client, "subdub-user-1@test.local")

    # 2. POST /api/v1/features/subdub/jobs
    res = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {
                "upload_id": "upl_route_test_01",
                "mode": "dub",
                "target_language": "vi",
            },
            "idempotency_key": "idem-route-test-1",
        },
        headers={"x-csrf-token": csrf1},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ok"] is True
    job_id = data["data"]["id"]
    assert job_id.startswith("sdj_")
    assert data["data"]["subdub_mode"] == "dub"
    assert data["data"]["output_format"] == "video"

    # 3. GET /api/v1/features/subdub/jobs
    res_list = client.get("/api/v1/features/subdub/jobs")
    assert res_list.status_code == 200
    items = res_list.json()["data"]["items"]
    assert any(item["id"] == job_id for item in items)

    # 4. GET /api/v1/features/subdub/jobs/{job_id}
    res_detail = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["data"]["id"] == job_id

    # 5. GET /api/v1/jobs (unified read model includes SubDub job)
    res_unified = client.get("/api/v1/jobs")
    assert res_unified.status_code == 200
    unified_items = res_unified.json()["data"]["items"]
    assert any(item["id"] == job_id for item in unified_items)

    # 6. GET /api/v1/jobs/{job_id} (unified detail)
    res_unified_detail = client.get(f"/api/v1/jobs/{job_id}")
    assert res_unified_detail.status_code == 200
    assert res_unified_detail.json()["data"]["id"] == job_id

    # 7. Cross-user access via separate client returns 403
    client2 = TestClient(app)
    _register_and_login(client2, "subdub-user-2@test.local")
    res_cross = client2.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_cross.status_code == 403
    res_cross_unified = client2.get(f"/api/v1/jobs/{job_id}")
    assert res_cross_unified.status_code == 403
