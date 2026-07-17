"""Focused presentation contracts for Web-native Governance Documents.

The API suite owns authorization, DLP, revision and idempotency behavior.
These checks make sure the Portal keeps the same fail-closed, no-Bot boundary
instead of rendering an attractive screen that cannot safely execute.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_governance_routes_render_server_scoped_list_and_detail_workspaces() -> None:
    portal = _read("static/portal/portal.js")

    for requirement in (
        'adminPage("/admin/governance", "Governance Documents"',
        'layout: "governance-documents"',
        'path: "/admin/governance/documents/:id"',
        'layout: "governance-document-detail"',
        'case "governance-documents": return renderGovernanceDocuments(page, context);',
        'case "governance-document-detail": return renderGovernanceDocumentDetail(page, context);',
        'if (linkPath === "/admin/governance") return matchesRouteFamily(path, "/admin/governance");',
        '["/admin/governance/documents"]',
    ):
        assert requirement in portal

    list_view = _between(portal, "function renderGovernanceDocuments", "function governanceLifecycleForm")
    for action in (
        "governance-document-create",
        "governance-documents-filter",
        "governance-documents-filter-clear",
        "governance-documents-refresh",
    ):
        assert f'data-portal-action="{action}"' in list_view
    assert 'data-portal-action="governance-documents-page"' in portal
    assert list_view.count("data-portal-no-transient") >= 2
    assert "Tài liệu Bot vẫn là Telegram-only" in list_view
    assert "Không đọc Bot documents" in list_view
    assert "localStorage." not in list_view
    assert "sessionStorage." not in list_view
    assert "data-governance-type-map" in list_view
    assert "function synchronizeGovernanceDocumentType" in portal
    assert "event.target.name === \"department\"" in portal

    detail_view = _between(portal, "function governanceLifecycleForm", "function renderLegal")
    for requirement in (
        'data-portal-action="governance-document-update"',
        "governanceLifecycleForm(source, 'submit-review'",
        "capabilities['governance-document-approve']",
        "capabilities['governance-document-reject']",
        "capabilities['governance-document-archive']",
        "capabilities['governance-document-restore']",
    ):
        assert requirement in detail_view
    assert detail_view.count("data-portal-no-transient") >= 2
    assert "Người tạo không thể tự duyệt" in detail_view
    assert "Không có auto-approve, auto-publish hoặc external action." in detail_view


def test_governance_hydration_and_write_contract_stay_isolated_from_bot_and_bridge() -> None:
    integration = _read("static/portal/integration.js")
    helpers = _between(integration, "const GOVERNANCE_DOCUMENT_STATES", "function dataControlsRequestIsCurrent")
    actions = _between(
        integration,
        'if (action === "governance-documents-refresh")',
        'if (action === "data-controls-refresh")',
    )

    for requirement in (
        "governanceDocumentsSessionEpoch",
        "governanceDocumentsHydrationEpoch",
        "governanceDocumentDetailHydrationEpoch",
        "isNativeGovernanceDocumentsPath",
        'api("/admin/governance/policy")',
        'api("/admin/governance/summary")',
        "/admin/governance/documents/",
        "governanceBoundaryIsSafe",
        'external_effects === "none"',
        "source.by_state",
        "source.to_state || source.state",
        "retention_label",
        "confidentiality_level",
        "review_note",
        'clearGovernanceProjection("guarded")',
        "function governanceRetentionLabel",
        "GOVERNANCE_RETENTION_LABELS.has(label)",
    ):
        assert requirement in integration or requirement in helpers

    for requirement in (
        "governanceCreatePayload",
        "governanceUpdatePayload",
        "expected_revision",
        "acknowledgement",
        "confirm: true",
        "idempotency_key: submission.key",
        'operation === "reject" && !reviewNote',
        "await hydrateGovernanceDocumentDetail(documentId)",
    ):
        assert requirement in actions or requirement in helpers
    assert "/internal/v1/" not in helpers
    assert 'api("/wallet' not in helpers
    assert 'api("/payments' not in helpers
    assert 'api("/jobs' not in helpers

    portal = _read("static/portal/portal.js")
    projection = _between(portal, "function normalizeGovernanceBootstrapDocument", "function normalizeAssetVaultLifecycle")
    assert "function governanceBootstrapRetentionLabel" in portal
    assert "const retentionLabel = governanceBootstrapRetentionLabel(source.retentionLabel);" in projection
    assert "source.retentionLabels.map(governanceBootstrapRetentionLabel)" in projection


def test_governance_private_navigation_router_and_worker_boundaries_are_explicit() -> None:
    app = _read("app.py")
    portal = _read("static/portal/portal.js")
    worker = _read("static/portal/service-worker.js")
    navigation = _read("copyfast_admin_erp_navigation.py")

    assert "import copyfast_governance" in app
    assert "app.include_router(copyfast_governance.router)" in app
    assert 'normalized == "/admin/governance" or normalized.startswith("/admin/governance/")' in app
    assert "copyfast_auth.require_admin(request)" in app
    assert '"/" + "api/v1/admin/governance"' in worker
    assert '"/admin/governance"' in worker
    assert "governance_documents" in navigation
    assert '"/admin/governance"' in navigation
    assert "WEBAPP_GOVERNANCE_DOCUMENTS_ENABLED" in navigation
    assert 'Object.assign(fields, { __governanceOffset: source.getAttribute("data-governance-offset") || "" });' in portal
