"""Contracts for the public, Web-App-owned `/welcome` companion."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
MODULES = (
    "app",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_registry",
    "copyfast_api",
    "copyfast_pages",
    "copyfast_projects",
    "copyfast_assets",
    "copyfast_project_packages",
    "copyfast_document_operations",
    "copyfast_image_runtime",
    "copyfast_image_operations",
    "copyfast_memory",
    "copyfast_workspace_setup",
)


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def _rule(source: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{(?P<body>.*?)\}", source, flags=re.DOTALL)
    assert match, f"Missing CSS rule for {selector}"
    return match.group("body")


def _hex_literals_outside_root(source: str) -> list[str]:
    root_start = source.index(":root {")
    root_end = source.index("}", root_start)
    outside = source[:root_start] + source[root_end + 1 :]
    return re.findall(r"#[0-9a-fA-F]{3,8}\b", outside)


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "welcome-public-companion.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "welcome-public-companion-secret")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def test_welcome_allows_only_exact_reviewed_public_display_locales(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        default = client.get("/welcome")
        assert default.status_code == 200
        assert '<html lang="vi" dir="ltr" data-portal-locale="vi">' in default.text
        assert '"interfaceLocale": "vi"' in default.text

        for locale, html_lang in (("vi", "vi"), ("en", "en"), ("zh", "zh-CN")):
            response = client.get(f"/welcome?lang={locale}")
            assert response.status_code == 200
            assert f'<html lang="{html_lang}" dir="ltr" data-portal-locale="{locale}">' in response.text
            assert f'"interfaceLocale": "{locale}"' in response.text

        invalid = client.get("/welcome?lang=zh-TW")
        legacy = client.get("/welcome?locale=zh")
        assert 'data-portal-locale="vi"' in invalid.text
        assert 'data-portal-locale="vi"' in legacy.text


def test_public_landing_uses_i18n_real_routes_and_portal_svg_icons() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")
    for token in (
        'uiText(`landing.${key}`',
        'text("hero.title")',
        'text("cta.start")',
        "portalIcon(ICONS.arrowRight)",
        "portalIcon(ICONS.check)",
        'href="/register"',
        'href="/login"',
        'href="/legal"',
        'href="/privacy"',
        'href: "/welcome?lang=vi"',
        'href: "/welcome?lang=en"',
        'href: "/welcome?lang=zh"',
    ):
        assert token in landing
    for forbidden in ("fetch(", "api(", "payment", "provider", "wallet", "✦", "↗", "⌁"):
        assert forbidden not in landing


def test_landing_has_balanced_responsive_layout_and_accessible_controls() -> None:
    for selector in (
        ".portal-landing-locale-nav",
        ".portal-landing-hero",
        ".portal-landing-preview",
        ".portal-landing-studios",
        ".portal-landing-workflow",
        ".portal-landing-trust-grid",
        ".portal-landing-final",
        "@media (max-width: 920px)",
        "@media (max-width: 600px)",
    ):
        assert selector in THEME
    assert "min-height: 44px;" in _rule(THEME, ".portal-landing-locale-link")
    assert "var(--portal-light-canvas)" in THEME
    assert not _hex_literals_outside_root(THEME)
