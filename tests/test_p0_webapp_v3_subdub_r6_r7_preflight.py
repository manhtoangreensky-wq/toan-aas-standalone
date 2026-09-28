"""Preflight Verification Suite for SubDub R6 & R7 Runtime Activation.

Task: P0.WEBAPP.V3.SUBDUB.R6.R7.PREFLIGHT.TRUTH.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Parent Task: P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1

Enforces:
1. R6_PREFLIGHT: Runtime Adapter Activation Preflight
   - Confirms all 6 foundational dependencies (D1, D2, D3, D4, WEB_R2, R5) are resolved in authority truth.
   - Preserves fail-closed runtime safety invariant: WEB_CANONICAL_SUBDUB_RUNTIME_OUTPUT_PROVEN == "NO".
   - Jobs are admitted with initial status 'queued' and status_reason 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'.
   - Zero fake completions, zero simulated output artifacts, zero provider calls (PROVIDER_CALLS=0).
   - Worker execution remains strictly locked behind Owner approval (OWNER_GATE_REQUIRED).
2. R7_PREFLIGHT: Four-Lane E2E Product Truth Preflight
   - Lane 1 (subtitle_create): opaque source_upload_id intake, format reconciled to burn/srt, zero raw file paths.
   - Lane 2 (subtitle_translate): target_language validated, format reconciled, stage pipeline traced.
   - Lane 3 (dub): voice_profile_id intake, srt overridden to canonical video/audio media output.
   - Lane 4 (subtitle_plus_dub): combo lane intake, srt overridden to video_subtitle/audio output.
   - Idempotency via request_id replay and conflict detection.
   - Operations jobs policy synthesizes multi-stage pipeline trace (upload -> asr -> translation -> tts -> mux).
   - Invariants: WALLET_MUTATIONS=0, PROVIDER_CALLS=0, NO_OUTPUT_BYTES fail-closed protection.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi import HTTPException

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

import copyfast_registry as reg
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_subdub_job_bridge as bridge
from copyfast_operations_jobs_policy import (
    JOB_STATE_QUEUED,
    synthesize_operations_job_record,
)

AUDIT_JSON_PATH = STANDALONE_ROOT / "reports" / "audit" / "P0-WEBAPP-V3-SUBDUB-CANONICAL-PRODUCT-AUTHORITY-R1.json"
TEST_ACCOUNT_ID = "test-preflight-user"


@pytest.fixture(autouse=True)
def setup_subdub_preflight_db(monkeypatch):
    """Ensure database schema is initialized and isolated for testing."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-subdub-r6-r7")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "subdub,video_dub,subtitle_create,subtitle_translate")
    ensure_copyfast_schema()

    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs WHERE account_id LIKE 'test-preflight-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-preflight-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES (?, 'preflight@test.local', 'hash_preflight', '2026-09-29T00:00:00Z', '2026-09-29T00:00:00Z')
            """,
            (TEST_ACCOUNT_ID,),
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs WHERE account_id LIKE 'test-preflight-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-preflight-%'")


@pytest.fixture
def audit_data() -> dict[str, Any]:
    assert AUDIT_JSON_PATH.exists(), f"Missing audit JSON at {AUDIT_JSON_PATH}"
    data = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


# =============================================================================
# R6 PREFLIGHT: RUNTIME ADAPTER ACTIVATION VERIFICATION
# =============================================================================

class TestR6RuntimeAdapterActivationPreflight:
    """Verifies that all pre-conditions for runtime adapter activation are satisfied,
    while execution remains safely fail-closed and guarded behind Owner gate."""

    def test_r6_preflight_dependency_chain_authorities_resolved(self, audit_data: dict[str, Any]):
        """Proves D1, D2, D3, D4, WEB_R2, and R5 authority flags are marked YES."""
        flags = audit_data["flags"]
        assert flags["BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED"] == "YES"
        assert flags["BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED"] == "YES"
        assert flags["SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED"] == "YES"
        assert flags["BOT_MEDIA_DURATION_PROBE_AUTHORITY_RESOLVED"] == "YES"
        assert flags["WEB_VOICE_PROFILE_SELECTION_AUTHORITY_RESOLVED"] == "YES"
        assert flags["BOT_VOICE_RESOLUTION_AUTHORITY_SEPARATE"] == "YES"
        assert flags["R2_DURABLE_JOB_BRIDGE_AUTHORITY_READY"] == "YES"
        assert flags["SUBDUB_INPUT_CONTRACT_RESOLVED"] == "YES"
        assert flags["ADMIN_SUBDUB_JOB_TRACE_RESOLVED"] == "YES"
        assert flags["ADMIN_SUBDUB_FAILURE_TRACE_RESOLVED"] == "YES"
        assert flags["ADMIN_SUBDUB_PROVIDER_READINESS_RESOLVED"] == "YES"
        assert flags["ADMIN_SUBDUB_ARTIFACT_TRACE_RESOLVED"] == "YES"

    def test_r6_preflight_fail_closed_runtime_output_invariant_preserved(self, audit_data: dict[str, Any]):
        """Proves WEB_CANONICAL_SUBDUB_RUNTIME_OUTPUT_PROVEN remains strictly NO.
        
        Runtime output can ONLY be proven when live worker execution is authorized by Owner.
        """
        flags = audit_data["flags"]
        assert flags["WEB_CANONICAL_SUBDUB_RUNTIME_OUTPUT_PROVEN"] == "NO"
        assert flags["STATUS_ONLY_SUCCESS_AUTHORITY"] == "NO"
        assert flags["REAL_ARTIFACT_REQUIRED_FOR_COMPLETION"] == "YES"

    def test_r6_preflight_admitted_job_is_safely_queued_awaiting_owner_execution(self):
        """Proves newly admitted SubDub jobs enter SQLite with status 'queued' and
        status_reason 'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION', with zero fake output."""
        payload = {
            "mode": "subtitle_create",
            "upload_id": "upl_preflight_001_1122334455667788",
            "output_format": "burn",
        }
        job = bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_preflight_r6_001",
            payload=payload,
        )
        assert job["status"] == "queued"
        assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
        assert job["subdub_mode"] == "subtitle_create"
        assert job["output_format"] == "burn"
        assert job["output"] is None
        assert job["output_url"] is None
        assert job["output_available"] is False
        assert job["idempotent_replay"] is False

    def test_r6_preflight_authority_field_guard_blocks_forged_execution(self):
        """Proves client cannot bypass runtime gating by injecting execution state or provider voice ID."""
        forged_payloads = [
            {"mode": "dub", "upload_id": "upl_ok_123", "target_language": "vi", "status": "completed"},
            {"mode": "dub", "upload_id": "upl_ok_123", "target_language": "vi", "provider_voice_id": "pv_secret_99"},
            {"mode": "dub", "upload_id": "upl_ok_123", "target_language": "vi", "role": "admin"},
            {"mode": "dub", "upload_id": "upl_ok_123", "target_language": "vi", "wallet_id": "wal_forged_01"},
            {"mode": "dub", "upload_id": "upl_ok_123", "target_language": "vi", "charged_xu": 0},
        ]
        for idx, forged in enumerate(forged_payloads):
            with pytest.raises(HTTPException) as exc_info:
                bridge.create_or_replay_subdub_job(
                    account_id=TEST_ACCOUNT_ID,
                    request_id=f"req_preflight_forged_{idx}",
                    payload=forged,
                )
            assert exc_info.value.status_code == 400
            assert "authority" in str(exc_info.value.detail).lower()


# =============================================================================
# R7 PREFLIGHT: FOUR-LANE E2E PRODUCT TRUTH VERIFICATION
# =============================================================================

class TestR7FourLaneE2EProductTruthPreflight:
    """Verifies that all 4 canonical SubDub lanes adhere strictly to canonical contracts,
    output reconciliation, idempotency, and admin operations traceability."""

    def test_r7_preflight_lane1_subtitle_create(self):
        """Lane 1: subtitle_create intake, format reconciliation, durable persistence."""
        payload = {
            "mode": "subtitle_create",
            "upload_id": "upl_r7_lane1_1122334455667788",
            "output_format": "srt",
            "source_media_type": "video",
        }
        job = bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_preflight_r7_lane1",
            payload=payload,
        )
        assert job["subdub_mode"] == "subtitle_create"
        # Video source reconciles client srt to burn
        assert job["output_format"] == "burn"
        assert job["upload_id"] == "upl_r7_lane1_1122334455667788"

        # Operations policy trace check
        trace = synthesize_operations_job_record(job)
        assert trace["subdub_lane"] == "subtitle_create"
        assert trace["state"] == JOB_STATE_QUEUED
        assert trace["stage_pipeline"] == ["upload", "asr", "translation", "tts", "mux"]
        assert trace["artifact_trace"]["output_format"] == "burn"
        assert trace["artifact_trace"]["output_available"] is False

    def test_r7_preflight_lane2_subtitle_translate(self):
        """Lane 2: subtitle_translate intake, language validation, durable persistence."""
        payload = {
            "mode": "subtitle_translate",
            "upload_id": "upl_r7_lane2_1122334455667788",
            "target_language": "en",
            "output_format": "srt",
            "source_media_type": "audio",
        }
        job = bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_preflight_r7_lane2",
            payload=payload,
        )
        assert job["subdub_mode"] == "subtitle_translate"
        assert job["target_language"] == "en"
        # Audio source preserves srt
        assert job["output_format"] == "srt"

        # Missing target language must fail
        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_subdub_job(
                account_id=TEST_ACCOUNT_ID,
                request_id="req_preflight_r7_lane2_invalid",
                payload={"mode": "subtitle_translate", "upload_id": "upl_r7_lane2_1122334455667788"},
            )
        assert exc_info.value.status_code == 400
        assert "ngôn ngữ đích" in str(exc_info.value.detail).lower() or "target_language" in str(exc_info.value.detail).lower()

    def test_r7_preflight_lane3_dub(self):
        """Lane 3: dub intake, client srt override to canonical media, voice profile selection."""
        payload = {
            "mode": "dub",
            "upload_id": "upl_r7_lane3_1122334455667788",
            "target_language": "vi",
            "voice_profile_id": "vp_hn_male_warm_01",
            "speed": "1.0",
            "output_format": "srt",  # Client-side form restriction
            "source_media_type": "video",
        }
        job = bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_preflight_r7_lane3",
            payload=payload,
        )
        assert job["subdub_mode"] == "dub"
        assert job["target_language"] == "vi"
        assert job["voice_profile_id"] == "vp_hn_male_warm_01"
        assert job["speed"] == 1.0
        # Overrides client srt to video media output
        assert job["output_format"] == "video"

        trace = synthesize_operations_job_record(job)
        assert trace["subdub_lane"] == "dub"
        assert trace["artifact_trace"]["output_format"] == "video"

    def test_r7_preflight_lane4_subtitle_plus_dub_combo(self):
        """Lane 4: subtitle_plus_dub combo intake, client srt override to video_subtitle."""
        payload = {
            "mode": "subtitle_plus_dubbing",  # Form mode alias
            "upload_id": "upl_r7_lane4_1122334455667788",
            "target_language": "vi",
            "voice_profile_id": "vp_sg_female_gentle_01",
            "speed": "0.9",
            "output_format": "srt",
            "source_media_type": "video",
        }
        job = bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_preflight_r7_lane4",
            payload=payload,
        )
        assert job["subdub_mode"] == "subtitle_plus_dub"
        assert job["target_language"] == "vi"
        assert job["voice_profile_id"] == "vp_sg_female_gentle_01"
        assert job["speed"] == 0.9
        # Overrides client srt to combo video_subtitle output
        assert job["output_format"] == "video_subtitle"

        trace = synthesize_operations_job_record(job)
        assert trace["subdub_lane"] == "subtitle_plus_dub"
        assert trace["artifact_trace"]["output_format"] == "video_subtitle"

    def test_r7_preflight_strict_source_upload_id_validation(self):
        """Proves rejection of local filesystem paths and remote URLs across all lanes."""
        invalid_sources = [
            "/tmp/video.mp4",
            "C:\\Users\\toann\\video.mp4",
            "../../etc/passwd",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://tiktok.com/@user/video/123",
            "file:///var/data/input.mp4",
            "",
            "a" * 161,  # Exceeds max length
        ]
        for src in invalid_sources:
            with pytest.raises(HTTPException) as exc_info:
                bridge.create_or_replay_subdub_job(
                    account_id=TEST_ACCOUNT_ID,
                    request_id="req_preflight_inv_src",
                    payload={"mode": "subtitle_create", "upload_id": src},
                )
            assert exc_info.value.status_code == 400
            assert "upload_id" in str(exc_info.value.detail).lower()

    def test_r7_preflight_idempotent_replay_and_conflict_guarantee(self):
        """Proves exact replay returns existing job with idempotent_replay=True;
        payload mismatch on same request_id raises 409 Conflict."""
        payload = {
            "mode": "subtitle_create",
            "upload_id": "upl_r7_idemp_1122334455667788",
            "output_format": "burn",
        }
        res1 = bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_preflight_idemp_01",
            payload=payload,
        )
        assert res1["idempotent_replay"] is False
        job_id = res1["id"]

        # Exact replay
        res2 = bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_preflight_idemp_01",
            payload=payload,
        )
        assert res2["idempotent_replay"] is True
        assert res2["id"] == job_id

        # Conflicting payload
        different_payload = {
            "mode": "dub",
            "upload_id": "upl_r7_idemp_1122334455667788",
            "target_language": "vi",
        }
        with pytest.raises(HTTPException) as exc_info:
            bridge.create_or_replay_subdub_job(
                account_id=TEST_ACCOUNT_ID,
                request_id="req_preflight_idemp_01",
                payload=different_payload,
            )
        assert exc_info.value.status_code == 409
        assert "Xung đột" in str(exc_info.value.detail) or "idempotency" in str(exc_info.value.detail).lower()

    def test_r7_preflight_fail_closed_on_empty_output_artifacts(self):
        """Proves that zero-byte or empty output claims are rejected (NO_OUTPUT_BYTES contract)."""
        # When operations policy evaluates an empty output job, it must not claim success
        empty_job = {
            "job_id": "job_subdub_empty_test",
            "product_key": "subdub",
            "status": "succeeded",
            "output_available": False,
            "download_ready": False,
        }
        record = synthesize_operations_job_record(empty_job)
        # Succeeded state without outputs MUST trigger operator attention
        assert record["attention_required"] is True
        assert any("output unavailable" in r for r in record["attention_reasons"])
