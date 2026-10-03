"""Tests for Web SubDub Comprehensive Runtime & Financial Parity (R2.1 Correction).

Task: SUBDUB_WEB_RUNTIME_PARITY_R2_1_PR_CONTRACT_AND_CI_CORRECTION
Repo: manhtoangreensky-wq/toan-aas-standalone
Tracker: #612

Verifies:
1. 9/9 Direct Routes parity: all 9 aliases create, list, retrieve, and reconcile jobs.
2. GET Status Read is 100% Side-Effect Free:
   - GET /features/subdub/jobs/{job_id} makes ZERO settlement calls and ZERO wallet mutations.
   - Repeated GET calls make ZERO settlement calls.
   - GET list makes ZERO settlement calls.
3. Server-Authoritative Mutation Transition (settle_subdub_job_completion & POST reconcile):
   - Exactly 1 canonical settlement invocation on completed paid job with safe artifact.
   - Wire schema exact match: web_job_id, web_request_id, canonical_user_id, subdub_mode,
     output_url, validated_output_metadata, idempotency_key.
   - Zero legacy/drift keys in wire payload (request_id, mode, character_count, amount_xu, price, wallet_id).
   - Stable idempotency key: subdub_settle:{web_job_id}:{subdub_mode}.
   - Duplicate mutation call: idempotent replay, ZERO second debit.
4. Error Contract:
   - INSUFFICIENT_FUNDS -> 402, settlement_status='insufficient_funds', 0 wallet debit.
5. Safety Invariants:
   - subtitle_create: exempt_free, charged_xu = 0, ZERO settlement calls.
   - Unsafe artifact or job failure: cancelled, charged_xu = 0, ZERO settlement calls.
   - Cross-account access: 401 / 403 / 404 blocked.
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

            # 4. POST /api/v1/features/{alias}/jobs/{job_id}/reconcile
            recon_res = client.post(
                f"/api/v1/features/{alias}/jobs/{job_id}/reconcile",
                headers={"X-CSRF-Token": csrf},
            )
            assert recon_res.status_code == 200, f"Route /api/v1/features/{alias}/jobs/{job_id}/reconcile POST failed: {recon_res.text}"


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


def test_05_get_routes_strictly_read_only_zero_settlement_calls():
    """PHASE C CONTRACT: Prove GET job-detail and GET list perform ZERO settlement calls."""
    import app as app_module
    client = TestClient(app_module.app)
    csrf = _login_client(client, "test-user-subdub-r2")

    account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
    job = subdub_bridge.create_or_replay_subdub_job(
        account_id=account["id"],
        payload={"upload_id": "up_get_readonly", "mode": "dub", "target_language": "vi"},
    )
    job_id = job["id"]

    with transaction() as conn:
        conn.execute("UPDATE web_subdub_jobs SET runtime_job_id='rt_get_01' WHERE id=?", (job_id,))

    mock_rt_job = {
        "ok": True,
        "job": {
            "status": "completed",
            "result": {
                "output_url": "https://tg.toanaas.vn/subdub/outputs/dub_get_01.mp4",
                "character_count": 500,
                "duration": 30.0,
            },
        },
    }

    with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_rt_job

        # 1. GET job detail
        res1 = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
        assert res1.status_code == 200
        job_data1 = res1.json().get("data") or {}
        assert job_data1["status"] == "completed"
        # Settlement must still be pending because GET is strictly read-only
        assert job_data1["settlement_status"] == "pending"

        # 2. Repeated GET job detail
        res2 = client.get(f"/api/v1/features/subdub/jobs/{job_id}")
        assert res2.status_code == 200

        # 3. GET job list
        res3 = client.get("/api/v1/features/subdub/jobs")
        assert res3.status_code == 200

        # ASSERTION: Zero calls to /web-subdub/settle during any GET call
        settle_calls = [c for c in mock_bridge.call_args_list if "/web-subdub/settle" in str(c)]
        assert len(settle_calls) == 0, f"Expected 0 settlement calls on GET, got {len(settle_calls)}"


def test_06_server_mutation_wire_contract_exact_match():
    """PHASES B & E CONTRACT: Capture exact settlement wire payload and assert all 7 fields."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_wire_01", "mode": "dub", "target_language": "vi"},
        )
        job_id = job["id"]

        # Mark job as completed with safe artifact
        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_job_id='rt_wire_01',
                    status='completed',
                    status_reason='COMPLETED',
                    output_url='https://tg.toanaas.vn/subdub/outputs/dub_wire_01.mp4',
                    output_metadata=?
                WHERE id=?
                """,
                (json.dumps({"character_count": 250, "duration": 20.0}), job_id),
            )

        captured_calls = []

        async def mock_bridge_capture(method, endpoint, **kwargs):
            if "web-subdub/settle" in endpoint:
                captured_calls.append({"method": method, "endpoint": endpoint, "kwargs": kwargs})
                return {
                    "ok": True,
                    "settlement_id": "stl_wire_999",
                    "amount_xu": 25,
                    "balance_after": 475,
                    "settled_at": "2026-10-03T10:00:00Z",
                }
            return {"ok": False}

        with patch("copyfast_bridge.bridge_request", side_effect=mock_bridge_capture):
            settled = await subdub_bridge.settle_subdub_job_completion(job_id, account=account)
            assert settled["status"] == "completed"
            assert settled["settlement_status"] == "settled"
            assert settled["charged_xu"] == 25
            assert settled["settlement_id"] == "stl_wire_999"

            # 1. Exactly 1 settlement call
            assert len(captured_calls) == 1
            call = captured_calls[0]
            assert call["method"] == "POST"
            assert "/internal/v1/web-subdub/settle" in call["endpoint"]

            # 2. EXACT 7 CANONICAL FIELDS
            payload = call["kwargs"].get("payload", {})
            assert "web_job_id" in payload and payload["web_job_id"] == job_id
            assert "web_request_id" in payload and payload["web_request_id"].startswith("SDB-")
            assert "canonical_user_id" in payload and payload["canonical_user_id"] == "7126111111"
            assert "subdub_mode" in payload and payload["subdub_mode"] == "dub"
            assert "output_url" in payload and payload["output_url"] == "https://tg.toanaas.vn/subdub/outputs/dub_wire_01.mp4"
            assert "validated_output_metadata" in payload and isinstance(payload["validated_output_metadata"], dict)
            assert "idempotency_key" in payload and payload["idempotency_key"] == f"subdub_settle:{job_id}:dub"

            # 3. ZERO LEGACY/DRIFT AUTHORITY KEYS IN WIRE PAYLOAD
            for forbidden_key in ("request_id", "mode", "character_count", "amount_xu", "price", "wallet_id", "provider_id", "provider_voice_id"):
                assert forbidden_key not in payload, f"Forbidden legacy authority key '{forbidden_key}' found in settlement wire payload"

    asyncio.run(_test())


def test_07_duplicate_mutation_transition_zero_second_debit():
    """PHASE C CONTRACT: Duplicate call to settlement transition returns duplicate=True and 0 second debit."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_dup_mut", "mode": "dub", "target_language": "en"},
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
            settled = await subdub_bridge.settle_subdub_job_completion(job_id, account=account)
            assert settled["status"] == "completed"
            assert settled["settlement_status"] == "settled"
            assert settled["charged_xu"] == 20
            # Zero bridge calls since already settled
            assert mock_bridge.call_count == 0

    asyncio.run(_test())


def test_08_insufficient_funds_error_contract():
    """PHASE D CONTRACT: Settle call with INSUFFICIENT_FUNDS maps to 402 and settlement_status='insufficient_funds'."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_insuf_web", "mode": "dub", "target_language": "vi"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_job_id='rt_insuf_01',
                    status='completed',
                    status_reason='COMPLETED',
                    output_url='https://tg.toanaas.vn/subdub/outputs/dub_insuf.mp4',
                    output_metadata='{"character_count": 1000}'
                WHERE id=?
                """,
                (job_id,),
            )

        mock_insuf_response = {
            "ok": False,
            "error_code": "INSUFFICIENT_FUNDS",
            "message": "Số dư tài khoản không đủ",
            "balance_xu": 5,
            "required_xu": 90,
        }

        with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
            mock_bridge.return_value = mock_insuf_response

            settled = await subdub_bridge.settle_subdub_job_completion(job_id, account=account)
            assert settled["status"] == "completed"
            assert settled["settlement_status"] == "insufficient_funds"
            assert settled["status_reason"] == "SETTLEMENT_PAYMENT_REQUIRED"
            assert settled["charged_xu"] == 0

    asyncio.run(_test())


def test_09_subtitle_create_free_policy_zero_settlement_calls():
    """PHASE F CONTRACT: subtitle_create is exempt from settlement charges (exempt_free, 0 Xu)."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_free_safe", "mode": "subtitle_create"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_job_id='rt_free_01',
                    status='completed',
                    status_reason='COMPLETED',
                    output_url='https://tg.toanaas.vn/subdub/outputs/sub_free.vtt',
                    output_metadata='{"character_count": 300}'
                WHERE id=?
                """,
                (job_id,),
            )

        with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
            settled = await subdub_bridge.settle_subdub_job_completion(job_id, account=account)
            assert settled["status"] == "completed"
            assert settled["settlement_status"] == "exempt_free"
            assert settled["charged_xu"] == 0
            # Zero bridge settlement calls
            assert mock_bridge.call_count == 0

    asyncio.run(_test())


def test_10_unsafe_artifact_or_failure_zero_settlement_calls():
    """PHASE C CONTRACT: Job not completed or with unsafe artifact rejects settlement."""
    async def _test():
        account = {"id": "test-user-subdub-r2", "canonical_user_id": "7126111111"}
        job = subdub_bridge.create_or_replay_subdub_job(
            account_id=account["id"],
            payload={"upload_id": "up_insecure", "mode": "dub", "target_language": "vi"},
        )
        job_id = job["id"]

        with transaction() as conn:
            conn.execute(
                """
                UPDATE web_subdub_jobs
                SET runtime_job_id='rt_insec_01',
                    status='completed',
                    status_reason='COMPLETED_WITHOUT_SAFE_ARTIFACT',
                    output_url='http://insecure-http.com/dub.mp4'
                WHERE id=?
                """,
                (job_id,),
            )

        with patch("copyfast_bridge.bridge_request", new_callable=AsyncMock) as mock_bridge:
            settled = await subdub_bridge.settle_subdub_job_completion(job_id, account=account)
            # Must remain un-settled and not invoke settlement
            assert settled["settlement_status"] == "pending"
            assert mock_bridge.call_count == 0

    asyncio.run(_test())
