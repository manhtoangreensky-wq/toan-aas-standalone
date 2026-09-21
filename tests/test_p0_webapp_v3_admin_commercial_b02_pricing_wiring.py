"""First-Red and Green Contract Suite for:
P0.WEBAPP.V3.ADMIN.COMMERCIAL.B02.PRICING.WEB.WIRING.R1

Validates:
1. GET pricing collection Web endpoint invokes exact Bot collection endpoint (/internal/v1/admin/pricing).
2. GET single pricing invokes exact Bot single endpoint (/internal/v1/admin/pricing/{price_key}).
3. PATCH sends exact: expected_version, new_value, reason to Bot Core.
4. PATCH rejects missing/empty reason (HTTP 400).
5. PATCH rejects immutable internal cost fields (HTTP 400).
6. PATCH rejects negative price values (HTTP 400).
7. Successful Bot receipt followed by fresh GET readback.
8. UI/API success only after readback match (CANONICAL_WRITE_VERIFIED).
9. Readback mismatch fails closed (READBACK_VERIFICATION_FAILED).
10. 409 causes zero PATCH replay (STALE_WRITE_AUTO_RETRY = 0).
11. Unauthorized Web user cannot call APIs (ANONYMOUS=401, CUSTOMER=403, ADMIN=200).
12. PATCH requires valid CSRF token.
13. Bridge secrets never enter response payload.
14. Immutable price key rejection handled properly (HTTP 400).
15. B01 and B02 are CONTRACT_WIRED in capability matrix, B03-B05 remain FAIL_CLOSED.
16. portal.js contains canonical pricing editor with CAS, readback, diff preview, conflict recovery.
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

MOCK_BOT_PRICING = [
    {
        "price_key": "video_tier_400",
        "product_key": "video_ai_prompt",
        "label": "Video AI Tiêu chuẩn (Tier 400)",
        "unit": "scene",
        "base_value": 75,
        "value_type": "int",
        "effective_value": 75,
        "version": 1,
        "editable": True,
        "policy_type": "PAID_PRICE",
        "domain": "video",
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
    },
    {
        "price_key": "image_tier_standard",
        "product_key": "image_flux_schnell",
        "label": "Tạo ảnh AI Tiêu chuẩn (FLUX)",
        "unit": "image",
        "base_value": 10,
        "value_type": "int",
        "effective_value": 10,
        "version": 1,
        "editable": True,
        "policy_type": "PAID_PRICE",
        "domain": "image",
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
    },
    {
        "price_key": "video_local_edit",
        "product_key": "video_local_edit",
        "label": "Chỉnh sửa video nội bộ (FFmpeg)",
        "unit": "job",
        "base_value": 0,
        "value_type": "int",
        "effective_value": 0,
        "version": 1,
        "editable": False,
        "policy_type": "FREE_BY_CANONICAL_POLICY",
        "domain": "video_local_edit",
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
    },
    {
        "price_key": "subdub_auto_word",
        "product_key": "subdub_service",
        "label": "Tạo phụ đề tự động (mỗi từ)",
        "unit": "word",
        "base_value": 0.5,
        "value_type": "float",
        "effective_value": 0.5,
        "version": 1,
        "editable": False,
        "policy_type": "UNWIRED_RUNTIME_POLICY",
        "domain": "subdub",
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
    },
    {
        "price_key": "chat_pro_cache_read",
        "product_key": "chat_pro",
        "label": "Chat Pro Đọc bộ nhớ đệm (mỗi 1K tokens)",
        "unit": "1k_tokens",
        "base_value": 0.45,
        "value_type": "float",
        "effective_value": 0.45,
        "version": 1,
        "editable": True,
        "policy_type": "PAID_PRICE",
        "domain": "chat",
        "updated_at": None,
        "updated_by": None,
        "update_reason": None,
        "has_override": False,
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
    db_path = os.path.join(tmp_dir, "b02_pricing_wiring_test.db")
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH")
    old_secret = os.environ.get("WEB_SESSION_SECRET")
    old_bridge_url = os.environ.get("CORE_BRIDGE_BASE_URL")
    old_bridge_token = os.environ.get("CORE_BRIDGE_TOKEN")
    old_bridge_hmac = os.environ.get("CORE_BRIDGE_HMAC_SECRET")

    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "b02-test-session-secret-88888"
    os.environ["CORE_BRIDGE_BASE_URL"] = "http://127.0.0.1:8080"
    os.environ["CORE_BRIDGE_TOKEN"] = "b02-fixture-token-secret"
    os.environ["CORE_BRIDGE_HMAC_SECRET"] = "b02-fixture-hmac-secret-value"

    copyfast_db.ensure_copyfast_schema()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-admin-b02', 'admin_b02@toanaas.vn', 'hash', 'Admin B02', 'admin', '7126457028', 1, '2026-09-21T10:00:00Z', '2026-09-21T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-cust-b02', 'cust_b02@toanaas.vn', 'hash', 'Customer B02', 'user', '987654321', 1, '2026-09-21T10:00:00Z', '2026-09-21T10:00:00Z')"""
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


# ==============================================================================
# TEST SUITE: B02 PRICING WEB WIRING
# ==============================================================================

def test_01_get_pricing_collection_invokes_bot_collection(isolated_env, monkeypatch):
    """1. GET pricing collection Web endpoint invokes exact Bot collection endpoint."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "ok": True,
            "status": "completed",
            "message": "Nạp danh mục thành công",
            "pricing": MOCK_BOT_PRICING,
            "total_count": len(MOCK_BOT_PRICING),
            "catalog_version": "2026.09.b02.canonical",
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b02")

    res = client.get("/api/admin/commercial/pricing", cookies=cookies)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    assert len(bridge_calls) == 1
    assert bridge_calls[0]["method"] == "GET"
    assert bridge_calls[0]["path"] == "/internal/v1/admin/pricing"
    data = body.get("data") or {}
    assert "pricing" in data
    assert len(data["pricing"]) == len(MOCK_BOT_PRICING)
    assert data.get("catalog_version") == "2026.09.b02.canonical"


def test_02_get_pricing_single_invokes_bot_single(isolated_env, monkeypatch):
    """2. GET single pricing invokes exact Bot single endpoint."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        item = next(p for p in MOCK_BOT_PRICING if p["price_key"] == "video_tier_400")
        return {
            "ok": True,
            "pricing": item,
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b02")

    res = client.get("/api/admin/commercial/pricing/video_tier_400", cookies=cookies)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    assert len(bridge_calls) == 1
    assert bridge_calls[0]["method"] == "GET"
    assert bridge_calls[0]["path"] == "/internal/v1/admin/pricing/video_tier_400"
    data = body.get("data") or {}
    assert data.get("price_key") == "video_tier_400"
    assert data.get("pricing", {}).get("label") == "Video AI Tiêu chuẩn (Tier 400)"


def test_03_patch_pricing_sends_exact_contract_and_verifies_readback(isolated_env, monkeypatch):
    """3. PATCH sends exact: expected_version, new_value, reason and verifies readback."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        if method == "PATCH":
            return {
                "ok": True,
                "receipt": {
                    "receipt_id": "rcpt_prc_1_abcdef12",
                    "price_key": "video_tier_400",
                    "previous_version": 1,
                    "new_version": 2,
                    "previous_value": "75",
                    "new_value": 85,
                    "mutation_digest": "abcdef123456",
                    "timestamp": "2026-09-21 11:00:00",
                    "idempotent_replay": False,
                },
                "pricing": {
                    "price_key": "video_tier_400",
                    "product_key": "video_ai_prompt",
                    "label": "Video AI Tiêu chuẩn (Tier 400)",
                    "unit": "scene",
                    "effective_value": 85,
                    "version": 2,
                    "updated_at": "2026-09-21 11:00:00",
                },
            }
        elif method == "GET":
            return {
                "ok": True,
                "pricing": {
                    "price_key": "video_tier_400",
                    "effective_value": 85,
                    "version": 2,
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b02")

    payload = {
        "expected_version": 1,
        "new_value": 85,
        "reason": "Điều chỉnh theo biến động chi phí GPU Q3",
    }

    res = client.patch(
        "/api/admin/commercial/pricing/video_tier_400",
        json=payload,
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    assert body.get("status") == "completed"

    # Exactly 2 bridge calls: 1 PATCH then 1 GET readback
    assert len(bridge_calls) == 2
    assert bridge_calls[0]["method"] == "PATCH"
    assert bridge_calls[0]["path"] == "/internal/v1/admin/pricing/video_tier_400"
    sent_payload = bridge_calls[0]["kwargs"].get("payload", {})
    assert sent_payload.get("expected_version") == 1
    assert sent_payload.get("new_value") == 85
    assert sent_payload.get("reason") == "Điều chỉnh theo biến động chi phí GPU Q3"

    assert bridge_calls[1]["method"] == "GET"
    assert bridge_calls[1]["path"] == "/internal/v1/admin/pricing/video_tier_400"

    data = body.get("data") or {}
    assert data.get("readback_verified") is True
    assert data.get("customer_effective_live_verified") is False
    assert data.get("verification_status") == "BOT_CORE_READBACK_VERIFIED"
    assert data.get("new_version") == 2
    assert data.get("previous_version") == 1


def test_04_patch_pricing_rejects_missing_or_empty_reason(isolated_env, monkeypatch):
    """4. PATCH rejects missing/empty reason with HTTP 400."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {"ok": True}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b02")

    # Empty string reason
    res = client.patch(
        "/api/admin/commercial/pricing/video_tier_400",
        json={"expected_version": 1, "new_value": 85, "reason": "   "},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code in {400, 422}
    assert len(bridge_calls) == 0, "Zero PATCH calls allowed when reason is empty"


def test_05_patch_pricing_rejects_immutable_cost_fields(isolated_env, monkeypatch):
    """5. PATCH rejects payload containing forbidden internal cost fields."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {"ok": True}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b02")

    forbidden_payload = {
        "expected_version": 1,
        "new_value": 85,
        "reason": "Thử ghi đè trường chi phí",
        "provider_cost": 50,
        "margin": 0.2,
    }

    res = client.patch(
        "/api/admin/commercial/pricing/video_tier_400",
        json=forbidden_payload,
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 400
    assert len(bridge_calls) == 0, "Forbidden cost fields must be rejected before calling bridge"


def test_06_patch_pricing_rejects_negative_price(isolated_env, monkeypatch):
    """6. PATCH rejects negative price values with HTTP 400."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {"ok": True}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b02")

    res = client.patch(
        "/api/admin/commercial/pricing/video_tier_400",
        json={"expected_version": 1, "new_value": -50, "reason": "Giá âm không hợp lệ"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 400
    assert len(bridge_calls) == 0


def test_07_patch_pricing_handles_409_version_conflict_without_replay(isolated_env, monkeypatch):
    """7. 409 causes zero PATCH replay (STALE_WRITE_AUTO_RETRY = 0)."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path})
        return {
            "ok": False,
            "error_code": "VERSION_CONFLICT_STALE_WRITE",
            "message": "Version conflict for video_tier_400: expected 1, current is 2.",
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b02")

    res = client.patch(
        "/api/admin/commercial/pricing/video_tier_400",
        json={"expected_version": 1, "new_value": 85, "reason": "Conflict test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 409
    body = res.json()
    assert body.get("error_code") == "VERSION_CONFLICT_STALE_WRITE"
    # Exactly 1 call: NO retry
    assert len(bridge_calls) == 1


def test_08_patch_pricing_readback_mismatch_fails_closed(isolated_env, monkeypatch):
    """8. Readback mismatch fails closed with READBACK_VERIFICATION_FAILED."""
    async def _mock_bridge_request(method, path, **kwargs):
        if method == "PATCH":
            return {
                "ok": True,
                "receipt": {
                    "receipt_id": "rcpt_prc_1_mismatch",
                    "previous_version": 1,
                    "new_version": 2,
                    "new_value": 85,
                },
                "pricing": {"version": 2},
            }
        elif method == "GET":
            # Bot readback returns unexpected stale value or version
            return {
                "ok": True,
                "pricing": {
                    "effective_value": 75,  # Stale!
                    "version": 1,            # Stale!
                },
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b02")

    res = client.patch(
        "/api/admin/commercial/pricing/video_tier_400",
        json={"expected_version": 1, "new_value": 85, "reason": "Readback mismatch test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") is False
    assert body.get("error_code") == "READBACK_VERIFICATION_FAILED"
    data = body.get("data") or {}
    assert data.get("readback_verified") is False
    assert data.get("customer_effective_live_verified") is False
    assert data.get("verification_status") == "READBACK_VERIFICATION_FAILED"


def test_09_patch_pricing_immutable_key_rejected(isolated_env, monkeypatch):
    """9. Immutable price key mutation returns 400."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {
            "ok": False,
            "error_code": "IMMUTABLE_PRICE_KEY_REJECTED",
            "message": "Price key 'video_local_edit' is immutable by canonical policy.",
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf_token = _create_session(isolated_env, "acc-admin-b02")

    res = client.patch(
        "/api/admin/commercial/pricing/video_local_edit",
        json={"expected_version": 1, "new_value": 100, "reason": "Immutable test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 400
    body = res.json()
    assert body.get("error_code") == "IMMUTABLE_PRICE_KEY_REJECTED"


def test_10_pricing_rbac_security(isolated_env):
    """10. Unauthorized Web user cannot call APIs (ANONYMOUS=401, CUSTOMER=403, ADMIN=200)."""
    client = TestClient(app_module.app)

    # Anonymous -> 401
    res_anon = client.get("/api/admin/commercial/pricing")
    assert res_anon.status_code == 401

    # Customer -> 403
    cust_cookies, _ = _create_session(isolated_env, "acc-cust-b02")
    res_cust = client.get("/api/admin/commercial/pricing", cookies=cust_cookies)
    assert res_cust.status_code == 403

    # Admin -> 200
    admin_cookies, _ = _create_session(isolated_env, "acc-admin-b02")
    res_admin = client.get("/api/admin/commercial/pricing", cookies=admin_cookies)
    assert res_admin.status_code == 200


def test_11_patch_pricing_requires_valid_csrf(isolated_env):
    """11. PATCH pricing requires valid CSRF token."""
    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b02")

    # Missing CSRF
    res_no_csrf = client.patch(
        "/api/admin/commercial/pricing/video_tier_400",
        json={"expected_version": 1, "new_value": 85, "reason": "CSRF test"},
        cookies=cookies,
    )
    assert res_no_csrf.status_code == 403


def test_12_bridge_secrets_never_leak_in_pricing_responses(isolated_env, monkeypatch):
    """12. Bridge secrets never enter response payload."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {
            "ok": True,
            "pricing": MOCK_BOT_PRICING,
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b02")

    res = client.get("/api/admin/commercial/pricing", cookies=cookies)
    text = res.text
    assert "b02-fixture-token-secret" not in text
    assert "b02-fixture-hmac-secret-value" not in text
    assert "Authorization" not in text


def test_13_capability_matrix_b02_wired_b03_b05_guarded():
    """13. B01 and B02 are CONTRACT_WIRED in capability matrix, B03-B05 remain FAIL_CLOSED."""
    assert CAPABILITY_MATRIX_PATH.exists()
    matrix = json.loads(CAPABILITY_MATRIX_PATH.read_text(encoding="utf-8"))
    blockers = matrix.get("commercial_command_center", {}).get("upstream_blockers", {})

    b01 = blockers.get("B01", {})
    assert b01.get("code") == "BOT_CANONICAL_PRODUCT_WRITE_WIRED"
    assert b01.get("severity") == "CONTRACT_WIRED"

    b02 = blockers.get("B02", {})
    assert b02.get("code") == "BOT_CANONICAL_PRICING_WRITE_WIRED", f"Expected BOT_CANONICAL_PRICING_WRITE_WIRED, got {b02.get('code')}"
    assert b02.get("severity") == "CONTRACT_WIRED"
    assert b02.get("write_mode") == "CANONICAL_CAS_WRITE"
    assert b02.get("authority") == "BOT_CORE"
    assert b02.get("live_status") == "CONTRACT_WIRED_NOT_LIVE_VERIFIED"
    assert b02.get("contract_wired_to_bot_pr_1098") is True
    assert b02.get("bot_pr_1098_head") == "50218b7c69413e5be47e48517cb4a397c3026578"
    assert b02.get("bot_pr_1098_state") == "OPEN_UNMERGED"
    assert b02.get("bot_pr_1098_promoted") is False
    assert b02.get("remediation_gate") == "BOT_PR_1098_OPEN_UNMERGED_PENDING_PROMOTION"
    assert "1098" in b02.get("description", "")

    # B03-B05 must remain strictly FAIL_CLOSED
    assert blockers.get("B03", {}).get("code") == "BOT_WRITE_ENDPOINT_MISSING_FOR_PACKAGES"
    assert blockers.get("B03", {}).get("severity") == "FAIL_CLOSED"
    assert blockers.get("B04", {}).get("code") == "BOT_WRITE_ENDPOINT_MISSING_FOR_PROMOTIONS"
    assert blockers.get("B04", {}).get("severity") == "FAIL_CLOSED"
    assert blockers.get("B05", {}).get("code") == "BOT_WRITE_ENDPOINT_MISSING_FOR_TOPUP_PACKAGES"
    assert blockers.get("B05", {}).get("severity") == "FAIL_CLOSED"


def test_14_portal_js_pricing_editor_contract():
    """14. portal.js contains canonical pricing editor with CAS, readback, diff preview, conflict recovery."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    assert "fetchAdminCommercialPricing" in portal_code
    assert "/api/admin/commercial/pricing" in portal_code
    assert "openPricingEditor" in portal_code
    assert "renderPricingEditor" in portal_code
    assert "savePricingEditor" in portal_code
    assert "adminCommercialPricingState" in portal_code
    assert "expected_version" in portal_code
    assert "VERSION_CONFLICT_STALE_WRITE" in portal_code
    assert "CANONICAL_WRITE_VERIFIED" in portal_code


def test_15_portal_js_pricing_blocker_banner_removed_for_pricing():
    """15. Blocker banner is removed when activeTab is products or pricing, but retained for packages/promos/topups."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    idx_comm = portal_code.find("function renderAdminCommercial(")
    idx_pricing = portal_code.find("function renderAdminPricing(")
    comm_block = portal_code[idx_comm:idx_pricing]

    # Blocker banner expression does not show on products or pricing tabs
    assert 'activeTab !== "products" && activeTab !== "pricing"' in comm_block

    # B02 tag shows connected status with zero internal B02 jargon in visible text
    assert 'data-blocker="B02"' in comm_block
    assert "Bảng giá: Đã nối Bot Core · chưa xác minh live" in comm_block
    assert "B02: Bảng giá (Đã kết nối)" not in comm_block

    # B03-B05 tags remain present
    for b in ["B03", "B04", "B05"]:
        assert f'data-blocker="{b}"' in comm_block


def test_16_get_pricing_catalog_version_passthrough_and_no_fallback(isolated_env, monkeypatch):
    """16. C1-C: Web layer passes through Bot catalog_version without web-authored fallback."""
    # Sub-case A: Bot provides catalog_version -> passed through
    async def _mock_with_version(method, path, **kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "Nạp danh mục thành công",
            "pricing": MOCK_BOT_PRICING,
            "catalog_version": "2026.09.bot.pr1098.canonical",
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_with_version)
    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b02")

    res = client.get("/api/admin/commercial/pricing", cookies=cookies)
    assert res.status_code == 200
    assert res.json().get("data", {}).get("catalog_version") == "2026.09.bot.pr1098.canonical"

    # Sub-case B: Bot omits catalog_version -> returns None, NOT fallback string
    async def _mock_without_version(method, path, **kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "Nạp danh mục thành công",
            "pricing": MOCK_BOT_PRICING,
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_without_version)
    res2 = client.get("/api/admin/commercial/pricing", cookies=cookies)
    assert res2.status_code == 200
    assert res2.json().get("data", {}).get("catalog_version") is None


def test_17_no_jargon_or_hardcoded_sku_count_in_pricing_ui():
    """17. C1-D: UI text has zero internal blocker codes and no hardcoded 38 SKU count."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    idx_comm = portal_code.find("function renderAdminCommercial(")
    idx_pricing = portal_code.find("function renderAdminPricing(")
    comm_block = portal_code[idx_comm:idx_pricing]

    # No hardcoded "38 SKU"
    assert "38 SKU" not in comm_block
    # No visible B02 jargon in text content
    assert "B02: Bảng giá" not in comm_block
    assert "Bảng giá: Đã nối Bot Core · chưa xác minh live" in comm_block
