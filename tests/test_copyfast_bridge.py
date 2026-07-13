from datetime import datetime, timedelta, timezone

import anyio
import httpx
import pytest
from fastapi import HTTPException
from starlette.responses import RedirectResponse
from starlette.requests import Request

from copyfast_bridge import CoreBridgeClient
from copyfast_api import (
    FeatureRequest, FreezeRequest, PaymentRequest, TicketRequest, _bridge, _feature_action, _payment_topup_packages,
    _project_surface_data,
    admin_freeze_feature, admin_module, admin_refund_job, admin_retry_job, asset_download, create_payment, job_detail,
    create_support_ticket, payment_status, wallet_history,
)
from copyfast_db import ensure_copyfast_schema, transaction


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

    # A download route can mint a temporary delivery credential. It is a GET
    # syntactically, but it is intentionally not retried as a safe read.
    calls.clear()
    failed_delivery = await client.request("GET", "/internal/v1/assets/asset-1/download", actor_id="telegram-1")
    assert failed_delivery["error_code"] == "CORE_BRIDGE_UNAVAILABLE"
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
async def test_feature_confirm_adapter_is_explicitly_gated_and_idempotent(tmp_path, monkeypatch):
    """Confirm needs a server receipt and may queue only once per receipt/key."""
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "feature-confirm.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "feature-receipt-test-secret")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    ensure_copyfast_schema()
    calls = []

    async def fake_bridge(method, path, *, account, request, payload=None, params=None):
        calls.append({"method": method, "path": path, "account": account, "payload": payload, "params": params})
        if path.endswith("/estimate"):
            return {"ok": True, "status": "awaiting_confirm", "message": "Estimate canonical.", "data": {"estimate": {"available": True}}, "error_code": None}
        return {"ok": True, "status": "queued", "message": "Đã vào queue canonical.", "data": {}, "error_code": None}

    globals_map = _feature_action.__globals__
    monkeypatch.setitem(globals_map, "_bridge", fake_bridge)
    monkeypatch.setitem(globals_map, "bridge_configured", lambda: True)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/features/video_single/confirm", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    values = {"prompt": "Video sản phẩm", "tier": "video-standard", "scene_count": 1}
    payload = FeatureRequest(input=values, idempotency_key="feature-confirm-adapter-0001")

    disabled = await _feature_action("confirm", "video_single", payload, request, account)
    assert disabled["status"] == "guarded"
    assert disabled["error_code"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"
    assert calls == []

    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    no_feature_allowlist = await _feature_action("confirm", "video_single", payload, request, account, session_id="feature-session-1")
    assert no_feature_allowlist["error_code"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"
    assert calls == []

    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "image_create,unknown_feature")
    wrong_feature_allowlist = await _feature_action("confirm", "video_single", payload, request, account, session_id="feature-session-1")
    assert wrong_feature_allowlist["error_code"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"
    assert calls == []

    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_single")
    missing = await _feature_action("confirm", "video_single", payload, request, account, session_id="feature-session-1")
    assert missing["error_code"] == "FEATURE_ESTIMATE_REQUIRED"
    assert calls == []

    estimate = await _feature_action("estimate", "video_single", FeatureRequest(input=values), request, account, session_id="feature-session-1")
    receipt = estimate["data"]["web_quote_receipt"]
    assert isinstance(receipt, str) and len(receipt) >= 32
    with transaction() as conn:
        stored = conn.execute("SELECT token_hash, input_digest, session_id FROM web_feature_quote_receipts").fetchone()
    assert stored is not None
    assert receipt not in " ".join(str(value) for value in stored)
    assert "Video sản phẩm" not in " ".join(str(value) for value in stored)
    assert stored[2] == "feature-session-1"

    with_wrong_session = await _feature_action(
        "confirm", "video_single",
        FeatureRequest(input=values, idempotency_key="feature-confirm-adapter-0001", web_quote_receipt=receipt),
        request, account, session_id="other-session",
    )
    assert with_wrong_session["error_code"] == "FEATURE_ESTIMATE_REQUIRED"
    first = await _feature_action(
        "confirm", "video_single",
        FeatureRequest(input=values, idempotency_key="feature-confirm-adapter-0001", web_quote_receipt=receipt),
        request, account, session_id="feature-session-1",
    )
    duplicate = await _feature_action(
        "confirm", "video_single",
        FeatureRequest(input=values, idempotency_key="feature-confirm-adapter-0001", web_quote_receipt=receipt),
        request, account, session_id="feature-session-1",
    )
    assert first == duplicate
    assert first["status"] == "queued"
    replay = await _feature_action(
        "confirm", "video_single",
        FeatureRequest(input=values, idempotency_key="feature-confirm-adapter-0002", web_quote_receipt=receipt),
        request, account, session_id="feature-session-1",
    )
    assert replay["error_code"] == "FEATURE_ESTIMATE_ALREADY_USED"
    assert [item["path"] for item in calls] == [
        "/internal/v1/features/video_single/estimate",
        "/internal/v1/features/video_single/confirm",
    ]
    assert calls[1]["payload"] == {"input": values, "idempotency_key": "feature-confirm-adapter-0001"}


@pytest.mark.anyio
async def test_bot_companion_registry_keys_can_never_call_dynamic_engine_feature_routes():
    """Navigation-only Bot handoffs must not become a generic bridge API."""
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/features/notes/draft", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    with pytest.raises(HTTPException) as denied:
        await _feature_action("draft", "notes", FeatureRequest(input={"request": "do not forward"}), request, account)
    assert denied.value.status_code == 404


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
        ("documents", {"upload_ids": ["staged-image"], "operation": "image_to_pdf"}, "web_native_image_to_pdf_required"),
        ("documents_pdf", {"upload_ids": ["staged-image"], "operation": "image-to-pdf"}, "web_native_image_to_pdf_required"),
        ("documents", {"upload_ids": ["staged-document"], "operation": "unsafe_custom_converter"}, "document_operation_invalid"),
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

    # Older FastAPI/Starlette versions intentionally leave ``str(exc)``
    # empty, so assert the public HTTP detail rather than relying on a
    # framework-version-specific exception string.
    with pytest.raises(HTTPException) as payment_error:
        await payment_status("../admin/payments", request, account)
    assert payment_error.value.status_code == 422
    assert payment_error.value.detail == "Mã payment không hợp lệ"
    with pytest.raises(HTTPException) as job_error:
        await job_detail("job?other=1", request, account)
    assert job_error.value.status_code == 422
    assert job_error.value.detail == "Mã job không hợp lệ"
    with pytest.raises(HTTPException) as asset_error:
        await asset_download("asset/../secret", request, account)
    assert asset_error.value.status_code == 422
    assert asset_error.value.detail == "Mã tài sản không hợp lệ"
    with pytest.raises(HTTPException) as module_error:
        await admin_module("private-runtime", request, account)
    assert module_error.value.status_code == 404
    assert module_error.value.detail == "Module Admin chưa được công bố"
    record_request = Request({
        "type": "http", "method": "GET", "path": "/api/v1/admin/modules/users",
        "query_string": b"record_id=../other-user", "headers": [],
    })
    with pytest.raises(HTTPException) as record_error:
        await admin_module("users", record_request, account)
    assert record_error.value.status_code == 422
    assert record_error.value.detail == "ID bản ghi không hợp lệ"
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


def test_feature_tracking_reference_is_explicit_feature_bound_and_has_no_delivery_channel() -> None:
    valid = _project_surface_data({
        "feature": "video_single",
        "status": "queued",
        "tracking": {
            "id": "production_jobs:42",
            "status": "queued",
            "feature": "video_single",
            "provider_task_id": "private-provider-task",
            "download_url": "https://private.example/output",
            "output_path": "C:/private/output.mp4",
        },
        "job_id": "must-not-be-inferred",
    }, "feature")
    assert valid == {
        "feature": "video_single",
        "status": "queued",
        "tracking": {"id": "production_jobs:42", "status": "queued", "feature": "video_single"},
    }

    for tracking in (
        {"id": "production_jobs:42", "status": "queued", "feature": "image_create"},
        {"id": "../../private", "status": "queued", "feature": "video_single"},
        {"id": "production_jobs:42", "status": "guarded", "feature": "video_single"},
        {"id": "production_jobs:42", "status": "queued", "feature": "unknown_feature"},
    ):
        projected = _project_surface_data({"feature": "video_single", "tracking": tracking}, "feature")
        assert "tracking" not in projected


@pytest.mark.anyio
async def test_payment_idempotency_reserves_the_key_before_any_second_bridge_call(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "idempotency.db"))
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
    ensure_copyfast_schema()
    calls = []

    async def fake_bridge(method, path, *, account, request, payload=None, params=None):
        calls.append({"method": method, "path": path, "payload": payload})
        await anyio.sleep(0.03)
        return {
            "ok": True,
            "status": "awaiting_confirm",
            "message": "ok",
            "data": {
                "payment_id": "p-1", "order_code": "order-1", "amount_vnd": 10000,
                "xu": 100, "checkout_url": "https://pay.payos.vn/checkout/opaque-one-time",
            },
            "error_code": None,
        }

    monkeypatch.setitem(create_payment.__globals__, "_bridge", fake_bridge)
    monkeypatch.setitem(create_payment.__globals__, "_payment_topup_packages", lambda: [{
        "code": "pkg-basic", "label": "Gói cơ bản", "amount_vnd": 10000, "xu": 100, "available": True,
    }])
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/payments/create", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    payload = PaymentRequest(package_id="pkg-basic", payment_type="topup_xu", idempotency_key="payment-reserve-0001")
    results = []

    async def submit_duplicate() -> None:
        results.append(await create_payment(payload, request, account))

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(submit_duplicate)
        task_group.start_soon(submit_duplicate)
    first, second = results
    assert len(calls) == 1
    assert {first["error_code"], second["error_code"]} == {None, "IDEMPOTENCY_IN_PROGRESS"}
    # Payment results (including order, Xu and checkout URL) are never cached
    # in Web SQLite. A later retry goes to Bot-side durable idempotency.
    with transaction() as conn:
        stored = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'payment:%'").fetchall()
    assert stored == []
    replay = await create_payment(payload, request, account)
    assert replay["data"]["checkout_url"] == "https://pay.payos.vn/checkout/opaque-one-time"
    assert len(calls) == 2


def test_payment_projection_keeps_only_a_strictly_vetted_payos_checkout_url() -> None:
    raw = {
        "payment_id": "payment-1",
        "order_code": "order-1",
        "amount_vnd": 10000,
        "xu": 100,
        "status": "awaiting_confirm",
        "checkout_url": "https://pay.payos.vn/checkout/opaque?source=bot",
        "provider": "private-provider",
        "bank_account": "must-not-reach-browser",
        "raw_response": {"secret": "must-not-reach-browser"},
    }
    projected = _project_surface_data(raw, "payment")
    assert projected == {
        "payment_id": "payment-1",
        "order_code": "order-1",
        "amount_vnd": 10000,
        "xu": 100,
        "status": "awaiting_confirm",
        "checkout_url": "https://pay.payos.vn/checkout/opaque?source=bot",
    }
    for invalid in (
        "http://pay.payos.vn/checkout/opaque",
        "https://pay.payos.vn.evil.example/checkout/opaque",
        "https://user:pass@pay.payos.vn/checkout/opaque",
        "https://pay.payos.vn:444/checkout/opaque",
        "https://pay.payos.vn/checkout/opaque#fragment",
    ):
        assert "checkout_url" not in _project_surface_data({"checkout_url": invalid}, "payment")


@pytest.mark.anyio
async def test_support_rejects_manual_payment_proof_before_idempotency_or_bridge(monkeypatch):
    calls = []

    async def fake_bridge(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True, "status": "completed", "message": "unexpected", "data": {}, "error_code": None}

    monkeypatch.setitem(create_support_ticket.__globals__, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/support/tickets", "headers": []})
    account = {"id": "web-account", "canonical_user_id": "telegram-1"}
    for detail in (
        "TXID: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "Số tài khoản: 12345678901234567890",
        "Tôi sẽ gửi ảnh bill ở đây",
    ):
        with pytest.raises(HTTPException) as error:
            await create_support_ticket(
                TicketRequest(subject="Nạp thủ công", detail=detail, idempotency_key="manual-proof-block-0001"),
                request,
                account,
            )
        assert error.value.status_code == 422
        assert "/thucong" in str(error.value.detail)
    assert calls == []


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
async def test_admin_write_gate_does_not_contact_canonical_bridge_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "admin-write-disabled.db"))
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
    with transaction() as conn:
        audit = conn.execute("SELECT action, target, outcome FROM web_audit_events").fetchall()
    assert audit == [("admin.job.retry", "job-1", "denied")]


@pytest.mark.anyio
async def test_admin_erp_gate_short_circuits_writes_before_canonical_role_check(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "admin-erp-disabled.db"))
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
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

    globals_map = admin_retry_job.__globals__
    monkeypatch.setitem(globals_map, "require_admin_csrf", fake_local_admin)
    monkeypatch.setitem(globals_map, "require_canonical_admin_csrf", fake_canonical_admin)
    monkeypatch.setitem(globals_map, "_bridge", fake_bridge)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/admin/jobs/job-1/retry", "headers": []})
    result = await admin_retry_job("job-1", FeatureRequest(input={}, idempotency_key="admin-erp-gate-0001"), request)
    assert result["error_code"] == "WEBAPP_ADMIN_ERP_DISABLED"
    assert local_checks == [True]
    assert canonical_checks == []
    assert bridge_calls == []


@pytest.mark.anyio
async def test_admin_write_adapters_require_local_and_canonical_role_then_preserve_idempotency(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "admin-write.db"))
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    ensure_copyfast_schema()
    local_checks = []
    canonical_checks = []
    calls = []

    def fake_local_admin(_request):
        local_checks.append(True)
        return {"id": "web-admin", "canonical_user_id": "telegram-admin", "role": "admin"}

    async def fake_canonical_admin(_request):
        canonical_checks.append(True)
        return {"id": "web-admin", "canonical_user_id": "telegram-admin", "role": "admin"}

    async def fake_bridge(method, path, *, account, request, payload=None, params=None, admin_read=False):
        calls.append({"method": method, "path": path, "account": account, "payload": payload, "params": params, "admin_read": admin_read})
        return {"ok": True, "status": "queued", "message": "canonical accepted", "data": {"id": path.rsplit("/", 1)[0]}, "error_code": None}

    globals_map = admin_retry_job.__globals__
    monkeypatch.setitem(globals_map, "require_admin_csrf", fake_local_admin)
    monkeypatch.setitem(globals_map, "require_canonical_admin_csrf", fake_canonical_admin)
    monkeypatch.setitem(globals_map, "_bridge", fake_bridge)
    retry_request = Request({"type": "http", "method": "POST", "path": "/api/v1/admin/jobs/job-1/retry", "headers": []})
    retry = await admin_retry_job("job-1", FeatureRequest(input={}, idempotency_key="admin-retry-key-0001"), retry_request)
    retry_duplicate = await admin_retry_job("job-1", FeatureRequest(input={}, idempotency_key="admin-retry-key-0001"), retry_request)
    refund = await admin_refund_job("job-1", FeatureRequest(input={}, idempotency_key="admin-refund-key-0001"), retry_request)
    freeze = await admin_freeze_feature("video_single", FreezeRequest(frozen=True, note="Provider maintenance", idempotency_key="admin-freeze-key-0001"), retry_request)
    assert retry["ok"] is retry_duplicate["ok"] is refund["ok"] is freeze["ok"] is True
    assert local_checks == [True, True, True, True]
    assert canonical_checks == [True, True, True, True]
    assert [call["path"] for call in calls] == [
        "/internal/v1/admin/jobs/job-1/retry",
        "/internal/v1/admin/jobs/job-1/refund",
        "/internal/v1/admin/features/video_single/freeze",
    ]
    assert calls[0]["payload"] == {"idempotency_key": "admin-retry-key-0001"}
    assert calls[1]["payload"] == {"idempotency_key": "admin-refund-key-0001"}
    assert calls[2]["payload"] == {"frozen": True, "note": "Provider maintenance", "idempotency_key": "admin-freeze-key-0001"}
    assert all(call["account"]["canonical_user_id"] == "telegram-admin" for call in calls)
    with transaction() as conn:
        audit = conn.execute("SELECT action, target, outcome FROM web_audit_events").fetchall()
    assert sorted(row[0] for row in audit) == ["admin.feature.freeze", "admin.job.refund", "admin.job.retry", "admin.job.retry"]
    assert all(row[2] == "ok" for row in audit)


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
