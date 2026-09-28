"""Focused contracts for the root-scoped, public-only offline PWA policy."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import struct
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "static" / "portal" / "manifest.webmanifest").read_text(encoding="utf-8"))
OFFLINE = (ROOT / "static" / "portal" / "offline.html").read_text(encoding="utf-8")


def _worker_client(tmp_path, monkeypatch) -> TestClient:
    # The route is public, but importing the real ASGI app still needs the
    # minimal configuration used by the app's authentication boundary.
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "pwa-contract.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "pwa-contract-session-secret")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "pwa-contract-callback-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "pwa-contract-callback-hmac")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    sys.modules.pop("app", None)
    return TestClient(importlib.import_module("app").app)


def test_root_worker_is_served_before_the_portal_catch_all_with_root_scope_headers(tmp_path, monkeypatch) -> None:
    route = APP.index('@app.get("/service-worker.js", include_in_schema=False)')
    catch_all = APP.index('@app.get("/{page_path:path}", include_in_schema=False)')
    assert route < catch_all
    assert "FileResponse" in APP
    assert '"Service-Worker-Allowed": "/"' in APP
    assert '"Cache-Control": "no-cache, no-store, max-age=0, must-revalidate"' in APP

    with _worker_client(tmp_path, monkeypatch) as client:
        response = client.get("/service-worker.js")
        icon = client.get("/static/portal/app-icon.svg")

    assert response.status_code == 200
    assert response.headers["service-worker-allowed"] == "/"
    assert "no-cache" in response.headers["cache-control"]
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-type"].startswith("application/javascript")
    assert "PUBLIC_NAVIGATION_PATHS" in response.text
    assert icon.status_code == 200
    assert icon.headers["content-type"].startswith("image/svg+xml")
    assert "TOAN AAS" in icon.text


def test_root_scoped_registration_and_manifest_have_a_stable_in_scope_identity() -> None:
    assert 'const serviceWorkerUrl = `/service-worker.js?build=${encodeURIComponent(pwaBuildId(context))}`;' in INTEGRATION
    assert 'navigator.serviceWorker.register(serviceWorkerUrl, { scope: "/" })' in INTEGRATION
    assert 'navigator.serviceWorker.register("/service-worker.js", { scope: "/" })' not in INTEGRATION
    assert 'navigator.serviceWorker.register("/static/portal/service-worker.js")' not in INTEGRATION
    assert MANIFEST["id"] == "/"
    assert MANIFEST["scope"] == "/"
    assert MANIFEST["start_url"] == "/dashboard"
    assert MANIFEST["start_url"].startswith(MANIFEST["scope"])
    assert MANIFEST["icons"]
    assert MANIFEST["lang"] == "vi"
    assert MANIFEST["display"] == "standalone"
    primary_icon = MANIFEST["icons"][0]
    assert primary_icon == {
        "src": "/static/portal/app-icon.svg",
        "sizes": "any",
        "type": "image/svg+xml",
        "purpose": "any maskable",
    }
    assert (ROOT / "static" / "portal" / "app-icon.svg").is_file()
    assert '"/static/portal/app-icon.svg"' in WORKER


def test_manifest_shortcuts_are_fixed_in_scope_navigation_without_private_data() -> None:
    shortcuts = MANIFEST["shortcuts"]
    assert [(item["name"], item["url"]) for item in shortcuts] == [
        ("Tổng quan", "/dashboard"),
        ("Project Center", "/projects"),
        ("Tạo workflow", "/features"),
    ]
    assert all(item["url"].startswith(MANIFEST["scope"]) for item in shortcuts)
    # Launch shortcuts deliberately point at normal routes. The worker's
    # public-only policy means they do not make a dashboard/project/catalogue
    # response available after logout or while offline.
    assert all(item["url"] not in WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0] for item in shortcuts)


def test_install_offer_uses_only_an_explicit_browser_prompt_for_a_signed_pwa_session() -> None:
    """Installing the shell never creates an automatic or account-data action."""
    assert "let pwaInstallPrompt = null;" in PORTAL
    assert 'const canOfferPwaInstall = Boolean(!adminSurface && context && context.pwaEnabled === true && context.session && context.session.authenticated === true);' in PORTAL
    assert 'data-portal-install-app' in PORTAL
    # The install control keeps a real accessible name, while its reviewed
    # label follows the interface locale rather than being fixed to Vietnamese.
    assert 'type="button" aria-label="${safeText(uiText("chrome.installApp", "Cài TOAN AAS trên thiết bị"))}" hidden data-portal-install-app' in PORTAL
    assert "function requestPwaInstall()" in PORTAL
    assert "await prompt.prompt();" in PORTAL
    assert "pwaInstallPrompt = null;" in PORTAL
    assert "function bindPwaInstallEvents()" in PORTAL
    install_request = PORTAL.split("async function requestPwaInstall()", 1)[1].split("function bindPwaInstallEvents()", 1)[0]
    install_events = PORTAL.split('function bindPwaInstallEvents() {', 1)[1].split('function openCommandPalette', 1)[0]
    assert 'window.addEventListener("beforeinstallprompt"' in install_events
    assert "event.preventDefault();" in install_events
    # The handler only captures the browser event.  Prompting happens later
    # from the button's explicit click path, never during page hydration.
    assert ".prompt()" not in install_events
    assert 'event.target.closest("[data-portal-install-app]")' in PORTAL
    assert ".portal-pwa-install-trigger" in PORTAL_CSS
    assert "localStorage" not in install_request
    assert "sessionStorage" not in install_request


def test_offline_policy_has_only_fixed_public_shell_and_a_public_navigation_fallback() -> None:
    shell = WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    public_navigation = WORKER.split("const PUBLIC_NAVIGATION_PATHS = Object.freeze([", 1)[1].split("]);", 1)[0]

    assert 'const OFFLINE_FALLBACK = "/static/portal/offline.html";' in WORKER
    assert "OFFLINE_FALLBACK" in shell
    assert '"/welcome"' in public_navigation
    assert '"/legal"' in public_navigation
    assert '"/privacy"' in public_navigation
    assert '"/login"' in public_navigation
    assert '"/register"' in public_navigation
    for forbidden_public_fallback in ("/", "/dashboard", "/wallet", "/account", "/admin", "/jobs"):
        assert f'"{forbidden_public_fallback}"' not in public_navigation

    assert 'if (request.mode === "navigate")' in WORKER
    assert "if (!PUBLIC_NAVIGATION_PATHS.includes(url.pathname)) return;" in WORKER
    assert "matchCurrentShell(OFFLINE_FALLBACK)" in WORKER
    assert "if (request.method !== \"GET\" || url.origin !== self.location.origin || isPrivatePath) return;" in WORKER
    assert "if (!SHELL_PATHS.has(url.pathname)) return;" in WORKER
    assert "cache.put(" not in WORKER
    assert "cache.addAll(SHELL_CACHE_REQUESTS)" in WORKER
    assert '"/api/' not in WORKER
    for private_path in (
        '"/" + "api/v1/content-studio"',
        '"/" + "api/v1/operations"',
        '"/content/publish-review"',
        '"/admin/operations"',
        '"/workboard"',
    ):
        assert private_path in private_paths


def test_offline_document_is_generic_and_contains_no_portal_bootstrap_or_private_data() -> None:
    assert "Bạn đang ngoại tuyến" in OFFLINE
    assert 'href="/welcome"' in OFFLINE
    for forbidden in (
        "portal-bootstrap",
        "integration.js",
        "portal.js",
        "localStorage",
        "sessionStorage",
        "csrf",
        "wallet",
        "payment",
        "admin",
        "api/",
    ):
        assert forbidden.lower() not in OFFLINE.lower()


def test_pwa_manifest_and_apple_touch_icons_truth(tmp_path, monkeypatch) -> None:
    """Every manifest icon and apple-touch-icon resolves to valid image bytes."""
    # manifest id/scope/start_url remain unchanged
    assert MANIFEST["id"] == "/"
    assert MANIFEST["scope"] == "/"
    assert MANIFEST["start_url"] == "/dashboard"

    # every /static/portal/ manifest icon path exists
    icons = MANIFEST.get("icons", [])
    assert len(icons) >= 4
    for icon in icons:
        src = icon.get("src", "")
        if src.startswith("/static/portal/"):
            rel_path = src.lstrip("/")
            file_path = ROOT / rel_path
            assert file_path.exists(), f"Manifest icon missing on disk: {src}"
            assert file_path.stat().st_size > 0, f"Manifest icon empty: {src}"

    # app-icon.svg remains valid
    svg_path = ROOT / "static" / "portal" / "app-icon.svg"
    assert svg_path.exists()
    svg_text = svg_path.read_text(encoding="utf-8")
    assert "<svg" in svg_text and "</svg>" in svg_text

    # icon-192.png has valid PNG signature and IHDR = 192x192
    p192 = ROOT / "static" / "portal" / "icon-192.png"
    assert p192.exists()
    d192 = p192.read_bytes()
    assert d192[:8] == b"\x89PNG\r\n\x1a\n", "icon-192.png missing PNG signature"
    assert d192[12:16] == b"IHDR", "icon-192.png missing IHDR chunk"
    w192, h192 = struct.unpack(">II", d192[16:24])
    assert (w192, h192) == (192, 192), f"icon-192.png wrong dimensions: {(w192, h192)}"

    # icon-512.png has valid PNG signature and IHDR = 512x512
    p512 = ROOT / "static" / "portal" / "icon-512.png"
    assert p512.exists()
    d512 = p512.read_bytes()
    assert d512[:8] == b"\x89PNG\r\n\x1a\n", "icon-512.png missing PNG signature"
    assert d512[12:16] == b"IHDR", "icon-512.png missing IHDR chunk"
    w512, h512 = struct.unpack(">II", d512[16:24])
    assert (w512, h512) == (512, 512), f"icon-512.png wrong dimensions: {(w512, h512)}"

    # both apple-touch-icon references resolve
    shell_html = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
    assert '<link rel="apple-touch-icon" sizes="192x192" href="/static/portal/icon-192.png">' in shell_html
    assert '<link rel="apple-touch-icon" sizes="512x512" href="/static/portal/icon-512.png">' in shell_html

    # TestClient GET icon-192.png => HTTP 200 + image/png
    # TestClient GET icon-512.png => HTTP 200 + image/png
    client = _worker_client(tmp_path, monkeypatch)
    resp192 = client.get("/static/portal/icon-192.png")
    assert resp192.status_code == 200
    assert "image/png" in resp192.headers.get("content-type", "")
    assert resp192.content[:8] == b"\x89PNG\r\n\x1a\n"

    resp512 = client.get("/static/portal/icon-512.png")
    assert resp512.status_code == 200
    assert "image/png" in resp512.headers.get("content-type", "")
    assert resp512.content[:8] == b"\x89PNG\r\n\x1a\n"
