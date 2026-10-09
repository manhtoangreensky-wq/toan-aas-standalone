"""Tests for R8 External Capability and Final Live Engine Closure runtime matrix contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from copyfast_auth import _insert_session, _sign_session, SESSION_COOKIE
from copyfast_db import ensure_copyfast_schema, transaction

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "webapp_full_product_truth"
MATRIX_FILE = REPORT_DIR / "R8_FINAL_ROUTE_RUNTIME_MATRIX.json"
PROVENANCE_FILE = REPORT_DIR / "00_data_provenance.json"
DEFECTS_FILE = REPORT_DIR / "defects.json"
SOURCE_RUNTIME_FILE = REPORT_DIR / "00_source_runtime.json"


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret-at-least-16-bytes-long")
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-r8-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r8-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('test-r8-user-1', 'user1@test.local', 'hash1', '2026-10-09T00:00:00Z', '2026-10-09T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-r8-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r8-%'")


# ─── TEST 1: MATRIX SUMMARY & TOTAL INTEGRITY ─────────────────────────────────

def test_r8_matrix_summary_and_surface_counts() -> None:
    assert MATRIX_FILE.exists(), "R8_FINAL_ROUTE_RUNTIME_MATRIX.json must exist"
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    routes = data["routes"]

    assert summary["BATCH"] == "WEBAPP_R8_EXTERNAL_CAPABILITY_AND_FINAL_LIVE_ENGINE_CLOSURE_MASTER_BATCH_R1"
    assert summary["TOTAL_SURFACES"] == 221
    assert len(routes) == 221

    assert summary["UNCLASSIFIED_ROUTE_COUNT"] == 0
    assert summary["UNKNOWN_RUNTIME_OWNER_COUNT"] == 0
    assert summary["UNKNOWN_DATA_OWNER_COUNT"] == 0
    assert summary["STALE_PROVENANCE_SHA_COUNT"] == 0

    assert summary["BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 0
    assert summary["WEB_BRIDGE_NOT_MOUNTED_COUNT"] == 0
    assert summary["BOT_ADAPTER_EXISTS_NOT_EXPOSED_TO_WEB_COUNT"] == 0
    assert summary["WORKER_CONSUMER_EXISTS_NOT_ACTIVATED_COUNT"] == 0
    assert summary["FALSE_BLOCK_WEB_NATIVE_RUNTIME_ALREADY_EXISTS_COUNT"] == 0
    assert summary["OUTPUT_DELIVERY_GAP_COUNT"] == 0

    # R8 terminal elimination of generic external capability bucket
    assert summary["GENERIC_EXTERNAL_CAPABILITY_BUCKET_ELIMINATED"] is True
    assert summary["EXTERNAL_PROVIDER_CAPABILITY_MISSING_COUNT"] == 0
    assert summary["BLOCKED_EXTERNAL_CAPABILITY_OR_GRANT_REQUIRED_COUNT"] == 0

    # R8 terminal counts for the four lanes
    assert summary["BLOCKED_PROVIDER_ENTITLEMENT_COUNT"] == 3
    assert summary["IMPLEMENTED_DEPLOYED_WAIT_OWNER_LIVE_GRANT_COUNT"] == 1
    assert summary["ACCOUNT_ENTITLEMENT_MISSING_COUNT"] == 3
    assert summary["OWNER_LIVE_GRANT_REQUIRED_COUNT"] == 1

    # Exact classification counts
    cc = summary["CLASSIFICATION_COUNTS"]
    assert cc["NOT_A_PRODUCT_ACTION_INFORMATIONAL_ONLY"] == 16
    assert cc["RELEASED_WEB_NATIVE_RUNTIME"] == 112
    assert cc["RELEASED_READ_ONLY_CANONICAL_COMPANION"] == 19
    assert cc["RELEASED_ACTIVE_CANONICAL_RUNTIME"] == 22
    assert cc["ADMIN_INTERNAL_ONLY"] == 48
    assert cc["BLOCKED_PROVIDER_ENTITLEMENT"] == 3
    assert cc["IMPLEMENTED_DEPLOYED_WAIT_OWNER_LIVE_GRANT"] == 1
    assert sum(cc.values()) == 221

    # Exact root gap counts
    rg = summary["ROOT_GAP_COUNTS"]
    assert rg["NOT_APPLICABLE_INFORMATIONAL"] == 16
    assert rg["NONE_RELEASED_RUNTIME"] == 153
    assert rg["ADMIN_INTERNAL_BOUNDARY"] == 48
    assert rg["ACCOUNT_ENTITLEMENT_MISSING"] == 3
    assert rg["OWNER_LIVE_GRANT_REQUIRED"] == 1
    assert sum(rg.values()) == 221


# ─── TEST 2: THE FOUR R8 LANES EXACT DISPOSITION ──────────────────────────────

def test_r8_all_four_lanes_exact_terminal_disposition() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    route_map = {r["route"]: r for r in data["routes"]}

    # Lane A: /image/upscale
    assert "/image/upscale" in route_map
    upscale = route_map["/image/upscale"]
    assert upscale["final_classification"] == "BLOCKED_PROVIDER_ENTITLEMENT"
    assert upscale["actual_root_gap"] == "ACCOUNT_ENTITLEMENT_MISSING"
    assert upscale["canonical_bot_engine_exists"] is False
    assert upscale["canonical_bot_adapter_exists"] is False
    assert upscale["runtime_execution_enabled"] is False

    # Lane B: /image/transform
    assert "/image/transform" in route_map
    transform = route_map["/image/transform"]
    assert transform["final_classification"] == "BLOCKED_PROVIDER_ENTITLEMENT"
    assert transform["actual_root_gap"] == "ACCOUNT_ENTITLEMENT_MISSING"
    assert transform["canonical_bot_engine_exists"] is False
    assert transform["canonical_bot_adapter_exists"] is False
    assert transform["runtime_execution_enabled"] is False

    # Lane C: /music/sfx
    assert "/music/sfx" in route_map
    sfx = route_map["/music/sfx"]
    assert sfx["final_classification"] == "BLOCKED_PROVIDER_ENTITLEMENT"
    assert sfx["actual_root_gap"] == "ACCOUNT_ENTITLEMENT_MISSING"
    assert sfx["canonical_bot_engine_exists"] is False
    assert sfx["canonical_bot_adapter_exists"] is False
    assert sfx["runtime_execution_enabled"] is False

    # Lane D: /voice/clone
    assert "/voice/clone" in route_map
    clone = route_map["/voice/clone"]
    assert clone["final_classification"] == "IMPLEMENTED_DEPLOYED_WAIT_OWNER_LIVE_GRANT"
    assert clone["actual_root_gap"] == "OWNER_LIVE_GRANT_REQUIRED"
    assert clone["canonical_bot_engine_exists"] is True
    assert clone["canonical_bot_adapter_exists"] is True
    assert clone["canonical_worker_consumer_exists"] is True
    assert clone["web_to_bot_bridge_exists"] is True
    assert clone["web_to_bot_bridge_mounted"] is True
    assert clone["canonical_pricing_authority_exists"] is True
    assert clone["canonical_job_ledger_exists"] is True
    assert clone["canonical_output_delivery_exists"] is True
    assert clone["runtime_execution_enabled"] is False


# ─── TEST 3: WEB ENTRYPOINTS AUTH & REJECTION CONTRACTS ───────────────────────

def test_r8_web_entrypoints_auth_enforcement() -> None:
    client = TestClient(app)
    routes = ["/image/upscale", "/image/transform", "/music/sfx", "/voice/clone"]

    # 1. Unauthenticated requests must redirect to login (307)
    for r in routes:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 307, f"{r} must require authentication"
        assert "/login" in resp.headers.get("location", "")

    # 2. Authenticated requests render HTTP 200
    with transaction() as conn:
        sess = _insert_session(conn, "test-r8-user-1")

    sid = sess["session_id"]
    signed_cookie = sid + "." + _sign_session(sid)
    client.cookies.set(SESSION_COOKIE, signed_cookie)

    for r in routes:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 200, f"{r} must be accessible when authenticated"
        assert len(resp.text) > 1000


# ─── TEST 4: NON-REGRESSION OF ALL R7 RELEASED SURFACES ───────────────────────

def test_r8_non_regression_locked_surfaces() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    route_map = {r["route"]: r for r in data["routes"]}

    # Non-regression surfaces from R7, R6, R5
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


# ─── TEST 5: PROVENANCE, DEFECTS & SOURCE RUNTIME INTEGRITY ───────────────────

def test_r8_provenance_and_defects_integrity() -> None:
    assert PROVENANCE_FILE.exists()
    assert DEFECTS_FILE.exists()
    assert SOURCE_RUNTIME_FILE.exists()

    with open(PROVENANCE_FILE, "r", encoding="utf-8") as f:
        prov = json.load(f)
    psummary = prov["summary"]
    assert psummary["SOURCE_RUNTIME_MATCH"] == "YES"
    assert psummary["CORE_SURFACES"] == 221
    assert psummary["PLACEHOLDER_SURFACES"] == 0
    assert psummary["BROKEN_SURFACES"] == 0
    assert psummary["DEMO_DATA_SURFACES"] == 0
    assert psummary["UNKNOWN_DATA_SURFACES"] == 0

    with open(DEFECTS_FILE, "r", encoding="utf-8") as f:
        defects = json.load(f)

    defect_ids = {d["DEFECT_ID"] for d in defects}
    assert "DEFECT-R8-001" in defect_ids, "DEFECT-R8-001 must be tracked"
    assert "DEFECT-R8-002" in defect_ids, "DEFECT-R8-002 must be tracked"
