"""Focused boundary contracts for the canonical-admin Tax Readiness guide."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_start = source.find("\n  function ", start + len(marker))
    return source[start:] if next_start < 0 else source[start:next_start]


def test_tax_readiness_is_a_canonical_admin_directory_route_not_a_local_or_public_feature() -> None:
    app = _read("app.py")
    registry = _read("copyfast_registry.py")
    navigation = _read("copyfast_admin_erp_navigation.py")

    assert 'WebFeature("admin_tax_readiness", "Tax Readiness & Accounting Guidance", "admin", "/admin/finance/tax-readiness", "admin"' in registry
    assert '_directory_module("tax_readiness", "Tax Readiness & Accounting Guidance", "/admin/finance/tax-readiness")' in navigation
    assert '"tax_readiness": "Hướng dẫn chuẩn bị hồ sơ tax/accounting chỉ đọc' in navigation
    # The exact page deliberately falls through to the canonical gate rather
    # than becoming one of the narrow Web-local admin exceptions above it.
    assert 'elif normalized == "/admin" or normalized.startswith("/admin/"):\n        await require_canonical_admin(request)' in app
    assert 'normalized == "/admin/finance/tax-readiness"' not in app


def test_tax_readiness_renderer_is_static_guidance_and_finance_directory_card_is_manifest_gated() -> None:
    portal = _read("static/portal/portal.js")
    css = _read("static/portal/portal.css")

    for declaration in (
        'adminPage("/admin/finance/tax-readiness", "Tax Readiness & Accounting Guidance"',
        'layout: "admin-tax-readiness", action: "none", status: "read_only"',
        'case "admin-tax-readiness": return renderAdminTaxReadiness(page, context);',
        'route: "/admin/finance/tax-readiness", icon: ICONS.document',
        '"/admin/finance/tax-readiness"].includes(path)) return "finance"',
    ):
        assert declaration in portal

    renderer = _function_source(portal, "renderAdminTaxReadiness")
    assert 'serverAuthorizesAdminRoute(context, "/admin/finance")' in renderer
    for forbidden in (
        "fetch(",
        "api(",
        "readAdminPath(",
        "data-portal-action",
        "<form",
        "payloadFor(",
        "FormData",
        "Idempotency-Key",
        "/admin/modules/",
        "adminData",
        "localStorage",
        "sessionStorage",
    ):
        assert forbidden not in renderer
    assert "Không tính hoặc ước tính thuế" in renderer
    assert "Không tạo hoặc xuất chứng từ" in renderer
    assert "Không thay đổi financial authority" in renderer
    assert '${badge("guarded")}' not in renderer
    assert renderer.count('${badge("read_only")}') >= 3

    for selector in (
        ".portal-admin-tax-readiness",
        ".portal-tax-readiness-intro",
        ".portal-tax-readiness-grid",
        ".portal-tax-readiness-card",
        ".portal-tax-readiness-process",
        ".portal-tax-readiness-boundary",
        "font-size: 12px",
        "@media (max-width: 980px)",
        "@media (max-width: 700px)",
    ):
        assert selector in css


def test_tax_readiness_is_isolated_from_generic_finance_bridge_hydration_and_refresh() -> None:
    integration = _read("static/portal/integration.js")
    api = _read("copyfast_api.py")

    predicate = _function_source(integration, "isNativeAdminTaxReadinessPath")
    assert '=== "/admin/finance/tax-readiness"' in predicate
    bridge_target = _function_source(integration, "adminBridgeTargetForPath")
    assert "if (isNativeAdminTaxReadinessPath(normalized))" in bridge_target
    assert 'return { endpoint: "", module: "tax-readiness", requestedModule: "tax-readiness", recordId: "", supported: false };' in bridge_target
    assert "record_id=tax-readiness" not in bridge_target
    assert "return target.supported ? api(target.endpoint) : localAdminCompatibilityGuard(target);" in integration

    current_guard = _function_source(integration, "canonicalAdminDataRequestIsCurrent")
    admin_hydrator = _function_source(integration, "hydrateCanonicalAdminData")
    generic_hydrator = _function_source(integration, "hydrateCanonicalData")
    for source in (current_guard, admin_hydrator, generic_hydrator):
        assert "isNativeAdminTaxReadinessPath" in source
    assert '!isNativeAdminTaxReadinessPath(currentPath)' in integration
    assert '"/admin/finance/tax-readiness": account ? "read_only" : "guarded"' in integration

    refresh = integration[integration.index('if (action === "refresh-admin")'):integration.index('if (action === "admin-retry"')]
    assert "isNativeAdminTaxReadinessPath(path)" in refresh
    assert "không có làm mới, tính thuế, export hay control action trong browser" in refresh

    api_modules = api[api.index("ADMIN_BRIDGE_MODULES"):api.index("ADMIN_BRIDGE_MODULE_ALIASES")]
    assert "tax_readiness" not in api_modules
    assert "tax-readiness" not in api_modules


def test_tax_readiness_audit_contract_is_finite_and_documents_the_no_transfer_boundary() -> None:
    audit = _read("scripts/migration/audit_bot_to_web.py")
    catalog = _read("docs/migration/NON_VIDEO_MENU_NAVIGATION_CATALOG.md")

    for declaration in (
        "TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS",
        '"TAX_ACCOUNTING_GUIDANCE_CALLBACK_CONTRACT.md"',
        "reviewed_tax_accounting_guidance_fresh_web_navigation",
        "NO_CANONICAL_FINANCE_DATA_TRANSFER",
        "NO_TAX_ESTIMATE_OR_FINANCIAL_CALCULATION",
        "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
        "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
        "NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
    ):
        assert declaration in audit

    registry = audit[
        audit.index("TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS"):
        audit.index("TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_BASE_DISPOSITIONS")
    ]
    for callback in (
        "menu|finance_tax",
        "menu|tax_checklist",
        "menu|tax_custom_help",
    ):
        assert callback in registry
    for excluded in ("menu|tax_estimate", "menu|tax_config", "menu|tax_export", "menu|tax_export_custom_help", "menu|tax_export_month", "menu|tax_*"):
        assert f'"{excluded}":' not in registry

    assert "TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_ACTIONS" in audit
    assert "CANONICAL_TAX_ACCOUNTING_SOURCE_REVIEW_REQUIRED" in audit
    source_review_registry = audit[
        audit.index("TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_ACTIONS"):
        audit.index("GUIDED_VIDEO_MENU_DEFERRED_ACTIONS")
    ]
    for callback in ("menu|tax_export", "menu|tax_export_month", "menu|tax_export_custom_help"):
        assert callback in source_review_registry

    assert "Separately guarded Tax Readiness & Accounting Guidance" in catalog
    assert "fresh checklist/handoff guidance only" in catalog
