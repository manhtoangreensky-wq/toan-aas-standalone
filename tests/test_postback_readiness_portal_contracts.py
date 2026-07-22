"""Focused boundaries for the canonical-admin Postback Readiness guide."""

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


def test_postback_readiness_uses_the_generic_canonical_admin_route_gate() -> None:
    app = _read("app.py")
    registry = _read("copyfast_registry.py")
    navigation = _read("copyfast_admin_erp_navigation.py")

    assert 'WebFeature("admin_postback_readiness", "Postback Readiness Guide", "admin", "/admin/growth/postback-readiness", "admin"' in registry
    assert '_directory_module("postback_readiness", "Postback Readiness Guide", "/admin/growth/postback-readiness")' in navigation
    assert '"postback_readiness": "Hướng dẫn chuẩn bị postback chỉ đọc' in navigation
    assert 'elif normalized == "/admin" or normalized.startswith("/admin/"):\n        await require_canonical_admin(request)' in app
    assert 'normalized == "/admin/growth/postback-readiness"' not in app


def test_postback_readiness_renderer_is_static_guidance_without_a_configuration_or_event_surface() -> None:
    portal = _read("static/portal/portal.js")
    css = _read("static/portal/portal.css")

    for declaration in (
        'adminPage("/admin/growth/postback-readiness", "Postback Readiness"',
        'layout: "admin-postback-readiness", action: "none", status: "read_only"',
        'case "admin-postback-readiness": return renderAdminPostbackReadiness(page, context);',
        '"/admin/growth/postback-readiness", "/admin/affiliates"',
        'route: "/admin/growth/postback-readiness", icon: ICONS.security',
    ):
        assert declaration in portal

    renderer = _function_source(portal, "renderAdminPostbackReadiness")
    assert 'serverAuthorizesAdminRoute(context, "/admin/growth")' in renderer
    assert 'serverAuthorizesAdminRoute(context, "/admin/audit")' in renderer
    for forbidden in (
        "fetch(",
        "api(",
        "readAdminPath(",
        "data-portal-action",
        "<form",
        "FormData",
        "Idempotency-Key",
        "/admin/modules/",
        "adminData",
        "localStorage",
        "sessionStorage",
        "window.history",
        "history.back",
        "/api/affiliate/postback",
        "AFFILIATE_POSTBACK_TOKEN",
        "tracking_click_url",
        "postback_setup",
    ):
        assert forbidden not in renderer
    assert "Không tạo cấu hình kết nối" in renderer
    assert "Không gửi hoặc nhận sự kiện" in renderer
    assert "Không thay đổi attribution hay tài chính" in renderer
    assert renderer.count('${badge("read_only")}') >= 3

    for selector in (
        ".portal-admin-postback-readiness",
        ".portal-postback-readiness-intro",
        ".portal-postback-readiness-grid",
        ".portal-postback-readiness-card",
        ".portal-postback-readiness-process",
        ".portal-postback-readiness-boundary",
        "font-size: 12px",
        "@media (max-width: 980px)",
        "@media (max-width: 700px)",
    ):
        assert selector in css


def test_postback_readiness_is_fenced_off_from_bridge_hydration_refresh_and_private_cache() -> None:
    integration = _read("static/portal/integration.js")
    api = _read("copyfast_api.py")
    worker = _read("static/portal/service-worker.js")

    predicate = _function_source(integration, "isNativeAdminPostbackReadinessPath")
    assert '=== "/admin/growth/postback-readiness"' in predicate
    bridge_target = _function_source(integration, "adminBridgeTargetForPath")
    assert "if (isNativeAdminPostbackReadinessPath(normalized))" in bridge_target
    assert 'return { endpoint: "", module: "postback-readiness", requestedModule: "postback-readiness", recordId: "", supported: false };' in bridge_target
    assert "record_id=postback-readiness" not in bridge_target

    current_guard = _function_source(integration, "canonicalAdminDataRequestIsCurrent")
    admin_hydrator = _function_source(integration, "hydrateCanonicalAdminData")
    generic_hydrator = _function_source(integration, "hydrateCanonicalData")
    for source in (current_guard, admin_hydrator, generic_hydrator):
        assert "isNativeAdminPostbackReadinessPath" in source
    assert "!isNativeAdminPostbackReadinessPath(currentPath)" in integration
    assert '"/admin/growth/postback-readiness": account ? "read_only" : "guarded"' in integration

    refresh = integration[integration.index('if (action === "refresh-admin")'):integration.index('if (action === "admin-retry"')]
    assert "isNativeAdminPostbackReadinessPath(path)" in refresh
    assert "không có làm mới, cấu hình, gửi/nhận sự kiện hay control action trong browser" in refresh

    api_modules = api[api.index("ADMIN_BRIDGE_MODULES"):api.index("ADMIN_BRIDGE_MODULE_ALIASES")]
    assert "postback_readiness" not in api_modules
    assert "postback-readiness" not in api_modules

    assert '"/admin"' in worker
    assert "const isPrivatePath = PRIVATE_PATH_PREFIXES.some" in worker
    assert "url.pathname === prefix || url.pathname.startsWith(prefix + \"/\")" in worker
    shell = worker.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/admin/growth/postback-readiness"' not in shell


def test_postback_readiness_audit_contract_is_finite_and_keeps_configuration_in_bot() -> None:
    audit = _read("scripts/migration/audit_bot_to_web.py")
    contract = _read("docs/migration/POSTBACK_READINESS_CALLBACK_CONTRACT.md")
    catalog = _read("docs/migration/NON_VIDEO_MENU_NAVIGATION_CATALOG.md")

    for declaration in (
        "POSTBACK_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS",
        "POSTBACK_CONFIGURATION_SOURCE_REVIEW_COMMANDS",
        '"POSTBACK_READINESS_CALLBACK_CONTRACT.md"',
        "reviewed_postback_readiness_fresh_web_navigation",
        "reviewed_postback_configuration_command_requires_canonical_contract",
        "NO_WEB_POSTBACK_CONFIGURATION_OR_EVENT_ACTION",
        "NO_AFFILIATE_JOB_OR_ATTRIBUTION_TRANSFER",
        "NO_REWARD_PAYOUT_OR_FINANCIAL_ACTION",
    ):
        assert declaration in audit

    registry = audit[
        audit.index("POSTBACK_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS"):
        audit.index("POSTBACK_CONFIGURATION_SOURCE_REVIEW_BASE_DISPOSITIONS")
    ]
    assert '"menu|hint_postback_setup": {' in registry
    for excluded in ('"MENU|HINT_POSTBACK_SETUP":', '"menu|hint_postback_setup_*":'):
        assert excluded not in registry
    source_review = audit[
        audit.index("POSTBACK_CONFIGURATION_SOURCE_REVIEW_COMMANDS"):
        audit.index("TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS")
    ]
    assert '"postback_setup": {' in source_review

    assert "static preparation and handoff guide" in contract
    assert "canonical source-review record" in contract
    assert "must not expose, copy, parse or replay" in contract
    assert "Separately guarded Postback Readiness" in catalog
    assert "`menu|hint_postback_setup`" in catalog
