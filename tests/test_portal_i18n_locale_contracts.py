"""Focused contracts for the closed Web interface locale preference."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]

# Reload the signed Web stack against each temporary SQLite database.  The
# locale is intentionally a Web profile preference, so no Bot module appears
# in this fixture.
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
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "portal-i18n-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "portal-i18n-test-session-secret")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "portal-i18n@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Portal locale owner",
        },
    )
    assert registered.status_code == 200
    assert registered.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": "portal-i18n@example.com", "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def assert_web_only_boundary(data: dict) -> None:
    boundary = data["boundary"]
    assert boundary["execution"] == "web_native_workspace_setup_profile"
    for field in (
        "bot_called",
        "bridge_called",
        "provider_called",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "publish_action_created",
        "notification_sent",
    ):
        assert boundary[field] is False


def test_interface_locale_accepts_vi_en_zh_persists_and_stays_web_owned(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client)
        initial = client.get("/api/v1/auth/me")
        assert initial.status_code == 200
        assert initial.json()["data"]["account"]["profile"]["locale"] == "vi"

        for locale in ("vi", "en", "zh"):
            updated = client.post(
                "/api/v1/auth/profile",
                headers={"X-CSRF-Token": csrf},
                json={
                    "display_name": "Portal locale owner",
                    "locale": locale,
                    "timezone": "Asia/Ho_Chi_Minh",
                    # Browser-supplied identity/role and workflow language are
                    # not part of this Web presentation preference contract.
                    "canonical_user_id": "forged-telegram-id",
                    "role": "admin",
                    "workflow_language": "ja",
                },
            )
            assert updated.status_code == 200
            body = updated.json()
            assert body["ok"] is True
            account = body["data"]["account"]
            assert account["profile"]["locale"] == locale
            assert account["role"] == "user"
            assert "canonical_user_id" not in updated.text

            setup = client.get("/api/v1/workspace/setup")
            assert setup.status_code == 200
            assert setup.json()["data"]["preferences"] == {
                "locale": locale,
                "timezone": "Asia/Ho_Chi_Minh",
            }
            assert_web_only_boundary(setup.json()["data"])

        persisted = client.get("/api/v1/auth/me")
        assert persisted.status_code == 200
        assert persisted.json()["data"]["account"]["profile"]["locale"] == "zh"

        unsupported = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf},
            json={"display_name": "Portal locale owner", "locale": "zh-CN", "timezone": "Asia/Ho_Chi_Minh"},
        )
        assert unsupported.status_code == 200
        assert unsupported.json()["ok"] is False
        assert unsupported.json()["error_code"] == "PROFILE_LOCALE_INVALID"
        assert client.get("/api/v1/auth/me").json()["data"]["account"]["profile"]["locale"] == "zh"

        csrf_denied = client.post(
            "/api/v1/auth/profile",
            json={"display_name": "No CSRF", "locale": "zh", "timezone": "Asia/Ho_Chi_Minh"},
        )
        assert csrf_denied.status_code == 403


def test_workspace_setup_locale_projection_is_closed_and_never_a_workflow_language() -> None:
    integration = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    start = integration.index("const INTERFACE_LOCALES")
    finish = integration.index("// Keep the browser catalog closed", start)
    projection = integration[start:finish]

    assert 'const INTERFACE_LOCALES = new Set(["vi", "en", "zh"]);' in projection
    assert "locale: INTERFACE_LOCALES.has(locale) ? locale : \"vi\"" in projection
    for forbidden in ("workflow_language", "source_language", "target_language", "telegram_id", "canonical_user_id", "localStorage.", "sessionStorage."):
        assert forbidden not in projection
