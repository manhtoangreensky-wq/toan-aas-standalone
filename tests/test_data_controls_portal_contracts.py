"""Static browser contracts for the Web-only Data Control Center.

The API/database test suite owns server authorization and mutation semantics.
These focused checks ensure the Portal does not regress into a Bot data-delete
shortcut, browser persistence, or a cacheable private route.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_data_controls_has_a_distinct_guarded_web_route() -> None:
    assert 'customerPage("/account/data-controls", "Kiểm soát dữ liệu Web"' in PORTAL
    assert 'layout: "account-data-controls"' in PORTAL
    assert 'href="/account/data-controls">Kiểm soát dữ liệu Web →</a>' in PORTAL
    assert 'case "account-data-controls": return renderAccountDataControls(page, context);' in PORTAL

    view = _between(PORTAL, "function renderAccountDataControls", "function renderLegal")
    for action in (
        "data-controls-refresh",
        "data-controls-export",
        "data-controls-erasure-request",
        "data-controls-erasure-cancel",
    ):
        assert f'data-portal-action="{action}"' in view
    assert view.count("data-portal-no-transient") >= 2
    assert "Không có thao tác tự động" in view
    assert "Không gọi Bot" in view
    assert "Không có hành động ngầm" in view
    assert "<code>/data_delete</code> trong Bot" in view
    assert "localStorage." not in view
    assert "sessionStorage." not in view


def test_data_controls_hydration_is_flagged_owner_scoped_and_route_fenced() -> None:
    for epoch in ("dataControlsSessionEpoch", "dataControlsHydrationEpoch"):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION
    assert 'status.flags.data_controls_enabled === true' in INTEGRATION
    assert '"data-controls-view": Boolean(account && dataControlsEnabled)' in INTEGRATION
    assert '"data-controls-export": Boolean(account && me.csrf_token && dataControlsEnabled)' in INTEGRATION
    assert '"/account/data-controls": account && dataControlsEnabled ? "processing" : "guarded"' in INTEGRATION
    assert 'if (account && dataControlsEnabled && currentPath === "/account/data-controls")' in INTEGRATION
    assert 'currentPath !== "/account/data-controls"' in INTEGRATION

    helpers = _between(INTEGRATION, "const DATA_CONTROLS_POLICY_VERSION", "async function hydrateWorkspaceDrafts")
    for requirement in (
        'expectedPath === "/account/data-controls"',
        "requestEpoch === dataControlsHydrationEpoch",
        "sessionEpoch === dataControlsSessionEpoch",
        "base().dataControlsEnabled === true",
        'api("/account/data-controls/summary")',
        'return `/account/data-controls/requests?limit=${DATA_CONTROLS_LIST_LIMIT}&offset=${dataControlsRequestedOffset(offset)}`',
        "dataControlsBoundaryIsSafe",
        "dataControlsSummaryProjection",
        "dataControlsRequestProjection",
        "clearDataControlsProjection(\"guarded\")",
    ):
        assert requirement in helpers
    assert "localStorage." not in helpers
    assert "sessionStorage." not in helpers
    assert '"/data_delete"' not in helpers


def test_data_control_writes_use_csrf_confirmation_idempotency_and_server_attachment() -> None:
    actions = _between(
        INTEGRATION,
        'if (action === "data-controls-refresh")',
        'if (action === "account-security-refresh")',
    )
    for requirement in (
        'fetch(`${API}/account/data-controls/export.json`',
        '"X-CSRF-Token"',
        "policy_version: DATA_CONTROLS_POLICY_VERSION",
        "scope_key: DATA_CONTROLS_SCOPE_KEY",
        "acknowledgement: DATA_CONTROLS_ERASURE_ACKNOWLEDGEMENT",
        "acknowledgement: DATA_CONTROLS_CANCEL_ACKNOWLEDGEMENT",
        "idempotency_key: submission.key",
        "expected_revision: expectedRevision",
        "dataControlsWriteBoundary(result.data)",
        "await hydrateDataControls(0)",
        "URL.createObjectURL(blob)",
        "URL.revokeObjectURL(url)",
        "guardedEnvelope && guardedEnvelope.ok === false",
    ):
        assert requirement in INTEGRATION
    assert '"/data_delete"' not in actions


def test_data_controls_survives_the_strict_presentation_projection_and_private_pwa_boundary() -> None:
    projection = _between(PORTAL, "function normalizeDataControlsBootstrap", "function normalizeOperationsAdminQueueStates")
    for requirement in (
        "DATA_CONTROLS_POLICY_VERSION",
        "DATA_CONTROLS_SCOPE_KEY",
        "DATA_CONTROLS_CATEGORY_ORDER",
        "DATA_CONTROLS_REQUEST_STATES",
        "rawSummary.automaticDeletion !== false",
        "rawSummary.humanReviewRequired !== true",
        "readState: \"read_only\"",
    ):
        assert requirement in projection
    assert "localStorage." not in projection
    assert "sessionStorage." not in projection
    bootstrap = _between(PORTAL, "function normalizeBootstrap", "function getBootstrap")
    assert "const dataControls = normalizeDataControlsBootstrap" in bootstrap
    assert "dataControlsEnabled: dataControls.enabled" in bootstrap

    assert '"/" + "api/v1/account/data-controls"' in WORKER
    assert '"/account/data-controls"' in WORKER
    assert "export\n   attachments" in WORKER
