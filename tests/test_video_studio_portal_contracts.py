"""Static contracts for the Web-native Video Production Studio portal.

The route family deliberately sits beside, not inside, the legacy `/video/*`
feature pages.  These checks keep plan/scene authoring private and make future
UI edits fail closed instead of quietly falling back to a generic video flow.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_video_studio_is_a_native_route_not_a_legacy_video_alias() -> None:
    assert 'customerPage("/video-studio"' in PORTAL
    assert 'customerPage("/video-studio/new"' in PORTAL
    assert 'path: "/video-studio/:id"' in PORTAL
    assert "function renderVideoStudio(" in PORTAL
    assert "function renderVideoStudioDetail(" in PORTAL
    assert 'case "video-studio": return renderVideoStudio(page, context);' in PORTAL
    assert 'case "video-studio-detail": return renderVideoStudioDetail(page, context);' in PORTAL
    assert "VIDEO_STUDIO_PATH" in PAGES
    assert "VIDEO_STUDIO_PATH.fullmatch(normalized)" in PAGES
    assert 'botCompanionPage("/video-studio"' not in PORTAL

    # The historical video family must remain exact. A hyphenated native
    # route cannot inherit navigation or generic feature hydration from it.
    assert 'if (linkPath === "/video/create") return path === "/video" || path.startsWith("/video/");' in PORTAL
    assert 'const canonicalBotVideoRoute = path === "/video" || path.startsWith("/video/");' in INTEGRATION
    assert "!isNativeVideoStudioPath(currentPath)" in INTEGRATION
    assert "isNativeContentStudioPath(path) || isNativeVoiceStudioPath(path) || isNativeVideoStudioPath(path)" in INTEGRATION

    # The global delegated action must keep optimistic revisions and target
    # IDs server-verifiable rather than deriving them in browser state.
    for field in (
        'videoPlanId: source.getAttribute("data-video-plan-id") || ""',
        'videoPlanRevision: source.getAttribute("data-video-plan-revision") || ""',
        'videoPlanVersion: source.getAttribute("data-video-plan-version") || ""',
        'videoPlanState: source.getAttribute("data-video-plan-state") || ""',
        'videoSceneId: source.getAttribute("data-video-scene-id") || ""',
        'videoSceneRevision: source.getAttribute("data-video-scene-revision") || ""',
        'videoSceneVersion: source.getAttribute("data-video-scene-version") || ""',
        'videoSceneDirection: source.getAttribute("data-video-scene-direction") || ""',
    ):
        assert field in PORTAL


def test_video_studio_uses_only_its_private_web_api_and_safe_mutations() -> None:
    for helper in (
        "videoPlanIdFromPath",
        "isNativeVideoStudioPath",
        "videoStudioSafetyError",
        "videoPlanPayload",
        "videoScenePayload",
        "videoStudioBoundaryIsSafe",
        "hydrateVideoStudio",
        "hydrateVideoPlan",
        "videoStudioMutation",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    for endpoint in (
        'api("/video-studio/summary")',
        'api("/video-studio/plans")',
        'api("/video-studio/events?limit=50")',
        'api("/video-studio/references")',
        'api("/video-studio/plans/" + encodeURIComponent(String(planId)))',
        '"/video-studio/plans/" + encodeURIComponent(String(planId)) + "/estimate"',
        'path: "/video-studio/plans"',
    ):
        assert endpoint in INTEGRATION

    for capability in (
        '"video-studio-view": Boolean(account && videoStudioEnabled)',
        '"video-plan-create": Boolean(account && me.csrf_token && videoStudioEnabled)',
        '"video-scene-create": Boolean(account && me.csrf_token && videoStudioEnabled)',
        '"video-scene-reorder": Boolean(account && me.csrf_token && videoStudioEnabled)',
    ):
        assert capability in INTEGRATION

    start = INTEGRATION.index('if (action === "video-studio-refresh")')
    end = INTEGRATION.index('if (action === "voice-studio-filter"')
    actions = INTEGRATION[start:end].lower()
    for forbidden in ("bridgeavailable", "core bridge", "payos", "/payments", "/jobs", "provider", "renderer", "preview", "delivery"):
        assert forbidden not in actions
    for action in (
        "video-studio-refresh",
        "video-plan-create",
        "video-plan-update",
        "video-plan-state",
        "video-plan-restore-version",
        "video-scene-create",
        "video-scene-update",
        "video-scene-archive",
        "video-scene-restore",
        "video-scene-restore-version",
        "video-scene-reorder",
    ):
        assert action in actions
    assert "videostudiomutation({" in actions
    assert "target_revision: targetrevision" in actions
    assert "scene_ids: sceneids" in actions

    # Idempotency is generated in one narrow mutation helper, and the
    # boundary flags must be explicit before portal state is accepted.
    assert "idempotency_key: submission.key" in INTEGRATION
    assert 'boundary.execution === "authoring_only"' in INTEGRATION
    assert "boundary.provider_called === false" in INTEGRATION
    assert "boundary.video_created === false" in INTEGRATION
    assert "videoStudioBoundaryIsSafe(summary)" in INTEGRATION
    assert "videoStudioBoundaryIsSafe(data)" in INTEGRATION


def test_video_studio_has_no_private_pwa_cache_or_fake_media_surface() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/video-studio" in SERVICE_WORKER
    assert "/api/v1/video-studio" not in shell
    assert '"/video-studio"' not in shell
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v10"' in SERVICE_WORKER
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER

    for selector in (
        ".portal-video-studio-intro",
        ".portal-video-plan-grid",
        ".portal-video-scene-card",
        ".portal-video-runtime-grid",
        ".portal-video-studio-guard-list",
        ".portal-video-plan-grid, .portal-video-scene-grid { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS

    # Archive must close both child authoring and runtime estimate affordances;
    # self-review is metadata, not a claim that a media result exists.
    assert 'const writable = ["draft", "review"].includes(planState);' in PORTAL
    assert 'const estimateMarkup = planState === "archived"' in PORTAL
    assert "Estimate đã được khóa" in PORTAL
    assert "self-review only" not in PORTAL.lower()  # no generic status alias
    assert "Không có upload, renderer, player, URL media, tệp hoặc delivery" in PORTAL


def test_video_scene_order_uses_active_scene_position_not_raw_list_index() -> None:
    # Archived scenes can remain in history between active scenes. The render
    # index must therefore be derived from the active ordered sequence that
    # the reorder endpoint receives, rather than from the raw card list.
    assert "let activeSceneOrder = 0;" in PORTAL
    assert 'const order = active ? activeSceneOrder++ : -1;' in PORTAL
    assert "renderVideoSceneCard(scene, plan, context, route, order, activeScenes.length)" in PORTAL
    assert 'const displayOrder = active && Number.isInteger(order) && order >= 0' in PORTAL
