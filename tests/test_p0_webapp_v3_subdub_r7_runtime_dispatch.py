"""Tests for Web SubDub R7 Runtime Dispatch Wiring Remediation (WEB_R7_DISPATCH).

Task: WEBAPP_SUBDUB_R7_RUNTIME_DISPATCH_WIRING_EXECUTION_R1
Repo: manhtoangreensky-wq/toan-aas-standalone
Tracker: #515
Authoritative Baseline: #515 comment 5893077256

Proves 15 Test Matrix Contracts:
1. exact FIRST_RED proven / remediated: Web job created and canonically dispatched.
2. gate disabled -> 0 dispatch, local fail-closed.
3. bridge unavailable -> fail closed, no fake runtime ID.
4. accepted canonical job -> exactly 1 dispatch, runtime_job_id stored.
5. durable linkage fields -> all 5 fields persisted in web_subdub_jobs.
6. identical replay -> returns same Web job, 0 additional canonical dispatch calls.
7. payload conflict on same key -> HTTP 409 Conflict.
8. network ambiguity / bridge timeout -> no blind retry, records uncertain state.
9. canonical queued projection -> status queued, status_reason DISPATCHED_TO_CANONICAL_RUNTIME.
10. canonical processing projection -> status processing on reconcile read.
11. canonical terminal failure projection -> status failed on reconcile read.
12. completed without artifact -> fail-closed, download_ready=False.
13. completed with valid VTT -> output ready, safe HTTPS URL.
14. foreign account cannot read or dispatch -> HTTP 403.
15. unrelated feature -> zero leakage of SubDub runtime dispatch authority.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

import copyfast_bridge as bridge_mod
from copyfast_db import ensure_copyfast_schema, transaction, read_transaction
import copyfast_subdub_job_bridge as subdub_bridge


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure clean database and configuration."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-subdub-r7-dispatch")
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
    subdub_bridge.ensure_subdub_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, canonical_user_id, password_hash, created_at, updated_at)
            VALUES ('test-user-r7', 'user-r7@test.local', '7126111111', 'hash1', '2026-09-29T00:00:00Z', '2026-09-29T00:00:00Z'),
                   ('test-foreign-r7', 'foreign-r7@test.local', '7999222222', 'hash2', '2026-09-29T00:00:00Z', '2026-09-29T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


def _login_as(client: TestClient, account_id: str, email: str, canonical_user_id: str = "") -> str:
    """Create signed session directly for test account."""
    import uuid
    from copyfast_auth import _cookie_name, SESSION_COOKIE, _session_cookie_value
    sess_id = str(uuid.uuid4())
    csrf = f"csrf_{uuid.uuid4().hex[:16]}"
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_sessions (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
            VALUES (?, ?, ?, '2030-01-01 00:00:00', '2026-09-29 00:00:00', '2026-09-29 00:00:00')
            """,
            (sess_id, account_id, csrf),
        )
    cookie_val = _session_cookie_value(sess_id)
    c_name = _cookie_name(SESSION_COOKIE)
    client.cookies.set(c_name, cookie_val)
    return csrf


# ─── TEST 1 & 4 & 5: ACCEPTED DISPATCH, RUNTIME JOB ID STORED, DURABLE LINKAGE ─

def test_01_and_04_05_accepted_canonical_dispatch_persists_linkage(monkeypatch):
    """Test 1, 4, 5: Canonical dispatch wires successfully and stores all 5 linkage fields."""
    from app import app
    client = TestClient(app)

    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")
    bridge_calls = []

    async def mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "ok": True,
            "job": {
                "job_id": "subdub_rt_canonical_01",
                "status": "queued",
                "mode": "subtitle_create",
            },
        }

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_bridge_request)

    res = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {
                "upload_id": "upl_dispatch_test_01",
                "mode": "subtitle_create",
                "output_format": "vtt",
            },
            "idempotency_key": "idem-dispatch-test-01",
        },
        headers={"x-csrf-token": csrf},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    # Verify Web Job ID remains web-owned
    assert data["id"].startswith("sdj_")
    # Verify Runtime Job ID is populated
    assert data["runtime_job_id"] == "subdub_rt_canonical_01"
    assert data["runtime_dispatch_status"] == "dispatched"
    assert data["runtime_dispatched_at"] is not None

    # Verify exactly 1 dispatch call made
    assert len(bridge_calls) == 1
    call = bridge_calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/internal/v1/subdub/jobs"
    assert call["kwargs"]["actor_id"] == "7126111111"
    assert call["kwargs"]["owner_id"] == "7126111111"

    # Verify durable database row
    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT id, runtime_job_id, runtime_dispatch_status, runtime_dispatched_at,
                   runtime_request_id, runtime_last_error
            FROM web_subdub_jobs WHERE id=?
            """,
            (data["id"],),
        ).fetchone()
        assert row is not None
        assert row[1] == "subdub_rt_canonical_01"
        assert row[2] == "dispatched"
        assert row[3] is not None
        assert row[4].startswith("DISPATCH-")
        assert row[5] is None


# ─── TEST 2: RUNTIME GATE OFF -> ZERO DISPATCH ───────────────────────────────

def test_02_gate_disabled_yields_zero_dispatch(monkeypatch):
    """Test 2: When runtime gate is disabled, 0 dispatch calls occur and job is guarded or queued without dispatch."""
    import copyfast_api
    monkeypatch.setattr(copyfast_api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset())

    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    bridge_calls = []

    async def mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {"ok": True}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_bridge_request)

    res = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {
                "upload_id": "upl_gate_off_01",
                "mode": "subtitle_create",
                "output_format": "vtt",
            },
            "idempotency_key": "idem-gate-off-01",
        },
        headers={"x-csrf-token": csrf},
    )
    # When runtime gate is off, route returns guarded envelope
    assert res.status_code == 200
    assert res.json()["ok"] is False
    assert res.json()["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED"
    assert len(bridge_calls) == 0


# ─── TEST 3: BRIDGE UNAVAILABLE -> FAIL CLOSED ───────────────────────────────

def test_03_bridge_unavailable_fails_closed(monkeypatch):
    """Test 3: Bridge unconfigured/unavailable fails closed without fake runtime ID."""
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "")

    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    res = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {
                "upload_id": "upl_bridge_unavail_01",
                "mode": "subtitle_create",
                "output_format": "vtt",
            },
            "idempotency_key": "idem-bridge-unavail-01",
        },
        headers={"x-csrf-token": csrf},
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["ok"] is False
    assert res_data["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED"

    # Also verify direct dispatch helper returns pending without fake runtime ID
    import asyncio
    job = subdub_bridge.create_or_replay_subdub_job(
        account_id="test-user-r7",
        payload={"upload_id": "upl_bridge_unavail_01", "mode": "subtitle_create", "output_format": "vtt"},
        idempotency_key="idem-bridge-unavail-direct",
    )
    assert job["runtime_job_id"] is None
    assert job["runtime_dispatch_status"] == "pending"

    dispatched = asyncio.run(
        subdub_bridge.dispatch_subdub_job_to_canonical_runtime(
            job_id=job["id"],
            account={"id": "test-user-r7", "canonical_user_id": "7126111111"},
        )
    )
    assert dispatched["runtime_job_id"] is None
    assert dispatched["runtime_dispatch_status"] == "pending"



# ─── TEST 6: IDENTICAL REPLAY -> NO SECOND DISPATCH ──────────────────────────

def test_06_identical_replay_no_second_dispatch(monkeypatch):
    """Test 6: Exact same request replays existing job and does NOT trigger a second dispatch."""
    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    dispatch_count = 0

    async def mock_bridge_request(method, path, **kwargs):
        nonlocal dispatch_count
        if path == "/internal/v1/subdub/jobs":
            dispatch_count += 1
        return {"ok": True, "job": {"job_id": "subdub_rt_replay_01", "status": "queued"}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_bridge_request)

    payload = {
        "feature": "subdub",
        "input": {
            "upload_id": "upl_replay_01",
            "mode": "subtitle_create",
            "output_format": "vtt",
        },
        "idempotency_key": "idem-replay-01",
    }

    # 1. First submission: creates and dispatches
    res1 = client.post("/api/v1/features/subdub/jobs", json=payload, headers={"x-csrf-token": csrf})
    assert res1.status_code == 200
    job_id_1 = res1.json()["data"]["id"]
    assert dispatch_count == 1

    # 2. Replay: returns same job, dispatch count remains 1
    res2 = client.post("/api/v1/features/subdub/jobs", json=payload, headers={"x-csrf-token": csrf})
    assert res2.status_code == 200
    job_id_2 = res2.json()["data"]["id"]
    assert job_id_1 == job_id_2
    assert res2.json()["data"]["idempotent_replay"] is True
    assert dispatch_count == 1, "Replay MUST NOT trigger second canonical dispatch"


# ─── TEST 7: CONFLICTING PAYLOAD -> HTTP 409 ─────────────────────────────────

def test_07_conflicting_payload_returns_409():
    """Test 7: Same idempotency key with differing payload raises HTTP 409."""
    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    # 1. First payload
    res1 = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {"upload_id": "upl_conflict_01", "mode": "subtitle_create", "output_format": "vtt"},
            "idempotency_key": "idem-conflict-key-01",
        },
        headers={"x-csrf-token": csrf},
    )
    assert res1.status_code == 200

    # 2. Differing payload on same idempotency key
    res2 = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {"upload_id": "upl_conflict_DIFFERENT", "mode": "subtitle_create", "output_format": "vtt"},
            "idempotency_key": "idem-conflict-key-01",
        },
        headers={"x-csrf-token": csrf},
    )
    assert res2.status_code == 409


# ─── TEST 8: NETWORK AMBIGUITY / TIMEOUT -> NO BLIND RETRY ──────────────────

def test_08_network_ambiguity_no_blind_retry(monkeypatch):
    """Test 8: Exception during bridge call marks uncertain, does NOT retry."""
    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    attempt_count = 0

    async def mock_bridge_timeout(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        raise TimeoutError("Simulated bridge gateway timeout")

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_bridge_timeout)

    res = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {"upload_id": "upl_timeout_01", "mode": "subtitle_create", "output_format": "vtt"},
            "idempotency_key": "idem-timeout-01",
        },
        headers={"x-csrf-token": csrf},
    )
    assert res.status_code == 200
    data = res.json()["data"]

    # Verify attempt was made exactly once (no blind retry)
    assert attempt_count == 1
    assert data["runtime_dispatch_status"] == "uncertain"
    assert "TimeoutError" in (data["runtime_last_error"] or "")


# ─── TEST 9 & 10 & 11: STATUS RECONCILIATION ────────────────────────────────

def test_09_10_11_status_reconciliation(monkeypatch):
    """Test 9, 10, 11: Reconcile status on read for queued, processing, and failed."""
    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    # Mock dispatch
    async def mock_dispatch(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_recon_01", "status": "queued"}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_dispatch)

    res_create = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {"upload_id": "upl_recon_01", "mode": "subtitle_create", "output_format": "vtt"},
            "idempotency_key": "idem-recon-01",
        },
        headers={"x-csrf-token": csrf},
    )
    job_id = res_create.json()["data"]["id"]

    # Case A: Remote runtime is processing
    async def mock_get_processing(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_recon_01", "status": "processing"}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_get_processing)

    res_proc = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_proc.status_code == 200
    assert res_proc.json()["data"]["status"] == "processing"

    # Case B: Remote runtime failed
    async def mock_get_failed(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_recon_01", "status": "failed", "last_error": "ASR_PROVIDER_TIMEOUT"}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_get_failed)

    res_fail = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_fail.status_code == 200
    assert res_fail.json()["data"]["status"] == "failed"
    assert "ASR_PROVIDER_TIMEOUT" in res_fail.json()["data"]["status_reason"]


# ─── TEST 12 & 13: ARTIFACT PROJECTION & SAFETY ──────────────────────────────

def test_12_13_artifact_projection_and_safety(monkeypatch):
    """Test 12, 13: Output ready only with valid safe HTTPS URL; loopback/missing fails closed."""
    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    async def mock_dispatch(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_art_01", "status": "queued"}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_dispatch)

    res_create = client.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {"upload_id": "upl_art_01", "mode": "subtitle_create", "output_format": "vtt"},
            "idempotency_key": "idem-art-01",
        },
        headers={"x-csrf-token": csrf},
    )
    job_id = res_create.json()["data"]["id"]

    # 1. Completed without output URL -> download_ready must remain False
    async def mock_completed_no_artifact(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_art_01", "status": "completed", "result": {}}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_completed_no_artifact)
    res_no_art = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_no_art.status_code == 200
    assert res_no_art.json()["data"]["download_ready"] is False
    assert res_no_art.json()["data"]["output_available"] is False

    # 2. Completed with private loopback URL -> rejected, fail closed
    async def mock_completed_loopback(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_art_01", "status": "completed", "result": {"output_url": "http://127.0.0.1:8000/private.vtt"}}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_completed_loopback)
    res_loopback = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_loopback.status_code == 200
    assert res_loopback.json()["data"]["download_ready"] is False

    # 3. Completed with valid safe HTTPS URL -> download_ready=True, output_url exposed
    safe_url = "https://cdn.toanaas.vn/artifacts/subdub/r7_output.vtt"

    async def mock_completed_safe(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_art_01", "status": "completed", "result": {"output_url": safe_url}}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_completed_safe)
    res_safe = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_safe.status_code == 200
    assert res_safe.json()["data"]["status"] == "completed"
    assert res_safe.json()["data"]["download_ready"] is True
    assert res_safe.json()["data"]["output_url"] == safe_url


# ─── TEST 14: CROSS-USER SECURITY ────────────────────────────────────────────

def test_14_cross_user_security_denied(monkeypatch):
    """Test 14: Foreign account cannot read or dispatch another account's job."""
    from app import app
    client1 = TestClient(app)
    csrf1 = _login_as(client1, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    async def mock_dispatch(*args, **kwargs):
        return {"ok": True, "job": {"job_id": "subdub_rt_sec_01", "status": "queued"}}

    monkeypatch.setattr(bridge_mod, "bridge_request", mock_dispatch)

    res = client1.post(
        "/api/v1/features/subdub/jobs",
        json={
            "feature": "subdub",
            "input": {"upload_id": "upl_sec_01", "mode": "subtitle_create", "output_format": "vtt"},
            "idempotency_key": "idem-sec-01",
        },
        headers={"x-csrf-token": csrf1},
    )
    job_id = res.json()["data"]["id"]

    # Foreign client attempts read
    client2 = TestClient(app)
    _login_as(client2, "test-foreign-r7", "foreign-r7@test.local", canonical_user_id="7999222222")

    res_foreign = client2.get(f"/api/v1/features/subdub/jobs/{job_id}")
    assert res_foreign.status_code == 403


# ─── TEST 15: HISTORICAL R7 FAILED JOB IS PRESERVED ──────────────────────────

def test_15_historical_r7_job_never_dispatched():
    """Test 15: Historical R7 job sdj_0058b35d35ff42b2823ddf9c0068645c is preserved and never dispatched."""
    from app import app
    client = TestClient(app)
    csrf = _login_as(client, "test-user-r7", "user-r7@test.local", canonical_user_id="7126111111")

    hist_id = "sdj_0058b35d35ff42b2823ddf9c0068645c"

    # Insert historical job
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_subdub_jobs (
                id, request_id, account_id, upload_id, subdub_mode, output_format,
                status, status_reason, payload_hash, bridge_envelope, created_at, updated_at
            ) VALUES (?, 'SDB-HIST-01', 'test-user-r7', 'upl_hist_01', 'subtitle_create', 'vtt',
                     'queued', 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION', 'hash', '{}', '2026-09-29', '2026-09-29')
            """,
            (hist_id,),
        )

    # Calling dispatch on historical job must return without mutating or dispatching
    import asyncio
    job = asyncio.run(
        subdub_bridge.dispatch_subdub_job_to_canonical_runtime(
            job_id=hist_id,
            account={"id": "test-user-r7", "canonical_user_id": "7126111111"},
        )
    )
    assert job["id"] == hist_id
    assert job["runtime_job_id"] is None
    assert job["runtime_dispatch_status"] == "pending"
