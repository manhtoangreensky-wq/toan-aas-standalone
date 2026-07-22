"""Production-entrypoint contract for the signed Web Guide Center mount."""

from __future__ import annotations

import importlib
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app",
    "config",
    "db",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_auth_throttle",
    "copyfast_bridge",
    "copyfast_registry",
    "copyfast_api",
    "copyfast_pages",
    "copyfast_guide_center",
]


def _app_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "guide-center-app-mount.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "guide-center-app-mount-session-secret")
    monkeypatch.setenv("WEBAPP_AUTH_THROTTLE_HMAC_SECRET", "guide-center-app-mount-throttle-secret")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "guide-center-app-mount-callback-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "guide-center-app-mount-callback-hmac")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def test_production_entrypoint_mounts_the_signed_profile_localized_guide_center(tmp_path, monkeypatch) -> None:
    with _app_client(tmp_path, monkeypatch) as client:
        path = "/api/v1/guides/catalog"
        assert client.get(path).status_code == 401

        registered = client.post(
            "/api/v1/auth/register",
            json={
                "email": "guide-mounted@example.com",
                "password": "correct-horse-battery-staple",
                "display_name": "Guide Mounted",
            },
        )
        assert registered.status_code == 200
        signed_in = client.post(
            "/api/v1/auth/login",
            json={"email": "guide-mounted@example.com", "password": "correct-horse-battery-staple"},
        )
        assert signed_in.status_code == 200
        csrf = signed_in.json()["data"]["csrf_token"]

        initial = client.get(path, params={"locale": "en"}, headers={"Accept-Language": "en-US"})
        assert initial.status_code == 200
        assert initial.json()["data"]["locale"] == "vi"

        locale = client.post(
            "/api/v1/auth/profile/interface-locale",
            headers={"X-CSRF-Token": csrf},
            json={"locale": "zh"},
        )
        assert locale.status_code == 200
        response = client.get(path, params={"locale": "vi"}, headers={"Accept-Language": "en-US"})

    assert response.status_code == 200
    cache_directives = {item.strip() for item in response.headers["cache-control"].split(",")}
    assert {"private", "no-store"}.issubset(cache_directives)
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    data = response.json()["data"]
    assert data["locale"] == "zh"
    assert sum(len(group["topics"]) for group in data["groups"]) == 10
    assert data["boundaries"]["bot_called"] is False
    assert data["boundaries"]["bridge_called"] is False
    assert data["boundaries"]["job_created"] is False
