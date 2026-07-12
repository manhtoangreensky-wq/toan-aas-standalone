"""Static UI contracts for the independent Web Document Operations surface."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "PDF_SPLIT_CONTRACT.md").read_text(encoding="utf-8")


def test_pdf_split_replaces_the_generic_bot_feature_form_with_a_native_web_surface() -> None:
    assert 'customerPage("/documents/split", "Tách PDF riêng tư"' in PORTAL
    assert 'layout: "pdf-split", type: "document-operation", action: "none"' in PORTAL
    assert 'featurePage("/documents/split"' not in PORTAL
    assert "function renderPdfSplit(page, context)" in PORTAL
    assert 'case "pdf-split": return renderPdfSplit(page, context);' in PORTAL
    assert "function pdfSplitFormFields()" in PORTAL
    assert 'optionsFrom: "pdfVaultAssets"' in PORTAL
    assert 'name: "source_asset_id"' in PORTAL
    assert 'name: "page_range"' in PORTAL
    assert 'data-portal-action="document-operation-pdf-split"' in PORTAL
    assert 'data-portal-action="document-operation-refresh"' in PORTAL
    assert "function documentOperationDownloadPath(item)" in PORTAL
    assert '`/api/v1/document-operations/${encodeURIComponent(operationId)}/download`' in PORTAL
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    assert 'if normalized == "/documents/split":' in pages
    assert 'return "Tách PDF riêng tư"' in pages


def test_pdf_split_portal_keeps_source_and_output_boundaries_explicit() -> None:
    surface = PORTAL[PORTAL.index("function renderPdfSplit(page, context)"):PORTAL.index("function renderAssetVault(page, context)")]
    assert "Asset Vault" in surface
    assert "không upload bytes" in surface
    assert "Không fallback sang static, browser storage, Bot job hoặc provider" in surface
    assert "không tạo Job Bot" in surface
    assert "PayOS order" in surface
    assert "fetch(" not in surface
    assert "api(" not in surface
    assert "localStorage" not in surface
    assert "data-portal-confirm" in surface
    assert "document_operation" not in surface.lower()  # no server table shape leaks into rendered HTML


def test_pdf_split_hydration_and_write_are_signed_web_only_not_bridge_backed() -> None:
    assert "const documentOperationsEnabled" in INTEGRATION
    assert '"document-operation-view": Boolean(account && assetVaultEnabled && documentOperationsEnabled)' in INTEGRATION
    assert '"document-operation-pdf-split": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled)' in INTEGRATION
    assert "async function hydrateDocumentOperations()" in INTEGRATION
    assert 'api("/document-operations")' in INTEGRATION
    assert 'api("/document-operations/pdf-split"' in INTEGRATION
    assert "validDocumentOperationId" in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "document-operation-pdf-split")'):
        INTEGRATION.index('if (action === "project-package-export")')
    ]
    assert "source_asset_id: sourceAssetId" in action
    assert "page_range: pageRange" in action
    assert "idempotency_key: submission.key" in action
    assert "hydrateDocumentOperations" in action
    assert "hydrateAssetVault" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action


def test_document_operation_shell_is_responsive_and_never_pwa_cached_as_private_data() -> None:
    for selector in (
        ".portal-document-operation-intro",
        ".portal-document-operation-layout",
        ".portal-document-operation-grid",
        ".portal-document-operation-card",
        ".portal-document-operation-meta",
    ):
        assert selector in CSS
    assert ".portal-document-operation-intro, .portal-document-operation-layout { grid-template-columns: 1fr; }" in CSS
    assert ".portal-document-operation-grid { grid-template-columns: 1fr; }" in CSS
    assert "/api/v1/document-operations" in SERVICE_WORKER
    assert "SHELL_PATHS" in SERVICE_WORKER
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v4";' in SERVICE_WORKER


def test_pdf_split_contract_records_separate_private_storage_and_no_bot_payment_provider_execution() -> None:
    for phrase in (
        "Asset Vault",
        "separate from Asset Vault and Project Package",
        "20 MiB",
        "30 source pages",
        "signed-session ownership checks",
        "No browser-to-provider call",
        "PayOS",
        "pypdf",
    ):
        assert phrase in CONTRACT
