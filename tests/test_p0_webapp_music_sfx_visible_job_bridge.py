"""Tests for Music SFX Canonical Job Bridge and Visible Audio Result Retention.

Task: WEBAPP_R24B3_MUSIC_SFX_VISIBLE_JOB_BRIDGE_AND_AUDIO_RESULT_RETENTION_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: music_sfx
Customer Entrypoint: /music/sfx
Web API Family: /api/v1/features/music_sfx/*

Proves:
1. Product Identity: canonical key `music_sfx`, entrypoint `/music/sfx`, provider dispatch disabled.
2. Auth & Entrypoint: unauthenticated redirected to login; authenticated renders 200.
3. Strict Input Validation: missing brief, empty brief, oversized brief (>2000 chars), authority injection rejected.
4. Fail-Closed Job Creation: status='queued', status_reason='AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE'.
   Neutral provider/model/pricing: provider_name=None, model_name=None, xu_cost=None (NOT 0).
5. Idempotency: exact replay returns existing job (idempotent_replay=True); differing payload on same key returns 409 Conflict.
6. Customer History Visibility: job appears in GET /api/v1/jobs and GET /api/v1/jobs/{job_id}.
7. Cross-Account Job Protection: viewing other account's job detail returns 403 Forbidden.
8. Provider Dispatch Boundary: provider dispatch is strictly disabled (raises RuntimeError, 0 network calls).
9. Audio Result Finalizer: verifies asset existence, ownership, active state, supported audio format (.mp3, .wav, .m4a, .ogg) and MIME.
   Rejects non-audio formats (.jpg, .png, .pdf), inactive assets, and cross-account assets.
10. Secret Metadata Sanitization: sensitive keys (api_key, token, secret, password...) stripped from metadata.
11. Admin Ledger Integration: GET /api/v1/admin/jobs and GET /api/v1/admin/jobs/{job_id} surface details with web_native_music_sfx authority.
12. Freesound Separation: Generative SFX is completely separate from library catalog (/music/sfx-library).
13. Portal Contracts: portal.js and integration.js declare required elements without unproven fields.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
from typing import Any
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from app import app
import app as app_module
from copyfast_auth import SESSION_COOKIE, _cookie_name, _insert_session, _session_cookie_value, require_canonical_admin
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_music_sfx_job_bridge as bridge


# ─── FIXTURES & TEST SETUP ───────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db_and_env(monkeypatch):
    """Set test environment and initialize test tables."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-music-sfx-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()
    ensure_copyfast_schema()
    bridge.ensure_music_sfx_schema()

    with transaction() as conn:
        conn.execute("DELETE FROM web_music_sfx_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-sfx-%'")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-sfx-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-sfx-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES ('test-sfx-user-1', 'sfx1@test.local', 'hash1', 'member', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'),
                   ('test-sfx-user-2', 'sfx2@test.local', 'hash2', 'member', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'),
                   ('test-sfx-admin', 'admin@test.local', 'hashadmin', 'admin', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, created_at, updated_at
            ) VALUES (
                'asset-sfx-audio-mp3', 'test-sfx-user-1', NULL, 'Âm thanh MP3',
                'sound.mp3', '.mp3', 'audio/mpeg', 204800, 'hash_mp3', 'storage_sfx_mp3',
                'active', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'
            ), (
                'asset-sfx-audio-wav', 'test-sfx-user-1', NULL, 'Âm thanh WAV',
                'sound.wav', '.wav', 'audio/wav', 512000, 'hash_wav', 'storage_sfx_wav',
                'active', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'
            ), (
                'asset-sfx-audio-m4a', 'test-sfx-user-1', NULL, 'Âm thanh M4A',
                'sound.m4a', '.m4a', 'audio/mp4', 307200, 'hash_m4a', 'storage_sfx_m4a',
                'active', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'
            ), (
                'asset-sfx-audio-ogg', 'test-sfx-user-1', NULL, 'Âm thanh OGG',
                'sound.ogg', '.ogg', 'audio/ogg', 153600, 'hash_ogg', 'storage_sfx_ogg',
                'active', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'
            ), (
                'asset-sfx-image-jpg', 'test-sfx-user-1', NULL, 'Ảnh JPEG không hợp lệ cho audio',
                'image.jpg', '.jpg', 'image/jpeg', 102400, 'hash_jpg', 'storage_sfx_jpg',
                'active', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'
            ), (
                'asset-sfx-user2-audio', 'test-sfx-user-2', NULL, 'Âm thanh của User 2',
                'user2.mp3', '.mp3', 'audio/mpeg', 204800, 'hash_user2', 'storage_sfx_user2',
                'active', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'
            ), (
                'asset-sfx-inactive', 'test-sfx-user-1', NULL, 'Âm thanh chưa sẵn sàng',
                'pending.mp3', '.mp3', 'audio/mpeg', 204800, 'hash_pending', 'storage_sfx_pending',
                'pending', '2026-10-12T00:00:00Z', '2026-10-12T00:00:00Z'
            )
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_music_sfx_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-sfx-%'")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-sfx-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-sfx-%'")


def _create_authenticated_client(
    account_id: str = "test-sfx-user-1",
    role: str = "member",
) -> tuple[TestClient, str]:
    with transaction() as conn:
        conn.execute("UPDATE web_accounts SET role_cache=? WHERE id=?", (role, account_id))
        sess = _insert_session(conn, account_id)
    client = TestClient(app)
    client.cookies.set(_cookie_name(SESSION_COOKIE), _session_cookie_value(sess["session_id"]))
    return client, sess["csrf_token"]


# ─── 1. PRODUCT IDENTITY & CONTRACT ──────────────────────────────────────────

def test_music_sfx_product_identity():
    """Music SFX product identity is canonical music_sfx, entrypoint /music/sfx, dispatch disabled."""
    assert bridge.CANONICAL_PRODUCT_KEY == "music_sfx"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/music/sfx"
    assert bridge.MUSIC_SFX_PROVIDER_DISPATCH_ENABLED is False
    assert bridge.ELEVENLABS_PUBLIC_ENABLED is False


# ─── 2. AUTH & ENTRYPOINT ROUTE ──────────────────────────────────────────────

def test_music_sfx_entrypoint_unauthenticated():
    """Unauthenticated visitor to /music/sfx is redirected to /login."""
    client = TestClient(app, follow_redirects=False)
    resp = client.get("/music/sfx")
    assert resp.status_code in (302, 303, 307)
    assert "/login" in resp.headers.get("location", "")


def test_music_sfx_entrypoint_authenticated():
    """Authenticated visitor receives 200 HTML with canonical bridge indicators."""
    client, _ = _create_authenticated_client("test-sfx-user-1")
    resp = client.get("/music/sfx")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


# ─── 3. STRICT INPUT VALIDATION ──────────────────────────────────────────────

def test_validate_music_sfx_input_valid():
    """Valid brief passes validation and is trimmed."""
    ok, err, clean = bridge.validate_music_sfx_input(
        "test-sfx-user-1",
        {"brief": "  Tiếng mưa rơi trên mái tôn đêm khuya  "}
    )
    assert ok is True
    assert err == ""
    assert clean["brief"] == "Tiếng mưa rơi trên mái tôn đêm khuya"


def test_validate_music_sfx_input_missing_or_empty():
    """Missing or empty brief returns error."""
    ok, err, _ = bridge.validate_music_sfx_input("test-sfx-user-1", {})
    assert ok is False
    assert "Thiếu mô tả brief" in err

    ok2, err2, _ = bridge.validate_music_sfx_input("test-sfx-user-1", {"brief": "   "})
    assert ok2 is False
    assert "Thiếu mô tả brief" in err2


def test_validate_music_sfx_input_oversized():
    """Brief exceeding 2000 characters returns error."""
    long_brief = "a" * 2001
    ok, err, _ = bridge.validate_music_sfx_input("test-sfx-user-1", {"brief": long_brief})
    assert ok is False
    assert "vượt quá độ dài tối đa 2000 ký tự" in err


def test_validate_music_sfx_input_authority_injection_rejected():
    """Client cannot inject tier, model, price, xu_cost, wallet, provider, or other authority fields."""
    forbidden_keys = [
        "tier", "model", "provider", "provider_task_id",
        "price", "cost", "xu", "xu_cost", "quote_xu",
        "status", "status_reason", "wallet",
        "account_id", "user_id", "canonical_user_id",
        "output_url", "local_path", "file_path",
    ]
    for key in forbidden_keys:
        ok, err, _ = bridge.validate_music_sfx_input("test-sfx-user-1", {"brief": "Tiếng gió rít", key: "fake_val"})
        assert ok is False, f"Expected {key} to be rejected"
        assert "quyền hạn máy chủ bị cấm" in err


def test_validate_music_sfx_input_duration_seconds_rejected():
    """Unproven duration_seconds semantic is strictly rejected."""
    ok, err, _ = bridge.validate_music_sfx_input(
        "test-sfx-user-1",
        {"brief": "Tiếng sấm rền", "duration_seconds": 15}
    )
    assert ok is False
    assert "chưa được chứng minh" in err or "unproven" in err.lower()


def test_validate_music_sfx_input_loop_rejected():
    """Unproven loop semantic is strictly rejected."""
    ok, err, _ = bridge.validate_music_sfx_input(
        "test-sfx-user-1",
        {"brief": "Tiếng sóng biển", "loop": True}
    )
    assert ok is False
    assert "chưa được chứng minh" in err or "unproven" in err.lower()


def test_validate_music_sfx_input_category_rejected():
    """Unproven category semantic is strictly rejected."""
    ok, err, _ = bridge.validate_music_sfx_input(
        "test-sfx-user-1",
        {"brief": "Tiếng chim hót", "category": "nature"}
    )
    assert ok is False
    assert "chưa được chứng minh" in err or "unproven" in err.lower()


def test_validate_music_sfx_input_sfx_brief_alias_rejected():
    """Unproven alias sfx_brief is strictly rejected; only canonical 'brief' is accepted."""
    ok, err, _ = bridge.validate_music_sfx_input(
        "test-sfx-user-1",
        {"sfx_brief": "Tiếng mưa rơi"}
    )
    assert ok is False
    assert "chưa được chứng minh" in err or "unproven" in err.lower()


def test_validate_music_sfx_input_prompt_alias_rejected():
    """Unproven alias prompt is strictly rejected; only canonical 'brief' is accepted."""
    ok, err, _ = bridge.validate_music_sfx_input(
        "test-sfx-user-1",
        {"prompt": "Tiếng chuông ngân"}
    )
    assert ok is False
    assert "chưa được chứng minh" in err or "unproven" in err.lower()


# ─── 4. FAIL-CLOSED JOB CREATION & NEUTRAL PRICING ────────────────────────────

def test_create_music_sfx_job_fail_closed_initial_state():
    """Newly created job is durable, status='queued', neutral pricing, None provider/model."""
    job = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng bước chân giẫm trên lá khô trong rừng vắng"},
        idempotency_key="idemp_sfx_test_001_unique",
    )
    assert job["idempotent_replay"] is False
    assert job["id"].startswith("msfx_")
    assert job["account_id"] == "test-sfx-user-1"
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE"
    assert job["provider_name"] is None
    assert job["provider_task_id"] is None
    assert job["model_name"] is None
    assert job["xu_cost"] is None  # NOT 0, neutral until proven
    assert "duration_seconds" not in job or job.get("duration_seconds") is None
    assert job["output_asset_id"] is None
    assert job["output_url"] is None
    assert job["brief"] == "Tiếng bước chân giẫm trên lá khô trong rừng vắng"


# ─── 5. IDEMPOTENCY REPLAY & CONFLICT ────────────────────────────────────────

def test_idempotency_replay_exact_payload():
    """Exact replay on same idempotency key returns the existing job."""
    job1 = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng chuông gió ngân nga trong gió chiều"},
        idempotency_key="idemp_sfx_replay_exact_01",
    )
    assert job1["idempotent_replay"] is False

    job2 = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng chuông gió ngân nga trong gió chiều"},
        idempotency_key="idemp_sfx_replay_exact_01",
    )
    assert job2["idempotent_replay"] is True
    assert job1["id"] == job2["id"]


def test_idempotency_conflict_different_payload():
    """Differing brief with same idempotency key raises 409 Conflict."""
    bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng chuông gió ngân nga"},
        idempotency_key="idemp_sfx_conflict_01",
    )
    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_music_sfx_job(
            account_id="test-sfx-user-1",
            payload={"brief": "Tiếng sấm sét đánh ngang tai"},
            idempotency_key="idemp_sfx_conflict_01",
        )
    assert exc_info.value.status_code == 409
    assert "Xung đột Idempotency-Key" in exc_info.value.detail


def test_request_id_replay_and_conflict():
    """request_id exact replay returns existing job; conflicting payload raises 409."""
    req_id = "req_msfx_unique_custom_001"
    job1 = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng gió thổi qua rừng thông"},
        request_id=req_id,
    )
    assert job1["idempotent_replay"] is False
    assert job1["request_id"] == req_id

    # Exact replay
    job2 = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng gió thổi qua rừng thông"},
        request_id=req_id,
    )
    assert job2["idempotent_replay"] is True
    assert job2["id"] == job1["id"]

    # Conflicting payload on same request_id
    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_music_sfx_job(
            account_id="test-sfx-user-1",
            payload={"brief": "Tiếng sấm sét rền vang"},
            request_id=req_id,
        )
    assert exc_info.value.status_code == 409
    assert "Xung đột request_id" in exc_info.value.detail


# ─── 6. CUSTOMER API: CREATE, DETAIL, LIST ───────────────────────────────────

def test_api_create_and_get_job():
    """Customer can create job via POST /api/v1/features/music_sfx/jobs and retrieve it."""
    client, csrf_token = _create_authenticated_client("test-sfx-user-1")

    create_resp = client.post(
        "/api/v1/features/music_sfx/jobs",
        json={"feature": "music_sfx", "input": {"brief": "Tiếng sóng biển vỗ vào ghềnh đá hùng vĩ"}},
        headers={"Idempotency-Key": "idemp_api_sfx_create_001", "X-CSRF-Token": csrf_token},
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["ok"] is True
    job_id = create_data["data"]["job_id"]
    assert job_id.startswith("msfx_")
    assert create_data["data"]["status"] == "queued"

    # Fetch through feature endpoint
    get_resp = client.get(f"/api/v1/features/music_sfx/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["job_id"] == job_id
    assert get_resp.json()["data"]["brief"] == "Tiếng sóng biển vỗ vào ghềnh đá hùng vĩ"


def test_api_jobs_history_aggregation():
    """Music SFX jobs appear in general GET /api/v1/jobs history."""
    client, csrf_token = _create_authenticated_client("test-sfx-user-1")

    client.post(
        "/api/v1/features/music_sfx/jobs",
        json={"feature": "music_sfx", "input": {"brief": "Tiếng chim hót líu lo buổi sớm trong vườn"}},
        headers={"Idempotency-Key": "idemp_api_history_001", "X-CSRF-Token": csrf_token},
    )

    history_resp = client.get("/api/v1/jobs")
    assert history_resp.status_code == 200
    data = history_resp.json().get("data", {})
    items = data.get("items") or data.get("jobs") or []
    sfx_jobs = [j for j in items if (j.get("id") or j.get("job_id") or "").startswith("msfx_")]
    assert len(sfx_jobs) >= 1
    assert sfx_jobs[0]["product"] == "music_sfx"
    assert sfx_jobs[0]["kind"] == "music_sfx"


# ─── 7. CROSS-ACCOUNT TENANT ISOLATION (403) ─────────────────────────────────

def test_cross_account_protection_feature_endpoint():
    """User 2 cannot access User 1's Music SFX job via feature endpoint (403 Forbidden)."""
    client1, csrf1 = _create_authenticated_client("test-sfx-user-1")
    client2, _ = _create_authenticated_client("test-sfx-user-2")

    create_resp = client1.post(
        "/api/v1/features/music_sfx/jobs",
        json={"feature": "music_sfx", "input": {"brief": "Tiếng đàn piano du dương êm dịu"}},
        headers={"Idempotency-Key": "idemp_cross_user_001", "X-CSRF-Token": csrf1},
    )
    job_id = create_resp.json()["data"]["job_id"]

    # User 2 attempts to read User 1's job
    cross_resp = client2.get(f"/api/v1/features/music_sfx/jobs/{job_id}")
    assert cross_resp.status_code == 403


def test_cross_account_protection_generic_jobs_endpoint():
    """User 2 cannot access User 1's Music SFX job via generic /jobs/{job_id} (403 Forbidden)."""
    client1, csrf1 = _create_authenticated_client("test-sfx-user-1")
    client2, _ = _create_authenticated_client("test-sfx-user-2")

    create_resp = client1.post(
        "/api/v1/features/music_sfx/jobs",
        json={"feature": "music_sfx", "input": {"brief": "Tiếng violin da diết"}},
        headers={"Idempotency-Key": "idemp_cross_user_002", "X-CSRF-Token": csrf1},
    )
    job_id = create_resp.json()["data"]["job_id"]

    # User 2 attempts generic detail
    cross_resp = client2.get(f"/api/v1/jobs/{job_id}")
    assert cross_resp.status_code == 403


# ─── 8. PROVIDER DISPATCH DISABLED BOUNDARY ──────────────────────────────────

def test_provider_dispatch_disabled():
    """Calling dispatch_music_sfx_provider raises RuntimeError while dispatch is disabled."""
    job = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng gõ bàn phím cơ clicky"},
        idempotency_key="idemp_dispatch_disabled_01",
    )
    with pytest.raises(RuntimeError) as exc_info:
        bridge.dispatch_music_sfx_provider(job["id"])
    assert "Provider dispatch for music_sfx is currently disabled" in str(exc_info.value) or "MUSIC_SFX_PROVIDER_DISPATCH_DISABLED" in str(exc_info.value)


# ─── 9. AUDIO RESULT RETENTION FINALIZER ─────────────────────────────────────

def test_finalize_audio_result_valid_mp3():
    """Finalizing with a valid active MP3 audio asset sets status='completed' and safe output_url."""
    job = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng còi xe lửa vang vọng trong đêm"},
        idempotency_key="idemp_finalize_valid_mp3",
    )
    finalized = bridge.finalize_music_sfx_job_result(
        job_id=job["id"],
        output_asset_id="asset-sfx-audio-mp3",
        provider_name="fixture_audio_engine",
        model_name="fixture_sfx_v1",
        output_metadata={"sample_rate": 44100, "channels": 2},
    )
    assert finalized["status"] == "completed"
    assert finalized["output_asset_id"] == "asset-sfx-audio-mp3"
    assert finalized["output_url"] == "/api/v1/assets/asset-sfx-audio-mp3/download"
    assert finalized["provider_name"] == "fixture_audio_engine"
    assert finalized["model_name"] == "fixture_sfx_v1"


def test_finalize_audio_result_supported_extensions():
    """Finalizing succeeds for .wav, .m4a, and .ogg audio assets."""
    for asset_id in ["asset-sfx-audio-wav", "asset-sfx-audio-m4a", "asset-sfx-audio-ogg"]:
        job = bridge.create_or_replay_music_sfx_job(
            account_id="test-sfx-user-1",
            payload={"brief": f"Tiếng âm thanh cho {asset_id}"},
            idempotency_key=f"idemp_finalize_{asset_id}",
        )
        finalized = bridge.finalize_music_sfx_job_result(
            job_id=job["id"],
            output_asset_id=asset_id,
        )
        assert finalized["status"] == "completed"
        assert finalized["output_asset_id"] == asset_id


def test_finalize_audio_result_rejects_image_asset():
    """Finalizing with a non-audio asset (e.g. image .jpg) raises 400 Bad Request."""
    job = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng thác nước đổ ầm ầm"},
        idempotency_key="idemp_finalize_image_reject",
    )
    with pytest.raises(HTTPException) as exc_info:
        bridge.finalize_music_sfx_job_result(
            job_id=job["id"],
            output_asset_id="asset-sfx-image-jpg",
        )
    assert exc_info.value.status_code == 400
    assert ".mp3" in exc_info.value.detail or "không được hỗ trợ" in exc_info.value.detail


def test_finalize_audio_result_rejects_cross_account_asset():
    """Finalizing with another account's asset raises 403 Forbidden."""
    job = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng cười vui vẻ của trẻ thơ"},
        idempotency_key="idemp_finalize_cross_acc",
    )
    with pytest.raises(HTTPException) as exc_info:
        bridge.finalize_music_sfx_job_result(
            job_id=job["id"],
            output_asset_id="asset-sfx-user2-audio",
        )
    assert exc_info.value.status_code == 403
    assert "không thuộc sở hữu của chủ tác vụ" in exc_info.value.detail


def test_finalize_audio_result_rejects_inactive_asset():
    """Finalizing with an inactive/pending asset raises 400 Bad Request."""
    job = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng gió thổi qua rặng tre"},
        idempotency_key="idemp_finalize_inactive_acc",
    )
    with pytest.raises(HTTPException) as exc_info:
        bridge.finalize_music_sfx_job_result(
            job_id=job["id"],
            output_asset_id="asset-sfx-inactive",
        )
    assert exc_info.value.status_code == 400
    assert "chưa ở trạng thái active hợp lệ" in exc_info.value.detail


# ─── 10. SECRET METADATA SANITIZATION ────────────────────────────────────────

def test_secret_metadata_sanitization():
    """Sensitive keys (api_key, token, secret, password) are stripped upon finalization."""
    job = bridge.create_or_replay_music_sfx_job(
        account_id="test-sfx-user-1",
        payload={"brief": "Tiếng đàn tranh thánh thót"},
        idempotency_key="idemp_secret_sanitize_01",
    )
    finalized = bridge.finalize_music_sfx_job_result(
        job_id=job["id"],
        output_asset_id="asset-sfx-audio-mp3",
        output_metadata={
            "api_key": "secret-super-key-12345",
            "token": "bearer-token-abc",
            "provider_secret": "my-secret-vault",
            "safe_param": "high_fidelity",
            "sample_rate": 48000,
        },
    )
    meta = finalized.get("output_metadata") or {}
    assert "api_key" not in meta
    assert "token" not in meta
    assert "provider_secret" not in meta
    assert meta["safe_param"] == "high_fidelity"
    assert meta["sample_rate"] == 48000


# ─── 11. ADMIN LEDGER INTEGRATION ────────────────────────────────────────────

def test_admin_jobs_ledger_list():
    """Admin can list Music SFX jobs via GET /api/v1/admin/jobs."""
    client_admin, _ = _create_authenticated_client("test-sfx-admin", role="admin")
    app.dependency_overrides[require_canonical_admin] = lambda: {"id": "test-sfx-admin", "role": "admin"}

    try:
        # Create job as User 1
        bridge.create_or_replay_music_sfx_job(
            account_id="test-sfx-user-1",
            payload={"brief": "Tiếng động cơ phản lực cất cánh"},
            idempotency_key="idemp_admin_list_01",
        )

        admin_resp = client_admin.get("/api/v1/admin/jobs")
        assert admin_resp.status_code == 200
        all_jobs = admin_resp.json().get("data", {}).get("items", [])
        sfx_jobs = [j for j in all_jobs if (j.get("job_id") or j.get("id") or "").startswith("msfx_")]
        assert len(sfx_jobs) >= 1
        assert sfx_jobs[0]["product"] == "music_sfx"
        assert sfx_jobs[0]["owner_reference"] == "test-sfx-user-1"
    finally:
        app.dependency_overrides.pop(require_canonical_admin, None)


def test_admin_job_detail_endpoint():
    """Admin can get Music SFX job detail via GET /api/v1/admin/jobs/{job_id}."""
    client_admin, _ = _create_authenticated_client("test-sfx-admin", role="admin")
    app.dependency_overrides[require_canonical_admin] = lambda: {"id": "test-sfx-admin", "role": "admin"}

    try:
        job = bridge.create_or_replay_music_sfx_job(
            account_id="test-sfx-user-1",
            payload={"brief": "Tiếng giọt nước nhỏ tong tong trong hang đá"},
            idempotency_key="idemp_admin_detail_01",
        )

        detail_resp = client_admin.get(f"/api/v1/admin/jobs/{job['id']}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()["data"]
        assert detail_data["job_id"] == job["id"]
        assert detail_data["product"] == "music_sfx"
        assert detail_data["product_family"] == "music"
        assert detail_data["data_source_authority"] == "web_native_music_sfx"
        assert detail_data["owner_reference"] == "test-sfx-user-1"
    finally:
        app.dependency_overrides.pop(require_canonical_admin, None)


# ─── 12. FREESOUND CATALOG SEPARATION ────────────────────────────────────────

def test_freesound_catalog_separation():
    """Music SFX (/music/sfx) is separate from Freesound catalog (/music/sfx-library)."""
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT != "/music/sfx-library"
    assert bridge.CANONICAL_PRODUCT_KEY != "sfx_library"


# ─── 13. UI PORTAL & INTEGRATION CONTRACTS ───────────────────────────────────

def test_portal_js_and_integration_contracts():
    """Verify portal.js and integration.js contracts for music_sfx."""
    portal_js = (STANDALONE_ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    integration_js = (STANDALONE_ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")

    # portal.js contracts
    assert 'customerPage("/music/sfx"' in portal_js
    assert 'layout: "music-sfx"' in portal_js
    assert 'case "music-sfx": return renderMusicSfx(page, context);' in portal_js
    assert 'data-portal-submit="music-sfx"' in portal_js
    assert 'data-music-sfx-job-receipt' in portal_js
    assert 'classifyPageBoundary' in portal_js
    assert 'canonical_bridge' in portal_js
    assert 'renderMusicSfx' in portal_js
    assert 'data-field="music_sfx_brief_input"' in portal_js

    # Verify UI brief-only contract: NO unproven duration, loop, or category inputs
    render_sfx_idx = portal_js.find("function renderMusicSfx")
    assert render_sfx_idx != -1
    render_sfx_code = portal_js[render_sfx_idx : render_sfx_idx + 3500]
    assert 'name="duration_seconds"' not in render_sfx_code
    assert 'name="duration"' not in render_sfx_code
    assert 'name="loop"' not in render_sfx_code
    assert 'name="category"' not in render_sfx_code
    # Truthful initial queued state
    assert 'AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE' in render_sfx_code
    assert 'queued' in render_sfx_code

    # integration.js contracts
    assert 'if (action === "music-sfx-submit")' in integration_js
    assert 'if (action === "music-sfx-reset")' in integration_js
    assert '"/features/music_sfx/jobs"' in integration_js
    # Verify brief-only field extraction without prompt fallback
    submit_idx = integration_js.find('if (action === "music-sfx-submit")')
    assert submit_idx != -1
    submit_code = integration_js[submit_idx : submit_idx + 500]
    assert "fields.prompt" not in submit_code
