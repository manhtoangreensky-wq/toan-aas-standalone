"""Static contracts for the private Video Finishing Lab Portal handoff.

The browser can select only a typed, signed-account MP4 reference and closed
transform settings.  It must not turn this utility into a generic Video menu,
unverified media player, public URL, provider flow, or browser-side renderer.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "VIDEO_FINISHING_LAB_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_video_finishing_is_a_distinct_direct_private_portal_route() -> None:
    assert 'customerPage("/video/finishing", "Video Finishing Lab"' in PORTAL
    assert 'layout: "video-transform-operations", type: "video-transform-operations"' in PORTAL
    assert "function renderVideoTransformOperations(page, context)" in PORTAL
    assert 'case "video-transform-operations": return renderVideoTransformOperations(page, context);' in PORTAL
    assert 'const VIDEO_TRANSFORM_OPERATIONS_ROUTE = "/video/finishing";' in INTEGRATION
    assert 'if (currentPath === VIDEO_TRANSFORM_OPERATIONS_ROUTE)' in INTEGRATION

    route = _between(PORTAL, 'customerPage("/video/finishing"', 'featurePage("/subtitle"')
    assert "storage key" in route
    assert "direct, app-native workspace" in PORTAL
    assert "broad Video catalogue" in PORTAL

    # Keep the Finishing contract bounded to its own renderer.  Frame Video
    # and Preview are separate direct workspaces with different media rules.
    surface = _between(PORTAL, "function renderVideoTransformOperations(page, context)", "function renderFrameVideoOperations(page, context)")
    for phrase in (
            "Asset Vault",
            "Không upload lại file",
            "Không có trạng thái thành công do browser tự tạo",
            "không có kết quả giả",
        "data-portal-no-transient",
    ):
        assert phrase in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "bridge_request", "<video"):
        assert forbidden not in surface


def test_typed_mp4_picker_is_owner_scoped_no_store_and_session_fenced() -> None:
    hydration = _between(
        INTEGRATION,
        "function videoTransformOperationsPathIsCurrent(path)",
        "const OPERATION_HISTORY_LIST_LIMIT",
    )
    assert 'extension !== ".mp4" || contentType !== "video/mp4"' in hydration
    assert "reference_kind=video_transform" in hydration
    assert "reference_kind=video&" not in hydration
    assert "/video-transform-operations?limit=" in hydration
    assert 'cache: "no-store"' in hydration
    assert "videoTransformOperationsRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)" in hydration
    assert "videoTransformRouteSessionIsCurrent(sessionEpoch, expectedPath)" in hydration
    assert "clearVideoTransformOperationsProjection" in hydration
    assert "selected: null" in hydration
    assert "previous_offset" in hydration
    assert '"/assets"' not in hydration
    assert '"/jobs"' not in hydration
    assert "storage_key" not in hydration
    assert "sha256" not in hydration

    portal_picker = _between(PORTAL, "function videoTransformOperationSources(context)", "function videoTransformPortalSpec")
    assert "selected ? [selected, ...items] : items" in portal_picker
    assert 'extension === ".mp4" && contentType === "video/mp4"' in portal_picker
    assert "data-video-transform-reference-offset" in PORTAL
    assert 'data-portal-action="video-transform-reference-page"' in PORTAL


def test_estimate_confirm_create_actions_are_closed_csrf_idempotent_and_truthful() -> None:
    for capability in (
        '"video-transform-operation-view": Boolean(account && assetVaultEnabled && videoTransformOperationsEnabled)',
        '"video-transform-operation-estimate": Boolean(account && assetVaultEnabled && videoTransformOperationsEnabled)',
        '"video-transform-operation-create": Boolean(account && me.csrf_token && assetVaultEnabled && videoTransformOperationsEnabled)',
        '"video-transform-operation-detail": Boolean(account && assetVaultEnabled && videoTransformOperationsEnabled)',
        '"video-transform-operation-download": Boolean(account && assetVaultEnabled && videoTransformOperationsEnabled)',
    ):
        assert capability in INTEGRATION

    actions = _between(
        INTEGRATION,
        'if (action === "video-transform-operation-refresh")',
        'if (action === "subtitle-format-convert")',
    )
    for action in (
        "video-transform-operation-refresh",
        "video-transform-reference-page",
        "video-transform-history-page",
        "video-transform-operation-estimate",
        "video-transform-operation-confirm",
        "video-transform-operation-detail",
        "video-transform-operation-download",
    ):
        assert action in actions
    assert 'api("/video-transform-operations/estimate", {' in actions
    assert 'api("/video-transform-operations", {' in actions
    assert 'idempotency_key: submission.key' in actions
    assert "videoTransformOperationReceipt(result)" in actions
    assert "++videoTransformOperationsHydrationEpoch" in actions
    assert "await hydrateVideoTransformOperations({ selectedId: payload.source_asset_id })" in actions
    assert "if (!refreshed) throw new Error" in actions
    assert "cùng idempotency key sẽ được tái sử dụng" in actions
    for forbidden in ("/payments", "payos", "provider call", "core bridge", "wallet"):
        assert forbidden not in actions.lower()

    payload = _between(INTEGRATION, "function videoTransformPayload(fields)", "function videoTransformSpecMatches")
    for token in (
        "source_asset_id:",
        "target_ratio:",
        "fit_mode:",
        "preset:",
        "sharpen:",
        "preserve_audio:",
        "videoTransformSpecIsSafe(payload)",
        "videoTransformOperationSourcesFromState()",
    ):
        assert token in payload
    for forbidden in ("filter", "ffmpeg", "path", "url", "storage_key", "provider"):
        assert forbidden not in payload.lower()


def test_confirm_surface_requires_explicit_accepted_plan_and_never_synthesizes_output() -> None:
    surface = _between(PORTAL, "function renderVideoTransformOperations(page, context)", "function renderSubtitleProjectCards")
    assert "function videoTransformPortalEstimate(context)" in PORTAL
    assert "videoTransformPortalSpec(stored.payload)" in PORTAL
    assert 'data-portal-action="video-transform-operation-estimate"' in surface
    assert 'data-portal-action="video-transform-operation-confirm"' in surface
    assert 'data-portal-confirm="Tạo một MP4 private theo kế hoạch này?' in surface
    assert 'name="video_transform_confirmation"' in surface
    assert "function synchronizeVideoTransformEstimateForm(form)" in PORTAL
    assert "Lựa chọn đã thay đổi. Hãy kiểm tra lại kế hoạch" in PORTAL
    assert "videoTransformDraft: payload" in INTEGRATION
    assert "videoTransformOperationCanDownload(operation)" in surface
    assert 'operation.state === "completed" && !outputReady ? "unavailable" : operation.state' in surface
    assert "không có preview, download hoặc trạng thái thành công thay thế" in surface
    assert 'data-portal-action="video-transform-operation-detail"' in surface
    assert 'data-portal-action="video-transform-operation-download"' in surface
    assert 'data-portal-action="video-transform-history-page"' in surface


def test_private_download_requires_verified_attachment_and_excludes_pwa_cache() -> None:
    download = _between(INTEGRATION, "async function downloadVideoTransformOperation(operationId)", "const OPERATION_HISTORY_LIST_LIMIT")
    for required in (
        'operation.kind !== "video_transform"',
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

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/video/finishing"' not in shell
    assert '"/api/v1/video-transform-operations"' not in shell


def test_accessible_controls_and_mobile_video_finishing_layout_are_present() -> None:
    surface = _between(PORTAL, "function renderVideoTransformOperations(page, context)", "function renderSubtitleProjectCards")
    assert 'label for="video-transform-source"' in surface
    assert 'aria-describedby="video-transform-source-hint"' in surface
    assert 'id="video-transform-source-hint"' in surface
    assert 'role="status" aria-live="polite"' in surface
    assert "const readyForInteraction = readState === \"ready\";" in surface
    assert "canEstimate && sources.length > 0 && readyForInteraction" in surface
    assert "canView && readyForInteraction && canSourcePrevious" in surface
    assert "canView && readyForInteraction && canHistoryPrevious" in surface
    for selector in (
        ".portal-video-transform-operations",
        ".portal-video-transform-source-pager .portal-button",
        ".portal-video-transform-operation-actions .portal-button",
        ".portal-video-transform-confirm-check input",
        ".portal-video-transform-layout { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS


def test_contract_records_the_private_direct_route_boundary() -> None:
    for phrase in (
        "dedicated signed customer workspace",
        "not a new item in the broad Video menu/catalog",
        "reference_kind=video_transform",
        "idempotency key",
        "No\n  source ID, file metadata, receipt or setting is written to browser storage",
        "feature never fabricates success",
        "WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED",
    ):
        assert phrase in CONTRACT
