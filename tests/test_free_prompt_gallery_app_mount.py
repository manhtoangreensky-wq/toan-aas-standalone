"""Production-entrypoint contract for the Web Free Prompt Gallery mount."""

from __future__ import annotations

import importlib
import sys

from fastapi.testclient import TestClient


def _app_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "gallery-app-mount.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "gallery-app-mount-session-secret")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "gallery-app-mount-callback-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "gallery-app-mount-callback-hmac")
    monkeypatch.setenv("WEBAPP_CONTENT_STUDIO_ENABLED", "true")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    sys.modules.pop("app", None)
    return TestClient(importlib.import_module("app").app)


def test_production_entrypoint_mounts_the_signed_free_prompt_gallery(tmp_path, monkeypatch) -> None:
    with _app_client(tmp_path, monkeypatch) as client:
        path = "/api/v1/free-prompt-gallery/catalog"
        assert client.get(path).status_code == 401

        registered = client.post(
            "/api/v1/auth/register",
            json={
                "email": "gallery-mounted@example.com",
                "password": "correct-horse-battery-staple",
                "display_name": "Gallery Mounted",
            },
        )
        assert registered.status_code == 200
        signed_in = client.post(
            "/api/v1/auth/login",
            json={"email": "gallery-mounted@example.com", "password": "correct-horse-battery-staple"},
        )
        assert signed_in.status_code == 200

        response = client.get(path)

    assert response.status_code == 200
    cache_directives = {item.strip() for item in response.headers["cache-control"].split(",")}
    assert {"private", "no-store"}.issubset(cache_directives)
    assert response.json()["data"]["total_items"] == 140
    assert response.json()["data"]["boundaries"]["bot_called"] is False
