"""Static contracts for the private Web-native Audio Asset Operations UI.

The browser may choose only server-filtered owner-scoped audio metadata.  It
must not become a public player, provider/Bot adapter, browser FFmpeg runner
or a generic Jobs/Assets fallback.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "AUDIO_ASSET_OPERATIONS_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_audio_asset_operations_is_a_distinct_private_portal_route() -> None:
    assert 'customerPage("/audio/assets", "Audio Asset Operations"' in PORTAL
    assert 'layout: "audio-asset-operations", type: "audio-asset-operations"' in PORTAL
    assert "function renderAudioAssetOperations(page, context)" in PORTAL
    assert 'case "audio-asset-operations": return renderAudioAssetOperations(page, context);' in PORTAL
    assert '["/audio/assets", "Audio Asset Operations", ICONS.music]' in PORTAL
    assert '"/audio/assets": "audio_asset_operations"' in INTEGRATION
    assert 'const AUDIO_ASSET_OPERATIONS_ROUTE = "/audio/assets";' in INTEGRATION

    surface = _between(PORTAL, "function renderAudioAssetOperations(page, context)", "function renderSubtitleProjectCards")
    for phrase in (
        "Asset Vault",
        "Không public URL hay cache",
        "không có prompt, player, waveform hay browser-side processing",
        "không gọi Bot, provider, wallet/Xu hay PayOS",
        "data-portal-no-transient",
    ):
        assert phrase in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "bridge_request", "<audio"):
        assert forbidden not in surface


def test_audio_source_picker_is_typed_owner_scoped_and_paged() -> None:
    hydration = _between(
        INTEGRATION,
        "function audioAssetOperationsPathIsCurrent(path)",
        "const OPERATION_HISTORY_LIST_LIMIT",
    )
    assert "function audioAssetReferenceItem(value)" in hydration
    for pair in (
        'extension === ".mp3" && contentType === "audio/mpeg"',
        'extension === ".wav" && (contentType === "audio/wav" || contentType === "audio/x-wav")',
        'extension === ".m4a" && contentType === "audio/mp4"',
        'extension === ".ogg" && (contentType === "audio/ogg" || contentType === "application/ogg")',
    ):
        assert pair in hydration
    assert "reference_kind=audio" in hydration
    assert "/audio-asset-operations?limit=" in hydration
    assert 'cache: "no-store"' in hydration
    assert "audioAssetOperationsRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)" in hydration
    assert "audioAssetReferencesProjection" in hydration
    assert "selected: null" in hydration
    assert "previous_offset" in hydration
    assert '"/assets"' not in hydration
    assert '"/jobs"' not in hydration
    assert "storage_key" not in hydration
    assert "sha256" not in hydration
    assert "source_asset_id" not in hydration.split("function audioAssetOperationPayload", 1)[0]

    portal_surface = _between(PORTAL, "function audioAssetOperationSources(context)", "function renderAudioAssetOperations(page, context)")
    assert "selected ? [selected, ...items] : items" in portal_surface
    assert "data-audio-asset-reference-offset" in PORTAL
    assert 'data-portal-action="audio-asset-reference-page"' in PORTAL
    assert 'if (action === "audio-asset-reference-page")' in INTEGRATION


def test_hydration_and_writes_are_signed_idempotent_and_truthful() -> None:
    assert "await hydrateAudioAssetOperations();" in INTEGRATION
    assert 'clearAudioAssetOperationsProjection("guarded")' in INTEGRATION
    for capability in (
        '"audio-asset-operation-view": Boolean(account && assetVaultEnabled && audioAssetOperationsEnabled)',
        '"audio-asset-operation-submit": Boolean(account && me.csrf_token && assetVaultEnabled && audioAssetOperationsEnabled)',
        '"audio-asset-operation-download": Boolean(account && assetVaultEnabled && audioAssetOperationsEnabled)',
    ):
        assert capability in INTEGRATION

    actions = _between(
        INTEGRATION,
        'if (action === "audio-asset-operation-refresh")',
        'if (action === "subtitle-format-convert")',
    )
    for action in (
        "audio-asset-operation-refresh",
        "audio-asset-reference-page",
        "audio-asset-operation-submit",
        "audio-asset-operation-download",
    ):
        assert action in actions
    for endpoint in ('"/audio-asset-operations/inspect"', '"/audio-asset-operations/convert"', '"/audio-asset-operations/normalize"'):
        assert endpoint in INTEGRATION
    assert "idempotency_key: submission.key" in actions
    assert "acquireSubmission(intent.scope, JSON.stringify(intent.payload))" in actions
    assert "audioAssetOperationReceipt(result, intent.expectedKind)" in actions
    assert "++audioAssetOperationsHydrationEpoch" in actions
    assert "await hydrateAudioAssetOperations({ selectedId: intent.payload.source_asset_id })" in actions

    payload = _between(INTEGRATION, "function audioAssetOperationPayload(fields)", "function audioAssetOperationReceipt")
    assert "source_asset_id: sourceAssetId" in payload
    assert "target_format: \"mp3\"" in payload
    assert "target_format: \"m4a\"" in payload
    assert "normalization_profile" not in payload
    assert "ffmpeg" not in payload.lower()
    receipt = _between(INTEGRATION, "function audioAssetOperationReceipt", "function audioAssetOperationSourcesFromState")
    assert "Validate the raw server receipt before projecting it for display" in receipt
    assert "raw.output_available !== false" in receipt
    assert 'raw.normalization_profile !== "speech_safe_v1"' in receipt
    assert 'raw.target_format !== "m4a"' in receipt
    assert 'expectedKind === "audio_inspect" && operation.output_available === true' in receipt
    assert 'operation.output_available !== true' in receipt
    for forbidden in ("bridgeavailable", "core bridge", "payos", "/payments", "provider call"):
        assert forbidden not in actions.lower()


def test_private_download_requires_verified_attachment_and_is_not_cached() -> None:
    download = _between(INTEGRATION, "async function downloadAudioAssetOperation(operationId)", "const OPERATION_HISTORY_LIST_LIMIT")
    for required in (
        "operation.output_available !== true",
        '["audio_convert", "audio_normalize"].includes(operation.kind)',
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
    assert '"/audio/assets"' not in shell
    assert '"/api/v1/audio-asset-operations"' not in shell


def test_audio_portal_keeps_controls_accessible_and_metadata_is_not_a_job() -> None:
    surface = _between(PORTAL, "function renderAudioAssetOperations(page, context)", "function renderSubtitleProjectCards")
    assert 'label for="audio-asset-source"' in surface
    assert 'aria-describedby="audio-asset-source-hint"' in surface
    assert 'id="audio-asset-source-hint"' in surface
    assert "</label>${sourcePager}" not in surface
    assert 'const readyForInteraction = readState === "ready";' in surface
    assert "canSubmit && sources.length && readyForInteraction" in surface
    assert "canView && readyForInteraction && canPrevious" in surface
    assert 'const transform = kind === "audio_convert" || kind === "audio_normalize";' in surface
    assert 'kind === "audio_inspect" ? "Kiểm định không tạo file output"' in surface
    assert 'transform && String(item.state || "") === "completed" && !outputReady ? "unavailable"' in surface
    assert "Đang tải metadata audio từ Asset Vault owner-scoped" in surface
    assert "browser chưa suy đoán trạng thái hoặc output nào" in surface
    for selector in (
        ".portal-audio-assets-source-pager",
        ".portal-audio-assets-source-pager .portal-button, .portal-audio-asset-operation-actions .portal-button { min-height: 44px;",
        ".portal-audio-asset-operation-meta, .portal-audio-asset-operation-actions, .portal-audio-assets-source-pager { align-items: flex-start; flex-direction: column; }",
    ):
        assert selector in CSS


def test_write_keeps_idempotency_key_when_receipt_or_private_refresh_is_ambiguous() -> None:
    actions = _between(
        INTEGRATION,
        'if (action === "audio-asset-operation-submit")',
        'if (action === "audio-asset-operation-download")',
    )
    assert "let receiptAndRefreshConfirmed = false;" in actions
    assert "await hydrateAudioAssetOperations({ selectedId: intent.payload.source_asset_id })" in actions
    assert "if (!refreshed) throw new Error" in actions
    assert "same idempotency key will be reused" not in actions  # Vietnamese public copy must remain localized.
    assert "cùng idempotency key sẽ được tái sử dụng" in actions
    assert "receiptAndRefreshConfirmed = true;" in actions
    assert "receiptConfirmedAwayFromView = true;" in actions
    assert "audioAssetOperationsViewIsCurrent(submissionViewEpoch, submissionPath)" in actions
    assert "if (receiptAndRefreshConfirmed || receiptConfirmedAwayFromView) discardSubmission(intent.scope, submission);" in actions
    assert "acknowledged" not in actions


def test_contract_keeps_audio_asset_operations_outside_bot_payment_and_provider_scope() -> None:
    for phrase in (
        "does not claim AI audio enhancement",
        "Bot's guarded `/audio_enhance` provider flow",
        "The browser supplies only an Asset Vault UUID",
        "idempotency key",
        "No Bot/Core Bridge call",
        "PayOS",
        "No public URL",
        "fake completed output",
        "WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED",
        "Metadata hydration is a Portal read state",
    ):
        assert phrase in CONTRACT
