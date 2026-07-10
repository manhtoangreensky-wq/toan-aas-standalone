import asyncio

import httpx
import pytest
from starlette.requests import Request

from copyfast_bridge import CoreBridgeClient
from copyfast_api import FeatureRequest, PaymentRequest, _bridge, _feature_action, admin_retry_job, create_payment
from copyfast_db import ensure_copyfast_schema


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
    result = await client.request("GET", "/internal/v1/jobs", actor_id="telegram-1", request_id="browser-correlation-id")
    assert result["ok"] is True
    assert len(calls) == 2
    bridge_request_ids = [call.headers["x-toan-aas-request-id"] for call in calls]
    assert len(set(bridge_request_ids)) == 2
    assert "browser-correlation-id" not in bridge_request_ids

    calls.clear()
    failed_write = await client.request("POST", "/internal/v1/features/chat/draft", payload={"prompt": "x"}, actor_id="telegram-1")
    assert failed_write["error_code"] == "CORE_BRIDGE_UNAVAILABLE"
    assert len(calls) == 1


@pytest.mark.anyio
async def test_bridge_redacts_nested_runtime_details_before_the_browser_boundary():
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "ok": True,
            "status": "completed",
            "message": "ok",
            "data": {
                "public_url": "https://example.invalid/allowed-metadata",
                "job": {"provider_task_id": "private-task", "output_path": "C:/private/output.mp4", "status": "completed"},
                "items": [{"id": "safe", "api_key": "private-key"}, {"id": "safe-2", "raw_response": {"secret": "no"}}],
            },
        })

    client = CoreBridgeClient(
        base_url="https://bridge.invalid",
        token="bridge-token",
        hmac_secret="bridge-hmac",
        transport=httpx.MockTransport(handler),
    )
    result = await client.request("GET", "/internal/v1/jobs", actor_id="telegram-1")
    assert result["data"] == {
        "public_url": "https://example.invalid/allowed-metadata",
        "job": {"status": "completed"},
        "items": [{"id": "safe"}, {"id": "safe-2"}],
    }


@pytest.mark.anyio
async def test_web_bridge_redacts_canonical_identity_from_nested_browser_data(monkeypatch):
    async def fake_bridge_request(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "ok",
            "data": {
                "user": {"user_id": "telegram-1", "username": "private-name", "is_vip": True},
                "items": [{"id": "job-1", "canonical_user_id": "telegram-1", "chat_id": "123"}],
                "wallet": {"balance": 42, "telegram_username": "private-name"},
            },
            "error_code": None,
        }

    monkeypatch.setitem(_bridge.__globals__, "bridge_request", fake_bridge_request)
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/wallet", "headers": []})
    result = await _bridge(
        "GET",
        "/internal/v1/wallet",
        account={"id": "web-account", "canonical_user_id": "telegram-1"},
        request=request,
    )
    assert result["data"] == {"user": {"is_vip": True}, "items": [{"id": "job-1"}], "wallet": {"balance": 42}}


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
async def test_feature_action_rejects_browser_bypass_of_web_intake_contract(monkeypatch):
    """File/identity contracts must hold even when a caller skips portal JS."""
    calls = []

    async def fake_bridge(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True, "status": "draft", "message": "unexpected", "data": {}, "error_code": None}

    monkeypatch.setitem(_feature_action.__globals__, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/features/image_transform/draft", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    cases = [
        ("image_transform", {"prompt": "Đổi nền thành studio"}, "upload_required"),
        ("documents_merge", {"upload_ids": ["staged-one"]}, "multiple_uploads_required"),
        ("documents_merge", {"upload_ids": [f"staged-{index}" for index in range(9)]}, "too_many_uploads"),
        ("voice_clone", {"upload_ids": ["staged-audio"], "consent": False}, "voice_clone_consent_required"),
        ("music_song", {"brief": "Bài hát giới thiệu sản phẩm", "mode": "lyrics", "song_length_mode": "seconds"}, "song_duration_required"),
        ("subtitle_translate", {"upload_ids": ["staged-subtitle"], "target_language": "xx"}, "target_language_invalid"),
        ("video_single", {"prompt": "Video mới", "nested": {"user_id": "browser-forged"}}, "authority_field_not_allowed"),
    ]
    for feature, values, reason in cases:
        result = await _feature_action("draft", feature, FeatureRequest(input=values), request, account)
        assert result["status"] == "guarded"
        assert result["error_code"] == "FEATURE_INPUT_CONTRACT_REQUIRED"
        assert result["data"] == {"feature": feature, "reason": reason}
    assert calls == []


@pytest.mark.anyio
async def test_feature_action_forwards_all_canonical_translation_language_codes(monkeypatch):
    calls = []

    async def fake_bridge(method, path, *, account, request, payload=None, params=None):
        calls.append({"method": method, "path": path, "payload": payload})
        return {"ok": True, "status": "draft", "message": "ok", "data": {}, "error_code": None}

    monkeypatch.setitem(_feature_action.__globals__, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/features/subtitle_translate/draft", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    for feature, target in (("subtitle_translate", "th"), ("video_dub", "AR"), ("documents_translate", "zh_tw")):
        result = await _feature_action(
            "draft",
            feature,
            FeatureRequest(input={"upload_ids": [f"staged-{feature}"], "target_language": target}),
            request,
            account,
        )
        assert result["ok"] is True
    assert [item["payload"]["input"]["target_language"] for item in calls] == ["th", "ar", "zh_tw"]


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


@pytest.mark.anyio
async def test_post_bridge_overwrites_a_forged_canonical_identity(monkeypatch):
    captured = {}

    async def fake_bridge_request(method, path, *, payload=None, params=None, request_id=None, actor_id=""):
        captured.update({"method": method, "path": path, "payload": payload, "params": params, "actor_id": actor_id})
        return {"ok": True, "status": "draft", "message": "ok", "data": {}, "error_code": None}

    monkeypatch.setitem(_bridge.__globals__, "bridge_request", fake_bridge_request)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/features/chat/draft", "headers": []})
    result = await _bridge(
        "POST",
        "/internal/v1/features/chat/draft",
        account={"id": "web-account", "canonical_user_id": "telegram-1"},
        request=request,
        payload={"user_id": "browser-forged", "input": {"request": "hello"}},
    )
    assert result["ok"] is True
    assert captured["payload"]["user_id"] == "telegram-1"
    assert captured["actor_id"] == "telegram-1"


@pytest.mark.anyio
async def test_payment_idempotency_reserves_the_key_before_any_second_bridge_call(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "idempotency.db"))
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
    ensure_copyfast_schema()
    calls = []

    async def fake_bridge(method, path, *, account, request, payload=None, params=None):
        calls.append({"method": method, "path": path, "payload": payload})
        await asyncio.sleep(0.03)
        return {"ok": True, "status": "awaiting_confirm", "message": "ok", "data": {"payment_id": "p-1"}, "error_code": None}

    monkeypatch.setitem(create_payment.__globals__, "_bridge", fake_bridge)
    monkeypatch.setitem(create_payment.__globals__, "_payment_topup_catalog_available", lambda: True)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/payments/create", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    payload = PaymentRequest(package_id="pkg-basic", payment_type="topup_xu", idempotency_key="payment-reserve-0001")
    first, second = await asyncio.gather(
        create_payment(payload, request, account),
        create_payment(payload, request, account),
    )
    assert len(calls) == 1
    assert {first["error_code"], second["error_code"]} == {None, "IDEMPOTENCY_IN_PROGRESS"}
    cached = await create_payment(payload, request, account)
    assert cached["data"] == {"payment_id": "p-1"}
    assert len(calls) == 1


@pytest.mark.anyio
async def test_web_payment_creation_requires_a_dedicated_topup_catalog_before_the_bridge(monkeypatch):
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
    calls = []

    async def fake_bridge(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True, "status": "completed", "message": "unexpected", "data": {}, "error_code": None}

    monkeypatch.setitem(create_payment.__globals__, "_bridge", fake_bridge)
    monkeypatch.setitem(create_payment.__globals__, "_payment_topup_catalog_available", lambda: False)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/payments/create", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    result = await create_payment(
        PaymentRequest(package_id="starter_monthly", payment_type="topup_xu", idempotency_key="payment-catalog-guard-0001"),
        request,
        account,
    )
    assert result["status"] == "guarded"
    assert result["error_code"] == "PAYMENT_TOPUP_CATALOG_REQUIRED"
    assert calls == []


@pytest.mark.anyio
async def test_web_payment_creation_rejects_non_topup_types_before_the_bridge(monkeypatch):
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
    calls = []

    async def fake_bridge(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True, "status": "completed", "message": "unexpected", "data": {}, "error_code": None}

    monkeypatch.setitem(create_payment.__globals__, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/payments/create", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    result = await create_payment(
        PaymentRequest(package_id="storage-custom", payment_type="storage_addon", idempotency_key="payment-type-guard-0001"),
        request,
        account,
    )
    assert result["status"] == "guarded"
    assert result["error_code"] == "PAYMENT_TYPE_NOT_ALLOWED"
    assert calls == []


@pytest.mark.anyio
async def test_admin_write_gate_does_not_contact_canonical_bridge_when_disabled(monkeypatch):
    local_checks = []
    canonical_checks = []
    bridge_calls = []

    def fake_local_admin(_request):
        local_checks.append(True)
        return {"id": "web-admin", "canonical_user_id": "telegram-admin", "role": "admin"}

    async def fake_canonical_admin(_request):
        canonical_checks.append(True)
        return {"id": "web-admin", "canonical_user_id": "telegram-admin", "role": "admin"}

    async def fake_bridge(*args, **kwargs):
        bridge_calls.append((args, kwargs))
        return {"ok": True, "status": "completed", "message": "unexpected", "data": {}, "error_code": None}

    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "false")
    monkeypatch.setitem(admin_retry_job.__globals__, "require_admin_csrf", fake_local_admin)
    monkeypatch.setitem(admin_retry_job.__globals__, "require_canonical_admin_csrf", fake_canonical_admin)
    monkeypatch.setitem(admin_retry_job.__globals__, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/admin/jobs/job-1/retry", "headers": []})
    result = await admin_retry_job("job-1", FeatureRequest(input={}, idempotency_key="admin-write-gate-0001"), request)
    assert result["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"
    assert local_checks == [True]
    assert canonical_checks == []
    assert bridge_calls == []


@pytest.mark.anyio
async def test_web_feature_flags_guard_bridge_calls_before_identity_or_network(monkeypatch):
    calls = []

    async def fake_bridge_request(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True, "status": "completed", "message": "unexpected", "data": {}, "error_code": None}

    monkeypatch.setitem(_bridge.__globals__, "bridge_request", fake_bridge_request)
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/wallet", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}

    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "false")
    disabled = await _bridge("GET", "/internal/v1/wallet", account=account, request=request)
    assert disabled["status"] == "guarded"
    assert disabled["error_code"] == "WEBAPP_COPYFAST_DISABLED"
    assert calls == []

    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
    admin_disabled = await _bridge("GET", "/internal/v1/admin/summary", account=account, request=request)
    assert admin_disabled["status"] == "guarded"
    assert admin_disabled["error_code"] == "WEBAPP_ADMIN_ERP_DISABLED"
    assert calls == []
