"""Contracts for fixed, signed Admin Security and Access locale chrome.

The locale preference applies only to Portal-owned wording.  It must not turn
the signed, read-only posture projection into a browser-owned security model.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    return source[match.start():match.end() + following.start() if following else len(source)]


def test_security_access_fixed_copy_uses_reviewed_locale_catalogue() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")
    pages = _read("copyfast_pages.py")

    for key in (
        "adminGeneric.securityAccess.state.loadingTitle",
        "adminGeneric.securityAccess.state.integrityGuardedTitle",
        "adminGeneric.securityAccess.metric.mfaRuntime.label",
        "adminGeneric.securityAccess.panel.rateLimit.title",
        "adminGeneric.securityAccess.boundary.0",
        "adminGeneric.securityAccess.route.securityTitle",
        "adminGeneric.securityAccess.route.accessDescription",
    ):
        assert i18n.count(f'"{key}"') == 3

    renderer = _function_source(portal, "renderAdminSecurityAccessPosture")
    page_titles = _function_source(portal, "localizedPageTitle")
    page_descriptions = _function_source(portal, "localizedPageDescription")
    assert "function adminSecurityAccessText(key, fallback, params)" in portal
    assert "adminSecurityAccessText(" in renderer
    assert "ADMIN_SECURITY_ACCESS_POSTURE_BOUNDARIES" in portal
    for forbidden in ("fetch(", "/internal/", "localStorage", "sessionStorage", "data-portal-action", "<button"):
        assert forbidden.lower() not in renderer.lower()
    assert '"/admin/security": {"vi": "Security Posture · TOAN AAS", "en": "Security Posture · TOAN AAS", "zh": "安全态势 · TOAN AAS"}' in pages
    assert '"/admin/access": {"vi": "Access Posture · TOAN AAS", "en": "Access Posture · TOAN AAS", "zh": "访问态势 · TOAN AAS"}' in pages
    assert 'if (path === "/admin/security") return adminSecurityAccessText("route.securityTitle", fallback);' in page_titles
    assert 'if (path === "/admin/access") return adminSecurityAccessText("route.accessTitle", fallback);' in page_titles
    assert 'if (path === "/admin/security") return adminSecurityAccessText("route.securityDescription", fallback);' in page_descriptions
    assert 'if (path === "/admin/access") return adminSecurityAccessText("route.accessDescription", fallback);' in page_descriptions
