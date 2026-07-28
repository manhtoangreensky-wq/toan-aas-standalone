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


def test_customer_sidebar_uses_five_compact_groups_and_keeps_deep_routes_discoverable() -> None:
    navigation = _section("function navGroups(context, currentPage)", "function matchesRouteFamily(path, root)")
    palette = _section("function commandPaletteItems(context, page)", "function renderCommandPalette(page, context)")
    sidebar = _section("function renderSidebar(page, context)", "function renderHeader(page, context)")

    # The signed customer rail is a compact orientation surface, rather than
    # a second full catalogue.  All customer destinations remain available
    # through the feature catalogue and command palette below.
    permanent_projection = navigation[
        navigation.index("const groups = ["):navigation.index("const videoStudioNavGroups = [")
    ]
    permanent_labels = [
        line.strip().split('"', 2)[1]
        for line in permanent_projection.splitlines()
        if line.strip().startswith('label: "')
    ]
    expected_labels = ["Workspace", "Tạo mới", "Công việc", "Ví & gói", "Tài khoản & hỗ trợ"]
    assert permanent_labels == expected_labels
    for label in expected_labels:
        assert navigation.count(f'label: "{label}"') == 1

    label_positions = [permanent_projection.index(f'label: "{label}"') for label in expected_labels]
    for index, start in enumerate(label_positions):
        end = label_positions[index + 1] if index + 1 < len(label_positions) else len(permanent_projection)
        assert permanent_projection[start:end].count('["/') <= 5

    for path in (
        "/dashboard", "/projects", "/workboard", "/campaigns", "/calendar",
        "/features", "/chat", "/content-studio", "/image-studio",
        "/workspace", "/jobs", "/assets", "/asset-vault", "/approvals",
        "/wallet", "/wallet/topup", "/membership", "/packages", "/pricing",
        "/account", "/tickets", "/support",
    ):
        assert f'["{path}",' in permanent_projection

    # These dense non-video blocks must move out of the permanent rail, not
    # disappear from the authoritative manifest or palette.
    for stale_literal in (
        'label: "Nội dung & kế hoạch"',
        'label: "AI Labs & Media"',
        'label: "Bot companion"',
        '["/workspace-menu", "Chuyển workspace"',
        '["/prompt-library", "Prompt Library"',
        '["/voice-studio", "Voice Studio"',
        '["/document-workspace", "Document Workspace"',
        '["/automation", "Automation Center"',
        '["/operations", "Operations Center"',
    ):
        assert stale_literal not in permanent_projection

    assert "Object.values(manifest)" in palette
    assert "const authorizedAdminRoutes = adminErpNavigation(context).routes;" in palette
    assert 'candidate.access === "admin" && !authorizedAdminRoutes.has(path)' in palette

    # Video keeps its existing planner tree, but only on a Video Studio route.
    video_guard = 'if (matchesRouteFamily(currentRoute, "/video-studio")) {'
    video_insertion = "groups.splice(3, 0, ...videoStudioNavGroups);"
    assert "const videoStudioNavGroups = [" in navigation
    assert video_guard in navigation
    assert video_insertion in navigation
    assert navigation.index(video_guard) < navigation.index(video_insertion)

    # Deep routes retain a single, presentation-only orientation cue rather
    # than expanding the full customer catalogue again.
    assert "function currentCustomerWorkflowGroup(currentPage, groups)" in PORTAL
    assert 'label: "Đang mở"' in PORTAL
    assert "current: true" in PORTAL
    assert "groups.unshift(currentGroup);" in navigation
    assert "portal-nav-group--current" in sidebar


def test_desktop_focus_navigation_is_ephemeral_accessible_and_keeps_the_same_menu() -> None:
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
    interactions = _section("function bindInteractions()", "function mountPortal(override)")
    focus_mode = _section("function desktopFocusNavigationSupported()", "function closeSidebar(options)")

    # Focus mode only changes the desktop presentation. It must not introduce
    # a second route model, storage-backed profile preference, or browser-side
    # authority. The existing drawer/menu control remains the way back.
    assert "let desktopNavigationFocusEnabled = false;" in PORTAL
    assert "data-portal-focus-navigation" in PORTAL
    assert "function toggleDesktopFocusNavigation()" in PORTAL
    assert 'window.matchMedia("(min-width: 981px)")' in PORTAL
    assert 'event.target.closest("[data-portal-focus-navigation]")' in interactions
    assert 'closeSidebar({ restoreFocus: false });' in PORTAL
    assert 'document.querySelector("[data-portal-menu]")' in PORTAL
    assert "sessionStorage" not in focus_mode
    assert "localStorage" not in focus_mode
    assert ".portal-shell--focus" in css
    assert ".portal-shell--focus .portal-sidebar.is-open" in css
    assert ".portal-shell--focus .portal-menu-button" in css
