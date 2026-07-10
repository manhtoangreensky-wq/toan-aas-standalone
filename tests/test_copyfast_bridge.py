import httpx
import pytest
from starlette.requests import Request

from copyfast_bridge import CoreBridgeClient
from copyfast_api import FeatureRequest, _bridge, _feature_action


@pytest.mark.anyio
async def test_bridge_signs_request_and_removes_sensitive_data():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer bridge-token"
        assert request.headers["x-toan-aas-signature"]
        return httpx.Response(200, json={
            "ok": True,
            "status": "completed",
            "message": "ok",
            "data": {"public_url": "https://example.invalid/file", "provider_task_id": "secret-task", "raw_response": {"x": 1}},
            "error_code": None,
        })

    client = CoreBridgeClient(
        base_url="https://bridge.invalid",
        token="bridge-token",
        hmac_secret="bridge-hmac",
        transport=httpx.MockTransport(handler),
    )
    result = await client.request("POST", "/internal/v1/features/video_single/draft", payload={"prompt": "hello"}, actor_id="telegram-1")
    assert result["ok"] is True
    assert result["data"] == {"public_url": "https://example.invalid/file"}


@pytest.mark.anyio
async def test_unconfigured_bridge_is_guarded():
    result = await CoreBridgeClient(base_url="", token="", hmac_secret="").request("GET", "/internal/v1/wallet")
    assert result["status"] == "guarded"
    assert result["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"


@pytest.mark.anyio
async def test_retry_only_uses_safe_or_idempotent_requests():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("temporary", request=request)
        return httpx.Response(200, json={"ok": True, "status": "completed", "message": "ok", "data": {}})

    client = CoreBridgeClient(
        base_url="https://bridge.invalid",
        token="bridge-token",
        hmac_secret="bridge-hmac",
        transport=httpx.MockTransport(handler),
    )
    result = await client.request("GET", "/internal/v1/jobs", actor_id="telegram-1")
    assert result["ok"] is True
    assert len(calls) == 2

    calls.clear()
    failed_write = await client.request("POST", "/internal/v1/features/chat/draft", payload={"prompt": "x"}, actor_id="telegram-1")
    assert failed_write["error_code"] == "CORE_BRIDGE_UNAVAILABLE"
    assert len(calls) == 1


@pytest.mark.anyio
async def test_feature_action_preserves_form_input_inside_the_core_contract(monkeypatch):
    captured = {}

    async def fake_bridge(method, path, *, account, request, payload=None, params=None):
        captured.update({"method": method, "path": path, "account": account, "payload": payload, "params": params})
        return {"ok": True, "status": "draft", "message": "ok", "data": {}, "error_code": None}

    # Other API tests deliberately reload the app modules. Patch the function
    # globals of this imported coroutine so this contract assertion remains
    # independent from that isolation strategy.
    monkeypatch.setitem(_feature_action.__globals__, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/features/video_single/draft", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    result = await _feature_action(
        "draft",
        "video_single",
        FeatureRequest(input={"prompt": "Video sản phẩm", "duration": "8"}),
        request,
        account,
    )
    assert result["status"] == "draft"
    assert captured["path"] == "/internal/v1/features/video_single/draft"
    assert captured["payload"] == {
        "input": {"prompt": "Video sản phẩm", "duration": "8"},
        "idempotency_key": None,
    }


@pytest.mark.anyio
async def test_get_bridge_keeps_canonical_identity_when_a_safe_filter_is_added(monkeypatch):
    captured = {}

    async def fake_bridge_request(method, path, *, payload=None, params=None, request_id=None, actor_id=""):
        captured.update({"method": method, "path": path, "payload": payload, "params": params, "actor_id": actor_id})
        return {"ok": True, "status": "read_only", "message": "ok", "data": {}, "error_code": None}

    monkeypatch.setitem(_bridge.__globals__, "bridge_request", fake_bridge_request)
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/admin/modules/users", "headers": []})
    result = await _bridge(
        "GET",
        "/internal/v1/admin/modules/users",
        account={"id": "web-account", "canonical_user_id": "telegram-1"},
        request=request,
        params={"record_id": "telegram-1", "user_id": "browser-forged"},
    )
    assert result["ok"] is True
    assert captured["payload"] is None
    assert captured["params"] == {"record_id": "telegram-1", "user_id": "telegram-1"}
    assert captured["actor_id"] == "telegram-1"
