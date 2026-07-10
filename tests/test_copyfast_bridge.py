import httpx
import pytest

from copyfast_bridge import CoreBridgeClient


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
