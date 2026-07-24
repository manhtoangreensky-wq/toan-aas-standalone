"""Focused contracts for the Audio Production Hub visual projection.

The hub is intentionally not another audio database or API. These checks keep
the new app-first route professional without letting it drift into a second
authority, a hidden handoff, or a faux audio/provider surface.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "AUDIO_PRODUCTION_HUB_CONTRACT.md").read_text(encoding="utf-8")
HANDOFF_CONTRACT = (ROOT / "docs" / "migration" / "AUDIO_COLLECTION_OPERATION_HANDOFF_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_audio_hub_registers_list_create_and_owner_checked_detail_routes() -> None:
    assert 'WebFeature("audio_hub", "Audio Production Hub", "music", "/audio-hub"' in REGISTRY
    assert 'customerPage("/audio-hub", "Audio Production Hub"' in PORTAL
    assert 'customerPage("/audio-hub/new", "Audio Production Brief mới"' in PORTAL
    assert 'path: "/audio-hub/:id"' in PORTAL
    assert 'case "audio-hub": return renderMediaWorkspace(page, context);' in PORTAL
    assert 'case "audio-hub-detail": return renderMediaWorkspaceDetail(page, context);' in PORTAL
    assert "AUDIO_HUB_PATH" in PAGES
    assert "AUDIO_HUB_PATH.fullmatch(normalized)" in PAGES
    assert '"/audio-hub/new"' in PAGES


def test_audio_hub_keeps_media_workspace_as_the_only_data_authority() -> None:
    alias_helpers = _between(INTEGRATION, "function mediaWorkspaceVisualRoot", "function mediaWorkspaceSafetyError")
    for required in (
        'return route === "/audio-hub" || route.startsWith("/audio-hub/") ? "/audio-hub" : "/media-workspace";',
        "function mediaWorkspaceCollectionRoute(collectionId, path)",
        "function isMediaWorkspaceListViewPath(path)",
        '"/audio-hub", "/audio-hub/new"',
        "^\\/(?:media-workspace|audio-hub)\\/([^/]+)$",
    ):
        assert required in alias_helpers

    for existing_endpoint in (
        'api("/media-workspace/summary")',
        'api("/media-workspace/policy")',
        'api("/media-workspace/events?limit=50")',
        'api(`/media-workspace/collections/${encodeURIComponent(String(collectionId))}`)',
    ):
        assert existing_endpoint in INTEGRATION
    assert 'api("/audio-hub' not in INTEGRATION
    assert "/api/v1/audio-hub" not in INTEGRATION
    assert "copyfast_audio_hub" not in (ROOT / "app.py").read_text(encoding="utf-8")

    actions = _between(INTEGRATION, 'if (action === "media-collection-create")', 'if (action === "media-collection-compose")')
    assert "window.location.assign(mediaWorkspaceCollectionRoute(collectionId, route));" in actions
    assert "window.location.assign(mediaWorkspaceCollectionRoute(createdId, route));" in actions
    assert "window.location.assign(`/media-workspace/${encodeURIComponent(collectionId)}`)" not in actions
    assert "window.location.assign(`/media-workspace/${encodeURIComponent(createdId)}`)" not in actions


def test_audio_hub_board_is_a_plain_safe_projection_with_explicit_next_steps() -> None:
    board = _between(PORTAL, "function renderAudioHubOverview", "function renderMediaWorkspace(page, context)")
    for required in (
        "Audio production board",
        "Brief & policy",
        "Asset Vault assembly",
        "Direction review",
        'href="/media-workspace/music-directions"',
        'href="/media-workspace/sfx-cue-sheet"',
        'href="/audio/assets"',
    ):
        assert required in board
    assert "function renderAudioHubCollectionBoard" in PORTAL
    for forbidden in (
        "<audio",
        "new audio(",
        "fetch(",
        "api(",
        "localstorage",
        "sessionstorage",
        "source_url",
        "download_url",
        "?collection",
        "?asset",
    ):
        assert forbidden not in board.lower()


def test_audio_hub_handoff_reuses_fresh_media_detail_and_private_pwa_scope() -> None:
    handoff = _between(INTEGRATION, "function mediaAudioOperationHandoffSource", "function isNativeMusicPromptComposerPath")
    assert "const expectedRoute = mediaWorkspaceCollectionRoute(normalizedCollectionId, route);" in handoff
    assert "route !== expectedRoute || currentPortalPath() !== expectedRoute" in handoff
    assert 'api("/media-workspace/collections/" + encodeURIComponent(collectionId), { cache: "no-store" })' in INTEGRATION
    assert 'window.history.pushState({}, "", AUDIO_ASSET_OPERATIONS_ROUTE)' in INTEGRATION

    shell = _between(WORKER, "const SHELL = Object.freeze([", "]);" )
    private_paths = _between(WORKER, "const PRIVATE_PATH_PREFIXES = Object.freeze([", "]);" )
    public_paths = _between(WORKER, "const PUBLIC_NAVIGATION_PATHS = Object.freeze([", "]);" )
    assert '"/audio-hub"' in private_paths
    assert '"/audio-hub"' not in shell
    assert '"/audio-hub"' not in public_paths
    assert "`/audio-hub/{collection_id}`" in HANDOFF_CONTRACT
    assert "no `audio_hub` database table, API namespace" in CONTRACT


def test_audio_hub_keeps_phone_controls_at_the_required_touch_target_size() -> None:
    phone_rules = _between(CSS, "@media (max-width: 700px) {", "}\n\n")
    for selector in (
        ".portal-audio-hub .portal-button",
        ".portal-audio-hub-detail .portal-button",
        ".portal-audio-hub .portal-input",
        ".portal-audio-hub-detail .portal-input",
        ".portal-audio-hub .portal-select",
        ".portal-audio-hub-detail .portal-select",
    ):
        assert selector in phone_rules
    assert "min-height: 44px;" in phone_rules
