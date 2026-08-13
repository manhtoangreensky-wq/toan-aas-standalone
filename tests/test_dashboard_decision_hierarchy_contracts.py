"""Contracts for a single, truthful next decision on the customer Dashboard.

The Dashboard may reorganize already-scoped Web records into a clearer
customer journey.  It must not use that presentation choice to infer
canonical data, authority or execution capability.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_dashboard_decision_helper_chooses_one_safe_route_from_web_owned_records() -> None:
    helper = _section(PORTAL, "function dashboardDecision(context)", "function dashboardReportedOutput")

    for token in (
        "function dashboardDecision(context)",
        'return { kind: setupProfile.setup_state === "completed" ? "first_session_ready" : "first_session" };',
        'return { kind: "continue_draft", href: "/workspace", secondaryHref: "/features" };',
        'return { kind: "continue_project", href: "/projects", secondaryHref: "/features" };',
        '"/workspace/setup"',
        '"/workspace"',
        '"/projects"',
        '"/features"',
        "dashboardActiveDrafts(context)",
        "validProjectId(item.id)",
    ):
        assert token in helper

    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        "sessionStorage",
        "wallet",
        "jobs",
        "assets",
        "tickets",
        "provider",
        "payment",
        "bridge",
        "capabilities",
    ):
        assert forbidden not in helper.lower()


def test_dashboard_waits_for_both_web_owned_libraries_before_calling_a_session_first() -> None:
    read_state = _section(PORTAL, "function dashboardWebWorkReadState(context)", "function dashboardDecision(context)")
    helper = _section(PORTAL, "function dashboardDecision(context)", "function dashboardReportedOutput")
    guide = _section(PORTAL, "function renderDashboardStartGuide", "function renderDashboardAccountLane")

    for token in (
        "projectCenterReadState(context)",
        "workspaceDraftReadState(context)",
        'return "loading";',
        'return "unavailable";',
    ):
        assert token in read_state

    for token in (
        "const webWorkState = dashboardWebWorkReadState(context);",
        'kind: "loading"',
        'kind: "unavailable"',
        'setupProfile.setup_state === "completed" ? "first_session_ready" : "first_session"',
    ):
        assert token in helper

    first_session_start = helper.index("if (!projects.length && !drafts.length)")
    drafts_start = helper.index("if (drafts.length)")
    assert "href:" not in helper[first_session_start:drafts_start]
    assert 'if (!["first_session", "first_session_ready"].includes(decision.kind)) return "";' in guide


def test_dashboard_preserves_an_explicit_owner_scoped_workspace_draft_read_state() -> None:
    drafts = _section(INTEGRATION, "async function hydrateWorkspaceDrafts", "function canonicalRequestIsCurrent")

    for token in (
        'workspaceDraftReadState: account ? "loading" : "guarded"',
        'workspaceDraftReadState: "loading"',
        'workspaceDraftReadState: "ready"',
        'workspaceDraftReadState: "failed"',
        'workspaceDraftReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.workspaceDraftReadState || ""))',
    ):
        assert token in (INTEGRATION + PORTAL)
    assert 'workspaceDraftReadState: "loading"' in drafts
    assert 'workspaceDraftReadState: "ready"' in drafts
    assert 'workspaceDraftReadState: "failed"' in drafts


def test_dashboard_summary_and_first_session_guide_do_not_duplicate_primary_routes() -> None:
    summary = _section(PORTAL, "function renderDashboardWorkspaceSummary", "function renderDashboardRecentDrafts")
    guide = _section(PORTAL, "function renderDashboardStartGuide", "function renderDashboardAccountLane")

    assert "const decision = dashboardDecision(context);" in summary
    assert 'const summaryActions = ["continue_draft", "continue_project"].includes(decision.kind)' in summary
    assert ': "";' in summary
    assert "dashboardText(`summary.decision.${decision.kind}.action`)" in summary
    assert "dashboardText(`summary.decision.${decision.kind}.secondary`)" in summary
    assert "href=\"/workspace/setup\"" not in summary
    assert "href=\"/projects\"" not in summary
    assert "href=\"/features\"" not in summary

    assert 'if (!["first_session", "first_session_ready"].includes(decision.kind)) return "";' in guide
    assert "number: \"01\"" in guide
    assert "number: \"02\"" in guide
    assert "number: \"03\"" in guide
    assert "linked" not in guide


def test_dashboard_labels_library_destinations_honestly_and_changes_completed_setup_copy() -> None:
    guide = _section(PORTAL, "function renderDashboardStartGuide", "function renderDashboardAccountLane")

    assert 'decision.kind === "first_session_ready"' in guide
    assert 'dashboardText("guide.setupReview.eyebrow")' in guide
    assert 'dashboardText("guide.setupReview.title")' in guide
    assert 'dashboardText("guide.setupReview.body")' in guide
    assert 'dashboardText("guide.setupReview.action")' in guide
    assert 'dashboardText("guide.setup.eyebrow")' in guide
    assert 'dashboardText("guide.setup.title")' in guide
    assert 'dashboardText("guide.setup.body")' in guide
    assert 'dashboardText("guide.setup.action")' in guide
    assert 'const setupStep = setupComplete' in guide
    assert I18N.count('"dashboard.guide.setupReview.title"') == 3
    assert I18N.count('"dashboard.summary.decision.continue_draft.action"') == 3
    assert I18N.count('"dashboard.summary.decision.continue_project.action"') == 3
    for visible_label in (
        "Mở thư viện bản nháp",
        "Open Draft Library",
        "打开草稿库",
        "Mở Project Center",
        "Open Project Center",
        "打开项目中心",
    ):
        assert visible_label in I18N


def test_action_center_only_projects_actionable_canonical_records() -> None:
    action_center = _section(PORTAL, "function renderWorkspaceActionCenter", "function renderStudioLaunchpad")

    assert "const activeCards = cards.filter((card) => card.count > 0);" in action_center
    assert "if (!activeCards.length) return \"\";" in action_center
    assert "activeCards.map" in action_center
    assert "cards.map" not in action_center


def test_action_center_never_advertises_one_incorrect_all_work_destination() -> None:
    action_center = _section(PORTAL, "function renderWorkspaceActionCenter", "function renderStudioLaunchpad")

    assert "const actionCenterTarget = activeCards.length" in action_center
    assert "activeCards.every((card) => card.href === activeCards[0].href)" in action_center
    assert "const headerAction = actionCenterTarget" in action_center
    assert 'href="/jobs">${dashboardText("actionCenter.openAll")}' not in action_center


def test_dashboard_decision_copy_is_present_in_all_supported_locales() -> None:
    keys = (
        "dashboard.summary.decision.continue_draft.action",
        "dashboard.summary.decision.continue_draft.secondary",
        "dashboard.summary.decision.continue_project.action",
        "dashboard.summary.decision.continue_project.secondary",
    )

    for key in keys:
        assert I18N.count(f'"{key}"') == 3


def test_dashboard_mobile_summary_keeps_compact_two_column_metrics() -> None:
    assert "/* Dashboard decision hierarchy -------------------------------------------" in THEME
    decision_layer = THEME[THEME.index("/* Dashboard decision hierarchy -------------------------------------------"):]
    assert re.search(
        r"@media \(max-width: 460px\)\s*\{\s*"
        r"\.portal-workspace-command-center \.portal-dashboard-overview-stats\s*\{\s*"
        r"grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);",
        decision_layer,
        flags=re.DOTALL,
    )


def test_dashboard_summary_does_not_show_zero_for_pending_web_owned_reads() -> None:
    summary = _section(PORTAL, "function renderDashboardWorkspaceSummary", "function renderDashboardRecentDrafts")

    assert 'const webWorkState = dashboardWebWorkReadState(context);' in summary
    assert 'const webWorkReady = webWorkState === "ready";' in summary
    assert 'webWorkReady ? String(projects.length) : "—"' in summary
    assert 'webWorkReady ? String(drafts.length) : "—"' in summary


def test_dashboard_project_refresh_clears_a_prior_project_projection_before_deciding() -> None:
    projects = _section(INTEGRATION, "async function hydrateProjects", "async function hydrateMemoryCenter")

    assert 'const projectReadPath = expectedPath === "/projects" || expectedPath === "/dashboard";' in projects
    assert "if (projectReadPath && projectCenterRequestIsCurrent" in projects
    assert 'projects: [],' in projects
    assert 'projectCenterReadState: "loading",' in projects


def test_dashboard_summary_has_no_cta_for_loading_unavailable_or_first_session() -> None:
    summary = _section(PORTAL, "function renderDashboardWorkspaceSummary", "function renderDashboardRecentDrafts")

    conditional = summary[summary.index("const summaryActions"):summary.index("return `<section")]
    assert 'const summaryActions = ["continue_draft", "continue_project"].includes(decision.kind)' in conditional
    assert ': "";' in conditional
    assert 'href="${safeText(decision.href)}"' in conditional
    assert 'href="${safeText(decision.secondaryHref)}"' in conditional


def test_dashboard_does_not_call_an_unread_workspace_setup_a_first_session() -> None:
    """A failed setup read must never manufacture a first-session guide."""

    helper = _section(PORTAL, "function dashboardDecision(context)", "function dashboardReportedOutput")

    assert 'const workspaceSetupReadState = workspaceSetup.readState === "read_only" ? "read_only" : "unavailable";' in helper
    empty_libraries = helper[helper.index("if (!projects.length && !drafts.length)"):helper.index("if (drafts.length)")]
    assert 'if (workspaceSetupReadState !== "read_only") return { kind: "unavailable" };' in empty_libraries


def test_dashboard_library_cards_preserve_loading_and_unavailable_states() -> None:
    """Empty arrays describe empty libraries only after their signed reads succeed."""

    drafts = _section(PORTAL, "function renderDashboardRecentDrafts", "function renderDashboardRecentProjects")
    projects = _section(PORTAL, "function renderDashboardRecentProjects", "function renderDashboardStartGuide")

    for block, read_state, namespace in (
        (drafts, "workspaceDraftReadState(context)", "drafts"),
        (projects, "projectCenterReadState(context)", "projects"),
    ):
        assert f"const readState = {read_state};" in block
        assert 'readState === "loading"' in block
        assert 'readState !== "ready"' in block
        assert f'dashboardText("{namespace}.loadingTitle")' in block
        assert f'dashboardText("{namespace}.unavailableTitle")' in block
        assert f'dashboardText("{namespace}.emptyTitle")' in block


def test_dashboard_list_hydrators_fail_closed_on_malformed_success_envelopes() -> None:
    """A successful envelope without a list is not evidence of an empty library."""

    projects = _section(INTEGRATION, "async function hydrateProjects", "async function hydrateMemoryCenter")
    drafts = _section(INTEGRATION, "async function hydrateWorkspaceDrafts", "function canonicalRequestIsCurrent")

    for hydrator, state in ((projects, "projectCenterReadState"), (drafts, "workspaceDraftReadState")):
        assert 'if (result.status !== "read_only" || !result.data || !Array.isArray(result.data.items)) {' in hydrator
        assert 'throw new Error("Danh sách Web riêng tư không đúng schema.");' in hydrator
        assert hydrator.index('if (result.status !== "read_only" || !result.data || !Array.isArray(result.data.items)) {') < hydrator.index(f'{state}: "ready"')
        assert "const rawItems = result.data.items;" in hydrator
        assert "if (!rawItems.every((item) => item && valid" in hydrator


def test_dashboard_read_state_copy_is_available_in_every_supported_locale() -> None:
    keys = (
        "dashboard.drafts.loadingTitle",
        "dashboard.drafts.loadingBody",
        "dashboard.drafts.unavailableTitle",
        "dashboard.drafts.unavailableBody",
        "dashboard.projects.loadingTitle",
        "dashboard.projects.loadingBody",
        "dashboard.projects.unavailableTitle",
        "dashboard.projects.unavailableBody",
    )
    for key in keys:
        assert I18N.count(f'"{key}"') == 3


def test_dashboard_truthful_state_fixtures_cover_setup_libraries_and_malformed_lists() -> None:
    """Exercise real Dashboard helpers and list hydrators with safe fixtures."""

    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise Dashboard truthful-state fixtures")
    script = r'''
const fs = require("fs");
const portal = fs.readFileSync(process.argv[1], "utf8");
const integration = fs.readFileSync(process.argv[2], "utf8");
function extract(source, start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end ${end}`);
  return source.slice(offset, finish);
}
const portalRuntime = [
  extract(portal, "function validProjectId", "function projectState"),
  extract(portal, "function projectCenterReadState", "function renderProjectCenterAuthoring"),
  extract(portal, "function dashboardActiveDrafts", "function dashboardReadState"),
  extract(portal, "function workspaceDraftReadState", "function dashboardWebWorkReadState"),
  extract(portal, "function dashboardWebWorkReadState", "function dashboardText"),
  extract(portal, "function dashboardText", "// A Dashboard decision"),
  extract(portal, "function dashboardDecision", "// This is a closed presentation map"),
  extract(portal, "function renderDashboardRecentDrafts", "function renderDashboardRecentProjects"),
  extract(portal, "function renderDashboardRecentProjects", "function renderDashboardStartGuide")
].join("\n");
const ICONS = { prompt: "prompt", refresh: "refresh", security: "security", dashboard: "dashboard", arrowRight: "arrowRight" };
function safeText(value) { return String(value ?? ""); }
function uiText(key) { return key; }
function portalIcon(icon) { return icon; }
function renderEmpty(title, body, icon) { return `empty(${title}|${body}|${icon})`; }
eval(portalRuntime);
const emptyLibraries = { projects: [], workspaceDrafts: [], projectCenterReadState: "ready", workspaceDraftReadState: "ready" };
const setup = (readState) => ({ readState, profile: { setup_state: "not_started" } });
const dashboard = {
  loadingSetup: dashboardDecision({ ...emptyLibraries, workspaceSetup: setup("loading") }).kind,
  guardedSetup: dashboardDecision({ ...emptyLibraries, workspaceSetup: setup("guarded") }).kind,
  readableSetup: dashboardDecision({ ...emptyLibraries, workspaceSetup: setup("read_only") }).kind,
  existingProjectWithoutSetup: dashboardDecision({
    ...emptyLibraries,
    projects: [{ id: "11111111-1111-4111-8111-111111111111", state: "active" }],
    workspaceSetup: setup("guarded")
  }).kind,
  draftCards: {
    loading: renderDashboardRecentDrafts({ workspaceDraftReadState: "loading" }),
    unavailable: renderDashboardRecentDrafts({ workspaceDraftReadState: "failed" }),
    empty: renderDashboardRecentDrafts({ workspaceDraftReadState: "ready", workspaceDrafts: [] })
  },
  projectCards: {
    loading: renderDashboardRecentProjects({ projectCenterReadState: "loading" }),
    unavailable: renderDashboardRecentProjects({ projectCenterReadState: "failed" }),
    empty: renderDashboardRecentProjects({ projectCenterReadState: "ready", projects: [] })
  }
};
async function projectHydrationFixture(response) {
  let projectCenterListHydrationEpoch = 0;
  let projectCenterSessionEpoch = 1;
  let state = { session: { authenticated: true }, projects: [{ id: "stale" }], projectListing: {}, pageStates: {} };
  function base() { return state; }
  function merge(next) { state = { ...state, ...next }; }
  function currentPortalPath() { return "/dashboard"; }
  function projectRouteUsesListView() { return false; }
  function projectFilterPayload(value) { return value && typeof value === "object" ? value : { q: "", state: "all" }; }
  function projectListOffset() { return 0; }
  function projectListingProjection() { return {}; }
  function projectCenterRequestIsCurrent() { return true; }
  function projectListPath() { return "/projects"; }
  function validProjectId(value) { return value === "valid-project"; }
  async function api() { return response; }
  eval(extract(integration, "async function hydrateProjects", "async function hydrateMemoryCenter"));
  await hydrateProjects();
  return state.projectCenterReadState;
}
async function draftHydrationFixture(response) {
  let workspaceDraftHydrationEpoch = 0;
  let workspaceDraftSessionEpoch = 1;
  const WORKSPACE_DRAFT_LIST_LIMIT = 100;
  const WORKSPACE_DRAFT_DASHBOARD_LIST_LIMIT = 100;
  let state = { session: { authenticated: true }, workspaceDrafts: [{ id: "stale" }], workspaceDraftListing: {}, pageStates: {} };
  function base() { return state; }
  function merge(next) { state = { ...state, ...next }; }
  function currentPortalPath() { return "/dashboard"; }
  function workspaceDraftRouteUsesListView() { return false; }
  function workspaceDraftFilterPayload(value) { return value && typeof value === "object" ? value : { q: "", state: "active", feature_key: "" }; }
  function workspaceDraftListOffset() { return 0; }
  function workspaceDraftListingProjection() { return {}; }
  function workspaceDraftRequestIsCurrent() { return true; }
  function workspaceDraftListPath() { return "/workspace/drafts"; }
  function validWorkspaceDraftId(value) { return value === "valid-draft"; }
  async function api() { return response; }
  eval(extract(integration, "async function hydrateWorkspaceDrafts", "function canonicalRequestIsCurrent"));
  await hydrateWorkspaceDrafts();
  return state.workspaceDraftReadState;
}
(async () => {
  const hydration = {
    projectMalformed: await projectHydrationFixture({ status: "read_only", data: {} }),
    projectInvalidStatus: await projectHydrationFixture({ status: "ready", data: { items: [] } }),
    projectInvalidItem: await projectHydrationFixture({ status: "read_only", data: { items: [{ id: "malformed-project" }] } }),
    projectEmpty: await projectHydrationFixture({ status: "read_only", data: { items: [] } }),
    draftMalformed: await draftHydrationFixture({ status: "read_only", data: {} }),
    draftInvalidStatus: await draftHydrationFixture({ status: "ready", data: { items: [] } }),
    draftInvalidItem: await draftHydrationFixture({ status: "read_only", data: { items: [{ id: "malformed-draft" }] } }),
    draftEmpty: await draftHydrationFixture({ status: "read_only", data: { items: [] } })
  };
  process.stdout.write(JSON.stringify({ dashboard, hydration }));
})().catch((error) => { process.stderr.write(error.stack || String(error)); process.exit(1); });
'''
    result = subprocess.run(
        [
            node,
            "-e",
            script,
            str(ROOT / "static" / "portal" / "portal.js"),
            str(ROOT / "static" / "portal" / "integration.js"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    actual = json.loads(result.stdout)
    dashboard = actual["dashboard"]
    assert dashboard["loadingSetup"] == "unavailable"
    assert dashboard["guardedSetup"] == "unavailable"
    assert dashboard["readableSetup"] == "first_session"
    assert dashboard["existingProjectWithoutSetup"] == "continue_project"
    for scope in ("draftCards", "projectCards"):
        assert ".loadingTitle|" in dashboard[scope]["loading"]
        assert ".unavailableTitle|" in dashboard[scope]["unavailable"]
        assert ".emptyTitle|" in dashboard[scope]["empty"]
    assert actual["hydration"] == {
        "projectMalformed": "failed",
        "projectInvalidStatus": "failed",
        "projectInvalidItem": "failed",
        "projectEmpty": "ready",
        "draftMalformed": "failed",
        "draftInvalidStatus": "failed",
        "draftInvalidItem": "failed",
        "draftEmpty": "ready",
    }
