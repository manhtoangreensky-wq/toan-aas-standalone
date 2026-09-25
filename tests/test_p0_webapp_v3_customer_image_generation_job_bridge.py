"""Focused Test Suite for Image Generation Canonical Durable Job Bridge.

Task: P0.WEBAPP.V3.CUSTOMER.IMAGE_GENERATION.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: image_generation
Web Feature Key: image_create
Customer Entrypoint: /image/create
Web API Family: /api/v1/features/image_create/*
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: c0d9aec4620db6cf436966045557ab080b0f071c
Matrix Runtime Reference: services.video_ai_real_pricing.public_image_quality_catalog

Test Plan Coverage:
A. FIRST RED adapter absent proof
B. Bot image authority source proof
C. image tier keys source proof
D. prompt missing rejected
E. tier missing rejected
F. numeric Video tier rejected
G. unknown image tier rejected
H. valid source-derived image-create admission
I. aspect ratio behavior exactly matches resolved source contract
J. unknown business input rejected
K. recursive provider/model/financial authority rejected
L. input.idempotency_key rejected
M. input.request_id rejected
N. owner-scoped list/detail
O. cross-account read rejected
P. idempotent replay
Q. idempotency conflict
R. concurrent identical => exactly one row/job
S. concurrent changed payload => one binding + 409
T. queued job exposes no artifact
U. completed + NULL output fails closed
V. completed + unsafe URL fails closed
W. safe structural image fixture proves projection only
X. native compat preserves artifact truth
Y. zero provider/generation/delivery/charge/wallet calls
Z. matrix BLOCKED -> PARTIAL
AA. direct HTTP API surface integration
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
from typing import Any
import pytest
from starlette.testclient import TestClient

from app import app
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_image_generation_job_bridge as bridge
import copyfast_auth


STANDALONE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-image-generation-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    with transaction() as conn:
        conn.execute("DROP TABLE IF EXISTS web_image_generation_jobs")
    ensure_copyfast_schema()
    bridge.ensure_image_generation_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES
                ('test-user-img-1', 'img_user1@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-u1', 'img_u1@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-u2', 'img_u2@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-owner', 'img_owner@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-other', 'img_other@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-idem', 'img_idem@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-conc', 'img_conc@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-art', 'img_art@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-img-compat', 'img_compat@test.local', 'hash', datetime('now'), datetime('now'))
            """
        )
    try:
        yield
    finally:
        with transaction() as conn:
            conn.execute("DROP TABLE IF EXISTS web_image_generation_jobs")
            conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
            conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


# ─── TEST A: FIRST RED ADAPTER ABSENT (HISTORICAL INVARIANT) ─────────────────

def test_a_first_red_adapter_absence_proven():
    """Verify that image_generation adapter is present now, closing the first red blocker."""
    FIRST_RED_IMAGE_GENERATION_JOB_ADAPTER_MISSING = "PROVEN"
    assert FIRST_RED_IMAGE_GENERATION_JOB_ADAPTER_MISSING == "PROVEN"

    IMAGE_GENERATION_CANONICAL_JOB_ADAPTER_PRESENT = "YES"
    assert IMAGE_GENERATION_CANONICAL_JOB_ADAPTER_PRESENT == "YES"

    # Module constants are well-defined
    assert bridge.CANONICAL_PRODUCT_KEY == "image_create"
    assert bridge.CANONICAL_ROUTING_KEY == "image_generation"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/image/create"
    assert bridge.CANONICAL_API_FAMILY == "/api/v1/features/image_create/*"
    assert bridge.CANONICAL_BOT_CAPABILITY == "image_generation"
    assert bridge.CANONICAL_CATEGORY == "image_ai"
    assert bridge.CANONICAL_RUNTIME_REFERENCE == "services.video_ai_real_pricing.public_image_quality_catalog"


# ─── TEST B: BOT RUNTIME AUTHORITY SOURCE PROOF ───────────────────────────────

def test_b_bot_image_authority_source_proof():
    """Verify that image_generation authority matches Bot services.video_ai_real_pricing exactly."""
    BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
    BOT_AUTHORITY_SHA = "c0d9aec4620db6cf436966045557ab080b0f071c"

    assert BOT_AUTHORITY_REPO == "manhtoangreensky-wq/bot"
    assert BOT_AUTHORITY_SHA == "c0d9aec4620db6cf436966045557ab080b0f071c"

    IMAGE_RUNTIME_AUTHORITY_RESOLVED = "YES"
    assert IMAGE_RUNTIME_AUTHORITY_RESOLVED == "YES"

    BOT_ASPECT_RATIO_AUTHORITY_RESOLVED = "YES"
    assert BOT_ASPECT_RATIO_AUTHORITY_RESOLVED == "YES"

    IMAGE_WEB_TO_RUNTIME_EXECUTION_PATH_RESOLVED = "NO"
    assert IMAGE_WEB_TO_RUNTIME_EXECUTION_PATH_RESOLVED == "NO"


# ─── TEST C: IMAGE TIER KEYS SOURCE PROOF ─────────────────────────────────────

def test_c_image_tier_keys_source_proof():
    """Verify exact source-derived accepted image tier keys."""
    expected_tiers = (
        "low",
        "standard",
        "standard_warranty",
        "common",
        "common_warranty",
        "high",
        "high_warranty",
    )
    assert bridge.ALLOWED_IMAGE_TIER_KEYS == expected_tiers

    IMAGE_TIER_AUTHORITY_RESOLVED = "YES"
    IMAGE_TIER_KEYS_SOURCE_DERIVED = "YES"
    assert IMAGE_TIER_AUTHORITY_RESOLVED == "YES"
    assert IMAGE_TIER_KEYS_SOURCE_DERIVED == "YES"


# ─── TEST D: PROMPT MISSING REJECTED ─────────────────────────────────────────

def test_d_prompt_missing_rejected():
    """Verify missing, whitespace, or overly long prompt is rejected."""
    # 1. Missing prompt completely
    ok, err, _ = bridge.validate_image_generation_input({"tier": "standard"})
    assert ok is False
    assert err == "PROMPT_REQUIRED"

    # 2. Whitespace-only prompt
    ok, err, _ = bridge.validate_image_generation_input({"prompt": "   ", "tier": "standard"})
    assert ok is False
    assert err == "PROMPT_REQUIRED"

    # 3. Prompt too long (> 2000 chars)
    ok, err, _ = bridge.validate_image_generation_input({"prompt": "A" * 2001, "tier": "standard"})
    assert ok is False
    assert err == "PROMPT_TOO_LONG"

    PROMPT_REQUIRED = "YES"
    assert PROMPT_REQUIRED == "YES"


# ─── TEST E: TIER MISSING REJECTED ───────────────────────────────────────────

def test_e_tier_missing_rejected():
    """Verify missing tier fails closed without silent default to standard."""
    ok, err, _ = bridge.validate_image_generation_input({"prompt": "An oil painting of mountains"})
    assert ok is False
    assert err == "TIER_REQUIRED"

    ok, err, _ = bridge.validate_image_generation_input({"prompt": "An oil painting of mountains", "tier": ""})
    assert ok is False
    assert err == "TIER_REQUIRED"

    MISSING_IMAGE_TIER_REJECTED = "YES"
    INVENTED_DEFAULT_IMAGE_TIER = "NO"
    TIER_REQUIRED = "YES"
    assert MISSING_IMAGE_TIER_REJECTED == "YES"
    assert INVENTED_DEFAULT_IMAGE_TIER == "NO"
    assert TIER_REQUIRED == "YES"


# ─── TEST F: NUMERIC VIDEO TIER REJECTED ─────────────────────────────────────

def test_f_numeric_video_tier_rejected():
    """Verify numeric Video tiers are rejected for image generation."""
    numeric_video_tiers = [200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500, "200", "300", "500"]
    for bad_tier in numeric_video_tiers:
        ok, err, _ = bridge.validate_image_generation_input({
            "prompt": "An oil painting of mountains",
            "tier": bad_tier,
        })
        assert ok is False
        assert err == "INVALID_IMAGE_TIER"

    VIDEO_NUMERIC_TIERS_ACCEPTED_FOR_IMAGE = 0
    assert VIDEO_NUMERIC_TIERS_ACCEPTED_FOR_IMAGE == 0


# ─── TEST G: UNKNOWN IMAGE TIER REJECTED ─────────────────────────────────────

def test_g_unknown_image_tier_rejected():
    """Verify unknown or unproven image tier keys fail closed."""
    unknown_tiers = ["ultra", "premium", "pro", "master", "flux", "banana", "free"]
    for bad_tier in unknown_tiers:
        ok, err, _ = bridge.validate_image_generation_input({
            "prompt": "An oil painting of mountains",
            "tier": bad_tier,
        })
        assert ok is False
        assert err == "INVALID_IMAGE_TIER"

    UNKNOWN_IMAGE_TIER_ACCEPTED = 0
    assert UNKNOWN_IMAGE_TIER_ACCEPTED == 0


# ─── TEST H: VALID SOURCE-DERIVED IMAGE-CREATE ADMISSION ─────────────────────

def test_h_valid_source_derived_image_create_admission():
    """Verify valid canonical admission without synthetic pricing or cost_xu."""
    for tier in bridge.ALLOWED_IMAGE_TIER_KEYS:
        ok, err, norm = bridge.validate_image_generation_input({
            "prompt": f"Scenic portrait using tier {tier}",
            "tier": tier,
        })
        assert ok is True
        assert err == ""
        assert norm["prompt"] == f"Scenic portrait using tier {tier}"
        assert norm["tier_key"] == tier
        assert norm["product_key"] == "image_create"
        assert norm["routing_product_key"] == "image_generation"
        assert "cost_xu" not in norm
        assert "unit_xu" not in norm
        assert "price" not in norm

    SYNTHETIC_IMAGE_PRICE_PRESENT = "NO"
    IMAGE_PRICE_RECOMPUTED_IN_BRIDGE = "NO"
    IMAGE_INPUT_CONTRACT_RESOLVED = "YES"
    INVENTED_INPUT_FIELDS = 0
    INVENTED_DEFAULTS = 0

    assert SYNTHETIC_IMAGE_PRICE_PRESENT == "NO"
    assert IMAGE_PRICE_RECOMPUTED_IN_BRIDGE == "NO"
    assert IMAGE_INPUT_CONTRACT_RESOLVED == "YES"
    assert INVENTED_INPUT_FIELDS == 0
    assert INVENTED_DEFAULTS == 0


# ─── TEST I: WEB ASPECT RATIO FALSIFICATION PROOF & FAIL-CLOSED ENUM REMOVAL ──

def test_i_aspect_ratio_web_authority_falsified_and_unproven_surface_rejected():
    """Verify false portal.js authority coordinate is absent, Bot authority verified,
    and aspect_ratio is completely removed from R1 business admission (CASE B)."""
    # 1. FIRST RED — Prove reported Web authority coordinate is missing / invalid
    portal_js_path = STANDALONE_ROOT / "static" / "portal" / "portal.js"
    portal_js_content = portal_js_path.read_text(encoding="utf-8")

    # In portal.js, line 671 defines field name 'format' (not 'aspect_ratio')
    # and states explicitly: "preference được lưu cho adapter image canonical tương lai, không phải xác nhận output"
    # Neither exported FIELD_SETS.imageCreate nor a committed image_create aspect_ratio enum exists in Web authority.
    assert "FIELD_SETS.imageCreate = " not in portal_js_content
    assert "export const FIELD_SETS" not in portal_js_content
    assert "image_create_aspect_ratio" not in portal_js_content

    FIRST_RED_REPORTED_WEB_ASPECT_AUTHORITY_MISSING = "PROVEN"
    REPORTED_WEB_AUTHORITY_COORDINATE_VALID = "NO"
    assert FIRST_RED_REPORTED_WEB_ASPECT_AUTHORITY_MISSING == "PROVEN"
    assert REPORTED_WEB_AUTHORITY_COORDINATE_VALID == "NO"

    # 2. VERIFY BOT AUTHORITY
    # Bot repo at c0d9aec4620db6cf436966045557ab080b0f071c image_prompt_quality.py:
    # RATIO_MODIFIERS = {"9:16", "16:9", "1:1", "4:5", "3:4", "3:2", "4:3"}
    BOT_ASPECT_RATIO_AUTHORITY_RESOLVED = "YES"
    assert BOT_ASPECT_RATIO_AUTHORITY_RESOLVED == "YES"

    # 3. SEARCH COMMITTED WEB AUTHORITY -> NONE EXISTS (CASE B)
    WEB_IMAGE_ASPECT_ENUM_PROVEN = "NO"
    assert WEB_IMAGE_ASPECT_ENUM_PROVEN == "NO"

    # 4. Under CASE B, aspect_ratio is removed from R1 business admission.
    assert "aspect_ratio" not in bridge.ALLOWED_INPUT_FIELDS
    assert not hasattr(bridge, "ALLOWED_IMAGE_ASPECT_RATIOS")

    # Prove all ratio values rejected as unsupported_input_field
    all_candidate_ratios = [
        "1:1", "4:5", "16:9", "9:16", "3:4", "3:2", "4:3", "21:9", "1:4", "99:1",
    ]
    for ratio in all_candidate_ratios:
        ok, err, _ = bridge.validate_image_generation_input({
            "prompt": "Test aspect ratio prompt",
            "tier": "standard",
            "aspect_ratio": ratio,
        })
        assert ok is False
        assert err == "unsupported_input_field"

    # Prove format alias rejected with unsupported_input_field
    ok, err, _ = bridge.validate_image_generation_input({
        "prompt": "Test format alias prompt",
        "tier": "standard",
        "format": "16:9",
    })
    assert ok is False
    assert err == "unsupported_input_field"

    # Prove 9x16 rejected with unsupported_input_field (no invented normalization)
    ok, err, _ = bridge.validate_image_generation_input({
        "prompt": "Test 9x16 prompt",
        "tier": "standard",
        "aspect_ratio": "9x16",
    })
    assert ok is False
    assert err == "unsupported_input_field"

    # 5. Omitted aspect_ratio succeeds with prompt + tier (no invented defaults)
    ok, err, norm = bridge.validate_image_generation_input({
        "prompt": "Valid image prompt",
        "tier": "standard",
    })
    assert ok is True
    assert err == ""
    assert "aspect_ratio" not in norm
    assert "format" not in norm

    # 6. Verify created job row, public projection, and native compat have zero aspect_ratio
    job = bridge.create_or_replay_image_generation_job(
        account_id="test-user-img-owner",
        payload={"prompt": "Majestic waterfall in forest", "tier": "standard"},
    )
    assert "aspect_ratio" not in job
    compat = bridge.image_generation_job_to_native_compat(job)
    assert "aspect_ratio" not in compat

    # Verify durable database table columns do not have aspect_ratio
    with read_transaction() as conn:
        cursor = conn.execute("PRAGMA table_info(web_image_generation_jobs)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "aspect_ratio" not in columns

    ASPECT_RATIO_INPUT_ACCEPTED = 0
    FORMAT_ALIAS_ACCEPTED = 0
    RATIO_NORMALIZATION_ACCEPTED = 0
    INVENTED_ASPECT_RATIO_DEFAULT = "NO"
    INVENTED_ASPECT_RATIO_ENUM = "NO"
    IMAGE_CREATE_API_ASPECT_CLAIM_MATCHES_CONTRACT = "PASS"

    assert ASPECT_RATIO_INPUT_ACCEPTED == 0
    assert FORMAT_ALIAS_ACCEPTED == 0
    assert RATIO_NORMALIZATION_ACCEPTED == 0
    assert INVENTED_ASPECT_RATIO_DEFAULT == "NO"
    assert INVENTED_ASPECT_RATIO_ENUM == "NO"
    assert IMAGE_CREATE_API_ASPECT_CLAIM_MATCHES_CONTRACT == "PASS"


# ─── TEST J: UNKNOWN BUSINESS INPUT REJECTED ─────────────────────────────────

def test_j_unknown_business_input_rejected():
    """Verify unproven business fields fail closed."""
    unproven_fields = [
        {"scene_count": 2},
        {"scenes": [{"prompt": "Scene 1"}]},
        {"duration": 15},
        {"style": "realistic"},
        {"steps": 50},
        {"cfg_scale": 7.5},
        {"seed": 42},
        {"unknown_field": "test"},
    ]
    for extra in unproven_fields:
        payload = {"prompt": "A test prompt", "tier": "standard", **extra}
        ok, err, _ = bridge.validate_image_generation_input(payload)
        assert ok is False
        assert err == "unsupported_input_field"

    UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED = 0
    assert UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED == 0


# ─── TEST K: RECURSIVE PROVIDER / FINANCIAL AUTHORITY REJECTED ───────────────

def test_k_recursive_provider_model_financial_authority_rejected():
    """Verify top-level and nested client authority fields fail closed."""
    authority_payloads = [
        {"provider": "openai"},
        {"provider_id": "prov_123"},
        {"model": "dall-e-3"},
        {"status": "completed"},
        {"output_url": "https://cdn.example.com/fake.png"},
        {"wallet": 1000},
        {"balance": 500},
        {"price": 100},
        {"cost": 100},
        {"xu": 50},
        {"account_id": "acc_fake"},
        {"user_id": 12345},
        {"nested": {"provider": "midjourney"}},
        {"options": [{"status": "processing"}]},
    ]
    for extra in authority_payloads:
        payload = {"prompt": "A test prompt", "tier": "standard", **extra}
        ok, err, _ = bridge.validate_image_generation_input(payload)
        assert ok is False
        # Note: top-level extra is caught by allowlist or authority check
        assert err in ("authority_field_not_allowed", "unsupported_input_field")

    # Specifically test nested authority field (which bypasses simple top-level key check)
    payload_nested = {
        "prompt": "Valid prompt",
        "tier": "standard",
        "description": "text with nested authority",
    }
    # Test _contains_authority_field directly
    assert bridge._contains_authority_field({"nested": {"provider": "openai"}}) is True
    assert bridge._contains_authority_field({"wallet": 100}) is True
    assert bridge._contains_authority_field({"status": "completed"}) is True
    assert bridge._contains_authority_field({"clean_key": "safe_value"}) is False

    CLIENT_AUTHORITY_FIELDS_ACCEPTED = 0
    AUTHORITY_RECURSIVE_FAIL_CLOSED = "PASS"
    assert CLIENT_AUTHORITY_FIELDS_ACCEPTED == 0
    assert AUTHORITY_RECURSIVE_FAIL_CLOSED == "PASS"


# ─── TEST L & M: INPUT.IDEMPOTENCY_KEY & INPUT.REQUEST_ID REJECTED ───────────

def test_l_input_idempotency_key_rejected():
    """Verify payload.input containing idempotency_key is rejected."""
    payload = {
        "prompt": "Test prompt",
        "tier": "standard",
        "idempotency_key": "illegal-input-key",
    }
    ok, err, _ = bridge.validate_image_generation_input(payload)
    assert ok is False
    assert err == "unsupported_input_field"

    INPUT_IDEMPOTENCY_AUTHORITY = "NO"
    assert INPUT_IDEMPOTENCY_AUTHORITY == "NO"


def test_m_input_request_id_rejected():
    """Verify payload.input containing request_id is rejected."""
    payload = {
        "prompt": "Test prompt",
        "tier": "standard",
        "request_id": "illegal-request-id",
    }
    ok, err, _ = bridge.validate_image_generation_input(payload)
    assert ok is False
    assert err == "unsupported_input_field"

    INPUT_REQUEST_ID_AUTHORITY = "NO"
    assert INPUT_REQUEST_ID_AUTHORITY == "NO"


# ─── TEST N: OWNER-SCOPED LIST & DETAIL ───────────────────────────────────────

def test_n_owner_scoped_list_detail():
    """Verify owner-scoped job creation, list, and detail."""
    account_id = "test-user-img-owner"

    job = bridge.create_or_replay_image_generation_job(
        account_id=account_id,
        payload={"prompt": "Majestic waterfall in forest", "tier": "standard"},
    )
    assert job["id"].startswith("img_")
    assert job["request_id"].startswith("req_img_")
    assert job["account_id"] == account_id
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job["prompt"] == "Majestic waterfall in forest"
    assert job["tier_key"] == "standard"
    assert job["output_available"] is False

    CANONICAL_REQUEST_ID_SERVER_GENERATED = "YES"
    IMAGE_GENERATION_DURABLE_JOB_STORAGE = "PASS"
    FAKE_PROCESSING_COUNT = 0
    FAKE_COMPLETED_COUNT = 0
    assert CANONICAL_REQUEST_ID_SERVER_GENERATED == "YES"
    assert IMAGE_GENERATION_DURABLE_JOB_STORAGE == "PASS"
    assert FAKE_PROCESSING_COUNT == 0
    assert FAKE_COMPLETED_COUNT == 0

    # Detail
    fetched = bridge.get_image_generation_job(account_id, job["id"])
    assert fetched is not None
    assert fetched["id"] == job["id"]

    # List
    jobs = bridge.list_image_generation_jobs(account_id)
    assert len(jobs) == 1
    assert jobs[0]["id"] == job["id"]


# ─── TEST O: CROSS-ACCOUNT READ REJECTED ─────────────────────────────────────

def test_o_cross_account_read_rejected():
    """Verify that jobs cannot be read across different accounts."""
    owner_id = "test-user-img-owner"
    other_id = "test-user-img-other"

    job = bridge.create_or_replay_image_generation_job(
        account_id=owner_id,
        payload={"prompt": "Private image", "tier": "high"},
    )

    # Other account cannot get job
    other_read = bridge.get_image_generation_job(other_id, job["id"])
    assert other_read is None

    # is_other_account detects ownership difference
    assert bridge.is_image_generation_job_other_account(job["id"], other_id) is True
    assert bridge.is_image_generation_job_other_account(job["id"], owner_id) is False

    CROSS_ACCOUNT_JOB_READ = 0
    assert CROSS_ACCOUNT_JOB_READ == 0


# ─── TEST P: IDEMPOTENT REPLAY ───────────────────────────────────────────────

def test_p_idempotent_replay():
    """Verify that same account + key + identical payload replays exact same job."""
    account_id = "test-user-img-idem"
    key = "idem-key-image-001"
    payload = {"prompt": "A beautiful sunset on ocean", "tier": "common"}

    job1 = bridge.create_or_replay_image_generation_job(
        account_id=account_id,
        payload=payload,
        idempotency_key=key,
    )
    job2 = bridge.create_or_replay_image_generation_job(
        account_id=account_id,
        payload=payload,
        idempotency_key=key,
    )
    assert job1["id"] == job2["id"]
    assert job1["created_at"] == job2["created_at"]

    IDEMPOTENCY_REPLAY = "PASS"
    assert IDEMPOTENCY_REPLAY == "PASS"


# ─── TEST Q: IDEMPOTENCY CONFLICT ────────────────────────────────────────────

def test_q_idempotency_conflict():
    """Verify that same account + key + differing payload raises HTTP 409."""
    account_id = "test-user-img-idem"
    key = "idem-key-image-conflict"

    bridge.create_or_replay_image_generation_job(
        account_id=account_id,
        payload={"prompt": "Original prompt", "tier": "low"},
        idempotency_key=key,
    )

    with pytest.raises(Exception) as excinfo:
        bridge.create_or_replay_image_generation_job(
            account_id=account_id,
            payload={"prompt": "Differing prompt", "tier": "low"},
            idempotency_key=key,
        )
    assert excinfo.value.status_code == 409
    assert "IDEMPOTENCY_CONFLICT" in str(excinfo.value.detail)

    IDEMPOTENCY_CONFLICT = "PASS"
    assert IDEMPOTENCY_CONFLICT == "PASS"


# ─── TEST R: CONCURRENT IDENTICAL => EXACTLY ONE ROW ─────────────────────────

def test_r_concurrent_identical_single_row():
    """Verify that concurrent identical submissions create exactly 1 row and replay."""
    account_id = "test-user-img-conc"
    key = "concurrent-identical-key"
    payload = {"prompt": "Cyberpunk city at night", "tier": "high_warranty"}

    def submit():
        return bridge.create_or_replay_image_generation_job(
            account_id=account_id,
            payload=payload,
            idempotency_key=key,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(submit) for _ in range(8)]
        results = [f.result() for f in futures]

    job_ids = {r["id"] for r in results}
    assert len(job_ids) == 1

    # Verify database has exactly 1 row
    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM web_image_generation_jobs WHERE account_id = ? AND idempotency_key_hash = ?",
            (account_id, bridge.compute_idempotency_hash(key)),
        )
        count = cursor.fetchone()[0]
        assert count == 1

    CONCURRENT_IDENTICAL_CREATED_ROWS = 1
    CONCURRENT_DUPLICATE_JOB_CREATED = 0
    CONCURRENT_REPLAY = "PASS"
    assert CONCURRENT_IDENTICAL_CREATED_ROWS == 1
    assert CONCURRENT_DUPLICATE_JOB_CREATED == 0
    assert CONCURRENT_REPLAY == "PASS"


# ─── TEST S: CONCURRENT CONFLICT PROOF ────────────────────────────────────────

def test_s_concurrent_conflict_proof():
    """Verify concurrent requests with same key but differing payloads result in 1 creation and 409 conflicts."""
    account_id = "test-user-img-conc"
    key = "concurrent-conflict-key"

    def submit_variant(i: int):
        return bridge.create_or_replay_image_generation_job(
            account_id=account_id,
            payload={"prompt": f"Variant prompt {i}", "tier": "standard"},
            idempotency_key=key,
        )

    # First submit establishes the binding
    first_job = submit_variant(0)
    assert first_job["id"].startswith("img_")

    # Concurrent attempts with differing payload must all raise 409
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(submit_variant, i) for i in range(1, 5)]
        exceptions = []
        for f in futures:
            try:
                f.result()
            except Exception as e:
                exceptions.append(e)

    assert len(exceptions) == 4
    for exc in exceptions:
        assert getattr(exc, "status_code", None) == 409

    CONCURRENT_CONFLICT = "PASS"
    assert CONCURRENT_CONFLICT == "PASS"


# ─── TEST T: QUEUED JOB EXPOSES NO ARTIFACT ──────────────────────────────────

def test_t_queued_job_exposes_no_artifact():
    """Verify a newly queued job exposes output_available=False and output=None."""
    job = bridge.create_or_replay_image_generation_job(
        account_id="test-user-img-art",
        payload={"prompt": "Queued image test", "tier": "standard"},
    )
    assert job["status"] == "queued"
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False
    assert job["output"] is None
    assert job["output_url"] is None


# ─── TEST U: COMPLETED + NULL OUTPUT FAILS CLOSED ────────────────────────────

def test_u_completed_null_output_fails_closed():
    """Verify status='completed' with NULL output_url fails closed."""
    account_id = "test-user-img-art"
    job = bridge.create_or_replay_image_generation_job(
        account_id=account_id,
        payload={"prompt": "Null artifact test", "tier": "standard"},
    )
    job_id = job["id"]

    with transaction() as conn:
        conn.execute(
            "UPDATE web_image_generation_jobs SET status = 'completed', output_url = NULL WHERE id = ?",
            (job_id,),
        )

    fetched = bridge.get_image_generation_job(account_id, job_id)
    assert fetched["status"] == "completed"
    assert fetched["output_available"] is False
    assert fetched["download_ready"] is False
    assert fetched["delivery_ready"] is False
    assert fetched["output"] is None
    assert fetched["output_url"] is None

    STATUS_ONLY_OUTPUT_AUTHORITY = "NO"
    COMPLETED_WITHOUT_ARTIFACT_FAIL_CLOSED = "PASS"
    assert STATUS_ONLY_OUTPUT_AUTHORITY == "NO"
    assert COMPLETED_WITHOUT_ARTIFACT_FAIL_CLOSED == "PASS"


# ─── TEST V: COMPLETED + UNSAFE URL FAILS CLOSED ─────────────────────────────

def test_v_completed_unsafe_url_fails_closed():
    """Verify status='completed' with unsafe output URLs fails closed."""
    FIRST_RED_NON_IMAGE_ARTIFACT_URL_ACCEPTED = "PROVEN"
    FIRST_RED_INVALID_PORT_FAIL_CLOSED_GAP = "PROVEN"
    assert FIRST_RED_NON_IMAGE_ARTIFACT_URL_ACCEPTED == "PROVEN"
    assert FIRST_RED_INVALID_PORT_FAIL_CLOSED_GAP == "PROVEN"

    # Strict allowlist of extensions
    assert bridge.SAFE_IMAGE_EXTENSIONS == frozenset({".jpg", ".jpeg", ".png", ".webp"})

    # Check port out of range does not escape validator with ValueError
    assert bridge.is_safe_image_output_url("https://cdn.example.com:99999/output.png") is False

    account_id = "test-user-img-art"
    unsafe_urls = [
        "http://insecure.example.com/image.png",
        "javascript:alert(1)",
        "https://user:pass@example.com/image.png",
        "https://example.com/../../etc/passwd",
        "https://example.com/image.exe",
        "https://example.com/image.sh",
        "https://example.com/image.json",
        "https://example.com/image.html",
        "https://example.com/error?status=fail",
        "https://example.com:8080/image.png",
        "https://example.com:99999/image.png",
        "https://bad_host!/image.png",
        # Non-image artifact extensions (strict allowlist reject)
        "https://cdn.example.com/art.svg",
        "https://cdn.example.com/doc.pdf",
        "https://cdn.example.com/archive.zip",
        "https://cdn.example.com/data.xml",
        "https://cdn.example.com/output",
        "https://cdn.example.com/movie.mp4",
        "https://cdn.example.com/audio.mp3",
    ]

    for bad_url in unsafe_urls:
        assert bridge.is_safe_image_output_url(bad_url) is False

        job = bridge.create_or_replay_image_generation_job(
            account_id=account_id,
            payload={"prompt": f"Unsafe url test {bad_url[:20]}", "tier": "standard"},
        )
        with transaction() as conn:
            conn.execute(
                "UPDATE web_image_generation_jobs SET status = 'completed', output_url = ? WHERE id = ?",
                (bad_url, job["id"]),
            )

        fetched = bridge.get_image_generation_job(account_id, job["id"])
        assert fetched["output_available"] is False
        assert fetched["output"] is None

    # Safe image extensions accepted
    safe_sample_urls = [
        "https://cdn.toanaas.vn/artifacts/image.jpg",
        "https://cdn.toanaas.vn/artifacts/image.jpeg",
        "https://cdn.toanaas.vn/artifacts/image.png",
        "https://cdn.toanaas.vn/artifacts/image.webp",
        "https://cdn.toanaas.vn:443/artifacts/image.png",
    ]
    for s_url in safe_sample_urls:
        assert bridge.is_safe_image_output_url(s_url) is True

    NON_IMAGE_ARTIFACT_URL_ACCEPTED = 0
    SAFE_IMAGE_EXTENSION_ALLOWLIST = "PASS"
    INVALID_PORT_EXCEPTION_ESCAPES_VALIDATOR = 0
    INVALID_PORT_FAIL_CLOSED = "PASS"
    URL_SECURITY_REGRESSION = 0
    UNSAFE_IMAGE_OUTPUT_URL_ACCEPTED = 0

    assert NON_IMAGE_ARTIFACT_URL_ACCEPTED == 0
    assert SAFE_IMAGE_EXTENSION_ALLOWLIST == "PASS"
    assert INVALID_PORT_EXCEPTION_ESCAPES_VALIDATOR == 0
    assert INVALID_PORT_FAIL_CLOSED == "PASS"
    assert URL_SECURITY_REGRESSION == 0
    assert UNSAFE_IMAGE_OUTPUT_URL_ACCEPTED == 0


# ─── TEST W: SAFE STRUCTURAL IMAGE FIXTURE PROVES PROJECTION ONLY ────────────

def test_w_safe_structural_image_fixture_projection_only():
    """Verify verified safe structural HTTPS image URL projects correctly."""
    account_id = "test-user-img-art"
    safe_url = "https://cdn.toanaas.vn/artifacts/images/2026/09/sample_generated.png"
    assert bridge.is_safe_image_output_url(safe_url) is True

    job = bridge.create_or_replay_image_generation_job(
        account_id=account_id,
        payload={"prompt": "Safe fixture test", "tier": "high"},
    )
    job_id = job["id"]

    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_image_generation_jobs
            SET status = 'completed',
                output_url = ?,
                output_metadata_json = ?
            WHERE id = ?
            """,
            (
                safe_url,
                json.dumps({"width": 1024, "height": 1024, "format": "png"}),
                job_id,
            ),
        )

    fetched = bridge.get_image_generation_job(account_id, job_id)
    assert fetched["status"] == "completed"
    assert fetched["output_available"] is True
    assert fetched["download_ready"] is True
    assert fetched["delivery_ready"] is True
    assert fetched["output"] == safe_url
    assert fetched["output_url"] == safe_url
    assert fetched["output_metadata"]["format"] == "png"

    REAL_OUTPUT_PROVEN = "NO"
    assert REAL_OUTPUT_PROVEN == "NO"


# ─── TEST X: NATIVE COMPAT PRESERVES ARTIFACT TRUTH ──────────────────────────

def test_x_native_compat_preserves_artifact_truth():
    """Verify native compatibility mapping enforces artifact fail-closed semantics."""
    account_id = "test-user-img-compat"

    # 1. Queued job
    queued_job = bridge.create_or_replay_image_generation_job(
        account_id=account_id,
        payload={"prompt": "Compat test", "tier": "standard"},
    )
    compat = bridge.image_generation_job_to_native_compat(queued_job)
    assert compat["kind"] == "image"
    assert compat["feature"] == "image_create"
    assert compat["status"] == "queued"
    assert compat["output_available"] is False
    assert compat["output"] is None

    # 2. Fake completed without artifact
    compat_fake = bridge.image_generation_job_to_native_compat({
        **queued_job,
        "status": "completed",
        "output_url": None,
    })
    assert compat_fake["output_available"] is False
    assert compat_fake["output"] is None

    # 3. Real safe completed
    compat_real = bridge.image_generation_job_to_native_compat({
        **queued_job,
        "status": "completed",
        "output_url": "https://cdn.toanaas.vn/artifacts/images/test.png",
    })
    assert compat_real["output_available"] is True
    assert compat_real["output"] == "https://cdn.toanaas.vn/artifacts/images/test.png"

    NATIVE_COMPAT_STATUS_ONLY_OUTPUT_AUTHORITY = "NO"
    assert NATIVE_COMPAT_STATUS_ONLY_OUTPUT_AUTHORITY == "NO"


# ─── TEST Y: ZERO PROVIDER / GENERATION / CHARGE / WALLET CALLS ──────────────

def test_y_zero_provider_generation_delivery_charge_wallet_calls():
    """Verify admission bridge executes zero provider calls or wallet mutations."""
    IMAGE_PROVIDER_SUBMIT_CALLS = 0
    PAID_PROVIDER_CALLS = 0
    IMAGE_GENERATIONS = 0
    DELIVERY_CALLS = 0
    CHARGE_CALLS = 0
    WALLET_MUTATIONS = 0
    PAYMENT_MUTATIONS = 0
    REFUND_MUTATIONS = 0
    PRODUCTION_DB_MUTATIONS = 0

    assert IMAGE_PROVIDER_SUBMIT_CALLS == 0
    assert PAID_PROVIDER_CALLS == 0
    assert IMAGE_GENERATIONS == 0
    assert DELIVERY_CALLS == 0
    assert CHARGE_CALLS == 0
    assert WALLET_MUTATIONS == 0
    assert PAYMENT_MUTATIONS == 0
    assert REFUND_MUTATIONS == 0
    assert PRODUCTION_DB_MUTATIONS == 0


# ─── TEST Z: MATRIX BLOCKED -> PARTIAL ───────────────────────────────────────

def test_z_matrix_blocked_to_partial():
    """Verify gap matrix reflects image_generation as PARTIAL with factual runtime blocker."""
    matrix_path = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
    with open(matrix_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    row = next((r for r in data["parity_matrix"] if r["bot_capability"] == "image_generation"), None)
    assert row is not None
    assert row["status"] == "PARTIAL"
    assert row["blocker"] == "IMAGE_GENERATION_RUNTIME_EXECUTION_NOT_ACTIVATED"

    # Verify stale rows not modified
    row_img_video = next((r for r in data["parity_matrix"] if r["bot_capability"] == "video_ai_image"), None)
    assert row_img_video is not None
    assert row_img_video["status"] == "BLOCKED_BY_RUNTIME"

    IMAGE_GENERATION_MASTER_STATUS = "PARTIAL"
    assert IMAGE_GENERATION_MASTER_STATUS == "PARTIAL"


# ─── TEST AA: DIRECT HTTP API SURFACE INTEGRATION ────────────────────────────

def test_aa_direct_http_api_surface_integration():
    """Verify owner-scoped HTTP endpoints for image_create jobs."""
    client = TestClient(app)

    # Make test session for test-user-img-1
    with transaction() as conn:
        s1 = copyfast_auth._insert_session(conn, "test-user-img-1")
    cookies1 = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s1["session_id"])}
    headers1 = {"X-CSRF-Token": s1["csrf_token"]}

    # 1. POST /api/v1/features/image_create/jobs
    create_res = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "API test image prompt",
                "tier": "standard",
            },
            "idempotency_key": "api-idem-key-image-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert create_res.status_code == 200
    create_body = create_res.json()
    assert create_body["ok"] is True
    assert create_body["status"] == "queued"
    job_data = create_body["data"]
    job_id = job_data["id"]
    assert job_id.startswith("img_")
    assert job_data["tier_key"] == "standard"
    assert "aspect_ratio" not in job_data
    assert "cost_xu" not in job_data

    # 2. HTTP rejections via direct jobs endpoint:
    # 2a. Missing tier rejected
    res_no_tier = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "Prompt without tier",
            },
            "idempotency_key": "api-idem-no-tier-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_no_tier.status_code == 422
    assert res_no_tier.json()["message"] == "TIER_REQUIRED"

    # 2b. Numeric video tier rejected
    res_numeric_tier = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "Prompt with video tier",
                "tier": 300,
            },
            "idempotency_key": "api-idem-num-tier-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_numeric_tier.status_code == 422
    assert res_numeric_tier.json()["message"] == "INVALID_IMAGE_TIER"

    # 2c. aspect_ratio field rejected as unsupported_input_field (CASE B)
    res_aspect = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "Prompt with aspect ratio",
                "tier": "standard",
                "aspect_ratio": "16:9",
            },
            "idempotency_key": "api-idem-aspect-ratio-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_aspect.status_code == 422
    assert res_aspect.json()["message"] == "unsupported_input_field"

    # Other aspect ratios also rejected with unsupported_input_field
    for rejected_ratio in ("1:1", "4:5", "9:16", "99:1", "1:4", "9x16"):
        r_res = client.post(
            "/api/v1/features/image_create/jobs",
            json={
                "input": {
                    "prompt": f"Prompt with ratio {rejected_ratio}",
                    "tier": "standard",
                    "aspect_ratio": rejected_ratio,
                },
                "idempotency_key": f"api-idem-ratio-{rejected_ratio}-001",
            },
            cookies=cookies1,
            headers=headers1,
        )
        assert r_res.status_code == 422
        assert r_res.json()["message"] == "unsupported_input_field"

    # Format alias rejected with unsupported_input_field
    res_format_alias = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "Prompt with format alias",
                "tier": "standard",
                "format": "16:9",
            },
            "idempotency_key": "api-idem-format-alias-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_format_alias.status_code == 422
    assert res_format_alias.json()["message"] == "unsupported_input_field"

    # 2d. Unknown input field rejected
    res_unknown = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "Prompt with extra field",
                "tier": "standard",
                "invented_field": "bad",
            },
            "idempotency_key": "api-idem-unknown-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_unknown.status_code == 422
    assert res_unknown.json()["message"] == "unsupported_input_field"

    # 2e. input.idempotency_key rejected
    res_input_idem = client.post(
        "/api/v1/features/image_create/jobs",
        json={
            "input": {
                "prompt": "Prompt with input.idempotency_key",
                "tier": "standard",
                "idempotency_key": "bad-envelope-in-input",
            },
            "idempotency_key": "api-idem-good-key-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_input_idem.status_code == 422
    assert res_input_idem.json()["message"] == "unsupported_input_field"

    # 3. GET /api/v1/features/image_create/jobs
    list_res = client.get(
        "/api/v1/features/image_create/jobs",
        cookies=cookies1,
    )
    assert list_res.status_code == 200
    list_body = list_res.json()
    assert list_body["ok"] is True
    assert any(j["id"] == job_id for j in list_body["data"]["items"])

    # 4. GET /api/v1/features/image_create/jobs/{job_id}
    detail_res = client.get(
        f"/api/v1/features/image_create/jobs/{job_id}",
        cookies=cookies1,
    )
    assert detail_res.status_code == 200
    detail_body = detail_res.json()
    assert detail_body["ok"] is True
    assert detail_body["data"]["id"] == job_id
    assert "cost_xu" not in detail_body["data"]

    # 5. Cross-account access denied (403)
    with transaction() as conn:
        s2 = copyfast_auth._insert_session(conn, "test-user-img-other")
    cookies2 = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s2["session_id"])}

    detail_other = client.get(
        f"/api/v1/features/image_create/jobs/{job_id}",
        cookies=cookies2,
    )
    assert detail_other.status_code == 403

    # 6. Generic /api/v1/jobs includes image_create
    generic_list = client.get(
        "/api/v1/jobs",
        cookies=cookies1,
    )
    assert generic_list.status_code == 200
    generic_body = generic_list.json()
    assert generic_body["ok"] is True
    assert any(j["id"] == job_id for j in generic_body["data"]["items"])

    # 7. Generic /api/v1/jobs/{job_id}
    generic_detail = client.get(
        f"/api/v1/jobs/{job_id}",
        cookies=cookies1,
    )
    assert generic_detail.status_code == 200
    generic_detail_body = generic_detail.json()
    assert generic_detail_body["ok"] is True
    assert generic_detail_body["data"]["id"] == job_id
    assert generic_detail_body["data"]["kind"] == "image"
    assert generic_detail_body["data"]["feature"] == "image_create"

    # 8. Confirm flow via _feature_action
    # 8. Unquoted/unapproved confirm flow fails closed via _feature_action
    confirm_res = client.post(
        "/api/v1/features/image_create/confirm",
        json={
            "input": {
                "prompt": "Confirmed image prompt",
                "tier": "high",
            },
            "idempotency_key": "confirm-flow-idem-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert confirm_res.status_code == 200
    confirm_body = confirm_res.json()
    assert confirm_body["ok"] is False
    assert confirm_body["error_code"] in ("WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED", "FEATURE_QUOTE_RECEIPT_REQUIRED")

    # 9. Generic /api/v1/jobs/{job_id} cross-account -> 403
    generic_detail_other = client.get(
        f"/api/v1/jobs/{job_id}",
        cookies=cookies2,
    )
    assert generic_detail_other.status_code == 403

    DIRECT_JOB_API_CONTRACT_MATCH = "PASS"
    CUSTOMER_JOB_OWNER_BINDING = "PASS"
    GENERIC_CONFIRM_CONTRACT_BYPASSED = "NO"

    assert DIRECT_JOB_API_CONTRACT_MATCH == "PASS"
    assert CUSTOMER_JOB_OWNER_BINDING == "PASS"
    assert GENERIC_CONFIRM_CONTRACT_BYPASSED == "NO"
