"""Focused UI/security contracts for the Workspace Command Center."""

import json
import re
from pathlib import Path

import copyfast_pages


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "WORKSPACE_COMMAND_CENTER_CONTRACT.md").read_text(encoding="utf-8")


def dashboard_surface() -> str:
    start = PORTAL.index("function dashboardReadState")
    end = PORTAL.index("function renderWorkspaceActionCenter", start)
    return PORTAL[start:end]


def canonical_hydration() -> str:
    start = INTEGRATION.index("async function hydrateCanonicalData()")
    end = INTEGRATION.index("async function payloadFor", start)
    return INTEGRATION[start:end]


def dashboard_shell_payload() -> dict[str, object]:
    response = copyfast_pages.render_portal("/dashboard", interface_locale="en")
    assert response.status_code == 200
    match = re.search(
        r'<script id="portal-bootstrap" type="application/json">(.*?)</script>',
        response.body.decode("utf-8"),
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_dashboard_keeps_one_existing_route_and_a_real_app_workspace_renderer() -> None:
    surface = dashboard_surface()
    assert 'customerPage("/dashboard", "Không gian làm việc"' in PORTAL
    assert 'case "dashboard": return renderDashboard(page, context);' in PORTAL
    assert "function renderDashboardAccountLane" in surface
    assert "function renderDashboardCanonicalLane" in surface
    assert 'class="portal-page portal-dashboard-app portal-workspace-command-center"' in surface
    assert "/workspace-command-center" not in PORTAL
    payload = dashboard_shell_payload()
    assert payload["path"] == "/dashboard"
    assert isinstance(payload["title"], str)
    assert "_title_for" in PAGES


def test_dashboard_separates_web_native_account_and_canonical_lanes() -> None:
    surface = dashboard_surface()
    root = surface[surface.index("function renderDashboard(page, context)"):]
    for token in (
        "Continue Web work",
        "renderDashboardRecentProjects(context)",
        "renderDashboardRecentDrafts(context)",
        "renderDashboardAccountLane(context)",
        "renderDashboardCanonicalLane(context, readState)",
        "renderDashboardStartGuide(context)",
        "renderStudioLaunchpad(context)",
    ):
        assert token in root
    for token in ("Account & Security", "Canonical integration"):
        assert token in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "bridge_request", "CORE_BRIDGE"):
        assert forbidden.lower() not in root.lower()


def test_dashboard_uses_typed_read_state_and_never_disguises_unread_counts_as_zero() -> None:
    surface = dashboard_surface()
    assert 'dashboardReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.dashboardReadState || ""))' in PORTAL
    assert "function dashboardReadState(context)" in surface
    summary = surface[
        surface.index("function renderDashboardWorkspaceSummary"):
        surface.index("function renderDashboardRecentDrafts")
    ]
    for token in (
        'const canonicalReady = readState === "ready";',
        'const processing = canonicalReady ?',
        'const deliveryReady = canonicalReady ?',
        'readState === "failed"',
        "Cần làm mới",
    ):
        assert token in summary
    canonical = surface[surface.index("function renderDashboardCanonicalLane"):surface.index("function renderDashboard(page, context)")]
    for token in (
        'if (readState === "loading")',
        'if (readState === "failed")',
        'if (readState !== "ready")',
        'data-portal-action="dashboard-refresh"',
        "Dashboard đã xóa projection canonical cũ",
        "Không dùng placeholder để thay thế một output đã được xác minh.",
    ):
        assert token in canonical


def test_dashboard_canonical_hydration_clears_before_read_and_fails_closed() -> None:
    hydration = canonical_hydration()
    dashboard = hydration[
        hydration.index('if (path === "/dashboard")'):
        hydration.index('} else if (path === "/pricing")')
    ]
    for token in (
        "wallet: null",
        "jobs: []",
        "assets: []",
        "tickets: []",
        "readiness: {}",
        'dashboardReadState: "loading"',
        'api("/wallet")',
        'api("/jobs")',
        'api("/assets")',
        'api("/features/status")',
        'api("/support/tickets")',
        'dashboardReadState: "ready"',
    ):
        assert token in dashboard
    assert dashboard.index('dashboardReadState: "loading"') < dashboard.index('const [wallet, jobs, assets, readiness, tickets] = await Promise.all([')
    assert 'api("/support/tickets").catch' not in dashboard
    failure = hydration[hydration.index("} catch (error) {"):]
    assert 'if (path === "/dashboard")' in failure
    assert 'dashboardReadState: "failed"' in failure
    for token in ("wallet: null", "jobs: []", "assets: []", "tickets: []", "readiness: {}"):
        assert token in failure
    assert 'dashboardReadState: account && bridgeAvailable ? "loading" : "guarded"' in INTEGRATION
    assert '"dashboard-refresh": Boolean(account && bridgeAvailable)' in INTEGRATION


def test_dashboard_malformed_success_payloads_fail_closed_before_ready() -> None:
    hydration = canonical_hydration()
    dashboard = hydration[
        hydration.index('if (path === "/dashboard")'):
        hydration.index('} else if (path === "/pricing")')
    ]
    validators = INTEGRATION[
        INTEGRATION.index("function dashboardCanonicalRecord"):
        INTEGRATION.index("async function hydrateCanonicalData()")
    ]
    for token in (
        "function dashboardCanonicalSnapshot",
        "function dashboardCanonicalRows",
        "Array.isArray(data.items)",
        "typeof item.id === \"string\"",
        "typeof item.status === \"string\"",
        "Number.isSafeInteger(wallet.balance_xu)",
        "Number.isSafeInteger(wallet.total_spent_xu)",
        "typeof wallet.is_vip === \"boolean\"",
        "dashboardCanonicalRecord(readiness.features)",
        'throw new Error("Dashboard canonical snapshot không đúng schema.")',
    ):
        assert token in validators
    assert "const snapshot = dashboardCanonicalSnapshot(wallet, jobs, assets, readiness, tickets);" in dashboard
    assert dashboard.index("const snapshot = dashboardCanonicalSnapshot") < dashboard.index('dashboardReadState: "ready"')
    for token in (
        "wallet: snapshot.wallet",
        "jobs: snapshot.jobs",
        "assets: snapshot.assets",
        "tickets: snapshot.tickets",
        "readiness: snapshot.readiness",
    ):
        assert token in dashboard


def test_dashboard_retry_is_signed_and_does_not_create_write_authority() -> None:
    handler = INTEGRATION[
        INTEGRATION.index('if (action === "dashboard-refresh")'):
        INTEGRATION.index('if (action === "campaign-update")', INTEGRATION.index('if (action === "dashboard-refresh")'))
    ]
    for token in (
        'route !== "/dashboard"',
        'currentPortalPath() !== "/dashboard"',
        'capabilities["dashboard-refresh"] === true',
        "await hydrateCanonicalData();",
        'base().dashboardReadState',
    ):
        assert token in handler
    for forbidden in ("method: \"POST\"", "payos", "wallet", "provider", "refund", "charge"):
        assert forbidden.lower() not in handler.lower()


def test_dashboard_is_private_in_pwa_and_uses_app_first_mobile_ui_rules() -> None:
    private_prefixes = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/dashboard"' in private_prefixes
    assert '"/dashboard"' not in shell
    command_center_css = CSS[CSS.index("/* Workspace Command Center"):]
    for token in (
        ".portal-workspace-command-center",
        ".portal-command-center-lanes",
        ".portal-command-center-canonical",
        "min-height: 44px",
        "@media (prefers-reduced-motion: reduce)",
        ".portal-command-center-lane--work .portal-dashboard-draft { transition: none; }",
    ):
        assert token in command_center_css
    assert "linear-gradient" not in command_center_css


def test_dashboard_contract_records_authority_non_goals_and_failure_semantics() -> None:
    for token in (
        "`/dashboard`",
        "Continue Web work",
        "Canonical integration",
        "`dashboardReadState`",
        "GET /api/v1/wallet",
        "GET /api/v1/support/tickets",
        "PayOS",
        "Service Worker",
        "44px",
        "database table/migration mới",
    ):
        assert token in CONTRACT
