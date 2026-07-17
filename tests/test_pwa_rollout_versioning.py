"""Focused contracts for safe public-shell PWA rollouts."""

from __future__ import annotations

import json
from pathlib import Path
import re

import copyfast_pages


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _clear_build_environment(monkeypatch) -> None:
    for key in copyfast_pages._PORTAL_BUILD_ID_ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_public_build_id_prefers_safe_explicit_then_railway_identifiers(monkeypatch) -> None:
    _clear_build_environment(monkeypatch)
    monkeypatch.setenv("APP_BUILD_ID", "release-2026.07.16")
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "a" * 40)
    assert copyfast_pages._portal_build_id() == "release-2026.07.16"

    # The public shell must not echo an arbitrary environment string into an
    # HTML/script URL. It can safely fall through to Railway's opaque commit.
    monkeypatch.setenv("APP_BUILD_ID", "<release>&/not-a-cache-key")
    assert copyfast_pages._portal_build_id() == "a" * 40

    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    monkeypatch.setenv("RAILWAY_DEPLOYMENT_ID", "railway_deploy-42")
    assert copyfast_pages._portal_build_id() == "railway_deploy-42"


def test_local_build_fallback_is_deterministic_and_bounded(monkeypatch) -> None:
    _clear_build_environment(monkeypatch)
    first = copyfast_pages._portal_build_id()
    second = copyfast_pages._portal_build_id()
    assert first == second
    assert re.fullmatch(r"local-[0-9a-f]{20}", first)
    assert copyfast_pages._safe_portal_build_id("leading space") is None
    assert copyfast_pages._safe_portal_build_id("../not-a-build") is None
    assert copyfast_pages._safe_portal_build_id("safe_build.42") == "safe_build.42"


def test_rendered_shell_shares_one_public_build_id_with_assets(monkeypatch) -> None:
    _clear_build_environment(monkeypatch)
    monkeypatch.setenv("APP_BUILD_ID", "pwa-rollout-42")
    response = copyfast_pages.render_portal("/welcome")
    body = response.body.decode("utf-8")
    bootstrap = re.search(
        r'<script id="portal-bootstrap" type="application/json">(.*?)</script>',
        body,
        flags=re.DOTALL,
    )
    assert bootstrap is not None
    payload = json.loads(bootstrap.group(1))
    assert payload["buildId"] == "pwa-rollout-42"
    assert "/static/portal/portal.js?v=pwa-rollout-42" in body
    assert "/static/portal/integration.js?v=pwa-rollout-42" in body
    assert "/static/portal/portal.css?v=pwa-rollout-42" in body


def test_worker_uses_only_validated_build_id_and_a_scoped_cache_generation() -> None:
    assert 'const BUILD_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/;' in WORKER
    assert 'new URL(self.location.href).searchParams.get("build")' in WORKER
    assert "BUILD_ID_PATTERN.test(candidate) ? candidate : LOCAL_BUILD_ID" in WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in WORKER
    assert "key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME" in WORKER
    assert "const SHELL_CACHE_REQUESTS = Object.freeze(" in WORKER
    assert 'new Request(`${path}?build=${encodeURIComponent(BUILD_ID)}`, { cache: "reload" })' in WORKER
    assert "return caches.open(CACHE_NAME).then((cache) => cache.match(path, { ignoreSearch: true }));" in WORKER


def test_registration_carries_encoded_public_build_id_without_forcing_takeover() -> None:
    assert "const PUBLIC_BUILD_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/;" in PORTAL
    assert "window.__TOAN_AAS_PORTAL_BUILD_ID__ = publicBuildId(" in PORTAL
    assert "const PWA_BUILD_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/;" in INTEGRATION
    assert 'const serviceWorkerUrl = `/service-worker.js?build=${encodeURIComponent(pwaBuildId(context))}`;' in INTEGRATION
    assert 'navigator.serviceWorker.register(serviceWorkerUrl, { scope: "/" })' in INTEGRATION
    assert "skipWaiting" not in WORKER
    assert "clients.claim" not in WORKER
    assert "location.reload" not in PORTAL
    assert "location.reload" not in INTEGRATION


def test_explicit_server_pwa_disable_retires_only_this_root_worker_and_shell_caches() -> None:
    """An API outage cannot remove another same-origin application's PWA."""

    assert "function pwaExplicitlyDisabled(statusResponse)" in INTEGRATION
    assert "statusResponse.ok === true" in INTEGRATION
    assert "statusResponse.data.flags.pwa_enabled === false" in INTEGRATION
    assert "async function retirePortalPwaIfExplicitlyDisabled(statusResponse)" in INTEGRATION
    assert "if (!pwaExplicitlyDisabled(statusResponse)) return;" in INTEGRATION
    assert "void retirePortalPwaIfExplicitlyDisabled(statusResponse);" in INTEGRATION
    assert 'const PORTAL_SHELL_CACHE_PREFIX = "toan-aas-portal-shell-";' in INTEGRATION
    assert 'const PORTAL_ROOT_WORKER_PATH = "/service-worker.js";' in INTEGRATION
    assert "function isPortalRootWorkerRegistration(registration)" in INTEGRATION
    assert 'const rootScope = new URL("/", window.location.origin).href;' in INTEGRATION
    assert "registration.scope !== rootScope" in INTEGRATION
    assert "workerUrl.pathname === PORTAL_ROOT_WORKER_PATH" in INTEGRATION

    retirement = INTEGRATION.split("async function retirePortalPwaIfExplicitlyDisabled(statusResponse)", 1)[1].split(
        "function base()", 1
    )[0]
    assert "navigator.serviceWorker.getRegistrations" in retirement
    assert ".filter(isPortalRootWorkerRegistration)" in retirement
    assert ".map((registration) => registration.unregister())" in retirement
    assert ".filter((name) => typeof name === \"string\" && name.startsWith(PORTAL_SHELL_CACHE_PREFIX))" in retirement
    assert ".map((name) => cacheStorage.delete(name))" in retirement
    assert "Promise.allSettled" in retirement
    assert "location.reload" not in retirement
    assert "caches.delete" not in retirement
    # The worker shares the same narrow prefix, so emergency cleanup cannot
    # sweep a cache owned by another application on app.toanaas.vn.
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in WORKER


def test_worker_retains_the_private_cache_boundary() -> None:
    shell = WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/api/' not in shell
    assert '"/dashboard"' not in shell
    assert '"/wallet"' not in shell
    assert '"/admin"' not in shell
    assert '"/" + "api/v1/operations"' in private_paths
    assert '"/" + "api/v1/inbox"' in private_paths
    assert '"/admin"' in private_paths
    assert '"/workboard"' in private_paths
    assert "cache.put(" not in WORKER
    assert "localStorage" not in WORKER
    assert "sessionStorage" not in WORKER
