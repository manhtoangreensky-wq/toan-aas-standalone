"""Focused static contracts for the app-first Web workspace redesign.

These checks intentionally verify presentation boundaries only.  They do not
exercise payment, provider, authentication, or admin mutation behaviour;
those remain covered by their endpoint-specific test suites.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
REDESIGN = (ROOT / "docs" / "UX_APP_FIRST_REDESIGN.md").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_app_first_direction_is_documented_without_changing_authority_boundaries() -> None:
    assert "signed workspace and operations application, not a\nmarketing landing page" in REDESIGN
    assert "optional public introduction remains at `/welcome`" in REDESIGN
    assert "Browser state cannot disclose an admin route or grant access." in REDESIGN
    assert "does not alter Bot ownership" in REDESIGN
    assert "wallet/PayOS authority" in REDESIGN
    assert "PWA no-cache boundaries" in REDESIGN


def test_app_shell_keeps_touch_focus_motion_and_local_svg_contracts() -> None:
    # Desktop controls remain comfortably sized, while mobile raises the
    # common token to the 44px touch-target floor.
    assert "--portal-control-height: 42px;" in CSS
    assert "@media (max-width: 700px) {\n  :root { --portal-control-height: 44px; }" in CSS
    assert ":focus-visible {" in CSS
    assert "outline: 3px solid rgba(99, 225, 208, .65);" in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert "transition: none !important;" in CSS

    # The mobile dock is an app navigation surface, not a generic marketing
    # homepage, and its decorative glyphs are rendered from a closed SVG map.
    assert '["dashboard", "/dashboard", "Workspace", ICONS.dashboard]' in PORTAL
    assert "const PORTAL_ICON_PATHS = Object.freeze({" in PORTAL
    icon_helper = _section(PORTAL, "function portalIcon(icon)", "const WEB_LOCAL_ACTIONS")
    assert "PORTAL_ICON_PATHS[key] || PORTAL_ICON_PATHS[ICONS.default]" in icon_helper
    assert '<svg class="portal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' in icon_helper


def test_app_shell_isolates_all_non_dialog_landmarks_and_keeps_mobile_auth_controls_touch_safe() -> None:
    modal = _section(PORTAL, "function setPortalTargetInert(target, opened)", "function setSidebarMenuState(button, opened)")

    assert 'document.querySelector(".skip-link")' in modal
    assert 'document.querySelector(".portal-workspace")' in modal
    assert 'document.querySelector("[data-portal-mobile-nav]")' in modal
    assert 'document.querySelector("[data-portal-sidebar]")' in modal
    assert "PORTAL_MODAL_ARIA_HIDDEN" in modal
    assert "PORTAL_MODAL_INERT" in modal
    assert "setPortalBackgroundInert(opened, true);" in PORTAL
    assert "@media (max-width: 980px)" in CSS
    assert ".portal-sidebar-close, .portal-command-close { width: 44px; height: 44px; }" in CSS
    assert ".portal-password-toggle { right: 4px; min-width: 52px; min-height: 44px; }" in CSS
    assert ".portal-auth-provider-option .portal-button { min-height: 44px; }" in CSS


def test_customer_surfaces_use_progressive_disclosure_and_ephemeral_password_reveal() -> None:
    # Secondary assurance, payment lookup, and implementation notes stay
    # discoverable without taking attention away from the first useful action.
    disclosures = {
        "portal-auth-assurance": '<details class="portal-auth-assurance">',
        "portal-dashboard-assurance": '<details class="portal-dashboard-assurance">',
        "portal-onboarding-assurance": '<details class="portal-onboarding-assurance">',
        "portal-account-assurance": '<details class="portal-account-assurance">',
        "portal-wallet-assurance": '<details class="portal-wallet-assurance">',
        "portal-wallet-secondary": '<details class="portal-wallet-secondary">',
    }
    for css_class, markup in disclosures.items():
        assert markup in PORTAL
        assert f".{css_class}" in CSS

    assert 'class="portal-settings-nav" aria-label="Thiết lập tài khoản"' in PORTAL
    assert 'class="portal-onboarding-steps" aria-label="Tiến trình liên kết Telegram"' in PORTAL

    # Password visibility is an in-page accessibility affordance only.  The
    # event handler changes the active input and does not create persistence
    # or an authentication action.
    assert "data-portal-toggle-password" in PORTAL
    password_toggle = _section(
        PORTAL,
        'const passwordToggle = event.target.closest("[data-portal-toggle-password]")',
        'if (event.target.closest("[data-portal-catalog-clear]"))',
    )
    assert 'input.type = reveal ? "text" : "password";' in password_toggle
    assert 'passwordToggle.setAttribute("aria-pressed", reveal ? "true" : "false");' in password_toggle
    assert "localStorage" not in password_toggle
    assert "sessionStorage" not in password_toggle


def test_admin_work_queue_is_only_a_server_grant_filtered_projection_when_present() -> None:
    """Keep optional Admin home shortcuts from inferring a browser role.

    The Admin home can be iterated independently of the customer shell.  If
    the optional queue component is present, it must intersect its shortlist
    with the normalized, server-issued route set and expose no cards without a
    grant.
    """

    marker = "function renderAdminWorkQueues(context)"
    if marker not in PORTAL:
        return

    queues = _section(PORTAL, marker, "function renderAdminOverview(page, context)")
    assert "const authorized = adminErpNavigation(context);" in queues
    assert "authorized.routes.has(route)" in queues
    assert "const cards = candidates.filter(([route]) => authorized.routes.has(route)).slice(0, 4);" in queues
    assert 'if (!cards.length) return "";' in queues
    assert 'class="portal-admin-work-queues"' in queues
    assert "browser role or guessed URL never adds" in queues
