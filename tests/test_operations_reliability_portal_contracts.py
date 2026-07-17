"""Static safety contracts for the staff-only Reliability Follow-up portal.

This surface intentionally aggregates only bounded Web metadata.  It must not
become a browser log viewer, a Bot/Core Bridge projection, or an auto-repair
executor merely because an authenticated staff member opens the route.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
RELIABILITY = (ROOT / "copyfast_reliability.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin + len(start))
    return source[begin:finish]


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    end = match.end() + following.start() if following else len(source)
    return source[match.start():end]


def test_reliability_is_a_native_staff_portal_not_a_bridge_admin_projection() -> None:
    page = _between(
        PORTAL,
        'adminPage("/admin/reliability", "Reliability Follow-up"',
        'adminPage("/admin/campaigns"',
    )
    assert 'layout: "reliability-admin", action: "none"' in page
    assert "không phải log, tự sửa hay kênh liên hệ khách" in page
    assert "function renderReliabilityAdmin(page, context)" in PORTAL
    assert 'case "reliability-admin": return renderReliabilityAdmin(page, context);' in PORTAL

    native_path = _function_source(INTEGRATION, "isNativeOperationsPath")
    assert '"/admin/reliability"' in native_path
    for helper in ("reliabilityBoundaryIsSafe", "reliabilitySummaryIsSafe", "reliabilityFollowupIsSafe", "hydrateReliabilityAdmin"):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION
    for request in (
        'api("/operations/admin/reliability/summary")',
    ):
        assert request in INTEGRATION
    assert 'currentPath === "/admin/reliability" && reliabilityFollowupEnabled) await hydrateReliabilityAdmin()' in INTEGRATION
    canonical_gate = INTEGRATION[INTEGRATION.index("if (bridgeAvailable &&") :]
    assert "!isNativeOperationsPath(currentPath)" in canonical_gate[:1_200]


def test_reliability_followup_pagination_has_its_own_staff_receipt_and_cursor() -> None:
    """Reliability follow-ups must not borrow an Operations Admin list page."""

    for fragment in (
        "const RELIABILITY_FOLLOWUP_LIST_LIMIT =",
        "const OPERATIONS_MAX_LIST_OFFSET =",
        "function reliabilityFollowupsPath",
        "function reliabilityFollowupListingProjection",
        "reliabilityFollowupListing:",
        'if (action === "reliability-followups-page")',
        "__reliabilityFollowupOffset",
        "next_offset",
        "previous_offset",
    ):
        assert fragment in INTEGRATION

    for fragment in (
        "function reliabilityFollowupListing(context)",
        "function renderReliabilityFollowupPagination(listing",
        "data-portal-action",
        "reliability-followups-page",
        "data-reliability-followup-offset",
    ):
        assert fragment in PORTAL

    start = PORTAL.index("function renderReliabilityAdmin(page, context)")
    end = PORTAL.index("function renderPage(page, context)", start)
    renderer = PORTAL[start:end]
    assert "reliabilityFollowupListing(context)" in renderer
    assert "renderReliabilityFollowupPagination(" in renderer


def test_reliability_filters_use_only_server_allowlisted_metadata_and_persist_through_paging() -> None:
    contract = _between(INTEGRATION, "function reliabilityFollowupFilterPayload", "function operationsListingProjection")
    assert 'const RELIABILITY_FOLLOWUP_STATES = new Set(["open", "acknowledged", "resolved", "superseded"])' in INTEGRATION
    assert 'const RELIABILITY_FOLLOWUP_SEVERITIES = new Set(["low", "medium", "high", "critical"])' in INTEGRATION
    for requirement in (
        "function reliabilityFollowupFilterPayload",
        'state !== "all"',
        'severity !== "all"',
        "RELIABILITY_FOLLOWUP_STATES.has(state)",
        "RELIABILITY_FOLLOWUP_SEVERITIES.has(severity)",
        "function reliabilityFollowupsPath(filter, offset)",
        "state: safeFilter.state",
        "severity: safeFilter.severity",
    ):
        assert requirement in contract
    for forbidden in ("source_id", "account_id", "fingerprint", "created_by_run_id", "sort:", "q:"):
        assert forbidden not in contract

    projection = _function_source(INTEGRATION, "reliabilityFollowupListingProjection")
    assert "filters: reliabilityFollowupFilterPayload(filter)" in projection

    hydrate = _function_source(INTEGRATION, "hydrateReliabilityAdmin")
    for requirement in (
        "const storedFilter = currentListing.filters",
        "const filter = reliabilityFollowupFilterPayload",
        "api(reliabilityFollowupsPath(filter, offset))",
        "reliabilityFollowupFilter: filter",
        "reliabilityFollowupListingProjection(filter, offset",
    ):
        assert requirement in hydrate

    handler = _between(INTEGRATION, 'if (action === "reliability-followup-filter")', 'if (action === "reliability-refresh")')
    for requirement in (
        '"reliability-followup-view"',
        "reliabilityFollowupFilterPayload(fields)",
        "hydrateReliabilityAdmin(reliabilityFollowupFilterPayload(fields), 0)",
        'if (action === "reliability-followup-filter-clear")',
        'hydrateReliabilityAdmin({ state: "all", severity: "all" }, 0)',
    ):
        assert requirement in handler

    renderer = _between(PORTAL, "function renderReliabilityAdmin(page, context)", "function renderTickets(page, context)")
    for requirement in (
        "reliabilityFollowupFilter(context)",
        'data-portal-action="reliability-followup-filter"',
        'data-portal-action="reliability-followup-filter-clear"',
        "data-portal-no-transient",
        'name="state"',
        'name="severity"',
        "không có tìm kiếm theo source, account, route, ID, nội dung hoặc log",
    ):
        assert requirement in renderer
    filter_form = _between(renderer, "const filterMarkup", "const followupMarkup")
    for forbidden in ('name="q"', 'name="source_kind"', 'name="account_id"', 'name="source_id"', 'name="sort"'):
        assert forbidden not in filter_form


def test_reliability_boundary_and_browser_records_fail_closed() -> None:
    verifier = _function_source(INTEGRATION, "reliabilityBoundaryIsSafe")
    for predicate in (
        'boundary.execution === "web_native_reliability_metadata_only"',
        'boundary.data_origin === "sanitized_web_response_metadata_and_signed_operations_scheduler_only"',
        "boundary.reliability_followup_enabled === true",
        'typeof boundary.safe_remediation_enabled === "boolean"',
        'typeof boundary.reliability_config_ready === "boolean"',
        "boundary.bot_called === false",
        "boundary.provider_called === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_mutated === false",
        "boundary.payment_processed === false",
        "boundary.customer_reply_sent === false",
        "boundary.external_notification_sent === false",
        "boundary.telegram_sent === false",
        "boundary.email_sent === false",
        "boundary.sms_sent === false",
        "boundary.web_push_sent === false",
        "boundary.job_retried === false",
        "boundary.asset_delivery_changed === false",
        "boundary.deployment_changed === false",
        "boundary.self_modifying_code === false",
        "boundary.dangerous_action_executed === false",
    ):
        assert predicate in verifier

    record_verifier = _function_source(INTEGRATION, "reliabilityFollowupIsSafe")
    for forbidden_field in ('"source_id"', '"account_id"', '"fingerprint"', '"created_by_run_id"'):
        assert forbidden_field in record_verifier
    assert "reliabilitySummaryIsSafe(summary)" in INTEGRATION
    assert "reliabilityBoundaryIsSafe(followupsData)" in INTEGRATION


def test_reliability_actions_remain_confirmed_metadata_updates_only() -> None:
    assert 'data-portal-action="reliability-followup-${safeText(action)}"' in PORTAL
    for action in ("reliability-followup-acknowledge", "reliability-followup-resolve", "reliability-followup-reopen"):
        assert f'"{action}"' in INTEGRATION
    action_start = INTEGRATION.index('if (["reliability-followup-acknowledge",')
    action_end = INTEGRATION.index('if (action === "operations-approval-approve" ||', action_start)
    actions = INTEGRATION[action_start:action_end].lower()
    for requirement in ("expected_revision", "confirm: true", "idempotency_key", "/operations/admin/followups/"):
        assert requirement.lower() in actions
    for forbidden in ("copyfast_bridge", "/payments", "/jobs", "wallet", "payos", "provider", "telegram", "restart", "deploy"):
        assert forbidden not in actions

    # Runtime collection is a tightly scoped request-metadata consumer. It
    # must not touch raw request material or integration clients.
    capture = RELIABILITY[RELIABILITY.index("def record_runtime_failure"):RELIABILITY.index("def _event", RELIABILITY.index("def record_runtime_failure"))]
    assert "request.url.path" in capture
    assert "best_effort_transaction" in capture
    assert "ensure_copyfast_schema" not in capture
    for forbidden in ("request.headers", "request.cookies", "request.client", "await request.body", "request.query_params", "traceback", "copyfast_bridge", "PayOS", "requests.", "httpx."):
        assert forbidden not in capture
    assert '"execution": "web_native_reliability_metadata_only"' in RELIABILITY
    assert "no repair, deployment, money, provider, Bot or customer contact" in RELIABILITY


def test_reliability_support_handoff_is_server_resolved_and_route_constrained() -> None:
    """The queue must never expose a source ID or accept a browser redirect."""

    assert 'GET  /api/v1/operations/admin/followups/{id}/handoff' not in RELIABILITY
    assert '@router.get("/api/v1/operations/admin/followups/{followup_id}/handoff")' in RELIABILITY
    handoff_start = RELIABILITY.index("async def support_handoff(")
    handoff_end = RELIABILITY.index("def _mutate_followup(", handoff_start)
    handoff = RELIABILITY[handoff_start:handoff_end]
    for requirement in (
        "require_support_staff(account)",
        "followup.source_kind='support_triage'",
        "followup.state IN ('open', 'acknowledged')",
        "support_case.revision",
        "triage.source_revision",
        "protected_support_case_navigation_only",
        'f"/admin/support/{case_id}"',
        "source_content_copied",
        "support_case_mutated",
        "web.operations.reliability_followup.handoff_read",
    ):
        assert requirement in handoff
    for forbidden in ("copyfast_bridge", "PayOS", "provider", "telegram", "email", "restart", "deploy", "requests.", "httpx."):
        assert forbidden.lower() not in handoff.lower()

    verifier = _function_source(INTEGRATION, "reliabilityHandoffIsSafe")
    for requirement in (
        "reliabilityBoundaryIsSafe(source)",
        'handoff.execution === "protected_support_case_navigation_only"',
        "supportAdminCaseIdFromPath(targetRoute)",
        "targetRoute === `/admin/support/${targetId}`",
        "source_content_copied === false",
        "support_case_mutated === false",
    ):
        assert requirement in verifier

    renderer = _between(PORTAL, "function renderReliabilityAdmin(page, context)", "function renderTickets(page, context)")
    assert 'data-portal-action="reliability-followup-handoff"' in renderer
    assert 'String(item.source_kind || "") !== "support_triage"' in renderer
    assert '!["open", "acknowledged"].includes(state)' in renderer

    action_start = INTEGRATION.index('if (action === "reliability-followup-handoff")')
    action_end = INTEGRATION.index('if (["reliability-followup-acknowledge"', action_start)
    action = INTEGRATION[action_start:action_end]
    for requirement in (
        'api(`/operations/admin/followups/${encodeURIComponent(followupId)}/handoff`)',
        "reliabilityHandoffIsSafe(result.data)",
        "window.history.pushState({}, \"\", handoffRoute)",
        "await hydrate()",
    ):
        assert requirement in action
    for forbidden in ("source_id", "case_id", "copyfast_bridge", "/payments", "/jobs", "wallet", "payos", "provider", "telegram", "restart", "deploy"):
        assert forbidden not in action.lower()


def test_service_worker_never_caches_reliability_staff_metadata() -> None:
    # Cache revisions intentionally change with public-shell releases. The
    # privacy invariant is the shell-only cache boundary below, not one stale
    # release number in this contract test.
    assert "const CACHE_PREFIX =" in SERVICE_WORKER
    assert "const BUILD_ID =" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    for private_prefix in ('"/" + "api/v1/operations"', '"/admin/reliability"'):
        assert private_prefix in SERVICE_WORKER
        assert private_prefix not in shell
    assert "private `/admin/reliability/*`" in SERVICE_WORKER
    assert "isPrivatePath" in SERVICE_WORKER


def test_reliability_hydration_rejects_stale_staff_session_route_and_page_responses() -> None:
    """A delayed staff queue must never repopulate after bootstrap or navigation."""

    for declaration in (
        "let operationsSessionEpoch = 0;",
        "let reliabilityHydrationEpoch = 0;",
    ):
        assert declaration in INTEGRATION

    bootstrap = _between(INTEGRATION, "const currentAdminErpNavigationEpoch", "    merge({")
    for invalidation in ("++operationsSessionEpoch;", "++reliabilityHydrationEpoch;"):
        assert invalidation in bootstrap

    guard = _function_source(INTEGRATION, "operationsRequestIsCurrent")
    for invariant in (
        "requestEpoch === currentEpoch",
        "sessionEpoch === operationsSessionEpoch",
        "currentPortalPath() === expectedPath",
        "base().session && base().session.authenticated === true",
    ):
        assert invariant in guard

    hydrate = _function_source(INTEGRATION, "hydrateReliabilityAdmin")
    assert "const requestEpoch = ++reliabilityHydrationEpoch;" in hydrate
    assert "const sessionEpoch = operationsSessionEpoch;" in hydrate
    assert "const expectedPath = currentPortalPath();" in hydrate
    assert 'if (expectedPath !== "/admin/reliability") return { stale: true };' in hydrate
    # The same guard must run before both the success merge and the
    # fail-closed merge, otherwise a late rejected response can still erase a
    # newer staff queue.
    assert hydrate.count("operationsRequestIsCurrent(") >= 2
