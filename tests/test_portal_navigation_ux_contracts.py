"""Focused navigation contracts for the signed portal shell."""

import re
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
    compact_groups = {
        "Workspace": ["/dashboard", "/projects", "/workboard", "/campaigns", "/calendar"],
        "Tạo mới": ["/features", "/chat", "/content-studio", "/image-studio"],
        "Công việc": ["/workspace", "/jobs", "/assets", "/asset-vault", "/approvals"],
        "Ví & gói": ["/wallet", "/wallet/topup", "/membership", "/packages", "/pricing"],
        "Tài khoản & hỗ trợ": ["/account", "/tickets", "/support"],
    }
    group_pattern = re.compile(
        r'label:\s*"(?P<label>[^"]+)"(?P<body>.*?)(?=\s*\]\s*\},?\s*\n\s*\{|\s*\]\s*\}\s*\n\s*\];)',
        re.DOTALL,
    )
    permanent_groups = [
        (
            match.group("label"),
            re.findall(r'\["(?P<path>/[^"]+)"\s*,', match.group("body")),
        )
        for match in group_pattern.finditer(permanent_projection)
    ]
    assert permanent_groups == list(compact_groups.items())

    permanent_routes = [path for _, paths in permanent_groups for path in paths]
    assert len(permanent_routes) == 22
    assert len(permanent_routes) == len(set(permanent_routes))
    # Dense and Bot-companion routes remain discoverable through the manifest
    # and palette, but do not get a permanent signed-customer rail position.
    dense_or_bot_routes = {
        "/workspace-menu", "/starter-kits", "/project-packages", "/prompt-library",
        "/free-prompt-gallery", "/content/channel-strategy", "/content/handoffs",
        "/crm/leads", "/content/prompt-pack", "/content/publish-review",
        "/content/contextual-prompt", "/trend-research", "/media-factory", "/creative-flow",
        "/guides/source-rights", "/analytics", "/notes", "/reminders", "/image/prompt-composer",
        "/image-hub", "/document-workspace", "/subtitle-studio", "/subtitle/assets",
        "/subtitle/formats", "/voice-studio", "/voice-studio/direction-composer",
        "/media-workspace", "/media-workspace/sfx-cue-sheet", "/audio/assets",
        "/account/interface-language", "/account/activity", "/account/data-controls",
        "/account/workspace-care", "/guides", "/inbox", "/automation", "/operations",
        "/status", "/referrals", "/rewards", "/community",
    }
    assert not set(permanent_routes).intersection(dense_or_bot_routes)

    assert "Object.values(manifest)" in palette
    assert "const authorizedAdminRoutes = adminErpNavigation(context).routes;" in palette
    assert 'candidate.access === "admin" && !authorizedAdminRoutes.has(path)' in palette

    # Video keeps its existing planner tree, but only on a Video Studio route.
    video_guard = 'if (matchesRouteFamily(currentRoute, "/video-studio")) {'
    video_insertion = "groups.splice(3, 0, ...videoStudioNavGroups);"
    assert "const videoStudioNavGroups = [" in navigation
    assert video_guard in navigation
    assert video_insertion in navigation
    guard_open = navigation.index("{", navigation.index(video_guard))
    guard_depth = 0
    guard_close = None
    for position, character in enumerate(navigation[guard_open:], start=guard_open):
        if character == "{":
            guard_depth += 1
        elif character == "}":
            guard_depth -= 1
            if guard_depth == 0:
                guard_close = position
                break
    assert guard_close is not None
    assert video_insertion in navigation[guard_open + 1:guard_close]

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
