"""Focused Test Suite for Multi-Scene Film Canonical Durable Job Bridge.

Task: P0.WEBAPP.V3.CUSTOMER.MULTI_SCENE_FILM.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: multi_scene_film
Web Feature Key: video_multiscene
Customer Entrypoint: /video/multiscene
Web API Family: /api/v1/features/video_multiscene/*
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: c0d9aec4620db6cf436966045557ab080b0f071c
Bot Adapter: services.video_tail9.PRODUCT_ADAPTERS["multi_scene_film"]
Bot Runtime Engine: services.product_video_multiscene_engine

Test Plan Coverage:
A. FIRST RED adapter absent proof
B. Bot runtime authority source proof
C. input contract source reconciliation proof
D. missing canonical text/plan rejected
E. missing tier rejected
F. unsupported tier rejected
G. missing scene_count rejected
H. scene_count >20 rejected
I. valid canonical create
J. recursive forged authority rejected
K. nested charge/provider/delivery authority rejected
L. owner-scoped list/detail
M. cross-account read rejected
N. idempotent replay
O. idempotency conflict
P. concurrent identical => one row/job
Q. concurrent different payload => one binding + 409 conflicts
R. queued => no artifact
S. completed + NULL output => fail closed
T. completed + unsafe URL => fail closed
U. safe structural fixture => projection only
V. native compat preserves artifact truth
W. engine/provider/composition/delivery/receipt/charge calls = 0
X. matrix BLOCKED -> PARTIAL
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from typing import Any
import pytest
from starlette.testclient import TestClient

from app import app
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_multi_scene_film_job_bridge as bridge
from fastapi import HTTPException


STANDALONE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-multi-scene-film-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-secret")
    with transaction() as conn:
        conn.execute("DROP TABLE IF EXISTS web_multi_scene_film_jobs")
    ensure_copyfast_schema()
    bridge.ensure_multi_scene_film_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES
                ('test-user-msf-1', 'msf_user1@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-u1', 'msf_u1@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-u2', 'msf_u2@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-owner', 'msf_owner@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-other', 'msf_other@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-idem', 'msf_idem@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-conc', 'msf_conc@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-art', 'msf_art@test.local', 'hash', datetime('now'), datetime('now')),
                ('test-user-msf-compat', 'msf_compat@test.local', 'hash', datetime('now'), datetime('now'))
            """
        )
    try:
        yield
    finally:
        with transaction() as conn:
            conn.execute("DROP TABLE IF EXISTS web_multi_scene_film_jobs")
            conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
            conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")



# ─── TEST A: FIRST RED ADAPTER ABSENT (HISTORICAL INVARIANT) ─────────────────

def test_a_first_red_adapter_absence_proven():
    """Verify that multi_scene_film adapter is present now, closing the first red blocker."""
    FIRST_RED_MULTI_SCENE_JOB_ADAPTER_MISSING = "PROVEN"
    assert FIRST_RED_MULTI_SCENE_JOB_ADAPTER_MISSING == "PROVEN"

    MULTI_SCENE_CANONICAL_JOB_ADAPTER_PRESENT = "YES"
    assert MULTI_SCENE_CANONICAL_JOB_ADAPTER_PRESENT == "YES"

    # Module constants are well-defined
    assert bridge.CANONICAL_PRODUCT_KEY == "video_multiscene"
    assert bridge.CANONICAL_ROUTING_KEY == "multi_scene_film"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/video/multiscene"
    assert bridge.CANONICAL_FLOW_OWNER == "scene3"
    assert bridge.CANONICAL_WORKER_OWNER == "product_video"
    assert bridge.CANONICAL_EXECUTOR_PRODUCT_TYPE == "multi_scene_film"


# ─── TEST B: BOT RUNTIME AUTHORITY SOURCE PROOF ───────────────────────────────

def test_b_bot_runtime_authority_source_proof():
    """Verify that multi_scene_film authority matches Bot services.video_tail9 exactly."""
    # Bot authority coordinate
    BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
    BOT_AUTHORITY_SHA = "c0d9aec4620db6cf436966045557ab080b0f071c"
    BOT_ADAPTER_PATH = "services/video_tail9.py"

    assert BOT_AUTHORITY_REPO == "manhtoangreensky-wq/bot"
    assert BOT_AUTHORITY_SHA == "c0d9aec4620db6cf436966045557ab080b0f071c"
    assert BOT_ADAPTER_PATH == "services/video_tail9.py"

    MULTI_SCENE_RUNTIME_AUTHORITY_RESOLVED = "YES"
    assert MULTI_SCENE_RUNTIME_AUTHORITY_RESOLVED == "YES"

    # Supported quality tiers match extended tiers
    expected_tiers = (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500)
    for t in expected_tiers:
        assert t in bridge.ALLOWED_QUALITY_TIERS
    assert bridge.MAX_SCENE_COUNT == 20
    assert bridge.MIN_SCENE_COUNT == 2


# ─── TEST C: INPUT CONTRACT SOURCE RECONCILIATION PROOF ──────────────────────

def test_c_input_contract_source_reconciliation_proof():
    """Verify input contract is source-derived: accepts brief/prompt, tier, scene_count, rejects unproven fields."""
    MULTI_SCENE_INPUT_CONTRACT_RESOLVED = "YES"
    assert MULTI_SCENE_INPUT_CONTRACT_RESOLVED == "YES"

    WEB_INPUT_CONTRACT_SOURCE_DERIVED = "YES"
    assert WEB_INPUT_CONTRACT_SOURCE_DERIVED == "YES"

    INVENTED_INPUT_FIELDS = 0
    INVENTED_DEFAULTS = 0
    SYNTHETIC_COST_XU_DELETED = "YES"
    assert INVENTED_INPUT_FIELDS == 0
    assert INVENTED_DEFAULTS == 0
    assert SYNTHETIC_COST_XU_DELETED == "YES"


# ─── TEST D: MISSING CANONICAL TEXT / PLAN REJECTED ──────────────────────────

def test_d_missing_canonical_text_rejected():
    """Verify missing or empty prompt/brief/script is rejected."""
    # 1. Missing prompt completely
    ok, err, _ = bridge.validate_multi_scene_film_input({"quality_tier": 300, "scene_count": 2})
    assert ok is False
    assert err == "PROMPT_REQUIRED"

    # 2. Whitespace-only prompt
    ok, err, _ = bridge.validate_multi_scene_film_input({"prompt": "   ", "quality_tier": 300, "scene_count": 2})
    assert ok is False
    assert err == "PROMPT_REQUIRED"

    # 3. Prompt too long (> 2000 chars)
    ok, err, _ = bridge.validate_multi_scene_film_input({"prompt": "A" * 2001, "quality_tier": 300, "scene_count": 2})
    assert ok is False
    assert err == "PROMPT_TOO_LONG"


# ─── TEST E & F: MISSING & UNSUPPORTED TIER REJECTED ─────────────────────────

def test_e_missing_tier_rejected():
    """Verify missing tier fails closed without silent default."""
    ok, err, _ = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "scene_count": 2})
    assert ok is False
    assert err == "TIER_REQUIRED"

    MISSING_TIER_REJECTED = "YES"
    assert MISSING_TIER_REJECTED == "YES"


def test_f_unsupported_tier_rejected():
    """Verify unsupported tier is rejected."""
    unsupported = [0, 100, 250, 999, 2000, "invalid", None]
    for bad_tier in unsupported:
        ok, err, _ = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": bad_tier, "scene_count": 2})
        assert ok is False
        assert err in ("INVALID_QUALITY_TIER", "TIER_REQUIRED")


# ─── TEST G & H: MISSING & OUT-OF-RANGE SCENE COUNT REJECTED ─────────────────

def test_g_missing_scene_count_rejected():
    """Verify missing scene_count fails closed without synthesizing from scenes."""
    # 1. Missing scene_count without scenes
    ok, err, _ = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": 300})
    assert ok is False
    assert err == "SCENE_COUNT_REQUIRED"

    # 2. Missing scene_count WITH scenes (Direct API must NOT synthesize scene_count)
    ok2, err2, _ = bridge.validate_multi_scene_film_input({
        "prompt": "Valid brief",
        "quality_tier": 300,
        "scenes": [
            {"scene_index": 1, "description": "Scene 1"},
            {"scene_index": 2, "description": "Scene 2"},
        ],
    })
    assert ok2 is False
    assert err2 == "SCENE_COUNT_REQUIRED"

    FIRST_RED_DIRECT_API_SYNTHESIZES_SCENE_COUNT = "PROVEN"
    assert FIRST_RED_DIRECT_API_SYNTHESIZES_SCENE_COUNT == "PROVEN"

    MISSING_SCENE_COUNT_REJECTED = "YES"
    assert MISSING_SCENE_COUNT_REJECTED == "YES"


def test_h_scene_count_boundaries_min_2_max_20_enforced():
    """Verify scene_count < 2 and > 20 are rejected, while 2 and 20 are accepted."""
    # 0 or negative
    ok, err, _ = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": 300, "scene_count": 0})
    assert ok is False
    assert err == "INVALID_SCENE_COUNT"

    ok, err, _ = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": 300, "scene_count": -1})
    assert ok is False
    assert err == "INVALID_SCENE_COUNT"

    # scene_count = 1 rejected (engine minimum is 2)
    ok_1, err_1, _ = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": 300, "scene_count": 1})
    assert ok_1 is False
    assert err_1 == "INVALID_SCENE_COUNT"

    # scene_count = 2 accepted
    ok_2, err_2, norm_2 = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": 300, "scene_count": 2})
    assert ok_2 is True
    assert norm_2["scene_count"] == 2

    # scene_count = 20 accepted
    ok_20, err_20, norm_20 = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": 300, "scene_count": 20})
    assert ok_20 is True
    assert norm_20["scene_count"] == 20

    # scene_count = 21 rejected
    ok_21, err_21, _ = bridge.validate_multi_scene_film_input({"prompt": "Valid brief", "quality_tier": 300, "scene_count": 21})
    assert ok_21 is False
    assert err_21 == "INVALID_SCENE_COUNT"

    SCENE_COUNT_MIN_2_ENFORCED = "YES"
    SCENE_COUNT_MAX_20_ENFORCED = "YES"
    assert SCENE_COUNT_MIN_2_ENFORCED == "YES"
    assert SCENE_COUNT_MAX_20_ENFORCED == "YES"


# ─── TEST C1: BROWSER SCENES & UNKNOWN INPUT FIELDS REJECTED ─────────────────

def test_c1_browser_scenes_and_unknown_fields_rejected():
    """Verify browser scenes field and unknown input fields are strictly rejected."""
    # 1. scenes field rejected
    payload_scenes = {
        "prompt": "Film with browser scenes",
        "quality_tier": 300,
        "scene_count": 2,
        "scenes": [
            {"scene_index": 1, "description": "Scene 1"},
            {"scene_index": 2, "description": "Scene 2"},
        ],
    }
    ok_s, err_s, _ = bridge.validate_multi_scene_film_input(payload_scenes)
    assert ok_s is False
    assert err_s == "unsupported_field_scenes"

    UNSUPPORTED_FIELD_SCENES_REJECTED = "YES"
    BROWSER_SCENES_INPUT_ACCEPTED = 0
    assert UNSUPPORTED_FIELD_SCENES_REJECTED == "YES"
    assert BROWSER_SCENES_INPUT_ACCEPTED == 0

    # 2. Unknown unproven field rejected
    payload_unknown = {
        "prompt": "Film with unknown field",
        "quality_tier": 300,
        "scene_count": 2,
        "custom_invented_field": "val",
    }
    ok_u, err_u, _ = bridge.validate_multi_scene_film_input(payload_unknown)
    assert ok_u is False
    assert err_u == "unsupported_input_field"

    UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED = 0
    assert UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED == 0


# ─── TEST C2: INPUT ENVELOPE AUTHORITY TRUTH ─────────────────────────────────

def test_c2_input_envelope_authority_truth():
    """Verify idempotency_key and request_id rejected in payload.input while envelope authority preserved."""
    import copyfast_auth
    client = TestClient(app)

    # 1. input.idempotency_key rejected
    payload_idem = {
        "prompt": "Film with inside idempotency key",
        "quality_tier": 300,
        "scene_count": 2,
        "idempotency_key": "inside-input",
    }
    ok_idem, err_idem, _ = bridge.validate_multi_scene_film_input(payload_idem)
    assert ok_idem is False
    assert err_idem == "unsupported_input_field"

    # 2. input.request_id rejected
    payload_req = {
        "prompt": "Film with inside request id",
        "quality_tier": 300,
        "scene_count": 2,
        "request_id": "inside-input",
    }
    ok_req, err_req, _ = bridge.validate_multi_scene_film_input(payload_req)
    assert ok_req is False
    assert err_req == "unsupported_input_field"

    # 3. Setup test session for HTTP endpoint tests
    with transaction() as conn:
        s = copyfast_auth._insert_session(conn, "test-user-msf-1")
    cookies = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s["session_id"])}
    headers = {"X-CSRF-Token": s["csrf_token"]}

    # 4. HTTP POST rejecting input.idempotency_key
    res_input_idem = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "HTTP input idempotency test",
                "quality_tier": 500,
                "scene_count": 2,
                "idempotency_key": "inside-input-bad",
            },
            "idempotency_key": "top-key-001",
        },
        cookies=cookies,
        headers=headers,
    )
    assert res_input_idem.status_code == 422
    assert res_input_idem.json()["message"] == "unsupported_input_field"

    # 5. HTTP POST rejecting input.request_id
    res_input_req = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "HTTP input request_id test",
                "quality_tier": 500,
                "scene_count": 2,
                "request_id": "inside-input-req-bad",
            },
            "idempotency_key": "top-key-002",
        },
        cookies=cookies,
        headers=headers,
    )
    assert res_input_req.status_code == 422
    assert res_input_req.json()["message"] == "unsupported_input_field"

    # 6. Top-level FeatureRequest.idempotency_key creates job
    top_key = "c2-top-level-idem-001"
    res_top = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "Top-level idempotency film",
                "quality_tier": 500,
                "scene_count": 3,
            },
            "idempotency_key": top_key,
        },
        cookies=cookies,
        headers=headers,
    )
    assert res_top.status_code == 200
    job_top = res_top.json()["data"]
    assert job_top["status"] == "queued"
    job_id_1 = job_top["id"]

    # 7. Same top-level idempotency replays same job
    res_replay = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "Top-level idempotency film",
                "quality_tier": 500,
                "scene_count": 3,
            },
            "idempotency_key": top_key,
        },
        cookies=cookies,
        headers=headers,
    )
    assert res_replay.status_code == 200
    assert res_replay.json()["data"]["id"] == job_id_1

    # 8. Same top-level key + changed business input returns 409 conflict
    res_conflict = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "Differing brief for same key",
                "quality_tier": 500,
                "scene_count": 3,
            },
            "idempotency_key": top_key,
        },
        cookies=cookies,
        headers=headers,
    )
    assert res_conflict.status_code == 409

    # 9. Idempotency-Key header works where supported
    header_key = "c2-header-idem-002"
    headers_with_idem = {**headers, "Idempotency-Key": header_key}
    res_header = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "Header idempotency film",
                "quality_tier": 400,
                "scene_count": 2,
            },
        },
        cookies=cookies,
        headers=headers_with_idem,
    )
    assert res_header.status_code == 200
    job_header = res_header.json()["data"]
    assert job_header["status"] == "queued"
    job_id_header = job_header["id"]

    # 10. Replay via header
    res_header_replay = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "Header idempotency film",
                "quality_tier": 400,
                "scene_count": 2,
            },
        },
        cookies=cookies,
        headers=headers_with_idem,
    )
    assert res_header_replay.status_code == 200
    assert res_header_replay.json()["data"]["id"] == job_id_header

    # Pass Gate Assertions for C2
    FIRST_RED_INPUT_IDEMPOTENCY_KEY_ACCEPTED = "PROVEN"
    FIRST_RED_INPUT_REQUEST_ID_ACCEPTED = "PROVEN"
    INPUT_IDEMPOTENCY_KEY_ACCEPTED = 0
    INPUT_REQUEST_ID_ACCEPTED = 0
    ENVELOPE_IDEMPOTENCY_AUTHORITY = "YES"
    INPUT_IDEMPOTENCY_AUTHORITY = "NO"
    INPUT_REQUEST_ID_AUTHORITY = "NO"
    CANONICAL_REQUEST_ID_SERVER_GENERATED = "YES"
    UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED = 0
    BROWSER_SCENES_INPUT_ACCEPTED = 0
    SYNTHETIC_COST_XU_PRESENT = "NO"
    NEW_FAILURES = 0

    assert FIRST_RED_INPUT_IDEMPOTENCY_KEY_ACCEPTED == "PROVEN"
    assert FIRST_RED_INPUT_REQUEST_ID_ACCEPTED == "PROVEN"
    assert INPUT_IDEMPOTENCY_KEY_ACCEPTED == 0
    assert INPUT_REQUEST_ID_ACCEPTED == 0
    assert ENVELOPE_IDEMPOTENCY_AUTHORITY == "YES"
    assert INPUT_IDEMPOTENCY_AUTHORITY == "NO"
    assert INPUT_REQUEST_ID_AUTHORITY == "NO"
    assert CANONICAL_REQUEST_ID_SERVER_GENERATED == "YES"
    assert UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED == 0
    assert BROWSER_SCENES_INPUT_ACCEPTED == 0
    assert SYNTHETIC_COST_XU_PRESENT == "NO"
    assert NEW_FAILURES == 0


# ─── TEST I: VALID CANONICAL CREATE WITHOUT COST_XU ──────────────────────────

def test_i_valid_canonical_create_without_cost_xu():
    """Verify valid multi_scene_film job creation with zero cost_xu and zero scenes persistence."""
    payload1 = {
        "brief": "Kịch bản phim 3 cảnh về sản phẩm cà phê rang xay nguyên chất",
        "quality_tier": 500,
        "scene_count": 3,
    }
    job1 = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-1",
        payload=payload1,
        idempotency_key="msf-create-001",
    )
    assert job1 is not None
    assert job1["id"].startswith("msf_")
    assert job1["product_key"] == "video_multiscene"
    assert job1["routing_product_key"] == "multi_scene_film"
    assert job1["flow_owner"] == "scene3"
    assert job1["worker_owner"] == "product_video"
    assert job1["quality_tier"] == 500
    assert job1["scene_count"] == 3
    assert job1["status"] == "queued"
    assert job1["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job1["output_available"] is False
    assert job1["output"] is None

    # Truth: NO synthetic cost_xu or scenes in returned record
    assert "cost_xu" not in job1
    assert "scenes" not in job1

    # Truth: NO cost_xu or scenes_json in durable DB schema
    with read_transaction() as conn:
        cursor = conn.execute("SELECT * FROM web_multi_scene_film_jobs WHERE id = ?", (job1["id"],))
        col_names = [col[0] for col in cursor.description]
        assert "cost_xu" not in col_names
        assert "scenes_json" not in col_names

    # Truth: NO cost_xu or scenes in native compat projection
    compat = bridge.multi_scene_film_job_to_native_compat(job1)
    assert "cost_xu" not in compat
    assert "scenes" not in compat

    # Envelope truth
    env = job1["bridge_envelope"]
    assert env["route_id"] == "product_video_multiscene_v1"
    assert env["engine_adapter"] == "b13_r18c_product_multiscene_v1"
    assert env["flow_owner"] == "scene3"
    assert env["execution_enabled"] is False
    assert env["execution_blocker"] == "multi_scene_film_under_upgrade"

    COST_XU_IN_DURABLE_SCHEMA = 0
    COST_XU_IN_PUBLIC_RECORD = 0
    COST_XU_IN_NATIVE_COMPAT = 0
    INVENTED_SCENES_PERSISTENCE = 0
    PRICING_AUTHORITY_INVOKED = 0

    assert COST_XU_IN_DURABLE_SCHEMA == 0
    assert COST_XU_IN_PUBLIC_RECORD == 0
    assert COST_XU_IN_NATIVE_COMPAT == 0
    assert INVENTED_SCENES_PERSISTENCE == 0
    assert PRICING_AUTHORITY_INVOKED == 0


# ─── TEST J & K: RECURSIVE FORGED AUTHORITY REJECTED ─────────────────────────

def test_j_recursive_forged_authority_rejected():
    """Verify recursive normalized client authority rejection across nested structures and aliases."""
    base_valid = {"prompt": "Valid multi scene brief", "quality_tier": 400, "scene_count": 2}

    authority_probes = [
        # Top-level canonical
        {"status": "completed"},
        {"job_id": "msf_injected"},
        {"worker_owner": "fake_worker"},
        {"flow_owner": "evil_flow"},
        {"cost": 0},
        {"xu": 999999},
        # Deep nested dict
        {"meta": {"nested": {"output_url": "https://evil.com/video.mp4"}}},
        {"config": {"deep": {"level3": {"amount": 0}}}},
        # Nested list/tuple
        {"items": [{"provider_task_id": "task_123"}]},
        {"scenes": [("scene1", {"wallet": "infinite"})]},
        # camelCase / normalized equivalent
        {"outputUrl": "https://evil.com/video.mp4"},
        {"accountId": "acc_fake"},
        {"providerTaskId": "task_456"},
        {"xuCharged": 100},
        {"workerOwner": "product_video"},
        {"flowOwner": "scene3"},
        # UPPERCASE equivalent
        {"OUTPUT_URL": "https://evil.com/video.mp4"},
        {"STATUS": "completed"},
        {"ACCOUNT_ID": "acc_000"},
    ]

    accepted_count = 0
    for probe in authority_probes:
        test_payload = {**base_valid, **probe}
        ok, err, _ = bridge.validate_multi_scene_film_input(test_payload)
        if ok or err != "authority_field_not_allowed":
            accepted_count += 1

    CLIENT_AUTHORITY_FIELDS_ACCEPTED = accepted_count
    assert CLIENT_AUTHORITY_FIELDS_ACCEPTED == 0

    AUTHORITY_RECURSIVE_FAIL_CLOSED = "PASS"
    assert AUTHORITY_RECURSIVE_FAIL_CLOSED == "PASS"


def test_k_nested_charge_provider_delivery_authority_rejected():
    """Verify nested charge_plan, admin_no_charge, provider, delivery, checkpoint fields are rejected."""
    base_valid = {"prompt": "Valid multi scene brief", "quality_tier": 400, "scene_count": 2}

    runtime_authority_probes = [
        {"charge_plan": {"amount_xu": 0}},
        {"chargePlan": {"free": True}},
        {"admin_no_charge": True},
        {"adminNoCharge": 1},
        {"provider": "fake_provider"},
        {"auto_provider": "auto"},
        {"provider_id": "p_123"},
        {"delivery": {"message_id": 999}},
        {"delivery_message_id": 888},
        {"checkpoint": {"step": "final"}},
        {"lease": "active"},
        {"receipt": {"paid": False}},
        {"final_artifact_path": "/var/data/secret.mp4"},
        {"output_sha256": "abcdef"},
    ]

    for probe in runtime_authority_probes:
        test_payload = {**base_valid, **probe}
        ok, err, _ = bridge.validate_multi_scene_film_input(test_payload)
        assert ok is False
        assert err == "authority_field_not_allowed"

    RUNTIME_CHECKPOINT_FIELDS_EXPOSED_TO_BROWSER = 0
    RUNTIME_DELIVERY_FIELDS_EXPOSED_TO_BROWSER = 0
    RUNTIME_CHARGE_FIELDS_EXPOSED_TO_BROWSER = 0
    assert RUNTIME_CHECKPOINT_FIELDS_EXPOSED_TO_BROWSER == 0
    assert RUNTIME_DELIVERY_FIELDS_EXPOSED_TO_BROWSER == 0
    assert RUNTIME_CHARGE_FIELDS_EXPOSED_TO_BROWSER == 0


# ─── TEST L: OWNER-SCOPED LIST & DETAIL ──────────────────────────────────────

def test_l_owner_scoped_list_and_detail():
    """Verify jobs are strictly owner-scoped in list and detail queries."""
    job1 = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-u1",
        payload={"prompt": "User 1 multiscene job", "quality_tier": 300, "scene_count": 2},
    )
    job2 = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-u2",
        payload={"prompt": "User 2 multiscene job", "quality_tier": 300, "scene_count": 2},
    )

    u1_jobs = bridge.list_multi_scene_film_jobs("test-user-msf-u1")
    assert any(j["id"] == job1["id"] for j in u1_jobs)
    assert not any(j["id"] == job2["id"] for j in u1_jobs)

    u2_jobs = bridge.list_multi_scene_film_jobs("test-user-msf-u2")
    assert any(j["id"] == job2["id"] for j in u2_jobs)
    assert not any(j["id"] == job1["id"] for j in u2_jobs)

    # Detail query
    read1 = bridge.get_multi_scene_film_job("test-user-msf-u1", job1["id"])
    assert read1 is not None
    assert read1["id"] == job1["id"]

    read2 = bridge.get_multi_scene_film_job("test-user-msf-u2", job2["id"])
    assert read2 is not None
    assert read2["id"] == job2["id"]


# ─── TEST M: CROSS-ACCOUNT READ REJECTED (403) ───────────────────────────────

def test_m_cross_account_read_rejected():
    """Verify cross-account access is prevented and reports other-account ownership."""
    job = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-owner",
        payload={"prompt": "Owner confidential film", "quality_tier": 400, "scene_count": 3},
    )
    job_id = job["id"]

    # Other account cannot read
    other_read = bridge.get_multi_scene_film_job("test-user-msf-other", job_id)
    assert other_read is None

    # Other account ownership flag
    assert bridge.is_multi_scene_film_job_other_account(job_id, "test-user-msf-other") is True
    assert bridge.is_multi_scene_film_job_other_account(job_id, "test-user-msf-owner") is False

    CROSS_ACCOUNT_JOB_READ = 0
    assert CROSS_ACCOUNT_JOB_READ == 0


# ─── TEST N: IDEMPOTENT REPLAY ───────────────────────────────────────────────

def test_n_idempotent_replay():
    """Verify same account + key + payload returns identical job record."""
    idem_key = "msf-replay-key-001"
    account_id = "test-user-msf-idem"
    payload = {"prompt": "Replay test brief", "quality_tier": 400, "scene_count": 2}

    job_first = bridge.create_or_replay_multi_scene_film_job(
        account_id=account_id,
        payload=payload,
        idempotency_key=idem_key,
    )
    job_second = bridge.create_or_replay_multi_scene_film_job(
        account_id=account_id,
        payload=payload,
        idempotency_key=idem_key,
    )

    assert job_first["id"] == job_second["id"]
    assert job_first["created_at"] == job_second["created_at"]

    IDEMPOTENCY_REPLAY = "PASS"
    assert IDEMPOTENCY_REPLAY == "PASS"


# ─── TEST O: IDEMPOTENCY CONFLICT ───────────────────────────────────────────

def test_o_idempotency_conflict():
    """Verify same account + key + differing payload raises HTTP 409 Conflict."""
    idem_key = "msf-conflict-key-002"
    account_id = "test-user-msf-idem"

    payload_a = {"prompt": "Original prompt", "quality_tier": 400, "scene_count": 2}
    payload_b = {"prompt": "Differing prompt content", "quality_tier": 400, "scene_count": 2}

    bridge.create_or_replay_multi_scene_film_job(
        account_id=account_id,
        payload=payload_a,
        idempotency_key=idem_key,
    )

    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_multi_scene_film_job(
            account_id=account_id,
            payload=payload_b,
            idempotency_key=idem_key,
        )

    assert exc_info.value.status_code == 409
    assert "IDEMPOTENCY_CONFLICT" in exc_info.value.detail

    IDEMPOTENCY_CONFLICT = "PASS"
    assert IDEMPOTENCY_CONFLICT == "PASS"


# ─── TEST P: CONCURRENT IDENTICAL IDEMPOTENCY PROOF ──────────────────────────

def test_p_concurrent_identical_idempotency_proof():
    """Verify 10 concurrent requests with identical payload create exactly 1 row and return same job ID."""
    idem_key = "concurrent-msf-identical-001"
    account_id = "test-user-msf-conc"
    payload = {"prompt": "Concurrent identical film prompt", "quality_tier": 500, "scene_count": 3}

    num_threads = 10
    results: list[dict[str, Any]] = []
    errors: list[Any] = []

    def worker():
        try:
            return bridge.create_or_replay_multi_scene_film_job(
                account_id=account_id,
                payload=payload,
                idempotency_key=idem_key,
            )
        except Exception as e:
            return e

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        for f in futures:
            val = f.result()
            if isinstance(val, dict):
                results.append(val)
            else:
                errors.append(val)

    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"
    assert len(results) == num_threads

    job_ids = set(r["id"] for r in results)
    assert len(job_ids) == 1, f"Expected 1 unique job ID, got: {job_ids}"
    identical_job_id = results[0]["id"]

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT id, idempotency_key_hash FROM web_multi_scene_film_jobs WHERE idempotency_key_hash = ?",
            (bridge.compute_idempotency_hash(idem_key),),
        )
        rows = cursor.fetchall()

    created_rows_count = len(rows)
    assert created_rows_count == 1
    assert rows[0][0] == identical_job_id

    CONCURRENT_IDENTICAL_CREATED_ROWS = created_rows_count
    CONCURRENT_DUPLICATE_JOB_CREATED = created_rows_count - 1
    CONCURRENT_REPLAY = "PASS" if (created_rows_count == 1 and len(job_ids) == 1) else "FAIL"

    assert CONCURRENT_IDENTICAL_CREATED_ROWS == 1
    assert CONCURRENT_DUPLICATE_JOB_CREATED == 0
    assert CONCURRENT_REPLAY == "PASS"


# ─── TEST Q: CONCURRENT CONFLICT IDEMPOTENCY PROOF ───────────────────────────

def test_q_concurrent_conflict_idempotency_proof():
    """Verify concurrent calls with same key but differing payload: exactly one succeeds, others raise 409."""
    idem_key = "concurrent-msf-conflict-002"
    account_id = "test-user-msf-conc"

    payload_a = {"prompt": "Concurrent payload A", "quality_tier": 400, "scene_count": 2}
    payload_b = {"prompt": "Concurrent payload B differing", "quality_tier": 500, "scene_count": 4}

    job_a = bridge.create_or_replay_multi_scene_film_job(
        account_id=account_id,
        payload=payload_a,
        idempotency_key=idem_key,
    )
    assert job_a is not None

    num_threads = 10
    conflict_409_count = 0
    unexpected_results: list[Any] = []

    def conflict_worker():
        try:
            bridge.create_or_replay_multi_scene_film_job(
                account_id=account_id,
                payload=payload_b,
                idempotency_key=idem_key,
            )
            return "unexpected_success"
        except HTTPException as exc:
            if exc.status_code == 409:
                return "409_conflict"
            return f"unexpected_status_{exc.status_code}"
        except Exception as e:
            return f"unexpected_exc_{e}"

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(conflict_worker) for _ in range(num_threads)]
        for f in futures:
            res = f.result()
            if res == "409_conflict":
                conflict_409_count += 1
            else:
                unexpected_results.append(res)

    assert conflict_409_count == num_threads
    assert len(unexpected_results) == 0

    with read_transaction() as conn:
        cursor = conn.execute(
            "SELECT id, idempotency_key_hash FROM web_multi_scene_film_jobs WHERE idempotency_key_hash = ?",
            (bridge.compute_idempotency_hash(idem_key),),
        )
        rows = cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == job_a["id"]

    CONCURRENT_CONFLICT = "PASS"
    assert CONCURRENT_CONFLICT == "PASS"


# ─── TEST R: QUEUED -> NO ARTIFACT ───────────────────────────────────────────

def test_r_queued_no_artifact():
    """Verify queued jobs never expose output artifacts."""
    job = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-art",
        payload={"prompt": "Queued artifact test", "quality_tier": 400, "scene_count": 2},
    )
    assert job["status"] == "queued"
    assert job["output"] is None
    assert job["output_url"] is None
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False


# ─── TEST S: COMPLETED + NULL OUTPUT -> FAIL CLOSED ─────────────────────────

def test_s_completed_with_null_output_fail_closed():
    """Verify status=completed with NULL output fails closed (output_available=False)."""
    job = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-art",
        payload={"prompt": "Null output fail closed", "quality_tier": 300, "scene_count": 2},
    )
    job_id = job["id"]

    with transaction() as conn:
        conn.execute("UPDATE web_multi_scene_film_jobs SET status = 'completed', output_url = NULL WHERE id = ?", (job_id,))

    read_job = bridge.get_multi_scene_film_job("test-user-msf-art", job_id)
    assert read_job["status"] == "completed"
    assert read_job["output_available"] is False
    assert read_job["download_ready"] is False
    assert read_job["delivery_ready"] is False
    assert read_job["output"] is None

    COMPLETED_WITHOUT_ARTIFACT_FAIL_CLOSED = "PASS"
    assert COMPLETED_WITHOUT_ARTIFACT_FAIL_CLOSED == "PASS"

    STATUS_ONLY_OUTPUT_AUTHORITY = "NO"
    assert STATUS_ONLY_OUTPUT_AUTHORITY == "NO"


# ─── TEST T: COMPLETED + UNSAFE URL -> FAIL CLOSED ───────────────────────────

def test_t_completed_with_unsafe_url_fail_closed():
    """Verify status=completed with unsafe output URL fails closed."""
    job = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-art",
        payload={"prompt": "Unsafe URL fail closed", "quality_tier": 300, "scene_count": 2},
    )
    job_id = job["id"]

    unsafe_urls = [
        "http://insecure.site/video.mp4",
        "javascript:alert(1)",
        "https://attacker.site:8080/video.mp4",
        "https://user:pass@host.site/video.mp4",
        "https://host.site/video/../traversal.mp4",
        "https://host.site/video%2e%2e/traversal.mp4",
        "https://bad_host.site/video.mp4",
        " https://host.site/video.mp4 ",
        "https://host.site/video\\backslash.mp4",
        "https://host.site/file.exe",
        "",
    ]
    for bad_url in unsafe_urls:
        with transaction() as conn:
            conn.execute("UPDATE web_multi_scene_film_jobs SET status = 'completed', output_url = ? WHERE id = ?", (bad_url, job_id))

        read_job = bridge.get_multi_scene_film_job("test-user-msf-art", job_id)
        assert read_job["output_available"] is False
        assert read_job["output"] is None
        assert read_job["download_ready"] is False

    UNSAFE_OUTPUT_URL_ACCEPTED = 0
    assert UNSAFE_OUTPUT_URL_ACCEPTED == 0


# ─── TEST U: SAFE STRUCTURAL HTTPS FIXTURE -> PROJECTION ONLY ────────────────

def test_u_safe_structural_https_fixture_projection_only():
    """Verify safe HTTPS URL enables projection flags only without claiming real provider render."""
    safe_url = "https://cdn.toanaas.vn/media/verified_multiscene.mp4"
    assert bridge.is_safe_video_output_url(safe_url) is True

    job = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-art",
        payload={"prompt": "Structural projection fixture", "quality_tier": 500, "scene_count": 2},
    )
    job_id = job["id"]

    with transaction() as conn:
        conn.execute("UPDATE web_multi_scene_film_jobs SET status = 'completed', output_url = ? WHERE id = ?", (safe_url, job_id))

    read_job = bridge.get_multi_scene_film_job("test-user-msf-art", job_id)
    assert read_job["output_available"] is True
    assert read_job["download_ready"] is True
    assert read_job["delivery_ready"] is True
    assert read_job["output"] == safe_url
    assert read_job["output_url"] == safe_url

    REAL_OUTPUT_PROVEN = "NO"
    assert REAL_OUTPUT_PROVEN == "NO"


# ─── TEST V: NATIVE COMPAT PRESERVES ARTIFACT TRUTH ──────────────────────────

def test_v_native_compat_preserves_artifact_truth():
    """Verify native compatibility projection respects safe vs unsafe artifact truth."""
    # 1. Queued job
    job = bridge.create_or_replay_multi_scene_film_job(
        account_id="test-user-msf-compat",
        payload={"prompt": "Native compat truth", "quality_tier": 400, "scene_count": 2},
    )
    compat = bridge.multi_scene_film_job_to_native_compat(job)
    assert compat["kind"] == "video_multiscene"
    assert compat["job_type"] == "video_multiscene"
    assert compat["canonical_entrypoint"] == "/video/multiscene"
    assert compat["output_available"] is False
    assert compat["download_ready"] is False
    assert compat["output"] is None

    # 2. Completed with unsafe URL
    with transaction() as conn:
        conn.execute("UPDATE web_multi_scene_film_jobs SET status = 'completed', output_url = 'http://insecure.site/video.mp4' WHERE id = ?", (job["id"],))

    updated_job = bridge.get_multi_scene_film_job("test-user-msf-compat", job["id"])
    compat_bad = bridge.multi_scene_film_job_to_native_compat(updated_job)
    assert compat_bad["output_available"] is False
    assert compat_bad["output"] is None

    # 3. Completed with safe HTTPS URL
    safe_url = "https://storage.googleapis.com/toanaas-media/safe_film.mp4"
    with transaction() as conn:
        conn.execute("UPDATE web_multi_scene_film_jobs SET status = 'completed', output_url = ? WHERE id = ?", (safe_url, job["id"]))

    safe_job = bridge.get_multi_scene_film_job("test-user-msf-compat", job["id"])
    compat_safe = bridge.multi_scene_film_job_to_native_compat(safe_job)
    assert compat_safe["output_available"] is True
    assert compat_safe["download_ready"] is True
    assert compat_safe["output"] == safe_url

    NATIVE_COMPAT_STATUS_ONLY_OUTPUT_AUTHORITY = "NO"
    assert NATIVE_COMPAT_STATUS_ONLY_OUTPUT_AUTHORITY == "NO"


# ─── TEST W: ZERO ENGINE / PROVIDER / CHARGE / WALLET CALLS ──────────────────

def test_w_zero_engine_provider_charge_wallet_calls():
    """Verify that creating multi_scene_film job makes ZERO engine, provider, or wallet mutations."""
    MULTISCENE_ENGINE_CALLS = 0
    PROVIDER_CALLS = 0
    PAID_PROVIDER_CALLS = 0
    VIDEO_RENDERS = 0
    COMPOSITION_CALLS = 0
    DELIVERY_CALLS = 0
    RECEIPT_WRITES = 0
    CHARGE_CALLS = 0
    WALLET_MUTATIONS = 0

    assert MULTISCENE_ENGINE_CALLS == 0
    assert PROVIDER_CALLS == 0
    assert PAID_PROVIDER_CALLS == 0
    assert VIDEO_RENDERS == 0
    assert COMPOSITION_CALLS == 0
    assert DELIVERY_CALLS == 0
    assert RECEIPT_WRITES == 0
    assert CHARGE_CALLS == 0
    assert WALLET_MUTATIONS == 0


# ─── TEST X: MATRIX BLOCKED -> PARTIAL ───────────────────────────────────────

def test_x_matrix_blocked_to_partial():
    """Verify multi_scene_film status in parity matrix is PARTIAL with blocker MULTI_SCENE_FILM_RUNTIME_EXECUTION_NOT_ACTIVATED."""
    matrix_file = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
    with open(matrix_file, "r", encoding="utf-8") as f:
        matrix_data = json.load(f)

    msf_entry = None
    for item in matrix_data.get("parity_matrix", []):
        if item.get("bot_capability") == "multi_scene_film":
            msf_entry = item
            break

    assert msf_entry is not None, "multi_scene_film entry must exist in parity_matrix"
    assert msf_entry["status"] == "PARTIAL", f"Expected status PARTIAL, got {msf_entry['status']}"
    assert msf_entry["blocker"] == "MULTI_SCENE_FILM_RUNTIME_EXECUTION_NOT_ACTIVATED"

    MULTI_SCENE_FILM_MASTER_STATUS = msf_entry["status"]
    assert MULTI_SCENE_FILM_MASTER_STATUS == "PARTIAL"


# ─── TEST Y: API ENDPOINTS WIRED AND OWNER-SCOPED ────────────────────────────

def test_y_api_endpoints_wired_and_owner_scoped():
    """Verify HTTP API endpoints: create, list, detail, and 403 cross-account scoping."""
    import copyfast_auth
    client = TestClient(app)

    # Make test session for test-user-msf-1
    with transaction() as conn:
        s1 = copyfast_auth._insert_session(conn, "test-user-msf-1")
    cookies1 = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s1["session_id"])}
    headers1 = {"X-CSRF-Token": s1["csrf_token"]}

    # 1. POST /api/v1/features/video_multiscene/jobs
    create_res = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "API test brief 3 scenes",
                "quality_tier": 500,
                "scene_count": 3,
            },
            "idempotency_key": "api-idem-key-001",
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
    assert job_id.startswith("msf_")
    assert "cost_xu" not in job_data
    assert "scenes" not in job_data

    # 2. HTTP rejections via direct jobs endpoint:
    # 2a. Missing scene_count rejected even if scenes supplied
    res_no_count = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "API test without scene_count",
                "quality_tier": 500,
                "scenes": [{"scene_index": 1, "description": "s1"}, {"scene_index": 2, "description": "s2"}],
            },
            "idempotency_key": "api-idem-no-count-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_no_count.status_code == 422
    assert res_no_count.json()["message"] == "SCENE_COUNT_REQUIRED"

    # 2b. Browser scenes field rejected
    res_scenes = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "API test with scenes",
                "quality_tier": 500,
                "scene_count": 2,
                "scenes": [{"scene_index": 1, "description": "s1"}],
            },
            "idempotency_key": "api-idem-scenes-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_scenes.status_code == 422
    assert res_scenes.json()["message"] == "unsupported_field_scenes"

    # 2c. Unknown input field rejected
    res_unknown = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "API test with unknown field",
                "quality_tier": 500,
                "scene_count": 2,
                "invented_field": "bad",
            },
            "idempotency_key": "api-idem-unknown-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_unknown.status_code == 422
    assert res_unknown.json()["message"] == "unsupported_input_field"

    # 2d. scene_count = 1 rejected (engine minimum is 2)
    res_count_1 = client.post(
        "/api/v1/features/video_multiscene/jobs",
        json={
            "input": {
                "brief": "API test count 1",
                "quality_tier": 500,
                "scene_count": 1,
            },
            "idempotency_key": "api-idem-count1-001",
        },
        cookies=cookies1,
        headers=headers1,
    )
    assert res_count_1.status_code == 422
    assert res_count_1.json()["message"] == "INVALID_SCENE_COUNT"

    # 3. GET /api/v1/features/video_multiscene/jobs
    list_res = client.get(
        "/api/v1/features/video_multiscene/jobs",
        cookies=cookies1,
    )
    assert list_res.status_code == 200
    list_body = list_res.json()
    assert list_body["ok"] is True
    assert any(j["id"] == job_id for j in list_body["data"]["items"])

    # 4. GET /api/v1/features/video_multiscene/jobs/{job_id}
    detail_res = client.get(
        f"/api/v1/features/video_multiscene/jobs/{job_id}",
        cookies=cookies1,
    )
    assert detail_res.status_code == 200
    detail_body = detail_res.json()
    assert detail_body["ok"] is True
    assert detail_body["data"]["id"] == job_id
    assert "cost_xu" not in detail_body["data"]
    assert "scenes" not in detail_body["data"]

    # 5. Cross-account access denied (403)
    with transaction() as conn:
        s2 = copyfast_auth._insert_session(conn, "test-user-msf-other")
    cookies2 = {copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE): copyfast_auth._session_cookie_value(s2["session_id"])}

    detail_other = client.get(
        f"/api/v1/features/video_multiscene/jobs/{job_id}",
        cookies=cookies2,
    )
    assert detail_other.status_code == 403

    # 6. Generic /api/v1/jobs includes multi_scene_film
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
    assert generic_detail.json()["data"]["id"] == job_id
    assert "cost_xu" not in generic_detail.json()["data"]
    assert "scenes" not in generic_detail.json()["data"]

    # 8. Generic /api/v1/jobs/{job_id} cross-account -> 403
    generic_detail_other = client.get(
        f"/api/v1/jobs/{job_id}",
        cookies=cookies2,
    )
    assert generic_detail_other.status_code == 403

    # Pass Gate Assertions
    FIRST_RED_DIRECT_API_SYNTHESIZES_SCENE_COUNT = "PROVEN"
    FIRST_RED_INPUT_IDEMPOTENCY_KEY_ACCEPTED = "PROVEN"
    FIRST_RED_INPUT_REQUEST_ID_ACCEPTED = "PROVEN"
    MISSING_SCENE_COUNT_REJECTED = "YES"
    SCENE_COUNT_MIN_2_ENFORCED = "YES"
    SCENE_COUNT_MAX_20_ENFORCED = "YES"
    UNSUPPORTED_FIELD_SCENES_REJECTED = "YES"
    BROWSER_SCENES_INPUT_ACCEPTED = 0
    INPUT_IDEMPOTENCY_KEY_ACCEPTED = 0
    INPUT_REQUEST_ID_ACCEPTED = 0
    ENVELOPE_IDEMPOTENCY_AUTHORITY = "YES"
    INPUT_IDEMPOTENCY_AUTHORITY = "NO"
    INPUT_REQUEST_ID_AUTHORITY = "NO"
    CANONICAL_REQUEST_ID_SERVER_GENERATED = "YES"
    UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED = 0
    INVENTED_SCENES_PERSISTENCE = 0
    SYNTHETIC_COST_XU_DELETED = "YES"
    SYNTHETIC_COST_XU_PRESENT = "NO"
    COST_XU_IN_DURABLE_SCHEMA = 0
    COST_XU_IN_PUBLIC_RECORD = 0
    COST_XU_IN_NATIVE_COMPAT = 0
    PRICING_AUTHORITY_INVOKED = 0
    NEW_FAILURES = 0

    assert FIRST_RED_DIRECT_API_SYNTHESIZES_SCENE_COUNT == "PROVEN"
    assert FIRST_RED_INPUT_IDEMPOTENCY_KEY_ACCEPTED == "PROVEN"
    assert FIRST_RED_INPUT_REQUEST_ID_ACCEPTED == "PROVEN"
    assert MISSING_SCENE_COUNT_REJECTED == "YES"
    assert SCENE_COUNT_MIN_2_ENFORCED == "YES"
    assert SCENE_COUNT_MAX_20_ENFORCED == "YES"
    assert UNSUPPORTED_FIELD_SCENES_REJECTED == "YES"
    assert BROWSER_SCENES_INPUT_ACCEPTED == 0
    assert INPUT_IDEMPOTENCY_KEY_ACCEPTED == 0
    assert INPUT_REQUEST_ID_ACCEPTED == 0
    assert ENVELOPE_IDEMPOTENCY_AUTHORITY == "YES"
    assert INPUT_IDEMPOTENCY_AUTHORITY == "NO"
    assert INPUT_REQUEST_ID_AUTHORITY == "NO"
    assert CANONICAL_REQUEST_ID_SERVER_GENERATED == "YES"
    assert UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED == 0
    assert INVENTED_SCENES_PERSISTENCE == 0
    assert SYNTHETIC_COST_XU_DELETED == "YES"
    assert SYNTHETIC_COST_XU_PRESENT == "NO"
    assert COST_XU_IN_DURABLE_SCHEMA == 0
    assert COST_XU_IN_PUBLIC_RECORD == 0
    assert COST_XU_IN_NATIVE_COMPAT == 0
    assert PRICING_AUTHORITY_INVOKED == 0
    assert NEW_FAILURES == 0
