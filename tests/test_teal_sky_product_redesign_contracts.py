"""Contracts for the approved teal–sky product redesign."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "static" / "portal" / "manifest.webmanifest").read_text(encoding="utf-8"))
OFFLINE = (ROOT / "static" / "portal" / "offline.html").read_text(encoding="utf-8")


MARKER = "/* Teal–Sky Product Redesign -- final semantic layer. */"


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _redesign_layer() -> str:
    marker = THEME.index(MARKER)
    return THEME[marker:]


def test_redesign_layer_owns_light_surface_typography_and_header_alignment() -> None:
    layer = _redesign_layer()

    assert ".portal-shell:not(.portal-shell--auth):not(.portal-shell--landing)" in layer
    assert ".portal-card-title" in layer
    assert ".portal-card-subtitle" in layer
    assert "color: var(--portal-ink);" in layer
    assert "color: var(--portal-muted);" in layer
    assert ".portal-header" in layer
    assert "var(--portal-content-max-width)" in layer
    assert "var(--portal-desktop-page-padding)));" in layer
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\\b", layer)


def test_access_renderer_adds_only_localized_context_without_changing_real_auth_actions() -> None:
    auth = _section(PORTAL, "function renderAuth(page, context)", "const RESULT_LABELS")

    assert 'class="portal-auth-context"' in auth
    assert 'class="portal-auth-primary"' in auth
    assert "data-portal-action=" in auth
    assert "data-portal-route=" in auth
    assert 'class="portal-auth-alternatives"' in auth
    assert 'class="portal-auth-assurance"' in auth


def test_access_context_has_complete_vietnamese_english_and_chinese_copy() -> None:
    for key in (
        "access.context.label",
        "access.context.kicker",
        "access.context.loginTitle",
        "access.context.registerTitle",
        "access.context.pointOne",
        "access.context.pointTwo",
        "access.context.pointThree",
    ):
        assert I18N.count(f'"{key}"') == 3


def test_access_desktop_uses_a_balanced_two_column_rail_and_mobile_hides_context() -> None:
    layer = _redesign_layer()

    assert "@media (min-width: 1081px)" in layer
    assert "@media (min-width: 981px)" not in layer
    assert 'grid-template-areas: "intro card";' in layer
    assert "minmax(420px, 480px)" in layer
    assert "width: min(100%, 1180px);" in layer
    assert "@media (max-width: 1080px)" in layer
    assert 'grid-template-areas: "card" "intro";' in layer
    assert ".portal-auth-context { display: none; }" in layer


def test_access_header_preserves_locale_targets_at_320px() -> None:
    """The compact header visually hides redundant brand copy without losing its name."""

    layer = _redesign_layer()

    assert "@media (max-width: 380px)" in layer
    assert ".portal-auth-page--access .portal-auth-header { gap: 6px; }" in layer
    assert ".portal-auth-page--access .portal-auth-brand > span:last-child {\n    position: absolute;" in layer
    assert "clip: rect(0, 0, 0, 0);" in layer
    assert "white-space: nowrap;" in layer
    assert ".portal-auth-page--access .portal-auth-locale-link {\n  display: inline-grid;\n  min-width: 44px;\n  min-height: 44px;" in THEME
    assert ".portal-auth-back {\n  display: inline-flex;\n  min-height: 44px;\n  min-width: 44px;" in THEME


def test_register_mobile_hides_only_field_help_to_keep_primary_action_visible() -> None:
    layer = _redesign_layer()

    assert "@media (max-width: 600px)" in layer
    assert (
        '.portal-auth-page--access form[data-portal-action="auth-register"] .portal-field-help {\n'
        "    display: none;\n"
        "  }"
    ) in layer
    assert ".portal-auth-page--access .portal-auth-submit-btn {\n  font-weight: 750;\n  border: none;\n  border-radius: 12px;\n  height: 44px;" in layer


def test_pwa_and_first_paint_chrome_use_the_same_deep_teal_as_the_signed_rail() -> None:
    assert MANIFEST["background_color"] == "#063b47"
    assert MANIFEST["theme_color"] == "#063b47"
    assert '<meta name="theme-color" content="#063b47">' in OFFLINE
    assert "background: #063b47;" in OFFLINE
    assert '<meta name="theme-color" content="#063b47">' in SHELL
