"""Static safety contracts for the Web-native Creative Content Studio.

These checks protect the important boundary: this is a signed-account
authoring workspace with versioned text, not a disguised Bot, payment,
provider, job, publish or PWA-private-data surface.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_content_studio.py").read_text(encoding="utf-8")


def test_content_studio_is_a_real_private_workspace_route() -> None:
    assert 'customerPage("/content-studio", "Creative Content Studio"' in PORTAL
    assert 'customerPage("/content-studio/new", "Content Brief mới"' in PORTAL
    assert 'path: "/content-studio/:id"' in PORTAL
    assert "function renderContentStudio(page, context)" in PORTAL
    assert "function renderContentStudioDetail(page, context)" in PORTAL
    assert 'case "content-studio": return renderContentStudio(page, context);' in PORTAL
    assert 'case "content-studio-detail": return renderContentStudioDetail(page, context);' in PORTAL
    assert "CONTENT_STUDIO_PATH" in PAGES
    assert "CONTENT_STUDIO_PATH.fullmatch(normalized)" in PAGES
    assert 'botCompanionPage("/content-studio"' not in PORTAL


def test_content_studio_hydrates_and_mutates_only_via_owner_scoped_api() -> None:
    for helper in (
        "contentBriefIdFromPath",
        "isNativeContentStudioPath",
        "contentStudioSafetyError",
        "contentBriefPayload",
        "contentVariantPayload",
        "contentStudioFilterPayload",
        "contentStudioListOffset",
        "contentStudioListPath",
        "contentStudioListingProjection",
        "hydrateContentStudio",
        "hydrateContentBrief",
        "hydrateContentVariantHistory",
        "contentStudioMutation",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    for endpoint in (
        'api("/content-studio/summary")',
        'api("/content-studio/policy")',
        'api("/content-studio/events?limit=50")',
        'api("/content-studio/references")',
        'path: "/content-studio/briefs"',
        'api("/content-studio/briefs/" + encodeURIComponent(String(briefId)))',
    ):
        assert endpoint in INTEGRATION

    for capability in (
        '"content-studio-view": Boolean(account && contentStudioEnabled)',
        '"content-studio-page": Boolean(account && contentStudioEnabled)',
        '"content-studio-create": Boolean(account && me.csrf_token && contentStudioEnabled)',
        '"content-studio-variant-create": Boolean(account && me.csrf_token && contentStudioEnabled)',
        '"content-studio-variant-select": Boolean(account && me.csrf_token && contentStudioEnabled)',
    ):
        assert capability in INTEGRATION

    assert "WEB_CONTENT_STUDIO_BODY_TOO_LARGE" in APP
    assert "CONTENT_STUDIO_BODY_MAX_BYTES = 128 * 1024" in APP
    assert '"content-studio-write" if content_studio_write' in APP
    assert '"content-studio-read" if content_studio_read' in APP
    assert "WEBAPP_CONTENT_STUDIO_ENABLED" in ROUTER

    start = INTEGRATION.index('if (action === "content-studio-filter"')
    end = INTEGRATION.index('if (action === "video-prompt-plan")')
    actions = INTEGRATION[start:end].lower()
    for forbidden in ("bridgeavailable", "payos", "wallet", "telegram", "/jobs", "/payments", "publish"):
        assert forbidden not in actions
    for action in (
        "content-brief-create",
        "content-brief-update",
        "content-brief-archive",
        "content-brief-restore",
        "content-brief-duplicate",
        "content-brief-restore-version",
        "content-brief-compose",
        "content-variant-create",
        "content-variant-update",
        "content-variant-archive",
        "content-variant-restore",
        "content-variant-duplicate",
        "content-variant-restore-version",
        "content-variant-select",
        "content-variant-history",
        "content-studio-page",
    ):
        assert action in actions
    assert "contentstudiomutation({" in actions
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "local_deterministic_draft_only" in actions
    assert "provider_called !== false" in actions
    assert "charge_started !== false" in actions


def test_content_studio_keeps_private_authoring_out_of_bot_and_pwa_paths() -> None:
    assert "from copyfast_bridge import" not in ROUTER
    assert "import requests" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "payos" not in ROUTER.lower()
    assert "source_url" not in ROUTER
    assert "local_deterministic_draft_only" in ROUTER
    assert "provider_called\": False" in ROUTER
    assert "charge_started\": False" in ROUTER

    assert "/api/v1/content-studio" in SERVICE_WORKER
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/content-studio" not in shell
    assert '"/content-studio"' not in shell
    # Private workspace additions may intentionally invalidate the public
    # shell cache, but the cache name must remain versioned while private
    # API/routes stay outside the shell checks above.
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v' in SERVICE_WORKER
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER

    for selector in (
        ".portal-content-studio-intro",
        ".portal-content-studio-grid",
        ".portal-content-studio-pagination",
        ".portal-content-variant-card",
        ".portal-content-variant-history",
        ".portal-content-studio-grid, .portal-content-variant-grid { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS

    # Rendered private fields must pass through the portal's escaping helper,
    # never raw interpolation.
    detail_start = PORTAL.index("function renderContentStudioDetail")
    detail_end = PORTAL.index("function renderStudioDocumentEditor")
    detail = PORTAL[detail_start:detail_end]
    assert "safeText" in detail
    assert "data-content-brief-id" in detail
    assert "data-content-variant-id" in detail


def test_content_studio_filter_and_pagination_remain_ephemeral_and_owner_scoped() -> None:
    assert 'data-portal-no-transient data-portal-action="content-studio-filter"' in PORTAL
    assert '"content-studio-page"' in PORTAL
    assert '__contentStudioOffset: source.getAttribute("data-content-studio-offset") || ""' in PORTAL
    assert "function contentStudioListing(context)" in PORTAL
    assert "function renderContentStudioPagination(listing)" in PORTAL


def test_content_studio_private_reads_ignore_stale_session_route_and_variant_responses() -> None:
    """Brief text and references must not reappear after a late response."""

    for epoch in (
        "contentStudioSessionEpoch",
        "contentStudioListHydrationEpoch",
        "contentStudioDetailHydrationEpoch",
        "contentStudioVariantHistoryHydrationEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    helper_start = INTEGRATION.index("function contentStudioRequestIsCurrent")
    helper_end = INTEGRATION.index("async function hydrateContentStudio", helper_start)
    helper = INTEGRATION[helper_start:helper_end]
    for requirement in (
        "sessionEpoch === contentStudioSessionEpoch",
        "currentPortalPath() === expectedPath",
        "isNativeContentStudioPath(expectedPath)",
        "base().contentStudioEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper

    list_start = INTEGRATION.index("async function hydrateContentStudio")
    detail_start = INTEGRATION.index("async function hydrateContentBrief", list_start)
    list_read = INTEGRATION[list_start:detail_start]
    detail_end = INTEGRATION.index("const CHANNEL_STRATEGY_LIST_LIMIT", detail_start)
    detail_read = INTEGRATION[detail_start:detail_end]
    variant_start = INTEGRATION.index("async function hydrateContentVariantHistory")
    variant_end = INTEGRATION.index("function voiceStudioPolicyIsSafe", variant_start)
    variant_read = INTEGRATION[variant_start:variant_end]

    assert "const requestEpoch = ++contentStudioListHydrationEpoch;" in list_read
    assert "if (!contentStudioRequestIsCurrent(requestEpoch, contentStudioListHydrationEpoch, sessionEpoch, path)) return { stale: true };" in list_read
    assert "const requestEpoch = ++contentStudioDetailHydrationEpoch;" in detail_read
    assert "if (currentPortalPath() !== route) return null;" in detail_read
    assert "if (!contentStudioRequestIsCurrent(requestEpoch, contentStudioDetailHydrationEpoch, sessionEpoch, route)) return null;" in detail_read
    assert "const requestEpoch = ++contentStudioVariantHistoryHydrationEpoch;" in variant_read
    assert "if (!contentStudioRequestIsCurrent(requestEpoch, contentStudioVariantHistoryHydrationEpoch, sessionEpoch, route)) return null;" in variant_read
