"""Static contracts for the controlled Operations Autopilot portal.

Operations is a Web-only observability and approval-record surface.  These
checks make it difficult for a future portal refactor to fall back to the Bot
bridge, mistake a browser timer for an authenticated tick, or advertise an
approval record as a provider/payment execution.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
AUTOPILOT = (ROOT / "copyfast_autopilot.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    """Return a stable source slice and fail clearly if a contract disappears."""
    begin = source.index(start)
    finish = source.index(end, begin + len(start))
    return source[begin:finish]


def _function_source(source: str, name: str) -> str:
    """Read one normal portal helper without assuming its position in the file."""
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    end = match.end() + following.start() if following else len(source)
    return source[match.start():end]


def test_operations_customer_and_staff_routes_are_native_portal_surfaces() -> None:
    customer = _between(
        PORTAL,
        'customerPage("/operations", "Operations Center"',
        'customerPage("/legal"',
    )
    admin = _between(
        PORTAL,
        'adminPage("/admin/operations", "Operations Autopilot"',
        'adminPage("/admin/campaigns"',
    )

    assert 'layout: "operations", action: "none"' in customer
    assert 'layout: "operations-admin", action: "none"' in admin
    assert '["/admin/autopilot"]' in admin
    assert "không gọi Bot, provider, ví Xu, PayOS, job" in customer
    assert "Approval chỉ ghi audit record" in admin
    for layout, renderer in (
        ("operations", "renderOperations"),
        ("operations-admin", "renderOperationsAdmin"),
    ):
        assert f"function {renderer}(page, context)" in PORTAL
        assert f'case "{layout}": return {renderer}(page, context);' in PORTAL


def test_operations_is_excluded_from_generic_bridge_hydration() -> None:
    for helper in (
        "isNativeOperationsPath",
        "operationsBoundaryIsSafe",
        "hydrateOperations",
        "hydrateOperationsAdmin",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    native_path = _function_source(INTEGRATION, "isNativeOperationsPath")
    for path in ('"/operations"', '"/admin/operations"', '"/admin/autopilot"'):
        assert path in native_path
    assert "else if (isNativeOperationsPath(currentPath))" in INTEGRATION

    # Native Operations reads go exclusively to the signed Web API.  The
    # substring intentionally spans both customer and staff hydration helpers.
    for request in (
        'api("/operations/status")',
        'api("/operations/policy")',
        'api("/operations/admin/summary")',
    ):
        assert request in INTEGRATION
    route_block = _between(
        INTEGRATION,
        "if (account && autopilotEnabled) {",
        'if (account && currentPath === "/account/activity")',
    )
    assert 'currentPath === "/operations") await hydrateOperations()' in route_block
    assert '"/admin/operations", "/admin/autopilot"' in route_block
    assert "await hydrateOperationsAdmin()" in route_block
    # The generic bridge hydrator has a separate, explicit native-route gate.
    canonical_gate = INTEGRATION[INTEGRATION.index("if (bridgeAvailable &&") :]
    canonical_gate = canonical_gate[:800]
    assert "!isNativeOperationsPath(currentPath)" in canonical_gate


def test_portal_preserves_unverified_sla_clock_as_a_guarded_state() -> None:
    """A missing semantic SLA clock must never look like a healthy case."""

    assert '"unverified"' in INTEGRATION
    assert 'unverified: "guarded"' in PORTAL
    assert 'unverified: "Chưa xác minh đồng hồ SLA"' in PORTAL
    assert "Không dùng cập nhật nội bộ làm mốc SLA" in PORTAL


def test_operations_pagination_receipts_keep_customer_and_admin_queues_independent() -> None:
    """Each Operations list owns its cursor, receipt state and portal action."""

    for fragment in (
        "const OPERATIONS_INCIDENT_LIST_LIMIT =",
        "const OPERATIONS_ADMIN_RUN_LIST_LIMIT =",
        "const OPERATIONS_ADMIN_INCIDENT_LIST_LIMIT =",
        "const OPERATIONS_APPROVAL_LIST_LIMIT =",
        "const OPERATIONS_MAX_LIST_OFFSET =",
        "function operationsIncidentsPath",
        "function operationsAdminRunsPath",
        "function operationsAdminIncidentsPath",
        "function operationsApprovalsPath",
        "function operationsIncidentListingProjection",
        "function operationsAdminRunListingProjection",
        "function operationsAdminIncidentListingProjection",
        "function operationsApprovalListingProjection",
        "operationsIncidentListing:",
        "operationsAdminRunListing:",
        "operationsAdminIncidentListing:",
        "operationsApprovalListing:",
        'if (action === "operations-incidents-page")',
        'if (action === "operations-admin-runs-page")',
        'if (action === "operations-admin-incidents-page")',
        'if (action === "operations-approvals-page")',
        "__operationsIncidentOffset",
        "__operationsAdminRunOffset",
        "__operationsAdminIncidentOffset",
        "__operationsApprovalOffset",
        "next_offset",
        "previous_offset",
    ):
        assert fragment in INTEGRATION

    for fragment in (
        "function operationsIncidentListing(context)",
        "function operationsAdminRunListing(context)",
        "function operationsAdminIncidentListing(context)",
        "function operationsApprovalListing(context)",
        "function renderOperationsIncidentPagination(listing",
        "function renderOperationsAdminRunPagination(listing",
        "function renderOperationsAdminIncidentPagination(listing",
        "function renderOperationsApprovalPagination(listing",
        "data-portal-action",
        "operations-incidents-page",
        "operations-admin-runs-page",
        "operations-admin-incidents-page",
        "operations-approvals-page",
        "data-operations-incident-offset",
        "data-operations-admin-run-offset",
        "data-operations-admin-incident-offset",
        "data-operations-approval-offset",
    ):
        assert fragment in PORTAL

    customer_start = PORTAL.index("function renderOperations(page, context)")
    customer_end = PORTAL.index("function renderOperationsAdmin(page, context)", customer_start)
    customer = PORTAL[customer_start:customer_end]
    assert "operationsIncidentListing(context)" in customer
    assert "renderOperationsIncidentPagination(" in customer

    admin_start = PORTAL.index("function renderOperationsAdmin(page, context)")
    admin_end = PORTAL.index("function renderReliabilityAdmin(page, context)", admin_start)
    admin = PORTAL[admin_start:admin_end]
    for listing, pager in (
        ("operationsAdminRunListing(context)", "renderOperationsAdminRunPagination("),
        ("operationsAdminIncidentListing(context)", "renderOperationsAdminIncidentPagination("),
        ("operationsApprovalListing(context)", "renderOperationsApprovalPagination("),
    ):
        assert listing in admin
        assert pager in admin


def test_operations_boundary_verifier_fails_closed_for_every_prohibited_side_effect() -> None:
    verifier = _function_source(INTEGRATION, "operationsBoundaryIsSafe")
    for predicate in (
        'boundary.execution === "controlled_web_operations_only"',
        'boundary.data_origin === "signed_web_records_and_authenticated_scheduler_only"',
        "boundary.bot_called === false",
        "boundary.provider_called === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_mutated === false",
        "boundary.payment_processed === false",
        "boundary.customer_reply_sent === false",
        "boundary.external_notification_sent === false",
        "boundary.job_retried === false",
        "boundary.asset_delivery_changed === false",
        "boundary.role_changed === false",
        "boundary.secret_changed === false",
        "boundary.deployment_changed === false",
        "boundary.self_modifying_code === false",
        "boundary.dangerous_action_executed === false",
    ):
        assert predicate in verifier

    # Hydration must discard a malformed/unsafe boundary rather than render its
    # payload as a successful Operations status.
    assert ".every(operationsBoundaryIsSafe)" in INTEGRATION
    assert "operationsBoundaryIsSafe(result.data)" in INTEGRATION


def test_operations_admin_heartbeat_is_a_strict_staff_only_read_projection() -> None:
    heartbeat = _function_source(INTEGRATION, "operationsHeartbeatProjection")
    summary_projection = _function_source(INTEGRATION, "operationsAdminSummaryProjection")
    admin_hydrator = _function_source(INTEGRATION, "hydrateOperationsAdmin")
    customer_renderer = _between(PORTAL, "function renderOperations(page, context)", "function renderOperationsAdmin(page, context)")
    admin_renderer = _between(PORTAL, "function renderOperationsAdmin(page, context)", "function renderReliabilityAdmin(page, context)")

    for requirement in (
        'const OPERATIONS_HEARTBEAT_STATES = new Set(["disabled", "baseline_pending", "within_window", "late", "guarded"]);',
        '"OPS_HEARTBEAT_CONFIG_UNVERIFIED", "OPS_HEARTBEAT_HISTORY_INVALID"',
        'const expectedKeys = ["state", "previous_tick_seen", "late", "code", "open_followups"];',
        "late !== (state === \"late\")",
        "return { state, previous_tick_seen: previousTickSeen, late, code, open_followups: openFollowups };",
    ):
        assert requirement in INTEGRATION
    assert "operationsHeartbeatProjection(source.scheduler_heartbeat)" in summary_projection
    assert "rawSummary" in admin_hydrator
    assert "operationsAdminSummaryProjection(rawSummary)" in admin_hydrator
    assert "operationsAdminSummary: summary" in admin_hydrator
    assert "scheduler_heartbeat" not in customer_renderer
    for requirement in (
        "function operationsHeartbeatPresentation",
        "không phải xác nhận Railway, Bot, provider hay job khỏe",
        "không có repair, restart hay retry tự động",
    ):
        assert requirement in PORTAL
    for requirement in ("Scheduler heartbeat", "Mở Reliability Follow-up"):
        assert requirement in admin_renderer
    assert 'data-portal-action="operations-admin-heartbeat' not in admin_renderer


def test_operations_approval_ui_and_server_remain_record_only() -> None:
    for action in ("operations-approval-approve", "operations-approval-reject"):
        assert action in PORTAL
        assert f'action === "{action}"' in INTEGRATION
    assert '"/operations/admin/approvals/"' in INTEGRATION
    for field in ("expected_revision", "confirm: true", "decision_code", "idempotency_key"):
        assert field in INTEGRATION

    action_start = INTEGRATION.index('if (action === "operations-approval-approve" ||')
    actions = INTEGRATION[action_start:action_start + 5_000].lower()
    for forbidden in ("copyfast_bridge", 'api("/payments', 'api("/jobs'):
        assert forbidden not in actions

    # The server endpoint may record an approval decision but must not acquire
    # an integration client or make money/provider work happen as a consequence.
    assert '"execution": "approval_record_only"' in AUTOPILOT
    assert "no external execution" in AUTOPILOT
    assert "Chưa gọi money/provider/job/deploy" in AUTOPILOT
    for forbidden in (
        "import copyfast_bridge", "from copyfast_bridge", "import requests", "import httpx",
        "import urllib", "import payos", "from payos", "from wallet",
    ):
        assert forbidden not in AUTOPILOT


def test_service_worker_never_caches_operations_records_or_admin_routes() -> None:
    assert "const CACHE_PREFIX =" in SERVICE_WORKER
    assert "const BUILD_ID =" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    for private_prefix in (
        '"/" + "api/v1/operations"',
        '"/" + "internal/v1/operations"',
        '"/operations"',
        '"/admin/operations"',
        '"/admin/autopilot"',
    ):
        assert private_prefix in SERVICE_WORKER
        assert private_prefix not in shell
    assert "private `/operations/*`, private `/admin/operations/*`, private `/admin/reliability/*`" in SERVICE_WORKER
    assert "isPrivatePath" in SERVICE_WORKER


def test_operations_hydration_rejects_stale_session_route_and_newer_list_responses() -> None:
    """Private Operations reads must not win after a bootstrap, route or page change.

    Customer incidents and the three independent staff queues all share one
    signed-session invalidator, while each hydration flow owns a request
    counter.  The helper also binds the response to the route that started
    it, so a delayed `/admin/autopilot` response cannot populate a different
    screen after navigation.
    """

    for declaration in (
        "let operationsSessionEpoch = 0;",
        "let operationsCustomerHydrationEpoch = 0;",
        "let operationsAdminHydrationEpoch = 0;",
    ):
        assert declaration in INTEGRATION

    bootstrap = _between(INTEGRATION, "const currentAdminErpNavigationEpoch", "    merge({")
    for invalidation in (
        "++operationsSessionEpoch;",
        "++operationsCustomerHydrationEpoch;",
        "++operationsAdminHydrationEpoch;",
    ):
        assert invalidation in bootstrap

    guard = _function_source(INTEGRATION, "operationsRequestIsCurrent")
    for invariant in (
        "requestEpoch === currentEpoch",
        "sessionEpoch === operationsSessionEpoch",
        "currentPortalPath() === expectedPath",
        "base().session && base().session.authenticated === true",
    ):
        assert invariant in guard

    customer = _function_source(INTEGRATION, "hydrateOperations")
    assert "const requestEpoch = ++operationsCustomerHydrationEpoch;" in customer
    assert "const sessionEpoch = operationsSessionEpoch;" in customer
    assert "const expectedPath = currentPortalPath();" in customer
    assert 'if (expectedPath !== "/operations") return { stale: true };' in customer
    assert customer.count("operationsRequestIsCurrent(") >= 2

    admin = _function_source(INTEGRATION, "hydrateOperationsAdmin")
    assert "const requestEpoch = ++operationsAdminHydrationEpoch;" in admin
    assert "const sessionEpoch = operationsSessionEpoch;" in admin
    assert "const expectedPath = currentPortalPath();" in admin
    # Both canonical staff aliases are valid hydration origins, but a later
    # navigation must not accept an older response from either one.
    native_paths = _function_source(INTEGRATION, "isNativeOperationsPath")
    for path in ('"/admin/operations"', '"/admin/autopilot"'):
        assert path in native_paths
        assert path in admin
    assert "operationsRequestIsCurrent(" in admin
    assert admin.count("operationsRequestIsCurrent(") >= 2


def test_operations_admin_keeps_verified_summary_when_one_queue_is_guarded() -> None:
    """A transient list error must not turn an authorized ERP view into empty data."""

    queue_projection = _function_source(INTEGRATION, "operationsAdminQueueProjection")
    queue_receipt = _function_source(INTEGRATION, "operationsAdminQueueReceiptIsSafe")
    for requirement in (
        'outcome.status !== "fulfilled"',
        "operationsBoundaryIsSafe(data)",
        "operationsAdminQueueReceiptIsSafe(data, itemValidator, limit, offset)",
        "items: []",
        'readState: "guarded"',
        'readState: "ready"',
    ):
        assert requirement in queue_projection

    # A boundary-valid response is still guarded if it does not carry a
    # complete canonical list receipt.  Silently filtering a broken row would
    # turn a schema failure into an empty staff queue.
    for requirement in (
        "Array.isArray(data.items)",
        "data.items.length > limit",
        "data.items.every(itemValidator)",
        "new Set(ids).size !== ids.length",
        'typeof data.has_more !== "boolean"',
        "data.next_offset === null",
        "data.next_offset === currentOffset + limit",
    ):
        assert requirement in queue_receipt

    hydrator = _function_source(INTEGRATION, "hydrateOperationsAdmin")
    for requirement in (
        "Promise.allSettled([",
        "summaryOutcome.status !== \"fulfilled\"",
        "operationsAdminSummaryProjection(rawSummary)",
        "operationsAdminQueueProjection(",
        "runs: runQueue.readState",
        "incidents: incidentQueue.readState",
        "approvals: approvalQueue.readState",
        "operationsAdminQueueStates: queueStates",
        'operationsAdminReadState: "ready"',
        "operationsAdminQueueStatesProjection({}, \"guarded\")",
    ):
        assert requirement in hydrator

    # Summary remains the mandatory authority proof. A partial queue response
    # cannot unlock staff access by itself.
    assert "operationsBoundaryIsSafe(rawSummary)" in hydrator
    assert '["operator", "manager"].includes(role)' in hydrator

    bootstrap = PORTAL[PORTAL.index("function normalizeBootstrap"):PORTAL.index("function getBootstrap")]
    assert "operationsAdminQueueStates: normalizeOperationsAdminQueueStates(source.operationsAdminQueueStates)" in bootstrap

    renderer = _between(PORTAL, "function renderOperationsAdmin(page, context)", "function renderReliabilityAdmin(page, context)")
    for requirement in (
        "operationsAdminQueueStates(context)",
        'const runReadable = queueStates.runs === "ready";',
        'const incidentReadable = queueStates.incidents === "ready";',
        'const approvalReadable = queueStates.approvals === "ready";',
        "const guardedQueue =",
        "không dùng dữ liệu cũ hoặc coi đó là queue rỗng",
        "allowed && approvalReadable",
        "allowed && runReadable",
        "allowed && incidentReadable",
    ):
        assert requirement in renderer
