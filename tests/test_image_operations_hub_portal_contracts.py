"""Focused contracts for the app-first Image Operations Hub projection.

The hub is a second visual route for the existing private Image Creative
Studio authoring model.  It intentionally does not become an image provider,
an operation executor, a transport channel, or a duplicate persistence/API
authority.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi import HTTPException

import copyfast_pages


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
IMGTOOL_DISPOSITION = (ROOT / "docs" / "migration" / "IMGTOOL_WEB_NATIVE_DISPOSITION.md").read_text(encoding="utf-8")


IMAGE_HUB_ARTBOARD_ID = "4f8c8d27-8a65-4a26-91da-8a437a6d1d73"


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def _shell_payload(path: str, locale: str = "en") -> dict[str, object]:
    response = copyfast_pages.render_portal(path, interface_locale=locale)
    body = response.body.decode("utf-8")
    match = re.search(
        r'<script id="portal-bootstrap" type="application/json">(.*?)</script>',
        body,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_image_hub_has_strict_server_list_new_and_uuid_detail_routes() -> None:
    """The visual alias must not silently turn arbitrary child paths into a shell."""

    assert "IMAGE_HUB_PATH" in PAGES
    assert "IMAGE_HUB_PATH.fullmatch(normalized)" in PAGES
    assert '"/image-hub/new"' in PAGES

    list_payload = _shell_payload("/image-hub")
    new_payload = _shell_payload("/image-hub/new")
    detail_payload = _shell_payload(f"/image-hub/{IMAGE_HUB_ARTBOARD_ID}")
    assert list_payload["path"] == "/image-hub"
    assert list_payload["title"] == "Image Operations Hub · TOAN AAS"
    assert new_payload["path"] == "/image-hub/new"
    assert new_payload["title"] == "New Image Direction · TOAN AAS"
    assert detail_payload["path"] == f"/image-hub/{IMAGE_HUB_ARTBOARD_ID}"
    assert detail_payload["title"] == "Image Operations Board · TOAN AAS"
    assert copyfast_pages._title_for(f"/image-hub/{IMAGE_HUB_ARTBOARD_ID}") == "Image Operations Hub"

    for invalid in (
        "/image-hub/not-a-uuid",
        "/image-hub/new/extra",
        f"/image-hub/{IMAGE_HUB_ARTBOARD_ID}/history",
    ):
        with pytest.raises(HTTPException) as error:
            copyfast_pages.render_portal(invalid)
        assert error.value.status_code == 404


def test_image_hub_registers_a_visual_alias_for_list_new_and_detail() -> None:
    assert 'WebFeature("image_hub", "Image Operations Hub", "image", "/image-hub"' in REGISTRY
    assert 'customerPage("/image-hub", "Image Operations Hub"' in PORTAL
    assert 'customerPage("/image-hub/new", "Image Direction mới"' in PORTAL
    assert 'path: "/image-hub/:id"' in PORTAL
    assert 'case "image-hub": return renderImageStudio(page, context);' in PORTAL
    assert 'case "image-hub-detail": return renderImageStudioDetail(page, context);' in PORTAL
    assert 'botCompanionPage("/image-hub"' not in PORTAL


def test_image_hub_reuses_existing_image_studio_authority_without_a_second_backend() -> None:
    """A route alias must keep all signed owner reads/writes on Image Studio."""

    alias_helpers = _between(INTEGRATION, "function imageStudioVisualRoot", "function imageStudioRequestIsCurrent")
    for requirement in (
        "function imageStudioArtboardRoute(artboardId, path)",
        "function isImageStudioListViewPath(path)",
        '"/image-hub", "/image-hub/new"',
        "^\\/(?:image-studio|image-hub)\\/([^/]+)$",
    ):
        assert requirement in alias_helpers

    for endpoint in (
        'api("/image-studio/summary")',
        'api("/image-studio/policy")',
        'api("/image-studio/events?limit=50")',
        'api("/image-studio/artboards/" + encodeURIComponent(String(artboardId)))',
    ):
        assert endpoint in INTEGRATION
    assert 'api("/image-hub' not in INTEGRATION
    assert "/api/v1/image-hub" not in INTEGRATION
    assert "copyfast_image_hub" not in (ROOT / "app.py").read_text(encoding="utf-8")
    assert not (ROOT / "copyfast_image_hub.py").exists()
    assert "web_image_hub" not in (ROOT / "copyfast_db.py").read_text(encoding="utf-8")

    action_start = INTEGRATION.index('if (action === "image-artboard-create")')
    action_end = INTEGRATION.index('if (action === "image-artboard-update")', action_start)
    create_action = INTEGRATION[action_start:action_end]
    assert re.search(r"window\.location\.assign\([^;]*(?:route|image-hub)[^;]*\);", create_action)
    assert "window.location.assign(`/image-studio/${encodeURIComponent(artboardId)}`)" not in create_action

    refresh_action = _between(
        INTEGRATION,
        'if (action === "image-studio-refresh")',
        'if (action === "subtitle-studio-refresh")',
    )
    assert "await hydrateImageArtboard(artboardId, route);" in refresh_action


def test_image_hub_board_never_transfers_private_media_or_claims_provider_output() -> None:
    """Hub cards may link to fresh tools, never replay an artboard/asset into them."""

    hub_board = _between(PORTAL, "function renderImageHubOverview", "function renderImageStudio(")
    for fresh_route in (
        'href: "/image/prompt-composer"',
        'href: "/image/resize"',
        'href: "/image/edit"',
        'href: "/image/brand-overlay"',
        'href: "/asset-vault"',
    ):
        assert fresh_route in hub_board
    for forbidden in (
        "<img",
        "fetch(",
        "api(",
        "localstorage",
        "sessionstorage",
        "urlsearchparams",
        "window.location.search",
        "source_url",
        "download_url",
        "blob",
        "objecturl",
        "?artboard",
        "?asset",
        "provider",
        "payos",
        "wallet",
        "job",
        "telegram",
    ):
        assert forbidden not in hub_board.lower()

    # The alias helper may strip a query string defensively, but it must not
    # construct a browser query/state handoff for a private artboard.
    for forbidden in ("URLSearchParams", "localStorage", "sessionStorage", "window.location.search"):
        assert forbidden not in alias_helpers_casefold_safe(INTEGRATION)


def alias_helpers_casefold_safe(source: str) -> str:
    """Return just alias routing helpers, not the existing API query builders."""

    return _between(source, "function imageStudioVisualRoot", "function imageStudioRequestIsCurrent")


def test_image_hub_private_pwa_scope_and_phone_touch_targets() -> None:
    shell = _between(WORKER, "const SHELL = Object.freeze([", "]);" )
    private_paths = _between(WORKER, "const PRIVATE_PATH_PREFIXES = Object.freeze([", "]);" )
    public_paths = _between(WORKER, "const PUBLIC_NAVIGATION_PATHS = Object.freeze([", "]);" )
    assert '"/image-hub"' in private_paths
    assert '"/image-hub"' not in shell
    assert '"/image-hub"' not in public_paths
    assert "SHELL_PATHS.has(url.pathname)" in WORKER

    phone_start = CSS.rfind("@media (max-width: 700px) {")
    assert phone_start >= 0
    phone_rules = CSS[phone_start:]
    for selector in (
        ".portal-image-hub .portal-button",
        ".portal-image-hub-detail .portal-button",
        ".portal-image-hub .portal-input",
        ".portal-image-hub-detail .portal-input",
        ".portal-image-hub .portal-select",
        ".portal-image-hub-detail .portal-select",
    ):
        assert selector in phone_rules
    assert "min-height: 44px;" in phone_rules
    assert '"/image-hub"' in _between(PORTAL, 'function isMobileNavCurrent', 'function renderMobileNav')
    assert 'path.startsWith("/image-hub/")' in _between(PORTAL, 'function isMobileNavCurrent', 'function renderMobileNav')


def test_imgtool_remains_fail_closed_and_does_not_rewrite_the_frozen_menu_map() -> None:
    """A new Hub route must not silently claim a Telegram callback mapping."""

    assert "`menu|hint_image_tools`, `menu|guide_image_ai` | `/image-studio` (current frozen navigation catalog)" in IMGTOOL_DISPOSITION
    assert "Image Hub is a separate customer-selected visual route" in IMGTOOL_DISPOSITION
    assert "`imgtool|*` is a frozen Telegram transport namespace" in IMGTOOL_DISPOSITION
    assert "`IMGTOOL_SOURCE_REVIEW_REQUIRED`" in IMGTOOL_DISPOSITION
    assert "never converts an existing raw `imgtool|*` callback into a browser" in IMGTOOL_DISPOSITION
