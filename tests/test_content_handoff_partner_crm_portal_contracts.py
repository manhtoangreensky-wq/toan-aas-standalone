"""Focused contracts for private Content Handoff and Partner CRM portal flows."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_private_routes_are_mounted_flagged_bounded_and_never_pwa_cached() -> None:
    app = _read("app.py")
    api = _read("copyfast_api.py")
    worker = _read("static/portal/service-worker.js")

    assert "import copyfast_content_handoff" in app
    assert "import copyfast_partner_crm" in app
    assert "app.include_router(copyfast_content_handoff.router)" in app
    assert "app.include_router(copyfast_partner_crm.router)" in app
    assert "CONTENT_HANDOFF_BODY_MAX_BYTES" in app
    assert "PARTNER_CRM_BODY_MAX_BYTES" in app
    assert '"content_handoff_enabled": enabled("WEBAPP_CONTENT_HANDOFF_ENABLED", True)' in api
    assert '"partner_crm_enabled": enabled("WEBAPP_PARTNER_CRM_ENABLED", True)' in api
    for value in ('"/" + "api/v1/content-handoffs"', '"/content/handoffs"', '"/" + "api/v1/partner-crm"', '"/crm"'):
        assert value in worker
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in worker
    assert "const BUILD_ID = workerBuildId();" in worker
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in worker
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in worker


def test_integration_uses_owner_scoped_contracts_with_csrf_revision_and_idempotency() -> None:
    integration = _read("static/portal/integration.js")

    for endpoint in (
        'api("/content-handoffs/summary")',
        'api("/content-handoffs/policy")',
        'api("/partner-crm/summary")',
        'api("/partner-crm/policy")',
    ):
        assert endpoint in integration
    for capability in (
        '"content-handoff-create": Boolean(account && me.csrf_token && contentHandoffEnabled)',
        '"partner-crm-create": Boolean(account && me.csrf_token && partnerCrmEnabled)',
        '"partner-crm-stage": Boolean(account && me.csrf_token && partnerCrmEnabled)',
    ):
        assert capability in integration
    for action in (
        "content-handoff-create",
        "content-handoff-update",
        "content-handoff-submit-review",
        "partner-crm-create",
        "partner-crm-update",
        "partner-crm-stage",
        "partner-crm-consent",
        "partner-crm-note",
    ):
        assert f'if (action === "{action}")' in integration or action in integration
    assert "webNativeCoordinationMutation" in integration
    assert "idempotency_key: submission.key" in integration
    assert "expected_revision: expectedRevision" in integration
    assert 'if (action === "content-handoff-staff-review")' in integration
    assert "confirm_manual_handoff: confirmManualHandoff" in integration
    assert "contentHandoffBoundaryIsSafe" in integration
    assert "partnerCrmBoundaryIsSafe" in integration


def test_partner_crm_owner_and_manager_pagination_are_separate_private_contracts() -> None:
    """Owner pipeline and redacted manager directory never share cursors.

    The two API surfaces have different authorization and data-safety rules,
    so pagination state, offsets and DOM actions must remain distinct.
    """

    integration = _read("static/portal/integration.js")
    portal = _read("static/portal/portal.js")

    for fragment in (
        "const PARTNER_CRM_LIST_LIMIT =",
        "const PARTNER_CRM_MANAGER_LIST_LIMIT =",
        "function partnerCrmLeadsPath(offset)",
        "function partnerCrmManagerStage(value)",
        "function partnerCrmManagerDirectoryPath(stage, offset)",
        "function partnerCrmListingProjection(offset, source, returned)",
        "function partnerCrmManagerListingProjection(stage, offset, source, returned)",
        "partnerCrmListing:",
        "partnerCrmManagerListing:",
        'if (action === "partner-crm-page")',
        'if (action === "partner-crm-manager-filter")',
        'if (action === "partner-crm-manager-page")',
        "__partnerCrmOffset",
        "__partnerCrmManagerOffset",
        "__partnerCrmManagerStage",
        "next_offset",
        "previous_offset",
    ):
        assert fragment in integration

    for fragment in (
        "function partnerCrmListing(context)",
        "function partnerCrmManagerListing(context)",
        "function renderPartnerCrmPagination(listing",
        "function renderPartnerCrmManagerPagination(listing",
        "function renderPartnerCrmManagerFilter(listing, enabled)",
        'data-portal-action="partner-crm-page"',
        'data-portal-action="partner-crm-manager-page"',
        'data-portal-action="partner-crm-manager-filter"',
        "data-partner-crm-offset",
        "data-partner-crm-manager-offset",
        "data-partner-crm-manager-stage",
        "partnerCrmListing(context)",
        "partnerCrmManagerListing(context)",
    ):
        assert fragment in portal

    owner_start = portal.index("function renderPartnerCrm(page, context)")
    owner_end = portal.index("function renderPartnerCrmDetail(page, context)", owner_start)
    owner_view = portal[owner_start:owner_end]
    assert "const listing = partnerCrmListing(context);" in owner_view
    assert "renderPartnerCrmPagination(listing, canView)" in owner_view

    manager_start = portal.index("function renderPartnerCrmManager(page, context)")
    manager_end = portal.index("function renderPage(page, context)", manager_start)
    manager_view = portal[manager_start:manager_end]
    assert "const listing = partnerCrmManagerListing(context);" in manager_view
    assert "renderPartnerCrmManagerFilter(listing, !guarded)" in manager_view
    # The pager is rendered only in the non-guarded branch. Passing the
    # existing server-authorized state through keeps the disabled state
    # correct without trusting a browser-supplied manager role.
    assert "renderPartnerCrmManagerPagination(listing, !guarded)" in manager_view


def test_content_handoff_owner_and_staff_pagination_are_separate_private_contracts() -> None:
    """Pagination metadata stays in transient Web state, never in a shared queue.

    Owner records and Customer Care records deliberately have different paths,
    limits, DOM offsets and actions.  This prevents a regular customer page
    from accidentally inheriting a staff page cursor (or vice versa).
    """

    integration = _read("static/portal/integration.js")
    portal = _read("static/portal/portal.js")

    for fragment in (
        "const CONTENT_HANDOFF_LIST_LIMIT =",
        "const CONTENT_HANDOFF_STAFF_LIST_LIMIT =",
        "function contentHandoffListOffset(value)",
        "function contentHandoffRecordsPath(offset)",
        "function contentHandoffStaffStatus(value)",
        "function contentHandoffStaffQueuePath(status, offset)",
        "function contentHandoffListingProjection(offset, source, returned)",
        "function contentHandoffStaffListingProjection(status, offset, source, returned)",
        "contentHandoffListing:",
        "contentHandoffStaffListing:",
        'if (action === "content-handoff-page")',
        'if (action === "content-handoff-staff-filter")',
        'if (action === "content-handoff-staff-page")',
        "__contentHandoffOffset",
        "__contentHandoffStaffOffset",
        "__contentHandoffStaffStatus",
        "next_offset",
        "previous_offset",
    ):
        assert fragment in integration

    for fragment in (
        "function contentHandoffListing(context)",
        "function contentHandoffStaffListing(context)",
        "function renderContentHandoffPagination(listing",
        "function renderContentHandoffStaffPagination(listing",
        "function renderContentHandoffStaffFilter(listing, enabled)",
        'data-portal-action="content-handoff-page"',
        'data-portal-action="content-handoff-staff-page"',
        'data-portal-action="content-handoff-staff-filter"',
        "data-content-handoff-offset",
        "data-content-handoff-staff-offset",
        "data-content-handoff-staff-status",
        "contentHandoffListing(context)",
        "contentHandoffStaffListing(context)",
    ):
        assert fragment in portal

    owner_start = portal.index("function renderContentHandoff(page, context)")
    owner_end = portal.index("function renderContentHandoffDetail(page, context)", owner_start)
    owner_view = portal[owner_start:owner_end]
    assert "const listing = contentHandoffListing(context);" in owner_view
    assert "renderContentHandoffPagination(listing, canView)" in owner_view

    staff_start = portal.index("function renderContentHandoffAdmin(page, context)")
    staff_end = portal.index("function partnerCrmForm(", staff_start)
    staff_view = portal[staff_start:staff_end]
    assert "const listing = contentHandoffStaffListing(context);" in staff_view
    assert "renderContentHandoffStaffFilter(listing, !guarded)" in staff_view
    assert "renderContentHandoffStaffPagination(listing, !guarded)" in staff_view


def test_admin_coordination_filters_are_allowlisted_reset_pagination_and_preserve_route_guards() -> None:
    """Read filters remain scoped to the existing signed admin endpoints."""

    integration = _read("static/portal/integration.js")
    portal = _read("static/portal/portal.js")

    for fragment in (
        'return status === "all" || CONTENT_HANDOFF_STATUSES.has(status) ? status : "all";',
        'return stage === "all" || PARTNER_CRM_STAGES.has(stage) ? stage : "all";',
        "api(contentHandoffStaffQueuePath(status, offset))",
        "api(partnerCrmManagerDirectoryPath(stage, offset))",
        "await hydrateContentHandoffStaffQueue(status, 0);",
        "await hydratePartnerCrmManagerDirectory(stage, 0);",
        "await hydrateContentHandoffStaffQueue(fields.__contentHandoffStaffStatus, contentHandoffListOffset(fields.__contentHandoffStaffOffset));",
        "await hydratePartnerCrmManagerDirectory(fields.__partnerCrmManagerStage, partnerCrmListOffset(fields.__partnerCrmManagerOffset));",
        'const expectedPath = "/admin/content-handoffs";',
        'const expectedPath = "/admin/crm/leads";',
    ):
        assert fragment in integration

    for fragment in (
        'data-portal-action="content-handoff-staff-filter"',
        'data-portal-action="partner-crm-manager-filter"',
        "data-content-handoff-staff-status",
        "data-partner-crm-manager-stage",
        "renderContentHandoffStaffFilter(listing, !guarded)",
        "renderPartnerCrmManagerFilter(listing, !guarded)",
        "data-portal-no-transient",
    ):
        assert fragment in portal

    handoff_start = portal.index("function renderContentHandoffAdmin(page, context)")
    handoff_end = portal.index("function partnerCrmForm(", handoff_start)
    assert 'data-portal-route="/admin/content-handoffs"' in portal[handoff_start:handoff_end]

    crm_start = portal.index("function renderPartnerCrmManager(page, context)")
    crm_end = portal.index("function renderPage(page, context)", crm_start)
    assert 'data-portal-route="/admin/crm/leads"' in portal[crm_start:crm_end]


def test_portal_has_professional_operational_views_without_external_execution_claims() -> None:
    portal = _read("static/portal/portal.js")

    for route in (
        'customerPage("/content/handoffs", "Content Handoff"',
        'customerPage("/crm/leads", "Partner & Lead CRM"',
        'path: "/content/handoffs/:id"',
        'path: "/crm/leads/:id"',
    ):
        assert route in portal
    for renderer in (
        "function renderContentHandoff(page, context)",
        "function renderContentHandoffDetail(page, context)",
        "function renderPartnerCrm(page, context)",
        "function renderPartnerCrmDetail(page, context)",
        "function renderPartnerCrmManager(page, context)",
    ):
        assert renderer in portal
    assert "Odoo-style private pipeline" in portal
    assert "Internal human handoff only" in portal
    assert 'data-portal-action="content-handoff-staff-review"' in portal
    assert 'path.startsWith("/content/handoffs/")' in portal
    assert 'path.startsWith("/crm/leads/")' in portal
    assert 'route.includes("handoff")' in portal
    assert "không tự liên hệ, không lookup, không referral/payout" in portal
    assert "Không có social OAuth, recipient, email/Telegram, publish, file delivery, provider, job, Xu hoặc PayOS." in portal

    manager_start = portal.index("function renderPartnerCrmManager(page, context)")
    manager_end = portal.index("function renderPage(page, context)", manager_start)
    manager = portal[manager_start:manager_end]
    # The directory is deliberately anonymous: once the API stopped emitting
    # identifiers, the renderer must not require or display them either.
    assert "validPartnerCrmLeadId(item.lead_id)" not in manager
    assert 'PARTNER_CRM_STAGES.has(String(item.stage || ""))' in manager
    assert "owner_account_id" not in manager
    assert "owner_display_name" not in manager
    assert "item.tags" not in manager
