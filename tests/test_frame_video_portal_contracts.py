"""Static contracts for the private Frame Video Lab Portal handoff.

The Portal is a direct signed-account workspace: it accepts only a bounded,
ordered image sequence already owned by the account, asks the native Web
runtime for an estimate, and never creates an unverified browser-side video.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_frame_video_is_a_direct_private_portal_route() -> None:
    assert 'customerPage("/video/frame-sequence", "Frame Video Lab"' in PORTAL
    assert 'layout: "frame-video-operations", type: "frame-video-operations"' in PORTAL
    assert "function renderFrameVideoOperations(page, context)" in PORTAL
    assert 'case "frame-video-operations": return renderFrameVideoOperations(page, context);' in PORTAL
    assert 'const FRAME_VIDEO_OPERATIONS_ROUTE = "/video/frame-sequence";' in INTEGRATION
    assert "if (currentPath === FRAME_VIDEO_OPERATIONS_ROUTE)" in INTEGRATION

    route = _between(PORTAL, 'customerPage("/video/frame-sequence"', 'featurePage("/subtitle"')
    assert "direct app workspace" in PORTAL
    assert "broad Video catalogue" in PORTAL
    assert "Asset Vault" in route

    # Keep this renderer contract bounded to its own surface.  New adjacent
    # video workspaces may legitimately contain a private `<video>` element
    # without turning Frame Video itself into a browser media player.
    surface = _between(PORTAL, "function renderFrameVideoOperations(page, context)", "function renderVideoPreview(page, context)")
    for phrase in (
        "2–8 ảnh",
        "Không upload lại ảnh",
        "không có kết quả giả",
        "data-portal-no-transient",
        "frame_video_selection_order",
    ):
        assert phrase in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "bridge_request", "<video"):
        assert forbidden not in surface


def test_typed_ordered_image_picker_is_owner_scoped_no_store_and_session_fenced() -> None:
    hydration = _between(
        INTEGRATION,
        "function frameVideoOperationsPathIsCurrent(path)",
        "const OPERATION_HISTORY_LIST_LIMIT",
    )
    for required in (
        'extension === ".jpg" || extension === ".jpeg"',
        'extension === ".png"',
        'extension === ".webp"',
        'contentType !== expectedMime',
        "reference_kind=image",
        "/frame-video-operations?limit=",
        'cache: "no-store"',
        "frameVideoOperationsRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)",
        "frameVideoRouteSessionIsCurrent(sessionEpoch, expectedPath)",
        "clearFrameVideoOperationsProjection",
        "selected_ids",
        "selected_items",
        "previous_offset",
    ):
        assert required in hydration
    for forbidden in ('"/assets"', '"/jobs"', "storage_key", "sha256"):
        assert forbidden not in hydration

    picker = _between(PORTAL, "function frameVideoPortalReferenceItem", "function frameVideoPortalSpec")
    for required in ('".jpg": "image/jpeg"', '".jpeg": "image/jpeg"', '".png": "image/png"', '".webp": "image/webp"'):
        assert required in PORTAL
    assert "FRAME_VIDEO_PORTAL_IMAGE_TYPES[extension] !== contentType" in picker
    assert "frameVideoPortalSelectionIds" in picker
    assert "data-frame-video-source-id" in PORTAL
    assert 'data-portal-action="frame-video-reference-page"' in PORTAL
    assert "frameVideoSelectionIdsFromForm" in PORTAL


def test_estimate_confirm_create_actions_are_closed_csrf_idempotent_and_truthful() -> None:
    for capability in (
        '"frame-video-operation-view": Boolean(account && assetVaultEnabled && frameVideoOperationsEnabled)',
        '"frame-video-operation-estimate": Boolean(account && assetVaultEnabled && frameVideoOperationsEnabled)',
        '"frame-video-operation-create": Boolean(account && me.csrf_token && assetVaultEnabled && frameVideoOperationsEnabled)',
        '"frame-video-operation-detail": Boolean(account && assetVaultEnabled && frameVideoOperationsEnabled)',
        '"frame-video-operation-download": Boolean(account && assetVaultEnabled && frameVideoOperationsEnabled)',
    ):
        assert capability in INTEGRATION

    actions = _between(
        INTEGRATION,
        'if (action === "frame-video-operation-refresh")',
        'if (action === "subtitle-format-convert")',
    )
    for action in (
        "frame-video-operation-refresh",
        "frame-video-reference-page",
        "frame-video-history-page",
        "frame-video-operation-estimate",
        "frame-video-operation-confirm",
        "frame-video-operation-detail",
        "frame-video-operation-download",
    ):
        assert action in actions
    assert 'api("/frame-video-operations/estimate", {' in actions
    assert 'api("/frame-video-operations", {' in actions
    assert 'idempotency_key: submission.key' in actions
    assert "frameVideoOperationReceipt(result)" in actions
    assert "++frameVideoOperationsHydrationEpoch" in actions
    assert "await hydrateFrameVideoOperations({ selectedIds: payload.source_asset_ids })" in actions
    assert "if (!refreshed) throw new Error" in actions
    assert "cùng idempotency key sẽ được tái sử dụng" in actions
    for forbidden in ("/payments", "payos", "provider call", "core bridge", "wallet"):
        assert forbidden not in actions.lower()

    payload = _between(INTEGRATION, "function frameVideoPayload(fields)", "function frameVideoSpecMatches")
    for token in (
        "source_asset_ids: ids",
        "aspect_ratio:",
        "seconds_per_image:",
        "effect:",
        "frameVideoSpecIsSafe(payload)",
        "frameVideoSelectedSourcesFromState()",
        "FRAME_VIDEO_MAX_SOURCE_TOTAL_BYTES",
    ):
        assert token in payload
    for forbidden in ("filter", "ffmpeg", "path", "url", "storage_key", "provider"):
        assert forbidden not in payload.lower()


def test_confirm_surface_requires_explicit_matching_plan_and_never_synthesizes_output() -> None:
    surface = _between(PORTAL, "function renderFrameVideoOperations(page, context)", "function renderSubtitleProjectCards")
    assert "function frameVideoPortalEstimate(context)" in PORTAL
    assert "frameVideoPortalSpec(stored.payload)" in PORTAL
    assert 'data-portal-action="frame-video-operation-estimate"' in surface
    assert 'data-portal-action="frame-video-operation-confirm"' in surface
    assert 'data-portal-confirm="Tạo một MP4 private theo thứ tự khung hình và kế hoạch này?' in surface
    assert 'name="frame_video_confirmation"' in surface
    assert "function synchronizeFrameVideoEstimateForm(form, changedInput)" in PORTAL
    assert "Thứ tự ảnh hoặc cấu hình đã thay đổi. Hãy kiểm tra lại kế hoạch" in PORTAL
    assert "frameVideoDraft: payload" in INTEGRATION
    assert "frameVideoOperationCanDownload(operation)" in surface
    assert 'operation.state === "completed" && !outputReady ? "unavailable" : operation.state' in surface
    assert "không có preview, download hoặc trạng thái thành công thay thế" in surface
    assert 'data-portal-action="frame-video-operation-detail"' in surface
    assert 'data-portal-action="frame-video-operation-download"' in surface
    assert 'data-portal-action="frame-video-history-page"' in surface


def test_private_download_requires_verified_attachment() -> None:
    download = _between(INTEGRATION, "async function downloadFrameVideoOperation(operationId)", "const OPERATION_HISTORY_LIST_LIMIT")
    assert "const FRAME_VIDEO_MAX_OUTPUT_BYTES = 100 * 1024 * 1024;" in INTEGRATION
    for required in (
        'operation.kind !== "frame_video"',
        'operation.state !== "completed"',
        'output.available !== true',
        'cache: "no-store"',
        'disposition.includes("attachment")',
        'cacheControl.includes("no-store")',
        'nosniff !== "nosniff"',
        'referrerPolicy.includes("no-referrer")',
        'contentPolicy.includes("sandbox")',
        'corp !== "same-origin"',
        "byteSize !== expectedSize",
        "blob.size !== expectedSize",
        "URL.revokeObjectURL(objectUrl)",
    ):
        assert required in download
    assert "window.open" not in download
    assert "location.href" not in download


def test_accessible_controls_and_mobile_frame_video_layout_are_present() -> None:
    surface = _between(PORTAL, "function renderFrameVideoOperations(page, context)", "function renderSubtitleProjectCards")
    assert 'aria-describedby="frame-video-source-hint"' in surface
    assert 'id="frame-video-source-hint"' in surface
    assert 'role="status" aria-live="polite"' in surface
    assert 'const readyForInteraction = readState === "ready";' in surface
    assert "canEstimate && referenceItems.length > 0 && readyForInteraction" in surface
    assert "canView && readyForInteraction && canReferencePrevious" in surface
    assert "canView && readyForInteraction && canHistoryPrevious" in surface
    for selector in (
        ".portal-frame-video-operations",
        ".portal-frame-video-source-pager .portal-button",
        ".portal-frame-video-operation-actions .portal-button",
        ".portal-frame-video-confirm-check input",
        "min-height: 44px",
        ".portal-frame-video-layout { grid-template-columns: 1fr; }",
        ".portal-frame-video-source-list, .portal-frame-video-sequence { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS
