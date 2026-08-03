"""Contracts for reviewed System & Data Stewardship directory locale chrome.

The interface locale changes Portal-owned presentation only.  It must not
widen the signed, read-only directory's authorization or operational boundary.
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


def test_system_stewardship_fixed_copy_uses_reviewed_locale_catalogue() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")
    pages = _read("copyfast_pages.py")
    renderer = _function_source(portal, "renderAdminSystemStewardship")
    page_titles = _function_source(portal, "localizedPageTitle")
    page_descriptions = _function_source(portal, "localizedPageDescription")

    for key in (
        "adminGeneric.systemStewardship.route.title",
        "adminGeneric.systemStewardship.route.description",
        "adminGeneric.systemStewardship.card.automation.title",
        "adminGeneric.systemStewardship.card.backups.description",
        "adminGeneric.systemStewardship.authority.canonical",
        "adminGeneric.systemStewardship.action.requiresCanonical",
        "adminGeneric.systemStewardship.intro.title",
        "adminGeneric.systemStewardship.section.local.title",
        "adminGeneric.systemStewardship.boundary.noDeploy.title",
    ):
        assert i18n.count(f'"{key}"') == 3

    assert "function adminSystemStewardshipText(key, fallback, params)" in portal
    assert "const text = (key, fallback, params) => adminSystemStewardshipText(key, fallback, params);" in renderer
    assert '"System & Data Stewardship": "adminGeneric.systemStewardship.route.title"' in portal
    assert 'if (path === "/admin/system-stewardship") return adminSystemStewardshipText("route.title", fallback);' in page_titles
    assert 'if (path === "/admin/system-stewardship") return adminSystemStewardshipText("route.description", fallback);' in page_descriptions
    assert (
        '"/admin/system-stewardship": {"vi": "System & Data Stewardship · TOAN AAS", '
        '"en": "System & Data Stewardship · TOAN AAS", '
        '"zh": "系统与数据治理 · TOAN AAS"}'
    ) in pages

    # Directory authority and card access must remain server-owned.  Locale
    # copy cannot introduce actions, browser persistence, or a control plane.
    for required in (
        "adminErpNavigation(context)",
        "hasLiveCanonicalAdmin(context)",
        "serverAuthorizesAdminRoute(context, card.route)",
        'authority !== "canonical" || canonicalAdmin',
        "badge(state)",
    ):
        assert required in renderer
    for forbidden in ("fetch(", "/internal/", "localStorage", "sessionStorage", "data-portal-action"):
        assert forbidden.lower() not in renderer.lower()
    assert not re.search(r'''["']?method["']?\s*:\s*["']post["']''', renderer, flags=re.IGNORECASE)


def test_system_stewardship_routes_every_fixed_renderer_label_through_presentation_helper() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")
    renderer = _function_source(portal, "renderAdminSystemStewardship")

    keyset = (
        "route.title", "route.description",
        "authority.local", "authority.canonical",
        "action.open", "action.requiresCanonical", "action.waitingServer", "action.guardedAria",
        "manifest.ready", "manifest.guarded",
        "intro.kicker", "intro.title", "intro.boundary", "intro.statusVerified", "intro.statusSeparated", "intro.statusBody",
        "section.local.kicker", "section.local.title", "section.local.body",
        "section.canonical.kicker", "section.canonical.title", "section.canonical.body",
        "boundary.kicker", "boundary.title", "boundary.body",
        "boundary.noDeploy.title", "boundary.noDeploy.body",
        "boundary.noProvider.title", "boundary.noProvider.body",
        "boundary.noLedger.title", "boundary.noLedger.body",
    )
    for card in ("automation", "security", "access", "governance", "archive", "system", "runtime", "backups"):
        keyset += (f"card.{card}.title", f"card.{card}.description")

    for key in keyset:
        assert i18n.count(f'"adminGeneric.systemStewardship.{key}"') == 3

    for key in (
        "authority.local", "authority.canonical",
        "action.open", "action.requiresCanonical", "action.waitingServer", "action.guardedAria",
        "manifest.ready", "manifest.guarded",
        "intro.kicker", "intro.title", "intro.boundary", "intro.statusVerified", "intro.statusSeparated", "intro.statusBody",
        "section.local.kicker", "section.local.title", "section.local.body",
        "section.canonical.kicker", "section.canonical.title", "section.canonical.body",
        "boundary.kicker", "boundary.title", "boundary.body",
        "boundary.noDeploy.title", "boundary.noDeploy.body",
        "boundary.noProvider.title", "boundary.noProvider.body",
        "boundary.noLedger.title", "boundary.noLedger.body",
    ):
        assert f'text("{key}"' in renderer

    for card in ("automation", "security", "access", "governance", "archive", "system", "runtime", "backups"):
        assert f'text("card.{card}.title"' in renderer
        assert f'text("card.{card}.description"' in renderer

    # The guarded aria string has only presentation-safe title text injected;
    # routes, authorities, outcome states and manifest entries stay data.
    assert 'safeText(text("action.guardedAria"' in renderer


def test_system_stewardship_localization_preserves_canonical_source_fallbacks() -> None:
    portal = _read("static/portal/portal.js")
    renderer = _function_source(portal, "renderAdminSystemStewardship")

    for source_fragment in (
        'text("card.system.description", "System read model do canonical authority cấp và redaction.")',
        'text("card.runtime.description", "Runtime metadata canonical đã redaction; không có deploy hoặc repair executor.")',
        'text("card.backups.description", "Backup metadata canonical chỉ đọc; không có restore action trong release này.")',
        'text("manifest.ready", "Các điểm đến dưới đây được lọc theo manifest mà máy chủ cấp cho phiên hiện tại.")',
        'text("intro.boundary", "Không có số liệu runtime, log, secret, provider state hay action vận hành được dựng tại hub này.")',
        'text("section.local.body", "Các màn hình local vẫn cần signed Web admin và kiểm tra server-side tại từng route.")',
    ):
        assert source_fragment in renderer
