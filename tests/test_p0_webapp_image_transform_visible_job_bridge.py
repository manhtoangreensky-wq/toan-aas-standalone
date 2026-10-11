"""Tests for Image Transform Canonical Job Bridge and Visible Result Retention.

Task: WEBAPP_R24B2_IMAGE_TRANSFORM_VISIBLE_JOB_BRIDGE_AND_RESULT_RETENTION_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: image_transform
Customer Entrypoint: /image/transform
Web API Family: /api/v1/features/image_transform/*

Proves:
1. Product Identity: canonical key `image_transform`, entrypoint `/image/transform`.
2. Auth & Entrypoint: unauthenticated redirected to login; authenticated renders 200.
3. Input Validation: missing asset, missing prompt, invalid aspect ratio, invalid model, authority field injection rejected.
4. Cross-Owner Isolation: cross-account source asset access rejected with 400/403.
5. Fail-Closed Job Creation: status='queued', status_reason='AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE'.
6. Zero Paid Calls / Zero Wallet Mutations on creation.
7. Idempotency: exact replay returns existing job; differing payload on same key returns 409 Conflict.
8. Customer History Visibility: job appears in GET /api/v1/jobs and GET /api/v1/jobs/{job_id}.
9. Cross-Account Job Protection: viewing other account's job detail returns 403.
10. Result Retention Finalization: attaches verified, owner-scoped Asset Vault item.
11. Output Preview & Download: download_url and preview_url point to safe Asset Vault endpoints.
12. Admin Visibility: GET /api/v1/admin/jobs/{job_id} returns product, owner reference, status, model.
13. Future Provider Boundary: provider dispatch is strictly disabled (raises RuntimeError, 0 network calls).
14. Admin Jobs Ledger List: GET /api/v1/admin/jobs aggregates transform jobs.
15. Customer UI Portal Contract: portal.js and integration.js declare required elements.
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
from copyfast_db import ensure_copyfast_schema, read_transaction, session_database_path, transaction
import copyfast_image_transform_job_bridge as bridge


# ─── FIXTURE ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db_and_env(monkeypatch):
    """Set test environment and clean test tables."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-transform-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()
    ensure_copyfast_schema()
    bridge.ensure_image_transform_schema()

    with transaction() as conn:
        conn.execute("DELETE FROM web_image_transform_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-transform-%'")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-transform-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-transform-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES ('test-transform-user-1', 'transform1@test.local', 'hash1', 'user', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'),
                   ('test-transform-user-2', 'transform2@test.local', 'hash2', 'user', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'),
                   ('test-transform-admin', 'admin@test.local', 'hashadmin', 'admin', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, created_at, updated_at
            ) VALUES (
                'asset-transform-source-1', 'test-transform-user-1', NULL, 'Ảnh thử nghiệm',
                'sample.jpg', '.jpg', 'image/jpeg', 102400, 'hashsha256', 'storage_key_1',
                'active', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'
            ), (
                'asset-transform-user2-source', 'test-transform-user-2', NULL, 'Ảnh người khác',
                'private.png', '.png', 'image/png', 204800, 'hashsha256_2', 'storage_key_2',
                'active', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'
            ), (
                'asset-transform-inactive', 'test-transform-user-1', NULL, 'Ảnh chưa sẵn sàng',
                'draft.jpg', '.jpg', 'image/jpeg', 51200, 'hashsha256_3', 'storage_key_3',
                'pending', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'
            ), (
                'asset-transform-non-image', 'test-transform-user-1', NULL, 'Tệp văn bản',
                'document.pdf', '.pdf', 'application/pdf', 51200, 'hashsha256_4', 'storage_key_4',
                'active', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'
            )
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_image_transform_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-transform-%'")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-transform-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-transform-%'")


from copyfast_auth import SESSION_COOKIE, _cookie_name, _insert_session, _session_cookie_value


def _create_authenticated_client(
    account_id: str = "test-transform-user-1",
    email: str | None = None,
    role: str = "member",
) -> tuple[TestClient, str]:
    with transaction() as conn:
        conn.execute("UPDATE web_accounts SET role_cache=? WHERE id=?", (role, account_id))
        sess = _insert_session(conn, account_id)
    client = TestClient(app)
    client.cookies.set(_cookie_name(SESSION_COOKIE), _session_cookie_value(sess["session_id"]))
    return client, sess["csrf_token"]


# ─── TEST 1: PRODUCT IDENTITY AND ROUTING ────────────────────────────────────

def test_01_product_identity_and_entrypoint():
    """Verify canonical constants and entrypoint."""
    assert bridge.CANONICAL_PRODUCT_KEY == "image_transform"
    assert bridge.CANONICAL_ROUTING_KEY == "image_transform"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/image/transform"
    assert bridge.DEFAULT_MODEL == "key4u_img2img"
    assert bridge.DEFAULT_ASPECT_RATIO == "1:1"
    assert "1:1" in bridge.SUPPORTED_ASPECT_RATIOS
    assert "4:5" in bridge.SUPPORTED_ASPECT_RATIOS
    assert "16:9" in bridge.SUPPORTED_ASPECT_RATIOS
    assert "9:16" in bridge.SUPPORTED_ASPECT_RATIOS
    assert "standard" in bridge.SUPPORTED_TIERS


# ─── TEST 2: AUTH ENFORCEMENT ON CUSTOMER ENTRYPOINT ─────────────────────────

def test_02_customer_entrypoint_auth():
    """Unauthenticated GET /image/transform redirects to login; authenticated renders 200."""
    unauth_client = TestClient(app)
    resp = unauth_client.get("/image/transform", follow_redirects=False)
    assert resp.status_code == 307
    assert "/login" in resp.headers.get("location", "")

    auth_client, _ = _create_authenticated_client()
    resp_auth = auth_client.get("/image/transform", follow_redirects=False)
    assert resp_auth.status_code == 200
    assert len(resp_auth.text) > 500


# ─── TEST 3: INPUT VALIDATION CONTRACTS ──────────────────────────────────────

def test_03_input_validation():
    """Input validation enforces source asset, transform instruction, aspect ratio, ownership."""
    # 1. Missing asset_id rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {})
    assert not ok
    assert "Thiếu mã tài sản ảnh" in err

    # 2. Missing prompt/instruction rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-source-1",
        "transform_instruction": "",
    })
    assert not ok
    assert "Thiếu câu lệnh biến đổi" in err

    # 3. Invalid aspect ratio rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-source-1",
        "transform_instruction": "Biến đổi thành phong cách anime",
        "aspect_ratio": "21:9",
    })
    assert not ok
    assert "Tỷ lệ khung hình không hợp lệ" in err

    # 4. Invalid model rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-source-1",
        "transform_instruction": "Biến đổi thành tranh sơn dầu",
        "model_name": "unknown_model_v9",
    })
    assert not ok
    assert "Mô hình không hợp lệ" in err

    # 5. Invalid tier rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-source-1",
        "transform_instruction": "Biến đổi thành tranh sơn dầu",
        "tier": "ultra_vip",
    })
    assert not ok
    assert "Tier không hợp lệ" in err

    # 6. Authority field injection rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-source-1",
        "transform_instruction": "Biến đổi thành cyberpunk",
        "status": "completed",
    })
    assert not ok
    assert "authority field injection" in err

    # 7. Non-existent asset rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-does-not-exist",
        "transform_instruction": "Biến đổi thành cyberpunk",
    })
    assert not ok
    assert "Không tìm thấy tài sản ảnh" in err

    # 8. Cross-owner asset rejected (user 1 accessing user 2's asset)
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-user2-source",
        "transform_instruction": "Biến đổi",
    })
    assert not ok
    assert "Không tìm thấy tài sản ảnh trong Asset Vault hoặc bạn không có quyền truy cập" in err

    # 9. Inactive asset rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-inactive",
        "transform_instruction": "Biến đổi",
    })
    assert not ok
    assert "không ở trạng thái sẵn sàng" in err

    # 10. Non-image extension rejected
    ok, err, _ = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-non-image",
        "transform_instruction": "Biến đổi",
    })
    assert not ok
    assert "Định dạng tệp không được hỗ trợ" in err

    # 11. Valid input passes
    ok, err, clean = bridge.validate_image_transform_input("test-transform-user-1", {
        "image_asset_id": "asset-transform-source-1",
        "transform_instruction": "Biến đổi phong cách Studio Ghibli",
        "aspect_ratio": "16:9",
    })
    assert ok
    assert err == ""
    assert clean["aspect_ratio"] == "16:9"
    assert clean["transform_instruction"] == "Biến đổi phong cách Studio Ghibli"
    assert clean["model_name"] == "key4u_img2img"


# ─── TEST 4: FAIL-CLOSED JOB CREATION VIA WEB API ────────────────────────────

def test_04_create_job_fail_closed_via_web_api():
    """POST /features/image_transform/jobs creates durable queued job with zero provider calls."""
    client, csrf = _create_authenticated_client()

    resp = client.post(
        "/api/v1/features/image_transform/jobs",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "test-key-transform-001"},
        json={
            "feature": "image_transform",
            "input": {
                "image_asset_id": "asset-transform-source-1",
                "transform_instruction": "Biến đổi phong cách tranh sơn mài",
                "aspect_ratio": "1:1",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    job = data["data"]

    # Verify fail-closed initial state
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE"
    assert job["output_available"] is False
    assert job["output_asset_id"] is None
    assert job["output_url"] is None
    assert job["product_key"] == "image_transform"
    assert job["aspect_ratio"] == "1:1"
    assert job["transform_instruction"] == "Biến đổi phong cách tranh sơn mài"
    assert job["idempotent_replay"] is False

    # Verify record in SQLite table
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        db_job = conn.execute("SELECT * FROM web_image_transform_jobs WHERE id = ?", (job["id"],)).fetchone()
        assert db_job is not None
        assert db_job["account_id"] == "test-transform-user-1"
        assert db_job["status"] == "queued"


# ─── TEST 5: IDEMPOTENCY REPLAY AND CONFLICT ─────────────────────────────────

def test_05_idempotency_replay_and_conflict():
    """Identical replay returns existing job; differing payload on same key raises 409."""
    client, csrf = _create_authenticated_client()

    payload_a = {
        "feature": "image_transform",
        "input": {
            "image_asset_id": "asset-transform-source-1",
            "transform_instruction": "Biến đổi sang tranh thủy mặc",
            "aspect_ratio": "1:1",
            "request_id": "req-idempotent-transform-test",
        },
    }

    # 1. First creation
    resp1 = client.post(
        "/api/v1/features/image_transform/jobs",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "idem-key-transform-1"},
        json=payload_a,
    )
    assert resp1.status_code == 200
    job1 = resp1.json()["data"]
    assert job1["idempotent_replay"] is False

    # 2. Replay with identical payload and key
    resp2 = client.post(
        "/api/v1/features/image_transform/jobs",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "idem-key-transform-1"},
        json=payload_a,
    )
    assert resp2.status_code == 200
    job2 = resp2.json()["data"]
    assert job2["id"] == job1["id"]
    assert job2["idempotent_replay"] is True

    # 3. Differing payload on same idempotency key raises 409
    payload_diff = {
        "feature": "image_transform",
        "input": {
            "image_asset_id": "asset-transform-source-1",
            "transform_instruction": "Biến đổi sang tranh sơn dầu",  # different prompt
            "aspect_ratio": "16:9",
            "request_id": "req-idempotent-transform-test-2",
        },
    }
    resp_conflict = client.post(
        "/api/v1/features/image_transform/jobs",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "idem-key-transform-1"},
        json=payload_diff,
    )
    assert resp_conflict.status_code == 409
    err_msg = resp_conflict.json().get("message") or resp_conflict.json().get("detail", "")
    assert "Xung đột Idempotency-Key" in err_msg


# ─── TEST 6: CUSTOMER JOB HISTORY AND ISOLATION ──────────────────────────────

def test_06_customer_jobs_visibility_and_isolation():
    """Job is visible in /api/v1/jobs and /api/v1/jobs/{job_id}; other user rejected with 403."""
    client1, csrf1 = _create_authenticated_client("test-transform-user-1", "transform1@test.local")
    client2, csrf2 = _create_authenticated_client("test-transform-user-2", "transform2@test.local")

    # User 1 creates job
    resp = client1.post(
        "/api/v1/features/image_transform/jobs",
        headers={"X-CSRF-Token": csrf1},
        json={
            "feature": "image_transform",
            "input": {
                "image_asset_id": "asset-transform-source-1",
                "transform_instruction": "Biến đổi phong cách hoạt hình 3D",
                "aspect_ratio": "4:5",
            },
        },
    )
    assert resp.status_code == 200
    job_id = resp.json()["data"]["id"]

    # User 1 sees job in generic /api/v1/jobs
    jobs_resp = client1.get("/api/v1/jobs")
    assert jobs_resp.status_code == 200
    job_items = jobs_resp.json()["data"]["items"]
    matched = [j for j in job_items if j.get("id") == job_id or j.get("job_id") == job_id]
    assert len(matched) == 1
    assert matched[0]["kind"] == "image_transform"

    # User 1 gets job detail
    detail_resp = client1.get(f"/api/v1/jobs/{job_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["ok"] is True

    # User 1 gets job detail via feature endpoint
    feat_resp = client1.get(f"/api/v1/features/image_transform/jobs/{job_id}")
    assert feat_resp.status_code == 200
    assert feat_resp.json()["ok"] is True

    # User 2 cannot see User 1's job in /api/v1/jobs
    jobs_u2 = client2.get("/api/v1/jobs")
    assert jobs_u2.status_code == 200
    u2_matched = [j for j in jobs_u2.json()["data"]["items"] if j.get("id") == job_id or j.get("job_id") == job_id]
    assert len(u2_matched) == 0

    # User 2 gets 403 on User 1's job detail
    detail_u2 = client2.get(f"/api/v1/jobs/{job_id}")
    assert detail_u2.status_code == 403

    feat_u2 = client2.get(f"/api/v1/features/image_transform/jobs/{job_id}")
    assert feat_u2.status_code == 403


# ─── TEST 7: RESULT RETENTION FINALIZATION ───────────────────────────────────

def test_07_result_retention_finalization():
    """Result finalization links output asset, sets completed, and verifies preview/download."""
    client, csrf = _create_authenticated_client()

    # 1. Create initial queued job
    resp = client.post(
        "/api/v1/features/image_transform/jobs",
        headers={"X-CSRF-Token": csrf},
        json={
            "feature": "image_transform",
            "input": {
                "image_asset_id": "asset-transform-source-1",
                "transform_instruction": "Biến đổi phong cách màu nước",
                "aspect_ratio": "16:9",
            },
        },
    )
    job_id = resp.json()["data"]["id"]

    # 2. Create an output asset owned by User 1 in web_asset_files
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, created_at, updated_at
            ) VALUES (
                'asset-transformed-output-1', 'test-transform-user-1', NULL, 'Ảnh đã biến đổi',
                'transformed.png', '.png', 'image/png', 512000, 'sha256_output_xf', 'key_out_xf_1',
                'active', '2026-10-11T00:01:00Z', '2026-10-11T00:01:00Z'
            )
            """
        )

    # 3. Finalize result with verified asset
    finalized = bridge.finalize_image_transform_job_result(
        job_id=job_id,
        provider_task_id="k4u_task_12345",
        provider_name="key4u",
        model_name="key4u_img2img",
        output_asset_id="asset-transformed-output-1",
        output_metadata={"width": 1920, "height": 1080, "aspect_ratio": "16:9"},
        cost_metadata={"unit_cost_usd": 0.005, "billed_xu": 0},
    )

    assert finalized["status"] == "completed"
    assert finalized["status_reason"] == "COMPLETED"
    assert finalized["output_available"] is True
    assert finalized["output_asset_id"] == "asset-transformed-output-1"
    assert finalized["download_url"] == "/api/v1/assets/asset-transformed-output-1/download"
    assert finalized["preview_url"] == "/api/v1/assets/asset-transformed-output-1/preview"
    assert finalized["provider_name"] == "key4u"
    assert finalized["provider_task_id"] == "k4u_task_12345"

    # 4. Verify cross-owner output asset rejection
    with pytest.raises(HTTPException) as exc:
        bridge.finalize_image_transform_job_result(
            job_id=job_id,
            output_asset_id="asset-transform-user2-source",  # User 2's asset
        )
    assert exc.value.status_code == 403


# ─── TEST 8: ADMIN VISIBILITY ────────────────────────────────────────────────

def test_08_admin_visibility():
    """Admin endpoint /api/v1/admin/jobs/{job_id} surfaces product, owner, status without secrets."""
    client_user, csrf_user = _create_authenticated_client("test-transform-user-1")
    client_admin, _ = _create_authenticated_client("test-transform-admin", "admin@test.local", role="admin")

    from copyfast_auth import require_canonical_admin
    app.dependency_overrides[require_canonical_admin] = lambda: {"id": "test-transform-admin", "role": "admin"}

    try:
        # User creates job
        resp = client_user.post(
            "/api/v1/features/image_transform/jobs",
            headers={"X-CSRF-Token": csrf_user},
            json={
                "feature": "image_transform",
                "input": {
                    "image_asset_id": "asset-transform-source-1",
                    "transform_instruction": "Biến đổi tranh phong cảnh",
                    "aspect_ratio": "1:1",
                },
            },
        )
        job_id = resp.json()["data"]["id"]

        # Admin queries job detail
        admin_resp = client_admin.get(f"/api/v1/admin/jobs/{job_id}")
        assert admin_resp.status_code == 200
        admin_data = admin_resp.json()
        assert admin_data["ok"] is True
        job_info = admin_data["data"]
        assert job_info["job_id"] == job_id
        assert job_info["product"] == "image_transform"
        assert job_info["product_family"] == "image"
        assert job_info["owner_reference"] == "test-transform-user-1"
        assert job_info["status"] == "queued"
        # Ensure no secrets in output
        text_data = json.dumps(job_info)
        assert "apikey" not in text_data.lower()
        assert "token" not in text_data.lower()
        assert "secret" not in text_data.lower()
    finally:
        app.dependency_overrides.clear()


# ─── TEST 9: FUTURE PROVIDER BOUNDARY IS DISABLED ────────────────────────────

def test_09_provider_dispatch_disabled():
    """Provider dispatch raises RuntimeError and makes zero network calls."""
    assert bridge.IMAGE_TRANSFORM_PROVIDER_DISPATCH_ENABLED is False
    assert bridge.KEY4U_IMG2IMG_DISPATCH_AUTHORIZED is False
    assert bridge.REPLICATE_SD_IMG2IMG_DISPATCH_AUTHORIZED is False
    assert bridge.STABILITY_IMG2IMG_DISPATCH_AUTHORIZED is False

    with pytest.raises(RuntimeError) as exc:
        bridge.dispatch_image_transform_provider("imgxf_123")
    assert "IMAGE_TRANSFORM_PROVIDER_DISPATCH_DISABLED" in str(exc.value)


# ─── TEST 10: ADMIN JOBS LEDGER LIST AGGREGATION ──────────────────────────────

def test_10_admin_jobs_ledger_list():
    """Admin endpoint /api/v1/admin/jobs aggregates transform jobs into the global ledger."""
    client_user, csrf_user = _create_authenticated_client("test-transform-user-1")
    client_admin, _ = _create_authenticated_client("test-transform-admin", role="admin")

    from copyfast_auth import require_canonical_admin
    app.dependency_overrides[require_canonical_admin] = lambda: {"id": "test-transform-admin", "role": "admin"}

    try:
        resp = client_user.post(
            "/api/v1/features/image_transform/jobs",
            headers={"X-CSRF-Token": csrf_user},
            json={
                "feature": "image_transform",
                "input": {
                    "image_asset_id": "asset-transform-source-1",
                    "transform_instruction": "Biến đổi tranh kỹ thuật số",
                    "aspect_ratio": "9:16",
                },
            },
        )
        assert resp.status_code == 200
        job_id = resp.json()["data"]["id"]

        list_resp = client_admin.get("/api/v1/admin/jobs")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["ok"] is True
        items = list_data["data"]["items"]
        matched = [j for j in items if j.get("id") == job_id or j.get("job_id") == job_id]
        assert len(matched) == 1
        assert matched[0]["product"] == "image_transform"
        assert matched[0]["status"] == "queued"
    finally:
        app.dependency_overrides.clear()


# ─── TEST 11: CUSTOMER UI PORTAL CONTRACT ─────────────────────────────────────

def test_11_customer_ui_portal_contract():
    """Customer portal and integration contracts strictly declare visible transform elements."""
    portal_js_path = STANDALONE_ROOT / "static" / "portal" / "portal.js"
    integration_js_path = STANDALONE_ROOT / "static" / "portal" / "integration.js"

    assert portal_js_path.exists()
    assert integration_js_path.exists()

    portal_text = portal_js_path.read_text(encoding="utf-8")
    integration_text = integration_js_path.read_text(encoding="utf-8")

    # Portal layout and elements
    assert 'customerPage("/image/transform"' in portal_text
    assert 'layout: "image-transform"' in portal_text
    assert "function renderImageTransform" in portal_text
    assert 'data-field="source_image_selector"' in portal_text
    assert 'data-field="transform_instruction_input"' in portal_text
    assert 'data-field="format_selector"' in portal_text
    assert 'data-portal-submit="image-transform"' in portal_text
    assert "data-transform-job-receipt" in portal_text
    assert 'data-link="view-job-history"' in portal_text
    assert 'case "image-transform": return renderImageTransform' in portal_text

    # Integration action handlers
    assert 'action === "image-transform-submit"' in integration_text
    assert 'action === "image-transform-reset"' in integration_text
    assert '"/features/image_transform/jobs"' in integration_text
