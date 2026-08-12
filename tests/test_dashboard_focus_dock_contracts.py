"""Contracts for the saved-priority Dashboard Focus Dock."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def _function_section(name: str) -> str:
    start = PORTAL.index(f"function {name}(")
    end = PORTAL.find("\n  function ", start + 1)
    return PORTAL[start:end if end != -1 else len(PORTAL)]


def test_focus_dock_uses_only_saved_completed_workspace_priorities() -> None:
    helper = _function_section("dashboardFocusWorkspaces")
    renderer = _function_section("renderDashboardFocusDock")

    for token in (
        'workspaceSetup.readState !== "read_only"',
        'profile.setup_state !== "completed"',
        "profile.focus_areas",
        ".slice(0, 3)",
        "DASHBOARD_FOCUS_WORKSPACE_SPECS",
    ):
        assert token in helper

    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        "sessionStorage",
        "telegram",
        "wallet",
        "payment",
        "provider",
        "job",
        "data-portal-action",
    ):
        assert forbidden.lower() not in (helper + renderer).lower()


def test_focus_dock_is_closed_allowlisted_navigation_only() -> None:
    specs = _section(
        PORTAL,
        "const DASHBOARD_FOCUS_WORKSPACE_SPECS",
        "function dashboardFocusWorkspaces(context)",
    )
    helper = _section(
        PORTAL,
        "function dashboardFocusWorkspaces(context)",
        "function renderDashboardFocusDock(context)",
    )

    assert specs.count('key: "') == 8
    for route in (
        "/projects",
        "/content-studio",
        "/image-studio",
        "/voice-studio",
        "/music/library",
        "/subtitle-studio",
        "/document-workspace",
        "/workboard",
    ):
        assert f'route: "{route}"' in specs
    assert "manifest[normalizePath(route)]" in helper
    assert 'page.access === "admin"' in helper
    assert 'page.access !== "member"' in helper


def test_focus_dock_precedes_project_and_draft_libraries() -> None:
    dashboard = _section(
        PORTAL,
        "function renderDashboard(page, context)",
        "function renderWorkspaceActionCenter(context)",
    )

    assert dashboard.index("${renderDashboardFocusDock(context)}") < dashboard.index(
        '<div class="portal-dashboard-library-grid">'
    )


def test_focus_dock_fixed_copy_is_reviewed_in_all_customer_locales() -> None:
    keys = (
        "dashboard.focus.kicker",
        "dashboard.focus.title",
        "dashboard.focus.body",
        "dashboard.focus.adjust",
        "dashboard.focus.open",
        "dashboard.focus.projects.title",
        "dashboard.focus.projects.body",
        "dashboard.focus.content.title",
        "dashboard.focus.content.body",
        "dashboard.focus.image.title",
        "dashboard.focus.image.body",
        "dashboard.focus.voice.title",
        "dashboard.focus.voice.body",
        "dashboard.focus.music.title",
        "dashboard.focus.music.body",
        "dashboard.focus.subtitle.title",
        "dashboard.focus.subtitle.body",
        "dashboard.focus.documents.title",
        "dashboard.focus.documents.body",
        "dashboard.focus.automation.title",
        "dashboard.focus.automation.body",
    )

    for key in keys:
        assert I18N.count(f'"{key}"') == 3


def test_focus_dock_is_responsive_token_scoped_and_uses_existing_motion_lifecycle() -> None:
    css = _section(THEME, "/* Dashboard Focus Dock", "/* Customer dashboard decision motion")
    dashboard_items = _section(
        MOTION,
        "const dashboardItemSelector = [",
        "const dashboardTargets =",
    )

    for token in (
        '.portal-shell[data-portal-app-kind="customer"] .portal-dashboard-focus-dock',
        ".portal-dashboard-focus-card:focus-visible",
        "repeat(3, minmax(0, 1fr))",
        "repeat(2, minmax(0, 1fr))",
        "grid-template-columns: minmax(0, 1fr)",
        "min-height: 44px",
        "var(--portal-",
    ):
        assert token in css
    assert '".portal-dashboard-focus-card"' in dashboard_items
