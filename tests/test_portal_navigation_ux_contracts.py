"""Focused navigation contracts for the signed portal shell."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    offset = PORTAL.index(start)
    return PORTAL[offset:PORTAL.index(end, offset + len(start))]


def _run_current_customer_workflow_harness(source_path: Path) -> dict:
    """Execute the real cue helper without exporting browser internals for tests."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the Portal navigation helper")
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end ${end}`);
  return source.slice(offset, finish);
}
const routePattern = source.includes("const CUSTOMER_APPLICATION_ROUTE")
  ? extract("const CUSTOMER_APPLICATION_ROUTE", "function currentCustomerWorkflowGroup(currentPage, groups)")
  : "";
const runtime = [
  'const window = { location: { pathname: "/dashboard" } };',
  'const ICONS = Object.freeze({ prompt: "prompt" });',
  'function uiText(_key, fallback) { return fallback; }',
  extract("function normalizePath(path)", "const CAPABILITY_HUB_FAMILY_KEYS"),
  extract("function safeCatalogRoute(value)", "function catalogEntryRoute(entry)"),
  extract("function matchesRouteFamily(path, root)", "function isNavCurrent(linkPath, page)"),
  extract("function isNavCurrent(linkPath, page)", "// The compact dock intentionally links"),
  routePattern,
  extract("function currentCustomerWorkflowGroup(currentPage, groups)", "function navGroups(context, currentPage)")
].join("\n");
eval(runtime);
const compactGroups = [{ links: [["/dashboard", "Tổng quan", "dashboard"]] }];
const cue = (page) => currentCustomerWorkflowGroup(page, compactGroups);
const videoCue = cue({
  routePath: "/video-studio/story-video-plan", access: "member",
  title: "Story Video Planner"
});
if (!videoCue || videoCue.current !== true || videoCue.links.length !== 1 || videoCue.links[0][0] !== "/video-studio/story-video-plan") {
  throw new Error("registered deep Video Studio route did not receive one current workflow cue");
}
for (const [name, page] of Object.entries({
  compact: { routePath: "/dashboard", access: "member", title: "Tổng quan" },
  public: { routePath: "/login", access: "public", title: "Đăng nhập" },
  admin: { routePath: "/admin/users", access: "admin", title: "Người dùng" },
  notFound: { routePath: "/not-found", path: "/not-found", access: "member", layout: "not-found", title: "Trang chưa được định tuyến" },
  hostile: { routePath: '/video-studio/"onmouseover="alert(1)', access: "member", title: "Hostile" }
})) {
  if (cue(page) !== null) throw new Error(`${name} route unexpectedly received a current workflow cue`);
}
process.stdout.write(JSON.stringify({ videoCuePath: videoCue.links[0][0], videoCueCount: videoCue.links.length }));
'''
    try:
        result = subprocess.run(
            [node, "-e", script, str(source_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        pytest.skip(f"Node subprocess is unavailable in this test runner: {exc}")
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def _run_admin_mobile_nav_harness(source_path: Path) -> dict:
    """Exercise the real fail-closed ERP mobile helpers without exporting them."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the Portal Admin mobile navigation helper")
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end ${end}`);
  return source.slice(offset, finish);
}
const runtime = [
  'const window = { location: { pathname: "/admin" } };',
  'const ICONS = Object.freeze({ admin: "admin", support: "support", users: "users", payments: "payments", jobs: "jobs", providers: "providers", security: "security", reports: "reports", system: "system", default: "default" });',
  'const ALLOWED_STATES = new Set(["ready", "guarded", "read_only"]);',
  'function safeText(value, fallback) { if (typeof value !== "string") return fallback || ""; return value.replace(/[&<>\'\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\'": "&#39;", \'"\': "&quot;" }[character])); }',
  'function portalIcon(icon) { return `<svg data-icon="${icon}"></svg>`; }',
  extract("function normalizePath(path)", "const CAPABILITY_HUB_FAMILY_KEYS"),
  extract("function safeCatalogRoute(value)", "function catalogEntryRoute(entry)"),
  extract("function adminErpNavigation(context)", "function adminRouteIcon(route)"),
  extract("function adminRouteIcon(route)", "function hasLiveCanonicalAdmin(context)"),
  extract("function serverAuthorizesAdminRoute(context, route)", "const CUSTOMER_APPLICATION_ROUTE"),
  extract("function isAdminPortalSurface(page)", "function normalizeCommandSearch(value)")
].join("\n");
eval(runtime);

const context = {
  adminErpNavigation: {
    read_state: "ready",
    groups: [
      { id: "support", modules: [
        { route: "/admin/support", title: "Support & <Ops>", state: "available" },
        { route: "/admin/users", title: "Users", state: "available" }
      ] },
      { id: "web-local", modules: [
        { route: "/admin/crm", title: "CRM", state: "available" },
        { route: "/admin/reports", title: "Reports", state: "guarded" }
      ] },
      { id: "canonical", modules: [
        { route: "/admin", title: "ERP overview", state: "available" },
        { route: "/admin/jobs", title: "Jobs", state: "available" },
        { route: "/admin/providers", title: "Providers", state: "available" }
      ] }
    ]
  }
};
const jobItems = adminMobileNavItems({ routePath: "/admin/jobs/job-42" }, context);
const exactItems = adminMobileNavItems({ routePath: "/admin/users" }, context);
const nonInheritingItems = adminMobileNavItems({ routePath: "/admin/users/user-42" }, context);
const supportItems = adminMobileNavItems({ routePath: "/admin/support/ticket-42" }, context);
const unavailable = adminMobileNavItems({ routePath: "/admin/jobs/job-42" }, { adminErpNavigation: { read_state: "loading", groups: context.adminErpNavigation.groups } });
const markup = renderAdminMobileNav({ routePath: "/admin/support/ticket-42" }, context);
const desktopGroups = adminDesktopNavGroups(context, { routePath: "/admin/jobs/job-42" });
const desktopLinks = desktopGroups.flatMap((group) => group.links);
const unavailableDesktop = adminDesktopNavGroups({ adminErpNavigation: { read_state: "loading", groups: context.adminErpNavigation.groups } }, { routePath: "/admin/jobs/job-42" });

if (jobItems.length !== 5 || jobItems[0].route !== "/admin/jobs" || jobItems[1].route !== "/admin") {
  throw new Error(`current job and issued overview were not retained: ${JSON.stringify(jobItems)}`);
}
if (jobItems.filter((item) => item.current).length !== 1 || !jobItems[0].current) {
  throw new Error(`job detail did not receive one inherited current state: ${JSON.stringify(jobItems)}`);
}
if (exactItems.filter((item) => item.current).map((item) => item.route).join(",") !== "/admin/users") {
  throw new Error(`exact issued route was not current: ${JSON.stringify(exactItems)}`);
}
if (nonInheritingItems.some((item) => item.current)) {
  throw new Error(`non-job/support detail inherited an unauthorized current state: ${JSON.stringify(nonInheritingItems)}`);
}
if (supportItems.filter((item) => item.current).map((item) => item.route).join(",") !== "/admin/support") {
  throw new Error(`support detail did not inherit its issued module: ${JSON.stringify(supportItems)}`);
}
if (unavailable.length !== 0 || renderAdminMobileNav({ routePath: "/admin" }, { adminErpNavigation: { read_state: "loading", groups: [] } }) !== "") {
  throw new Error("an unavailable server grant did not fail closed");
}
if (!isAdminMobileSurface({ routePath: "/admin/jobs" }) || isAdminMobileSurface({ routePath: "/dashboard", isAdmin: true }) || isAdminMobileSurface({})) {
  throw new Error("Admin surface selection did not use only the normalized path");
}
if (!markup.includes('href="/admin/support"') || !markup.includes("Support &amp; &lt;Ops&gt;")) {
  throw new Error(`server-issued route/title were not safely rendered: ${markup}`);
}
if (desktopGroups.length !== 3 || desktopLinks.some((link) => link[0] === "/dashboard" || link[0] === "/features")) {
  throw new Error(`desktop ERP sidebar included a customer route or lost a granted group: ${JSON.stringify(desktopGroups)}`);
}
if (desktopLinks.filter((link) => link[3] === true).map((link) => link[0]).join(",") !== "/admin/jobs") {
  throw new Error(`desktop ERP sidebar did not announce exactly the current issued job route: ${JSON.stringify(desktopLinks)}`);
}
if (!desktopGroups[2].current || !desktopGroups[2].defaultOpen || unavailableDesktop.length !== 0) {
  throw new Error(`desktop ERP sidebar did not open only the current group or fail closed: ${JSON.stringify({ desktopGroups, unavailableDesktop })}`);
}
if (!isAdminPortalSurface({ routePath: "/admin/jobs" }) || isAdminPortalSurface({ routePath: "/dashboard", isAdmin: true })) {
  throw new Error("desktop Admin surface selection did not use only the normalized path");
}
process.stdout.write(JSON.stringify({ jobRoutes: jobItems.map((item) => item.route), supportMarkup: markup, desktopRoutes: desktopLinks.map((link) => link[0]) }));
'''
    try:
        result = subprocess.run(
            [node, "-e", script, str(source_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        pytest.skip(f"Node subprocess is unavailable in this test runner: {exc}")
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def test_admin_mobile_dock_keeps_current_server_issued_destination_within_five_items() -> None:
    result = _run_admin_mobile_nav_harness(ROOT / "static" / "portal" / "portal.js")

    assert result["jobRoutes"] == ["/admin/jobs", "/admin", "/admin/support", "/admin/users", "/admin/crm"]
    assert result["desktopRoutes"] == ["/admin/support", "/admin/users", "/admin/crm", "/admin/reports", "/admin", "/admin/jobs", "/admin/providers"]
    assert 'aria-current="page"' in result["supportMarkup"]


def test_admin_mobile_mount_portal_selects_the_admin_dock_only_for_admin_routes() -> None:
    mount = PORTAL[PORTAL.index("function mountPortal(override)"):]

    # The same signed-session guard still protects every mobile dock.  The
    # route projection changes only after the signed page is selected.
    assert "const mobileNavMarkup = showMobileNav" in mount
    assert "isAdminMobileSurface(page) ? renderAdminMobileNav(page, context) : renderMobileNav(page)" in mount
    assert "mobileNav.hidden = !mobileNavMarkup;" in mount
    assert "mobileNav.innerHTML = mobileNavMarkup;" in mount


def test_desktop_admin_shell_uses_the_same_issued_projection_without_customer_shortcuts() -> None:
    navigation = _section("function navGroups(context, currentPage)", "function matchesRouteFamily(path, root)")
    sidebar = _section("function renderSidebar(page, context)", "function renderHeader(page, context)")
    header = _section("function renderHeader(page, context)", "function renderFields(fields, enabled, context, fieldValues, idNamespace)")
    palette = _section("function commandPaletteItems(context, page)", "function renderCommandPalette(page, context)")
    dialog = _section("function renderCommandPalette(page, context)", "function renderSidebar(page, context)")

    assert "if (isAdminPortalSurface(currentPage)) return adminDesktopNavGroups(context, currentPage);" in navigation
    assert "const currentOverride = link.length > 3 ? link[3] : null;" in sidebar
    assert "const adminSurface = isAdminPortalSurface(page);" in sidebar
    assert 'adminRoutes.has("/admin")' in sidebar
    assert "const sidebarPrimaryAction = adminSurface" in sidebar
    assert 'href="/features"' in sidebar
    assert "const adminSurface = isAdminPortalSurface(page);" in header
    assert "chrome.searchAdmin" in header
    assert "const adminSurface = isAdminPortalSurface(page);" in palette
    assert 'candidate.access !== "admin"' in palette
    assert "chrome.adminCommandCount" in dialog
    assert "const commandKicker = adminSurface" in dialog
    assert "const commandTitle = adminSurface" in dialog
    assert "const commandEmpty = adminSurface" in dialog


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

    # The permanent default is intentionally small. Video is the one deep
    # workspace that retains its established contextual disclosure tree; the
    # general customer catalogue stays in `/features` and the command palette.
    assert 'label: "Workspace", defaultOpen: true' in navigation
    for group in (
        "Video Studio",
        "Video Studio · Ý tưởng & kịch bản",
        "Video Studio · Phim & storyboard",
        "Video Studio · Tư liệu & chuyển động",
    ):
        assert f'label: "{group}"' in navigation
    assert 'label: "Nội dung & kế hoạch"' not in navigation
    assert 'label: "AI Labs & Media"' not in navigation
    assert "const videoStudioNavGroups = [" in navigation
    assert "groups.splice(3, 0, ...videoStudioNavGroups);" in navigation
    assert 'if (matchesRouteFamily(currentRoute, "/video-studio")) {' in navigation
    assert "if (isAdminPortalSurface(currentPage)) return adminDesktopNavGroups(context, currentPage);" in navigation
    assert '<details class="portal-nav-group${group.current === true ? " portal-nav-group--current" : ""}"${open ? " open" : ""}>' in sidebar
    assert 'const open = group.defaultOpen === true || preparedLinks.some((link) => link.current);' in sidebar
    assert 'class="portal-nav-summary"' in sidebar
    assert ".portal-nav-summary" in css
    assert ".portal-nav-group[open] .portal-nav-summary::before" in css


def test_customer_sidebar_uses_five_compact_groups_and_keeps_deep_routes_discoverable() -> None:
    navigation = _section("function navGroups(context, currentPage)", "function matchesRouteFamily(path, root)")
    palette = _section("function commandPaletteItems(context, page)", "function renderCommandPalette(page, context)")
    sidebar = _section("function renderSidebar(page, context)", "function renderHeader(page, context)")
    theme = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")

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
    assert 'label: uiText("nav.currentWorkflow", "Đang mở")' in PORTAL
    assert "current: true" in PORTAL
    assert "const currentGroup = currentCustomerWorkflowGroup(currentPage, groups);" in navigation
    assert "if (currentGroup) groups.unshift(currentGroup);" in navigation
    assert "portal-nav-group--current" in sidebar
    assert ".portal-nav-group--current" in theme
    assert "var(--portal-border-strong)" in theme


def test_current_customer_workflow_cue_supports_video_deep_routes_without_accepting_untrusted_paths() -> None:
    sidebar = _section("function renderSidebar(page, context)", "function renderHeader(page, context)")

    result = _run_current_customer_workflow_harness(ROOT / "static" / "portal" / "portal.js")
    assert result == {
        "videoCuePath": "/video-studio/story-video-plan",
        "videoCueCount": 1,
    }
    assert 'href="${safeText(path)}"' in sidebar


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
