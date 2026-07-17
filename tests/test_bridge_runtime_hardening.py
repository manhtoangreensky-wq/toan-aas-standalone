"""Focused contracts for guarded Core Bridge runtime behavior."""

from __future__ import annotations

import importlib
import sys

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from copyfast_bridge import CoreBridgeClient


@pytest.mark.anyio
@pytest.mark.parametrize(
    "base_url",
    (
        "http://bridge.invalid",
        "https://bridge.invalid/extra-path",
        "https://bridge-token@bridge.invalid",
        "https://bridge.invalid?private=query",
        "https://[not-an-ipv6",
    ),
)
async def test_unsafe_bridge_base_url_stays_in_a_sanitized_guard(base_url: str) -> None:
    secret = "runtime-hardening-secret-must-not-leak"
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True, "status": "completed", "message": "unexpected"})

    result = await CoreBridgeClient(
        base_url=base_url,
        token=secret,
        hmac_secret=secret,
        transport=httpx.MockTransport(handler),
    ).request("GET", "/internal/v1/jobs")

    assert result == {
        "ok": False,
        "status": "guarded",
        "message": "Hệ thống đang bảo trì/nâng cấp. TOAN AAS chưa xử lý và chưa trừ Xu. Vui lòng thử lại sau.",
        "data": {},
        "error_code": "CORE_BRIDGE_INVALID_CONFIGURATION",
    }
    assert calls == []
    assert secret not in repr(result)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "failure",
    (
        httpx.InvalidURL("runtime-hardening-secret-must-not-leak"),
        httpx.RemoteProtocolError("runtime-hardening-secret-must-not-leak"),
    ),
)
async def test_httpx_client_failures_use_the_same_sanitized_guard(failure: Exception) -> None:
    secret = "runtime-hardening-secret-must-not-leak"
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise failure

    result = await CoreBridgeClient(
        base_url="https://bridge.invalid",
        token=secret,
        hmac_secret=secret,
        transport=httpx.MockTransport(handler),
    ).request("GET", "/internal/v1/jobs")

    assert result["ok"] is False
    assert result["status"] == "guarded"
    assert result["error_code"] == "CORE_BRIDGE_UNAVAILABLE"
    assert secret not in repr(result)
    # GET remains the existing retry-safe category; the error never escapes
    # into FastAPI as a 500 on either attempt.
    assert calls == 2


def _app_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "runtime-hardening.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "runtime-hardening-session-secret")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.delenv("WEBAPP_REQUIRE_CORE_BRIDGE", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    sys.modules.pop("app", None)
    return TestClient(importlib.import_module("app").app)


def test_unknown_api_and_internal_gets_do_not_fall_back_to_the_portal(tmp_path, monkeypatch) -> None:
    with _app_client(tmp_path, monkeypatch) as client:
        unknown_api = client.get("/api/v1/does-not-exist")
        unknown_internal = client.get("/internal/v1/does-not-exist")
        api_root = client.get("/api/")
        internal_root = client.get("/internal/")
        public_portal = client.get("/welcome")

    for response in (unknown_api, unknown_internal, api_root, internal_root):
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["ok"] is False
        assert response.json()["error_code"] == "REQUEST_INVALID"
    assert public_portal.status_code == 200
    assert public_portal.headers["content-type"].startswith("text/html")


def test_explicit_release_gate_rejects_invalid_bridge_before_startup(monkeypatch) -> None:
    monkeypatch.setenv("WEBAPP_REQUIRE_CORE_BRIDGE", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://runtime-hardening-secret-must-not-leak")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "runtime-hardening-secret-must-not-leak")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "runtime-hardening-secret-must-not-leak")
    application_module = importlib.import_module("app")

    async def exercise() -> None:
        async with application_module.lifespan(FastAPI()):
            raise AssertionError("invalid opt-in bridge configuration reached readiness")

    with pytest.raises(RuntimeError, match="WEBAPP_REQUIRE_CORE_BRIDGE") as failure:
        import anyio

        anyio.run(exercise)
    assert "runtime-hardening-secret-must-not-leak" not in str(failure.value)
