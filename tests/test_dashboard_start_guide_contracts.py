"""Contracts for the explicit, Web-native first-session guide."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    offset = PORTAL.index(start)
    return PORTAL[offset:PORTAL.index(end, offset + len(start))]


def _function_section(name: str) -> str:
    start = PORTAL.index(f"function {name}(")
    end = PORTAL.find("\n  function ", start + 1)
    return PORTAL[start:end if end != -1 else len(PORTAL)]


def test_dashboard_first_session_guide_is_explicit_and_web_native() -> None:
    guide = _function_section("renderDashboardStartGuide")

    assert 'data-dashboard-start-guide' in guide
    assert "if (hasProjects || hasDrafts) return" in guide
    assert 'href: "/projects"' in guide
    assert 'href: "/features"' in guide
    assert 'href: "/onboarding"' in guide
    assert "telegramIdentityLinked(context)" in guide
    assert 'dashboardText("guide.title")' in guide
    assert 'dashboardText("guide.optional.body")' in guide
    assert 'dashboardText("guide.setup.body")' in guide
    assert 'data-portal-action' not in guide
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "data-portal-action"):
        assert forbidden.lower() not in guide.lower()

    for key in (
        "dashboard.guide.title",
        "dashboard.guide.optional.body",
        "dashboard.guide.setup.body",
    ):
        assert I18N.count(f'"{key}"') == 3


def test_telegram_link_entrypoint_is_explicitly_optional() -> None:
    assert 'customerPage("/onboarding", "Liên kết Telegram (tùy chọn)"' in PORTAL
    assert "Web Workspace vẫn hoạt động độc lập." in PORTAL
    assert "Không nhận Telegram ID thô từ URL hay localStorage." in PORTAL


def test_dashboard_places_the_guide_before_private_integration_summaries() -> None:
    dashboard = _section("function renderDashboard(page, context)", "function renderWorkspaceActionCenter(context)")

    assert dashboard.index("${renderDashboardStartGuide(context)}") < dashboard.index("${renderDashboardCanonicalLane(context, readState)}")


def test_dashboard_hides_an_empty_work_queue_and_keeps_the_first_action_first() -> None:
    dashboard = _section("function renderDashboard(page, context)", "function renderWorkspaceActionCenter(context)")
    canonical = _section("function renderDashboardCanonicalLane(context, readState)", "function renderDashboard(page, context)")
    action_center = _section("function renderWorkspaceActionCenter(context)", "function renderStudioLaunchpad(context)")

    assert dashboard.index("${renderDashboardWorkspaceSummary(context)}") < dashboard.index("${renderDashboardStartGuide(context)}")
    assert dashboard.index("${renderDashboardStartGuide(context)}") < dashboard.index('<div class="portal-command-center-lanes">')
    assert dashboard.index('<div class="portal-command-center-lanes">') < dashboard.index("${renderDashboardCanonicalLane(context, readState)}")
    assert 'if (readState !== "ready")' in canonical
    assert "${renderWorkspaceActionCenter(context)}" in canonical
    assert "const actionableCount = processing + deliveryReady + needsReview + waitingUser;" in action_center
    assert 'if (!actionableCount) return "";' in action_center


def test_dashboard_first_session_guide_has_responsive_keyboard_visible_presentation() -> None:
    for requirement in (
        ".portal-start-guide {",
        ".portal-start-guide-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));",
        ".portal-start-guide-step:hover, .portal-start-guide-step:focus-visible",
        ".portal-start-guide-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }",
        ".portal-start-guide-grid { grid-template-columns: 1fr; }",
        ".portal-start-guide-head { flex-direction: column;",
    ):
        assert requirement in CSS
