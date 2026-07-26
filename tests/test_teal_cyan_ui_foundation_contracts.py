"""Presentation contracts for the teal/cyan portal theme foundation."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SHELL_TEMPLATE = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
PORTAL_THEME = ROOT / "static" / "portal" / "portal-theme.css"
PORTAL_CATALOGUE = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
MANIFEST = ROOT / "static" / "portal" / "manifest.webmanifest"
OFFLINE_SHELL = ROOT / "static" / "portal" / "offline.html"

BASE_STYLESHEET = '<link rel="stylesheet" href="/static/portal/portal.css?v=__PORTAL_ASSET_VERSION__">'
THEME_STYLESHEET = '<link rel="stylesheet" href="/static/portal/portal-theme.css?v=__PORTAL_ASSET_VERSION__">'
I18N_SCRIPT = '<script src="/static/portal/portal-i18n.js?v=__PORTAL_ASSET_VERSION__" defer></script>'
PORTAL_SCRIPT = '<script src="/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__" defer></script>'
INTEGRATION_SCRIPT = '<script src="/static/portal/integration.js?v=__PORTAL_ASSET_VERSION__" defer></script>'


def _relative_luminance(hex_colour: str) -> float:
    channels = tuple(int(hex_colour[index : index + 2], 16) / 255 for index in (1, 3, 5))

    def linearise(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearise(channel) for channel in channels)
    return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((_relative_luminance(foreground), _relative_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_portal_shell_loads_the_teal_cyan_theme_between_base_css_and_javascript() -> None:
    portal_css = SHELL_TEMPLATE.index(BASE_STYLESHEET)
    portal_theme = SHELL_TEMPLATE.index(THEME_STYLESHEET)
    i18n = SHELL_TEMPLATE.index(I18N_SCRIPT)
    portal = SHELL_TEMPLATE.index(PORTAL_SCRIPT)
    integration = SHELL_TEMPLATE.index(INTEGRATION_SCRIPT)

    assert portal_css < portal_theme < i18n < portal < integration


def test_unified_teal_sky_tokens_drive_light_and_dark_surfaces() -> None:
    assert PORTAL_THEME.is_file()
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)
    assert root is not None
    root_declarations = root.group("declarations")

    expected_tokens = (
        "--portal-bg: #062a36;",
        "--portal-surface: #0b3440;",
        "--portal-surface-strong: #104352;",
        "--portal-border: #246070;",
        "--portal-accent: #14b8a6;",
        "--portal-accent-hover: #2dd4bf;",
        "--portal-info: #38bdf8;",
        "--portal-light-canvas: #f4fbfc;",
        "--portal-light-border: #d7ecef;",
        "--portal-ink: #092b36;",
    )

    for token in expected_tokens:
        assert token in root_declarations

    assert re.search(r"\.portal-button:focus-visible\s*\{[^}]*outline:", theme_source, flags=re.DOTALL)
    assert "@media (prefers-reduced-motion: reduce)" in theme_source
    assert "@media (max-width: 920px)" in theme_source
    assert "min-height: 44px;" in theme_source


def test_theme_tokenizes_shared_chrome_and_repeated_light_landing_colours() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)

    assert root is not None
    root_declarations = root.group("declarations")
    expected_tokens = (
        "--portal-chrome: #062a36;",
        "--portal-light-surface: #ffffff;",
        "--portal-light-soft: #e8f5f6;",
        "--portal-light-accent-border: #8bded7;",
        "--portal-light-accent-soft: #e0f7f5;",
        "--portal-light-hover-surface: #f8fdfd;",
        "--portal-landing-divider: #d7ecef;",
    )

    for token in expected_tokens:
        assert token in root_declarations

    rendered_rules = theme_source[root.end() :]
    for literal in (
        "#062a36",
        "#0b3440",
        "#104352",
        "#246070",
        "#14b8a6",
        "#2dd4bf",
        "#38bdf8",
        "#092b36",
        "#335969",
        "#0d2330",
        "#ffffff",
        "#f4fbfc",
        "#d7ecef",
        "#e8f5f6",
        "#e0f7f5",
    ):
        assert literal not in rendered_rules


def test_root_is_the_only_owner_of_hex_colour_literals() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)

    assert root is not None
    rendered_rules = theme_source[root.end() :]
    literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", rendered_rules)
    assert not literals, f"move semantic colour literals into :root: {', '.join(sorted(set(literals)))}"


def test_final_theme_preserves_44px_mobile_controls_after_the_legacy_catalogue() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    theme_root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)
    legacy_mobile_height = re.search(
        r"@media \(max-width: 700px\)\s*\{\s*:root\s*\{\s*--portal-control-height: 44px;\s*\}",
        PORTAL_CATALOGUE,
        flags=re.DOTALL,
    )
    final_mobile_height = re.search(
        r"@media \(max-width: 700px\)\s*\{\s*:root\s*\{\s*--portal-control-height: 44px;\s*\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert theme_root is not None
    assert legacy_mobile_height is not None
    assert final_mobile_height is not None
    assert theme_root.end() < final_mobile_height.start()
    assert SHELL_TEMPLATE.index(BASE_STYLESHEET) < SHELL_TEMPLATE.index(THEME_STYLESHEET)


def test_light_surface_focus_ring_overrides_the_catalogue_important_outline_with_3_to_1_contrast() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    legacy_focus = re.search(
        r"^:focus-visible\s*\{(?P<declarations>[^}]*outline: 2px solid #5eead4 !important;[^}]*)\}",
        PORTAL_CATALOGUE,
        flags=re.MULTILINE,
    )
    final_focus = re.search(
        r"\.portal-shell--auth :focus-visible,\s*"
        r"\.portal-shell--landing :focus-visible,\s*"
        r"\.portal-landing :focus-visible\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert legacy_focus is not None
    assert "outline: 2px solid #5eead4 !important;" in legacy_focus.group("declarations")
    assert final_focus is not None
    assert "outline: 3px solid var(--portal-focus) !important;" in final_focus.group("declarations")
    assert "--portal-focus: #0b6d8c;" in theme_source
    assert "--portal-light-canvas: #f4fbfc;" in theme_source
    assert "--portal-light-surface: #ffffff;" in theme_source
    assert _contrast_ratio("#0b6d8c", "#ffffff") >= 3
    assert _contrast_ratio("#0b6d8c", "#f4fbfc") >= 3
    assert SHELL_TEMPLATE.index(BASE_STYLESHEET) < SHELL_TEMPLATE.index(THEME_STYLESHEET)


def test_pwa_metadata_and_offline_shell_share_the_canonical_portal_background() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    offline_shell = OFFLINE_SHELL.read_text(encoding="utf-8")

    assert manifest["background_color"] == "#07141d"
    assert manifest["theme_color"] == "#07141d"
    assert '<meta name="theme-color" content="#07141d">' in offline_shell
    assert "background: #07141d;" in offline_shell
    assert "#07131f" not in offline_shell


def test_access_copy_stays_top_aligned_with_the_email_form() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    intro = re.search(
        r"\.portal-auth-page--access \.portal-auth-intro\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert intro is not None
    assert "align-content: start;" in intro.group("declarations")


def test_access_secondary_actions_keep_readable_ink_on_the_light_form() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    secondary_actions = re.search(
        r"\.portal-auth-page--access \.portal-auth-primary \.portal-form-footer > a\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert secondary_actions is not None
    assert "color: var(--portal-light-action);" in secondary_actions.group("declarations")


def test_access_disclosure_summaries_keep_readable_text_on_light_surfaces() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    summaries = re.search(
        r"\.portal-auth-page--access :is\(\.portal-auth-assurance, \.portal-auth-help, "
        r"\.portal-auth-alternatives\) > summary\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert summaries is not None
    assert "color: var(--portal-light-action);" in summaries.group("declarations")


def test_public_landing_uses_a_bounded_editorial_hero_scale() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    headings = re.findall(
        r"\.portal-landing-hero h1\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert headings
    assert any("font-size: clamp(40px, 4.5vw, 64px);" in declaration for declaration in headings)


def test_primary_teal_actions_use_dark_ink_for_readable_contrast() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)
    primary = re.search(r"\.portal-button--primary\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)

    assert root is not None
    assert primary is not None
    assert "--portal-accent-ink: #092b36;" in root.group("declarations")
    assert "color: var(--portal-accent-ink);" in primary.group("declarations")


def test_light_auth_provider_options_override_dark_catalogue_text() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    enabled = re.search(
        r"\.portal-auth-page--access \.portal-auth-provider-option\.is-enabled\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    strong = re.search(
        r"\.portal-auth-page--access \.portal-auth-provider-option strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert enabled is not None
    assert strong is not None
    assert "background: var(--portal-light-soft);" in enabled.group("declarations")
    assert "color: var(--portal-ink);" in strong.group("declarations")


def test_light_auth_primary_submit_uses_the_shared_teal_action() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    primary_submit = re.search(
        r"\.portal-auth-page--access \.portal-auth-primary \.portal-button--primary\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert primary_submit is not None
    assert "background: var(--portal-accent);" in primary_submit.group("declarations")
    assert "color: var(--portal-accent-ink);" in primary_submit.group("declarations")


def test_theme_is_in_build_hash_fallback_shell_and_public_pwa_shell() -> None:
    build_sources = PAGES[
        PAGES.index("_PORTAL_BUILD_SOURCE_FILES = ("):
        PAGES.index(")\n\n# The portal shell")
    ]
    fallback = PAGES[PAGES.index("def _fallback_template()"):PAGES.index("\n\ndef render_portal")]
    worker_shell = WORKER[
        WORKER.index("const SHELL = Object.freeze(["):
        WORKER.index("]);\nconst SHELL_PATHS")
    ]

    assert '"portal-theme.css",' in build_sources
    assert THEME_STYLESHEET in fallback.replace('\\\"', '"')
    assert '"/static/portal/portal-theme.css",' in worker_shell


def test_mobile_portal_main_keeps_both_safe_area_insets() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    mobile = re.search(
        r"@media \(max-width: 920px\)\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert mobile is not None
    main = re.search(
        r"\.portal-main\s*\{(?P<declarations>.*?)\n  \}",
        mobile.group("declarations"),
        flags=re.DOTALL,
    )
    assert main is not None
    assert "var(--portal-safe-left)" in main.group("declarations")
    assert "var(--portal-safe-right)" in main.group("declarations")
