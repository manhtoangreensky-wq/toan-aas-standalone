"""Focused UI contracts for the Web-native Customer Care ERP surface.

The browser may present an Odoo-style board and forms, but it must never make
staff, payment, provider or external-delivery decisions.  These checks keep
the portal wired to the narrow Support Desk contracts only.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_customer_care_hydration_is_staff_scoped_and_cleared_between_sessions() -> None:
    integration = _read("static/portal/integration.js")

    assert 'api("/support/admin/care/queues")' in integration
    assert 'api("/support/admin/care/staff")' in integration
    assert "normalizedSupportCareQueues" in integration
    assert "normalizedSupportCareStaff" in integration
    assert "normalizedSupportCareHistory" in integration
    assert "supportAdminCareQueues: []" in integration
    assert "supportAdminCareStaff: []" in integration
    assert "supportAdminCareHistory: []" in integration
    assert "Only a manager may obtain the roster" in integration
    assert "An operator's 403 is expected" in integration


def test_customer_care_writes_keep_csrf_confirmation_idempotency_and_revision() -> None:
    integration = _read("static/portal/integration.js")

    triage_start = integration.index('if (action === "support-admin-care-triage")')
    escalation_start = integration.index('if (action === "support-admin-care-escalation")')
    operations_start = integration.index('if (action === "operations-refresh")')
    triage = integration[triage_start:escalation_start]
    escalation = integration[escalation_start:operations_start]

    assert "/support/admin/cases/${encodeURIComponent(caseId)}/care/triage" in triage
    assert "expected_revision: revision" in triage
    assert "confirm: true" in triage
    assert "idempotency_key: submission.key" in triage
    assert "await hydrateSupportAdminCase(caseId);" in triage
    assert "/support/admin/cases/${encodeURIComponent(caseId)}/care/escalation" in escalation
    assert "expected_revision: revision" in escalation
    assert "confirm: true" in escalation
    assert "idempotency_key: submission.key" in escalation
    assert "supportCareTriagePayload" in integration
    assert "supportCareEscalationPayload" in integration
    assert "validateWebSupportText(operationNote)" in integration
    assert "validateWebSupportText(reason)" in integration


def test_portal_renders_erp_board_controls_and_redacted_activity_only_for_live_staff_view() -> None:
    portal = _read("static/portal/portal.js")

    assert "function renderSupportCareQueueBoard(context)" in portal
    assert "Customer Care Board" in portal
    assert "Kanban hàng đợi theo team, SLA và escalation" in portal
    assert "function renderSupportCareControls(page, context)" in portal
    assert 'data-portal-action="support-admin-care-triage"' in portal
    assert 'data-portal-action="support-admin-care-escalation"' in portal
    assert "function renderSupportAdminBase(page, context)" in portal
    assert "function renderSupportAdmin(page, context)" in portal
    assert "function renderSupportAdminCaseDetailBase(page, context)" in portal
    assert "function renderSupportAdminCaseDetail(page, context)" in portal
    assert "hasLiveStaffRole" in portal
    assert "không hiển thị account ID, email, raw audit target hay payload ngoài Web" in portal
    assert "PayOS" in portal
    assert "provider" in portal


def test_customer_care_queue_filters_are_fixed_enums_with_no_account_id_selector() -> None:
    integration = _read("static/portal/integration.js")
    portal = _read("static/portal/portal.js")

    helper = _between(integration, "function supportAdminCaseFilterPayload", "function supportCaseListOffset")
    for requirement in (
        'SUPPORT_CARE_ASSIGNMENT_FILTERS = new Set(["all", "mine", "assigned", "unassigned"])',
        "SUPPORT_CARE_TEAM_QUEUES.has(teamQueue)",
        "SUPPORT_CARE_SLA_CLASSES.has(slaClass)",
        'SUPPORT_CARE_SLA_STATUSES = new Set(["all", "unavailable", "pending", "within_target", "breached", "overdue_unacknowledged"])',
        "SUPPORT_CARE_SLA_STATUSES.has(careSlaStatus)",
        "SUPPORT_CARE_ESCALATION_STATES.has(escalationState)",
        "team_queue: teamQueue",
        "assignment",
        "sla_class: slaClass",
        "care_sla_status: careSlaStatus",
        "escalation_state: escalationState",
    ):
        assert requirement in integration or requirement in helper
    assert "assigned_account_id" not in helper
    assert "provider" not in helper
    assert "payment" not in helper

    path = _between(integration, "function supportAdminCasesPath", "function supportCustomerListRoute")
    for requirement in (
        "team_queue: normalized.team_queue",
        "assignment: normalized.assignment",
        "sla_class: normalized.sla_class",
        "care_sla_status: normalized.care_sla_status",
        "escalation_state: normalized.escalation_state",
    ):
        assert requirement in path
    assert "assigned_account_id" not in path

    view = _between(portal, "function renderSupportAdminBase", "function renderSupportAdmin(page")
    for requirement in (
        'name="team_queue"',
        'name="assignment"',
        'name="sla_class"',
        'name="care_sla_status"',
        'name="escalation_state"',
        "supportCareFilterOptions",
        "Trạng thái SLA là mốc tiếp nhận nội bộ do máy chủ tính",
        "browser không gửi account ID, giờ hệ thống hoặc external state",
        "data-portal-no-transient",
        'data-portal-action="support-admin-cases-filter-clear"',
    ):
        assert requirement in view
    assert '"mine", "Việc của tôi"' in portal
    assert 'name="assigned_account_id"' not in view

    clear_handler = _between(integration, 'if (action === "support-admin-cases-filter-clear")', 'if (action === "support-admin-cases-page")')
    for requirement in (
        'q: ""',
        'state: "all"',
        'team_queue: "all"',
        'assignment: "all"',
        'sla_class: "all"',
        'care_sla_status: "all"',
        'escalation_state: "all"',
        "hydrateSupportAdmin",
    ):
        assert requirement in clear_handler
