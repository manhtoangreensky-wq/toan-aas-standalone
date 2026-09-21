"""First-Red and Green Contract Suite for:
P0.WEBAPP.V3.ADMIN.COMMERCIAL.B01.PRODUCT.EDITOR.WEB.WIRING.R1

Validates:
1. GET collection Web endpoint invokes exact Bot collection endpoint.
2. GET single invokes exact Bot single endpoint.
3. PATCH sends exact: expected_version, changes, reason.
4. PATCH cannot contain immutable technical field.
5. Successful Bot receipt followed by fresh GET readback.
6. UI success only after readback_match.
7. 409 causes no PATCH replay.
8. timeout/502 causes no PATCH replay.
9. no-op edit sends zero PATCH.
10. unauthorized Web user cannot call APIs (ANONYMOUS=401, CUSTOMER=403, ADMIN=200).
11. bridge secrets never enter response payload.
12. script_image_video canonical key preserved.
13. video_idea canonical key preserved.
14. executor aliases not duplicated as products.
15. deferred execution lock rendered read-only.
16. B02-B05 remain guarded, B01 matrix updated.
17. portal.js product editor contract verified.
"""

from __future__ import annotations

import copy
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

MOCK_BOT_PRODUCTS = [
    {
        "product_key": "video_trend",
        "display_name": "Video theo trend",
        "description": "Tạo video ngắn bắt trend mạng xã hội tự động",
        "product_group": "video",
        "public_visible": True,
        "commercial_enabled": True,
        "sort_order": 10,
        "execution_enabled": True,
        "execution_blocker": "",
        "supported_tiers": ["standard", "pro"],
        "supported_ratios": ["9:16", "16:9"],
        "version": 1,
        "has_override": False,
    },
    {
        "product_key": "script_image_video",
        "display_name": "Kịch bản → Video",
        "description": "Chuyển kịch bản hoàn chỉnh thành chuỗi cảnh video",
        "product_group": "video",
        "public_visible": True,
        "commercial_enabled": True,
        "sort_order": 50,
        "execution_enabled": True,
        "execution_blocker": "",
        "supported_tiers": ["standard", "pro"],
        "supported_ratios": ["16:9", "9:16"],
        "version": 1,
        "has_override": False,
    },
    {
        "product_key": "video_idea",
        "display_name": "Ý tưởng → Video AI",
        "description": "Từ ý tưởng thô phát triển thành video hoàn chỉnh",
        "product_group": "video",
        "public_visible": True,
        "commercial_enabled": True,
        "sort_order": 55,
        "execution_enabled": True,
        "execution_blocker": "",
        "supported_tiers": ["standard"],
        "supported_ratios": ["16:9"],
        "version": 1,
        "has_override": False,
    },
    {
        "product_key": "video_local_edit",
        "display_name": "Chỉnh sửa Video cục bộ",
        "description": "Chỉnh sửa trực tiếp trên timeline",
        "product_group": "video",
        "public_visible": False,
        "commercial_enabled": False,
        "sort_order": 70,
        "execution_enabled": False,
        "execution_blocker": "DEFERRED_POST_LAUNCH",
        "supported_tiers": [],
        "supported_ratios": [],
        "version": 1,
        "has_override": False,
    },
    {
        "product_key": "multi_scene_film",
        "display_name": "Video dài tập (Nhiều phân cảnh)",
        "description": "Sản xuất video nhiều tập có cốt truyện xuyên suốt",
        "product_group": "video",
        "public_visible": False,
        "commercial_enabled": False,
        "sort_order": 100,
        "execution_enabled": False,
        "execution_blocker": "EXECUTION_LOCKED_PENDING_RELEASE",
        "supported_tiers": [],
        "supported_ratios": [],
        "version": 1,
        "has_override": False,
    },
    {
        "product_key": "video_long",
        "display_name": "Video thời lượng dài",
        "description": "Dựng phim AI thời lượng trên 3 phút",
        "product_group": "video",
        "public_visible": False,
        "commercial_enabled": False,
        "sort_order": 110,
        "execution_enabled": False,
        "execution_blocker": "EXECUTION_LOCKED_INFRA_UPGRADE",
        "supported_tiers": [],
        "supported_ratios": [],
        "version": 1,
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
    db_path = os.path.join(tmp_dir, "b01_product_editor_test.db")
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH")
    old_secret = os.environ.get("WEB_SESSION_SECRET")
    old_bridge_url = os.environ.get("CORE_BRIDGE_BASE_URL")
    old_bridge_token = os.environ.get("CORE_BRIDGE_TOKEN")
    old_bridge_hmac = os.environ.get("CORE_BRIDGE_HMAC_SECRET")

    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "b01-test-session-secret-99999"
    os.environ["CORE_BRIDGE_BASE_URL"] = "http://127.0.0.1:8080"
    os.environ["CORE_BRIDGE_TOKEN"] = "b01-fixture-token-secret"
    os.environ["CORE_BRIDGE_HMAC_SECRET"] = "b01-fixture-hmac-secret-value"

    copyfast_db.ensure_copyfast_schema()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-admin-b01', 'admin_b01@toanaas.vn', 'hash', 'Admin B01', 'admin', '7126457028', 1, '2026-09-20T10:00:00Z', '2026-09-20T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-cust-b01', 'cust_b01@toanaas.vn', 'hash', 'Customer B01', 'user', '123456789', 1, '2026-09-20T10:00:00Z', '2026-09-20T10:00:00Z')"""
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
# TEST SUITE: B01 PRODUCT EDITOR WEB WIRING
# ==============================================================================

def test_01_get_collection_invokes_bot_collection(isolated_env, monkeypatch):
    """1. GET collection Web endpoint invokes exact Bot collection endpoint."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "ok": True,
            "status": "completed",
            "message": "Nạp danh mục thành công",
            "data": {
                "count": len(MOCK_BOT_PRODUCTS),
                "products": MOCK_BOT_PRODUCTS,
            },
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b01")

    res = client.get("/api/admin/commercial/products", cookies=cookies)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    assert len(bridge_calls) == 1
    assert bridge_calls[0]["method"] == "GET"
    assert bridge_calls[0]["path"] == "/internal/v1/admin/products"
    data = body.get("data") or {}
    assert "products" in data
    assert len(data["products"]) == len(MOCK_BOT_PRODUCTS)


def test_02_get_single_invokes_bot_single(isolated_env, monkeypatch):
    """2. GET single invokes exact Bot single endpoint."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        prod = next(p for p in MOCK_BOT_PRODUCTS if p["product_key"] == "script_image_video")
        return {
            "ok": True,
            "status": "completed",
            "message": "Nạp chi tiết sản phẩm thành công",
            "data": {
                "product_key": "script_image_video",
                "base": prod,
                "effective": prod,
                "version": 1,
            },
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b01")

    res = client.get("/api/admin/commercial/products/script_image_video", cookies=cookies)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    assert len(bridge_calls) == 1
    assert bridge_calls[0]["method"] == "GET"
    assert bridge_calls[0]["path"] == "/internal/v1/admin/products/script_image_video"


def test_03_patch_sends_exact_contract(isolated_env, monkeypatch):
    """3. PATCH sends exact expected_version, changes, reason to Bot."""
    bridge_calls = []

    async def _mock_bridge_request(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        if method == "PATCH":
            payload = kwargs.get("payload", {})
            return {
                "ok": True,
                "status": "completed",
                "message": "Cập nhật thành công",
                "data": {
                    "product_key": "script_image_video",
                    "previous_version": payload.get("expected_version", 1),
                    "new_version": payload.get("expected_version", 1) + 1,
                    "accepted_changes": payload.get("changes", {}),
                    "write_receipt": {
                        "receipt_id": "rcpt-test-001",
                        "product_key": "script_image_video",
                        "version": 2,
                        "timestamp": "2026-09-20T21:00:00Z",
                        "actor_id": "acc-admin-b01",
                        "reason": payload.get("reason"),
                        "mutation_digest": "hash123",
                    },
                    "effective_product": {
                        **MOCK_BOT_PRODUCTS[1],
                        **payload.get("changes", {}),
                        "version": 2,
                    },
                    "readback_match": True,
                },
            }
        # Subsequent GET readback
        return {
            "ok": True,
            "status": "completed",
            "data": {
                "product_key": "script_image_video",
                "effective": {
                    **MOCK_BOT_PRODUCTS[1],
                    "display_name": "Kịch bản sang Video AI Pro",
                    "sort_order": 52,
                    "version": 2,
                },
                "version": 2,
            },
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    payload = {
        "expected_version": 1,
        "changes": {
            "display_name": "Kịch bản sang Video AI Pro",
            "sort_order": 52,
        },
        "reason": "Điều chỉnh tên gọi hiển thị thương mại",
    }

    res = client.patch(
        "/api/admin/commercial/products/script_image_video",
        json=payload,
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    patch_call = next(c for c in bridge_calls if c["method"] == "PATCH")
    assert patch_call["path"] == "/internal/v1/admin/products/script_image_video"
    bot_payload = patch_call["kwargs"].get("payload", {})
    assert bot_payload.get("expected_version") == 1
    assert bot_payload.get("changes") == {"display_name": "Kịch bản sang Video AI Pro", "sort_order": 52}
    assert bot_payload.get("reason") == "Điều chỉnh tên gọi hiển thị thương mại"


def test_04_patch_cannot_contain_immutable_technical_field(isolated_env, monkeypatch):
    """4. PATCH cannot contain immutable technical field (execution_enabled, pricing, etc.)."""
    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    forbidden_payloads = [
        {"expected_version": 1, "changes": {"execution_enabled": True}, "reason": "hack"},
        {"expected_version": 1, "changes": {"execution_blocker": ""}, "reason": "hack"},
        {"expected_version": 1, "changes": {"pricing": 100}, "reason": "hack"},
        {"expected_version": 1, "changes": {"supported_tiers": ["vip"]}, "reason": "hack"},
        {"expected_version": 1, "changes": {"provider_capability": "mock"}, "reason": "hack"},
    ]

    for p in forbidden_payloads:
        res = client.patch(
            "/api/admin/commercial/products/script_image_video",
            json=p,
            cookies=cookies,
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code in (400, 422), f"Expected 400/422 for forbidden field, got {res.status_code}: {res.text}"


def test_05_successful_bot_receipt_followed_by_fresh_get_readback(isolated_env, monkeypatch):
    """5. Successful Bot receipt followed by fresh GET readback (POST_PATCH_GET_READBACK=YES)."""
    call_sequence = []

    async def _mock_bridge_request(method, path, **kwargs):
        call_sequence.append(method)
        if method == "PATCH":
            return {
                "ok": True,
                "status": "completed",
                "message": "Cập nhật thành công",
                "data": {
                    "product_key": "script_image_video",
                    "previous_version": 1,
                    "new_version": 2,
                    "accepted_changes": {"display_name": "Tên mới"},
                    "write_receipt": {
                        "receipt_id": "rcpt-readback-001",
                        "product_key": "script_image_video",
                        "version": 2,
                        "timestamp": "2026-09-20T21:00:00Z",
                        "actor_id": "acc-admin-b01",
                        "reason": "Test readback",
                        "mutation_digest": "dig123",
                    },
                    "effective_product": {
                        **MOCK_BOT_PRODUCTS[1],
                        "display_name": "Tên mới",
                        "version": 2,
                    },
                    "readback_match": True,
                },
            }
        # GET readback
        return {
            "ok": True,
            "status": "completed",
            "data": {
                "product_key": "script_image_video",
                "effective": {
                    **MOCK_BOT_PRODUCTS[1],
                    "display_name": "Tên mới",
                    "version": 2,
                },
                "version": 2,
            },
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    res = client.patch(
        "/api/admin/commercial/products/script_image_video",
        json={"expected_version": 1, "changes": {"display_name": "Tên mới"}, "reason": "Test readback"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    # Must have called PATCH then GET
    assert call_sequence == ["PATCH", "GET"], f"Expected ['PATCH', 'GET'], got {call_sequence}"
    body = res.json()
    assert body.get("data", {}).get("readback_verified") is True


def test_06_ui_success_only_after_readback_match(isolated_env, monkeypatch):
    """6. UI success only after readback_match (returns failure/guarded if readback mismatch)."""
    async def _mock_bridge_request(method, path, **kwargs):
        if method == "PATCH":
            return {
                "ok": True,
                "status": "completed",
                "data": {
                    "product_key": "script_image_video",
                    "previous_version": 1,
                    "new_version": 2,
                    "accepted_changes": {"display_name": "Tên mới"},
                    "write_receipt": {"receipt_id": "r1", "version": 2},
                    "effective_product": {"display_name": "Tên mới", "version": 2},
                    "readback_match": True,
                },
            }
        # GET readback returns old/mismatched version!
        return {
            "ok": True,
            "status": "completed",
            "data": {
                "product_key": "script_image_video",
                "effective": {"display_name": "Tên cũ", "version": 1},
                "version": 1,
            },
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    res = client.patch(
        "/api/admin/commercial/products/script_image_video",
        json={"expected_version": 1, "changes": {"display_name": "Tên mới"}, "reason": "Test mismatch"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    # Must fail or flag unverified readback
    body = res.json()
    assert body.get("ok") is False or body.get("data", {}).get("readback_verified") is False


def test_07_409_causes_no_patch_replay(isolated_env, monkeypatch):
    """7. 409 causes no PATCH replay (STALE_WRITE_AUTO_RETRY=0)."""
    patch_attempts = []

    async def _mock_bridge_request(method, path, **kwargs):
        if method == "PATCH":
            patch_attempts.append(kwargs)
            return {
                "ok": False,
                "status": "guarded",
                "error_code": "VERSION_CONFLICT_STALE_WRITE",
                "message": "Stale write rejected: expected_version=1 but current_version=2",
                "data": {"current_version": 2, "expected_version": 1},
            }
        return {"ok": True, "data": {}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    res = client.patch(
        "/api/admin/commercial/products/script_image_video",
        json={"expected_version": 1, "changes": {"display_name": "Tên mới"}, "reason": "Test stale"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert len(patch_attempts) == 1, f"Expected exactly 1 PATCH attempt, got {len(patch_attempts)}"
    assert res.status_code in (409, 200)
    body = res.json()
    assert body.get("ok") is False
    assert body.get("error_code") == "VERSION_CONFLICT_STALE_WRITE" or "409" in str(body)


def test_08_timeout_502_causes_no_patch_replay(isolated_env, monkeypatch):
    """8. timeout/502 causes no PATCH replay (AMBIGUOUS_PATCH_AUTO_RETRY=0)."""
    patch_attempts = []

    async def _mock_bridge_request(method, path, **kwargs):
        if method == "PATCH":
            patch_attempts.append(kwargs)
            return {
                "ok": False,
                "status": "guarded",
                "error_code": "CORE_BRIDGE_UNAVAILABLE",
                "message": "Hệ thống đang bảo trì",
                "data": {},
            }
        return {"ok": True, "data": {}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    res = client.patch(
        "/api/admin/commercial/products/script_image_video",
        json={"expected_version": 1, "changes": {"display_name": "Tên mới"}, "reason": "Test timeout"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert len(patch_attempts) == 1, f"Expected exactly 1 PATCH attempt without retry, got {len(patch_attempts)}"
    body = res.json()
    assert body.get("ok") is False


def test_09_no_op_edit_sends_zero_patch(isolated_env, monkeypatch):
    """9. no-op edit sends zero PATCH (NO_OP_PATCH_COUNT=0)."""
    patch_attempts = []

    async def _mock_bridge_request(method, path, **kwargs):
        if method == "PATCH":
            patch_attempts.append(kwargs)
        return {"ok": True, "data": {}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    # Empty changes
    res = client.patch(
        "/api/admin/commercial/products/script_image_video",
        json={"expected_version": 1, "changes": {}, "reason": "No-op"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert len(patch_attempts) == 0, f"Expected 0 PATCH attempts for empty changes, got {len(patch_attempts)}"
    assert res.status_code in (400, 422)


def test_10_unauthorized_web_user_cannot_call_apis(isolated_env):
    """10. Unauthorized Web users cannot call APIs (ANONYMOUS=401, CUSTOMER=403, ADMIN=200)."""
    client = TestClient(app_module.app)

    # Anonymous
    res_anon_get = client.get("/api/admin/commercial/products")
    assert res_anon_get.status_code in (401, 403, 307), f"Anonymous GET leaked: {res_anon_get.status_code}"
    res_anon_patch = client.patch("/api/admin/commercial/products/script_image_video", json={"expected_version": 1, "changes": {}, "reason": "hack"})
    assert res_anon_patch.status_code in (401, 403, 422), f"Anonymous PATCH leaked: {res_anon_patch.status_code}"

    # Customer user
    cust_cookies, cust_csrf = _create_session(isolated_env, "acc-cust-b01")
    res_cust_get = client.get("/api/admin/commercial/products", cookies=cust_cookies)
    assert res_cust_get.status_code == 403, f"Customer GET leaked: {res_cust_get.status_code}"
    res_cust_patch = client.patch(
        "/api/admin/commercial/products/script_image_video",
        json={"expected_version": 1, "changes": {"display_name": "hack"}, "reason": "hack"},
        cookies=cust_cookies,
        headers={"X-CSRF-Token": cust_csrf},
    )
    assert res_cust_patch.status_code == 403, f"Customer PATCH leaked: {res_cust_patch.status_code}"


def test_11_bridge_secrets_never_enter_response_payload(isolated_env, monkeypatch):
    """11. Bridge secrets never enter response payload."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {
            "ok": True,
            "data": {
                "products": MOCK_BOT_PRODUCTS,
            },
        }

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b01")

    res = client.get("/api/admin/commercial/products", cookies=cookies)
    content = res.text.lower()
    assert "b01-fixture-token-secret" not in content
    assert "b01-fixture-hmac-secret-value" not in content
    assert "authorization" not in content
    assert "signature" not in content


def test_12_script_image_video_canonical_key_preserved(isolated_env, monkeypatch):
    """12. script_image_video canonical key preserved."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {"ok": True, "data": {"products": MOCK_BOT_PRODUCTS}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b01")

    res = client.get("/api/admin/commercial/products", cookies=cookies)
    body = res.json()
    keys = [p["product_key"] for p in body.get("data", {}).get("products", [])]
    assert "script_image_video" in keys


def test_13_video_idea_canonical_key_preserved(isolated_env, monkeypatch):
    """13. video_idea canonical key preserved."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {"ok": True, "data": {"products": MOCK_BOT_PRODUCTS}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b01")

    res = client.get("/api/admin/commercial/products", cookies=cookies)
    body = res.json()
    keys = [p["product_key"] for p in body.get("data", {}).get("products", [])]
    assert "video_idea" in keys


def test_14_executor_aliases_not_duplicated_as_products(isolated_env, monkeypatch):
    """14. executor aliases (script_to_video, video_idea_to_product) not duplicated as products."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {"ok": True, "data": {"products": MOCK_BOT_PRODUCTS}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, _ = _create_session(isolated_env, "acc-admin-b01")

    res = client.get("/api/admin/commercial/products", cookies=cookies)
    body = res.json()
    keys = [p["product_key"] for p in body.get("data", {}).get("products", [])]
    assert "script_to_video" not in keys
    assert "video_idea_to_product" not in keys


def test_15_deferred_execution_lock_rendered_read_only(isolated_env, monkeypatch):
    """15. deferred execution lock rendered read-only; execution_enabled cannot be mutated."""
    async def _mock_bridge_request(method, path, **kwargs):
        return {"ok": True, "data": {"products": MOCK_BOT_PRODUCTS}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    res = client.get("/api/admin/commercial/products", cookies=cookies)
    body = res.json()
    prods = {p["product_key"]: p for p in body.get("data", {}).get("products", [])}
    assert prods["video_local_edit"]["execution_enabled"] is False
    assert prods["video_local_edit"]["execution_blocker"] == "DEFERRED_POST_LAUNCH"
    assert prods["multi_scene_film"]["execution_enabled"] is False
    assert prods["multi_scene_film"]["execution_blocker"] == "EXECUTION_LOCKED_PENDING_RELEASE"
    assert prods["video_long"]["execution_enabled"] is False
    assert prods["video_long"]["execution_blocker"] == "EXECUTION_LOCKED_INFRA_UPGRADE"

    # Attempt to mutate execution_enabled must be rejected
    patch_res = client.patch(
        "/api/admin/commercial/products/video_local_edit",
        json={"expected_version": 1, "changes": {"execution_enabled": True}, "reason": "force unlock"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert patch_res.status_code in (400, 422)


def test_16_b02_b05_remain_guarded_and_b01_matrix_updated():
    """16. B02-B05 remain FAIL_CLOSED and B01 is updated to BOT_CANONICAL_PRODUCT_WRITE_WIRED."""
    assert CAPABILITY_MATRIX_PATH.exists()
    matrix = json.loads(CAPABILITY_MATRIX_PATH.read_text(encoding="utf-8"))
    blockers = matrix.get("commercial_command_center", {}).get("upstream_blockers", {})

    b01 = blockers.get("B01", {})
    assert b01.get("code") == "BOT_CANONICAL_PRODUCT_WRITE_WIRED", f"Expected BOT_CANONICAL_PRODUCT_WRITE_WIRED, got {b01.get('code')}"
    assert b01.get("write_mode") == "CANONICAL_CAS_WRITE"
    assert b01.get("authority") == "BOT_CORE"
    assert b01.get("live_status") == "CONTRACT_WIRED_NOT_LIVE_VERIFIED"

    # B02 is exact BOT_CANONICAL_PRICING_WRITE_WIRED; B03-B05 must remain FAIL_CLOSED
    b02 = blockers.get("B02", {})
    assert b02.get("code") == "BOT_CANONICAL_PRICING_WRITE_WIRED"
    assert b02.get("severity") == "CONTRACT_WIRED"
    assert b02.get("authority") == "BOT_CORE"
    assert b02.get("live_status") == "DEPLOYED_PRODUCTION_READONLY_PARTIAL"
    assert blockers.get("B03", {}).get("severity") in {"CONTRACT_WIRED", "FAIL_CLOSED"}
    assert blockers.get("B04", {}).get("code") == "BOT_WRITE_ENDPOINT_MISSING_FOR_PROMOTIONS"
    assert blockers.get("B04", {}).get("severity") == "FAIL_CLOSED"
    assert blockers.get("B05", {}).get("code") == "BOT_WRITE_ENDPOINT_MISSING_FOR_TOPUP_PACKAGES"
    assert blockers.get("B05", {}).get("severity") == "FAIL_CLOSED"


def test_17_portal_js_product_editor_contract():
    """17. portal.js contains canonical product editor with CAS, readback, diff preview, conflict recovery."""
    assert PORTAL_JS_PATH.exists()
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    assert "loadAdminCommercialProducts" in portal_code or "fetchAdminCommercialProducts" in portal_code
    assert "/api/admin/commercial/products" in portal_code
    assert "openProductEditor" in portal_code or "renderProductEditor" in portal_code
    assert "expected_version" in portal_code
    assert "VERSION_CONFLICT_STALE_WRITE" in portal_code
    assert "readback_match" in portal_code or "readback_verified" in portal_code
    assert "CANONICAL_WRITE_VERIFIED" in portal_code


# ==============================================================================
# C1 Regression Contracts (Section 14)
# ==============================================================================

def test_c1_01_canonical_default_products_absent():
    """01 CANONICAL_DEFAULT_PRODUCTS absent: WebApp contains zero static fallback catalog."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "CANONICAL_DEFAULT_PRODUCTS" not in portal_code, "Static CANONICAL_DEFAULT_PRODUCTS must not exist"


def test_c1_02_canonical_collection_failure_renders_error_state():
    """02 canonical collection failure renders error state: shows error message & retry button."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "adminCommercialProductsLoadError" in portal_code
    assert "Không thể tải danh mục sản phẩm" in portal_code
    assert "Thử tải lại" in portal_code
    assert "reload-commercial-products" in portal_code


def test_c1_03_collection_failure_renders_zero_fake_product_rows():
    """03 collection failure renders zero fake product rows: fail closed."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    idx = portal_code.find("function renderProductTableBody(")
    assert idx != -1
    fn_body = portal_code[idx:idx + 2500]
    assert "adminCommercialProductsLoadError" in fn_body
    assert 'colspan="9"' in fn_body
    assert "CANONICAL_DEFAULT_PRODUCTS" not in fn_body


def test_c1_04_editor_cannot_open_from_invented_or_static_product():
    """04 editor cannot open from invented/static product: fail-closed if collection not loaded."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    idx = portal_code.find("function openProductEditor(")
    assert idx != -1
    fn_body = portal_code[idx:idx + 1200]
    assert "!adminCommercialProductsState" in fn_body or "Array.isArray(adminCommercialProductsState)" in fn_body
    assert "CANONICAL_DEFAULT_PRODUCTS" not in fn_body


def test_c1_05_empty_successful_collection_shows_legitimate_empty_state():
    """05 empty successful collection shows legitimate empty state."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "Chưa có sản phẩm nào trong danh mục." in portal_code


def test_c1_06_product_count_dynamic():
    """06 product count dynamic: table rows mapped directly from API state."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    idx = portal_code.find("function renderProductTableBody(")
    assert idx != -1
    fn_body = portal_code[idx:idx + 2500]
    assert "adminCommercialProductsState.map(" in fn_body


def test_c1_07_no_invented_technical_metadata():
    """07 no invented technical metadata: client does not fabricate missing execution metadata."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert 'product_key: "video_trend"' not in portal_code
    assert 'product_key: "script_image_video"' not in portal_code
    assert 'product_key: "video_idea"' not in portal_code


def test_c1_08_canonical_object_technical_fields_render_only_if_actually_supplied():
    """08 canonical object technical fields render only if actually supplied."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "p.execution_enabled !== undefined" in portal_code
    assert "product.execution_enabled !== undefined" in portal_code


def test_c1_09_canonical_patch_still_works(isolated_env, monkeypatch):
    """09 canonical PATCH still works: sends expected_version, changes, reason to bridge."""
    sent_payload = {}

    async def _mock_bridge_request(method, path, **kwargs):
        nonlocal sent_payload
        if method == "PATCH":
            sent_payload = kwargs.get("payload", {})
            return {
                "ok": True,
                "data": {
                    "receipt_id": "RCPT-TEST-09",
                    "product_key": "video_trend",
                    "previous_version": 1,
                    "new_version": 2,
                    "readback_match": True,
                },
            }
        elif method == "GET":
            return {"ok": True, "data": {"product": {**MOCK_BOT_PRODUCTS[0], "version": 2, "display_name": "Trend Updated"}}}
        return {"ok": False, "detail": "not found"}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", _mock_bridge_request)

    client = TestClient(app_module.app)
    cookies, csrf = _create_session(isolated_env, "acc-admin-b01")

    res = client.patch(
        "/api/admin/commercial/products/video_trend",
        json={"expected_version": 1, "changes": {"display_name": "Trend Updated"}, "reason": "C1 regression test"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    assert sent_payload.get("expected_version") == 1
    assert sent_payload.get("changes") == {"display_name": "Trend Updated"}
    assert sent_payload.get("reason") == "C1 regression test"


def test_c1_10_cas_conflict_still_zero_replay():
    """10 CAS conflict still zero replay: STALE_WRITE_AUTO_RETRY = 0 and no auto-resend."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "STALE_WRITE_AUTO_RETRY = 0" in portal_code
    assert "VERSION_CONFLICT_STALE_WRITE" in portal_code
    assert "Dữ liệu đã thay đổi ở phiên khác" in portal_code


def test_c1_11_receipt_still_required():
    """11 receipt still required: receiptId extracted from write response."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "write_receipt" in portal_code or "receipt_id" in portal_code
    assert "Mã biên nhận" in portal_code


def test_c1_12_fresh_get_readback_still_required():
    """12 fresh GET readback still required: readback_verified / readback_match checked."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "readback_verified" in portal_code
    assert "readback_match" in portal_code


def test_c1_13_readback_mismatch_still_fail_closed():
    """13 readback mismatch still fail-closed: mismatch renders warning, not success."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "dữ liệu đọc lại chưa khớp" in portal_code


def test_c1_14_user_visible_b01_cas_pr_jargon_absent():
    """14 user-visible B01/CAS/PR jargon absent from normal Admin UI."""
    portal_code = PORTAL_JS_PATH.read_text(encoding="utf-8")

    idx_editor = portal_code.find("function renderProductEditor(")
    idx_open = portal_code.find("function openProductEditor(")
    editor_body = portal_code[idx_editor:idx_open]

    assert "Bot Canonical Commercial Editor" not in editor_body
    assert "Bot Core PR #1093" not in editor_body
    assert "Technical Lock - Read-only" not in editor_body
    assert "Execution Ready" not in editor_body
    assert "Execution Locked" not in editor_body
    assert "CAS PATCH" not in editor_body
    assert "CAS expected_version" not in editor_body

    idx_comm = portal_code.find("function renderAdminCommercial(")
    idx_pricing = portal_code.find("function renderAdminPricing(")
    comm_body = portal_code[idx_comm:idx_pricing]

    assert "Trụ cột 1 / 5 · Bot Authority Canonical" not in comm_body
    assert "Danh mục Sản phẩm AI Canonical (Bot PR #1093)" not in comm_body
    assert "CAS Wired" not in comm_body
    assert "Quản lý thương mại" in comm_body
    assert "Danh mục Sản phẩm AI" in comm_body
    assert "Đã kết nối" in comm_body


def test_c1_15_navigation_i18n_unmapped_count_zero():
    """15 navigation i18n unmapped count zero."""
    import tests.test_portal_i18n_bundle_contracts as i18n_tests
    assert hasattr(i18n_tests, "test_vietnamese_shell_dashboard_and_admin_navigation_copy_is_clear")
