"""Regression contracts for the fail-closed Admin ERP Operations Desk."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_operations_desk_rejects_a_malformed_receipt_instead_of_filtering_it_away() -> None:
    sources = _between(INTEGRATION, "function operationsDeskSources", "function operationsDeskUpdatedAt")
    rows = _between(INTEGRATION, "function operationsDeskItemProjection", "function operationsDeskAggregate")
    work_items = _between(INTEGRATION, "function operationsDeskWorkItemsProjection", "function operationsDeskListingProjection")

    assert "raw.length !== expected.length" in sources
    assert "kind !== expected[index]" in sources
    assert "if (source.count !== null) return null;" in sources
    assert "raw.map((entry) => operationsDeskItemProjection(entry, expectedKinds))" in rows
    assert "items.some((item) => !item) ? null : items" in rows
    assert "source.target_route !== OPERATIONS_DESK_TARGETS[kind]" in rows
    assert "source.available_total !== aggregate.availableTotal" in work_items
    assert "source.has_more !== hasMore" in work_items
    assert "source.next_offset !== currentOffset + OPERATIONS_DESK_LIST_LIMIT" in work_items


def test_operations_desk_clears_stale_staff_metadata_before_and_after_a_failed_read() -> None:
    hydrator = _between(INTEGRATION, "async function hydrateOperationsDesk", "function operationsRequestIsCurrent")

    assert "operationsDeskReadState: \"loading\"" in hydrator
    assert "operationsDeskSummary: { sources: [], partial: true }" in hydrator
    assert "operationsDeskItems: []" in hydrator
    assert "operationsDeskReadState: \"failed\"" in hydrator
    assert "summary.partial !== list.partial" in hydrator
    assert "localStorage" not in hydrator
    assert "setTimeout" not in hydrator


def test_operations_desk_second_render_boundary_and_recovery_ui_are_strict() -> None:
    normalizer = _between(PORTAL, "function normalizeOperationsDeskSummary", "function normalizeOperationsDeskFilter")
    bootstrap = _between(PORTAL, "function normalizeBootstrap", "function getBootstrap")
    view = _between(PORTAL, "function renderOperationsDesk", "function renderOperationsAdmin")

    assert "OPERATIONS_DESK_BOOTSTRAP_KIND_LIST" in normalizer
    assert "Object.keys(source).some((key) => !expectedKeys.has(key))" in normalizer
    assert "items.some((item) => !item) ? null : items" in normalizer
    assert "operationsDeskReceiptValid" in bootstrap
    assert 'requestedOperationsDeskReadState === "ready" && !operationsDeskReceiptValid' in bootstrap
    assert "sources.length === Object.keys(OPERATIONS_DESK_TARGETS).length" in view
    assert 'data-portal-action="operations-desk-refresh"' in view
    assert "Máy chủ không thể xác minh receipt Operations Desk hiện tại" in view
    assert "available_actions" not in view
    assert "target_route" not in view
