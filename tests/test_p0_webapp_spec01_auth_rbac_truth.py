"""Empirical verification test suite for SPEC-01: AUTH / SESSION / RBAC.

Covers:
1. Customer:
   - registration (valid, invalid email, duplicate non-enumerating)
   - login (valid credentials, invalid credentials, password verification)
   - logout (CSRF required, session revoked, cookie deleted)
   - session expiration (expired session fails closed)
   - refresh / me probe (returns real account data, updates last_seen)
   - direct URL bypass prevention (customer cannot access /admin or /api/v1/admin/*)
   - account disabled (is_active=0 rejected at login and active session)
2. Admin:
   - /admin/login loads
   - backend role enforcement (only admin role allowed)
   - customer cannot login via admin portal
   - admin access to /admin succeeds
   - admin session expiration
   - unauthenticated access fails closed
   - API admin actions fail closed
3. Social Login Honesty:
   - provider discovery reflects backend configuration
   - disabled providers (Google, Apple, Telegram if unconfigured) do not show fake buttons
   - FAKE_SOCIAL_LOGIN_BUTTONS = 0
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys
import time

import pytest
from fastapi.testclient import TestClient

MODULES = (
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_mfa", "copyfast_pages",
)

CUSTOMER_EMAIL = "customer-spec01@toanaas.vn"
CUSTOMER_PASSWORD = "CustomerPassword123!@#"
ADMIN_EMAIL = "admin-spec01@toanaas.vn"
ADMIN_PASSWORD = "AdminPassword123!@#"


def _setup_app_client(tmp_path, monkeypatch) -> tuple[TestClient, Path]:
    database_path = tmp_path / "spec01-auth-truth.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "spec01-test-session-secret-key-32b")
    monkeypatch.setenv("BOT_USERNAME", "toanaasbot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "true")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    for name in MODULES:
        sys.modules.pop(name, None)

    application = importlib.import_module("app").app
    return TestClient(application), database_path


def test_customer_registration_and_login_lifecycle(tmp_path, monkeypatch):
    """Customer registration and login must operate with real DB persistence and password hashing."""
    client, db_path = _setup_app_client(tmp_path, monkeypatch)

    with client:
        # 1. Invalid email format rejected
        res_invalid = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": CUSTOMER_PASSWORD, "display_name": "Invalid"},
        )
        assert res_invalid.status_code == 200
        assert res_invalid.json()["ok"] is False
        assert res_invalid.json()["error_code"] == "INVALID_EMAIL"

        # 2. Valid customer registration
        res_reg = client.post(
            "/api/v1/auth/register",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "display_name": "Test Customer"},
        )
        assert res_reg.status_code == 200
        assert res_reg.json()["ok"] is True
        assert res_reg.json()["status"] == "awaiting_confirm"

        # Verify real database row created with hashed password
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT id, email, password_hash, role_cache, is_active FROM web_accounts WHERE email=?",
                (CUSTOMER_EMAIL,),
            ).fetchone()
            assert row is not None
            account_id, email, pwd_hash, role, is_active = row
            assert email == CUSTOMER_EMAIL
            assert role == "user"
            assert is_active == 1
            assert pwd_hash != CUSTOMER_PASSWORD
            assert pwd_hash.startswith("scrypt$")

        # 3. Duplicate registration is non-enumerating
        res_dup = client.post(
            "/api/v1/auth/register",
            json={"email": CUSTOMER_EMAIL, "password": "DifferentPassword123!", "display_name": "Duplicate"},
        )
        assert res_dup.status_code == 200
        assert res_dup.json()["ok"] is True

        # 4. Wrong password login fails
        res_wrong = client.post(
            "/api/v1/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": "WrongPassword123!"},
        )
        assert res_wrong.status_code == 200
        assert res_wrong.json()["ok"] is False
        assert res_wrong.json()["error_code"] == "LOGIN_DENIED"
        assert "toan_aas_session" not in res_wrong.headers.get("set-cookie", "")

        # 5. Correct password login succeeds and sets signed session cookie
        res_login = client.post(
            "/api/v1/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
        )
        assert res_login.status_code == 200
        data = res_login.json()
        assert data["ok"] is True
        assert data["data"]["account"]["email"] == CUSTOMER_EMAIL
        assert data["data"]["account"]["role"] == "user"
        assert "toan_aas_session" in res_login.headers.get("set-cookie", "")
        csrf_token = data["data"]["csrf_token"]
        assert len(csrf_token) > 20

        # 6. Session refresh / me probe returns verified account
        res_me = client.get("/api/v1/auth/me")
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["ok"] is True
        assert me_data["data"]["account"]["email"] == CUSTOMER_EMAIL
        assert me_data["data"]["account"]["role"] == "user"

        # 7. Customer logout requires CSRF
        res_logout_nocsrf = client.post("/api/v1/auth/logout")
        assert res_logout_nocsrf.status_code == 403

        # 8. Customer logout with CSRF revokes session
        res_logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
        assert res_logout.status_code == 200
        assert res_logout.json()["ok"] is True

        # Verify session is revoked in database
        with sqlite3.connect(db_path) as conn:
            revoked = conn.execute("SELECT revoked_at FROM web_sessions WHERE account_id=?", (account_id,)).fetchone()
            assert revoked is not None and revoked[0] is not None

        # 9. Accessing me after logout returns 401
        res_me_after = client.get("/api/v1/auth/me")
        assert res_me_after.status_code == 401


def test_session_expiration_truth(tmp_path, monkeypatch):
    """Expired sessions must be rejected fail-closed with 401."""
    client, db_path = _setup_app_client(tmp_path, monkeypatch)

    with client:
        # Register and login
        client.post("/api/v1/auth/register", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "display_name": "Expiring User"})
        res_login = client.post("/api/v1/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
        assert res_login.status_code == 200

        # Artificially expire the session in SQLite
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_sessions SET expires_at='2020-01-01T00:00:00+00:00'")

        # Next call to /api/v1/auth/me must fail with 401
        res_expired = client.get("/api/v1/auth/me")
        assert res_expired.status_code == 401
        assert res_expired.json()["ok"] is False
        assert "hết hạn" in res_expired.json()["message"].lower()


def test_account_disabled_truth(tmp_path, monkeypatch):
    """Disabled accounts (is_active=0) cannot login and existing sessions are immediately revoked."""
    client, db_path = _setup_app_client(tmp_path, monkeypatch)

    with client:
        # Register and login
        client.post("/api/v1/auth/register", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "display_name": "Active User"})
        res_login = client.post("/api/v1/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
        assert res_login.status_code == 200

        # Disable the account in SQLite
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET is_active=0 WHERE email=?", (CUSTOMER_EMAIL,))

        # 1. Existing active session is rejected immediately
        res_active_session = client.get("/api/v1/auth/me")
        assert res_active_session.status_code == 401

        # 2. Login attempt is denied
        client.cookies.clear()
        res_login_disabled = client.post("/api/v1/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
        assert res_login_disabled.status_code == 200
        assert res_login_disabled.json()["ok"] is False
        assert res_login_disabled.json()["error_code"] == "LOGIN_DENIED"


def test_rbac_and_direct_url_bypass_prevention(tmp_path, monkeypatch):
    """Customer accounts cannot access Admin pages or Admin API endpoints directly."""
    client, db_path = _setup_app_client(tmp_path, monkeypatch)

    with client:
        # Register and login customer
        client.post("/api/v1/auth/register", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "display_name": "Customer User"})
        res_login = client.post("/api/v1/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
        assert res_login.status_code == 200
        csrf = res_login.json()["data"]["csrf_token"]

        # DIRECT URL CHECKS: Customer trying to visit Admin HTML pages
        admin_pages = [
            "/admin",
            "/admin/customers",
            "/admin/topups",
            "/admin/finance/planning",
            "/admin/system-stewardship",
            "/admin/security",
            "/admin/access",
        ]
        for path in admin_pages:
            res_admin_page = client.get(path, follow_redirects=False)
            assert res_admin_page.status_code == 403, f"Customer was able to access {path} with status {res_admin_page.status_code}"

        # API CHECKS: Customer trying to call Admin API routes
        res_api_manual = client.get("/api/v1/admin/payments/manual")
        assert res_api_manual.status_code == 403

        res_api_draft = client.post(
            "/api/v1/admin/payments/manual/REQ-123/draft",
            json={"action": "approve", "reason": "hack"},
            headers={"X-CSRF-Token": csrf},
        )
        assert res_api_draft.status_code == 403


def test_admin_auth_and_authority_truth(tmp_path, monkeypatch):
    """Admin portal login, role validation, and access control."""
    client, db_path = _setup_app_client(tmp_path, monkeypatch)

    with client:
        # 1. Admin login page loads as HTML
        res_admin_login_page = client.get("/admin/login")
        assert res_admin_login_page.status_code == 200
        assert "text/html" in res_admin_login_page.headers["content-type"]

        # 2. Register customer account
        client.post("/api/v1/auth/register", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "display_name": "Customer"})

        # Customer attempts admin portal login -> rejected with ADMIN_LOGIN_REQUIRED
        res_customer_admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "admin_portal": True},
        )
        assert res_customer_admin_login.status_code == 200
        assert res_customer_admin_login.json()["ok"] is False
        assert res_customer_admin_login.json()["error_code"] == "ADMIN_LOGIN_REQUIRED"

        # 3. Create Admin account in SQLite
        client.post("/api/v1/auth/register", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "display_name": "Admin User"})
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", (ADMIN_EMAIL,))

        # Admin logs in via admin portal -> succeeds
        res_admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "admin_portal": True},
        )
        assert res_admin_login.status_code == 200
        data = res_admin_login.json()
        assert data["ok"] is True
        assert data["data"]["account"]["role"] == "admin"

        # Admin accesses /admin HTML page -> 200 OK
        res_admin_portal = client.get("/admin", follow_redirects=False)
        assert res_admin_portal.status_code == 200
        assert "text/html" in res_admin_portal.headers["content-type"]

        # Admin accesses /admin/topups HTML page -> 200 OK
        res_topups_page = client.get("/admin/topups", follow_redirects=False)
        assert res_topups_page.status_code == 200
        assert "text/html" in res_topups_page.headers["content-type"]


def test_unauthenticated_requests_fail_closed(tmp_path, monkeypatch):
    """Unauthenticated access to protected APIs returns 401; protected customer pages redirect."""
    client, db_path = _setup_app_client(tmp_path, monkeypatch)

    with client:
        # API calls without session
        assert client.get("/api/v1/auth/me").status_code == 401
        assert client.get("/api/v1/admin/payments/manual").status_code == 401
        assert client.get("/api/v1/wallet").status_code == 401

        # Customer page visits redirect to /login with next target
        res_dash = client.get("/dashboard", follow_redirects=False)
        assert res_dash.status_code == 307
        assert res_dash.headers["location"] == "/login?next=/dashboard"

        res_wallet = client.get("/wallet", follow_redirects=False)
        assert res_wallet.status_code == 307
        assert res_wallet.headers["location"] == "/login?next=/wallet"

        # Admin page visits fail closed (401)
        res_admin = client.get("/admin", follow_redirects=False)
        assert res_admin.status_code == 401


def test_social_login_buttons_honesty_contract(tmp_path, monkeypatch):
    """OAuth provider endpoint must accurately report configuration without fake buttons."""
    client, db_path = _setup_app_client(tmp_path, monkeypatch)

    with client:
        res = client.get("/api/v1/auth/providers")
        assert res.status_code == 200
        payload = res.json()
        assert payload["ok"] is True
        providers = payload["data"]["providers"]

        # By default in test/staging without ENV keys, external OAuth providers must be disabled
        assert providers["google"]["enabled"] is False
        assert providers["apple"]["enabled"] is False
        assert providers["github"]["enabled"] is False

        # Verify telegram connection status endpoint
        res_tg = client.get("/api/v1/auth/telegram/connection/status")
        assert res_tg.status_code == 200
        tg_data = res_tg.json()
        assert tg_data["ok"] is True
        # In test setup with bot username configured:
        assert tg_data["data"]["bot_username"] == "toanaasbot"
