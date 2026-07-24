"""Focused contracts for the Collection → Audio Operations handoff.

The handoff is a route-local convenience only. It must not become a second
asset authority, retain a source outside the current tab interaction, or turn
an explicit navigation into a hidden media operation.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "AUDIO_COLLECTION_OPERATION_HANDOFF_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_collection_detail_exposes_only_an_explicit_typed_audio_handoff() -> None:
    item_surface = _between(PORTAL, "function mediaAudioOperationHandoffAsset", "function renderMediaWorkspaceDetail")
    assert 'data-portal-action="media-audio-operation-handoff"' in item_surface
    assert "Mở Audio Operations" in item_surface
    assert "function mediaAudioOperationHandoffAsset(item, collection)" in item_surface
    for required in (
        'String(sourceCollection.state || "") !== "active"',
        'String(asset.state || "") !== "active"',
        "asset.download_available !== true",
        "String(sourceItem.asset_id || \"\") !== assetId",
        "byteSize > 25 * 1024 * 1024",
        'data-media-collection-id="${safeText(String(collection.id))}"',
        'data-media-item-id="${safeText(itemId)}"',
        'canOpenAudioOperations ? "" : " disabled"',
    ):
        assert required in item_surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "<audio", "provider", "payos", "wallet"):
        assert forbidden not in item_surface.lower()


def test_handoff_freshly_rechecks_signed_detail_then_only_navigates_and_rehydrates() -> None:
    source_guard = _between(INTEGRATION, "function mediaAudioOperationHandoffSource", "function isNativeMusicPromptComposerPath")
    for required in (
        "route !== expectedRoute || currentPortalPath() !== expectedRoute",
        "base().mediaCollectionDetail",
        'String(collection.state || "") !== "active"',
        "String(item.delivery || \"\") !== \"asset_vault_attachment_only\"",
        "audioAssetReferenceItem(asset)",
        "source.id !== String(item.asset_id)",
        "return { asset_id: source.id };",
    ):
        assert required in source_guard

    action = _between(
        INTEGRATION,
        'if (action === "media-audio-operation-handoff")',
        'if (action === "media-collection-create")',
    )
    for required in (
        'base().capabilities["audio-asset-operation-view"] === true',
        "mediaAudioOperationHandoffSource(collectionId, itemId, route)",
        "const localSource = mediaAudioOperationHandoffSource(collectionId, itemId, route)",
        'api("/media-workspace/collections/" + encodeURIComponent(collectionId), { cache: "no-store" })',
        "mediaAudioOperationHandoffRequestIsCurrent(requestEpoch, sessionEpoch, route)",
        "const freshDetail = verified.data",
        "mediaAudioOperationHandoffSource(collectionId, itemId, route, freshDetail)",
        "++audioAssetOperationsViewEpoch;",
        'clearAudioAssetOperationsProjection("loading")',
        'window.history.pushState({}, "", AUDIO_ASSET_OPERATIONS_ROUTE)',
        'merge({ path: AUDIO_ASSET_OPERATIONS_ROUTE, title: "TOAN AAS" })',
        "await hydrateAudioAssetOperations({ selectedId: source.asset_id })",
        "refreshed.references && refreshed.references.selected",
        'document.getElementById("audio-asset-source")',
        "sourceControl.focus({ preventScroll: true })",
        "selected.id === source.asset_id",
        "không tự dùng nguồn cũ",
    ):
        assert required in action
    for forbidden in (
        "localstorage",
        "sessionstorage",
        "window.location.assign",
        "/audio-asset-operations/inspect",
        "/audio-asset-operations/convert",
        "/audio-asset-operations/normalize",
        "idempotency_key",
        "telegram",
        "provider",
        "payos",
        "wallet",
    ):
        assert forbidden not in action.lower()
    assert action.lower().count("api(") == 1


def test_direct_audio_operations_route_stays_independent_of_collection_handoff() -> None:
    hydration = _between(INTEGRATION, "async function hydrateAudioAssetOperations(options)", "function audioAssetOperationPayload")
    assert "media-audio-operation-handoff" not in hydration
    assert "/media-workspace" not in hydration
    assert "reference_kind=audio" in hydration
    assert "audioAssetReferencesProjection" in hydration
    assert "selectedId" in hydration

    surface = _between(PORTAL, "function renderAudioAssetOperations(page, context)", "function renderSubtitleProjectCards")
    assert "media-audio-operation-handoff" not in surface
    assert "Mở Audio Operations" not in surface


def test_handoff_contract_keeps_bot_payment_provider_and_output_import_out_of_scope() -> None:
    for phrase in (
        "explicitly press **Mở Audio Operations**",
        "written to a URL/query",
        "state=active&reference_kind=audio",
        "Direct `/audio/assets` navigation remains unchanged",
        "This handoff adds no API and no server-side write",
        "AUDIO_SOURCE_CHANGED",
        "No Bot/Core Bridge, provider, Key4U, PayOS, wallet/Xu, Telegram identity",
        "output import into Asset Vault",
    ):
        assert phrase in CONTRACT


def test_late_audio_write_cannot_rehydrate_over_a_newer_handoff_or_source_page() -> None:
    helper = _between(
        INTEGRATION,
        "function audioAssetOperationsViewIsCurrent",
        "function clearAudioAssetOperationsProjection",
    )
    for required in (
        "viewEpoch === audioAssetOperationsViewEpoch",
        "currentPortalPath() === expectedPath",
        "audioAssetOperationsPathIsCurrent(expectedPath)",
        "base().assetVaultEnabled === true",
        "base().audioAssetOperationsEnabled === true",
    ):
        assert required in helper

    submit = _between(
        INTEGRATION,
        'if (action === "audio-asset-operation-submit")',
        'if (action === "audio-asset-operation-download")',
    )
    for required in (
        "const submissionViewEpoch = audioAssetOperationsViewEpoch;",
        "const submissionPath = AUDIO_ASSET_OPERATIONS_ROUTE;",
        "audioAssetOperationsViewIsCurrent(submissionViewEpoch, submissionPath)",
        "receiptConfirmedAwayFromView = true;",
        "if (receiptAndRefreshConfirmed || receiptConfirmedAwayFromView) discardSubmission(intent.scope, submission);",
    ):
        assert required in submit

    action_surface = _between(
        INTEGRATION,
        'if (action === "audio-asset-operation-refresh")',
        'if (action === "audio-asset-operation-download")',
    )
    assert action_surface.count("++audioAssetOperationsViewEpoch;") >= 2
