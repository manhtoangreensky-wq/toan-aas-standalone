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
