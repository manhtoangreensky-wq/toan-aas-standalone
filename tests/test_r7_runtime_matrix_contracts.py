"""Tests for R7 Final Residual Engine and Root Gap Closure runtime matrix contracts."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import app
from copyfast_api import WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
from copyfast_db import ensure_copyfast_schema, transaction
import copyfast_image_remove_background_bridge as bg_bridge

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "webapp_full_product_truth"
MATRIX_FILE = REPORT_DIR / "R7_FINAL_ROUTE_RUNTIME_MATRIX.json"
PROVENANCE_FILE = REPORT_DIR / "00_data_provenance.json"
DEFECTS_FILE = REPORT_DIR / "defects.json"


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret-r7-matrix")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_image_remove_background_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-r7-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r7-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('test-r7-user-1', 'user1@test.local', 'hash1', '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z'),
                   ('test-r7-user-2', 'user2@test.local', 'hash2', '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, lifecycle_revision, created_at, updated_at
            ) VALUES (
                'test-r7-asset-img-1', 'test-r7-user-1', NULL, 'photo.png', 'photo.png',
                '.png', 'image/png', 1024, 'aabbcc112233', 'storage-key-img-1',
                'active', 1, '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z'
            ), (
                'test-r7-asset-doc-1', 'test-r7-user-1', NULL, 'manual.pdf', 'manual.pdf',
                '.pdf', 'application/pdf', 2048, 'ddeeff445566', 'storage-key-doc-1',
                'active', 1, '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z'
            )
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_image_remove_background_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-r7-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r7-%'")


# ─── TEST 1: MATRIX SUMMARY & TOTAL INTEGRITY ─────────────────────────────────

def test_r7_matrix_summary_and_surface_counts() -> None:
    assert MATRIX_FILE.exists(), "R7_FINAL_ROUTE_RUNTIME_MATRIX.json must exist"
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    routes = data["routes"]

    assert summary["BATCH"] == "WEBAPP_R7_FINAL_RESIDUAL_ENGINE_AND_ROOT_GAP_CLOSURE_MASTER_BATCH_R1"
    assert summary["TOTAL_SURFACES"] == 221
    assert len(routes) == 221
    assert summary["UNCLASSIFIED_ROUTE_COUNT"] == 0
    assert summary["UNKNOWN_RUNTIME_OWNER_COUNT"] == 0
    assert summary["UNKNOWN_DATA_OWNER_COUNT"] == 0
    assert summary["STALE_PROVENANCE_SHA_COUNT"] == 0

    assert summary["R4_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 18
    assert summary["R5_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 13
    assert summary["R6_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 2
    assert summary["R7_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 0

    assert summary["R7_ACTIVE_CANONICAL_PROMOTED_COUNT"] == 3
    assert summary["R7_FALSE_BLOCK_ELIMINATED_COUNT"] == 4
    assert summary["R7_OUTPUT_DELIVERY_GAP_ELIMINATED_COUNT"] == 1

    assert summary["WEB_BRIDGE_NOT_MOUNTED_COUNT"] == 0
    assert summary["BOT_ADAPTER_EXISTS_NOT_EXPOSED_TO_WEB_COUNT"] == 0
    assert summary["WORKER_CONSUMER_EXISTS_NOT_ACTIVATED_COUNT"] == 0
    assert summary["FALSE_BLOCK_WEB_NATIVE_RUNTIME_ALREADY_EXISTS_COUNT"] == 0
    assert summary["OUTPUT_DELIVERY_GAP_COUNT"] == 0
    assert summary["EXTERNAL_PROVIDER_CAPABILITY_MISSING_COUNT"] == 4

    class_counts = summary["CLASSIFICATION_COUNTS"]
    assert class_counts["RELEASED_ACTIVE_CANONICAL_RUNTIME"] == 22
    assert class_counts["RELEASED_WEB_NATIVE_RUNTIME"] == 112
    assert class_counts["RELEASED_READ_ONLY_CANONICAL_COMPANION"] == 19
    assert class_counts["ADMIN_INTERNAL_ONLY"] == 48
    assert class_counts["NOT_A_PRODUCT_ACTION_INFORMATIONAL_ONLY"] == 16
    assert class_counts["BLOCKED_EXTERNAL_CAPABILITY_OR_GRANT_REQUIRED"] == 4
    assert class_counts.get("BLOCKED_CANONICAL_BACKEND_MISSING", 0) == 0

    root_gap_counts = summary["ROOT_GAP_COUNTS"]
    assert root_gap_counts["NONE_RELEASED_RUNTIME"] == 153
    assert root_gap_counts["ADMIN_INTERNAL_BOUNDARY"] == 48
    assert root_gap_counts["NOT_APPLICABLE_INFORMATIONAL"] == 16
    assert root_gap_counts["EXTERNAL_PROVIDER_CAPABILITY_MISSING"] == 4


# ─── TEST 2: ALL 12 RESIDUAL ROUTES EXACT DISPOSITIONS ────────────────────────

def test_r7_all_12_residual_routes_exact_dispositions() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    routes_by_path = {r["route"]: r for r in data["routes"]}

    # 1-4. Four False-Block residues normalized to RELEASED_WEB_NATIVE_RUNTIME
    for p in ("/video/poster", "/video/frame-sequence", "/video/finishing", "/video/add-ons"):
        r = routes_by_path[p]
        assert r["final_classification"] == "RELEASED_WEB_NATIVE_RUNTIME", f"Route {p} classification"
        assert r["actual_root_gap"] == "NONE_RELEASED_RUNTIME", f"Route {p} root gap"
        assert r["runtime_execution_enabled"] is True
        assert r["local_web_native_engine_exists"] is True

    # 5. /video/export -> Normalized to RELEASED_READ_ONLY_CANONICAL_COMPANION with gap eliminated
    exp = routes_by_path["/video/export"]
    assert exp["final_classification"] == "RELEASED_READ_ONLY_CANONICAL_COMPANION"
    assert exp["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert exp["canonical_output_delivery_exists"] is True
    assert exp["runtime_execution_enabled"] is True

    # 6. /video/long -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    vlong = routes_by_path["/video/long"]
    assert vlong["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert vlong["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert vlong["canonical_worker_consumer_exists"] is True
    assert vlong["runtime_execution_enabled"] is True
    assert vlong["web_to_bot_bridge_mounted"] is True

    # 7. /video/multiscene -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    vmsc = routes_by_path["/video/multiscene"]
    assert vmsc["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert vmsc["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert vmsc["canonical_worker_consumer_exists"] is True
    assert vmsc["runtime_execution_enabled"] is True
    assert vmsc["web_to_bot_bridge_mounted"] is True

    # 8. /image/remove-background -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    rmbg = routes_by_path["/image/remove-background"]
    assert rmbg["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert rmbg["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert rmbg["canonical_bot_engine_exists"] is True
    assert rmbg["runtime_execution_enabled"] is True
    assert rmbg["web_to_bot_bridge_mounted"] is True

    # 9-12. Four genuine external capability blocks proven
    for p in ("/voice/clone", "/music/sfx", "/image/upscale", "/image/transform"):
        r = routes_by_path[p]
        assert r["final_classification"] == "BLOCKED_EXTERNAL_CAPABILITY_OR_GRANT_REQUIRED", f"Route {p} classification"
        assert r["actual_root_gap"] == "EXTERNAL_PROVIDER_CAPABILITY_MISSING", f"Route {p} root gap"
        assert r["runtime_execution_enabled"] is False


# ─── TEST 3: IMAGE REMOVE BACKGROUND BRIDGE CONTRACTS ─────────────────────────

def test_r7_image_remove_background_bridge_contracts() -> None:
    # 1. Authority field injection rejected
    with pytest.raises(HTTPException) as exc_info:
        bg_bridge.create_or_replay_image_remove_background_job(
            account_id="test-r7-user-1",
            payload={"image_asset_id": "test-r7-asset-img-1", "mode": "removebg_hd", "amount": 100},
        )
    assert exc_info.value.status_code == 400
    assert "authority" in exc_info.value.detail

    # 2. Missing image_asset_id rejected
    with pytest.raises(HTTPException) as exc_info:
        bg_bridge.create_or_replay_image_remove_background_job(
            account_id="test-r7-user-1",
            payload={"mode": "removebg_hd"},
        )
    assert exc_info.value.status_code == 400
    assert "image_asset_id" in exc_info.value.detail or "tài sản" in exc_info.value.detail

    # 3. Invalid asset format (e.g., pdf instead of image) rejected
    with pytest.raises(HTTPException) as exc_info:
        bg_bridge.create_or_replay_image_remove_background_job(
            account_id="test-r7-user-1",
            payload={"image_asset_id": "test-r7-asset-doc-1"},
        )
    assert exc_info.value.status_code == 400
    assert "hình ảnh" in exc_info.value.detail.lower() or "định dạng" in exc_info.value.detail.lower()

    # 4. Asset owned by other account rejected
    with pytest.raises(HTTPException) as exc_info:
        bg_bridge.create_or_replay_image_remove_background_job(
            account_id="test-r7-user-2",  # user 2 doesn't own test-r7-asset-img-1
            payload={"image_asset_id": "test-r7-asset-img-1"},
        )
    assert exc_info.value.status_code == 400
    assert "Asset Vault" in exc_info.value.detail

    # 5. Valid job creation with removebg_hd
    job = bg_bridge.create_or_replay_image_remove_background_job(
        account_id="test-r7-user-1",
        payload={"image_asset_id": "test-r7-asset-img-1", "mode": "removebg_hd"},
        request_id="REQ-RMBG-001",
    )
    assert job["id"].startswith("irbj_")
    assert job["mode"] == "removebg_hd"
    assert job["status"] == "queued"
    assert job["request_id"] == "REQ-RMBG-001"
    assert job["idempotent_replay"] is False

    # 6. Idempotent replay
    replayed = bg_bridge.create_or_replay_image_remove_background_job(
        account_id="test-r7-user-1",
        payload={"image_asset_id": "test-r7-asset-img-1", "mode": "removebg_hd"},
        request_id="REQ-RMBG-001",
    )
    assert replayed["id"] == job["id"]
    assert replayed["idempotent_replay"] is True

    # 7. Conflict detection on same request_id with differing payload
    with pytest.raises(HTTPException) as exc_info:
        bg_bridge.create_or_replay_image_remove_background_job(
            account_id="test-r7-user-1",
            payload={"image_asset_id": "test-r7-asset-img-1", "mode": "cutout"},  # different mode
            request_id="REQ-RMBG-001",
        )
    assert exc_info.value.status_code == 409

    # 8. Query job detail
    fetched = bg_bridge.get_image_remove_background_job("test-r7-user-1", job["id"])
    assert fetched is not None
    assert fetched["id"] == job["id"]

    # 9. Cross-account security
    assert bg_bridge.get_image_remove_background_job("test-r7-user-2", job["id"]) is None
    assert bg_bridge.is_image_remove_background_job_other_account(job["id"], "test-r7-user-2") is True


# ─── TEST 4: ACTIVE RUNTIME FEATURES REGISTRATION ─────────────────────────────

def test_r7_active_features_registration() -> None:
    assert "video_long" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "video_multiscene" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "image_remove_background" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
    assert "image_remove-background" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES


# ─── TEST 5: API ROUTES AUTHENTICATION CONTRACTS ──────────────────────────────

def test_r7_api_feature_routes_unauthenticated_reject() -> None:
    client = TestClient(app)

    endpoints = [
        "/api/v1/features/image_remove_background/jobs",
        "/api/v1/features/image_remove-background/jobs",
    ]

    for ep in endpoints:
        resp = client.post(ep, json={"image_asset_id": "test"})
        assert resp.status_code == 401, f"POST {ep} must require auth"
        resp_get = client.get(ep)
        assert resp_get.status_code == 401, f"GET {ep} must require auth"

    # HTML page route redirects unauthenticated users to /login
    resp_page = client.get("/image/remove-background", follow_redirects=False)
    assert resp_page.status_code in (200, 307), "HTML page should either render or redirect to login"


# ─── TEST 6: PROVENANCE & DEFECTS INTEGRITY ───────────────────────────────────

def test_r7_provenance_and_defects_integrity() -> None:
    with open(PROVENANCE_FILE, "r", encoding="utf-8") as f:
        prov = json.load(f)

    s = prov["summary"]
    assert s["SOURCE_RUNTIME_MATCH"] == "YES"
    assert s["PLACEHOLDER_SURFACES"] == 0
    assert s["BROKEN_SURFACES"] == 0
    assert s["UNKNOWN_DATA_SURFACES"] == 0
    assert s["DEMO_DATA_SURFACES"] == 0
    assert s["FIRST_RED"] == "NONE - R7 WHOLE APP FINAL RESIDUAL RUNTIME CLOSURE COMPLETE"

    with open(DEFECTS_FILE, "r", encoding="utf-8") as f:
        defects = json.load(f)

    defect_ids = {d["DEFECT_ID"]: d for d in defects}
    assert "DEFECT-R7-001" in defect_ids
    assert defect_ids["DEFECT-R7-001"]["STATUS"] == "REPAIRED_IN_R7"
    assert "DEFECT-R7-002" in defect_ids
    assert defect_ids["DEFECT-R7-002"]["STATUS"] == "REPAIRED_IN_R7"
    assert "DEFECT-R7-003" in defect_ids
    assert defect_ids["DEFECT-R7-003"]["STATUS"] == "REPAIRED_IN_R7"
