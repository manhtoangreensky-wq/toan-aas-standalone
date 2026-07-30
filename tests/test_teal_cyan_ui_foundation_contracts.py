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
