"""Portal contracts for the signed Community Trust Center."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


def test_community_replaces_the_command_handoff_with_a_signed_trust_center() -> None:
    assert 'WebFeature("community", "Cộng đồng", "account", "/community", description="Kênh chính thức, community và anti-impersonation guidance được Web App kiểm tra riêng; không replay state Bot."' in REGISTRY
    assert 'customerPage("/community", "Cộng đồng"' in PORTAL
    assert 'type: "community-trust-center", layout: "community-trust-center", fields: [], action: "none", status: "read_only"' in PORTAL
    assert 'botCompanionPage("/community",' not in PORTAL
    assert 'case "community-trust-center": return renderCommunityTrustCenter(page, context);' in PORTAL


def test_trust_center_only_renders_server_checked_routes_and_urls() -> None:
    renderer = _between(PORTAL, "function renderCommunityTrustCenter", "function renderBotCompanion")
    for requirement in (
        "context.communityTrustCatalog",
        "context.communityTrustReadState",
        "target=\"_blank\" rel=\"noopener noreferrer\"",
        "availability === \"ready\"",
        "availability === \"guarded\"",
        "Mở kênh",
        "renderNotes(page)",
    ):
        assert requirement in renderer
    for forbidden in (
        "copy-bot-companion-command",
        "telegram_id",
        "callback_data",
        "localStorage",
        "sessionStorage",
        "fetch(",
        "api(",
        "data-portal-action",
        "/internal/",
    ):
        assert forbidden not in renderer


def test_trust_center_hydration_fails_closed_for_malformed_or_external_data() -> None:
    normalizer = _between(INTEGRATION, "const COMMUNITY_TRUST_CHANNEL_IDS", "const GUIDE_CENTER_GROUP_IDS")
    hydration = _between(INTEGRATION, "function communityTrustRequestIsCurrent", "async function hydrateGuideCenter")
    for requirement in (
        'new Set(["website", "workspace", "telegram_bot", "community", "support"])',
        'new Set(["/dashboard", "/support"])',
        "function communityTrustUrl",
        'url.protocol === "https:"',
        "COMMUNITY_TRUST_EXTERNAL_HOSTS[id]",
        "communityTrustCatalogIsSafe",
        "web_native_community_trust_center",
        "notification_sent",
    ):
        assert requirement in normalizer
    for requirement in (
        'api("/community/trust-center", { cache: "no-store" })',
        "communityTrustCatalogIsSafe(catalog)",
        "communityTrustHydrationEpoch",
        "communityTrustSessionEpoch",
        'communityTrustReadState: "ready"',
        'communityTrustReadState: "failed"',
        '"/community": "read_only"',
    ):
        assert requirement in hydration
    assert "localStorage" not in hydration
    assert "sessionStorage" not in hydration
    assert "copy-bot-companion-command" not in hydration


def test_trust_center_binds_each_card_to_its_single_approved_destination() -> None:
    """A valid host or route for one card cannot be reused by another card."""

    integration = _between(INTEGRATION, "const COMMUNITY_TRUST_CHANNEL_IDS", "const GUIDE_CENTER_GROUP_IDS")
    portal = _between(PORTAL, "const COMMUNITY_TRUST_CHANNEL_IDS", "// Guide Center")
    for source in (integration, portal):
        for requirement in (
            "const COMMUNITY_TRUST_CHANNEL_KINDS = Object.freeze({",
            "const COMMUNITY_TRUST_EXTERNAL_HOSTS = Object.freeze({",
            "website: new Set([\"toanaas.vn\", \"www.toanaas.vn\"])",
            "telegram_bot: new Set([\"t.me\"])",
            "community: new Set([\"t.me\"])",
            "const COMMUNITY_TRUST_INTERNAL_ROUTE_BY_ID = Object.freeze({ workspace: \"/dashboard\", support: \"/support\" });",
            "COMMUNITY_TRUST_CHANNEL_KINDS[id] === kind",
            "COMMUNITY_TRUST_INTERNAL_ROUTE_BY_ID[id] ===",
        ):
            assert requirement in source


def test_trust_center_is_localized_accessible_responsive_and_private() -> None:
    for key in (
        "page.communityTrust.title",
        "page.communityTrust.description",
        "communityTrust.loadingTitle",
        "communityTrust.guardedTitle",
        "communityTrust.failedTitle",
    ):
        assert I18N.count(f'"{key}":') == 3
    for selector in (
        ".portal-community-trust-center",
        ".portal-community-trust-grid",
        ".portal-community-trust-card:focus-visible",
        ".portal-community-trust-safety",
    ):
        assert selector in CSS
    assert "@media (max-width: 700px)" in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert '"/" + "api/v1/community"' in WORKER
    assert '"/community"' in WORKER
