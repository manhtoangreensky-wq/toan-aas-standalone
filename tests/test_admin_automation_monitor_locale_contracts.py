"""Contracts for reviewed Admin Automation Monitor locale chrome.

The interface locale changes only Portal-owned presentation. It must not widen
the signed, read-only Automation Monitor's authorization or control boundary.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    return source[match.start():match.end() + following.start() if following else len(source)]


def test_automation_monitor_fixed_copy_uses_reviewed_locale_catalogue() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")
    pages = _read("copyfast_pages.py")
    renderer = _function_source(portal, "renderAdminAutomationMonitor")
    page_titles = _function_source(portal, "localizedPageTitle")
    page_descriptions = _function_source(portal, "localizedPageDescription")

    for key in (
        "adminGeneric.automationMonitor.route.title",
        "adminGeneric.automationMonitor.route.description",
        "adminGeneric.automationMonitor.state.loadingTitle",
        "adminGeneric.automationMonitor.state.loadingBody",
        "adminGeneric.automationMonitor.state.unavailableTitle",
        "adminGeneric.automationMonitor.state.unavailableBody",
        "adminGeneric.automationMonitor.scheduler.ready",
        "adminGeneric.automationMonitor.scheduler.centerDisabled",
        "adminGeneric.automationMonitor.scheduler.automationDisabled",
        "adminGeneric.automationMonitor.scheduler.persistentStoreUnverified",
        "adminGeneric.automationMonitor.scheduler.topologyUnverified",
        "adminGeneric.automationMonitor.scheduler.singleReplicaRequired",
        "adminGeneric.automationMonitor.scheduler.limitsUnverified",
        "adminGeneric.automationMonitor.scheduler.guarded",
        "adminGeneric.automationMonitor.scheduler.started",
        "adminGeneric.automationMonitor.scheduler.completed",
        "adminGeneric.automationMonitor.scheduler.failed",
        "adminGeneric.automationMonitor.metric.aria",
        "adminGeneric.automationMonitor.metric.inboxCenter.label",
        "adminGeneric.automationMonitor.metric.scheduler.label",
        "adminGeneric.automationMonitor.metric.latestReceipt.label",
        "adminGeneric.automationMonitor.metric.completedReceipt.label",
        "adminGeneric.automationMonitor.metric.enabled",
        "adminGeneric.automationMonitor.metric.disabled",
        "adminGeneric.automationMonitor.metric.observing",
        "adminGeneric.automationMonitor.metric.pendingVerification",
        "adminGeneric.automationMonitor.metric.redactedCounter",
        "adminGeneric.automationMonitor.metric.noExternalDelivery",
        "adminGeneric.automationMonitor.latest.copyWithReceipt",
        "adminGeneric.automationMonitor.latest.copyWithoutReceipt",
        "adminGeneric.automationMonitor.latest.detailWithReceipt",
        "adminGeneric.automationMonitor.latest.detailWithoutReceipt",
        "adminGeneric.automationMonitor.latest.emptyTitle",
        "adminGeneric.automationMonitor.run.actionCandidateCaption",
        "adminGeneric.automationMonitor.run.emptyTitle",
        "adminGeneric.automationMonitor.run.emptyBody",
        "adminGeneric.automationMonitor.run.previousPage",
        "adminGeneric.automationMonitor.run.nextPage",
        "adminGeneric.automationMonitor.run.refresh",
        "adminGeneric.automationMonitor.aggregate.title",
        "adminGeneric.automationMonitor.aggregate.guardedTitle",
        "adminGeneric.automationMonitor.aggregate.guardedBody",
        "adminGeneric.automationMonitor.aggregate.unknownTitle",
        "adminGeneric.automationMonitor.aggregate.unknownBody",
        "adminGeneric.automationMonitor.aggregate.unknownLabel",
        "adminGeneric.automationMonitor.aggregate.unknownNote",
        "adminGeneric.automationMonitor.aggregate.healthyBody",
        "adminGeneric.automationMonitor.aggregate.startedLabel",
        "adminGeneric.automationMonitor.aggregate.startedNote",
        "adminGeneric.automationMonitor.aggregate.completedLabel",
        "adminGeneric.automationMonitor.aggregate.completedNote",
        "adminGeneric.automationMonitor.aggregate.failedLabel",
        "adminGeneric.automationMonitor.aggregate.failedNote",
        "adminGeneric.automationMonitor.aggregate.guardedLabel",
        "adminGeneric.automationMonitor.aggregate.guardedNote",
        "adminGeneric.automationMonitor.history.title",
        "adminGeneric.automationMonitor.history.body",
        "adminGeneric.automationMonitor.intro.kicker",
        "adminGeneric.automationMonitor.intro.title",
        "adminGeneric.automationMonitor.intro.body",
        "adminGeneric.automationMonitor.intro.preflightLabel",
        "adminGeneric.automationMonitor.intro.preflightValue",
        "adminGeneric.automationMonitor.intro.readOnlyLabel",
        "adminGeneric.automationMonitor.intro.guardedLabel",
        "adminGeneric.automationMonitor.intro.noMutation",
        "adminGeneric.automationMonitor.boundary.kicker",
        "adminGeneric.automationMonitor.boundary.noControlPlane.title",
        "adminGeneric.automationMonitor.boundary.noControlPlane.body",
        "adminGeneric.automationMonitor.boundary.noIdentifiers",
        "adminGeneric.automationMonitor.boundary.noActions",
        "adminGeneric.automationMonitor.boundary.refreshReadOnly",
    ):
        assert i18n.count(f'"{key}"') == 3

    assert "function adminAutomationMonitorText(key, fallback, params)" in portal
    assert "adminAutomationMonitorText(" in renderer
    assert '"Automation Monitor": "adminGeneric.automationMonitor.route.title"' in portal
    assert 'if (path === "/admin/automation") return adminAutomationMonitorText("route.title", fallback);' in page_titles
    assert 'if (path === "/admin/automation") return adminAutomationMonitorText("route.description", fallback);' in page_descriptions
    assert 'data-portal-action="admin-automation-monitor-refresh"' in renderer
    assert 'data-portal-action="admin-automation-monitor-page"' in renderer
    for forbidden in ("fetch(", "/internal/", "localStorage", "sessionStorage"):
        assert forbidden.lower() not in renderer.lower()
    assert not re.search(
        r"""["']?method["']?\s*:\s*["']post["']""",
        renderer,
        flags=re.IGNORECASE,
    )
    assert (
        '"/admin/automation": {"vi": "Automation Monitor · TOAN AAS", '
        '"en": "Automation Monitor · TOAN AAS", '
        '"zh": "自动化监控 · TOAN AAS"}'
    ) in pages


def test_automation_monitor_routes_every_fixed_renderer_label_through_presentation_helpers() -> None:
    portal = _read("static/portal/portal.js")
    renderer = _function_source(portal, "renderAdminAutomationMonitor")
    state_label = _function_source(portal, "automationMonitorStateLabel")
    count = _function_source(portal, "automationMonitorCount")

    assert "const text = (key, fallback, params) => adminAutomationMonitorText(key, fallback, params);" in renderer
    assert "localizedNumber(value)" in count

    for key in (
        "scheduler.ready",
        "scheduler.centerDisabled",
        "scheduler.automationDisabled",
        "scheduler.persistentStoreUnverified",
        "scheduler.topologyUnverified",
        "scheduler.singleReplicaRequired",
        "scheduler.limitsUnverified",
        "scheduler.guarded",
        "scheduler.started",
        "scheduler.completed",
        "scheduler.failed",
    ):
        assert f'adminAutomationMonitorText("{key}"' in state_label

    for key in (
        "state.loadingTitle",
        "state.loadingBody",
        "state.unavailableTitle",
        "state.unavailableBody",
        "metric.aria",
        "metric.inboxCenter.label",
        "metric.scheduler.label",
        "metric.latestReceipt.label",
        "metric.completedReceipt.label",
        "metric.enabled",
        "metric.disabled",
        "metric.observing",
        "metric.pendingVerification",
        "metric.redactedCounter",
        "metric.noExternalDelivery",
        "latest.copyWithReceipt",
        "latest.copyWithoutReceipt",
        "latest.detailWithReceipt",
        "latest.detailWithoutReceipt",
        "latest.emptyTitle",
        "run.actionCandidateCaption",
        "run.emptyTitle",
        "run.emptyBody",
        "run.previousPage",
        "run.nextPage",
        "run.refresh",
        "aggregate.title",
        "aggregate.guardedTitle",
        "aggregate.guardedBody",
        "aggregate.unknownTitle",
        "aggregate.unknownBody",
        "aggregate.unknownLabel",
        "aggregate.unknownNote",
        "aggregate.healthyBody",
        "aggregate.startedLabel",
        "aggregate.startedNote",
        "aggregate.completedLabel",
        "aggregate.completedNote",
        "aggregate.failedLabel",
        "aggregate.failedNote",
        "aggregate.guardedLabel",
        "aggregate.guardedNote",
        "history.title",
        "history.body",
        "intro.kicker",
        "intro.title",
        "intro.body",
        "intro.preflightValue",
        "intro.readOnlyLabel",
        "intro.guardedLabel",
        "intro.noMutation",
        "boundary.kicker",
        "boundary.noControlPlane.title",
        "boundary.noControlPlane.body",
        "boundary.noIdentifiers",
        "boundary.noActions",
        "boundary.refreshReadOnly",
    ):
        assert f'text("{key}"' in renderer

    # Translation interpolation itself is intentionally plain text.  The
    # receipt-derived values passed to these strings must remain escaped only
    # after the locale template has been resolved.
    for key in (
        "latest.copyWithReceipt",
        "latest.detailWithReceipt",
        "run.actionCandidateCaption",
        "intro.body",
    ):
        assert f'safeText(text("{key}"' in renderer


def test_automation_monitor_receipt_timestamps_follow_the_active_interface_locale() -> None:
    portal = _read("static/portal/portal.js")
    renderer = _function_source(portal, "renderAdminAutomationMonitor")
    timestamp = _function_source(portal, "automationMonitorTimestamp")

    assert "localizedDateTime" in timestamp
    assert "dateStyle" in timestamp and "timeStyle" in timestamp
    assert "supportCaseTimestamp(" not in renderer
    assert renderer.count("automationMonitorTimestamp(") >= 2
