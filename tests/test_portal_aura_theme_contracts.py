"""Presentation-only contracts for the Aura light/dark theme layer."""

from pathlib import Path

import copyfast_pages


ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
THEME_JS = (ROOT / "static" / "portal" / "portal-theme.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")


def test_theme_asset_is_versioned_in_the_server_shell_and_pwa_allowlist() -> None:
    page = copyfast_pages.render_portal("/welcome", interface_locale="en")
    html = page.body.decode("utf-8")

    assert 'src="/static/portal/portal-theme.js?v=' in html
    assert "portal-theme.js" in copyfast_pages._PORTAL_BUILD_SOURCE_FILES
    assert '"/static/portal/portal-theme.js",' in WORKER
    assert 'src="/static/portal/portal-theme.js?v=__PORTAL_ASSET_VERSION__"' in SHELL
    assert "portal-theme.js" in PAGES


def test_theme_controller_is_local_presentation_state_only() -> None:
    assert 'const STORAGE_KEY = "toan-aas-portal-theme";' in THEME_JS
    assert 'const THEMES = Object.freeze(["system", "light", "dark"]);' in THEME_JS
    assert 'documentElement.setAttribute("data-portal-theme", resolved);' in THEME_JS
    assert 'global.document.body.setAttribute("data-portal-theme", resolved);' in THEME_JS
    assert 'new global.CustomEvent("toanaas:theme-change"' in THEME_JS
    assert "fetch(" not in THEME_JS
    assert "XMLHttpRequest" not in THEME_JS
    assert "/api/" not in THEME_JS
    assert "telegram" not in THEME_JS.lower()
    assert "payos" not in THEME_JS.lower()
    assert "provider" not in THEME_JS.lower()


def test_theme_controller_does_not_observe_its_own_icon_rendering() -> None:
    """Portal mount explicitly syncs controls, avoiding a mutation feedback loop."""
    assert "new global.MutationObserver" not in THEME_JS
    assert "observer.observe(" not in THEME_JS


def test_theme_toggle_is_shared_by_workspace_access_and_public_companion() -> None:
    assert "function renderThemeToggle()" in PORTAL
    assert PORTAL.count("${renderThemeToggle()}") == 3
    assert "data-portal-theme-toggle" in PORTAL
    assert "theme.syncControls()" in PORTAL
    assert 'class="portal-auth-header-actions"' in PORTAL
    assert 'class="portal-landing-nav-actions"' in PORTAL


def test_all_reviewed_interface_locales_have_theme_copy() -> None:
    for key in (
        "chrome.theme_switch",
        "chrome.theme_label",
        "chrome.theme_light",
        "chrome.theme_dark",
        "chrome.theme_system",
        "chrome.theme_switch_to_light",
        "chrome.theme_switch_to_dark",
        "chrome.theme_switch_to_system",
    ):
        assert I18N.count(f'"{key}"') == 3


def test_aura_tokens_use_requested_slate_dark_pair_and_accessible_controls() -> None:
    assert ':root[data-portal-theme="dark"]' in THEME
    assert "--portal-app-canvas: #0b132b;" in THEME
    assert "--portal-surface-light: #1c2541;" in THEME
    assert "--portal-action: #14b8a6;" in THEME
    assert "--portal-context: #38bdf8;" in THEME
    assert ".portal-theme-toggle" in THEME
    assert "min-width: 44px;" in THEME
    assert "min-height: var(--portal-control-height);" in THEME
    assert ".portal-theme-toggle:focus-visible" in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME
    assert "transition-duration: 0ms !important;" in THEME


def test_compact_landing_header_preserves_locale_and_theme_without_clipping_cta() -> None:
    assert "@media (max-width: 420px)" in THEME
    assert ".portal-landing-nav-primary { display: none; }" in THEME
