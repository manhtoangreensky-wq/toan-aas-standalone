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


def test_light_media_and_bot_companion_surfaces_replace_dark_panel_ink() -> None:
    """Legacy media cards remain readable after the shared light-card override."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    shared_light_cards = re.search(
        r"\.portal-card,.*?\.portal-page \[class\$=\"-card\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    intro_meta = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-bot-companion-intro[^)]*)\) "
        r"\.portal-state-meta span\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    state_icons = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-bot-companion-intro[^)]*)\) "
        r"\.portal-state-icon\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    finalization_state_icon = re.search(
        r"\.portal-page \.portal-finalization-intro \.portal-state-icon\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    card_headings = re.search(
        r"\.portal-page :is\((?P<selectors>[^)]*\.portal-bot-companion-card[^)]*)\) h3\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    finalization_icon = re.search(
        r"\.portal-page \.portal-finalization-card \.portal-module-icon\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    finalization_number = re.search(
        r"\.portal-page \.portal-finalization-number\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    finalization_guard = re.search(
        r"\.portal-page \.portal-finalization-guard\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    bot_command = re.search(
        r"\.portal-page \.portal-bot-companion-card \.portal-link-code\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    legacy_selectors = (
        ".portal-finalization-intro",
        ".portal-media-studio-intro",
        ".portal-bot-companion-intro",
        ".portal-finalization-card h3",
        ".portal-bot-companion-card h3",
        ".portal-link-code",
    )
    assert all(selector in PORTAL_CATALOGUE for selector in legacy_selectors)
    assert shared_light_cards is not None
    assert intro_meta is not None
    assert state_icons is not None
    assert finalization_state_icon is not None
    assert card_headings is not None
    assert finalization_icon is not None
    assert finalization_number is not None
    assert finalization_guard is not None
    assert bot_command is not None
    for selector in (
        ".portal-finalization-intro",
        ".portal-media-studio-intro",
        ".portal-bot-companion-intro",
    ):
        assert selector in intro_meta.group("selectors")
    for selector in (".portal-media-studio-intro", ".portal-bot-companion-intro"):
        assert selector in state_icons.group("selectors")
    for selector in (".portal-finalization-card", ".portal-bot-companion-card"):
        assert selector in card_headings.group("selectors")
    assert "border-color: var(--portal-border);" in shared_light_cards.group("declarations")
    assert "background: var(--portal-surface);" in shared_light_cards.group("declarations")
    assert ".portal-finalization-card.is-guarded { border-style: dashed;" in PORTAL_CATALOGUE
    assert "border: 1px solid var(--portal-border);" in intro_meta.group("declarations")
    assert "background: var(--portal-surface-light);" in intro_meta.group("declarations")
    assert "color: var(--portal-muted);" in intro_meta.group("declarations")
    assert "color: var(--portal-context);" in state_icons.group("declarations")
    assert "color: var(--portal-warning);" in finalization_state_icon.group("declarations")
    assert "color: var(--portal-ink);" in card_headings.group("declarations")
    assert "border-color: var(--portal-border);" in finalization_icon.group("declarations")
    assert "background: var(--portal-surface-soft);" in finalization_icon.group("declarations")
    assert "color: var(--portal-context);" in finalization_icon.group("declarations")
    assert "color: var(--portal-context);" in finalization_number.group("declarations")
    assert "color: var(--portal-warning);" in finalization_guard.group("declarations")
    assert "border-color: var(--portal-border);" in bot_command.group("declarations")
    assert "background: var(--portal-surface-soft);" in bot_command.group("declarations")
    assert "color: var(--portal-context);" in bot_command.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5
    assert _contrast_ratio("#0369a1", "#ffffff") >= 4.5
    assert _contrast_ratio("#a16207", "#ffffff") >= 4.5


def test_light_dashboard_and_catalogue_cards_keep_their_actual_heading_hierarchy() -> None:
    """Dashboard markup uses plain strong/h3 elements, not the legacy title aliases."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    headings = re.search(
        r"\.portal-page \.portal-action-card > strong,\s*"
        r"\.portal-page \.portal-action-card h3,\s*"
        r"\.portal-page \.portal-module-card h3,\s*"
        r"\.portal-page \.portal-studio-card h3\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    hover = re.search(
        r"\.portal-page :is\(\s*\.portal-action-card,\s*\.portal-module-card,\s*"
        r"\.portal-studio-card\s*\):hover\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    studio_tags = re.search(
        r"\.portal-page \.portal-studio-tags span\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    studio_open = re.search(
        r"\.portal-page \.portal-studio-open,\s*\.portal-page \.portal-studio-open b\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert '<a class="portal-action-card"' in PORTAL_CLIENT
    assert '<strong>${safeText(String(card.count))}</strong><h3>${card.label}</h3>' in PORTAL_CLIENT
    assert '<a class="portal-module-card"' in PORTAL_CLIENT
    assert '<a class="portal-studio-card"' in PORTAL_CLIENT
    assert headings is not None
    assert hover is not None
    assert studio_tags is not None
    assert studio_open is not None
    assert "color: var(--portal-ink);" in headings.group("declarations")
    assert "border-color: var(--portal-border-strong);" in hover.group("declarations")
    assert "background: var(--portal-surface-soft);" in hover.group("declarations")
    assert "border-color: var(--portal-border);" in studio_tags.group("declarations")
    assert "background: var(--portal-surface-light);" in studio_tags.group("declarations")
    assert "color: var(--portal-muted);" in studio_tags.group("declarations")
    assert "color: var(--portal-action);" in studio_open.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#0f766e", "#ffffff") >= 4.5


def test_light_catalogue_card_icons_and_engine_labels_preserve_status_meaning() -> None:
    """Native, companion and guarded labels remain distinct on a light card."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    icon_surfaces = re.search(
        r"\.portal-page :is\(\s*\.portal-action-card,\s*\.portal-module-card\s*\) "
        r"\.portal-module-icon,\s*\.portal-page \.portal-studio-card \.portal-studio-icon\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    engine_label = re.search(
        r"\.portal-page \.portal-module-card \.portal-engine-label\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    web_native = re.search(
        r"\.portal-page \.portal-module-card \.portal-engine-label\[data-engine-mode=\"web_native\"\] "
        r"\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    bot_companion = re.search(
        r"\.portal-page \.portal-module-card \.portal-engine-label\[data-engine-mode=\"bot_companion\"\] "
        r"\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    guarded = re.search(
        r"\.portal-page \.portal-module-card \.portal-engine-label\[data-engine-mode=\"guarded\"\] "
        r"\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert 'class="portal-engine-label" data-engine-mode="${safeText(engine.mode)}"' in PORTAL_CLIENT
    assert icon_surfaces is not None
    assert engine_label is not None
    assert web_native is not None
    assert bot_companion is not None
    assert guarded is not None
    assert "border-color: var(--portal-border);" in icon_surfaces.group("declarations")
    assert "background: var(--portal-surface-soft);" in icon_surfaces.group("declarations")
    assert "color: var(--portal-context);" in icon_surfaces.group("declarations")
    assert "border-color: var(--portal-border);" in engine_label.group("declarations")
    assert "background: var(--portal-surface-light);" in engine_label.group("declarations")
    assert "color: var(--portal-muted);" in engine_label.group("declarations")
    assert "color: var(--portal-action);" in web_native.group("declarations")
    assert "color: var(--portal-context);" in bot_companion.group("declarations")
    assert "background: var(--portal-surface-light);" in guarded.group("declarations")
    assert "color: var(--portal-warning);" in guarded.group("declarations")
    assert _contrast_ratio("#0f766e", "#ffffff") >= 4.5
    assert _contrast_ratio("#0369a1", "#ffffff") >= 4.5
    assert _contrast_ratio("#a16207", "#ffffff") >= 4.5


def test_light_canonical_suggestions_keep_generated_text_readable() -> None:
    """Suggestion cards inherit the light card system without retaining dark-panel ink."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    heading = re.search(
        r"\.portal-page \.portal-suggestion-card-head strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    label = re.search(
        r"\.portal-page \.portal-suggestion-card-head span\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    generated_text = re.search(
        r"\.portal-page \.portal-suggestion-card \.portal-result-text\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert '<article class="portal-suggestion-card">' in PORTAL_CLIENT
    assert '<strong>${safeText(String(item.name || `Gợi ý ${index + 1}`))}</strong>' in PORTAL_CLIENT
    assert '<div class="portal-result-text">${safeText(prompt)}</div>' in PORTAL_CLIENT
    assert ".portal-suggestion-card-head strong" in PORTAL_CATALOGUE
    assert ".portal-result-text" in PORTAL_CATALOGUE
    assert heading is not None
    assert label is not None
    assert generated_text is not None
    assert "color: var(--portal-ink);" in heading.group("declarations")
    assert "color: var(--portal-action);" in label.group("declarations")
    assert "border-color: var(--portal-border);" in generated_text.group("declarations")
    assert "background: var(--portal-surface-soft);" in generated_text.group("declarations")
    assert "color: var(--portal-ink);" in generated_text.group("declarations")
    assert _contrast_ratio("#073a45", "#e6f8f7") >= 4.5
    assert _contrast_ratio("#0f766e", "#ffffff") >= 4.5


def test_light_support_case_cards_keep_customer_and_operator_metadata_readable() -> None:
    """The shared light-card rule must not leave Support Desk's old pale ink behind."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    card_hover = re.search(
        r"\.portal-page \.portal-support-case-card:hover\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    category = re.search(
        r"\.portal-page \.portal-support-case-card \.portal-support-case-category\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    heading = re.search(
        r"\.portal-page \.portal-support-case-card h3\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    excerpt = re.search(
        r"\.portal-page \.portal-support-case-card > p\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    meta_card = re.search(
        r"\.portal-page \.portal-support-case-meta > div\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    meta_label = re.search(
        r"\.portal-page \.portal-support-case-meta dt,\s*"
        r"\.portal-page \.portal-support-case-meta dd small\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    meta_value = re.search(
        r"\.portal-page \.portal-support-case-meta dd\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert '<article class="portal-support-case-card">' in PORTAL_CLIENT
    assert '<span class="portal-support-case-category">' in PORTAL_CLIENT
    assert '<dl class="portal-support-case-meta">' in PORTAL_CLIENT
    assert ".portal-support-case-card h3" in PORTAL_CATALOGUE
    assert ".portal-support-case-meta dd" in PORTAL_CATALOGUE
    for match in (card_hover, category, heading, excerpt, meta_card, meta_label, meta_value):
        assert match is not None
    assert "border-color: var(--portal-border-strong);" in card_hover.group("declarations")
    assert "background: var(--portal-surface-soft);" in card_hover.group("declarations")
    assert "border-color: var(--portal-border);" in category.group("declarations")
    assert "background: var(--portal-surface-soft);" in category.group("declarations")
    assert "color: var(--portal-context);" in category.group("declarations")
    assert "color: var(--portal-ink);" in heading.group("declarations")
    assert "color: var(--portal-muted);" in excerpt.group("declarations")
    assert "border-color: var(--portal-border);" in meta_card.group("declarations")
    assert "background: var(--portal-surface-light);" in meta_card.group("declarations")
    assert "color: var(--portal-muted);" in meta_label.group("declarations")
    assert "color: var(--portal-ink);" in meta_value.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5
    assert _contrast_ratio("#0369a1", "#e6f8f7") >= 4.5


def test_light_campaign_cards_keep_planning_metadata_and_actions_readable() -> None:
    """Campaign list, detail and self-review cards share the same light card surface."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    card_hover = re.search(
        r"\.portal-page \.portal-campaign-card:hover\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    heading = re.search(
        r"\.portal-page \.portal-campaign-card h3,\s*"
        r"\.portal-page \.portal-campaign-card h3 a\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    eyebrow = re.search(
        r"\.portal-page \.portal-campaign-card \.portal-eyebrow\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    card_copy = re.search(
        r"\.portal-page \.portal-campaign-card-head p\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    destination = re.search(
        r"\.portal-page \.portal-campaign-destination\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    destination_hover = re.search(
        r"\.portal-page \.portal-campaign-destination:hover,\s*"
        r"\.portal-page \.portal-campaign-destination:focus-visible\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    edit = re.search(
        r"\.portal-page \.portal-campaign-edit\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    edit_summary = re.search(
        r"\.portal-page \.portal-campaign-edit > summary\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    assert '<article class="portal-campaign-card"' in PORTAL_CLIENT
    assert '<dl class="portal-campaign-facts">' in PORTAL_CLIENT
    assert ".portal-campaign-card h3" in PORTAL_CATALOGUE
    assert ".portal-campaign-destination" in PORTAL_CATALOGUE
    for match in (
        card_hover,
        heading,
        eyebrow,
        card_copy,
        destination,
        destination_hover,
        edit,
        edit_summary,
    ):
        assert match is not None
    assert "border-color: var(--portal-border-strong);" in card_hover.group("declarations")
    assert "background: var(--portal-surface-soft);" in card_hover.group("declarations")
    assert "color: var(--portal-ink);" in heading.group("declarations")
    assert "color: var(--portal-action);" in eyebrow.group("declarations")
    assert "color: var(--portal-muted);" in card_copy.group("declarations")
    assert "color: var(--portal-action);" in destination.group("declarations")
    assert "color: var(--portal-action-hover);" in destination_hover.group("declarations")
    assert "border-top-color: var(--portal-border);" in edit.group("declarations")
    assert "border-bottom-color: var(--portal-border);" in edit.group("declarations")
    assert "color: var(--portal-ink);" in edit_summary.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#0f766e", "#ffffff") >= 4.5
    assert _contrast_ratio("#115e59", "#ffffff") >= 4.5


def test_light_artifact_cards_keep_icons_and_private_metadata_readable() -> None:
    """Project exports, document operations, vault files and reminders share light cards."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    icons = re.search(
        r"\.portal-page :is\(\s*\.portal-project-package-icon,\s*"
        r"\.portal-document-operation-icon,\s*\.portal-vault-file-icon\s*\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_cards = re.search(
        r"\.portal-page :is\(\s*\.portal-project-package-meta,\s*"
        r"\.portal-document-operation-meta,\s*\.portal-vault-meta,\s*"
        r"\.portal-memory-reminder-meta\s*\) > div\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_labels = re.search(
        r"\.portal-page :is\(\s*\.portal-project-package-meta,\s*"
        r"\.portal-document-operation-meta,\s*\.portal-vault-meta,\s*"
        r"\.portal-memory-reminder-meta\s*\) dt\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_values = re.search(
        r"\.portal-page :is\(\s*\.portal-project-package-meta,\s*"
        r"\.portal-document-operation-meta,\s*\.portal-vault-meta,\s*"
        r"\.portal-memory-reminder-meta\s*\) dd\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    overdue = re.search(
        r"\.portal-page \.portal-memory-overdue\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    reminder_edit = re.search(
        r"\.portal-page \.portal-memory-reminder-edit > summary\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    for marker in (
        'class="portal-project-package-icon"',
        'class="portal-document-operation-icon"',
        'class="portal-vault-file-icon"',
        'class="portal-memory-reminder-meta"',
    ):
        assert marker in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-project-package-icon",
            ".portal-document-operation-icon",
            ".portal-vault-file-icon",
            ".portal-memory-reminder-meta",
        )
    )
    for match in (icons, metadata_cards, metadata_labels, metadata_values, overdue, reminder_edit):
        assert match is not None
    assert "border-color: var(--portal-border);" in icons.group("declarations")
    assert "background: var(--portal-surface-soft);" in icons.group("declarations")
    assert "color: var(--portal-context);" in icons.group("declarations")
    assert "border-color: var(--portal-border);" in metadata_cards.group("declarations")
    assert "background: var(--portal-surface-light);" in metadata_cards.group("declarations")
    assert "color: var(--portal-muted);" in metadata_labels.group("declarations")
    assert "color: var(--portal-ink);" in metadata_values.group("declarations")
    assert "border-color: var(--portal-warning);" in overdue.group("declarations")
    assert "background: var(--portal-surface-light);" in overdue.group("declarations")
    assert "color: var(--portal-warning);" in overdue.group("declarations")
    assert "color: var(--portal-context);" in reminder_edit.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5
    assert _contrast_ratio("#0369a1", "#e6f8f7") >= 4.5
    assert _contrast_ratio("#a16207", "#ffffff") >= 4.5


def test_light_workboard_cards_keep_kanban_and_list_metadata_readable() -> None:
    """Workboard must not retain dark-panel ink after the shared card reset."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    tabs = re.search(
        r"\.portal-page \.portal-workboard-tabs a\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    active_tab = re.search(
        r"\.portal-page \.portal-workboard-tabs a:hover,\s*"
        r"\.portal-page \.portal-workboard-tabs a\[aria-current=\"page\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    column = re.search(
        r"\.portal-page \.portal-workboard-column\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    column_label = re.search(
        r"\.portal-page \.portal-workboard-column > header span\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    card_hover = re.search(
        r"\.portal-page \.portal-workboard-card:hover\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    card_title = re.search(
        r"\.portal-page \.portal-workboard-card h3,\s*"
        r"\.portal-page \.portal-workboard-card h3 a\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    card_metadata = re.search(
        r"\.portal-page \.portal-workboard-card :is\(p, footer\)\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    list_row = re.search(
        r"\.portal-page \.portal-workboard-list-row\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    list_title = re.search(
        r"\.portal-page \.portal-workboard-list-title b\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    list_metadata = re.search(
        r"\.portal-page :is\(\.portal-workboard-list-title small, "
        r"\.portal-workboard-list-meta small\)\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    priority = re.search(
        r"\.portal-page \.portal-workboard-priority\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    urgent_priority = re.search(
        r"\.portal-page \.portal-workboard-priority\[data-priority=\"urgent\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    for marker in (
        'class="portal-workboard-card"',
        'class="portal-workboard-list-row"',
        'class="portal-workboard-priority"',
    ):
        assert marker in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-workboard-column",
            ".portal-workboard-card h3",
            ".portal-workboard-list-row",
            ".portal-workboard-priority",
        )
    )
    for match in (
        tabs,
        active_tab,
        column,
        column_label,
        card_hover,
        card_title,
        card_metadata,
        list_row,
        list_title,
        list_metadata,
        priority,
        urgent_priority,
    ):
        assert match is not None
    assert "border-color: var(--portal-border);" in tabs.group("declarations")
    assert "background: var(--portal-surface-light);" in tabs.group("declarations")
    assert "color: var(--portal-muted);" in tabs.group("declarations")
    assert "background: var(--portal-surface-soft);" in active_tab.group("declarations")
    assert "color: var(--portal-action);" in active_tab.group("declarations")
    assert "border-color: var(--portal-border);" in column.group("declarations")
    assert "background: var(--portal-surface-soft);" in column.group("declarations")
    assert "color: var(--portal-ink);" in column_label.group("declarations")
    assert "border-color: var(--portal-border-strong);" in card_hover.group("declarations")
    assert "background: var(--portal-surface-soft);" in card_hover.group("declarations")
    assert "color: var(--portal-ink);" in card_title.group("declarations")
    assert "color: var(--portal-muted);" in card_metadata.group("declarations")
    assert "border-color: var(--portal-border);" in list_row.group("declarations")
    assert "background: var(--portal-surface-light);" in list_row.group("declarations")
    assert "color: var(--portal-ink);" in list_title.group("declarations")
    assert "color: var(--portal-muted);" in list_metadata.group("declarations")
    assert "border-color: var(--portal-border);" in priority.group("declarations")
    assert "background: var(--portal-surface-light);" in priority.group("declarations")
    assert "color: var(--portal-muted);" in priority.group("declarations")
    assert "color: var(--portal-danger);" in urgent_priority.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5
    assert _contrast_ratio("#0f766e", "#e6f8f7") >= 4.5
    assert _contrast_ratio("#b91c1c", "#ffffff") >= 4.5


def test_light_operations_cards_keep_erp_evidence_and_severity_readable() -> None:
    """Operations metrics and incidents must not retain the dark control-room palette."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    metrics = re.search(
        r"\.portal-page :is\(\.portal-operations, \.portal-operations-admin\) "
        r"\.portal-operations-metrics \.portal-metric\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metric_label = re.search(
        r"\.portal-page :is\(\.portal-operations, \.portal-operations-admin\) "
        r"\.portal-operations-metrics \.portal-metric > span\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metric_value = re.search(
        r"\.portal-page :is\(\.portal-operations, \.portal-operations-admin\) "
        r"\.portal-operations-metrics \.portal-metric > strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    incident = re.search(
        r"\.portal-page \.portal-operations-incident\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    high_incident = re.search(
        r"\.portal-page \.portal-operations-incident\[data-severity=\"high\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    critical_incident = re.search(
        r"\.portal-page \.portal-operations-incident\[data-severity=\"critical\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    incident_heading = re.search(
        r"\.portal-page \.portal-operations-incident h3\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    incident_copy = re.search(
        r"\.portal-page \.portal-operations-incident p\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_card = re.search(
        r"\.portal-page \.portal-operations-meta > div\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_label = re.search(
        r"\.portal-page \.portal-operations-meta dt\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_value = re.search(
        r"\.portal-page \.portal-operations-meta dd\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    code = re.search(
        r"\.portal-page \.portal-operations-code\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    approval = re.search(
        r"\.portal-page \.portal-operations-approval\[data-state=\"awaiting_approval\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    for marker in (
        'class="portal-operations-metrics"',
        'class="portal-operations-incident"',
        'class="portal-operations-meta"',
        'class="portal-operations-code"',
    ):
        assert marker in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-operations-metrics .portal-metric",
            ".portal-operations-incident",
            ".portal-operations-meta > div",
            ".portal-operations-code",
        )
    )
    for match in (
        metrics,
        metric_label,
        metric_value,
        incident,
        high_incident,
        critical_incident,
        incident_heading,
        incident_copy,
        metadata_card,
        metadata_label,
        metadata_value,
        code,
        approval,
    ):
        assert match is not None
    assert "border-color: var(--portal-border);" in metrics.group("declarations")
    assert "background: var(--portal-surface-light);" in metrics.group("declarations")
    assert "color: var(--portal-muted);" in metric_label.group("declarations")
    assert "color: var(--portal-ink);" in metric_value.group("declarations")
    assert "border-color: var(--portal-border);" in incident.group("declarations")
    assert "background: var(--portal-surface-light);" in incident.group("declarations")
    assert "border-color: var(--portal-warning);" in high_incident.group("declarations")
    assert "border-color: var(--portal-danger);" in critical_incident.group("declarations")
    assert "color: var(--portal-ink);" in incident_heading.group("declarations")
    assert "color: var(--portal-muted);" in incident_copy.group("declarations")
    assert "border-color: var(--portal-border);" in metadata_card.group("declarations")
    assert "background: var(--portal-surface-soft);" in metadata_card.group("declarations")
    assert "color: var(--portal-muted);" in metadata_label.group("declarations")
    assert "color: var(--portal-ink);" in metadata_value.group("declarations")
    assert "background: var(--portal-surface-soft);" in code.group("declarations")
    assert "color: var(--portal-context);" in code.group("declarations")
    assert "border-color: var(--portal-warning);" in approval.group("declarations")
    assert "background: var(--portal-surface-light);" in approval.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5
    assert _contrast_ratio("#a16207", "#ffffff") >= 4.5
    assert _contrast_ratio("#b91c1c", "#ffffff") >= 4.5


def test_light_inbox_cards_keep_private_notification_states_readable() -> None:
    """Inbox must retain a calm, truthful customer surface after the light reset."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    intro = re.search(
        r"\.portal-page :is\(\.portal-inbox, \.portal-notification-automation\) "
        r"\.portal-inbox-intro :is\(h2, dt\)\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    intro_copy = re.search(
        r"\.portal-page :is\(\.portal-inbox, \.portal-notification-automation\) "
        r"\.portal-inbox-intro :is\(p, dd\)\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metrics = re.search(
        r"\.portal-page \.portal-inbox \.portal-inbox-metrics \.portal-metric\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metric_value = re.search(
        r"\.portal-page \.portal-inbox \.portal-inbox-metrics \.portal-metric > strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    filter_surface = re.search(
        r"\.portal-page \.portal-inbox-filter\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    notification = re.search(
        r"\.portal-page \.portal-inbox-item\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    notification_hover = re.search(
        r"\.portal-page \.portal-inbox-item:hover,\s*"
        r"\.portal-page \.portal-inbox-item:focus-within\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    urgent_notification = re.search(
        r"\.portal-page \.portal-inbox-item\[data-severity=\"urgent\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    dismissed_notification = re.search(
        r"\.portal-page \.portal-inbox-item\[data-state=\"dismissed\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    kind = re.search(
        r"\.portal-page \.portal-inbox-kind\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    notification_heading = re.search(
        r"\.portal-page \.portal-inbox-item h3\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    notification_copy = re.search(
        r"\.portal-page \.portal-inbox-item p\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_card = re.search(
        r"\.portal-page \.portal-inbox-item-meta > div\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_label = re.search(
        r"\.portal-page \.portal-inbox-item-meta dt\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    metadata_value = re.search(
        r"\.portal-page \.portal-inbox-item-meta dd\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    run_title = re.search(
        r"\.portal-page \.portal-inbox-run strong\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    for marker in (
        'class="portal-inbox-metrics"',
        'class="portal-inbox-filter"',
        'class="portal-inbox-item"',
        'class="portal-inbox-item-meta"',
    ):
        assert marker in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-inbox-metrics .portal-metric",
            ".portal-inbox-filter",
            ".portal-inbox-item",
            ".portal-inbox-item-meta > div",
        )
    )
    for match in (
        intro,
        intro_copy,
        metrics,
        metric_value,
        filter_surface,
        notification,
        notification_hover,
        urgent_notification,
        dismissed_notification,
        kind,
        notification_heading,
        notification_copy,
        metadata_card,
        metadata_label,
        metadata_value,
        run_title,
    ):
        assert match is not None
    assert "color: var(--portal-ink);" in intro.group("declarations")
    assert "color: var(--portal-muted);" in intro_copy.group("declarations")
    assert "border-color: var(--portal-border);" in metrics.group("declarations")
    assert "background: var(--portal-surface-light);" in metrics.group("declarations")
    assert "color: var(--portal-ink);" in metric_value.group("declarations")
    assert "border-color: var(--portal-border);" in filter_surface.group("declarations")
    assert "background: var(--portal-surface-soft);" in filter_surface.group("declarations")
    assert "border-color: var(--portal-border);" in notification.group("declarations")
    assert "background: var(--portal-surface-light);" in notification.group("declarations")
    assert "border-color: var(--portal-border-strong);" in notification_hover.group("declarations")
    assert "background: var(--portal-surface-soft);" in notification_hover.group("declarations")
    assert "border-color: var(--portal-warning);" in urgent_notification.group("declarations")
    assert "opacity: 1;" in dismissed_notification.group("declarations")
    assert "color: var(--portal-context);" in kind.group("declarations")
    assert "color: var(--portal-ink);" in notification_heading.group("declarations")
    assert "color: var(--portal-muted);" in notification_copy.group("declarations")
    assert "border-color: var(--portal-border);" in metadata_card.group("declarations")
    assert "background: var(--portal-surface-soft);" in metadata_card.group("declarations")
    assert "color: var(--portal-muted);" in metadata_label.group("declarations")
    assert "color: var(--portal-ink);" in metadata_value.group("declarations")
    assert "color: var(--portal-ink);" in run_title.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5
    assert _contrast_ratio("#0369a1", "#ffffff") >= 4.5
    assert _contrast_ratio("#a16207", "#ffffff") >= 4.5


def test_light_billing_surfaces_keep_canonical_wallet_decisions_readable() -> None:
    """Canonical billing projections need the same calm hierarchy as the workspace."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    wallet_facts = re.search(
        r"\.portal-page \.portal-wallet-facts\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    wallet_label = re.search(
        r"\.portal-page \.portal-wallet-facts dt\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    wallet_value = re.search(
        r"\.portal-page \.portal-wallet-facts dd\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    wallet_status = re.search(
        r"\.portal-page \.portal-wallet-read-status\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    journey = re.search(
        r"\.portal-page \.portal-billing-journey\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    journey_heading = re.search(
        r"\.portal-page \.portal-billing-journey h2\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    journey_copy = re.search(
        r"\.portal-page \.portal-billing-journey p\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    journey_lane = re.search(
        r"\.portal-page \.portal-billing-journey-lanes li\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    entry = re.search(
        r"\.portal-page \.portal-billing-entrypoints \.portal-payment-entry\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    catalog_intro = re.search(
        r"\.portal-page \.portal-billing-catalog-intro\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    catalog_heading = re.search(
        r"\.portal-page \.portal-billing-catalog-intro h2\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    billing_nav = re.search(
        r"\.portal-page \.portal-billing-nav\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    billing_nav_link = re.search(
        r"\.portal-page \.portal-billing-nav a\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    billing_nav_current = re.search(
        r"\.portal-page \.portal-billing-nav a\[aria-current=\"page\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    for marker in (
        'class="portal-wallet-facts"',
        'class="portal-wallet-read-status"',
        'class="portal-billing-journey"',
        'class="portal-billing-catalog-intro"',
        'class="portal-billing-nav"',
    ):
        assert marker in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-wallet-facts",
            ".portal-wallet-read-status",
            ".portal-billing-journey",
            ".portal-billing-catalog-intro",
            ".portal-billing-nav",
        )
    )
    for match in (
        wallet_facts,
        wallet_label,
        wallet_value,
        wallet_status,
        journey,
        journey_heading,
        journey_copy,
        journey_lane,
        entry,
        catalog_intro,
        catalog_heading,
        billing_nav,
        billing_nav_link,
        billing_nav_current,
    ):
        assert match is not None
    assert "border-color: var(--portal-border);" in wallet_facts.group("declarations")
    assert "background: var(--portal-surface-light);" in wallet_facts.group("declarations")
    assert "color: var(--portal-muted);" in wallet_label.group("declarations")
    assert "color: var(--portal-ink);" in wallet_value.group("declarations")
    assert "background: var(--portal-surface-soft);" in wallet_status.group("declarations")
    assert "color: var(--portal-muted);" in wallet_status.group("declarations")
    assert "background: var(--portal-surface-light);" in journey.group("declarations")
    assert "color: var(--portal-ink);" in journey_heading.group("declarations")
    assert "color: var(--portal-muted);" in journey_copy.group("declarations")
    assert "background: var(--portal-surface-soft);" in journey_lane.group("declarations")
    assert "background: var(--portal-surface-light);" in entry.group("declarations")
    assert "background: var(--portal-surface-light);" in catalog_intro.group("declarations")
    assert "color: var(--portal-ink);" in catalog_heading.group("declarations")
    assert "background: var(--portal-surface-light);" in billing_nav.group("declarations")
    assert "color: var(--portal-muted);" in billing_nav_link.group("declarations")
    assert "border-color: var(--portal-context);" in billing_nav_current.group("declarations")
    assert "background: var(--portal-surface-soft);" in billing_nav_current.group("declarations")


def test_light_delivery_surfaces_keep_private_job_and_asset_metadata_readable() -> None:
    """Job and asset records stay owner-scoped while their light cards keep state legible."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    summary = re.search(
        r"\.portal-page \.portal-delivery-summary-card\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    summary_label = re.search(
        r"\.portal-page \.portal-delivery-summary-card > span\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    summary_value = re.search(
        r"\.portal-page \.portal-delivery-summary-card > strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    source_vault = re.search(
        r"\.portal-page \.portal-record-source\[data-record-source=\"web_vault\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    source_output = re.search(
        r"\.portal-page \.portal-record-source\[data-record-source=\"web_native_output\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    source_delivery = re.search(
        r"\.portal-page \.portal-record-source\[data-record-source=\"canonical_delivery\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    lifecycle_item = re.search(
        r"\.portal-page \.portal-delivery-lifecycle-list li\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    lifecycle_title = re.search(
        r"\.portal-page \.portal-delivery-lifecycle-list strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    lifecycle_copy = re.search(
        r"\.portal-page \.portal-delivery-lifecycle-list p\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    next_action = re.search(
        r"\.portal-page \.portal-delivery-next-action\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    mobile_card = re.search(
        r"\.portal-page \.portal-delivery-mobile-card\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    mobile_title = re.search(
        r"\.portal-page \.portal-delivery-mobile-card-head strong\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    mobile_value = re.search(
        r"\.portal-page \.portal-delivery-mobile-meta dd\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_nav = re.search(
        r"\.portal-page \.portal-delivery-nav\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_nav_link = re.search(
        r"\.portal-page \.portal-delivery-nav a\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_nav_current = re.search(
        r"\.portal-page \.portal-delivery-nav a\[aria-current=\"page\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    for marker in (
        'class="portal-delivery-summary"',
        'class="portal-record-source"',
        'class="portal-delivery-lifecycle-list"',
        'class="portal-delivery-next-action"',
        'class="portal-delivery-mobile-card"',
        'class="portal-delivery-nav"',
    ):
        assert marker in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-delivery-summary-card",
            ".portal-record-source",
            ".portal-delivery-lifecycle-list",
            ".portal-delivery-next-action",
            ".portal-delivery-mobile-card",
            ".portal-delivery-nav",
        )
    )
    for match in (
        summary,
        summary_label,
        summary_value,
        source_vault,
        source_output,
        source_delivery,
        lifecycle_item,
        lifecycle_title,
        lifecycle_copy,
        next_action,
        mobile_card,
        mobile_title,
        mobile_value,
        delivery_nav,
        delivery_nav_link,
        delivery_nav_current,
    ):
        assert match is not None
    assert "border-color: var(--portal-border);" in summary.group("declarations")
    assert "background: var(--portal-surface-light);" in summary.group("declarations")
    assert "color: var(--portal-muted);" in summary_label.group("declarations")
    assert "color: var(--portal-ink);" in summary_value.group("declarations")
    assert "color: var(--portal-context);" in source_vault.group("declarations")
    assert "color: var(--portal-action);" in source_output.group("declarations")
    assert "color: var(--portal-warning);" in source_delivery.group("declarations")
    assert "background: var(--portal-surface-light);" in lifecycle_item.group("declarations")
    assert "color: var(--portal-ink);" in lifecycle_title.group("declarations")
    assert "color: var(--portal-muted);" in lifecycle_copy.group("declarations")
    assert "background: var(--portal-surface-light);" in next_action.group("declarations")
    assert "background: var(--portal-surface-light);" in mobile_card.group("declarations")
    assert "color: var(--portal-ink);" in mobile_title.group("declarations")
    assert "color: var(--portal-ink);" in mobile_value.group("declarations")
    assert "background: var(--portal-surface-light);" in delivery_nav.group("declarations")
    assert "color: var(--portal-muted);" in delivery_nav_link.group("declarations")
    assert "border-color: var(--portal-context);" in delivery_nav_current.group("declarations")
    assert "background: var(--portal-surface-soft);" in delivery_nav_current.group("declarations")


def test_delivery_light_surface_keeps_live_states_and_manual_handoff_readable() -> None:
    """Every real delivery state must remain readable without changing its authority."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    filter_button = re.search(
        r"\.portal-page \.portal-filter-button\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    filter_active = re.search(
        r"\.portal-page \.portal-filter-button:hover,\s*"
        r"\.portal-page \.portal-filter-button\.is-active\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    filter_count = re.search(
        r"\.portal-page \.portal-filter-button span\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_state = re.search(
        r"\.portal-page \.portal-delivery-state\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_reported = re.search(
        r"\.portal-page \.portal-delivery-state\[data-delivery=\"reported\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_pending = re.search(
        r"\.portal-page \.portal-delivery-state\[data-delivery=\"pending\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_validated = re.search(
        r"\.portal-page \.portal-delivery-state\[data-delivery=\"validated\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_unavailable = re.search(
        r"\.portal-page \.portal-delivery-state\[data-delivery=\"unavailable\"\]\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_link_hover = re.search(
        r"\.portal-page \.portal-delivery-link:hover\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    delivery_link_focus = re.search(
        r"\.portal-page \.portal-delivery-link:focus-visible\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    job_cost = re.search(
        r"\.portal-page \.portal-job-cost strong\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    payment_entry = re.search(
        r"\.portal-page \.portal-payment-entry\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    payment_heading = re.search(
        r"\.portal-page \.portal-payment-entry h3\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    payment_note = re.search(
        r"\.portal-page \.portal-payment-entry-note\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    payment_code = re.search(
        r"\.portal-page \.portal-billing-entrypoints \.portal-link-code\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    manual_route = re.search(
        r"\.portal-page \.portal-manual-topup-route\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    manual_heading = re.search(
        r"\.portal-page \.portal-manual-topup-route h3\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    manual_copy = re.search(
        r"\.portal-page \.portal-manual-topup-route p\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    manual_status_copy = re.search(
        r"\.portal-page \.portal-manual-topup-route > span:last-child\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    manual_guarded = re.search(
        r"\.portal-page \.portal-manual-topup-route\.is-guarded\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    manual_status = re.search(
        r"\.portal-page \.portal-manual-topup-status > span\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )
    manual_code = re.search(
        r"\.portal-page \.portal-manual-topup-status code\s*\{"
        r"(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL,
    )

    for marker in (
        'class="portal-filter-button',
        'class="portal-delivery-state"',
        'class="portal-delivery-state portal-delivery-link"',
        'class="portal-job-cost"',
        'class="portal-payment-entry',
        'class="portal-manual-topup-route',
        'class="portal-manual-topup-status"',
    ):
        assert marker in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-filter-button",
            ".portal-delivery-state",
            ".portal-delivery-link",
            ".portal-job-cost strong",
            ".portal-payment-entry",
            ".portal-manual-topup-route",
            ".portal-manual-topup-status > span",
        )
    )
    for match in (
        filter_button,
        filter_active,
        filter_count,
        delivery_state,
        delivery_reported,
        delivery_pending,
        delivery_validated,
        delivery_unavailable,
        delivery_link_hover,
        delivery_link_focus,
        job_cost,
        payment_entry,
        payment_heading,
        payment_note,
        payment_code,
        manual_route,
        manual_heading,
        manual_copy,
        manual_status_copy,
        manual_guarded,
        manual_status,
        manual_code,
    ):
        assert match is not None
    assert "background: var(--portal-surface-light);" in filter_button.group("declarations")
    assert "color: var(--portal-muted);" in filter_button.group("declarations")
    assert "border-color: var(--portal-context);" in filter_active.group("declarations")
    assert "background: var(--portal-surface-soft);" in filter_active.group("declarations")
    assert "color: var(--portal-ink);" in filter_active.group("declarations")
    assert "color: var(--portal-context);" in filter_count.group("declarations")
    assert "background: var(--portal-surface-light);" in delivery_state.group("declarations")
    assert "color: var(--portal-muted);" in delivery_state.group("declarations")
    assert "color: var(--portal-action);" in delivery_reported.group("declarations")
    assert "color: var(--portal-warning);" in delivery_pending.group("declarations")
    assert "background: var(--portal-surface-soft);" in delivery_validated.group("declarations")
    assert "color: var(--portal-action);" in delivery_validated.group("declarations")
    assert "color: var(--portal-danger);" in delivery_unavailable.group("declarations")
    assert "background: var(--portal-action);" in delivery_link_hover.group("declarations")
    assert "color: var(--portal-on-action);" in delivery_link_hover.group("declarations")
    assert "outline: 3px solid var(--portal-focus);" in delivery_link_focus.group("declarations")
    assert "color: var(--portal-ink);" in job_cost.group("declarations")
    assert "background: var(--portal-surface-light);" in payment_entry.group("declarations")
    assert "color: var(--portal-ink);" in payment_heading.group("declarations")
    assert "color: var(--portal-muted);" in payment_note.group("declarations")
    assert "background: var(--portal-surface-soft);" in payment_code.group("declarations")
    assert "color: var(--portal-context);" in payment_code.group("declarations")
    assert "background: var(--portal-surface-light);" in manual_route.group("declarations")
    assert "color: var(--portal-ink);" in manual_heading.group("declarations")
    assert "color: var(--portal-muted);" in manual_copy.group("declarations")
    assert "color: var(--portal-muted);" in manual_status_copy.group("declarations")
    assert "border-color: var(--portal-warning);" in manual_guarded.group("declarations")
    assert "background: var(--portal-surface-light);" in manual_guarded.group("declarations")
    assert "background: var(--portal-surface-soft);" in manual_status.group("declarations")
    assert "color: var(--portal-context);" in manual_code.group("declarations")


def test_light_music_library_keeps_private_metadata_and_guard_states_readable() -> None:
    """Music/SFX remains a readable private library, never a faux player or delivery flow."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    for marker in (
        'class="portal-music-library-intro"',
        'class="portal-music-library-read-badge"',
        'class="portal-music-library-filter"',
        'class="portal-music-library-card"',
        'class="portal-music-library-meta"',
        'class="portal-music-library-boundary"',
        "portal-music-library-guard",
    ):
        assert marker in PORTAL_CLIENT
    assert "Không mở player/preview" in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-music-library-intro",
            ".portal-music-library-filter",
            ".portal-music-library-card",
            ".portal-music-library-meta > div",
            ".portal-music-library-boundary",
            ".portal-music-library-guard",
        )
    )

    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-music-library-intro")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-music-library-intro h2")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-music-library-intro p")
    assert "background: var(--portal-surface-soft);" in declarations(".portal-page .portal-music-library-read-badge")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-music-library-board")
    assert "background: var(--portal-surface-soft);" in declarations(".portal-page .portal-music-library-filter")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-music-library-card")
    hover = declarations(".portal-page .portal-music-library-card:hover,\n.portal-page .portal-music-library-card:focus-within")
    assert "border-color: var(--portal-border-strong);" in hover
    assert "background: var(--portal-surface-soft);" in hover
    assert "transform: none;" in hover
    assert "color: var(--portal-action);" in declarations(".portal-page .portal-music-library-role")
    assert "color: var(--portal-warning);" in declarations(".portal-page .portal-music-library-favorite")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-music-library-card-copy h3")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-music-library-card-copy p")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-music-library-card-copy strong")
    assert "background: var(--portal-surface-soft);" in declarations(".portal-page .portal-music-library-meta > div")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-music-library-meta dt")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-music-library-meta dd")
    assert "color: var(--portal-context);" in declarations(".portal-page .portal-music-library-tags span")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-music-library-boundary")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-music-library-boundary strong")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-music-library-boundary span")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-music-library-guard")


def test_light_onboarding_keeps_optional_telegram_linking_clear_and_readable() -> None:
    """Onboarding must keep Web-first choice and signed Telegram linking equally legible."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    for marker in (
        'class="portal-onboarding-choice"',
        'class="portal-onboarding-steps"',
        'class="portal-onboarding-route"',
        'class="portal-onboarding-assurance"',
    ):
        assert marker in PORTAL_CLIENT
    assert "Web hoạt động độc lập" in PORTAL_CLIENT
    assert "Telegram là tùy chọn" in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-onboarding-action > .portal-notice",
            ".portal-onboarding-choice-icon",
            ".portal-onboarding-steps",
            ".portal-onboarding-route",
            ".portal-onboarding-page > .portal-onboarding-assurance",
        )
    )

    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-onboarding-action > .portal-notice")
    assert "background: var(--portal-surface-soft);" in declarations(".portal-page .portal-onboarding-action .portal-onboarding-choice-icon")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-onboarding-action .portal-onboarding-choice strong")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-onboarding-action .portal-onboarding-choice p")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-onboarding-steps")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-onboarding-steps li > span")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-onboarding-steps strong")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-onboarding-steps small")
    current = declarations(".portal-page .portal-onboarding-steps li[data-state=\"current\"]")
    assert "border-left-color: var(--portal-action);" in current
    assert "background: var(--portal-surface-soft);" in current
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-onboarding-route")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-onboarding-route strong")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-onboarding-route p")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-onboarding-page > .portal-onboarding-assurance")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-onboarding-page > .portal-onboarding-assurance > summary")


def test_light_account_security_keeps_signed_session_and_mfa_states_readable() -> None:
    """Account and MFA posture stay server-owned while their UI gains a clear light hierarchy."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    for marker in (
        'class="portal-settings-nav"',
        'class="portal-account-command"',
        "portal-account-session",
        'class="portal-security-posture"',
        'class="portal-security-posture-facts"',
        "portal-security-assurance",
    ):
        assert marker in PORTAL_CLIENT
    assert "Signed session hợp lệ" in PORTAL_CLIENT
    assert "Tình trạng bảo mật" in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-account-page .portal-settings-nav",
            ".portal-account-page .portal-account-command",
            ".portal-security-posture",
            ".portal-security-posture-facts > div",
            ".portal-account-security .portal-security-assurance",
        )
    )

    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-settings-nav")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-settings-nav a")
    current = declarations(".portal-page .portal-settings-nav a[aria-current=\"page\"]")
    assert "border-color: var(--portal-context);" in current
    assert "background: var(--portal-surface-soft);" in current
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-account-command")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-account-command-copy h2")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-account-command-copy p")
    assert "background: var(--portal-surface-soft);" in declarations(".portal-page .portal-account-command-facts > div")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-account-command-facts dt")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-account-command-facts dd")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-account-session")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-security-posture")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-security-posture-head h2")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-security-posture-head p")
    assert "background: var(--portal-surface-soft);" in declarations(".portal-page .portal-security-posture-facts > div")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-security-posture-facts small")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-security-posture-facts strong")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-security-posture-facts em")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-account-security .portal-security-assurance")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-account-security .portal-security-assurance summary")


def test_light_admin_home_keeps_erp_authority_and_work_queues_readable() -> None:
    """Admin ERP stays role-gated while its queues and disclosures use a calm light hierarchy."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    for marker in (
        "portal-admin-home",
        "portal-admin-guard",
        'class="portal-admin-work-queues"',
        'class="portal-admin-work-queue"',
        'class="portal-admin-authority"',
        "portal-admin-directory",
        'class="portal-admin-directory-group"',
    ):
        assert marker in PORTAL_CLIENT
    assert "Authority & ranh giới quản trị" in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-admin-home > .portal-admin-guard",
            ".portal-admin-work-queues",
            ".portal-admin-work-queue",
            ".portal-admin-authority",
            ".portal-admin-directory-group",
        )
    )

    guard = declarations(".portal-page .portal-admin-home > .portal-admin-guard")
    assert "border-color: var(--portal-warning);" in guard
    assert "background: var(--portal-surface-light);" in guard
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-admin-home > .portal-admin-guard .portal-state h2")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-admin-home > .portal-admin-guard .portal-state p")
    metric = declarations(".portal-page .portal-admin-home > .portal-admin-grid .portal-metric")
    assert "border-color: var(--portal-border);" in metric
    assert "background: var(--portal-surface-light);" in metric
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-admin-home > .portal-admin-grid .portal-metric strong")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-admin-work-queues")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-admin-work-queues .portal-section-heading h2")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-admin-work-queues .portal-section-heading p")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-admin-work-queue")
    queue_hover = declarations(".portal-page .portal-admin-work-queue:hover,\n.portal-page .portal-admin-work-queue:focus-visible")
    assert "background: var(--portal-surface-soft);" in queue_hover
    assert "transform: none;" in queue_hover
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-admin-work-queue strong")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-admin-work-queue small")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-admin-authority")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-admin-authority > summary")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-admin-authority > .portal-card")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-admin-directory-group")
    assert "color: var(--portal-ink);" in declarations(".portal-page .portal-admin-directory-group > summary")
    assert "color: var(--portal-muted);" in declarations(".portal-page .portal-admin-directory-group > summary small")
    assert "background: var(--portal-surface-soft);" in declarations(".portal-page .portal-admin-directory-group[open]")
    assert "background: var(--portal-surface-light);" in declarations(".portal-page .portal-admin-directory-group .portal-module-card")


def test_light_coordination_and_crm_surfaces_keep_private_workflows_readable() -> None:
    """Private handoff and CRM preserve their contracts while shedding dark legacy panels."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    workspace = (
        ".portal-page:is(.portal-coordination-workspace, .portal-coordination-detail, "
        ".portal-crm-workspace, .portal-crm-detail)"
    )
    for marker in (
        "portal-coordination-summary",
        "portal-coordination-card",
        "portal-crm-kanban",
        "portal-crm-lane",
        "portal-crm-card",
    ):
        assert marker in PORTAL_CLIENT
    assert "Internal human handoff only" in PORTAL_CLIENT
    assert "Odoo-style private pipeline" in PORTAL_CLIENT
    assert all(
        selector in PORTAL_CATALOGUE
        for selector in (
            ".portal-coordination-summary",
            ".portal-coordination-card",
            ".portal-crm-lane",
            ".portal-crm-card",
        )
    )

    summary = declarations(f"{workspace} .portal-coordination-summary")
    summary_primary = declarations(f"{workspace} .portal-coordination-summary :is(h2, dt)")
    summary_secondary = declarations(f"{workspace} .portal-coordination-summary :is(p, dd)")
    summary_metric = declarations(f"{workspace} .portal-coordination-summary dl > div")
    coordination_card = declarations(".portal-page .portal-coordination-card")
    coordination_hover = declarations(".portal-page .portal-coordination-card:hover")
    lane = declarations(".portal-page .portal-crm-lane")
    lane_header = declarations(".portal-page .portal-crm-lane header")
    lane_count = declarations(".portal-page .portal-crm-lane header span")
    crm_card = declarations(".portal-page .portal-crm-card")
    crm_card_hover = declarations(".portal-page .portal-crm-card:hover,\n.portal-page .portal-crm-card:focus-visible")
    crm_card_focus_match = re.search(
        r"(?<!\,\n)^\.portal-page \.portal-crm-card:focus-visible\s*\{(?P<declarations>.*?)\n\}",
        theme_source,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert crm_card_focus_match is not None
    crm_card_focus = crm_card_focus_match.group("declarations")
    crm_card_title = declarations(".portal-page .portal-crm-card b")
    crm_card_metadata = declarations(".portal-page .portal-crm-card :is(span, small, em)")

    assert "border-color: var(--portal-border);" in summary
    assert "background: var(--portal-surface-light);" in summary
    assert "color: var(--portal-ink);" in summary_primary
    assert "color: var(--portal-muted);" in summary_secondary
    assert "border-color: var(--portal-border);" in summary_metric
    assert "background: var(--portal-surface-soft);" in summary_metric
    assert "border-color: var(--portal-border);" in coordination_card
    assert "background: var(--portal-surface-light);" in coordination_card
    assert "border-color: var(--portal-border-strong);" in coordination_hover
    assert "background: var(--portal-surface-soft);" in coordination_hover
    assert "border-color: var(--portal-border);" in lane
    assert "background: var(--portal-surface-soft);" in lane
    assert "color: var(--portal-ink);" in lane_header
    assert "background: var(--portal-surface-light);" in lane_count
    assert "color: var(--portal-action);" in lane_count
    assert "border-color: var(--portal-border);" in crm_card
    assert "background: var(--portal-surface-light);" in crm_card
    assert "border-color: var(--portal-border-strong);" in crm_card_hover
    assert "background: var(--portal-light-hover-surface);" in crm_card_hover
    assert "outline: 3px solid var(--portal-focus) !important;" in crm_card_focus
    assert "outline-offset: 3px;" in crm_card_focus
    assert "color: var(--portal-ink);" in crm_card_title
    assert "color: var(--portal-muted);" in crm_card_metadata
    mobile_kanban = re.search(
        r"@media \(max-width: 740px\) \{\s*"
        r"\.portal-page \.portal-crm-kanban\s*\{(?P<declarations>.*?)\n\s*\}",
        theme_source,
        flags=re.DOTALL,
    )
    assert mobile_kanban is not None
    assert "grid-auto-columns: minmax(min(84vw, 308px), 1fr);" in mobile_kanban.group("declarations")
    assert "scroll-padding-inline: 1px;" in mobile_kanban.group("declarations")
    assert _contrast_ratio("#073a45", "#ffffff") >= 4.5
    assert _contrast_ratio("#456b77", "#ffffff") >= 4.5
    assert _contrast_ratio("#0f766e", "#ffffff") >= 4.5


def test_light_job_recovery_guide_keeps_admin_safety_guidance_readable() -> None:
    """The canonical-admin guide stays read-only while its legacy dark panels become light."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    guide = ".portal-page.portal-admin-job-recovery-guide"
    renderer_match = re.search(
        r"function renderAdminJobRecoveryGuide\(page, context\) \{(?P<body>.*?)\n  \}",
        PORTAL_CLIENT,
        flags=re.DOTALL,
    )
    assert renderer_match is not None
    renderer = renderer_match.group("body")

    assert "Job-Lock Recovery Safety Guide" in PORTAL_CLIENT
    assert "Không clear, retry hoặc refund" in renderer
    assert "Không điều khiển runtime" in renderer
    assert "Không có financial side effect" in renderer
    assert "data-portal-action" not in renderer
    assert "/admin/jobs" in renderer
    assert ".portal-job-recovery-card" in PORTAL_CATALOGUE
    assert ".portal-job-recovery-process li" in PORTAL_CATALOGUE
    assert ".portal-job-recovery-boundary li" in PORTAL_CATALOGUE

    intro = declarations(f"{guide} .portal-job-recovery-intro")
    card = declarations(f"{guide} .portal-job-recovery-card")
    card_icon = declarations(f"{guide} .portal-job-recovery-card-icon")
    heading_title = declarations(f"{guide} .portal-job-recovery-section .portal-section-heading h2")
    heading_body = declarations(f"{guide} .portal-job-recovery-section .portal-section-heading p")
    process_item = declarations(f"{guide} .portal-job-recovery-process li")
    boundary_item = declarations(f"{guide} .portal-job-recovery-boundary li")

    assert "border-color: var(--portal-border);" in intro
    assert "background: var(--portal-surface-light) !important;" in intro
    assert "border-color: var(--portal-border);" in card
    assert "background: var(--portal-surface-light);" in card
    assert "box-shadow: none;" in card
    assert "border-color: var(--portal-border-strong);" in card_icon
    assert "background: var(--portal-surface-soft);" in card_icon
    assert "color: var(--portal-ink);" in heading_title
    assert "color: var(--portal-muted);" in heading_body
    assert "border-color: var(--portal-border);" in process_item
    assert "background: var(--portal-surface-soft);" in process_item
    assert "border-color: var(--portal-border);" in boundary_item
    assert "background: var(--portal-surface-soft);" in boundary_item


def test_light_audio_asset_operations_keeps_private_utility_surfaces_readable() -> None:
    """Audio asset work stays owner-scoped while its operational surfaces become light and legible."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    route = ".portal-page.portal-audio-asset-operations"
    intro = declarations(f"{route} .portal-audio-assets-intro")
    form = declarations(f"{route} .portal-audio-assets-form")
    boundary = declarations(f"{route} .portal-audio-assets-boundary")
    history = declarations(f"{route} .portal-audio-assets-history")
    guard_row = declarations(f"{route} .portal-audio-assets-guard-list > span")
    pager = declarations(f"{route} .portal-audio-assets-source-pager")
    operation = declarations(f"{route} .portal-audio-asset-operation-list > li")
    empty = declarations(f"{route} .portal-audio-asset-empty")

    assert "border-color: var(--portal-border);" in intro
    assert "background: var(--portal-surface-light) !important;" in intro
    assert "box-shadow: none;" in intro
    assert "background: var(--portal-surface-light);" in form
    assert "background: var(--portal-surface-light);" in boundary
    assert "background: var(--portal-surface-light);" in history
    assert "background: var(--portal-surface-soft);" in guard_row
    assert "border-top-color: var(--portal-border);" in pager
    assert "color: var(--portal-muted);" in pager
    assert "background: var(--portal-surface-light);" in operation
    assert "background: var(--portal-surface-soft);" in empty
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-audio-assets-intro h2")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-audio-assets-intro p")
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-audio-assets-form label.portal-field")
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-audio-asset-operation-meta strong")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-audio-asset-operation-meta span")
    assert "color: var(--portal-context);" in declarations(f"{route} .portal-audio-asset-operation-meta small")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-audio-asset-operation-actions")
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-audio-asset-empty strong")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-audio-asset-empty span")
    assert not re.search(r"(?m)^\s*\.portal-audio-(?:assets|asset)-", theme_source)


def test_light_audio_production_hub_main_surface_keeps_authoring_boundaries_readable() -> None:
    """The main Hub becomes a calm workspace without changing its media authority."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    route = ".portal-page.portal-audio-hub"
    for marker in (
        "Audio production board",
        "Hub dùng collection Media Workspace đã có thay vì tạo thêm kho dữ liệu.",
        "Handoff có chủ đích",
        "Không có music generation, provider library, enhance, translate, mux/render, job, Xu hay payment",
    ):
        assert marker in PORTAL_CLIENT
    for selector in (
        ".portal-audio-hub-overview",
        ".portal-audio-hub-lanes li",
        ".portal-audio-hub-next-steps",
        ".portal-audio-hub-next-card",
        ".portal-media-create",
        ".portal-media-policy",
        ".portal-media-collection-card",
        ".portal-media-filter",
        ".portal-media-events > div",
    ):
        assert selector in PORTAL_CATALOGUE

    overview = declarations(f"{route} .portal-audio-hub-overview")
    lane = declarations(f"{route} .portal-audio-hub-lanes li")
    next_steps = declarations(f"{route} .portal-audio-hub-next-steps")
    next_card = declarations(f"{route} .portal-audio-hub-next-card")
    create = declarations(f"{route} .portal-media-create")
    policy = declarations(f"{route} .portal-media-policy")
    collection_card = declarations(f"{route} .portal-media-collection-card")
    collection_hover = declarations(f"{route} .portal-media-collection-card:hover,\n{route} .portal-media-collection-card:focus-visible")
    media_filter = declarations(f"{route} .portal-media-filter")
    event_row = declarations(f"{route} .portal-media-events > div")
    field_help = declarations(f"{route} .portal-field-help")
    policy_flag = declarations(f"{route} .portal-media-policy-flag")

    assert "border-color: var(--portal-border);" in overview
    assert "background: var(--portal-surface-light);" in overview
    assert "box-shadow: none;" in overview
    assert "background: var(--portal-surface-soft);" in lane
    assert "background: var(--portal-surface-light);" in next_steps
    assert "background: var(--portal-surface-light);" in next_card
    assert "background: var(--portal-surface-light);" in create
    assert "background: var(--portal-surface-soft);" in policy
    assert "background: var(--portal-surface-light);" in collection_card
    assert "border-color: var(--portal-border-strong);" in collection_hover
    assert "background: var(--portal-light-hover-surface);" in collection_hover
    assert "background: var(--portal-surface-soft);" in media_filter
    assert "border-top-color: var(--portal-border);" in event_row
    assert "color: var(--portal-muted);" in field_help
    assert "border-color: color-mix(in srgb, var(--portal-warning) 42%, var(--portal-border));" in policy_flag
    assert "background: color-mix(in srgb, var(--portal-warning) 8%, var(--portal-surface-light));" in policy_flag
    assert "color: var(--portal-warning);" in policy_flag
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-audio-hub-overview-copy h2")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-audio-hub-overview-copy p")
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-audio-hub-lanes strong")
    assert "color: var(--portal-action);" in declarations(f"{route} .portal-audio-hub-lanes b")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-audio-hub-lanes small")
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-audio-hub-next-card strong")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-audio-hub-next-card span")
    assert "color: var(--portal-ink);" in declarations(f"{route} .portal-media-policy .portal-project-steps strong")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-media-policy .portal-project-steps span")
    assert "color: var(--portal-muted);" in declarations(f"{route} .portal-media-events small")
    assert not re.search(r"(?m)^\s*\.portal-audio-hub(?!-detail)", theme_source)


def test_light_audio_production_hub_detail_keeps_review_and_change_requests_readable() -> None:
    """A private collection detail uses the same calm light system as its Hub."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    route = ".portal-page.portal-audio-hub-detail"
    for selector in (
        ".portal-media-detail-summary",
        ".portal-audio-hub-collection-board",
        ".portal-media-editor",
        ".portal-media-composer",
        ".portal-media-item-card",
        ".portal-audio-change-requests",
        ".portal-audio-change-request-row",
    ):
        assert selector in PORTAL_CATALOGUE
    assert "portal-audio-hub-review-pack" in PORTAL_CLIENT

    summary = declarations(f"{route} .portal-media-detail-summary")
    detail_surfaces = declarations(
        f"{route} .portal-audio-hub-collection-board,\n"
        f"{route} .portal-media-editor,\n"
        f"{route} .portal-media-item-card,\n"
        f"{route} .portal-audio-change-requests,\n"
        f"{route} .portal-audio-change-request-row"
    )
    review_pack = declarations(f"{route} :is(.portal-media-composer, .portal-media-detail-boundary, .portal-audio-hub-review-pack)")
    field_help = declarations(f"{route} :is(.portal-field-help, .portal-form-note)")
    field_label = declarations(f"{route} :is(.portal-media-attach-form, .portal-media-filter, .portal-media-editor, .portal-media-composer, .portal-media-detail-boundary, .portal-media-item-card, .portal-audio-change-request-form) label.portal-field > span")
    warning_stage = declarations(f'{route} .portal-audio-change-request-stage[data-stage="awaiting_confirmation"]')
    media_filter = declarations(f"{route} .portal-media-filter")
    pagination = declarations(f"{route} .portal-media-pagination")
    tags = declarations(f"{route} .portal-media-tags span")
    version_row = declarations(f"{route} .portal-version-row")
    version_title = declarations(f"{route} .portal-version-row strong")
    version_note = declarations(f"{route} .portal-version-row small")
    policy_notice = declarations(f"{route} .portal-notice--warning")
    staged = declarations(f"{route} .portal-field-staged")
    mobile_checkbox = re.search(
        rf"@media \(max-width: 700px\)\s*\{{(?P<rules>.*?{re.escape(route)} \.portal-media-checkbox\s*\{{.*?\n\}}.*?)\n\}}",
        theme_source,
        flags=re.DOTALL,
    )

    assert "border-color: var(--portal-border);" in summary
    assert "background: var(--portal-surface-light);" in summary
    assert "box-shadow: none;" in summary
    assert "background: var(--portal-surface-light);" in detail_surfaces
    assert "background: var(--portal-surface-soft);" in review_pack
    assert "color: var(--portal-muted);" in field_help
    assert "color: var(--portal-ink);" in field_label
    assert "border-color: color-mix(in srgb, var(--portal-warning) 42%, var(--portal-border));" in warning_stage
    assert "background: color-mix(in srgb, var(--portal-warning) 8%, var(--portal-surface-light));" in warning_stage
    assert "color: var(--portal-warning);" in warning_stage
    assert "background: var(--portal-surface-soft);" in media_filter
    assert "border-top-color: var(--portal-border);" in pagination
    assert "color: var(--portal-muted);" in pagination
    assert "background: var(--portal-surface-soft);" in tags
    assert "color: var(--portal-muted);" in tags
    assert "border-top-color: var(--portal-border);" in version_row
    assert "color: var(--portal-ink);" in version_title
    assert "color: var(--portal-muted);" in version_note
    assert "background: color-mix(in srgb, var(--portal-warning) 6%, var(--portal-surface-light));" in policy_notice
    assert "color: var(--portal-muted);" in staged
    assert mobile_checkbox is not None
    assert "min-height: 44px;" in mobile_checkbox.group("rules")
    assert not re.search(r"(?m)^\s*\.portal-audio-hub-detail", theme_source)


def test_light_music_prompt_composer_keeps_native_direction_receipts_readable() -> None:
    """Music planning receipts remain readable without implying audio delivery."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    route = ".portal-page.portal-music-prompt-composer"
    for selector in (
        ".portal-music-prompt-composer-intro",
        ".portal-music-prompt-composer-form",
        ".portal-music-prompt-composer-boundary",
        ".portal-music-prompt-composer-result",
        ".portal-music-prompt-composer-suggestions",
        ".portal-music-prompt-composer-usage",
        ".portal-music-prompt-composer-review",
    ):
        assert selector in PORTAL_CATALOGUE
    assert "function renderMusicPromptComposer(page, context)" in PORTAL_CLIENT

    intro = declarations(f"{route} .portal-music-prompt-composer-intro")
    form = declarations(f"{route} .portal-music-prompt-composer-form")
    boundary_and_result = declarations(
        f"{route} .portal-music-prompt-composer-boundary,\n"
        f"{route} .portal-music-prompt-composer-result"
    )
    suggestion_list = declarations(f"{route} .portal-music-prompt-composer-suggestions li")
    selected_suggestion = declarations(f'{route} .portal-music-prompt-composer-suggestions li[data-selected="true"]')
    usage = declarations(f"{route} .portal-music-prompt-composer-usage")
    review = declarations(f"{route} .portal-music-prompt-composer-review")
    intro_metric_label = declarations(f"{route} .portal-music-prompt-composer-intro dd")
    standard_field_label = declarations(
        f"{route} .portal-music-prompt-composer-form .portal-field > label"
    )
    receipt_copy = declarations(
        f"{route} :is(.portal-music-prompt-composer-suggestions dd, "
        ".portal-music-prompt-composer-suggestions pre, "
        ".portal-music-prompt-composer-usage p, "
        ".portal-music-prompt-composer-usage dd, "
        ".portal-music-prompt-composer-review p, "
        ".portal-music-prompt-composer-review li)"
    )

    assert "background: var(--portal-surface-light);" in intro
    assert "box-shadow: none;" in intro
    assert "background: var(--portal-surface-light);" in form
    assert "background: var(--portal-surface-soft);" in boundary_and_result
    assert "background: var(--portal-surface-light);" in suggestion_list
    assert "border-color: var(--portal-border-strong);" in selected_suggestion
    assert "background: var(--portal-light-hover-surface);" in selected_suggestion
    assert "background: var(--portal-surface-soft);" in usage
    assert "background: color-mix(in srgb, var(--portal-warning) 6%, var(--portal-surface-light));" in review
    assert "color: var(--portal-muted);" in intro_metric_label
    assert "font-size: 13px;" in intro_metric_label
    assert "color: var(--portal-ink);" in standard_field_label
    assert "font-size: 13px;" in standard_field_label
    assert "color: var(--portal-muted);" in receipt_copy
    assert "font-size: 13px;" in receipt_copy
    assert not re.search(r"(?m)^\s*\.portal-music-prompt-composer", theme_source)


def test_light_voice_direction_composer_keeps_text_only_receipts_readable() -> None:
    """Voice planning stays text-only while its receipt remains readable."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    route = ".portal-page.portal-voice-direction-composer"
    for selector in (
        ".portal-voice-direction-composer-intro",
        ".portal-voice-direction-composer-form",
        ".portal-voice-direction-composer-boundary",
        ".portal-voice-direction-composer-result",
        ".portal-voice-direction-composer-suggestions",
        ".portal-voice-direction-composer-delivery",
        ".portal-voice-direction-composer-review",
    ):
        assert selector in PORTAL_CATALOGUE
    assert "function renderVoiceDirectionComposer(page, context)" in PORTAL_CLIENT
    assert "web_native_deterministic_voice_direction_only" in PORTAL_CLIENT

    intro = declarations(f"{route} .portal-voice-direction-composer-intro")
    form = declarations(f"{route} .portal-voice-direction-composer-form")
    boundary_and_result = declarations(
        f"{route} .portal-voice-direction-composer-boundary,\n"
        f"{route} .portal-voice-direction-composer-result"
    )
    suggestion_list = declarations(f"{route} .portal-voice-direction-composer-suggestions li")
    selected_suggestion = declarations(
        f'{route} .portal-voice-direction-composer-suggestions li[data-selected="true"]'
    )
    delivery = declarations(f"{route} .portal-voice-direction-composer-delivery")
    review = declarations(f"{route} .portal-voice-direction-composer-review")
    intro_metric_label = declarations(f"{route} .portal-voice-direction-composer-intro dd")
    standard_field_label = declarations(
        f"{route} .portal-voice-direction-composer-form .portal-field > label"
    )
    guard_label = declarations(f"{route} .portal-voice-direction-composer-guard-list strong")
    guard_status = declarations(f"{route} .portal-voice-direction-composer-guard-list em")
    receipt_metadata = declarations(
        f"{route} :is(.portal-voice-direction-composer-meta, .portal-voice-direction-composer-tags) span"
    )
    suggestion_heading = declarations(
        f"{route} .portal-voice-direction-composer-suggestion-head strong"
    )
    receipt_field_label = declarations(
        f"{route} :is(.portal-voice-direction-composer-suggestions, .portal-voice-direction-composer-delivery) dt"
    )
    receipt_copy = declarations(
        f"{route} :is(.portal-voice-direction-composer-suggestions dd, "
        ".portal-voice-direction-composer-suggestions pre, "
        ".portal-voice-direction-composer-delivery p, "
        ".portal-voice-direction-composer-delivery dd, "
        ".portal-voice-direction-composer-review p, "
        ".portal-voice-direction-composer-review li)"
    )

    assert "background: var(--portal-surface-light);" in intro
    assert "box-shadow: none;" in intro
    assert "background: var(--portal-surface-light);" in form
    assert "background: var(--portal-surface-soft);" in boundary_and_result
    assert "background: var(--portal-surface-light);" in suggestion_list
    assert "border-color: var(--portal-border-strong);" in selected_suggestion
    assert "background: var(--portal-light-hover-surface);" in selected_suggestion
    assert "background: var(--portal-surface-soft);" in delivery
    assert "background: color-mix(in srgb, var(--portal-warning) 6%, var(--portal-surface-light));" in review
    assert "color: var(--portal-muted);" in intro_metric_label
    assert "font-size: 13px;" in intro_metric_label
    assert "color: var(--portal-ink);" in standard_field_label
    assert "font-size: 13px;" in standard_field_label
    assert "font-size: 13px;" in guard_label
    assert "font-size: 13px;" in guard_status
    assert "font-size: 13px;" in receipt_metadata
    assert "font-size: 13px;" in suggestion_heading
    assert "font-size: 13px;" in receipt_field_label
    assert "color: var(--portal-muted);" in receipt_copy
    assert "font-size: 13px;" in receipt_copy
    assert not re.search(r"(?m)^\s*\.portal-voice-direction-composer", theme_source)


def test_light_account_data_and_workspace_care_keep_private_actions_readable() -> None:
    """Privacy-facing account work keeps hierarchy readable on the light app shell."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    workspace_route = ".portal-page.portal-workspace-care"
    data_route = ".portal-page.portal-account-data-controls"
    for selector in (
        ".portal-workspace-care-intro",
        ".portal-workspace-care-status",
        ".portal-workspace-care-card",
        ".portal-workspace-care-boundary",
        ".portal-panel-row",
        ".portal-project-steps",
    ):
        assert selector in PORTAL_CATALOGUE
    assert "function renderWorkspaceCare(page, context)" in PORTAL_CLIENT
    assert "function renderAccountDataControls(page, context)" in PORTAL_CLIENT

    intro = declarations(f"{workspace_route} .portal-workspace-care-intro")
    status = declarations(f"{workspace_route} .portal-workspace-care-status")
    card = declarations(f"{workspace_route} .portal-workspace-care-card")
    card_hover = declarations(
        f"{workspace_route} .portal-workspace-care-card:hover,\n"
        f"{workspace_route} .portal-workspace-care-card:focus-visible"
    )
    card_meta = declarations(f"{workspace_route} .portal-workspace-care-card-copy small")
    card_copy = declarations(f"{workspace_route} .portal-workspace-care-card-copy > span")
    boundary_item = declarations(f"{workspace_route} .portal-workspace-care-boundary li")
    boundary_label = declarations(f"{workspace_route} .portal-workspace-care-boundary strong")
    boundary_copy = declarations(f"{workspace_route} .portal-workspace-care-boundary small")
    data_row = declarations(f"{data_route} .portal-panel-row")
    data_row_icon = declarations(f"{data_route} .portal-panel-row-icon")
    data_row_label = declarations(f"{data_route} .portal-panel-row strong")
    data_row_copy_selector = f"{data_route} .portal-panel-row > div > span:not(.portal-badge)"
    data_row_copy = declarations(data_row_copy_selector)
    data_step = declarations(f"{data_route} .portal-project-steps li")
    data_step_label = declarations(f"{data_route} .portal-project-steps strong")
    data_step_copy = declarations(f"{data_route} .portal-project-steps span")

    assert "background: var(--portal-surface-light);" in intro
    assert "box-shadow: none;" in intro
    assert "background: var(--portal-surface-soft);" in status
    assert "background: var(--portal-surface-light);" in card
    assert "box-shadow: none;" in card
    assert "background: var(--portal-light-hover-surface);" in card_hover
    assert "transform: none;" in card_hover
    assert "color: var(--portal-action);" in card_meta
    assert "font-size: 13px;" in card_meta
    assert "color: var(--portal-muted);" in card_copy
    assert "font-size: 13px;" in card_copy
    assert "background: var(--portal-surface-soft);" in boundary_item
    assert "color: var(--portal-ink);" in boundary_label
    assert "color: var(--portal-muted);" in boundary_copy
    assert "font-size: 13px;" in boundary_copy
    assert "background: var(--portal-surface-soft);" in data_row
    assert "color: var(--portal-action);" in data_row_icon
    assert "color: var(--portal-ink);" in data_row_label
    assert "color: var(--portal-muted);" in data_row_copy
    assert "font-size: 13px;" in data_row_copy
    assert f"{data_route} .portal-panel-row span {{" not in theme_source
    assert "border-top-color: var(--portal-border);" in data_step
    assert "color: var(--portal-ink);" in data_step_label
    assert "color: var(--portal-muted);" in data_step_copy
    assert "font-size: 13px;" in data_step_copy

    mobile_status = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(workspace_route)} \.portal-workspace-care-status\s*"
        rf"\{{(?P<declarations>.*?)\n\s*\}}\s*\}}",
        theme_source,
        flags=re.DOTALL,
    )
    assert mobile_status is not None
    assert "flex: 0 1 auto;" in mobile_status.group("declarations")


def test_light_image_operations_hub_keeps_artboard_review_readable() -> None:
    """Image Hub keeps its owner-scoped review surfaces on the shared light system."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            theme_source,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    hub_route = ".portal-page.portal-image-hub"
    detail_route = ".portal-page.portal-image-hub-detail"
    for selector in (
        ".portal-image-hub-overview",
        ".portal-image-hub-detail-board",
        ".portal-image-hub-next-steps",
        ".portal-image-hub-step",
        ".portal-image-studio-editor",
        ".portal-image-direction-create",
        ".portal-image-studio-estimate",
        ".portal-image-reference-library",
        ".portal-image-direction-card",
        ".portal-image-reference-picker",
    ):
        assert selector in PORTAL_CATALOGUE
    assert "function renderImageHubOverview(summary)" in PORTAL_CLIENT
    assert "function renderImageHubDetailBoard(artboard, directions)" in PORTAL_CLIENT
    assert "function renderImageStudioDetail(page, context)" in PORTAL_CLIENT

    overview = declarations(f"{hub_route} .portal-image-hub-overview")
    detail_board = declarations(f"{detail_route} .portal-image-hub-detail-board")
    detail_summary = declarations(f"{detail_route} .portal-image-studio-detail-summary")
    shared_heading = declarations(
        ".portal-page:is(.portal-image-hub, .portal-image-hub-detail) "
        ":is(.portal-image-hub-overview, .portal-image-hub-detail-board, "
        ".portal-image-studio-detail-summary) :is(h2, h3)"
    )
    shared_copy = declarations(
        ".portal-page:is(.portal-image-hub, .portal-image-hub-detail) "
        ":is(.portal-image-hub-overview, .portal-image-hub-detail-board, "
        ".portal-image-studio-detail-summary) p"
    )
    metric_cards = declarations(
        f"{hub_route} .portal-image-hub-overview dl > div,\n"
        f"{detail_route} .portal-image-hub-detail-board dl > div"
    )
    metric_copy = declarations(
        f"{hub_route} .portal-image-hub-overview dd,\n"
        f"{detail_route} .portal-image-hub-detail-board dd"
    )
    detail_summary_label = declarations(f"{detail_route} .portal-image-studio-detail-summary dt")
    detail_summary_value = declarations(f"{detail_route} .portal-image-studio-detail-summary dd")
    step_board = declarations(f"{hub_route} .portal-image-hub-next-steps")
    step = declarations(f"{hub_route} .portal-image-hub-step")
    step_hover = declarations(f"{hub_route} .portal-image-hub-step:hover")
    step_focus = declarations(f"{hub_route} .portal-image-hub-step:focus-visible")
    step_copy = declarations(f"{hub_route} .portal-image-hub-step span")
    hub_authoring_panels = declarations(
        f"{hub_route} :is(.portal-image-studio-create, .portal-image-studio-boundary, "
        ".portal-image-studio-filter, .portal-image-artboard-card, "
        ".portal-image-reference-library, .portal-image-reference-picker)"
    )
    hub_artboard_hover = declarations(f"{hub_route} .portal-image-artboard-card:hover")
    hub_metadata = declarations(
        f"{hub_route} .portal-image-artboard-meta span,\n"
        f"{hub_route} .portal-image-studio-tags span"
    )
    authoring_panels = declarations(
        f"{detail_route} :is(.portal-image-studio-editor, .portal-image-direction-create, "
        ".portal-image-studio-estimate, .portal-image-studio-activity, "
        ".portal-image-reference-library, .portal-image-reference-picker)"
    )
    direction_card = declarations(f"{detail_route} .portal-image-direction-card")
    direction_card_hover = declarations(f"{detail_route} .portal-image-direction-card:hover")
    direction_metadata = declarations(
        f"{detail_route} .portal-image-direction-meta span,\n"
        f"{detail_route} .portal-image-studio-tags span"
    )
    reference_item = declarations(
        ".portal-page:is(.portal-image-hub, .portal-image-hub-detail) "
        ".portal-image-reference-list > :is(li, article, a, button)"
    )
    guard = declarations(
        ".portal-page:is(.portal-image-hub, .portal-image-hub-detail) "
        ".portal-image-studio-guard-list span"
    )
    guard_label = declarations(
        ".portal-page:is(.portal-image-hub, .portal-image-hub-detail) "
        ".portal-image-studio-guard-list strong"
    )
    guard_status = declarations(
        ".portal-page:is(.portal-image-hub, .portal-image-hub-detail) "
        ".portal-image-studio-guard-list em"
    )
    estimate = declarations(f"{detail_route} .portal-image-studio-estimate-grid span")
    activity_copy = declarations(f"{detail_route} .portal-image-studio-events small")
    pagination = declarations(
        ".portal-page:is(.portal-image-hub, .portal-image-hub-detail) "
        ":is(.portal-image-studio-pagination, .portal-image-reference-pagination)"
    )
    mobile_metrics = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(f'{hub_route} .portal-image-hub-overview dl,')}\s*"
        rf"{re.escape(f'{detail_route} .portal-image-hub-detail-board dl')}\s*"
        rf"\{{(?P<declarations>.*?)\n\s*\}}\s*\}}",
        theme_source,
        flags=re.DOTALL,
    )

    assert "background: var(--portal-surface-light);" in overview
    assert "box-shadow: none;" in overview
    assert "background: var(--portal-surface-light);" in detail_board
    assert "box-shadow: none;" in detail_board
    assert "background: var(--portal-surface-light) !important;" in detail_summary
    assert "box-shadow: none;" in detail_summary
    assert "color: var(--portal-ink);" in shared_heading
    assert "color: var(--portal-muted);" in shared_copy
    assert "background: var(--portal-surface-soft);" in metric_cards
    assert "color: var(--portal-muted);" in metric_copy
    assert "font-size: 13px;" in metric_copy
    assert "color: var(--portal-muted);" in detail_summary_label
    assert "color: var(--portal-ink);" in detail_summary_value
    assert "font-size: 13px;" in detail_summary_value
    assert "background: var(--portal-surface-light);" in step_board
    assert "background: var(--portal-surface-light);" in step
    assert "box-shadow: none;" in step
    assert "background: var(--portal-light-hover-surface);" in step_hover
    assert "transform: none;" in step_hover
    assert "outline: 3px solid var(--portal-focus) !important;" in step_focus
    assert "color: var(--portal-muted);" in step_copy
    assert "font-size: 13px;" in step_copy
    assert "background: var(--portal-surface-light);" in hub_authoring_panels
    assert "box-shadow: none;" in hub_authoring_panels
    assert "background: var(--portal-light-hover-surface);" in hub_artboard_hover
    assert "transform: none;" in hub_artboard_hover
    assert "background: var(--portal-surface-soft);" in hub_metadata
    assert "font-size: 13px;" in hub_metadata
    assert "background: var(--portal-surface-light);" in authoring_panels
    assert "box-shadow: none;" in authoring_panels
    assert "background: var(--portal-surface-light);" in direction_card
    assert "background: var(--portal-light-hover-surface);" in direction_card_hover
    assert "transform: none;" in direction_card_hover
    assert "background: var(--portal-surface-soft);" in direction_metadata
    assert "font-size: 13px;" in direction_metadata
    assert "background: var(--portal-surface-soft);" in reference_item
    assert "background: var(--portal-surface-soft);" in guard
    assert "color: var(--portal-ink);" in guard_label
    assert "background: color-mix(in srgb, var(--portal-action) 8%, var(--portal-surface-light));" in guard_status
    assert "background: var(--portal-surface-soft);" in estimate
    assert "color: var(--portal-muted);" in activity_copy
    assert "font-size: 13px;" in activity_copy
    assert "border-color: var(--portal-border);" in pagination
    assert "color: var(--portal-muted);" in pagination
    assert "font-size: 13px;" in pagination
    assert mobile_metrics is not None
    assert "grid-template-columns: repeat(auto-fit, minmax(142px, 1fr));" in mobile_metrics.group("declarations")


def test_light_chat_workspace_final_surface_keeps_private_authoring_readable() -> None:
    """The Chat routes end with their own scoped light-surface override layer."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light AI Chat Workspace surface \*/(?P<css>.*)\Z",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    chat_css = layer.group("css")
    route = ".portal-page:is(.portal-chat-workspace, .portal-chat-workspace-detail)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            chat_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    authoring_surfaces = declarations(
        f"{route} :is(.portal-chat-workspace-create, .portal-chat-workspace-boundary, "
        ".portal-chat-workspace-filters, .portal-chat-context-card, .portal-chat-turn, "
        ".portal-chat-version-list > article, .portal-chat-event-list > div, "
        ".portal-chat-execution, .portal-chat-execution-layout > section, .portal-chat-run-card)"
    )
    guard_surface = declarations(f"{route} .portal-chat-workspace-guard-list span")
    guard_label = declarations(f"{route} .portal-chat-workspace-guard-list strong")
    guard_status = declarations(f"{route} .portal-chat-workspace-guard-list em")
    thread = declarations(f"{route} .portal-chat-thread-card")
    thread_hover = declarations(f"{route} .portal-chat-thread-card:hover")
    metadata = declarations(
        f"{route} :is(.portal-chat-workspace-meta span, .portal-chat-workspace-tags span, "
        ".portal-chat-workspace-pagination, .portal-chat-turn small, .portal-chat-version-list small, "
        ".portal-chat-event-list small, .portal-chat-run-card small)"
    )
    context_copy = declarations(f"{route} .portal-chat-context-card > p")
    execution_status = declarations(f"{route} .portal-chat-execution-status > span")
    execution_status_label = declarations(f"{route} .portal-chat-execution-status strong")
    execution_status_value = declarations(f"{route} .portal-chat-execution-status em")
    card_titles = declarations(f"{route} .portal-card-title")
    primary_text = declarations(
        f"{route} :is(.portal-chat-execution-heading, .portal-chat-run-card h3, "
        ".portal-chat-version-list strong, .portal-chat-event-list strong)"
    )
    thread_summary_label = declarations(f"{route} .portal-chat-thread-summary dt")
    secondary_text = declarations(
        f"{route} :is(.portal-chat-turn p, .portal-chat-version-list p, .portal-chat-run-card p, "
        ".portal-card-subtitle, .portal-form-note)"
    )
    event_dot = declarations(f"{route} .portal-chat-event-list > div > span:first-child")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        chat_css,
        flags=re.DOTALL,
    )

    assert "border-color: var(--portal-border);" in authoring_surfaces
    assert "background: var(--portal-surface-light);" in authoring_surfaces
    assert "box-shadow: none;" in authoring_surfaces
    assert "background: var(--portal-surface-soft);" in guard_surface
    assert "color: var(--portal-ink);" in guard_label
    assert "font-size: 13px;" in guard_label
    assert "color: var(--portal-muted);" in guard_status
    assert "font-size: 13px;" in guard_status
    assert "background: var(--portal-surface-light);" in thread
    assert "background: var(--portal-light-hover-surface);" in thread_hover
    assert "transform: none;" in thread_hover
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "font-size: 13px;" in metadata
    assert "color: var(--portal-muted);" in context_copy
    assert "font-size: 13px;" in context_copy
    assert "background: var(--portal-surface-soft);" in execution_status
    assert "color: var(--portal-ink);" in execution_status_label
    assert "font-size: 13px;" in execution_status_label
    assert "color: var(--portal-muted);" in execution_status_value
    assert "font-size: 13px;" in execution_status_value
    assert "color: var(--portal-ink);" in card_titles
    assert "font-size: 16px;" in card_titles
    assert "color: var(--portal-ink);" in primary_text
    assert "font-size: 13px;" in primary_text
    assert "font-size: 13px;" in thread_summary_label
    assert "color: var(--portal-muted);" in secondary_text
    assert "font-size: 13px;" in secondary_text
    assert "background: var(--portal-action);" in event_dot
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-chat-workspace-intro dl" in mobile_selectors
    assert ".portal-chat-thread-summary dl" in mobile_selectors
    assert ".portal-chat-execution-status" in mobile_selectors
    assert ".portal-chat-execution-layout" in mobile_selectors
    assert ".portal-chat-workspace-guard-list" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")


def test_light_document_workspace_final_surface_keeps_private_planning_readable() -> None:
    """Document planning stays truthful while its signed surfaces use the light app system."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Document & PDF Workspace surface \*/(?P<css>.*)\Z",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    document_css = layer.group("css")
    route = ".portal-page:is(.portal-document-workspace, .portal-document-workspace-detail)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            document_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(
        f"{route} :is(.portal-document-workspace-intro, .portal-document-workspace-detail-summary)"
    )
    summary_heading = declarations(
        f"{route} :is(.portal-document-workspace-intro, .portal-document-workspace-detail-summary) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-document-workspace-intro, .portal-document-workspace-detail-summary) p"
    )
    summary_metric = declarations(
        f"{route} :is(.portal-document-workspace-intro, .portal-document-workspace-detail-summary) dl > div"
    )
    summary_label = declarations(
        f"{route} :is(.portal-document-workspace-intro dd, .portal-document-workspace-detail-summary dt)"
    )
    summary_value = declarations(f"{route} .portal-document-workspace-detail-summary dd")
    authoring_surfaces = declarations(
        f"{route} :is(.portal-document-workspace-create, .portal-document-workspace-editor, "
        ".portal-document-plan-create, .portal-document-workspace-boundary, "
        ".portal-document-workspace-estimate, .portal-document-workspace-activity, "
        ".portal-document-plan-card, .portal-document-plan-handoff, "
        ".portal-document-plan-version-list > article, .portal-document-version-list > article, "
        ".portal-document-workspace-events > div)"
    )
    guard_surface = declarations(f"{route} .portal-document-workspace-guard-list span")
    guard_label = declarations(f"{route} .portal-document-workspace-guard-list strong")
    guard_status = declarations(f"{route} .portal-document-workspace-guard-list em")
    brief_card = declarations(f"{route} .portal-document-workspace-card")
    brief_card_hover = declarations(f"{route} .portal-document-workspace-card:hover")
    metadata = declarations(
        f"{route} :is(.portal-document-workspace-meta span, .portal-document-plan-meta span, "
        ".portal-document-workspace-tags span, .portal-document-workspace-pagination)"
    )
    estimate = declarations(f"{route} .portal-document-workspace-estimate-grid span")
    estimate_value = declarations(f"{route} .portal-document-workspace-estimate-grid strong")
    primary_text = declarations(
        f"{route} :is(.portal-document-plan-handoff h4, .portal-document-plan-version-list strong, "
        ".portal-document-version-list strong, .portal-document-workspace-events strong)"
    )
    secondary_text = declarations(
        f"{route} :is(.portal-document-plan-handoff p, .portal-document-plan-handoff small, "
        ".portal-document-plan-version-list small, .portal-document-version-list p, "
        ".portal-document-version-list small, .portal-document-workspace-events small, "
        ".portal-card-subtitle, .portal-form-note)"
    )
    event_dot = declarations(f"{route} .portal-document-workspace-events > div > span:first-child")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        document_css,
        flags=re.DOTALL,
    )

    assert "background: var(--portal-surface-light);" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "font-size: 14px;" in summary_copy
    assert "background: var(--portal-surface-soft);" in summary_metric
    assert "color: var(--portal-muted);" in summary_label
    assert "font-size: 13px;" in summary_label
    assert "color: var(--portal-ink);" in summary_value
    assert "font-size: 13px;" in summary_value
    assert "border-color: var(--portal-border);" in authoring_surfaces
    assert "background: var(--portal-surface-light);" in authoring_surfaces
    assert "box-shadow: none;" in authoring_surfaces
    assert "background: var(--portal-surface-soft);" in guard_surface
    assert "color: var(--portal-ink);" in guard_label
    assert "font-size: 13px;" in guard_label
    assert "background: var(--portal-surface-light);" in guard_status
    assert "color: var(--portal-muted);" in guard_status
    assert "font-size: 13px;" in guard_status
    assert "background: var(--portal-surface-light);" in brief_card
    assert "background: var(--portal-light-hover-surface);" in brief_card_hover
    assert "transform: none;" in brief_card_hover
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "font-size: 13px;" in metadata
    assert "background: var(--portal-surface-soft);" in estimate
    assert "color: var(--portal-muted);" in estimate
    assert "font-size: 13px;" in estimate
    assert "color: var(--portal-ink);" in estimate_value
    assert "color: var(--portal-ink);" in primary_text
    assert "font-size: 13px;" in primary_text
    assert "color: var(--portal-muted);" in secondary_text
    assert "font-size: 13px;" in secondary_text
    assert "background: var(--portal-action);" in event_dot
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-document-workspace-intro dl" in mobile_selectors
    assert ".portal-document-workspace-detail-summary dl" in mobile_selectors
    assert ".portal-document-workspace-estimate-grid" in mobile_selectors
    assert ".portal-document-workspace-guard-list" in mobile_selectors
    assert ".portal-document-workspace-layout" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")


def test_light_analytics_workspace_final_surface_keeps_manual_measurement_readable() -> None:
    """Manual Analytics records retain truthfulness while leaving the legacy dark palette behind."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Analytics Workspace surface \*/(?P<css>.*)\Z",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    analytics_css = layer.group("css")
    route = ".portal-page:is(.portal-analytics-workspace, .portal-analytics-workspace-detail)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            analytics_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(f"{route} :is(.portal-analytics-intro, .portal-analytics-detail-summary)")
    summary_heading = declarations(
        f"{route} :is(.portal-analytics-intro, .portal-analytics-detail-summary) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-analytics-intro, .portal-analytics-detail-summary) p"
    )
    summary_metric = declarations(
        f"{route} :is(.portal-analytics-intro, .portal-analytics-detail-summary) dl > div"
    )
    summary_metric_value = declarations(f"{route} .portal-analytics-intro dt")
    summary_label = declarations(
        f"{route} :is(.portal-analytics-intro dd, .portal-analytics-detail-summary dt)"
    )
    summary_value = declarations(f"{route} .portal-analytics-detail-summary dd")
    authoring_surfaces = declarations(
        f"{route} :is(.portal-analytics-create, .portal-analytics-editor, "
        ".portal-analytics-metric-create, .portal-analytics-finding-create, "
        ".portal-analytics-boundary, .portal-analytics-activity, .portal-analytics-filters, "
        ".portal-analytics-metric-card, .portal-analytics-finding-card, "
        ".portal-analytics-snapshot-create, .portal-analytics-snapshot-card)"
    )
    guard_surface = declarations(f"{route} .portal-analytics-guard-list span")
    guard_label = declarations(f"{route} .portal-analytics-guard-list strong")
    guard_status = declarations(f"{route} .portal-analytics-guard-list em")
    report_card = declarations(f"{route} .portal-analytics-report-card")
    report_hover = declarations(f"{route} .portal-analytics-report-card:hover")
    metadata = declarations(
        f"{route} :is(.portal-analytics-meta span, .portal-analytics-tags span, "
        ".portal-analytics-references span)"
    )
    filters = declarations(f"{route} .portal-analytics-filters")
    pagination = declarations(f"{route} .portal-analytics-pagination")
    form_dividers = declarations(
        f"{route} :is(.portal-analytics-metric-form, .portal-analytics-finding-form, "
        ".portal-analytics-snapshot-form)"
    )
    version_row = declarations(f"{route} .portal-analytics-version-list > article")
    comparison = declarations(f"{route} .portal-analytics-comparison")
    comparison_item = declarations(f"{route} .portal-analytics-comparison > div")
    comparison_label = declarations(f"{route} .portal-analytics-comparison span")
    comparison_value = declarations(f"{route} .portal-analytics-comparison strong")
    comparison_copy = declarations(f"{route} .portal-analytics-comparison p")
    archived_card = declarations(
        f"{route} :is(.portal-analytics-metric-card, .portal-analytics-finding-card, "
        ".portal-analytics-snapshot-card).is-archived"
    )
    empty_state = declarations(f"{route} .portal-empty")
    empty_icon = declarations(f"{route} .portal-empty-icon")
    empty_heading = declarations(f"{route} .portal-empty h3")
    empty_copy = declarations(f"{route} .portal-empty p")
    snapshot_heading = declarations(f"{route} .portal-analytics-snapshot-card h4")
    primary_text = declarations(
        f"{route} :is(.portal-analytics-version-list strong, .portal-analytics-event-list strong)"
    )
    secondary_text = declarations(
        f"{route} :is(.portal-analytics-snapshot-note, .portal-analytics-finding-body, "
        ".portal-analytics-version-list p, .portal-analytics-version-list small, "
        ".portal-analytics-event-list small, .portal-card-subtitle, .portal-form-note)"
    )
    event_dot = declarations(f"{route} .portal-analytics-event-list > div > span:first-child")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        analytics_css,
        flags=re.DOTALL,
    )

    assert "background: var(--portal-surface-light);" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "font-size: 14px;" in summary_copy
    assert "background: var(--portal-surface-soft);" in summary_metric
    assert "color: var(--portal-action);" in summary_metric_value
    assert "color: var(--portal-muted);" in summary_label
    assert "font-size: 13px;" in summary_label
    assert "color: var(--portal-ink);" in summary_value
    assert "font-size: 13px;" in summary_value
    assert "border-color: var(--portal-border);" in authoring_surfaces
    assert "background: var(--portal-surface-light);" in authoring_surfaces
    assert "box-shadow: none;" in authoring_surfaces
    assert "background: var(--portal-surface-soft);" in guard_surface
    assert "color: var(--portal-ink);" in guard_label
    assert "font-size: 13px;" in guard_label
    assert "background: var(--portal-surface-light);" in guard_status
    assert "color: var(--portal-muted);" in guard_status
    assert "font-size: 13px;" in guard_status
    assert "background: var(--portal-surface-light);" in report_card
    assert "background: var(--portal-light-hover-surface);" in report_hover
    assert "transform: none;" in report_hover
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "font-size: 13px;" in metadata
    assert "background: var(--portal-surface-light);" in filters
    assert "border-color: var(--portal-border);" in pagination
    assert "color: var(--portal-muted);" in pagination
    assert "font-size: 13px;" in pagination
    assert "border-top-color: var(--portal-border);" in form_dividers
    assert "border-color: var(--portal-border);" in version_row
    assert "background: var(--portal-surface-soft);" in comparison
    assert "background: var(--portal-surface-light);" in comparison_item
    assert "color: var(--portal-muted);" in comparison_label
    assert "font-size: 13px;" in comparison_label
    assert "color: var(--portal-ink);" in comparison_value
    assert "font-size: 13px;" in comparison_value
    assert "color: var(--portal-muted);" in comparison_copy
    assert "font-size: 13px;" in comparison_copy
    assert "background: var(--portal-surface-soft);" in archived_card
    assert "opacity: 1;" in archived_card
    assert "border-color: var(--portal-border);" in empty_state
    assert "background: var(--portal-surface-soft);" in empty_state
    assert "background: color-mix(in srgb, var(--portal-action) 8%, var(--portal-surface-light));" in empty_icon
    assert "color: var(--portal-action);" in empty_icon
    assert "color: var(--portal-ink);" in empty_heading
    assert "font-size: 16px;" in empty_heading
    assert "color: var(--portal-muted);" in empty_copy
    assert "font-size: 13px;" in empty_copy
    assert "color: var(--portal-ink);" in snapshot_heading
    assert "font-size: 16px;" in snapshot_heading
    assert "color: var(--portal-ink);" in primary_text
    assert "font-size: 13px;" in primary_text
    assert "color: var(--portal-muted);" in secondary_text
    assert "font-size: 13px;" in secondary_text
    assert "background: var(--portal-action);" in event_dot
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-analytics-intro dl" in mobile_selectors
    assert ".portal-analytics-detail-summary dl" in mobile_selectors
    assert ".portal-analytics-guard-list" in mobile_selectors
    assert ".portal-analytics-layout" in mobile_selectors
    assert ".portal-analytics-report-grid" in mobile_selectors
    assert ".portal-analytics-comparison" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")


def test_light_subtitle_studio_final_surface_keeps_authored_cues_readable() -> None:
    """Authored transcript work remains truthful while using the shared light app system."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Subtitle Studio surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    subtitle_css = layer.group("css")
    route = ".portal-page:is(.portal-subtitle-studio, .portal-subtitle-studio-detail)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            subtitle_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(
        f"{route} :is(.portal-subtitle-studio-intro, .portal-subtitle-studio-detail-summary)"
    )
    summary_heading = declarations(
        f"{route} :is(.portal-subtitle-studio-intro, .portal-subtitle-studio-detail-summary) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-subtitle-studio-intro, .portal-subtitle-studio-detail-summary) p"
    )
    summary_metric = declarations(
        f"{route} :is(.portal-subtitle-studio-intro, .portal-subtitle-studio-detail-summary) dl > div"
    )
    summary_metric_value = declarations(f"{route} .portal-subtitle-studio-intro dt")
    summary_label = declarations(
        f"{route} :is(.portal-subtitle-studio-intro dd, .portal-subtitle-studio-detail-summary dt)"
    )
    summary_value = declarations(f"{route} .portal-subtitle-studio-detail-summary dd")
    authoring_surfaces = declarations(
        f"{route} :is(.portal-subtitle-studio-create, .portal-subtitle-studio-editor, "
        ".portal-subtitle-cue-create, .portal-subtitle-studio-boundary, "
        ".portal-subtitle-runtime-estimate, .portal-subtitle-studio-activity, "
        ".portal-subtitle-text-preview)"
    )
    source = declarations(f"{route} .portal-subtitle-language-source")
    source_guarded = declarations(f"{route} .portal-subtitle-language-source.is-guarded")
    source_facts = declarations(f"{route} .portal-subtitle-language-source-facts span")
    source_pager = declarations(f"{route} .portal-subtitle-language-source-pager")
    guard_surface = declarations(f"{route} .portal-subtitle-studio-guard-list span")
    guard_label = declarations(f"{route} .portal-subtitle-studio-guard-list strong")
    guard_status = declarations(f"{route} .portal-subtitle-studio-guard-list em")
    project_card = declarations(f"{route} .portal-subtitle-project-card")
    project_hover = declarations(f"{route} .portal-subtitle-project-card:hover")
    metadata = declarations(
        f"{route} :is(.portal-subtitle-project-meta span, .portal-subtitle-cue-meta span, "
        ".portal-subtitle-studio-tags span)"
    )
    estimate = declarations(f"{route} .portal-subtitle-estimate-grid span")
    estimate_value = declarations(f"{route} .portal-subtitle-estimate-grid strong")
    cue_card = declarations(f"{route} .portal-subtitle-cue-card")
    cue_archived = declarations(f"{route} .portal-subtitle-cue-card.is-archived")
    cue_translation = declarations(f"{route} .portal-subtitle-cue-translation")
    cue_dividers = declarations(
        f"{route} :is(.portal-subtitle-cue-form, .portal-subtitle-cue-history)"
    )
    version_row = declarations(f"{route} .portal-subtitle-version-list > article")
    preview = declarations(f"{route} .portal-subtitle-preview-text")
    primary_text = declarations(
        f"{route} :is(.portal-subtitle-cue-history > strong, .portal-subtitle-version-list strong, "
        ".portal-subtitle-studio-events strong)"
    )
    secondary_text = declarations(
        f"{route} :is(.portal-subtitle-cue-history > div, .portal-subtitle-cue-history em, "
        ".portal-subtitle-version-list p, .portal-subtitle-version-list small, "
        ".portal-subtitle-studio-events small, .portal-card-subtitle, .portal-form-note)"
    )
    event_dot = declarations(f"{route} .portal-subtitle-studio-events > div > span:first-child")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        subtitle_css,
        flags=re.DOTALL,
    )

    assert "border-color: var(--portal-border);" in summary
    assert "background: var(--portal-surface-light);" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "font-size: clamp(24px, 2.4vw, 32px);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "font-size: 14px;" in summary_copy
    assert "background: var(--portal-surface-soft);" in summary_metric
    assert "color: var(--portal-action);" in summary_metric_value
    assert "color: var(--portal-muted);" in summary_label
    assert "font-size: 13px;" in summary_label
    assert "color: var(--portal-ink);" in summary_value
    assert "font-size: 13px;" in summary_value
    assert "border-color: var(--portal-border);" in authoring_surfaces
    assert "background: var(--portal-surface-light);" in authoring_surfaces
    assert "box-shadow: none;" in authoring_surfaces
    assert "background: var(--portal-surface-soft);" in source
    assert "background: var(--portal-surface-soft);" in source_guarded
    assert "border-color: var(--portal-border);" in source_facts
    assert "background: var(--portal-surface-light);" in source_facts
    assert "border-color: var(--portal-border);" in source_pager
    assert "color: var(--portal-muted);" in source_pager
    assert "background: var(--portal-surface-soft);" in guard_surface
    assert "color: var(--portal-ink);" in guard_label
    assert "font-size: 13px;" in guard_label
    assert "background: var(--portal-surface-light);" in guard_status
    assert "color: var(--portal-muted);" in guard_status
    assert "font-size: 13px;" in guard_status
    assert "border-color: var(--portal-border);" in project_card
    assert "background: var(--portal-surface-light);" in project_card
    assert "background: var(--portal-light-hover-surface);" in project_hover
    assert "transform: none;" in project_hover
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "font-size: 13px;" in metadata
    assert "background: var(--portal-surface-soft);" in estimate
    assert "color: var(--portal-muted);" in estimate
    assert "font-size: 13px;" in estimate
    assert "color: var(--portal-ink);" in estimate_value
    assert "border-color: var(--portal-border);" in cue_card
    assert "background: var(--portal-surface-light);" in cue_card
    assert "background: var(--portal-surface-soft);" in cue_archived
    assert "opacity: 1;" in cue_archived
    assert "color: var(--portal-muted);" in cue_translation
    assert "border-top-color: var(--portal-border);" in cue_dividers
    assert "border-color: var(--portal-border);" in version_row
    assert "border-color: var(--portal-border);" in preview
    assert "background: var(--portal-surface-soft);" in preview
    assert "color: var(--portal-ink);" in primary_text
    assert "font-size: 13px;" in primary_text
    assert "color: var(--portal-muted);" in secondary_text
    assert "font-size: 13px;" in secondary_text
    assert "background: var(--portal-action);" in event_dot
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-subtitle-studio-intro dl" in mobile_selectors
    assert ".portal-subtitle-studio-detail-summary dl" in mobile_selectors
    assert ".portal-subtitle-studio-guard-list" in mobile_selectors
    assert ".portal-subtitle-studio-layout" in mobile_selectors
    assert ".portal-subtitle-studio-detail-grid" in mobile_selectors
    assert ".portal-subtitle-project-grid" in mobile_selectors
    assert ".portal-subtitle-cue-grid" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")


def test_light_content_studio_final_surface_keeps_private_authoring_readable() -> None:
    """Content briefs retain readable, owner-scoped authoring surfaces on the light app system."""

    content_detail = re.search(
        r"function renderContentStudioDetail\(page, context\).*?"
        r'return `<article class="(?P<classes>[^"]*)"',
        PORTAL_CLIENT,
        flags=re.DOTALL,
    )
    channel_strategy_detail = re.search(
        r"function renderChannelStrategyDetail\(page, context\).*?"
        r'return `<article class="(?P<classes>[^"]*)"',
        PORTAL_CLIENT,
        flags=re.DOTALL,
    )

    assert content_detail is not None
    assert channel_strategy_detail is not None
    assert "portal-content-studio-workspace-detail" in content_detail.group("classes")
    assert "portal-content-studio-workspace-detail" not in channel_strategy_detail.group("classes")

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Content Studio surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    content_css = layer.group("css")
    route = (
        ".portal-page:is(.portal-content-operations-board, "
        ".portal-content-studio-authoring, .portal-content-studio-workspace-detail)"
    )

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            content_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(
        f"{route} :is(.portal-content-operations-summary, "
        ".portal-content-operations-authoring-intro, .portal-content-studio-detail-summary)"
    )
    summary_heading = declarations(
        f"{route} :is(.portal-content-operations-summary, "
        ".portal-content-operations-authoring-intro, .portal-content-studio-detail-summary) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-content-operations-summary, "
        ".portal-content-operations-authoring-intro, .portal-content-studio-detail-summary) p"
    )
    summary_metric = declarations(
        f"{route} :is(.portal-content-operations-summary, "
        ".portal-content-studio-detail-summary) dl > div"
    )
    summary_metric_value = declarations(f"{route} .portal-content-operations-summary dt")
    summary_label = declarations(
        f"{route} :is(.portal-content-operations-summary dd, "
        ".portal-content-studio-detail-summary dt)"
    )
    summary_value = declarations(f"{route} .portal-content-studio-detail-summary dd")
    surfaces = declarations(
        f"{route} :is(.portal-content-operations-primary, .portal-content-operations-kinds, "
        ".portal-content-operations-briefs, .portal-content-operations-activity-card, "
        ".portal-content-operations-boundary, .portal-content-studio-create, "
        ".portal-content-studio-policy, .portal-content-studio-editor, "
        ".portal-content-variant-create, .portal-content-studio-activity)"
    )
    field_label = declarations(f"{route} .portal-field > label")
    metadata = declarations(
        f"{route} :is(.portal-content-studio-meta span, .portal-content-studio-tags span, "
        ".portal-content-selected)"
    )
    selected_variant = declarations(f"{route} .portal-content-variant-card.is-selected")
    policy_step = declarations(f"{route} .portal-content-studio-policy .portal-project-steps li")
    policy_heading = declarations(
        f"{route} .portal-content-studio-policy .portal-project-steps strong"
    )
    policy_copy = declarations(f"{route} .portal-content-studio-policy .portal-project-steps span")
    dividers = declarations(
        f"{route} :is(.portal-content-variant-form, .portal-content-variant-history)"
    )
    history_row = declarations(f"{route} .portal-content-variant-history > div")
    version_row = declarations(f"{route} .portal-content-version-list > article")
    activity_row = declarations(f"{route} .portal-content-activity-list > div")
    primary_text = declarations(
        f"{route} :is(.portal-content-variant-history > strong, "
        ".portal-content-version-list strong, .portal-content-activity-list strong)"
    )
    secondary_text = declarations(
        f"{route} :is(.portal-content-variant-history > div, "
        ".portal-content-variant-history em, .portal-content-version-list p, "
        ".portal-content-version-list small, .portal-content-activity-list small, "
        ".portal-card-subtitle, .portal-form-note, .portal-content-studio-pagination)"
    )
    hover = declarations(
        f"{route} :is(.portal-content-operations-kind-card, .portal-content-studio-card):hover"
    )
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        content_css,
        flags=re.DOTALL,
    )

    assert route in content_css
    assert "border-color: var(--portal-border);" in summary
    assert "background: var(--portal-surface-light) !important;" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "border-color: var(--portal-border);" in summary_metric
    assert "background: var(--portal-surface-soft);" in summary_metric
    assert "color: var(--portal-action);" in summary_metric_value
    assert "color: var(--portal-muted);" in summary_label
    assert "color: var(--portal-ink);" in summary_value
    assert "border-color: var(--portal-border);" in surfaces
    assert "background: var(--portal-surface-light);" in surfaces
    assert "box-shadow: none;" in surfaces
    assert "color: var(--portal-ink);" in field_label
    assert "font-size: 13px;" in field_label
    assert "border-color: var(--portal-border);" in metadata
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "font-size: 13px;" in metadata
    assert "border-color: var(--portal-border-strong);" in selected_variant
    assert "background: var(--portal-surface-soft);" in selected_variant
    assert "border-top-color: var(--portal-border);" in policy_step
    assert "color: var(--portal-ink);" in policy_heading
    assert "color: var(--portal-muted);" in policy_copy
    assert "border-top-color: var(--portal-border);" in dividers
    assert "border-top-color: var(--portal-border);" in history_row
    assert "border-color: var(--portal-border);" in version_row
    assert "border-top-color: var(--portal-border);" in activity_row
    assert "color: var(--portal-ink);" in primary_text
    assert "font-size: 13px;" in primary_text
    assert "color: var(--portal-muted);" in secondary_text
    assert "font-size: 13px;" in secondary_text
    assert "border-color: var(--portal-border-strong);" in hover
    assert "background: var(--portal-light-hover-surface);" in hover
    assert "box-shadow: none;" in hover
    assert "transform: none;" in hover
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-content-operations-summary dl" in mobile_selectors
    assert ".portal-content-studio-detail-summary dl" in mobile_selectors
    assert ".portal-content-operations-workspace" in mobile_selectors
    assert ".portal-content-operations-boundary-grid" in mobile_selectors
    assert ".portal-content-operations-kind-grid" in mobile_selectors
    assert ".portal-content-operations-authoring-layout" in mobile_selectors
    assert ".portal-content-studio-detail-grid" in mobile_selectors
    assert ".portal-content-studio-history-grid" in mobile_selectors
    assert ".portal-content-studio-grid" in mobile_selectors
    assert ".portal-content-variant-grid" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")
    assert not re.search(r"(?:#[0-9a-f]{3,8}\b|(?:linear|radial)-gradient|rgba?\()", content_css, re.I)
    assert not re.search(r"var\(--(?!portal-)", content_css)


def test_light_voice_studio_final_surface_keeps_direction_and_consent_readable() -> None:
    """Voice direction stays truthful while the old orange/dark shell is removed."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Voice Studio surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    voice_css = layer.group("css")
    route = ".portal-page:is(.portal-voice-studio, .portal-voice-studio-detail)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            voice_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(
        f"{route} :is(.portal-voice-studio-intro, .portal-voice-studio-detail-summary)"
    )
    summary_heading = declarations(
        f"{route} :is(.portal-voice-studio-intro, .portal-voice-studio-detail-summary) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-voice-studio-intro, .portal-voice-studio-detail-summary) p"
    )
    summary_metric = declarations(
        f"{route} :is(.portal-voice-studio-intro, .portal-voice-studio-detail-summary) dl > div"
    )
    summary_metric_value = declarations(f"{route} .portal-voice-studio-intro dt")
    summary_label = declarations(
        f"{route} :is(.portal-voice-studio-intro dd, .portal-voice-studio-detail-summary dt)"
    )
    summary_value = declarations(f"{route} .portal-voice-studio-detail-summary dd")
    authoring_surfaces = declarations(
        f"{route} :is(.portal-voice-studio-create, .portal-voice-studio-editor, "
        ".portal-voice-script-create, .portal-voice-studio-policy, "
        ".portal-voice-studio-composer, .portal-voice-studio-activity, "
        ".portal-voice-studio-boundary)"
    )
    field_label = declarations(f"{route} .portal-field > label")
    guard_surface = declarations(f"{route} .portal-voice-studio-guard-list span")
    guard_label = declarations(f"{route} .portal-voice-studio-guard-list strong")
    guard_status = declarations(f"{route} .portal-voice-studio-guard-list em")
    vault_card = declarations(f"{route} .portal-voice-vault-card")
    vault_hover = declarations(f"{route} .portal-voice-vault-card:hover")
    default_vault = declarations(f"{route} .portal-voice-vault-card.is-default")
    script_card = declarations(f"{route} .portal-voice-script-card")
    metadata = declarations(
        f"{route} :is(.portal-voice-vault-meta span, .portal-voice-script-meta span, "
        ".portal-voice-studio-tags span, .portal-voice-reference-list span)"
    )
    default_tag = declarations(f"{route} .portal-voice-default")
    policy_flag = declarations(f"{route} .portal-voice-policy-flag")
    filter_surface = declarations(f"{route} .portal-voice-studio-filter")
    pagination = declarations(f"{route} .portal-voice-studio-pagination")
    cue_sheet = declarations(f"{route} .portal-voice-cue-sheet")
    cue_heading = declarations(f"{route} .portal-voice-cue-sheet h4")
    cue_copy = declarations(f"{route} .portal-voice-cue-sheet p")
    cue_metadata = declarations(f"{route} .portal-voice-cue-metrics span")
    cue_row = declarations(f"{route} .portal-voice-cue-sheet li")
    cue_index = declarations(f"{route} .portal-voice-cue-sheet li > span")
    cue_timing = declarations(f"{route} :is(.portal-voice-cue-sheet time, .portal-voice-cue-sheet small)")
    dividers = declarations(f"{route} :is(.portal-voice-script-form, .portal-voice-script-history)")
    history_row = declarations(f"{route} .portal-voice-script-history > div")
    version_row = declarations(f"{route} .portal-voice-version-list > article")
    primary_text = declarations(
        f"{route} :is(.portal-voice-script-history > strong, .portal-voice-version-list strong, "
        ".portal-voice-studio-events strong)"
    )
    secondary_text = declarations(
        f"{route} :is(.portal-voice-script-history > div, .portal-voice-script-history em, "
        ".portal-voice-version-list p, .portal-voice-version-list small, "
        ".portal-voice-studio-events small, .portal-card-subtitle, .portal-form-note)"
    )
    event_row = declarations(f"{route} .portal-voice-studio-events > div")
    event_dot = declarations(f"{route} .portal-voice-studio-events > div > span:first-child")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        voice_css,
        flags=re.DOTALL,
    )

    assert route in voice_css
    assert "border-color: var(--portal-border);" in summary
    assert "background: var(--portal-surface-light) !important;" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "font-size: clamp(24px, 2.4vw, 32px);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "font-size: 14px;" in summary_copy
    assert "background: var(--portal-surface-soft);" in summary_metric
    assert "color: var(--portal-action);" in summary_metric_value
    assert "color: var(--portal-muted);" in summary_label
    assert "font-size: 13px;" in summary_label
    assert "color: var(--portal-ink);" in summary_value
    assert "font-size: 13px;" in summary_value
    assert "border-color: var(--portal-border);" in authoring_surfaces
    assert "background: var(--portal-surface-light);" in authoring_surfaces
    assert "box-shadow: none;" in authoring_surfaces
    assert "color: var(--portal-ink);" in field_label
    assert "font-size: 13px;" in field_label
    assert "background: var(--portal-surface-soft);" in guard_surface
    assert "color: var(--portal-ink);" in guard_label
    assert "font-size: 13px;" in guard_label
    assert "background: var(--portal-surface-light);" in guard_status
    assert "color: var(--portal-muted);" in guard_status
    assert "font-size: 13px;" in guard_status
    assert "background: var(--portal-surface-light);" in vault_card
    assert "box-shadow: none;" in vault_card
    assert "background: var(--portal-light-hover-surface);" in vault_hover
    assert "transform: none;" in vault_hover
    assert "border-color: var(--portal-border-strong);" in default_vault
    assert "background: var(--portal-surface-soft);" in default_vault
    assert "background: var(--portal-surface-light);" in script_card
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "font-size: 13px;" in metadata
    assert "color: var(--portal-action);" in default_tag
    assert "color: var(--portal-danger);" in policy_flag
    assert "background: var(--portal-surface-light);" in filter_surface
    assert "border-color: var(--portal-border);" in pagination
    assert "color: var(--portal-muted);" in pagination
    assert "font-size: 13px;" in pagination
    assert "background: var(--portal-surface-soft);" in cue_sheet
    assert "color: var(--portal-ink);" in cue_heading
    assert "color: var(--portal-muted);" in cue_copy
    assert "font-size: 13px;" in cue_copy
    assert "background: var(--portal-surface-light);" in cue_metadata
    assert "border-top-color: var(--portal-border);" in cue_row
    assert "background: var(--portal-action);" in cue_index
    assert "font-size: 12px;" in cue_index
    assert "color: var(--portal-muted);" in cue_timing
    assert "font: 12px/1.5 var(--portal-mono" in cue_timing
    assert "border-top-color: var(--portal-border);" in dividers
    assert "border-top-color: var(--portal-border);" in history_row
    assert "border-color: var(--portal-border);" in version_row
    assert "color: var(--portal-ink);" in primary_text
    assert "font-size: 13px;" in primary_text
    assert "color: var(--portal-muted);" in secondary_text
    assert "font-size: 13px;" in secondary_text
    assert "border-top-color: var(--portal-border);" in event_row
    assert "background: var(--portal-action);" in event_dot
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-voice-studio-intro dl" in mobile_selectors
    assert ".portal-voice-studio-detail-summary dl" in mobile_selectors
    assert ".portal-voice-studio-guard-list" in mobile_selectors
    assert ".portal-voice-studio-layout" in mobile_selectors
    assert ".portal-voice-studio-detail-grid" in mobile_selectors
    assert ".portal-voice-vault-grid" in mobile_selectors
    assert ".portal-voice-script-grid" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")
    assert not re.search(r"(?:#[0-9a-f]{3,8}\b|(?:linear|radial)-gradient|rgba?\()", voice_css, re.I)
    assert not re.search(r"var\(--(?!portal-)", voice_css)


def test_light_image_studio_final_surface_keeps_artboards_truthful_and_readable() -> None:
    """Image Studio remains metadata-only while artboards use the shared light surface."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Image Studio surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    image_css = layer.group("css")
    route = ".portal-page:is(.portal-image-studio, .portal-image-studio-detail)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            image_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(
        f"{route} :is(.portal-image-studio-intro, .portal-image-studio-detail-summary)"
    )
    summary_heading = declarations(
        f"{route} :is(.portal-image-studio-intro, .portal-image-studio-detail-summary) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-image-studio-intro, .portal-image-studio-detail-summary) p"
    )
    summary_metric = declarations(
        f"{route} :is(.portal-image-studio-intro, .portal-image-studio-detail-summary) dl > div"
    )
    summary_metric_value = declarations(f"{route} .portal-image-studio-intro dt")
    summary_label = declarations(
        f"{route} :is(.portal-image-studio-intro dd, .portal-image-studio-detail-summary dt)"
    )
    summary_value = declarations(f"{route} .portal-image-studio-detail-summary dd")
    authoring_surfaces = declarations(
        f"{route} :is(.portal-image-studio-create, .portal-image-studio-editor, "
        ".portal-image-direction-create, .portal-image-studio-estimate, "
        ".portal-image-reference-library, .portal-image-reference-picker, "
        ".portal-image-studio-activity, .portal-image-studio-boundary)"
    )
    field_label = declarations(f"{route} .portal-field > label")
    estimate = declarations(f"{route} .portal-image-studio-estimate-grid span")
    artboard_card = declarations(f"{route} .portal-image-artboard-card")
    direction_card = declarations(f"{route} .portal-image-direction-card")
    card_title = declarations(
        f"{route} :is(.portal-image-artboard-card, .portal-image-direction-card) .portal-card-title"
    )
    card_copy = declarations(
        f"{route} :is(.portal-image-artboard-card, .portal-image-direction-card) .portal-card-subtitle"
    )
    hover = declarations(
        f"{route} :is(.portal-image-artboard-card, .portal-image-direction-card, "
        ".portal-image-reference-list > :is(a, button)):hover"
    )
    archived_direction = declarations(f"{route} .portal-image-direction-card.is-archived")
    metadata = declarations(
        f"{route} :is(.portal-image-artboard-meta span, .portal-image-direction-meta span, "
        ".portal-image-studio-tags span)"
    )
    selected_metadata = declarations(f"{route} .portal-image-direction-history em")
    guard_surface = declarations(f"{route} .portal-image-studio-guard-list span")
    guard_label = declarations(f"{route} .portal-image-studio-guard-list strong")
    guard_status = declarations(f"{route} .portal-image-studio-guard-list em")
    reference_row = declarations(
        f"{route} .portal-image-reference-list > :is(li, article, a, button)"
    )
    reference_title = declarations(f"{route} .portal-image-reference-list strong")
    reference_copy = declarations(f"{route} .portal-image-reference-list small")
    unavailable_reference = declarations(
        f"{route} .portal-image-reference-list > .is-unavailable strong"
    )
    filter_surface = declarations(
        f"{route} :is(.portal-image-studio-filter, .portal-image-reference-filter)"
    )
    pagination = declarations(
        f"{route} :is(.portal-image-studio-pagination, .portal-image-reference-pagination)"
    )
    dividers = declarations(
        f"{route} :is(.portal-image-direction-form, .portal-image-direction-history)"
    )
    history_row = declarations(f"{route} .portal-image-direction-history > div")
    version_row = declarations(f"{route} .portal-image-version-list > article")
    activity_row = declarations(f"{route} .portal-image-studio-events > div")
    primary_text = declarations(
        f"{route} :is(.portal-image-direction-history > strong, .portal-image-version-list strong, "
        ".portal-image-studio-events strong)"
    )
    secondary_text = declarations(
        f"{route} :is(.portal-image-direction-history > div, .portal-image-version-list p, "
        ".portal-image-version-list small, .portal-image-studio-events small, "
        ".portal-card-subtitle, .portal-form-note)"
    )
    event_dot = declarations(f"{route} .portal-image-studio-events > div > span:first-child")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        image_css,
        flags=re.DOTALL,
    )

    selector_lines = re.findall(r"(?m)^\s*(?!@)(?P<selector>[^\n{}]+)\s*\{", image_css)
    assert selector_lines
    assert all(selector.startswith(route) for selector in selector_lines)
    assert route in image_css
    assert ".portal-image-hub" not in image_css
    assert "border-color: var(--portal-border);" in summary
    assert "background: var(--portal-surface-light) !important;" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "font-size: clamp(24px, 2.4vw, 32px);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "font-size: 14px;" in summary_copy
    assert "border-color: var(--portal-border);" in summary_metric
    assert "background: var(--portal-surface-soft);" in summary_metric
    assert "color: var(--portal-action);" in summary_metric_value
    assert "color: var(--portal-muted);" in summary_label
    assert "font-size: 13px;" in summary_label
    assert "color: var(--portal-ink);" in summary_value
    assert "font-size: 13px;" in summary_value
    assert "border-color: var(--portal-border);" in authoring_surfaces
    assert "background: var(--portal-surface-light);" in authoring_surfaces
    assert "box-shadow: none;" in authoring_surfaces
    assert "color: var(--portal-ink);" in field_label
    assert "font-size: 13px;" in field_label
    assert "background: var(--portal-surface-soft);" in estimate
    assert "color: var(--portal-muted);" in estimate
    assert "font-size: 13px;" in estimate
    assert "background: var(--portal-surface-light);" in artboard_card
    assert "box-shadow: none;" in artboard_card
    assert "background: var(--portal-surface-light);" in direction_card
    assert "box-shadow: none;" in direction_card
    assert "color: var(--portal-ink);" in card_title
    assert "color: var(--portal-muted);" in card_copy
    assert "font-size: 13px;" in card_copy
    assert "border-color: var(--portal-border-strong);" in hover
    assert "background: var(--portal-light-hover-surface);" in hover
    assert "box-shadow: none;" in hover
    assert "transform: none;" in hover
    assert "background: var(--portal-surface-soft);" in archived_direction
    assert "color: var(--portal-muted);" in archived_direction
    assert "opacity: 1;" in archived_direction
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "font-size: 13px;" in metadata
    assert "color: var(--portal-action);" in selected_metadata
    assert "font-size: 13px;" in selected_metadata
    assert "background: var(--portal-surface-soft);" in guard_surface
    assert "color: var(--portal-ink);" in guard_label
    assert "font-size: 13px;" in guard_label
    assert "background: var(--portal-surface-light);" in guard_status
    assert "color: var(--portal-action);" in guard_status
    assert "font-size: 13px;" in guard_status
    assert "background: var(--portal-surface-soft);" in reference_row
    assert "color: var(--portal-ink);" in reference_title
    assert "color: var(--portal-muted);" in reference_copy
    assert "font-size: 13px;" in reference_copy
    assert "color: var(--portal-danger);" in unavailable_reference
    assert "background: var(--portal-surface-light);" in filter_surface
    assert "border-color: var(--portal-border);" in pagination
    assert "color: var(--portal-muted);" in pagination
    assert "font-size: 13px;" in pagination
    assert "border-top-color: var(--portal-border);" in dividers
    assert "border-top-color: var(--portal-border);" in history_row
    assert "border-color: var(--portal-border);" in version_row
    assert "border-top-color: var(--portal-border);" in activity_row
    assert "color: var(--portal-ink);" in primary_text
    assert "font-size: 13px;" in primary_text
    assert "color: var(--portal-muted);" in secondary_text
    assert "font-size: 13px;" in secondary_text
    assert "background: var(--portal-action);" in event_dot
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-image-studio-intro dl" in mobile_selectors
    assert ".portal-image-studio-detail-summary dl" in mobile_selectors
    assert ".portal-image-studio-layout" in mobile_selectors
    assert ".portal-image-studio-detail-grid" in mobile_selectors
    assert ".portal-image-studio-history-grid" in mobile_selectors
    assert ".portal-image-artboard-grid" in mobile_selectors
    assert ".portal-image-direction-grid" in mobile_selectors
    assert ".portal-image-reference-library-grid" in mobile_selectors
    assert ".portal-image-studio-estimate-grid" in mobile_selectors
    assert ".portal-image-studio-guard-list" in mobile_selectors
    assert ".portal-image-direction-form .portal-fields" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")
    assert not re.search(r"(?:#[0-9a-f]{3,8}\b|(?:linear|radial)-gradient|rgba?\()", image_css, re.I)
    assert not re.search(r"var\(--(?!portal-)", image_css)


def test_light_music_sfx_final_surface_keeps_audio_planning_truthful_and_readable() -> None:
    """Music planning stays explicit while legacy dark audio panels become light workspace surfaces."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Music and SFX surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    music_css = layer.group("css")
    route = ".portal-page:is(.portal-music-library, .portal-music-prompt-composer, .portal-music-directions, .portal-sfx-cue-sheet)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            music_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(
        f"{route} :is(.portal-music-library-intro, .portal-music-prompt-composer-intro, "
        ".portal-music-directions-intro, .portal-sfx-cue-sheet-intro)"
    )
    summary_heading = declarations(
        f"{route} :is(.portal-music-library-intro, .portal-music-prompt-composer-intro, "
        ".portal-music-directions-intro, .portal-sfx-cue-sheet-intro) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-music-library-intro, .portal-music-prompt-composer-intro, "
        ".portal-music-directions-intro, .portal-sfx-cue-sheet-intro) p"
    )
    metrics = declarations(
        f"{route} :is(.portal-music-prompt-composer-intro, .portal-music-directions-intro, "
        ".portal-sfx-cue-sheet-intro) dl > div"
    )
    metric_value = declarations(
        f"{route} :is(.portal-music-prompt-composer-intro, .portal-music-directions-intro, "
        ".portal-sfx-cue-sheet-intro) dt"
    )
    working_surfaces = declarations(
        f"{route} :is(.portal-music-library-board, .portal-music-library-filter, .portal-music-library-guard, "
        ".portal-music-library-boundary, .portal-music-prompt-composer-form, "
        ".portal-music-prompt-composer-boundary, .portal-music-prompt-composer-result, "
        ".portal-music-directions-form, .portal-music-directions-boundary, "
        ".portal-music-directions-result, .portal-sfx-cue-sheet-form, "
        ".portal-sfx-cue-sheet-boundary, .portal-sfx-cue-sheet-result)"
    )
    library_card = declarations(f"{route} .portal-music-library-card")
    library_hover = declarations(f"{route} .portal-music-library-card:hover")
    picker_card = declarations(
        f"{route} :is(.portal-music-directions-preset-card, .portal-sfx-cue-sheet-preset-card)"
    )
    picker_selected = declarations(
        f"{route} :is(.portal-music-directions-preset-card, .portal-sfx-cue-sheet-preset-card)[data-selected=\"true\"]"
    )
    guard_surface = declarations(
        f"{route} :is(.portal-music-prompt-composer-guard-list span, "
        ".portal-music-directions-guard-list span, .portal-sfx-cue-sheet-guard-list span)"
    )
    guard_status = declarations(
        f"{route} :is(.portal-music-prompt-composer-guard-list em, "
        ".portal-music-directions-guard-list em, .portal-sfx-cue-sheet-guard-list em)"
    )
    metadata = declarations(
        f"{route} :is(.portal-music-prompt-composer-meta span, .portal-music-prompt-composer-tags span, "
        ".portal-music-directions-meta span, .portal-sfx-cue-sheet-meta span, .portal-music-library-tags span)"
    )
    direction_rows = declarations(
        f"{route} :is(.portal-music-prompt-composer-suggestions li, .portal-music-directions-list li, "
        ".portal-sfx-cue-sheet-list li)"
    )
    detail_cells = declarations(
        f"{route} :is(.portal-music-prompt-composer-suggestions dl > div, "
        ".portal-music-prompt-composer-usage > dl > div, .portal-music-directions-list dl > div, "
        ".portal-sfx-cue-sheet-list dl > div)"
    )
    selected_direction = declarations(f"{route} .portal-music-prompt-composer-suggestions li[data-selected=\"true\"]")
    review = declarations(
        f"{route} :is(.portal-music-prompt-composer-review, .portal-music-directions-review, .portal-sfx-cue-sheet-review)"
    )
    review_heading = declarations(
        f"{route} :is(.portal-music-prompt-composer-review, .portal-music-directions-review, .portal-sfx-cue-sheet-review) strong"
    )
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        music_css,
        flags=re.DOTALL,
    )

    selector_lines = re.findall(r"(?m)^\s*(?!@)(?P<selector>[^\n{}]+)\s*\{", music_css)
    assert selector_lines
    assert all(selector.startswith(route) for selector in selector_lines)
    assert "background: var(--portal-surface-light) !important;" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "background: var(--portal-surface-soft);" in metrics
    assert "color: var(--portal-action);" in metric_value
    assert "background: var(--portal-surface-light);" in working_surfaces
    assert "box-shadow: none;" in working_surfaces
    assert "background: var(--portal-surface-light);" in library_card
    assert "background: var(--portal-light-hover-surface);" in library_hover
    assert "transform: none;" in library_hover
    assert "background: var(--portal-surface-light);" in picker_card
    assert "border-color: var(--portal-border-strong);" in picker_selected
    assert "background: var(--portal-surface-soft);" in picker_selected
    assert "background: var(--portal-surface-soft);" in guard_surface
    assert "background: var(--portal-surface-light);" in guard_status
    assert "color: var(--portal-action);" in guard_status
    assert "background: var(--portal-surface-soft);" in metadata
    assert "color: var(--portal-muted);" in metadata
    assert "background: var(--portal-surface-light);" in direction_rows
    assert "border-color: var(--portal-border);" in detail_cells
    assert "background: var(--portal-surface-light);" in detail_cells
    assert "border-color: var(--portal-border-strong);" in selected_direction
    assert "background: var(--portal-light-hover-surface);" in selected_direction
    assert "background: var(--portal-surface-soft);" in review
    assert "color: var(--portal-warning);" in review_heading
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-music-library-grid" in mobile_selectors
    assert ".portal-music-prompt-composer-layout" in mobile_selectors
    assert ".portal-music-directions-layout" in mobile_selectors
    assert ".portal-sfx-cue-sheet-layout" in mobile_selectors
    assert ".portal-music-directions-preset-grid" in mobile_selectors
    assert ".portal-sfx-cue-sheet-preset-grid" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")
    assert not re.search(r"(?:#[0-9a-f]{3,8}\b|(?:linear|radial)-gradient|rgba?\()", music_css, re.I)
    assert not re.search(r"var\(--(?!portal-)", music_css)


def test_light_project_center_final_surface_keeps_authoring_and_history_readable() -> None:
    """Private Project authoring stays explicit while its final surface becomes light and legible."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Project Center surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    project_css = layer.group("css")
    route = ".portal-page:is(.portal-project-center, .portal-project-center-authoring, .portal-project-detail)"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            project_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    summary = declarations(
        f"{route} :is(.portal-project-operations-summary, .portal-project-operations-authoring-intro, .portal-project-summary)"
    )
    summary_heading = declarations(
        f"{route} :is(.portal-project-operations-summary, .portal-project-operations-authoring-intro, .portal-project-summary) h2"
    )
    summary_copy = declarations(
        f"{route} :is(.portal-project-operations-summary, .portal-project-operations-authoring-intro, .portal-project-summary) p"
    )
    operation_metrics = declarations(f"{route} .portal-project-operations-summary dl > div")
    operation_metric_value = declarations(f"{route} .portal-project-operations-summary dt")
    detail_metrics = declarations(f"{route} .portal-project-summary dl > div")
    detail_metric_value = declarations(f"{route} .portal-project-summary dd")
    working_panels = declarations(
        f"{route} :is(.portal-project-operations-primary, .portal-project-operations-library, "
        ".portal-project-operations-boundary, .portal-project-operations-create)"
    )
    filter_panel = declarations(f"{route} .portal-project-filter")
    pagination = declarations(f"{route} .portal-project-pagination")
    project_card = declarations(f"{route} .portal-project-card")
    document_row = declarations(f"{route} .portal-project-document")
    document_text = declarations(f"{route} :is(.portal-project-document strong, .portal-project-editor .portal-card-title)")
    document_metadata = declarations(f"{route} .portal-project-document small")
    step_row = declarations(f"{route} .portal-project-steps li")
    step_title = declarations(f"{route} .portal-project-steps strong")
    step_copy = declarations(f"{route} .portal-project-steps span")
    step_marker = declarations(f"{route} .portal-project-steps li::before")
    authoring_regions = declarations(f"{route} :is(.portal-project-new-document, .portal-project-history)")
    editor = declarations(f"{route} .portal-project-editor")
    version_list = declarations(f"{route} .portal-version-list")
    version_row = declarations(f"{route} .portal-version-row")
    package_panel = declarations(f"{route} :is(.portal-project-package-panel, .portal-project-package-actions)")
    package_card = declarations(f"{route} .portal-project-package-card")
    package_meta = declarations(f"{route} .portal-project-package-meta > div")
    package_metadata = declarations(f"{route} :is(.portal-project-package-meta dt, .portal-project-package-meta dd)")
    hover = declarations(f"{route} :is(.portal-project-card, .portal-project-document, .portal-project-package-card):hover")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        project_css,
        flags=re.DOTALL,
    )

    selector_lines = re.findall(r"(?m)^\s*(?!@)(?P<selector>[^\n{}]+)\s*\{", project_css)
    assert selector_lines
    assert all(selector.startswith(route) for selector in selector_lines)
    assert "background: var(--portal-surface-light) !important;" in summary
    assert "box-shadow: none;" in summary
    assert "color: var(--portal-ink);" in summary_heading
    assert "color: var(--portal-muted);" in summary_copy
    assert "background: var(--portal-surface-soft);" in operation_metrics
    assert "color: var(--portal-action);" in operation_metric_value
    assert "background: var(--portal-surface-soft);" in detail_metrics
    assert "color: var(--portal-ink);" in detail_metric_value
    assert "background: var(--portal-surface-light);" in working_panels
    assert "border-color: var(--portal-border);" in working_panels
    assert "box-shadow: none;" in working_panels
    assert "background: var(--portal-surface-light);" in filter_panel
    assert "color: var(--portal-muted);" in pagination
    assert "background: var(--portal-surface-light);" in project_card
    assert "background: var(--portal-surface-light);" in document_row
    assert "color: var(--portal-ink);" in document_text
    assert "color: var(--portal-muted);" in document_metadata
    assert "border-top-color: var(--portal-border);" in step_row
    assert "color: var(--portal-ink);" in step_title
    assert "font-size: 13px;" in step_title
    assert "color: var(--portal-muted);" in step_copy
    assert "font-size: 13px;" in step_copy
    assert "background: var(--portal-action);" in step_marker
    assert "box-shadow: none;" in step_marker
    assert "border-top-color: var(--portal-border);" in authoring_regions
    assert "background: var(--portal-surface-light);" in editor
    assert "background: var(--portal-surface-soft);" in version_list
    assert "border-color: var(--portal-border);" in version_row
    assert "background: var(--portal-surface-light);" in package_panel
    assert "background: var(--portal-surface-light);" in package_card
    assert "background: var(--portal-surface-soft);" in package_meta
    assert "color: var(--portal-muted);" in package_metadata
    assert "border-color: var(--portal-border-strong);" in hover
    assert "background: var(--portal-light-hover-surface);" in hover
    assert "transform: none;" in hover
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-project-operations-summary" in mobile_selectors
    assert ".portal-project-operations-authoring-intro" in mobile_selectors
    assert ".portal-project-operations-workspace" in mobile_selectors
    assert ".portal-project-operations-authoring-layout" in mobile_selectors
    assert ".portal-project-grid" in mobile_selectors
    assert ".portal-project-filter .portal-fields" in mobile_selectors
    assert ".portal-project-detail-grid" in mobile_selectors
    assert ".portal-project-package-grid" in mobile_selectors
    assert ".portal-project-package-meta" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")
    assert "min-height: 44px;" in project_css
    assert not re.search(r"(?:#[0-9a-f]{3,8}\b|(?:linear|radial)-gradient|rgba?\()", project_css, re.I)
    assert not re.search(r"var\(--(?!portal-)", project_css)


def test_light_asset_vault_final_surface_keeps_private_storage_states_readable() -> None:
    """Asset Vault stays owner-scoped and truthful while its legacy dark surface becomes light."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Asset Vault surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    asset_css = layer.group("css")
    route = ".portal-page.portal-asset-vault"

    def declarations(selector: str) -> str:
        match = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<declarations>.*?)\n\}}",
            asset_css,
            flags=re.DOTALL,
        )
        assert match is not None
        return match.group("declarations")

    intro = declarations(f"{route} .portal-vault-intro")
    intro_heading = declarations(f"{route} .portal-vault-intro h2")
    intro_copy = declarations(f"{route} .portal-vault-intro p")
    intro_metric = declarations(f"{route} .portal-vault-intro dl > div")
    intro_metric_value = declarations(f"{route} .portal-vault-intro dt")
    intro_metric_label = declarations(f"{route} .portal-vault-intro dd")
    card_surface = declarations(f"{route} .portal-card")
    field_label = declarations(f"{route} .portal-field > :is(span, label)")
    field_help = declarations(f"{route} :is(.portal-field-help, .portal-form-note)")
    input_surface = declarations(f"{route} :is(.portal-input, .portal-select, .portal-textarea)")
    dropzone = declarations(f"{route} .portal-vault-dropzone")
    dropzone_interaction = declarations(f"{route} :is(.portal-vault-dropzone:hover, .portal-vault-dropzone:focus-within)")
    dropzone_icon = declarations(f"{route} .portal-vault-dropzone-icon")
    dropzone_text = declarations(f"{route} .portal-vault-dropzone strong")
    dropzone_copy = declarations(f"{route} .portal-vault-dropzone small")
    file_input = declarations(f"{route} .portal-vault-file-input")
    file_button = declarations(f"{route} .portal-vault-file-input::file-selector-button")
    filter_surface = declarations(f"{route} .portal-vault-filter")
    pagination = declarations(f"{route} .portal-vault-pagination")
    vault_card = declarations(f"{route} .portal-vault-card")
    vault_hover = declarations(f"{route} .portal-vault-card:hover")
    vault_title = declarations(f"{route} .portal-vault-card .portal-card-title")
    vault_copy = declarations(f"{route} .portal-vault-card .portal-card-subtitle")
    file_icon = declarations(f"{route} .portal-vault-file-icon")
    vault_meta = declarations(f"{route} .portal-vault-meta > div")
    vault_meta_key = declarations(f"{route} .portal-vault-meta dt")
    vault_meta_value = declarations(f"{route} .portal-vault-meta dd")
    step_row = declarations(f"{route} .portal-project-steps li")
    step_title = declarations(f"{route} .portal-project-steps strong")
    step_copy = declarations(f"{route} .portal-project-steps span")
    step_marker = declarations(f"{route} .portal-project-steps li::before")
    lifecycle_summary = declarations(f"{route} .portal-summary-item")
    lifecycle_key = declarations(f"{route} .portal-summary-key")
    lifecycle_value = declarations(f"{route} .portal-summary-value")
    lifecycle_row = declarations(f"{route} .portal-panel-row")
    lifecycle_title = declarations(f"{route} .portal-panel-row strong")
    lifecycle_copy = declarations(f"{route} .portal-panel-row span")
    lifecycle_icon = declarations(f"{route} .portal-panel-row-icon")
    empty = declarations(f"{route} .portal-empty")
    focus = declarations(f"{route} :is(button, a, input, select, textarea):focus-visible")
    mobile = re.search(
        rf"@media \(max-width: 700px\)\s*\{{\s*"
        rf"{re.escape(route)} :is\((?P<selectors>[^{{}}]*)\)\s*\{{"
        rf"(?P<declarations>.*?)\n\s*\}}\s*\}}\s*\Z",
        asset_css,
        flags=re.DOTALL,
    )
    mobile_controls = re.search(
        r"@media \(max-width: 700px\)\s*\{(?P<css>.*)\}\s*\Z",
        asset_css,
        flags=re.DOTALL,
    )

    selector_lines = re.findall(r"(?m)^\s*(?!@)(?P<selector>[^\n{}]+)\s*\{", asset_css)
    assert selector_lines
    assert all(selector.startswith(route) for selector in selector_lines)
    assert "background: var(--portal-surface-light) !important;" in intro
    assert "box-shadow: none;" in intro
    assert "color: var(--portal-ink);" in intro_heading
    assert "color: var(--portal-muted);" in intro_copy
    assert "background: var(--portal-surface-soft);" in intro_metric
    assert "color: var(--portal-action);" in intro_metric_value
    assert "color: var(--portal-muted);" in intro_metric_label
    assert "background: var(--portal-surface-light);" in card_surface
    assert "box-shadow: none;" in card_surface
    assert "color: var(--portal-ink);" in field_label
    assert "color: var(--portal-muted);" in field_help
    assert "background: var(--portal-surface-light);" in input_surface
    assert "color: var(--portal-ink);" in input_surface
    assert "background: var(--portal-surface-soft);" in dropzone
    assert "border-color: var(--portal-border-strong);" in dropzone_interaction
    assert "transform: none;" in dropzone_interaction
    assert "background: var(--portal-surface-light);" in dropzone_icon
    assert "color: var(--portal-action);" in dropzone_icon
    assert "color: var(--portal-ink);" in dropzone_text
    assert "color: var(--portal-muted);" in dropzone_copy
    assert "color: var(--portal-muted);" in file_input
    assert "background: var(--portal-surface-light);" in file_button
    assert "color: var(--portal-action);" in file_button
    assert "background: var(--portal-surface-light);" in filter_surface
    assert "color: var(--portal-muted);" in pagination
    assert "background: var(--portal-surface-light);" in vault_card
    assert "background: var(--portal-light-hover-surface);" in vault_hover
    assert "transform: none;" in vault_hover
    assert "color: var(--portal-ink);" in vault_title
    assert "color: var(--portal-muted);" in vault_copy
    assert "background: var(--portal-surface-soft);" in file_icon
    assert "color: var(--portal-action);" in file_icon
    assert "background: var(--portal-surface-soft);" in vault_meta
    assert "color: var(--portal-muted);" in vault_meta_key
    assert "color: var(--portal-ink);" in vault_meta_value
    assert "border-top-color: var(--portal-border);" in step_row
    assert "color: var(--portal-ink);" in step_title
    assert "color: var(--portal-muted);" in step_copy
    assert "background: var(--portal-action);" in step_marker
    assert "box-shadow: none;" in step_marker
    assert "border-bottom-color: var(--portal-border);" in lifecycle_summary
    assert "color: var(--portal-muted);" in lifecycle_key
    assert "color: var(--portal-ink);" in lifecycle_value
    assert "background: var(--portal-surface-soft);" in lifecycle_row
    assert "color: var(--portal-ink);" in lifecycle_title
    assert "color: var(--portal-muted);" in lifecycle_copy
    assert "background: var(--portal-surface-light);" in lifecycle_icon
    assert "background: var(--portal-surface-soft);" in empty
    assert "outline: 3px solid var(--portal-focus) !important;" in focus
    assert mobile is not None
    mobile_selectors = mobile.group("selectors")
    assert ".portal-vault-intro" in mobile_selectors
    assert ".portal-vault-intro dl" in mobile_selectors
    assert ".portal-vault-layout" in mobile_selectors
    assert ".portal-vault-grid" in mobile_selectors
    assert ".portal-vault-meta" in mobile_selectors
    assert ".portal-vault-filter .portal-fields" in mobile_selectors
    assert "grid-template-columns: 1fr;" in mobile.group("declarations")
    assert mobile_controls is not None
    assert f"{route} :is(.portal-button, .portal-input, .portal-select, .portal-textarea, .portal-vault-file-input::file-selector-button)" in mobile_controls.group("css")
    assert "min-height: 44px;" in mobile_controls.group("css")
    assert not re.search(r"(?:#[0-9a-f]{3,8}\b|(?:linear|radial)-gradient|rgba?\()", asset_css, re.I)
    assert not re.search(r"var\(--(?!portal-)", asset_css)


def test_light_workboard_final_surface_keeps_lifecycle_workspace_readable() -> None:
    """The planning workspace stays compact, owner-scoped and light without legacy colours."""

    theme_source = PORTAL_THEME.read_text(encoding="utf-8")
    layer = re.search(
        r"/\* Final light Workboard surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
        theme_source,
        flags=re.DOTALL,
    )

    assert layer is not None
    workboard_css = layer.group("css")
    required = (
        ".portal-workboard",
        ".portal-workboard-new",
        ".portal-workboard-detail",
        ".portal-workboard-tabs",
        ".portal-workboard-column",
        ".portal-workboard-card",
        ".portal-workboard-reference-picker",
        ".portal-workboard-events",
        ":focus-visible",
        "@media (max-width: 700px)",
    )

    for evidence in required:
        assert evidence in workboard_css
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", workboard_css)
    assert "rgba(" not in workboard_css.lower()
    assert "linear-gradient" not in workboard_css.lower()
    assert "radial-gradient" not in workboard_css.lower()
    assert not re.search(r"var\(--(?!portal-)", workboard_css)
