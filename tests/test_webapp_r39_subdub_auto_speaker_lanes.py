"""Tests for WebApp SubDub Auto-Speaker Lanes Canonical Job Bridge Parity (R39).

SPEC_ID: WEBAPP-R39-SUBDUB-AUTO-SPEAKER-LANES
Verifies:
- LANE_INCLUDED_IN_NORMALIZED_PAYLOAD
- LANE_INCLUDED_IN_PAYLOAD_HASH
- LANE_PERSISTED_IN_DURABLE_WEB_JOB
- COLD_READ_PRESERVES_LANE
- INVALID_LANE_FAILS_CLOSED
- CLIENT_SPEAKER_COUNT_CANNOT_FORGE_DETECTION
- CONFLICTING_VOICE_CONFIG_BLOCKED
- IDEMPOTENCY_HASH_INCLUDES_LANE
- REPLAY_SAME_LANE_IDEMPOTENT
- REPLAY_DIFFERENT_LANE_CONFLICT
- DISPATCH_FORWARDS_CANONICAL_LANE
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from copyfast_db import ensure_copyfast_schema, transaction, read_transaction
import copyfast_bridge as core_bridge
import copyfast_subdub_job_bridge as bridge


@pytest.fixture(autouse=True)
def setup_subdub_test_env(monkeypatch):
    """Setup test database, insert test accounts, and clean web_subdub_jobs table."""
    monkeypatch.setenv("APP_ENV", "test")
    ensure_copyfast_schema()
    bridge.ensure_subdub_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs")
        try:
            conn.execute("DELETE FROM copyfast_idempotency_keys")
        except Exception:
            pass
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('acc_test_user_1', 'user1@test.local', 'hash1', '2026-10-25T00:00:00Z', '2026-10-25T00:00:00Z'),
                   ('acc_test_user_2', 'user2@test.local', 'hash2', '2026-10-25T00:00:00Z', '2026-10-25T00:00:00Z'),
                   ('acc_test_user_3', 'user3@test.local', 'hash3', '2026-10-25T00:00:00Z', '2026-10-25T00:00:00Z'),
                   ('acc_test_user_4', 'user4@test.local', 'hash4', '2026-10-25T00:00:00Z', '2026-10-25T00:00:00Z')
            """
        )


def test_lane_included_in_normalized_payload():
    """Verify validate_subdub_input preserves and normalizes valid auto speaker lanes."""
    lanes = [
        ("auto_2", "auto_2"),
        ("auto_two", "auto_2"),
        ("auto_multi_3_8", "auto_multi_3_8"),
        ("multi", "auto_multi_3_8"),
        ("smart_multi", "smart_multi"),
        ("auto_smart_multivoice", "smart_multi"),
    ]
    for raw_lane, expected_lane in lanes:
        ok, reason, normalized = bridge.validate_subdub_input({
            "mode": "dub",
            "upload_id": "upl_test12345",
            "target_language": "vi",
            "auto_speaker_lane": raw_lane,
        })
        assert ok is True, f"Failed for lane {raw_lane}: {reason}"
        assert normalized["auto_speaker_lane"] == expected_lane


def test_invalid_lane_fails_closed():
    """Verify unknown auto_speaker_lane fails closed with INVALID_AUTO_SPEAKER_LANE."""
    ok, reason, _ = bridge.validate_subdub_input({
        "mode": "dub",
        "upload_id": "upl_test12345",
        "target_language": "vi",
        "auto_speaker_lane": "unknown_forged_lane",
    })
    assert ok is False
    assert reason == "INVALID_AUTO_SPEAKER_LANE"


def test_client_speaker_count_cannot_forge_detection():
    """Verify client cannot specify speaker_count, detected_speaker_count, or mapping internals."""
    forged_fields = [
        {"speaker_count": 4},
        {"detected_speaker_count": 3},
        {"speaker_mapping": "custom"},
        {"speaker_mapping_internals": "custom"},
        {"provider_voice_id": "secret"},
        {"provider_model_id": "model_xyz"},
        {"raw_worker_route": "custom_route"},
    ]
    for forged in forged_fields:
        ok, reason, _ = bridge.validate_subdub_input({
            "mode": "dub",
            "upload_id": "upl_test12345",
            "target_language": "vi",
            "auto_speaker_lane": "auto_2",
            **forged,
        })
        assert ok is False, f"Failed to block forged field: {forged}"
        assert reason == "authority_field_not_allowed"


def test_conflicting_voice_config_blocked():
    """Verify specifying both voice_profile_id and auto_speaker_lane fails closed."""
    ok, reason, _ = bridge.validate_subdub_input({
        "mode": "dub",
        "upload_id": "upl_test12345",
        "target_language": "vi",
        "voice_profile_id": "vp_123",
        "auto_speaker_lane": "auto_2",
    })
    assert ok is False
    assert reason == "CONFLICTING_VOICE_CONFIGURATION"


def test_idempotency_hash_includes_lane():
    """Verify compute_payload_hash distinguishes between different auto_speaker_lanes."""
    base_payload = {
        "upload_id": "upl_test12345",
        "subdub_mode": "dub",
        "source_language": "auto",
        "target_language": "vi",
        "voice_profile_id": "",
        "output_format": "mp4",
        "speed": 1.0,
        "product_key": "subdub",
    }

    hash_auto2 = bridge.compute_payload_hash({**base_payload, "auto_speaker_lane": "auto_2"})
    hash_multi = bridge.compute_payload_hash({**base_payload, "auto_speaker_lane": "auto_multi_3_8"})
    hash_smart = bridge.compute_payload_hash({**base_payload, "auto_speaker_lane": "smart_multi"})
    hash_none = bridge.compute_payload_hash({**base_payload, "auto_speaker_lane": ""})

    assert len({hash_auto2, hash_multi, hash_smart, hash_none}) == 4, "Payload hashes must all be unique across lanes"


def test_create_and_cold_read_preserves_lane():
    """Verify create_or_replay_subdub_job persists auto_speaker_lane and get_subdub_job cold read preserves it."""
    account_id = "acc_test_user_1"
    request_id = "req_lane_persist_001"

    job = bridge.create_or_replay_subdub_job(
        account_id=account_id,
        request_id=request_id,
        payload={
            "mode": "dub",
            "upload_id": "upl_test12345",
            "target_language": "vi",
            "auto_speaker_lane": "auto_multi_3_8",
        },
    )

    assert job["auto_speaker_lane"] == "auto_multi_3_8"
    job_id = job["id"]

    # Cold read from DB
    cold_job = bridge.get_subdub_job(account_id, job_id)
    assert cold_job is not None
    assert cold_job["auto_speaker_lane"] == "auto_multi_3_8"


def test_replay_same_lane_idempotent():
    """Verify replay with exact same payload and lane returns existing job with idempotent_replay=True."""
    account_id = "acc_test_user_2"
    request_id = "req_lane_replay_002"

    input_data = {
        "mode": "dub",
        "upload_id": "upl_test12345",
        "target_language": "vi",
        "auto_speaker_lane": "smart_multi",
    }

    job1 = bridge.create_or_replay_subdub_job(
        account_id=account_id,
        request_id=request_id,
        payload=input_data,
    )
    assert job1["idempotent_replay"] is False

    job2 = bridge.create_or_replay_subdub_job(
        account_id=account_id,
        request_id=request_id,
        payload=input_data,
    )
    assert job2["idempotent_replay"] is True
    assert job2["id"] == job1["id"]
    assert job2["auto_speaker_lane"] == "smart_multi"


def test_replay_different_lane_conflict():
    """Verify replaying different auto_speaker_lane on same request_id returns 409 Conflict."""
    account_id = "acc_test_user_3"
    request_id = "req_lane_conflict_003"

    bridge.create_or_replay_subdub_job(
        account_id=account_id,
        request_id=request_id,
        payload={
            "mode": "dub",
            "upload_id": "upl_test12345",
            "target_language": "vi",
            "auto_speaker_lane": "auto_2",
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_subdub_job(
            account_id=account_id,
            request_id=request_id,
            payload={
                "mode": "dub",
                "upload_id": "upl_test12345",
                "target_language": "vi",
                "auto_speaker_lane": "smart_multi",  # Different lane!
            },
        )
    assert exc_info.value.status_code == 409


def test_dispatch_subdub_job_forwards_lane(monkeypatch):
    """Verify dispatch_subdub_job_to_canonical_runtime forwards auto_speaker_lane in payload to Bot internal API."""
    account_id = "acc_test_user_4"
    request_id = "req_lane_dispatch_004"

    job = bridge.create_or_replay_subdub_job(
        account_id=account_id,
        request_id=request_id,
        payload={
            "mode": "dub",
            "upload_id": "upl_test12345",
            "target_language": "vi",
            "auto_speaker_lane": "smart_multi",
        },
    )

    posted_calls = []

    async def mock_bridge_request(method, path, payload=None, request_id="", actor_id="", owner_id=""):
        posted_calls.append({
            "method": method,
            "path": path,
            "payload": payload,
            "request_id": request_id,
            "actor_id": actor_id,
            "owner_id": owner_id,
        })
        return {
            "ok": True,
            "job": {
                "job_id": "subdub_bot_12345",
                "status": "queued",
                "mode": "dub",
            },
        }

    monkeypatch.setattr(bridge, "_is_runtime_execution_active", lambda *a, **k: True)
    with patch.object(core_bridge, "bridge_configured", return_value=True), \
         patch.object(core_bridge, "bridge_request", new=mock_bridge_request):
        dispatched_job = asyncio.run(
            bridge.dispatch_subdub_job_to_canonical_runtime(
                job_id=job["id"],
                account={"id": account_id, "canonical_user_id": "10004"},
            )
        )

    assert dispatched_job is not None
    assert len(posted_calls) == 1
    call_payload = posted_calls[0]["payload"]["payload"]
    assert call_payload["auto_speaker_lane"] == "smart_multi"
