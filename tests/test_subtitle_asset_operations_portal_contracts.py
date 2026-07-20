"""Static contracts for the private Web-native Subtitle Asset Operations UI.

The browser may choose only a server-filtered SRT/VTT Asset Vault UUID. It
must never turn a subtitle into generic Jobs/Assets data, raw text/bytes or a
public/cached download claim.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "SUBTITLE_ASSET_OPERATIONS_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_subtitle_asset_operations_is_a_distinct_private_portal_route() -> None:
    assert 'customerPage("/subtitle/assets", "Subtitle Asset Operations"' in PORTAL
    assert 'layout: "subtitle-asset-operations", type: "subtitle-asset-operations"' in PORTAL
    assert "function renderSubtitleAssetOperations(page, context)" in PORTAL
    assert 'case "subtitle-asset-operations": return renderSubtitleAssetOperations(page, context);' in PORTAL
    assert '["/subtitle/assets", "Subtitle Asset Operations", ICONS.subtitle]' in PORTAL
    assert 'if (linkPath === "/subtitle/assets") return path === "/subtitle/assets";' in PORTAL
    assert '"/subtitle/assets": "subtitle_asset_operations"' in INTEGRATION
    assert 'const SUBTITLE_ASSET_OPERATIONS_ROUTE = "/subtitle/assets";' in INTEGRATION

    surface = _between(PORTAL, "function renderSubtitleAssetOperations(page, context)", "function renderSubtitleProjectCards")
    for phrase in (
        "Asset Vault",
        "Không public URL hay cache",
        "không có raw upload hoặc URL nguồn",
        "không tạo Job, Xu hay PayOS action",
        "data-portal-no-transient",
    ):
        assert phrase in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "bridge_request"):
        assert forbidden not in surface


def test_subtitle_source_picker_is_typed_owner_scoped_and_paged() -> None:
    hydration = _between(
        INTEGRATION,
        "function subtitleAssetOperationsPathIsCurrent(path)",
        "const OPERATION_HISTORY_LIST_LIMIT",
    )
    assert "function subtitleAssetReferenceItem(value)" in hydration
    assert 'extension === ".srt" && contentType === "application/x-subrip"' in hydration
    assert 'extension === ".vtt" && contentType === "text/vtt"' in hydration
    assert "source.items.map(subtitleAssetReferenceItem).filter(Boolean)" in hydration
    assert "reference_kind=subtitle" in hydration
    assert "/subtitle-asset-operations?limit=" in hydration
    assert 'cache: "no-store"' in hydration
    assert "subtitleAssetOperationsRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)" in hydration
    assert "subtitleAssetReferencesProjection" in hydration
    assert "selected: null" in hydration
    assert "previous_offset" in hydration
    assert '"/assets"' not in hydration
    assert '"/jobs"' not in hydration
    assert "storage_key" not in hydration
    assert "sha256" not in hydration
    assert "source_asset_id" not in hydration.split("function subtitleAssetOperationPayload", 1)[0]

    portal_surface = _between(PORTAL, "function subtitleAssetOperationSources(context)", "function subtitleAssetOperationCanDownload")
    assert "selected ? [selected, ...items] : items" in portal_surface
    assert "data-subtitle-asset-reference-offset" in PORTAL
    assert 'data-portal-action="subtitle-asset-reference-page"' in PORTAL
    assert "subtitle-asset-reference-page" in _between(PORTAL, "function dispatchAction(source, context)", "function sidebarFocusables")


def test_hydration_and_actions_are_signed_csrf_idempotent_and_no_fake_success() -> None:
    assert 'if (currentPath === SUBTITLE_ASSET_OPERATIONS_ROUTE)' in INTEGRATION
    assert "await hydrateSubtitleAssetOperations();" in INTEGRATION
    assert 'clearSubtitleAssetOperationsProjection("guarded")' in INTEGRATION
    for capability in (
        '"subtitle-asset-operation-view": Boolean(account && assetVaultEnabled && subtitleAssetOperationsEnabled)',
        '"subtitle-asset-operation-submit": Boolean(account && me.csrf_token && assetVaultEnabled && subtitleAssetOperationsEnabled)',
        '"subtitle-asset-operation-download": Boolean(account && assetVaultEnabled && subtitleAssetOperationsEnabled)',
    ):
        assert capability in INTEGRATION

    actions = _between(
        INTEGRATION,
        'if (action === "subtitle-asset-operation-refresh")',
        'if (action === "subtitle-format-convert")',
    )
    for action in (
        "subtitle-asset-operation-refresh",
        "subtitle-asset-reference-page",
        "subtitle-asset-operation-submit",
        "subtitle-asset-operation-download",
    ):
        assert action in actions
    for endpoint in ('"/subtitle-asset-operations/validate"', '"/subtitle-asset-operations/convert"'):
        assert endpoint in INTEGRATION
    assert "idempotency_key: submission.key" in actions
    assert "acquireSubmission(intent.scope, JSON.stringify(intent.payload))" in actions
    assert "subtitleAssetOperationReceipt(result, expectedKind)" in actions
    assert "++subtitleAssetOperationsHydrationEpoch" in actions
    assert "await hydrateSubtitleAssetOperations({ selectedId: intent.payload.source_asset_id })" in actions
    assert "operation.output_available !== true" in INTEGRATION
    assert "browser still waits for a fresh" in actions
    for forbidden in ("bridgeavailable", "core bridge", "payos", "/payments", "/jobs", "provider call"):
        assert forbidden not in actions.lower()


def test_download_requires_verified_attachment_and_private_cache_headers() -> None:
    download = _between(INTEGRATION, "async function downloadSubtitleAssetOperation(operationId)", "const OPERATION_HISTORY_LIST_LIMIT")
    for required in (
        'operation.output_available !== true',
        'operation.kind !== "subtitle_convert"',
        'operation.state !== "completed"',
        'cache: "no-store"',
        'disposition.includes("attachment")',
        'cacheControl.includes("no-store")',
        'nosniff !== "nosniff"',
        'referrerPolicy.includes("no-referrer")',
        'corp !== "same-origin"',
        "byteSize !== expectedSize",
        "blob.size !== expectedSize",
        "URL.revokeObjectURL(objectUrl)",
    ):
        assert required in download
    assert "window.open" not in download
    assert "location.href" not in download

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/subtitle/assets"' not in shell
    assert '"/api/v1/subtitle-asset-operations"' not in shell


def test_portal_keeps_source_target_selection_accessible_and_mobile_sized() -> None:
    assert "function synchronizeSubtitleAssetOperationForm(form)" in PORTAL
    assert "data-subtitle-asset-format=" in PORTAL
    assert 'target.value = sourceFormat === "srt" ? "vtt" : "srt";' in PORTAL
    assert "Kiểm định không tạo file output" in PORTAL
    assert "data-subtitle-asset-target-hint" in PORTAL
    assert "data-subtitle-asset-operation-id" in PORTAL
    # The pager remains outside the label so native select naming and button
    # activation stay unambiguous for keyboard and screen-reader users.
    assert 'label for="subtitle-asset-source"' in PORTAL
    assert 'aria-describedby="subtitle-asset-source-hint"' in PORTAL
    assert 'id="subtitle-asset-source-hint"' in PORTAL
    assert "</label>${sourcePager}" not in PORTAL
    for selector in (
        ".portal-subtitle-assets-source-pager",
        ".portal-subtitle-assets-source-pager .portal-button { min-height: 44px;",
        ".portal-subtitle-asset-operation-actions .portal-button { min-height: 44px;",
        ".portal-subtitle-assets-source-pager { align-items: flex-start; flex-direction: column; }",
    ):
        assert selector in CSS


def test_metadata_loading_and_unverified_conversion_never_claim_a_job_success() -> None:
    # Hydration is a metadata read, not the lifecycle of a subtitle operation.
    assert 'loading: { status: "read_only", label: "Đang tải metadata private" }' in PORTAL
    assert "function pageStatusBadge(page, context)" in PORTAL
    assert '[SUBTITLE_ASSET_OPERATIONS_ROUTE]: "read_only"' in INTEGRATION
    assert "subtitleAssetOperationsReadState: \"loading\"" in INTEGRATION

    surface = _between(PORTAL, "function renderSubtitleAssetOperations(page, context)", "function renderSubtitleProjectCards")
    assert "const readyForInteraction = readState === \"ready\";" in surface
    assert "canSubmit && sources.length && readyForInteraction" in surface
    assert "canView && readyForInteraction && canPrevious" in surface
    assert 'String(item.kind || "") === "subtitle_convert" && String(item.state || "") === "completed" && !outputReady' in surface
    assert '? "unavailable" : String(item.state || "guarded")' in surface


def test_contract_keeps_subtitle_asset_operations_outside_bot_payment_and_provider_scope() -> None:
    for phrase in (
        "The browser submits only an Asset Vault UUID",
        "idempotency key",
        "No Bot/Core Bridge call",
        "PayOS",
        "No public URL",
        "fake completed output",
        "WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED",
        "Metadata hydration is a Portal read state",
    ):
        assert phrase in CONTRACT
