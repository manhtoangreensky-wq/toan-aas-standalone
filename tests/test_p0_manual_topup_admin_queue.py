import json
from pathlib import Path
import re

import httpx
import pytest
from pydantic import ValidationError

import copyfast_api
import copyfast_auth
import copyfast_bridge
from tests.test_copyfast_auth_api import make_client


ROOT = Path(__file__).resolve().parents[1]
ADMIN_ID = "9001"
REQUEST_ID = "MANUAL-17"
BOT_TOKEN = "eyJ2IjoxLCJhZG1pbl9pZCI6IjkwMDEifQ.signature-value-0123456789"


def _bridge_record(*, status: str = "pending_admin_review") -> dict:
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
def _manual_admin_flags(monkeypatch):
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")


@pytest.mark.anyio
async def test_legacy_admin_bridge_adapter_keeps_exact_private_header_and_strips_token(monkeypatch):
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
                        **_bridge_record(),
                        "action": "approve_expected",
                        "approved_xu_to_apply": 1_000,
                        "reason": "Duyệt đúng Xu dự kiến",
                        "confirmation_token": BOT_TOKEN,
                        "expires_at": 2_000_000_000,
                    },
                    "error_code": None,
                },
            )
        return httpx.Response(
            200,
            json={
                "ok": True,
                "status": "completed",
                "message": "canonical",
                "data": {"items": [_bridge_record()], "count": 1, "filter": "pending"},
                "error_code": None,
            },
        )

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
async def test_legacy_admin_bridge_token_and_admin_id_fail_closed_before_network(monkeypatch):
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


def test_web_local_manual_admin_models_are_reject_only_and_forbid_authority_fields():
    rejected = copyfast_api.ManualAdminDraftRequest(
        action="reject", reason="  Không tìm thấy giao dịch  "
    )
    assert rejected.model_dump() == {
        "action": "reject",
        "reason": "Không tìm thấy giao dịch",
    }
    for payload in (
        {"action": "approve_expected"},
        {"action": "approve_custom", "approved_xu": 100, "reason": "forged"},
        {"action": "reject"},
        {"action": "reject", "reason": "x"},
        {"action": "reject", "reason": "bad\nreason"},
        {"action": "reject", "reason": "hợp lệ", "admin_id": ADMIN_ID},
        {"action": "reject", "reason": "hợp lệ", "approved_xu": 1},
        {"action": "reject", "reason": "hợp lệ", "confirmation_token": BOT_TOKEN},
    ):
        with pytest.raises(ValidationError):
            copyfast_api.ManualAdminDraftRequest(**payload)

    confirmed = copyfast_api.ManualAdminConfirmRequest(
        confirmation_receipt="r" * 43,
        idempotency_key="manual-admin-confirm-0001",
    )
    assert confirmed.confirmation_receipt == "r" * 43
    with pytest.raises(ValidationError):
        copyfast_api.ManualAdminConfirmRequest(
            confirmation_receipt="r" * 43,
            idempotency_key="manual-admin-confirm-0001",
            admin_id=ADMIN_ID,
        )


def test_manual_admin_routes_use_local_dependencies_and_unsigned_is_401(tmp_path, monkeypatch):
    routes = [
        (
            method,
            route.path,
            route.endpoint,
            tuple(dependency.call for dependency in route.dependant.dependencies),
        )
        for route in copyfast_api.router.routes
        if route.path.startswith("/api/v1/admin/payments/manual")
        for method in sorted(route.methods)
    ]
    assert [(method, path) for method, path, _endpoint, _deps in routes] == [
        ("GET", "/api/v1/admin/payments/manual"),
        ("GET", "/api/v1/admin/payments/manual/{request_id}"),
        ("POST", "/api/v1/admin/payments/manual/{request_id}/draft"),
        ("POST", "/api/v1/admin/payments/manual/{request_id}/confirm"),
    ]
    assert [endpoint for _method, _path, endpoint, _deps in routes] == [
        copyfast_api.manual_admin_list,
        copyfast_api.manual_admin_detail,
        copyfast_api.manual_admin_draft,
        copyfast_api.manual_admin_confirm,
    ]
    assert routes[0][3] == (copyfast_auth.require_admin,)
    assert routes[1][3] == (copyfast_auth.require_admin,)
    assert routes[2][3] == (copyfast_auth.require_admin_csrf,)
    assert routes[3][3] == (copyfast_auth.require_admin_csrf,)
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/admin/payments/manual").status_code == 401
        assert client.post(
            f"/api/v1/admin/payments/manual/{REQUEST_ID}/draft",
            json={"action": "reject", "reason": "Không tìm thấy"},
        ).status_code == 401


def test_admin_portal_contract_is_web_local_reject_only_localized_and_responsive():
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    integration = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    locale = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")

    renderer = portal[
        portal.index("function adminManualTopupFacts(record)"):
        portal.index("const BOT_COMPANION_COMMAND_PATTERN")
    ]
    normalizer = portal[
        portal.index("function normalizeAdminManualTopupRecord(value)"):
        portal.index("function normalizeBootstrap(raw)")
    ]
    handler = integration[
        integration.index('if (String(action || "").startsWith("admin-manual-topup-"))'):
        integration.index('if (action === "manual-topup-refresh")')
    ]
    for marker in (
        'adminPage("/admin/topups"',
        'layout: "admin-manual-topups"',
        "function renderAdminManualTopups(page, context)",
        'case "admin-manual-topups": return renderAdminManualTopups(page, context);',
        'data-portal-action="admin-manual-topup-refresh"',
        'data-portal-action="admin-manual-topup-draft"',
        'data-portal-action="admin-manual-topup-confirm"',
        'data-manual-admin-decision="reject"',
        'role="dialog"',
        'aria-modal="true"',
        'adminManualTopupText("field.paymentCode", "Mã nạp tiền")',
        'adminManualTopupText("field.email", "Email")',
    ):
        assert marker in portal
    for forbidden in (
        'data-manual-admin-decision="approve_expected"',
        'data-manual-admin-decision="approve_custom"',
        'name="approved_xu"',
        "record.telegram_user_id",
        "draft.telegram_user_id",
        "approved_xu_to_apply",
    ):
        assert forbidden not in renderer
    for marker in (
        '"display_name", "email", "currency", "method", "payment_code"',
        'String(rawDraft.action || "") === "reject"',
        "const expiresAt =",
    ):
        assert marker in normalizer
    for forbidden in (
        "source.telegram_user_id",
        '"approve_expected", "approve_custom", "reject"',
        "approved_xu_to_apply",
    ):
        assert forbidden not in normalizer

    for marker in (
        "localManualAdminViewEnabled",
        "localManualAdminWriteEnabled",
        'account.role === "admin" && currentPath === "/admin/topups"',
        'currentPath !== "/admin/topups"',
        'draftAction !== "reject"',
        'body = { action: "reject"',
        'String(result.status || "") === "rejected"',
    ):
        assert marker in integration
    for forbidden in (
        '["approve_expected", "approve_custom", "reject"]',
        "body.approved_xu",
        "manual_admin_bridge_request",
    ):
        assert forbidden not in handler

    keysets = {}
    for language, next_language in (("vi", "en"), ("en", "zh"), ("zh", None)):
        start = f"Object.assign(ADMIN_MANUAL_TOPUP_MESSAGES.{language}, {{"
        end = (
            f"Object.assign(ADMIN_MANUAL_TOPUP_MESSAGES.{next_language}, {{"
            if next_language
            else "const MANUAL_TOPUP_MESSAGES"
        )
        section = locale[locale.index(start):locale.index(end, locale.index(start) + 1)]
        keysets[language] = set(re.findall(r'"(adminManualTopup\.[^"]+)"\s*:', section))
    assert keysets["vi"] == keysets["en"] == keysets["zh"]
    for marker in (
        '"adminManualTopup.page.description": "Kiểm tra yêu cầu theo hai bước; chỉ ghi nhận từ chối và không tự cộng Xu."',
        '"adminManualTopup.page.description": "Review manual top-up requests in two steps; only rejection is available and no Xu is added."',
        '"adminManualTopup.page.description": "分两步审核人工充值请求；仅可记录拒绝，且不会增加 Xu。"',
        '"adminManualTopup.field.email": "Email"',
        '"adminManualTopup.field.email": "Account email"',
        '"adminManualTopup.field.email": "账户邮箱"',
        '"adminErpNavigation.route.topups": "Đối soát nạp thủ công"',
        '"adminErpNavigation.route.topups": "Manual top-up reconciliation"',
        '"adminErpNavigation.route.topups": "人工充值对账"',
        '"adminErpNavigation.route.topups.description": "Đối soát yêu cầu nạp thủ công; giai đoạn này chỉ cho phép ghi nhận từ chối."',
        '"adminErpNavigation.route.topups.description": "Review manual top-up requests; this phase allows rejection only."',
        '"adminErpNavigation.route.topups.description": "审核人工充值请求；当前阶段仅允许记录拒绝。"',
    ):
        assert marker in locale

    obsolete_keys = {
        "adminManualTopup.action.approveExpected",
        "adminManualTopup.action.approveCustom",
        "adminManualTopup.column.expectedXu",
        "adminManualTopup.column.approvedXu",
        "adminManualTopup.column.approver",
        "adminManualTopup.field.telegramId",
        "adminManualTopup.field.expectedXu",
        "adminManualTopup.field.approvedXu",
        "adminManualTopup.field.approver",
        "adminManualTopup.field.customXu",
        "adminManualTopup.decision.approveExpected",
        "adminManualTopup.decision.approveCustom",
        "adminManualTopup.confirm.custom",
        "adminManualTopup.confirm.expected",
        "adminManualTopup.error.customXu",
    }
    assert keysets["vi"].isdisjoint(obsolete_keys)

    values = {}
    for language, next_language in (("vi", "en"), ("en", "zh"), ("zh", None)):
        start = f"Object.assign(ADMIN_MANUAL_TOPUP_MESSAGES.{language}, {{"
        end = (
            f"Object.assign(ADMIN_MANUAL_TOPUP_MESSAGES.{next_language}, {{"
            if next_language
            else "const MANUAL_TOPUP_MESSAGES"
        )
        section = locale[locale.index(start):locale.index(end, locale.index(start) + 1)]
        values[language] = " ".join(
            re.findall(r'"adminManualTopup\.[^"]+"\s*:\s*"([^"]*)"', section)
        )
    for forbidden in ("G2", "Core Bridge", "Web-local", "capability", "Telegram ID"):
        assert forbidden not in values["vi"]
        assert forbidden not in values["en"]
        assert forbidden not in values["zh"]
    for forbidden in ("Review", "record", "queue", "Web Admin"):
        assert forbidden not in values["vi"]
    assert re.search(r"[ăâđêôơưĂÂĐÊÔƠƯàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũỳýỵỷỹ]", values["en"]) is None
    chinese_ascii_terms = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", values["zh"]))
    assert chinese_ascii_terms <= {"Xu", "VND", "ACB", "MoMo", "ZaloPay", "TOAN", "AAS"}

    for marker in (
        ".portal-admin-manual-topup-layout",
        "@media (max-width: 1100px)",
        "grid-template-columns: 1fr",
        "@media (max-width: 700px)",
        ".portal-admin-manual-topup-mobile",
        "min-height: 44px",
    ):
        assert marker in css
    tablet_rules = css[
        css.index("@media (max-width: 1100px)"):
        css.index("@media (max-width: 700px)", css.index("@media (max-width: 1100px)"))
    ]
    assert ".portal-admin-manual-topup-table > .portal-data-table-wrap" in tablet_rules
    assert ".portal-admin-manual-topup-mobile" in tablet_rules
    assert "display: none" in tablet_rules
    assert "display: grid" in tablet_rules
    mobile_rules = css[
        css.index("@media (max-width: 700px)", css.index(".portal-admin-manual-topup-modal")):
        css.index("@media (prefers-reduced-motion: reduce)", css.index(".portal-admin-manual-topup-modal"))
    ]
    assert ".portal-admin-manual-topup-controls form" in mobile_rules
    assert "flex: 0 0 auto" in mobile_rules
    assert "width: 100%" in mobile_rules

    customer_section = integration[
        integration.index('if (action === "manual-topup-create")'):
        integration.index('if (action === "finance-planning-view")')
    ]
    assert 'api("/payments/manual", {' in customer_section
    assert 'amount_vnd: amount, method, reference' in customer_section
    assert "_manual_topup_bridge" not in customer_section
