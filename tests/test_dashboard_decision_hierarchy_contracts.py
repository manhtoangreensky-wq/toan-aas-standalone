"""Contracts for a single, truthful next decision on the customer Dashboard.

The Dashboard may reorganize already-scoped Web records into a clearer
customer journey.  It must not use that presentation choice to infer
canonical data, authority or execution capability.
"""

from __future__ import annotations

import re
from pathlib import Path


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
