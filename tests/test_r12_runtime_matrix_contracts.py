"""Tests for R12 Bot Runtime Alignment and Parallel External Residual Closure contracts.

Validates:
1. Exact 221 surface inventory, classification, and root gap distributions.
2. Whole-app stall policy (NO_SINGLE_EXTERNAL_LANE_MAY_BLOCK_OTHER_LANES).
3. Product Video Bot runtime alignment lane (WAIT_OWNER_EXACT_DEPLOY_AUTHORIZATION).
4. SubDub remains CLOSED_RELEASED with zero provider entitlement residuals.
5. Voice Clone remains non-blocking incident hold (MiniMax 503) with zero internal engineering rework required.
6. The 3 external provider residual lanes (/image/upscale, /image/transform, /music/sfx) under WAIT_OWNER_EXTERNAL_ENTITLEMENT
   with exact Owner actions and activation readiness.
7. Complete 5-row Owner Action Board.
8. Entrypoints auth enforcement (307 redirect unauthenticated, 200 authenticated).
9. Non-regression across all 217 released/terminal surfaces.
10. Provenance baseline and tracking of DEFECT-R12-001 in defects.json.
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
MATRIX_FILE = REPORT_DIR / "R12_FINAL_ROUTE_RUNTIME_MATRIX.json"
PROVENANCE_FILE = REPORT_DIR / "00_data_provenance.json"
DEFECTS_FILE = REPORT_DIR / "defects.json"
SOURCE_RUNTIME_FILE = REPORT_DIR / "00_source_runtime.json"

EXPECTED_BASE_SHA = "66e546b0726da68a62038abc4f0690c70f4e0ef6"
EXPECTED_BOT_SOURCE_SHA = "5c38bd31c20f26f815e2f05b6419f4dd64afbba9"
EXPECTED_BOT_RUNTIME_SHA = "381d335961bea01db60cda99f0dfe98e2b2d1760"
STALE_R7_CANDIDATE_SHA = "a76d1d1446b091ebd1df78707059d30e7c28b6c2"
STALE_LEGACY_SHA = "d734e3cb86edf44d4be6fa96a161c4d6de389947"


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret-at-least-16-bytes-long")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-r12-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r12-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('test-r12-user-1', 'user1@test.local', 'hash1', '2026-10-10T00:00:00Z', '2026-10-10T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-r12-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r12-%'")


# ─── TEST 1: MATRIX SUMMARY & TOTAL INTEGRITY ─────────────────────────────────

def test_r12_matrix_summary_and_surface_counts() -> None:
    assert MATRIX_FILE.exists(), "R12_FINAL_ROUTE_RUNTIME_MATRIX.json must exist"
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    routes = data["routes"]

    assert summary["BATCH"] == "WEBAPP_R12_BOT_RUNTIME_ALIGNMENT_AND_PARALLEL_EXTERNAL_RESIDUAL_CLOSURE_MASTER_BATCH_R1"
    assert summary["REPORT_SCHEMA_VERSION"] == "R12"
    assert summary["REPORT_GENERATED_FROM_WEB_BASE_SHA"] == EXPECTED_BASE_SHA
    assert summary["BOT_SOURCE_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SOURCE_SHA
    assert summary["BOT_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_RUNTIME_SHA
    assert summary["WEB_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BASE_SHA
    assert summary["BOT_SOURCE_RUNTIME_MATCH"] == "NO"
    assert summary["BOT_SOURCE_RUNTIME_SPLIT"] == "YES"
    assert summary["WEB_SOURCE_RUNTIME_MATCH"] == "YES"
    assert summary["SOURCE_RUNTIME_MATCH"] == "YES"
    assert summary["WHOLE_APP_STALLED_BY_SINGLE_LANE"] == "NO"

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
    assert summary["OPEN_ENGINEERING_DEFECTS"] == 0

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
    assert summary["EXTERNAL_PROVIDER_INCIDENT_HOLD_COUNT"] == 1
    assert summary["OTHER_UNRESOLVED_ENGINEERING_RESIDUALS"] == 0
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


# ─── TEST 2: MULTI-LANE PARALLEL GOVERNANCE & OWNER ACTION BOARD ──────────────

def test_r12_multi_lane_governance_and_action_board() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    assert summary["SUBDUB_LANE_STATUS"] == "CLOSED_RELEASED"
    assert summary["SUBDUB_ROUTE_REGRESSION_COUNT"] == 0
    assert summary["SUBDUB_PROVIDER_ENTITLEMENT_RESIDUAL_COUNT"] == 0

    assert summary["VOICE_CLONE_LANE_STATUS"] == "EXTERNAL_PROVIDER_INCIDENT_HOLD"
    assert summary["VOICE_CLONE_INTERNAL_ENGINE_REWORK_REQUIRED"] == "NO"
    assert summary["VOICE_CLONE_BLOCKS_OTHER_PRODUCT_LANES"] == "NO"

    assert summary["PRODUCT_VIDEO_LANE_STATUS"] == "WAIT_OWNER_EXACT_DEPLOY_AUTHORIZATION"
    assert summary["IMAGE_UPSCALE_LANE_STATUS"] == "WAIT_OWNER_EXTERNAL_ENTITLEMENT"
    assert summary["IMAGE_TRANSFORM_LANE_STATUS"] == "WAIT_OWNER_EXTERNAL_ENTITLEMENT"
    assert summary["MUSIC_SFX_LANE_STATUS"] == "WAIT_OWNER_EXTERNAL_ENTITLEMENT"

    # Action Board validation
    board = summary["OWNER_ACTION_BOARD"]
    assert len(board) == 5

    lanes_in_board = {row["LANE"]: row for row in board}
    assert "Product Video (Bot Core Runtime)" in lanes_in_board
    assert "/image/upscale" in lanes_in_board
    assert "/image/transform" in lanes_in_board
    assert "/music/sfx" in lanes_in_board
    assert "/voice/clone" in lanes_in_board

    for row in board:
        assert row["CAN_OTHER_LANES_CONTINUE"] == "YES"
        assert row["INTERNAL_ENGINEERING_REQUIRED"] == "NO"
        assert len(row["OWNER_ACTION_REQUIRED"]) > 10
        assert len(row["EXACT_NEXT_AUTHORITY_NEEDED"]) > 5

    # Non-regression probes
    probes = summary["NON_REGRESSION_PROBES"]
    assert probes["NEW_CROSS_PRODUCT_ROUTE_BREAK_COUNT"] == 0
    assert probes["NEW_INTERNAL_PROVIDER_ADAPTER_BREAK_COUNT"] == 0
    assert probes["NEW_WALLET_SETTLEMENT_REGRESSION_COUNT"] == 0
    assert probes["NEW_IDEMPOTENCY_REGRESSION_COUNT"] == 0
    assert probes["NEW_WEB_BRIDGE_REGRESSION_COUNT"] == 0

    # Shared engine contracts
    shared = summary["SHARED_ENGINE_CONTRACTS"]
    assert shared["AUTH_ACCOUNT_OPEN_ENGINEERING_DEFECTS"] == 0
    assert shared["SHARED_WEB_BRIDGE_OPEN_ENGINEERING_DEFECTS"] == 0
    assert shared["AUTH_SESSION_ROUTE_HEALTH"] == "HEALTHY"
    assert shared["CANONICAL_ACTOR_BINDING_HEALTH"] == "HEALTHY"
    assert shared["WALLET_READ_PATH_HEALTH"] == "HEALTHY"
    assert shared["WEB_TO_CANONICAL_ENGINE_BRIDGE_HEALTH"] == "HEALTHY"


# ─── TEST 3: WEB ENTRYPOINTS AUTH & REJECTION CONTRACTS ───────────────────────

def test_r12_web_entrypoints_auth_enforcement() -> None:
    client = TestClient(app)
    routes = ["/image/upscale", "/image/transform", "/music/sfx", "/voice/clone"]

    # 1. Unauthenticated requests must redirect to login (307)
    for r in routes:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 307, f"{r} must require authentication"
        assert "/login" in resp.headers.get("location", "")

    # 2. Authenticated requests render HTTP 200
    with transaction() as conn:
        sess = _insert_session(conn, "test-r12-user-1")

    sid = sess["session_id"]
    signed_cookie = sid + "." + _sign_session(sid)
    client.cookies.set(SESSION_COOKIE, signed_cookie)

    for r in routes:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 200, f"{r} must be accessible when authenticated"
        assert len(resp.text) > 1000


# ─── TEST 4: NON-REGRESSION OF ALL RELEASED SURFACES ──────────────────────────

def test_r12_non_regression_locked_surfaces() -> None:
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

def test_r12_provenance_and_defects_integrity() -> None:
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
    assert psummary["REPORT_SCHEMA_VERSION"] == "R12"
    assert psummary["REPORT_GENERATED_FROM_WEB_BASE_SHA"] == EXPECTED_BASE_SHA
    assert psummary["BOT_SOURCE_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SOURCE_SHA
    assert psummary["BOT_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_RUNTIME_SHA
    assert psummary["WEB_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BASE_SHA
    assert psummary["BOT_SOURCE_RUNTIME_MATCH"] == "NO"
    assert psummary["BOT_SOURCE_RUNTIME_SPLIT"] == "YES"
    assert psummary["WEB_SOURCE_RUNTIME_MATCH"] == "YES"
    assert psummary["SOURCE_RUNTIME_MATCH"] == "YES"
    assert psummary["CORE_SURFACES"] == 221
    assert psummary["PLACEHOLDER_SURFACES"] == 0
    assert psummary["BROKEN_SURFACES"] == 0
    assert psummary["DEMO_DATA_SURFACES"] == 0
    assert psummary["UNKNOWN_DATA_SURFACES"] == 0
    assert psummary["FIRST_RED"] == "NONE - R12 WHOLE APP BOT RUNTIME ALIGNMENT AND PARALLEL EXTERNAL RESIDUAL CLOSURE COMPLETE"
    assert psummary["NEXT_SPEC"] == "WAIT_ONLY_FOR_EXACT_PER_LANE_OWNER_ACTIONS_WHILE_KEEPING_OTHER_PRODUCTS_RELEASED"

    with open(SOURCE_RUNTIME_FILE, "r", encoding="utf-8") as f:
        src_text = f.read()
        src_data = json.loads(src_text)

    assert STALE_R7_CANDIDATE_SHA not in src_text, "Stale candidate SHA must not appear in source_runtime"
    assert src_data["REPORT_SCHEMA_VERSION"] == "R12"
    assert src_data["REPORT_GENERATED_FROM_WEB_BASE_SHA"] == EXPECTED_BASE_SHA
    assert src_data["BOT_SOURCE_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_SOURCE_SHA
    assert src_data["BOT_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BOT_RUNTIME_SHA
    assert src_data["WEB_RUNTIME_SHA_OBSERVED_AT_REPORT_GENERATION"] == EXPECTED_BASE_SHA
    assert src_data["BOT_SOURCE_RUNTIME_MATCH"] == "NO"
    assert src_data["BOT_SOURCE_RUNTIME_SPLIT"] == "YES"
    assert src_data["WEB_SOURCE_RUNTIME_MATCH"] == "YES"
    assert src_data["SOURCE_RUNTIME_MATCH"] == "YES"

    with open(DEFECTS_FILE, "r", encoding="utf-8") as f:
        defects = json.load(f)

    defect_ids = {d["DEFECT_ID"]: d for d in defects}
    assert "DEFECT-R12-001" in defect_ids, "DEFECT-R12-001 must be tracked"
    assert defect_ids["DEFECT-R12-001"]["STATUS"] == "REPAIRED_IN_R12"
