"""Focused browser-boundary contracts for the Web Consultation Brief flow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_consultation_brief_renderer_is_embedded_accessible_and_non_persistent() -> None:
    start = PORTAL.index("function renderSupportConsultationBrief")
    renderer = PORTAL[start:PORTAL.index("function supportCaseTimestamp", start)]

    for required in (
        'id="support-consultation-brief"',
        'id="support-consultation-service"',
        'id="support-consultation-goal"',
        'id="support-consultation-context"',
        'id="support-consultation-outcome"',
        'data-portal-no-transient',
        'data-portal-action="support-consultation-compose"',
        'data-portal-action="support-consultation-handoff"',
        'data-portal-action="support-consultation-catalog-retry"',
        'role="status" aria-live="polite"',
        "Bản nháp chỉ tồn tại trong trang hiện tại.",
        "không tạo yêu cầu tự động",
        "data-portal-confirm",
    ):
        assert required in renderer

    assert 'method="post"' not in renderer.lower()
    assert "support-case-create" not in renderer
    assert "localStorage" not in renderer
    assert "sessionStorage" not in renderer
    assert "Không nhập email, số điện thoại, Zalo, Telegram" in renderer
    assert "supportConsultationCatalog(context)" in renderer
    assert "supportConsultationDraftInput(context, catalog)" in renderer
    assert "supportConsultationPreview(context, catalog)" in renderer
    assert "value=\"${safeText(draftInput.goal)}\"" in renderer
    assert "${safeText(draftInput.currentContext)}" in renderer
    assert "${safeText(draftInput.requestedOutcome)}" in renderer


def test_consultation_catalog_and_preview_are_closed_signed_page_projections() -> None:
    for required in (
        'const SUPPORT_CONSULTATION_CATALOG_VERSION = "2026-07-23"',
        "const SUPPORT_CONSULTATION_GROUP_IDS",
        "const SUPPORT_CONSULTATION_SERVICE_META",
        "const SUPPORT_CONSULTATION_BOUNDARY_KEYS",
        "function supportConsultationCatalogProjection",
        "function supportConsultationPreviewProjection",
        'data.delivery !== "web_view_only"',
        'data.persistence !== "none"',
        'data.automation !== "none"',
        "data.case_created !== false",
        "data.input_persisted !== false",
        "Object.keys(boundaries).length === SUPPORT_CONSULTATION_BOUNDARY_KEYS.length",
        'api("/support/consultation-brief/catalog")',
        '"support-consultation-view": Boolean(account && supportDeskEnabled)',
        '"support-consultation-compose": Boolean(account && me.csrf_token && supportDeskEnabled)',
    ):
        assert required in INTEGRATION

    for epoch in (
        "supportConsultationCatalogHydrationEpoch",
        "supportConsultationComposeRequestEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    for required in (
        "let supportConsultationComposeInFlight = false;",
        "function setSupportConsultationComposeBusy",
        "supportConsultationDraftInput: payload",
        "supportConsultationDraftInput: {}",
        'if (action === "support-consultation-catalog-retry")',
        'return { catalog: {}, readState: "guarded", error };',
    ):
        assert required in INTEGRATION

    helper_start = INTEGRATION.index("function supportConsultationCatalogRequestIsCurrent")
    helper_end = INTEGRATION.index("async function hydrateSupportAdvisor", helper_start)
    helper = INTEGRATION[helper_start:helper_end]
    for required in (
        "sessionEpoch === supportSessionEpoch",
        'currentPortalPath() === "/support"',
        "base().supportDeskEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert required in helper


def test_consultation_compose_posts_only_a_transient_draft_and_handoff_cannot_create_case() -> None:
    compose_start = INTEGRATION.index('if (action === "support-consultation-compose")')
    handoff_start = INTEGRATION.index('if (action === "support-consultation-handoff")', compose_start)
    end = INTEGRATION.index('if (action === "support-cases-filter" || action === "support-cases-filter-clear")', handoff_start)
    compose = INTEGRATION[compose_start:handoff_start]
    handoff = INTEGRATION[handoff_start:end]

    for required in (
        "supportConsultationCatalogProjection",
        "supportConsultationComposePayload",
        "acquireSubmission",
        "supportConsultationComposeRequestEpoch",
        "supportConsultationComposeInFlight = true",
        "setSupportConsultationComposeBusy(true)",
        "setSupportConsultationComposeBusy(false)",
        'api("/support/consultation-brief/compose"',
        "supportConsultationPreviewProjection",
        "supportConsultationPreview: projection.preview",
    ):
        assert required in compose
    assert "/support/cases" not in compose

    for required in (
        "supportConsultationComposeInFlight",
        "supportConsultationPreviewProjection",
        'document.querySelector("#support-category")',
        'document.querySelector("#support-priority")',
        'document.querySelector("#support-subject")',
        'document.querySelector("#support-detail")',
        'field.dispatchEvent(new Event("input", { bubbles: true }))',
        'field.dispatchEvent(new Event("change", { bubbles: true }))',
        "supportConsultationPreview: {}",
        "supportConsultationDraftInput: {}",
        "mountedSubject.focus",
        "normal case form remains the only case write",
    ):
        assert required in handoff
    for forbidden in (
        "api(", "fetch(", "/support/cases", "window.location", "submit()",
        "data-support-consultation-service", "localStorage", "sessionStorage",
    ):
        assert forbidden.lower() not in handoff.lower()


def test_consultation_brief_uses_portal_mobile_and_private_pwa_boundaries() -> None:
    for selector in (
        ".portal-support-consultation",
        ".portal-support-consultation-form",
        ".portal-support-consultation-result",
        ".portal-support-consultation-actions",
        "min-height: 44px",
    ):
        assert selector in CSS

    mobile_start = CSS.index("@media (max-width: 700px)")
    mobile = CSS[mobile_start:]
    for selector in (
        ".portal-support-consultation-form .portal-fields { grid-template-columns: 1fr; }",
        ".portal-support-consultation-actions { align-items: stretch; flex-direction: column; }",
        ".portal-support-consultation-actions .portal-button { width: 100%; }",
    ):
        assert selector in mobile

    for private_path in ("/api/v1/support", '"/support"', '"/tickets"', '"/admin/support"'):
        assert private_path not in SERVICE_WORKER
