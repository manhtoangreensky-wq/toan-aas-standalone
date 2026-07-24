"""Focused UI/security contracts for the canonical Campaign Operations Board."""

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
CONTRACT = (ROOT / "docs" / "migration" / "CAMPAIGN_OPERATIONS_BOARD_CONTRACT.md").read_text(encoding="utf-8")


def campaign_surface() -> str:
    start = PORTAL.index("function campaignPlannerReadState")
    end = PORTAL.index("function renderCampaignDetail", start)
    return PORTAL[start:end]


def root_renderer() -> str:
    start = PORTAL.index("function renderCampaignPlanner(page, context)")
    end = PORTAL.index("function renderCampaignDetail", start)
    return PORTAL[start:end]


def campaign_shell_payload(path: str) -> dict[str, object]:
    response = copyfast_pages.render_portal(path, interface_locale="en")
    assert response.status_code == 200
    match = re.search(
        r'<script id="portal-bootstrap" type="application/json">(.*?)</script>',
        response.body.decode("utf-8"),
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_campaign_operations_board_keeps_canonical_root_new_and_detail_routes() -> None:
    surface = campaign_surface()
    assert 'customerPage("/campaigns", "Campaign Planner"' in PORTAL
    assert 'customerPage("/campaigns/new", "Campaign mới"' in PORTAL
    assert 'path: "/campaigns/:id"' in PORTAL
    assert "function renderCampaignPlannerAuthoring" in surface
    assert 'const authoringRoute = route === "/campaigns/new";' in surface
    assert "renderCampaignPlannerAuthoring(page, context, canAct(page, context))" in surface
    assert "/campaign-hub" not in PORTAL


def test_campaign_authoring_is_server_routable_exact_path_with_a_reviewed_shell_title() -> None:
    assert 'CAMPAIGN_CREATE_PATH = "/campaigns/new"' in PAGES
    payload = campaign_shell_payload("/campaigns/new")
    assert payload["path"] == "/campaigns/new"
    assert payload["title"] == "New Campaign · TOAN AAS"


def test_campaign_operations_board_has_truthful_owner_scoped_read_states() -> None:
    root = root_renderer()
    for token in (
        'const canView = Boolean(context && context.capabilities && context.capabilities["campaigns-refresh"] === true);',
        "if (!signedSession)",
        "if (!canView)",
        'if (readState === "loading")',
        'if (readState !== "ready")',
        'data-portal-action="campaigns-refresh"',
        "Không có dữ liệu cũ",
        "Không có activity giả",
        "projection hiện tại",
    ):
        assert token in root
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "URLSearchParams", "bridge_request", "CORE_BRIDGE"):
        assert forbidden.lower() not in root.lower()


def test_campaign_operations_board_separates_authoring_from_detail_write_controls() -> None:
    surface = campaign_surface()
    root = root_renderer()
    authoring_start = surface.index("function renderCampaignPlannerAuthoring")
    authoring_end = surface.index("function renderCampaignPlanner(page, context)")
    authoring = surface[authoring_start:authoring_end]
    assert 'data-portal-action="campaign-create"' in authoring
    assert 'data-portal-route="${safeText(route)}"' in authoring
    assert "transientFormValues(route)" in authoring
    for token in ('data-portal-action="campaign-create"', "campaignEditControls(", "campaignStatusControls("):
        assert token not in root
    assert 'href="/campaigns/new"' in root
    assert "portal-campaign-operations-create-guard" in root
    assert "Chỉ có quyền xem" in root
    assert "Mở Campaign" in root


def test_campaign_operations_board_fails_closed_before_the_signed_list_read() -> None:
    hydration = INTEGRATION[
        INTEGRATION.index("async function hydrateCampaignPlans()"):
        INTEGRATION.index("function campaignCalendarRequestIsCurrent", INTEGRATION.index("async function hydrateCampaignPlans()"))
    ]
    for token in (
        "const requestEpoch = ++campaignListHydrationEpoch;",
        'const rootBoard = expectedPath === "/campaigns";',
        "campaignRequestIsCurrent(requestEpoch, campaignListHydrationEpoch, sessionEpoch, expectedPath)",
        'campaignPlannerReadState: "loading"',
        'campaignPlannerReadState: "ready"',
        'campaignPlannerReadState: "failed"',
        'const result = await api("/campaigns");',
    ):
        assert token in hydration
    assert hydration.index('campaignPlannerReadState: "loading"') < hydration.index('const result = await api("/campaigns");')
    for forbidden in ("bridge_request", "CORE_BRIDGE", "payos", "wallet", "provider"):
        assert forbidden.lower() not in hydration.lower()
    assert 'campaignPlannerReadState: account ? "loading" : "guarded"' in INTEGRATION
    assert '"campaigns-refresh": Boolean(account)' in INTEGRATION
    assert 'if (action === "campaigns-refresh")' in INTEGRATION
    assert 'window.location.assign(`/campaigns/${encodeURIComponent(String(item.id))}`);' in INTEGRATION
    assert 'campaignPlannerReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.campaignPlannerReadState || ""))' in PORTAL
    assert 'projectCenterReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.projectCenterReadState || ""))' in PORTAL


def test_campaign_authoring_draft_is_cleared_before_every_fresh_signed_projection() -> None:
    clear_start = INTEGRATION.index("function clearSessionScopedTransientDrafts()")
    clear_end = INTEGRATION.index("function toast", clear_start)
    clear = INTEGRATION[clear_start:clear_end]
    assert 'const CAMPAIGN_CREATE_ROUTE = "/campaigns/new";' in INTEGRATION
    assert "clearTransientFormDraft(CAMPAIGN_CREATE_ROUTE);" in clear
    hydrate_start = INTEGRATION.index("async function hydrate()")
    hydrate_end = INTEGRATION.index("async function hydrateCampaignCalendar", hydrate_start)
    assert "clearSessionScopedTransientDrafts();" in INTEGRATION[hydrate_start:hydrate_end]
    pageshow_start = INTEGRATION.index('window.addEventListener("pageshow"')
    pageshow_end = INTEGRATION.index('window.addEventListener("visibilitychange"', pageshow_start)
    assert "event.persisted" in INTEGRATION[pageshow_start:pageshow_end]
    assert "hydrate()" in INTEGRATION[pageshow_start:pageshow_end]


def test_campaign_operations_board_remains_private_in_pwa_and_app_first_on_mobile() -> None:
    private_prefixes = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/campaigns"' in private_prefixes
    assert '"/" + "api/v1/campaigns"' in private_prefixes
    assert '"/campaigns"' not in shell
    assert '"/api/v1/campaigns"' not in shell
    for token in (
        ".portal-campaign-operations-board",
        ".portal-campaign-operations-authoring",
        ".portal-campaign-operations-create-guard",
        "min-height: 44px",
        "@media (prefers-reduced-motion: reduce)",
        ".portal-campaign-operations-quick-links a { transition: none; }",
    ):
        assert token in CSS
    board_css = CSS[CSS.index("/* Campaign Operations Board"):]
    assert "linear-gradient" not in board_css


def test_campaign_operations_contract_records_current_authority_and_non_goals() -> None:
    for token in (
        "`/campaigns`",
        "`/campaigns/new`",
        "`/campaigns/{uuid}`",
        "GET /api/v1/campaigns",
        "owner-scoped",
        "loaded/current projection",
        "Bot parity disposition",
        "PayOS",
        "Service Worker",
        "44px",
    ):
        assert token in CONTRACT
