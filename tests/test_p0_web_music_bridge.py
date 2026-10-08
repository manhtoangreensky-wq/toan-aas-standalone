"""P0 Integration and Unit Tests for Web Music Job Bridge.

Task: MUSIC_WEB_CANONICAL_ENGINE_PARITY_AND_PRODUCTION_RELEASE_R1
Product Family: Music (/music/ai, /music/song)
Tracker: manhtoangreensky-wq/toan-aas-standalone#612

Validates:
1. Canonical schema initialization and tenant isolation.
2. Server-side authority: client cannot supply provider, price, wallet, or status.
3. Strict tier enforcement: basic, standard, premium required; NO silent default.
4. Canonical pricing parity:
   - Background: basic=130 Xu, standard=150 Xu, premium=200 Xu.
   - Song: basic=200 Xu, standard=250 Xu, premium=300 Xu.
5. Strict product separation:
   - Background rejects lyrics/vocal/duet fields.
   - Song accepts lyrics and validates vocal mode.
6. Replay idempotency and conflict rejection on modified payload.
7. Confirm, reconcile, and safe audio artifact streaming.
"""

from __future__ import annotations

import json
import sqlite3
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from copyfast_music_job_bridge import (
    ensure_music_schema,
    validate_music_input,
    create_or_replay_music_job,
    get_music_job,
    list_music_jobs,
    is_music_job_other_account,
    confirm_music_job,
    reconcile_music_job_status,
    music_job_to_native_compat,
    MUSIC_BACKGROUND_TIER_PRICES,
    MUSIC_SONG_TIER_PRICES,
    STATUS_PREPARED,
    STATUS_COMPLETED,
)


@pytest.fixture(autouse=True)
def init_test_db():
    ensure_music_schema()


# ─── 1. PRICING & TIER AUTHORITY TESTS ────────────────────────────────────────

def test_music_background_pricing_parity():
    """Verify background music pricing parity matches canonical spec (130, 150, 200 Xu)."""
    assert MUSIC_BACKGROUND_TIER_PRICES["basic"] == 130
    assert MUSIC_BACKGROUND_TIER_PRICES["standard"] == 150
    assert MUSIC_BACKGROUND_TIER_PRICES["premium"] == 200

    for tier, expected_xu in [("basic", 130), ("standard", 150), ("premium", 200)]:
        ok, err, norm = validate_music_input(
            "music_background",
            {"brief": "Lo-Fi study beats", "tier": tier, "duration_seconds": 60},
        )
        assert ok is True, f"Validation failed for tier {tier}: {err}"
        assert norm["quote_xu"] == expected_xu
        assert norm["tier"] == tier
        assert norm["product_kind"] == "background"


def test_music_song_pricing_parity():
    """Verify song music pricing parity matches canonical spec (200, 250, 300 Xu)."""
    assert MUSIC_SONG_TIER_PRICES["basic"] == 200
    assert MUSIC_SONG_TIER_PRICES["standard"] == 250
    assert MUSIC_SONG_TIER_PRICES["premium"] == 300

    for tier, expected_xu in [("basic", 200), ("standard", 250), ("premium", 300)]:
        ok, err, norm = validate_music_input(
            "music_song",
            {
                "brief": "Indie pop anthem",
                "tier": tier,
                "lyrics": "Walking under city lights",
                "vocal_mode": "female",
                "duration_seconds": 120,
            },
        )
        assert ok is True, f"Validation failed for tier {tier}: {err}"
        assert norm["quote_xu"] == expected_xu
        assert norm["tier"] == tier
        assert norm["product_kind"] == "song"
        assert norm["vocal_mode"] == "female"


def test_music_tier_strictly_required():
    """Verify that omitting tier or providing an invalid tier is rejected."""
    # Missing tier
    ok, err, _ = validate_music_input(
        "music_background",
        {"brief": "Chill acoustic guitar", "duration_seconds": 30},
    )
    assert ok is False
    assert "TIER_REQUIRED" in err

    # Invalid tier
    ok2, err2, _ = validate_music_input(
        "music_background",
        {"brief": "Chill acoustic guitar", "tier": "ultra_deluxe", "duration_seconds": 30},
    )
    assert ok2 is False
    assert "INVALID_TIER" in err2


# ─── 2. PRODUCT SEPARATION TESTS ──────────────────────────────────────────────

def test_background_rejects_song_fields():
    """Verify background rejects lyrics, song_vocal, and vocal_mode."""
    for field in ("lyrics", "song_vocal", "vocal_mode", "duet"):
        payload = {
            "brief": "Ambient coffee shop background",
            "tier": "basic",
            field: "Something not allowed",
        }
        ok, err, _ = validate_music_input("music_background", payload)
        assert ok is False
        assert "SONG_FIELD_REJECTED_FOR_BACKGROUND" in err


def test_song_vocal_mode_validation():
    """Verify song requires valid vocal mode (male, female, duet, auto)."""
    valid_modes = ["male", "female", "duet", "auto"]
    for mode in valid_modes:
        ok, err, norm = validate_music_input(
            "music_song",
            {"brief": "Acoustic ballad", "tier": "standard", "vocal_mode": mode},
        )
        assert ok is True, f"Failed for valid vocal mode {mode}: {err}"
        assert norm["vocal_mode"] == mode

    # Invalid vocal mode
    ok_inv, err_inv, _ = validate_music_input(
        "music_song",
        {"brief": "Acoustic ballad", "tier": "standard", "vocal_mode": "robot_choir"},
    )
    assert ok_inv is False
    assert "INVALID_VOCAL_MODE" in err_inv


# ─── 3. FORBIDDEN AUTHORITY FIELD REJECTION ───────────────────────────────────

def test_rejects_client_injected_authority_fields():
    """Verify that client cannot inject provider, price, wallet, or status fields."""
    forbidden_payloads = [
        {"brief": "Test", "tier": "basic", "provider": "suno_v3"},
        {"brief": "Test", "tier": "basic", "price": 0},
        {"brief": "Test", "tier": "basic", "amount": 10},
        {"brief": "Test", "tier": "basic", "wallet": 99999},
        {"brief": "Test", "tier": "basic", "status": "completed"},
        {"brief": "Test", "tier": "basic", "output_url": "https://evil.com/fake.mp3"},
    ]
    for p in forbidden_payloads:
        ok, err, _ = validate_music_input("music_background", p)
        assert ok is False
        assert "FORBIDDEN_AUTHORITY_FIELD_REJECTED" in err


# ─── 4. REPLAY IDEMPOTENCY & CONFLICT TESTS ───────────────────────────────────

def test_idempotent_job_replay_and_conflict():
    """Verify exact replay returns existing job; modified payload returns 409 conflict."""
    import uuid
    account_id = f"test_user_music_idemp_{uuid.uuid4().hex[:6]}"
    key = f"idemp_test_music_key_{uuid.uuid4().hex[:8]}"
    payload = {
        "brief": "Synthwave night drive",
        "tier": "standard",
        "duration_seconds": 60,
        "idempotency_key": key,
    }

    # 1. Create initial job
    job1 = create_or_replay_music_job(
        feature_key="music_background",
        account_id=account_id,
        payload=payload,
    )
    assert job1["idempotent_replay"] is False
    assert job1["quote_xu"] == 150
    assert job1["tier"] == "standard"
    assert job1["status"] == STATUS_PREPARED

    # 2. Replay with exact same payload
    job2 = create_or_replay_music_job(
        feature_key="music_background",
        account_id=account_id,
        payload=payload,
    )
    assert job2["idempotent_replay"] is True
    assert job2["id"] == job1["id"]
    assert job2["request_id"] == job1["request_id"]

    # 3. Conflict: same idempotency key with modified payload
    modified_payload = dict(payload)
    modified_payload["brief"] = "Different brief entirely"
    with pytest.raises(HTTPException) as exc_info:
        create_or_replay_music_job(
            feature_key="music_background",
            account_id=account_id,
            payload=modified_payload,
        )
    assert exc_info.value.status_code == 409


# ─── 5. TENANT ISOLATION TESTS ────────────────────────────────────────────────

def test_tenant_isolation_job_access():
    """Verify cross-tenant access is strictly denied."""
    owner_a = "user_music_tenant_a"
    owner_b = "user_music_tenant_b"

    job = create_or_replay_music_job(
        feature_key="music_background",
        account_id=owner_a,
        payload={"brief": "Ambient meditation", "tier": "basic", "duration_seconds": 30},
    )
    job_id = job["id"]

    # Owner A can access
    assert get_music_job(owner_a, job_id) is not None
    assert is_music_job_other_account(job_id, owner_a) is False

    # Owner B cannot access
    assert get_music_job(owner_b, job_id) is None
    assert is_music_job_other_account(job_id, owner_b) is True


# ─── 6. CONFIRM & SETTLEMENT FLOW ─────────────────────────────────────────────

import asyncio

def test_confirm_music_job_success():
    """Verify confirming a prepared job dispatches to bot runtime and updates status."""
    async def _run():
        account = {"id": "user_music_confirm", "canonical_user_id": "123456"}
        job = create_or_replay_music_job(
            feature_key="music_song",
            account_id=account["id"],
            payload={"brief": "Power pop anthem", "tier": "premium", "lyrics": "Keep going", "vocal_mode": "female"},
        )
        job_id = job["id"]

        mock_dispatch_res = {
            "ok": True,
            "data": {
                "job": {
                    "job_id": "bot_mjb_mock_001",
                    "status": "prepared",
                    "quote_xu": 300,
                }
            },
        }
        mock_confirm_res = {
            "ok": True,
            "data": {
                "job": {
                    "job_id": "bot_mjb_mock_001",
                    "status": "completed",
                    "charged_xu": 300,
                    "completed_at": "2026-10-09T03:00:00Z",
                }
            },
        }

        with patch("copyfast_bridge.bridge_configured", return_value=True), \
             patch("copyfast_bridge.bridge_request", side_effect=[mock_dispatch_res, mock_confirm_res]):
            confirmed = await confirm_music_job(job_id=job_id, account=account)
            assert confirmed["status"] == "completed"
            assert confirmed["charged_xu"] == 300
            assert confirmed["can_download"] is True

    asyncio.run(_run())
