import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException
from starlette.responses import RedirectResponse
from starlette.requests import Request

from copyfast_bridge import CoreBridgeClient
from copyfast_api import (
    FeatureRequest, PaymentRequest, _bridge, _feature_action, _payment_topup_packages,
    admin_module, admin_retry_job, asset_download, create_payment, job_detail,
    payment_status, wallet_history,
)
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
                "balance_xu": 42,
                "total_spent_xu": 9,
                "is_vip": True,
                "user": {"user_id": "telegram-1", "username": "private-name"},
                "items": [{"id": "job-1", "canonical_user_id": "telegram-1", "chat_id": "123"}],
                "wallet": {"balance": 42, "telegram_username": "private-name"},
                "bank_account": "must-not-reach-browser",
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
    assert result["data"] == {"balance_xu": 42, "total_spent_xu": 9, "is_vip": True}


@pytest.mark.anyio
async def test_canonical_admin_read_can_keep_only_erp_user_references(monkeypatch):
    async def fake_bridge_request(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "ok",
            "data": {
                "items": [{
                    "user_id": "telegram-user-ref",
                    "username": "customer_public_name",
                    "canonical_user_id": "must-stay-server-side",
                    "chat_id": "must-stay-server-side",
                }],
            },
            "error_code": None,
        }

    monkeypatch.setitem(_bridge.__globals__, "bridge_request", fake_bridge_request)
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/admin/users", "headers": []})
    result = await _bridge(
        "GET",
        "/internal/v1/admin/users",
        account={"id": "web-admin", "canonical_user_id": "telegram-admin", "role": "admin"},
        request=request,
        admin_read=True,
    )
    assert result["data"] == {"items": [{"user_id": "telegram-user-ref", "username": "customer_public_name"}]}


@pytest.mark.anyio
async def test_wallet_history_drops_unrendered_ledger_notes_and_references(monkeypatch):
    async def fake_bridge(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "ok",
            "data": {
                "reference": "top-level-private-order",
                "note": "top-level-private-note",
                "next_cursor": "private-cursor",
                "items": [{
                    "id": "wallet-event-private-id",
                    "event_type": "charge",
                    "delta_xu": -12,
                    "balance_after_xu": 88,
                    "created_at": "2026-07-11T00:00:00Z",
                    "reference": "order-private",
                    "note": "prompt riêng tư của khách",
                    "provider": "private-provider-context",
                }, "private-receipt-string", {"event_type": ["not-a-scalar"], "delta_xu": "not-a-number"}],
            },
            "debug_context": "private-bridge-detail",
            "error_code": None,
        }

    monkeypatch.setitem(wallet_history.__globals__, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/wallet/history", "headers": []})
    result = await wallet_history(request, {"id": "web-account", "canonical_user_id": "telegram-1"})
    assert result["data"]["items"] == [{
        "event_type": "charge",
        "delta_xu": -12,
        "balance_after_xu": 88,
        "created_at": "2026-07-11T00:00:00Z",
    }]
    assert set(result["data"]) == {"items"}
    assert "private" not in str(result)


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
        ("video_single", {"prompt": "Video mới", "nested": {"canonicalUserId": "browser-forged"}}, "authority_field_not_allowed"),
        ("video_single", {"prompt": "Video mới", "paymentId": "browser-forged"}, "authority_field_not_allowed"),
        ("video_single", {"prompt": "Video mới", "nested": {"output-url": "https://invalid.example/output"}}, "authority_field_not_allowed"),
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
async def test_untrusted_route_identifiers_and_admin_modules_fail_before_the_bridge(monkeypatch):
    """Path fragments must not become a signed internal route or query filter."""
    bridge_calls = []

    async def fake_bridge(*args, **kwargs):
        bridge_calls.append((args, kwargs))
        return {"ok": True, "status": "completed", "message": "unexpected", "data": {}}

    for handler in (payment_status, job_detail, asset_download, admin_module):
        monkeypatch.setitem(handler.__globals__, "_bridge", fake_bridge)
    account = {"id": "web-account", "canonical_user_id": "telegram-1", "role": "admin"}
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/payments/invalid", "headers": []})

    with pytest.raises(HTTPException, match="Mã payment không hợp lệ"):
        await payment_status("../admin/payments", request, account)
    with pytest.raises(HTTPException, match="Mã job không hợp lệ"):
        await job_detail("job?other=1", request, account)
    with pytest.raises(HTTPException, match="Mã tài sản không hợp lệ"):
        await asset_download("asset/../secret", request, account)
    with pytest.raises(HTTPException, match="Module Admin chưa được công bố"):
        await admin_module("private-runtime", request, account)
    record_request = Request({
        "type": "http", "method": "GET", "path": "/api/v1/admin/modules/users",
        "query_string": b"record_id=../other-user", "headers": [],
    })
    with pytest.raises(HTTPException, match="ID bản ghi không hợp lệ"):
        await admin_module("users", record_request, account)
    assert bridge_calls == []


@pytest.mark.anyio
async def test_asset_delivery_redirect_requires_an_explicit_temporary_canonical_contract(tmp_path, monkeypatch):
    """Asset metadata cannot become a provider URL or an open redirect."""
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "asset-delivery.db"))
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_DELIVERY_ALLOWED_HOSTS", "downloads.toanaas.vn")
    captured = {}
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    async def approved_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id=""):
        captured.update({"method": method, "path": path, "payload": payload, "params": params, "actor_id": actor_id})
        return {
            "ok": True,
            "status": "completed",
            "message": "internal only",
            "data": {
                "asset_id": "asset-001",
                "download_ready": True,
                "delivery_ready": True,
                "delivery": {"url": "https://downloads.toanaas.vn/private/file?signature=opaque", "expires_at": expiry},
            },
            "error_code": None,
        }

    monkeypatch.setitem(asset_download.__globals__, "bridge_request", approved_bridge)
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/assets/asset-001/download", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    response = await asset_download("asset-001", request, account)
    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307
    assert response.headers["location"] == "https://downloads.toanaas.vn/private/file?signature=opaque"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert captured == {
        "method": "GET",
        "path": "/internal/v1/assets/asset-001/download",
        "payload": None,
        "params": {"user_id": "telegram-1"},
        "actor_id": "telegram-1",
    }

    async def rejected_bridge(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "internal only",
            "data": {
                "asset_id": "asset-001",
                "download_ready": True,
                "delivery_ready": True,
                "delivery": {"url": "https://evil.invalid/private?token=must-not-leak", "expires_at": expiry},
            },
            "error_code": None,
        }

    monkeypatch.setitem(asset_download.__globals__, "bridge_request", rejected_bridge)
    rejected = await asset_download("asset-001", request, account)
    assert isinstance(rejected, dict)
    assert rejected["status"] == "guarded"
    assert rejected["error_code"] == "ASSET_DELIVERY_CONTRACT_INVALID"
    assert "evil.invalid" not in str(rejected)
    assert "must-not-leak" not in str(rejected)

    async def wrong_asset_bridge(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "internal only",
            "data": {
                "asset_id": "another-users-asset",
                "download_ready": True,
                "delivery_ready": True,
                "delivery": {"url": "https://downloads.toanaas.vn/private/file?signature=opaque", "expires_at": expiry},
            },
            "error_code": None,
        }

    monkeypatch.setitem(asset_download.__globals__, "bridge_request", wrong_asset_bridge)
    wrong_asset = await asset_download("asset-001", request, account)
    assert isinstance(wrong_asset, dict)
    assert wrong_asset["error_code"] == "ASSET_DELIVERY_NOT_READY"

    async def expired_bridge(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "internal only",
            "data": {
                "asset_id": "asset-001",
                "download_ready": True,
                "delivery_ready": True,
                "delivery": {
                    "url": "https://downloads.toanaas.vn/private/file?signature=expired",
                    "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                },
            },
            "error_code": None,
        }

    monkeypatch.setitem(asset_download.__globals__, "bridge_request", expired_bridge)
    expired = await asset_download("asset-001", request, account)
    assert isinstance(expired, dict)
    assert expired["error_code"] == "ASSET_DELIVERY_CONTRACT_INVALID"


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
async def test_feature_bridge_projection_keeps_planning_but_drops_delivery_and_operator_side_channels(monkeypatch):
    """A future feature adapter must not turn draft/estimate into delivery."""

    async def fake_bridge_request(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "awaiting_confirm",
            "message": "provider debug: https://private.example/trace",
            "error_code": "BRIDGE_DEBUG_SHOULD_NOT_LEAK",
            "data": {
                "feature": "video_single",
                "draft": {
                    "available": True,
                    "source": "canonical_planner",
                    "content": {
                        "script": "Kịch bản planning hợp lệ",
                        "estimated_xu": 18,
                        "preview_url": "https://provider.example/preview",
                        "output": "output giả không được render",
                        "providerTask": "private-task",
                    },
                },
                "estimate": {
                    "available": True,
                    "estimated_xu": 30,
                    "choices": [{"label": "Standard", "cost_xu": 30}],
                    "checkout_url": "https://pay.payos.vn/private-checkout",
                },
                "uploads": [{
                    "id": "stage-1", "file_name": "clip.mp4", "content_size": 12,
                    "provider_id": "private-provider", "download_url": "https://private.example/download",
                }],
                "job_id": "job-private",
                "unrelated_internal_field": "must-not-reach-browser",
            },
        }

    monkeypatch.setitem(_bridge.__globals__, "bridge_request", fake_bridge_request)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/features/video_single/estimate", "headers": []})
    result = await _bridge(
        "POST",
        "/internal/v1/features/video_single/estimate",
        account={"id": "web-account", "canonical_user_id": "telegram-1"},
        request=request,
        payload={"input": {"prompt": "Video giới thiệu"}},
    )

    assert result["message"] == "Dữ liệu canonical đang chờ bước xác nhận phù hợp."
    assert result["error_code"] == "CORE_BRIDGE_RESPONSE_GUARDED"
    assert result["data"] == {
        "feature": "video_single",
        "draft": {
            "available": True,
            "source": "canonical_planner",
            "content": {"script": "Kịch bản planning hợp lệ", "estimated_xu": 18},
        },
        "estimate": {
            "available": True,
            "estimated_xu": 30,
            "choices": [{"label": "Standard", "cost_xu": 30}],
        },
        "uploads": [{"id": "stage-1", "file_name": "clip.mp4", "content_size": 12}],
    }


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
    monkeypatch.setitem(create_payment.__globals__, "_payment_topup_packages", lambda: [{
        "code": "pkg-basic", "label": "Gói cơ bản", "amount_vnd": 10000, "xu": 100, "available": True,
    }])
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
    monkeypatch.setitem(create_payment.__globals__, "_payment_topup_packages", lambda: [])
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
async def test_web_payment_creation_rejects_codes_outside_the_current_canonical_topup_catalog(monkeypatch):
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
    calls = []

    async def fake_bridge(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True, "status": "completed", "message": "unexpected", "data": {}, "error_code": None}

    monkeypatch.setitem(create_payment.__globals__, "_bridge", fake_bridge)
    monkeypatch.setitem(create_payment.__globals__, "_payment_topup_packages", lambda: [{
        "code": "topup-100", "label": "100 Xu", "amount_vnd": 10000, "xu": 100, "available": True,
    }])
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/payments/create", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    result = await create_payment(
        PaymentRequest(package_id="forged-package", payment_type="topup_xu", idempotency_key="payment-outside-catalog-0001"),
        request,
        account,
    )
    assert result["status"] == "failed"
    assert result["error_code"] == "PAYMENT_PACKAGE_NOT_IN_CATALOG"
    assert calls == []


def test_payment_topup_catalog_projects_only_selectable_well_formed_skus(monkeypatch):
    monkeypatch.setitem(_payment_topup_packages.__globals__, "_payment_topup_catalog", lambda: [
        {"code": "topup-100", "label": "100 Xu", "amount_vnd": 10000, "xu": 100, "available": True, "internal_note": "do-not-leak"},
        {"code": "topup-100", "label": "Duplicate", "amount_vnd": 20000, "xu": 200, "available": True},
        {"code": "invalid code with spaces", "label": "Bad", "amount_vnd": 10000, "xu": 100, "available": True},
        {"code": "hidden", "label": "Hidden", "amount_vnd": 10000, "xu": 100, "available": False},
        {"code": "zero", "label": "Zero", "amount_vnd": 0, "xu": 0, "available": True},
    ])
    assert _payment_topup_packages() == [{
        "code": "topup-100", "label": "100 Xu", "amount_vnd": 10000, "xu": 100, "available": True,
    }]


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
