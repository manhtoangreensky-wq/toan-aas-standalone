"""Focused navigation contracts for the signed portal shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    offset = PORTAL.index(start)
    return PORTAL[offset:PORTAL.index(end, offset + len(start))]


def test_sidebar_marks_only_the_direct_account_or_voice_destination_current() -> None:
    nav = _section("function isNavCurrent(linkPath, page)", "function isMobileNavCurrent(key, page)")

    assert 'if (linkPath === "/voice-studio/direction-composer") return matchesRouteFamily(path, "/voice-studio/direction-composer");' in nav
    assert 'if (linkPath === "/voice-studio") return !matchesRouteFamily(path, "/voice-studio/direction-composer") && matchesRouteFamily(path, "/voice-studio");' in nav
    assert 'if (linkPath === "/account/activity") return matchesRouteFamily(path, "/account/activity");' in nav
    assert 'if (linkPath === "/account") return path === "/account" || path === "/onboarding";' in nav


def test_mobile_video_studio_highlights_ai_studio_instead_of_dashboard() -> None:
    mobile = _section("function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")
    dashboard = mobile[mobile.index('if (key === "dashboard")'):mobile.index('if (key === "studio")')]
    studio = mobile[mobile.index('if (key === "studio")'):]

    assert '"/video-studio"' not in dashboard
    assert 'path.startsWith("/video-studio/")' not in dashboard
    assert 'matchesRouteFamily(path, "/video-studio")' in studio


def test_mobile_memory_center_and_reminders_stay_in_the_workspace_navigation() -> None:
    mobile = _section("function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")
    dashboard = mobile[mobile.index('if (key === "dashboard")'):mobile.index('if (key === "studio")')]
    account = mobile[mobile.index('if (key === "account")'):]

    # Memory is an authoring/work-management surface in the desktop
    # Workspace grouping. Mobile must not misleadingly promote it as a
    # profile/account page merely because a customer owns the records.
    assert '"/notes", "/reminders"' in dashboard
    assert '"/notes", "/reminders"' not in account


def test_sidebar_uses_progressive_disclosure_without_hiding_the_active_workflow() -> None:
    navigation = _section("function navGroups(context, currentPage)", "function matchesRouteFamily(path, root)")
    sidebar = _section("function renderSidebar(page, context)", "function renderHeader(page, context)")
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")

    # The permanent default is intentionally small; all non-core groups open
    # automatically only for their active route family and remain reachable
    # via their native disclosure summary or the command palette.
    assert 'label: "Workspace", defaultOpen: true' in navigation
    for group in (
        "Nội dung & kế hoạch",
        "AI Labs & Media",
        "Video Studio",
        "Video Studio · Ý tưởng & kịch bản",
        "Video Studio · Phim & storyboard",
        "Video Studio · Tư liệu & chuyển động",
    ):
        assert f'label: "{group}"' in navigation
    assert "const videoStudioNavGroups = [" in navigation
    assert "groups.splice(3, 0, ...videoStudioNavGroups);" in navigation
    assert '<details class="portal-nav-group"${open ? " open" : ""}>' in sidebar
    assert 'const open = group.defaultOpen === true || preparedLinks.some((link) => link.current);' in sidebar
    assert 'class="portal-nav-summary"' in sidebar
    assert ".portal-nav-summary" in css
    assert ".portal-nav-group[open] .portal-nav-summary::before" in css
