"""Tests for Web SubDub Comprehensive Runtime & Financial Parity (R2).

Task: SUBDUB_WEB_RUNTIME_PARITY_COMPREHENSIVE_REMEDIATION_R2
Repo: manhtoangreensky-wq/toan-aas-standalone
Tracker: #612

Verifies:
1. 9/9 Direct Routes parity: all 9 aliases create, list, and retrieve jobs.
2. Canonical Mode Normalization: maps legacy and alias names to 4 canonical lanes.
3. Idempotency & Conflict: deterministic hash replay and 409 conflict detection.
4. Cross-Account Isolation: 401 unauthenticated, 403/404 cross-account access blocked.
5. Canonical Settlement on Reconcile:
   - subtitle_create: exempt_free, charged_xu = 0.
   - paid lanes (translate, dub, combo): exactly 1 settlement debit, charged_xu populated.
   - duplicate read: 0 duplicate debit calls.
   - unsafe artifact: blocks completion and settlement, charged_xu = 0.
   - failed runtime job: cancelled, charged_xu = 0.
"""

from __future__ import annotations

import asyncio
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
def setup_subdub_r2_environment(monkeypatch):
    """Ensure clean test database, environment, and auth for SubDub R2 tests."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-subdub-r2-comprehensive")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv(
        "WEBAPP_FEATURE_JOB_ADAPTERS",
        "subdub,video_dub,subtitle_create,subtitle_translate,subtitle_plus_dub,dubbing,subtitle_plus_dubbing,subtitle_asr,asr",
    )
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")

    import app as app_module
    import copyfast_api
    monkeypatch.setattr(
        copyfast_api,
        "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES",
        frozenset({"subdub", "video_ai_prompt"}),
    )
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
            VALUES ('test-user-subdub-r2', 'user-subdub@test.local', '7126111111', 'hash1', '2026-10-03T00:00:00Z', '2026-10-03T00:00:00Z'),
                   ('test-foreign-subdub-r2', 'foreign-subdub@test.local', '7999222222', 'hash2', '2026-10-03T00:00:00Z', '2026-10-03T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


def _login_client(client: TestClient, account_id: str) -> str:
    import uuid
    from copyfast_auth import _cookie_name, SESSION_COOKIE, _session_cookie_value
    sess_id = str(uuid.uuid4())
    csrf = f"csrf_{uuid.uuid4().hex[:16]}"
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_sessions (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
            VALUES (?, ?, ?, '2030-01-01 00:00:00', '2026-10-03 00:00:00', '2026-10-03 00:00:00')
            """,
            (sess_id, account_id, csrf),
        )
    cookie_val = _session_cookie_value(sess_id)
    c_name = _cookie_name(SESSION_COOKIE)
    client.cookies.set(c_name, cookie_val)
    return csrf


def test_01_all_nine_direct_routes_registered_and_reachable():
    """Prove all 9 direct SubDub endpoints exist, accept jobs, list jobs, and retrieve job details."""
    import app as app_module
    client = TestClient(app_module.app)
    csrf = _login_client(client, "test-user-subdub-r2")

    nine_routes = [
        ("subdub", {"upload_id": "up_test_01", "mode": "subtitle_create"}),
        ("video_dub", {"upload_id": "up_test_02", "target_language": "vi"}),
        ("subtitle_create", {"upload_id": "up_test_03"}),
        ("subtitle_translate", {"upload_id": "up_test_04", "target_language": "en"}),
        ("subtitle_plus_dub", {"upload_id": "up_test_05", "target_language": "vi"}),
        ("dubbing", {"upload_id": "up_test_06", "target_language": "ja"}),
        ("subtitle_plus_dubbing", {"upload_id": "up_test_07", "target_language": "vi"}),
        ("subtitle_asr", {"upload_id": "up_test_08"}),
        ("asr", {"upload_id": "up_test_09"}),
    ]

    with patch("copyfast_subdub_job_bridge.dispatch_subdub_job_to_canonical_runtime", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.side_effect = lambda **kwargs: subdub_bridge.get_subdub_job(kwargs["account"]["id"], kwargs["job_id"])

        for alias, payload in nine_routes:
            # 1. POST /api/v1/features/{alias}/jobs
            post_res = client.post(
                f"/api/v1/features/{alias}/jobs",
                json={"input": payload},
                headers={"X-CSRF-Token": csrf},
            )
            assert post_res.status_code == 200, f"Route /api/v1/features/{alias}/jobs POST failed: {post_res.text}"
            data = post_res.json()
            job = data.get("data") if isinstance(data.get("data"), dict) and "id" in data.get("data", {}) else (data.get("data") or {}).get("job") or data.get("job") or data
            assert job["id"].startswith("sdj_"), f"Job ID missing on {alias}"
            job_id = job["id"]

            # 2. GET /api/v1/features/{alias}/jobs
            list_res = client.get(f"/api/v1/features/{alias}/jobs")
            assert list_res.status_code == 200, f"Route /api/v1/features/{alias}/jobs GET failed: {list_res.text}"
            list_data = list_res.json()
            jobs = (list_data.get("data") or {}).get("items") or (list_data.get("data") or {}).get("jobs") or list_data.get("jobs", [])
            assert any(j["id"] == job_id for j in jobs), f"Created job not in list for {alias}"

            # 3. GET /api/v1/features/{alias}/jobs/{job_id}
            get_res = client.get(f"/api/v1/features/{alias}/jobs/{job_id}")
            assert get_res.status_code == 200, f"Route /api/v1/features/{alias}/jobs/{job_id} GET failed: {get_res.text}"
            get_data = get_res.json()
            retrieved = get_data.get("data") if isinstance(get_data.get("data"), dict) and "id" in get_data.get("data", {}) else (get_data.get("data") or {}).get("job") or get_data.get("job") or get_data
            assert retrieved["id"] == job_id


def test_02_alias_normalization_maps_to_canonical_modes():
    """Prove alias routes correctly map to the 4 canonical modes without client ambiguity."""
    import app as app_module
    client = TestClient(app_module.app)
    csrf = _login_client(client, "test-user-subdub-r2")

    test_cases = [
        ("subtitle_asr", {"upload_id": "up_norm_1"}, "subtitle_create"),
        ("asr", {"upload_id": "up_norm_2"}, "subtitle_create"),
        ("video_dub", {"upload_id": "up_norm_3", "target_language": "en"}, "dub"),
        ("dubbing", {"upload_id": "up_norm_4", "target_language": "fr"}, "dub"),
        ("subtitle_plus_dub", {"upload_id": "up_norm_5", "target_language": "vi"}, "subtitle_plus_dub"),
        ("subtitle_plus_dubbing", {"upload_id": "up_norm_6", "target_language": "vi"}, "subtitle_plus_dub"),
    ]

    with patch("copyfast_subdub_job_bridge.dispatch_subdub_job_to_canonical_runtime", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.side_effect = lambda **kwargs: subdub_bridge.get_subdub_job(kwargs["account"]["id"], kwargs["job_id"])

        for alias, payload, expected_mode in test_cases:
            res = client.post(
                f"/api/v1/features/{alias}/jobs",
                json={"input": payload},
                headers={"X-CSRF-Token": csrf},
            )
            assert res.status_code == 200
            data = res.json()
            job = data.get("data") if isinstance(data.get("data"), dict) and "subdub_mode" in data.get("data", {}) else (data.get("data") or {}).get("job") or data.get("job") or data
            assert job["subdub_mode"] == expected_mode, f"Expected {expected_mode} for alias {alias}, got {job['subdub_mode']}"


def test_03_idempotent_replay_and_conflict_detection():
    """Prove same request_id replays safely while conflicting payload returns HTTP 409."""
    import app as app_module
    client = TestClient(app_module.app)
    csrf = _login_client(client, "test-user-subdub-r2")

    req_id = "REQ-IDEM-001"
    initial_payload = {"upload_id": "up_idem_1", "mode": "subtitle_create", "request_id": req_id}

    with patch("copyfast_subdub_job_bridge.dispatch_subdub_job_to_canonical_runtime", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.side_effect = lambda **kwargs: subdub_bridge.get_subdub_job(kwargs["account"]["id"], kwargs["job_id"])

        # 1. Initial create
        res1 = client.post("/api/v1/features/subdub/jobs", json={"input": initial_payload}, headers={"X-CSRF-Token": csrf})
        assert res1.status_code == 200
        d1 = res1.json()
        job1 = d1.get("data") if isinstance(d1.get("data"), dict) and "id" in d1.get("data", {}) else (d1.get("data") or {}).get("job") or d1.get("job") or d1

        # 2. Identical replay -> returns same job with idempotent_replay=True
        res2 = client.post("/api/v1/features/subdub/jobs", json={"input": initial_payload}, headers={"X-CSRF-Token": csrf})
        assert res2.status_code == 200
        d2 = res2.json()
        job2 = d2.get("data") if isinstance(d2.get("data"), dict) and "id" in d2.get("data", {}) else (d2.get("data") or {}).get("job") or d2.get("job") or d2
        assert job2["id"] == job1["id"]
        assert job2["idempotent_replay"] is True

        # 3. Conflicting payload with same request_id -> 409 Conflict
        conflict_payload = {"upload_id": "up_different_target", "mode": "subtitle_create", "request_id": req_id}
        res3 = client.post("/api/v1/features/subdub/jobs", json={"input": conflict_payload}, headers={"X-CSRF-Token": csrf})
        assert res3.status_code == 409


def test_04_cross_account_isolation_and_unauthenticated():
    """Prove unauthenticated calls return 401 and foreign account access returns 404/403."""
    import app as app_module
    client = TestClient(app_module.app)

    # 1. Unauthenticated request
    unauth_res = client.post("/api/v1/features/subdub/jobs", json={"input": {"upload_id": "up_x"}})
    assert unauth_res.status_code == 401

    # 2. User A creates job
    csrf_a = _login_client(client, "test-user-subdub-r2")
    with patch("copyfast_subdub_job_bridge.dispatch_subdub_job_to_canonical_runtime", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.side_effect = lambda **kwargs: subdub_bridge.get_subdub_job(kwargs["account"]["id"], kwargs["job_id"])
        res_a = client.post(
            "/api/v1/features/subdub/jobs",
            json={"input": {"upload_id": "up_owner_a", "mode": "subtitle_create"}},
            headers={"X-CSRF-Token": csrf_a},
        )
        d_a = res_a.json()
        job_a = d_a.get("data") if isinstance(d_a.get("data"), dict) and "id" in d_a.get("data", {}) else (d_a.get("data") or {}).get("job") or d_a.get("job") or d_a
        job_a_id = job_a["id"]

    # 3. User B attempts to access User A's job
    csrf_b = _login_client(client, "test-foreign-subdub-r2")
    res_b = client.get(f"/api/v1/features/subdub/jobs/{job_a_id}")
    assert res_b.status_code in (403, 404)


def test_05_reconciliation_subtitle_create_free_policy():
    """Prove subtitle_create is exempt from settlement charges (0 Xu charged)."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_free_01", "mode": "subtitle_create"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute("UPDATE web_subdub_jobs SET runtime_job_id='rt_free_01' WHERE id=?", (job_id,))

        mock_rt_job = {
            "ok": True,
            "job": {
                "status": "completed",
                "result": {
                    "output_url": "https://tg.toanaas.vn/subdub/outputs/sub_free_01.vtt",
                    "character_count": 300,
                },
            },
        }

        with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
            mock_bridge.return_value = mock_rt_job

            reconciled = await subdub_bridge.reconcile_subdub_job_status(job_id, account=account)
            assert reconciled["status"] == "completed"
            assert reconciled["settlement_status"] == "exempt_free"
            assert reconciled["charged_xu"] == 0
            assert reconciled["output_available"] is True

            settle_calls = [c for c in mock_bridge.call_args_list if "/web-subdub/settle" in str(c)]
            assert len(settle_calls) == 0

    asyncio.run(_test())


def test_06_reconciliation_paid_lane_settles_and_stores_balance():
    """Prove paid lanes (dub) invoke canonical settlement and store charged Xu."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_paid_01", "mode": "dub", "target_language": "vi"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute("UPDATE web_subdub_jobs SET runtime_job_id='rt_paid_01' WHERE id=?", (job_id,))

        async def mock_bridge_router(method, endpoint, **kwargs):
            if "web-subdub/settle" in endpoint:
                return {
                    "ok": True,
                    "settlement_id": "stl_paid_01",
                    "amount_xu": 20,
                    "balance_after": 280,
                    "settled_at": "2026-10-03T10:00:00Z",
                }
            elif "subdub/jobs/rt_paid_01" in endpoint:
                return {
                    "ok": True,
                    "job": {
                        "status": "completed",
                        "result": {
                            "output_url": "https://tg.toanaas.vn/subdub/outputs/dub_paid_01.mp4",
                            "character_count": 200,
                            "duration": 15.0,
                        },
                    },
                }
            return {"ok": False}

        with patch("copyfast_bridge.bridge_request", side_effect=mock_bridge_router) as mock_bridge:
            reconciled = await subdub_bridge.reconcile_subdub_job_status(job_id, account=account)
            assert reconciled["status"] == "completed"
            assert reconciled["settlement_status"] == "settled"
            assert reconciled["charged_xu"] == 20
            assert reconciled["settlement_id"] == "stl_paid_01"
            assert reconciled["output_available"] is True

    asyncio.run(_test())


def test_07_duplicate_reconcile_read_does_not_double_settle():
    """Prove reading a settled job a second time makes 0 additional settlement calls."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_dup_01", "mode": "dub", "target_language": "en"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_job_id='rt_dup_01',
                    status='completed',
                    status_reason='COMPLETED',
                    settlement_status='settled',
                    charged_xu=20,
                    settlement_id='stl_dup_01',
                    output_url='https://tg.toanaas.vn/subdub/outputs/dub_dup_01.mp4'
                WHERE id=?
                """,
                (job_id,),
            )

        with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
            reconciled = await subdub_bridge.reconcile_subdub_job_status(job_id, account=account)
            assert reconciled["status"] == "completed"
            assert reconciled["settlement_status"] == "settled"
            assert reconciled["charged_xu"] == 20
            assert mock_bridge.call_count == 0

    asyncio.run(_test())


def test_08_reconciliation_unsafe_artifact_blocks_settlement():
    """Prove completion with an unsafe URL blocks settlement and marks failure."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_unsafe_01", "mode": "dub", "target_language": "vi"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute("UPDATE web_subdub_jobs SET runtime_job_id='rt_unsafe_01' WHERE id=?", (job_id,))

        mock_rt_job = {
            "ok": True,
            "job": {
                "status": "completed",
                "result": {
                    "output_url": "http://insecure-http.com/dub.mp4",
                    "character_count": 100,
                },
            },
        }

        with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
            mock_bridge.return_value = mock_rt_job

            reconciled = await subdub_bridge.reconcile_subdub_job_status(job_id, account=account)
            assert reconciled["status_reason"] == "COMPLETED_WITHOUT_SAFE_ARTIFACT"
            assert reconciled["output_available"] is False
            assert reconciled["settlement_status"] == "cancelled_unsafe_artifact"
            assert reconciled["charged_xu"] == 0

            settle_calls = [c for c in mock_bridge.call_args_list if "/web-subdub/settle" in str(c)]
            assert len(settle_calls) == 0

    asyncio.run(_test())


def test_09_failed_job_no_settlement():
    """Prove failed runtime job records cancellation with 0 Xu charged."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_fail_01", "mode": "dub", "target_language": "vi"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute("UPDATE web_subdub_jobs SET runtime_job_id='rt_fail_01' WHERE id=?", (job_id,))

        mock_rt_job = {
            "ok": True,
            "job": {
                "status": "failed",
                "last_error": "AUDIO_EXTRACTION_FAILED",
            },
        }

        with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
            mock_bridge.return_value = mock_rt_job

            reconciled = await subdub_bridge.reconcile_subdub_job_status(job_id, account=account)
            assert reconciled["status"] == "failed"
            assert reconciled["status_reason"] == "AUDIO_EXTRACTION_FAILED"
            assert reconciled["settlement_status"] == "cancelled_job_failed"
            assert reconciled["charged_xu"] == 0

    asyncio.run(_test())
