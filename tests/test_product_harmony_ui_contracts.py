"""Regression contracts for the final teal--sky product-harmony layer."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
SPEC = (ROOT / "docs" / "superpowers" / "specs" / "2026-07-27-product-harmony-teal-sky-design.md").read_text(encoding="utf-8")


PRODUCT_HARMONY_MARKER = "/* Product Harmony -- final light teal-sky application layer. */"
ADMIN_HOME_KEYS = (
    "adminHome.title",
    "adminHome.guard.kicker",
    "adminHome.guard.verifiedTitle",
    "adminHome.guard.pendingTitle",
    "adminHome.metrics.users",
    "adminHome.metrics.engineJobs",
    "adminHome.metrics.workerJobs",
    "adminHome.metrics.payments",
    "adminHome.metrics.readiness",
    "adminHome.queues.kicker",
    "adminHome.queues.title",
    "adminHome.queues.body",
    "adminHome.readiness.kicker",
    "adminHome.readiness.title",
    "adminHome.readiness.body",
    "adminHome.authority.summary",
)


def _root_declarations() -> str:
    match = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", THEME, flags=re.DOTALL)
    assert match is not None
    return match.group("declarations")


def product_harmony_css() -> str:
    marker = THEME.find(PRODUCT_HARMONY_MARKER)
    return "" if marker < 0 else THEME[marker:]


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_product_harmony_defines_semantic_geometry_and_no_raw_paint() -> None:
    root = _root_declarations()
    for token in (
        "--portal-rail-width: 272px;",
        "--portal-content-max-width: 1600px;",
        "--portal-desktop-page-padding: clamp(24px, 3vw, 40px);",
        "--portal-mobile-page-padding: 16px;",
        "--portal-mobile-content-inset: 104px;",
        "--portal-section-gap: clamp(20px, 2.4vw, 30px);",
    ):
        assert token in root

    harmony = product_harmony_css()
    assert PRODUCT_HARMONY_MARKER in harmony
    assert "grid-template-columns: var(--portal-rail-width) minmax(0, 1fr);" in harmony
    assert "max-width: var(--portal-content-max-width);" in harmony
    assert "padding-bottom: calc(var(--portal-mobile-content-inset) + var(--portal-safe-bottom));" in harmony
    assert "linear-gradient" not in harmony
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", harmony)


def test_product_harmony_keeps_dashboard_summary_even_on_a_phone() -> None:
    harmony = product_harmony_css()
    assert ".portal-workspace-command-center .portal-dashboard-overview-stats {" in harmony
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in harmony
    assert "@media (max-width: 460px)" not in harmony


def test_admin_home_visible_hero_uses_the_reviewed_localized_title() -> None:
    localized_title = _section(PORTAL, "function localizedPageTitle(page, context)", "function documentTitle")
    document_title = _section(PORTAL, "function documentTitle(page, context)", "function localizedPageDescription")
    hero = _section(PORTAL, "function renderHero(page, context)", "const FEATURE_CATALOG_GROUPS")

    assert 'if (path === "/admin") return uiText("adminHome.title", fallback);' in localized_title
    assert "localizedPageTitle(page, context)" in document_title
    assert "localizedPageTitle(page, context)" in hero


def test_product_harmony_repairs_dashboard_quick_start_light_surfaces() -> None:
    harmony = product_harmony_css()
    for selector in (
        ".portal-start-guide {",
        ".portal-start-guide-step {",
        ".portal-start-guide-head h2",
        ".portal-start-guide-head p",
        ".portal-start-guide-copy small",
        ".portal-start-guide-copy strong",
        ".portal-start-guide-copy p",
        ".portal-start-guide-number {",
        ".portal-start-guide-step:hover,",
        ".portal-start-guide-step:focus-visible {",
    ):
        assert selector in harmony
    for token in (
        "var(--portal-surface-strong)",
        "var(--portal-surface-light)",
        "var(--portal-surface-soft)",
        "var(--portal-border)",
        "var(--portal-ink)",
        "var(--portal-muted)",
        "var(--portal-context)",
    ):
        assert token in harmony
    assert "rgba(" not in harmony


def test_admin_authority_nested_content_stays_readable_on_light_cards() -> None:
    harmony = product_harmony_css()
    assert re.search(
        r"\.portal-admin-authority > \.portal-card \.portal-card-title,\s*"
        r"\.portal-admin-authority > \.portal-card \.portal-summary-value\s*\{[^}]*"
        r"color:\s*var\(--portal-ink\);",
        harmony,
        flags=re.DOTALL,
    )
    assert re.search(
        r"\.portal-admin-authority > \.portal-card \.portal-card-subtitle,\s*"
        r"\.portal-admin-authority > \.portal-card \.portal-summary-key\s*\{[^}]*"
        r"color:\s*var\(--portal-muted\);",
        harmony,
        flags=re.DOTALL,
    )


def test_quick_start_small_informational_copy_uses_accessible_action_text() -> None:
    harmony = product_harmony_css()
    assert re.search(
        r"\.portal-start-guide-copy small,\s*\.portal-start-guide-copy em\s*\{[^}]*"
        r"color:\s*var\(--portal-action\);",
        harmony,
        flags=re.DOTALL,
    )
    assert ".portal-start-guide-step:focus-visible" in harmony
    assert "outline: 3px solid var(--portal-context) !important;" in harmony


def test_product_harmony_repairs_catalog_context_customer_canvas() -> None:
    harmony = product_harmony_css()
    for selector in (
        ".portal-catalog-context {",
        ".portal-catalog-context strong",
        ".portal-catalog-context p",
        ".portal-catalog-context > .portal-module-icon",
        ".portal-catalog-context > .portal-badge",
    ):
        assert selector in harmony
    assert re.search(
        r"\.portal-catalog-context\s*\{[^}]*border-color:\s*var\(--portal-border\);[^}]*"
        r"background:\s*var\(--portal-surface-light\);[^}]*color:\s*var\(--portal-ink\);",
        harmony,
        flags=re.DOTALL,
    )
    assert "rgba(" not in harmony
    assert "linear-gradient" not in harmony
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", harmony)


def test_admin_overview_uses_reviewed_copy_and_a_closed_svg_icon() -> None:
    overview = _section(PORTAL, "function renderAdminOverview(page, context)", "function renderAdminSystemStewardship")

    assert "const adminText" in overview
    assert "adminHome.title" in overview
    assert "portalIcon(ICONS.security)" in overview
    assert 'aria-hidden="true">⌘</span>' not in overview
    for key in ADMIN_HOME_KEYS:
        assert I18N.count(f'"{key}"') == 3


def test_admin_erp_final_layer_is_light_teal_sky_and_keeps_authority_unchanged() -> None:
    harmony = product_harmony_css()
    for selector in (
        ".portal-admin-home > .portal-admin-grid .portal-metric",
        ".portal-admin-work-queues",
        ".portal-admin-work-queue",
        ".portal-admin-authority",
        ".portal-admin-directory-group",
        ".portal-admin-directory-group > .portal-module-grid .portal-module-card",
    ):
        assert selector in harmony
    for token in (
        "var(--portal-surface-light)",
        "var(--portal-surface-strong)",
        "var(--portal-border)",
        "var(--portal-ink)",
        "var(--portal-muted)",
        "var(--portal-context)",
    ):
        assert token in harmony
    assert "canonical signed-admin and route-authority protections" in SPEC
