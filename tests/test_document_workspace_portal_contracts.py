"""Focused contracts for the private Document & PDF Workspace portal.

The new workspace is a Web-native planning/review surface.  It must not blur
the line with the independent deterministic `/documents/*` utilities or make
an OCR, conversion, output, download, payment, or Bot job claim in the UI.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "copyfast_document_workspace.py").read_text(encoding="utf-8")


def _document_surface() -> str:
    start = PORTAL.index("const DOCUMENT_WORKSPACE_TYPES")
    return PORTAL[start:PORTAL.index("const SUBTITLE_STUDIO_FORMATS", start)]


def _document_integration_helpers() -> str:
    start = INTEGRATION.index("const DOCUMENT_WORKSPACE_TYPES")
    return INTEGRATION[start:INTEGRATION.index("const SUBTITLE_STUDIO_FORMATS", start)]


def test_document_workspace_is_native_and_precedes_legacy_document_routes() -> None:
    assert 'customerPage("/document-workspace"' in PORTAL
    assert 'customerPage("/document-workspace/new"' in PORTAL
    assert 'path: "/document-workspace/:id"' in PORTAL
    assert "function renderDocumentWorkspace(" in PORTAL
    assert "function renderDocumentWorkspaceDetail(" in PORTAL
    assert 'case "document-workspace": return renderDocumentWorkspace(page, context);' in PORTAL
    assert 'case "document-workspace-detail": return renderDocumentWorkspaceDetail(page, context);' in PORTAL
    assert "DOCUMENT_WORKSPACE_PATH" in PAGES
    assert "DOCUMENT_WORKSPACE_PATH.fullmatch(normalized)" in PAGES
    assert 'if (linkPath === "/document-workspace") return matchesRouteFamily(path, "/document-workspace");' in PORTAL

    # The native family is claimed before the historical `/documents/*` tool
    # matcher; otherwise a signed workspace route could hydrate the wrong UI.
    assert "function isNativeDocumentWorkspacePath(" in INTEGRATION
    assert "isNativeDocumentWorkspacePath(path)" in INTEGRATION
    assert "isNativeDocumentWorkspacePath(currentPath)" in INTEGRATION
    assert "else if (isNativeDocumentWorkspacePath(currentPath))" in INTEGRATION


def test_document_workspace_keeps_authoring_boundary_and_owner_scoped_refs() -> None:
    helpers = _document_integration_helpers()
    for helper in (
        "documentWorkspaceSafetyError",
        "documentWorkspacePayload",
        "documentPlanPayload",
        "documentWorkspaceBoundaryIsSafe",
    ):
        assert f"function {helper}" in helpers

    for flag in (
        'boundary.execution === "authoring_only"',
        "boundary.provider_called === false",
        "boundary.ocr_called === false",
        "boundary.translation_called === false",
        "boundary.output_created === false",
        "boundary.job_created === false",
        "boundary.payment_started === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_processed === false",
        "boundary.browser_file_upload === false",
        "boundary.preview_available === false",
        'boundary.output_delivery === "guarded"',
    ):
        assert flag in helpers

    surface = _document_surface()
    assert "Asset Vault metadata" in surface
    assert "Không upload/đọc file" in surface
    assert "Không có raw upload, file path" in surface
    assert "const writable = state === \"draft\";" in surface
    assert "fetch(" not in surface
    assert "api(" not in surface
    assert "localStorage" not in surface
    for forbidden in (
        'data-portal-action="document-workspace-execute"',
        'data-portal-action="document-plan-execute"',
        'data-portal-action="document-workspace-download"',
        'data-portal-action="document-plan-download"',
        "/document-workspace/output",
        "/document-workspace/download",
    ):
        assert forbidden not in surface


def test_document_workspace_forms_have_real_signed_mutation_handlers() -> None:
    # Every rendered authoring control must reach the dedicated guarded API
    # with server-owned revisions; no button may silently fall through to the
    # generic "waiting adapter" toast.
    for action in (
        "document-workspace-refresh",
        "document-workspace-create",
        "document-workspace-update",
        "document-workspace-state",
        "document-workspace-restore-version",
        "document-plan-create",
        "document-plan-update",
        "document-plan-archive",
        "document-plan-restore",
        "document-plan-restore-version",
        "document-plan-reorder",
    ):
        assert f'action === "{action}"' in INTEGRATION

    assert "async function documentWorkspaceMutation(" in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "expected_revision: expectedRevision" in INTEGRATION
    assert "documentWorkspaceBoundaryIsSafe(result.data)" in INTEGRATION
    assert "__documentWorkspaceId" in PORTAL
    assert "__documentPlanRevision" in PORTAL
    assert "data-document-plan-version" in PORTAL


def test_document_workspace_links_to_but_never_runs_existing_deterministic_tools() -> None:
    surface = _document_surface()
    assert "Separate deterministic utilities" in surface
    for route in (
        "/documents/split",
        "/documents/merge",
        "/documents/compress",
        "/documents/image-to-pdf",
        "/documents/pdf-to-images",
        "/documents/pdf-to-word",
    ):
        assert f'href="{route}"' in surface

    # The authoring router cannot import or delegate to the executor.  It
    # owns no binary output/download lifecycle; existing tools retain theirs.
    assert "import copyfast_document_operations" not in WORKSPACE
    assert "from copyfast_document_operations" not in WORKSPACE
    assert 'prefix="/api/v1/document-workspace"' in WORKSPACE
    assert 'prefix="/api/v1/document-operations"' not in WORKSPACE


def test_document_workspace_private_routes_are_explicitly_outside_pwa_cache() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/document-workspace" in SERVICE_WORKER
    assert "private `/document-workspace/*` routes" in SERVICE_WORKER
    assert "api/v1/document-workspace" in SERVICE_WORKER
    assert '"/document-workspace"' in SERVICE_WORKER
    assert "PRIVATE_PATH_PREFIXES" in SERVICE_WORKER
    assert "isPrivatePath" in SERVICE_WORKER
    assert "/api/v1/document-workspace" not in shell
    assert '"/document-workspace"' not in shell
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v14"' in SERVICE_WORKER
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER

    for selector in (
        ".portal-document-workspace-intro",
        ".portal-document-workspace-grid",
        ".portal-document-plan-card",
        ".portal-document-workspace-estimate-grid",
        ".portal-document-workspace-guard-list",
        ".portal-document-workspace-intro, .portal-document-workspace-detail-summary, .portal-document-workspace-layout, .portal-document-workspace-detail-grid, .portal-document-workspace-history-grid { grid-template-columns: 1fr; }",
        ".portal-document-workspace-grid, .portal-document-plan-grid { grid-template-columns: 1fr; }",
        ".portal-document-workspace-intro dl, .portal-document-workspace-detail-summary dl, .portal-document-workspace-estimate-grid, .portal-document-workspace-guard-list { grid-template-columns: 1fr; }",
        ".portal-document-plan-form .portal-fields { grid-template-columns: 1fr; }",
        ".portal-document-version-list > article { align-items: flex-start; flex-direction: column; }",
    ):
        assert selector in CSS
