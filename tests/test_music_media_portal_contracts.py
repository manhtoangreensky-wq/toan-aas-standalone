"""Static safety contracts for the Web-native Audio Library & Briefing Portal.

The checks intentionally cover only UI/API boundary regressions that would be
costly or unsafe in production: accidentally falling back to Bot music paths,
introducing a provider/payment bridge, rendering a raw audio player, or adding
private workspace responses to the PWA cache.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_music_media.py").read_text(encoding="utf-8")


def test_media_workspace_is_a_real_signed_web_route_not_a_bot_music_shell() -> None:
    assert 'customerPage("/media-workspace", "Audio Library & Briefing"' in PORTAL
    assert 'customerPage("/media-workspace/new", "Audio Collection mới"' in PORTAL
    assert 'path: "/media-workspace/:id"' in PORTAL
    assert "function renderMediaWorkspace(page, context)" in PORTAL
    assert "function renderMediaWorkspaceDetail(page, context)" in PORTAL
    assert 'case "media-workspace": return renderMediaWorkspace(page, context);' in PORTAL
    assert 'case "media-workspace-detail": return renderMediaWorkspaceDetail(page, context);' in PORTAL
    assert "MEDIA_WORKSPACE_PATH" in PAGES
    assert "MEDIA_WORKSPACE_PATH.fullmatch(normalized)" in PAGES
    assert 'botCompanionPage("/media-workspace"' not in PORTAL
    assert 'href="/media-workspace/${encodeURIComponent(id)}"' in PORTAL


def test_media_workspace_hydrates_and_mutates_only_through_owner_scoped_web_api() -> None:
    for helper in (
        "mediaWorkspaceCollectionIdFromPath",
        "isNativeMediaWorkspacePath",
        "mediaWorkspaceSafetyError",
        "mediaWorkspaceFilterPayload",
        "mediaWorkspaceListOffset",
        "mediaWorkspaceListPath",
        "mediaWorkspaceListingProjection",
        "mediaAudioAssetFilterPayload",
        "mediaAudioAssetListPath",
        "mediaAudioAssetListingProjection",
        "mediaCollectionPayload",
        "mediaItemPayload",
        "hydrateMediaWorkspace",
        "hydrateMediaAudioAssets",
        "hydrateMediaCollection",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    for endpoint in (
        'api("/media-workspace/summary")',
        'api("/media-workspace/policy")',
        'api("/media-workspace/events?limit=50")',
        'api(mediaWorkspaceListPath(filter, offset))',
        'api(mediaAudioAssetListPath(audioFilter, audioOffset))',
        'api(mediaAudioAssetListPath(filter, offset))',
        'api(`/media-workspace/collections/${encodeURIComponent(String(collectionId))}`)',
        'api("/media-workspace/collections",',
    ):
        assert endpoint in INTEGRATION

    assert '"media-workspace-view": Boolean(account && mediaWorkspaceEnabled)' in INTEGRATION
    assert '"media-workspace-page": Boolean(account && mediaWorkspaceEnabled)' in INTEGRATION
    assert '"media-audio-page": Boolean(account && mediaWorkspaceEnabled)' in INTEGRATION
    assert '"media-workspace-create": Boolean(account && me.csrf_token && mediaWorkspaceEnabled)' in INTEGRATION
    assert "WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED" in ROUTER
    assert "WEB_MEDIA_WORKSPACE_BODY_TOO_LARGE" in APP
    assert "MEDIA_WORKSPACE_BODY_MAX_BYTES = 64 * 1024" in APP
    assert '"media-workspace-write" if media_workspace_write' in APP
    assert '"media-workspace-read" if media_workspace_read' in APP

    # A denied/failed collection read must not leave a prior account's media
    # summary, collection cards, or audit events in the client projection.
    detail_hydrator = INTEGRATION[
        INTEGRATION.index("async function hydrateMediaCollection"):
        INTEGRATION.index("async function hydrateSupportDesk")
    ]
    assert "mediaWorkspaceSummary: {}, mediaCollections: [], mediaWorkspaceEvents: []" in detail_hydrator

    action_start = INTEGRATION.index('if (action === "media-workspace-filter"')
    # Stop at the next standalone composer route. The action dispatcher has
    # several unrelated Web-native tools after Media Workspace; including
    # them here made this contract inspect unrelated Telegram copy.
    action_end = INTEGRATION.index('if (action === "content-prompt-pack-compose")', action_start)
    actions = INTEGRATION[action_start:action_end].lower()
    for forbidden in ("bridgeavailable", "payos", "wallet", "telegram", "/music"):
        assert forbidden not in actions
    for action in (
        "media-collection-create",
        "media-collection-update",
        "media-collection-archive",
        "media-collection-restore",
        "media-collection-duplicate",
        "media-collection-restore-version",
        "media-collection-compose",
        "media-item-attach",
        "media-item-update",
        "media-item-detach",
        "media-workspace-page",
        "media-audio-filter",
        "media-audio-page",
    ):
        assert action in actions
    assert "acquiresubmission(scope" in actions
    assert "idempotency_key: submission.key" in actions
    assert "local_deterministic_draft_only" in actions
    assert "provider_called !== false" in actions
    assert "charge_started !== false" in actions
    assert "data-media-collection-offset" in PORTAL
    assert "data-media-audio-offset" in PORTAL
    assert "function renderMediaWorkspacePagination" in PORTAL
    assert "function renderMediaAudioAssetPagination" in PORTAL
    assert "portal-media-pagination" in PORTAL
    assert "portal-media-pagination" in CSS
    assert "portal-media-audio-filter" in CSS
    assert "LIMIT ? OFFSET ?" in ROUTER
    assert "LOWER(extension)=?" in ROUTER


def test_media_workspace_has_no_raw_player_provider_import_or_private_pwa_cache() -> None:
    # Audio is retained as an Asset Vault attachment. A future streaming/player
    # adapter needs its own signed URL and media-security review.
    assert "<audio" not in PORTAL.lower()
    assert "new audio(" not in PORTAL.lower()
    assert "source_url" not in PORTAL
    assert "asset.download_url" not in PORTAL
    assert '"delivery": "asset_vault_attachment_only"' in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import requests" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import payos" not in ROUTER.lower()
    assert "from payos" not in ROUTER.lower()

    # The source explicitly documents the protected route, while the actual
    # cache manifest remains a fixed public shell only.
    assert "/api/v1/media-workspace" in SERVICE_WORKER
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/media-workspace" not in shell
    assert '"/media-workspace"' not in shell
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v' in SERVICE_WORKER
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER

    for selector in (
        ".portal-media-workspace-intro",
        ".portal-media-collection-grid",
        ".portal-media-item-card",
        ".portal-media-composer-result",
        ".portal-media-collection-grid { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS


def test_media_workspace_reads_ignore_late_session_route_and_page_responses() -> None:
    for epoch in (
        "mediaWorkspaceSessionEpoch",
        "mediaWorkspaceListHydrationEpoch",
        "mediaWorkspaceAudioHydrationEpoch",
        "mediaWorkspaceDetailHydrationEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    helper_start = INTEGRATION.index("function mediaWorkspaceRequestIsCurrent")
    helper_end = INTEGRATION.index("async function hydrateMediaWorkspace", helper_start)
    helper = INTEGRATION[helper_start:helper_end]
    for requirement in (
        "sessionEpoch === mediaWorkspaceSessionEpoch",
        "currentPortalPath() === expectedPath",
        "isNativeMediaWorkspacePath(expectedPath)",
        "!isNativeMusicPromptComposerPath(expectedPath)",
        "base().mediaWorkspaceEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper

    list_start = INTEGRATION.index("async function hydrateMediaWorkspace")
    audio_start = INTEGRATION.index("async function hydrateMediaAudioAssets", list_start)
    detail_start = INTEGRATION.index("async function hydrateMediaCollection", audio_start)
    list_read = INTEGRATION[list_start:audio_start]
    audio_read = INTEGRATION[audio_start:detail_start]
    detail_read = INTEGRATION[detail_start:INTEGRATION.index("function contentStudioRequestIsCurrent", detail_start)]

    assert "const requestEpoch = ++mediaWorkspaceListHydrationEpoch;" in list_read
    assert "mediaWorkspaceRequestIsCurrent(requestEpoch, mediaWorkspaceListHydrationEpoch, sessionEpoch, path)" in list_read
    assert "const requestEpoch = ++mediaWorkspaceAudioHydrationEpoch;" in audio_read
    assert "mediaWorkspaceRequestIsCurrent(requestEpoch, mediaWorkspaceAudioHydrationEpoch, sessionEpoch, expectedPath)" in audio_read
    assert "const requestEpoch = ++mediaWorkspaceDetailHydrationEpoch;" in detail_read
    assert "if (currentPortalPath() !== route) return null;" in detail_read
    assert "mediaWorkspaceRequestIsCurrent(requestEpoch, mediaWorkspaceDetailHydrationEpoch, sessionEpoch, route)" in detail_read
