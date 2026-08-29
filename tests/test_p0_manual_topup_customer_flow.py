import json
import re
from pathlib import Path

import anyio
import httpx
import pytest
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

import copyfast_api
from copyfast_bridge import CoreBridgeClient
from copyfast_db import ensure_copyfast_schema, transaction


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
OWNER = "123456789"
ACCOUNT = {"id": "web-account", "canonical_user_id": OWNER}


def _request(method: str, path: str) -> Request:
    return Request({"type": "http", "method": method, "path": path, "headers": []})


def _section(source: str, start: str, end: str) -> str:
    left = source.index(start)
    right = source.index(end, left)
    return source[left:right]


@pytest.mark.anyio
async def test_manual_bridge_binds_exact_ascii_owner_and_preserves_list_statuses():
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        status_name = request.url.path.rsplit("/", 1)[-1]
        if status_name not in {"approved", "rejected"}:
            status_name = "pending_admin_review"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "status": status_name,
                "message": "canonical",
                "data": [] if request.url.path.endswith("/empty") else [{"request_id": "MANUAL-1", "secret": "drop"}],
                "error_code": None,
            },
        )

    client = CoreBridgeClient(
        base_url="https://bridge.invalid",
        token="bridge-token",
        hmac_secret="bridge-hmac",
        transport=httpx.MockTransport(handler),
    )
    pending = await client.request("GET", "/internal/v1/payments/manual", owner_id=OWNER)
    assert pending["status"] == "pending_admin_review"
    assert pending["data"] == [{"request_id": "MANUAL-1"}]
    assert calls[0].headers["x-toan-aas-telegram-user-id"] == OWNER

    empty = await client.request("GET", "/empty", owner_id=OWNER)
    assert empty["data"] == []
    for status_name in ("approved", "rejected"):
        result = await client.request("GET", f"/{status_name}", owner_id=OWNER)
        assert result["status"] == status_name

    before = len(calls)
    for invalid in ("0", "-1", " 1", "1 ", "١", "１２", "1" * 21):
        denied = await client.request("GET", "/internal/v1/payments/manual", owner_id=invalid)
        assert denied["status"] == "guarded"
        assert denied["error_code"] == "CORE_BRIDGE_OWNER_INVALID"
    assert len(calls) == before


def test_manual_create_schema_rejects_browser_authority_and_unsafe_values():
    schema = copyfast_api.ManualTopupCreateRequest
    valid = schema(
        amount_vnd=1,
        method="bank_acb_vietqr",
        idempotency_key="manual-schema-0001",
        reference=" tx-safe ",
    )
    assert valid.amount_vnd == 1
    assert valid.reference == "tx-safe"

    invalid_payloads = [
        {"amount_vnd": True},
        {"amount_vnd": "10000"},
        {"amount_vnd": 0},
        {"amount_vnd": -1},
        {"amount_vnd": 9007199254740992},
        {"method": "unknown"},
        {"reference": "bad<ref>"},
        {"reference": "bad\u0000ref"},
        {"reference": None},
        {"idempotency_key": "short"},
        {"user_id": OWNER},
        {"telegram_id": OWNER},
        {"canonical_user_id": OWNER},
        {"expected_xu": 100},
        {"approved_xu": 100},
        {"status": "approved"},
        {"admin_id": "1"},
        {"wallet": {}},
        {"credits": 100},
        {"txid": "browser-owned"},
    ]
    base = {
        "amount_vnd": 10_000,
        "method": "bank_acb",
        "idempotency_key": "manual-schema-0002",
        "reference": "",
    }
    for override in invalid_payloads:
        with pytest.raises(ValidationError):
            schema(**{**base, **override})


@pytest.mark.anyio
async def test_manual_proxy_uses_dedicated_owner_header_without_browser_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "manual-proxy.db"))
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    ensure_copyfast_schema()
    calls = []

    async def fake_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        calls.append({
            "method": method,
            "path": path,
            "payload": payload,
            "params": params,
            "request_id": request_id,
            "actor_id": actor_id,
            "owner_id": owner_id,
        })
        if method == "POST":
            await anyio.sleep(0.03)
            return {
                "ok": True,
                "status": "pending_admin_review",
                "message": "canonical",
                "data": {
                    "request_id": "MANUAL-9",
                    "amount_vnd": 10_000,
                    "method": "bank_acb",
                    "status": "pending_admin_review",
                    "transfer_content": "AAS 9",
                    "raw_response": "drop",
                    "user_id": OWNER,
                },
                "error_code": None,
            }
        if path.endswith("/status"):
            return {
                "ok": True,
                "status": "approved",
                "message": "canonical",
                "data": {"request_id": "MANUAL-9", "status": "approved", "admin_id": "drop"},
                "error_code": None,
            }
        if path.endswith("/manual"):
            return {
                "ok": True,
                "status": "pending_admin_review",
                "message": "canonical",
                "data": [{"request_id": "MANUAL-9", "status": "pending_admin_review", "raw_response": "drop"}],
                "error_code": None,
            }
        return {
            "ok": False,
            "status": "guarded",
            "message": "canonical private message",
            "data": {},
            "error_code": "WEB_MANUAL_TOPUP_NOT_FOUND",
        }

    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)
    payload = copyfast_api.ManualTopupCreateRequest(
        amount_vnd=10_000,
        method="bank_acb",
        idempotency_key="manual-concurrent-0001",
        reference=" tx-safe ",
    )
    results = []

    async def submit() -> None:
        results.append(await copyfast_api.manual_topup_create(payload, _request("POST", "/api/v1/payments/manual"), ACCOUNT))

    async with anyio.create_task_group() as group:
        group.start_soon(submit)
        group.start_soon(submit)
    assert len([call for call in calls if call["method"] == "POST"]) == 1
    assert {result.get("error_code") for result in results} == {None, "IDEMPOTENCY_IN_PROGRESS"}
    post = next(call for call in calls if call["method"] == "POST")
    assert post["path"] == "/internal/v1/payments/manual"
    assert post["owner_id"] == OWNER
    assert post["actor_id"] == OWNER
    assert post["payload"] == {
        "amount_vnd": 10_000,
        "method": "bank_acb",
        "idempotency_key": "manual-concurrent-0001",
        "txid": "tx-safe",
    }
    assert "user_id" not in post["payload"]
    assert "user_id" not in str(results)
    assert "raw_response" not in str(results)
    with transaction() as conn:
        assert conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'manual-topup:%'").fetchall() == []

    replay = await copyfast_api.manual_topup_create(payload, _request("POST", "/api/v1/payments/manual"), ACCOUNT)
    assert replay["ok"] is True
    assert len([call for call in calls if call["method"] == "POST"]) == 2

    history = await copyfast_api.manual_topup_history(_request("GET", "/api/v1/payments/manual"), ACCOUNT, limit=20)
    assert history["data"] == {"items": [{"request_id": "MANUAL-9", "status": "pending_admin_review"}]}
    assert calls[-1]["params"] == {"limit": 20}
    assert calls[-1]["owner_id"] == OWNER

    status_result = await copyfast_api.manual_topup_status("MANUAL-9", _request("GET", "/api/v1/payments/manual/MANUAL-9/status"), ACCOUNT)
    assert status_result["status"] == "approved"
    assert status_result["data"] == {"request_id": "MANUAL-9", "status": "approved"}

    missing = await copyfast_api.manual_topup_detail("MANUAL-404", _request("GET", "/api/v1/payments/manual/MANUAL-404"), ACCOUNT)
    assert isinstance(missing, JSONResponse)
    assert missing.status_code == 404
    missing_payload = json.loads(missing.body)
    assert missing_payload["error_code"] == "MANUAL_TOPUP_NOT_FOUND"
    assert "canonical private" not in missing.body.decode("utf-8")

    before = len(calls)
    for invalid in ("1", "MANUAL-0", "MANUAL--1", "MANUAL-abc", "../MANUAL-1", "MANUAL-" + "1" * 20):
        invalid_result = await copyfast_api.manual_topup_detail(invalid, _request("GET", "/api/v1/payments/manual/invalid"), ACCOUNT)
        assert isinstance(invalid_result, JSONResponse)
        assert invalid_result.status_code == 404
    assert len(calls) == before


def test_manual_portal_has_full_state_lifecycle_and_never_enters_payos_flow():
    guide = _section(PORTAL, "function renderManualTopupGuide(context)", "function renderPaymentRequestForm(page, context)")
    handler = _section(INTEGRATION, 'if (action === "manual-topup-create")', 'if (action === "finance-planning-view")')
    lifecycle = _section(INTEGRATION, "function manualTopupRecord", "async function hydratePaymentOptions")

    for marker in (
        'data-portal-action="manual-topup-create"',
        'data-portal-action="manual-topup-refresh"',
        'name="amount_vnd"',
        'name="method"',
        'name="reference"',
        "manual.methods",
        "context.manualTopupFlow",
        "context.manualTopupHistory",
        "context.manualTopupReadState",
        'role="status"',
        'aria-live="polite"',
    ):
        assert marker in guide
    for marker in (
        "manualTopupFlow:",
        "manualTopupHistory:",
        "manualTopupReadState:",
    ):
        assert marker in PORTAL
        assert marker in INTEGRATION

    for status_name in ("loading", "form", "submitting", "pending_admin_review", "approved", "rejected", "guarded", "failed", "empty"):
        assert status_name in guide or status_name in lifecycle

    assert "const MANUAL_TOPUP_POLL_INTERVAL_MS = 10000;" in INTEGRATION
    assert "const MANUAL_TOPUP_POLL_MAX_ATTEMPTS = 30;" in INTEGRATION
    assert "function scheduleManualTopupPolling" in lifecycle
    assert "manualTopupPollingCanContinue" in lifecycle
    assert 'api(`/payments/manual/${encodeURIComponent(normalized)}/status`)' in lifecycle
    assert 'api("/payments/manual?limit=20")' in lifecycle
    assert 'api("/payments/manual", {' in handler
    assert 'method: "POST"' in handler
    assert "acquireSubmission" in handler
    assert "releaseSubmission" in handler
    assert 'discardSubmission("manual-topup"' not in handler

    forbidden = (
        "payment-create",
        "/payments/create",
        "window.open",
        "schedulePaymentPolling",
        "safePayosCheckout",
        "checkout_url",
        "window.location",
    )
    for marker in forbidden:
        assert marker not in guide
        assert marker not in handler
        assert marker not in lifecycle

    for leaked in (
        "/static/ACBBANK.jpg",
        "/static/momo.jpg",
        "/static/binance_usdt.png",
        "TUqyVeoRhBtFvJmQzaKkqrTVRa1ULNj6o5",
        "0387532320",
        "NAPXU ${userClean}",
        "1 USDT = 26.000",
    ):
        assert leaked not in guide

    payos = _section(INTEGRATION, 'if (action === "payment-create")', 'if (action === "payment-lookup")')
    for protected in ("window.open", 'api("/payments/create"', "safePayosCheckout", "schedulePaymentPolling"):
        assert protected in payos


def test_manual_topup_locale_keysets_and_responsive_controls_are_complete():
    keysets = {}
    for locale, next_locale in (("vi", "en"), ("en", "zh"), ("zh", None)):
        start = f"Object.assign(MANUAL_TOPUP_MESSAGES.{locale}, {{"
        end = f"Object.assign(MANUAL_TOPUP_MESSAGES.{next_locale}, {{" if next_locale else "function verifyEqualKeysets()"
        section = _section(I18N, start, end)
        keysets[locale] = set(re.findall(r'"(manualTopup\.[^"]+)"\s*:', section))
    assert keysets["vi"] == keysets["en"] == keysets["zh"]
    required_suffixes = {
        "title", "description", "guardedTitle", "guardedBody", "amountLabel", "amountPlaceholder",
        "methodLabel", "methodPlaceholder", "referenceLabel", "referencePlaceholder", "submit", "refresh",
        "automaticCreditWarning", "historyTitle", "historyEmpty", "loading", "submitting", "pending",
        "form", "approved", "rejected", "guarded", "failed", "requestId", "amount", "method", "reference", "transferContent",
        "expectedXu", "approvedXu", "submittedAt", "updatedAt", "invalidAmount", "invalidMethod",
        "invalidReference", "inProgress",
    }
    assert {key.rsplit(".", 1)[-1] for key in keysets["vi"]} >= required_suffixes
    assert len(keysets["vi"]) >= len(required_suffixes)
    vi_values = _section(I18N, "Object.assign(MANUAL_TOPUP_MESSAGES.vi, {", "Object.assign(MANUAL_TOPUP_MESSAGES.en, {")
    en_values = _section(I18N, "Object.assign(MANUAL_TOPUP_MESSAGES.en, {", "Object.assign(MANUAL_TOPUP_MESSAGES.zh, {")
    zh_values = _section(I18N, "Object.assign(MANUAL_TOPUP_MESSAGES.zh, {", "function verifyEqualKeysets()")
    assert re.search(r"[À-ỹ]", vi_values)
    assert not re.search(r"[一-鿿]", en_values)
    assert re.search(r"[一-鿿]", zh_values)

    for selector in (
        ".portal-manual-topup-form",
        ".portal-manual-topup-form input",
        ".portal-manual-topup-form select",
        ".portal-manual-topup-form button",
        ".portal-manual-topup-history",
        ".portal-manual-topup-record",
    ):
        assert selector in PORTAL_CSS
    assert "min-height: 44px" in PORTAL_CSS
    assert "@media (max-width: 480px)" in PORTAL_CSS
    assert "@media (prefers-reduced-motion: reduce)" in PORTAL_CSS


def test_manual_topup_routes_and_payos_implementation_stay_isolated():
    source = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    start = source.index('def _manual_topup_request_id')
    end = source.index('def _payos_config()', start)
    manual_api = source[start:end]
    for forbidden in (
        "_create_payos_checkout",
        'httpx.AsyncClient',
        "payos_orders",
        "db_connect",
        "UPDATE users",
        "credit_events",
    ):
        assert forbidden not in manual_api
    assert 'lambda: _manual_topup_bridge(' in manual_api
    assert 'owner_id=owner_id' in manual_api
    assert 'enriched["user_id"]' not in manual_api

    routes = {
        (method, route.path)
        for route in copyfast_api.router.routes
        if getattr(route, "path", "").startswith("/api/v1/payments/manual")
        for method in getattr(route, "methods", set())
    }
    assert routes == {
        ("POST", "/api/v1/payments/manual"),
        ("GET", "/api/v1/payments/manual"),
        ("GET", "/api/v1/payments/manual/{request_id}"),
        ("GET", "/api/v1/payments/manual/{request_id}/status"),
    }

    payos_handler = _section(INTEGRATION, 'if (action === "payment-create")', 'if (action === "payment-lookup")')
    for marker in ("window.open", 'api("/payments/create"', "safePayosCheckout", "schedulePaymentPolling"):
        assert marker in payos_handler


@pytest.mark.anyio
async def test_manual_topup_detail_uses_owner_header_and_preserves_not_found_status(monkeypatch):
    calls = []

    async def fake_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        calls.append({"method": method, "path": path, "payload": payload, "params": params, "owner_id": owner_id})
        return {
            "ok": False,
            "status": "guarded",
            "message": "private bridge detail",
            "data": {"user_id": OWNER, "raw_response": "drop"},
            "error_code": "WEB_MANUAL_TOPUP_NOT_FOUND",
        }

    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)
    result = await copyfast_api.manual_topup_status(
        "MANUAL-77",
        _request("GET", "/api/v1/payments/manual/MANUAL-77/status"),
        ACCOUNT,
    )
    assert isinstance(result, JSONResponse)
    assert result.status_code == 404
    body = json.loads(result.body)
    assert body == {
        "ok": False,
        "status": "guarded",
        "message": "Yêu cầu nạp thủ công đang được bảo vệ.",
        "data": {},
        "error_code": "MANUAL_TOPUP_NOT_FOUND",
    }
    assert calls == [{
        "method": "GET",
        "path": "/internal/v1/payments/manual/MANUAL-77/status",
        "payload": None,
        "params": None,
        "owner_id": OWNER,
    }]
