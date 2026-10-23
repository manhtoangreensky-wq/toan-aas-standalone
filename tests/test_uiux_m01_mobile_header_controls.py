"""Regression contract for the 390px public landing header controls."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")


def test_mobile_locale_controls_keep_full_accessible_name_and_compact_visual_label() -> None:
    assert 'aria-label="${safeText(item.label)}"' in PORTAL
    assert '<span class="portal-landing-locale-full">${safeText(item.label)}</span>' in PORTAL
    assert '<span class="portal-landing-locale-short" aria-hidden="true">${safeText(shortLabel)}</span>' in PORTAL


def test_narrow_landing_header_has_non_wrapping_44px_locale_targets() -> None:
    assert ".portal-landing-locale-short { display: none; }" in THEME
    assert "@media (max-width: 420px)" in THEME
    assert ".portal-landing-locale-full { display: none; }" in THEME
    assert ".portal-landing-locale-short { display: inline; }" in THEME
    assert ".portal-landing-locale-link { min-width: 44px; padding-inline: 2px; white-space: nowrap; }" in THEME
    assert "@media (max-width: 380px)" in THEME
    assert ".portal-landing-nav-actions { display: contents; }" in THEME
    assert ".portal-landing-locale-nav { grid-column: 1 / -1; grid-row: 2; justify-self: start; }" in THEME
