"""Focused RED contracts for PAYOS-CHECKOUT-RESTORE-001."""

from __future__ import annotations
import random
import sys
import types
from pathlib import Path

import anyio
import pytest
from starlette.requests import Request
import copyfast_api as api
from copyfast_api import PaymentRequest


ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static/portal/integration.js").read_text(encoding="utf-8")
PACKAGE = {
    "code": "topup_10k",
    "label": "10.000 đ",
    "amount_vnd": 10_000,
    "xu": 100,
    "available": True,
}
ACCOUNT = {"id": "web-account", "canonical_user_id": "telegram-1"}


def _between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    return source[start_index : source.index(end, start_index + len(start))]


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/api/v1/payments/create", "headers": []})


def _enable_direct_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "_flags", lambda: {"payment_enabled": True})
    monkeypatch.setattr(api, "_payment_topup_packages", lambda: [dict(PACKAGE)])
    monkeypatch.setattr(
        api,
        "_payos_config",
        lambda: {"client_id": "stub-client", "api_key": "stub-api", "checksum": "stub-checksum"},
    )


def _stub_payos_order_db(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple]]:
    writes: list[tuple[str, tuple]] = []

    class Cursor:
        def execute(self, statement: str, params: tuple) -> "Cursor":
            if not statement.strip().upper().startswith("SELECT"):
                writes.append((statement, params))
            return self

        def fetchone(self) -> None:
            return None

    class Connection:
        def cursor(self) -> Cursor:
            return Cursor()

        def commit(self) -> None:
            return None

        def close(self) -> None:
            return None

    module = types.ModuleType("db")
    module.db_connect = Connection
    module.now_text = lambda: "2026-08-26 00:00:00"
    monkeypatch.setitem(sys.modules, "db", module)
    return writes


def _use_in_memory_single_flight(monkeypatch: pytest.MonkeyPatch) -> None:
    pending: set[tuple[str, str]] = set()

    def reserve(scope: str, key: str) -> tuple[str, str]:
        identity = (scope, key)
        if identity in pending:
            return "pending", ""
        pending.add(identity)
        return "owner", "stub-marker"

    def release(scope: str, key: str, marker: str) -> None:
        pending.discard((scope, key))

    monkeypatch.setattr(api, "_reserve_transient_idempotency", reserve)
    monkeypatch.setattr(api, "_release_idempotency", release)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("direct_config", "bridge_ready", "expected"),
    [
        ({"client_id": "client", "api_key": "api", "checksum": "checksum"}, False, True),
        ({"client_id": "", "api_key": "", "checksum": ""}, True, True),
        ({"client_id": "", "api_key": "", "checksum": ""}, False, False),
    ],
)
async def test_payment_options_uses_one_direct_or_bridge_readiness_contract(
    monkeypatch: pytest.MonkeyPatch,
    direct_config: dict[str, str],
    bridge_ready: bool,
    expected: bool,
) -> None:
    monkeypatch.setattr(api, "_flags", lambda: {"payment_enabled": True})
    monkeypatch.setattr(api, "_payment_topup_packages", lambda: [dict(PACKAGE)])
    monkeypatch.setattr(api, "_payos_config", lambda: direct_config)
    monkeypatch.setattr(api, "bridge_configured", lambda: bridge_ready)

    result = await api.payment_options(ACCOUNT)

    assert result["data"]["payos"]["request_enabled"] is expected


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_url",
    [
        "http://pay.payos.vn/checkout/order",
        "https://pay.payos.vn.evil.example/checkout/order",
        "https://user:pass@pay.payos.vn/checkout/order",
        "https://pay.payos.vn:443/checkout/order",
        "https://pay.payos.vn:444/checkout/order",
        "https://pay.payos.vn/checkout/order#fragment",
    ],
)
async def test_direct_provider_checkout_url_fails_closed_before_order_write(
    monkeypatch: pytest.MonkeyPatch,
    invalid_url: str,
) -> None:
    _enable_direct_checkout(monkeypatch)
    writes = _stub_payos_order_db(monkeypatch)

    async def provider_stub(*args, **kwargs):
        return {"code": "00", "data": {"checkoutUrl": invalid_url, "qrCode": "stub-qr"}}

    async def run_once(scope: str, key: str, operation):
        return await operation()

    monkeypatch.setattr(api, "_create_payos_checkout", provider_stub)
    monkeypatch.setattr(api, "_run_transient_idempotent", run_once)

    result = await api.create_payment(
        PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="invalid-url-0001"),
        _request(),
        ACCOUNT,
    )

    assert result["ok"] is False
    assert result["error_code"] == "PAYOS_CHECKOUT_URL_INVALID"
    assert writes == []


@pytest.mark.anyio
async def test_direct_provider_returns_only_a_canonical_vetted_checkout_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_direct_checkout(monkeypatch)
    writes = _stub_payos_order_db(monkeypatch)

    async def provider_stub(*args, **kwargs):
        return {"code": "00", "data": {"checkoutUrl": "https://pay.payos.vn/checkout/order?source=web"}}

    async def run_once(scope: str, key: str, operation):
        return await operation()

    monkeypatch.setattr(api, "_create_payos_checkout", provider_stub)
    monkeypatch.setattr(api, "_run_transient_idempotent", run_once)

    result = await api.create_payment(
        PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="valid-url-00001"),
        _request(),
        ACCOUNT,
    )

    assert result["ok"] is True
    assert result["data"]["checkout_url"] == "https://pay.payos.vn/checkout/order?source=web"
    assert {"checkoutUrl", "payment_url", "url"}.isdisjoint(result["data"])
    assert len(writes) == 1


@pytest.mark.anyio
async def test_direct_checkout_uses_amount_and_xu_from_the_selected_server_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_direct_checkout(monkeypatch)
    package = {
        "code": "topup_custom_reviewed",
        "label": "Gói tùy chỉnh đã duyệt",
        "amount_vnd": 73_000,
        "xu": 730,
        "available": True,
    }
    monkeypatch.setattr(api, "_payment_topup_packages", lambda: [package])
    writes = _stub_payos_order_db(monkeypatch)
    provider_amounts: list[int] = []

    async def provider_stub(amount: int, *args, **kwargs):
        provider_amounts.append(amount)
        return {"code": "00", "data": {"checkoutUrl": "https://pay.payos.vn/checkout/custom-order"}}

    async def run_once(scope: str, key: str, operation):
        return await operation()

    monkeypatch.setattr(api, "_create_payos_checkout", provider_stub)
    monkeypatch.setattr(api, "_run_transient_idempotent", run_once)

    result = await api.create_payment(
        PaymentRequest(
            package_id="topup_custom_reviewed",
            payment_type="topup_xu",
            idempotency_key="custom-catalog-package-0001",
        ),
        _request(),
        ACCOUNT,
    )

    assert provider_amounts == [73_000]
    assert result["data"]["xu"] == 730
    assert writes[0][1][2:4] == (73_000, 730)


@pytest.mark.anyio
async def test_concurrent_same_key_generates_one_order_and_calls_one_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_direct_checkout(monkeypatch)
    _stub_payos_order_db(monkeypatch)
    _use_in_memory_single_flight(monkeypatch)
    order_calls = 0
    provider_calls = 0

    def order_stub(start: int, end: int) -> int:
        nonlocal order_calls
        order_calls += 1
        return 12345678

    async def provider_stub(*args, **kwargs):
        nonlocal provider_calls
        provider_calls += 1
        await anyio.sleep(0.03)
        return {"code": "00", "data": {"checkoutUrl": "https://pay.payos.vn/checkout/order"}}

    monkeypatch.setattr(random, "randint", order_stub)
    monkeypatch.setattr(api, "_create_payos_checkout", provider_stub)
    payload = PaymentRequest(
        package_id="topup_10k",
        payment_type="topup_xu",
        idempotency_key="concurrent-payment-0001",
    )
    results: list[dict] = []

    async def submit() -> None:
        results.append(await api.create_payment(payload, _request(), ACCOUNT))

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(submit)
        task_group.start_soon(submit)

    assert order_calls == 1
    assert provider_calls == 1
    assert {item["error_code"] for item in results} == {None, "IDEMPOTENCY_IN_PROGRESS"}


def test_payment_form_uses_server_catalog_and_disables_checkout_when_not_ready() -> None:
    form = _between(PORTAL, "function renderPaymentRequestForm(page, context)", "function renderPaymentLookup(context)")
    wallet = _between(PORTAL, "function renderWallet(page, context)", "const DEFAULT_CANONICAL_PACKAGES")

    assert 'class="portal-page portal-wallet-page" style="grid-template-columns:minmax(0,1fr)"' in wallet
    assert 'grid-template-columns:repeat(3, minmax(0, 1fr)); min-width:0; width:100%' in form
    assert "min-width:0; width:100%; gap:12px;" in form
    assert "paymentWebCatalogReady(context)" in form
    assert "paymentOptions.payos.topup_packages" in form
    assert "disabled" in form
    for hardcoded_code in ("topup_10k", "topup_20k", "topup_50k", "topup_100k", "topup_200k", "topup_500k"):
        assert hardcoded_code not in form


def test_browser_opens_trusted_placeholder_before_await_then_validates_or_closes() -> None:
    branch = _between(INTEGRATION, 'if (action === "payment-create")', 'if (action === "payment-lookup")')
    open_call = 'window.open(checkoutUrl, "_blank")'
    await_call = 'await api("/payments/create"'

    assert 'let checkoutUrl = "about:blank"' in branch
    assert branch.index(open_call) < branch.index(await_call)
    assert "function safePayosCheckout(value)" in INTEGRATION
    assert "safePayosCheckout(result.data && result.data.checkout_url)" in branch
    assert "checkoutWindow.location.href = checkoutUrl" in branch
    assert "window.location.href = checkoutUrl" in branch
    assert "checkoutWindow.close()" in branch
    assert "result.data.checkoutUrl" not in branch
    assert "result.data.payment_url" not in branch
    assert "result.data.url" not in branch


def test_contract_module_stays_within_owner_file_limit() -> None:
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 300
