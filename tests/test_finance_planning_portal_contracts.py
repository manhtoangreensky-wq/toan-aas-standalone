"""Static contracts for the Web-native Finance Operations Planning workspace.

These checks deliberately cover the seams between the server-owned planning
module and the Portal.  They keep a future UI edit from turning a prospective
internal plan into a browser-owned payment, wallet or Bot compatibility flow.
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


def test_finance_planning_backend_is_a_separate_web_owned_admin_contract() -> None:
    backend = _read("copyfast_finance_planning.py")
    app = _read("app.py")
    api = _read("copyfast_api.py")
    registry = _read("copyfast_registry.py")

    for requirement in (
        'APIRouter(prefix="/api/v1/admin/finance-planning"',
        '@router.get("/policy")',
        '@router.get("/summary")',
        '@router.get("/budgets")',
        '@router.get("/cost-plans")',
        '@router.post("/budgets")',
        '@router.post("/budgets/{budget_id}/state")',
        '@router.post("/cost-plans")',
        '@router.post("/cost-plans/{cost_plan_id}/state")',
        "Depends(require_admin)",
        "Depends(require_admin_csrf)",
        "WEBAPP_ADMIN_ERP_ENABLED",
        "WEBAPP_FINANCE_PLANNING_ENABLED",
        "web_finance_planning_budgets",
        "web_finance_planning_costs",
        "web_finance_planning_events",
        "confirm_budget",
        "confirm_plan",
        "confirm_change",
        "expected_revision",
        "idempotency_key",
        "PAYMENT_PROOF_PATTERN",
        "BudgetStateRequest",
        "BUDGET_TRANSITIONS",
        "COST_TRANSITIONS",
    ):
        assert requirement in backend

    # The planning adapter must not import a Core Bridge or payment/ledger
    # writer.  Boundary booleans are intentionally present, so inspect imports
    # rather than searching ordinary explanatory text.
    assert not re.search(r"^\s*(?:from|import)\s+copyfast_bridge\b", backend, re.MULTILINE)
    assert not re.search(r"^\s*(?:from|import)\s+(?:billing|payos)\b", backend, re.MULTILINE)
    for false_boundary in (
        '"canonical_finance_read": False',
        '"canonical_finance_write": False',
        '"bot_called": False',
        '"bridge_called": False',
        '"provider_called": False',
        '"wallet_mutated": False',
        '"payment_started": False',
        '"payment_finalized": False',
        '"payos_webhook_created": False',
        '"refund_created": False',
        '"ledger_changed": False',
        '"tax_calculated": False',
        '"report_exported": False',
    ):
        assert false_boundary in backend

    assert "import copyfast_finance_planning" in app
    assert "app.include_router(copyfast_finance_planning.router)" in app
    assert '"finance_planning_enabled": enabled("WEBAPP_FINANCE_PLANNING_ENABLED", True)' in api
    assert 'WebFeature("admin_finance_planning", "Finance Operations Planning", "admin", "/admin/finance/planning", "admin"' in registry


def test_finance_planning_is_discoverable_only_as_a_signed_web_local_admin_surface() -> None:
    app = _read("app.py")
    navigation = _read("copyfast_admin_erp_navigation.py")

    # This exact Web-local route must be checked before the generic canonical
    # `/admin/*` fallback.  A Web admin is not silently promoted to a Bot
    # canonical admin merely to plan operating costs.
    guard = 'elif normalized == "/admin/finance/planning":\n        copyfast_auth.require_admin(request)'
    assert guard in app
    assert app.index(guard) < app.index('elif normalized == "/admin" or normalized.startswith("/admin/"):')

    for requirement in (
        '"web_finance_operations_planning"',
        '"finance_operations_planning"',
        '"Finance Operations Planning"',
        '"/admin/finance/planning"',
        '"WEBAPP_FINANCE_PLANNING_ENABLED"',
        'authority="web_local_admin"',
        'source="web_native"',
    ):
        assert requirement in navigation


def test_portal_renders_a_private_finance_planning_workspace_not_a_bridge_page() -> None:
    portal = _read("static/portal/portal.js")
    integration = _read("static/portal/integration.js")
    worker = _read("static/portal/service-worker.js")

    for requirement in (
        'adminPage("/admin/finance/planning", "Finance Operations Planning"',
        'layout: "admin-finance-planning"',
        'case "admin-finance-planning": return renderAdminFinancePlanning(page, context);',
        "function renderAdminFinancePlanning(page, context)",
        '"finance-planning-view"',
        'data-portal-action="finance-planning-refresh"',
        'data-portal-action="finance-planning-create-budget"',
        'data-portal-action="finance-planning-create-cost"',
        "data-portal-confirm",
    ):
        assert requirement in portal

    for requirement in (
        "function isNativeAdminFinancePlanningPath(path)",
        "function hydrateFinancePlanning",
        "financePlanningEnabled",
        "financePlanningSummary",
        "financePlanningBudgets",
        "financePlanningCostPlans",
        "financePlanningPolicy",
        "financePlanningReadState",
        "financePlanningSessionEpoch",
        "financePlanningHydrationEpoch",
        '"/admin/finance/planning"',
        "/admin/finance-planning/policy",
        "/admin/finance-planning/summary",
        "/admin/finance-planning/budgets",
        "/admin/finance-planning/cost-plans",
        "budget_transitions",
        "cost_transitions",
        'action === "finance-planning-refresh"',
        'action === "finance-planning-create-budget"',
        'action === "finance-planning-create-cost"',
        'action === "finance-planning-budget-state"',
        'action === "finance-planning-cost-state"',
        "expected_revision",
        "confirm_budget",
        "confirm_plan",
        "confirm_change",
    ):
        assert requirement in integration

    native = _function_source(integration, "isNativeAdminFinancePlanningPath")
    assert '"/admin/finance/planning"' in native
    lifecycle_actions = _function_source(portal, "financePlanningStateActions")
    for requirement in (
        '"finance-planning-budget-state"',
        '"finance-planning-cost-state"',
        'data-portal-action="finance-planning-budget-state"',
        'data-portal-action="finance-planning-cost-state"',
        "data-finance-planning-id",
        "data-finance-planning-revision",
        "data-finance-planning-state",
        "data-portal-confirm",
    ):
        assert requirement in lifecycle_actions
    hydrator = _function_source(integration, "hydrateFinancePlanning")
    for forbidden in ("/internal/v1/", "fetch(", "bridgeAvailable", "localStorage", "sessionStorage"):
        assert forbidden not in hydrator
    assert "financePlanningRequestIsCurrent" in hydrator

    # The worker has a closed public shell and its broad Admin/API private
    # prefixes cover this new route even when the shell grows in the future.
    shell = worker.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/admin/finance/planning" not in shell
    assert '"/" + "api/v1/admin"' in worker
    assert '"/admin"' in worker


def test_finance_planning_renderer_exposes_only_planning_lifecycle_controls() -> None:
    portal = _read("static/portal/portal.js")
    integration = _read("static/portal/integration.js")
    renderer = _function_source(portal, "renderAdminFinancePlanning")

    for state in ("active", "draft", "review", "approved", "archived"):
        assert state in renderer
    for forbidden in ("localStorage", "sessionStorage", "fetch(", "/internal/"):
        assert forbidden.lower() not in renderer.lower()
    for forbidden_action in (
        'data-portal-action="wallet',
        'data-portal-action="topup',
        'data-portal-action="payment',
        'data-portal-action="payos',
        'data-portal-action="refund',
        'data-portal-action="provider',
    ):
        assert forbidden_action not in renderer.lower()

    # The action dispatcher must use the same server-issued revision and a
    # fresh idempotency contract rather than calculating a financial result in
    # the browser.  No finance planning action reaches a Core Bridge path.
    action_start = integration.index('action === "finance-planning-refresh"')
    last_finance_action = integration.index('action === "finance-planning-cost-state"')
    next_action = integration.find('if (action ===', last_finance_action + 1)
    actions = integration[action_start:next_action if next_action >= 0 else len(integration)]
    for requirement in (
        "financePlanning",
        "expected_revision",
        "confirm_budget",
        "confirm_plan",
        "confirm_change",
        "hydrateFinancePlanning",
    ):
        assert requirement in actions
    submitter = _function_source(integration, "submitFinancePlanningWrite")
    assert "idempotency_key" in submitter
    for forbidden in ("/internal/v1/", 'api("/wallet', 'api("/payments', 'api("/providers'):
        assert forbidden.lower() not in actions.lower()


def test_finance_planning_ui_keeps_period_pagination_conflict_and_focus_safe() -> None:
    """Protect the high-risk async dashboard interactions from regressions.

    This is intentionally static and narrow: the route's real auth/body/rate
    behavior is covered by the focused API suite, while these assertions keep
    the Portal from silently returning to an unsafe double-submit, wrong-month
    or stale-revision interaction model.
    """

    portal = _read("static/portal/portal.js")
    integration = _read("static/portal/integration.js")

    for requirement in (
        "function setFinancePlanningActionBusy(action, route, busy)",
        'control.querySelectorAll("button, input, select, textarea")',
        "data-finance-planning-disabled-before-busy",
        "function acquireFinancePlanningSubmission(scope, fingerprint)",
        "existing && existing.inFlight",
        "function financePlanningDefaultPeriod(timezone)",
        "Intl.DateTimeFormat",
        "function financePlanningListingProjection(value, kind, expectedPeriod)",
        "financePlanningBudgetListing",
        "financePlanningCostPlanListing",
        "FINANCE_PLANNING_RESYNC_ERROR_CODES",
        "await hydrateFinancePlanning(financePlanningCurrentView())",
        "period !== view.period",
    ):
        assert requirement in integration

    for requirement in (
        "function financePlanningPeriodControl(period, enabled)",
        "function financePlanningPagination(kind, listing, enabled)",
        "finance-planning-budget-page",
        "finance-planning-cost-page",
        'role="status" aria-live="polite"',
        "data-finance-planning-status",
        "finance-planning-action",
        "finance-planning-field",
    ):
        assert requirement in portal
