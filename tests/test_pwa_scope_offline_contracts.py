"""Focused contracts for the root-scoped, public-only offline PWA policy."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
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
    assert 'const canOfferPwaInstall = context.pwaEnabled === true && context.session.authenticated === true;' in PORTAL
    assert 'data-portal-install-app' in PORTAL
    assert 'type="button" aria-label="Cài TOAN AAS trên thiết bị" hidden data-portal-install-app' in PORTAL
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
