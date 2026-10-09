"""Tests for R6 Remaining 13 Engine Gaps Full Closure runtime matrix contracts."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import app
from copyfast_db import ensure_copyfast_schema, transaction
import copyfast_document_translate_bridge as doc_bridge
import copyfast_product_video_job_bridge as pvid_bridge

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "webapp_full_product_truth"
MATRIX_FILE = REPORT_DIR / "R6_FINAL_ROUTE_RUNTIME_MATRIX.json"
PROVENANCE_FILE = REPORT_DIR / "00_data_provenance.json"
DEFECTS_FILE = REPORT_DIR / "defects.json"


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret-r6-matrix")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_document_translate_jobs")
        conn.execute("DELETE FROM web_product_video_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-r6-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r6-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('test-r6-user-1', 'user1@test.local', 'hash1', '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z'),
                   ('test-r6-user-2', 'user2@test.local', 'hash2', '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, lifecycle_revision, created_at, updated_at
            ) VALUES (
                'test-r6-asset-img-1', 'test-r6-user-1', NULL, 'photo.png', 'photo.png',
                '.png', 'image/png', 1024, 'aabbcc112233', 'storage-key-img-1',
                'active', 1, '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z'
            ), (
                'test-r6-asset-doc-1', 'test-r6-user-1', NULL, 'manual.pdf', 'manual.pdf',
                '.pdf', 'application/pdf', 2048, 'ddeeff445566', 'storage-key-doc-1',
                'active', 1, '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z'
            )
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_document_translate_jobs")
        conn.execute("DELETE FROM web_product_video_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-r6-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r6-%'")


# ─── TEST 1: MATRIX SUMMARY & TOTAL INTEGRITY ─────────────────────────────────

def test_r6_matrix_summary_and_surface_counts() -> None:
    assert MATRIX_FILE.exists(), "R6_FINAL_ROUTE_RUNTIME_MATRIX.json must exist"
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    routes = data["routes"]

    assert summary["BATCH"] == "WEBAPP_R6_REMAINING_13_ENGINE_GAPS_FULL_CLOSURE_MASTER_BATCH_R1"
    assert summary["TOTAL_SURFACES"] == 221
    assert len(routes) == 221
    assert summary["UNCLASSIFIED_ROUTE_COUNT"] == 0
    assert summary["UNKNOWN_RUNTIME_OWNER_COUNT"] == 0
    assert summary["UNKNOWN_DATA_OWNER_COUNT"] == 0
    assert summary["STALE_PROVENANCE_SHA_COUNT"] == 0

    assert summary["R4_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 18
    assert summary["R5_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 13
    assert summary["R6_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 2
    assert summary["R6_ACTIVE_CANONICAL_PROMOTED_COUNT"] == 6
    assert summary["R6_INFORMATIONAL_RECLASSIFIED_COUNT"] == 1
    assert summary["R6_GRANT_REQUIRED_RECLASSIFIED_COUNT"] == 4

    assert summary["WEB_BRIDGE_NOT_MOUNTED_COUNT"] == 0
    assert summary["BOT_ADAPTER_EXISTS_NOT_EXPOSED_TO_WEB_COUNT"] == 0
    assert summary["WORKER_CONSUMER_EXISTS_NOT_ACTIVATED_COUNT"] == 2

    class_counts = summary["CLASSIFICATION_COUNTS"]
    assert class_counts["RELEASED_ACTIVE_CANONICAL_RUNTIME"] == 19
    assert class_counts["RELEASED_WEB_NATIVE_RUNTIME"] == 112
    assert class_counts["RELEASED_READ_ONLY_CANONICAL_COMPANION"] == 19
    assert class_counts["NOT_A_PRODUCT_ACTION_INFORMATIONAL_ONLY"] == 16
    assert class_counts["BLOCKED_EXTERNAL_CAPABILITY_OR_GRANT_REQUIRED"] == 5
    assert class_counts["BLOCKED_CANONICAL_BACKEND_MISSING"] == 2
    assert class_counts["ADMIN_INTERNAL_ONLY"] == 48


# ─── TEST 2: ALL 13 ROUTES CLASSIFICATION & ROOT GAPS ─────────────────────────

def test_r6_all_13_target_routes_exact_dispositions() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    routes_by_path = {r["route"]: r for r in data["routes"]}

    # 1. /video/trend -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    trend = routes_by_path["/video/trend"]
    assert trend["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert trend["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert trend["canonical_worker_consumer_exists"] is True
    assert trend["runtime_execution_enabled"] is True

    # 2. /video/image-to-video -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    i2v = routes_by_path["/video/image-to-video"]
    assert i2v["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert i2v["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert i2v["web_to_bot_bridge_mounted"] is True

    # 3. /video/quick -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    quick = routes_by_path["/video/quick"]
    assert quick["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert quick["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert quick["web_to_bot_bridge_mounted"] is True

    # 4. /video/product -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    prod = routes_by_path["/video/product"]
    assert prod["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert prod["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert prod["web_to_bot_bridge_mounted"] is True

    # 5. /video/text-to-video -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    t2v = routes_by_path["/video/text-to-video"]
    assert t2v["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert t2v["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert t2v["web_to_bot_bridge_mounted"] is True

    # 6. /documents/translate -> Promoted to RELEASED_ACTIVE_CANONICAL_RUNTIME
    doc_tr = routes_by_path["/documents/translate"]
    assert doc_tr["final_classification"] == "RELEASED_ACTIVE_CANONICAL_RUNTIME"
    assert doc_tr["actual_root_gap"] == "NONE_RELEASED_RUNTIME"
    assert doc_tr["web_to_bot_bridge_mounted"] is True

    # 7. /video/mux -> Reclassified to NOT_A_PRODUCT_ACTION_INFORMATIONAL_ONLY
    mux = routes_by_path["/video/mux"]
    assert mux["final_classification"] == "NOT_A_PRODUCT_ACTION_INFORMATIONAL_ONLY"
    assert mux["actual_root_gap"] == "NOT_APPLICABLE_INFORMATIONAL"

    # 8-11. Four genuine external capability missing routes
    for p in ("/music/sfx", "/image/upscale", "/image/transform", "/image/remove-background"):
        r = routes_by_path[p]
        assert r["final_classification"] == "BLOCKED_EXTERNAL_CAPABILITY_OR_GRANT_REQUIRED", f"Route {p} classification"
        assert r["actual_root_gap"] == "EXTERNAL_PROVIDER_CAPABILITY_MISSING", f"Route {p} root gap"

    # 12-13. Two worker consumer not activated routes
    for p in ("/video/long", "/video/multiscene"):
        r = routes_by_path[p]
        assert r["final_classification"] == "BLOCKED_CANONICAL_BACKEND_MISSING", f"Route {p} classification"
        assert r["actual_root_gap"] == "WORKER_CONSUMER_EXISTS_NOT_ACTIVATED", f"Route {p} root gap"


# ─── TEST 3: DOCUMENT TRANSLATE BRIDGE CONTRACTS ──────────────────────────────

def test_r6_document_translate_bridge_contracts() -> None:
    # 1. Authority field injection rejected
    with pytest.raises(HTTPException) as exc_info:
        doc_bridge.create_or_replay_document_translate_job(
            account_id="test-r6-user-1",
            payload={"document_asset_id": "test-r6-asset-doc-1", "target_lang": "en", "amount": 100},
        )
    assert exc_info.value.status_code == 400
    assert "authority" in exc_info.value.detail

    # 2. Missing document_asset_id rejected
    with pytest.raises(HTTPException) as exc_info:
        doc_bridge.create_or_replay_document_translate_job(
            account_id="test-r6-user-1",
            payload={"target_lang": "en"},
        )
    assert exc_info.value.status_code == 400
    assert "Asset Vault" in exc_info.value.detail

    # 3. Invalid target language rejected
    with pytest.raises(HTTPException) as exc_info:
        doc_bridge.create_or_replay_document_translate_job(
            account_id="test-r6-user-1",
            payload={"document_asset_id": "test-r6-asset-doc-1", "target_lang": "invalid_lang_code_xyz"},
        )
    assert exc_info.value.status_code == 400
    assert "ngôn ngữ" in exc_info.value.detail.lower() or "target" in exc_info.value.detail.lower()

    # 4. Asset owned by other account rejected
    with pytest.raises(HTTPException) as exc_info:
        doc_bridge.create_or_replay_document_translate_job(
            account_id="test-r6-user-2",  # user 2 doesn't own test-r6-asset-doc-1
            payload={"document_asset_id": "test-r6-asset-doc-1", "target_lang": "en"},
        )
    assert exc_info.value.status_code == 400
    assert "Asset Vault" in exc_info.value.detail

    # 5. Valid job creation
    job = doc_bridge.create_or_replay_document_translate_job(
        account_id="test-r6-user-1",
        payload={"document_asset_id": "test-r6-asset-doc-1", "target_lang": "en", "source_lang": "vi"},
        request_id="REQ-DOC-TR-001",
    )
    assert job["id"].startswith("dtj_")
    assert job["status"] == "queued"
    assert job["request_id"] == "REQ-DOC-TR-001"
    assert job["target_language"] == "en"
    assert job["idempotent_replay"] is False

    # 6. Idempotent replay
    replayed = doc_bridge.create_or_replay_document_translate_job(
        account_id="test-r6-user-1",
        payload={"document_asset_id": "test-r6-asset-doc-1", "target_lang": "en", "source_lang": "vi"},
        request_id="REQ-DOC-TR-001",
    )
    assert replayed["id"] == job["id"]
    assert replayed["idempotent_replay"] is True

    # 7. Conflict detection on same request_id with differing payload
    with pytest.raises(HTTPException) as exc_info:
        doc_bridge.create_or_replay_document_translate_job(
            account_id="test-r6-user-1",
            payload={"document_asset_id": "test-r6-asset-doc-1", "target_lang": "ja"},  # different target lang
            request_id="REQ-DOC-TR-001",
        )
    assert exc_info.value.status_code == 409

    # 8. Query job detail
    fetched = doc_bridge.get_document_translate_job("test-r6-user-1", job["id"])
    assert fetched is not None
    assert fetched["id"] == job["id"]

    # 9. Cross-account security
    assert doc_bridge.get_document_translate_job("test-r6-user-2", job["id"]) is None
    assert doc_bridge.is_document_translate_job_other_account(job["id"], "test-r6-user-2") is True


# ─── TEST 4: IMAGE-TO-VIDEO BRIDGE CONTRACTS ──────────────────────────────────

def test_r6_image_to_video_bridge_contracts() -> None:
    # 1. Missing image_asset_id rejected
    with pytest.raises(HTTPException) as exc_info:
        pvid_bridge.create_or_replay_image_to_video_job(
            account_id="test-r6-user-1",
            payload={"prompt": "Camera pans slowly", "quality_tier": 200, "duration_seconds": 5},
        )
    assert exc_info.value.status_code == 400
    assert "Asset Vault" in exc_info.value.detail

    # 2. Asset owned by other account rejected
    with pytest.raises(HTTPException) as exc_info:
        pvid_bridge.create_or_replay_image_to_video_job(
            account_id="test-r6-user-2",
            payload={
                "image_asset_id": "test-r6-asset-img-1",
                "prompt": "Camera pans slowly",
                "quality_tier": 200,
                "duration_seconds": 5,
            },
        )
    assert exc_info.value.status_code == 400
    assert "Asset Vault" in exc_info.value.detail

    # 3. Valid job creation
    job = pvid_bridge.create_or_replay_image_to_video_job(
        account_id="test-r6-user-1",
        payload={
            "image_asset_id": "test-r6-asset-img-1",
            "prompt": "Cinematic camera zoom on product",
            "quality_tier": 300,
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
        },
        request_id="REQ-I2V-001",
    )
    assert job["id"].startswith("pvj_")
    assert job["product_key"] == "video_ai_image"
    assert job["status"] == "queued"
    assert job["request_id"] == "REQ-I2V-001"
    assert job["image_asset_id"] == "test-r6-asset-img-1"
    assert job["idempotent_replay"] is False

    # 4. Idempotent replay
    replayed = pvid_bridge.create_or_replay_image_to_video_job(
        account_id="test-r6-user-1",
        payload={
            "image_asset_id": "test-r6-asset-img-1",
            "prompt": "Cinematic camera zoom on product",
            "quality_tier": 300,
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
        },
        request_id="REQ-I2V-001",
    )
    assert replayed["id"] == job["id"]
    assert replayed["idempotent_replay"] is True


# ─── TEST 5: PRODUCT VIDEO COMPOSITION FOR QUICK, PRODUCT, TEXT-TO-VIDEO ──────

def test_r6_product_video_composition_routes() -> None:
    for product_key in ("video_quick", "video_product", "video_text_to_video"):
        job = pvid_bridge.create_or_replay_product_video_job(
            account_id="test-r6-user-1",
            payload={
                "prompt": f"Promo video for {product_key}",
                "aspect_ratio": "16:9",
                "duration_seconds": 5,
                "quality_tier": 200,
            },
            request_id=f"REQ-{product_key.upper()}-001",
            product_key=product_key,
        )
        assert job["id"].startswith("pvj_")
        assert job["product_key"] == product_key
        assert job["status"] == "queued"
        assert job["request_id"] == f"REQ-{product_key.upper()}-001"


# ─── TEST 6: API ROUTES AUTHENTICATION CONTRACTS ──────────────────────────────

def test_r6_api_feature_routes_unauthenticated_reject() -> None:
    client = TestClient(app)

    endpoints = [
        "/api/v1/features/video_quick/jobs",
        "/api/v1/features/video_product/jobs",
        "/api/v1/features/video_text_to_video/jobs",
        "/api/v1/features/video_image_to_video/jobs",
        "/api/v1/features/documents_translate/jobs",
    ]

    for ep in endpoints:
        resp = client.post(ep, json={"prompt": "test"})
        assert resp.status_code == 401, f"POST {ep} must require auth"
        resp_get = client.get(ep)
        assert resp_get.status_code == 401, f"GET {ep} must require auth"


# ─── TEST 7: PROVENANCE & DEFECTS INTEGRITY ───────────────────────────────────

def test_r6_provenance_and_defects_integrity() -> None:
    with open(PROVENANCE_FILE, "r", encoding="utf-8") as f:
        prov = json.load(f)

    s = prov["summary"]
    assert s["SOURCE_RUNTIME_MATCH"] == "YES"
    assert s["PLACEHOLDER_SURFACES"] == 0
    assert s["BROKEN_SURFACES"] == 0
    assert s["UNKNOWN_DATA_SURFACES"] == 0
    assert s["DEMO_DATA_SURFACES"] == 0

    with open(DEFECTS_FILE, "r", encoding="utf-8") as f:
        defects = json.load(f)

    defect_ids = {d["DEFECT_ID"]: d for d in defects}
    assert "DEFECT-R6-001" in defect_ids
    assert defect_ids["DEFECT-R6-001"]["STATUS"] == "REPAIRED_IN_R6"
    assert "DEFECT-R6-002" in defect_ids
    assert defect_ids["DEFECT-R6-002"]["STATUS"] == "REPAIRED_IN_R6"
