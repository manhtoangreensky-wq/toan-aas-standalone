"""Focused browser-boundary contracts for the Web-native Support Advisor."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_support_advisor_renderer_is_a_signed_accessible_non_writing_handoff() -> None:
    start = PORTAL.index("function renderSupportAdvisor")
    renderer = PORTAL[start:PORTAL.index("function supportCaseTimestamp", start)]

    for required in (
        'id="support-advisor"',
        'for="support-advisor-category"',
        'id="support-advisor-category"',
        'data-portal-no-transient',
        'data-portal-action="support-advisor-guide"',
        'role="status" aria-live="polite"',
        'data-portal-action="support-advisor-handoff"',
        "Chưa có yêu cầu nào được tạo.",
        "Không có phân loại AI, thông báo ngoài hệ thống hay ticket tự tạo.",
        "supportAdvisorSelection",
    ):
        assert required in renderer

    # The handoff is the only visual primary action after a valid guide; the
    # customer still writes a subject/body and submits the normal form later.
    assert renderer.count("portal-button--primary") == 1
    assert "support-case-create" not in renderer
    assert 'method="post"' not in renderer.lower()

    guide_start = PORTAL.index("function supportAdvisorGuide")
    guide = PORTAL[guide_start:start]
    assert "SUPPORT_ADVISOR_BOUNDARY_KEYS" in guide
    assert "checklist.some((item) => !item)" in guide


def test_support_advisor_accepts_only_a_closed_server_shape_and_never_writes() -> None:
    for requirement in (
        "const SUPPORT_ADVISOR_TOPICS",
        "const SUPPORT_ADVISOR_BOUNDARY_KEYS",
        "function supportAdvisorGuideProjection",
        'data.delivery !== "web_view_only"',
        'data.automation !== "none"',
        "Object.keys(boundaries).length === SUPPORT_ADVISOR_BOUNDARY_KEYS.length",
        "checklist.some((item) => !item)",
        "function hydrateSupportAdvisor",
        'api(`/support/advisor?category=${encodeURIComponent(category)}`)',
        "supportAdvisorHydrationEpoch",
        'supportAdvisorSelection: category',
        'supportAdvisorSelection: "general_support"',
        '"support-advisor-view": Boolean(account && supportDeskEnabled)',
    ):
        assert requirement in INTEGRATION

    action_start = INTEGRATION.index('if (action === "support-advisor-guide")')
    action_end = INTEGRATION.index('if (action === "support-cases-filter" || action === "support-cases-filter-clear")', action_start)
    actions = INTEGRATION[action_start:action_end]
    for forbidden in (
        "api(",
        "fetch(",
        'method: "post"',
        "/support/cases",
        "support-case-create",
        "bridge",
        "payos",
        "wallet",
        "telegram",
        "provider",
    ):
        assert forbidden.lower() not in actions.lower()

    for required in (
        'currentPortalPath() !== "/support"',
        "base().supportAdvisor",
        "supportAdvisorGuideProjection",
        "supportAdvisorCategory(projection.guide.category)",
        'document.querySelector("#support-category")',
        "categoryField.value = category",
        'document.querySelector("#support-subject")',
        "subjectField.focus",
    ):
        assert required in actions

    # A DOM category attribute can be useful to styling, but it must never be
    # read back for the non-writing handoff decision.
    assert "data-support-advisor-category" not in actions


def test_support_advisor_uses_existing_private_pwa_boundary_and_mobile_controls() -> None:
    for selector in (
        ".portal-support-advisor",
        ".portal-support-advisor-form",
        ".portal-support-advisor-result",
        ".portal-support-advisor-checklist",
        ".portal-support-advisor-actions",
        "min-height: 44px",
    ):
        assert selector in CSS

    mobile_start = CSS.index("@media (max-width: 700px)")
    mobile = CSS[mobile_start:]
    for selector in (
        ".portal-support-advisor-form { grid-template-columns: 1fr; }",
        ".portal-support-advisor-form-action .portal-button { width: 100%; }",
        ".portal-support-advisor-actions { align-items: stretch; flex-direction: column; }",
    ):
        assert selector in mobile

    for private_path in ("/api/v1/support", '"/support"', '"/tickets"', '"/admin/support"'):
        assert private_path not in SERVICE_WORKER
