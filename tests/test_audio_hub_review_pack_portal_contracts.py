"""Focused contracts for the transient Audio Hub collection review pack."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
ROUTER = (ROOT / "copyfast_music_media.py").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "AUDIO_HUB_REVIEW_PACK_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start): source.index(end, source.index(start))]


def test_review_pack_is_a_narrow_owner_scoped_media_workspace_endpoint() -> None:
    assert "class CollectionReviewPackRequest(BaseModel):" in ROUTER
    assert '@router.post("/collections/{collection_id}/review-pack")' in ROUTER
    endpoint = _between(ROUTER, "async def review_collection_pack", "def _collection_for_item_mutation")
    for required in (
        "Depends(require_csrf)",
        "_collection_row(conn, collection_id=collection_id, account_id=account_id)",
        "payload.expected_revision",
        "with read_transaction() as conn:",
        "_collection_review_reference_summary",
        "_collection_review_pack_boundary()",
    ):
        assert required in endpoint
    for forbidden in (
        "with transaction() as conn:",
        "_idempotent(",
        "_event(",
        "_audit(",
        "copyfast_bridge",
        "payos",
        "wallet",
        "provider",
        "telegram",
        "job",
    ):
        assert forbidden not in endpoint.lower()


def test_review_pack_receipt_is_count_only_and_has_literal_no_execution_boundary() -> None:
    composer = _between(ROUTER, "def _collection_review_pack_boundary", "def _music_prompt_composer_line")
    for required in (
        '"collection_mutated": False',
        '"review_pack_persisted": False',
        '"approval_recorded": False',
        '"source_audio_inspected": False',
        '"provider_called": False',
        '"job_created": False',
        '"wallet_mutated": False',
        '"payment_started": False',
        '"rights_verified": False',
        '"release_approved": False',
        '"needs_brief"',
        '"needs_reference_metadata"',
        '"human_review_required"',
    ):
        assert required in composer
    summary = _between(ROUTER, "def _collection_review_reference_summary", "def _collection_review_pack(")
    for required in ("SELECT i.role", "i.favorite", "i.user_declared_duration_seconds", "attribution_missing", "license_missing", "unavailable"):
        assert required in summary
    for forbidden in ("storage_key", "sha256", "original_filename", "display_name", "creative_brief"):
        assert forbidden not in summary


def test_portal_binds_review_to_the_current_audio_hub_route_revision_and_session() -> None:
    assert '"audio-hub-review-pack-compose": Boolean(account && me.csrf_token && mediaWorkspaceEnabled)' in INTEGRATION
    for helper in ("audioHubReviewPackBoundaryIsSafe", "audioHubReviewPackResultIsSafe", "audioHubReviewPackRequestIsCurrent"):
        assert f"function {helper}" in INTEGRATION
    action = _between(INTEGRATION, 'if (action === "audio-hub-review-pack-compose")', 'if (action === "media-collection-compose")')
    for required in (
        'mediaWorkspaceVisualRoot(route) !== "/audio-hub"',
        'capabilities["audio-hub-review-pack-compose"] !== true',
        "mediaWorkspaceReviewPackRequestEpoch",
        'api(`/media-workspace/collections/${encodeURIComponent(collectionId)}/review-pack`',
        "body: JSON.stringify({ expected_revision: expectedRevision })",
        "audioHubReviewPackResultIsSafe(output, collectionId, expectedRevision)",
        "merge({ audioHubReviewPack: output })",
    ):
        assert required in action
    for forbidden in ("acquiresubmission", "idempotency_key", "localstorage", "sessionstorage", "payos", "wallet", "telegram", "provider", "job"):
        assert forbidden not in action.lower()
    for reset in (
        "audioHubReviewPack: {},",
        "++mediaWorkspaceReviewPackRequestEpoch;",
        "mediaWorkspaceReviewPackRequestEpoch = 0;",
    ):
        assert reset in INTEGRATION


def test_portal_renders_an_explicit_accessible_review_without_audio_or_handoff() -> None:
    review = _between(PORTAL, "function renderAudioHubReviewPack", "function renderAudioHubCollectionBoard")
    for required in (
        "data-audio-hub-review-pack-status",
        'role="status"',
        'aria-live="polite"',
        'data-portal-action="audio-hub-review-pack-compose"',
        "Lập gói review",
        "Không có ghi nhận review nghiệp vụ, idempotency, event hay audit record",
    ):
        assert required in review
    for forbidden in ("<audio", "new audio(", "api(", "fetch(", "localstorage", "sessionstorage", "?collection", "?asset", "source_url", "download_url"):
        assert forbidden not in review.lower()
    assert "function focusSnapshot" in PORTAL
    assert "audio-hub-review-pack-status" in PORTAL
    assert "audio-hub-review-pack-action" in PORTAL
    assert "Audio Hub Collection Review Pack" in CONTRACT
