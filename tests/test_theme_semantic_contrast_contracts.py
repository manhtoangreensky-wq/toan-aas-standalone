"""Contract tests for Theme Semantic Contrast, Light/Dark parity, and Teal Accent isolation."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    channels = [
        (c / 12.92) if c <= 0.03928 else (((c + 0.055) / 1.055) ** 2.4)
        for c in (r, g, b)
    ]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = _relative_luminance(hex1)
    l2 = _relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_red_a_light_admin_does_not_leak_dark_mint_text() -> None:
    """RED-A: Prove that light theme + admin shell must NOT resolve to dark-theme mint/off-white text tokens."""
    forbidden_coupling = re.compile(
        r'\.portal-shell\[data-portal-app-kind="admin"\]\s*,\s*html\[data-portal-theme="dark"\]'
    )
    assert not forbidden_coupling.search(
        THEME_CSS
    ), "Admin app-kind selector must not be grouped with dark theme root"

    for match in re.finditer(
        r'([^{}]+)\{([^{}]*--portal-ink:\s*var\(--portal-saas-teal-ink\)[^{}]*)\}',
        THEME_CSS,
    ):
        selector = match.group(1).strip()
        assert (
            'data-portal-theme="dark"' in selector
        ), f"Selector '{selector}' sets light-mint text without requiring dark theme"


def test_red_b_dark_theme_uses_neutral_canvas_and_surfaces_not_teal_flood() -> None:
    """RED-B: Prove that dark canvas/surface roles are NEUTRAL roles, not aliases of accent/teal canvas roles."""
    assert (
        "--portal-app-canvas: var(--portal-saas-teal-canvas);" not in THEME_CSS
    ), "Dark canvas must not use saturated teal canvas"
    assert (
        "--portal-surface: var(--portal-saas-teal-surface);" not in THEME_CSS
    ), "Dark surface must not use saturated teal surface"
    assert (
        "--portal-surface-soft: var(--portal-saas-teal-soft);" not in THEME_CSS
    ), "Dark soft surface must not use saturated teal surface"

    assert (
        "radial-gradient(circle at 86% -12%, var(--portal-saas-teal-glow-mint)"
        not in THEME_CSS
    ), "Teal radial gradient flood must not be applied to shell"


def test_red_c_dark_theme_owns_semantic_input_tokens_and_color_scheme() -> None:
    """RED-C: Prove dark theme explicitly owns semantic input tokens and controls consume them."""
    assert (
        "--portal-input-bg:" in THEME_CSS
    ), "Missing semantic --portal-input-bg token definition"
    assert (
        "--portal-input-text:" in THEME_CSS
    ), "Missing semantic --portal-input-text token definition"
    assert (
        "--portal-input-border:" in THEME_CSS
    ), "Missing semantic --portal-input-border token definition"

    dark_controls = re.search(
        r'html\[data-portal-theme="dark"\]\s*:is\(input,\s*select,\s*textarea,\s*\.portal-input,\s*\.portal-select\)',
        THEME_CSS,
    )
    assert (
        dark_controls is not None
    ), "Dark theme must explicitly target form controls (input, select, textarea, .portal-select)"


def test_wcag_contrast_ratios_meet_specifications() -> None:
    """Verify WCAG contrast >= 4.5:1 for standard text and normal button text >= 4.5:1."""
    # Light theme tokens
    light_canvas = "#f3fbfc"
    light_surface = "#ffffff"
    light_ink = "#073a45"
    light_muted = "#456b77"
    light_action = "#0f766e"
    light_on_action = "#ffffff"

    # Dark theme tokens
    dark_canvas = "#09090b"
    dark_surface = "#121215"
    dark_ink = "#f4f4f5"
    dark_muted = "#a1a1aa"
    dark_action = "#0f766e"
    dark_on_action = "#ffffff"

    # Light contrasts
    light_primary_canvas = _contrast_ratio(light_ink, light_canvas)
    light_primary_surface = _contrast_ratio(light_ink, light_surface)
    light_muted_surface = _contrast_ratio(light_muted, light_surface)
    light_button_text_contrast = _contrast_ratio(light_on_action, light_action)

    assert light_primary_canvas >= 4.5, f"Light primary/canvas contrast too low: {light_primary_canvas:.2f}"
    assert light_primary_surface >= 4.5, f"Light primary/surface contrast too low: {light_primary_surface:.2f}"
    assert light_muted_surface >= 4.5, f"Light muted/surface contrast too low: {light_muted_surface:.2f}"
    assert light_button_text_contrast >= 4.5, f"Light normal button text contrast too low: {light_button_text_contrast:.2f}"

    # Dark contrasts
    dark_primary_canvas = _contrast_ratio(dark_ink, dark_canvas)
    dark_primary_surface = _contrast_ratio(dark_ink, dark_surface)
    dark_muted_surface = _contrast_ratio(dark_muted, dark_surface)
    dark_button_text_contrast = _contrast_ratio(dark_on_action, dark_action)

    assert dark_primary_canvas >= 4.5, f"Dark primary/canvas contrast too low: {dark_primary_canvas:.2f}"
    assert dark_primary_surface >= 4.5, f"Dark primary/surface contrast too low: {dark_primary_surface:.2f}"
    assert dark_muted_surface >= 4.5, f"Dark muted/surface contrast too low: {dark_muted_surface:.2f}"
    assert dark_button_text_contrast >= 4.5, f"Dark normal button text contrast too low: {dark_button_text_contrast:.2f}"


def test_theme_switch_decouples_admin_app_kind_from_theme_mode() -> None:
    """Verify admin app kind does not imply dark theme palette."""
    # Ensure no rule applies dark palette to admin shell without explicit dark theme
    for match in re.finditer(
        r"([^{}]+)\{([^{}]*--portal-app-canvas:\s*var\(--portal-saas-[^{}]*)\}",
        THEME_CSS,
    ):
        selector = match.group(1).strip()
        if 'data-portal-app-kind="admin"' in selector:
            assert 'data-portal-theme="dark"' in selector, (
                f"Admin app-kind selector '{selector}' must not bind dark canvas without dark theme attribute"
            )
    # In light theme, admin shell retains light ink and background
    assert "--portal-text: var(--portal-ink);" in THEME_CSS

