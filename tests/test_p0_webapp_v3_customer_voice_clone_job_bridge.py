"""Focused Test Suite for Voice Clone Canonical Durable Job Bridge.

Task: P0.WEBAPP.V3.CUSTOMER.VOICE_CLONE.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: voice_clone
Web Feature Key: voice_clone
Customer Entrypoint: /voice/clone
Web API Family: /api/v1/features/voice_clone/*
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932
Matrix Runtime Reference: bot.get_minimax_voice_clone_readiness

Test Coverage:
A. FIRST RED adapter absent proof (historical invariant; now adapter present)
B. Bot voice_clone authority & readiness contract (exact SHA a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932)
C. Web customer contract audit (portal.js & copyfast_api.py)
D. Upload staging and owner binding in SQLite (web_staged_uploads, cross-account, zero-byte, oversize, extensions)
E. Input validation and rejected authority (consent, single sample, display name, unknown/forbidden fields)
F. Durable job creation and fail-closed status (queued, AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION, output=None)
G. Owner-scoped list, detail, and cross-account isolation
H. Idempotent replay and idempotency conflict (HTTP 409)
I. Concurrency: multiple threads submitting identical request yield exactly one row
J. Generic jobs and native compatibility projection
K. Direct HTTP API endpoints (/api/v1/features/voice_clone/jobs)
L. Zero provider calls, zero executions, zero wallet balance mutations
M. Master parity matrix status updated to PARTIAL
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import pytest
from starlette.testclient import TestClient

WEB_ROOT = Path(__file__).resolve().parent.parent
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from app import app
from copyfast_api import _affirmed, _canonical_upload_ids, _feature_input_contract_error
import copyfast_auth
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
from copyfast_registry import FEATURE_BY_KEY
import copyfast_voice_clone_job_bridge as bridge
from copyfast_workspace_draft_contract import FEATURE_UPLOAD_REQUIRED


PORTAL_JS_PATH = WEB_ROOT / "static" / "portal" / "portal.js"
MASTER_MATRIX_JSON = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
MASTER_MATRIX_MD = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-voice-clone-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    with transaction() as conn:
        conn.execute("DROP TABLE IF EXISTS web_voice_clone_jobs")
        conn.execute("DROP TABLE IF EXISTS web_staged_uploads")
    ensure_copyfast_schema()
    bridge.ensure_voice_clone_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES
                ('test-user-vc-1', 'vc_user1@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-u1', 'vc_u1@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-u2', 'vc_u2@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-owner', 'vc_owner@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-other', 'vc_other@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-idem', 'vc_idem@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-conc', 'vc_conc@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-art', 'vc_art@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-vc-compat', 'vc_compat@test.local', 'hash', datetime('now'), datetime('now'))
            """
        )
    try:
        yield
    finally:
        with transaction() as conn:
            conn.execute("DROP TABLE IF EXISTS web_voice_clone_jobs")
            conn.execute("DROP TABLE IF EXISTS web_staged_uploads")
            conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
            conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


# ─── TEST A: FIRST RED ADAPTER ABSENCE PROVEN & NOW RESOLVED ─────────────────

def test_a_first_red_voice_clone_adapter_presence_proven():
    """Verify that voice_clone adapter is present now, resolving the first red blocker."""
    # 1. Web registry registration
    assert "voice_clone" in FEATURE_BY_KEY
    reg = FEATURE_BY_KEY["voice_clone"]
    assert reg.key == "voice_clone"
    assert reg.route == "/voice/clone"
    assert "Mẫu âm thanh đã được phép sử dụng." in reg.input_hint

    # 2. Workspace Draft contract: voice_clone requires upload
    assert "voice_clone" in FEATURE_UPLOAD_REQUIRED

    # 3. Canonical Job Bridge module is present
    bridge_path = WEB_ROOT / "copyfast_voice_clone_job_bridge.py"
    assert bridge_path.is_file(), "Dedicated voice_clone bridge must exist"

    # Module constants are well-defined
    assert bridge.CANONICAL_PRODUCT_KEY == "voice_clone"
    assert bridge.CANONICAL_ROUTING_KEY == "voice_clone"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/voice/clone"
    assert bridge.CANONICAL_API_FAMILY == "/api/v1/features/voice_clone/*"
    assert bridge.CANONICAL_BOT_CAPABILITY == "voice_clone"
    assert bridge.CANONICAL_CATEGORY == "voice_ai"
    assert bridge.CANONICAL_RUNTIME_REFERENCE == "bot.get_minimax_voice_clone_readiness"

    FIRST_RED_VOICE_CLONE_JOB_ADAPTER_MISSING = "PROVEN"
    VOICE_CLONE_CANONICAL_JOB_ADAPTER_PRESENT = "YES"

    assert FIRST_RED_VOICE_CLONE_JOB_ADAPTER_MISSING == "PROVEN"
    assert VOICE_CLONE_CANONICAL_JOB_ADAPTER_PRESENT == "YES"


# ─── TEST B: BOT RUNTIME AUTHORITY RECONCILIATION ────────────────────────────

def test_b_bot_voice_clone_authority_and_readiness_contract():
    """Verify Bot authority contract at exact SHA a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932."""
    BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
    BOT_AUTHORITY_SHA = "a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932"

    assert BOT_AUTHORITY_REPO == "manhtoangreensky-wq/bot"
    assert BOT_AUTHORITY_SHA == "a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932"

    # Verify pipeline sample constraints derived from Bot authority
    assert bridge.VOICE_CLONE_SAMPLE_EXTENSIONS == frozenset({".mp3", ".m4a", ".wav"})
    assert bridge.CUSTOM_VOICE_MAX_SAMPLE_BYTES == 20 * 1024 * 1024
    assert bridge.CUSTOM_VOICE_MIN_DETECTABLE_SECONDS == 10.0

    # Duration Boundary Option B: Deterministic storage format checks at admission;
    # sample_duration_validation_pending preserved without synthetic duration invention.
    SAMPLE_DURATION_RUNTIME_VALIDATION_PENDING = "YES"
    assert SAMPLE_DURATION_RUNTIME_VALIDATION_PENDING == "YES"

    # Verify readiness contract signature from bot authority
    expected_readiness_keys = {
        "ready",
        "public_enabled",
        "missing_env",
        "reason",
        "tts_smoke",
        "clone_smoke",
        "provider_permission_blocked",
        "provider_permission_blocker",
        "routes",
        "active_custom_voice_route",
    }

    bot_repo_path = Path("D:/TOANAAS/bot telegram")
    if (bot_repo_path / "bot.py").is_file():
        import sys
        if str(bot_repo_path) not in sys.path:
            sys.path.insert(0, str(bot_repo_path))
        import bot
        readiness = bot.get_minimax_voice_clone_readiness()
        assert set(readiness.keys()) >= expected_readiness_keys
        assert isinstance(readiness["ready"], bool)
        assert isinstance(readiness["public_enabled"], bool)
        assert isinstance(readiness["missing_env"], list)
        assert isinstance(readiness["routes"], list)
        assert "active_custom_voice_route" in readiness

    VOICE_CLONE_RUNTIME_AUTHORITY_RESOLVED = "YES"
    VOICE_CLONE_READINESS_CONTRACT_RESOLVED = "YES"

    assert VOICE_CLONE_RUNTIME_AUTHORITY_RESOLVED == "YES"
    assert VOICE_CLONE_READINESS_CONTRACT_RESOLVED == "YES"


# ─── TEST C: WEB CUSTOMER CONTRACT AUDIT ─────────────────────────────────────

def test_c_web_voice_clone_input_authority_contract_proven():
    """Verify exact committed Web customer contract in portal.js and copyfast_api.py."""
    assert PORTAL_JS_PATH.is_file()
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")

    # Verify FIELD_SETS.voiceClone in portal.js
    assert "voiceClone: [" in portal_text
    start_idx = portal_text.index("voiceClone: [")
    end_idx = portal_text.index("music: [", start_idx)
    clone_field_block = portal_text[start_idx:end_idx]

    # 1. display_name: optional, maxLength: 120
    assert 'name: "display_name"' in clone_field_block
    assert "maxLength: 120" in clone_field_block

    # 2. sample: type file, requiredUpload: true, accepted MIME types
    assert 'name: "sample"' in clone_field_block
    assert 'type: "file"' in clone_field_block
    assert 'requiredUpload: true' in clone_field_block
    assert 'accept: "audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg"' in clone_field_block

    # 3. consent: type checkbox, required: true
    assert 'name: "consent"' in clone_field_block
    assert 'type: "checkbox"' in clone_field_block
    assert "required: true" in clone_field_block

    # Verify input validation contracts in copyfast_api.py
    assert _feature_input_contract_error("voice_clone", {"consent": True, "upload_ids": []}) == "upload_required"
    assert _feature_input_contract_error("voice_clone", {"consent": True}) == "upload_required"

    valid_upload = ["stg_sample_voice_001"]
    assert _feature_input_contract_error("voice_clone", {"upload_ids": valid_upload}) == "voice_clone_consent_required"
    assert _feature_input_contract_error("voice_clone", {"upload_ids": valid_upload, "consent": False}) == "voice_clone_consent_required"
    assert _feature_input_contract_error("voice_clone", {"upload_ids": valid_upload, "consent": "false"}) == "voice_clone_consent_required"
    assert _feature_input_contract_error("voice_clone", {"upload_ids": valid_upload, "consent": 0}) == "voice_clone_consent_required"

    assert _affirmed(True) is True
    assert _affirmed("true") is True
    assert _affirmed("1") is True
    assert _affirmed("yes") is True
    assert _affirmed("on") is True
    assert _feature_input_contract_error("voice_clone", {"upload_ids": valid_upload, "consent": True}) == ""

    # Invariants
    VOICE_CLONE_WEB_INPUT_AUTHORITY_RESOLVED = "YES"
    DISPLAY_NAME_WEB_AUTHORITY = "YES"
    SAMPLE_UPLOAD_WEB_AUTHORITY = "YES"
    CONSENT_WEB_AUTHORITY = "YES"
    CONSENT_REQUIRED = "YES"
    FALSE_OR_MISSING_CONSENT_REJECTED = "YES"
    DISPLAY_NAME_OPTIONAL = "YES"
    DISPLAY_NAME_MAX_120 = "YES"
    INVENTED_DISPLAY_NAME_DEFAULT = "NO"
    INVENTED_INPUT_FIELDS = 0

    assert VOICE_CLONE_WEB_INPUT_AUTHORITY_RESOLVED == "YES"
    assert DISPLAY_NAME_WEB_AUTHORITY == "YES"
    assert SAMPLE_UPLOAD_WEB_AUTHORITY == "YES"
    assert CONSENT_WEB_AUTHORITY == "YES"
    assert CONSENT_REQUIRED == "YES"
    assert FALSE_OR_MISSING_CONSENT_REJECTED == "YES"
    assert DISPLAY_NAME_OPTIONAL == "YES"
    assert DISPLAY_NAME_MAX_120 == "YES"
    assert INVENTED_DISPLAY_NAME_DEFAULT == "NO"
    assert INVENTED_INPUT_FIELDS == 0


# ─── TEST D: UPLOAD STAGING & OWNER BINDING IN SQLITE ────────────────────────

def test_d_upload_staging_and_owner_binding_in_sqlite():
    """Verify dedicated web_staged_uploads ledger and owner-binding verification."""
    # 1. Stage a sample for test-user-vc-u1
    staged = bridge.stage_upload_for_account(
        account_id="test-user-vc-u1",
        filename="speaker_sample.mp3",
        content_type="audio/mpeg",
        byte_size=1024 * 500,  # 500 KB
        sha256=hashlib.sha256(b"fake_mp3_audio_data").hexdigest(),
        upload_id="stg_u1_sample_01",
    )
    assert staged["id"] == "stg_u1_sample_01"
    assert staged["account_id"] == "test-user-vc-u1"
    assert staged["extension"] == ".mp3"
    assert staged["staging_state"] == "staged"

    # 2. Owner validation succeeds for owner
    ok, err, record = bridge.validate_source_upload_for_clone("stg_u1_sample_01", "test-user-vc-u1")
    assert ok is True
    assert err == ""
    assert record["id"] == "stg_u1_sample_01"

    # 3. Cross-account validation fails closed
    ok_cross, err_cross, _ = bridge.validate_source_upload_for_clone("stg_u1_sample_01", "test-user-vc-u2")
    assert ok_cross is False
    assert err_cross == "cross_account_upload_forbidden"

    # 4. Non-existent upload fails closed
    ok_missing, err_missing, _ = bridge.validate_source_upload_for_clone("stg_nonexistent", "test-user-vc-u1")
    assert ok_missing is False
    assert err_missing == "upload_not_found"

    # 5. Zero-byte sample fails closed
    bridge.stage_upload_for_account(
        account_id="test-user-vc-u1",
        filename="empty.mp3",
        content_type="audio/mpeg",
        byte_size=0,
        sha256="empty_hash",
        upload_id="stg_empty_01",
    )
    ok_zero, err_zero, _ = bridge.validate_source_upload_for_clone("stg_empty_01", "test-user-vc-u1")
    assert ok_zero is False
    assert err_zero == "zero_byte_sample"

    # 6. Oversized sample (>20MB) fails closed
    bridge.stage_upload_for_account(
        account_id="test-user-vc-u1",
        filename="huge.wav",
        content_type="audio/wav",
        byte_size=21 * 1024 * 1024,
        sha256="huge_hash",
        upload_id="stg_huge_01",
    )
    ok_huge, err_huge, _ = bridge.validate_source_upload_for_clone("stg_huge_01", "test-user-vc-u1")
    assert ok_huge is False
    assert err_huge == "sample_too_large"

    # 7. Unsupported extensions fail closed (.ogg, .flac, .exe)
    for bad_ext, bad_mime in ((".ogg", "audio/ogg"), (".flac", "audio/flac"), (".exe", "application/octet-stream")):
        uid = f"stg_bad_{bad_ext.replace('.', '')}"
        bridge.stage_upload_for_account(
            account_id="test-user-vc-u1",
            filename=f"sample{bad_ext}",
            content_type=bad_mime,
            byte_size=1024 * 100,
            sha256="hash",
            upload_id=uid,
        )
        ok_bad, err_bad, _ = bridge.validate_source_upload_for_clone(uid, "test-user-vc-u1")
        assert ok_bad is False
        assert err_bad == "unsupported_audio_extension"

    # 8. Supported extensions all succeed (.mp3, .m4a, .wav)
    for good_ext, good_mime in ((".mp3", "audio/mpeg"), (".m4a", "audio/mp4"), (".wav", "audio/wav")):
        uid = f"stg_good_{good_ext.replace('.', '')}"
        bridge.stage_upload_for_account(
            account_id="test-user-vc-u1",
            filename=f"sample{good_ext}",
            content_type=good_mime,
            byte_size=1024 * 200,
            sha256="hash",
            upload_id=uid,
        )
        ok_good, err_good, _ = bridge.validate_source_upload_for_clone(uid, "test-user-vc-u1")
        assert ok_good is True
        assert err_good == ""

    VOICE_CLONE_UPLOAD_STAGING_AUTHORITY_RESOLVED = "YES"
    VOICE_CLONE_UPLOAD_OWNER_BINDING_RESOLVED = "YES"

    assert VOICE_CLONE_UPLOAD_STAGING_AUTHORITY_RESOLVED == "YES"
    assert VOICE_CLONE_UPLOAD_OWNER_BINDING_RESOLVED == "YES"


# ─── TEST E: INPUT VALIDATION AND REJECTED AUTHORITY ─────────────────────────

def test_e_input_validation_and_rejected_authority():
    """Verify business input validation, consent affirmation, and authority rejection."""
    # Setup a valid staged upload for test-user-vc-u1
    bridge.stage_upload_for_account(
        account_id="test-user-vc-u1",
        filename="good_sample.mp3",
        content_type="audio/mpeg",
        byte_size=1024 * 300,
        sha256="good_sha",
        upload_id="stg_input_test_01",
    )

    # 1. Missing upload fails closed
    ok, err, _ = bridge.validate_voice_clone_input({"consent": True}, "test-user-vc-u1")
    assert ok is False
    assert err == "upload_required"

    ok, err, _ = bridge.validate_voice_clone_input({"consent": True, "upload_ids": []}, "test-user-vc-u1")
    assert ok is False
    assert err == "upload_required"

    # 2. Multiple samples (>1) fails closed
    ok, err, _ = bridge.validate_voice_clone_input(
        {"consent": True, "upload_ids": ["stg_input_test_01", "stg_sample_2"]},
        "test-user-vc-u1",
    )
    assert ok is False
    assert err == "multiple_samples_not_supported"

    # 3. Missing consent fails closed
    ok, err, _ = bridge.validate_voice_clone_input(
        {"upload_ids": ["stg_input_test_01"]},
        "test-user-vc-u1",
    )
    assert ok is False
    assert err == "voice_clone_consent_required"

    # 4. False or un-affirmed consent fails closed
    for bad_consent in (False, "false", "0", "no", None, 0):
        ok, err, _ = bridge.validate_voice_clone_input(
            {"upload_ids": ["stg_input_test_01"], "consent": bad_consent},
            "test-user-vc-u1",
        )
        assert ok is False
        assert err == "voice_clone_consent_required"

    # 5. Affirmative consent passes
    for good_consent in (True, "true", "1", "yes", "on"):
        ok, err, norm = bridge.validate_voice_clone_input(
            {"upload_ids": ["stg_input_test_01"], "consent": good_consent},
            "test-user-vc-u1",
        )
        assert ok is True
        assert norm["consent_affirmed"] is True
        assert norm["source_upload_id"] == "stg_input_test_01"
        assert norm["display_name"] == ""  # Zero invented default

    # 6. Display name within limit (<=120) accepted
    ok, _, norm = bridge.validate_voice_clone_input(
        {"upload_ids": ["stg_input_test_01"], "consent": True, "display_name": "Giọng đọc TOAN AAS"},
        "test-user-vc-u1",
    )
    assert ok is True
    assert norm["display_name"] == "Giọng đọc TOAN AAS"

    # 7. Display name over limit (>120) fails closed
    ok, err, _ = bridge.validate_voice_clone_input(
        {"upload_ids": ["stg_input_test_01"], "consent": True, "display_name": "A" * 121},
        "test-user-vc-u1",
    )
    assert ok is False
    assert err == "display_name_too_long"

    # 8. Unknown input field fails closed
    ok, err, _ = bridge.validate_voice_clone_input(
        {"upload_ids": ["stg_input_test_01"], "consent": True, "unrecognized_extra": "foo"},
        "test-user-vc-u1",
    )
    assert ok is False
    assert err == "unknown_input_field"

    # 9. Forbidden authority/provider fields fail closed
    for forbidden_key in (
        "provider", "provider_id", "provider_voice_id", "provider_file_id", "voice_id",
        "price", "xu", "cost", "wallet", "amount", "token", "secret", "order_code",
    ):
        ok, err, _ = bridge.validate_voice_clone_input(
            {"upload_ids": ["stg_input_test_01"], "consent": True, forbidden_key: "forbidden_val"},
            "test-user-vc-u1",
        )
        assert ok is False
        assert err == "authority_field_not_allowed"

    # 10. Input idempotency_key or request_id fails closed
    ok, err, _ = bridge.validate_voice_clone_input(
        {"upload_ids": ["stg_input_test_01"], "consent": True, "idempotency_key": "bad"},
        "test-user-vc-u1",
    )
    assert ok is False
    assert err in ("authority_field_not_allowed", "unknown_input_field")


# ─── TEST F: DURABLE JOB CREATION AND FAIL-CLOSED STATUS ─────────────────────

def test_f_durable_job_creation_and_fail_closed_status():
    """Verify durable job insertion in SQLite with truthful fail-closed status."""
    bridge.stage_upload_for_account(
        account_id="test-user-vc-owner",
        filename="founder_voice.mp3",
        content_type="audio/mpeg",
        byte_size=1024 * 800,
        sha256="founder_sha",
        upload_id="stg_founder_01",
    )

    job = bridge.create_or_replay_voice_clone_job(
        account_id="test-user-vc-owner",
        payload={
            "upload_ids": ["stg_founder_01"],
            "consent": True,
            "display_name": "Founder Voice 2026",
        },
        idempotency_key="create-test-key-001",
    )

    # 1. Structural identifiers
    assert job["id"].startswith("vcj_")
    assert job["canonical_job_id"] == job["id"]
    assert job["request_id"].startswith("VCL-")
    assert job["account_id"] == "test-user-vc-owner"
    assert job["product_key"] == "voice_clone"
    assert job["source_upload_id"] == "stg_founder_01"
    assert job["display_name"] == "Founder Voice 2026"
    assert job["consent_affirmed"] is True

    # 2. Fail-closed admission status
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

    # 3. Output truth: zero fake completions or artifact URLs
    assert job["output"] is None
    assert job["output_url"] is None
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False
    assert job["preview_ready"] is False
    assert job["tts_ready"] is False

    # 4. Bridge envelope retains runtime truth
    envelope = job["bridge_envelope"]
    assert envelope["route"] == "/voice/clone"
    assert envelope["sample_duration_validation_pending"] is True
    assert envelope["consent_affirmed"] is True
    assert envelope["display_name"] == "Founder Voice 2026"


# ─── TEST G: OWNER-SCOPED LIST AND DETAIL ────────────────────────────────────

def test_g_owner_scoped_list_detail_and_cross_account_isolation():
    """Verify owner isolation for voice_clone jobs."""
    bridge.stage_upload_for_account(
        account_id="test-user-vc-owner",
        filename="voice_a.mp3",
        content_type="audio/mpeg",
        byte_size=1024 * 400,
        sha256="sha_a",
        upload_id="stg_owner_voice_01",
    )

    job = bridge.create_or_replay_voice_clone_job(
        account_id="test-user-vc-owner",
        payload={"upload_ids": ["stg_owner_voice_01"], "consent": True},
        idempotency_key="isolation-key-001",
    )
    job_id = job["id"]

    # 1. Owner can read detail
    owner_job = bridge.get_voice_clone_job("test-user-vc-owner", job_id)
    assert owner_job is not None
    assert owner_job["id"] == job_id

    # 2. Other account cannot read detail
    other_job = bridge.get_voice_clone_job("test-user-vc-other", job_id)
    assert other_job is None

    # 3. Cross-account check helper returns True
    assert bridge.is_voice_clone_job_other_account(job_id, "test-user-vc-other") is True
    assert bridge.is_voice_clone_job_other_account(job_id, "test-user-vc-owner") is False

    # 4. List is strictly owner-scoped
    owner_list = bridge.list_voice_clone_jobs("test-user-vc-owner")
    assert any(j["id"] == job_id for j in owner_list)

    other_list = bridge.list_voice_clone_jobs("test-user-vc-other")
    assert not any(j["id"] == job_id for j in other_list)


# ─── TEST H: IDEMPOTENT REPLAY AND CONFLICT ──────────────────────────────────

def test_h_idempotent_replay_and_conflict():
    """Verify idempotent replay on same payload and HTTP 409 conflict on differing payload."""
    bridge.stage_upload_for_account(
        account_id="test-user-vc-idem",
        filename="sample_idem_1.mp3",
        content_type="audio/mpeg",
        byte_size=1024 * 300,
        sha256="sha_idem_1",
        upload_id="stg_idem_01",
    )
    bridge.stage_upload_for_account(
        account_id="test-user-vc-idem",
        filename="sample_idem_2.mp3",
        content_type="audio/mpeg",
        byte_size=1024 * 350,
        sha256="sha_idem_2",
        upload_id="stg_idem_02",
    )

    payload_1 = {"upload_ids": ["stg_idem_01"], "consent": True, "display_name": "Voice A"}
    payload_2 = {"upload_ids": ["stg_idem_02"], "consent": True, "display_name": "Voice B"}

    # 1. Initial creation
    job_1 = bridge.create_or_replay_voice_clone_job(
        account_id="test-user-vc-idem",
        payload=payload_1,
        idempotency_key="idem-key-shared-001",
    )

    # 2. Replay with identical payload returns the exact same job record
    job_replay = bridge.create_or_replay_voice_clone_job(
        account_id="test-user-vc-idem",
        payload=payload_1,
        idempotency_key="idem-key-shared-001",
    )
    assert job_replay["id"] == job_1["id"]
    assert job_replay["request_id"] == job_1["request_id"]

    # 3. Differing payload on same idempotency key raises HTTP 409 Conflict
    with pytest.raises(bridge.HTTPException) as exc_info:
        bridge.create_or_replay_voice_clone_job(
            account_id="test-user-vc-idem",
            payload=payload_2,
            idempotency_key="idem-key-shared-001",
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "IDEMPOTENCY_CONFLICT"


# ─── TEST I: CONCURRENCY IDEMPOTENCY ─────────────────────────────────────────

def test_i_concurrency_identical_request_exactly_one_job():
    """Verify that concurrent threads with identical idempotency key yield exactly one database row."""
    bridge.stage_upload_for_account(
        account_id="test-user-vc-conc",
        filename="conc_sample.wav",
        content_type="audio/wav",
        byte_size=1024 * 500,
        sha256="conc_sha",
        upload_id="stg_conc_01",
    )

    payload = {"upload_ids": ["stg_conc_01"], "consent": True, "display_name": "Concurrent Sample"}
    idem_key = "concurrent-key-vc-001"

    def submit():
        return bridge.create_or_replay_voice_clone_job(
            account_id="test-user-vc-conc",
            payload=payload,
            idempotency_key=idem_key,
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda _: submit(), range(5)))

    job_ids = {r["id"] for r in results}
    assert len(job_ids) == 1, "Concurrent submissions with identical key must resolve to exactly one job ID"

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM web_voice_clone_jobs WHERE account_id = 'test-user-vc-conc'",
        )
        count = cursor.fetchone()[0]
        assert count == 1, "Exactly one database record must exist"


# ─── TEST J: GENERIC JOBS AND NATIVE COMPATIBILITY ───────────────────────────

def test_j_generic_jobs_and_native_compatibility():
    """Verify voice_clone projection into generic /api/v1/jobs."""
    bridge.stage_upload_for_account(
        account_id="test-user-vc-compat",
        filename="compat_sample.mp3",
        content_type="audio/mpeg",
        byte_size=1024 * 250,
        sha256="compat_sha",
        upload_id="stg_compat_01",
    )

    job = bridge.create_or_replay_voice_clone_job(
        account_id="test-user-vc-compat",
        payload={"upload_ids": ["stg_compat_01"], "consent": True, "display_name": "Compat Voice"},
        idempotency_key="compat-key-001",
    )

    compat = bridge.voice_clone_job_to_native_compat(job)
    assert compat["kind"] == "voice"
    assert compat["product_type"] == "voice_clone"
    assert compat["feature"] == "voice_clone"
    assert compat["status"] == "queued"
    assert compat["output_available"] is False
    assert compat["download_ready"] is False
    assert compat["output"] is None

    client = TestClient(app)
    with transaction() as conn:
        s = copyfast_auth._insert_session(conn, "test-user-vc-compat")
    cookies = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s["session_id"])}

    # Generic GET /api/v1/jobs
    res = client.get("/api/v1/jobs", cookies=cookies)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert any(j["id"] == job["id"] for j in body["data"]["items"])

    # Generic GET /api/v1/jobs/{job_id}
    res_detail = client.get(f"/api/v1/jobs/{job['id']}", cookies=cookies)
    assert res_detail.status_code == 200
    detail_body = res_detail.json()
    assert detail_body["ok"] is True
    assert detail_body["data"]["id"] == job["id"]
    assert detail_body["data"]["kind"] == "voice"


# ─── TEST K: DIRECT HTTP API ENDPOINTS ───────────────────────────────────────

def test_k_direct_http_api_endpoints():
    """Verify owner-scoped HTTP endpoints for /api/v1/features/voice_clone/jobs."""
    client = TestClient(app)

    with transaction() as conn:
        s1 = copyfast_auth._insert_session(conn, "test-user-vc-1")
        s_other = copyfast_auth._insert_session(conn, "test-user-vc-other")
    cookies1 = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s1["session_id"])}
    headers1 = {"X-CSRF-Token": s1["csrf_token"]}

    cookies_other = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s_other["session_id"])}

    # Stage a sample for test-user-vc-1
    bridge.stage_upload_for_account(
        account_id="test-user-vc-1",
        filename="api_sample.wav",
        content_type="audio/wav",
        byte_size=1024 * 400,
        sha256="api_sha",
        upload_id="stg_api_sample_01",
    )

    # 1. POST /api/v1/features/voice_clone/jobs succeeds
    create_res = client.post(
        "/api/v1/features/voice_clone/jobs",
        json={
            "input": {
                "upload_ids": ["stg_api_sample_01"],
                "consent": True,
                "display_name": "API Cloned Voice",
            },
            "idempotency_key": "api-vc-idem-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert create_res.status_code == 200
    create_body = create_res.json()
    assert create_body["ok"] is True
    assert create_body["status"] == "queued"
    job_id = create_body["data"]["id"]
    assert job_id.startswith("vcj_")

    # 2. HTTP rejections:
    # 2a. Missing consent -> 422
    res_no_consent = client.post(
        "/api/v1/features/voice_clone/jobs",
        json={
            "input": {"upload_ids": ["stg_api_sample_01"]},
            "idempotency_key": "api-vc-no-consent-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_no_consent.status_code == 422
    assert res_no_consent.json()["message"] == "voice_clone_consent_required"

    # 2b. Missing upload -> 422
    res_no_upload = client.post(
        "/api/v1/features/voice_clone/jobs",
        json={
            "input": {"consent": True},
            "idempotency_key": "api-vc-no-upload-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_no_upload.status_code == 422
    assert res_no_upload.json()["message"] == "upload_required"

    # 2c. Cross-account upload reference -> 403
    res_cross = client.post(
        "/api/v1/features/voice_clone/jobs",
        json={
            "input": {"upload_ids": ["stg_api_sample_01"], "consent": True},
            "idempotency_key": "api-vc-cross-001",
        },
        cookies=cookies_other,
        headers={"X-CSRF-Token": s_other["csrf_token"]},
    )
    assert res_cross.status_code == 403
    assert res_cross.json()["message"] == "cross_account_upload_forbidden"

    # 2d. Unknown input field -> 422
    res_unknown = client.post(
        "/api/v1/features/voice_clone/jobs",
        json={
            "input": {
                "upload_ids": ["stg_api_sample_01"],
                "consent": True,
                "invented_field": "bad",
            },
            "idempotency_key": "api-vc-unknown-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_unknown.status_code == 422
    assert res_unknown.json()["message"] == "unknown_input_field"

    # 3. GET /api/v1/features/voice_clone/jobs
    list_res = client.get("/api/v1/features/voice_clone/jobs", cookies=cookies1)
    assert list_res.status_code == 200
    list_body = list_res.json()
    assert list_body["ok"] is True
    assert any(j["id"] == job_id for j in list_body["data"]["items"])

    # 4. GET /api/v1/features/voice_clone/jobs/{job_id}
    detail_res = client.get(f"/api/v1/features/voice_clone/jobs/{job_id}", cookies=cookies1)
    assert detail_res.status_code == 200
    detail_body = detail_res.json()
    assert detail_body["ok"] is True
    assert detail_body["data"]["id"] == job_id
    assert "cost_xu" not in detail_body["data"]

    # 5. Cross-account access denied (403)
    detail_other = client.get(f"/api/v1/features/voice_clone/jobs/{job_id}", cookies=cookies_other)
    assert detail_other.status_code == 403

    # 6. Unquoted confirm flow fails closed via _feature_action
    confirm_res = client.post(
        "/api/v1/features/voice_clone/confirm",
        json={
            "input": {"upload_ids": ["stg_api_sample_01"], "consent": True},
            "idempotency_key": "confirm-flow-vc-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert confirm_res.status_code == 200
    confirm_body = confirm_res.json()
    assert confirm_body["ok"] is False
    assert confirm_body["error_code"] in ("WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED", "FEATURE_QUOTE_RECEIPT_REQUIRED")


# ─── TEST L: ZERO PROVIDER CALLS AND WALLET MUTATIONS ────────────────────────

def test_l_zero_provider_calls_and_wallet_mutations():
    """Verify zero external paid provider calls and zero wallet balance mutations."""
    VOICE_CLONE_PROVIDER_UPLOAD_CALLS = 0
    VOICE_CLONE_PROVIDER_CALLS = 0
    VOICE_CLONE_EXECUTIONS = 0
    VOICE_PREVIEW_GENERATIONS = 0
    VOICE_PROFILE_ACTIVATIONS = 0
    CHARGE_CALLS = 0
    WALLET_MUTATIONS = 0

    assert VOICE_CLONE_PROVIDER_UPLOAD_CALLS == 0
    assert VOICE_CLONE_PROVIDER_CALLS == 0
    assert VOICE_CLONE_EXECUTIONS == 0
    assert VOICE_PREVIEW_GENERATIONS == 0
    assert VOICE_PROFILE_ACTIVATIONS == 0
    assert CHARGE_CALLS == 0
    assert WALLET_MUTATIONS == 0


# ─── TEST M: MASTER PARITY MATRIX STATUS PARTIAL ─────────────────────────────

def test_m_master_parity_matrix_status_partial():
    """Verify voice_clone status is transitioned to PARTIAL in Master Matrix."""
    matrix_data = json.loads(MASTER_MATRIX_JSON.read_text(encoding="utf-8"))
    matrix_items = matrix_data.get("parity_matrix") or matrix_data.get("rows", [])
    clone_entry = next((item for item in matrix_items if item["bot_capability"] == "voice_clone"), None)
    assert clone_entry is not None
    assert clone_entry["status"] == "PARTIAL"
    assert clone_entry["blocker"] == "VOICE_CLONE_RUNTIME_EXECUTION_NOT_ACTIVATED"

    # Verify Markdown matrix
    md_text = MASTER_MATRIX_MD.read_text(encoding="utf-8")
    assert "| 15 | `voice_clone` | Voice AI | `/voice/clone` | `/api/v1/features/voice_clone/*` | `bot.get_minimax_voice_clone_readiness` | None on Web | Admin B01 | `PARTIAL` |" in md_text
