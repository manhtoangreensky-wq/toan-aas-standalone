"""Focused browser contracts for the read-only ERP Operations Desk.

The API behaviour is covered by ``test_operations_desk.py``.  These source
contracts keep the Portal integration from widening that reviewed API into a
browser-owned authority, identifier search, write surface, or stale queue.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_operations_desk_is_a_server_authorized_read_only_admin_route() -> None:
    declaration = _between(PORTAL, 'adminPage("/admin/work-queue"', 'adminPage("/admin/campaigns"')

    assert 'layout: "operations-desk"' in declaration
    assert "Desk không gọi Bot/Core Bridge, provider, PayOS, ví Xu, job, delivery, deploy hay ghi thay đổi." in declaration
    assert 'case "operations-desk": return renderOperationsDesk(page, context);' in PORTAL
    assert 'or normalized == "/admin/work-queue"' in APP
    assert "copyfast_support.require_support_staff(current_session(request)[\"account\"])" in APP


def test_operations_desk_client_projection_drops_identifier_and_route_fields() -> None:
    projection = _between(INTEGRATION, "function operationsDeskItemProjection", "function operationsDeskItems")

    assert "source.target_route !== OPERATIONS_DESK_TARGETS[kind]" in projection
    assert "const actionValues = source && Array.isArray(source.available_actions)" in projection
    assert "return level.key === \"priority\"" in projection
    assert "target_route:" not in projection
    assert "available_actions:" not in projection
    for forbidden in ("source.id", "source.account", "source.email", "source.title", "source.detail", "source.payload"):
        assert forbidden not in projection
    assert "target routes, IDs, account fields, titles, details, payloads" in projection


def test_operations_desk_bootstrap_normalizer_preserves_only_the_redacted_staff_projection() -> None:
    """A later portal render must not discard the already-authorized queue."""

    summary = _between(PORTAL, "function normalizeOperationsDeskSummary", "function operationsDeskBootstrapItemProjection")
    items = _between(PORTAL, "function operationsDeskBootstrapItemProjection", "function normalizeOperationsDeskFilter")
    listing = _between(PORTAL, "function normalizeOperationsDeskListing", "function normalizeBootstrap")
    bootstrap = _between(PORTAL, "function normalizeBootstrap", "function getBootstrap")

    assert "rawSources.length !== OPERATIONS_DESK_BOOTSTRAP_KIND_LIST.length" in summary
    assert "kind !== OPERATIONS_DESK_BOOTSTRAP_KIND_LIST[index]" in summary
    assert "if (item.count !== null) return null;" in summary
    assert "Never turn a guarded/unavailable source into a plausible zero" in summary
    assert "OPERATIONS_DESK_BOOTSTRAP_STATES_BY_KIND[kind].has(state)" in items
    assert 'const expectedKeys = new Set(["kind", "state", "updated_at", level.key]);' in items
    assert "return level.key === \"priority\"" in items
    for forbidden in ("source.id", "source.account", "source.email", "source.title", "source.detail", "source.payload", "target_route", "available_actions"):
        assert forbidden not in items
    assert "returned !== safeItems.length" in listing
    assert "pagination.previous_offset !== expectedPrevious" in listing
    assert "pagination.next_offset !== offset + limit" in listing
    assert "next_offset: pagination.next_offset" in listing
    assert "previous_offset: expectedPrevious" in listing
    for field in (
        "operationsDeskSummary,",
        "operationsDeskItems,",
        "operationsDeskFilter,",
        "operationsDeskListing,",
        "operationsDeskReadState,",
    ):
        assert field in bootstrap


def test_operations_desk_reads_are_fenced_and_allow_only_guarded_partial_envelopes() -> None:
    fence = _between(INTEGRATION, "function operationsDeskRequestIsCurrent", "async function hydrateOperationsDesk")
    for requirement in (
        "requestEpoch === operationsDeskHydrationEpoch",
        "sessionEpoch === operationsDeskSessionEpoch",
        'expectedPath === "/admin/work-queue"',
        "currentPortalPath() === expectedPath",
        "base().operationsDeskEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in fence

    reader = _between(INTEGRATION, "async function operationsDeskRead", "function operationsDeskRequestIsCurrent")
    assert 'payload.ok === true || (payload.ok === false && status === "guarded")' in reader
    assert '!response.ok || !accepted' in reader
    assert 'headers: { Accept: "application/json", "X-Request-ID": randomKey("web") }' in reader
    assert "localStorage" not in reader
    assert "sessionStorage" not in reader

    hydrator = _between(INTEGRATION, "async function hydrateOperationsDesk", "function operationsRequestIsCurrent")
    for requirement in (
        'operationsDeskRead("/admin/operations-desk/summary")',
        "operationsDeskRead(operationsDeskListPath(filter, offset))",
        "operationsDeskSummaryProjection(summaryResponse.data)",
        "operationsDeskWorkItemsProjection(listResponse.data, filter, offset)",
        "summary.partial !== list.partial",
        'operationsDeskSummary: { sources: [], partial: true }',
        "operationsDeskSummary: { sources: summary.sources, partial }",
        "operationsDeskItems: list.items",
        'operationsDeskReadState: partial ? "guarded" : "ready"',
        'operationsDeskReadState: "failed"',
    ):
        assert requirement in hydrator


def test_operations_desk_filters_and_actions_are_read_only_allowlists() -> None:
    filter_code = _between(INTEGRATION, "function operationsDeskFilterPayload", "function operationsDeskListPath")
    for requirement in ("OPERATIONS_DESK_KINDS", "OPERATIONS_DESK_STATES", "OPERATIONS_DESK_SEVERITIES", "OPERATIONS_DESK_VIEWS"):
        assert requirement in filter_code
    assert "return { kind, state, severity, view };" in filter_code

    list_path = _between(INTEGRATION, "function operationsDeskListPath", "function operationsDeskCount")
    assert "view: safeFilter.view" in list_path

    actions = _between(INTEGRATION, 'if (action === "operations-desk-refresh")', 'if (action === "operations-refresh")')
    for requirement in (
        'action === "operations-desk-refresh"',
        'action === "operations-desk-filter"',
        'action === "operations-desk-filter-clear"',
        'action === "operations-desk-page"',
        "hydrateOperationsDesk",
    ):
        assert requirement in actions
    assert "method: \"POST\"" not in actions
    assert "api(" not in actions

    view = _between(PORTAL, "function renderOperationsDesk", "function renderOperationsAdmin")
    pagination = _between(PORTAL, "function operationsDeskPagination", "function renderOperationsDesk")
    assert 'data-portal-action="operations-desk-refresh"' in view
    assert 'data-portal-action="operations-desk-filter"' in view
    assert 'data-portal-action="operations-desk-page"' in pagination
    assert "OPERATIONS_DESK_TARGETS[kind]" in view
    assert "target_route" not in view
    assert "available_actions" not in view
    assert "Không dùng số 0 thay cho nguồn guarded/unavailable" in view
    assert 'name="view"' in view
    assert 'value="attention"' in view
    assert "data-portal-no-transient" in view
    assert "Cần xử lý được máy chủ lọc trước khi đếm và phân trang" in view


def test_operations_desk_attention_view_stays_a_read_only_server_filter() -> None:
    source = (ROOT / "copyfast_operations_desk.py").read_text(encoding="utf-8")
    policy = _between(source, "def _attention_clause", "def _query_for")
    route = _between(source, "async def work_items", "return envelope(")
    reset = _between(INTEGRATION, "operationsDeskFilter: { kind: \"all\"", "operationsDeskReadState")

    for requirement in (
        '_WORK_ITEM_VIEWS = frozenset({"all", "attention"})',
        "def _normalize_view",
        "state NOT IN ('resolved', 'closed')",
        "state IN ('open', 'investigating')",
        "state='awaiting_approval'",
        "state IN ('open', 'acknowledged')",
        "handoff_status IN ('review', 'approved_for_handoff', 'blocked')",
    ):
        assert requirement in source if requirement.startswith("_") or requirement.startswith("def ") else requirement in policy
    assert "requested_view = _normalize_view(view)" in route
    assert "view=requested_view" in source
    assert "view: \"all\"" in reset
    for forbidden in ("account_id", "assigned_account_id", "source_id", "target_route", "request_id"):
        assert forbidden not in policy
