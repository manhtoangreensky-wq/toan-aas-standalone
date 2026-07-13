"""Static UI contracts for the independent Web Document Operations surface."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "PDF_SPLIT_CONTRACT.md").read_text(encoding="utf-8")
MERGE_CONTRACT = (ROOT / "docs" / "migration" / "PDF_MERGE_CONTRACT.md").read_text(encoding="utf-8")
OPTIMIZE_CONTRACT = (ROOT / "docs" / "migration" / "PDF_OPTIMIZE_CONTRACT.md").read_text(encoding="utf-8")
IMAGE_TO_PDF_CONTRACT = (ROOT / "docs" / "migration" / "IMAGE_TO_PDF_CONTRACT.md").read_text(encoding="utf-8")
PDF_TO_WORD_CONTRACT = (ROOT / "docs" / "migration" / "PDF_TO_WORD_CONTRACT.md").read_text(encoding="utf-8")
PDF_TO_IMAGES_CONTRACT = (ROOT / "docs" / "migration" / "PDF_TO_IMAGES_CONTRACT.md").read_text(encoding="utf-8")


def test_pdf_split_replaces_the_generic_bot_feature_form_with_a_native_web_surface() -> None:
    assert 'customerPage("/documents/split", "Tách PDF riêng tư"' in PORTAL
    assert 'layout: "pdf-split", type: "document-operation", action: "none"' in PORTAL
    assert 'featurePage("/documents/split"' not in PORTAL
    assert "function renderPdfSplit(page, context)" in PORTAL
    assert 'case "pdf-split": return renderPdfSplit(page, context);' in PORTAL
    assert "function pdfSplitFormFields()" in PORTAL
    assert 'documentOperationItems(context, "pdf_split")' in PORTAL
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


def test_pdf_merge_replaces_the_generic_bot_feature_form_with_an_ordered_native_surface() -> None:
    assert 'customerPage("/documents/merge", "Gộp PDF riêng tư"' in PORTAL
    assert 'layout: "pdf-merge", type: "document-operation", action: "none"' in PORTAL
    assert 'featurePage("/documents/merge"' not in PORTAL
    assert "function renderPdfMerge(page, context)" in PORTAL
    assert 'case "pdf-merge": return renderPdfMerge(page, context);' in PORTAL
    assert "function pdfMergeFormFields()" in PORTAL
    assert "Array.from({ length: 8 }" in PORTAL
    assert 'name: `source_asset_id_${position}`' in PORTAL
    assert 'optionsFrom: "pdfVaultAssets"' in PORTAL
    assert 'data-portal-action="document-operation-pdf-merge"' in PORTAL
    assert 'data-portal-route="/documents/merge"' in PORTAL
    assert "PDF 1 → PDF 8" in PORTAL
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    assert 'if normalized == "/documents/merge":' in pages
    assert 'return "Gộp PDF riêng tư"' in pages


def test_pdf_merge_hydration_and_write_are_signed_web_only_not_bridge_backed() -> None:
    assert '"document-operation-pdf-merge": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled)' in INTEGRATION
    assert '"/documents/merge"' in INTEGRATION
    assert '["pdf_split", "pdf_merge", "pdf_optimize", "image_to_pdf", "pdf_to_images", "pdf_to_word_text"].includes(String(item.kind || ""))' in INTEGRATION
    assert 'api("/document-operations/pdf-merge"' in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "document-operation-pdf-merge")'):
        INTEGRATION.index('if (action === "document-operation-refresh")')
    ]
    assert "Array.from({ length: 8 }" in action
    assert "new Set(sourceAssetIds).size" in action
    assert "source_asset_ids: sourceAssetIds" in action
    assert "idempotency_key: submission.key" in action
    assert "hydrateDocumentOperations" in action
    assert "hydrateAssetVault" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action


def test_pdf_optimize_replaces_the_generic_compress_feature_form_with_a_truthful_native_surface() -> None:
    assert 'customerPage("/documents/compress", "Tối ưu PDF riêng tư"' in PORTAL
    assert 'layout: "pdf-optimize", type: "document-operation", action: "none"' in PORTAL
    assert 'featurePage("/documents/compress"' not in PORTAL
    assert "function renderPdfOptimize(page, context)" in PORTAL
    assert 'case "pdf-optimize": return renderPdfOptimize(page, context);' in PORTAL
    assert "function pdfOptimizeFormFields()" in PORTAL
    assert 'data-portal-action="document-operation-pdf-optimize"' in PORTAL
    assert "light/medium/strong" in PORTAL
    assert "file gốc không bị thay đổi" in PORTAL.lower()
    assert "1 KiB" in PORTAL
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    assert 'if normalized == "/documents/compress":' in pages
    assert 'return "Tối ưu PDF riêng tư"' in pages


def test_pdf_optimize_hydration_and_write_are_signed_web_only_not_bridge_backed() -> None:
    assert '"document-operation-pdf-optimize": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled)' in INTEGRATION
    assert '"/documents/compress"' in INTEGRATION
    assert 'api("/document-operations/pdf-optimize"' in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "document-operation-pdf-optimize")'):
        INTEGRATION.index('if (action === "document-operation-refresh")')
    ]
    assert "source_asset_id: sourceAssetId" in action
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
    # The Support Desk public-shell change deliberately rolls the cache so an
    # installed PWA cannot keep a stale integration bundle.
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v' in SERVICE_WORKER


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


def test_pdf_merge_contract_records_ordered_private_sources_and_no_bot_payment_provider_execution() -> None:
    for phrase in (
        "PDF 1 → PDF 8",
        "20 MiB",
        "40 MiB",
        "30 pages",
        "web_document_operation_sources",
        "idempotency key",
        "No Bot bridge",
        "PayOS",
        "pypdf",
    ):
        assert phrase in MERGE_CONTRACT
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"/api/v1/document-operations/pdf-merge"' in app_source


def test_pdf_optimize_contract_records_truthful_lossless_boundary_and_parser_gate() -> None:
    for phrase in (
        "PDF_NOT_REDUCED",
        "20 MiB",
        "1–30 pages",
        "1 KiB and 1%",
        "compress_content_streams",
        "no storage key",
        "No lossy image recompression",
        "PayOS",
        "pypdf",
    ):
        assert phrase in OPTIMIZE_CONTRACT
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    operation_source = (ROOT / "copyfast_document_operations.py").read_text(encoding="utf-8")
    assert '"/api/v1/document-operations/pdf-optimize"' in app_source
    assert "PDF_OPTIMIZE_KIND" in operation_source
    assert "run_in_threadpool" in operation_source
    assert "_has_meaningful_optimization" in operation_source
    assert "bridge_request(" not in operation_source


def test_image_to_pdf_replaces_the_generic_form_with_a_native_ordered_private_surface() -> None:
    assert 'customerPage("/documents/image-to-pdf", "Ảnh sang PDF riêng tư"' in PORTAL
    assert 'layout: "image-to-pdf", type: "document-operation", action: "none"' in PORTAL
    assert 'featurePage("/documents/image-to-pdf"' not in PORTAL
    assert "function renderImageToPdf(page, context)" in PORTAL
    assert 'case "image-to-pdf": return renderImageToPdf(page, context);' in PORTAL
    assert "function imageToPdfFormFields()" in PORTAL
    assert 'documentOperationItems(context, "image_to_pdf")' in PORTAL
    assert 'optionsFrom: "imageVaultAssets"' in PORTAL
    assert 'data-portal-action="document-operation-image-to-pdf"' in PORTAL
    assert 'data-portal-route="/documents/image-to-pdf"' in PORTAL
    assert "Ảnh 1 → Ảnh 8" in PORTAL
    document_pdf = PORTAL[PORTAL.index("documentPdf:"):PORTAL.index("documentOcr: [")]
    assert "documentPdf: []" in document_pdf
    assert 'options: ["pdf_to_images"]' not in document_pdf
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    assert 'if normalized == "/documents/image-to-pdf":' in pages
    assert 'return "Ảnh sang PDF riêng tư"' in pages


def test_image_to_pdf_hydration_and_write_are_signed_web_only_not_bridge_backed() -> None:
    assert "const imageToPdfEnabled" in INTEGRATION
    assert '"document-operation-image-to-pdf": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && imageToPdfEnabled)' in INTEGRATION
    assert '"/documents/image-to-pdf"' in INTEGRATION
    assert "const nativeDocumentPageStates = {" in INTEGRATION
    assert '"/documents/image-to-pdf": base().imageToPdfEnabled === true ? "ready" : "guarded"' in INTEGRATION
    assert "function documentOperationKindForCurrentRoute()" in INTEGRATION
    assert '"/document-operations?kind=image_to_pdf&limit=100"' in INTEGRATION
    assert 'api("/document-operations/image-to-pdf"' in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "document-operation-image-to-pdf")'):
        INTEGRATION.index('if (action === "document-operation-refresh")')
    ]
    assert "Array.from({ length: 8 }" in action
    assert "new Set(sourceAssetIds).size" in action
    assert "source_asset_ids: sourceAssetIds" in action
    assert "idempotency_key: submission.key" in action
    assert "hydrateDocumentOperations" in action
    assert "hydrateAssetVault" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action


def test_image_to_pdf_contract_records_decoder_bounds_private_delivery_and_no_bot_payment_provider_execution() -> None:
    for phrase in (
        "Ảnh 1 → Ảnh 8",
        "20 MiB",
        "40 MiB",
        "16 MP",
        "32 MP",
        "7,680 px",
        "12:1",
        "Pillow",
        "pypdf",
        "WEBAPP_IMAGE_TO_PDF_ENABLED",
        "No Bot bridge",
        "PayOS",
    ):
        assert phrase in IMAGE_TO_PDF_CONTRACT
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    operation_source = (ROOT / "copyfast_document_operations.py").read_text(encoding="utf-8")
    api_source = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert '"/api/v1/document-operations/image-to-pdf"' in app_source
    assert "IMAGE_TO_PDF_KIND" in operation_source
    assert "MAX_IMAGE_PIXELS_PER_SOURCE" in operation_source
    assert "DecompressionBombWarning" in operation_source
    assert "DecompressionBombError" in operation_source
    assert "IMAGE_TO_PDF_MAX_CONCURRENT = 1" in operation_source
    assert "web_native_image_to_pdf_required" in api_source
    assert "bridge_request(" not in operation_source
    assert '"image_to_pdf_enabled": enabled("WEBAPP_IMAGE_TO_PDF_ENABLED", False)' in api_source


def test_pdf_to_word_replaces_the_generic_feature_with_a_truthful_native_private_surface() -> None:
    assert 'customerPage("/documents/pdf-to-word", "PDF có text → Word riêng tư"' in PORTAL
    assert 'layout: "pdf-to-word", type: "document-operation", action: "none"' in PORTAL
    assert 'featurePage("/documents/pdf-to-word"' not in PORTAL
    assert "function renderPdfToWord(page, context)" in PORTAL
    assert 'case "pdf-to-word": return renderPdfToWord(page, context);' in PORTAL
    assert "function pdfToWordFormFields()" in PORTAL
    assert 'documentOperationItems(context, "pdf_to_word_text")' in PORTAL
    assert 'data-portal-action="document-operation-pdf-to-word"' in PORTAL
    assert 'data-portal-route="/documents/pdf-to-word"' in PORTAL
    surface = PORTAL[PORTAL.index("function renderPdfToWord(page, context)"):PORTAL.index("function renderImageToPdf(page, context)")]
    assert "Không OCR" in surface
    assert "không có DOCX giả" in surface
    assert "không upload bytes" in surface
    assert "Bot job" in surface
    assert "PayOS" in surface
    assert "fetch(" not in surface
    assert "api(" not in surface
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    assert 'if normalized == "/documents/pdf-to-word":' in pages
    assert 'return "PDF có text → Word riêng tư"' in pages
    assert 'WebFeature("documents_pdf_to_word"' in registry


def test_pdf_to_word_hydration_and_write_are_signed_web_only_not_bridge_backed() -> None:
    assert "const pdfToWordEnabled" in INTEGRATION
    assert '"document-operation-pdf-to-word": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && pdfToWordEnabled)' in INTEGRATION
    assert '"/documents/pdf-to-word"' in INTEGRATION
    assert '"/documents/pdf-to-word": base().pdfToWordEnabled === true ? "ready" : "guarded"' in INTEGRATION
    assert '"/document-operations?kind=pdf_to_word_text&limit=100"' in INTEGRATION
    assert 'api("/document-operations/pdf-to-word"' in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "document-operation-pdf-to-word")'):
        INTEGRATION.index('if (action === "document-operation-image-to-pdf")')
    ]
    assert "source_asset_id: sourceAssetId" in action
    assert "idempotency_key: submission.key" in action
    assert "hydrateDocumentOperations" in action
    assert "hydrateAssetVault" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action


def test_pdf_to_word_contract_records_text_only_guarded_delivery_and_no_bot_payment_provider_execution() -> None:
    for phrase in (
        "pdf_to_word_text",
        "20 MiB",
        "1–30 page",
        "250,000",
        "25,000",
        "PDF_TEXT_NOT_FOUND",
        "WEBAPP_PDF_TO_WORD_ENABLED",
        "python-docx",
        "No Bot bridge",
        "PayOS",
        "No OCR fallback",
    ):
        assert phrase in PDF_TO_WORD_CONTRACT
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    operation_source = (ROOT / "copyfast_document_operations.py").read_text(encoding="utf-8")
    api_source = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert '"/api/v1/document-operations/pdf-to-word"' in app_source
    assert "PDF_TO_WORD_KIND" in operation_source
    assert "_verify_docx_output" in operation_source
    assert "PDF_TO_WORD_MAX_CONCURRENT = 1" in operation_source
    assert "web_native_pdf_to_word_required" in api_source
    assert '"pdf_to_word_enabled": enabled("WEBAPP_PDF_TO_WORD_ENABLED", False)' in api_source
    assert "bridge_request(" not in operation_source


def test_pdf_to_images_replaces_the_generic_pdf_feature_with_a_private_native_surface() -> None:
    assert 'customerPage("/documents/pdf-to-images", "PDF sang ảnh riêng tư"' in PORTAL
    assert 'layout: "pdf-to-images", type: "document-operation", action: "none"' in PORTAL
    assert 'featurePage("/documents/pdf-to-images"' not in PORTAL
    assert 'customerPage("/documents", "Document Studio"' in PORTAL
    assert 'layout: "document-hub", type: "document-hub", action: "none"' in PORTAL
    assert "function renderDocumentHub(page, context)" in PORTAL
    assert "function renderPdfToImages(page, context)" in PORTAL
    assert 'case "pdf-to-images": return renderPdfToImages(page, context);' in PORTAL
    assert "function pdfToImagesFormFields()" in PORTAL
    assert 'documentOperationItems(context, "pdf_to_images")' in PORTAL
    assert 'data-portal-action="document-operation-pdf-to-images"' in PORTAL
    assert 'data-portal-route="/documents/pdf-to-images"' in PORTAL
    surface = PORTAL[PORTAL.index("function renderPdfToImages(page, context)"):PORTAL.index("function renderPdfToWord(page, context)")]
    for phrase in ("Asset Vault", "2×", "page_001.png", "PNG", "ZIP", "không fallback", "Bot job", "PayOS", "Không upload bytes"):
        assert phrase in surface
    assert "fetch(" not in surface
    assert "api(" not in surface
    assert "localStorage" not in surface
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    assert 'if normalized == "/documents/pdf-to-images":' in pages
    assert 'return "PDF sang ảnh riêng tư"' in pages
    assert 'WebFeature("documents_pdf_to_images"' in registry


def test_pdf_to_images_hydration_and_write_are_signed_web_only_not_bridge_backed() -> None:
    assert "const pdfToImagesEnabled" in INTEGRATION
    assert '"document-operation-pdf-to-images": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && pdfToImagesEnabled)' in INTEGRATION
    assert '"/documents/pdf-to-images"' in INTEGRATION
    assert '"/documents/pdf-to-images": base().pdfToImagesEnabled === true ? "ready" : "guarded"' in INTEGRATION
    assert '"/document-operations?kind=pdf_to_images&limit=100"' in INTEGRATION
    assert 'api("/document-operations/pdf-to-images"' in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "document-operation-pdf-to-images")'):
        INTEGRATION.index('if (action === "document-operation-pdf-to-word")')
    ]
    assert "source_asset_id: sourceAssetId" in action
    assert "idempotency_key: submission.key" in action
    assert "hydrateDocumentOperations" in action
    assert "hydrateAssetVault" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action


def test_pdf_to_images_contract_records_renderer_bounds_private_delivery_and_no_bot_payment_provider_execution() -> None:
    for phrase in (
        "pdf_to_images",
        "2×",
        "20 MiB",
        "30 pages",
        "8,192",
        "8 MP",
        "48 MP",
        "pypdfium2==5.11.0",
        "WEBAPP_PDF_TO_IMAGES_ENABLED",
        "No Bot bridge",
        "PayOS",
    ):
        assert phrase in PDF_TO_IMAGES_CONTRACT
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    operation_source = (ROOT / "copyfast_document_operations.py").read_text(encoding="utf-8")
    api_source = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert '"/api/v1/document-operations/pdf-to-images"' in app_source
    assert "PDF_TO_IMAGES_KIND" in operation_source
    assert "PDF_TO_IMAGES_MAX_CONCURRENT = 1" in operation_source
    assert "_verify_pdf_to_images_zip" in operation_source
    assert "_verify_pdf_to_images_png_bytes" in operation_source
    assert "bridge_request(" not in operation_source
    assert "web_native_pdf_to_images_required" in api_source
    assert '"pdf_to_images_enabled": enabled("WEBAPP_PDF_TO_IMAGES_ENABLED", False)' in api_source
