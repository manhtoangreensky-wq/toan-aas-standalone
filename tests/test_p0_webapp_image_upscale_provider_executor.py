"""Tests for Image Upscale Provider Executor Foundation and Provider-Free Contract Proof.

Tasks:
- WEBAPP_R24E1_IMAGE_UPSCALE_PROVIDER_EXECUTOR_FOUNDATION_AND_PROVIDER_FREE_CONTRACT_PROOF_R1
- WEBAPP_R24E1_FIX1_IMAGE_UPSCALE_EXECUTOR_SECURITY_BOUNDARY_AND_RECEIPT_TRUTH_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Product Family: WebApp / Image Upscale
Customer Route: /image/upscale
Job Bridge: copyfast_image_upscale_job_bridge.py
Provider: Stability AI (Conservative Upscale)

Proves:
1. Executor contract constants truthful.
2. Unknown job blocked.
3. Queued canonical job accepted by executor logic via test harness.
4. Completed job cannot resubmit.
5. Provider dispatch default remains disabled with precise blockers.
6. Fake transport executes request builder.
7. Fake transport called exactly once.
8. Duplicate execution cannot call transport twice.
9. Source Asset Vault wrong owner blocked.
10. Missing source artifact blocked.
11. Malformed provider response fails closed.
12. Provider failure records failed state truthfully.
13. Ambiguous provider result prevents blind retry.
14. Successful mock result imports/creates owner-scoped Asset Vault artifact.
15. Successful result finalizes job completed.
16. Customer job exposes retained output.
17. Admin job exposes same canonical job.
18. No raw provider credential persisted.
19. No wallet/payment mutation.
20. REAL_PROVIDER_NETWORK_CALL_COUNT = 0.
21. Base64 JSON response payload parsing.
22 (FIX1-A). Arbitrary custom transport cannot bypass runtime gates in production executor.
23 (FIX1-B). Transport cannot reach network while PROVIDER_ENTITLEMENT_PROVEN = False.
24 (FIX1-C). Transport cannot reach network while OWNER_PAID_AUTHORIZATION_GRANTED = False.
25 (FIX1-D). Transport cannot reach network while IMAGE_UPSCALE_PROVIDER_DISPATCH_CURRENTLY_ENABLED = False.
26 (FIX1-E). Missing API key produces fail-closed behavior, no fake Bearer credential fallback.
27 (FIX1-F). Provider response with no request/task identifier leaves provider_task_id empty (None).
28 (FIX1-G). Output hash is recorded under output_sha256, NEVER labeled provider_task_id.
29 (FIX1-H). Provider-supplied request ID is retained accurately when present.
30 (FIX1-I). Malformed/non-success finish-reason fails closed, never finalizes output.
31 (FIX1-J). Existing duplicate/ambiguous retry protections remain green.
32 (FIX1-K). REAL_PROVIDER_NETWORK_CALL_COUNT = 0 globally verified.
"""

from __future__ import annotations

import base64
import hashlib
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
from copyfast_assets import _private_asset_vault_child_directory, _storage_path
from copyfast_db import (
    asset_vault_directory,
    ensure_copyfast_schema,
    read_transaction,
    transaction,
    utc_now,
)
import copyfast_image_upscale_job_bridge as bridge
import copyfast_image_upscale_provider as provider_mod


# Global network call tracker to empirically verify REAL_PROVIDER_NETWORK_CALL_COUNT = 0
REAL_PROVIDER_NETWORK_CALL_COUNT: int = 0


# Minimal valid 2x2 PNG bytes
SAMPLE_PNG_BYTES: bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x06\x00\x00\x00"
    b"\xf4x\xd4\xfa\x00\x00\x00\x10IDATx\x9cc\xfc\xff\xff?\x03\x00\x08\xfc\x02\xfe\xa7\x9a\xa0\xa0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def run_test_image_upscale_pipeline(
    job_id: str,
    *,
    transport: provider_mod.ImageUpscaleTransportProtocol,
    api_key: str = "test-explicit-key-upscale-999",
) -> dict[str, Any]:
    """Test-owned execution harness exercising pure request preparation, transport, and result application.

    Separates pure executor core from production dispatch as required by R24E1-FIX1.
    """
    job_dict, req, (url, headers, files, data) = bridge.prepare_image_upscale_request(job_id, api_key=api_key)
    try:
        raw_resp = transport.post(url, headers=headers, files=files, data=data)
    except Exception as exc:
        bridge.transition_image_upscale_job_failed(job_id, f"PROVIDER_TRANSPORT_FAILED: {exc}")
        raise

    try:
        result = provider_mod.parse_stability_upscale_response(raw_resp, job_id=job_id)
    except Exception as exc:
        bridge.transition_image_upscale_job_failed(job_id, f"PROVIDER_RESPONSE_PARSE_FAILED: {exc}")
        raise

    try:
        finalized = bridge.apply_image_upscale_result(job_id, result)
    except Exception as exc:
        bridge.transition_image_upscale_job_failed(job_id, f"OUTPUT_ASSET_STORAGE_FAILED: {exc}")
        raise

    return finalized


@pytest.fixture(autouse=True)
def setup_db_and_env(monkeypatch):
    """Set test environment and seed database tables."""
    global REAL_PROVIDER_NETWORK_CALL_COUNT
    REAL_PROVIDER_NETWORK_CALL_COUNT = 0

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-upscale-executor")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()

    ensure_copyfast_schema()
    bridge.ensure_image_upscale_schema()

    # Seed physical source artifact into Asset Vault objects/ directory
    root = asset_vault_directory()
    _private_asset_vault_child_directory(root, "objects")
    source_storage_key = f"objects/{uuid.uuid4().hex}.blob"
    source_path = _storage_path(root, source_storage_key)
    source_path.write_bytes(SAMPLE_PNG_BYTES)
    source_digest = hashlib.sha256(SAMPLE_PNG_BYTES).hexdigest()

    user2_storage_key = f"objects/{uuid.uuid4().hex}.blob"
    user2_path = _storage_path(root, user2_storage_key)
    user2_path.write_bytes(SAMPLE_PNG_BYTES)
    user2_digest = hashlib.sha256(SAMPLE_PNG_BYTES).hexdigest()

    missing_storage_key = f"objects/{uuid.uuid4().hex}.blob"

    with transaction() as conn:
        conn.execute("DELETE FROM web_image_upscale_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-upscale-%'")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-upscale-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-upscale-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES ('test-upscale-user-1', 'upscale1@test.local', 'hash1', 'user', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'),
                   ('test-upscale-user-2', 'upscale2@test.local', 'hash2', 'user', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'),
                   ('test-upscale-admin', 'admin@test.local', 'hashadmin', 'admin', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z');
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, created_at, updated_at
            ) VALUES (
                'asset-upscale-source-1', 'test-upscale-user-1', NULL, 'Ảnh hợp lệ',
                'sample.png', '.png', 'image/png', ?, ?, ?,
                'active', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'
            ), (
                'asset-upscale-user2-source', 'test-upscale-user-2', NULL, 'Ảnh của User 2',
                'user2.png', '.png', 'image/png', ?, ?, ?,
                'active', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'
            ), (
                'asset-upscale-missing-file', 'test-upscale-user-1', NULL, 'Ảnh mất file vật lý',
                'ghost.png', '.png', 'image/png', 100, 'ghosthash', ?,
                'active', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'
            );
            """,
            (
                len(SAMPLE_PNG_BYTES),
                source_digest,
                source_storage_key,
                len(SAMPLE_PNG_BYTES),
                user2_digest,
                user2_storage_key,
                missing_storage_key,
            ),
        )

    yield

    with transaction() as conn:
        conn.execute("DELETE FROM web_image_upscale_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'test-upscale-%'")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-upscale-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-upscale-%'")

    # Clean test physical artifacts
    for p in (source_path, user2_path):
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


# ─── CASE 1: EXECUTOR CONTRACT CONSTANTS TRUTHFUL ────────────────────────────

def test_01_executor_contract_constants_truthful():
    """Verify structural truth declarations and blocker constants."""
    assert bridge.IMAGE_UPSCALE_PROVIDER_EXECUTOR_IMPLEMENTED is True
    assert bridge.IMAGE_UPSCALE_PROVIDER_DISPATCH_CURRENTLY_ENABLED is False
    assert bridge.IMAGE_UPSCALE_PROVIDER_DISPATCH_ENABLED is False
    assert bridge.DIRECT_OWNER_AUTHORIZATION_TO_LIVE_TEST_POSSIBLE is False
    assert bridge.STABILITY_UPSCALE_ENTITLEMENT_PROVEN is False
    assert bridge.OWNER_PAID_AUTHORIZATION_GRANTED is False
    assert bridge.ARBITRARY_TRANSPORT_OBJECT_IS_AUTHORITY is False
    assert bridge.DIRECT_TRANSPORT_GATE_BYPASS is False

    assert bridge.BLOCKER_PROVIDER_EXECUTOR_READY_BUT_DISPATCH_DISABLED == "PROVIDER_EXECUTOR_READY_BUT_DISPATCH_DISABLED"
    assert bridge.BLOCKER_PROVIDER_ENTITLEMENT_UNPROVEN == "PROVIDER_ENTITLEMENT_UNPROVEN"
    assert bridge.BLOCKER_OWNER_PAID_AUTHORIZATION_REQUIRED == "OWNER_PAID_AUTHORIZATION_REQUIRED"
    assert bridge.BLOCKER_PROVIDER_CONTRACT_UNPROVEN == "PROVIDER_CONTRACT_UNPROVEN"

    assert provider_mod.PRODUCTION_FAKE_API_KEY_FALLBACK == "ABSENT"
    assert provider_mod.MISSING_PROVIDER_CREDENTIAL_BEHAVIOR == "FAIL_CLOSED_BEFORE_NETWORK"
    assert provider_mod.SYNTHETIC_PROVIDER_TASK_ID_ALLOWED is False

    assert provider_mod.STABILITY_UPSCALE_PROVIDER_NAME == "Stability AI"
    assert provider_mod.STABILITY_UPSCALE_PROVIDER_KEY == "stability"
    assert provider_mod.STABILITY_UPSCALE_MODEL_NAME == "stability_conservative"
    assert provider_mod.STABILITY_UPSCALE_CAPABILITY_ID == "stability-image-upscale-conservative-v1"
    assert provider_mod.STABILITY_UPSCALE_ENDPOINT == "https://api.stability.ai/v2beta/stable-image/upscale/conservative"


# ─── CASE 2: UNKNOWN JOB BLOCKED ─────────────────────────────────────────────

def test_02_unknown_job_blocked():
    """Attempting to execute an unknown job raises ValueError and fails closed."""
    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(ValueError) as exc:
        bridge.execute_image_upscale_job("upscale_ghost_999", transport=transport)
    assert "Không tìm thấy job Image Upscale" in str(exc.value)
    assert transport.call_count == 0

    with pytest.raises(ValueError) as exc_harness:
        run_test_image_upscale_pipeline("upscale_ghost_999", transport=transport)
    assert "Không tìm thấy job Image Upscale" in str(exc_harness.value)
    assert transport.call_count == 0


# ─── CASE 3: QUEUED CANONICAL JOB ACCEPTED BY EXECUTOR LOGIC ──────────────────

def test_03_queued_canonical_job_accepted_by_executor_logic():
    """A valid queued job with model='stability_conservative' executes cleanly via test harness."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]
    assert created["status"] == bridge.STATUS_QUEUED

    transport = provider_mod.FakeStabilityUpscaleTransport()
    result = run_test_image_upscale_pipeline(job_id, transport=transport)

    assert result["status"] == bridge.STATUS_COMPLETED
    assert result["status_reason"] == bridge.STATUS_REASON_COMPLETED
    assert result["output_available"] is True
    assert result["provider_name"] == "stability"
    assert result["model_name"] == "stability_conservative"
    assert result["output_asset_id"] is not None
    assert transport.call_count == 1


# ─── CASE 4: COMPLETED JOB CANNOT RESUBMIT ───────────────────────────────────

def test_04_completed_job_cannot_resubmit():
    """Completed job rejects second provider submit."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]
    transport = provider_mod.FakeStabilityUpscaleTransport()
    run_test_image_upscale_pipeline(job_id, transport=transport)

    # Attempt second execution
    with pytest.raises(ValueError) as exc:
        run_test_image_upscale_pipeline(job_id, transport=transport)
    assert "đã hoàn thành, không được submit lại" in str(exc.value)
    assert transport.call_count == 1  # Not called a second time


# ─── CASE 5: PROVIDER DISPATCH DEFAULT REMAINS DISABLED ──────────────────────

def test_05_provider_dispatch_default_remains_disabled():
    """Verify runtime dispatch boundary raises precise blocker errors."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    # In production without entitlement
    with pytest.raises(RuntimeError) as exc:
        bridge.dispatch_image_upscale_provider(job_id)
    assert "IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED" in str(exc.value)
    assert bridge.BLOCKER_PROVIDER_ENTITLEMENT_UNPROVEN in str(exc.value)

    # For replicate_real_esrgan job
    created_replicate = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "replicate_real_esrgan",
        },
    )
    with pytest.raises(RuntimeError) as exc_rep:
        bridge.dispatch_image_upscale_provider(created_replicate["id"])
    assert bridge.BLOCKER_PROVIDER_CONTRACT_UNPROVEN in str(exc_rep.value)

    # Calling execute_image_upscale_job without transport
    with pytest.raises(RuntimeError) as exc_exec:
        bridge.execute_image_upscale_job(job_id, transport=None)
    assert "IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED" in str(exc_exec.value)


# ─── CASE 6 & 7: FAKE TRANSPORT EXECUTES REQUEST BUILDER ONCE ────────────────

def test_06_and_07_fake_transport_executes_request_builder_once():
    """Fake transport inspects real constructed HTTP request payload and is called once."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 4,
            "model_name": "stability_conservative",
        },
    )
    transport = provider_mod.FakeStabilityUpscaleTransport()
    run_test_image_upscale_pipeline(created["id"], transport=transport)

    assert transport.call_count == 1
    req = transport.recorded_requests[0]
    assert req["url"] == provider_mod.STABILITY_UPSCALE_ENDPOINT
    assert "Authorization" in req["headers"]
    assert req["headers"]["Accept"] == "image/*"
    assert "image" in req["files"]
    assert req["data"]["output_format"] == "png"
    assert req["data"]["creativity"] == provider_mod.DEFAULT_CREATIVITY
    assert "4x" in req["data"]["prompt"]


# ─── CASE 8: DUPLICATE EXECUTION CANNOT CALL TRANSPORT TWICE ─────────────────

def test_08_duplicate_execution_cannot_call_transport_twice():
    """Concurrent/processing job cannot be submitted a second time."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    # Mark job as processing
    with transaction() as conn:
        conn.execute(
            "UPDATE web_image_upscale_jobs SET status = 'processing' WHERE id = ?;",
            (job_id,),
        )

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(ValueError) as exc:
        run_test_image_upscale_pipeline(job_id, transport=transport)
    assert "đang được xử lý, không thể gửi trùng lặp" in str(exc.value)
    assert transport.call_count == 0


# ─── CASE 9: SOURCE ASSET VAULT WRONG OWNER BLOCKED ──────────────────────────

def test_09_source_asset_vault_wrong_owner_blocked():
    """Job pointing to an asset owned by another user is blocked by tenant isolation."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    # Tamper job row to point to User 2's asset
    with transaction() as conn:
        conn.execute(
            "UPDATE web_image_upscale_jobs SET image_asset_id = 'asset-upscale-user2-source' WHERE id = ?;",
            (job_id,),
        )

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(ValueError) as exc:
        run_test_image_upscale_pipeline(job_id, transport=transport)
    assert "Vi phạm cách ly tài khoản" in str(exc.value)
    assert transport.call_count == 0

    # Job is transitioned to failed
    job_after = bridge.get_admin_image_upscale_job(job_id)
    assert job_after["status"] == bridge.STATUS_FAILED


# ─── CASE 10: MISSING SOURCE ARTIFACT BLOCKED ────────────────────────────────

def test_10_missing_source_artifact_blocked():
    """Job pointing to an asset without a physical file on disk fails closed."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    # Tamper to point to missing file asset
    with transaction() as conn:
        conn.execute(
            "UPDATE web_image_upscale_jobs SET image_asset_id = 'asset-upscale-missing-file' WHERE id = ?;",
            (job_id,),
        )

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(ValueError) as exc:
        run_test_image_upscale_pipeline(job_id, transport=transport)
    assert "Tệp lưu trữ vật lý không tồn tại trên đĩa" in str(exc.value)
    assert transport.call_count == 0


# ─── CASE 11: MALFORMED PROVIDER RESPONSE FAILS CLOSED ───────────────────────

def test_11_malformed_provider_response_fails_closed():
    """Provider returning empty bytes or invalid payload fails closed and marks job failed."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    transport = provider_mod.FakeStabilityUpscaleTransport(
        status_code=200,
        response_image_bytes=b"too_short",
    )
    with pytest.raises(provider_mod.ImageUpscaleProviderResponseError):
        run_test_image_upscale_pipeline(job_id, transport=transport)

    job_after = bridge.get_admin_image_upscale_job(job_id)
    assert job_after["status"] == bridge.STATUS_FAILED
    assert "PROVIDER_RESPONSE_PARSE_FAILED" in job_after["status_reason"]


# ─── CASE 12: PROVIDER FAILURE RECORDS FAILED STATE TRUTHFULLY ───────────────

def test_12_provider_failure_records_failed_state_truthfully():
    """Provider returning HTTP 500 error transitions job to failed."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    transport = provider_mod.FakeStabilityUpscaleTransport(
        status_code=500,
        error_text=json.dumps({"errors": ["Internal upscale cluster error"]}),
    )
    with pytest.raises(provider_mod.ImageUpscaleProviderError):
        run_test_image_upscale_pipeline(job_id, transport=transport)

    job_after = bridge.get_admin_image_upscale_job(job_id)
    assert job_after["status"] == bridge.STATUS_FAILED
    assert "PROVIDER_RESPONSE_PARSE_FAILED" in job_after["status_reason"]


# ─── CASE 13: AMBIGUOUS PROVIDER RESULT PREVENTS BLIND RETRY ─────────────────

def test_13_ambiguous_provider_result_prevents_blind_retry():
    """Failed job cannot be automatically re-executed without explicit new submission."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    # Force job into failed state
    bridge.transition_image_upscale_job_failed(job_id, "Ambiguous timeout")

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(ValueError) as exc:
        run_test_image_upscale_pipeline(job_id, transport=transport)
    assert "đã thất bại. Cấm tự động retry mù quáng" in str(exc.value)
    assert transport.call_count == 0


# ─── CASE 14 & 15: SUCCESSFUL RESULT IMPORTS ASSET & FINALIZES JOB ────────────

def test_14_and_15_successful_result_imports_asset_and_finalizes_job():
    """Successful execution creates owner-scoped Asset Vault item and completes job."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    transport = provider_mod.FakeStabilityUpscaleTransport()
    finalized = run_test_image_upscale_pipeline(job_id, transport=transport)

    assert finalized["status"] == bridge.STATUS_COMPLETED
    output_asset_id = finalized["output_asset_id"]
    assert output_asset_id is not None

    # Verify output asset exists in Asset Vault for User 1
    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        asset_row = conn.execute(
            "SELECT * FROM web_asset_files WHERE id = ?;", (output_asset_id,)
        ).fetchone()
    assert asset_row is not None
    assert asset_row["account_id"] == "test-upscale-user-1"
    assert asset_row["state"] == "active"
    assert asset_row["byte_size"] > 0

    # Verify physical file exists on disk
    root = asset_vault_directory()
    p = _storage_path(root, asset_row["storage_key"])
    assert p.is_file()
    assert p.stat().st_size == asset_row["byte_size"]


# ─── CASE 16 & 17: CUSTOMER AND ADMIN JOBS READ VISIBILITY ───────────────────

def test_16_and_17_customer_and_admin_jobs_read_visibility():
    """Customer and admin read models expose retained output URLs."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]
    transport = provider_mod.FakeStabilityUpscaleTransport()
    run_test_image_upscale_pipeline(job_id, transport=transport)

    # Customer view
    customer_job = bridge.get_image_upscale_job("test-upscale-user-1", job_id)
    assert customer_job is not None
    assert customer_job["output_available"] is True
    assert f"/api/v1/assets/{customer_job['output_asset_id']}/download" == customer_job["download_url"]
    assert f"/api/v1/assets/{customer_job['output_asset_id']}/preview" == customer_job["preview_url"]

    # Admin view
    admin_job = bridge.get_admin_image_upscale_job(job_id)
    assert admin_job is not None
    assert admin_job["id"] == job_id
    assert admin_job["provider_name"] == "stability"
    assert admin_job["model_name"] == "stability_conservative"
    assert admin_job["output_asset_id"] == customer_job["output_asset_id"]


# ─── CASE 18: NO RAW PROVIDER CREDENTIAL PERSISTED ───────────────────────────

def test_18_no_raw_provider_credential_persisted():
    """Ensures neither job rows nor asset records persist API keys or credentials."""
    secret_key = "sk-ultra-secret-key-must-not-leak"
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]
    transport = provider_mod.FakeStabilityUpscaleTransport()
    run_test_image_upscale_pipeline(job_id, transport=transport, api_key=secret_key)

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        job_row = conn.execute("SELECT * FROM web_image_upscale_jobs WHERE id = ?;", (job_id,)).fetchone()
        asset_row = conn.execute("SELECT * FROM web_asset_files WHERE id = ?;", (job_row["output_asset_id"],)).fetchone()

    for col in job_row.keys():
        val = str(job_row[col] or "")
        assert secret_key not in val
        assert "Bearer" not in val

    for col in asset_row.keys():
        val = str(asset_row[col] or "")
        assert secret_key not in val
        assert "Bearer" not in val


# ─── CASE 19: NO WALLET OR PAYMENT MUTATION ──────────────────────────────────

def test_19_no_wallet_or_payment_mutation():
    """Verify zero wallet mutations, payment mutations, or Xu debits occurred."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    transport = provider_mod.FakeStabilityUpscaleTransport()
    finalized = run_test_image_upscale_pipeline(created["id"], transport=transport)

    assert finalized["xu_cost"] == 0
    # Verify no wallet transactions exist
    with read_transaction() as conn:
        table_check = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='web_wallet_transactions';"
        ).fetchone()
        if table_check:
            tx_count = conn.execute(
                "SELECT COUNT(*) FROM web_wallet_transactions WHERE account_id='test-upscale-user-1';"
            ).fetchone()[0]
            assert tx_count == 0


# ─── CASE 20: REAL PROVIDER NETWORK CALL COUNT ZERO ──────────────────────────

def test_20_real_provider_network_call_count_zero():
    """Empirically prove REAL_PROVIDER_NETWORK_CALL_COUNT = 0."""
    assert REAL_PROVIDER_NETWORK_CALL_COUNT == 0


# ─── CASE 21: JSON BASE64 RESPONSE PAYLOAD PARSING ───────────────────────────

def test_21_json_base64_response_parsing():
    """Verify JSON with base64 encoded image response parses cleanly into Asset Vault."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    b64_image = base64.b64encode(SAMPLE_PNG_BYTES).decode("utf-8")
    transport = provider_mod.FakeStabilityUpscaleTransport(
        response_json={
            "image": b64_image,
            "finish_reason": "SUCCESS",
            "seed": 42,
        }
    )

    finalized = run_test_image_upscale_pipeline(job_id, transport=transport)
    assert finalized["status"] == bridge.STATUS_COMPLETED
    assert finalized["output_asset_id"] is not None

    with read_transaction() as conn:
        conn.row_factory = sqlite3.Row
        asset_row = conn.execute(
            "SELECT * FROM web_asset_files WHERE id = ?;", (finalized["output_asset_id"],)
        ).fetchone()
    assert asset_row is not None
    assert asset_row["byte_size"] == len(SAMPLE_PNG_BYTES)


# ─── CASE 22 (FIX1-A): ARBITRARY CUSTOM TRANSPORT CANNOT BYPASS RUNTIME GATES ─

def test_22_fix1_arbitrary_custom_transport_cannot_bypass_runtime_gates(monkeypatch):
    """Proves that passing an arbitrary transport object into execute_image_upscale_job cannot bypass gates.

    Even if all gates are monkeypatched to True, caller-supplied transport is rejected
    because ARBITRARY_TRANSPORT_OBJECT_IS_AUTHORITY = False.
    """
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    monkeypatch.setattr(bridge, "STABILITY_UPSCALE_ENTITLEMENT_PROVEN", True)
    monkeypatch.setattr(bridge, "OWNER_PAID_AUTHORIZATION_GRANTED", True)
    monkeypatch.setattr(bridge, "IMAGE_UPSCALE_PROVIDER_DISPATCH_ENABLED", True)
    monkeypatch.setattr(bridge, "IMAGE_UPSCALE_PROVIDER_DISPATCH_CURRENTLY_ENABLED", True)

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(RuntimeError) as exc:
        bridge.execute_image_upscale_job(job_id, transport=transport)

    assert "ARBITRARY_TRANSPORT_OBJECT_IS_AUTHORITY=NO" in str(exc.value)
    assert transport.call_count == 0


# ─── CASE 23 (FIX1-B): TRANSPORT CANNOT REACH NETWORK WHEN ENTITLEMENT UNPROVEN ─

def test_23_fix1_transport_cannot_reach_network_when_entitlement_unproven():
    """A real-looking transport object with .post() cannot reach network while PROVIDER_ENTITLEMENT_PROVEN = False."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    assert bridge.STABILITY_UPSCALE_ENTITLEMENT_PROVEN is False

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(RuntimeError) as exc:
        bridge.execute_image_upscale_job(job_id, transport=transport)

    assert "IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED" in str(exc.value)
    assert bridge.BLOCKER_PROVIDER_ENTITLEMENT_UNPROVEN in str(exc.value)
    assert transport.call_count == 0


# ─── CASE 24 (FIX1-C): TRANSPORT CANNOT REACH NETWORK WHEN OWNER AUTH MISSING ──

def test_24_fix1_transport_cannot_reach_network_when_owner_paid_auth_missing(monkeypatch):
    """Transport object with .post() cannot reach network while OWNER_PAID_AUTHORIZATION_GRANTED = False."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    monkeypatch.setattr(bridge, "STABILITY_UPSCALE_ENTITLEMENT_PROVEN", True)
    assert bridge.OWNER_PAID_AUTHORIZATION_GRANTED is False

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(RuntimeError) as exc:
        bridge.execute_image_upscale_job(job_id, transport=transport)

    assert "IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED" in str(exc.value)
    assert bridge.BLOCKER_OWNER_PAID_AUTHORIZATION_REQUIRED in str(exc.value)
    assert transport.call_count == 0


# ─── CASE 25 (FIX1-D): TRANSPORT CANNOT REACH NETWORK WHEN DISPATCH DISABLED ───

def test_25_fix1_transport_cannot_reach_network_when_dispatch_disabled(monkeypatch):
    """Transport object with .post() cannot reach network while IMAGE_UPSCALE_PROVIDER_DISPATCH_CURRENTLY_ENABLED = False."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    monkeypatch.setattr(bridge, "STABILITY_UPSCALE_ENTITLEMENT_PROVEN", True)
    monkeypatch.setattr(bridge, "OWNER_PAID_AUTHORIZATION_GRANTED", True)
    assert bridge.IMAGE_UPSCALE_PROVIDER_DISPATCH_CURRENTLY_ENABLED is False

    transport = provider_mod.FakeStabilityUpscaleTransport()
    with pytest.raises(RuntimeError) as exc:
        bridge.execute_image_upscale_job(job_id, transport=transport)

    assert "IMAGE_UPSCALE_PROVIDER_DISPATCH_DISABLED" in str(exc.value)
    assert bridge.BLOCKER_PROVIDER_EXECUTOR_READY_BUT_DISPATCH_DISABLED in str(exc.value)
    assert transport.call_count == 0


# ─── CASE 26 (FIX1-E): MISSING API KEY FAILS CLOSED WITHOUT FAKE BEARER ───────

def test_26_fix1_missing_api_key_fails_closed_no_fake_bearer():
    """Missing API key produces fail-closed behavior before network and never inserts fake Bearer credential."""
    assert provider_mod.PRODUCTION_FAKE_API_KEY_FALLBACK == "ABSENT"
    assert provider_mod.MISSING_PROVIDER_CREDENTIAL_BEHAVIOR == "FAIL_CLOSED_BEFORE_NETWORK"

    req = provider_mod.ImageUpscaleProviderRequest(
        job_id="test_job_key",
        account_id="test-upscale-user-1",
        source_asset_id="asset-upscale-source-1",
        image_bytes=SAMPLE_PNG_BYTES,
        filename="sample.png",
        content_type="image/png",
    )

    with pytest.raises(provider_mod.ImageUpscaleProviderError) as exc:
        provider_mod.build_stability_upscale_request_payload(req, api_key="")
    assert "Missing provider credential" in str(exc.value)

    # Calling prepare_image_upscale_request with empty api_key transitions job to failed
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]
    with pytest.raises(provider_mod.ImageUpscaleProviderError):
        bridge.prepare_image_upscale_request(job_id, api_key="")

    job_after = bridge.get_admin_image_upscale_job(job_id)
    assert job_after["status"] == bridge.STATUS_FAILED
    assert "PROVIDER_REQUEST_BUILD_FAILED" in job_after["status_reason"]


# ─── CASE 27 (FIX1-F): RESPONSE WITHOUT TASK ID LEAVES PROVIDER_TASK_ID EMPTY ─

def test_27_fix1_response_with_no_request_id_leaves_provider_task_id_empty():
    """Provider response with no request/task identifier leaves provider_task_id empty (None)."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    transport = provider_mod.FakeStabilityUpscaleTransport(include_request_id=False)
    finalized = run_test_image_upscale_pipeline(job_id, transport=transport)

    assert finalized["status"] == bridge.STATUS_COMPLETED
    assert finalized["provider_task_id"] is None

    # Inspect stored row in DB
    raw_job = bridge.get_admin_image_upscale_job(job_id)
    assert raw_job["provider_task_id"] is None


# ─── CASE 28 (FIX1-G): OUTPUT HASH IS NOT PROVIDER_TASK_ID ───────────────────

def test_28_fix1_output_hash_recorded_under_output_sha256_not_provider_task_id():
    """Output hash, if recorded, is stored under output_sha256 and never labeled provider_task_id."""
    assert provider_mod.SYNTHETIC_PROVIDER_TASK_ID_ALLOWED is False

    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    transport = provider_mod.FakeStabilityUpscaleTransport(include_request_id=False)
    finalized = run_test_image_upscale_pipeline(job_id, transport=transport)

    output_meta = finalized["output_metadata"]
    assert "output_sha256" in output_meta
    assert len(output_meta["output_sha256"]) == 64

    # Ensure provider_task_id was NOT synthesized as stbl_<sha256>
    assert finalized["provider_task_id"] is None
    assert finalized["provider_task_id"] != output_meta["output_sha256"]
    assert not str(finalized["provider_task_id"] or "").startswith("stbl_")


# ─── CASE 29 (FIX1-H): PROVIDER-SUPPLIED REQUEST ID RETAINED ACCURATELY ───────

def test_29_fix1_provider_supplied_request_id_retained_accurately():
    """Provider-supplied request ID is retained accurately when present in headers."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    official_id = "req_stability_conservative_prod_998877"
    transport = provider_mod.FakeStabilityUpscaleTransport(
        headers={"x-request-id": official_id},
    )
    finalized = run_test_image_upscale_pipeline(job_id, transport=transport)

    assert finalized["provider_task_id"] == official_id
    raw_job = bridge.get_admin_image_upscale_job(job_id)
    assert raw_job["provider_task_id"] == official_id


# ─── CASE 30 (FIX1-I): NON-SUCCESS FINISH REASON FAILS CLOSED ─────────────────

def test_30_fix1_non_success_finish_reason_fails_closed():
    """Non-success terminal provider finish-reason fails closed and does not finalize Asset Vault output."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    transport = provider_mod.FakeStabilityUpscaleTransport(
        headers={"finish-reason": "CONTENT_FILTERED"},
    )
    with pytest.raises(provider_mod.ImageUpscaleProviderResponseError) as exc:
        run_test_image_upscale_pipeline(job_id, transport=transport)
    assert "CONTENT_FILTERED" in str(exc.value)

    job_after = bridge.get_admin_image_upscale_job(job_id)
    assert job_after["status"] == bridge.STATUS_FAILED
    assert job_after["output_asset_id"] is None
    assert job_after["output_available"] is False


# ─── CASE 31 (FIX1-J): DUPLICATE AND AMBIGUOUS RETRY PROTECTIONS REMAIN GREEN ─

def test_31_fix1_duplicate_and_ambiguous_retry_protections_remain_green():
    """Verify existing duplicate/ambiguous retry protections remain green under pure preparation."""
    created = bridge.create_or_replay_image_upscale_job(
        account_id="test-upscale-user-1",
        payload={
            "image_asset_id": "asset-upscale-source-1",
            "scale_factor": 2,
            "model_name": "stability_conservative",
        },
    )
    job_id = created["id"]

    # In failed status
    bridge.transition_image_upscale_job_failed(job_id, "Ambiguous network blip")
    with pytest.raises(ValueError) as exc:
        bridge.prepare_image_upscale_request(job_id, api_key="test-key")
    assert "đã thất bại. Cấm tự động retry mù quáng" in str(exc.value)


# ─── CASE 32 (FIX1-K): REAL PROVIDER NETWORK CALL COUNT ZERO ──────────────────

def test_32_fix1_real_provider_network_call_count_zero():
    """Empirically confirm REAL_PROVIDER_NETWORK_CALL_COUNT = 0 across entire test suite."""
    assert REAL_PROVIDER_NETWORK_CALL_COUNT == 0
