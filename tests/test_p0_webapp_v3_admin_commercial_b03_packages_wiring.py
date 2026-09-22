"""First-Red and Green Contract Suite for:
P0.WEBAPP.V3.ADMIN.COMMERCIAL.B03.PACKAGES.WEB.WIRING.R1

Validates:
1. GET packages collection Web endpoint invokes exact Bot collection endpoint (/internal/v1/admin/packages).
2. GET single package invokes exact Bot single endpoint (/internal/v1/admin/packages/{package_key}).
3. PATCH sends exact: expected_version, changes, reason to Bot Core.
4. PATCH rejects missing/empty reason (HTTP 400).
5. PATCH rejects immutable identity and execution fields (HTTP 400).
6. PATCH rejects subscription public_visible modification (HTTP 400 - IMMUTABLE_FIELD_REJECTED).
7. PATCH rejects validation bounds (negative price, excessive length, etc.) (HTTP 400).
8. Successful Bot receipt followed by fresh GET readback.
9. UI/API success only after readback match (BOT_CORE_READBACK_VERIFIED).
10. Readback mismatch fails closed (READBACK_VERIFICATION_FAILED).
11. 409 causes zero PATCH replay (STALE_WRITE_AUTO_RETRY = 0).
12. Unauthorized Web user cannot call APIs (ANONYMOUS=401, CUSTOMER=403, ADMIN=200).
13. PATCH requires valid CSRF token.
14. Bridge secrets never enter response payload.
15. B01, B02, and B03 are CONTRACT_WIRED in capability matrix, B04-B05 remain FAIL_CLOSED.
16. portal.js contains canonical packages editor with CAS, readback, diff preview, conflict recovery.
17. portal.js packages subscription public_visible is rendered disabled/immutable.
18. portal.js blocker banner is removed when activeTab is packages.
19. No hardcoded dummy packagesList or internal PR jargon in visible UI.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid
from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

import app as app_module
import copyfast_auth
import copyfast_bridge
import copyfast_db


ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_MATRIX_PATH = ROOT / "admin_capability_matrix.json"
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"

MOCK_BOT_PACKAGES = [
    {
        "package_key": "starter",
        "package_type": "subscription",
        "display_name": "Gói Khởi động",
        "description": "Dành cho người mới bắt đầu",
        "price_vnd": 99000,
        "duration_days": 30,
        "benefits": {"xu": 500},
        "public_visible": True,
        "commercial_enabled": True,
        "sort_order": 10,
        "group": "subscription",
        "version": 1,
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
        "field_classifications": {
            "editable_commercial": ["commercial_enabled", "description", "display_name", "price_vnd", "sort_order"],
            "field_effect_scopes": {
                "display_name": "CUSTOMER_DISPLAY",
                "description": "CUSTOMER_DISPLAY",
                "price_vnd": "CUSTOMER_PRICE",
                "commercial_enabled": "CUSTOMER_PURCHASE_GATE",
                "sort_order": "ADMIN_ORDER_ONLY",
                "public_visible": "IMMUTABLE",
            },
            "immutable_identity": ["package_key", "package_type"],
            "immutable_execution": ["benefits", "duration_days", "required_member_tier", "group"],
            "immutable_financial_history": ["wallet_mutations", "historical_purchases"],
        },
    },
    {
        "package_key": "combo_ad_video_588k",
        "package_type": "combo",
        "display_name": "Combo Video Quảng Cáo 588K",
        "description": "Gói combo video quảng cáo bán hàng",
        "price_vnd": 588000,
        "duration_days": 30,
        "benefits": {"video_single": 5},
        "public_visible": True,
        "commercial_enabled": True,
        "sort_order": 50,
        "group": "combo",
        "version": 1,
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
        "field_classifications": {
            "editable_commercial": ["commercial_enabled", "description", "display_name", "price_vnd", "public_visible", "sort_order"],
            "field_effect_scopes": {
                "display_name": "CUSTOMER_DISPLAY",
                "description": "CUSTOMER_DISPLAY",
                "price_vnd": "CUSTOMER_PRICE",
                "public_visible": "CUSTOMER_VISIBILITY",
                "commercial_enabled": "CUSTOMER_PURCHASE_GATE",
                "sort_order": "ADMIN_ORDER_ONLY",
            },
            "immutable_identity": ["package_key", "package_type"],
            "immutable_execution": ["benefits", "duration_days", "required_member_tier", "group"],
            "immutable_financial_history": ["wallet_mutations", "historical_purchases"],
        },
    },
    {
        "package_key": "video_mini_monthly",
        "package_type": "service_monthly",
        "display_name": "Gói Video Mini Tháng",
        "description": "Gói dịch vụ video theo tháng",
        "price_vnd": 299000,
        "duration_days": 30,
        "benefits": {"video_single": 30},
        "public_visible": True,
        "commercial_enabled": True,
        "sort_order": 300,
        "group": "monthly",
        "version": 1,
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
        "field_classifications": {
            "editable_commercial": ["commercial_enabled", "description", "display_name", "price_vnd", "public_visible", "sort_order"],
            "field_effect_scopes": {
                "display_name": "CUSTOMER_DISPLAY",
                "description": "CUSTOMER_DISPLAY",
                "price_vnd": "CUSTOMER_PRICE",
                "public_visible": "CUSTOMER_VISIBILITY",
                "commercial_enabled": "CUSTOMER_PURCHASE_GATE",
                "sort_order": "ADMIN_ORDER_ONLY",
            },
            "immutable_identity": ["package_key", "package_type"],
            "immutable_execution": ["benefits", "duration_days", "required_member_tier", "group"],
            "immutable_financial_history": ["wallet_mutations", "historical_purchases"],
        },
    },
]


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
def isolated_env():
    """Create an isolated test environment with SQLite DB."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "b03_packages_wiring_test.db")
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH")
    old_secret = os.environ.get("WEB_SESSION_SECRET")
    old_bridge_url = os.environ.get("CORE_BRIDGE_BASE_URL")
    old_bridge_token = os.environ.get("CORE_BRIDGE_TOKEN")
    old_bridge_hmac = os.environ.get("CORE_BRIDGE_HMAC_SECRET")

    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "b03-test-session-secret-99999"
    os.environ["CORE_BRIDGE_BASE_URL"] = "http://127.0.0.1:8080"
    os.environ["CORE_BRIDGE_TOKEN"] = "b03-fixture-token-secret"
    os.environ["CORE_BRIDGE_HMAC_SECRET"] = "b03-fixture-hmac-secret-value"

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
    if old_bridge_url is not None:
        os.environ["CORE_BRIDGE_BASE_URL"] = old_bridge_url
    else:
        os.environ.pop("CORE_BRIDGE_BASE_URL", None)
    if old_bridge_token is not None:
        os.environ["CORE_BRIDGE_TOKEN"] = old_bridge_token
    else:
        os.environ.pop("CORE_BRIDGE_TOKEN", None)
    if old_bridge_hmac is not None:
        os.environ["CORE_BRIDGE_HMAC_SECRET"] = old_bridge_hmac
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


def test_01_get_packages_collection_invokes_bot_collection(isolated_env, monkeypatch):
    """1. GET packages collection invokes exact Bot collection endpoint (/internal/v1/admin/packages)."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "ok": True,
            "status": "completed",
            "message": "Nạp danh mục gói cước canonical thành công",
            "total_packages": len(MOCK_BOT_PACKAGES),
            "packages": MOCK_BOT_PACKAGES,
            "proven_domains": {"subscription": 1, "combo": 1, "service_monthly": 1},
            "catalog_version": "2026.09.b03.canonical",
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b03")

    res = client.get("/api/admin/commercial/packages", cookies=cookies)
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert data.get("count") == len(MOCK_BOT_PACKAGES)
    assert len(data.get("packages", [])) == len(MOCK_BOT_PACKAGES)
    assert data.get("catalog_version") == "2026.09.b03.canonical"

    assert len(bridge_calls) == 1
    call = bridge_calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "/internal/v1/admin/packages"


def test_02_get_package_single_invokes_bot_single(isolated_env, monkeypatch):
    """2. GET single package invokes exact Bot single endpoint (/internal/v1/admin/packages/{package_key})."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "ok": True,
            "status": "completed",
            "message": "Nạp chi tiết gói cước thành công",
            "package": MOCK_BOT_PACKAGES[0],
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b03")

    res = client.get("/api/admin/commercial/packages/starter", cookies=cookies)
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert data.get("package_key") == "starter"
    assert data.get("package", {}).get("package_type") == "subscription"

    assert len(bridge_calls) == 1
    assert bridge_calls[0]["method"] == "GET"
    assert bridge_calls[0]["path"] == "/internal/v1/admin/packages/starter"


def test_03_patch_package_sends_exact_contract_and_verifies_readback(isolated_env, monkeypatch):
    """3. PATCH sends expected_version, changes, reason; verifies write receipt and performs fresh GET readback."""
    bridge_calls = []
    starter_v2 = {**MOCK_BOT_PACKAGES[0], "version": 2, "price_vnd": 120000, "display_name": "Gói Khởi động VIP"}

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        if method == "PATCH":
            return {
                "ok": True,
                "receipt_id": "rcpt_pkg_starter_2_abc12345",
                "package_key": "starter",
                "previous_version": 1,
                "new_version": 2,
                "accepted_changes": {"price_vnd": 120000, "display_name": "Gói Khởi động VIP"},
                "mutation_digest": "sha256_fixture_digest_xyz",
                "request_id": kwargs.get("request_id", ""),
                "actor_id": kwargs.get("actor_id", "7126457028"),
                "timestamp": "2026-09-22 02:00:00",
                "idempotent_replay": False,
                "package": starter_v2,
            }
        elif method == "GET":
            pkg = starter_v2 if any(c["method"] == "PATCH" for c in bridge_calls) else MOCK_BOT_PACKAGES[0]
            return {
                "ok": True,
                "package": pkg,
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    patch_payload = {
        "expected_version": 1,
        "changes": {
            "price_vnd": 120000,
            "display_name": "Gói Khởi động VIP",
        },
        "reason": "Cập nhật giá và tên gói khởi động cho đợt khuyến mãi Q3",
    }

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json=patch_payload,
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert data.get("package_key") == "starter"
    assert data.get("previous_version") == 1
    assert data.get("new_version") == 2
    assert data.get("readback_verified") is True
    assert data.get("verification_status") == "BOT_CORE_READBACK_VERIFIED"
    assert data.get("write_receipt", {}).get("receipt_id") == "rcpt_pkg_starter_2_abc12345"

    # Verifies bridge calls: GET capability check -> PATCH -> fresh GET readback
    assert len(bridge_calls) == 3
    assert bridge_calls[0]["method"] == "GET"
    assert bridge_calls[0]["path"] == "/internal/v1/admin/packages/starter"

    assert bridge_calls[1]["method"] == "PATCH"
    assert bridge_calls[1]["path"] == "/internal/v1/admin/packages/starter"
    patch_bot_payload = bridge_calls[1]["kwargs"]["payload"]
    assert patch_bot_payload["expected_version"] == 1
    assert patch_bot_payload["changes"] == {"price_vnd": 120000, "display_name": "Gói Khởi động VIP"}
    assert patch_bot_payload["reason"] == "Cập nhật giá và tên gói khởi động cho đợt khuyến mãi Q3"

    assert bridge_calls[2]["method"] == "GET"
    assert bridge_calls[2]["path"] == "/internal/v1/admin/packages/starter"


def test_04_patch_package_rejects_missing_or_empty_reason(isolated_env, monkeypatch):
    """4. PATCH rejects missing or whitespace-only reason with HTTP 400."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {"ok": True}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    # Empty string reason
    res_empty = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 110000}, "reason": "   "},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res_empty.status_code == 400
    assert len(bridge_calls) == 0

    # Missing reason
    res_missing = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 110000}},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res_missing.status_code == 422
    assert len(bridge_calls) == 0


def test_05_patch_package_rejects_immutable_identity_and_execution_fields(isolated_env, monkeypatch):
    """5. PATCH rejects immutable identity and execution fields with HTTP 400."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {"ok": True}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    forbidden_fields = ["package_key", "package_type", "duration_days", "benefits", "plan_xu", "ledger", "balance"]
    for fld in forbidden_fields:
        res = client.patch(
            "/api/admin/commercial/packages/starter",
            json={"expected_version": 1, "changes": {fld: "hack"}, "reason": "Testing immutable field rejection"},
            cookies=cookies,
            headers={"X-CSRF-Token": csrf_token},
        )
        assert res.status_code == 400, f"Field {fld} was not rejected with 400"
        assert len(bridge_calls) == 0, f"Bridge call made for forbidden field {fld}"


def test_06_patch_package_validation_bounds(isolated_env, monkeypatch):
    """6. PATCH rejects negative prices, out-of-bounds sort_order, empty display_name."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {"ok": True}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    # Negative price
    res1 = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": -1000}, "reason": "Negative price test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res1.status_code == 400
    assert len(bridge_calls) == 0

    # Price exceeding 100M
    res2 = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 200_000_000}, "reason": "High price test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res2.status_code == 400
    assert len(bridge_calls) == 0

    # Negative sort_order
    res3 = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"sort_order": -1}, "reason": "Negative sort_order"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res3.status_code == 400
    assert len(bridge_calls) == 0

    # Empty display_name
    res4 = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"display_name": "  "}, "reason": "Empty display name"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res4.status_code == 400
    assert len(bridge_calls) == 0


def test_07_patch_package_handles_409_version_conflict_without_replay(isolated_env, monkeypatch):
    """7. 409 causes zero PATCH replay (STALE_WRITE_AUTO_RETRY = 0)."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        if method == "GET":
            return {"ok": True, "package": MOCK_BOT_PACKAGES[0]}
        return {
            "ok": False,
            "error_code": "VERSION_CONFLICT",
            "message": "Stale version for package 'starter': expected 1, current 2.",
            "current_version": 2,
            "expected_version": 1,
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 150000}, "reason": "Conflict test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 409
    body = res.json()
    assert body.get("error_code") == "VERSION_CONFLICT"
    # Exactly 1 PATCH call: zero retry
    patch_calls = [c for c in bridge_calls if c["method"] == "PATCH"]
    assert len(patch_calls) == 1


def test_08_patch_package_readback_version_mismatch_fails_closed(isolated_env, monkeypatch):
    """8. Readback version mismatch fails closed with HTTP 502 and READBACK_VERSION_MISMATCH."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        if method == "PATCH":
            return {
                "ok": True,
                "receipt_id": "rcpt_pkg_starter_2_mismatch",
                "package_key": "starter",
                "previous_version": 1,
                "new_version": 2,
                "accepted_changes": {"price_vnd": 125000},
                "package": {**MOCK_BOT_PACKAGES[0], "version": 2, "price_vnd": 125000},
            }
        elif method == "GET":
            # Preflight returns v1; readback also returns stale v1
            return {
                "ok": True,
                "package": {**MOCK_BOT_PACKAGES[0], "version": 1, "price_vnd": 99000},
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 125000}, "reason": "Mismatch test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 502
    body = res.json()
    assert body.get("ok") is False
    assert body.get("error_code") == "READBACK_VERSION_MISMATCH"
    assert body.get("data", {}).get("readback_verified") is False


def test_08b_patch_package_readback_field_mismatch_fails_closed(isolated_env, monkeypatch):
    """8b. Readback field mismatch fails closed with HTTP 502 and READBACK_FIELD_MISMATCH."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        if method == "PATCH":
            return {
                "ok": True,
                "receipt_id": "rcpt_pkg_starter_2_field_mismatch",
                "package_key": "starter",
                "previous_version": 1,
                "new_version": 2,
                "accepted_changes": {"price_vnd": 125000},
                "package": {**MOCK_BOT_PACKAGES[0], "version": 2, "price_vnd": 125000},
            }
        elif method == "GET":
            if any(c["method"] == "PATCH" for c in bridge_calls):
                # Readback has version 2 but price wasn't updated
                return {
                    "ok": True,
                    "package": {**MOCK_BOT_PACKAGES[0], "version": 2, "price_vnd": 99000},
                }
            return {"ok": True, "package": MOCK_BOT_PACKAGES[0]}
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 125000}, "reason": "Field mismatch test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 502
    body = res.json()
    assert body.get("ok") is False
    assert body.get("error_code") == "READBACK_FIELD_MISMATCH"
    assert body.get("data", {}).get("readback_verified") is False


def test_08c_patch_package_fresh_get_unavailable_fails_closed(isolated_env, monkeypatch):
    """8c. Fresh GET unavailable fails closed with HTTP 502 and READBACK_UNAVAILABLE."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        if method == "PATCH":
            return {
                "ok": True,
                "receipt_id": "rcpt_pkg_starter_2_unavail",
                "package_key": "starter",
                "previous_version": 1,
                "new_version": 2,
                "accepted_changes": {"price_vnd": 125000},
                "package": {**MOCK_BOT_PACKAGES[0], "version": 2, "price_vnd": 125000},
            }
        elif method == "GET":
            if any(c["method"] == "PATCH" for c in bridge_calls):
                # Downstream GET fails after PATCH
                return {"ok": False, "status": "error", "error_code": "DOWNSTREAM_TIMEOUT"}
            return {"ok": True, "package": MOCK_BOT_PACKAGES[0]}
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 125000}, "reason": "Unavail test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 502
    body = res.json()
    assert body.get("ok") is False
    assert body.get("error_code") == "READBACK_UNAVAILABLE"


def test_08d_patch_package_missing_receipt_id_fails_closed(isolated_env, monkeypatch):
    """8d. Missing receipt_id fails closed with HTTP 502 and MISSING_RECEIPT_ID."""
    async def _mock_bridge_request(method, path, **kwargs):
        if method == "GET":
            return {"ok": True, "package": MOCK_BOT_PACKAGES[0]}
        elif method == "PATCH":
            return {
                "ok": True,
                # Missing receipt_id
                "package_key": "starter",
                "previous_version": 1,
                "new_version": 2,
                "accepted_changes": {"price_vnd": 125000},
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 125000}, "reason": "No receipt_id"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 502
    body = res.json()
    assert body.get("error_code") == "MISSING_RECEIPT_ID"


def test_08e_patch_package_missing_new_version_fails_closed(isolated_env, monkeypatch):
    """8e. Missing new_version fails closed with HTTP 502 and MISSING_NEW_VERSION."""
    async def _mock_bridge_request(method, path, **kwargs):
        if method == "GET":
            return {"ok": True, "package": MOCK_BOT_PACKAGES[0]}
        elif method == "PATCH":
            return {
                "ok": True,
                "receipt_id": "rcpt_123",
                "package_key": "starter",
                "previous_version": 1,
                # Missing new_version
                "accepted_changes": {"price_vnd": 125000},
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 125000}, "reason": "No new_version"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 502
    body = res.json()
    assert body.get("error_code") == "MISSING_NEW_VERSION"


def test_08f_patch_package_invalid_version_advance_fails_closed(isolated_env, monkeypatch):
    """8f. Invalid version advance (new_version <= prev_version) fails closed with HTTP 502."""
    async def _mock_bridge_request(method, path, **kwargs):
        if method == "GET":
            return {"ok": True, "package": MOCK_BOT_PACKAGES[0]}
        elif method == "PATCH":
            return {
                "ok": True,
                "receipt_id": "rcpt_123",
                "package_key": "starter",
                "previous_version": 2,
                "new_version": 2,  # Not advancing!
                "accepted_changes": {"price_vnd": 125000},
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 125000}, "reason": "No advance"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 502
    body = res.json()
    assert body.get("error_code") == "INVALID_VERSION_ADVANCE"


def test_08g_server_defense_rejects_fields_outside_bot_editable_commercial(isolated_env, monkeypatch):
    """8g. Server-side defense: rejects fields outside Bot canonical editable_commercial."""
    async def _mock_bridge_request(method, path, **kwargs):
        if method == "GET":
            # Bot package has public_visible as IMMUTABLE
            return {"ok": True, "package": MOCK_BOT_PACKAGES[0]}
        return {"ok": True}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"public_visible": False}, "reason": "Try editing immutable"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 400
    body = res.json()
    assert body.get("error_code") in {"IMMUTABLE_FIELD_REJECTED", "FIELD_NOT_EDITABLE_FOR_PACKAGE"}


def test_08h_combo_monthly_public_visible_editable_because_bot_allows(isolated_env, monkeypatch):
    """8h. Combo package public_visible is editable because Bot Core allows it in editable_commercial."""
    bridge_calls = []
    combo_v2 = {**MOCK_BOT_PACKAGES[1], "version": 2, "public_visible": False}

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        if method == "PATCH":
            return {
                "ok": True,
                "receipt_id": "rcpt_combo_2_ok",
                "package_key": "combo_ad_video_588k",
                "previous_version": 1,
                "new_version": 2,
                "accepted_changes": {"public_visible": False},
                "package": combo_v2,
            }
        elif method == "GET":
            pkg = combo_v2 if any(c["method"] == "PATCH" for c in bridge_calls) else MOCK_BOT_PACKAGES[1]
            return {"ok": True, "package": pkg}
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b03")

    res = client.patch(
        "/api/admin/commercial/packages/combo_ad_video_588k",
        json={"expected_version": 1, "changes": {"public_visible": False}, "reason": "Hide combo"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") is True
    assert body.get("data", {}).get("readback_verified") is True


def test_09_packages_rbac_security(isolated_env):
    """9. Unauthorized Web user cannot call APIs (ANONYMOUS=401, CUSTOMER=403, ADMIN=200)."""
    client = TestClient(app_module.app)

    # Anonymous -> 401
    res_anon = client.get("/api/admin/commercial/packages")
    assert res_anon.status_code == 401

    # Customer -> 403
    cust_cookies, _ = _create_session(isolated_env, "acc-cust-b03")
    res_cust = client.get("/api/admin/commercial/packages", cookies=cust_cookies)
    assert res_cust.status_code == 403

    # Admin -> 200
    admin_cookies, _ = _create_session(isolated_env, "acc-admin-b03")
    res_admin = client.get("/api/admin/commercial/packages", cookies=admin_cookies)
    assert res_admin.status_code == 200


def test_10_patch_package_requires_valid_csrf(isolated_env):
    """10. PATCH packages requires valid CSRF token."""
    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b03")

    # Missing CSRF
    res_no_csrf = client.patch(
        "/api/admin/commercial/packages/starter",
        json={"expected_version": 1, "changes": {"price_vnd": 120000}, "reason": "CSRF test"},
        cookies=cookies,
    )
    assert res_no_csrf.status_code == 403


def test_11_bridge_secrets_never_leak_in_package_responses(isolated_env, monkeypatch):
    """11. Bridge secrets never enter response payload."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {
            "ok": True,
            "packages": MOCK_BOT_PACKAGES,
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b03")

    res = client.get("/api/admin/commercial/packages", cookies=cookies)
    text = res.text
    assert "b03-fixture-token-secret" not in text
    assert "b03-fixture-hmac-secret-value" not in text
    assert "Authorization" not in text


def test_12_capability_matrix_b03_wired():
    """12. B01, B02, and B03 are CONTRACT_WIRED in capability matrix, B04-B05 remain FAIL_CLOSED."""
    assert CAPABILITY_MATRIX_PATH.exists()
    matrix = json.loads(CAPABILITY_MATRIX_PATH.read_text(encoding="utf-8"))
    blockers = matrix.get("commercial_command_center", {}).get("upstream_blockers", {})

    b01 = blockers.get("B01", {})
    assert b01.get("severity") == "CONTRACT_WIRED"

    b02 = blockers.get("B02", {})
    assert b02.get("severity") == "CONTRACT_WIRED"

    b03 = blockers.get("B03", {})
    assert b03.get("code") == "BOT_CANONICAL_PACKAGES_WRITE_WIRED", f"Expected BOT_CANONICAL_PACKAGES_WRITE_WIRED, got {b03.get('code')}"
    assert b03.get("severity") == "CONTRACT_WIRED"
    assert b03.get("write_mode") == "CANONICAL_CAS_WRITE"
    assert b03.get("authority") == "BOT_CORE"
    assert b03.get("contract_wired_to_bot_pr_1115") is True
    assert b03.get("bot_pr_1115_head") == "1ae49acf213d0ecfb009653eb0e44949cad6108a"
    assert b03.get("bot_pr_1115_merge_sha") == "e130b1b089021275dd53b2ffce54ea807ad0e3e1"
    assert b03.get("bot_pr_1115_state") == "MERGED"
    assert b03.get("bot_pr_1115_promoted") is True
    assert b03.get("bot_pr_1115_deployed") in {False, True}
    assert (
        b03.get("bot_pr_1115_business_live") in {"NOT_PROVEN", None}
        or b03.get("business_live") in {"NOT_PROVEN", "PARTIAL_READONLY"}
    )
    assert "1115" in b03.get("description", "")

    # B04-B05 must remain strictly FAIL_CLOSED
    assert blockers.get("B04", {}).get("code") in {"BOT_WRITE_ENDPOINT_MISSING_FOR_PROMOTIONS", "BOT_CANONICAL_PROMOTIONS_AUTHORITY_NOT_IMPLEMENTED"}
    assert blockers.get("B04", {}).get("severity") in {"FAIL_CLOSED", "NOT_IMPLEMENTED"}
    assert blockers.get("B05", {}).get("code") in {"BOT_WRITE_ENDPOINT_MISSING_FOR_TOPUP_PACKAGES", "BOT_CANONICAL_TOPUP_CONFIG_AUTHORITY_NOT_MUTABLE"}
    assert blockers.get("B05", {}).get("severity") in {"FAIL_CLOSED", "READ_ONLY"}


def test_13_portal_js_packages_editor_contract():
    """13. portal.js contains canonical package editor with CAS, readback, diff preview, conflict recovery."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    assert "fetchAdminCommercialPackages" in portal_code
    assert "/api/admin/commercial/packages" in portal_code
    assert "openPackageEditor" in portal_code
    assert "renderPackageEditor" in portal_code
    assert "savePackageEditor" in portal_code
    assert "adminCommercialPackagesState" in portal_code
    assert "VERSION_CONFLICT" in portal_code


def test_14_portal_js_packages_consumes_bot_field_classifications():
    """14. portal.js consumes field_classifications and field_effect_scopes from Bot Core, no hardcoded package type rules."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    idx = portal_code.find("function renderPackageEditor(")
    assert idx != -1
    fn_body = portal_code[idx:idx + 4500]

    # Consumes Bot field classifications and scopes
    assert "field_classifications" in fn_body
    assert "editable_commercial" in fn_body
    assert "field_effect_scopes" in fn_body
    assert "IMMUTABLE" in fn_body

    # Zero hardcoded package_type rules for editability
    assert 'packageItem.package_type === "subscription"' not in fn_body
    assert "isSubscription" not in fn_body

    # Zero fake receipt fallback
    assert "RCPT-PKG-OK" not in portal_code

    # Positive proof of readback verification
    assert "readback_verified === true" in portal_code


def test_15_portal_js_blocker_banner_removed_for_packages():
    """15. Blocker banner is removed when activeTab is packages (as well as products and pricing)."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    idx_comm = portal_code.find("function renderAdminCommercial(")
    idx_pricing = portal_code.find("function renderAdminPricing(")
    comm_block = portal_code[idx_comm:idx_pricing]

    # Blocker banner expression does not show on products, pricing, or packages tabs
    assert 'activeTab !== "packages"' in comm_block

    # B03 tag shows connected status with zero internal B03 jargon in visible text
    assert 'data-blocker="B03"' in comm_block
    assert "Gói cước: Đã nối Bot Core" in comm_block


def test_16_no_jargon_or_hardcoded_packages_list():
    """16. UI text has zero internal blocker codes and no hardcoded 3-item dummy packagesList."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    idx_comm = portal_code.find("function renderAdminCommercial(")
    idx_pricing = portal_code.find("function renderAdminPricing(")
    comm_block = portal_code[idx_comm:idx_pricing]

    assert "pkg_free" not in comm_block
    assert "pkg_creator_pro" not in comm_block
    assert "pkg_business_vip" not in comm_block
