"""Static contracts for the Web-native manual Analytics Workspace portal.

These checks intentionally cover the browser boundary rather than visual
snapshots: route ownership, private hydration, signed mutations, transparent
manual-data language and PWA cache exclusion.  The UI must never become a
disguised Bot/platform/provider/revenue dashboard.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "copyfast_analytics_workspace.py").read_text(encoding="utf-8")
DATABASE = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
API = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _analytics_surface() -> str:
    start = PORTAL.index("const ANALYTICS_REPORT_STATES")
    return PORTAL[start:PORTAL.index("const DOCUMENT_WORKSPACE_TYPES", start)]


def _analytics_helpers() -> str:
    start = INTEGRATION.index("const ANALYTICS_REPORT_STATES")
    return INTEGRATION[start:INTEGRATION.index("// Document & PDF Workspace", start)]


def _analytics_actions() -> str:
    start = INTEGRATION.index('if (action === "analytics-report-manual-csv-export")')
    return INTEGRATION[start:INTEGRATION.index('if (action === "document-workspace-refresh")', start)]


def _analytics_manual_csv_helper() -> str:
    start = INTEGRATION.index("async function downloadAnalyticsManualCsvExport(")
    return INTEGRATION[start:INTEGRATION.index("function memoryReminderPayload", start)]


def test_analytics_workspace_is_a_native_private_route_family() -> None:
    for needle in (
        'customerPage("/analytics", "Analytics Workspace"',
        'customerPage("/analytics/new", "Báo cáo thủ công mới"',
        'path: "/analytics/:id"',
        "function renderAnalyticsWorkspace(page, context)",
        "function renderAnalyticsWorkspaceDetail(page, context)",
        'case "analytics-workspace": return renderAnalyticsWorkspace(page, context);',
        'case "analytics-workspace-detail": return renderAnalyticsWorkspaceDetail(page, context);',
        'if (linkPath === "/analytics") return matchesRouteFamily(path, "/analytics")',
    ):
        assert needle in PORTAL
    assert "ANALYTICS_WORKSPACE_PATH" in PAGES
    assert "ANALYTICS_WORKSPACE_PATH.fullmatch(normalized)" in PAGES
    assert 'analyticsBotCompanionPage("/analytics"' not in PORTAL

    for needle in (
        "function analyticsReportIdFromPath(path)",
        "function isNativeAnalyticsWorkspacePath(path)",
        "isNativeAnalyticsWorkspacePath(currentPath)",
        "else if (isNativeAnalyticsWorkspacePath(currentPath))",
    ):
        assert needle in INTEGRATION


def test_analytics_portal_makes_manual_only_boundary_visible_and_verifiable() -> None:
    helpers = _analytics_helpers()
    for helper in (
        "analyticsWorkspaceSafetyError",
        "analyticsReportPayload",
        "analyticsMetricPayload",
        "analyticsSnapshotPayload",
        "analyticsFindingPayload",
        "analyticsWorkspaceBoundaryIsSafe",
    ):
        assert f"function {helper}" in helpers
    for flag in (
        'boundary.execution === "manual_measurement_only"',
        'boundary.data_origin === "user_supplied_only"',
        "boundary.local_calculation === true",
        "boundary.bot_called === false",
        "boundary.provider_called === false",
        "boundary.social_api_called === false",
        "boundary.platform_data_connected === false",
        "boundary.platform_data_verified === false",
        "boundary.ai_recommendation_created === false",
        "boundary.canonical_revenue === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_processed === false",
        "boundary.job_created === false",
        "boundary.publish_action_created === false",
        "boundary.browser_file_upload === false",
        "boundary.external_url_import === false",
        "boundary.report_file_created === false",
        'boundary.output_delivery === "not_applicable"',
    ):
        assert flag in helpers

    surface = _analytics_surface()
    for copy in (
        "Manual-only boundary",
        "Ghi nhận có trách nhiệm, không giả analytics",
        "Platform / live API",
        "Bot / provider report",
        "AI insight / revenue",
        "Wallet / publish / CSV Campaign canonical",
        "CSV dữ liệu Web thủ công chỉ có thể xuất riêng",
        "Portal không tạo số liệu mẫu hoặc chart giả.",
        "không phải AI insight",
    ):
        assert copy in surface
    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        'data-portal-action="analytics-workspace-execute"',
        'data-portal-action="analytics-workspace-download"',
        'data-portal-action="analytics-workspace-export"',
        'data-portal-action="analytics-workspace-import"',
    ):
        assert forbidden not in surface


def test_analytics_hydrates_owner_scoped_records_and_rejects_unsafe_browser_data() -> None:
    for helper in (
        "analyticsWorkspaceListOptions",
        "analyticsWorkspaceReportsPath",
        "analyticsWorkspacePagination",
        "hydrateAnalyticsWorkspace",
        "hydrateAnalyticsReport",
        "refreshAnalyticsWorkspaceAfterMutation",
        "analyticsWorkspaceMutation",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    for endpoint in (
        'api("/analytics-workspace/summary")',
        'api("/analytics-workspace/references")',
        'api("/analytics-workspace/policy")',
        '"/analytics-workspace/reports?" + query.join("&")',
        'api("/analytics-workspace/reports/" + encodeURIComponent(String(reportId)))',
    ):
        assert endpoint in INTEGRATION
    for capability in (
        '"analytics-workspace-view": Boolean(account && analyticsWorkspaceEnabled)',
        '"analytics-report-create": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled)',
        '"analytics-snapshot-create": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled)',
        '"analytics-finding-create": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled)',
    ):
        assert capability in INTEGRATION
    for safety in (
        "analyticsWorkspaceSafetyError(q)",
        "data_origin === \"user_supplied_only\"",
        "item.platform_data_verified === false",
        "item.source_kind === \"manual_entry\"",
        "item.ai_recommendation_created === false",
        "analyticsWorkspaceSessionEpoch",
        "analyticsWorkspaceListHydrationEpoch",
        "analyticsWorkspaceDetailHydrationEpoch",
        "analyticsWorkspaceRequestIsCurrent",
    ):
        assert safety in INTEGRATION


def test_analytics_hydration_fences_session_list_detail_and_current_signed_path() -> None:
    """Report hydration must reject late reads after session or route changes."""
    for name in (
        "analyticsWorkspaceSessionEpoch",
        "analyticsWorkspaceListHydrationEpoch",
        "analyticsWorkspaceDetailHydrationEpoch",
    ):
        assert re.search(r"(?:\+\+|\+=\s*1)" + re.escape(name), INTEGRATION), name
    assert INTEGRATION.count("analyticsWorkspaceRequestIsCurrent(") >= 3
    assert "const sessionEpoch = analyticsWorkspaceSessionEpoch;" in INTEGRATION
    assert "const requestEpoch = ++analyticsWorkspaceListHydrationEpoch;" in INTEGRATION
    assert "const requestEpoch = ++analyticsWorkspaceDetailHydrationEpoch;" in INTEGRATION
    assert "if (!analyticsWorkspaceRequestIsCurrent(" in INTEGRATION
    assert "currentPortalPath()" in INTEGRATION


def test_analytics_forms_mutate_via_csrf_idempotent_receipts_then_rehydrate() -> None:
    actions = _analytics_actions()
    for action in (
        "analytics-workspace-refresh",
        "analytics-workspace-filter",
        "analytics-workspace-page",
        "analytics-report-create",
        "analytics-report-update",
        "analytics-report-lifecycle",
        "analytics-report-restore-version",
        "analytics-report-manual-csv-export",
        "analytics-metric-create",
        "analytics-metric-update",
        "analytics-metric-state",
        "analytics-snapshot-create",
        "analytics-snapshot-update",
        "analytics-snapshot-state",
        "analytics-finding-create",
        "analytics-finding-update",
        "analytics-finding-state",
    ):
        assert f'action === "{action}"' in actions
        assert action in PORTAL
    assert "async function analyticsWorkspaceMutation(" in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "analyticsWorkspaceBoundaryIsSafe(data)" in actions
    assert "refreshAnalyticsWorkspaceAfterMutation(reportId)" in actions
    for attr in (
        "__analyticsReportId",
        "__analyticsReportRevision",
        "__analyticsMetricId",
        "__analyticsMetricRevision",
        "__analyticsSnapshotId",
        "__analyticsSnapshotRevision",
        "__analyticsFindingId",
        "__analyticsFindingRevision",
        "__analyticsWorkspaceOffset",
    ):
        assert attr in PORTAL
    for forbidden in ("bridgeAvailable", "PayOS", "wallet", "telegram", "/payments", "/jobs", "publish"):
        assert forbidden.lower() not in actions.lower()
    for forbidden in (
        'analytics-workspace-export',
        'analytics-workspace-download',
        'analytics-workspace-import',
    ):
        assert forbidden not in actions


def test_analytics_manual_csv_export_is_a_narrow_finalized_server_attachment() -> None:
    """CSV is a separately flagged attachment, never a browser or Bot report export."""
    helper = _analytics_manual_csv_helper()
    for required in (
        "async function downloadAnalyticsManualCsvExport(reportId, expectedRevision)",
        "context.analyticsManualCsvExportEnabled !== true",
        'capabilities["analytics-report-manual-csv-export"] !== true',
        'context.analyticsWorkspaceReadState !== "ready"',
        "context.analyticsReportDetail",
        'String(report.state || "").trim().toLowerCase() !== "finalized"',
        'Accept: "text/csv, application/json"',
        '"X-CSRF-Token": csrfToken',
        'body: JSON.stringify({ expected_revision: revision })',
        "method: \"POST\"",
        "credentials: \"same-origin\"",
        "/analytics-workspace/reports/${encodeURIComponent(normalizedId)}/export.csv",
        'contentType.startsWith("text/csv")',
        'disposition.includes("attachment")',
        "24 * 1024 * 1024",
        "await response.blob()",
        "URL.createObjectURL(blob)",
        'anchor.download = "toan-aas-manual-analytics.csv"',
        "URL.revokeObjectURL(objectUrl)",
        "separate from Bot /campaign/report",
    ):
        assert required in helper
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "window.open(", "new Blob(", "join(\",\")"):
        assert forbidden not in helper

    detail_start = PORTAL.index("function renderAnalyticsWorkspaceDetail(page, context)")
    detail = PORTAL[detail_start:PORTAL.index("// This is a private authoring surface.", detail_start)]
    for required in (
        'const finalizedForCsv = state === "finalized"',
        "context.analyticsManualCsvExportEnabled === true",
        'context.capabilities["analytics-report-manual-csv-export"] === true',
        'class="portal-card portal-card-pad portal-analytics-manual-csv"',
        "CSV dữ liệu Web thủ công",
        "Không phải báo cáo Campaign/Bot",
        "doanh thu, Xu, PayOS, provider hoặc AI insight",
        'data-portal-action="analytics-report-manual-csv-export"',
        "analyticsDataAttrs(report, null, null, null)",
        'href="/campaign/report"',
        "Không lưu file, không tạo asset/job/delivery.",
    ):
        assert required in detail
    assert "fetch(" not in detail
    assert "localStorage" not in detail

    actions = _analytics_actions()
    for required in (
        'if (action === "analytics-report-manual-csv-export")',
        'capabilities["analytics-report-manual-csv-export"] !== true',
        "currentPortalPath() !== route",
        "setActionBusy(action, route, true)",
        "await downloadAnalyticsManualCsvExport(reportId, expectedRevision)",
    ):
        assert required in actions
    assert "analyticsManualCsvExportEnabled: source.analyticsManualCsvExportEnabled === true" in PORTAL

    for required in (
        '@router.post("/reports/{report_id}/export.csv")',
        "payload: ManualCsvExportRequest",
        "Depends(require_csrf)",
        "_require_manual_csv_export_enabled()",
        "_manual_csv_records(conn, report_id=resolved, account_id=account_id)",
        "MAX_MANUAL_CSV_EXPORT_BYTES",
        "MAX_MANUAL_CSV_EXPORT_ROWS",
        "CSV_FORMULA_PREFIX_PATTERN",
        "analytics_report_manual_csv_exported",
        '"Content-Disposition": \'attachment; filename="toan-aas-manual-analytics.csv"\'',
        '"Cache-Control": "no-store, private"',
        '"Content-Security-Policy": "sandbox"',
        '"Cross-Origin-Resource-Policy": "same-origin"',
        "WEB_ANALYTICS_MANUAL_CSV_EXPORT_LIMIT",
        "WEB_ANALYTICS_MANUAL_CSV_FINALIZED_REQUIRED",
        "WEB_ANALYTICS_REVISION_CONFLICT",
        "canonical_campaign_report",
        "stored_report_file_export",
    ):
        assert required in WORKSPACE
    for forbidden in ("import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS"):
        assert forbidden not in WORKSPACE

    records_start = WORKSPACE.index("def _manual_csv_records(")
    records = WORKSPACE[records_start:WORKSPACE.index('@router.get("/summary")', records_start)]
    assert "COUNT(*)" in records
    assert "MAX_MANUAL_CSV_EXPORT_ROWS" in records
    assert ".fetchall()" not in records
    assert "best_effort_transaction(timeout_seconds=0.25)" in WORKSPACE
    assert "WEB_ANALYTICS_MANUAL_CSV_RETRY_LATER" in WORKSPACE
    assert "request.state.reliability_expected_failure = True" in WORKSPACE

    assert 'os.environ.get("WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED", "false")' in DATABASE
    assert '"analytics_workspace_export_enabled": enabled("WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED", False)' in API
    for required in (
        "analytics_workspace_manual_csv_export = (",
        "analytics-workspace-manual-csv-export",
        "rate_limit = 10",
        "private_manual_analytics_csv_export = (",
    ):
        assert required in APP


def test_analytics_private_cache_and_responsive_ui_contract() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in SERVICE_WORKER
    assert "function workerBuildId()" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert "api/v1/analytics-workspace" in SERVICE_WORKER
    assert '"/analytics"' in SERVICE_WORKER
    assert "private `/analytics/*` routes" in SERVICE_WORKER
    assert "api/v1/analytics-workspace" not in shell
    assert '"/analytics"' not in shell
    assert "PRIVATE_PATH_PREFIXES" in SERVICE_WORKER
    assert "isPrivatePath" in SERVICE_WORKER
    for selector in (
        ".portal-analytics-intro",
        ".portal-analytics-layout",
        ".portal-analytics-boundary",
        ".portal-analytics-guard-list",
        ".portal-analytics-report-grid",
        ".portal-analytics-detail-summary",
        ".portal-analytics-detail-grid",
        ".portal-analytics-metric-grid",
        ".portal-analytics-snapshot-list",
        ".portal-analytics-finding-grid",
        ".portal-analytics-history-grid",
    ):
        assert selector in CSS
    assert ".portal-analytics-intro, .portal-analytics-detail-summary, .portal-analytics-layout, .portal-analytics-detail-grid, .portal-analytics-history-grid { grid-template-columns: 1fr; }" in CSS


def test_analytics_backend_never_imports_legacy_or_network_authorities() -> None:
    for forbidden in (
        "import copyfast_bridge",
        "from copyfast_bridge",
        "import requests",
        "import httpx",
        "import urllib",
        "import PayOS",
        "from PayOS",
        "import wallet",
        "from wallet",
    ):
        assert forbidden not in WORKSPACE
