"""Static contracts for the always-on, navigation-only Feature Family Explorer.

The explorer is deliberately a small, fixed Web directory.  It must not turn
catalogue discovery into a second capability, billing, provider, job, or Bot
state surface.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")


FAMILY_KEYS = ("content", "image", "video", "voice", "music", "subtitle", "documents")


def _function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:] if end == -1 else source[start:end]


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_feature_family_explorer_uses_a_closed_member_manifest_directory() -> None:
    explorer = _function(PORTAL, "renderFeatureFamilyExplorer")
    allowlist = re.search(
        r"const FEATURE_FAMILY_EXPLORER_KEYS = Object\.freeze\(\s*\[(?P<items>.*?)\]\s*\);",
        PORTAL,
        re.DOTALL,
    )

    assert allowlist, "The explorer must own an explicit, closed family allowlist."
    assert tuple(re.findall(r'"([^"]+)"', allowlist.group("items"))) == FAMILY_KEYS
    assert "FEATURE_FAMILY_EXPLORER_KEYS" in explorer
    assert "const route = `/features/${familyKey}`;" in explorer
    assert "const page = manifest[normalizePath(route)];" in explorer
    assert 'page && page.access === "member"' in explorer
    assert '<a class="portal-feature-family-explorer-card" href="${safeText(route)}"' in explorer
    assert '<section class="portal-feature-family-explorer"' in explorer
    assert 'aria-labelledby="portal-feature-family-explorer-title"' in explorer


def test_feature_catalog_places_search_then_intent_navigation_before_studio_and_detail() -> None:
    catalog = _function(PORTAL, "renderFeatureCatalog")
    explorer_call = re.search(r"\$\{renderFeatureFamilyExplorer\([^}]*\)\}", catalog)

    assert explorer_call, "The /features renderer must include the always-on explorer."
    assert catalog.index("${renderHero(page, context)}") < explorer_call.start()
    assert catalog.index("${search}") < explorer_call.start() < catalog.index("${jumps}")
    assert catalog.index("${jumps}") < catalog.index("${studioContinuation}") < catalog.index("${body}")
    assert catalog.index("${body}") < catalog.index("${renderRouteEngineBoundary(context)}")
    assert catalog.index("${body}") < catalog.index("${renderFeatureGuidedStart(context)}")
    assert catalog.index("${renderFeatureGuidedStart(context)}") < catalog.index("${renderCapabilityHub(context)}")
    assert "renderRouteEngineBoundary(context)" in catalog


def test_feature_family_explorer_has_complete_vi_en_zh_copy() -> None:
    explorer = _function(PORTAL, "renderFeatureFamilyExplorer")
    keys = (
        "featureCatalog.familyExplorer.kicker",
        "featureCatalog.familyExplorer.title",
        "featureCatalog.familyExplorer.body",
        "featureCatalog.familyExplorer.open",
    )

    for key in keys:
        assert I18N.count(f'"{key}"') == 3, key
        assert f'featureCatalogText("{key.removeprefix("featureCatalog.")}"' in explorer


def test_feature_family_explorer_uses_workspace_motion_and_accessible_aura_layout() -> None:
    explorer = _function(PORTAL, "renderFeatureFamilyExplorer")
    target_selector = _between(MOTION, "const targetSelector = [", '].join(", ");')
    item_selector = _between(MOTION, "const itemSelector = [", '].join(", ");')

    assert '<nav class="portal-feature-family-explorer-grid"' in explorer
    for requirement in (
        ".portal-feature-family-explorer {",
        ".portal-feature-family-explorer-grid {",
        ".portal-feature-family-explorer-card {",
        ".portal-feature-family-explorer-card:focus-visible",
        "repeat(3, minmax(0, 1fr))",
        "repeat(2, minmax(0, 1fr))",
        "grid-template-columns: minmax(0, 1fr)",
        "min-height: 44px",
        "var(--portal-",
    ):
        assert requirement in THEME
    assert re.search(
        r"@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]{0,2500}\.portal-feature-family-explorer",
        THEME,
    )
    assert '".portal-feature-family-explorer"' in target_selector
    assert '".portal-feature-family-explorer-card"' in item_selector


def test_feature_family_explorer_is_independent_navigation_without_inferred_state() -> None:
    explorer = _function(PORTAL, "renderFeatureFamilyExplorer").lower()

    for forbidden in (
        "fetch(",
        "localstorage",
        "sessionstorage",
        "data-portal-action",
        "dispatch(",
        "dispatchevent(",
        "capabilityhub",
        "provider",
        "payment",
        "wallet",
        "job",
        "readiness",
        "customercommandcount",
        "mappedroutecount",
        "guardedroutecount",
        "telegramonlycount",
        "data-count",
        "fake",
    ):
        assert forbidden not in explorer


def test_feature_family_navigation_routes_do_not_reenter_the_detailed_catalogue() -> None:
    helper = _function(PORTAL, "isFeatureFamilyExplorerRoute")
    fallback = _function(PORTAL, "fallbackFeatureCatalog")
    customer_catalog = _function(PORTAL, "customerCatalog")

    assert "FEATURE_FAMILY_EXPLORER_KEYS" in helper
    assert "normalizePath(path)" in helper
    assert "isFeatureFamilyExplorerRoute(page.path)" in fallback
    assert "!isFeatureFamilyExplorerRoute(route)" in customer_catalog


def test_customer_catalog_keeps_only_registered_customer_routes_from_server_catalogue() -> None:
    customer_catalog = _function(PORTAL, "customerCatalog")

    assert "const page = route ? manifest[normalizePath(route)] : null;" in customer_catalog
    assert 'page && page.access === "member"' in customer_catalog
    assert "page.access !== \"admin\"" in customer_catalog
    assert "!isFeatureFamilyExplorerRoute(route)" in customer_catalog
    assert "return entries.length ? entries : fallbackFeatureCatalog();" in customer_catalog


def test_feature_family_page_shows_sibling_directory_before_operational_detail() -> None:
    family = _function(PORTAL, "renderFeatureFamily")

    assert family.index("${renderHero(page, context)}") < family.index("${familyNav}")
    assert family.index("${familyNav}") < family.index('<div class="portal-status-grid">')
    assert family.index("${familyNav}") < family.index("${renderRouteEngineBoundary(context)}")
    assert family.count("${familyNav}") == 1


def test_feature_family_page_keeps_current_studio_visible_in_its_closed_switcher() -> None:
    family = _function(PORTAL, "renderFeatureFamily")

    assert "FEATURE_FAMILY_KEYS.map((groupKey) => {" in family
    assert "const route = `/features/${groupKey}`;" in family
    assert 'const memberPage = manifest[normalizePath(route)];' in family
    assert 'memberPage && memberPage.access === "member"' in family
    assert 'class="portal-feature-jump portal-feature-jump--current" aria-current="page"' in family
    assert 'class="portal-feature-jump" href="${safeText(route)}"' in family
    assert "groupKey === family.key" in family


def test_feature_family_switcher_uses_only_local_navigation_and_current_page_semantics() -> None:
    family = _function(PORTAL, "renderFeatureFamily").lower()

    for forbidden in (
        "fetch(",
        "localstorage",
        "sessionstorage",
        "data-portal-action",
        "provider",
        "payment",
        "wallet",
        "job",
        "telegram",
    ):
        assert forbidden not in family


def test_feature_family_current_studio_chip_has_token_only_accessible_responsive_presentation() -> None:
    for requirement in (
        ".portal-feature-jump {",
        ".portal-feature-jump--current {",
        ".portal-feature-jump:focus-visible",
        "min-height: 44px",
        "var(--portal-",
    ):
        assert requirement in THEME
    current_rule = _between(THEME, ".portal-feature-jump--current {", ".portal-feature-jump--current:focus-visible")
    assert "#" not in current_rule
    assert re.search(
        r"@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]{0,2500}\.portal-feature-jump",
        THEME,
    )


def test_feature_family_explorer_registers_every_closed_family_and_localizes_its_navigation_label() -> None:
    navigation = _between(PORTAL, "const NAVIGATION_I18N_KEYS", "function localizedNavigationLabel")
    registration = _between(
        PORTAL,
        "FEATURE_FAMILY_EXPLORER_KEYS.forEach((familyKey) => {",
        "function safeCatalogRoute",
    )

    for family in FAMILY_KEYS:
        assert f'"{family}"' in PORTAL
    assert 'customerPage(`/features/${familyKey}`' in registration
    assert "featureCatalogGroup(familyKey)" in registration
    for requirement in ('type: "feature-family"', 'layout: "feature-family"', 'status: "read_only"'):
        assert requirement in registration
    for label, key in (
        ("Music & SFX", "featureCatalog.group.music.title"),
        ("Phụ đề & ngôn ngữ", "featureCatalog.group.subtitle.title"),
        ("Documents & PDF", "featureCatalog.group.documents.title"),
    ):
        assert f'"{label}": "{key}"' in navigation
