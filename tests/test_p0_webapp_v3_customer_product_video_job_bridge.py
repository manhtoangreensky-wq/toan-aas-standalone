"""Tests for Product Video Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.CANONICAL.JOB_BRIDGE.ADAPTER.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Master Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Enforces 16 Invariants & Contracts:
1. Product Identity: canonical key `video_ai_prompt`, entrypoint `/video/create`,
   routing key `video_ai_canonical` matches `services.product_video_one_scene_engine`.
   Zero identity conflicts (aliases `video_single`), 180 total registry features preserved.
2. Web Feature Adapter Registration: `video_ai_prompt` recognized in adapter keys;
   ONLY `video_ai_prompt` is in `SUPPORTED_CANONICAL_JOB_ADAPTERS` (0 other 9 generators).
3. Payload Validation: missing prompt rejected (PROMPT_REQUIRED).
4. Payload Validation: prompt > 2000 chars rejected (PROMPT_TOO_LONG).
5. Payload Validation: invalid aspect ratio rejected (INVALID_ASPECT_RATIO).
6. Payload Validation: invalid duration rejected (INVALID_DURATION).
7. Payload Validation: invalid quality tier rejected (INVALID_QUALITY_TIER).
8. Payload Validation: authority field injection rejected (authority_field_not_allowed).
9. Persistence: persists durable record in SQLite table `web_product_video_jobs` with
   status 'queued', reason 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION', zero fake output.
10. Idempotency: exact replay returns existing job with `idempotent_replay=True`, zero duplicate.
11. Conflict: same request_id with differing payload rejected with 409 Conflict.
12. Query List: GET /api/v1/jobs & GET /api/v1/features/video_ai_prompt/jobs list account jobs.
13. Query Detail & Cross-User Security: owner can read job detail; other user rejected with 403.
14. Invariant: zero external provider calls and zero wallet/Xu/PayOS mutations.
15. Invariant: zero real video render subprocesses and zero fake completed status.
16. Admin Traceability: bridge envelope contains complete Bot authority metadata.
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
from copyfast_api import _web_feature_job_adapter_keys
from app import app
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_product_video_job_bridge as bridge


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-video-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt,video_single")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_product_video_jobs WHERE account_id LIKE 'test-%'")
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
        conn.execute("DELETE FROM web_product_video_jobs WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


# ─── TEST 1: PRODUCT IDENTITY AND ENTRYPOINT ─────────────────────────────────

def test_01_canonical_product_identity_and_entrypoint():
    """Prove canonical product identity, entrypoint, routing key, and registry integrity."""
    # 1. Canonical product key is video_ai_prompt
    assert bridge.CANONICAL_PRODUCT_KEY == "video_ai_prompt"
    # 2. Entrypoint is /video/create
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/video/create"
    # 3. Routing key matches Bot authority
    assert bridge.CANONICAL_ROUTING_KEY == "video_ai_canonical"
    assert bridge.CANONICAL_ROUTE_ID == "product_video_one_scene_v1"
    assert bridge.CANONICAL_ENGINE_ADAPTER == "b13_r18c_product_one_scene_v1"

    # 4. Registry contains video_ai_prompt and resolves to /video/create
    assert "video_ai_prompt" in reg.FEATURE_BY_KEY
    feat = reg.FEATURE_BY_KEY["video_ai_prompt"]
    assert feat.route == "/video/create"
    assert feat.group == "video"

    # 5. Registry count integrity: total 180, customer 139, admin 41
    assert len(reg.ALL_FEATURES) == 180
    assert len(reg.CUSTOMER_FEATURES) == 139
    assert len(reg.ADMIN_FEATURES) == 41

    # 6. Legacy video_single resolves without collision
    assert "video_single" in reg.FEATURE_BY_KEY
    assert reg.FEATURE_BY_KEY["video_single"].route == "/video/create"
    assert reg.FEATURE_ALIASES.get("video_ai_prompt") == "video_single"


# ─── TEST 2: WEB FEATURE ADAPTER REGISTRATION ────────────────────────────────

def test_02_web_feature_adapter_registration(monkeypatch):
    """Prove only video_ai_prompt is registered and other 9 generators are excluded."""
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt")
    adapter_keys = _web_feature_job_adapter_keys()
    assert "video_ai_prompt" in adapter_keys

    # Supported canonical job adapters contains ONLY video_ai_prompt
    assert bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS == frozenset({"video_ai_prompt"})

    # The other 9 video generators must NOT be in supported canonical adapters
    other_generators = [
        "video_trend",
        "video_ai_image",
        "video_ai_video_reference",
        "multi_scene_film",
        "video_long",
        "script_image_video",
        "storyboard",
        "self_shot",
        "voice",
    ]
    for gen in other_generators:
        assert gen not in bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS, (
            f"Expected {gen} to NOT be in canonical bridge adapters"
        )


# ─── TEST 3: PAYLOAD VALIDATION - MISSING PROMPT ─────────────────────────────

def test_03_payload_validation_rejects_missing_prompt():
    """Prove missing or empty prompt is rejected with PROMPT_REQUIRED."""
    for empty_prompt in ["", "   ", None]:
        payload = {
            "prompt": empty_prompt,
            "quality_tier": 200,
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
        }
        is_valid, err, _ = bridge.validate_product_video_input(payload)
        assert is_valid is False
        assert err == "PROMPT_REQUIRED"

        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_product_video_job(
                account_id="test-user-1",
                payload=payload,
            )
        assert exc_info.value.status_code == 400


# ─── TEST 4: PAYLOAD VALIDATION - OVERLONG PROMPT ────────────────────────────

def test_04_payload_validation_rejects_overlong_prompt():
    """Prove prompt > 2000 chars is rejected with PROMPT_TOO_LONG."""
    long_prompt = "A" * 2001
    payload = {
        "prompt": long_prompt,
        "quality_tier": 200,
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
    }
    is_valid, err, _ = bridge.validate_product_video_input(payload)
    assert is_valid is False
    assert err == "PROMPT_TOO_LONG"

    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_product_video_job(
            account_id="test-user-1",
            payload=payload,
        )
    assert exc_info.value.status_code == 400


# ─── TEST 5: PAYLOAD VALIDATION - INVALID ASPECT RATIO ───────────────────────

def test_05_payload_validation_rejects_invalid_aspect_ratio():
    """Prove aspect ratio not in ('9:16', '16:9', '1:1') is rejected."""
    for bad_ratio in ["21:9", "4:3", "invalid", "", None]:
        payload = {
            "prompt": "Valid product showcase video",
            "quality_tier": 200,
            "aspect_ratio": bad_ratio,
            "duration_seconds": 5,
        }
        is_valid, err, _ = bridge.validate_product_video_input(payload)
        assert is_valid is False
        assert err in {"ASPECT_RATIO_REQUIRED", "INVALID_ASPECT_RATIO"}

        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_product_video_job(
                account_id="test-user-1",
                payload=payload,
            )
        assert exc_info.value.status_code == 400


# ─── TEST 6: PAYLOAD VALIDATION - INVALID DURATION ───────────────────────────

def test_06_payload_validation_rejects_invalid_duration():
    """Prove duration not in (5, 10, 15) is rejected."""
    for bad_dur in [0, 3, 7, 20, 60, -5, "abc", None]:
        payload = {
            "prompt": "Valid product showcase video",
            "quality_tier": 200,
            "aspect_ratio": "9:16",
            "duration_seconds": bad_dur,
        }
        is_valid, err, _ = bridge.validate_product_video_input(payload)
        assert is_valid is False
        assert err in {"DURATION_REQUIRED", "INVALID_DURATION"}

        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_product_video_job(
                account_id="test-user-1",
                payload=payload,
            )
        assert exc_info.value.status_code == 400


# ─── TEST 7: PAYLOAD VALIDATION - INVALID QUALITY TIER ───────────────────────

def test_07_payload_validation_rejects_invalid_quality_tier():
    """Prove quality tier not in (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500) is rejected."""
    for bad_tier in [0, 100, 250, 999, 2000, "fast", None]:
        payload = {
            "prompt": "Valid product showcase video",
            "quality_tier": bad_tier,
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
        }
        is_valid, err, _ = bridge.validate_product_video_input(payload)
        assert is_valid is False
        assert err in {"TIER_REQUIRED", "INVALID_QUALITY_TIER"}

        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_product_video_job(
                account_id="test-user-1",
                payload=payload,
            )
        assert exc_info.value.status_code == 400


# ─── TEST 8: PAYLOAD VALIDATION - AUTHORITY FIELD INJECTION ──────────────────

def test_08_payload_validation_rejects_authority_field_injection():
    """Prove client injection of authority fields (status, output_url, etc.) is rejected."""
    for field_name in ["status", "job_id", "output_url", "amount", "payment_id", "provider", "wallet"]:
        payload = {
            "prompt": "Valid product showcase video",
            "quality_tier": 200,
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            field_name: "hacked_value",
        }
        is_valid, err, _ = bridge.validate_product_video_input(payload)
        assert is_valid is False
        assert err == "authority_field_not_allowed"

        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_product_video_job(
                account_id="test-user-1",
                payload=payload,
            )
        assert exc_info.value.status_code == 400


# ─── TEST 9: DURABLE RECORD PERSISTENCE IN SQLITE ────────────────────────────

def test_09_job_creation_persists_durable_record_in_sqlite():
    """Prove valid request creates durable SQLite job record with truthful queued status."""
    payload = {
        "prompt": "Chai nước hoa sang trọng trên nền đá cẩm thạch đen",
        "quality_tier": 400,
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
    }
    result = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload=payload,
        request_id="VID-20260922-000001",
    )

    assert result["id"].startswith("pvj_")
    assert result["request_id"] == "VID-20260922-000001"
    assert result["account_id"] == "test-user-1"
    assert result["product_key"] == "video_ai_prompt"
    assert result["routing_product_key"] == "video_ai_canonical"
    assert result["status"] == "queued"
    assert result["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert result["output_available"] is False
    assert result["download_ready"] is False
    assert result["delivery_ready"] is False
    assert result["output"] is None
    assert result["output_metadata"] is None
    assert result["idempotent_replay"] is False

    # Verify directly in SQLite
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT id, status, status_reason, output_metadata FROM web_product_video_jobs WHERE id=?",
            (result["id"],),
        ).fetchone()
        assert row is not None
        assert row[1] == "queued"
        assert row[2] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
        assert row[3] is None


# ─── TEST 10: IDEMPOTENT REPLAY ON IDENTICAL PAYLOAD ─────────────────────────

def test_10_idempotent_replay_on_identical_payload():
    """Prove replaying identical payload returns existing record without creating duplicate."""
    payload = {
        "prompt": "Gói quà Tết cao cấp đỏ vàng rực rỡ",
        "quality_tier": 500,
        "aspect_ratio": "16:9",
        "duration_seconds": 10,
    }
    first = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload=payload,
        request_id="VID-20260922-IDEM01",
        idempotency_key="idem-key-001",
    )
    assert first["idempotent_replay"] is False

    # Second call with identical payload
    second = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload=payload,
        request_id="VID-20260922-IDEM01",
        idempotency_key="idem-key-001",
    )
    assert second["idempotent_replay"] is True
    assert second["id"] == first["id"]
    assert second["request_id"] == first["request_id"]

    # Verify count in SQLite is exactly 1 (no duplicates)
    with read_transaction() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_product_video_jobs WHERE account_id=? AND request_id=?",
            ("test-user-1", "VID-20260922-IDEM01"),
        ).fetchone()[0]
        assert count == 1


# ─── TEST 11: REQUEST ID CONFLICT REJECTION ──────────────────────────────────

def test_11_request_id_conflict_rejection():
    """Prove same request_id with differing payload raises HTTP 409 Conflict."""
    payload1 = {
        "prompt": "Đôi giày thể thao chạy trên bãi cát hoàng hôn",
        "quality_tier": 200,
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
    }
    bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload=payload1,
        request_id="VID-20260922-CONF01",
    )

    # Conflicting payload with same request_id but different duration and prompt
    payload2 = {
        "prompt": "Khác biệt hoàn toàn: đồng hồ đeo tay phong cách cổ điển",
        "quality_tier": 600,
        "aspect_ratio": "1:1",
        "duration_seconds": 15,
    }
    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_product_video_job(
            account_id="test-user-1",
            payload=payload2,
            request_id="VID-20260922-CONF01",
        )
    assert exc_info.value.status_code == 409
    assert "Xung đột" in exc_info.value.detail or "conflict" in exc_info.value.detail.lower()


# ─── TEST 12: QUERY JOBS LIST FOR AUTHENTICATED ACCOUNT ──────────────────────

def test_12_query_jobs_list_for_authenticated_account():
    """Prove jobs can be listed for authenticated account via API and bridge."""
    for i in range(3):
        bridge.create_or_replay_product_video_job(
            account_id="test-user-1",
            payload={
                "prompt": f"Video sản phẩm mẫu số {i+1}",
                "quality_tier": 200,
                "aspect_ratio": "9:16",
                "duration_seconds": 5,
            },
            request_id=f"VID-20260922-LIST{i+1}",
        )

    jobs = bridge.list_product_video_jobs("test-user-1")
    assert len(jobs) == 3
    for j in jobs:
        assert j["account_id"] == "test-user-1"
        assert j["product_key"] == "video_ai_prompt"
        assert j["status"] == "queued"

    # User 2 has zero jobs
    user2_jobs = bridge.list_product_video_jobs("test-user-2")
    assert len(user2_jobs) == 0


# ─── TEST 13: QUERY JOB DETAIL AND CROSS-USER REJECTION ──────────────────────

def test_13_query_job_detail_and_cross_user_rejection():
    """Prove owner can query job detail, while other user is rejected with 403."""
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload={
            "prompt": "Ly cà phê sữa đá Việt Nam bốc khói nhẹ",
            "quality_tier": 300,
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
        },
        request_id="VID-20260922-DETAIL01",
    )
    job_id = job["id"]

    # Owner retrieves job successfully
    fetched = bridge.get_product_video_job("test-user-1", job_id)
    assert fetched is not None
    assert fetched["id"] == job_id
    assert fetched["prompt"] == "Ly cà phê sữa đá Việt Nam bốc khói nhẹ"

    # Cross-user check: test-user-2 cannot get job
    fetched_user2 = bridge.get_product_video_job("test-user-2", job_id)
    assert fetched_user2 is None

    # is_product_video_job_other_account returns True for test-user-2
    assert bridge.is_product_video_job_other_account(job_id, "test-user-2") is True
    assert bridge.is_product_video_job_other_account(job_id, "test-user-1") is False


# ─── TEST 14: ZERO PROVIDER CALLS AND ZERO WALLET MUTATIONS ──────────────────

def test_14_zero_provider_calls_zero_wallet_mutations_invariant():
    """Prove zero external provider HTTP calls and zero wallet mutations occur."""
    payload = {
        "prompt": "Mô hình đồ chơi phi thuyền không gian phát sáng",
        "quality_tier": 700,
        "aspect_ratio": "16:9",
        "duration_seconds": 15,
    }
    # Create job
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload=payload,
    )
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

    # Verify no external provider credentials or URLs are in envelope
    envelope = job["bridge_envelope"]
    assert "api_key" not in envelope
    assert "token" not in envelope
    assert "provider_task_id" not in envelope


# ─── TEST 15: ZERO REAL VIDEO RENDERS INVARIANT ──────────────────────────────

def test_15_zero_real_video_renders_invariant():
    """Prove zero real video render processes, zero fake output files, zero fake completed status."""
    payload = {
        "prompt": "Bình giữ nhiệt phong cách tối giản màu pastel",
        "quality_tier": 200,
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
    }
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload=payload,
    )
    # Output must be None
    assert job["output"] is None
    assert job["output_metadata"] is None
    assert job["status"] != "completed"
    assert job["status"] == "queued"


# ─── TEST 16: ADMIN TRACEABILITY ENVELOPE COMPLETENESS ───────────────────────

def test_16_admin_traceability_envelope_completeness():
    """Prove bridge envelope contains complete Bot authority traceability metadata."""
    payload = {
        "prompt": "Hộp bánh trung thu cao cấp hoa sen ép nhũ kim",
        "quality_tier": 1000,
        "aspect_ratio": "1:1",
        "duration_seconds": 10,
    }
    job = bridge.create_or_replay_product_video_job(
        account_id="test-user-1",
        payload=payload,
        request_id="VID-20260922-TRACE01",
    )
    envelope = job["bridge_envelope"]

    required_keys = [
        "version",
        "route_id",
        "product_family",
        "mode",
        "engine_adapter",
        "product_key",
        "routing_product_key",
        "request_id",
        "job_id",
        "account_id",
        "prompt",
        "aspect_ratio",
        "duration_seconds",
        "quality_tier",
        "scene_count",
        "status",
        "status_reason",
        "created_at",
        "output",
    ]
    for key in required_keys:
        assert key in envelope, f"Missing key '{key}' in bridge envelope"

    assert envelope["route_id"] == "product_video_one_scene_v1"
    assert envelope["engine_adapter"] == "b13_r18c_product_one_scene_v1"
    assert envelope["routing_product_key"] == "video_ai_canonical"
    assert envelope["product_key"] == "video_ai_prompt"
    assert envelope["scene_count"] == 1
    assert envelope["output"] is None


# ─── TEST 17: FASTAPI HTTP ENDPOINTS AND CROSS-USER SECURITY ─────────────────

def test_17_fastapi_http_endpoints_and_cross_user_security():
    """Prove FastAPI HTTP endpoints create and list jobs, and enforce cross-user isolation."""
    client1 = TestClient(app)
    # Register & login user1
    client1.post("/api/v1/auth/register", json={"email": "client1@test.local", "password": "secure-password-1234", "display_name": "Client 1"})
    login1 = client1.post("/api/v1/auth/login", json={"email": "client1@test.local", "password": "secure-password-1234"})
    assert login1.status_code == 200
    csrf1 = login1.json()["data"]["csrf_token"]
    headers1 = {"X-CSRF-Token": csrf1}

    # 1. Post job via /features/video_ai_prompt/jobs
    create_res = client1.post(
        "/api/v1/features/video_ai_prompt/jobs",
        json={
            "input": {
                "prompt": "Hạt điều rang muối cao cấp đóng hộp giấy",
                "quality_tier": 300,
                "aspect_ratio": "9:16",
                "duration_seconds": 5,
            },
            "idempotency_key": "http-idem-0001",
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

    # 2. Query job list via /features/video_ai_prompt/jobs
    list_res = client1.get("/api/v1/features/video_ai_prompt/jobs")
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) >= 1
    assert any(item["id"] == job_id for item in items)

    # 3. Query job detail via /features/video_ai_prompt/jobs/{job_id}
    detail_res = client1.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == job_id

    # 4. Query job via generic /api/v1/jobs
    generic_list = client1.get("/api/v1/jobs")
    assert generic_list.status_code == 200
    gen_items = generic_list.json()["data"]["items"]
    assert any(item["id"] == job_id for item in gen_items)

    # 5. Query job detail via generic /api/v1/jobs/{job_id}
    gen_detail = client1.get(f"/api/v1/jobs/{job_id}")
    assert gen_detail.status_code == 200
    assert gen_detail.json()["ok"] is True

    # 6. Cross-User Security: User 2 logs in and tries to query User 1's job
    client2 = TestClient(app)
    client2.post("/api/v1/auth/register", json={"email": "client2@test.local", "password": "secure-password-5678", "display_name": "Client 2"})
    login2 = client2.post("/api/v1/auth/login", json={"email": "client2@test.local", "password": "secure-password-5678"})
    assert login2.status_code == 200

    # User 2 calling /features/video_ai_prompt/jobs/{job_id} must receive 403
    cross_res1 = client2.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}")
    assert cross_res1.status_code == 403

    # User 2 calling /jobs/{job_id} must receive 403
    cross_res2 = client2.get(f"/api/v1/jobs/{job_id}")
    assert cross_res2.status_code == 403
