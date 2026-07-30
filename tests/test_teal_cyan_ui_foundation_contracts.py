"""Presentation contracts for the teal/cyan portal theme foundation."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SHELL_TEMPLATE = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
PORTAL_THEME = ROOT / "static" / "portal" / "portal-theme.css"
PORTAL_CATALOGUE = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
PORTAL_CLIENT = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
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


def test_rebalanced_teal_sky_tokens_keep_the_signed_canvas_light_and_rail_deep() -> None:
    assert PORTAL_THEME.is_file()
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)
    assert root is not None
    root_declarations = root.group("declarations")

    expected_tokens = (
        "--portal-app-canvas: #f3fbfc;",
        "--portal-surface-light: #ffffff;",
        "--portal-action: #0f766e;",
        "--portal-on-action: #ffffff;",
        "--portal-brand: #0d9488;",
        "--portal-context: #0369a1;",
        "--portal-rail: #063b47;",
        "--portal-border: #d5e9ed;",
        "--portal-muted: #456b77;",
        "--portal-ink: #073a45;",
    )

    for token in expected_tokens:
        assert token in root_declarations

    assert re.search(r"\.portal-button:focus-visible\s*\{[^}]*outline:", theme_source, flags=re.DOTALL)
    assert "@media (prefers-reduced-motion: reduce)" in theme_source
    assert "@media (max-width: 920px)" in theme_source
    assert "min-height: 44px;" in theme_source


def test_theme_maps_legacy_component_names_to_the_semantic_teal_sky_tokens() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)

    assert root is not None
    root_declarations = root.group("declarations")
    expected_tokens = (
        "--portal-bg: var(--portal-app-canvas);",
        "--portal-surface: var(--portal-surface-light);",
        "--portal-accent: var(--portal-brand);",
        "--portal-info: var(--portal-context);",
        "--portal-light-canvas: var(--portal-app-canvas);",
        "--portal-light-surface: var(--portal-surface-light);",
        "--portal-light-soft: #e8f6f7;",
        "--portal-light-accent-border: #8ccfcf;",
        "--portal-light-accent-soft: #e6f8f7;",
        "--portal-light-hover-surface: #f8fdfd;",
        "--portal-landing-divider: var(--portal-border);",
    )

    for token in expected_tokens:
        assert token in root_declarations

    rendered_rules = theme_source[root.end() :]
    for literal in (
        "#073a45",
        "#0f766e",
        "#0d9488",
        "#0369a1",
        "#ffffff",
        "#f3fbfc",
        "#d5e9ed",
        "#456b77",
        "#e8f6f7",
        "#e6f8f7",
    ):
        assert literal not in rendered_rules


def test_root_is_the_only_owner_of_hex_colour_literals() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)

    assert root is not None
    rendered_rules = theme_source[root.end() :]
    literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", rendered_rules)
    assert not literals, f"move semantic colour literals into :root: {', '.join(sorted(set(literals)))}"


def test_shared_chrome_does_not_keep_legacy_blue_or_teal_rgba_values() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)

    assert root is not None
    rendered_rules = theme_source[root.end() :]
    for legacy_colour in ("rgba(2, 132, 199", "rgba(14, 159, 154"):
        assert legacy_colour not in rendered_rules

    active_navigation = re.search(
        r"\.portal-nav-link\[aria-current=\"page\"\]\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    dark_focus = re.search(
        r"\.portal-input:focus,\s*\.portal-select:focus,\s*\.portal-textarea:focus\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    light_focus = re.search(
        r"\.portal-auth-page--access \.portal-input:focus,\s*"
        r"\.portal-auth-page--access \.portal-select:focus,\s*"
        r"\.portal-auth-page--access \.portal-textarea:focus\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    table_hover = re.search(
        r"\.portal-data-table tbody tr:hover\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert active_navigation is not None
    assert dark_focus is not None
    assert light_focus is not None
    assert table_hover is not None
    assert "var(--portal-context)" in active_navigation.group("declarations")
    assert "var(--portal-context)" in dark_focus.group("declarations")
    assert "var(--portal-context)" in light_focus.group("declarations")
    assert "var(--portal-brand)" in table_hover.group("declarations")


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
    assert "--portal-focus: var(--portal-context);" in theme_source
    assert "--portal-app-canvas: #f3fbfc;" in theme_source
    assert "--portal-surface-light: #ffffff;" in theme_source
    assert _contrast_ratio("#0369a1", "#ffffff") >= 3
    assert _contrast_ratio("#0369a1", "#f3fbfc") >= 3
    assert SHELL_TEMPLATE.index(BASE_STYLESHEET) < SHELL_TEMPLATE.index(THEME_STYLESHEET)


def test_light_workspace_intros_replace_dark_catalogue_text_and_metric_cards_with_semantic_tokens() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    light_intro_selectors = (
        ".portal-image-prompt-composer-intro",
        ".portal-video-prompt-planner-intro",
        ".portal-workboard-intro",
        ".portal-workboard-detail-summary",
    )
    metric_cards = re.search(
        r"\.portal-page :is\((?P<selectors>.*?)\) dl > div\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    shared_light_surfaces = re.search(
        r'\.portal-page :is\(\[class\$="-intro"\], \[class\$="-summary"\], '
        r'\.portal-action-center, \.portal-start-guide, \.portal-capability-hub, \.portal-state\) '
        r'\{(?P<declarations>.*?)\n\}',
        theme_source,
        flags=re.DOTALL,
    )
    primary_text = re.search(
        r"\.portal-page :is\((?P<selectors>.*?)\) :is\(h2, dt\),\s*"
        r"\.portal-page \.portal-workboard-detail-summary :is\(h2, dd\)\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    secondary_text = re.search(
        r"\.portal-page :is\((?P<selectors>.*?)\) :is\(p, dd\),\s*"
        r"\.portal-page \.portal-workboard-detail-summary :is\(p, dt\)\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert all(selector in PORTAL_CATALOGUE for selector in light_intro_selectors)
    assert metric_cards is not None
    assert shared_light_surfaces is not None
    assert primary_text is not None
    assert secondary_text is not None
    assert all(selector.endswith(("-intro", "-summary")) for selector in light_intro_selectors)
    assert "background: var(--portal-surface-strong) !important;" in shared_light_surfaces.group("declarations")
    for selector in light_intro_selectors:
        assert selector in metric_cards.group("selectors")
    for selector in light_intro_selectors[:3]:
        assert selector in primary_text.group("selectors")
        assert selector in secondary_text.group("selectors")
    assert "border-color: var(--portal-border);" in metric_cards.group("declarations")
    assert "background: var(--portal-surface-light);" in metric_cards.group("declarations")
    assert "color: var(--portal-ink);" in primary_text.group("declarations")
    assert "color: var(--portal-muted);" in secondary_text.group("declarations")


def test_light_support_and_operations_intros_replace_legacy_dark_panel_ink() -> None:
    """Shared Support/Operations intros inherit the light surface and matching ink."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    affected_intros = (
        ".portal-support-intro",
        ".portal-support-admin-intro",
        ".portal-operations-intro",
        ".portal-operations-admin-intro",
    )
    metric_cards = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-support-admin-intro[^)]*)\) dl > div\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    primary_text = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-support-admin-intro[^)]*)\) :is\(h2, dt\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    secondary_text = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-support-admin-intro[^)]*)\) :is\(p, dd\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    domain_meta = re.search(
        r"\.portal-page \.portal-admin-domain-intro \.portal-state-meta span\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert all(selector in PORTAL_CATALOGUE for selector in affected_intros)
    assert metric_cards is not None
    assert primary_text is not None
    assert secondary_text is not None
    assert domain_meta is not None
    for selector in affected_intros:
        assert selector in metric_cards.group("selectors")
        assert selector in primary_text.group("selectors")
        assert selector in secondary_text.group("selectors")
    assert "border-color: var(--portal-border);" in metric_cards.group("declarations")
    assert "background: var(--portal-surface-light);" in metric_cards.group("declarations")
    assert "color: var(--portal-ink);" in primary_text.group("declarations")
    assert "color: var(--portal-muted);" in secondary_text.group("declarations")
    assert "border: 1px solid var(--portal-border);" in domain_meta.group("declarations")
    assert "background: var(--portal-surface-light);" in domain_meta.group("declarations")
    assert "color: var(--portal-muted);" in domain_meta.group("declarations")
    assert _contrast_ratio("#073a45", "#e8f6f7") >= 4.5
    assert _contrast_ratio("#456b77", "#e8f6f7") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5


def test_light_core_workspace_intros_keep_their_metric_hierarchy_readable() -> None:
    """Core authoring surfaces keep labels and values distinct on the light theme."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    standard_intros = (
        ".portal-project-intro",
        ".portal-project-package-intro",
        ".portal-document-operation-intro",
        ".portal-vault-intro",
        ".portal-memory-intro",
    )
    metric_intros = (*standard_intros, ".portal-project-summary")
    metric_cards = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-memory-intro[^)]*)\) dl > div\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    standard_primary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-memory-intro[^)]*)\) :is\(h2, dt\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    standard_secondary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-memory-intro[^)]*)\) :is\(p, dd\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    summary_primary = re.search(
        r"\.portal-page \.portal-project-summary :is\(h2, dd\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    summary_secondary = re.search(
        r"\.portal-page \.portal-project-summary :is\(p, dt\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert all(selector in PORTAL_CATALOGUE for selector in metric_intros)
    assert '<section class="portal-project-summary">' in PORTAL_CLIENT
    assert '<dt>Mục tiêu</dt><dd>${safeText(String(project.objective || "Chưa đặt"))}</dd>' in PORTAL_CLIENT
    assert '<dt>Trạng thái</dt><dd>${badge(projectState(project.state))}</dd>' in PORTAL_CLIENT
    assert metric_cards is not None
    assert standard_primary is not None
    assert standard_secondary is not None
    assert summary_primary is not None
    assert summary_secondary is not None
    for selector in metric_intros:
        assert selector in metric_cards.group("selectors")
    for selector in standard_intros:
        assert selector in standard_primary.group("selectors")
        assert selector in standard_secondary.group("selectors")
    assert "border-color: var(--portal-border);" in metric_cards.group("declarations")
    assert "background: var(--portal-surface-light);" in metric_cards.group("declarations")
    assert "color: var(--portal-ink);" in standard_primary.group("declarations")
    assert "color: var(--portal-muted);" in standard_secondary.group("declarations")
    assert "color: var(--portal-ink);" in summary_primary.group("declarations")
    assert "color: var(--portal-muted);" in summary_secondary.group("declarations")
    assert _contrast_ratio("#073a45", "#e8f6f7") >= 4.5
    assert _contrast_ratio("#456b77", "#e8f6f7") >= 4.5
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5


def test_light_studio_intros_and_detail_summaries_keep_their_distinct_metric_roles() -> None:
    """Studio indexes present values first, while detail summaries present labels first."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    studio_intros = (
        ".portal-prompt-library-intro",
        ".portal-content-studio-intro",
        ".portal-voice-studio-intro",
        ".portal-media-workspace-intro",
        ".portal-video-studio-intro",
        ".portal-image-studio-intro",
        ".portal-document-workspace-intro",
        ".portal-chat-workspace-intro",
    )
    detail_summaries = (
        ".portal-prompt-library-detail-summary",
        ".portal-content-studio-detail-summary",
        ".portal-voice-studio-detail-summary",
        ".portal-media-detail-summary",
        ".portal-video-studio-detail-summary",
        ".portal-image-studio-detail-summary",
        ".portal-document-workspace-detail-summary",
        ".portal-chat-thread-summary",
    )
    metric_cards = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-chat-thread-summary[^)]*)\) > dl > div\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    intro_primary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-chat-workspace-intro[^)]*)\) > div > h2,\s*"
        r"\.portal-page :is\([^)]*\) > dl > div > dt\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    intro_secondary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-chat-workspace-intro[^)]*)\) > div > p,\s*"
        r"\.portal-page :is\([^)]*\) > dl > div > dd\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    detail_primary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-chat-thread-summary[^)]*)\) > div > h2,\s*"
        r"\.portal-page :is\([^)]*\) > dl > div > dd\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    detail_secondary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-chat-thread-summary[^)]*)\) > div > p,\s*"
        r"\.portal-page :is\([^)]*\) > dl > div > dt\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    detail_tags = re.search(
        r"\.portal-page :is\((?P<summaries>[^)]*\.portal-chat-thread-summary[^)]*)\) > div > :is\("
        r"(?P<tags>[^)]*\.portal-chat-workspace-tags[^)]*)\) > span\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    detail_tag_lists = (
        ".portal-prompt-library-tags",
        ".portal-content-studio-tags",
        ".portal-voice-studio-tags",
        ".portal-voice-reference-list",
        ".portal-media-tags",
        ".portal-video-studio-tags",
        ".portal-image-studio-tags",
        ".portal-document-workspace-tags",
        ".portal-chat-workspace-tags",
    )

    assert all(selector in PORTAL_CATALOGUE for selector in (*studio_intros, *detail_summaries, *detail_tag_lists))
    assert metric_cards is not None
    assert intro_primary is not None
    assert intro_secondary is not None
    assert detail_primary is not None
    assert detail_secondary is not None
    assert detail_tags is not None
    for selector in (*studio_intros, *detail_summaries):
        assert selector in metric_cards.group("selectors")
    for selector in studio_intros:
        assert selector in intro_primary.group("selectors")
        assert selector in intro_secondary.group("selectors")
    for selector in detail_summaries:
        assert selector in detail_primary.group("selectors")
        assert selector in detail_secondary.group("selectors")
        assert selector in detail_tags.group("summaries")
    for selector in detail_tag_lists:
        assert selector in detail_tags.group("tags")
    assert "border-color: var(--portal-border);" in metric_cards.group("declarations")
    assert "background: var(--portal-surface-light);" in metric_cards.group("declarations")
    assert "color: var(--portal-ink);" in intro_primary.group("declarations")
    assert "color: var(--portal-muted);" in intro_secondary.group("declarations")
    assert "color: var(--portal-ink);" in detail_primary.group("declarations")
    assert "color: var(--portal-muted);" in detail_secondary.group("declarations")
    assert "border-color: var(--portal-border);" in detail_tags.group("declarations")
    assert "background: var(--portal-surface-light);" in detail_tags.group("declarations")
    assert "color: var(--portal-muted);" in detail_tags.group("declarations")
    assert _contrast_ratio("#073a45", "#e8f6f7") >= 4.5
    assert _contrast_ratio("#456b77", "#e8f6f7") >= 4.5
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5


def test_light_readiness_intros_keep_admin_status_context_legible() -> None:
    """Read-only readiness guidance keeps its status panel distinct and readable."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    readiness_intros = (
        ".portal-stewardship-intro",
        ".portal-tax-readiness-intro",
        ".portal-postback-readiness-intro",
        ".portal-job-recovery-intro",
    )
    status_panels = (
        ".portal-stewardship-intro-status",
        ".portal-tax-readiness-intro-status",
        ".portal-postback-readiness-intro-status",
        ".portal-job-recovery-intro-status",
    )
    headings = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-job-recovery-intro[^)]*)\) > div:first-child > h2\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    body_copy = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-job-recovery-intro[^)]*)\) > div:first-child > p\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    status_surface = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-job-recovery-intro-status[^)]*)\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    status_primary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-job-recovery-intro-status[^)]*)\) strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    status_secondary = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-job-recovery-intro-status[^)]*)\) small\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    status_icon = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-job-recovery-intro-status[^)]*)\) > span:first-child\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert all(selector in PORTAL_CATALOGUE for selector in (*readiness_intros, *status_panels))
    assert headings is not None
    assert body_copy is not None
    assert status_surface is not None
    assert status_primary is not None
    assert status_secondary is not None
    assert status_icon is not None
    for selector in readiness_intros:
        assert selector in headings.group("selectors")
        assert selector in body_copy.group("selectors")
    for selector in status_panels:
        assert selector in status_surface.group("selectors")
        assert selector in status_primary.group("selectors")
        assert selector in status_secondary.group("selectors")
        assert selector in status_icon.group("selectors")
    assert "color: var(--portal-ink);" in headings.group("declarations")
    assert "color: var(--portal-muted);" in body_copy.group("declarations")
    assert "border-color: var(--portal-border);" in status_surface.group("declarations")
    assert "background: var(--portal-surface-light);" in status_surface.group("declarations")
    assert "color: var(--portal-ink);" in status_primary.group("declarations")
    assert "color: var(--portal-muted);" in status_secondary.group("declarations")
    assert "border-color: var(--portal-border-strong);" in status_icon.group("declarations")
    assert "background: var(--portal-surface-soft);" in status_icon.group("declarations")
    assert "color: var(--portal-action);" in status_icon.group("declarations")
    assert _contrast_ratio("#073a45", "#e8f6f7") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5


def test_light_guide_center_metrics_do_not_keep_the_legacy_dark_subpanel() -> None:
    """Guide Center metrics stay readable inside its shared light intro surface."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    metrics = re.search(
        r"\.portal-page \.portal-guide-center-intro > dl > div\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    primary = re.search(
        r"\.portal-page \.portal-guide-center-intro > dl > div > dt\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    secondary = re.search(
        r"\.portal-page \.portal-guide-center-intro > dl > div > dd\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert ".portal-guide-center-intro" in PORTAL_CATALOGUE
    assert metrics is not None
    assert primary is not None
    assert secondary is not None
    assert "border-color: var(--portal-border);" in metrics.group("declarations")
    assert "background: var(--portal-surface-light);" in metrics.group("declarations")
    assert "color: var(--portal-ink);" in primary.group("declarations")
    assert "color: var(--portal-muted);" in secondary.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5


def test_workspace_focus_ring_overrides_the_legacy_important_mint_outline() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    workspace_focus = re.search(
        r"\.portal-main :focus-visible\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert workspace_focus is not None
    assert "outline: 3px solid var(--portal-focus) !important;" in workspace_focus.group("declarations")
    assert "outline-offset: 3px;" in workspace_focus.group("declarations")
    assert "box-shadow: 0 0 0 2px var(--portal-surface-light), 0 0 0 5px var(--portal-focus);" in workspace_focus.group("declarations")
    assert _contrast_ratio("#0369a1", "#ffffff") >= 3
    assert _contrast_ratio("#0369a1", "#f3fbfc") >= 3


def test_account_logout_uses_the_semantic_danger_token_on_the_light_surface() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    logout = re.search(
        r'\.portal-account-page \[data-portal-action="auth-logout"\]\s*\{(?P<declarations>.*?)\n\}',
        theme_source,
        flags=re.DOTALL,
    )

    assert logout is not None
    assert "color: var(--portal-danger);" in logout.group("declarations")
    assert _contrast_ratio("#b91c1c", "#ffffff") >= 4.5


def test_pwa_metadata_and_offline_shell_share_the_canonical_portal_background() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    offline_shell = OFFLINE_SHELL.read_text(encoding="utf-8")

    assert manifest["background_color"] == "#063b47"
    assert manifest["theme_color"] == "#063b47"
    assert '<meta name="theme-color" content="#063b47">' in offline_shell
    assert "background: #063b47;" in offline_shell
    assert "#07141d" not in offline_shell


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


def test_primary_actions_use_the_accessible_dark_teal_and_readable_on_action_text() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)
    primary = re.search(r"\.portal-button--primary\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)

    assert root is not None
    assert primary is not None
    assert "--portal-action: #0f766e;" in root.group("declarations")
    assert "--portal-on-action: #ffffff;" in root.group("declarations")
    assert "background: var(--portal-action);" in primary.group("declarations")
    assert "color: var(--portal-on-action);" in primary.group("declarations")


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


def test_light_auth_primary_submit_uses_the_shared_dark_teal_action() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    primary_submit = re.search(
        r"\.portal-auth-page--access \.portal-auth-primary \.portal-button--primary\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert primary_submit is not None
    assert "background: var(--portal-action);" in primary_submit.group("declarations")
    assert "color: var(--portal-on-action);" in primary_submit.group("declarations")


def test_signed_workspace_uses_light_working_surfaces_and_a_deep_teal_sidebar_rail() -> None:
    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    marker = "/* Signed Workspace shell alignment. */"
    workspace = theme_source[theme_source.index(marker) : theme_source.index("/* Final public-companion layout.")]

    shell = re.search(
        r"\.portal-shell:not\(\.portal-shell--auth\):not\(\.portal-shell--landing\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        workspace,
        flags=re.DOTALL,
    )
    sidebar = re.search(r"\.portal-sidebar\s*\{(?P<declarations>.*?)\n\}", workspace, flags=re.DOTALL)
    header = re.search(r"\.portal-header\s*\{(?P<declarations>.*?)\n\}", workspace, flags=re.DOTALL)
    cards = re.search(
        r"\.portal-shell:not\(\.portal-shell--auth\):not\(\.portal-shell--landing\) :is\("
        r"(?P<declarations>.*?)\n\}",
        workspace,
        flags=re.DOTALL,
    )

    assert shell is not None
    assert sidebar is not None
    assert header is not None
    assert cards is not None
    assert "background: var(--portal-app-canvas);" in shell.group("declarations")
    assert "background: var(--portal-rail);" in sidebar.group("declarations")
    assert "background: var(--portal-surface-light);" in header.group("declarations")
    assert "background: var(--portal-surface-light);" in cards.group("declarations")


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


def test_light_auth_password_toggle_and_music_direction_presets_override_dark_catalogue_text() -> None:
    """Late dark catalogue rules cannot make controls unreadable on light surfaces."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    password_toggle = re.search(
        r"\.portal-auth-page--access \.portal-password-toggle\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    password_toggle_hover = re.search(
        r"\.portal-auth-page--access \.portal-password-toggle:hover,\s*"
        r"\.portal-auth-page--access \.portal-password-toggle:focus-visible\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    access_notice = re.search(
        r"\.portal-auth-page--access \.portal-notice\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    access_notice_title = re.search(
        r"\.portal-auth-page--access \.portal-notice strong\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    access_notice_body = re.search(
        r"\.portal-auth-page--access \.portal-notice p\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    preset_card = re.search(
        r"\.portal-page\.portal-music-directions \.portal-music-directions-preset-card\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    preset_title = re.search(
        r"\.portal-page\.portal-music-directions \.portal-music-directions-preset-copy strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    preset_detail = re.search(
        r"\.portal-page\.portal-music-directions \.portal-music-directions-preset-copy small\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    selected_preset = re.search(
        r"\.portal-shell:not\(\.portal-shell--auth\):not\(\.portal-shell--landing\) "
        r"\.portal-page\.portal-music-directions \.portal-music-directions-preset-card\[data-selected=\"true\"\],"
        r"\s*\.portal-shell:not\(\.portal-shell--auth\):not\(\.portal-shell--landing\) "
        r"\.portal-page\.portal-sfx-cue-sheet \.portal-sfx-cue-sheet-preset-card\[data-selected=\"true\"\]"
        r"\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert password_toggle is not None
    assert password_toggle_hover is not None
    assert access_notice is not None
    assert access_notice_title is not None
    assert access_notice_body is not None
    assert preset_card is not None
    assert preset_title is not None
    assert preset_detail is not None
    assert selected_preset is not None
    assert "color: var(--portal-light-action);" in password_toggle.group("declarations")
    assert "background: var(--portal-light-hover-surface);" in password_toggle_hover.group("declarations")
    assert "background: color-mix(in srgb, var(--portal-context) 8%, var(--portal-surface-light));" in access_notice.group("declarations")
    assert "color: var(--portal-ink);" in access_notice_title.group("declarations")
    assert "color: var(--portal-muted);" in access_notice_body.group("declarations")
    assert "font-size: 12px;" in access_notice_body.group("declarations")
    assert "background: var(--portal-surface-light);" in preset_card.group("declarations")
    assert "color: var(--portal-ink);" in preset_card.group("declarations")
    assert "color: var(--portal-ink);" in preset_title.group("declarations")
    assert "color: var(--portal-muted);" in preset_detail.group("declarations")
    assert "background: var(--portal-light-soft);" in selected_preset.group("declarations")
