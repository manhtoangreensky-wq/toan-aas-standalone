"""Focused contracts for the consent-gated customer Consultation CRM intake.

These checks deliberately inspect the narrow Web route rather than the broad
Partner CRM implementation.  The customer journey may create one private
draft after an explicit storage-only confirmation; it must never turn the
generic CRM form, Support Brief, browser storage, Bot, payment or provider
surfaces into an implicit dependency.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
CRM = (ROOT / "copyfast_partner_crm.py").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_consultation_crm_router_is_a_closed_storage_only_contract() -> None:
    """The durable customer route must not inherit browser-controlled CRM fields."""

    for fragment in (
        "CONSULTATION_CRM_CATALOG_VERSION",
        "CONSULTATION_CRM_STORAGE_SCOPE = \"crm_draft_storage_only\"",
        "CONSULTATION_CRM_GROUPS",
        "class ConsultationRequestFields(BaseModel)",
        "class ConsultationPreviewRequest(ConsultationRequestFields)",
        "class ConsultationConfirmRequest(ConsultationRequestFields)",
        "@router.get(\"/consultations/catalog\")",
        "@router.post(\"/consultations/preview\")",
        "@router.post(\"/consultations\")",
        "async def preview_consultation",
        "async def confirm_consultation",
        "def _consultation_snapshot",
        "consent_to_store: StrictBool",
        "confirm_create: StrictBool",
        '"outbound_contact_authorized": False',
        "action=\"consultation_lead_confirmed\"",
        "action=\"web.partner_crm.consultation.create\"",
        "web-partner-crm:{account_id}:consultation:create",
    ):
        assert fragment in CRM

    intake_model = _between(CRM, "class ConsultationRequestFields(BaseModel)", "class ConsultationPreviewRequest")
    assert "ConfigDict(extra=\"forbid\"" in intake_model
    for browser_controlled_field in (
        "contact_email:",
        "lead_kind:",
        "source_kind:",
        "source_label:",
        "tags:",
        "consent_status:",
        "consent_note:",
        "stage:",
    ):
        assert browser_controlled_field not in intake_model

    snapshot = _between(CRM, "def _consultation_snapshot", "LEAD_COLUMN_NAMES")
    for server_pinned_value in (
        'contact_email=""',
        'lead_kind="customer"',
        'source_kind="inbound"',
        'tags=["web-consultation", payload.service_id]',
        'consent_status="documented"',
        "stage=\"draft\"",
    ):
        assert server_pinned_value in snapshot

    # The dedicated validator owns the contact prohibition; it must not
    # silently defer to generic CRM text validation which permits contacts.
    validation = _between(CRM, "def _contains_consultation_contact", "def _code")
    for contact_guard in (
        "EMAIL_ADDRESS_PATTERN",
        "PHONE_NUMBER_PATTERN",
        "CONTACT_LABEL_PATTERN",
        "TELEGRAM_HANDLE_PATTERN",
        "_consultation_line",
        "_consultation_text",
    ):
        assert contact_guard in validation


def test_app_uses_one_bounded_fixed_rate_family_for_both_consultation_route_spellings() -> None:
    """A slash suffix cannot bypass body caps, rate limits or safe 429 data."""

    for path in (
        '"/api/v1/partner-crm/consultations/preview",',
        '"/api/v1/partner-crm/consultations/preview/",',
        '"/api/v1/partner-crm/consultations",',
        '"/api/v1/partner-crm/consultations/",',
    ):
        assert path in APP
    for fragment in (
        "PARTNER_CRM_BODY_MAX_BYTES",
        'path.startswith("/api/v1/partner-crm/")',
        "WEB_PARTNER_CRM_BODY_TOO_LARGE",
        "partner_crm_consultation_preview",
        "partner_crm_consultation_confirm",
        "if partner_crm_consultation_preview:",
        "rate_limit = 30",
        "if partner_crm_consultation_confirm:",
        "rate_limit = 20",
        '"partner-crm-consultation-preview" if partner_crm_consultation_preview',
        '"partner-crm-consultation-confirm" if partner_crm_consultation_confirm',
        "is_partner_crm_consultation_request",
        "copyfast_partner_crm._boundary(lead_persisted=False)",
    ):
        assert fragment in APP

    # Customer CRM pages/APIs are account-private, so the existing broad CRM
    # no-cache prefix must cover the new child route rather than creating a
    # separate cache policy which could drift during later UI work.
    assert '"/" + "api/v1/partner-crm"' in SERVICE_WORKER
    assert '"/crm"' in SERVICE_WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER


def test_portal_has_a_dedicated_accessible_two_step_intake_without_auto_navigation() -> None:
    """The UI stays in the app workspace and only exposes an explicit post-save link."""

    for fragment in (
        'customerPage("/crm/consultations/new", "Gửi nhu cầu tư vấn"',
        'layout: "consultation-crm-intake"',
        "function renderConsultationCrmIntake(page, context)",
        'case "consultation-crm-intake": return renderConsultationCrmIntake(page, context);',
        'data-portal-action="consultation-crm-preview"',
        'data-portal-action="consultation-crm-confirm"',
        'data-portal-action="consultation-crm-catalog-retry"',
        "data-portal-no-transient",
        'name="consent_to_store"',
        "Xác nhận phạm vi lưu trữ",
        "Mở lead draft",
        "Không có consent liên hệ",
        "aria-live=\"polite\"",
        "<fieldset",
    ):
        assert fragment in PORTAL

    renderer = _between(PORTAL, "function renderConsultationCrmIntake(page, context)", "function renderPartnerCrmDetail")
    for forbidden_cross_flow in (
        "partnerCrmForm(",
        "supportConsultation",
        "localStorage",
        "sessionStorage",
        "navigatePortal(",
        "window.location",
        "mailto:",
        "tel:",
    ):
        assert forbidden_cross_flow not in renderer
    assert 'href="' in renderer and '"/crm/leads/" + encodeURIComponent' in renderer

    # Discovery stays a quiet CRM-local affordance, not an unsolicited global
    # CTA or a conversion of a Support Brief into a lead.
    partner_crm = _between(PORTAL, "function renderPartnerCrm(page, context)", "function renderConsultationCrmIntake")
    assert "/crm/consultations/new" in partner_crm
    assert "Gửi nhu cầu tư vấn" in partner_crm

    assert 'if normalized == "/crm/consultations/new":' in PAGES
    assert 'return "Gửi nhu cầu tư vấn"' in PAGES


def test_portal_client_keeps_consultation_state_route_fenced_and_does_not_reuse_generic_crm() -> None:
    """Transient input is page-memory only and every write remains server guarded."""

    for fragment in (
        "consultationCrmCatalog",
        "consultationCrmReadState",
        "consultationCrmPreview",
        "consultationCrmDraftInput",
        "consultationCrmSelection",
        "consultationCrmSessionEpoch",
        "consultationCrmCatalogHydrationEpoch",
        "async function hydrateConsultationCrmIntake",
        "function consultationCrmRequestIsCurrent",
        'api("/partner-crm/consultations/catalog")',
        'api("/partner-crm/consultations/preview"',
        'api("/partner-crm/consultations",',
        '"consultation-crm-view": Boolean(account && partnerCrmEnabled)',
        '"consultation-crm-preview": Boolean(account && me.csrf_token && partnerCrmEnabled)',
        '"consultation-crm-confirm": Boolean(account && me.csrf_token && partnerCrmEnabled)',
        'if (action === "consultation-crm-catalog-retry")',
        'if (action === "consultation-crm-preview")',
        'if (action === "consultation-crm-confirm")',
        "webNativeCoordinationMutation",
        "idempotency_key: submission.key",
        "consent_to_store: true",
        "confirm_create: true",
        "partnerCrmBoundaryIsSafe",
    ):
        assert fragment in INTEGRATION

    nested_boundary = _between(INTEGRATION, "function consultationCrmCatalogBoundaries", "function consultationCrmBoundaryIsSafe")
    # The router returns the same explicit execution marker in the nested
    # catalog boundary as it does at the top level. Treating it as an unknown
    # key would make every valid catalog look guarded in the browser.
    assert '"execution"' in nested_boundary
    assert '"web_native_partner_lead_crm_only"' in nested_boundary

    # The server marks the new record as a CRM `draft`; the UI must not
    # mistake that pipeline stage for a generic completed job and hide the
    # validated receipt after a successful confirmation.
    receipt_projection = _between(INTEGRATION, "function consultationCrmReceiptProjection", "function channelStrategySafetyError")
    assert 'result.status !== "draft"' in receipt_projection
    assert 'result.status !== "completed"' not in receipt_projection

    start = INTEGRATION.index('if (action === "consultation-crm-preview")')
    end = INTEGRATION.index('if (action === "consultation-crm-confirm")', start)
    preview_action = INTEGRATION[start:end]
    for forbidden_generic_path in (
        'api("/partner-crm/leads"',
        "partnerCrmPayload(",
        "localStorage",
        "sessionStorage",
    ):
        assert forbidden_generic_path not in preview_action

    confirm_start = end
    # The next independent portal action acts as a stable local boundary. If
    # another consultation action is added later, it must preserve the same
    # properties and this test is intentionally updated with that review.
    confirm_end = INTEGRATION.find('\n      if (action === ', confirm_start + 4)
    confirm_action = INTEGRATION[confirm_start:confirm_end if confirm_end > confirm_start else None]
    for forbidden_generic_path in (
        'api("/partner-crm/leads"',
        "partnerCrmPayload(",
        "localStorage",
        "sessionStorage",
        "navigatePortal(",
        "window.location",
    ):
        assert forbidden_generic_path not in confirm_action
    assert 'api("/partner-crm/consultations",' in confirm_action
    # A malformed 2xx response can still represent a durable server write.
    # Keep the same key for an in-page retry until the receipt projection has
    # been accepted and put into route memory, rather than replacing it with
    # a second create intent after any HTTP response.
    assert "let receiptVerified = false;" in confirm_action
    assert "receiptVerified = true;" in confirm_action
    assert "if (receiptVerified) discardSubmission(scope, submission);" in confirm_action
    assert "if (acknowledged) discardSubmission(scope, submission);" not in confirm_action
