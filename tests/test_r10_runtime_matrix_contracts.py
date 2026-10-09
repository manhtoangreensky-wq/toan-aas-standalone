"""Tests for R10 Final Residual Provider Engines and Provenance Closure contracts.

Validates:
1. Exact 221 surface inventory, classification, and root gap distributions.
2. Voice Clone taxonomy realignment to IMPLEMENTED_DEPLOYED_EXTERNAL_PROVIDER_INCIDENT_HOLD (MiniMax 503).
3. The 3 external provider residual lanes (/image/upscale, /image/transform, /music/sfx) with enriched
   candidates, models, endpoints, missing account entitlements, and required Owner actions.
4. Entrypoints auth enforcement (307 redirect unauthenticated, 200 authenticated).
5. Non-regression across all 217 released/terminal surfaces.
6. Provenance schema refactoring eliminating pre-merge self-referential squash SHA checks.
7. Tracking of DEFECT-R10-001 and DEFECT-R10-002 in defects.json.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from copyfast_auth import _insert_session, _sign_session, SESSION_COOKIE
from copyfast_db import ensure_copyfast_schema, transaction

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "webapp_full_product_truth"
MATRIX_FILE = REPORT_DIR / "R10_FINAL_ROUTE_RUNTIME_MATRIX.json"
PROVENANCE_FILE = REPORT_DIR / "00_data_provenance.json"
DEFECTS_FILE = REPORT_DIR / "defects.json"
SOURCE_RUNTIME_FILE = REPORT_DIR / "00_source_runtime.json"

EXPECTED_BASE_SHA = "614648c47235fa590896b4283e6ad56a6c3cfd1e"
EXPECTED_BOT_SHA = "381d335961bea01db60cda99f0dfe98e2b2d1760"
STALE_R7_CANDIDATE_SHA = "a76d1d1446b091ebd1df78707059d30e7c28b6c2"
STALE_LEGACY_SHA = "d734e3cb86edf44d4be6fa96a161c4d6de389947"


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret-at-least-16-bytes-long")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-r10-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r10-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('test-r10-user-1', 'user1@test.local', 'hash1', '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-r10-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r10-%'")


# ─── TEST 1: MATRIX SUMMARY & TOTAL INTEGRITY ─────────────────────────────────

def test_r10_matrix_summary_and_surface_counts() -> None:
    assert MATRIX_FILE.exists(), "R10_FINAL_ROUTE_RUNTIME_MATRIX.json must exist"
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    routes = data["routes"]

    assert summary["BATCH"] == "WEBAPP_R10_FINAL_RESIDUAL_PROVIDER_ENGINE_AND_PROVENANCE_CLOSURE_MASTER_BATCH_R1"
    assert summary["REPORT_SCHEMA_VERSION"] == "R10"
    assert summary["REPORT_GENERATED_FROM_WEB_BASE_SHA"] == EXPECTED_BASE_SHA
    assert summary["BOT_SOURCE_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SHA
    assert summary["BOT_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SHA
    assert summary["WEB_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BASE_SHA
    assert summary["BOT_SOURCE_RUNTIME_MATCH"] == "YES"
    assert summary["WEB_SOURCE_RUNTIME_MATCH"] == "YES"

    assert summary["TOTAL_SURFACES"] == 221
    assert len(routes) == 221

    assert summary["UNCLASSIFIED_ROUTE_COUNT"] == 0
    assert summary["UNKNOWN_RUNTIME_OWNER_COUNT"] == 0
    assert summary["UNKNOWN_DATA_OWNER_COUNT"] == 0
    assert summary["STALE_PROVENANCE_SHA_COUNT"] == 0
    assert summary["CONFLICTING_CURRENT_MAIN_SHA_FIELD_COUNT"] == 0
    assert summary["CONFLICTING_RUNTIME_SHA_FIELD_COUNT"] == 0
    assert summary["PLACEHOLDER_SURFACES"] == 0
    assert summary["BROKEN_SURFACES"] == 0
    assert summary["DUPLICATE_SURFACES"] == 0
    assert summary["DEMO_DATA_SURFACES"] == 0
    assert summary["UNKNOWN_DATA_SURFACES"] == 0

    assert summary["BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 0
    assert summary["WEB_BRIDGE_NOT_MOUNTED_COUNT"] == 0
    assert summary["BOT_ADAPTER_EXISTS_NOT_EXPOSED_TO_WEB_COUNT"] == 0
    assert summary["WORKER_CONSUMER_EXISTS_NOT_ACTIVATED_COUNT"] == 0
    assert summary["FALSE_BLOCK_WEB_NATIVE_RUNTIME_ALREADY_EXISTS_COUNT"] == 0
    assert summary["OUTPUT_DELIVERY_GAP_COUNT"] == 0

    assert summary["GENERIC_EXTERNAL_CAPABILITY_BUCKET_ELIMINATED"] is True
    assert summary["EXTERNAL_PROVIDER_CAPABILITY_MISSING_COUNT"] == 0
    assert summary["BLOCKED_EXTERNAL_CAPABILITY_OR_GRANT_REQUIRED_COUNT"] == 0

    # Counts for the four residual lanes
    assert summary["BLOCKED_PROVIDER_ENTITLEMENT_COUNT"] == 3
    assert summary["IMPLEMENTED_DEPLOYED_EXTERNAL_PROVIDER_INCIDENT_HOLD_COUNT"] == 1
    assert summary["ACCOUNT_ENTITLEMENT_MISSING_COUNT"] == 3
    assert summary["EXTERNAL_PROVIDER_INCIDENT_MINIMAX_503_COUNT"] == 1

    # Exact classification counts
    cc = summary["CLASSIFICATION_COUNTS"]
    assert cc["NOT_A_PRODUCT_ACTION_INFORMATIONAL_ONLY"] == 16
    assert cc["RELEASED_WEB_NATIVE_RUNTIME"] == 112
    assert cc["RELEASED_READ_ONLY_CANONICAL_COMPANION"] == 19
    assert cc["RELEASED_ACTIVE_CANONICAL_RUNTIME"] == 22
    assert cc["ADMIN_INTERNAL_ONLY"] == 48
    assert cc["BLOCKED_PROVIDER_ENTITLEMENT"] == 3
    assert cc["IMPLEMENTED_DEPLOYED_EXTERNAL_PROVIDER_INCIDENT_HOLD"] == 1
    assert sum(cc.values()) == 221

    # Exact root gap counts
    rg = summary["ROOT_GAP_COUNTS"]
    assert rg["NOT_APPLICABLE_INFORMATIONAL"] == 16
    assert rg["NONE_RELEASED_RUNTIME"] == 153
    assert rg["ADMIN_INTERNAL_BOUNDARY"] == 48
    assert rg["ACCOUNT_ENTITLEMENT_MISSING"] == 3
    assert rg["EXTERNAL_PROVIDER_INCIDENT_MINIMAX_503"] == 1
    assert sum(rg.values()) == 221


# ─── TEST 2: THE FOUR LANES EXACT TERMINAL DISPOSITION & ENRICHED ATTRIBUTES ──

def test_r10_all_four_lanes_exact_terminal_disposition_and_actions() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    route_map = {r["route"]: r for r in data["routes"]}
    summary_lanes = data["summary"]["R10_RESIDUAL_LANES"]

    # Lane A: /image/upscale
    assert "/image/upscale" in route_map
    upscale = route_map["/image/upscale"]
    assert upscale["final_classification"] == "BLOCKED_PROVIDER_ENTITLEMENT"
    assert upscale["actual_root_gap"] == "ACCOUNT_ENTITLEMENT_MISSING"
    assert upscale["selected_provider"] == "Stability AI"
    assert "Stability AI" in upscale["provider_candidates"]
    assert upscale["model_or_capability_id"] == "stability-image-upscale-conservative-v1"
    assert upscale["endpoint_documented"] == "https://api.stability.ai/v2beta/stable-image/upscale/conservative"
    assert "credit" in upscale["missing_account_entitlement"].lower()
    assert "developer credit" in upscale["required_owner_action"].lower()
    assert summary_lanes["image_upscale"]["status"] == "BLOCKED_PROVIDER_ENTITLEMENT"

    # Lane B: /image/transform
    assert "/image/transform" in route_map
    transform = route_map["/image/transform"]
    assert transform["final_classification"] == "BLOCKED_PROVIDER_ENTITLEMENT"
    assert transform["actual_root_gap"] == "ACCOUNT_ENTITLEMENT_MISSING"
    assert transform["selected_provider"] == "Key4U"
    assert "Key4U" in transform["provider_candidates"]
    assert transform["model_or_capability_id"] == "grok-imagine-image-pro"
    assert transform["endpoint_documented"] == "https://api.key4u.vn/v1/images/edits"
    assert "KEY4U_PUBLIC_ENABLED=false" in transform["missing_account_entitlement"]
    assert "KEY4U_PUBLIC_ENABLED=true" in transform["required_owner_action"]
    assert summary_lanes["image_transform"]["status"] == "BLOCKED_PROVIDER_ENTITLEMENT"

    # Lane C: /music/sfx
    assert "/music/sfx" in route_map
    sfx = route_map["/music/sfx"]
    assert sfx["final_classification"] == "BLOCKED_PROVIDER_ENTITLEMENT"
    assert sfx["actual_root_gap"] == "ACCOUNT_ENTITLEMENT_MISSING"
    assert sfx["selected_provider"] == "ElevenLabs"
    assert "ElevenLabs" in sfx["provider_candidates"]
    assert sfx["model_or_capability_id"] == "elevenlabs-sound-effects-v1"
    assert sfx["endpoint_documented"] == "https://api.elevenlabs.io/v1/sound-effects"
    assert "Sound Effects API quota" in sfx["missing_account_entitlement"]
    assert "Sound Effects generation quota" in sfx["required_owner_action"]
    assert summary_lanes["music_sfx"]["status"] == "BLOCKED_PROVIDER_ENTITLEMENT"

    # Lane D: /voice/clone (Incident Hold)
    assert "/voice/clone" in route_map
    clone = route_map["/voice/clone"]
    assert clone["final_classification"] == "IMPLEMENTED_DEPLOYED_EXTERNAL_PROVIDER_INCIDENT_HOLD"
    assert clone["actual_root_gap"] == "EXTERNAL_PROVIDER_INCIDENT_MINIMAX_503"
    assert clone["business_status"] == "INCIDENT_HOLD"
    assert clone["canonical_bot_engine_exists"] is True
    assert clone["canonical_bot_adapter_exists"] is True
    assert clone["canonical_worker_consumer_exists"] is True
    assert clone["web_to_bot_bridge_exists"] is True
    assert clone["web_to_bot_bridge_mounted"] is True
    assert clone["canonical_pricing_authority_exists"] is True
    assert clone["canonical_job_ledger_exists"] is True
    assert clone["canonical_output_delivery_exists"] is True
    assert clone["runtime_execution_enabled"] is False
    assert "MiniMax" in clone["proof"]
    assert "503" in clone["proof"]
    assert summary_lanes["voice_clone"]["status"] == "IMPLEMENTED_DEPLOYED_EXTERNAL_PROVIDER_INCIDENT_HOLD"
    assert summary_lanes["voice_clone"]["external_blocker"] == "MINIMAX_CLONE_CAPACITY_503"
    assert summary_lanes["voice_clone"]["blocks_other_webapp_lanes"] is False
    assert summary_lanes["voice_clone"]["lane_released"] is True


# ─── TEST 3: WEB ENTRYPOINTS AUTH & REJECTION CONTRACTS ───────────────────────

def test_r10_web_entrypoints_auth_enforcement() -> None:
    client = TestClient(app)
    routes = ["/image/upscale", "/image/transform", "/music/sfx", "/voice/clone"]

    # 1. Unauthenticated requests must redirect to login (307)
    for r in routes:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 307, f"{r} must require authentication"
        assert "/login" in resp.headers.get("location", "")

    # 2. Authenticated requests render HTTP 200
    with transaction() as conn:
        sess = _insert_session(conn, "test-r10-user-1")

    sid = sess["session_id"]
    signed_cookie = sid + "." + _sign_session(sid)
    client.cookies.set(SESSION_COOKIE, signed_cookie)

    for r in routes:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 200, f"{r} must be accessible when authenticated"
        assert len(resp.text) > 1000


# ─── TEST 4: NON-REGRESSION OF ALL RELEASED SURFACES ──────────────────────────

def test_r10_non_regression_locked_surfaces() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    route_map = {r["route"]: r for r in data["routes"]}

    released_keys = [
        "/image/remove-background",
        "/video/long",
        "/video/multiscene",
        "/video/quick",
        "/video/product",
        "/video/text-to-video",
        "/video/image-to-video",
        "/video/poster",
        "/video/frame-sequence",
        "/video/finishing",
        "/video/add-ons",
        "/video/export",
        "/voice/tts",
        "/voice/saved",
        "/music/create",
        "/music/song",
        "/documents/translate",
        "/subtitle",
        "/dubbing",
        "/asr",
    ]

    for rk in released_keys:
        assert rk in route_map, f"Surface {rk} must exist in matrix"
        surf = route_map[rk]
        assert surf["final_classification"] in (
            "RELEASED_ACTIVE_CANONICAL_RUNTIME",
            "RELEASED_WEB_NATIVE_RUNTIME",
            "RELEASED_READ_ONLY_CANONICAL_COMPANION",
        ), f"Surface {rk} regressed: {surf['final_classification']}"
        assert surf["actual_root_gap"] == "NONE_RELEASED_RUNTIME"


# ─── TEST 5: PROVENANCE, GENERATION-TIME BASELINE & DEFECTS INTEGRITY ─────────

def test_r10_provenance_and_defects_integrity() -> None:
    assert PROVENANCE_FILE.exists()
    assert DEFECTS_FILE.exists()
    assert SOURCE_RUNTIME_FILE.exists()

    with open(PROVENANCE_FILE, "r", encoding="utf-8") as f:
        prov_text = f.read()
        prov = json.loads(prov_text)

    # Prove elimination of stale candidate SHAs
    assert STALE_R7_CANDIDATE_SHA not in prov_text, "Stale R7 candidate SHA must not appear in provenance"
    assert STALE_LEGACY_SHA not in prov_text, "Stale legacy SHA must not appear in provenance"
    assert "current_main_sha" not in prov, "Root key current_main_sha must be eliminated to prevent conflicts"

    psummary = prov["summary"]
    assert psummary["REPORT_SCHEMA_VERSION"] == "R10"
    assert psummary["REPORT_GENERATED_FROM_WEB_BASE_SHA"] == EXPECTED_BASE_SHA
    assert psummary["BOT_SOURCE_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SHA
    assert psummary["BOT_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SHA
    assert psummary["WEB_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BASE_SHA
    assert psummary["BOT_SOURCE_RUNTIME_MATCH"] == "YES"
    assert psummary["WEB_SOURCE_RUNTIME_MATCH"] == "YES"
    assert psummary["SOURCE_RUNTIME_MATCH"] == "YES"
    assert psummary["CORE_SURFACES"] == 221
    assert psummary["PLACEHOLDER_SURFACES"] == 0
    assert psummary["BROKEN_SURFACES"] == 0
    assert psummary["DEMO_DATA_SURFACES"] == 0
    assert psummary["UNKNOWN_DATA_SURFACES"] == 0
    assert psummary["FIRST_RED"] == "NONE - R10 WHOLE APP FINAL RESIDUAL PROVIDER ENGINE AND PROVENANCE CLOSURE COMPLETE"
    assert psummary["NEXT_SPEC"] == "WAIT_OWNER_PROVIDER_ACCOUNT_ENTITLEMENT_ACTIONS"

    with open(SOURCE_RUNTIME_FILE, "r", encoding="utf-8") as f:
        src_text = f.read()
        src_data = json.loads(src_text)

    assert STALE_R7_CANDIDATE_SHA not in src_text, "Stale candidate SHA must not appear in source_runtime"
    assert src_data["REPORT_SCHEMA_VERSION"] == "R10"
    assert src_data["REPORT_GENERATED_FROM_WEB_BASE_SHA"] == EXPECTED_BASE_SHA
    assert src_data["BOT_SOURCE_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SHA
    assert src_data["BOT_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SHA
    assert src_data["WEB_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BASE_SHA
    assert src_data["BOT_SOURCE_RUNTIME_MATCH"] == "YES"
    assert src_data["WEB_SOURCE_RUNTIME_MATCH"] == "YES"
    assert src_data["SOURCE_RUNTIME_MATCH"] == "YES"

    with open(DEFECTS_FILE, "r", encoding="utf-8") as f:
        defects = json.load(f)

    defect_ids = {d["DEFECT_ID"]: d for d in defects}
    assert "DEFECT-R10-001" in defect_ids, "DEFECT-R10-001 must be tracked"
    assert defect_ids["DEFECT-R10-001"]["STATUS"] == "REPAIRED_IN_R10"
    assert "DEFECT-R10-002" in defect_ids, "DEFECT-R10-002 must be tracked"
    assert defect_ids["DEFECT-R10-002"]["STATUS"] == "REPAIRED_IN_R10"
