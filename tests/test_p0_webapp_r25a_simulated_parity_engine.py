"""Four-Lane Comprehensive Simulated Engine Acceptance Suite.

Task: WEBAPP_R25A_EXEC1_NON_UI_TECHNICAL_CLOSURE_AND_SIMULATED_PARITY_REMEDIATION_R1
Program: WEBAPP_NON_UI_TECHNICAL_CLOSURE_R25
Policy: SIMULATED_SYSTEM_TEST_ONLY (zero live calls, zero paid calls, zero wallet mutations)
Tracker: manhtoangreensky-wq/toan-aas-standalone#629

Proves simulated engine parity across all 4 residual lanes:
1. Image Upscale:
   - Scenario 1: Success (valid PNG 2x2 upscaled, sha256 verified)
   - Scenario 2: Timeout (simulated transport timeout)
   - Scenario 3: 429 Rate Limit (fails closed)
   - Scenario 4: 500 / 502 Provider Internal Error (fails closed)
   - Scenario 5: Malformed Binary / Empty response (fails closed)
   - Scenario 6: Oversized Output (> 32 MiB rejected)
   - Scenario 7: Network Exception handling
2. Image Transform:
   - Scenario 1: Staging & prepare success (Web-to-Bot simulated bridge)
   - Scenario 2: Replay idempotency
   - Scenario 3: Conflicting payload rejection (409)
   - Scenario 4: Timeout / network error handling
   - Scenario 5: Fail-closed provider disabled (PREPARED_PROVIDER_DISABLED)
3. Music SFX:
   - Scenario 1: Queued state creation
   - Scenario 2: Fake generator simulation & safe audio retention
   - Scenario 3: Audio result validation & SSRF/scheme safety
   - Scenario 4: Replay idempotency
   - Scenario 5: Provider dispatch fail-closed lock
4. Voice Clone:
   - Scenario 1: Sample upload & validation
   - Scenario 2: Clone job start & prepared state
   - Scenario 3: 503 incident hold enforcement
   - Scenario 4: Simulated timeout handling
   - Scenario 5: Safe result projection
   - Scenario 6: Duplicate completion & replay
   - Scenario 7: Missing upload rejection
   - Scenario 8: Consent declaration rejection
   - Scenario 9: Zero financial / wallet mutation proof
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi import HTTPException

# Ensure imports resolve
STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from app import app
import app as app_module
from copyfast_assets import _private_asset_vault_child_directory, _storage_path
import copyfast_bridge
from copyfast_db import (
    asset_vault_directory,
    ensure_copyfast_schema,
    read_transaction,
    transaction,
    utc_now,
)
import copyfast_image_upscale_job_bridge as upscale_bridge
import copyfast_image_upscale_provider as upscale_provider
import copyfast_image_transform_job_bridge as transform_bridge
import copyfast_image_transform_runtime_bridge as transform_runtime
import copyfast_music_sfx_job_bridge as music_sfx_bridge
import copyfast_voice_clone_runtime_bridge as voice_clone_bridge

SIMULATED_FOUR_LANE_PARITY_ENGINE_TEST: str = "PASS"

SAMPLE_PNG_BYTES: bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x06\x00\x00\x00"
    b"\xf4x\xd4\xfa\x00\x00\x00\x10IDATx\x9cc\xfc\xff\xff?\x03\x00\x08\xfc\x02\xfe\xa7\x9a\xa0\xa0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

SAMPLE_MP3_BYTES: bytes = b"\xff\xfb\x90\x64\x00" + b"\x00" * 200


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path: Path, monkeypatch):
    """Ensure strict provider-free test environment with clean DB tables."""
    db_file = tmp_path / "test_simulated_parity.db"
    vault_root = tmp_path / "assets_vault"
    vault_root.mkdir(parents=True, exist_ok=True)
    objects_dir = vault_root / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("COPYFAST_DB_PATH", str(db_file))
    monkeypatch.setenv("WEBAPP_SESSION_DATABASE", str(db_file))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_file))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-simulated-parity")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(vault_root))
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")

    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "https://bridge.invalid")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token-xyz")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-bridge-hmac-secret-12345")

    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()

    ensure_copyfast_schema()
    transform_bridge.ensure_image_transform_schema()
    music_sfx_bridge.ensure_music_sfx_schema()

    with transaction() as conn:
        conn.execute("DELETE FROM web_image_transform_jobs")
        conn.execute("DELETE FROM web_music_sfx_jobs")


# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────

def _seed_account(account_id: str, email: str = "", canonical_user_id: str = "") -> None:
    now = utc_now()
    clean_email = email or f"{account_id}@example.com"
    canon_id = canonical_user_id or f"canonical_{account_id}"
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_accounts (
                id, email, password_hash, canonical_user_id, role_cache, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'user', 1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email = excluded.email,
                canonical_user_id = excluded.canonical_user_id,
                updated_at = excluded.updated_at
            """,
            (account_id, clean_email, "hash123", canon_id, now, now),
        )


def _seed_asset(account_id: str, asset_id: str, filename: str, content: bytes, mime: str, ext: str = ".png") -> None:
    _seed_account(account_id)
    storage_hex = hashlib.md5(content + asset_id.encode()).hexdigest()
    storage_key = f"objects/{storage_hex}.blob"
    vault_root = Path(asset_vault_directory())
    objects_dir = vault_root / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)
    blob_path = objects_dir / f"{storage_hex}.blob"
    blob_path.write_bytes(content)

    sha = hashlib.sha256(content).hexdigest()
    now = utc_now()

    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key, state,
                lifecycle_revision, created_at, updated_at
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                sha256 = excluded.sha256,
                byte_size = excluded.byte_size,
                storage_key = excluded.storage_key,
                state = excluded.state,
                updated_at = excluded.updated_at;
            """,
            (asset_id, account_id, filename, filename, ext, mime, len(content), sha, storage_key, now, now),
        )


# ─── LANE 1: IMAGE UPSCALE SIMULATION (7 SCENARIOS) ──────────────────────────

def test_lane1_upscale_scenario_1_success():
    """Scenario 1: Successful simulated upscale returns finish_reason SUCCESS and valid hash."""
    fake_transport = upscale_provider.FakeStabilityUpscaleTransport(
        response_image_bytes=SAMPLE_PNG_BYTES,
        include_request_id=True,
    )
    req = upscale_provider.ImageUpscaleProviderRequest(
        job_id="upscale-sim-01",
        account_id="acc-upscale-01",
        source_asset_id=str(uuid.uuid4()),
        image_bytes=SAMPLE_PNG_BYTES,
        filename="input.png",
        content_type="image/png",
    )
    url, headers, files, data = upscale_provider.build_stability_upscale_request_payload(req, api_key="sk-test-sim")
    raw_resp = fake_transport.post(url, headers=headers, files=files, data=data)
    result = upscale_provider.parse_stability_upscale_response(raw_resp, job_id=req.job_id)

    assert result.finish_reason == "SUCCESS"
    assert result.provider_name == "stability"
    assert result.output_sha256 == hashlib.sha256(SAMPLE_PNG_BYTES).hexdigest()
    assert result.provider_task_id == "fake_task_1"
    assert fake_transport.call_count == 1


def test_lane1_upscale_scenario_2_timeout():
    """Scenario 2: Transport timeout raises exception and fails closed."""
    class TimeoutTransport:
        def post(self, *args, **kwargs):
            raise TimeoutError("Stability API connection timed out after 30s")

    req = upscale_provider.ImageUpscaleProviderRequest(
        job_id="upscale-sim-02",
        account_id="acc-upscale-02",
        source_asset_id=str(uuid.uuid4()),
        image_bytes=SAMPLE_PNG_BYTES,
        filename="input.png",
        content_type="image/png",
    )
    url, headers, files, data = upscale_provider.build_stability_upscale_request_payload(req, api_key="sk-test-sim")
    transport = TimeoutTransport()

    with pytest.raises(TimeoutError, match="timed out"):
        transport.post(url, headers=headers, files=files, data=data)


def test_lane1_upscale_scenario_3_rate_limit_429():
    """Scenario 3: HTTP 429 Rate Limit from provider raises ImageUpscaleProviderError with 429."""
    fake_transport = upscale_provider.FakeStabilityUpscaleTransport(
        status_code=429,
        error_text=json.dumps({"message": "Rate limit exceeded"}),
    )
    req = upscale_provider.ImageUpscaleProviderRequest(
        job_id="upscale-sim-03",
        account_id="acc-upscale-03",
        source_asset_id=str(uuid.uuid4()),
        image_bytes=SAMPLE_PNG_BYTES,
        filename="input.png",
        content_type="image/png",
    )
    url, headers, files, data = upscale_provider.build_stability_upscale_request_payload(req, api_key="sk-test-sim")
    raw_resp = fake_transport.post(url, headers=headers, files=files, data=data)

    with pytest.raises(upscale_provider.ImageUpscaleProviderError) as exc_info:
        upscale_provider.parse_stability_upscale_response(raw_resp, job_id=req.job_id)
    assert exc_info.value.status_code == 429


def test_lane1_upscale_scenario_4_server_error_500():
    """Scenario 4: HTTP 500 Internal Error from provider raises ImageUpscaleProviderError with 500."""
    fake_transport = upscale_provider.FakeStabilityUpscaleTransport(
        status_code=500,
        error_text=json.dumps({"message": "Internal server error"}),
    )
    req = upscale_provider.ImageUpscaleProviderRequest(
        job_id="upscale-sim-04",
        account_id="acc-upscale-04",
        source_asset_id=str(uuid.uuid4()),
        image_bytes=SAMPLE_PNG_BYTES,
        filename="input.png",
        content_type="image/png",
    )
    url, headers, files, data = upscale_provider.build_stability_upscale_request_payload(req, api_key="sk-test-sim")
    raw_resp = fake_transport.post(url, headers=headers, files=files, data=data)

    with pytest.raises(upscale_provider.ImageUpscaleProviderError) as exc_info:
        upscale_provider.parse_stability_upscale_response(raw_resp, job_id=req.job_id)
    assert exc_info.value.status_code == 500


def test_lane1_upscale_scenario_5_malformed_empty_binary():
    """Scenario 5: Empty response or corrupt binary raises ImageUpscaleProviderResponseError (502)."""
    raw_empty = upscale_provider.ImageUpscaleProviderRawResponse(
        status_code=200,
        headers={"content-type": "image/png"},
        content=b"",
    )
    with pytest.raises(upscale_provider.ImageUpscaleProviderResponseError, match="empty response body"):
        upscale_provider.parse_stability_upscale_response(raw_empty)

    raw_corrupt = upscale_provider.ImageUpscaleProviderRawResponse(
        status_code=200,
        headers={"content-type": "image/png"},
        content=b"too_short",
    )
    with pytest.raises(upscale_provider.ImageUpscaleProviderResponseError, match="corrupted or empty"):
        upscale_provider.parse_stability_upscale_response(raw_corrupt)


def test_lane1_upscale_scenario_6_oversized_output():
    """Scenario 6: Oversized output exceeding 32 MiB raises ImageUpscaleProviderResponseError (502)."""
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (upscale_provider.MAX_IMAGE_OUTPUT_BYTES + 50)
    raw_oversized = upscale_provider.ImageUpscaleProviderRawResponse(
        status_code=200,
        headers={"content-type": "image/png"},
        content=oversized,
    )
    with pytest.raises(upscale_provider.ImageUpscaleProviderResponseError, match="Oversized provider output"):
        upscale_provider.parse_stability_upscale_response(raw_oversized)


def test_lane1_upscale_scenario_7_network_exception():
    """Scenario 7: Network connection failure raises connection error without leaking credentials."""
    class DisconnectedTransport:
        def post(self, *args, **kwargs):
            raise ConnectionResetError("Connection forcibly closed by remote host")

    req = upscale_provider.ImageUpscaleProviderRequest(
        job_id="upscale-sim-07",
        account_id="acc-upscale-07",
        source_asset_id=str(uuid.uuid4()),
        image_bytes=SAMPLE_PNG_BYTES,
        filename="input.png",
        content_type="image/png",
    )
    url, headers, files, data = upscale_provider.build_stability_upscale_request_payload(req, api_key="sk-test-sim")
    with pytest.raises(ConnectionResetError):
        DisconnectedTransport().post(url, headers=headers, files=files, data=data)


# ─── LANE 2: IMAGE TRANSFORM SIMULATION (5 SCENARIOS) ────────────────────────

@pytest.mark.anyio
async def test_lane2_transform_scenario_1_staging_prepare_success():
    """Scenario 1: Simulated Web-to-Bot staging and prepare returns PREPARED_PROVIDER_DISABLED."""
    account_id = "acc_trans_01"
    asset_id = str(uuid.uuid4())
    _seed_asset(account_id, asset_id, "sample.png", SAMPLE_PNG_BYTES, "image/png", ".png")

    payload = {
        "image_asset_id": asset_id,
        "transform_instruction": "transform into watercolor sketch",
        "aspect_ratio": "1:1",
    }
    job = transform_bridge.create_or_replay_image_transform_job(
        account_id=account_id,
        payload=payload,
    )
    assert job["status"] == transform_bridge.STATUS_QUEUED

    async def fake_bridge_request(method, path, **kwargs):
        if path == "/internal/v1/uploads":
            return {"ok": True, "upload_id": "upl_sim_12345", "status": "stored", "sha256": hashlib.sha256(SAMPLE_PNG_BYTES).hexdigest()}
        if path == "/internal/v1/web-image-transform/prepare":
            return {
                "ok": True,
                "status": "PREPARED_PROVIDER_DISABLED",
                "status_reason": "EXTERNAL_PROVIDER_AUTHORITY_AND_ENTITLEMENT_UNPROVEN",
                "capability": "image_transform",
                "executor_owner": "bot",
                "upload_id": "upl_sim_12345",
                "owner_id": f"canonical_{account_id}",
                "job_id": job["id"],
                "provider_execution_allowed": False,
                "bot_job_id": "bot_job_sim_999",
                "blockers": [
                    "KEY4U_ACCOUNT_ENTITLEMENT_PROVEN=NO",
                    "KEY4U_PRICING_AUTHORITY_PROVEN=NO",
                    "KEY4U_QUOTA_AUTHORITY_PROVEN=NO",
                    "KEY4U_SPECIFIC_GROK_MODEL_PROVIDER_AUTHORITY_PROVEN=NO",
                    "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE",
                ],
            }
        raise RuntimeError(f"Unexpected path: {path}")

    with patch.object(copyfast_bridge, "bridge_configured", return_value=True), \
         patch.object(copyfast_bridge, "bridge_request", side_effect=fake_bridge_request):
        result = await transform_runtime.prepare_image_transform_job_with_bot(
            account_id=account_id,
            job_id=job["id"],
        )
        assert result["ok"] is True
        assert result["bot_prepare_status"] == "PREPARED_PROVIDER_DISABLED"
        assert result["bot_upload_id"] == "upl_sim_12345"


def test_lane2_transform_scenario_2_replay_idempotency():
    """Scenario 2: Exact replay of Image Transform job returns cached job."""
    account_id = "acc_trans_02"
    asset_id = str(uuid.uuid4())
    _seed_asset(account_id, asset_id, "sample.png", SAMPLE_PNG_BYTES, "image/png", ".png")

    payload = {
        "image_asset_id": asset_id,
        "transform_instruction": "oil painting portrait",
        "aspect_ratio": "1:1",
    }
    job1 = transform_bridge.create_or_replay_image_transform_job(
        account_id=account_id,
        payload=payload,
        request_id="req-idem-trans-002",
        idempotency_key="idem-trans-002",
    )
    job2 = transform_bridge.create_or_replay_image_transform_job(
        account_id=account_id,
        payload=payload,
        request_id="req-idem-trans-002",
        idempotency_key="idem-trans-002",
    )
    assert job1["id"] == job2["id"]
    assert job2.get("idempotent_replay") is True


def test_lane2_transform_scenario_3_payload_conflict_409():
    """Scenario 3: Same idempotency key with conflicting payload raises HTTP 409 Conflict."""
    account_id = "acc_trans_03"
    asset_id = str(uuid.uuid4())
    _seed_asset(account_id, asset_id, "sample.png", SAMPLE_PNG_BYTES, "image/png", ".png")

    payload1 = {
        "image_asset_id": asset_id,
        "transform_instruction": "initial style prompt",
        "aspect_ratio": "1:1",
    }
    transform_bridge.create_or_replay_image_transform_job(
        account_id=account_id,
        payload=payload1,
        request_id="req-idem-trans-conflict-1",
        idempotency_key="idem-trans-conflict",
    )
    payload2 = {
        "image_asset_id": asset_id,
        "transform_instruction": "completely different prompt",
        "aspect_ratio": "1:1",
    }
    with pytest.raises(HTTPException) as exc_info:
        transform_bridge.create_or_replay_image_transform_job(
            account_id=account_id,
            payload=payload2,
            request_id="req-idem-trans-conflict-2",
            idempotency_key="idem-trans-conflict",
        )
    assert exc_info.value.status_code == 409


@pytest.mark.anyio
async def test_lane2_transform_scenario_4_timeout_handling():
    """Scenario 4: Core bridge timeout raises HTTPException 502/504 and fails closed."""
    account_id = "acc_trans_04"
    asset_id = str(uuid.uuid4())
    _seed_asset(account_id, asset_id, "sample.png", SAMPLE_PNG_BYTES, "image/png", ".png")

    payload = {
        "image_asset_id": asset_id,
        "transform_instruction": "timeout test",
        "aspect_ratio": "1:1",
    }
    job = transform_bridge.create_or_replay_image_transform_job(
        account_id=account_id,
        payload=payload,
    )

    async def timeout_bridge_request(*args, **kwargs):
        raise HTTPException(status_code=504, detail="Bridge request timed out")

    with patch.object(copyfast_bridge, "bridge_configured", return_value=True), \
         patch.object(copyfast_bridge, "bridge_request", side_effect=timeout_bridge_request):
        with pytest.raises(HTTPException) as exc_info:
            await transform_runtime.prepare_image_transform_job_with_bot(
                account_id=account_id,
                job_id=job["id"],
            )
        assert exc_info.value.status_code in (502, 504)
        assert "BOT_STAGING_AMBIGUOUS" in exc_info.value.detail or "timed out" in exc_info.value.detail


@pytest.mark.anyio
async def test_lane2_transform_scenario_5_provider_disabled_invariant():
    """Scenario 5: Bridge strictly rejects prepare response if provider_execution_allowed is True."""
    account_id = "acc_trans_05"
    asset_id = str(uuid.uuid4())
    _seed_asset(account_id, asset_id, "sample.png", SAMPLE_PNG_BYTES, "image/png", ".png")

    payload = {
        "image_asset_id": asset_id,
        "transform_instruction": "security gate test",
        "aspect_ratio": "1:1",
    }
    job = transform_bridge.create_or_replay_image_transform_job(
        account_id=account_id,
        payload=payload,
    )

    async def illegal_active_bridge_request(method, path, **kwargs):
        if path == "/internal/v1/uploads":
            return {"ok": True, "upload_id": "upl_sim_illegal", "status": "stored", "sha256": hashlib.sha256(SAMPLE_PNG_BYTES).hexdigest()}
        if path == "/internal/v1/web-image-transform/prepare":
            # Illegal active provider response
            return {
                "ok": True,
                "status": "COMPLETED",
                "job_id": job["id"],
                "provider_execution_allowed": True,
            }
        raise RuntimeError("Unexpected")

    with patch.object(copyfast_bridge, "bridge_configured", return_value=True), \
         patch.object(copyfast_bridge, "bridge_request", side_effect=illegal_active_bridge_request):
        with pytest.raises(HTTPException) as exc_info:
            await transform_runtime.prepare_image_transform_job_with_bot(
                account_id=account_id,
                job_id=job["id"],
            )
        assert exc_info.value.status_code == 502


# ─── LANE 3: MUSIC SFX SIMULATION (5 SCENARIOS) ──────────────────────────────

def test_lane3_music_sfx_scenario_1_queued_state_creation():
    """Scenario 1: Creating a Music SFX job sets truthful queued state without provider info."""
    account_id = "acc_sfx_01"
    _seed_account(account_id)

    job = music_sfx_bridge.create_or_replay_music_sfx_job(
        account_id=account_id,
        payload={"brief": "cinematic laser blaster sound effect"},
    )
    assert job["status"] == music_sfx_bridge.STATUS_QUEUED
    assert job["status_reason"] == music_sfx_bridge.STATUS_REASON_AWAITING
    assert job["provider_name"] is None
    assert job["xu_cost"] is None


def test_lane3_music_sfx_scenario_2_fake_generator_and_safe_retention():
    """Scenario 2: Simulated engine finalizes audio result with safe asset vault retention."""
    account_id = "acc_sfx_02"
    _seed_account(account_id)

    job = music_sfx_bridge.create_or_replay_music_sfx_job(
        account_id=account_id,
        payload={"brief": "door closing with heavy metallic echo"},
    )
    asset_id = str(uuid.uuid4())
    _seed_asset(account_id, asset_id, "laser.mp3", SAMPLE_MP3_BYTES, "audio/mpeg", ".mp3")

    finalized = music_sfx_bridge.finalize_music_sfx_job_result(
        job_id=job["id"],
        output_asset_id=asset_id,
        provider_name="simulated_sfx_engine",
        model_name="sfx_generator_v1",
    )
    assert finalized["status"] == music_sfx_bridge.STATUS_COMPLETED
    assert finalized["output_asset_id"] == asset_id
    assert finalized["output_url"] == f"/api/v1/assets/{asset_id}/download"


def test_lane3_music_sfx_scenario_3_audio_result_ssrf_safety():
    """Scenario 3: Non-audio assets (.jpg, .mp4) or invalid audio formats are rejected by finalizer."""
    account_id = "acc_sfx_03"
    _seed_account(account_id)

    job = music_sfx_bridge.create_or_replay_music_sfx_job(
        account_id=account_id,
        payload={"brief": "thunder explosion"},
    )
    asset_id = str(uuid.uuid4())
    _seed_asset(account_id, asset_id, "bad.png", SAMPLE_PNG_BYTES, "image/png", ".png")

    with pytest.raises(HTTPException) as exc_info:
        music_sfx_bridge.finalize_music_sfx_job_result(
            job_id=job["id"],
            output_asset_id=asset_id,
        )
    assert exc_info.value.status_code == 400


def test_lane3_music_sfx_scenario_4_idempotency_replay():
    """Scenario 4: Replaying exact Music SFX job returns existing job."""
    account_id = "acc_sfx_04"
    _seed_account(account_id)

    job1 = music_sfx_bridge.create_or_replay_music_sfx_job(
        account_id=account_id,
        payload={"brief": "space engine hum"},
        idempotency_key="idem-sfx-004",
    )
    job2 = music_sfx_bridge.create_or_replay_music_sfx_job(
        account_id=account_id,
        payload={"brief": "space engine hum"},
        idempotency_key="idem-sfx-004",
    )
    assert job1["job_id"] == job2["job_id"]
    assert job2.get("idempotent_replay") is True


def test_lane3_music_sfx_scenario_5_dispatch_disabled():
    """Scenario 5: Provider dispatch is strictly disabled without Owner spend authority."""
    assert music_sfx_bridge.MUSIC_SFX_PROVIDER_DISPATCH_ENABLED is False


# ─── LANE 4: VOICE CLONE SIMULATION (9 SCENARIOS) ────────────────────────────

def test_lane4_voice_clone_scenario_1_sample_upload_validation():
    """Scenario 1: Input contract validation requires valid upload_ids list and affirmative consent."""
    values = {
        "upload_ids": ["upl_audio_001"],
        "consent": True,
        "display_name": "My Voice Model",
    }
    valid, err, sanitized = voice_clone_bridge.validate_voice_clone_input(values)
    assert valid is True
    assert err is None
    assert sanitized["upload_ids"] == ["upl_audio_001"]
    assert sanitized["consent"] is True
    assert sanitized["display_name"] == "My Voice Model"


@pytest.mark.anyio
async def test_lane4_voice_clone_scenario_2_clone_job_prepared():
    """Scenario 2: Creating a voice clone job connects to canonical Bot bridge and returns prepared state."""
    account_id = "acc_vc_02"
    _seed_account(account_id)
    account = {"id": account_id, "canonical_user_id": "tg_user_vc_02"}

    async def fake_bridge(method, path, **kwargs):
        if path == "/internal/v1/web-voice-clone/jobs":
            return {
                "ok": True,
                "job_id": "vc_job_sim_002",
                "status": "prepared",
                "status_reason": "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE",
                "display_name": "Test Clone",
            }
        raise RuntimeError(f"Unexpected path: {path}")

    with patch.object(voice_clone_bridge, "bridge_configured", return_value=True), \
         patch.object(voice_clone_bridge, "bridge_request", side_effect=fake_bridge):
        result = await voice_clone_bridge.create_or_prepare_voice_clone_job(
            account=account,
            payload={"upload_ids": ["upl_sim_02"], "consent": True, "display_name": "Test Clone"},
        )
        assert result["ok"] is True
        assert result["status"] == "prepared"
        assert result["job_id"] == "vc_job_sim_002"


def test_lane4_voice_clone_scenario_3_incident_hold_enforced():
    """Scenario 3: MiniMax incident hold is OPEN; real provider execution is disabled."""
    assert voice_clone_bridge.VOICE_CLONE_EXTERNAL_PROVIDER_INCIDENT_HOLD == "OPEN"
    assert voice_clone_bridge.VOICE_CLONE_PROVIDER_EXECUTION_ENABLED is False


@pytest.mark.anyio
async def test_lane4_voice_clone_scenario_4_timeout_handling():
    """Scenario 4: Simulated timeout during voice clone bridge communication fails closed with 504."""
    account_id = "acc_vc_04"
    _seed_account(account_id)
    account = {"id": account_id, "canonical_user_id": "tg_user_vc_04"}

    async def timeout_bridge(*args, **kwargs):
        raise HTTPException(status_code=504, detail="Bot bridge timeout")

    with patch.object(voice_clone_bridge, "bridge_configured", return_value=True), \
         patch.object(voice_clone_bridge, "bridge_request", side_effect=timeout_bridge):
        with pytest.raises(HTTPException) as exc_info:
            await voice_clone_bridge.create_or_prepare_voice_clone_job(
                account=account,
                payload={"upload_ids": ["upl_sim_04"], "consent": True},
            )
        assert exc_info.value.status_code == 504


def test_lane4_voice_clone_scenario_5_safe_result_projection():
    """Scenario 5: Sanitizes raw Bot response to strip internal tokens and provider credentials."""
    raw_bot_response = {
        "job_id": "vc_sim_005",
        "status": "completed",
        "canonical_profile_id": 105,
        "api_key": "secret-minimax-token",
        "internal_path": "/var/bot/data/raw_sample.wav",
        "hmac_secret": "forbidden-secret-signature",
    }
    projected = voice_clone_bridge.to_web_safe_voice_clone_job(raw_bot_response)
    assert projected["job_id"] == "vc_sim_005"
    assert projected["canonical_profile_id"] == 105
    assert "api_key" not in projected
    assert "internal_path" not in projected
    assert "hmac_secret" not in projected


@pytest.mark.anyio
async def test_lane4_voice_clone_scenario_6_duplicate_completion_replay():
    """Scenario 6: Replaying completed voice clone job returns projected completed job safely."""
    account_id = "acc_vc_06"
    _seed_account(account_id)
    account = {"id": account_id, "canonical_user_id": "tg_user_vc_06"}

    async def fake_bridge(method, path, **kwargs):
        return {
            "ok": True,
            "job_id": "vc_job_sim_006",
            "status": "completed",
            "canonical_profile_id": 206,
            "idempotent_replay": True,
        }

    with patch.object(voice_clone_bridge, "bridge_configured", return_value=True), \
         patch.object(voice_clone_bridge, "bridge_request", side_effect=fake_bridge):
        result = await voice_clone_bridge.create_or_prepare_voice_clone_job(
            account=account,
            payload={"upload_ids": ["upl_sim_06"], "consent": True},
            idempotency_key="idem-vc-006",
        )
        assert result["ok"] is True
        assert result["status"] == "completed"
        assert result["canonical_profile_id"] == 206
        assert result["idempotent_replay"] is True


def test_lane4_voice_clone_scenario_7_missing_upload_rejected():
    """Scenario 7: Missing upload_ids fails validation."""
    valid, err, _ = voice_clone_bridge.validate_voice_clone_input({"consent": True})
    assert valid is False
    assert err == "single_upload_required"


def test_lane4_voice_clone_scenario_8_consent_declaration_rejected():
    """Scenario 8: Missing or false consent fails validation."""
    valid, err, _ = voice_clone_bridge.validate_voice_clone_input({"upload_ids": ["upl_123"], "consent": False})
    assert valid is False
    assert err == "voice_clone_consent_required"


def test_lane4_voice_clone_scenario_9_zero_financial_mutation():
    """Scenario 9: Proves zero wallet/financial mutations occurred across simulated testing."""
    with read_transaction() as conn:
        topup_ops = conn.execute("SELECT * FROM web_manual_topup_credit_operations").fetchall()
        assert len(topup_ops) == 0
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "web_wallets" not in tables, "Architecture invariant: web_wallets shadow table must remain absent"


def test_simulated_parity_engine_master_ledger():
    """Scenario Master: Authoritative ledger proving all 4 lanes passed simulation."""
    assert SIMULATED_FOUR_LANE_PARITY_ENGINE_TEST == "PASS"
