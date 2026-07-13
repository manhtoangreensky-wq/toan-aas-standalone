"""Static contracts for the private Web-native Image Enhance Studio surface."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "IMAGE_ENHANCE_CONTRACT.md").read_text(encoding="utf-8")


def test_enhance_replaces_generic_bridge_form_with_a_native_private_surface() -> None:
    assert 'customerPage("/image/edit", "Image Enhance Studio"' in PORTAL
    assert 'layout: "image-enhance", type: "image-operation", action: "none", status: "guarded"' in PORTAL
    assert 'featurePage("/image/edit"' not in PORTAL
    assert "function renderImageEnhance(page, context)" in PORTAL
    assert 'case "image-enhance": return renderImageEnhance(page, context);' in PORTAL
    assert "function imageEnhanceFormFields(values)" in PORTAL
    assert "function synchronizeImageEnhancePreset(form)" in PORTAL
    assert "function imageEnhanceOperationItems(context)" in PORTAL
    assert "function renderImageEnhanceOperationCards(items)" in PORTAL
    assert 'optionsFrom: "imageVaultAssets"' in PORTAL
    assert 'data-portal-action="image-operation-enhance"' in PORTAL
    assert 'data-portal-action="image-enhance-refresh"' in PORTAL
    for token in (
        "photo_clear_detail",
        "product_clean",
        "cinematic_warm",
        "fresh_blue",
        "food_vivid",
        'name: "brightness"',
        'name: "contrast"',
        'name: "saturation"',
        'name: "sharpness"',
        'name: "basic_upscale"',
        "dynamicRequired: true",
    ):
        assert token in PORTAL


def test_enhance_hydration_and_write_use_only_private_image_operation_routes() -> None:
    assert "const imageEnhanceEnabled" in INTEGRATION
    assert '"image-operation-enhance": Boolean(account && me.csrf_token && assetVaultEnabled && imageOperationsEnabled && imageEnhanceEnabled)' in INTEGRATION
    assert '"image-enhance-refresh": Boolean(account && assetVaultEnabled && imageOperationsEnabled)' in INTEGRATION
    assert '"/image/edit": account && assetVaultEnabled && imageOperationsEnabled && imageEnhanceEnabled ? "processing" : "guarded"' in INTEGRATION
    assert "function imageEnhancePrivateReadPageState(assetState, operationState)" in INTEGRATION
    assert "async function hydrateImageEnhanceOperations()" in INTEGRATION
    assert 'api("/image-operations?kind=image_enhance&limit=100")' in INTEGRATION
    assert 'api("/image-operations/enhance"' in INTEGRATION
    action = INTEGRATION[
        INTEGRATION.index('if (action === "image-operation-enhance")'):
        INTEGRATION.index('if (action === "document-operation-refresh")')
    ]
    for token in (
        "source_asset_id: sourceAssetId",
        "preset,",
        "basic_upscale: basicUpscale",
        "idempotency_key: submission.key",
        "hydrateImageEnhanceOperations",
        "hydrateAssetVault",
        "brightness",
        "contrast",
        "saturation",
        "sharpness",
        "tone",
    ):
        assert token in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action
    assert "PayOS" not in action
    assert "provider" not in action.lower()


def test_enhance_surface_is_truthful_and_has_no_browser_output_or_private_cache() -> None:
    surface = PORTAL[
        PORTAL.index("function renderImageEnhance(page, context)"):
        PORTAL.index("function renderAssetVault(page, context)")
    ]
    for phrase in (
        "không hứa hẹn AI",
        "Không tạo chi tiết mới",
        "Không upload bytes",
        "preview công khai",
        "không tạo Bot job",
        "PayOS order",
    ):
        assert phrase in surface
    assert "fetch(" not in surface
    assert "api(" not in surface
    assert "localStorage" not in surface
    assert "canvas.to" not in surface
    assert "SHELL_PATHS" in SERVICE_WORKER
    # The service worker uses an explicit public-shell allowlist. A private
    # enhancement API must not gain a route-prefix cache path by accident.
    assert "image-operations" not in SERVICE_WORKER.lower() or "private" in SERVICE_WORKER.lower()


def test_enhance_backend_is_bounded_private_and_blocks_generic_bridge_duplicates() -> None:
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    db_source = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    api_source = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    operation_source = (ROOT / "copyfast_image_operations.py").read_text(encoding="utf-8")
    runtime_source = (ROOT / "copyfast_image_runtime.py").read_text(encoding="utf-8")

    assert '"/api/v1/image-operations/enhance"' in app_source
    assert "WEBAPP_IMAGE_ENHANCE_ENABLED" in db_source
    assert "settings_json" in db_source
    assert "ALTER TABLE web_image_operations ADD COLUMN settings_json" in db_source
    assert "WEBAPP_IMAGE_ENHANCE_ENABLED" in api_source
    assert "web_native_image_enhance_required" in api_source
    assert "IMAGE_ENHANCE_KIND" in operation_source
    assert "ImageEnhanceRequest" in operation_source
    assert "ENHANCE_PRESETS" in operation_source
    assert "_normalized_enhance_spec" in operation_source
    assert "_enhance_request_fingerprint" in operation_source
    assert "_render_enhance" in operation_source
    assert "_build_enhance_output" in operation_source
    assert "_inspect_enhance_geometry" in operation_source
    assert "ImageOps.autocontrast" in operation_source
    assert "ImageFilter.UnsharpMask" in operation_source
    assert "run_in_threadpool" in operation_source
    assert "image_decoder_capacity" in operation_source
    assert "IMAGE_DECODER_MAX_CONCURRENT = 1" in runtime_source
    assert "state='completed' AND byte_size IS NOT NULL" in operation_source
    assert "StreamingResponse" in operation_source
    assert "O_NOFOLLOW" in operation_source
    assert "BackgroundTask(verified_stream.close)" in operation_source
    assert "bridge_request(" not in operation_source
    assert "requests." not in operation_source
    assert "httpx." not in operation_source


def test_enhance_contract_records_parity_safety_and_non_goals() -> None:
    for phrase in (
        "photo_clear_detail",
        "product_clean",
        "cinematic_warm",
        "fresh_blue",
        "food_vivid",
        "0.50 to 2.00",
        "2×",
        "4,096 px",
        "16 MP",
        "WEBAPP_IMAGE_ENHANCE_ENABLED",
        "idempotency",
        "No Bot bridge",
        "PayOS",
        "public preview URL",
    ):
        assert phrase in CONTRACT
