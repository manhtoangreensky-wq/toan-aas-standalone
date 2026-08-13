"""Contracts for the focused AI Studio directory presentation.

The directory is presentation-only: it may narrow the already-rendered,
server-published catalogue, but it must not invent route readiness or perform
network/provider/payment work.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")


def _function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:] if end == -1 else source[start:end]


def _rule(source: str, selector: str, end_selector: str) -> str:
    start = source.index(selector)
    end = source.find(end_selector, start + len(selector))
    return source[start:] if end == -1 else source[start:end]


def test_catalog_has_a_semantic_directory_control_bar_without_changing_route_authority() -> None:
    catalog = _function(PORTAL, "renderFeatureCatalog")

    assert 'class="portal-feature-directory-controls"' in catalog
    assert 'data-catalog-group-key="${safeText(group.key)}"' in catalog
    assert 'data-catalog-family-jump="${safeText(group.key)}"' in catalog
    assert 'aria-controls="feature-group-${safeText(group.key)}"' in catalog
    assert 'role="region"' in catalog
    assert 'aria-labelledby="feature-group-${safeText(group.key)}-title"' in catalog
    assert 'aria-live="polite"' in catalog
    assert "customerCatalog(context)" in catalog
    assert "fetch(" not in catalog.lower()
    assert "provider" not in catalog.lower()
    assert "payment" not in catalog.lower()


def test_search_hides_stale_group_jumps_and_restores_them_without_network_work() -> None:
    filter_source = _function(PORTAL, "filterFeatureCatalog")

    assert 'querySelectorAll("[data-catalog-family-jump]")' in filter_source
    assert "data-catalog-group-key" in filter_source
    assert "jump.hidden" in filter_source
    assert "group.hidden" in filter_source
    assert 'jumps[0].closest("nav")' in filter_source
    assert "jumpNavigation.hidden" in filter_source
    assert 'document.querySelector(".portal-feature-family-explorer")' in filter_source
    assert "familyExplorer.hidden = Boolean(needle)" in filter_source
    assert 'filterFeatureCatalog("")' in PORTAL
    assert "filterFeatureCatalog(\"\")" not in filter_source
    assert "fetch(" not in filter_source.lower()
    assert "dispatch(" not in filter_source.lower()
    assert "provider" not in filter_source.lower()


def test_search_updates_each_visible_group_count_from_currently_visible_items() -> None:
    filter_source = _function(PORTAL, "filterFeatureCatalog")

    assert "querySelector(\".portal-feature-count\")" in filter_source
    assert "visibleItems.length" in filter_source
    assert "data-catalog-total" in filter_source


def test_catalog_control_bar_has_token_driven_desktop_mobile_and_dark_treatment() -> None:
    controls = _rule(THEME, ".portal-feature-directory-controls {", "\n.portal-feature-directory-controls")
    assert "display: grid" in controls
    assert "var(--portal-" in controls
    assert "grid-template-columns" in controls

    for requirement in (
        ".portal-feature-directory-controls .portal-catalog-search",
        ".portal-feature-directory-controls .portal-feature-family-explorer",
        ".portal-feature-directory-controls .portal-feature-jumps",
        ".portal-feature-jump[aria-controls]",
        "min-height: 44px",
        "flex-wrap: wrap",
        "@media (prefers-reduced-motion: reduce)",
        'html[data-portal-theme="dark"] .portal-feature-directory-controls',
    ):
        assert requirement in THEME


def test_catalog_motion_uses_one_bounded_container_and_reveals_on_focus() -> None:
    target_selector = _function(MOTION, "mountWorkspace")
    assert '".portal-feature-directory-controls"' in target_selector
    item_selector = target_selector.split("const itemSelector =", 1)[1].split("].join", 1)[0]
    assert '".portal-feature-directory-controls"' not in item_selector
    assert 'target.closest(".portal-feature-directory-controls")' in target_selector
    assert "return !boundary || target === boundary" in target_selector
    assert "revealTarget(event.currentTarget)" in target_selector
    assert "WORKSPACE_REVEAL_FALLBACK_MS" in target_selector


def test_catalog_control_bar_reduced_motion_never_leaves_content_hidden() -> None:
    marker = "@media (prefers-reduced-motion: reduce) {\n  .portal-feature-directory-controls,"
    assert marker in THEME
    block = THEME[THEME.index(marker) : THEME.index("}\n\n/* Dashboard decision hierarchy", THEME.index(marker))]
    assert "opacity: 1" in block
    assert "transform: none" in block
    assert "animation: none" in block
