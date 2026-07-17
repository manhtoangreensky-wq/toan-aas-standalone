"""Static contracts for the private Web-native Image Creative Studio.

The route is an art-direction workspace, not an alias for legacy `/image/*`
tools and not a browser-side image/provider/payment pipeline.  These focused
checks keep that boundary explicit as the portal changes.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_image_studio_is_a_native_route_not_a_legacy_image_alias() -> None:
    assert 'customerPage("/image-studio"' in PORTAL
    assert 'customerPage("/image-studio/new"' in PORTAL
    assert 'path: "/image-studio/:id"' in PORTAL
    assert "function renderImageStudio(" in PORTAL
    assert "function renderImageStudioDetail(" in PORTAL
    assert 'case "image-studio": return renderImageStudio(page, context);' in PORTAL
    assert 'case "image-studio-detail": return renderImageStudioDetail(page, context);' in PORTAL
    assert "IMAGE_STUDIO_PATH" in PAGES
    assert "IMAGE_STUDIO_PATH.fullmatch(normalized)" in PAGES
    assert 'if (linkPath === "/image-studio") return matchesRouteFamily(path, "/image-studio");' in PORTAL
    assert 'botCompanionPage("/image-studio"' not in PORTAL

    # The native family is excluded before either generic canonical hydration
    # or the historical `/image/*` operation surface can absorb it.
    assert "function isNativeImageStudioPath(" in INTEGRATION
    assert "isNativeImageStudioPath(path)" in INTEGRATION
    assert "isNativeImageStudioPath(currentPath)" in INTEGRATION
    assert "!isNativeImageStudioPath(currentPath)" in INTEGRATION
    assert "`/image`, `/image/edit` and" in INTEGRATION


def test_image_studio_uses_only_signed_owner_scoped_api_contracts() -> None:
    for helper in (
        "imageArtboardIdFromPath",
        "isNativeImageStudioPath",
        "imageStudioMetadataSafetyError",
        "imageArtboardPayload",
        "imageDirectionPayload",
        "imageStudioBoundaryIsSafe",
        "imageStudioArtboardFilterPayload",
        "imageStudioReferenceFilterPayload",
        "imageStudioListOffset",
        "imageStudioArtboardListPath",
        "imageStudioReferenceListPath",
        "imageStudioListingProjection",
        "imageStudioReferenceListingProjection",
        "imageStudioReferenceStateWithPage",
        "hydrateImageStudio",
        "hydrateImageStudioReferences",
        "hydrateImageArtboard",
        "imageStudioMutation",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    for endpoint in (
        'api("/image-studio/summary")',
        'api(imageStudioArtboardListPath(filter, offset))',
        'api("/image-studio/events?limit=50")',
        'api(imageStudioReferenceListPath("projects", projectRequest.filter, projectRequest.offset))',
        'api(imageStudioReferenceListPath("image_assets", assetRequest.filter, assetRequest.offset))',
        'api("/image-studio/policy")',
        'api("/image-studio/artboards/" + encodeURIComponent(String(artboardId)))',
        '"/image-studio/artboards/" + encodeURIComponent(String(artboardId)) + "/estimate"',
        'path: "/image-studio/artboards"',
        '`/image-studio/artboards/${encodeURIComponent(artboardId)}/directions`',
        '`/image-studio/artboards/${encodeURIComponent(artboardId)}/directions/${encodeURIComponent(directionId)}`',
        '`/image-studio/artboards/${encodeURIComponent(artboardId)}/directions/${encodeURIComponent(directionId)}/restore-version`',
        'return "/image-studio/artboards?" + query.toString();',
        'return "/image-studio/references/" + normalizedKind.replace("_", "-") + "?" + query.toString();',
    ):
        assert endpoint in INTEGRATION

    for capability in (
        '"image-studio-view": Boolean(account && imageStudioEnabled)',
        '"image-studio-page": Boolean(account && imageStudioEnabled)',
        '"image-studio-reference-page": Boolean(account && imageStudioEnabled)',
        '"image-artboard-create": Boolean(account && me.csrf_token && imageStudioEnabled)',
        '"image-artboard-update": Boolean(account && me.csrf_token && imageStudioEnabled)',
        '"image-direction-create": Boolean(account && me.csrf_token && imageStudioEnabled)',
        '"image-direction-update": Boolean(account && me.csrf_token && imageStudioEnabled)',
    ):
        assert capability in INTEGRATION

    # Metadata rejects URLs/handles; the browser may submit only canonical
    # Asset Vault UUID references, which remain owner-checked by the server.
    assert "https?:\\/\\/|\\bwww\\." in INTEGRATION
    assert "Asset Vault/Project UUID hợp lệ do server cấp" in INTEGRATION
    assert "asset_id: assetId || null" in INTEGRATION
    assert "reference_asset_id: referenceAssetId || null" in INTEGRATION
    image_studio_surface = PORTAL[PORTAL.index("const IMAGE_STUDIO_INTENTS"):PORTAL.index("const SUBTITLE_STUDIO_FORMATS")]
    assert "original_filename" not in image_studio_surface


def test_image_studio_portal_pagination_actions_keep_owner_scoped_reference_state() -> None:
    """Old artboards/references must be browsable without a client-side cache."""
    for value in (
        "IMAGE_STUDIO_ARTBOARD_LIST_LIMIT = 50",
        "IMAGE_STUDIO_REFERENCE_LIST_LIMIT = 50",
        "IMAGE_STUDIO_MAX_LIST_OFFSET = 10000",
        '"projects", "image_assets"',
        "imageStudioReferencesWithPinned",
        "imageStudioReferenceHydrationEpoch",
        "imageStudioReferenceRequestState",
        "imageStudioReferenceStateWithPage(existing, normalizedKind, filter, offset, data)",
    ):
        assert value in INTEGRATION

    # The browser receives bounded metadata pages only.  Current selections
    # are pinned from the signed detail response so an old reference never
    # silently switches to the first option after a page/filter change.
    assert "imageStudioReferenceListPath(\"projects\", projectRequest.filter, projectRequest.offset)" in INTEGRATION
    assert "imageStudioReferenceListPath(\"image_assets\", assetRequest.filter, assetRequest.offset)" in INTEGRATION
    assert "imageStudioReferencesWithPinned(" in INTEGRATION

    action_start = INTEGRATION.index('if (action === "image-studio-filter")')
    action_end = INTEGRATION.index('if (action === "subtitle-studio-refresh")')
    actions = INTEGRATION[action_start:action_end]
    for action in (
        "image-studio-filter",
        "image-studio-filter-clear",
        "image-studio-page",
        "image-studio-project-reference-filter",
        "image-studio-project-reference-filter-clear",
        "image-studio-project-reference-page",
        "image-studio-asset-reference-filter",
        "image-studio-asset-reference-filter-clear",
        "image-studio-asset-reference-page",
    ):
        assert action in actions
    assert "hydrateImageStudio(filter, 0)" in actions
    assert "hydrateImageStudio(undefined, imageStudioListOffset(" in actions
    assert "hydrateImageStudioReferences(kind, filter, 0)" in actions
    assert "hydrateImageStudioReferences(kind, undefined, imageStudioListOffset(" in actions
    assert "data-image-studio-offset" in PORTAL
    assert "data-image-studio-project-reference-offset" in PORTAL
    assert "data-image-studio-asset-reference-offset" in PORTAL


def test_image_studio_action_block_has_idempotency_and_child_revision_cas() -> None:
    start = INTEGRATION.index('if (action === "image-studio-refresh")')
    end = INTEGRATION.index('if (action === "subtitle-studio-refresh")')
    actions = INTEGRATION[start:end]
    actions_lower = actions.lower()
    for forbidden in (
        "bridgeavailable",
        "core bridge",
        "payos",
        "/payments",
        "/jobs",
        "provider",
        "renderer",
        "preview",
        "delivery",
        "wallet",
        "telegram",
    ):
        assert forbidden not in actions_lower
    for action in (
        "image-studio-refresh",
        "image-artboard-create",
        "image-artboard-update",
        "image-artboard-state",
        "image-artboard-restore-version",
        "image-direction-create",
        "image-direction-update",
        "image-direction-archive",
        "image-direction-restore",
        "image-direction-restore-version",
    ):
        assert action in actions

    # Artboard writes compare the artboard revision. Direction mutations use
    # the child revision so a sibling change cannot silently overwrite it.
    assert "const expectedRevision = validImageStudioRevision(detail.imageArtboardRevision);" in actions
    assert actions.count("const expectedRevision = validImageStudioRevision(detail.imageDirectionRevision);") >= 3
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "expected_revision: expectedRevision" in actions
    assert 'imageDirectionRevision: source.getAttribute("data-image-direction-revision") || ""' in PORTAL
    assert "data-image-direction-revision" in PORTAL

    # Client operation validation mirrors the backend DTO and prevents
    # predictable 422s before a signed mutation is sent.
    assert 'if (operation === "create" && !promptText)' in INTEGRATION
    assert 'if (["edit", "image_to_image"].includes(operation) && !promptText && !editInstructions)' in INTEGRATION
    assert 'if (["upscale", "remove_background"].includes(operation) && !promptText && !editInstructions && !compositionNotes)' in INTEGRATION


def test_image_studio_is_truthful_about_no_execution_or_media_output() -> None:
    for flag in (
        'boundary.execution === "authoring_only"',
        "boundary.provider_called === false",
        "boundary.image_created === false",
        "boundary.output_created === false",
        "boundary.media_uploads === false",
        "boundary.browser_media_url === false",
        "boundary.preview_available === false",
        "boundary.job_created === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_started === false",
        "boundary.payment_processed === false",
        'boundary.output_delivery === "guarded"',
    ):
        assert flag in INTEGRATION

    assert "const writable = state === \"draft\";" in PORTAL
    assert 'const artboardWritable = String(artboard.state || "") === "draft";' in PORTAL
    assert "Direction & self-review, không tạo ảnh" in PORTAL
    assert "Không có raw URL, blob, thumbnail, provider call, preview hoặc output." in PORTAL
    assert "Resize & Enhance là utility Web-native riêng" in PORTAL
    # List, detail and version DTOs intentionally expose bounded excerpts;
    # use their actual response keys instead of rendering a blank card.
    assert "item.creative_brief_excerpt || item.brief_excerpt" in PORTAL
    assert "version.creative_brief_excerpt || version.brief_excerpt" in PORTAL


def test_image_studio_private_routes_and_api_are_not_in_pwa_shell_cache() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/image-studio" in SERVICE_WORKER
    assert "private `/image-studio/*` routes" in SERVICE_WORKER
    assert "/api/v1/image-studio" not in shell
    assert '"/image-studio"' not in shell
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in SERVICE_WORKER
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER

    for selector in (
        ".portal-image-studio-intro",
        ".portal-image-artboard-grid",
        ".portal-image-direction-card",
        ".portal-image-studio-estimate-grid",
        ".portal-image-studio-guard-list",
        ".portal-image-studio-intro, .portal-image-studio-detail-summary, .portal-image-studio-layout, .portal-image-studio-detail-grid, .portal-image-studio-history-grid { grid-template-columns: 1fr; }",
        ".portal-image-artboard-grid, .portal-image-direction-grid { grid-template-columns: 1fr; }",
        ".portal-image-studio-intro dl, .portal-image-studio-detail-summary dl, .portal-image-studio-estimate-grid, .portal-image-studio-guard-list { grid-template-columns: 1fr; }",
        ".portal-image-direction-form .portal-fields { grid-template-columns: 1fr; }",
        ".portal-image-version-list > article { align-items: flex-start; flex-direction: column; }",
    ):
        assert selector in CSS


def test_image_studio_artboard_and_reference_reads_ignore_stale_responses() -> None:
    for epoch in ("imageStudioSessionEpoch", "imageStudioHydrationEpoch", "imageStudioDetailHydrationEpoch"):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION
    assert "imageStudioReferenceHydrationEpoch.projects += 1;" in INTEGRATION
    assert "imageStudioReferenceHydrationEpoch.image_assets += 1;" in INTEGRATION

    helper_start = INTEGRATION.index("function imageStudioRequestIsCurrent")
    helper_end = INTEGRATION.index("function isNativeImagePromptComposerPath", helper_start)
    helper = INTEGRATION[helper_start:helper_end]
    for requirement in (
        "sessionEpoch === imageStudioSessionEpoch",
        "currentPortalPath() === expectedPath",
        "isNativeImageStudioPath(expectedPath)",
        "base().imageStudioEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper

    list_start = INTEGRATION.index("async function hydrateImageStudio(")
    references_start = INTEGRATION.index("async function hydrateImageStudioReferences", list_start)
    detail_start = INTEGRATION.index("async function hydrateImageArtboard", references_start)
    listing = INTEGRATION[list_start:references_start]
    references = INTEGRATION[references_start:detail_start]
    detail = INTEGRATION[detail_start:INTEGRATION.index("const CHAT_WORKSPACE_LIST_LIMIT", detail_start)]
    assert "const sessionEpoch = imageStudioSessionEpoch;" in listing
    assert "imageStudioRequestIsCurrent(epoch, imageStudioHydrationEpoch, sessionEpoch, expectedPath)" in listing
    assert "imageStudioRequestIsCurrent(epoch, imageStudioReferenceHydrationEpoch[normalizedKind], sessionEpoch, expectedPath)" in references
    assert "const requestEpoch = ++imageStudioDetailHydrationEpoch;" in detail
    assert "imageStudioRequestIsCurrent(requestEpoch, imageStudioDetailHydrationEpoch, sessionEpoch, route)" in detail
