"""Contracts for the signed, read-only Community Trust Center."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


WEB_ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "copyfast_db",
    "copyfast_auth",
    "copyfast_auth_throttle",
    "copyfast_community_trust",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "community-trust.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-community-trust-session-secret")
    monkeypatch.setenv("BOT_USERNAME", "toanaasbot")
    monkeypatch.setenv("WEBAPP_COMMUNITY_URL", "https://t.me/+TrustedToanAas")
    monkeypatch.setenv("WEBAPP_OFFICIAL_SITE_URL", "https://toanaas.vn")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)

    auth = importlib.import_module("copyfast_auth")
    trust = importlib.import_module("copyfast_community_trust")
    application = FastAPI()
    application.include_router(auth.router, prefix="/api/v1/auth")
    application.include_router(trust.router)
    return TestClient(application)


def login(client: TestClient) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "community-owner@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Community Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": "community-owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return str(signed_in.json()["data"]["csrf_token"])


def channel_by_id(data: dict, channel_id: str) -> dict:
    return next(item for item in data["channels"] if item["id"] == channel_id)


def assert_false_boundaries(data: dict) -> None:
    assert data["boundaries"] == {
        "execution": "web_native_community_trust_center",
        "snapshot_read_only": True,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "wallet_mutated": False,
        "payment_started": False,
        "job_created": False,
        "asset_saved": False,
        "notification_sent": False,
    }


def test_trust_center_requires_a_signed_session_and_returns_only_safe_configured_links(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        path = "/api/v1/community/trust-center"
        assert client.get(path).status_code == 401
        csrf = login(client)
        assert csrf

        response = client.get(path, params={"locale": "en"}, headers={"Accept-Language": "en-US"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    data = response.json()["data"]
    assert data["snapshot_version"] == "2026-07-27.1"
    assert data["locale"] == "vi"
    assert [item["id"] for item in data["channels"]] == ["website", "workspace", "telegram_bot", "community", "support"]
    website = channel_by_id(data, "website")
    assert website["kind"] == "external"
    assert website["availability"] == "ready"
    assert website["url"] == "https://toanaas.vn"
    assert website["title"]
    assert website["summary"]
    assert channel_by_id(data, "workspace")["route"] == "/dashboard"
    assert channel_by_id(data, "telegram_bot")["url"] == "https://t.me/toanaasbot"
    assert channel_by_id(data, "community")["url"] == "https://t.me/+TrustedToanAas"
    assert channel_by_id(data, "support")["route"] == "/support"
    assert "OTP" in " ".join(data["safety"]["checks"])
    assert_false_boundaries(data)


def test_invalid_or_missing_external_configuration_is_guarded_without_a_url(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        monkeypatch.setenv("WEBAPP_COMMUNITY_URL", "https://evil.example/t.me/+not-toanaas")
        monkeypatch.setenv("WEBAPP_OFFICIAL_SITE_URL", "https://toanaas.vn/?tracking=1")
        monkeypatch.setenv("BOT_USERNAME", "BOT_USERNAME")
        login(client)
        response = client.get("/api/v1/community/trust-center")

    assert response.status_code == 200
    data = response.json()["data"]
    for channel_id, expected_setting in (
        ("website", "WEBAPP_OFFICIAL_SITE_URL"),
        ("telegram_bot", "BOT_USERNAME"),
        ("community", "WEBAPP_COMMUNITY_URL"),
    ):
        item = channel_by_id(data, channel_id)
        assert item["availability"] == "guarded"
        assert "url" not in item
        assert item["missing_config"] == [expected_setting]
    assert_false_boundaries(data)


def test_catalog_is_fresh_and_has_no_runtime_adapter_imports(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-community-trust-static-secret")
    for name in MODULES:
        sys.modules.pop(name, None)
    trust = importlib.import_module("copyfast_community_trust")

    first = trust.trust_center_catalog("en")
    first["channels"][0]["title"] = "corrupted"
    second = trust.trust_center_catalog("en")

    assert second["locale"] == "en"
    assert second["channels"][0]["title"] != "corrupted"
    assert_false_boundaries(second)
    source = (WEB_ROOT / "copyfast_community_trust.py").read_text(encoding="utf-8")
    for forbidden in ("copyfast_bridge", "copyfast_api", "requests", "httpx", "telegram_id", "callback_data"):
        assert forbidden not in source
