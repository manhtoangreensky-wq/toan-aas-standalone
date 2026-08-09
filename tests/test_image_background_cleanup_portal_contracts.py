"""Static contracts for the private Web-native plain-background cleanup UI."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_background_cleanup_is_a_separate_private_image_operation_surface() -> None:
    assert 'customerPage("/image/background-cleanup", "Xóa nền màu trơn"' in PORTAL
    assert 'layout: "image-background-cleanup", type: "image-operation", action: "none", status: "guarded"' in PORTAL
    assert 'featurePage("/image/background-cleanup"' not in PORTAL
    assert "function renderImageBackgroundCleanup(page, context)" in PORTAL
    assert 'case "image-background-cleanup": return renderImageBackgroundCleanup(page, context);' in PORTAL
    assert 'data-portal-action="image-operation-background-cleanup"' in PORTAL
    assert 'data-portal-action="image-background-cleanup-refresh"' in PORTAL
    for token in ("white_studio", "light_neutral", "dark_neutral", "Asset Vault", "không phải AI", "Không upload bytes"):
        assert token in PORTAL


def test_background_cleanup_uses_only_csrf_private_routes_and_never_calls_provider_or_bridge() -> None:
    assert "const imageBackgroundCleanupEnabled" in INTEGRATION
    assert 'const IMAGE_OPERATION_HISTORY_KINDS = new Set(["image_resize", "image_enhance", "image_brand_overlay", "image_background_cleanup"]);' in INTEGRATION
    assert '"image-operation-background-cleanup": Boolean(account && me.csrf_token && assetVaultEnabled && imageOperationsEnabled && imageBackgroundCleanupEnabled)' in INTEGRATION
    assert '"/image/background-cleanup": account && assetVaultEnabled && imageOperationsEnabled && imageBackgroundCleanupEnabled ? "processing" : "guarded"' in INTEGRATION
    assert "async function hydrateImageBackgroundCleanupOperations" in INTEGRATION
    action_start = INTEGRATION.index('if (action === "image-operation-background-cleanup")')
    action_end = INTEGRATION.index('if (action === "image-background-cleanup-refresh")', action_start)
    action = INTEGRATION[action_start:action_end]
    for token in (
        'api("/image-operations/background-cleanup", {',
        "source_asset_id: sourceAssetId",
        "profile,",
        "idempotency_key: submission.key",
        "hydrateImageBackgroundCleanupOperations",
        "hydrateAssetVault",
    ):
        assert token in action
    for forbidden in ("bridge_request", "CORE_BRIDGE", "provider", "removebg", "cutout", "wallet", "payos", "fetch("):
        assert forbidden.lower() not in action.lower()


def test_background_cleanup_never_enters_private_cache_or_replaces_guarded_ai_route() -> None:
    assert "/image-operations/background-cleanup" not in SERVICE_WORKER
    assert 'featurePage("/image/remove-background"' in PORTAL
    surface_start = PORTAL.index("function renderImageBackgroundCleanup(page, context)")
    surface_end = PORTAL.index("function renderImageHistoryOperationCards", surface_start)
    surface = PORTAL[surface_start:surface_end]
    for forbidden in ("localStorage", "canvas.to", "fetch(", "api(", "RemoveBG", "Cutout", "provider"):
        assert forbidden.lower() not in surface.lower()
