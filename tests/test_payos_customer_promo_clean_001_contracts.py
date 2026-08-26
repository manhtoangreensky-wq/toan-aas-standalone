"""Focused contracts for PAYOS-CUSTOMER-PROMO-CLEAN-001."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static/portal/integration.js").read_text(encoding="utf-8")
ADMIN_NAV = (ROOT / "copyfast_admin_erp_navigation.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
PUBLIC_PROMO_CODES = ("WEEKLY10", "MONTHLY20", "DAILY5", "BETA50")


def _between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    return source[start_index : source.index(end, start_index + len(start))]


def _contains(source: str, *values: str) -> None:
    for value in values:
        assert value in source, value


def _excludes(source: str, *values: str) -> None:
    for value in values:
        assert value not in source, value


def test_customer_payment_form_has_no_public_promo_controls_or_codes() -> None:
    form = _between(
        PORTAL,
        "function renderPaymentRequestForm(page, context)",
        "function renderBillingJourney()",
    )

    _excludes(
        form,
        "portal-topup-promo-section",
        "portal-topup-promo-input",
        'name="promo_code"',
        "portal-promo-tag",
        *PUBLIC_PROMO_CODES,
    )
    _contains(
        form,
        "const packages = [",
        "${packageOptions}",
        'data-portal-action="payment-create"',
        "Nạp ngay (Mở cổng PayOS)",
        "renderPaymentFlow(context)",
        "renderPaymentLookup(context)",
    )


def test_browser_payment_create_uses_package_only_fingerprint_and_payload() -> None:
    branch = _between(
        INTEGRATION,
        'if (action === "payment-create")',
        'if (action === "payment-lookup")',
    )
    payload = _between(branch, "body: JSON.stringify({", "})").split("{", 1)[1]

    _excludes(branch, "promoInput", "promoCode", "promo_code", *PUBLIC_PROMO_CODES)
    _contains(
        branch,
        'acquireSubmission("payment", packageId);',
        "window.open(checkoutUrl, \"_blank\")",
        "schedulePaymentPolling(",
        "releaseSubmission(submission);",
    )
    assert re.findall(r"\b([a-z_]+):", payload) == [
        "package_id",
        "payment_type",
        "idempotency_key",
    ]


def test_payment_api_uses_base_package_xu_without_browser_promo_bonus() -> None:
    model = _between(API, "class PaymentRequest(BaseModel):", "class FreezeRequest(BaseModel):")
    create = _between(
        API,
        '@router.post("/payments/create")',
        '@router.get("/payments/{payment_id}")',
    )

    _excludes(model, "promo_code")
    _contains(model, "package_id:", "payment_type:", "idempotency_key:")
    _excludes(
        create,
        "payload.promo_code",
        "promo_rates",
        "promo_bonus",
        "promo_msg",
        "expected_xu +=",
        *PUBLIC_PROMO_CODES,
    )
    _contains(
        create,
        "expected_xu = base_xu",
        "_create_payos_checkout(amount, order_code, description, public_base_url)",
        "INSERT INTO payos_orders",
        'f"payment:{account[\'id\']}"',
        "Vui lòng quét mã VietQR để hoàn tất nạp Xu.",
    )


def test_canonical_admin_promo_route_and_feature_remain_available() -> None:
    _contains(ADMIN_NAV, '_canonical_module("promos", "Khuyến mãi", "/admin/promos")')
    _contains(REGISTRY, 'WebFeature("admin_promos", "Khuyến mãi", "admin", "/admin/promos", "admin")')
    _contains(PORTAL, 'adminPage("/admin/promos"', 'route: "/admin/promos"')


def test_contract_module_stays_within_owner_file_limit() -> None:
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 300
