"""Static and browser-semantics contracts for the Web-native Support Desk."""

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_support_pages_are_native_case_workspaces_not_primary_bot_ticket_cards() -> None:
    support_start = PORTAL.index('customerPage("/support", "Web Support Desk"')
    tickets_start = PORTAL.index('customerPage("/tickets", "Yêu cầu của tôi"')
    support_page = PORTAL[support_start:tickets_start]
    tickets_page = PORTAL[tickets_start:PORTAL.index('customerPage("/legal"', tickets_start)]

    assert 'layout: "support-desk", action: "support-case-create"' in support_page
    assert 'layout: "support-cases", action: "none"' in tickets_page
    assert 'action: "create-ticket"' not in support_page
    assert '"/support/tickets"' not in support_page
    assert 'botCompanionPage("/support"' not in PORTAL
    assert 'botCompanionPage("/tickets"' not in PORTAL
    ticket_renderer = PORTAL[PORTAL.index("function renderSupportCasePagination"):PORTAL.index("function renderSupportCaseDetail")]
    assert 'data-portal-no-transient data-portal-action="support-cases-filter"' in ticket_renderer
    assert 'data-portal-action="support-cases-page"' in ticket_renderer
    assert 'data-support-case-offset=' in ticket_renderer

    for layout, renderer in (
        ("support-desk", "renderSupportDesk"),
        ("support-cases", "renderSupportCases"),
        ("support-case-detail", "renderSupportCaseDetail"),
        ("support-admin", "renderSupportAdmin"),
        ("support-admin-case-detail", "renderSupportAdminCaseDetail"),
    ):
        assert f'case "{layout}": return {renderer}(page, context);' in PORTAL
        assert f"function {renderer}(page, context)" in PORTAL

    assert 'path: "/tickets/:id"' in PORTAL
    assert 'path: "/admin/support/:id"' in PORTAL
    assert 'data-portal-action="support-case-close"' in PORTAL
    assert 'data-portal-action="support-case-reopen"' in PORTAL
    assert 'data-portal-action="support-admin-case-reply"' in PORTAL
    assert 'data-portal-action="support-admin-case-update"' in PORTAL


def test_support_hydrates_owner_scoped_native_routes_with_no_bridge_fallback() -> None:
    for name in (
        "supportCaseIdFromPath",
        "supportAdminCaseIdFromPath",
        "supportCaseFilterPayload",
        "supportCaseListOffset",
        "supportCustomerCasesPath",
        "supportCaseListingProjection",
        "supportCasesPath",
        "hydrateSupportDesk",
        "hydrateSupportCase",
        "hydrateSupportAdmin",
        "hydrateSupportAdminCase",
    ):
        assert f"function {name}" in INTEGRATION

    assert 'return `${admin ? "/support/admin/cases" : "/support/cases"}' in INTEGRATION
    assert 'api(supportCustomerCasesPath(filter, offset))' in INTEGRATION
    assert 'supportCaseListing: supportCaseListingProjection(filter, offset, casesResult.data, cases.length)' in INTEGRATION
    assert 'api("/support/summary")' in INTEGRATION
    assert 'api("/support/events?limit=40")' in INTEGRATION
    assert 'api("/support/events?limit=40").catch(() => null)' in INTEGRATION
    assert "function supportEventsProjection" in INTEGRATION
    assert "supportEventsReadState: eventProjection.readState" in INTEGRATION
    assert 'api(`/support/cases/${encodeURIComponent(String(caseId))}`)' in INTEGRATION
    assert 'api(`/support/admin/cases/${encodeURIComponent(String(caseId))}`)' in INTEGRATION
    assert 'if (account && supportDeskEnabled)' in INTEGRATION
    assert 'else if (isNativeSupportPath(currentPath))' in INTEGRATION
    assert 'supportSummary: {}, supportCases: [], supportEvents: [], supportEventsReadState: "guarded", supportCaseDetail: {}' in INTEGRATION

    # The customer pager is a signed, page-memory receipt. It must survive
    # normalizeBootstrap just as the separate staff pager does; otherwise a
    # successful /tickets read re-renders as page zero and drops navigation.
    bootstrap_start = PORTAL.index("function normalizeBootstrap")
    bootstrap_end = PORTAL.index("function getBootstrap", bootstrap_start)
    bootstrap = PORTAL[bootstrap_start:bootstrap_end]
    assert "const customerSupportCaseListing = supportCaseListing(source);" in bootstrap
    assert "supportCaseListing: customerSupportCaseListing," in bootstrap
    assert "supportEventsReadState:" in bootstrap

    # A failed event feed is deliberately separate from the verified summary
    # and owner-scoped case listing. Its empty projection must be marked
    # guarded, never rendered as a genuine “no activity” state.
    activity = PORTAL[PORTAL.index("function renderSupportActivity"):PORTAL.index("function renderSupportDesk")]
    assert "Hoạt động đang tạm chưa xác minh" in activity
    assert "coi activity là trống" in activity
    desk = PORTAL[PORTAL.index("function renderSupportDesk"):PORTAL.index("function renderSupportCases")]
    assert "renderSupportActivity(context.supportEvents, context.supportEventsReadState)" in desk

    # The existing bridge ticket endpoint may remain for explicit legacy
    # recovery flows, but all actions belonging to the new native surface
    # must remain independent of it and of money/provider/Telegram state.
    action_start = INTEGRATION.index('if (action === "support-cases-filter" || action === "support-cases-filter-clear")')
    action_end = INTEGRATION.index('if (action === "asset-vault-upload")')
    native_actions = INTEGRATION[action_start:action_end].lower()
    for forbidden in (
        "bridgeavailable",
        "/support/tickets",
        "create-ticket",
        "payment",
        "payos",
        "wallet",
        "telegram",
        "provider",
    ):
        assert forbidden not in native_actions
    for action in (
        'action === "support-case-create"',
        'action === "support-case-reply"',
        'action === "support-case-close"',
        'action === "support-case-reopen"',
        'action === "support-cases-filter-clear"',
        'action === "support-cases-page"',
        'action === "support-admin-case-reply"',
        'action === "support-admin-case-update"',
    ):
        assert action in native_actions


def test_support_admin_case_pagination_uses_a_bounded_server_list_and_ephemeral_pager() -> None:
    """The staff queue must keep its own 50-record page receipt.

    Admin status is always server-authorized.  This only protects the client
    contract: an operator can move through bounded pages without the browser
    inventing a complete queue or persisting a staff filter locally.
    """
    for needle in (
        "const SUPPORT_ADMIN_CASE_LIST_LIMIT = 50;",
        "function supportAdminCasesPath(filter, offset)",
        "function supportAdminCaseListingProjection(filter, offset, source, returned)",
        "api(supportAdminCasesPath(filter, offset))",
        "supportAdminCaseListing: supportAdminCaseListingProjection(filter, offset, casesResult.data, cases.length)",
    ):
        assert needle in INTEGRATION

    # The portal state keeps a separate admin listing receipt; do not reuse
    # the customer-owned `/tickets` pagination state for a staff queue.
    assert "supportAdminCaseListing:" in PORTAL
    assert "function supportAdminCaseListing(context)" in PORTAL
    assert "function renderSupportAdminCasePagination(listing)" in PORTAL
    assert 'data-portal-action="support-admin-cases-page"' in PORTAL
    assert "data-support-admin-case-offset=" in PORTAL
    assert 'Object.assign(fields, { __supportAdminCaseOffset: source.getAttribute("data-support-admin-case-offset") || "" });' in PORTAL

    admin_renderer_start = PORTAL.index("function renderSupportAdminBase")
    admin_renderer_end = PORTAL.index("function renderSupportAdmin(page, context)", admin_renderer_start)
    admin_renderer = PORTAL[admin_renderer_start:admin_renderer_end]
    assert "supportAdminCaseListing(context)" in admin_renderer
    assert "renderSupportAdminCasePagination" in admin_renderer

    action_start = INTEGRATION.index('if (action === "support-admin-cases-page")')
    action_end = INTEGRATION.index('if (action === "support-admin-cases-refresh")', action_start)
    action = INTEGRATION[action_start:action_end]
    assert "__supportAdminCaseOffset" in action
    assert "hydrateSupportAdmin" in action


def test_support_ui_has_responsive_native_primitives_and_no_private_pwa_cache() -> None:
    for selector in (
        ".portal-support-intro",
        ".portal-support-layout",
        ".portal-support-thread",
        ".portal-support-case-hero",
        ".portal-support-admin-forms",
        ".portal-support-filter",
        ".portal-support-pagination",
    ):
        assert selector in CSS

    assert "/api/v1/support" not in SERVICE_WORKER
    assert '"/support"' not in SERVICE_WORKER
    assert '"/tickets"' not in SERVICE_WORKER
    assert '"/admin/support"' not in SERVICE_WORKER
    assert "portal.js" in SERVICE_WORKER
    assert "integration.js" in SERVICE_WORKER


def test_support_browser_preflight_tracks_the_server_sensitive_content_contract() -> None:
    # The server remains authoritative; this protects the early browser UX
    # from drifting behind known secret/payment/card shapes that the server
    # rejects before any Support Desk write is stored.
    assert "function supportSensitiveContentKind" in INTEGRATION
    assert "SUPPORT_KNOWN_SECRET_TOKEN_PATTERN" in INTEGRATION
    assert "AIza" in INTEGRATION
    assert "AKIA" in INTEGRATION
    assert "(?:dịch|gd)" in INTEGRATION
    assert "[\\s./-]*[0-9]" in INTEGRATION


def test_support_browser_preflight_blocks_direct_sensitive_values() -> None:
    """Execute the actual browser guard without giving production a test hook."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is unavailable; static UI contract above still runs")

    script = r'''
const fs = require("fs");
const vm = require("vm");
const sourcePath = process.argv[1];
let source = fs.readFileSync(sourcePath, "utf8");
const closing = "}());";
const position = source.lastIndexOf(closing);
if (position < 0) throw new Error("Portal integration closure was not found");
source = source.slice(0, position)
  + "\nglobalThis.__supportGuard = { validateWebSupportText };\n"
  + source.slice(position);
const noop = () => {};
const window = {
  addEventListener: noop,
  clearTimeout: noop,
  setTimeout: () => 0,
  location: { pathname: "/", search: "" },
  crypto: { getRandomValues: (bytes) => bytes }
};
const document = { readyState: "loading", addEventListener: noop, querySelector: () => null };
const context = { window, document, console, URL, URLSearchParams, crypto: window.crypto };
vm.createContext(context);
vm.runInContext(source, context, { filename: sourcePath });
const guard = context.__supportGuard;
if (!guard || typeof guard.validateWebSupportText !== "function") throw new Error("Support guard was not captured");
const blocked = [
  "token: abcdefghijk",
  "sk_" + "abcdefghijklmnopqrstuvwxyz123456",
  "ghp_" + "abcdefghijklmnopqrstuvwxyz123456789012345678",
  "AIza" + "SyDUMMYEXAMPLEKEY123456789012345",
  "AKIA" + "IOSFODNN7EXAMPLE",
  "Mã xác thực: 123456",
  "STK: 0123456789",
  "Mã GD 1234567890",
  "4111\n1111\n1111\n1111",
  "4111.1111.1111.1111"
];
for (const value of blocked) {
  if (!guard.validateWebSupportText(value)) throw new Error(`Accepted sensitive support input: ${value}`);
}
if (guard.validateWebSupportText("Please review this account workflow and transaction state.")) {
  throw new Error("Rejected an ordinary non-payment support narrative");
}
'''
    try:
        result = subprocess.run(
            [node, "-e", script, str(ROOT / "static" / "portal" / "integration.js")],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        # Some Windows sandbox sessions expose Node on PATH but do not pass
        # valid inheritable pipe handles into a child process. Static contract
        # assertions above still cover the source in that runner; do not
        # misreport the runner defect as an application regression.
        pytest.skip(f"Node subprocess is unavailable in this test runner: {exc}")
    assert result.returncode == 0, result.stderr or result.stdout
