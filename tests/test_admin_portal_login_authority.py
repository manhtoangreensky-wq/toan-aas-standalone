"""Authority contracts for password login submitted from the Admin portal."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient


EMAIL = "admin-login-contract@example.com"
PASSWORD = "correct-horse-battery-staple"
ROLE_ADMIN = "admin"
ROLE_USER = "user"
MODULES = (
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_mfa", "copyfast_pages",
)


def _make_client(tmp_path, monkeypatch) -> tuple[TestClient, Path]:
    database_path = tmp_path / "admin-login-contract.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "true")
    for name in MODULES:
        sys.modules.pop(name, None)
    application = importlib.import_module("app").app
    return TestClient(application), database_path


def test_admin_login_requires_admin_role_before_session(tmp_path, monkeypatch) -> None:
    client, database_path = _make_client(tmp_path, monkeypatch)
    with client:
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": EMAIL, "password": PASSWORD, "display_name": "Contract User"},
        )
        assert registered.json()["ok"] is True
        with sqlite3.connect(database_path) as conn:
            role = conn.execute(
                "SELECT role_cache FROM web_accounts WHERE email=?", (EMAIL,)
            ).fetchone()[0]
        assert role == ROLE_USER

        denied = client.post(
            "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD, "admin_portal": True},
        )
        assert denied.status_code == 200
        assert denied.json()["ok"] is False
        assert denied.json()["error_code"] == "ADMIN_LOGIN_REQUIRED"
        assert denied.json()["message"] == "Tài khoản này không có quyền truy cập Admin"
        assert "toan_aas_session" not in denied.headers.get("set-cookie", "")
        assert not any("toan_aas_session" in cookie.name for cookie in client.cookies.jar)
        with sqlite3.connect(database_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_sessions").fetchone()[0] == 0
        assert client.get("/admin", follow_redirects=False).status_code == 401

        regular = client.post(
            "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
        assert regular.json()["ok"] is True
        assert regular.json()["data"]["account"]["role"] == ROLE_USER

        client.cookies.clear()
        with sqlite3.connect(database_path) as conn:
            conn.execute(
                "UPDATE web_accounts SET role_cache=? WHERE email=?", (ROLE_ADMIN, EMAIL)
            )
        allowed = client.post(
            "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD, "admin_portal": True},
        )
        assert allowed.json()["ok"] is True
        assert allowed.json()["data"]["account"]["role"] == ROLE_ADMIN
        admin_page = client.get("/admin", follow_redirects=False)
        assert admin_page.status_code == 200
        assert "text/html" in admin_page.headers["content-type"]


def test_admin_login_frontend_sends_authority_intent_and_routes_mfa() -> None:
    source = Path("static/portal/integration.js").read_text(encoding="utf-8")
    login_start = source.index('if (action === "auth-login")')
    mfa_start = source.index('if (action === "auth-mfa-login")', login_start)
    login_block = source[login_start:mfa_start]
    mfa_end = source.index('if (action === "auth-mfa-login-cancel")', mfa_start)
    mfa_block = source[mfa_start:mfa_end]

    assert login_block.index("const isAdminLogin") < login_block.index('api("/auth/login"')
    assert "admin_portal: isAdminLogin" in login_block
    assert 'result.data.account.role !== "admin"' in login_block
    admin_route = 'window.location.assign(isAdminLogin ? "/admin" : (requested || "/dashboard"));'
    assert admin_route in login_block
    assert "const isAdminLogin" in mfa_block
    assert 'result.data.account.role !== "admin"' in mfa_block
    assert admin_route in mfa_block
