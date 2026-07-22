"""Focused contracts for the signed, read-only Web Guide Center."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


WEB_ROOT = Path(__file__).resolve().parents[1]
MODULES = ["copyfast_db", "copyfast_auth", "copyfast_auth_throttle", "copyfast_guide_center"]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "guide-center.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-guide-center-session-secret")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)

    auth = importlib.import_module("copyfast_auth")
    guides = importlib.import_module("copyfast_guide_center")
    application = FastAPI()
    application.include_router(auth.router, prefix="/api/v1/auth")
    application.include_router(guides.router)
    return TestClient(application)


def login(client: TestClient) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "guide-owner@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Guide Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": "guide-owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return str(signed_in.json()["data"]["csrf_token"])


def assert_boundaries(data: dict) -> None:
    assert data["boundaries"] == {
        "execution": "web_native_guide_center",
        "snapshot_read_only": True,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "content_published": False,
        "media_delivered": False,
    }


def test_catalog_requires_signed_session_and_has_a_closed_web_snapshot(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        path = "/api/v1/guides/catalog"
        assert client.get(path).status_code == 401
        csrf = login(client)
        assert csrf

        response = client.get(path, params={"locale": "en"}, headers={"Accept-Language": "en-US"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    payload = response.json()
    data = payload["data"]
    assert payload["ok"] is True
    assert data["snapshot_version"] == "2026-07-22.1"
    # Browser query/header values cannot replace the signed profile locale.
    assert data["locale"] == "vi"
    assert [group["id"] for group in data["groups"]] == ["start", "create", "media", "organize", "safe"]
    assert [topic["id"] for group in data["groups"] for topic in group["topics"]] == [
        "getting_started",
        "find_tools",
        "content_brief",
        "prompt_library",
        "image_preparation",
        "audio_brief",
        "notes",
        "reminders",
        "safe_workspace",
        "get_support",
    ]
    assert all(topic["route"].startswith("/") for group in data["groups"] for topic in group["topics"])
    assert_boundaries(data)


def test_catalog_uses_only_the_signed_profile_locale(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client)
        changed = client.post(
            "/api/v1/auth/profile/interface-locale",
            headers={"X-CSRF-Token": csrf},
            json={"locale": "zh"},
        )
        assert changed.status_code == 200

        response = client.get(
            "/api/v1/guides/catalog",
            params={"locale": "vi"},
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["locale"] == "zh"
    assert data["ui"]["heading"] == "无需记住命令，也能找到正确的下一步。"
    assert_boundaries(data)


def test_snapshot_is_fresh_closed_data_without_runtime_adapters(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-guide-center-static-secret")
    for name in MODULES:
        sys.modules.pop(name, None)
    guides = importlib.import_module("copyfast_guide_center")

    first = guides.guide_catalog("en")
    first["groups"][0]["topics"][0]["steps"][0] = "corrupted"
    second = guides.guide_catalog("en")

    assert second["groups"][0]["topics"][0]["steps"][0] == "Check your account details."
    assert {topic["id"] for group in second["groups"] for topic in group["topics"]} == guides.TOPIC_IDS
    assert all(
        topic["route"] in guides.ROUTE_ALLOWLIST
        for group in second["groups"]
        for topic in group["topics"]
    )
    source = (WEB_ROOT / "copyfast_guide_center.py").read_text(encoding="utf-8")
    for forbidden in ("copyfast_bridge", "copyfast_api", "copyfast_provider", "requests", "httpx"):
        assert forbidden not in source
