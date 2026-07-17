"""Static lifecycle boundaries for the public-shell service worker."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_activation_only_removes_obsolete_toan_aas_shell_caches() -> None:
    """Activation must not delete Cache Storage owned by another app on this origin."""
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in WORKER
    assert 'new URL(self.location.href).searchParams.get("build")' in WORKER
    assert "BUILD_ID_PATTERN.test(candidate) ? candidate : LOCAL_BUILD_ID" in WORKER

    activate = WORKER.split('self.addEventListener("activate", (event) => {', 1)[1].split(
        'function matchCurrentShell(path) {', 1
    )[0]

    assert "caches" in activate
    assert ".keys()" in activate
    assert "key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME" in activate
    assert "keys.filter((key) => key !== CACHE_NAME)" not in activate
    assert "clients.claim" not in activate


def test_install_waits_for_natural_activation_without_forced_client_takeover() -> None:
    """A new worker may cache a shell but must not interrupt a live workspace."""
    install = WORKER.split('self.addEventListener("install", (event) => {', 1)[1].split(
        'self.addEventListener("activate", (event) => {', 1
    )[0]

    assert "cache.addAll(SHELL_CACHE_REQUESTS)" in install
    assert "skipWaiting" not in install
    assert "clients.claim" not in WORKER
