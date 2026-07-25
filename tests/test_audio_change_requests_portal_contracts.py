"""Static contracts for the Audio Hub-only Audio Change Request surface."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
BACKEND = (ROOT / "copyfast_audio_change_requests.py").read_text(encoding="utf-8")
OPERATIONS = (ROOT / "copyfast_audio_asset_operations.py").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "AUDIO_CHANGE_REQUEST_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_audio_change_request_is_audio_hub_only_and_never_a_direct_execution_control() -> None:
    surface = _between(PORTAL, "function renderAudioChangeRequests", "function renderAudioHubCollectionBoard")
    assert 'const changeRequests = isAudioHubRoute(route) ? renderAudioChangeRequests(collection, items, context, route) : "";' in PORTAL
    assert "data-portal-action=\"audio-change-request-draft\"" in surface
    assert "data-portal-action=\"audio-change-request-estimate\"" in surface
    assert "data-portal-action=\"audio-change-request-confirm\"" in surface
    assert "data-portal-action=\"audio-change-request-refresh\"" in surface
    for operation in ("inspect", "convert_mp3", "convert_m4a", "normalize"):
        assert operation in surface
    for forbidden in ("fetch(", "api(", "audio-asset-operations/convert", "audio-asset-operations/normalize", "localStorage", "<audio"):
        assert forbidden not in surface


def test_portal_hydrates_a_private_request_projection_and_fences_route_session_and_shape() -> None:
    hydration = _between(INTEGRATION, "const AUDIO_CHANGE_REQUEST_OPERATIONS", "async function hydrateMediaCollection")
    assert "function audioChangeRequestItem" in hydration
    assert "audioAssetOperationItem(source.operation)" in hydration
    assert "mediaWorkspaceVisualRoot(route) === \"/audio-hub\"" in hydration
    assert "base().audioChangeRequestsEnabled === true" in hydration
    assert 'api(`/audio-change-requests/drafts?collection_id=${encodeURIComponent(expectedCollectionId)}&limit=24`, { cache: "no-store" })' in hydration
    assert "requestEpoch !== audioChangeRequestHydrationEpoch" in hydration
    assert "sessionEpoch !== mediaWorkspaceSessionEpoch" in hydration
    assert 'merge({ audioChangeRequests: [], audioChangeRequestReadState: "loading" })' in hydration
    assert "clearAudioChangeRequestsProjection(\"failed\")" in hydration
    assert '"audio-change-request-view": Boolean(account && mediaWorkspaceEnabled && assetVaultEnabled && audioAssetOperationsEnabled && audioChangeRequestsEnabled)' in INTEGRATION
    for key in ("draft", "estimate", "confirm", "refresh"):
        assert f'"audio-change-request-{key}"' in INTEGRATION


def test_detached_audio_request_stays_visible_as_a_guarded_history_record() -> None:
    surface = _between(PORTAL, "function renderAudioChangeRequests", "function renderAudioHubCollectionBoard")
    assert "requestId && itemId && sourceById.has(itemId)" not in surface
    assert "function audioChangeRequestSourceIsActive" in surface
    assert "Audio reference đã được gỡ khỏi collection" in surface
    assert "sourceAttached ? audioChangeRequestStage(source)" in surface


def test_archived_collection_never_exposes_actionable_request_controls() -> None:
    surface = _between(PORTAL, "function renderAudioChangeRequests", "function renderAudioHubCollectionBoard")
    assert 'const collectionActive = String(collection && collection.state || "").trim() === "active";' in surface
    assert "const ready = collectionActive && canView && readState === \"ready\";" in surface
    assert "Collection đã archive" in surface
    assert "collectionActive && sourceAttached" in surface


def test_backend_has_explicit_lifecycle_and_atomic_executor_precondition() -> None:
    for required in (
        '@router.post("/drafts")',
        '@router.post("/drafts/{request_id}/estimate")',
        '@router.post("/drafts/{request_id}/confirm")',
        '@router.get("/drafts")',
        "class AudioChangeDraftRequest",
        "class AudioChangeEstimateRequest",
        "class AudioChangeConfirmRequest",
        "_assert_snapshot_current",
        "reservation_precondition",
        "audio_operations.execute_audio_asset_operation",
        "WEB_AUDIO_CHANGE_REQUEST_SOURCE_CHANGED",
        "requires_confirmation",
    ):
        assert required in BACKEND
    assert "reservation_precondition: Callable[[Any, dict[str, Any]], None] | None = None" in OPERATIONS
    assert "reservation_precondition(conn, source)" in OPERATIONS
    assert "WEBAPP_AUDIO_CHANGE_REQUESTS_ENABLED" in CONTRACT
    assert "price quote" in CONTRACT
    assert "PayOS" in CONTRACT
    assert "fake" not in CONTRACT.lower() or "fake completed" in CONTRACT.lower()
