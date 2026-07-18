"""Contracts for the explicit, Web-native first-session guide."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    offset = PORTAL.index(start)
    return PORTAL[offset:PORTAL.index(end, offset + len(start))]


def test_dashboard_first_session_guide_is_explicit_and_web_native() -> None:
    guide = _section("function renderDashboardStartGuide(context)", "function renderDashboard(page, context)")

    assert 'data-dashboard-start-guide' in guide
    assert "if (hasProjects || hasDrafts) return" in guide
    assert 'href: "/projects"' in guide
    assert 'href: "/features"' in guide
    assert 'href: "/onboarding"' in guide
    assert "telegramIdentityLinked(context)" in guide
    assert "không bị khóa vào Telegram" in guide
    assert "không nhập Telegram ID trên Web" in guide
    assert "không tự tạo job, charge hoặc dữ liệu provider" in guide


def test_telegram_link_entrypoint_is_explicitly_optional() -> None:
    assert 'customerPage("/onboarding", "Liên kết Telegram (tùy chọn)"' in PORTAL
    assert "Web Workspace vẫn hoạt động độc lập." in PORTAL
    assert "Không nhận Telegram ID thô từ URL hay localStorage." in PORTAL


def test_dashboard_places_the_guide_before_private_integration_summaries() -> None:
    dashboard = _section("function renderDashboard(page, context)", "function renderWorkspaceActionCenter(context)")

    assert '${renderDashboardStartGuide(context)}<div class="portal-status-grid' in dashboard


def test_dashboard_hides_an_empty_work_queue_and_keeps_the_first_action_first() -> None:
    dashboard = _section("function renderDashboard(page, context)", "function renderWorkspaceActionCenter(context)")
    action_center = _section("function renderWorkspaceActionCenter(context)", "function renderStudioLaunchpad(context)")

    assert dashboard.index("${renderDashboardWorkspaceSummary(context)}") < dashboard.index("${renderDashboardStartGuide(context)}")
    assert dashboard.index("${renderDashboardStartGuide(context)}") < dashboard.index('<div class="portal-status-grid">')
    assert dashboard.index('<div class="portal-status-grid">') < dashboard.index("${renderWorkspaceActionCenter(context)}")
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
