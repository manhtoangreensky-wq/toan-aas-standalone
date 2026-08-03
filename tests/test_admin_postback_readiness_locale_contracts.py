"""RED contracts for reviewed Postback Readiness Portal locale copy.

This route is a signed, read-only preparation guide.  Localizing its fixed
Portal-owned copy must never introduce a postback control plane.
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


def test_postback_readiness_fixed_copy_uses_reviewed_locale_catalogue_and_route_chrome() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")
    pages = _read("copyfast_pages.py")
    renderer = _function_source(portal, "renderAdminPostbackReadiness")
    page_titles = _function_source(portal, "localizedPageTitle")
    page_descriptions = _function_source(portal, "localizedPageDescription")

    for key in (
        "route.title", "route.description",
        "intro.kicker", "intro.title", "intro.body", "intro.statusTitle", "intro.statusBody",
        "checklist.kicker", "checklist.title", "checklist.body",
        "checkpoint.scope.title", "checkpoint.scope.body",
        "checkpoint.dedupe.title", "checkpoint.dedupe.body",
        "checkpoint.handoff.title", "checkpoint.handoff.body",
        "handoff.kicker", "handoff.title", "handoff.body",
        "handoff.itemScope.title", "handoff.itemScope.body",
        "handoff.itemAuthority.title", "handoff.itemAuthority.body",
        "handoff.itemChannel.title", "handoff.itemChannel.body",
        "limits.kicker", "limits.title", "limits.body",
        "boundary.noConfig.title", "boundary.noConfig.body",
        "boundary.noEvents.title", "boundary.noEvents.body",
        "boundary.noFinancial.title", "boundary.noFinancial.body",
        "link.growth", "link.audit",
        "notes.integration.title", "notes.safety.title", "notes.scope.body", "notes.botBoundary.body",
    ):
        assert i18n.count(f'"adminGeneric.postbackReadiness.{key}"') == 3

    assert "function adminPostbackReadinessText(key, fallback, params)" in portal
    assert "const text = (key, fallback, params) => adminPostbackReadinessText(key, fallback, params);" in renderer
    assert '"Postback Readiness": "adminGeneric.postbackReadiness.route.title"' in portal
    assert 'if (path === "/admin/growth/postback-readiness") return adminPostbackReadinessText("route.title", fallback);' in page_titles
    assert 'if (path === "/admin/growth/postback-readiness") return adminPostbackReadinessText("route.description", fallback);' in page_descriptions
    assert (
        '"/admin/growth/postback-readiness": {"vi": "Postback Readiness · TOAN AAS", '
        '"en": "Postback Readiness · TOAN AAS", "zh": "回传准备 · TOAN AAS"}'
    ) in pages


def test_postback_readiness_locale_renderer_preserves_read_only_boundary_and_vietnamese_fallbacks() -> None:
    portal = _read("static/portal/portal.js")
    renderer = _function_source(portal, "renderAdminPostbackReadiness")

    for required in (
        'serverAuthorizesAdminRoute(context, "/admin/growth")',
        'serverAuthorizesAdminRoute(context, "/admin/audit")',
        "renderHero(page, context)",
        'badge("read_only")',
        "renderNotes({ ...page, notes: localizedNotes }, noteLabels)",
    ):
        assert required in renderer

    for forbidden in (
        "fetch(", "api(", "data-portal-action", "<form", "localStorage", "sessionStorage",
        "/api/affiliate/postback", "tracking_click_url", "AFFILIATE_POSTBACK_TOKEN",
        "postback_setup", "postback_config",
    ):
        assert forbidden.lower() not in renderer.lower()
    assert not re.search(r'''["']?method["']?\s*:\s*["']post["']''', renderer, flags=re.IGNORECASE)

    for fallback in (
        'text("boundary.noConfig.title", "Không tạo cấu hình kết nối")',
        'text("boundary.noEvents.title", "Không gửi hoặc nhận sự kiện")',
        'text("boundary.noFinancial.title", "Không thay đổi attribution hay tài chính")',
        'text("notes.scope.body", "Route này chỉ giúp chuẩn bị phạm vi và handoff.',
        'text("notes.integration.title", "Trạng thái tích hợp")',
        'text("notes.safety.title", "Nguyên tắc an toàn")',
    ):
        assert fallback in renderer


def test_render_notes_keeps_legacy_defaults_when_optional_localized_labels_are_absent() -> None:
    portal = _read("static/portal/portal.js")
    notes = _function_source(portal, "renderNotes")

    assert "function renderNotes(page, labels)" in notes
    assert 'const noteLabels = labels && typeof labels === "object" ? labels : {};' in notes
    assert 'const integrationTitle = typeof noteLabels.integrationTitle === "string"' in notes
    assert 'const safetyTitle = typeof noteLabels.safetyTitle === "string"' in notes
    assert '"Trạng thái tích hợp"' in notes
    assert '"Nguyên tắc an toàn"' in notes
    assert "safeText(index ? safetyTitle : integrationTitle)" in notes
