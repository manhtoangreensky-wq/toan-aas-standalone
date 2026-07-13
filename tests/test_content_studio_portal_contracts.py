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
    end = INTEGRATION.index('if (action === "support-cases-filter")')
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
    # A private Workspace route changed the public shell bundle, so the
    # service worker intentionally moved from v9 to v10. Private API/routes
    # remain outside the shell cache checks above.
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v10"' in SERVICE_WORKER
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER

    for selector in (
        ".portal-content-studio-intro",
        ".portal-content-studio-grid",
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
