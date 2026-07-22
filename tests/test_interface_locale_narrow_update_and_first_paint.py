"""Critical contracts for the signed Web interface-locale update flow."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "app",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_registry",
    "copyfast_api",
    "copyfast_pages",
    "copyfast_projects",
    "copyfast_assets",
    "copyfast_project_packages",
    "copyfast_document_operations",
    "copyfast_image_runtime",
    "copyfast_image_operations",
    "copyfast_memory",
    "copyfast_workspace_setup",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "interface-locale-narrow-update.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "interface-locale-narrow-update-secret")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, *, email: str, name: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": name},
    )
    assert registered.status_code == 200
    assert registered.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def profile(client: TestClient) -> dict:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    return response.json()["data"]["account"]


def test_narrow_interface_locale_write_preserves_other_profile_fields_and_account_scope(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, email="locale-a@example.com", name="Locale A")
        full_profile = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf_a},
            json={"display_name": "A name that must stay", "locale": "vi", "timezone": "UTC"},
        )
        assert full_profile.status_code == 200
        changed = client.post(
            "/api/v1/auth/profile/interface-locale",
            headers={"X-CSRF-Token": csrf_a},
            json={"locale": " zh "},
        )
        assert changed.status_code == 200
        assert changed.headers["cache-control"] == "no-store, private"
        body = changed.json()
        assert body["ok"] is True
        assert body["data"] == {"profile": {"locale": "zh"}}
        assert "canonical_user_id" not in changed.text
        assert profile(client)["display_name"] == "A name that must stay"
        assert profile(client)["profile"] == {"locale": "zh", "timezone": "UTC", "avatar_style": "gradient"}

        # A forged additional field is rejected by the dedicated schema rather
        # than silently mutating any other account field.
        forged = client.post(
            "/api/v1/auth/profile/interface-locale",
            headers={"X-CSRF-Token": csrf_a},
            json={"locale": "en", "display_name": "forged", "role": "admin", "workflow_language": "ja"},
        )
        assert forged.status_code == 422
        assert forged.headers["cache-control"] == "no-store, private"
        assert profile(client)["profile"]["locale"] == "zh"

        for invalid in ("zh-CN", "ja", "auto"):
            rejected = client.post(
                "/api/v1/auth/profile/interface-locale",
                headers={"X-CSRF-Token": csrf_a},
                json={"locale": invalid},
            )
            assert rejected.status_code == 200
            assert rejected.json()["ok"] is False
            assert rejected.json()["error_code"] == "PROFILE_LOCALE_INVALID"
            assert profile(client)["profile"]["locale"] == "zh"

        assert client.post(
            "/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_a}
        ).status_code == 200
        csrf_b = register_and_login(client, email="locale-b@example.com", name="Locale B")
        changed_b = client.post(
            "/api/v1/auth/profile/interface-locale",
            headers={"X-CSRF-Token": csrf_b},
            json={"locale": "en"},
        )
        assert changed_b.json()["ok"] is True
        assert profile(client)["profile"]["locale"] == "en"

        assert client.post(
            "/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_b}
        ).status_code == 200
        signed_back_into_a = client.post(
            "/api/v1/auth/login",
            json={"email": "locale-a@example.com", "password": "correct-horse-battery-staple"},
        )
        assert signed_back_into_a.status_code == 200
        restored_a = profile(client)
        assert restored_a["display_name"] == "A name that must stay"
        assert restored_a["profile"] == {"locale": "zh", "timezone": "UTC", "avatar_style": "gradient"}


def test_interface_locale_write_requires_signed_csrf_and_has_a_dedicated_raw_body_cap(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        unsigned = client.post("/api/v1/auth/profile/interface-locale", json={"locale": "en"})
        assert unsigned.status_code == 401

        csrf = register_and_login(client, email="locale-guard@example.com", name="Locale guard")
        no_csrf = client.post("/api/v1/auth/profile/interface-locale", json={"locale": "en"})
        assert no_csrf.status_code == 403

        too_large = client.post(
            "/api/v1/auth/profile/interface-locale",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content='{"locale":"' + ("z" * 4096) + '"}',
        )
        assert too_large.status_code == 413
        assert too_large.headers["cache-control"] == "no-store, private"
        assert too_large.json()["error_code"] == "WEB_INTERFACE_LOCALE_BODY_TOO_LARGE"


def test_signed_first_paint_uses_only_server_profile_locale_and_public_login_stays_vi(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, email="locale-shell@example.com", name="Locale shell")
        updated = client.post(
            "/api/v1/auth/profile/interface-locale",
            headers={"X-CSRF-Token": csrf},
            json={"locale": "zh"},
        )
        assert updated.json()["ok"] is True
        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.headers["cache-control"] == "no-store, private"
        assert '<html lang="zh-CN" dir="ltr" data-portal-locale="zh">' in dashboard.text
        assert "<title>概览 · TOAN AAS</title>" in dashboard.text
        assert "正在启动 TOAN AAS…" in dashboard.text
        assert '"interfaceLocale": "zh"' in dashboard.text
        assert "locale-shell@example.com" not in dashboard.text

        app = client.app
        with TestClient(app) as anonymous:
            login = anonymous.get("/login?locale=zh")
            assert login.status_code == 200
            assert '<html lang="vi" dir="ltr" data-portal-locale="vi">' in login.text
            assert '"interfaceLocale": "vi"' in login.text
            assert "Đang khởi tạo giao diện TOAN AAS…" in login.text


def test_locale_navigator_uses_only_the_narrow_receipt_and_endpoint() -> None:
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    integration = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")

    view_start = portal.index("function renderInterfaceLocaleNavigator")
    view_end = portal.index("function renderAccountSecurity", view_start)
    view = portal[view_start:view_end]
    assert 'data-portal-action="update-interface-locale"' in view
    for forbidden in ('name="display_name"', 'name="timezone"', "canonical_user_id", "telegram_id", "localStorage", "sessionStorage"):
        assert forbidden not in view

    action_start = integration.index('if (action === "update-interface-locale") {')
    action_end = integration.index('if (action === "upgrade-telegram-account") {', action_start)
    action = integration[action_start:action_end]
    payload_start = integration.index("function interfaceLocaleUpdatePayload")
    payload_end = integration.index("function confirmedProfileInterfaceLocale", payload_start)
    payload = integration[payload_start:payload_end]
    receipt_start = integration.index("function confirmedInterfaceLocaleReceipt")
    receipt_end = integration.index("function applyConfirmedProfileInterfaceLocale", receipt_start)
    receipt = integration[receipt_start:receipt_end]

    assert 'api("/auth/profile/interface-locale"' in action
    assert "interfaceLocaleUpdatePayload(fields)" in action
    assert "confirmedInterfaceLocaleReceipt(result)" in action
    assert action.index("applyConfirmedProfileInterfaceLocale") < action.index("await hydrate()")
    assert "return { locale: profileUpdateInterfaceLocale(source.locale) };" in payload
    assert "result.data && result.data.profile" in receipt
    for forbidden in ("display_name", "timezone", "canonical_user_id", "telegram_id", "role", "workflow_language", "localStorage", "sessionStorage"):
        assert forbidden not in payload
        assert forbidden not in receipt
