"""Portal contracts for the signed, navigation-only Web Guide Center."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start):source.index(end, source.index(start))]


def test_guide_center_is_a_signed_read_only_customer_surface() -> None:
    assert 'WebFeature("guides", "Guide Center", "account", "/guides"' in REGISTRY
    assert 'customerPage("/guides", "Guide Center"' in PORTAL
    assert 'type: "guide-center", layout: "guide-center", fields: [], action: "none", status: "read_only"' in PORTAL
    assert 'case "guide-center": return renderGuideCenter(page, context);' in PORTAL
    assert 'if (path === "/guides") return uiText("page.guideCenter.title", fallback);' in PORTAL
    assert 'if (path === "/guides") return uiText("page.guideCenter.description", fallback);' in PORTAL


def test_guide_cards_only_follow_the_server_validated_route_catalog() -> None:
    renderer = _between(PORTAL, "function renderGuideCenterTopic", "function guideCenterShellText")
    normalizer = _between(INTEGRATION, "const GUIDE_CENTER_GROUP_IDS", "const FREE_PROMPT_GALLERY_BOUNDARY_FIELDS")

    assert 'data-guide-center-item' in renderer
    assert 'href="${safeText(String(topic.route || ""))}"' in renderer
    assert "data-portal-action" not in renderer
    assert "fetch(" not in renderer
    assert "GUIDE_CENTER_ROUTE_ALLOWLIST.has(topic.route)" in normalizer
    assert "GUIDE_CENTER_TOPIC_IDS.has(topicId)" in normalizer
    assert 'boundaries.execution === "web_native_guide_center"' in normalizer
    assert "GUIDE_CENTER_BOUNDARY_FIELDS.every((field) => boundaries[field] === false)" in normalizer


def test_guide_hydration_fails_closed_and_is_never_a_bridge_fallback() -> None:
    guide_hydration = _between(INTEGRATION, "function guideCenterRequestIsCurrent", "async function hydratePromptLibrary")

    assert 'api("/guides/catalog")' in guide_hydration
    assert "guideCenterCatalogIsSafe(catalog)" in guide_hydration
    assert "guideCenterHydrationEpoch" in guide_hydration
    assert "guideCenterSessionEpoch" in guide_hydration
    assert 'guideCenterReadState: "ready"' in guide_hydration
    assert 'pageStates: { ...(base().pageStates || {}), "/guides": "read_only" }' in guide_hydration
    assert 'guideCenterCatalog: {}' in guide_hydration
    assert 'guideCenterReadState: "failed"' in guide_hydration
    assert "!isNativeGuideCenterPath(currentPath)" in INTEGRATION
    assert 'if (isNativeWorkspaceMenuPath(path) || isNativeGuideCenterPath(path)' in INTEGRATION


def test_guide_center_has_localized_accessible_and_private_shell_contracts() -> None:
    for key in (
        "nav.guideCenter",
        "page.guideCenter.title",
        "page.guideCenter.description",
        "guideCenter.loadingTitle",
        "guideCenter.guardedTitle",
        "guideCenter.failedTitle",
    ):
        assert I18N.count(f'"{key}":') == 3

    assert '"/" + "api/v1/guides"' in SERVICE_WORKER
    assert '"/guides"' in SERVICE_WORKER
    for selector in (
        ".portal-guide-center",
        ".portal-guide-center-search",
        ".portal-guide-center-grid",
        ".portal-guide-center-topic",
        ".portal-guide-center-boundary",
    ):
        assert selector in CSS
    assert "@media (max-width: 980px)" in CSS
    assert "@media (max-width: 700px)" in CSS
    assert "prefers-reduced-motion" in CSS
