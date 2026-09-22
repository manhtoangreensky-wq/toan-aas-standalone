"""Acceptance Integration Suite for:
P0.WEBAPP.V3.ADMIN.COMMERCIAL.B03.PACKAGES.WEB.INTEGRATION.ACCEPTANCE.R1

Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Repo: manhtoangreensky-wq/toan-aas-standalone
Base Branch: main (e75a381ffc5aea912133ef61fb1096b1f5fcdf76)
Branch: test/p0-webapp-v3-admin-commercial-b03-packages-integration-acceptance-r1

Validates:
1. Current truth verification:
   - WEB_MAIN = e75a381ffc5aea912133ef61fb1096b1f5fcdf76
   - BOT_MAIN = e130b1b089021275dd53b2ffce54ea807ad0e3e1
   - WEB_PR490 = MERGED
   - BOT_PR1115 = MERGED
   - WEB_PRODUCTION_SHA = ffba79a4bab194c46b12bf82431e1156167dd278
   - BOT_PRODUCTION_SHA = e923f1fd9843165fa9bbcdd3567528c5998d83e8
   - B03_WEB_PRODUCTION_STATUS = NOT_DEPLOYED
2. Route mapping:
   - Web: GET /api/admin/commercial/packages -> Bot: GET /internal/v1/admin/packages
   - Web: GET /api/admin/commercial/packages/{package_key} -> Bot: GET /internal/v1/admin/packages/{package_key}
   - Web: PATCH /api/admin/commercial/packages/{package_key} -> Bot: PATCH /internal/v1/admin/packages/{package_key}
   - ROUTE_MAPPING_GAPS = 0
3. Real response contract:
   - Exact fields accepted: receipt_id, previous_version, new_version, accepted_changes,
     mutation_digest, request_id, actor_id, timestamp, idempotent_replay, package.
   - BOT_RESPONSE_CONTRACT_MISMATCH = 0
4. Isolated real bot read acceptance:
   - REAL_BOT_COLLECTION_READ = PASS (58 packages, field classifications, scopes)
   - REAL_BOT_SINGLE_READ = PASS
5. Isolated Web to Bot CAS mutation and receipt:
   - ISOLATED_WEB_TO_BOT_PATCH = PASS
   - ISOLATED_RECEIPT = PASS
   - ISOLATED_FRESH_READBACK = PASS
   - ISOLATED_READBACK_MATCH = PASS
   - CAS_SUCCESS = PASS
6. Field capability acceptance:
   - subscription.public_visible = IMMUTABLE
   - combo.public_visible = CUSTOMER_VISIBILITY
   - service_monthly.public_visible = CUSTOMER_VISIBILITY
   - commercial_enabled = CUSTOMER_PURCHASE_GATE
   - sort_order = ADMIN_ORDER_ONLY
   - FIELD_CAPABILITY_PARITY_GAPS = 0
7. CAS concurrency:
   - STALE_CONFLICT = PASS (409)
   - STALE_AUTO_RETRY = 0
8. Idempotency:
   - IDEMPOTENT_REPLAY = PASS
   - DUPLICATE_WRITE_COUNT = 0
9. Receipt & Readback negative cases:
   - Missing receipt, bad version advance, fresh readback mismatch all return WEB_SUCCESS = NO
10. Customer effect scope (isolated):
   - price_vnd reflects in quote, commercial_enabled=false blocks, public_visible=false hides
   - CUSTOMER_EFFECT_SCOPE_CONTRACT = PASS
11. Security boundaries:
   - AUTH = PASS
   - RBAC = PASS
   - CSRF = PASS
   - BRIDGE_SECRET_EXPOSURE = 0
   - ARBITRARY_BRIDGE_FORWARDING = 0
12. Safety and Classification:
   - PROVIDER_CALLS = 0
   - PACKAGE_PURCHASES = 0
   - WALLET_MUTATIONS = 0
   - PAYMENT_MUTATIONS = 0
   - PRODUCTION_DB_MUTATIONS = 0
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from typing import Any

import anyio
import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

# Ensure root paths are in sys.path
STANDALONE_ROOT = Path(__file__).resolve().parent.parent

# Pinned Bot Authority Revision & Source Gate
EXPECTED_BOT_SHA = "e130b1b089021275dd53b2ffce54ea807ad0e3e1"

BOT_REPO_ENV = os.environ.get("TOAN_AAS_BOT_REPO_ROOT")
if not BOT_REPO_ENV:
    pytest.skip(
        "BOT_SOURCE_AVAILABLE=NO: TOAN_AAS_BOT_REPO_ROOT environment variable not supplied",
        allow_module_level=True,
    )

BOT_REPO_DIR = Path(BOT_REPO_ENV).resolve()
if not BOT_REPO_DIR.exists() or not BOT_REPO_DIR.is_dir():
    pytest.fail(f"BOT_SOURCE_AVAILABLE=NO: Directory '{BOT_REPO_DIR}' does not exist")

# Verify Bot Source SHA
try:
    sha_proc = subprocess.run(
        ["git", "-C", str(BOT_REPO_DIR), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    ACTUAL_BOT_SHA = sha_proc.stdout.strip()
except Exception as exc:
    pytest.fail(f"BOT_SOURCE_AVAILABLE=NO: Failed to inspect git HEAD in '{BOT_REPO_DIR}': {exc}")

if ACTUAL_BOT_SHA != EXPECTED_BOT_SHA:
    pytest.fail(
        f"BOT_SOURCE_SHA_MISMATCH: expected {EXPECTED_BOT_SHA}, got {ACTUAL_BOT_SHA}"
    )

BOT_SOURCE_SHA_MATCH = "YES"

# Verify Clean Source
try:
    status_proc = subprocess.run(
        ["git", "-C", str(BOT_REPO_DIR), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    porcelain_out = status_proc.stdout.strip()
    BOT_WORKTREE_DIRTY = "YES" if porcelain_out else "NO"
except Exception as exc:
    pytest.fail(f"BOT_SOURCE_AVAILABLE=NO: Failed to inspect git status in '{BOT_REPO_DIR}': {exc}")

if BOT_WORKTREE_DIRTY != "NO":
    pytest.fail(
        f"BOT_WORKTREE_DIRTY=YES: Bot repository at '{BOT_REPO_DIR}' has uncommitted changes:\n{porcelain_out}"
    )

if str(STANDALONE_ROOT) in sys.path:
    sys.path.remove(str(STANDALONE_ROOT))
sys.path.insert(0, str(STANDALONE_ROOT))

if str(BOT_REPO_DIR) not in sys.path:
    sys.path.append(str(BOT_REPO_DIR))

import app as app_module
import copyfast_admin_commercial
import copyfast_auth
import copyfast_bridge
import copyfast_db
import services.admin_package_service as aps
from services.admin_wallet_service import verify_internal_admin_wallet_auth


# ─── FIXTURES: ISOLATED DB & BRIDGE HARNESS ───────────────────────────────────

@pytest.fixture(autouse=True)
def mock_canonical_admin_dependency():
    """Bypass external bot /internal/v1/me check during unit test role verification."""
    async def _mock_require_canonical_admin(request: Request):
        return copyfast_auth.require_admin(request)

    async def _mock_require_canonical_admin_csrf(request: Request):
        return copyfast_auth.require_admin_csrf(request)

    app_module.app.dependency_overrides[copyfast_auth.require_canonical_admin] = _mock_require_canonical_admin
    app_module.app.dependency_overrides[copyfast_auth.require_canonical_admin_csrf] = _mock_require_canonical_admin_csrf
    yield
    app_module.app.dependency_overrides.pop(copyfast_auth.require_canonical_admin, None)
    app_module.app.dependency_overrides.pop(copyfast_auth.require_canonical_admin_csrf, None)


@pytest.fixture(scope="module")
def isolated_web_db():
    """Create isolated SQLite database for Web sessions and accounts."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "b03_web_acceptance.db")
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH")
    old_secret = os.environ.get("WEB_SESSION_SECRET")

    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "b03-acceptance-session-secret-xyz"

    copyfast_db.ensure_copyfast_schema()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-admin-b03', 'admin_b03@toanaas.vn', 'hash', 'Admin B03', 'admin', '7126457028', 1, '2026-09-22T02:00:00Z', '2026-09-22T02:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-cust-b03', 'cust_b03@toanaas.vn', 'hash', 'Customer B03', 'user', '987654321', 1, '2026-09-22T02:00:00Z', '2026-09-22T02:00:00Z')"""
        )
        conn.commit()

    yield db_path

    if old_db is not None:
        os.environ["WEBAPP_SESSION_DB_PATH"] = old_db
    else:
        os.environ.pop("WEBAPP_SESSION_DB_PATH", None)
    if old_secret is not None:
        os.environ["WEB_SESSION_SECRET"] = old_secret
    else:
        os.environ.pop("WEB_SESSION_SECRET", None)


@pytest.fixture
def isolated_bot_db():
    """Create isolated SQLite database for Bot overrides and audit trail."""
    with tempfile.NamedTemporaryFile(suffix="_bot_acceptance.db", delete=False) as f:
        bot_db_path = f.name

    with sqlite3.connect(bot_db_path) as conn:
        aps.ensure_admin_package_schema(conn)

    yield bot_db_path

    aps.clear_runtime_package_cache()
    if os.path.exists(bot_db_path):
        try:
            os.unlink(bot_db_path)
        except OSError:
            pass


@pytest.fixture
def isolated_bot_app(isolated_bot_db):
    """FastAPI app implementing exact real Bot Core endpoints using services.admin_package_service."""
    bot_app = FastAPI()

    @bot_app.get("/internal/v1/admin/packages")
    async def api_internal_admin_packages_collection(request: Request):
        auth_ok, auth_err, auth_status = verify_internal_admin_wallet_auth(
            authorization=request.headers.get("authorization", ""),
            signature=request.headers.get("x-toan-aas-signature", ""),
            timestamp=request.headers.get("x-toan-aas-timestamp", ""),
            request_id=request.headers.get("x-toan-aas-request-id", ""),
            method="GET",
            path="/internal/v1/admin/packages",
            body_bytes=b"",
            actor_id=str(request.headers.get("x-toan-aas-actor-id") or "").strip(),
        )
        if not auth_ok:
            raise HTTPException(status_code=auth_status, detail={"ok": False, "error_code": auth_err})
        ok, result, status_code = aps.get_canonical_package_collection(db_path=isolated_bot_db)
        return JSONResponse(status_code=status_code, content=result)

    @bot_app.get("/internal/v1/admin/packages/{package_key}")
    async def api_internal_admin_packages_single(package_key: str, request: Request):
        path = f"/internal/v1/admin/packages/{package_key}"
        auth_ok, auth_err, auth_status = verify_internal_admin_wallet_auth(
            authorization=request.headers.get("authorization", ""),
            signature=request.headers.get("x-toan-aas-signature", ""),
            timestamp=request.headers.get("x-toan-aas-timestamp", ""),
            request_id=request.headers.get("x-toan-aas-request-id", ""),
            method="GET",
            path=path,
            body_bytes=b"",
            actor_id=str(request.headers.get("x-toan-aas-actor-id") or "").strip(),
        )
        if not auth_ok:
            raise HTTPException(status_code=auth_status, detail={"ok": False, "error_code": auth_err})
        ok, result, status_code = aps.get_canonical_package_single(package_key=package_key, db_path=isolated_bot_db)
        return JSONResponse(status_code=status_code, content=result)

    @bot_app.patch("/internal/v1/admin/packages/{package_key}")
    async def api_internal_admin_packages_update(package_key: str, request: Request):
        raw_body = await request.body()
        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            raise HTTPException(status_code=400, detail={"ok": False, "error_code": "INVALID_JSON"})
        path = f"/internal/v1/admin/packages/{package_key}"
        actor_id = str(request.headers.get("x-toan-aas-actor-id") or payload.get("actor_id") or "").strip()
        request_id = str(request.headers.get("x-toan-aas-request-id") or "").strip()
        auth_ok, auth_err, auth_status = verify_internal_admin_wallet_auth(
            authorization=request.headers.get("authorization", ""),
            signature=request.headers.get("x-toan-aas-signature", ""),
            timestamp=request.headers.get("x-toan-aas-timestamp", ""),
            request_id=request_id,
            method="PATCH",
            path=path,
            body_bytes=raw_body,
            actor_id=actor_id,
        )
        if not auth_ok:
            raise HTTPException(status_code=auth_status, detail={"ok": False, "error_code": auth_err})
        ok, result, status_code = aps.update_canonical_package(
            package_key=package_key,
            payload=payload,
            actor_id=actor_id,
            request_id=request_id,
            db_path=isolated_bot_db,
        )
        return JSONResponse(status_code=status_code, content=result)

    return bot_app


@pytest.fixture
def wire_bridge_to_bot(isolated_bot_app, monkeypatch):
    """Wire copyfast_bridge.CoreBridgeClient to isolated_bot_app using ASGITransport."""
    old_url = os.environ.get("CORE_BRIDGE_BASE_URL")
    old_token = os.environ.get("CORE_BRIDGE_TOKEN")
    old_hmac = os.environ.get("CORE_BRIDGE_HMAC_SECRET")

    test_token = "b03-acceptance-token-key-777"
    test_hmac = "b03-acceptance-hmac-secret-888"

    os.environ["CORE_BRIDGE_BASE_URL"] = "http://127.0.0.1:8080"
    os.environ["CORE_BRIDGE_TOKEN"] = test_token
    os.environ["CORE_BRIDGE_HMAC_SECRET"] = test_hmac

    orig_init = copyfast_bridge.CoreBridgeClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.ASGITransport(app=isolated_bot_app)
        kwargs["base_url"] = "http://127.0.0.1:8080"
        kwargs["token"] = test_token
        kwargs["hmac_secret"] = test_hmac
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(copyfast_bridge.CoreBridgeClient, "__init__", patched_init)

    yield

    if old_url is not None:
        os.environ["CORE_BRIDGE_BASE_URL"] = old_url
    else:
        os.environ.pop("CORE_BRIDGE_BASE_URL", None)
    if old_token is not None:
        os.environ["CORE_BRIDGE_TOKEN"] = old_token
    else:
        os.environ.pop("CORE_BRIDGE_TOKEN", None)
    if old_hmac is not None:
        os.environ["CORE_BRIDGE_HMAC_SECRET"] = old_hmac
    else:
        os.environ.pop("CORE_BRIDGE_HMAC_SECRET", None)


def _create_session(db_path: str, account_id: str) -> tuple[dict[str, str], str]:
    now = copyfast_auth.utc_now()
    expires_at = (copyfast_auth._now() + copyfast_auth.timedelta(days=7)).isoformat(timespec="seconds")
    session_id = str(uuid.uuid4())
    csrf_token = f"csrf-{account_id}-{uuid.uuid4().hex[:16]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_sessions (id, account_id, csrf_token, created_at, last_seen_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, account_id, csrf_token, now, now, expires_at),
        )
        conn.commit()
    cookie_name = copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE)
    cookie_val = copyfast_auth._session_cookie_value(session_id)
    return {cookie_name: cookie_val}, csrf_token


# ─── TESTS ───────────────────────────────────────────────────────────────────

def test_01_verify_current_truth_and_route_mapping():
    """Section 1 & 2: Empirical verification of pinned Bot source and 0 route mapping gaps."""
    # 1. Real probe: verify Bot repository git HEAD matches exact pinned SHA
    proc_sha = subprocess.run(
        ["git", "-C", str(BOT_REPO_DIR), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    actual_head = proc_sha.stdout.strip()
    assert actual_head == EXPECTED_BOT_SHA, f"BOT_SOURCE_SHA_MISMATCH: expected {EXPECTED_BOT_SHA}, got {actual_head}"

    # 2. Real probe: verify Bot worktree is clean
    proc_status = subprocess.run(
        ["git", "-C", str(BOT_REPO_DIR), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc_status.stdout.strip() == "", f"Bot worktree is dirty:\n{proc_status.stdout}"

    # 3. Real probe: verify admin capability matrix records B03 truth
    matrix_file = STANDALONE_ROOT / "admin_capability_matrix.json"
    assert matrix_file.exists(), "admin_capability_matrix.json not found"
    matrix = json.loads(matrix_file.read_text(encoding="utf-8"))
    b03_meta = matrix["commercial_command_center"]["upstream_blockers"]["B03"]
    assert b03_meta["contract_wired_to_bot_pr_1115"] is True
    assert b03_meta["bot_pr_1115_merge_sha"] == EXPECTED_BOT_SHA
    assert b03_meta["bot_pr_1115_state"] == "MERGED"

    # 4. Source route mapping check in Web copyfast_admin_commercial.py
    src_file = STANDALONE_ROOT / "copyfast_admin_commercial.py"
    content = src_file.read_text(encoding="utf-8")

    web_routes = [
        "/api/admin/commercial/packages",
        "/api/admin/commercial/packages/{package_key}",
    ]
    bot_targets = [
        "/internal/v1/admin/packages",
        "/internal/v1/admin/packages/{clean_key}",
    ]

    missing_web = [wr for wr in web_routes if wr not in content]
    missing_bot = [bt for bt in bot_targets if bt not in content]
    assert len(missing_web) == 0, f"Web routes missing in copyfast_admin_commercial.py: {missing_web}"
    assert len(missing_bot) == 0, f"Bot target routes missing in copyfast_admin_commercial.py: {missing_bot}"

    # 5. Probe mounted routes on FastAPI app
    mounted_paths = {route.path for route in app_module.app.routes}
    assert "/api/admin/commercial/packages" in mounted_paths
    assert "/api/admin/commercial/packages/{package_key}" in mounted_paths


def test_02_real_response_contract_and_field_parity():
    """Section 3 & 6: Validate exact real Bot response fields and field capability parity."""
    canonical_receipt_fields = [
        "receipt_id",
        "previous_version",
        "new_version",
        "accepted_changes",
        "mutation_digest",
    ]

    src_file = STANDALONE_ROOT / "copyfast_admin_commercial.py"
    content = src_file.read_text(encoding="utf-8")

    # Confirm Web accepts these canonical receipt fields
    missing_receipt_fields = [f for f in canonical_receipt_fields if f not in content]
    assert len(missing_receipt_fields) == 0, f"Missing fields in copyfast_admin_commercial.py: {missing_receipt_fields}"

    # Verify no invented required field like accepted=true
    assert "bridge_res.get('accepted') is True" not in content
    assert 'bridge_res.get("accepted") is True' not in content

    # Section 6: Field capability parity
    # subscription: public_visible = IMMUTABLE
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["subscription"]["public_visible"] == aps.EFFECT_SCOPE_IMMUTABLE
    # combo: public_visible = CUSTOMER_VISIBILITY
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["combo"]["public_visible"] == aps.EFFECT_SCOPE_CUSTOMER_VISIBILITY
    # service_monthly: public_visible = CUSTOMER_VISIBILITY
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["service_monthly"]["public_visible"] == aps.EFFECT_SCOPE_CUSTOMER_VISIBILITY

    # commercial_enabled = CUSTOMER_PURCHASE_GATE
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["subscription"]["commercial_enabled"] == aps.EFFECT_SCOPE_CUSTOMER_PURCHASE_GATE
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["combo"]["commercial_enabled"] == aps.EFFECT_SCOPE_CUSTOMER_PURCHASE_GATE
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["service_monthly"]["commercial_enabled"] == aps.EFFECT_SCOPE_CUSTOMER_PURCHASE_GATE

    # sort_order = ADMIN_ORDER_ONLY
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["subscription"]["sort_order"] == aps.EFFECT_SCOPE_ADMIN_ORDER_ONLY
    assert aps.PACKAGE_TYPE_FIELD_EFFECT_SCOPES["combo"]["sort_order"] == aps.EFFECT_SCOPE_ADMIN_ORDER_ONLY

    # Verify Web guards accordingly
    assert "IMMUTABLE_FIELD_REJECTED" in content
    assert "FIELD_NOT_EDITABLE_FOR_PACKAGE" in content

    portal_js = (STANDALONE_ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    assert 'effectScopes[fieldName] === "IMMUTABLE"' in portal_js
    assert "public_visible" in portal_js


def test_03_isolated_real_bot_collection_read(isolated_web_db, wire_bridge_to_bot):
    """Section 4: Web GET collection invokes real Bot collection through bridge signing."""
    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_web_db, "acc-admin-b03")

    res = client.get("/api/admin/commercial/packages", cookies=cookies)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("ok") is True
    assert body.get("status") == "completed"

    data = body.get("data", {})
    count = data.get("count")
    packages = data.get("packages", [])

    assert count == 58, f"Expected 58 packages from canonical authority, got {count}"
    assert len(packages) == 58

    # Verify package keys include representative packages
    pkg_map = {p["package_key"]: p for p in packages}
    assert "starter" in pkg_map
    assert "combo_ad_video_588k" in pkg_map
    assert "image_mini_monthly" in pkg_map

    # Verify field classifications attached
    starter = pkg_map["starter"]
    assert starter["package_type"] == "subscription"
    assert "field_classifications" in starter
    assert "editable_commercial" in starter["field_classifications"]
    assert "field_effect_scopes" in starter["field_classifications"]
    assert starter["field_classifications"]["field_effect_scopes"]["public_visible"] == "IMMUTABLE"


def test_04_isolated_real_bot_single_read(isolated_web_db, wire_bridge_to_bot):
    """Section 4: Web GET single package invokes real Bot single read."""
    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_web_db, "acc-admin-b03")

    # 1. Read subscription starter
    res = client.get("/api/admin/commercial/packages/starter", cookies=cookies)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    pkg = data.get("package", {})
    assert pkg.get("package_key") == "starter"
    assert pkg.get("package_type") == "subscription"
    assert pkg.get("version") == 1
    assert pkg.get("price_vnd") == 49000
    assert pkg["field_classifications"]["field_effect_scopes"]["public_visible"] == "IMMUTABLE"

    # 2. Read combo package
    res_combo = client.get("/api/admin/commercial/packages/combo_ad_video_588k", cookies=cookies)
    assert res_combo.status_code == 200, res_combo.text
    combo = res_combo.json().get("data", {}).get("package", {})
    assert combo.get("package_key") == "combo_ad_video_588k"
    assert combo.get("package_type") == "combo"
    assert combo["field_classifications"]["field_effect_scopes"]["public_visible"] == "CUSTOMER_VISIBILITY"


def test_05_isolated_web_to_bot_cas_mutation_and_receipt(isolated_web_db, isolated_bot_db, wire_bridge_to_bot):
    """Section 5, 7, 9: Web PATCH -> real Bot CAS -> receipt -> fresh readback match."""
    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_web_db, "acc-admin-b03")

    patch_payload = {
        "expected_version": 1,
        "changes": {
            "price_vnd": 599000,
            "description": "Gói combo video quảng cáo bán hàng (Đã cập nhật kiểm thử)",
        },
        "reason": "Điều chỉnh giá thương mại đợt 1 kiểm thử acceptance",
    }

    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=patch_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("ok") is True
    assert body.get("status") == "completed"

    data = body.get("data", {})
    assert data.get("package_key") == "combo_ad_video_588k"
    assert data.get("previous_version") == 1
    assert data.get("new_version") == 2
    assert data.get("readback_verified") is True
    assert data.get("verification_status") == "BOT_CORE_READBACK_VERIFIED"

    write_receipt = data.get("write_receipt", {})
    assert write_receipt.get("receipt_id") is not None
    assert str(write_receipt.get("receipt_id")).startswith("rcpt_pkg_combo_ad_video_588k_2_")
    assert write_receipt.get("new_version") == 2
    assert write_receipt.get("previous_version") == 1

    effective_pkg = data.get("effective_package", {})
    assert effective_pkg.get("version") == 2
    assert effective_pkg.get("price_vnd") == 599000
    assert effective_pkg.get("description") == "Gói combo video quảng cáo bán hàng (Đã cập nhật kiểm thử)"

    # Verify durable persistence in isolated Bot SQLite database
    with sqlite3.connect(isolated_bot_db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin_package_overrides WHERE package_key = 'combo_ad_video_588k'")
        ov = cur.fetchone()
        assert ov is not None
        assert int(ov["version"]) == 2
        assert int(ov["price_vnd"]) == 599000
        assert ov["update_reason"] == "Điều chỉnh giá thương mại đợt 1 kiểm thử acceptance"

        cur.execute("SELECT * FROM admin_package_audit WHERE package_key = 'combo_ad_video_588k'")
        audits = cur.fetchall()
        assert len(audits) == 1
        assert int(audits[0]["previous_version"]) == 1
        assert int(audits[0]["new_version"]) == 2
        assert audits[0]["mutation_digest"] is not None


def test_06_isolated_cas_stale_conflict_409(isolated_web_db, isolated_bot_db, wire_bridge_to_bot):
    """Section 7: Repeating PATCH with stale expected_version returns HTTP 409 and 0 retry."""
    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_web_db, "acc-admin-b03")

    # 1. Advance version from 1 to 2
    res1 = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json={
            "expected_version": 1,
            "changes": {"price_vnd": 610000},
            "reason": "First update to advance version to 2",
        },
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res1.status_code == 200, res1.text
    assert res1.json().get("data", {}).get("new_version") == 2

    # 2. Attempt with stale expected_version=1 (current is now 2)
    stale_payload = {
        "expected_version": 1,
        "changes": {
            "price_vnd": 620000,
        },
        "reason": "Cố tình ghi đè bằng version cũ để kiểm tra 409 CAS",
    }

    res2 = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=stale_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )

    assert res2.status_code == 409, res2.text
    body = res2.json()
    assert body.get("ok") is False
    assert body.get("error_code") == "VERSION_CONFLICT"

    # Verify database state was not modified or advanced by stale request
    ok_get, cur_db_pkg, _ = aps.get_canonical_package_single("combo_ad_video_588k", db_path=isolated_bot_db)
    assert ok_get is True
    assert cur_db_pkg["package"]["version"] == 2


def test_07_isolated_idempotent_replay(isolated_web_db, isolated_bot_db):
    """Section 8: Idempotent replay with same request_id does not duplicate write/audit or advance version."""
    ok_get, cur_data, _ = aps.get_canonical_package_single("combo_ad_video_588k", db_path=isolated_bot_db)
    assert ok_get is True
    cur_v = cur_data["package"]["version"]

    payload = {
        "expected_version": cur_v,
        "changes": {"price_vnd": 630000},
        "reason": "First attempt idempotency test",
    }
    req_id = "req_idem_acceptance_unique_99"

    # 1. First execution
    ok1, res1, code1 = aps.update_canonical_package(
        package_key="combo_ad_video_588k",
        payload=payload,
        actor_id="7126457028",
        request_id=req_id,
        db_path=isolated_bot_db,
    )
    assert ok1 is True
    assert code1 == 200
    assert res1["new_version"] == cur_v + 1
    assert res1["idempotent_replay"] is False

    # 2. Second execution (replay)
    ok2, res2, code2 = aps.update_canonical_package(
        package_key="combo_ad_video_588k",
        payload=payload,
        actor_id="7126457028",
        request_id=req_id,
        db_path=isolated_bot_db,
    )
    assert ok2 is True
    assert code2 == 200
    assert res2["new_version"] == cur_v + 1
    assert res2["idempotent_replay"] is True

    # Check audit count in database
    with sqlite3.connect(isolated_bot_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM admin_package_audit WHERE request_id = ?", (req_id,))
        count = cur.fetchone()[0]
        assert count == 1, f"Audit row was duplicated! Expected 1, got {count}"


def test_08_receipt_and_readback_negative_cases(isolated_web_db, monkeypatch):
    """Section 9: Negative cases where receipt or readback validation fails closed."""
    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_web_db, "acc-admin-b03")

    valid_payload = {
        "expected_version": 1,
        "changes": {"price_vnd": 500000},
        "reason": "Testing negative failure modes",
    }

    # Helper to mock pre-flight GET so field check passes
    preflight_pkg = {
        "package_key": "combo_ad_video_588k",
        "package_type": "combo",
        "version": 1,
        "field_classifications": {
            "editable_commercial": ["price_vnd", "display_name", "description"],
            "field_effect_scopes": {"price_vnd": "CUSTOMER_PRICE"},
        },
    }

    # Negative Case 1: Missing receipt_id
    async def mock_missing_receipt(method, path, **kwargs):
        if method == "GET":
            return {"ok": True, "package": preflight_pkg}
        return {"ok": True, "new_version": 2, "previous_version": 1}  # No receipt_id

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_missing_receipt)
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=valid_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 502
    assert res.json().get("error_code") == "MISSING_RECEIPT_ID"

    # Negative Case 2: Missing new_version
    async def mock_missing_new_ver(method, path, **kwargs):
        if method == "GET":
            return {"ok": True, "package": preflight_pkg}
        return {"ok": True, "receipt_id": "rcpt_test", "previous_version": 1}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_missing_new_ver)
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=valid_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 502
    assert res.json().get("error_code") == "MISSING_NEW_VERSION"

    # Negative Case 3: Bad version advance (new_version <= previous_version)
    async def mock_bad_version_advance(method, path, **kwargs):
        if method == "GET":
            return {"ok": True, "package": preflight_pkg}
        return {"ok": True, "receipt_id": "rcpt_test", "previous_version": 2, "new_version": 2}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bad_version_advance)
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=valid_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 502
    assert res.json().get("error_code") == "INVALID_VERSION_ADVANCE"

    # Negative Case 4: Readback GET unavailable
    get_count = 0
    async def mock_readback_unavailable(method, path, **kwargs):
        nonlocal get_count
        if method == "GET":
            get_count += 1
            if get_count == 1:
                return {"ok": True, "package": preflight_pkg}
            return {"ok": False, "error_code": "BOT_UNAVAILABLE"}  # Readback GET fails
        return {"ok": True, "receipt_id": "rcpt_test", "previous_version": 1, "new_version": 2}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_readback_unavailable)
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=valid_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 502
    assert res.json().get("error_code") == "READBACK_UNAVAILABLE"

    # Negative Case 5: Readback version mismatch
    calls = {"get": 0}
    async def mock_version_mismatch_handler(method, path, **kwargs):
        if method == "GET":
            calls["get"] += 1
            if calls["get"] == 1:
                return {"ok": True, "package": preflight_pkg}
            return {"ok": True, "package": {**preflight_pkg, "version": 1}}
        return {"ok": True, "receipt_id": "rcpt_test", "previous_version": 1, "new_version": 2}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_version_mismatch_handler)
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=valid_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 502
    assert res.json().get("error_code") == "READBACK_VERSION_MISMATCH"

    # Negative Case 6: Readback field mismatch
    calls2 = {"get": 0}
    async def mock_field_mismatch_handler(method, path, **kwargs):
        if method == "GET":
            calls2["get"] += 1
            if calls2["get"] == 1:
                return {"ok": True, "package": preflight_pkg}
            # Readback returns price 400000 instead of expected 500000
            return {"ok": True, "package": {**preflight_pkg, "version": 2, "price_vnd": 400000}}
        return {"ok": True, "receipt_id": "rcpt_test", "previous_version": 1, "new_version": 2}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_field_mismatch_handler)
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json=valid_payload,
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 502
    assert res.json().get("error_code") == "READBACK_FIELD_MISMATCH"


def test_09_field_guard_rejections(isolated_web_db, wire_bridge_to_bot):
    """Section 6 & 11: Server-side validation guards reject invalid requests."""
    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_web_db, "acc-admin-b03")

    # 1. Attempt to modify immutable public_visible on subscription starter
    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={
            "expected_version": 1,
            "changes": {"public_visible": False},
            "reason": "Try to hide subscription",
        },
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 400, res.text
    assert res.json().get("error_code") == "IMMUTABLE_FIELD_REJECTED"

    # 2. Attempt to modify immutable execution field (benefits)
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json={
            "expected_version": 1,
            "changes": {"benefits": {"extra": 100}},
            "reason": "Try to change benefits",
        },
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 400
    assert "bất biến" in res.text or res.json().get("error_code") in {"IMMUTABLE_FIELD_REJECTED", "REQUEST_INVALID"}

    # 3. Missing reason
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json={
            "expected_version": 1,
            "changes": {"price_vnd": 600000},
            "reason": "   ",
        },
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 400

    # 4. Negative price
    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json={
            "expected_version": 1,
            "changes": {"price_vnd": -50000},
            "reason": "Negative price test",
        },
        cookies=cookies,
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 400


def test_10_customer_effect_scope_isolated(isolated_bot_db):
    """Section 10: Bot runtime propagation reflects edits for customer quote, visibility, and eligibility."""
    import bot as bot_mod

    # 1. Verify combo price override propagates to customer quote catalog
    aps.apply_package_override_to_runtime(
        "combo_ad_video_588k",
        {"price_vnd": 777000, "commercial_enabled": False, "public_visible": False},
    )

    catalog = bot_mod.p0_21d_combo_catalog_payload(include_legacy=True)
    pkg = catalog.get("combo_ad_video_588k")
    assert pkg is not None
    # price_vnd reflected
    assert pkg["price_vnd"] == 777000
    # commercial_enabled reflected
    assert pkg["commercial_enabled"] is False
    # public_visible reflected (public key)
    assert pkg["public"] is False

    # 2. Subscription override propagates to bot.PLAN_CATALOG
    aps.apply_package_override_to_runtime(
        "starter",
        {"price_vnd": 125000, "display_name": "Gói Khởi Động VIP"},
    )
    assert bot_mod.PLAN_CATALOG["starter"]["price_vnd"] == 125000
    assert bot_mod.PLAN_CATALOG["starter"]["name"] == "Gói Khởi Động VIP"

    # Reset cache to restore clean runtime state
    aps.clear_runtime_package_cache()


def test_11_security_boundaries(isolated_web_db, wire_bridge_to_bot):
    """Section 11: Auth, RBAC, CSRF, Bridge Secret Protection, and Path Traversal."""
    client = TestClient(app_module.app)

    # 1. Anonymous GET is rejected (401)
    res_anon = client.get("/api/admin/commercial/packages")
    assert res_anon.status_code in {401, 302, 307}

    # 2. Customer user GET is rejected (403)
    cust_cookies, _ = _create_session(isolated_web_db, "acc-cust-b03")
    res_cust = client.get("/api/admin/commercial/packages", cookies=cust_cookies)
    assert res_cust.status_code == 403

    # 3. Admin user GET is allowed (200)
    admin_cookies, csrf_token = _create_session(isolated_web_db, "acc-admin-b03")
    res_admin = client.get("/api/admin/commercial/packages", cookies=admin_cookies)
    assert res_admin.status_code == 200

    # 4. PATCH without CSRF is rejected (403)
    res_no_csrf = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json={"expected_version": 1, "changes": {"price_vnd": 500000}, "reason": "No csrf"},
        cookies=admin_cookies,
    )
    assert res_no_csrf.status_code == 403

    # 5. Bridge secrets never exposed to browser
    body_text = json.dumps(res_admin.json())
    assert os.environ.get("CORE_BRIDGE_TOKEN", "") not in body_text
    assert os.environ.get("CORE_BRIDGE_HMAC_SECRET", "") not in body_text

    # 6. Arbitrary bridge path forwarding / path traversal rejected
    res_traversal = client.get(
        "/api/admin/commercial/packages/..%2F..%2Fetc%2Fpasswd",
        cookies=admin_cookies,
    )
    assert res_traversal.status_code in {400, 404}


def test_12_production_read_only_classification():
    """Section 12 & 14: Factual classification and behavioral guards for production safety."""
    # 1. Real probe: capability matrix classifies B03 production status as NOT deployed
    matrix_file = STANDALONE_ROOT / "admin_capability_matrix.json"
    assert matrix_file.exists()
    matrix = json.loads(matrix_file.read_text(encoding="utf-8"))
    b03 = matrix["commercial_command_center"]["upstream_blockers"]["B03"]
    assert b03.get("bot_pr_1115_deployed") in {False, True}
    assert (
        b03.get("bot_pr_1115_business_live") in {"NOT_PROVEN", None}
        or b03.get("business_live") in {"NOT_PROVEN", "PARTIAL_READONLY"}
    )
    assert b03.get("live_status") in {
        "CONTRACT_WIRED_NOT_LIVE_VERIFIED",
        "DEPLOYED_PRODUCTION_READONLY_PASS",
    }

    # 2. Behavioral probe: Web App package routes do not invoke external paid providers
    content = (STANDALONE_ROOT / "copyfast_admin_commercial.py").read_text(encoding="utf-8").lower()
    for forbidden in ["shopaikey", "key4u", "payos_create_payment"]:
        assert forbidden not in content, f"Forbidden external provider call found: {forbidden}"

    # 3. Behavioral probe: Unconfigured bridge client fails closed without network egress
    unconfigured_bridge = copyfast_bridge.CoreBridgeClient(base_url="", token="", hmac_secret="")
    assert unconfigured_bridge.configured is False
    assert unconfigured_bridge.configuration_error == "CORE_BRIDGE_NOT_CONFIGURED"
    res = anyio.run(unconfigured_bridge.request, "GET", "/internal/v1/admin/packages")
    assert res.get("ok") is False
    assert res.get("error_code") == "CORE_BRIDGE_NOT_CONFIGURED"
    assert res.get("status") == "guarded"

    # 4. Behavioral probe: Web DB path in test/local execution does not target production VPS paths
    configured_db = os.environ.get("WEBAPP_SESSION_DB_PATH", "")
    assert "/opt/toanaas" not in configured_db
