"""Focused Portal and migration contracts for the Web-native Guided Start."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
AUDIT = (ROOT / "scripts" / "migration" / "audit_bot_to_web.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_guided_start_uses_a_closed_navigation_catalog_not_bot_callback_data() -> None:
    assert '"guided_start",' in REGISTRY
    assert '"feature_catalog",' in REGISTRY
    assert '"SIGNED_CUSTOMER_WEB_NATIVE",' in REGISTRY
    assert '"Mở catalog Web theo mục tiêu để bắt đầu workflow mới' in REGISTRY

    normalizer = _section(PORTAL, "const GUIDED_START_CAPABILITY_SPECS", "// Capability Hub is intentionally")
    for marker in (
        'key: "guided_start", featureKey: "feature_catalog", route: "/features"',
        'key: "prompt_studio", featureKey: "prompt_studio", route: "/prompt-studio"',
        'key: "image_studio", featureKey: "image_studio", route: "/image-studio"',
        'key: "media_workspace", featureKey: "media_workspace", route: "/media-workspace"',
        'key: "wallet", featureKey: "wallet", route: "/wallet"',
        'key: "support", featureKey: "support", route: "/support"',
        "function normalizeMenuCapabilities(raw)",
        'safeHubText(item.execution, 80) === "NO_EXECUTION_CLAIM"',
        "every destination repeats signed-session, ownership and feature checks",
    ):
        assert marker in normalizer
    for forbidden in ('key: "video_studio"', 'key: "wallet_topup"', 'key: "admin_', "menu|"):
        assert forbidden not in normalizer

    assert "const menuCapabilities = Array.isArray(catalogData.menu_capabilities) ? catalogData.menu_capabilities : [];" in INTEGRATION
    assert "menuCapabilities," in INTEGRATION
    assert "menuCapabilities: normalizeMenuCapabilities(source.menuCapabilities)" in PORTAL


def test_features_renders_intent_led_guided_start_without_an_execution_claim() -> None:
    guide = _section(PORTAL, "function renderFeatureGuidedStart(context)", "function renderFeatureCatalog(page, context)")
    catalog = _section(PORTAL, "function renderFeatureCatalog(page, context)", "function validWorkspaceDraftId")

    assert 'data-feature-guided-start' in guide
    assert 'aria-labelledby="feature-guided-start-title"' in guide
    assert 'const href = step.route === "/features" ? "#feature-catalog-list" : step.route;' in guide
    assert 'portalIcon(ICONS.arrowRight)' in guide
    assert "ứng dụng sẽ kiểm tra quyền và trạng thái thực tế" in guide
    assert "menu|" not in guide
    assert "${renderFeatureGuidedStart(context)}${renderCapabilityHub(context)}" in catalog
    assert 'id="feature-catalog-list"' in catalog
    assert ".portal-start-guide-step" in CSS
    assert "scroll-margin-top: 20px" in CSS
    assert ".portal-start-guide-step { transition: none !important; }" in CSS


def test_audit_maps_only_safe_main_guide_navigation_and_explicitly_defers_video() -> None:
    for marker in (
        "GUIDED_START_FRESH_WEB_NAVIGATION_ACTIONS",
        '"menu|guide_quick_start"',
        '"target": "/features"',
        '"menu|guide_faq"',
        '"target": "/support"',
        "NO_RAW_TELEGRAM_ID_BROWSER_INPUT",
        "GUIDED_VIDEO_MENU_DEFERRED_ACTIONS",
        '"menu|guide_video_ai"',
        '"menu|guide_guided_video"',
        '"target": "GUIDED_VIDEO_MENU_DEFERRED"',
        "guided_video_menu_deferred_until_video_menu_phase",
        "GUIDED_START_CALLBACK_CONTRACT.md",
    ):
        assert marker in AUDIT

    contract = (ROOT / "docs" / "migration" / "NON_VIDEO_MENU_NAVIGATION_CATALOG.md").read_text(encoding="utf-8")
    assert "menu|guide_quick_start" in contract
    assert "menu|guide_faq" in contract
    assert "GUIDED_VIDEO_MENU_DEFERRED" in contract

    generated_contract = (ROOT / "docs" / "migration" / "GUIDED_START_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    for marker in (
        "# Main Guide callback contract",
        "menu\\|guide_quick_start",
        "menu\\|guide_faq",
        "GUIDED_VIDEO_MENU_DEFERRED",
        "raw Telegram-ID field",
    ):
        assert marker in generated_contract
