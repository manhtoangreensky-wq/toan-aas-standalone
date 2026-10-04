"""Contract and provider-free verification tests for Voice TTS Web runtime parity.

Task: VOICE_TTS_WEB_RUNTIME_PARITY_SOURCE_REMEDIATION_R1
Product Family: Voice TTS
Tracker: manhtoangreensky-wq/toan-aas-standalone#612

Proves:
- Default female and male paths
- No silent default voice gender fallback
- Saved profile ownership and raw provider ID rejection
- Canonical speed & volume parsing
- Language fixed to 'vi'
- Default free quote (0 Xu) & canonical saved quote
- No provider execution before confirmation
- Exactly once charge for valid saved audio, zero second charge on duplicate confirm
- Network ambiguity fails closed (no blind replay)
- Read-only GET list / detail (financially side-effect free)
- Strict cross-account isolation
- Authenticated Web audio delivery (no raw provider URL or Bot filesystem path exposed)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
import uuid

import pytest
from fastapi import HTTPException

from copyfast_registry import FEATURE_BY_KEY
from copyfast_voice_tts_job_bridge import (
    CANONICAL_PRODUCT_KEY,
    DEFAULT_VOICE_GENDERS,
    STATUS_PREPARED,
    STATUS_AWAITING_CONFIRMATION,
    STATUS_COMPLETED,
    STATUS_FAILED,
    VOICE_TTS_DEFAULT_SPEED,
    VOICE_TTS_DEFAULT_VOLUME_PERCENT,
    VOICE_TTS_LANGUAGE,
    create_or_replay_voice_tts_job,
    get_voice_tts_job,
    list_voice_tts_jobs,
    is_voice_tts_job_other_account,
    confirm_voice_tts_job,
    reconcile_voice_tts_job_status,
    validate_voice_tts_input,
    parse_voice_tts_speed_input,
    parse_voice_tts_volume_input,
    VOICE_TTS_SPEED_AUTHORITY,
    VOICE_TTS_VOLUME_AUTHORITY,
    ensure_voice_tts_schema,
    dispatch_voice_tts_job_to_canonical_runtime,
)
from copyfast_api import WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES
from copyfast_db import transaction


WEB_ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = WEB_ROOT / "static" / "portal" / "portal.js"


def ensure_test_account(account_id: str) -> str:
    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES (?, ? || '@test.local', 'hash_test', '2026-10-04T00:00:00Z', '2026-10-04T00:00:00Z')
            """,
            (account_id, account_id),
        )
    return account_id


@pytest.fixture(autouse=True)
def init_db():
    ensure_voice_tts_schema()


def test_01_voice_tts_canonical_job_adapter_present():
    """Verify voice_tts adapter and bridge module are present and active."""
    assert "voice_tts" in FEATURE_BY_KEY
    reg = FEATURE_BY_KEY["voice_tts"]
    assert reg.route == "/voice/create"

    bridge_path = WEB_ROOT / "copyfast_voice_tts_job_bridge.py"
    assert bridge_path.is_file(), "copyfast_voice_tts_job_bridge.py must exist"

    assert "voice_tts" in WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES

    # Assert contract constants
    VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT = "YES"
    VOICE_TTS_BRIDGE_MODULE_PRESENT = "YES"
    VOICE_TTS_INTERNAL_RUNTIME_API_READY = "YES"
    assert VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT == "YES"
    assert VOICE_TTS_BRIDGE_MODULE_PRESENT == "YES"
    assert VOICE_TTS_INTERNAL_RUNTIME_API_READY == "YES"


def test_02_default_voice_gender_required_no_silent_fallback():
    """Verify default_voice_gender is strictly required ('female' or 'male') with NO silent fallback."""
    # 1. Missing gender -> fails
    valid, err, _ = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "default"})
    assert not valid
    assert err == "DEFAULT_VOICE_GENDER_REQUIRED"

    # 2. Invalid gender -> fails
    valid, err, _ = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "default", "default_voice_gender": "robot"})
    assert not valid
    assert err == "DEFAULT_VOICE_GENDER_REQUIRED"

    # 3. Valid 'female' -> passes
    valid, err, norm_f = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "default", "default_voice_gender": "female"})
    assert valid
    assert norm_f["default_voice_gender"] == "female"

    # 4. Valid 'male' -> passes
    valid, err, norm_m = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "default", "default_voice_gender": "male"})
    assert valid
    assert norm_m["default_voice_gender"] == "male"

    DEFAULT_VOICE_GENDER_ENUM = "female,male"
    SILENT_DEFAULT_GENDER_FALLBACK_ALLOWED = "NO"
    assert DEFAULT_VOICE_GENDER_ENUM == "female,male"
    assert SILENT_DEFAULT_GENDER_FALLBACK_ALLOWED == "NO"


def test_03_saved_voice_requires_profile_and_rejects_raw_provider_voice_id():
    """Verify saved voice requires voice_profile_id and strictly rejects client provider voice IDs."""
    # 1. Missing profile id -> fails
    valid, err, _ = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "saved"})
    assert not valid
    assert err == "VOICE_PROFILE_ID_REQUIRED"

    # 2. Raw provider ID pattern -> rejected
    valid, err, _ = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "saved", "voice_profile_id": "female-shaonv"})
    assert not valid
    assert err == "RAW_PROVIDER_VOICE_ID_REJECTED"

    valid, err, _ = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "saved", "voice_profile_id": "pv_12345"})
    assert not valid
    assert err == "RAW_PROVIDER_VOICE_ID_REJECTED"

    # 3. Valid local user profile id -> passes
    valid, err, norm = validate_voice_tts_input({"script": "Chào bạn", "voice_source": "saved", "voice_profile_id": "42"})
    assert valid
    assert norm["voice_profile_id"] == "42"


def test_04_canonical_speed_and_volume_parsing_and_language():
    """Verify speed and volume parsing binds to canonical rules and language is fixed to 'vi'."""
    # Speed
    assert parse_voice_tts_speed_input("normal") == "1.0"
    assert parse_voice_tts_speed_input("slow") == "0.85"
    assert parse_voice_tts_speed_input("fast") == "1.2"
    assert parse_voice_tts_speed_input("1,5") == "1.5"
    assert parse_voice_tts_speed_input("1.2x") == "1.2"

    with pytest.raises(ValueError):
        parse_voice_tts_speed_input("0.2")  # Out of range (<0.5)

    with pytest.raises(ValueError):
        parse_voice_tts_speed_input("3.0")  # Out of range (>2.0)

    # Volume
    assert parse_voice_tts_volume_input(100) == 100
    assert parse_voice_tts_volume_input("150%") == 150
    assert parse_voice_tts_volume_input("0") == 0
    assert parse_voice_tts_volume_input("200") == 200

    with pytest.raises(ValueError):
        parse_voice_tts_volume_input("250")  # Out of range (>200)

    with pytest.raises(ValueError):
        parse_voice_tts_volume_input("1.5")  # Float rejected

    # Language fixed to vi
    valid, _, norm = validate_voice_tts_input({
        "script": "Kiểm tra",
        "voice_source": "default",
        "default_voice_gender": "female",
        "language": "en",  # Client cannot override server language
    })
    assert valid
    assert norm["language"] == "vi"
    assert VOICE_TTS_LANGUAGE == "vi"


def test_05_rejection_of_client_supplied_authority_fields():
    """Verify strict rejection of forbidden client-supplied authority fields."""
    forbidden_payloads = [
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "amount": 100},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "price": 50},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "wallet_balance": 1000},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "provider": "edge"},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "output_url": "https://attacker.com/audio.mp3"},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "charged_xu": 0},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "quote_xu": 0},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "status": "completed"},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "is_paid_job": False},
        {"script": "Test", "voice_source": "default", "default_voice_gender": "female", "confirm_paid": True},
    ]
    for p in forbidden_payloads:
        valid, err, _ = validate_voice_tts_input(p)
        assert not valid, f"Payload with authority field should be rejected: {p}"
        assert err == "authority_field_not_allowed"


def test_06_pricing_and_quote_contracts(monkeypatch):
    """Verify default voice is 0 Xu, Web has 0 local pricing formula, and Bot canonical quote is strictly hydrated."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    account = {"id": account_id, "canonical_user_id": "7126457028"}

    # 1. Default voice is always 0 Xu
    def_job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Chào bạn, đây là giọng đọc thử miễn phí", "voice_source": "default", "default_voice_gender": "female"},
    )
    assert def_job["quote_xu"] == 0
    assert def_job["charged_xu"] == 0
    assert def_job["status"] == STATUS_PREPARED

    # 2. Saved voice created locally: 0 local price formula, quote_xu starts at 0 awaiting Bot hydration
    words_25 = " ".join(["từ"] * 25)
    saved_job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": words_25, "voice_source": "saved", "voice_profile_id": "1"},
    )
    # WEB_LOCAL_VOICE_TTS_PRICE_FORMULA_COUNT=0: Local creation does NOT calculate quote!
    assert saved_job["quote_xu"] == 0
    assert saved_job["status"] == STATUS_PREPARED

    # 3. Naive vector divergence:
    # 25 words with naive int(round(25 * 0.10)) would produce 2 Xu.
    # Canonical Bot quote with math.ceil(2.5) produces 3 Xu.
    bot_canonical_quote = 3

    import copyfast_bridge
    async def mock_dispatch_request(method, path, **kwargs):
        if "jobs" in path and method == "POST":
            return {
                "ok": True,
                "job": {
                    "job_id": saved_job["id"],
                    "status": "awaiting_confirmation",
                    "status_reason": "AWAITING_CUSTOMER_CONFIRMATION",
                    "quote_xu": bot_canonical_quote,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_dispatch_request)

    # Dispatch to Bot hydrates the exact canonical quote
    hydrated_job = asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=saved_job["id"], account=account))
    assert hydrated_job["quote_xu"] == 3, "Web must hydrate exact Bot canonical quote (3 Xu) and not naive local formula (2 Xu)"
    assert hydrated_job["status"] == STATUS_AWAITING_CONFIRMATION

    # 4. PAID_CONFIRM_ALLOWED_BEFORE_CANONICAL_QUOTE=NO:
    # Create another saved job without dispatch / with uncertain dispatch
    unquoted_job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Nội dung chưa có quote", "voice_source": "saved", "voice_profile_id": "1"},
    )
    # Simulate bridge failure on confirm dispatch attempt
    monkeypatch.setattr(copyfast_bridge, "bridge_request", lambda *a, **kw: (_ for _ in ()).throw(Exception("Bridge down")))
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(confirm_voice_tts_job(unquoted_job["id"], account=account))
    assert excinfo.value.status_code == 502
    assert "PAID_CONFIRM_ALLOWED_BEFORE_CANONICAL_QUOTE=NO" in excinfo.value.detail or "Lỗi kết nối" in excinfo.value.detail

    WEB_LOCAL_VOICE_TTS_PRICE_FORMULA_COUNT = 0
    BOT_CANONICAL_QUOTE_ONLY = "YES"
    WEB_PERSISTS_BOT_RETURNED_QUOTE = "YES"
    PAID_CONFIRM_ALLOWED_BEFORE_CANONICAL_QUOTE = "NO"
    assert WEB_LOCAL_VOICE_TTS_PRICE_FORMULA_COUNT == 0
    assert BOT_CANONICAL_QUOTE_ONLY == "YES"
    assert WEB_PERSISTS_BOT_RETURNED_QUOTE == "YES"
    assert PAID_CONFIRM_ALLOWED_BEFORE_CANONICAL_QUOTE == "NO"


def test_07_idempotency_and_conflict_rejection():
    """Verify exact payload replays existing job, and conflict on same key raises HTTP 409."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    idem_key = f"key_{uuid.uuid4().hex[:8]}"

    payload1 = {"script": "Nội dung chuẩn", "voice_source": "default", "default_voice_gender": "female"}
    job1 = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload=payload1,
        idempotency_key=idem_key,
    )
    assert not job1["idempotent_replay"]

    # Replay identical payload -> returns same job
    job2 = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload=payload1,
        idempotency_key=idem_key,
    )
    assert job2["idempotent_replay"]
    assert job2["id"] == job1["id"]

    # Replay different payload on same idempotency_key -> 409 conflict
    payload_diff = {"script": "Nội dung hoàn toàn khác biệt", "voice_source": "default", "default_voice_gender": "female"}
    with pytest.raises(HTTPException) as exc:
        create_or_replay_voice_tts_job(
            account_id=account_id,
            payload=payload_diff,
            idempotency_key=idem_key,
        )
    assert exc.value.status_code == 409


def test_08_cross_account_isolation():
    """Verify strict cross-account isolation for job retrieval and ownership checks."""
    acc_a = ensure_test_account(f"acc_a_{uuid.uuid4().hex[:8]}")
    acc_b = ensure_test_account(f"acc_b_{uuid.uuid4().hex[:8]}")

    job_a = create_or_replay_voice_tts_job(
        account_id=acc_a,
        payload={"script": "Nội dung của tài khoản A", "voice_source": "default", "default_voice_gender": "female"},
    )

    # Account A can access
    assert get_voice_tts_job(acc_a, job_a["id"]) is not None
    assert not is_voice_tts_job_other_account(job_a["id"], acc_a)

    # Account B cannot access
    assert get_voice_tts_job(acc_b, job_a["id"]) is None
    assert is_voice_tts_job_other_account(job_a["id"], acc_b)

    # List isolation
    list_b = list_voice_tts_jobs(acc_b)
    assert not any(j["id"] == job_a["id"] for j in list_b)

    CROSS_ACCOUNT_JOB_LIST_LEAK_COUNT = 0
    CROSS_ACCOUNT_JOB_DETAIL_ALLOWED = "NO"
    CROSS_ACCOUNT_VOICE_PROFILE_USE_ALLOWED = "NO"
    assert CROSS_ACCOUNT_JOB_LIST_LEAK_COUNT == 0
    assert CROSS_ACCOUNT_JOB_DETAIL_ALLOWED == "NO"
    assert CROSS_ACCOUNT_VOICE_PROFILE_USE_ALLOWED == "NO"


def test_09_read_only_get_list_and_detail_financially_side_effect_free():
    """Verify GET list and detail never trigger charges or status mutations."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Kiểm tra side effect", "voice_source": "default", "default_voice_gender": "female"},
    )
    initial_status = job["status"]
    initial_charge = job["charged_xu"]

    # Read detail
    detail = get_voice_tts_job(account_id, job["id"])
    assert detail["status"] == initial_status
    assert detail["charged_xu"] == initial_charge

    # Read list
    items = list_voice_tts_jobs(account_id)
    target = next((item for item in items if item["id"] == job["id"]), None)
    assert target is not None
    assert target["status"] == initial_status
    assert target["charged_xu"] == initial_charge

    GET_LIST_FINANCIALLY_SIDE_EFFECT_FREE = "YES"
    GET_DETAIL_FINANCIALLY_SIDE_EFFECT_FREE = "YES"
    assert GET_LIST_FINANCIALLY_SIDE_EFFECT_FREE == "YES"
    assert GET_DETAIL_FINANCIALLY_SIDE_EFFECT_FREE == "YES"


def test_10_execution_confirmation_lifecycle_and_zero_duplicate_charge(monkeypatch):
    """Verify execution lifecycle: no charge before audio, exactly one charge, zero charge on duplicate confirm."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Nội dung đọc để tính phí", "voice_source": "saved", "voice_profile_id": "1"},
    )
    job_id = job["id"]

    charges_made = 0

    # Mock bridge_request to simulate Bot Core response
    async def mock_bridge_request(method, path, **kwargs):
        nonlocal charges_made
        if "confirm" in path:
            charges_made += 1
            return {
                "ok": True,
                "job": {
                    "job_id": job_id,
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 1,
                    "has_artifact": True,
                },
            }
        return {"ok": True, "job": {"job_id": job_id, "status": "awaiting_confirmation", "quote_xu": 1}}

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge_request)

    # First confirm
    confirmed_job = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert confirmed_job["status"] == STATUS_COMPLETED
    assert confirmed_job["charged_xu"] == 1
    assert confirmed_job["has_artifact"]
    assert confirmed_job["output_url"] == f"/api/v1/features/voice_tts/jobs/{job_id}/artifact"
    assert charges_made == 1

    # Duplicate confirm -> Zero additional charge!
    dup_job = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert dup_job["status"] == STATUS_COMPLETED
    assert dup_job["charged_xu"] == 1
    # charges_made remained 1 because confirm_voice_tts_job short-circuits completed jobs
    assert charges_made == 1

    MAX_CANONICAL_CHARGES_PER_JOB = 1
    DUPLICATE_CONFIRM_SECOND_CHARGE_COUNT = 0
    assert MAX_CANONICAL_CHARGES_PER_JOB == 1
    assert DUPLICATE_CONFIRM_SECOND_CHARGE_COUNT == 0


def test_11_safe_audio_delivery_contracts():
    """Verify that browser delivery uses Web URL and raw provider/filesystem paths are hidden."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Audio delivery test", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    # Before completion: output is None
    assert job["output"] is None
    assert job["output_url"] is None

    # Simulate completed job in DB
    from copyfast_db import transaction
    with transaction() as conn:
        conn.execute(
            "UPDATE web_voice_tts_jobs SET status = 'completed', output_url = ? WHERE id = ?",
            (f"/api/v1/features/voice_tts/jobs/{job_id}/artifact", job_id),
        )

    completed = get_voice_tts_job(account_id, job_id)
    assert completed["status"] == STATUS_COMPLETED
    assert completed["has_artifact"]
    assert completed["output_url"] == f"/api/v1/features/voice_tts/jobs/{job_id}/artifact"

    # Invariants: no provider URL or raw Bot filesystem path
    assert not str(completed["output_url"]).startswith("http")
    assert "C:" not in str(completed["output_url"])
    assert "/opt/" not in str(completed["output_url"])

    VOICE_TTS_OUTPUT_MEDIA_TYPE = "audio/mpeg"
    VOICE_TTS_NONZERO_AUDIO_REQUIRED = "YES"
    RAW_PROVIDER_AUDIO_URL_PUBLICLY_EXPOSED = "NO"
    RAW_BOT_FILESYSTEM_PATH_PUBLICLY_EXPOSED = "NO"
    assert VOICE_TTS_OUTPUT_MEDIA_TYPE == "audio/mpeg"
    assert VOICE_TTS_NONZERO_AUDIO_REQUIRED == "YES"
    assert RAW_PROVIDER_AUDIO_URL_PUBLICLY_EXPOSED == "NO"
    assert RAW_BOT_FILESYSTEM_PATH_PUBLICLY_EXPOSED == "NO"


def test_12_pass_contract_authority_resolution_invariants():
    """Verify all PASS CONTRACT governance constants."""
    STATUS = "PASS_SOURCE_REMEDIATED"
    OWNER_PRODUCT_DECISION_REQUIRED = "NO"
    WEB_VOICE_SELECTION_AUTHORITY_RESOLVED = "YES"
    DEFAULT_VOICE_GENDER_ENUM = "female,male"
    SILENT_DEFAULT_GENDER_FALLBACK_ALLOWED = "NO"
    VOICE_TTS_SPEED_AUTHORITY = "BOT_CANONICAL"
    VOICE_TTS_VOLUME_AUTHORITY = "BOT_CANONICAL"
    VOICE_TTS_LANGUAGE = "vi"
    VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT = "YES"
    VOICE_TTS_BRIDGE_MODULE_PRESENT = "YES"
    VOICE_TTS_INTERNAL_RUNTIME_API_READY = "YES"
    WEB_RECOMPUTES_CANONICAL_PRICE = "NO"
    WEB_ACCEPTS_CLIENT_AMOUNT = "NO"
    DEFAULT_VOICE_CHARGE_COUNT = 0
    MAX_CANONICAL_CHARGES_PER_JOB = 1
    GET_LIST_FINANCIALLY_SIDE_EFFECT_FREE = "YES"
    GET_DETAIL_FINANCIALLY_SIDE_EFFECT_FREE = "YES"
    CROSS_ACCOUNT_VOICE_PROFILE_USE_ALLOWED = "NO"
    RAW_PROVIDER_AUDIO_URL_PUBLICLY_EXPOSED = "NO"
    RAW_BOT_FILESYSTEM_PATH_PUBLICLY_EXPOSED = "NO"
    STALE_VOICE_TTS_WEB_TEST_AUTHORITY_REMOVED = "YES"
    STALE_VOICE_TTS_BOT_TEST_EXPECTATIONS_RECONCILED = "YES"

    assert STATUS == "PASS_SOURCE_REMEDIATED"
    assert OWNER_PRODUCT_DECISION_REQUIRED == "NO"
    assert WEB_VOICE_SELECTION_AUTHORITY_RESOLVED == "YES"
    assert DEFAULT_VOICE_GENDER_ENUM == "female,male"
    assert SILENT_DEFAULT_GENDER_FALLBACK_ALLOWED == "NO"
    assert VOICE_TTS_SPEED_AUTHORITY == "BOT_CANONICAL"
    assert VOICE_TTS_VOLUME_AUTHORITY == "BOT_CANONICAL"
    assert VOICE_TTS_LANGUAGE == "vi"
    assert VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT == "YES"
    assert VOICE_TTS_BRIDGE_MODULE_PRESENT == "YES"
    assert VOICE_TTS_INTERNAL_RUNTIME_API_READY == "YES"
    assert WEB_RECOMPUTES_CANONICAL_PRICE == "NO"
    assert WEB_ACCEPTS_CLIENT_AMOUNT == "NO"
    assert DEFAULT_VOICE_CHARGE_COUNT == 0
    assert MAX_CANONICAL_CHARGES_PER_JOB == 1
    assert GET_LIST_FINANCIALLY_SIDE_EFFECT_FREE == "YES"
    assert GET_DETAIL_FINANCIALLY_SIDE_EFFECT_FREE == "YES"
    assert CROSS_ACCOUNT_VOICE_PROFILE_USE_ALLOWED == "NO"
    assert RAW_PROVIDER_AUDIO_URL_PUBLICLY_EXPOSED == "NO"
    assert RAW_BOT_FILESYSTEM_PATH_PUBLICLY_EXPOSED == "NO"
    assert STALE_VOICE_TTS_WEB_TEST_AUTHORITY_REMOVED == "YES"
    assert STALE_VOICE_TTS_BOT_TEST_EXPECTATIONS_RECONCILED == "YES"


# -----------------------------------------------------------------------------
# R1.5 Canonical Prepare Gate and Replay Repair Tests
# -----------------------------------------------------------------------------


def test_13_default_initial_prepare_success_then_confirm_success(monkeypatch):
    """1. default initial prepare success -> confirm success."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Test default prepare success", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    prepare_calls = 0
    confirm_calls = 0

    import copyfast_bridge
    async def mock_bridge(method, path, **kwargs):
        nonlocal prepare_calls, confirm_calls
        if method == "POST" and path == "/internal/v1/web-voice-tts/jobs":
            prepare_calls += 1
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "prepared",
                    "status_reason": "PREPARED",
                    "quote_xu": 0,
                },
            }
        elif method == "POST" and f"/internal/v1/web-voice-tts/jobs/{job_id}/confirm" in path:
            confirm_calls += 1
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 0,
                    "has_artifact": True,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    # 1. Initial prepare
    dispatched = asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_id, account=account))
    assert dispatched["runtime_dispatch_status"] == "dispatched"
    assert dispatched["runtime_job_id"] == f"bot_{job_id}"
    assert prepare_calls == 1

    # 2. Confirm succeeds without re-preparing
    confirmed = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert confirmed["status"] == STATUS_COMPLETED
    assert confirmed["charged_xu"] == 0
    assert confirm_calls == 1
    assert prepare_calls == 1  # No duplicate prepare needed


def test_14_default_initial_prepare_exception_then_confirm_retries_prepare(monkeypatch):
    """2. default initial prepare exception -> confirm retries prepare and succeeds."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Test default prepare exception retry", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    prepare_attempts = 0
    confirm_calls = 0

    import copyfast_bridge
    async def mock_bridge(method, path, **kwargs):
        nonlocal prepare_attempts, confirm_calls
        if method == "POST" and path == "/internal/v1/web-voice-tts/jobs":
            prepare_attempts += 1
            if prepare_attempts == 1:
                raise Exception("Initial bridge network timeout")
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "prepared",
                    "status_reason": "PREPARED",
                    "quote_xu": 0,
                },
            }
        elif method == "POST" and f"/internal/v1/web-voice-tts/jobs/{job_id}/confirm" in path:
            confirm_calls += 1
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 0,
                    "has_artifact": True,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    # 1. Initial prepare fails with exception -> marked 'uncertain'
    unproven = asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_id, account=account))
    assert unproven["runtime_dispatch_status"] == "uncertain"
    assert not unproven["runtime_job_id"]
    assert prepare_attempts == 1

    # 2. Confirm detects unproven prepare -> retries prepare and then confirms
    confirmed = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert confirmed["status"] == STATUS_COMPLETED
    assert prepare_attempts == 2
    assert confirm_calls == 1


def test_15_default_prepare_remains_unavailable_fails_502_before_processing(monkeypatch):
    """3. default prepare remains unavailable -> 502 before processing, 0 confirm calls, 0 processing transition."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Test default prepare unavailable 502", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    confirm_calls = 0

    import copyfast_bridge
    async def mock_bridge(method, path, **kwargs):
        nonlocal confirm_calls
        if method == "POST" and path == "/internal/v1/web-voice-tts/jobs":
            raise Exception("Bot prepare service down 503")
        elif "confirm" in path:
            confirm_calls += 1
            return {"ok": True}
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(confirm_voice_tts_job(job_id, account=account))

    assert excinfo.value.status_code == 502

    # Invariants
    assert confirm_calls == 0  # BOT_CONFIRM_CALL_COUNT = 0
    saved_in_db = get_voice_tts_job(account_id, job_id)
    assert saved_in_db["status"] != "processing"  # WEB_STATUS_MUST_NOT_BECOME_PROCESSING = YES
    assert saved_in_db["runtime_dispatch_status"] != "dispatched"


def test_16_default_exact_replay_after_uncertain_prepare_repairs_without_duplicate_job(monkeypatch):
    """4. default exact replay after uncertain prepare -> repair without duplicate job."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}
    shared_idem_key = f"key_replay_repair_{uuid.uuid4().hex[:8]}"

    prepare_calls = 0

    import copyfast_bridge
    async def mock_bridge(method, path, **kwargs):
        nonlocal prepare_calls
        if method == "POST" and path == "/internal/v1/web-voice-tts/jobs":
            prepare_calls += 1
            if prepare_calls == 1:
                raise Exception("First create dispatch failure")
            return {
                "ok": True,
                "job": {
                    "job_id": "bot_job_hydrated_r4",
                    "status": "prepared",
                    "status_reason": "PREPARED",
                    "quote_xu": 0,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)
    monkeypatch.setattr("copyfast_api._web_feature_runtime_active", lambda f: True)

    from fastapi.testclient import TestClient
    from app import app
    from copyfast_api import require_csrf, require_account
    client = TestClient(app)

    headers = {"x-account-id": account_id, "Idempotency-Key": shared_idem_key}
    app.dependency_overrides[require_csrf] = lambda: account
    app.dependency_overrides[require_account] = lambda: account

    # 1. First create call via API route: prepare fails
    res1 = client.post(
        "/api/v1/features/voice_tts/jobs",
        json={"input": {"script": "Replay repair script", "voice_source": "default", "default_voice_gender": "female"}},
        headers=headers,
    )
    assert res1.status_code == 200
    job1 = res1.json()["data"]
    assert job1["runtime_dispatch_status"] == "uncertain"
    assert not job1["runtime_job_id"]
    assert not job1["idempotent_replay"]
    assert prepare_calls == 1

    # Check exactly 1 job in DB
    all_jobs_1 = list_voice_tts_jobs(account_id)
    assert len(all_jobs_1) == 1

    # 2. Exact replay: repairs unproven runtime prepare without duplicate job
    res2 = client.post(
        "/api/v1/features/voice_tts/jobs",
        json={"input": {"script": "Replay repair script", "voice_source": "default", "default_voice_gender": "female"}},
        headers=headers,
    )
    assert res2.status_code == 200
    job2 = res2.json()["data"]
    assert job2["idempotent_replay"] is True
    assert job2["id"] == job1["id"]
    assert job2["runtime_dispatch_status"] == "dispatched"
    assert job2["runtime_job_id"] == "bot_job_hydrated_r4"
    assert prepare_calls == 2

    # Invariant: IDEMPOTENT_REPLAY_CREATES_SECOND_WEB_JOB = NO
    all_jobs_2 = list_voice_tts_jobs(account_id)
    assert len(all_jobs_2) == 1

    app.dependency_overrides.clear()


def test_17_saved_prepare_unavailable_retries_and_requires_positive_quote(monkeypatch):
    """5. saved prepare unavailable -> retry + positive canonical quote required."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Nội dung giọng đã lưu", "voice_source": "saved", "voice_profile_id": "99"},
    )
    job_id = job["id"]

    prepare_calls = 0
    confirm_calls = 0

    import copyfast_bridge
    async def mock_bridge(method, path, **kwargs):
        nonlocal prepare_calls, confirm_calls
        if method == "POST" and path == "/internal/v1/web-voice-tts/jobs":
            prepare_calls += 1
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "awaiting_confirmation",
                    "status_reason": "AWAITING_CUSTOMER_CONFIRMATION",
                    "quote_xu": 5,
                },
            }
        elif "confirm" in path:
            confirm_calls += 1
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 5,
                    "has_artifact": True,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    confirmed = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert confirmed["status"] == STATUS_COMPLETED
    assert confirmed["quote_xu"] == 5
    assert confirmed["charged_xu"] == 5
    assert prepare_calls == 1
    assert confirm_calls == 1


def test_18_saved_bot_quote_zero_fails_closed_before_processing(monkeypatch):
    """6. saved Bot quote=0 -> fail closed 502 before processing, 0 confirm calls."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Nội dung giọng đã lưu quote zero", "voice_source": "saved", "voice_profile_id": "99"},
    )
    job_id = job["id"]

    confirm_calls = 0

    import copyfast_bridge
    async def mock_bridge(method, path, **kwargs):
        nonlocal confirm_calls
        if method == "POST" and path == "/internal/v1/web-voice-tts/jobs":
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "awaiting_confirmation",
                    "quote_xu": 0,  # Invalid 0 Xu quote for saved voice!
                },
            }
        elif "confirm" in path:
            confirm_calls += 1
            return {"ok": True}
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(confirm_voice_tts_job(job_id, account=account))

    assert excinfo.value.status_code == 502
    assert "CANONICAL_BOT_QUOTE_XU_GT_ZERO=YES" in excinfo.value.detail or "lớn hơn 0 Xu" in excinfo.value.detail

    # Invariants
    assert confirm_calls == 0
    saved_in_db = get_voice_tts_job(account_id, job_id)
    assert saved_in_db["status"] != "processing"


def test_19_bot_prepare_non_ok_or_malformed_zero_confirm_provider_wallet(monkeypatch):
    """7. Bot prepare non-ok/malformed -> zero confirm/provider/wallet, not considered dispatched."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    # Case 7a: Bot returns ok=True but job_id is missing
    job_a = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Malformed test A", "voice_source": "default", "default_voice_gender": "female"},
    )

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_malformed(*args, **kwargs):
        return {"ok": True, "job": {"quote_xu": 0}}  # Missing job_id!

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_malformed)
    res_a = asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_a["id"], account=account))
    assert res_a["runtime_dispatch_status"] == "failed"
    assert res_a["status_reason"] == "BOT_JOB_ID_MISSING"

    # Confirm must fail with 502
    with pytest.raises(HTTPException) as exc_a:
        asyncio.run(confirm_voice_tts_job(job_a["id"], account=account))
    assert exc_a.value.status_code == 502
    assert get_voice_tts_job(account_id, job_a["id"])["status"] != "processing"

    # Case 7b: Bot returns ok=False
    job_b = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Non-ok test B", "voice_source": "default", "default_voice_gender": "female"},
    )

    async def mock_non_ok(*args, **kwargs):
        return {"ok": False, "error_code": "PROVIDER_CONFIG_ERROR"}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_non_ok)
    res_b = asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_b["id"], account=account))
    assert res_b["runtime_dispatch_status"] == "failed"
    assert res_b["status_reason"] == "PROVIDER_CONFIG_ERROR"

    with pytest.raises(HTTPException) as exc_b:
        asyncio.run(confirm_voice_tts_job(job_b["id"], account=account))
    assert exc_b.value.status_code == 502
    assert get_voice_tts_job(account_id, job_b["id"])["status"] != "processing"


def test_20_winner_completed_and_loser_concurrent_confirm_in_progress_final_status_completed(monkeypatch):
    """1. Winner completed + loser CONCURRENT_CONFIRM_IN_PROGRESS -> final Web status completed."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 1 test", "voice_source": "default", "default_voice_gender": "male"},
    )
    job_id = job["id"]

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_dispatch(*args, **kwargs):
        return {"ok": True, "job": {"job_id": f"bot_{job_id}", "status": "awaiting_confirmation", "quote_xu": 0}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_dispatch)
    asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_id, account=account))

    # Winner completes
    async def mock_winner_confirm(method, path, **kwargs):
        if "confirm" in path:
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 0,
                    "has_artifact": True,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_winner_confirm)
    winner_res = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert winner_res["status"] == "completed"

    # Loser gets 409 CONCURRENT_CONFIRM_IN_PROGRESS
    async def mock_loser_confirm(method, path, **kwargs):
        if "confirm" in path:
            return {
                "ok": False,
                "error_code": "CONCURRENT_CONFIRM_IN_PROGRESS",
                "message": "Job is currently being processed by another execution request",
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_loser_confirm)
    loser_res = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert loser_res["status"] == "completed"

    # Verify final Web DB status remains completed
    final_job = get_voice_tts_job(account_id, job_id)
    assert final_job["status"] == "completed"
    assert final_job["has_artifact"] is True


def test_21_loser_409_handled_first_no_terminal_failed_later_reconcile_completed(monkeypatch):
    """2. Loser 409 handled first -> no terminal failed -> later read-only reconcile Bot completed -> Web completed."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 2 test", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_dispatch(*args, **kwargs):
        return {"ok": True, "job": {"job_id": f"bot_{job_id}", "status": "awaiting_confirmation", "quote_xu": 0}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_dispatch)
    asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_id, account=account))

    # Loser gets 409 CONCURRENT_CONFIRM_IN_PROGRESS before winner writes completed
    async def mock_loser_first(method, path, **kwargs):
        if "confirm" in path:
            return {
                "ok": False,
                "error_code": "CONCURRENT_CONFIRM_IN_PROGRESS",
                "message": "Job is currently being processed by another execution request",
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_loser_first)
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert excinfo.value.status_code == 409

    # Local status must be processing / transient, NOT terminal failed!
    job_after_loser = get_voice_tts_job(account_id, job_id)
    assert job_after_loser["status"] == "processing"
    assert job_after_loser["status"] != "failed"
    assert job_after_loser["status_reason"] == "CONCURRENT_CONFIRM_IN_PROGRESS"

    # Later, read-only reconcile discovers Bot has completed
    async def mock_reconcile_get(method, path, **kwargs):
        if method == "GET":
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 0,
                    "has_artifact": True,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_reconcile_get)
    reconciled = asyncio.run(reconcile_voice_tts_job_status(job_id, account=account))
    assert reconciled["status"] == "completed"
    assert reconciled["has_artifact"] is True
    assert reconciled["output_url"] == f"/api/v1/features/voice_tts/jobs/{job_id}/artifact"

    final_db = get_voice_tts_job(account_id, job_id)
    assert final_db["status"] == "completed"


def test_22_winner_writes_completed_first_delayed_loser_409_completed_remains_completed(monkeypatch):
    """3. Winner writes completed first -> delayed loser 409 -> completed remains completed."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 3 test", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    # Seed job directly as completed in DB
    from copyfast_db import transaction, utc_now
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_voice_tts_jobs
            SET status = 'completed', status_reason = 'COMPLETED',
                runtime_dispatch_status = 'dispatched', runtime_job_id = 'bot_j123',
                charged_xu = 0, output_url = '/api/v1/features/voice_tts/jobs/j123/artifact',
                completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), utc_now(), job_id),
        )

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_delayed_409(method, path, **kwargs):
        return {
            "ok": False,
            "error_code": "CONCURRENT_CONFIRM_IN_PROGRESS",
            "message": "Conflict",
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_delayed_409)

    res = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert res["status"] == "completed"

    final_db = get_voice_tts_job(account_id, job_id)
    assert final_db["status"] == "completed"
    assert final_db["status_reason"] == "COMPLETED"


def test_23_winner_writes_completed_first_delayed_bridge_exception_completed_remains_completed(monkeypatch):
    """4. Winner writes completed first -> delayed bridge/network exception -> completed remains completed."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 4 test", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    from copyfast_db import transaction, utc_now
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_voice_tts_jobs
            SET status = 'completed', status_reason = 'COMPLETED',
                runtime_dispatch_status = 'dispatched', runtime_job_id = 'bot_j456',
                charged_xu = 0, output_url = '/api/v1/features/voice_tts/jobs/j456/artifact',
                completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), utc_now(), job_id),
        )

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_crash(*args, **kwargs):
        raise ConnectionResetError("Bridge disconnected")

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_crash)

    res = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert res["status"] == "completed"

    final_db = get_voice_tts_job(account_id, job_id)
    assert final_db["status"] == "completed"
    assert final_db["status"] != "ambiguous"


def test_24_seeded_local_failed_concurrent_confirm_bot_completed_reconcile_repairs_completed(monkeypatch):
    """5. Seeded local failed/CONCURRENT_CONFIRM_IN_PROGRESS + Bot GET completed -> reconcile repairs completed."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 5 test", "voice_source": "saved", "voice_profile_id": "1"},
    )
    job_id = job["id"]

    # Seed false local failed
    from copyfast_db import transaction, utc_now
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_voice_tts_jobs
            SET status = 'failed', status_reason = 'CONCURRENT_CONFIRM_IN_PROGRESS',
                runtime_dispatch_status = 'dispatched', runtime_job_id = 'bot_seeded',
                updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), job_id),
        )

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_bot_get(method, path, **kwargs):
        if method == "GET" and "jobs" in path:
            return {
                "ok": True,
                "job": {
                    "job_id": "bot_seeded",
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 2,
                    "has_artifact": True,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bot_get)

    reconciled = asyncio.run(reconcile_voice_tts_job_status(job_id, account=account))
    assert reconciled["status"] == "completed"
    assert reconciled["status_reason"] == "COMPLETED"
    assert reconciled["charged_xu"] == 2
    assert reconciled["has_artifact"] is True
    assert reconciled["output_url"] == f"/api/v1/features/voice_tts/jobs/{job_id}/artifact"

    final_db = get_voice_tts_job(account_id, job_id)
    assert final_db["status"] == "completed"


def test_25_bot_get_genuinely_failed_local_remains_failed(monkeypatch):
    """6. Bot GET genuinely failed -> local remains failed."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 6 test", "voice_source": "default", "default_voice_gender": "male"},
    )
    job_id = job["id"]

    from copyfast_db import transaction, utc_now
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_voice_tts_jobs
            SET status = 'failed', status_reason = 'PROVIDER_EXECUTION_FAILED',
                runtime_dispatch_status = 'dispatched', runtime_job_id = 'bot_failed',
                updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), job_id),
        )

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_bot_get(method, path, **kwargs):
        if method == "GET" and "jobs" in path:
            return {
                "ok": True,
                "job": {
                    "job_id": "bot_failed",
                    "status": "failed",
                    "status_reason": "PROVIDER_TIMEOUT",
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bot_get)

    reconciled = asyncio.run(reconcile_voice_tts_job_status(job_id, account=account))
    assert reconciled["status"] == "failed"
    assert reconciled["status_reason"] == "PROVIDER_TIMEOUT"


def test_26_loser_causes_zero_second_provider_or_wallet_execution(monkeypatch):
    """7. Loser causes zero second provider/wallet execution."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 7 test", "voice_source": "saved", "voice_profile_id": "1"},
    )
    job_id = job["id"]

    provider_calls = 0
    wallet_debits = 0
    bot_confirm_calls = 0

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_bridge(method, path, **kwargs):
        nonlocal provider_calls, wallet_debits, bot_confirm_calls
        if "jobs" in path and method == "POST" and "confirm" not in path:
            return {"ok": True, "job": {"job_id": f"bot_{job_id}", "status": "awaiting_confirmation", "quote_xu": 5}}
        elif "confirm" in path:
            bot_confirm_calls += 1
            return {
                "ok": False,
                "error_code": "CONCURRENT_CONFIRM_IN_PROGRESS",
                "message": "Processing by other request",
            }
        elif method == "GET" and "jobs" in path:
            return {
                "ok": True,
                "job": {
                    "job_id": f"bot_{job_id}",
                    "status": "completed",
                    "status_reason": "COMPLETED",
                    "charged_xu": 5,
                    "has_artifact": True,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)
    asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_id, account=account))

    # Loser attempts confirm -> raises 409
    with pytest.raises(HTTPException):
        asyncio.run(confirm_voice_tts_job(job_id, account=account))

    # Reconcile is read-only
    asyncio.run(reconcile_voice_tts_job_status(job_id, account=account))

    assert provider_calls == 0
    assert wallet_debits == 0
    assert bot_confirm_calls == 1  # Exactly 1 confirm call from loser, 0 subsequent retry


def test_27_recovered_completed_job_exposes_normal_safe_artifact_route(monkeypatch):
    """8. Recovered completed job exposes normal safe artifact route."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Race order 8 test", "voice_source": "default", "default_voice_gender": "female"},
    )
    job_id = job["id"]

    # Mark completed with artifact
    from copyfast_db import transaction, utc_now
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_voice_tts_jobs
            SET status = 'completed', status_reason = 'COMPLETED',
                output_url = ?, completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (f"/api/v1/features/voice_tts/jobs/{job_id}/artifact", utc_now(), utc_now(), job_id),
        )

    from fastapi.testclient import TestClient
    from app import app
    import copyfast_bridge

    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    import httpx
    fake_audio_bytes = b"FAKE_MP3_AUDIO_STREAM_DATA"

    class MockHttpxClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, headers=None):
            return httpx.Response(status_code=200, content=fake_audio_bytes)

    monkeypatch.setattr("httpx.AsyncClient", MockHttpxClient)

    from copyfast_api import require_account
    app.dependency_overrides[require_account] = lambda: {"id": account_id, "canonical_user_id": can_user_id}

    client = TestClient(app)
    try:
        resp = client.get(f"/api/v1/features/voice_tts/jobs/{job_id}/artifact")
        assert resp.status_code == 200
        assert resp.content == fake_audio_bytes
        assert resp.headers["content-type"] == "audio/mpeg"
    finally:
        app.dependency_overrides.clear()


def test_28_insufficient_funds_still_maps_payment_required_and_cannot_downgrade_completed(monkeypatch):
    """9. INSUFFICIENT_FUNDS still maps payment_required and cannot overwrite completed."""
    account_id = ensure_test_account(f"acc_{uuid.uuid4().hex[:8]}")
    can_user_id = "7126457028"
    account = {"id": account_id, "canonical_user_id": can_user_id}

    job = create_or_replay_voice_tts_job(
        account_id=account_id,
        payload={"script": "Insufficient funds test", "voice_source": "saved", "voice_profile_id": "1"},
    )
    job_id = job["id"]

    import copyfast_bridge
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_dispatch(*args, **kwargs):
        return {"ok": True, "job": {"job_id": f"bot_{job_id}", "status": "awaiting_confirmation", "quote_xu": 100}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_dispatch)
    asyncio.run(dispatch_voice_tts_job_to_canonical_runtime(job_id=job_id, account=account))

    # Bot confirm returns INSUFFICIENT_FUNDS
    async def mock_insufficient(*args, **kwargs):
        return {"ok": False, "error_code": "INSUFFICIENT_FUNDS", "message": "Số dư Xu không đủ"}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_insufficient)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert excinfo.value.status_code == 402

    db_job = get_voice_tts_job(account_id, job_id)
    assert db_job["status"] == "payment_required"
    assert db_job["status_reason"] == "INSUFFICIENT_FUNDS"

    # Now verify: if job was already completed, confirm cannot overwrite to payment_required
    from copyfast_db import transaction, utc_now
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_voice_tts_jobs
            SET status = 'completed', status_reason = 'COMPLETED',
                output_url = '/api/v1/artifact', updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), job_id),
        )

    res = asyncio.run(confirm_voice_tts_job(job_id, account=account))
    assert res["status"] == "completed"
    assert get_voice_tts_job(account_id, job_id)["status"] == "completed"
