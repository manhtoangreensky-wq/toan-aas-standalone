"""Static UI/API boundary checks for product-readiness labels."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_projects_a_display_only_product_readiness_descriptor() -> None:
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    readiness = ROOT / "copyfast_product_readiness.py"

    assert readiness.exists(), "the centralized product-readiness registry is missing"
    assert "from copyfast_product_readiness import readiness_descriptor" in api
    assert 'item["readiness"] = readiness_descriptor' in api
    catalog = api[api.index("async def feature_catalog():"):api.index('@router.get("/core/status")')]
    assert "flags = _flags()\n    bridge_ready = bridge_configured()" in catalog
    assert "bridge_ready=bridge_ready" in catalog
    assert catalog.index("bridge_ready = bridge_configured()") < catalog.index('item["readiness"] = readiness_descriptor')


def test_portal_renders_a_closed_readiness_label_without_using_it_as_authority() -> None:
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
    theme = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
    i18n = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")

    assert 'const CATALOG_READINESS_STATES = new Set(["available", "planning_only", "local_execution", "canonical_read", "guarded", "disabled"])' in portal
    assert "function normalizeCatalogReadiness(raw)" in portal
    assert "function renderReadinessLabel(module)" in portal
    assert "readiness; không xác nhận job, payment hoặc output." in portal
    assert "${renderReadinessLabel(module)}" in portal
    assert '.portal-readiness-label[data-readiness="available"]' in css
    assert '.portal-readiness-label[data-readiness="planning_only"]' in css
    assert '.portal-readiness-label[data-readiness="local_execution"]' in css
    assert '.portal-readiness-label[data-readiness="canonical_read"]' in css
    assert '.portal-readiness-label[data-readiness="guarded"]' in css
    assert '.portal-readiness-label[data-readiness="disabled"]' in css
    assert '.portal-page .portal-module-card .portal-readiness-label[data-readiness="available"]' in theme
    assert '.portal-page .portal-module-card .portal-readiness-label[data-readiness="disabled"]' in theme
    assert '"catalog.readiness.available"' in i18n
    assert '"catalog.readiness.planning_only"' in i18n
    assert '"catalog.readiness.local_execution"' in i18n
    assert '"catalog.readiness.canonical_read"' in i18n
    assert '"catalog.readiness.guarded"' in i18n
    assert '"catalog.readiness.disabled"' in i18n

    label = portal[portal.index("function renderReadinessLabel(module)"):portal.index("function catalogEntryState(module, page, context)")]
    state = portal[portal.index("function catalogEntryState(module, page, context)"):portal.index("function moduleCard(module, context, label, options)")]
    assert "canAct" not in label
    assert "fetch(" not in label
    assert "api(" not in label
    assert "provider" not in label.lower()
    assert "wallet" not in label.lower()
    assert "module.readiness" not in state
    assert "normalizeCatalogReadiness" not in state


def test_catalog_cards_do_not_pair_readiness_with_a_conflicting_legacy_badge() -> None:
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    card = portal[portal.index("function moduleCard(module, context, label, options)"):portal.index("function fallbackCatalogGroup(path)")]

    assert (
        '? `<span class="portal-module-card-signals">${renderEngineLabel(module)}${renderReadinessLabel(module)}</span>`\n'
        "      : badge(displayState);"
    ) in card
