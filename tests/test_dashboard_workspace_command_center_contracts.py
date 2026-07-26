"""Focused UI/security contracts for the Workspace Command Center."""

import json
import re
from pathlib import Path

import copyfast_pages


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "WORKSPACE_COMMAND_CENTER_CONTRACT.md").read_text(encoding="utf-8")
PORTAL_SHELL_TEMPLATE = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")


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
        'dashboardText("work.kicker")',
        "renderDashboardRecentProjects(context)",
        "renderDashboardRecentDrafts(context)",
        "renderDashboardAccountLane(context)",
        "renderDashboardCanonicalLane(context, readState)",
        "renderDashboardStartGuide(context)",
        "renderStudioLaunchpad(context)",
    ):
        assert token in root
    for token in ('dashboardText("account.kicker")', "function renderDashboardCanonicalLane"):
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
            'dashboardText("summary.canonicalFailed")',
    ):
        assert token in summary
    canonical = surface[surface.index("function renderDashboardCanonicalLane"):surface.index("function renderDashboard(page, context)")]
    for token in (
        'if (readState === "loading")',
        'if (readState === "failed")',
        'if (readState !== "ready")',
        'data-portal-action="dashboard-refresh"',
        'dashboardText("canonical.failedBody")',
        'dashboardText("canonical.assets.emptyBody")',
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


def test_dashboard_hero_uses_a_quiet_data_first_grid_with_aligned_mobile_actions() -> None:
    command_center_css = CSS[CSS.index("/* Workspace Command Center"):]
    for token in (
        ".portal-workspace-command-center .portal-dashboard-overview {",
        "grid-template-columns: minmax(0, 1fr);",
        "border-color: var(--portal-border);",
        ".portal-workspace-command-center .portal-dashboard-overview-stats { grid-template-columns: repeat(4, minmax(0, 1fr)); }",
        ".portal-workspace-command-center .portal-dashboard-overview-actions {",
        "grid-column: 1 / -1;",
    ):
        assert token in command_center_css

    mobile_css = command_center_css[command_center_css.index("@media (max-width: 700px)"):]
    assert (
        ".portal-workspace-command-center .portal-dashboard-overview-stats "
        "{ grid-template-columns: repeat(2, minmax(0, 1fr)); }"
    ) in mobile_css

    compact_mobile_css = command_center_css[command_center_css.index("@media (max-width: 460px)"):]
    assert (
        ".portal-workspace-command-center .portal-dashboard-overview-stats "
        "{ grid-template-columns: 1fr; }"
    ) in compact_mobile_css


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


def test_dashboard_fixed_copy_uses_reviewed_catalogue_without_changing_authority() -> None:
    surface = dashboard_surface()
    assert "function dashboardText(key, params)" in surface
    for function_name in (
        "renderDashboardWorkspaceSummary",
        "renderDashboardRecentDrafts",
        "renderDashboardRecentProjects",
        "renderDashboardStartGuide",
        "renderDashboardAccountLane",
        "renderDashboardCanonicalLane",
        "renderDashboard",
        "renderWorkspaceActionCenter",
        "renderStudioLaunchpad",
    ):
        start = PORTAL.index(f"function {function_name}(")
        next_function = PORTAL.find("\n  function ", start + 1)
        block = PORTAL[start:next_function if next_function != -1 else len(PORTAL)]
        assert "dashboardText(" in block
    dashboard = PORTAL[PORTAL.index("function renderDashboard(page, context)"):PORTAL.index("function renderWorkspaceActionCenter")]
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage"):
        assert forbidden not in dashboard.lower()


def test_dashboard_command_center_moves_all_fixed_chrome_to_dashboard_keys() -> None:
    """Keep fixed chrome localized without rewriting canonical customer data."""

    expected_keys = {
        "renderDashboardCanonicalLane": (
            "canonical.kicker",
            "canonical.loadingTitle",
            "canonical.loadingBody",
            "canonical.failedTitle",
            "canonical.failedBody",
            "canonical.retry",
            "canonical.checkConnection",
            "canonical.guardedTitle",
            "canonical.guardedBody",
            "canonical.learnLink",
            "canonical.openSecurity",
            "canonical.readyTitle",
            "canonical.readyBody",
            "canonical.metrics.balanceLabel",
            "canonical.metrics.balanceCanonicalDetail",
            "canonical.metrics.balancePendingDetail",
            "canonical.metrics.spentLabel",
            "canonical.metrics.spentCanonicalDetail",
            "canonical.metrics.spentPendingDetail",
            "canonical.metrics.jobsLabel",
            "canonical.metrics.jobsDetail",
            "canonical.metrics.assetsLabel",
            "canonical.metrics.assetsDetail",
            "canonical.jobs.title",
            "canonical.jobs.body",
            "canonical.jobs.open",
            "canonical.jobs.table.id",
            "canonical.jobs.table.feature",
            "canonical.jobs.table.status",
            "canonical.jobs.table.output",
            "canonical.jobs.emptyTitle",
            "canonical.jobs.emptyBody",
            "canonical.assets.title",
            "canonical.assets.body",
            "canonical.assets.open",
            "canonical.assets.table.asset",
            "canonical.assets.table.feature",
            "canonical.assets.table.status",
            "canonical.assets.table.delivery",
            "canonical.assets.emptyTitle",
            "canonical.assets.emptyBody",
        ),
        "renderDashboard": (
            "work.kicker",
            "work.title",
            "work.body",
            "assurance.title",
            "assurance.body",
        ),
        "renderWorkspaceActionCenter": (
            "actionCenter.kicker",
            "actionCenter.title",
            "actionCenter.body",
            "actionCenter.openAll",
            "actionCenter.processing.label",
            "actionCenter.processing.detailActive",
            "actionCenter.processing.detailEmpty",
            "actionCenter.processing.action",
            "actionCenter.delivery.label",
            "actionCenter.delivery.detailActive",
            "actionCenter.delivery.detailEmpty",
            "actionCenter.delivery.action",
            "actionCenter.review.label",
            "actionCenter.review.detailActive",
            "actionCenter.review.detailEmpty",
            "actionCenter.review.action",
            "actionCenter.tickets.label",
            "actionCenter.tickets.detailActive",
            "actionCenter.tickets.detailEmpty",
            "actionCenter.tickets.action",
        ),
        "renderStudioLaunchpad": (
            "launchpad.kicker",
            "launchpad.title",
            "launchpad.body",
            "launchpad.pricing",
            "launchpad.open",
            "launchpad.studio.image.title",
            "launchpad.studio.image.body",
            "launchpad.studio.image.tagPrompt",
            "launchpad.studio.image.tagAssets",
            "launchpad.studio.video.title",
            "launchpad.studio.video.body",
            "launchpad.studio.video.tagDraft",
            "launchpad.studio.video.tagJobs",
            "launchpad.studio.voice.title",
            "launchpad.studio.voice.body",
            "launchpad.studio.voice.tagVault",
            "launchpad.studio.voice.tagEstimate",
            "launchpad.studio.music.title",
            "launchpad.studio.music.body",
            "launchpad.studio.music.tagPolicy",
            "launchpad.studio.music.tagQuote",
            "launchpad.studio.content.title",
            "launchpad.studio.content.body",
            "launchpad.studio.content.tagPlanning",
            "launchpad.studio.content.tagDraft",
            "launchpad.studio.documents.title",
            "launchpad.studio.documents.body",
            "launchpad.studio.documents.tagFiles",
            "launchpad.studio.documents.tagGuarded",
        ),
    }
    blocks: dict[str, str] = {}
    for function_name, keys in expected_keys.items():
        start = PORTAL.index(f"function {function_name}(")
        next_function = PORTAL.find("\n  function ", start + 1)
        block = PORTAL[start:next_function if next_function != -1 else len(PORTAL)]
        blocks[function_name] = block
        for key in keys:
            assert f'dashboardText("{key}")' in block

    fixed_literals = (
        "Canonical integration",
        "Wallet, job, asset, ticket và feature readiness chỉ xuất hiện",
        "Chưa thể xác minh trạng thái vận hành",
        "Dashboard đã xóa projection canonical cũ",
        "Thử lại",
        "Kiểm tra kết nối",
        "Integration chưa sẵn sàng",
        "Phần Web-native vẫn hoạt động độc lập.",
        "Xem cách liên kết",
        "Mở Security Center",
        "Xu canonical",
        "Không tính lại ở browser",
        "Đã dùng",
        "Đọc từ ledger canonical",
        "Job gần đây",
        "Trong cửa sổ hiện tại",
        "Asset metadata",
        "Không đồng nghĩa delivery",
        "Core Bridge kiểm tra ownership",
        "Mở Job Center →",
        "Output engine",
        "Chưa có hoạt động được xác minh",
        "Tài sản gần đây",
        "Chỉ metadata riêng tư",
        "Mở tài sản →",
        "Chưa có asset metadata",
        "Continue Web work",
        "Hai thư viện này là dữ liệu Web-owned",
        "Web-native authoring, canonical read models",
        "Work Queue",
        "Chỉ tổng hợp metadata canonical",
        "Xem tất cả công việc →",
        "Đang xử lý",
        "Tệp đã sẵn sàng",
        "Cần xem job",
        "Ticket chờ bạn",
        "TOAN AAS Studio",
        "Mỗi studio dùng cùng hợp đồng",
        "Xem pricing canonical →",
        "Prompt, tham chiếu và estimate canonical.",
        "Brief, cảnh và tiến độ từ Job Center.",
        "TTS, Voice Vault và consent rõ ràng.",
        "Prompt nhạc, chính sách và báo giá bot.",
        "Caption, hook, script và storyboard.",
        "PDF/OCR theo contract và delivery riêng tư.",
        "Mở studio",
    )
    command_center = "\n".join(blocks.values())
    for literal in fixed_literals:
        assert literal not in command_center


def test_dashboard_ready_rows_use_dashboard_localized_delivery_helpers() -> None:
    """A ready Dashboard must not borrow fixed Vietnamese delivery chrome."""

    canonical_start = PORTAL.index("function renderDashboardCanonicalLane(")
    canonical_end = PORTAL.index("function renderDashboard(page, context)", canonical_start)
    canonical = PORTAL[canonical_start:canonical_end]

    for helper in (
        "function dashboardReportedOutput(item)",
        "function dashboardAssetJobLink(item)",
        "function dashboardAssetDeliveryState(item)",
    ):
        assert helper in PORTAL

    assert "dashboardReportedOutput(item)" in canonical
    assert "dashboardAssetJobLink(item)" in canonical
    assert 'dashboardAssetDeliveryState(item)' in canonical
    for leaked_helper in (
        "reportedOutput(item)",
        "assetJobLink(item)",
        'assetDeliveryState(item, "asset")',
    ):
        assert leaked_helper not in canonical


def test_signed_workspace_shell_uses_token_driven_geometry_at_each_breakpoint() -> None:
    """The final theme keeps the data-first shell operable without fake cards."""

    marker = "/* Signed Workspace shell alignment. */"
    assert marker in THEME
    next_marker = "/* Final public-companion layout."
    start = THEME.index(marker)
    end = THEME.index(next_marker, start)
    workspace_theme = THEME[start:end]

    for selector in (
        ".portal-shell:not(.portal-shell--auth):not(.portal-shell--landing)",
        ".portal-sidebar {",
        ".portal-header {",
        ".portal-main {",
        ".portal-data-table-wrap {",
        ".portal-mobile-nav {",
        ".portal-mobile-nav-link {",
    ):
        assert selector in workspace_theme

    for declaration in (
        "grid-template-columns: minmax(0, 1fr);",
        "min-height: 44px;",
        "border-color: var(--portal-border);",
        "background: var(--portal-surface);",
        "background: var(--portal-surface-strong);",
        "color: var(--portal-text);",
    ):
        assert declaration in workspace_theme

    for breakpoint in ("@media (max-width: 1040px)", "@media (max-width: 700px)", "@media (max-width: 460px)"):
        assert breakpoint in workspace_theme

    mobile_theme = workspace_theme[workspace_theme.index("@media (max-width: 700px)"):]
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in mobile_theme
    assert "padding-bottom: calc(104px + var(--portal-safe-bottom));" in mobile_theme
    assert "gradient(" not in workspace_theme
    assert re.search(r"#[0-9a-fA-F]{3,8}\b", workspace_theme) is None


def test_signed_workspace_primary_actions_keep_the_shared_teal_hierarchy() -> None:
    marker = "/* Signed Workspace shell alignment. */"
    next_marker = "/* Final public-companion layout."
    start = THEME.index(marker)
    workspace_theme = THEME[start:THEME.index(next_marker, start)]

    base = re.search(
        r"\.portal-button\s*\{(?P<declarations>.*?)\n\}",
        workspace_theme,
        flags=re.DOTALL,
    )
    base_hover = re.search(
        r"\.portal-button:hover:not\(:disabled\),\s*\n"
        r"\.portal-button:focus-visible\s*\{(?P<declarations>.*?)\n\}",
        workspace_theme,
        flags=re.DOTALL,
    )
    primary = re.search(
        r"\.portal-button--primary\s*\{(?P<declarations>.*?)\n\}",
        workspace_theme,
        flags=re.DOTALL,
    )
    hover = re.search(
        r"\.portal-button--primary:hover:not\(:disabled\),\s*\n"
        r"\.portal-button--primary:focus-visible\s*\{(?P<declarations>.*?)\n\}",
        workspace_theme,
        flags=re.DOTALL,
    )

    assert base is not None
    assert base_hover is not None
    assert primary is not None
    assert hover is not None
    assert primary.start() > base.start()
    assert hover.start() > base_hover.start()
    assert "background: var(--portal-action);" in primary.group("declarations")
    assert "color: var(--portal-on-action);" in primary.group("declarations")
    assert "background: var(--portal-action-hover);" in hover.group("declarations")


def test_signed_shell_document_theme_color_matches_the_teal_pwa_shell() -> None:
    assert '<meta name="theme-color" content="#062a36">' in PORTAL_SHELL_TEMPLATE
    assert "#07141d" not in PORTAL_SHELL_TEMPLATE
