"""RED contracts for the reference-informed customer tool directory and Studio.

This is intentionally a presentation-only slice.  The Portal may copy useful
spatial hierarchy and navigation rhythm from a reference, but it may not copy
third-party source/assets or invent operational authority.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:] if end == -1 else source[start:end]


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_media_studio_has_equal_reviewed_vi_en_zh_fixed_chrome() -> None:
    keys = (
        "page.title",
        "page.description",
        "intro.title",
        "intro.body",
        "flow.label",
        "step.discover.title",
        "step.brief.title",
        "step.plan.title",
        "step.review.title",
        "step.jobs.title",
        "step.assets.title",
        "handoff.title",
        "action.explore",
    )

    for key in keys:
        assert I18N.count(f'"mediaStudio.{key}"') == 3, key


def test_media_studio_is_a_route_only_customer_workflow_rail() -> None:
    studio = _function(PORTAL, "renderMediaStudio")

    assert "function mediaStudioText(" in PORTAL
    assert "mediaStudioText(" in studio
    assert "portal-media-studio-shell" in studio
    assert "portal-media-studio-flow" in studio
    assert "portal-media-studio-step" in studio
    assert "portal-finalization-card" not in studio

    for route in ("/features", "/content/storyboard", "/video/product", "/approvals", "/jobs", "/assets"):
        assert f'href: "{route}"' in studio, route

    for forbidden in (
        "fetch(",
        "data-portal-action",
        "dispatchAction",
        "wallet",
        "payment",
        "provider",
        "createJob",
        "completed",
    ):
        assert forbidden not in studio, forbidden


def test_media_studio_page_metadata_uses_fixed_locale_chrome() -> None:
    title = _function(PORTAL, "localizedPageTitle")
    description = _function(PORTAL, "localizedPageDescription")

    assert 'if (path === "/studio") return mediaStudioText("page.title", fallback);' in title
    assert 'if (path === "/studio") return mediaStudioText("page.description", fallback);' in description


def test_feature_catalog_has_a_localized_continuation_into_media_studio() -> None:
    catalog = _function(PORTAL, "renderFeatureCatalog")

    assert 'href="/studio"' in catalog
    assert 'mediaStudioText("catalog.title"' in catalog
    assert 'mediaStudioText("catalog.body"' in catalog
    assert 'mediaStudioText("catalog.action"' in catalog

    for key in ("catalog.title", "catalog.body", "catalog.action"):
        assert I18N.count(f'"mediaStudio.{key}"') == 3, key


def test_feature_catalog_keeps_search_and_intent_selection_before_studio_continuation() -> None:
    """The optional Studio handoff cannot displace the primary discovery task."""
    catalog = _function(PORTAL, "renderFeatureCatalog")
    rendered = catalog[catalog.index("return `<article class=\"portal-page\">"):]

    assert rendered.index("${search}") < rendered.index("${renderFeatureFamilyExplorer()}")
    assert rendered.index("${renderFeatureFamilyExplorer()}") < rendered.index("${studioContinuation}")
    assert rendered.index("${jumps}") < rendered.index("${studioContinuation}")
    assert rendered.index("${studioContinuation}") < rendered.index("${body}")


def test_media_studio_desktop_grid_uses_a_semantic_connected_rail() -> None:
    marker = "/* Reference-first Media Studio rail"
    studio_theme = THEME[THEME.index(marker):]

    assert "@media (min-width: 921px)" in studio_theme
    assert ".portal-media-studio-grid::before" in studio_theme
    assert ".portal-media-studio-grid::after" in studio_theme
    assert "background: var(--portal-border-strong);" in studio_theme
    assert "z-index: 1;" in studio_theme

    compact = studio_theme[studio_theme.index("@media (max-width: 920px)"):]
    assert "content: none;" in compact


def test_media_studio_section_chrome_is_localized_by_its_reviewed_namespace() -> None:
    studio_registration = PORTAL[PORTAL.index('customerPage("/studio"'):PORTAL.index('customerPage("/studio"') + 650]
    navigation = _section(PORTAL, "const NAVIGATION_I18N_KEYS", "function localizedNavigationLabel")

    assert 'section: "Media Studio"' in studio_registration
    assert '"Media Studio": "mediaStudio.section"' in navigation
    assert I18N.count('"mediaStudio.section"') == 3


def test_media_studio_hero_and_safety_copy_use_the_same_fixed_locale_namespace() -> None:
    studio = _function(PORTAL, "renderMediaStudio")
    assert 'mediaStudioText("intro.title"' in studio
    assert 'mediaStudioText("intro.body"' in studio
    assert 'mediaStudioText("intro.meta.truth"' in studio
    assert I18N.count('"mediaStudio.intro.meta.truth"') == 3


def test_media_studio_uses_existing_workspace_motion_and_token_only_theme_rules() -> None:
    workspace = _section(MOTION, "function mountWorkspace(root)", "function mountLanding(root)")
    assert '".portal-media-studio-shell .portal-media-studio-intro"' in workspace
    assert '".portal-media-studio-shell .portal-media-studio-flow"' in workspace
    assert '".portal-media-studio-shell .portal-media-studio-handoff"' in workspace
    assert '".portal-feature-studio-continuation"' in workspace
    assert '".portal-media-studio-step"' in workspace

    marker = "/* Reference-first Media Studio rail"
    assert marker in THEME
    studio_theme = THEME[THEME.index(marker):]
    assert "--portal-" in studio_theme
    assert "#" not in studio_theme
    assert ".portal-media-studio-shell" in studio_theme
    assert ".portal-media-studio-step" in studio_theme

    reduced_start = studio_theme.index("@media (prefers-reduced-motion: reduce)")
    reduced = studio_theme[reduced_start:]
    for selector in (".portal-media-studio-shell", ".portal-media-studio-step"):
        assert selector in reduced
    for reset in ("animation: none !important;", "transition: none !important;", "transform: none !important;"):
        assert reset in reduced


def test_workspace_motion_never_hides_a_keyboard_destination_or_waits_forever_for_observer() -> None:
    """Optional scroll polish cannot delay a keyboard destination or blank a group.

    ``mountWorkspace`` initially applies ``is-pending`` so a late observer
    callback can reveal a group.  A focus event must override the stagger
    immediately, and a bounded fallback must reveal every group if the
    observer never delivers an entry (for example during a layout failure).
    """
    workspace = _section(MOTION, "function mountWorkspace(root)", "function mountLanding(root)")

    assert "const WORKSPACE_REVEAL_FALLBACK_MS" in MOTION
    assert "let revealFallbackTimer = 0;" in workspace
    assert "const timerHost = typeof window.setTimeout" in workspace
    assert "timerHost.setTimeout(() => {" in workspace
    assert "targets.forEach(revealTarget);" in workspace
    assert "timerHost.clearTimeout(revealFallbackTimer);" in workspace

    motion_start = THEME.index("@media (prefers-reduced-motion: no-preference)", THEME.index("/* Reference-first Media Studio rail"))
    motion_end = THEME.index("/* Reference-first Media Studio rail", motion_start + 1) if "/* Reference-first Media Studio rail" in THEME[motion_start + 1:] else len(THEME)
    workspace_theme = THEME[THEME.index(".portal-shell[data-portal-app-kind=\"customer\"] .portal-workspace-motion-target.is-pending"):motion_end]
    assert ".portal-workspace-motion-target.is-visible:focus-within" in workspace_theme
    assert ".portal-workspace-motion-target.is-visible:focus-within .portal-workspace-motion-item" in workspace_theme
    assert "opacity: 1;" in workspace_theme
    assert "animation: none;" in workspace_theme


def test_feature_catalog_studio_handoff_joins_the_existing_workspace_motion_lifecycle() -> None:
    """The continuation is a visible decision point, not a static orphan."""
    workspace = _section(MOTION, "function mountWorkspace(root)", "function mountLanding(root)")

    assert '".portal-feature-studio-continuation"' in workspace
