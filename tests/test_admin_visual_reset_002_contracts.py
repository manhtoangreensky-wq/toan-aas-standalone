"""Presentation contracts for the approved Admin Visual Reset 002."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
MARKER = "/* Admin Visual Reset 002 ---------------------------------------------- */"


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_admin_navigation_uses_server_titles_without_redundant_erp_prefix() -> None:
    desktop = _between(PORTAL, "function adminDesktopNavGroups", "function navGroups")
    palette = _between(PORTAL, "function commandPaletteItems", "function renderCommandPalette")

    assert "label: group.title," in desktop
    assert "`ERP · ${group.title}`" not in desktop
    assert 'const section = localizedNavigationLabel(String(group.title || "Quản trị"));' in palette
    assert "issuedRoutes.has(module.route)" in desktop
    assert "authorizedAdminRoutes.has(path)" in palette


def test_admin_breadcrumb_removes_repeated_section_without_changing_customer_crumbs() -> None:
    header = _between(PORTAL, "function renderHeader(page, context)", "function renderFields")

    assert "const crumbItems = (adminSurface" in header
    assert '? ["TOAN AAS", localizedPageTitle(page, context)]' in header
    assert ': ["TOAN AAS", page.section, localizedPageTitle(page, context)])' in header
    assert '<nav class="portal-crumbs"' in header


def test_admin_reset_layer_wraps_sidebar_and_stacks_mobile_header() -> None:
    assert MARKER in THEME
    reset = THEME[THEME.index(MARKER) :]
    root = '.portal-shell[data-portal-app-kind="admin"]'

    for selector in (
        f"{root} .portal-nav-summary {{",
        f"{root} .portal-nav-label {{",
        f"{root} .portal-page.portal-admin-home > .portal-hero .portal-eyebrow {{",
    ):
        assert selector in reset
    for contract in (
        "white-space: normal;",
        "-webkit-line-clamp: 2;",
        "overflow-wrap: anywhere;",
        "text-overflow: clip;",
        "text-transform: none;",
        "@media (max-width: 700px)",
        "grid-template-rows: auto auto;",
        "grid-column: 1 / -1;",
        "min-height: 44px;",
        "@media (max-width: 460px)",
        "font-size: 28px;",
        "line-height: 1.625;",
    ):
        assert contract in reset
    assert "linear-gradient" not in reset
    assert "rgba(" not in reset
    assert "@keyframes" not in reset
