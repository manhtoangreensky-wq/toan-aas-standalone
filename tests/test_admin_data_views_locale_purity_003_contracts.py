"""Locale-purity contracts for the five generic Admin data routes."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static/portal/portal-i18n.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_five_data_routes_use_closed_locale_owned_hero_and_notes() -> None:
    assert "const ADMIN_DATA_VIEW_ROUTE_KEYS" in PORTAL
    helper = _between(PORTAL, "const ADMIN_DATA_VIEW_ROUTE_KEYS", "function renderAdminDataViewControls")
    render = _between(PORTAL, "function renderAdmin(page, context)", "const BOT_COMPANION_COMMAND_PATTERN")
    title = _between(PORTAL, "function localizedPageTitle(page, context)", "function documentTitle")
    description = _between(PORTAL, "function localizedPageDescription(page)", "function initials")

    for route in ("users", "jobs", "payments", "providers", "tickets"):
        assert f'"/admin/{route}": "{route}"' in helper
    assert "adminDataViewRouteText(page, \"title\", fallback)" in title
    assert "adminDataViewRouteText(page, \"description\", fallback)" in description
    assert "adminDataViewRouteText(page, \"section\"" in PORTAL
    assert "adminDataViewNotes(page)" in render
    assert 'adminDataViewText("notes.integrationTitle"' in render
    assert 'adminDataViewText("notes.safetyTitle"' in render


def test_vi_fixed_data_page_catalogue_contains_no_forbidden_jargon() -> None:
    generic = _between(I18N, "const ADMIN_GENERIC_MESSAGES =", "const ADMIN_FINANCE_WORKSPACE_MESSAGES =")
    vi_generic = _between(generic, "vi: {", "en: {")
    surfaces = _between(I18N, "const ADMIN_DATA_SURFACE_MESSAGES =", "const ADMIN_DATA_VIEW_MESSAGES =")
    vi_surface = _between(surfaces, "vi: {", "en: {")
    data_view = _between(I18N, "const ADMIN_DATA_VIEW_MESSAGES =", "const ADMIN_GENERIC_MESSAGES =")
    vi_view = _between(data_view, "vi: {", "en: {")
    delivery_center = _between(
        I18N,
        "const DELIVERY_CENTER_MESSAGES =",
        "const SUPPORT_TICKET_MESSAGES =",
    )
    vi_delivery = _between(
        delivery_center,
        "Object.assign(DELIVERY_CENTER_MESSAGES.vi, {",
        "Object.assign(DELIVERY_CENTER_MESSAGES.en, {",
    )

    owned_keys = (
        "adminGeneric.guard.canonicalTitle",
        "adminGeneric.guard.canonicalBody",
        "adminGeneric.data.body",
        "adminGeneric.access.readOnlyBody",
        "adminGeneric.module.jobs",
        "adminGeneric.jobs.column.job",
        "adminGeneric.jobs.column.canonicalCost",
        "adminGeneric.jobs.column.outputEngine",
        "adminGeneric.jobs.column.delivery",
        "adminGeneric.jobs.column.actions",
        "adminDataSurface.serverScope",
        "adminDataView.notes.session",
        "adminDataView.notes.safety",
    )
    source = "\n".join((vi_generic, vi_surface, vi_view))
    values = []
    for key in owned_keys:
        match = re.search(rf'"{re.escape(key)}":\s*"([^"]*)"', source)
        assert match, key
        values.append(match.group(1))

    forbidden = (
        "canonical", "csrf", "audit", "core bridge", "permission", "redaction",
        "ownership", "adapter", "signed session", "business rules", "job center",
        "output engine", "delivery", "browser", "role check",
    )
    lowered = "\n".join(values).lower()
    assert not [token for token in forbidden if token in lowered]

    jobs_shared_keys = (
        "deliveryCenter.status.output.none",
        "deliveryCenter.status.output.held",
        "deliveryCenter.status.output.reportedWaiting",
        "deliveryCenter.status.output.reportedPending",
        "deliveryCenter.status.delivery.pending",
        "deliveryCenter.status.delivery.vault",
        "deliveryCenter.status.delivery.validatedWaiting",
        "deliveryCenter.status.delivery.unavailable",
        "deliveryCenter.status.delivery.reported",
        "deliveryCenter.status.delivery.completedWaiting",
        "deliveryCenter.cost.ledger",
        "adminGeneric.jobAction.invalidId",
        "adminGeneric.jobAction.noneAvailable",
        "adminGeneric.jobAction.disabledTitle",
        "adminGeneric.jobAction.retryConfirm",
        "adminGeneric.jobAction.retryLabel",
        "adminGeneric.jobAction.refundConfirm",
    )
    jobs_source = "\n".join((vi_generic, vi_delivery))
    jobs_values = []
    for key in jobs_shared_keys:
        match = re.search(rf'"{re.escape(key)}":\s*"([^"]*)"', jobs_source)
        assert match, key
        jobs_values.append(match.group(1))

    jobs_forbidden = (
        "metadata", "output", "validation", "delivery", "url", "ledger",
        "retry", "action", "job", "canonical", "csrf", "audit", "core bridge",
        "signed session", "browser",
    )
    jobs_lowered = "\n".join(jobs_values).lower()
    leaked = [
        token for token in jobs_forbidden
        if re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", jobs_lowered)
    ]
    assert not leaked


def test_cancelled_and_ticket_statuses_are_locale_owned() -> None:
    state_keys = _between(PORTAL, "const STATE_I18N_KEYS", "function stateLabel")
    data_view = _between(I18N, "const ADMIN_DATA_VIEW_MESSAGES =", "const ADMIN_GENERIC_MESSAGES =")
    assert 'cancelled: "states.cancelled"' in state_keys
    assert I18N.count('"states.cancelled"') == 3
    for key in (
        "new", "reviewing", "waitingUser", "waitingProvider",
        "refundPending", "resolved", "closed", "unknown",
    ):
        assert data_view.count(f'"adminDataView.ticketStatus.{key}"') == 3
