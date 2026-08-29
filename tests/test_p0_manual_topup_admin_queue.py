import asyncio
import json
import logging
from pathlib import Path

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

import copyfast_api
import copyfast_bridge
from tests.test_copyfast_auth_api import make_client


ROOT = Path(__file__).resolve().parents[1]
ADMIN_ID = "9001"
ACCOUNT = {"id": "web-admin-account", "canonical_user_id": ADMIN_ID, "role": "admin"}
REQUEST_ID = "MANUAL-17"
BOT_TOKEN = "eyJ2IjoxLCJhZG1pbl9pZCI6IjkwMDEifQ.signature-value-0123456789"


def _request(method: str, path: str, *, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request({"type": "http", "method": method, "path": path, "query_string": b"", "headers": headers or []})


def _body(response) -> dict:
    if isinstance(response, JSONResponse):
        return json.loads(response.body)
    return response


def _record(*, status: str = "pending_admin_review") -> dict:
    return {
        "request_id": REQUEST_ID,
        "telegram_user_id": "123456789",
        "display_name": "Khách QA",
        "amount_vnd": 100_000,
        "currency": "VND",
        "method": "bank_acb",
        "transfer_content": "AAS 123456789 MANUAL",
        "reference": "TX-SAFE",
        "status": status,
        "expected_xu": 1_000,
        "approved_xu": 1_000 if status == "approved" else 0,
        "submitted_at": "2026-08-29 01:00:00",
        "decision_at": "2026-08-29 01:05:00" if status != "pending_admin_review" else "",
        "decided_by_admin_id": ADMIN_ID if status != "pending_admin_review" else "",
        "admin_note": "Đã đối soát" if status != "pending_admin_review" else "",
    }


@pytest.fixture(autouse=True)
def _clean_receipt_vault(monkeypatch):
    vault = getattr(copyfast_api, "_manual_admin_receipt_vault", None)
    lock = getattr(copyfast_api, "_manual_admin_receipt_lock", None)
    if isinstance(vault, dict) and lock is not None:
        with lock:
            vault.clear()
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")


@pytest.mark.anyio
async def test_dedicated_admin_bridge_uses_exact_private_path_header_and_strips_token(monkeypatch):
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        payload = json.loads(request.content or b"{}")
        if request.url.path.endswith("/draft"):
            assert payload == {"action": "approve_expected"}
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "status": "awaiting_confirm",
                    "message": "canonical",
                    "data": {
                        **_record(),
                        "action": "approve_expected",
                        "approved_xu_to_apply": 1_000,
                        "reason": "Duyệt đúng Xu dự kiến",
                        "confirmation_token": BOT_TOKEN,
                        "expires_at": 2_000_000_000,
                    },
                    "error_code": None,
                },
            )
        return httpx.Response(200, json={"ok": True, "status": "completed", "message": "canonical", "data": {"items": [_record()], "count": 1, "filter": "pending"}, "error_code": None})

    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "https://bridge.example")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "owner-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "bridge-hmac")
    monkeypatch.setenv("INTERNAL_MANUAL_ADMIN_TOKEN", "separate-admin-token")
    transport = httpx.MockTransport(handler)

    listed, private = await copyfast_bridge.manual_admin_bridge_request(
        "GET",
        "/internal/v1/admin/payments/manual",
        admin_id=ADMIN_ID,
        params={"status": "pending", "limit": 20},
        transport=transport,
    )
    assert listed["ok"] is True and private == ""
    draft, private = await copyfast_bridge.manual_admin_bridge_request(
        "POST",
        f"/internal/v1/admin/payments/manual/{REQUEST_ID}/draft",
        admin_id=ADMIN_ID,
        payload={"action": "approve_expected"},
        transport=transport,
    )
    assert private == BOT_TOKEN
    assert "confirmation_token" not in json.dumps(draft)
    assert [request.url.path for request in calls] == [
        "/internal/v1/admin/payments/manual",
        f"/internal/v1/admin/payments/manual/{REQUEST_ID}/draft",
    ]
    for request in calls:
        assert request.headers["authorization"] == "Bearer separate-admin-token"
        assert request.headers["x-toan-aas-admin-id"] == ADMIN_ID
        assert "x-toan-aas-actor-id" not in request.headers
        assert "x-toan-aas-telegram-user-id" not in request.headers


@pytest.mark.anyio
async def test_admin_bridge_token_and_admin_id_fail_closed_before_network(monkeypatch):
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "https://bridge.example")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "owner-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "bridge-hmac")
    transport = httpx.MockTransport(handler)

    for value in (None, "", "owner-token", "tốken"):
        if value is None:
            monkeypatch.delenv("INTERNAL_MANUAL_ADMIN_TOKEN", raising=False)
        else:
            monkeypatch.setenv("INTERNAL_MANUAL_ADMIN_TOKEN", value)
        assert copyfast_bridge.manual_admin_bridge_configured() is False
        result, private = await copyfast_bridge.manual_admin_bridge_request(
            "GET", "/internal/v1/admin/payments/manual", admin_id=ADMIN_ID, transport=transport
        )
        assert result["ok"] is False and private == ""

    monkeypatch.setenv("INTERNAL_MANUAL_ADMIN_TOKEN", "separate-admin-token")
    for invalid in ("0", "-1", " 1", "1 ", "١", "１２", "1" * 21):
        result, _ = await copyfast_bridge.manual_admin_bridge_request(
            "GET", "/internal/v1/admin/payments/manual", admin_id=invalid, transport=transport
        )
        assert result["error_code"] == "CORE_BRIDGE_ADMIN_INVALID"
    assert calls == 0


def test_manual_admin_models_are_closed_strict_action_contracts():
    draft = copyfast_api.ManualAdminDraftRequest(action="approve_expected")
    assert draft.model_dump(exclude_none=True) == {"action": "approve_expected"}
    custom = copyfast_api.ManualAdminDraftRequest(action="approve_custom", approved_xu=900, reason="  Đối soát thiếu tiền  ")
    assert custom.model_dump(exclude_none=True) == {"action": "approve_custom", "approved_xu": 900, "reason": "Đối soát thiếu tiền"}
    rejected = copyfast_api.ManualAdminDraftRequest(action="reject", reason="  Không tìm thấy giao dịch  ")
    assert rejected.reason == "Không tìm thấy giao dịch"

    invalid = [
        {"action": "approve_expected", "approved_xu": 1},
        {"action": "approve_expected", "reason": "thừa"},
        {"action": "approve_custom", "approved_xu": True, "reason": "lý do hợp lệ"},
        {"action": "approve_custom", "approved_xu": "10", "reason": "lý do hợp lệ"},
        {"action": "approve_custom", "approved_xu": 10},
        {"action": "reject"},
        {"action": "reject", "approved_xu": 1, "reason": "lý do hợp lệ"},
        {"action": "reject", "reason": "x"},
        {"action": "approve_expected", "admin_id": ADMIN_ID},
        {"action": "approve_expected", "confirmation_token": BOT_TOKEN},
    ]
    for payload in invalid:
        with pytest.raises(ValidationError):
            copyfast_api.ManualAdminDraftRequest(**payload)

    confirmed = copyfast_api.ManualAdminConfirmRequest(
        confirmation_receipt="r" * 43,
        idempotency_key="manual-admin-confirm-0001",
    )
    assert confirmed.confirmation_receipt == "r" * 43
    with pytest.raises(ValidationError):
        copyfast_api.ManualAdminConfirmRequest(confirmation_receipt="r" * 43, idempotency_key="manual-admin-confirm-0001", admin_id=ADMIN_ID)


@pytest.mark.anyio
async def test_web_routes_derive_canonical_admin_project_list_and_map_not_found(monkeypatch):
    calls = []

    async def fake_bridge(method, path, *, admin_id, payload=None, params=None, request_id=None, transport=None):
        calls.append({"method": method, "path": path, "admin_id": admin_id, "payload": payload, "params": params})
        if path.endswith("MANUAL-404"):
            return ({"ok": False, "status": "guarded", "message": "private", "data": {}, "error_code": "WEB_MANUAL_ADMIN_NOT_FOUND"}, "")
        if path.endswith(REQUEST_ID):
            return ({"ok": True, "status": "pending_admin_review", "message": "canonical", "data": _record(), "error_code": None}, "")
        return ({"ok": True, "status": "completed", "message": "canonical", "data": {"items": [{**_record(), "raw_response": "drop", "confirmation_token": "drop"}], "count": 1, "filter": "pending"}, "error_code": None}, "")

    monkeypatch.setattr(copyfast_api, "manual_admin_bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "manual_admin_bridge_request", fake_bridge)
    forged = [(b"x-toan-aas-admin-id", b"7777")]
    listed = await copyfast_api.manual_admin_list(_request("GET", "/api/v1/admin/payments/manual", headers=forged), ACCOUNT, status="pending", limit=20)
    assert listed["data"] == {"items": [_record()], "count": 1, "filter": "pending"}
    detailed = await copyfast_api.manual_admin_detail(REQUEST_ID, _request("GET", f"/api/v1/admin/payments/manual/{REQUEST_ID}", headers=forged), ACCOUNT)
    assert detailed["data"] == _record()
    missing = await copyfast_api.manual_admin_detail("MANUAL-404", _request("GET", "/api/v1/admin/payments/manual/MANUAL-404"), ACCOUNT)
    assert isinstance(missing, JSONResponse) and missing.status_code == 404
    assert "private" not in missing.body.decode()
    assert [call["admin_id"] for call in calls] == [ADMIN_ID, ADMIN_ID, ADMIN_ID]
    assert calls[0]["path"] == "/internal/v1/admin/payments/manual"
    assert calls[1]["path"] == f"/internal/v1/admin/payments/manual/{REQUEST_ID}"
    assert calls[0]["params"] == {"status": "pending", "limit": 20}


@pytest.mark.anyio
async def test_draft_confirm_receipt_is_session_bound_single_flight_and_token_private(monkeypatch, caplog):
    calls = []
    session = {"session_id": "session-one", "account": ACCOUNT}
    confirm_started = anyio.Event()
    release_confirm = anyio.Event()

    async def fake_bridge(method, path, *, admin_id, payload=None, params=None, request_id=None, transport=None):
        calls.append({"method": method, "path": path, "admin_id": admin_id, "payload": payload})
        if path.endswith("/draft"):
            return (
                {
                    "ok": True,
                    "status": "awaiting_confirm",
                    "message": "canonical",
                    "data": {**_record(), "action": "approve_expected", "approved_xu_to_apply": 1_000, "reason": "Duyệt đúng Xu dự kiến", "expires_at": 2_000_000_000},
                    "error_code": None,
                },
                BOT_TOKEN,
            )
        if path.endswith("/confirm"):
            confirm_started.set()
            await release_confirm.wait()
            return ({"ok": True, "status": "approved", "message": "Đã duyệt", "data": {**_record(status="approved"), "action": "approve_expected", "idempotent_replay": False}, "error_code": None}, "")
        raise AssertionError(path)

    monkeypatch.setattr(copyfast_api, "manual_admin_bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "manual_admin_bridge_request", fake_bridge)
    monkeypatch.setattr(copyfast_api, "current_session", lambda _request: session)
    caplog.set_level(logging.DEBUG)

    draft = await copyfast_api.manual_admin_draft(
        REQUEST_ID,
        copyfast_api.ManualAdminDraftRequest(action="approve_expected"),
        _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/draft"),
        ACCOUNT,
    )
    draft_body = _body(draft)
    receipt = draft_body["data"]["confirmation_receipt"]
    assert len(receipt) >= 32
    assert BOT_TOKEN not in json.dumps(draft_body)
    assert "confirmation_token" not in json.dumps(draft_body)
    assert BOT_TOKEN not in caplog.text
    assert calls[0]["payload"] == {"action": "approve_expected"}

    cross_session = dict(session)
    cross_session["session_id"] = "session-two"
    monkeypatch.setattr(copyfast_api, "current_session", lambda _request: cross_session)
    denied = await copyfast_api.manual_admin_confirm(
        REQUEST_ID,
        copyfast_api.ManualAdminConfirmRequest(confirmation_receipt=receipt, idempotency_key="manual-admin-confirm-0001"),
        _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/confirm"),
        ACCOUNT,
    )
    assert _body(denied)["error_code"] == "MANUAL_ADMIN_CONFIRMATION_REQUIRED"
    assert len(calls) == 1

    monkeypatch.setattr(copyfast_api, "current_session", lambda _request: session)
    results = []

    async def confirm_once():
        results.append(await copyfast_api.manual_admin_confirm(
            REQUEST_ID,
            copyfast_api.ManualAdminConfirmRequest(confirmation_receipt=receipt, idempotency_key="manual-admin-confirm-0001"),
            _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/confirm"),
            ACCOUNT,
        ))

    async with anyio.create_task_group() as group:
        group.start_soon(confirm_once)
        await confirm_started.wait()
        group.start_soon(confirm_once)
        await anyio.sleep(0.02)
        release_confirm.set()
    assert len([call for call in calls if call["path"].endswith("/confirm")]) == 1
    assert {item.get("error_code") for item in map(_body, results)} == {None, "MANUAL_ADMIN_CONFIRMATION_IN_PROGRESS"}
    confirm_call = next(call for call in calls if call["path"].endswith("/confirm"))
    assert confirm_call["payload"] == {"confirmation_token": BOT_TOKEN}

    replay = await copyfast_api.manual_admin_confirm(
        REQUEST_ID,
        copyfast_api.ManualAdminConfirmRequest(confirmation_receipt=receipt, idempotency_key="manual-admin-confirm-0001"),
        _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/confirm"),
        ACCOUNT,
    )
    assert _body(replay)["status"] == "approved"
    assert len([call for call in calls if call["path"].endswith("/confirm")]) == 1
    wrong_key = await copyfast_api.manual_admin_confirm(
        REQUEST_ID,
        copyfast_api.ManualAdminConfirmRequest(confirmation_receipt=receipt, idempotency_key="manual-admin-confirm-0002"),
        _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/confirm"),
        ACCOUNT,
    )
    assert _body(wrong_key)["error_code"] == "MANUAL_ADMIN_CONFIRMATION_ALREADY_USED"


@pytest.mark.anyio
async def test_expired_receipt_and_guarded_write_do_not_call_bridge(monkeypatch):
    calls = []
    monkeypatch.setattr(copyfast_api, "manual_admin_bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "current_session", lambda _request: {"session_id": "session-expiry", "account": ACCOUNT})

    async def fake_bridge(method, path, *, admin_id, payload=None, params=None, request_id=None, transport=None):
        calls.append(path)
        return (
            {"ok": True, "status": "awaiting_confirm", "message": "canonical", "data": {**_record(), "action": "reject", "approved_xu_to_apply": 0, "reason": "Không tìm thấy", "expires_at": 2_000_000_000}, "error_code": None},
            BOT_TOKEN,
        )

    monkeypatch.setattr(copyfast_api, "manual_admin_bridge_request", fake_bridge)
    draft = await copyfast_api.manual_admin_draft(
        REQUEST_ID,
        copyfast_api.ManualAdminDraftRequest(action="reject", reason="Không tìm thấy giao dịch"),
        _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/draft"),
        ACCOUNT,
    )
    receipt = _body(draft)["data"]["confirmation_receipt"]
    receipt_hash = copyfast_api.hashlib.sha256(receipt.encode()).hexdigest()
    with copyfast_api._manual_admin_receipt_lock:
        copyfast_api._manual_admin_receipt_vault[receipt_hash].expires_at = 0
    expired = await copyfast_api.manual_admin_confirm(
        REQUEST_ID,
        copyfast_api.ManualAdminConfirmRequest(confirmation_receipt=receipt, idempotency_key="manual-admin-expired-01"),
        _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/confirm"),
        ACCOUNT,
    )
    assert _body(expired)["error_code"] == "MANUAL_ADMIN_CONFIRMATION_EXPIRED"
    assert len(calls) == 1

    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "false")
    guarded = await copyfast_api.manual_admin_draft(
        REQUEST_ID,
        copyfast_api.ManualAdminDraftRequest(action="approve_expected"),
        _request("POST", f"/api/v1/admin/payments/manual/{REQUEST_ID}/draft"),
        ACCOUNT,
    )
    assert _body(guarded)["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"
    assert len(calls) == 1


def test_admin_routes_are_registered_with_canonical_dependencies_and_unsigned_is_401(tmp_path, monkeypatch):
    expected = {
        ("GET", "/api/v1/admin/payments/manual"),
        ("GET", "/api/v1/admin/payments/manual/{request_id}"),
        ("POST", "/api/v1/admin/payments/manual/{request_id}/draft"),
        ("POST", "/api/v1/admin/payments/manual/{request_id}/confirm"),
    }
    routes = {
        (method, route.path)
        for route in copyfast_api.router.routes
        if route.path.startswith("/api/v1/admin/payments/manual")
        for method in route.methods
    }
    assert routes == expected
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/admin/payments/manual").status_code == 401
        assert client.post(f"/api/v1/admin/payments/manual/{REQUEST_ID}/draft", json={"action": "approve_expected"}).status_code == 401


def test_admin_portal_contract_is_specialized_localized_and_keeps_p0_03_protected():
    portal = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
    integration = (ROOT / "static/portal/integration.js").read_text(encoding="utf-8")
    locale = (ROOT / "static/portal/portal-i18n.js").read_text(encoding="utf-8")
    css = (ROOT / "static/portal/portal.css").read_text(encoding="utf-8")

    for marker in (
        'adminPage("/admin/topups"',
        'layout: "admin-manual-topups"',
        "function renderAdminManualTopups(page, context)",
        'case "admin-manual-topups": return renderAdminManualTopups(page, context);',
        'data-portal-action="admin-manual-topup-refresh"',
        'data-portal-action="admin-manual-topup-draft"',
        'data-portal-action="admin-manual-topup-confirm"',
        'role="dialog"',
        'aria-modal="true"',
    ):
        assert marker in portal
    for marker in (
        "async function hydrateAdminManualTopups",
        'path === "/admin/topups"',
        'api(`/admin/payments/manual?status=',
        "data.items",
        "currentPortalPath()",
        "admin-manual-topup-write",
        'if (action === "admin-manual-topup-confirm")',
        "manual-admin-confirm",
    ):
        assert marker in integration
    assert "onclick=" not in portal[portal.index("function renderAdminManualTopups"):portal.index("const BOT_COMPANION_COMMAND_PATTERN")]
    assert "confirmation_token" not in portal
    assert "confirmation_token" not in integration
    assert "INTERNAL_MANUAL_ADMIN_TOKEN" not in portal + integration + locale
    assert "const ADMIN_MANUAL_TOPUP_MESSAGES = { vi: {}, en: {}, zh: {} };" in locale
    for language in ("vi", "en", "zh"):
        assert f"Object.assign(ADMIN_MANUAL_TOPUP_MESSAGES.{language}, {{" in locale
    assert locale.count("Object.assign(ADMIN_MANUAL_TOPUP_MESSAGES.") == 3
    for marker in (
        '"adminManualTopup.status.pending": "Chờ duyệt"',
        '"adminManualTopup.status.approved": "Đã duyệt"',
        '"adminManualTopup.status.rejected": "Đã từ chối"',
        '"adminManualTopup.status.guarded": "Được bảo vệ"',
        '"adminManualTopup.status.pending": "Pending review"',
        '"adminManualTopup.status.approved": "Approved"',
        '"adminManualTopup.status.rejected": "Rejected"',
        '"adminManualTopup.status.guarded": "Guarded"',
        '"adminManualTopup.status.pending": "待审核"',
        '"adminManualTopup.status.approved": "已批准"',
        '"adminManualTopup.status.rejected": "已拒绝"',
        '"adminManualTopup.status.guarded": "受保护"',
        '"adminManualTopup.page.title": "Đối soát nạp thủ công"',
        '"adminManualTopup.page.description": "Review hàng đợi canonical theo hai bước; Web không tự cộng Xu."',
        '"adminManualTopup.column.ordinal": "STT"',
        '"adminManualTopup.page.title": "Manual top-up reconciliation"',
        '"adminManualTopup.page.description": "Review the canonical queue in two steps; the Web never credits Xu directly."',
        '"adminManualTopup.column.ordinal": "#"',
        '"adminManualTopup.page.title": "人工充值对账"',
        '"adminManualTopup.page.description": "分两步审核权威队列；Web 绝不直接增加 Xu。"',
        '"adminManualTopup.column.ordinal": "序号"',
        '"adminManualTopup.field.action": "Quyết định"',
        '"adminManualTopup.decision.approveExpected": "Duyệt Xu dự kiến"',
        '"adminManualTopup.decision.approveCustom": "Duyệt Xu tùy chỉnh"',
        '"adminManualTopup.decision.reject": "Từ chối"',
        '"adminManualTopup.field.action": "Decision"',
        '"adminManualTopup.decision.approveExpected": "Approve expected credits"',
        '"adminManualTopup.decision.approveCustom": "Approve custom credits"',
        '"adminManualTopup.decision.reject": "Reject"',
        '"adminManualTopup.field.action": "决定"',
        '"adminManualTopup.decision.approveExpected": "批准预计 Xu"',
        '"adminManualTopup.decision.approveCustom": "批准自定义 Xu"',
        '"adminManualTopup.decision.reject": "拒绝"',
    ):
        assert marker in locale
    manual_admin_renderer = portal[
        portal.index("function adminManualTopupText(key, fallback, params)"):
        portal.index("const BOT_COMPANION_COMMAND_PATTERN")
    ]
    assert "function adminManualTopupStatusBadge(status)" in portal
    assert portal.count("function adminManualTopupStatusBadge(status)") == 1
    assert "adminManualTopupStatusBadge(record.status)" in manual_admin_renderer
    assert "adminManualTopupStatusBadge(item.status)" in manual_admin_renderer
    assert 'badge(record.status || "guarded")' not in manual_admin_renderer
    assert "badge(item.status)" not in manual_admin_renderer
    assert 'if (path === "/admin/topups") return adminManualTopupText("page.title", fallback);' in portal
    assert 'if (path === "/admin/topups") return adminManualTopupText("page.description", fallback);' in portal
    assert 'adminManualTopupText("column.ordinal", "STT")' in manual_admin_renderer
    confirmation = manual_admin_renderer[
        manual_admin_renderer.index("function renderAdminManualTopupConfirmation(draft)"):
        manual_admin_renderer.index("function renderAdminManualTopups(page, context)")
    ]
    assert 'adminManualTopupText("field.customer", "Khách hàng")' in confirmation
    assert "draft.display_name || draft.telegram_user_id" in confirmation
    assert 'adminManualTopupText("field.telegramId", "Telegram ID")' in confirmation
    assert "draft.telegram_user_id" in confirmation
    assert 'adminManualTopupText("field.action", "Quyết định")' in confirmation
    assert "adminManualTopupDecisionLabel(draft.action)" in confirmation
    assert 'data-manual-admin-read-state="${safeText(state.readState || "guarded")}"' in manual_admin_renderer
    assert 'main.querySelectorAll(`button[data-manual-admin-request-id="${escaped}"]`)' in portal
    assert ".find((element) => element.getClientRects().length > 0" in portal
    assert 'const readState = main && main.querySelector(".portal-admin-manual-topup")?.getAttribute("data-manual-admin-read-state");' in portal
    assert 'if (readState === "loading") {' in portal
    assert 'if (fallback && typeof fallback.focus === "function") fallback.focus({ preventScroll: true });' in portal
    assert 'data-portal-action="admin-manual-topup-filter"][aria-pressed="true"]' in portal

    assert "let adminManualTopupWriteEpoch = 0;" in integration
    assert "function adminManualTopupWriteIsCurrent(" in integration
    assert integration.count("if (!adminManualTopupWriteIsCurrent(") >= 2
    assert "++adminManualTopupWriteEpoch;" in integration
    assert 'readState: "loading", draft: null' in integration
    assert 'const expectedPath = currentPortalPath();' in integration
    assert 'const sessionEpoch = canonicalSessionEpoch;' in integration
    assert ".portal-admin-manual-topup" in css
    assert "@media (max-width: 700px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "min-height: 44px" in css

    assert "function renderManualTopupGuide(context)" in portal
    guide = portal[portal.index("function renderManualTopupGuide(context)"):portal.index("function renderPaymentRequestForm(page, context)")]
    assert 'data-portal-action="manual-topup-create"' in guide
    assert "/static/ACBBANK.jpg" not in guide
    assert "8899397968" not in guide
    assert "TUqyVeo" not in guide
    assert "const walletReady" in portal[portal.index("function renderWallet(page, context)"):portal.index("function renderCatalog(page, context)")]
    assert "|| DEFAULT_CANONICAL_PRICING_CATALOG" not in portal[portal.index("function renderCatalog(page, context)"):portal.index("const JOB_FILTERS")]
