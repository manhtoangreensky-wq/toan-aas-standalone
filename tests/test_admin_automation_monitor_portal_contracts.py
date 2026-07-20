"""Static contracts for the identifier-free Admin Automation Monitor portal."""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
NAVIGATION = (ROOT / "copyfast_admin_erp_navigation.py").read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    return source[match.start():match.end() + following.start() if following else len(source)]


def test_admin_automation_monitor_is_a_separate_local_admin_native_route() -> None:
    assert 'WebFeature("admin_automation", "Automation Monitor", "admin", "/admin/automation", "admin"' in REGISTRY
    assert '"web_automation_monitor"' in NAVIGATION
    assert '"/admin/automation"' in NAVIGATION
    assert 'elif normalized == "/admin/automation":\n        copyfast_auth.require_admin(request)' in APP
    assert 'adminPage("/admin/automation", "Automation Monitor"' in PORTAL
    assert 'layout: "admin-automation-monitor", action: "none", status: "read_only"' in PORTAL
    assert 'case "admin-automation-monitor": return renderAdminAutomationMonitor(page, context);' in PORTAL
    assert 'function isNativeAdminAutomationMonitorPath(path)' in INTEGRATION
    native = _function_source(INTEGRATION, "isNativeAdminAutomationMonitorPath")
    assert '"/admin/automation"' in native
    bridge_gate = INTEGRATION[INTEGRATION.index("if (bridgeAvailable &&") :]
    bridge_gate = bridge_gate[:1_500]
    assert "!isNativeAdminAutomationMonitorPath(currentPath)" in bridge_gate


def test_portal_uses_dedicated_redacted_read_state_and_stale_response_fence() -> None:
    for declaration in (
        "let adminAutomationMonitorSessionEpoch = 0;",
        "let adminAutomationMonitorHydrationEpoch = 0;",
        "++adminAutomationMonitorSessionEpoch;",
        "++adminAutomationMonitorHydrationEpoch;",
        "adminAutomationMonitorSummary: {}",
        "adminAutomationMonitorRuns: []",
        "adminAutomationMonitorReadState: account && adminAutomationMonitorEnabled ? \"loading\" : \"guarded\"",
        'if (account && adminAutomationMonitorEnabled && currentPath === "/admin/automation")',
        "function adminAutomationMonitorRequestIsCurrent",
        'expectedPath === "/admin/automation"',
        "currentPortalPath() === expectedPath",
        "base().adminAutomationMonitorEnabled === true",
    ):
        assert declaration in INTEGRATION

    hydrator = _function_source(INTEGRATION, "hydrateAdminAutomationMonitor")
    for required in (
        'api("/admin/automation/summary", { cache: "no-store" })',
        "api(adminAutomationMonitorRunsPath(offset), { cache: \"no-store\" })",
        "adminAutomationMonitorSummaryProjection",
        "adminAutomationMonitorRunsProjection",
        "adminAutomationMonitorRequestIsCurrent",
        'adminAutomationMonitorReadState: "loading"',
        'adminAutomationMonitorSummary: {},',
        'adminAutomationMonitorRuns: [],',
        'adminAutomationMonitorReadState: "failed"',
        '"/admin/automation": "guarded"',
    ):
        assert required in hydrator
    for forbidden in ("bridgeAvailable", "setInterval", "showNotification", "/internal/v1/notifications/tick", "method: \"POST\""):
        assert forbidden not in hydrator
    assert hydrator.index('adminAutomationMonitorReadState: "loading"') < hydrator.index("await Promise.all")
    assert 'function setAdminAutomationMonitorReadBusy(route, busy)' in INTEGRATION


def test_projection_is_closed_and_excludes_scheduler_identifiers_and_receipt_content() -> None:
    for helper in (
        "adminAutomationMonitorRunProjection",
        "adminAutomationMonitorSchedulerProjection",
        "adminAutomationMonitorSummaryProjection",
        "adminAutomationMonitorRunsProjection",
    ):
        assert f"function {helper}" in INTEGRATION
    projection = _function_source(INTEGRATION, "adminAutomationMonitorRunProjection")
    assert 'new Set(["state", "action_count", "candidate_count", "started_at", "finished_at"])' in projection
    for forbidden in ("id", "request_id", "nonce", "hmac", "lease", "receipt_json", "source_id", "account_id", "error_code"):
        assert not re.search(rf"\b{re.escape(forbidden)}\b", projection.lower())
    summary = _function_source(INTEGRATION, "adminAutomationMonitorSummaryProjection")
    assert '"scheduler", "latest_run", "run_counts", "integrity_guarded"' in summary
    assert 'scheduler.state === "center_disabled"' in summary
    assert 'scheduler.state === "guarded" && latest === null && source.integrity_guarded === false' in summary
    renderer = _function_source(PORTAL, "renderAdminAutomationMonitor")
    assert "serverAuthorizesAdminRoute(context, \"/admin/automation\")" in renderer
    assert 'data-portal-action="admin-automation-monitor-refresh"' in renderer
    assert 'data-portal-action="admin-automation-monitor-page"' in renderer
    for forbidden in ("localStorage", "sessionStorage", "fetch(", "/internal/", "idempotency", "csrf"):
        assert forbidden.lower() not in renderer.lower()
    assert 'data-state="guarded"' in renderer
    assert "Đang xác minh receipt private" in renderer
    assert 'data-state="${loading ? "processing"' not in renderer
    assert "counts.unknown > 0" in renderer
    assert "Chưa xác minh" in renderer
    assert "adminAutomationMonitorIntegrityGuarded" in renderer
    assert "visibleCounts = integrityGuarded ? null : counts" in renderer


def test_monitor_has_only_read_refresh_actions_and_keeps_pwa_paths_private() -> None:
    for action in ("admin-automation-monitor-refresh", "admin-automation-monitor-page"):
        assert action in PORTAL and f'action === "{action}"' in INTEGRATION
    action_region = INTEGRATION[INTEGRATION.index('if (action === "admin-automation-monitor-refresh")'):INTEGRATION.index('if (action === "operations-refresh")')]
    for forbidden in ("method: \"POST\"", "PayOS", "wallet", "provider", "telegram", "deploy", "tick", "retry", "freeze"):
        assert forbidden.lower() not in action_region.lower()
    assert action_region.count("setAdminAutomationMonitorReadBusy(route, true);") == 2
    assert action_region.count("setAdminAutomationMonitorReadBusy(route, false);") == 2
    assert '"/" + "api/v1/admin"' in SERVICE_WORKER
    assert '"/admin"' in SERVICE_WORKER
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/admin/automation"' not in shell
