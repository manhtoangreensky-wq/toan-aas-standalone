"""Static contracts for the reviewed feature-catalogue presentation shell.

The server continues to own workflow records, feature readiness, route
authorization and public-sale pricing. These contracts deliberately cover only
the fixed Portal chrome that must follow the signed interface locale.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:] if end == -1 else source[start:end]


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_feature_catalogue_chrome_has_reviewed_vi_en_zh_messages() -> None:
    keys = (
        "featureCatalog.page.title",
        "featureCatalog.page.description",
        "featureCatalog.group.account.title",
        "featureCatalog.group.content.title",
        "featureCatalog.group.documents.description",
        "featureCatalog.group.free_tools.title",
        "featureCatalog.group.free_tools.description",
        "featureCatalog.guidedStart.title",
        "featureCatalog.capabilityHub.title",
        "featureCatalog.search.label",
        "featureCatalog.search.result.matches",
        "featureCatalog.engine.webNative",
        "featureCatalog.readiness.available",
        "featureCatalog.family.summary.title",
        "featureCatalog.action.openWorkflow",
    )

    for key in keys:
        assert I18N.count(f'"{key}"') == 3, key


def test_feature_catalogue_routes_fixed_chrome_through_i18n_without_price_surface() -> None:
    catalog = _between(PORTAL, "function renderFeatureCatalog(page, context)", "function workspaceMenuText")
    family = _between(PORTAL, "function renderFeatureFamily(page, context)", "function normalizeCatalogSearch")
    guided_start = _function(PORTAL, "renderFeatureGuidedStart")
    capability_hub = _between(PORTAL, "function renderCapabilityHubFamilyMetrics", "function renderModuleCards")
    module_card = _between(PORTAL, "function moduleCard(module, context, label, options)", "function fallbackCatalogGroup")
    engine_label = _function(PORTAL, "renderEngineLabel")
    readiness_label = _function(PORTAL, "renderReadinessLabel")
    search = _function(PORTAL, "filterFeatureCatalog")

    assert "function featureCatalogText(" in PORTAL
    assert "function featureCatalogGroupCopy(" in PORTAL
    assert "featureCatalogGroupCopy(" in catalog
    assert "featureCatalogText(" in catalog
    assert "featureCatalogGroupCopy(" in family
    assert "featureCatalogText(" in family
    assert "featureCatalogText(" in guided_start
    assert "featureCatalogText(" in capability_hub
    assert "featureCatalogText(" in module_card
    assert "featureCatalogText(" in engine_label
    assert "featureCatalogText(" in readiness_label
    assert "featureCatalogText(" in search

    for forbidden in ("public_sale_catalog", "sale_price_xu", "cost_xu", "price_vnd", "provider", "fallback"):
        assert forbidden not in catalog
        assert forbidden not in family


def test_feature_family_hero_uses_reviewed_group_copy_and_keeps_route_engine_guard() -> None:
    title = _function(PORTAL, "localizedPageTitle")
    description = _function(PORTAL, "localizedPageDescription")
    route_engine = _function(PORTAL, "renderRouteEngineBoundary")

    assert "featureCatalogGroupCopy(" in title
    assert "featureCatalogGroupCopy(" in description
    assert 'role="status"' in route_engine
    assert "data-portal-action" not in route_engine
