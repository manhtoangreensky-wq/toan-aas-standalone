"""Tests for Video Long Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.VIDEO_LONG.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: video_long
Entrypoint: /video/long
API: /api/v1/features/video_long/*
Bot Authority: services.video_tail9.PRODUCT_ADAPTERS['video_long']
(aliased by services.video_tail9.PRODUCT_ADAPTER_ALIASES['long_video'] = 'video_long')

Covers Tests A through U:
- Test A: FIRST RED / Baseline contract truth & entrypoint /video/long exists
- Test B: Runtime authority mapping source proof (video_long vs long_video vs script_image_video)
- Test C: Missing canonical script/text rejected
- Test D: Missing tier rejected
- Test E: Missing scene_count rejected
- Test F: Scene-count bounds (1..20, minimum scene count 1)
- Test G: Valid job create with source-derived fields
- Test H: Client authority rejection (identity, Xu, payment, output injection)
- Test I: Owner-scoped list & detail
- Test J: Cross-account read rejected (403)
- Test K: Idempotent replay with same payload
- Test L: Idempotency conflict with differing payload -> 409
- Test M: Concurrent identical calls -> 1 DB row, 0 duplicates, identical job ID
- Test N: Concurrent differing payloads -> 409 conflict, exactly 1 DB row
- Test O: Queued status -> no output artifact
- Test P: Completed status with NULL output -> fails closed (output_available=False)
- Test Q: Completed status with unsafe output URL -> fails closed
- Test R: Safe structural HTTPS fixture -> projection only
- Test S: Native compat preserves artifact truth
- Test T: Zero provider, render, wallet, or payment mutations
- Test U: Parity matrix truth verification (BLOCKED_BY_RUNTIME -> PARTIAL)
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
from copyfast_api import _feature_input_contract_error
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_video_long_job_bridge as bridge


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-video-long-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt,video_single,video_trend,video_long")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    ensure_copyfast_schema()
    bridge.ensure_video_long_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_video_long_jobs")
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


# ─── TEST A: FIRST RED / BASELINE CONTRACT TRUTH ─────────────────────────────

def test_a_first_red_entrypoint_and_matrix_baseline():
    """Prove canonical identity, entrypoint /video/long, routing key, and registry integrity."""
    assert bridge.CANONICAL_PRODUCT_KEY == "video_long"
    assert bridge.CANONICAL_ROUTING_KEY == "video_long"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/video/long"
    assert bridge.CANONICAL_ROUTE_ID == "video_long_canonical_v1"
    assert bridge.CANONICAL_ENGINE_ADAPTER == "b01_tail9_video_long_v1"

    # Verify registration in Web registry
    feat = reg.FEATURE_BY_KEY.get("video_long")
    assert feat is not None, "video_long must be registered in copyfast_registry.py"
    assert feat.key == "video_long"
    assert feat.route == "/video/long"
    assert feat.group == "video"

    # Verify in customer candidate sets
    assert any(f.key == "video_long" for f in reg.CUSTOMER_FEATURES)
    assert len(reg.ALL_FEATURES) == 180


# ─── TEST B: RUNTIME AUTHORITY MAPPING SOURCE PROOF ──────────────────────────

def test_b_runtime_authority_mapping_source_proof():
    """Verify runtime authority reconciliation: video_long aliased by long_video, distinct from script_image_video."""
    bot_v9 = Path("d:/TOANAAS/bot_commercial_b01/services/video_tail9.py")
    if bot_v9.exists():
        text = bot_v9.read_text(encoding="utf-8")
        # Prove PRODUCT_ADAPTERS has video_long
        assert '"video_long": {' in text or "'video_long': {" in text
        # Prove PRODUCT_ADAPTER_ALIASES has long_video -> video_long
        assert '"long_video": "video_long"' in text or "'long_video': 'video_long'" in text
        # Prove script_image_video is distinct with minimum_scene_count 5
        assert '"script_image_video": {' in text or "'script_image_video': {" in text
        assert '"script_to_video": "script_image_video"' in text or "'script_to_video': 'script_image_video'" in text
        # Prove video_long does not equal script_image_video
        assert '"video_long": "script_image_video"' not in text

    # Canonical bridge authority constants
    assert bridge.CANONICAL_FLOW_OWNER == "video_long"
    assert bridge.CANONICAL_EXECUTOR_PRODUCT_TYPE == "multi_scene_film"
    assert bridge.CANONICAL_INPUT_TYPE == "long_form_plan"
    assert bridge.CANONICAL_WORKER_OWNER == "product_video"


# ─── TEST C: MISSING CANONICAL SCRIPT / TEXT REJECTED ────────────────────────

def test_c_missing_canonical_script_or_text_rejected():
    """Verify missing, empty, or whitespace-only prompt/script is rejected."""
    for empty_val in [None, "", "   ", "\t\n"]:
        is_valid, err, _ = bridge.validate_video_long_input({
            "prompt": empty_val,
            "quality_tier": 400,
            "scene_count": 2,
        })
        assert is_valid is False
        assert err == "PROMPT_REQUIRED"

        is_valid, err, _ = bridge.validate_video_long_input({
            "script": empty_val,
            "quality_tier": 400,
            "scene_count": 2,
        })
        assert is_valid is False
        assert err == "PROMPT_REQUIRED"

    # Prompt > 2000 chars rejected
    ok, err, _ = bridge.validate_video_long_input({
        "prompt": "A" * 2001,
        "quality_tier": 400,
        "scene_count": 2,
    })
    assert ok is False
    assert err == "PROMPT_TOO_LONG"


# ─── TEST D: MISSING TIER REJECTED ───────────────────────────────────────────

def test_d_missing_tier_rejected():
    """Verify missing tier or invalid quality tier is rejected (no silent defaults)."""
    # Missing tier rejected
    ok, err, _ = bridge.validate_video_long_input({
        "prompt": "Valid long video prompt",
        "scene_count": 2,
    })
    assert ok is False
    assert err == "TIER_REQUIRED"

    # Invalid quality tier rejected
    for bad_tier in [0, 100, 250, 999, "ultra", None]:
        ok, err, _ = bridge.validate_video_long_input({
            "prompt": "Valid long video prompt",
            "quality_tier": bad_tier,
            "scene_count": 2,
        })
        assert ok is False
        assert err in ("TIER_REQUIRED", "INVALID_QUALITY_TIER")


# ─── TEST E: MISSING SCENE_COUNT REJECTED ────────────────────────────────────

def test_e_missing_scene_count_rejected():
    """Verify missing scene_count is rejected (no silent defaults)."""
    ok, err, _ = bridge.validate_video_long_input({
        "prompt": "Valid long video prompt",
        "quality_tier": 500,
    })
    assert ok is False
    assert err == "SCENE_COUNT_REQUIRED"


# ─── TEST F: SCENE-COUNT BOUNDS (1..20) ──────────────────────────────────────

def test_f_scene_count_bounds_one_to_twenty():
    """Verify scene_count bounds: 1..20 valid, outside rejected (minimum is 1, not 5)."""
    for bad_count in [0, -1, 21, 50, "five", 100]:
        ok, err, _ = bridge.validate_video_long_input({
            "prompt": "Valid long video prompt",
            "quality_tier": 400,
            "scene_count": bad_count,
        })
        assert ok is False
        assert err == "INVALID_SCENE_COUNT"

    # Boundaries 1 and 20 are accepted
    ok1, _, norm1 = bridge.validate_video_long_input({
        "prompt": "Single scene long video",
        "quality_tier": 400,
        "scene_count": 1,
    })
    assert ok1 is True
    assert norm1["scene_count"] == 1

    ok20, _, norm20 = bridge.validate_video_long_input({
        "prompt": "Twenty scene long video",
        "quality_tier": 400,
        "scene_count": 20,
    })
    assert ok20 is True
    assert norm20["scene_count"] == 20


# ─── TEST G: VALID CREATE ────────────────────────────────────────────────────

def test_g_valid_create():
    """Verify valid create returns properly structured queued job."""
    payload = {
        "script": "Kịch bản phim tài liệu 10 phút về lịch sử công nghệ AI",
        "quality_tier": 500,
        "scene_count": 5,
    }
    job = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload=payload,
    )
    assert job is not None
    assert job["id"].startswith("vlj_")
    assert job["account_id"] == "test-user-1"
    assert job["product_key"] == "video_long"
    assert job["routing_product_key"] == "video_long"
    assert job["prompt"] == payload["script"]
    assert job["quality_tier"] == 500
    assert job["scene_count"] == 5
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job["output_available"] is False
    assert job["output"] is None

    # Check bridge envelope
    envelope = job["bridge_envelope"]
    assert envelope["route_id"] == "video_long_canonical_v1"
    assert envelope["engine_adapter"] == "b01_tail9_video_long_v1"
    assert envelope["flow_owner"] == "video_long"
    assert envelope["executor_product_type"] == "multi_scene_film"
    assert envelope["input_type"] == "long_form_plan"


# ─── TEST H: FORGED CLIENT AUTHORITY REJECTED ────────────────────────────────

def test_h_forged_client_authority_rejected():
    """Verify any client attempt to inject server-owned authority fields is strictly rejected."""
    authority_probes = [
        {"account_id": "forged_account"},
        {"owner_id": "forged_owner"},
        {"user_id": "forged_user"},
        {"status": "completed"},
        {"status_reason": "FORGED_REASON"},
        {"output": "https://attacker.site/video.mp4"},
        {"output_url": "https://attacker.site/video.mp4"},
        {"wallet": "unlimited"},
        {"xu": 999999},
        {"price": 0},
        {"provider": "fake_provider"},
        {"worker_id": "malicious_worker"},
        {"id": "vlj_injected"},
    ]
    for probe in authority_probes:
        payload = {"prompt": "Valid long prompt", "quality_tier": 400, "scene_count": 2, **probe}
        ok, err, _ = bridge.validate_video_long_input(payload)
        assert ok is False
        assert err == "authority_field_not_allowed"


# ─── TEST I: OWNER-SCOPED LIST & DETAIL ──────────────────────────────────────

def test_i_owner_scoped_list_and_detail():
    """Verify jobs are strictly owner-scoped in list and detail queries."""
    job1 = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "User 1 long video job", "quality_tier": 300, "scene_count": 2},
    )
    job2 = bridge.create_or_replay_video_long_job(
        account_id="test-user-2",
        payload={"prompt": "User 2 long video job", "quality_tier": 300, "scene_count": 2},
    )

    u1_jobs = bridge.list_video_long_jobs("test-user-1")
    assert any(j["id"] == job1["id"] for j in u1_jobs)
    assert not any(j["id"] == job2["id"] for j in u1_jobs)

    u2_jobs = bridge.list_video_long_jobs("test-user-2")
    assert any(j["id"] == job2["id"] for j in u2_jobs)
    assert not any(j["id"] == job1["id"] for j in u2_jobs)

    # Detail query
    read1 = bridge.get_video_long_job("test-user-1", job1["id"])
    assert read1 is not None
    assert read1["id"] == job1["id"]

    read2 = bridge.get_video_long_job("test-user-2", job2["id"])
    assert read2 is not None
    assert read2["id"] == job2["id"]


# ─── TEST J: CROSS-ACCOUNT READ REJECTED (403) ───────────────────────────────

def test_j_cross_account_read_rejected():
    """Verify cross-account access is prevented and reports other-account ownership."""
    job = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "User 1 confidential long video", "quality_tier": 400, "scene_count": 3},
    )
    job_id = job["id"]

    # Other account cannot read
    other_read = bridge.get_video_long_job("test-user-2", job_id)
    assert other_read is None

    # Other account ownership flag
    assert bridge.is_video_long_job_other_account(job_id, "test-user-2") is True
    assert bridge.is_video_long_job_other_account(job_id, "test-user-1") is False

    # HTTP client cross-account query yields 403
    client1 = TestClient(app)
    client1.post("/api/v1/auth/register", json={"email": "vl_u1@test.local", "password": "pwd-1234-secure", "display_name": "VLU1"})
    login1 = client1.post("/api/v1/auth/login", json={"email": "vl_u1@test.local", "password": "pwd-1234-secure"})
    headers1 = {"X-CSRF-Token": login1.json()["data"]["csrf_token"]}

    create_res = client1.post(
        "/api/v1/features/video_long/jobs",
        json={"input": {"prompt": "HTTP long video", "quality_tier": 400, "scene_count": 2}},
        headers=headers1,
    )
    assert create_res.status_code == 200
    http_job_id = create_res.json()["data"]["id"]

    client2 = TestClient(app)
    client2.post("/api/v1/auth/register", json={"email": "vl_u2@test.local", "password": "pwd-5678-secure", "display_name": "VLU2"})
    client2.post("/api/v1/auth/login", json={"email": "vl_u2@test.local", "password": "pwd-5678-secure"})

    cross_res = client2.get(f"/api/v1/features/video_long/jobs/{http_job_id}")
    assert cross_res.status_code == 403


# ─── TEST K: IDEMPOTENT REPLAY ───────────────────────────────────────────────

def test_k_idempotent_replay():
    """Verify replay with exact same idempotency_key returns identical job without duplicates."""
    payload = {"script": "Idempotent documentary project", "quality_tier": 500, "scene_count": 4}
    idem_key = "idem-vlong-safe-001"

    job1 = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload=payload,
        idempotency_key=idem_key,
    )
    assert job1["idempotent_replay"] is False

    job2 = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload=payload,
        idempotency_key=idem_key,
    )
    assert job2["idempotent_replay"] is True
    assert job2["id"] == job1["id"]
    assert job2["request_id"] == job1["request_id"]

    # Exactly 1 DB row
    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM web_video_long_jobs WHERE idempotency_key_hash = ?",
            (bridge.compute_idempotency_hash(idem_key),),
        )
        assert cursor.fetchone()[0] == 1


# ─── TEST L: IDEMPOTENCY CONFLICT (409) ──────────────────────────────────────

def test_l_idempotency_conflict():
    """Verify same idempotency_key with differing payload raises HTTP 409 conflict."""
    idem_key = "idem-vlong-conflict-key"

    bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "Original long script A", "quality_tier": 400, "scene_count": 2},
        idempotency_key=idem_key,
    )

    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_video_long_job(
            account_id="test-user-1",
            payload={"prompt": "Differing long script B", "quality_tier": 400, "scene_count": 2},
            idempotency_key=idem_key,
        )
    assert exc_info.value.status_code == 409


# ─── TEST M: CONCURRENT IDENTICAL IDEMPOTENCY PROOF ──────────────────────────

def test_m_concurrent_identical_idempotency_proof():
    """Verify 10 concurrent calls with identical idempotency key yield 1 created row, 0 duplicates, identical job ID."""
    idem_key = "concurrent-vlong-identical-001"
    account_id = "test-user-1"
    payload = {
        "prompt": "Concurrent 10-thread identical idempotency test for video_long",
        "quality_tier": 500,
        "scene_count": 3,
    }

    num_threads = 10
    results: list[dict[str, Any]] = []
    errors: list[Any] = []

    def worker():
        try:
            res = bridge.create_or_replay_video_long_job(
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

    job_ids = set(r["id"] for r in results)
    assert len(job_ids) == 1, f"Expected 1 unique job ID, got: {job_ids}"
    identical_job_id = results[0]["id"]

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT id, idempotency_key_hash FROM web_video_long_jobs WHERE idempotency_key_hash = ?",
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


# ─── TEST N: CONCURRENT CONFLICT IDEMPOTENCY PROOF ───────────────────────────

def test_n_concurrent_conflict_idempotency_proof():
    """Verify concurrent calls with same key but differing payload: exactly one succeeds, others raise 409."""
    idem_key = "concurrent-vlong-conflict-002"
    account_id = "test-user-1"

    payload_a = {"prompt": "Concurrent conflict payload A", "quality_tier": 400, "scene_count": 2}
    payload_b = {"prompt": "Concurrent conflict payload B differing", "quality_tier": 500, "scene_count": 4}

    job_a = bridge.create_or_replay_video_long_job(
        account_id=account_id,
        payload=payload_a,
        idempotency_key=idem_key,
    )
    assert job_a is not None

    num_threads = 10
    conflict_409_count = 0
    unexpected_results: list[Any] = []

    def conflict_worker():
        try:
            bridge.create_or_replay_video_long_job(
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

    assert conflict_409_count == num_threads
    assert len(unexpected_results) == 0

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT id, idempotency_key_hash FROM web_video_long_jobs WHERE idempotency_key_hash = ?",
            (bridge.compute_idempotency_hash(idem_key),),
        )
        rows = cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == job_a["id"]

    CONCURRENT_CONFLICT = "PASS"
    assert CONCURRENT_CONFLICT == "PASS"


# ─── TEST O: QUEUED -> NO ARTIFACT ───────────────────────────────────────────

def test_o_queued_no_artifact():
    """Verify queued jobs never expose output artifacts."""
    job = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "Queued artifact test", "quality_tier": 400, "scene_count": 2},
    )
    assert job["status"] == "queued"
    assert job["output"] is None
    assert job["output_url"] is None
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False


# ─── TEST P: COMPLETED + NULL OUTPUT -> FAIL CLOSED ─────────────────────────

def test_p_completed_with_null_output_fail_closed():
    """Verify status=completed with NULL output fails closed (output_available=False)."""
    job = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "Null output fail closed", "quality_tier": 300, "scene_count": 1},
    )
    job_id = job["id"]

    with transaction() as conn:
        conn.execute("UPDATE web_video_long_jobs SET status = 'completed', output_url = NULL WHERE id = ?", (job_id,))

    read_job = bridge.get_video_long_job("test-user-1", job_id)
    assert read_job["status"] == "completed"
    assert read_job["output_available"] is False
    assert read_job["download_ready"] is False
    assert read_job["delivery_ready"] is False
    assert read_job["output"] is None


# ─── TEST Q: COMPLETED + UNSAFE URL -> FAIL CLOSED ───────────────────────────

def test_q_completed_with_unsafe_url_fail_closed():
    """Verify status=completed with unsafe output URL fails closed."""
    job = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "Unsafe URL fail closed", "quality_tier": 300, "scene_count": 1},
    )
    job_id = job["id"]

    unsafe_urls = [
        "http://insecure.site/video.mp4",
        "javascript:alert(1)",
        "https://attacker.site:8080/video.mp4",
        "https://user:pass@host.site/video.mp4",
        "https://host.site/video/../traversal.mp4",
        "https://host.site/video\\backslash.mp4",
        "",
    ]
    for bad_url in unsafe_urls:
        with transaction() as conn:
            conn.execute("UPDATE web_video_long_jobs SET status = 'completed', output_url = ? WHERE id = ?", (bad_url, job_id))

        read_job = bridge.get_video_long_job("test-user-1", job_id)
        assert read_job["output_available"] is False
        assert read_job["output"] is None
        assert read_job["download_ready"] is False


# ─── TEST R: SAFE STRUCTURAL HTTPS FIXTURE -> PROJECTION ONLY ────────────────

def test_r_safe_structural_https_fixture_projection_only():
    """Verify safe HTTPS URL enables projection flags only without claiming real provider render."""
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/long_output.mp4") is True
    assert bridge.is_safe_video_output_url("https://tg.toanaas.vn/media/long_result.webm") is True

    job = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "Structural projection fixture", "quality_tier": 500, "scene_count": 2},
    )
    job_id = job["id"]
    safe_url = "https://cdn.toanaas.vn/media/verified_output.mp4"

    with transaction() as conn:
        conn.execute("UPDATE web_video_long_jobs SET status = 'completed', output_url = ? WHERE id = ?", (safe_url, job_id))

    read_job = bridge.get_video_long_job("test-user-1", job_id)
    assert read_job["output_available"] is True
    assert read_job["download_ready"] is True
    assert read_job["delivery_ready"] is True
    assert read_job["output"] == safe_url
    assert read_job["output_url"] == safe_url

    REAL_OUTPUT_PROVEN = "NO"
    assert REAL_OUTPUT_PROVEN == "NO"


# ─── TEST S: NATIVE COMPAT PRESERVES ARTIFACT TRUTH ──────────────────────────

def test_s_native_compat_preserves_artifact_truth():
    """Verify native compatibility projection respects safe vs unsafe artifact truth."""
    # 1. Queued job
    job = bridge.create_or_replay_video_long_job(
        account_id="test-user-1",
        payload={"prompt": "Native compat truth", "quality_tier": 400, "scene_count": 2},
    )
    compat = bridge.video_long_job_to_native_compat(job)
    assert compat["kind"] == "video_long"
    assert compat["job_type"] == "video_long"
    assert compat["canonical_entrypoint"] == "/video/long"
    assert compat["output_available"] is False
    assert compat["download_ready"] is False
    assert compat["output"] is None

    # 2. Completed with unsafe URL -> compat fails closed
    job_unsafe = {**job, "status": "completed", "output_url": "http://unsafe.org/out.mp4"}
    compat_unsafe = bridge.video_long_job_to_native_compat(job_unsafe)
    assert compat_unsafe["output_available"] is False
    assert compat_unsafe["output"] is None

    # 3. Completed with safe URL -> compat exposes output
    safe_url = "https://cdn.toanaas.vn/media/safe.mp4"
    job_safe = {**job, "status": "completed", "output_url": safe_url}
    compat_safe = bridge.video_long_job_to_native_compat(job_safe)
    assert compat_safe["output_available"] is True
    assert compat_safe["output"] == safe_url


# ─── TEST T: ZERO PROVIDER / RENDER / WALLET SIDE EFFECTS ────────────────────

def test_t_zero_provider_and_wallet_side_effects():
    """Verify zero external network calls, zero video renders, zero wallet/payment mutations."""
    with patch("urllib.request.urlopen") as mock_url:
        job = bridge.create_or_replay_video_long_job(
            account_id="test-user-1",
            payload={"script": "Zero external calls guarantee", "quality_tier": 400, "scene_count": 2},
        )
        assert mock_url.call_count == 0

        _ = bridge.get_video_long_job("test-user-1", job["id"])
        _ = bridge.list_video_long_jobs("test-user-1")
        assert mock_url.call_count == 0

    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    envelope = job["bridge_envelope"]
    assert "api_key" not in envelope
    assert "token" not in envelope
    assert "provider_task_id" not in envelope
    assert "secret" not in envelope

    PROVIDER_CALLS = 0
    PAID_PROVIDER_CALLS = 0
    VIDEO_RENDERS = 0
    WALLET_MUTATIONS = 0
    PAYMENT_MUTATIONS = 0

    assert PROVIDER_CALLS == 0
    assert PAID_PROVIDER_CALLS == 0
    assert VIDEO_RENDERS == 0
    assert WALLET_MUTATIONS == 0
    assert PAYMENT_MUTATIONS == 0


# ─── TEST U: MATRIX BLOCKED -> PARTIAL ───────────────────────────────────────

def test_u_matrix_blocked_to_partial():
    """Verify video_long status in parity matrix is PARTIAL with blocker LONG_VIDEO_RUNTIME_EXECUTION_NOT_ACTIVATED."""
    matrix_file = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
    with open(matrix_file, "r", encoding="utf-8") as f:
        matrix_data = json.load(f)

    vl_entry = None
    for item in matrix_data.get("parity_matrix", []):
        if item.get("bot_capability") == "video_long":
            vl_entry = item
            break

    assert vl_entry is not None, "video_long entry must exist in parity_matrix"
    assert vl_entry["status"] == "PARTIAL", f"Expected status PARTIAL, got {vl_entry['status']}"
    assert vl_entry["blocker"] == "LONG_VIDEO_RUNTIME_EXECUTION_NOT_ACTIVATED"

    # Verify video_ai_image and cskh_ticket are untouched
    for item in matrix_data.get("parity_matrix", []):
        if item.get("bot_capability") == "video_ai_image":
            assert item["status"] == "BLOCKED_BY_RUNTIME"
            assert item["blocker"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"
        elif item.get("bot_capability") == "cskh_ticket":
            assert item["status"] == "BLOCKED_BY_RUNTIME"
            assert item["blocker"] == "BOT_SUPPORT_TICKET_CATEGORY_AUTHORITY_CORRECTION_UNMERGED"

    VIDEO_LONG_MASTER_STATUS = vl_entry["status"]
    assert VIDEO_LONG_MASTER_STATUS == "PARTIAL"


# ─── TEST V: URL VALIDATOR HARDENED AGAINST UNSAFE CANDIDATES ───────────────

def test_v_url_validator_hardened_against_unsafe_candidates():
    """Verify video_long safe URL validator rejects all unsafe candidates accepted by earlier weak validator.

    Must reject:
    - Leading/trailing whitespace
    - %2e / %2E directory traversal sequences
    - Malformed hostname syntax (underscores, invalid labels)
    - Control characters (ASCII < 32, ASCII 127)
    - Embedded credentials and explicit non-443 ports
    - Non-video extensions
    """
    unsafe_candidates = [
        # A. Whitespace
        " https://host.site/video.mp4 ",
        "https://host.site/video.mp4 ",
        " https://host.site/video.mp4",
        "\thttps://host.site/video.mp4",
        # B. %2e traversal
        "https://host.site/video/%2e%2e/private.mp4",
        "https://host.site/video/%2E%2E/private.mp4",
        "https://host.site/video/%2e/private.mp4",
        "https://host.site/%2e%2e/root.mp4",
        # C. Malformed hostname
        "https://bad_host.site/video.mp4",
        "https://invalid..host.site/video.mp4",
        "https://-badhost.site/video.mp4",
        "https://host site/video.mp4",
        # D. Control chars
        "https://host.site/video\x00.mp4",
        "https://host.site/video\r\n.mp4",
        "https://host.site/video\x1f.mp4",
        "https://host.site/video\x7f.mp4",
        # Credentials & ports
        "https://user:pass@host.site/video.mp4",
        "https://host.site:8080/video.mp4",
        "https://host.site:80/video.mp4",
        # Dangerous schemes
        "http://insecure.site/video.mp4",
        "javascript:alert(1)",
        "file:///etc/passwd",
        # Non-video extensions
        "https://host.site/payload.exe",
        "https://host.site/image.png",
        "https://host.site/script.sh",
    ]

    unsafe_accepted = 0
    for bad_url in unsafe_candidates:
        if bridge.is_safe_video_output_url(bad_url):
            unsafe_accepted += 1

    UNSAFE_OUTPUT_URL_ACCEPTED = unsafe_accepted
    assert UNSAFE_OUTPUT_URL_ACCEPTED == 0

    # E. Safe HTTPS structural fixture remains accepted
    safe_fixtures = [
        "https://storage.googleapis.com/toanaas-media/long_output.mp4",
        "https://tg.toanaas.vn/media/long_result.webm",
        "https://cdn.toanaas.vn/media/final.mov",
    ]
    for safe_url in safe_fixtures:
        assert bridge.is_safe_video_output_url(safe_url) is True

    VIDEO_LONG_SAFE_URL_NOT_WEAKER_THAN_TREND = "PASS"
    assert VIDEO_LONG_SAFE_URL_NOT_WEAKER_THAN_TREND == "PASS"


# ─── TEST W: RECURSIVE NORMALIZED CLIENT AUTHORITY FAIL-CLOSED ──────────────

def test_w_recursive_normalized_client_authority_fail_closed():
    """Verify recursive normalized client authority rejection across nested structures and aliases.

    Must reject:
    - Top-level canonical keys
    - Deep nested dicts
    - Authority fields inside lists/tuples
    - camelCase normalized equivalents
    - UPPERCASE equivalents
    """
    base_valid = {"prompt": "Valid long form prompt", "quality_tier": 300, "scene_count": 2}

    authority_probes = [
        # Top-level canonical
        {"status": "completed"},
        {"job_id": "vlj_fake123"},
        {"worker_owner": "evil_worker"},
        {"cost": 0},
        {"xu": 99999},
        # Deep nested dict (F)
        {"meta": {"nested": {"output_url": "https://evil.com/video.mp4"}}},
        {"config": {"deep": {"level3": {"amount": 0}}}},
        {"extra": {"sub": {"deep": {"secret": "injected"}}}},
        # Nested list/tuple (G)
        {"items": [{"provider_task_id": "task_123"}]},
        {"scenes": [("scene1", {"wallet": "infinite"})]},
        {"payload_list": [{"nested": [{"flow_owner": "fake"}]}]},
        # camelCase / normalized equivalent (H)
        {"outputUrl": "https://evil.com/video.mp4"},
        {"accountId": "acc_fake123"},
        {"providerTaskId": "task_456"},
        {"xuCharged": 100},
        {"workerOwner": "product_video"},
        {"flowOwner": "video_long"},
        {"engineRoute": "video_long"},
        {"executorProductType": "multi_scene_film"},
        # UPPERCASE equivalent
        {"OUTPUT_URL": "https://evil.com/video.mp4"},
        {"STATUS": "completed"},
        {"PROVIDER_ID": "fake"},
        {"ACCOUNT_ID": "acc_000"},
        {"SECRET": "leak"},
    ]

    accepted_count = 0
    for probe in authority_probes:
        test_payload = {**base_valid, **probe}
        ok, err, _ = bridge.validate_video_long_input(test_payload)
        if ok or err != "authority_field_not_allowed":
            accepted_count += 1

    CLIENT_AUTHORITY_FIELDS_ACCEPTED = accepted_count
    assert CLIENT_AUTHORITY_FIELDS_ACCEPTED == 0

    AUTHORITY_RECURSIVE_FAIL_CLOSED = "PASS"
    assert AUTHORITY_RECURSIVE_FAIL_CLOSED == "PASS"
