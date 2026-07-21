"""Static guardrails for the private Blob-only Video Preview workspace."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
ASSETS = (ROOT / "copyfast_assets.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_video_preview_is_a_direct_private_workspace_not_a_video_catalog_or_bot_adapter() -> None:
    assert 'customerPage("/video/preview", "Video Preview & Inspector"' in PORTAL
    assert 'layout: "video-preview", type: "video-preview"' in PORTAL
    assert "direct Web-native Asset Vault inspector" in PORTAL
    assert 'readOnlyPage("/video/preview"' not in PORTAL
    assert 'const VIDEO_PREVIEW_ROUTE = "/video/preview";' in INTEGRATION
    assert 'if (currentPath === VIDEO_PREVIEW_ROUTE)' in INTEGRATION
    assert '"video-preview-view": Boolean(account && assetVaultEnabled && videoPreviewEnabled)' in INTEGRATION

    surface = _between(PORTAL, "function renderVideoPreview(page, context)", "function renderVideoPosterOperations")
    for required in (
        'data-portal-action="video-preview-load"',
        'data-portal-action="video-preview-reference-page"',
        'data-portal-action="video-preview-clear"',
        'data-portal-no-transient',
        'aria-describedby="video-preview-source-hint"',
        'role="status" aria-live="polite"',
        'data-video-preview-player',
        'src="${safeText(objectUrl)}"',
        "Không autoplay",
        "Không có Bot, provider, FFmpeg, job, Xu, PayOS",
    ):
        assert required in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "window.open", "location.href", "/api/v1/asset-vault/"):
        assert forbidden not in surface


def test_video_preview_picker_is_typed_owner_scoped_and_bounded_before_a_blob_can_be_loaded() -> None:
    selector = _between(ASSETS, 'elif selected_reference_kind == "video_preview":', "    if needle:")
    for required in (".mp4", "video/mp4", ".webm", "video/webm", "VIDEO_PREVIEW_MAX_BYTES", "byte_size <= ?"):
        assert required in selector
    assert ".mov" not in selector
    assert "video/*" not in selector

    hydration = _between(INTEGRATION, "function videoPreviewPathIsCurrent(path)", "// Video Poster is intentionally")
    for required in (
        "reference_kind=video_preview",
        "VIDEO_PREVIEW_MIME_BY_EXTENSION",
        "videoPreviewRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)",
        "videoPreviewRouteSessionIsCurrent(sessionEpoch, expectedPath)",
        "videoPreviewContentEpoch",
        "revokeVideoPreviewObjectUrl",
        "previous_offset",
    ):
        assert required in hydration
    for forbidden in ('api("/assets")', 'api("/jobs")', "storage_key", "sha256", "provider URL", "payment"):
        assert forbidden not in hydration


def test_binary_preview_loader_validates_private_delivery_before_assigning_only_a_blob_url() -> None:
    loader = _between(INTEGRATION, "async function loadVideoPreview(sourceAssetId)", "function updateVideoPreviewBrowserMetadata")
    for required in (
        'fetch(`${API}/asset-vault/${encodeURIComponent(source.id)}/preview`',
        'credentials: "same-origin"',
        'cache: "no-store"',
        "new AbortController()",
        'disposition.includes("inline")',
        'cacheControl.includes("no-store")',
        'nosniff !== "nosniff"',
        'referrerPolicy.includes("no-referrer")',
        'contentPolicy.includes("sandbox")',
        'crossOriginPolicy !== "same-origin"',
        'response.headers.has("Accept-Ranges")',
        "byteSize !== source.byte_size",
        "blob.size !== source.byte_size",
        "URL.createObjectURL(blob)",
        "URL.revokeObjectURL(objectUrl)",
        "videoPreviewContentIsCurrent",
    ):
        assert required in loader
    for forbidden in ("window.open", "location.href", "localStorage", "sessionStorage", "download_url", "signed_url", "provider"):
        assert forbidden not in loader.lower()

    endpoint = _between(ASSETS, '@router.get("/{asset_id}/preview")', '@router.get("/{asset_id}")')
    for required in (
        "asset_vault_video_preview_enabled",
        'request.headers.get("range")',
        "status_code=416",
        "_video_preview_source_allowed",
        "open_verified_private_asset_stream",
        "seal_verified_private_file",
        "private_asset_inline_response",
        'action="web.asset_vault.video_preview"',
        "inline_no_range",
    ):
        assert required in endpoint
    # The endpoint documents its deliberate separation from provider/payment
    # systems; prohibit only actual remote URL delivery, not those explanatory
    # words in the contract docstring.
    for forbidden in ("http://", "https://"):
        assert forbidden not in endpoint.lower()


def test_preview_has_private_middleware_pwa_and_accessibility_boundaries() -> None:
    for required in (
        "asset_vault_video_preview = (",
        'else "asset-vault-video-preview" if asset_vault_video_preview',
        "if asset_vault_video_preview:",
        "private_asset_vault_video_preview = (",
        "media-src 'self' blob:",
    ):
        assert required in APP
    for required in ('"/" + "api/v1/asset-vault"', '"/asset-vault"', '"/video/preview"'):
        assert required in SERVICE_WORKER
    shell = _between(SERVICE_WORKER, "const SHELL = Object.freeze([", "]);\nconst SHELL_PATHS")
    public_navigation = _between(SERVICE_WORKER, "const PUBLIC_NAVIGATION_PATHS", "]);\n// This is deliberately")
    assert "/video/preview" not in shell
    assert "/video/preview" not in public_navigation

    for selector in (
        ".portal-video-preview-player",
        ".portal-video-preview-player:focus-visible",
        ".portal-video-preview-pager .portal-button, .portal-video-preview-player-wrap .portal-button { min-height: 44px",
        ".portal-video-preview-intro, .portal-video-preview-layout { grid-template-columns: 1fr; }",
        ".portal-video-preview-intro dl, .portal-video-preview-player-meta { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS
    binder = _between(PORTAL, "function bindVideoPreviewPlayer(main)", "function mountPortal")
    for required in ("loadedmetadata", "video-preview-player-metadata", "video-preview-player-error", "CustomEvent(ACTION_EVENT", "{ once: true }"):
        assert required in binder
