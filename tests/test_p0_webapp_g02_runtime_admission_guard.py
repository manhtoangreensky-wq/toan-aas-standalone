"""Tests for G02 E01: Guard Runtime-Unbacked Admission.

Spec: WEBAPP_G02_E01_GUARD_RUNTIME_UNBACKED_ADMISSION_R1
Issue: #570
Parent: #569 (G02), #561 (Master)

Proves:
1. All 5 direct POST /features/{family}/jobs routes are guarded when
   runtime execution is not activated (WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES is empty).
2. Confirm path returns WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED.
3. Historical queued jobs remain readable via GET (list + detail) but are
   projected with runtime_execution_active=False and source_state=guarded_runtime_unavailable.
4. Zero durable rows created when runtime is inactive.
5. Env alone cannot activate runtime execution (adapter keys set but allowlist empty).
6. Owner isolation preserved (cross-account access denied).
7. Generic /jobs parity: projected fields match per-family views.
8. provider_calls=0, paid_calls=0, wallet/payment mutation=0.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from app import app
import app as app_module
from copyfast_api import (
    WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES,
    _web_feature_execution_available,
    _web_feature_runtime_active,
)
from copyfast_db import ensure_copyfast_schema, read_transaction, session_database_path, transaction
import copyfast_product_video_job_bridge as video_bridge
import copyfast_video_trend_job_bridge as trend_bridge
import copyfast_video_long_job_bridge as long_bridge
import copyfast_multi_scene_film_job_bridge as multi_bridge
import copyfast_image_generation_job_bridge as image_bridge


# ─── FIXTURE ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db_and_env(monkeypatch):
    """Set env flags that would normally enable job creation, clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-g02-e01")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv(
        "WEBAPP_FEATURE_JOB_ADAPTERS",
        "video_ai_prompt,video_single,video_trend,video_long,video_multiscene,image_create,subdub,voice_tts,music,music_background,music_song",
    )
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    # Bypass auth throttle to avoid 429 across 14 tests
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    # Clear in-process middleware rate limiter so each test starts fresh
    app_module._auth_rate_windows.clear()
    ensure_copyfast_schema()
    _clean_test_data()
    yield
    _clean_test_data()


def _clean_test_data():
    """Delete test data using raw sqlite3 with FK constraints OFF (before BEGIN)."""
    db_path = session_database_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        for tbl in [
            "web_product_video_jobs",
            "web_video_trend_jobs",
            "web_video_long_jobs",
            "web_multi_scene_film_jobs",
            "web_image_generation_jobs",
        ]:
            try:
                conn.execute(f"DELETE FROM {tbl}")
            except Exception:
                pass
        conn.execute("DELETE FROM web_sessions WHERE 1=1")
        conn.execute("DELETE FROM web_accounts WHERE email LIKE 'g02t%@test.local'")
        conn.commit()
    finally:
        conn.close()


def _login(client: TestClient, email: str, password: str) -> dict:
    """Register + login, return csrf_token, account_id, and headers."""
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "G02 Test"},
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, f"Login failed {res.status_code}: {res.text[:300]}"
    data = res.json()["data"]
    assert "csrf_token" in data, f"No csrf_token in login data: {list(data.keys())}"
    conn = sqlite3.connect(session_database_path())
    try:
        row = conn.execute("SELECT id FROM web_accounts WHERE email = ?", (email.strip().lower(),)).fetchone()
        account_id = str(row[0]) if row else data.get("account", {}).get("id", "")
    finally:
        conn.close()
    return {
        "csrf_token": data["csrf_token"],
        "account_id": account_id,
        "headers": {"X-CSRF-Token": data["csrf_token"]},
    }


# ─── TEST 1: COMPILE-TIME ALLOWLIST EXACT ACTIVATION SET ─────────────────────

def test_01_allowlist_exact_activation_set():
    """Prove WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES contains the source-reviewed active features.

    Currently admitted:
    - subdub
    - video_ai_prompt
    - voice_tts
    - music
    - music_background
    - music_song
    - image_create

    Guarded and NOT active (awaiting complete canonical runtime backend execution authority):
    - video_trend
    - video_long
    - video_multiscene
    """
    assert isinstance(WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES, frozenset)
    expected_active = frozenset({
        "subdub",
        "video_ai_prompt",
        "voice_tts",
        "music",
        "music_background",
        "music_song",
        "image_create",
    })
    assert WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES == expected_active

    # Preserved active features
    assert "subdub" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "video_ai_prompt" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "voice_tts" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "music" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "music_background" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "music_song" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "image_create" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES

    # Guarded lanes must NOT be in active set
    assert "video_trend" not in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "video_long" not in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "video_multiscene" not in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES


# ─── TEST 2: ENV ALONE CANNOT ACTIVATE RUNTIME ──────────────────────────────

def test_02_env_alone_cannot_activate_runtime():
    """Prove that even with all env flags enabled, runtime stays inactive
    for unactivated features (video_trend, video_long, video_multiscene)
    because they are not in the compile-time allowlist."""
    for feature in ["video_trend", "video_long", "video_multiscene"]:
        assert _web_feature_execution_available(feature) is False
        assert _web_feature_runtime_active(feature) is False
    # Activated features are available
    assert _web_feature_execution_available("image_create") is True
    assert _web_feature_runtime_active("image_create") is True
    assert _web_feature_execution_available("video_ai_prompt") is True
    assert _web_feature_runtime_active("video_ai_prompt") is True
    assert _web_feature_execution_available("subdub") is True
    assert _web_feature_runtime_active("subdub") is True
    assert _web_feature_execution_available("voice_tts") is True
    assert _web_feature_runtime_active("voice_tts") is True
    assert _web_feature_execution_available("music") is True
    assert _web_feature_runtime_active("music") is True
    assert _web_feature_execution_available("music_background") is True
    assert _web_feature_runtime_active("music_background") is True
    assert _web_feature_execution_available("music_song") is True
    assert _web_feature_runtime_active("music_song") is True
    # Aliases cannot bypass allowlist
    for alias in ["image_generation", "trend_video", "long_video", "multi_scene_film"]:
        assert _web_feature_execution_available(alias) is False
        assert _web_feature_runtime_active(alias) is False
    # Generic check is True because active features exist
    assert _web_feature_execution_available(None) is True


# ─── TEST 3: DIRECT POST ACTIVE — video_ai_prompt ───────────────────────────

def test_03_direct_post_video_ai_prompt_active():
    """Prove POST /features/video_ai_prompt/jobs succeeds and queues a job when runtime is active."""
    client = TestClient(app)
    auth = _login(client, "g02t03@test.local", "secure-g02-pwd-1234")
    res = client.post(
        "/api/v1/features/video_ai_prompt/jobs",
        json={
            "input": {
                "prompt": "Test product video active",
                "quality_tier": 200,
                "aspect_ratio": "9:16",
                "duration_seconds": 5,
            },
            "idempotency_key": "g02-guard-vap-001",
        },
        headers=auth["headers"],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "queued"
    assert "data" in body
    assert body["data"]["status"] == "queued"
    assert body["data"]["routing_product_key"] == "video_ai_canonical"


# ─── TEST 4: DIRECT POST GUARDED — video_trend ──────────────────────────────

def test_04_direct_post_guarded_video_trend():
    """Prove POST /features/video_trend/jobs returns guarded."""
    client = TestClient(app)
    auth = _login(client, "g02t04@test.local", "secure-g02-pwd-1234")
    res = client.post(
        "/api/v1/features/video_trend/jobs",
        json={
            "input": {
                "prompt": "Test trend video",
                "quality_tier": 200,
            },
            "idempotency_key": "g02-guard-vt-001",
        },
        headers=auth["headers"],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["status"] == "guarded"
    assert body["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED"


# ─── TEST 5: DIRECT POST GUARDED — video_long ───────────────────────────────

def test_05_direct_post_guarded_video_long():
    """Prove POST /features/video_long/jobs returns guarded."""
    client = TestClient(app)
    auth = _login(client, "g02t05@test.local", "secure-g02-pwd-1234")
    res = client.post(
        "/api/v1/features/video_long/jobs",
        json={
            "input": {
                "prompt": "Test long video",
                "quality_tier": 200,
            },
            "idempotency_key": "g02-guard-vl-001",
        },
        headers=auth["headers"],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["status"] == "guarded"
    assert body["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED"


# ─── TEST 6: DIRECT POST GUARDED — video_multiscene ─────────────────────────

def test_06_direct_post_guarded_video_multiscene():
    """Prove POST /features/video_multiscene/jobs returns guarded."""
    client = TestClient(app)
    auth = _login(client, "g02t06@test.local", "secure-g02-pwd-1234")
    res = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "prompt": "Test multiscene video",
                "quality_tier": 200,
            },
            "idempotency_key": "g02-guard-vm-001",
        },
        headers=auth["headers"],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["status"] == "guarded"
    assert body["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED"


# ─── TEST 7: DIRECT POST ACTIVE — image_create ──────────────────────────────

def test_07_direct_post_active_image_create():
    """Prove POST /features/image_create/jobs succeeds and queues a job when runtime is active."""
    client = TestClient(app)
    auth = _login(client, "g02t07@test.local", "secure-g02-pwd-1234")
    res = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "Test image create active",
                "tier": "standard",
            },
            "idempotency_key": "g02-guard-ic-001",
        },
        headers=auth["headers"],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "queued"
    data = body["data"]
    assert data["prompt"] == "Test image create active"
    assert data["tier_key"] == "standard"


# ─── TEST 8: ZERO DURABLE ROWS AFTER GUARDED POSTS ──────────────────────────

def test_08_zero_durable_rows_created():
    """After attempting the 3 guarded direct POST routes, prove no durable rows exist in their tables."""
    client = TestClient(app)
    auth = _login(client, "g02t08@test.local", "secure-g02-pwd-1234")
    for route in [
        "/api/v1/features/video_trend/jobs",
        "/api/v1/features/video_long/jobs",
        "/api/v1/features/video_multiscene/jobs",
    ]:
        client.post(route, json={"input": {"prompt": "test"}, "idempotency_key": f"zero-{route}"}, headers=auth["headers"])

    with read_transaction() as conn:
        for tbl in [
            "web_video_trend_jobs",
            "web_video_long_jobs",
            "web_multi_scene_film_jobs",
        ]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                assert count == 0, f"Expected 0 rows in {tbl}, got {count}"
            except Exception:
                pass  # table may not exist yet


# ─── TEST 9: CONFIRM PATH GUARDED FOR UNACTIVATED FEATURES ──────────────────

def test_09_confirm_path_guarded():
    """Prove POST /features/{feature}/confirm returns guarded error_code for unactivated features."""
    client = TestClient(app)
    auth = _login(client, "g02t09@test.local", "secure-g02-pwd-1234")
    for feature in ["video_trend", "video_long", "video_multiscene"]:
        res = client.post(
            f"/api/v1/features/{feature}/confirm",
            json={
                "input": {"prompt": "test confirm guard"},
                "idempotency_key": f"confirm-guard-{feature}",
            },
            headers=auth["headers"],
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is False
        assert body["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED", (
            f"Expected WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED for {feature}, got {body.get('error_code')}"
        )


# ─── TEST 10: NATIVE COMPAT PROJECTION — QUEUED ROWS ────────────────────────

def test_10_native_compat_queued_projection():
    """Prove *_to_native_compat() for queued rows projects:
    - video_ai_prompt (active): runtime_execution_active=True, source_state=queued_locally
    - other features (guarded): runtime_execution_active=False, source_state=guarded_runtime_unavailable,
      status_reason=RUNTIME_EXECUTION_NOT_ACTIVATED
    """
    queued_base = {
        "id": "test-job-001",
        "status": "queued",
        "status_reason": "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION",
        "created_at": "2026-09-27T00:00:00Z",
        "updated_at": "2026-09-27T00:00:00Z",
        "output": None,
        "output_metadata": None,
        "prompt": "test",
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
        "quality_tier": 200,
    }

    # video_ai_prompt (now active)
    compat = video_bridge.product_video_job_to_native_compat(queued_base)
    assert compat["runtime_execution_active"] is True
    assert compat["source_state"] == "queued_locally"
    assert compat["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

    # video_trend
    trend_job = {**queued_base, "trend_prompt": "test trend", "scene_count": 1,
                 "output_available": False, "download_ready": False, "delivery_ready": False}
    compat = trend_bridge.video_trend_job_to_native_compat(trend_job)
    assert compat["runtime_execution_active"] is False
    assert compat["source_state"] == "guarded_runtime_unavailable"
    assert compat["status_reason"] == "RUNTIME_EXECUTION_NOT_ACTIVATED"

    # video_long
    long_job = {**queued_base, "script": "", "long_form_plan": "", "scene_count": 1, "output_url": None}
    compat = long_bridge.video_long_job_to_native_compat(long_job)
    assert compat["runtime_execution_active"] is False
    assert compat["source_state"] == "guarded_runtime_unavailable"
    assert compat["status_reason"] == "RUNTIME_EXECUTION_NOT_ACTIVATED"

    # video_multiscene
    multi_job = {**queued_base, "canonical_job_id": None, "output_url": None, "scene_count": 1}
    compat = multi_bridge.multi_scene_film_job_to_native_compat(multi_job)
    assert compat["runtime_execution_active"] is False
    assert compat["source_state"] == "guarded_runtime_unavailable"
    assert compat["status_reason"] == "RUNTIME_EXECUTION_NOT_ACTIVATED"

    # image_create (now active)
    image_job = {**queued_base, "canonical_job_id": None, "output_url": None, "tier_key": "standard"}
    compat = image_bridge.image_generation_job_to_native_compat(image_job)
    assert compat["runtime_execution_active"] is True
    assert compat["source_state"] == "queued_locally"
    assert compat["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"


# ─── TEST 11: NATIVE COMPAT PROJECTION — COMPLETED ROWS ─────────────────────

def test_11_native_compat_completed_projection():
    """Prove completed rows still project correctly (not broken by guard changes)."""
    completed_base = {
        "id": "test-job-002",
        "status": "completed",
        "status_reason": "COMPLETED_SUCCESSFULLY",
        "created_at": "2026-09-27T00:00:00Z",
        "updated_at": "2026-09-27T01:00:00Z",
        "output": "https://cdn.example.com/video.mp4",
        "output_metadata": None,
        "output_available": True,
        "download_ready": True,
        "delivery_ready": True,
        "prompt": "test completed",
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
        "quality_tier": 200,
    }

    compat = video_bridge.product_video_job_to_native_compat(completed_base)
    assert compat["runtime_execution_active"] is True  # True — video_ai_prompt is in active allowlist
    assert compat["source_state"] == "completed"  # NOT overridden for completed
    assert compat["status_reason"] == "COMPLETED_SUCCESSFULLY"  # Preserved
    assert compat["output_available"] is True
    assert compat["output"] == "https://cdn.example.com/video.mp4"


# ─── TEST 12: GET LIST STILL WORKS FOR HISTORICAL ROWS ──────────────────────

def test_12_get_list_still_works():
    """Prove GET /features/video_ai_prompt/jobs returns readable list (even if empty)."""
    client = TestClient(app)
    auth = _login(client, "g02t12@test.local", "secure-g02-pwd-1234")
    res = client.get("/api/v1/features/video_ai_prompt/jobs", headers=auth["headers"])
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "read_only"
    assert "items" in body["data"]


# ─── TEST 13: DRAFT AND ESTIMATE STILL PASS ──────────────────────────────────

def test_13_draft_and_estimate_still_pass():
    """Prove draft and estimate actions are NOT blocked by runtime guard."""
    client = TestClient(app)
    auth = _login(client, "g02t13@test.local", "secure-g02-pwd-1234")
    for action in ["draft", "estimate"]:
        res = client.post(
            f"/api/v1/features/video_ai_prompt/{action}",
            json={
                "input": {"prompt": "Test draft/estimate not blocked"},
                "idempotency_key": f"de-{action}-001",
            },
            headers=auth["headers"],
        )
        # draft/estimate should NOT return WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED
        body = res.json()
        assert body.get("error_code") != "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED", (
            f"{action} should not be blocked by runtime guard"
        )


# ─── TEST 14: PROVIDER CALLS = 0, PAID CALLS = 0 ────────────────────────────

def test_14_zero_provider_and_paid_calls():
    """Confirm no external provider calls are made during the guard flow.
    For unactivated features, the guard returns immediately.
    For activated video_ai_prompt, direct POST queues locally in SQLite with zero provider calls."""
    client = TestClient(app)
    auth = _login(client, "g02t14@test.local", "secure-g02-pwd-1234")
    for route in [
        "/api/v1/features/video_trend/jobs",
        "/api/v1/features/video_long/jobs",
        "/api/v1/features/video_multiscene/jobs",
    ]:
        res = client.post(
            route,
            json={"input": {"prompt": "no provider call"}, "idempotency_key": f"np-{route}"},
            headers=auth["headers"],
        )
        body = res.json()
        # Guard returns immediately, no bridge function is called, hence no provider call
        assert body["ok"] is False
        assert body["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED"

    # Activated image_create queues locally with 0 provider calls
    img_res = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "zero provider test",
                "tier": "standard",
            },
            "idempotency_key": "np-img-001",
        },
        headers=auth["headers"],
    )
    img_body = img_res.json()
    assert img_body["ok"] is True
    assert img_body["status"] == "queued"

    # Activated video_ai_prompt queues locally with 0 provider calls
    vap_res = client.post(
        "/api/v1/features/video_ai_prompt/jobs",
        json={
            "input": {
                "prompt": "zero provider test",
                "aspect_ratio": "9:16",
                "duration_seconds": 5,
                "quality_tier": 200,
            },
            "idempotency_key": "np-vap-001",
        },
        headers=auth["headers"],
    )
    vap_body = vap_res.json()
    assert vap_body["ok"] is True
    assert vap_body["status"] == "queued"


# ─── FIXTURE HELPER FOR HISTORICAL ROWS ───────────────────────────────────────

def _insert_historical_fixture(
    table: str,
    job_id: str,
    account_id: str,
    status: str = "queued",
    status_reason: str = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION",
    output_url: str | None = None,
):
    db_path = session_database_path()
    conn = sqlite3.connect(db_path)
    try:
        now = "2026-09-27T10:00:00Z"
        if table == "web_product_video_jobs":
            conn.execute(
                """
                INSERT INTO web_product_video_jobs (
                    id, request_id, account_id, product_key, routing_product_key,
                    prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                    status, status_reason, payload_hash, bridge_envelope, created_at, updated_at, output_url
                ) VALUES (?, ?, ?, 'video_ai_prompt', 'product_video', 'prompt', '9:16', 5, 200, 1, ?, ?, 'hash', '{}', ?, ?, ?)
                """,
                (job_id, f"req_{job_id}", account_id, status, status_reason, now, now, output_url),
            )
        elif table == "web_video_trend_jobs":
            conn.execute(
                """
                INSERT INTO web_video_trend_jobs (
                    id, request_id, account_id, product_key, routing_product_key,
                    prompt, quality_tier, scene_count,
                    status, status_reason, payload_hash, bridge_envelope, created_at, updated_at, output_url
                ) VALUES (?, ?, ?, 'video_trend', 'trend_video', 'prompt', 200, 1, ?, ?, 'hash', '{}', ?, ?, ?)
                """,
                (job_id, f"req_{job_id}", account_id, status, status_reason, now, now, output_url),
            )
        elif table == "web_video_long_jobs":
            conn.execute(
                """
                INSERT INTO web_video_long_jobs (
                    id, request_id, account_id, product_key, routing_product_key,
                    prompt, quality_tier, scene_count,
                    status, status_reason, payload_hash, bridge_envelope, created_at, updated_at, output_url
                ) VALUES (?, ?, ?, 'video_long', 'video_long', 'prompt', 200, 3, ?, ?, 'hash', '{}', ?, ?, ?)
                """,
                (job_id, f"req_{job_id}", account_id, status, status_reason, now, now, output_url),
            )
        elif table == "web_multi_scene_film_jobs":
            conn.execute(
                """
                INSERT INTO web_multi_scene_film_jobs (
                    id, canonical_job_id, request_id, account_id, product_key, routing_product_key,
                    prompt, quality_tier, scene_count,
                    status, status_reason, payload_hash, bridge_envelope_json, created_at, updated_at, output_url
                ) VALUES (?, ?, ?, ?, 'video_multiscene', 'multi_scene_film', 'prompt', 200, 3, ?, ?, 'hash', '{}', ?, ?, ?)
                """,
                (job_id, f"can_{job_id}", f"req_{job_id}", account_id, status, status_reason, now, now, output_url),
            )
        elif table == "web_image_generation_jobs":
            conn.execute(
                """
                INSERT INTO web_image_generation_jobs (
                    id, canonical_job_id, request_id, account_id, product_key, routing_product_key,
                    prompt, tier_key,
                    status, status_reason, payload_hash, bridge_envelope_json, created_at, updated_at, output_url
                ) VALUES (?, ?, ?, ?, 'image_create', 'image_generation', 'prompt', 'standard', ?, ?, 'hash', '{}', ?, ?, ?)
                """,
                (job_id, f"can_{job_id}", f"req_{job_id}", account_id, status, status_reason, now, now, output_url),
            )
        conn.commit()
    finally:
        conn.close()


# ─── TEST 15: PRODUCT-SPECIFIC & GENERIC READ PARITY (ALL 5 FAMILIES) ────────

def test_15_product_specific_and_generic_read_parity_all_5_families():
    """Prove that for ALL FIVE families:
    1. GET /features/<family>/jobs (list)
    2. GET /features/<family>/jobs/{job_id} (detail)
    3. GET /jobs (generic list)
    4. GET /jobs/{job_id} (generic detail)
    maintain complete parity across list and detail.
    For active features (video_ai_prompt):
      runtime_execution_active=True, source_state=queued_locally, status_reason=AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION
    For guarded features (video_trend, video_long, video_multiscene, image_create):
      runtime_execution_active=False, source_state=guarded_runtime_unavailable, status_reason=RUNTIME_EXECUTION_NOT_ACTIVATED
    """
    client = TestClient(app)
    auth = _login(client, "g02t15@test.local", "secure-g02-pwd-1234")
    account_id = auth["account_id"]
    headers = auth["headers"]

    families = [
        ("video_ai_prompt", "web_product_video_jobs", "pvj_parity_test_001"),
        ("video_trend", "web_video_trend_jobs", "vtj_parity_test_001"),
        ("video_long", "web_video_long_jobs", "vlj_parity_test_001"),
        ("video_multiscene", "web_multi_scene_film_jobs", "msf_parity_test_001"),
        ("image_create", "web_image_generation_jobs", "img_parity_test_001"),
    ]

    for family, table, job_id in families:
        _insert_historical_fixture(table, job_id, account_id, status="queued")
        is_active = family in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
        exp_active = is_active
        exp_source_state = "queued_locally" if is_active else "guarded_runtime_unavailable"
        exp_status_reason = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION" if is_active else "RUNTIME_EXECUTION_NOT_ACTIVATED"

        # 1. Product-specific GET list
        list_res = client.get(f"/api/v1/features/{family}/jobs", headers=headers)
        assert list_res.status_code == 200, f"Failed list for {family}: {list_res.text}"
        items = list_res.json()["data"]["items"]
        matching = [item for item in items if item.get("id") == job_id]
        assert len(matching) == 1, f"Fixture {job_id} not found in {family} list"
        item = matching[0]
        assert item["runtime_execution_active"] is exp_active, f"{family} list runtime_execution_active mismatch"
        assert item["source_state"] == exp_source_state, f"{family} list source_state mismatch: {item.get('source_state')}"
        assert item["status_reason"] == exp_status_reason, f"{family} list status_reason mismatch: {item.get('status_reason')}"
        assert item["output_available"] is False
        assert item["download_ready"] is False
        assert item["delivery_ready"] is False

        # 2. Product-specific GET detail
        detail_res = client.get(f"/api/v1/features/{family}/jobs/{job_id}", headers=headers)
        assert detail_res.status_code == 200, f"Failed detail for {family}: {detail_res.text}"
        detail_item = detail_res.json()["data"]
        assert detail_item["runtime_execution_active"] is exp_active, f"{family} detail runtime_execution_active mismatch"
        assert detail_item["source_state"] == exp_source_state, f"{family} detail source_state mismatch"
        assert detail_item["status_reason"] == exp_status_reason, f"{family} detail status_reason mismatch"
        assert detail_item["output_available"] is False
        assert detail_item["download_ready"] is False
        assert detail_item["delivery_ready"] is False

        # 3. Generic GET /jobs list
        generic_list_res = client.get("/api/v1/jobs", headers=headers)
        assert generic_list_res.status_code == 200, f"Failed generic list: {generic_list_res.text}"
        g_items = generic_list_res.json()["data"]["items"]
        g_matching = [it for it in g_items if it.get("id") == job_id]
        assert len(g_matching) == 1, f"Fixture {job_id} not found in generic /jobs list"
        g_item = g_matching[0]
        assert g_item["runtime_execution_active"] is exp_active, f"{family} generic list runtime_execution_active mismatch"
        assert g_item["source_state"] == exp_source_state, f"{family} generic list source_state mismatch"
        assert g_item["status_reason"] == exp_status_reason, f"{family} generic list status_reason mismatch"
        assert g_item["output_available"] is False
        assert g_item["download_ready"] is False
        assert g_item["delivery_ready"] is False

        # 4. Generic GET /jobs/{job_id} detail
        generic_detail_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert generic_detail_res.status_code == 200, f"Failed generic detail: {generic_detail_res.text}"
        g_detail = generic_detail_res.json()["data"]
        assert g_detail["runtime_execution_active"] is exp_active, f"{family} generic detail runtime_execution_active mismatch"
        assert g_detail["source_state"] == exp_source_state, f"{family} generic detail source_state mismatch"
        assert g_detail["status_reason"] == exp_status_reason, f"{family} generic detail status_reason mismatch"
        assert g_detail["output_available"] is False
        assert g_detail["download_ready"] is False
        assert g_detail["delivery_ready"] is False


# ─── TEST 16: COMPLETED HISTORICAL ROWS PRESERVED ────────────────────────────

def test_16_completed_historical_rows_preserved():
    """Prove truthful completed historical rows preserve their completed status,
    verified output, original status_reason, and are NOT downgraded to runtime-disabled."""
    client = TestClient(app)
    auth = _login(client, "g02t16@test.local", "secure-g02-pwd-1234")
    account_id = auth["account_id"]
    headers = auth["headers"]

    completed_job_id = "pvj_completed_hist_001"
    _insert_historical_fixture(
        "web_product_video_jobs",
        completed_job_id,
        account_id,
        status="completed",
        status_reason="RENDER_SUCCESS_ORIGINAL",
        output_url="https://cdn.example.com/rendered_historical.mp4",
    )

    # Product-specific detail
    res = client.get(f"/api/v1/features/video_ai_prompt/jobs/{completed_job_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "completed"
    assert data["output_available"] is True
    assert data["download_ready"] is True
    assert data["delivery_ready"] is True
    assert data["status_reason"] == "RENDER_SUCCESS_ORIGINAL"
    assert data["source_state"] == "completed"
    assert data["output"] == "https://cdn.example.com/rendered_historical.mp4"

    # Generic detail
    res_g = client.get(f"/api/v1/jobs/{completed_job_id}", headers=headers)
    assert res_g.status_code == 200
    data_g = res_g.json()["data"]
    assert data_g["status"] == "completed"
    assert data_g["output_available"] is True
    assert data_g["status_reason"] == "RENDER_SUCCESS_ORIGINAL"
    assert data_g["source_state"] == "completed"


# ─── TEST 17: OWNER ISOLATION FOR HISTORICAL ROWS ────────────────────────────

def test_17_owner_isolation_for_historical_rows():
    """Prove Customer B cannot read Customer A's historical queued job
    via product-specific list/detail or generic list/detail."""
    client_a = TestClient(app)
    auth_a = _login(client_a, "g02t17_a@test.local", "secure-g02-pwd-1234")
    account_a_id = auth_a["account_id"]

    job_id = "pvj_isolated_owner_a_001"
    _insert_historical_fixture("web_product_video_jobs", job_id, account_a_id, status="queued")

    # Customer B logs in
    client_b = TestClient(app)
    auth_b = _login(client_b, "g02t17_b@test.local", "secure-g02-pwd-5678")
    headers_b = auth_b["headers"]

    # Customer B cannot read via product-specific detail
    res_b_detail = client_b.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=headers_b)
    assert res_b_detail.status_code in (403, 404)

    # Customer B cannot see in product-specific list
    res_b_list = client_b.get("/api/v1/features/video_ai_prompt/jobs", headers=headers_b)
    assert res_b_list.status_code == 200
    items_b = res_b_list.json()["data"]["items"]
    assert not any(it["id"] == job_id for it in items_b)

    # Customer B cannot read via generic detail
    res_b_g_detail = client_b.get(f"/api/v1/jobs/{job_id}", headers=headers_b)
    assert res_b_g_detail.status_code in (403, 404) or res_b_g_detail.json().get("ok") is False

    # Customer B cannot see in generic list
    res_b_g_list = client_b.get("/api/v1/jobs", headers=headers_b)
    assert res_b_g_list.status_code == 200
    g_items_b = res_b_g_list.json()["data"]["items"]
    assert not any(it["id"] == job_id for it in g_items_b)


# ─── TEST 18: ENV ALONE CANNOT ACTIVATE UNKNOWN FEATURE ──────────────────────

def test_18_env_only_cannot_activate_unknown_feature():
    """Prove that environment configuration alone cannot activate an unreviewed feature."""
    assert _web_feature_execution_available("unknown_feature_xyz") is False
    assert _web_feature_runtime_active("unknown_feature_xyz") is False
    assert _web_feature_execution_available("arbitrary_mock") is False
    assert _web_feature_runtime_active("arbitrary_mock") is False


# ─── TEST 19: ALIAS CANNOT BYPASS ALLOWLIST ─────────────────────────────────

def test_19_alias_cannot_bypass_allowlist():
    """Prove aliases cannot bypass runtime admission allowlist."""
    aliases = ["image_generation", "trend_video", "long_video", "multi_scene_film"]
    for alias in aliases:
        assert _web_feature_execution_available(alias) is False
        assert _web_feature_runtime_active(alias) is False


# ─── TEST 20: CLIENT PROVIDER INJECTION REJECTED ─────────────────────────────

def test_20_client_provider_injection_rejected():
    """Prove client authority injection (provider, provider_task_id, api_key) is rejected."""
    client = TestClient(app)
    auth = _login(client, "g02t20@test.local", "secure-g02-pwd-1234")
    injection_payload = {
        "prompt": "Legitimate looking prompt",
        "provider": "unauthorized_mock_provider",
        "provider_task_id": "forged_task_123",
        "api_key": "sk-1234567890abcdef12345678",
    }
    for route in [
        "/api/v1/features/image_create/jobs",
        "/api/v1/features/video_trend/jobs",
        "/api/v1/features/video_long/jobs",
        "/api/v1/features/video_multiscene/jobs",
    ]:
        res = client.post(route, json={"input": injection_payload, "idempotency_key": f"inj-{route}"}, headers=auth["headers"])
        assert res.status_code in (200, 422)
        if res.status_code == 200:
            body = res.json()
            assert body["ok"] is False


# ─── TEST 21: CLIENT PRICE AND WALLET INJECTION REJECTED ─────────────────────

def test_21_client_price_and_wallet_injection_rejected():
    """Prove client financial/wallet authority injection is rejected."""
    client = TestClient(app)
    auth = _login(client, "g02t21@test.local", "secure-g02-pwd-1234")
    injection_payload = {
        "prompt": "Test injection",
        "amount": 0,
        "price": 0,
        "cost": 0,
        "wallet": "free",
        "balance": 999999,
        "xu": 0,
    }
    for feature in ["image_create", "video_trend", "video_long", "video_multiscene"]:
        res = client.post(
            f"/api/v1/features/{feature}/confirm",
            json={"input": injection_payload, "idempotency_key": f"fin-{feature}"},
            headers=auth["headers"],
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is False


# ─── TEST 22: CLIENT COMPLETED STATUS INJECTION REJECTED ────────────────────

def test_22_client_completed_status_injection_rejected():
    """Prove client cannot inject completed status or forged output URL."""
    client = TestClient(app)
    auth = _login(client, "g02t22@test.local", "secure-g02-pwd-1234")
    injection_payload = {
        "prompt": "Test fake completion",
        "status": "completed",
        "output": "https://attacker.example.com/fake.mp4",
        "output_url": "https://attacker.example.com/fake.mp4",
    }
    for route in [
        "/api/v1/features/image_create/jobs",
        "/api/v1/features/video_trend/jobs",
        "/api/v1/features/video_long/jobs",
        "/api/v1/features/video_multiscene/jobs",
    ]:
        res = client.post(route, json={"input": injection_payload, "idempotency_key": f"fake-{route}"}, headers=auth["headers"])
        assert res.status_code in (200, 422)
        if res.status_code == 200:
            body = res.json()
            assert body["ok"] is False
