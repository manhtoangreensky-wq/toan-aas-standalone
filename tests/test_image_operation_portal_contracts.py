"""Static contracts for the private Web-native Resize & Aspect Studio surface."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "IMAGE_RESIZE_ASPECT_CONTRACT.md").read_text(encoding="utf-8")


def test_resize_replaces_a_generic_bridge_form_with_a_native_private_surface() -> None:
    assert 'customerPage("/image/resize", "Resize & Aspect Studio"' in PORTAL
    assert 'layout: "image-resize", type: "image-operation", action: "none", status: "guarded"' in PORTAL
    assert 'featurePage("/image/resize"' not in PORTAL
    assert "function renderImageResize(page, context)" in PORTAL
    assert 'case "image-resize": return renderImageResize(page, context);' in PORTAL
    assert "function imageResizeFormFields(values)" in PORTAL
    assert "function synchronizeImageResizePreset(form)" in PORTAL
    assert 'input.disabled = !isCustom' in PORTAL
    assert 'input.setAttribute("aria-required", String(isCustom))' in PORTAL
    assert 'data-portal-required-mark' in PORTAL
    assert 'dynamicRequired: true' in PORTAL
    assert "function renderImageOperationCards(items)" in PORTAL
    assert 'optionsFrom: "imageVaultAssets"' in PORTAL
    assert 'name: "preset"' in PORTAL
    assert 'name: "target_width"' in PORTAL
    assert 'name: "target_height"' in PORTAL
    assert 'name: "fit_mode"' in PORTAL
    assert 'data-portal-action="image-operation-resize"' in PORTAL
    assert 'data-portal-action="image-operation-refresh"' in PORTAL
    for token in ("1:1", "4:5", "9:16", "16:9", "crop", "pad", "blur"):
        assert token in PORTAL


def test_resize_hydration_and_write_use_only_private_image_operation_routes() -> None:
    assert "const imageOperationsEnabled" in INTEGRATION
    assert "const imageResizeEnabled" in INTEGRATION
    assert '"image-operation-view": Boolean(account && assetVaultEnabled && imageOperationsEnabled)' in INTEGRATION
    assert '"image-operation-resize": Boolean(account && me.csrf_token && assetVaultEnabled && imageOperationsEnabled && imageResizeEnabled)' in INTEGRATION
    assert '"/image/resize": account && assetVaultEnabled && imageOperationsEnabled && imageResizeEnabled ? "processing" : "guarded"' in INTEGRATION
    assert "function imageResizePrivateReadPageState(assetState, operationState)" in INTEGRATION
    assert '"/image/resize": imageResizePrivateReadPageState("ready", String(base().imageOperationsReadState || "loading"))' in INTEGRATION
    assert '"/image/resize": imageResizePrivateReadPageState(String(base().assetVaultReadState || "loading"), "ready")' in INTEGRATION
    # Resize history is now paged, while preserving the same owner-scoped
    # Web-native API boundary.
    assert "async function hydrateImageOperations(offsetValue)" in INTEGRATION
    assert 'assetVaultReadState: account && assetVaultEnabled ? "loading" : "guarded"' in INTEGRATION
    assert 'imageOperationsReadState: account && assetVaultEnabled && imageOperationsEnabled ? "loading" : "guarded"' in INTEGRATION
    assert 'assetVaultReadState: "failed"' in INTEGRATION
    assert 'imageOperationsReadState: "failed"' in INTEGRATION
    history_start = INTEGRATION.index("function imageOperationHistoryPath(kind, offset)")
    history_end = INTEGRATION.index("function operationHistoryRequestIsCurrent", history_start)
    history_path = INTEGRATION[history_start:history_end]
    resize_reader_start = INTEGRATION.index("async function hydrateImageOperations(offsetValue)")
    resize_reader_end = INTEGRATION.index("async function hydrateImageEnhanceOperations", resize_reader_start)
    resize_reader = INTEGRATION[resize_reader_start:resize_reader_end]
    assert 'return "/image-operations?" + new URLSearchParams({' in history_path
    assert "kind: normalizedKind" in history_path
    assert "limit: String(OPERATION_HISTORY_LIST_LIMIT)" in history_path
    assert "offset: String(operationHistoryListOffset(offset))" in history_path
    assert 'const kind = "image_resize"' in resize_reader
    assert "api(imageOperationHistoryPath(kind, offset))" in resize_reader
    assert 'api("/image-operations/resize"' in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "image-operation-resize")'):
        INTEGRATION.index('if (action === "document-operation-refresh")')
    ]
    for token in ("source_asset_id: sourceAssetId", "preset,", "target_width: targetWidth", "target_height: targetHeight", "fit_mode: fitMode", "idempotency_key: submission.key", "hydrateImageOperations", "hydrateAssetVault"):
        assert token in action
    assert 'preset === "custom" ? parseDimension(widthText, "Chiều rộng") : null' in action
    assert 'preset === "custom" ? parseDimension(heightText, "Chiều cao") : null' in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action
    assert "PayOS" not in action


def test_resize_surface_is_truthful_and_has_no_browser_generated_output_or_private_cache() -> None:
    surface = PORTAL[PORTAL.index("function renderImageResize(page, context)"):PORTAL.index("function renderAssetVault(page, context)")]
    for phrase in ("không tạo ảnh AI", "Không upload bytes", "Không có focal-point", "không retouch", "Không có preview công khai", "không tạo Bot job", "PayOS order"):
        assert phrase in surface
    assert "fetch(" not in surface
    assert "api(" not in surface
    assert "localStorage" not in surface
    assert "canvas.to" not in surface
    assert "SHELL_PATHS" in SERVICE_WORKER
    assert "/api/v1/document-operations" in SERVICE_WORKER
    # The worker has an explicit fixed public shell allowlist, so the private
    # image operation API can never be cached by route prefix or accident.
    assert "image-operations" not in SERVICE_WORKER.lower() or "private" in SERVICE_WORKER.lower()


def test_resize_backend_is_independent_bounded_and_blocks_generic_bridge_duplicates() -> None:
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    db_source = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    api_source = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    operation_source = (ROOT / "copyfast_image_operations.py").read_text(encoding="utf-8")
    runtime_source = (ROOT / "copyfast_image_runtime.py").read_text(encoding="utf-8")
    assert '"/api/v1/image-operations/resize"' in app_source
    assert "private_image_download" in app_source
    assert "ensure_image_operations_persistence" in app_source
    assert "reconcile_image_operation_storage" in app_source
    assert "web_image_operations" in db_source
    assert "web_image_operation_events" in db_source
    assert "WEBAPP_IMAGE_OPERATIONS_ROOT" in db_source
    assert "WEBAPP_IMAGE_RESIZE_ENABLED" in api_source
    assert "web_native_image_resize_required" in api_source
    assert "IMAGE_RESIZE_KIND" in operation_source
    assert "DecompressionBombWarning" in operation_source
    assert "DecompressionBombError" in operation_source
    assert "run_in_threadpool" in operation_source
    assert "image_decoder_capacity" in operation_source
    assert "IMAGE_DECODER_MAX_CONCURRENT = 1" in runtime_source
    assert "Cropping in source coordinates" in operation_source
    assert "IMAGE_OPERATION_INTERRUPTED" in operation_source
    assert "state='completed' AND byte_size IS NOT NULL" in operation_source
    assert "StreamingResponse" in operation_source
    assert "O_NOFOLLOW" in operation_source
    assert "BackgroundTask(verified_stream.close)" in operation_source
    assert "bridge_request(" not in operation_source
    assert "requests." not in operation_source
    assert "httpx." not in operation_source


def test_resize_contract_records_parity_safety_and_non_goals() -> None:
    for phrase in (
        "center crop",
        "white pad",
        "blur background",
        "20 MiB",
        "16 MP",
        "7,680 px",
        "12:1",
        "WEBAPP_IMAGE_OPERATIONS_ENABLED",
        "WEBAPP_IMAGE_RESIZE_ENABLED",
        "idempotency",
        "No Bot bridge",
        "PayOS",
        "No public preview URL",
    ):
        assert phrase in CONTRACT
