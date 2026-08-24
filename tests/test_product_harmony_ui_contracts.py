"""Regression contracts for the final teal--sky product-harmony layer."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
SPEC = (ROOT / "docs" / "superpowers" / "specs" / "2026-07-27-product-harmony-teal-sky-design.md").read_text(encoding="utf-8")


PRODUCT_HARMONY_MARKER = "/* Product Harmony -- final light teal-sky application layer. */"
ADMIN_HOME_KEYS = (
    "adminHome.title",
    "adminHome.guard.kicker",
    "adminHome.guard.verifiedTitle",
    "adminHome.guard.pendingTitle",
    "adminHome.guard.verifiedBody",
    "adminHome.guard.pendingBody",
    "adminHome.metrics.users",
    "adminHome.metrics.engineJobs",
    "adminHome.metrics.workerJobs",
    "adminHome.metrics.payments",
    "adminHome.metrics.readiness",
    "adminHome.metrics.usersNote",
    "adminHome.metrics.engineJobsNote",
    "adminHome.metrics.workerJobsNote",
    "adminHome.metrics.paymentsNote",
    "adminHome.metrics.readinessNote",
    "adminHome.directory.kicker",
    "adminHome.directory.title",
    "adminHome.directory.mode.canonicalAdmin",
    "adminHome.directory.mode.supportRole",
    "adminHome.directory.mode.webLocalAdmin",
    "adminHome.directory.mode.serverAuthorized",
    "adminHome.directory.description",
    "adminHome.directory.moduleCount",
    "adminHome.directory.openAction",
    "adminHome.queues.kicker",
    "adminHome.queues.title",
    "adminHome.queues.body",
    "adminHome.queues.support.title",
    "adminHome.queues.support.body",
    "adminHome.queues.failedJobs.title",
    "adminHome.queues.failedJobs.body",
    "adminHome.queues.jobs.title",
    "adminHome.queues.jobs.body",
    "adminHome.queues.payments.title",
    "adminHome.queues.payments.body",
    "adminHome.queues.users.title",
    "adminHome.queues.users.body",
    "adminHome.queues.audit.title",
    "adminHome.queues.audit.body",
    "adminHome.readiness.kicker",
    "adminHome.readiness.title",
    "adminHome.readiness.body",
    "adminHome.readiness.refresh",
    "adminHome.readiness.table.feature",
    "adminHome.readiness.table.status",
    "adminHome.readiness.table.adapter",
    "adminHome.readiness.emptyTitle",
    "adminHome.readiness.emptyBody",
    "adminHome.authority.summary",
)

TABLE_HORIZONTAL_SCROLL_KEYS = (
    "table.horizontalScroll.region",
    "table.horizontalScroll.hint",
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


def _declarations_after(source: str, selector: str, offset: int) -> str:
    selector_offset = source.index(selector, offset)
    opening = source.index("{", selector_offset)
    closing = source.index("}", opening)
    return source[opening + 1 : closing]


def test_product_harmony_defines_semantic_geometry_and_no_raw_paint() -> None:
    root = _root_declarations()
    for token in (
        "--portal-rail-width: 272px;",
        "--portal-content-max-width: 1600px;",
        "--portal-desktop-page-padding: clamp(24px, 3vw, 40px);",
        "--portal-mobile-page-padding: 16px;",
        "--portal-mobile-content-inset: 128px;",
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


def test_mobile_utility_ctas_are_compact_accessible_and_safe_area_aware() -> None:
    pwa_media = PORTAL_CSS.index(
        "@media (max-width: 640px)",
        PORTAL_CSS.index("/* Floating PWA Install Trigger"),
    )
    pwa = _declarations_after(PORTAL_CSS, ".portal-pwa-fab-trigger", pwa_media)
    for token in (
        "bottom: calc(var(--portal-safe-bottom, 0px) + 80px);",
        "left: 12px;",
        "width: 44px;",
        "min-width: 44px;",
        "height: 44px;",
        "justify-content: center;",
        "gap: 0;",
        "padding: 0;",
        "border-radius: 50%;",
    ):
        assert token in pwa
    pwa_label = _declarations_after(PORTAL_CSS, ".portal-pwa-fab-label", pwa_media)
    assert "display: none;" in pwa_label

    copilot_render = PORTAL.index("function renderCopilotHtml")
    copilot_media = PORTAL.index("@media (max-width: 640px)", copilot_render)
    copilot = _declarations_after(PORTAL, ".portal-copilot-btn", copilot_media)
    for token in (
        "bottom: calc(var(--portal-safe-bottom, 0px) + 80px);",
        "right: 12px;",
        "width: 44px;",
        "min-width: 44px;",
        "height: 44px;",
        "justify-content: center;",
        "gap: 0;",
        "padding: 0;",
        "border-radius: 50%;",
    ):
        assert token in copilot
    copilot_label = _declarations_after(PORTAL, ".portal-copilot-btn-label", copilot_media)
    assert "display: none;" in copilot_label
    assert 'aria-label="Mở Trợ Lý AI AAS BOT"' in PORTAL
    assert '${portalIcon(ICONS.chat)}' in PORTAL
    assert '<span>🤖</span>' not in PORTAL


def test_product_harmony_keeps_dashboard_summary_even_on_a_phone() -> None:
    harmony = product_harmony_css()
    assert ".portal-workspace-command-center .portal-dashboard-overview-stats {" in harmony
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in harmony
    decision_marker = "/* Dashboard decision hierarchy -------------------------------------------"
    assert decision_marker in harmony
    decision_layer = harmony[harmony.index(decision_marker):]
    assert "@media (max-width: 460px)" in decision_layer
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in decision_layer


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


def test_admin_home_and_table_chrome_keys_exist_in_each_locale() -> None:
    for key in (*ADMIN_HOME_KEYS, *TABLE_HORIZONTAL_SCROLL_KEYS):
        assert I18N.count(f'"{key}"') == 3


def test_admin_home_fixed_chrome_uses_i18n_without_translating_server_data() -> None:
    directory = _section(PORTAL, "function renderAdminDirectory(context)", "function renderAdminWorkQueues(context)")
    queues = _section(PORTAL, "function renderAdminWorkQueues(context)", "function renderAdminOverview(page, context)")
    overview = _section(PORTAL, "function renderAdminOverview(page, context)", "function renderAdminSystemStewardship")
    scoped_chrome = "\n".join((directory, queues, overview))

    for renderer in (directory, queues, overview):
        assert "const adminText" in renderer
    for key in ADMIN_HOME_KEYS:
        chrome_key = re.escape(key.removeprefix("adminHome."))
        assert re.search(rf'adminText\(\s*"{chrome_key}"', scoped_chrome)
    assert "portalIcon(ICONS.security)" in overview
    assert 'aria-hidden="true">⌘</span>' not in overview

    # Only fixed browser chrome belongs in this catalog. The signed manifest's
    # group/module titles, descriptions, readiness keys, and adapter values
    # remain data supplied by the server and must stay untouched.
    assert "safeText(group.title)" in directory
    assert "safeText(group.description)" in directory
    assert "safeText(entry" not in directory
    assert "safeText(key)" in overview
    assert "safeText(item && item.adapter" in overview

    # Vietnamese fallback values remain deliberate when the tiny local i18n
    # bundle has not loaded. The rendered path, including every fixed Admin
    # label above, still goes through adminText rather than directly emitting
    # a browser-owned string.


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
