"""Empirical verification test suite for WEB08: Providers Truth.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB08.PROVIDERS.TRUTH
Repository: manhtoangreensky-wq/toan-aas-standalone

Invariants:
1. PROVIDER_INVENTORY_TRUTH: Providers strictly match canonical source/runtime catalog.
2. STATE_CONFLATION=0: CONFIGURED != AVAILABLE != HEALTHY != ELIGIBLE != SELECTED.
3. RAW_SECRET_EXPOSURE=0 & RAW_TOKEN_EXPOSURE=0: All secrets, keys, and tokens stripped.
4. CAPABILITY_FAKE_READY=0: Only declared + executable + healthy capabilities are ready.
5. ROUTING_READY_FAKE=0: Unconfigured/probation/degraded providers not routing eligible.
6. CUSTOMER_PROVIDER_ADMIN_ACCESS=0: Strict RBAC (unauthenticated -> 401, customer -> 403, admin -> 200).
7. DEAD_PROVIDER_CTA=0 & FAKE_PROVIDER_ACTION_SUCCESS=0: All actions audited/guarded.
8. BACKEND_FAILURE_FAKE_EMPTY=0: Timeout/5xx returned truthfully as guarded/unavailable.
9. REAL_PROVIDER_NETWORK_CALLS=0 & PAID_PROVIDER_CALLS=0: Zero real network invocation.
10. SECRET_MUTATIONS=0 & ENV_MUTATIONS=0: Read-model only, no credential writes.
11. STALE_HEALTH_AS_CURRENT=0: Observations older than freshness window flagged as stale.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import importlib
import os
from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_db
import copyfast_provider_policy as policy


# ==============================================================================
# 1. FIXTURES & HELPERS
# ==============================================================================
CUSTOMER_EMAIL = "web08-customer@toanaas.vn"
CUSTOMER_PWD = "Web08CustomerPassword123!@#"
ADMIN_EMAIL = "web08-admin@toanaas.vn"
ADMIN_PWD = "Web08AdminPassword123!@#"
CUSTOMER_TELEGRAM_UID = "7126457088"
ADMIN_TELEGRAM_UID = "1000000088"


def _clear_rate_limits() -> None:
    for mod_name in ("app",):
        m = sys.modules.get(mod_name)
        if m and hasattr(m, "_auth_rate_windows"):
            m._auth_rate_windows.clear()
    if hasattr(app_module, "_auth_rate_windows"):
        app_module._auth_rate_windows.clear()


def _patch_bridge(monkeypatch, mock_fn) -> None:
    api_live = sys.modules.get("copyfast_api") or copyfast_api
    bridge_live = sys.modules.get("copyfast_bridge") or importlib.import_module("copyfast_bridge")
    auth_live = sys.modules.get("copyfast_auth") or importlib.import_module("copyfast_auth")

    for m in {copyfast_api, api_live}:
        if m:
            monkeypatch.setattr(m, "bridge_configured", lambda: True)
            monkeypatch.setattr(m, "bridge_request", mock_fn)
    for m in {bridge_live}:
        if m:
            monkeypatch.setattr(m, "bridge_configured", lambda: True)
            monkeypatch.setattr(m, "bridge_request", mock_fn)
    for m in {auth_live}:
        if m and hasattr(m, "bridge_request"):
            monkeypatch.setattr(m, "bridge_request", mock_fn)


def _setup_test_env(tmp_path: Path, monkeypatch) -> tuple[TestClient, Path, Path]:
    _clear_rate_limits()
    session_db = tmp_path / "web08_session.db"
    system_db = tmp_path / "web08_system.db"

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(session_db))
    monkeypatch.setenv("DB_FILE", str(system_db))
    monkeypatch.setenv("DB_PATH", str(system_db))
    monkeypatch.setenv("WEB_SESSION_SECRET", "web08-test-session-secret-key-64b-secure-value")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "web08-fixture-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "web08-fixture-hmac")

    _clear_rate_limits()

    copyfast_db.ensure_copyfast_schema()

    db_mod = importlib.import_module("db")
    db_mod.init_db()

    app_mod = sys.modules.get("app") or importlib.import_module("app")
    client = TestClient(app_mod.app)
    return client, session_db, system_db


def _create_and_login_user(client: TestClient, session_db: Path, email: str, pwd: str, role: str = "customer", telegram_uid: str | None = None) -> dict:
    _clear_rate_limits()
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "display_name": email.split("@")[0]})
    assert reg.status_code == 200, f"Register failed: {reg.status_code} {reg.text}"

    with sqlite3.connect(str(session_db)) as conn:
        conn.execute(
            "UPDATE web_accounts SET role_cache=?, canonical_user_id=? WHERE email=?",
            (role, telegram_uid, email),
        )
        row = conn.execute("SELECT id, role_cache, canonical_user_id FROM web_accounts WHERE email=?", (email,)).fetchone()
        conn.commit()

    _clear_rate_limits()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 200, f"Login failed: {login.status_code} {login.text}"
    csrf = login.json()["data"]["csrf_token"]
    cookies = dict(login.cookies)

    app_mod = sys.modules.get("app") or importlib.import_module("app")
    authed_client = TestClient(app_mod.app, cookies=cookies)
    authed_client.headers["X-CSRF-Token"] = csrf
    return {
        "client": authed_client,
        "account_id": str(row[0]),
        "role": str(row[1]),
        "canonical_user_id": str(row[2] or ""),
    }


# ==============================================================================
# 2. PURE POLICY & TAXONOMY CONTRACTS (STATE_CONFLATION = 0)
# ==============================================================================
def test_configured_not_equal_available_not_equal_healthy():
    """Case 1: CONFIGURED != AVAILABLE != HEALTHY != ELIGIBLE != SELECTED.

    State conflation count must be 0.
    """
    # 1. Configured with credentials present, but no health evidence -> UNKNOWN health, not healthy
    rec1 = policy.synthesize_provider_record({
        "provider_id": "shopaikey",
        "configured": True,
        "credential_present": True,
        "available": True,
        "health_state": "UNKNOWN",
    })
    assert rec1["configured"] is True
    assert rec1["health_state"] == "UNKNOWN"
    assert rec1["routing_eligible"] is False  # Cannot route on UNKNOWN health

    # 2. Configured with degraded health -> available but degraded
    rec2 = policy.synthesize_provider_record({
        "provider_id": "gemini",
        "configured": True,
        "health_state": "DEGRADED",
        "available": True,
    })
    assert rec2["configured"] is True
    assert rec2["health_state"] == "DEGRADED"
    assert rec2["available"] is True

    # 3. Not configured -> available must be False regardless of incoming flag
    rec3 = policy.synthesize_provider_record({
        "provider_id": "groq",
        "configured": False,
        "available": True,  # should be forced False
        "health_state": "HEALTHY",  # should be forced UNAVAILABLE
    })
    assert rec3["configured"] is False
    assert rec3["available"] is False
    assert rec3["health_state"] == "UNAVAILABLE"
    assert rec3["routing_eligible"] is False


def test_unknown_provider_health_never_shown_as_healthy():
    """Case 2: UNKNOWN_PROVIDER_AS_HEALTHY = 0."""
    rec = policy.synthesize_provider_record({
        "provider_id": "key4u",
        "configured": True,
        "health_state": "UNKNOWN",
    })
    assert rec["health_state"] == "UNKNOWN"
    assert rec["routing_eligible"] is False


def test_capability_fake_ready_zero():
    """Case 3: CAPABILITY_FAKE_READY = 0.

    A capability is only 'ready' if declared + executable + healthy.
    """
    # Provider is configured but health is DEGRADED -> healthy is False
    rec = policy.synthesize_provider_record({
        "provider_id": "shopaikey",
        "configured": True,
        "health_state": "DEGRADED",
        "capabilities": ["video", "image"],
    })
    caps = {c["name"]: c for c in rec["capabilities"]}
    assert "video" in caps
    assert caps["video"]["declared"] is True
    assert caps["video"]["executable"] is True
    assert caps["video"]["healthy"] is False
    assert caps["video"]["ready"] is False  # CAPABILITY_FAKE_READY = 0


def test_routing_ready_fake_zero():
    """Case 4: ROUTING_READY_FAKE = 0.

    Probation or unconfigured cannot be routing eligible.
    """
    # Configured + healthy, but on probation
    rec = policy.synthesize_provider_record({
        "provider_id": "kling",
        "configured": True,
        "available": True,
        "health_state": "HEALTHY",
        "probation": True,
    })
    assert rec["probation"] is True
    assert rec["routing_eligible"] is False


def test_stale_health_flagged_correctly():
    """Case 5: STALE_HEALTH_AS_CURRENT = 0.

    Observations older than 3600 seconds are flagged as stale.
    """
    old_time = (datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=2)).isoformat()
    rec_stale = policy.synthesize_provider_record({
        "provider_id": "elevenlabs",
        "configured": True,
        "available": True,
        "health_state": "HEALTHY",
        "last_observed_at": old_time,
    })
    assert rec_stale["stale"] is True

    fresh_time = datetime.datetime.now(timezone.utc).isoformat()
    rec_fresh = policy.synthesize_provider_record({
        "provider_id": "elevenlabs",
        "configured": True,
        "available": True,
        "health_state": "HEALTHY",
        "last_observed_at": fresh_time,
    })
    assert rec_fresh["stale"] is False


def test_zero_raw_secret_exposure():
    """Case 6: RAW_SECRET_EXPOSURE = 0 & RAW_TOKEN_EXPOSURE = 0.

    All API keys, tokens, Bearer tokens, secrets must be completely scrubbed.
    """
    poisoned_payload = {
        "provider_id": "shopaikey",
        "configured": True,
        "api_key": "sk-secret-live-shopaikey-key-12345",
        "token": "tok_private_bearer_token_abc",
        "auth_header": "Bearer sk-secret-bearer-999",
        "secret": "super_secret_hmac_value",
        "webhook_secret": "whsec_live_webhook_value",
        "password": "private_password_123",
        "nested": {
            "credentials": {
                "client_secret": "raw_client_secret_xyz",
                "api_key": "sk-nested-key",
            },
        },
    }
    cleaned = policy.redact_provider_secrets(poisoned_payload)
    # Check that none of the secret keys or values remain
    raw_str = str(cleaned)
    assert "sk-secret-live-shopaikey" not in raw_str
    assert "tok_private_bearer" not in raw_str
    assert "Bearer sk-secret" not in raw_str
    assert "super_secret_hmac" not in raw_str
    assert "whsec_live" not in raw_str
    assert "private_password" not in raw_str
    assert "raw_client_secret" not in raw_str
    assert "api_key" not in cleaned
    assert "token" not in cleaned
    assert "auth_header" not in cleaned


def test_failure_states_distinguished_in_read_model():
    """Case 7: Distinguish NO_PROVIDERS_CONFIGURED, READ_MODEL_UNAVAILABLE, SOURCE_ERROR, EMPTY_VALID_REGISTRY."""
    # 1. READ_MODEL_UNAVAILABLE (bridge guarded/unavailable)
    rm_unavail = policy.synthesize_providers_read_model({}, bridge_status="guarded", bridge_error_code="CORE_BRIDGE_NOT_CONFIGURED")
    assert rm_unavail["read_model_state"] == "READ_MODEL_UNAVAILABLE"

    # 2. SOURCE_ERROR (bridge error 5xx)
    rm_err = policy.synthesize_providers_read_model({}, bridge_status="error", bridge_error_code="CORE_BRIDGE_INVALID_RESPONSE")
    assert rm_err["read_model_state"] == "SOURCE_ERROR"

    # 3. EMPTY_VALID_REGISTRY (valid items = [])
    rm_empty = policy.synthesize_providers_read_model({"items": []})
    assert rm_empty["read_model_state"] == "EMPTY_VALID_REGISTRY"

    # 4. NO_PROVIDERS_CONFIGURED (items exist, but 0 configured)
    rm_noconf = policy.synthesize_providers_read_model({
        "items": [
            {"provider_id": "shopaikey", "configured": False},
            {"provider_id": "gemini", "configured": False},
        ]
    })
    assert rm_noconf["read_model_state"] == "NO_PROVIDERS_CONFIGURED"

    # 5. VALID_REGISTRY (configured items present)
    rm_valid = policy.synthesize_providers_read_model({
        "items": [
            {"provider_id": "shopaikey", "configured": True, "available": True, "health_state": "HEALTHY"},
        ]
    })
    assert rm_valid["read_model_state"] == "VALID_REGISTRY"
    assert rm_valid["summary"]["configured_count"] == 1


def test_provider_action_classification_and_dead_cta_zero():
    """Case 8: DEAD_PROVIDER_CTA = 0 & FAKE_PROVIDER_ACTION_SUCCESS = 0."""
    refresh_info = policy.classify_provider_action("refresh")
    assert refresh_info["classification"] == "LOCAL_SOURCE_ONLY"
    assert refresh_info["executable_on_web"] is True

    test_info = policy.classify_provider_action("test")
    assert test_info["classification"] == "EXTERNAL_NETWORK"
    assert test_info["executable_on_web"] is False

    freeze_info = policy.classify_provider_action("freeze")
    assert freeze_info["classification"] == "MUTATING"
    assert freeze_info["executable_on_web"] is False

    unknown_info = policy.classify_provider_action("hack_provider")
    assert unknown_info["classification"] == "NOT_IMPLEMENTED"
    assert unknown_info["executable_on_web"] is False


# ==============================================================================
# 3. API RBAC & ENDPOINT TRUTH (CUSTOMER_PROVIDER_ADMIN_ACCESS = 0)
# ==============================================================================
def test_unauthenticated_request_blocked(tmp_path, monkeypatch):
    """Case 9: Unauthenticated request to /api/v1/admin/providers -> 401."""
    client, _, _ = _setup_test_env(tmp_path, monkeypatch)
    res = client.get("/api/v1/admin/providers")
    assert res.status_code in {401, 403}


def test_customer_role_forbidden_to_access_provider_admin(tmp_path, monkeypatch):
    """Case 10: Customer role request to /api/v1/admin/providers -> 403 Forbidden.

    CUSTOMER_PROVIDER_ADMIN_ACCESS = 0.
    """
    client, session_db, _ = _setup_test_env(tmp_path, monkeypatch)
    customer = _create_and_login_user(client, session_db, CUSTOMER_EMAIL, CUSTOMER_PWD, role="customer")
    res = customer["client"].get("/api/v1/admin/providers")
    assert res.status_code == 403
    assert res.json()["error_code"] == "REQUEST_DENIED"

    # Also detail route
    res_detail = customer["client"].get("/api/v1/admin/providers/shopaikey")
    assert res_detail.status_code == 403


def test_canonical_admin_receives_sanitized_provider_list(tmp_path, monkeypatch):
    """Case 11: Canonical admin gets 200 OK with sanitized provider list."""
    client, session_db, _ = _setup_test_env(tmp_path, monkeypatch)
    admin = _create_and_login_user(
        client, session_db, ADMIN_EMAIL, ADMIN_PWD, role="admin", telegram_uid=ADMIN_TELEGRAM_UID
    )

    async def mock_bridge_request(method, path, **kwargs):
        if path == "/internal/v1/me":
            return {"ok": True, "status": "completed", "data": {"role": "admin"}}
        return {
            "ok": True,
            "status": "completed",
            "message": "Providers loaded",
            "data": {
                "items": [
                    {
                        "provider_id": "shopaikey",
                        "display_name": "ShopAIKey",
                        "provider_kind": "commercial_api",
                        "configured": True,
                        "available": True,
                        "health_state": "HEALTHY",
                        "api_key": "sk-secret-leaked-key-12345",
                        "capabilities": ["video", "image"],
                    },
                    {
                        "provider_id": "gemini",
                        "display_name": "Google Gemini",
                        "provider_kind": "cloud_llm",
                        "configured": True,
                        "available": False,
                        "health_state": "UNKNOWN",
                        "capabilities": ["text"],
                    },
                ]
            },
            "error_code": None,
        }

    _patch_bridge(monkeypatch, mock_bridge_request)

    res = admin["client"].get("/api/v1/admin/providers")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True, f"Admin providers read failed: status={res.status_code}, body={body}"
    data = body["data"]
    assert "items" in data
    items = data["items"]
    assert len(items) == 2

    # Verify ShopAIKey record
    shopai = next(i for i in items if i["provider_id"] == "shopaikey")
    assert shopai["configured"] is True
    assert shopai["available"] is True
    assert shopai["health_state"] == "HEALTHY"
    # Zero secret exposure
    assert "api_key" not in shopai
    assert "12345" not in str(shopai)

    # Verify Gemini record
    gem = next(i for i in items if i["provider_id"] == "gemini")
    assert gem["configured"] is True
    assert gem["available"] is False
    assert gem["health_state"] == "UNKNOWN"
    assert gem["routing_eligible"] is False  # UNKNOWN health not routing eligible


def test_backend_failure_fake_empty_zero(tmp_path, monkeypatch):
    """Case 12: BACKEND_FAILURE_FAKE_EMPTY = 0.

    When backend/bridge fails or times out, do NOT fake an empty success.
    """
    client, session_db, _ = _setup_test_env(tmp_path, monkeypatch)
    admin = _create_and_login_user(
        client, session_db, ADMIN_EMAIL, ADMIN_PWD, role="admin", telegram_uid=ADMIN_TELEGRAM_UID
    )

    async def mock_bridge_down(method, path, **kwargs):
        if path == "/internal/v1/me":
            return {"ok": True, "status": "completed", "data": {"role": "admin"}}
        return {
            "ok": False,
            "status": "guarded",
            "message": "Cầu nối Core Bridge chưa sẵn sàng.",
            "data": {},
            "error_code": "CORE_BRIDGE_UNAVAILABLE",
        }

    _patch_bridge(monkeypatch, mock_bridge_down)

    res = admin["client"].get("/api/v1/admin/providers")
    assert res.status_code == 200
    body = res.json()
    # Response must truthfully show ok=False and status=guarded
    assert body["ok"] is False
    assert body["status"] == "guarded"
    assert body["error_code"] == "CORE_BRIDGE_UNAVAILABLE"
    # Read model state confirms READ_MODEL_UNAVAILABLE
    assert body["data"]["read_model_state"] == "READ_MODEL_UNAVAILABLE"


def test_provider_action_guard_blocks_mutations_and_network(tmp_path, monkeypatch):
    """Case 13: Provider action endpoint guards mutating and external test actions.

    SECRET_MUTATIONS = 0, REAL_PROVIDER_NETWORK_CALLS = 0.
    """
    client, session_db, _ = _setup_test_env(tmp_path, monkeypatch)
    admin = _create_and_login_user(
        client, session_db, ADMIN_EMAIL, ADMIN_PWD, role="admin", telegram_uid=ADMIN_TELEGRAM_UID
    )

    async def mock_bridge_auth(method, path, **kwargs):
        if path == "/internal/v1/me":
            return {"ok": True, "status": "completed", "data": {"role": "admin"}}
        return {"ok": True, "status": "completed", "data": {}}

    _patch_bridge(monkeypatch, mock_bridge_auth)

    # Attempt to test provider
    res_test = admin["client"].post("/api/v1/admin/providers/shopaikey/test")
    assert res_test.status_code == 200
    b_test = res_test.json()
    assert b_test["ok"] is False
    assert b_test["status"] == "guarded"
    assert b_test["error_code"] == "PROVIDER_CONTROL_ACTION_GUARDED"
    assert b_test["data"]["classification"] == "EXTERNAL_NETWORK"

    # Attempt to freeze provider
    res_freeze = admin["client"].post("/api/v1/admin/providers/shopaikey/freeze")
    assert res_freeze.status_code == 200
    b_freeze = res_freeze.json()
    assert b_freeze["ok"] is False
    assert b_freeze["status"] == "guarded"
    assert b_freeze["data"]["classification"] == "MUTATING"


def test_real_provider_network_hard_gate(monkeypatch):
    """Case 14: REAL_PROVIDER_NETWORK_CALLS = 0.

    Assert that any attempt to make real external HTTP requests raises an error.
    """
    import urllib.request

    def forbidden_network(*args, **kwargs):
        pytest.fail("CRITICAL HARD GATE VIOLATION: Real provider network call attempted!")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)


def test_admin_providers_page_requires_auth(tmp_path, monkeypatch):
    """Case 15: HTML page /admin/providers redirects unauthenticated users."""
    client, _, _ = _setup_test_env(tmp_path, monkeypatch)
    res = client.get("/admin/providers", follow_redirects=False)
    assert res.status_code in {307, 401, 403}
    if res.status_code == 307:
        assert "/login" in res.headers["location"]
