"""Static contracts for the signed, private Video Poster Lab Portal handoff."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
ASSETS = (ROOT / "copyfast_assets.py").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_video_poster_is_a_direct_private_workspace_not_a_video_catalog_change() -> None:
    assert 'customerPage("/video/poster", "Video Poster Lab"' in PORTAL
    assert 'layout: "video-poster-operations", type: "video-poster-operations"' in PORTAL
    assert "direct app workspace" in PORTAL
    assert "broad Video catalogue" in PORTAL
    assert "function renderVideoPosterOperations(page, context)" in PORTAL
    assert 'case "video-poster-operations": return renderVideoPosterOperations(page, context);' in PORTAL
    assert 'const VIDEO_POSTER_OPERATIONS_ROUTE = "/video/poster";' in INTEGRATION
    assert "if (currentPath === VIDEO_POSTER_OPERATIONS_ROUTE)" in INTEGRATION

    surface = _between(PORTAL, "function renderVideoPosterOperations(page, context)", "function renderSubtitleProjectCards")
    for phrase in ("MP4, MOV hoặc WebM", "Không có player", "không có kết quả giả", "data-portal-no-transient"):
        assert phrase in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "<video"):
        assert forbidden not in surface


def test_typed_server_picker_has_exact_poster_media_pairs_and_owner_scoped_portal_read() -> None:
    assert '"video_poster"' in ASSETS
    selector = _between(ASSETS, 'elif selected_reference_kind == "video_poster":', "    if needle:")
    for phrase in (".mp4", "video/mp4", ".mov", "video/quicktime", ".webm", "video/webm"):
        assert phrase in selector
    assert "video/*" in selector

    hydration = _between(INTEGRATION, "function videoPosterOperationsPathIsCurrent(path)", "const OPERATION_HISTORY_LIST_LIMIT")
    for required in (
        "reference_kind=video_poster",
        "/video-operations?limit=",
        'cache: "no-store"',
        "VIDEO_POSTER_MIME_BY_EXTENSION",
        "videoPosterOperationsRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)",
        "videoPosterRouteSessionIsCurrent(sessionEpoch, expectedPath)",
        "clearVideoPosterOperationsProjection",
        "previous_offset",
    ):
        assert required in hydration
    for forbidden in ('"/assets"', '"/jobs"', "storage_key", "sha256", "provider", "bridge"):
        assert forbidden not in hydration.lower()


def test_create_actions_are_csrf_idempotent_owner_scoped_and_never_fake_a_jpeg() -> None:
    for capability in (
        '"video-poster-operation-view": Boolean(account && assetVaultEnabled && videoPosterEnabled)',
        '"video-poster-operation-create": Boolean(account && me.csrf_token && assetVaultEnabled && videoPosterEnabled)',
        '"video-poster-operation-detail": Boolean(account && assetVaultEnabled && videoPosterEnabled)',
        '"video-poster-operation-download": Boolean(account && assetVaultEnabled && videoPosterEnabled)',
    ):
        assert capability in INTEGRATION

    actions = _between(INTEGRATION, 'if (action === "video-poster-operation-refresh")', 'if (action === "subtitle-format-convert")')
    for action in (
        "video-poster-operation-refresh",
        "video-poster-reference-page",
        "video-poster-operation-confirm",
        "video-poster-operation-detail",
        "video-poster-operation-download",
    ):
        assert action in actions
    assert 'api("/video-operations/poster", {' in actions
    assert "idempotency_key: submission.key" in actions
    assert "videoPosterOperationReceipt(result)" in actions
    assert "await hydrateVideoPosterOperations({ selectedId: payload.source_asset_id })" in actions
    assert "cùng idempotency key sẽ được tái sử dụng" in actions
    for forbidden in ("/payments", "payos", "wallet", "core bridge", "provider call"):
        assert forbidden not in actions.lower()

    payload = _between(INTEGRATION, "function videoPosterPayload(fields)", "function videoPosterRouteSessionIsCurrent")
    for token in ("source_asset_id", "poster_position", "VIDEO_POSTER_POSITIONS", "videoPosterOperationSourcesFromState"):
        assert token in payload
    for forbidden in ("filter", "ffmpeg", "path", "url", "storage_key", "provider"):
        assert forbidden not in payload.lower()

    surface = _between(PORTAL, "function renderVideoPosterOperations(page, context)", "function renderSubtitleProjectCards")
    assert 'data-portal-action="video-poster-operation-confirm"' in surface
    assert 'data-portal-confirm="Tạo một JPEG private' in surface
    assert 'name="video_poster_confirmation"' in surface
    assert "output chỉ có thể tải sau khi máy chủ kiểm chứng" in surface


def test_detail_and_download_require_a_verified_private_jpeg_attachment() -> None:
    download = _between(INTEGRATION, "async function downloadVideoPosterOperation(operationId)", "const OPERATION_HISTORY_LIST_LIMIT")
    for required in (
        'operation.kind !== "video_poster"',
        'operation.state !== "completed"',
        'output.available !== true',
        'cache: "no-store"',
        'disposition.includes("attachment")',
        'cacheControl.includes("no-store")',
        'nosniff !== "nosniff"',
        'referrerPolicy.includes("no-referrer")',
        'contentPolicy.includes("sandbox")',
        'actualMime !== "image/jpeg"',
        "byteSize !== expectedSize",
        "blob.size !== expectedSize",
        "URL.revokeObjectURL(objectUrl)",
    ):
        assert required in download
    assert "window.open" not in download
    assert "location.href" not in download
    assert "video-operations" not in SERVICE_WORKER


def test_video_poster_controls_are_accessible_and_responsive() -> None:
    surface = _between(PORTAL, "function renderVideoPosterOperations(page, context)", "function renderSubtitleProjectCards")
    for required in (
        'aria-describedby="video-poster-source-hint"',
        'id="video-poster-source-hint" role="status" aria-live="polite"',
        "const readyForInteraction = readState === \"ready\";",
        "canCreate && sourceItems.length > 0 && readyForInteraction",
    ):
        assert required in surface
    for selector in (
        ".portal-video-poster-operations",
        ".portal-video-poster-confirm-check:focus-within",
        ".portal-video-poster-source-pager .portal-button",
        "min-height: 44px",
        ".portal-video-poster-intro, .portal-video-poster-layout { grid-template-columns: 1fr; }",
        ".portal-video-poster-intro dl, .portal-video-poster-detail-summary { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS
