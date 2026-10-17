"""Red contracts for the customer PWA and internal ERP shell distinction.

The contracts are deliberately presentation-only.  They must not let browser
state create an Admin route, change a signed-session decision, or broaden the
public-shell-only PWA cache policy.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_mount_marks_customer_and_admin_app_shells_without_changing_route_authority() -> None:
    mount = _section(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")

    assert 'const appKind = isAdminPortalSurface(page) ? "admin" : "customer";' in mount
    assert "shell.dataset.portalAppKind = appKind;" in mount
    assert "document.body.dataset.portalAppKind = appKind;" in mount
    assert 'mobileNav.dataset.portalMobileNavKind = appKind;' in mount
    assert 'mobileNav.removeAttribute("data-portal-mobile-nav-kind");' in mount
    assert "context.isAdmin" not in mount
    assert "isAdminMobileSurface(page) ? renderAdminMobileNav(page, context) : renderMobileNav(page)" in mount


def test_customer_dock_uses_app_words_in_all_reviewed_interface_locales() -> None:
    dock = _section(PORTAL, "function renderMobileNav(page) {", "function isAdminMobileSurface(page)")

    assert '["studio", "/studio", uiText("mobile.studio", "Công cụ"), ICONS.video]' in dock
    assert '["publishing", "/publishing", uiText("mobile.publishing", "Đăng bài"), ICONS.reports]' in dock
    assert '["projects", "/projects", uiText("mobile.projects", "Dự án"), ICONS.dashboard]' in dock
    assert '["wallet", "/wallet", uiText("mobile.wallet", "Ví Xu"), ICONS.wallet]' in dock
    assert '["account", "/account", uiText("mobile.account", "Tài khoản"), ICONS.account]' in dock

    for locale_values in (
        (
            '"mobile.studio": "Công cụ"',
            '"mobile.publishing": "Đăng bài"',
            '"mobile.projects": "Dự án"',
            '"mobile.wallet": "Ví Xu"',
        ),
        (
            '"mobile.studio": "Studio"',
            '"mobile.publishing": "Publishing"',
            '"mobile.projects": "Projects"',
            '"mobile.wallet": "Credits"',
        ),
        (
            '"mobile.studio": "工作室"',
            '"mobile.publishing": "发布"',
            '"mobile.projects": "项目"',
            '"mobile.wallet": "积分"',
        ),
    ):
        for value in locale_values:
            assert value in I18N


def test_app_docks_have_distinct_aura_surfaces_safe_area_and_motion_fallback() -> None:
    assert '.portal-mobile-nav[data-portal-mobile-nav-kind="customer"]' in THEME
    assert '.portal-mobile-nav[data-portal-mobile-nav-kind="admin"]' in THEME
    assert "var(--portal-safe-bottom)" in THEME
    assert "min-height: 44px;" in THEME
    assert "@keyframes portal-mobile-dock-enter" in THEME
    assert "animation: portal-mobile-dock-enter var(--portal-motion-base) var(--portal-motion-ease-emphasis) both;" in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME
    assert '.portal-mobile-nav[data-portal-mobile-nav-kind] {' in THEME
    assert "animation: none !important;" in THEME


def test_customer_and_admin_surfaces_receive_motion_without_new_authority_or_data_paths() -> None:
    """Keep app-wide motion presentational, bounded and accessibility-safe."""
    assert '@keyframes portal-app-surface-enter' in THEME
    assert '.portal-shell[data-portal-app-kind="customer"] .portal-page' in THEME
    assert '.portal-shell[data-portal-app-kind="admin"] .portal-page' in THEME
    assert 'animation: portal-app-surface-enter var(--portal-motion-base) var(--portal-motion-ease-emphasis) both;' in THEME
    assert '.portal-dashboard-app .portal-dashboard-overview' in THEME
    assert '.portal-admin-home .portal-admin-work-queue' in THEME
    assert 'animation-delay: calc(var(--portal-app-motion-index, 0) * 34ms);' in THEME
    assert 'transform: translateY(-1px);' in THEME
    assert '.portal-shell[data-portal-app-kind] .portal-page' in THEME
    assert 'animation: none !important;' in THEME

    mount = _section(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")
    assert "data-portal-app-kind" not in mount
    assert "context.isAdmin" not in mount
