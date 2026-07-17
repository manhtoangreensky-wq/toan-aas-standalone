"""Targeted stale-response contracts for private coordination workspaces."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _source(name: str, next_name: str) -> str:
    start = INTEGRATION.index(f"async function {name}(")
    end = INTEGRATION.index(f"async function {next_name}(", start)
    return INTEGRATION[start:end]


def _assert_epochs_and_helper(prefix: str, epochs: tuple[str, ...], helper: str, flag: str) -> None:
    for epoch in epochs:
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION
    helper_source = INTEGRATION[INTEGRATION.index(f"function {helper}"):INTEGRATION.index("async function", INTEGRATION.index(f"function {helper}"))]
    for requirement in (
        f"sessionEpoch === {prefix}SessionEpoch",
        "currentPortalPath() === expectedPath",
        "Boolean(base().session && base().session.authenticated === true)",
        f"base().{flag} === true",
    ):
        assert requirement in helper_source


def test_content_handoff_owner_detail_and_staff_reads_are_session_route_fenced() -> None:
    _assert_epochs_and_helper(
        "contentHandoff",
        (
            "contentHandoffSessionEpoch",
            "contentHandoffOwnerListHydrationEpoch",
            "contentHandoffDetailHydrationEpoch",
            "contentHandoffStaffListHydrationEpoch",
        ),
        "contentHandoffRequestIsCurrent",
        "contentHandoffEnabled",
    )
    owner = _source("hydrateContentHandoffs", "hydrateContentHandoffRecord")
    detail = _source("hydrateContentHandoffRecord", "hydrateContentHandoffStaffQueue")
    staff = _source("hydrateContentHandoffStaffQueue", "hydratePartnerCrm")

    assert "const requestEpoch = ++contentHandoffOwnerListHydrationEpoch;" in owner
    assert '["/content/handoffs", "/content/handoffs/new"].includes(expectedPath)' in owner
    assert "if (!contentHandoffRequestIsCurrent(requestEpoch, contentHandoffOwnerListHydrationEpoch, sessionEpoch, expectedPath)) return { stale: true };" in owner

    assert "const requestEpoch = ++contentHandoffDetailHydrationEpoch;" in detail
    assert "if (currentPortalPath() !== route) return null;" in detail
    assert "if (!contentHandoffRequestIsCurrent(requestEpoch, contentHandoffDetailHydrationEpoch, sessionEpoch, route)) return null;" in detail

    assert "const requestEpoch = ++contentHandoffStaffListHydrationEpoch;" in staff
    assert 'const expectedPath = "/admin/content-handoffs";' in staff
    assert "if (!contentHandoffRequestIsCurrent(requestEpoch, contentHandoffStaffListHydrationEpoch, sessionEpoch, expectedPath)) return { stale: true };" in staff


def test_partner_crm_owner_detail_and_manager_reads_are_session_route_fenced() -> None:
    _assert_epochs_and_helper(
        "partnerCrm",
        (
            "partnerCrmSessionEpoch",
            "partnerCrmListHydrationEpoch",
            "partnerCrmDetailHydrationEpoch",
            "partnerCrmManagerHydrationEpoch",
        ),
        "partnerCrmRequestIsCurrent",
        "partnerCrmEnabled",
    )
    owner = _source("hydratePartnerCrm", "hydratePartnerCrmLead")
    detail = _source("hydratePartnerCrmLead", "hydratePartnerCrmManagerDirectory")
    manager = _source("hydratePartnerCrmManagerDirectory", "hydrateContentVariantHistory")

    assert "const requestEpoch = ++partnerCrmListHydrationEpoch;" in owner
    assert '["/crm/leads", "/crm/leads/new"].includes(expectedPath)' in owner
    assert "if (!partnerCrmRequestIsCurrent(requestEpoch, partnerCrmListHydrationEpoch, sessionEpoch, expectedPath)) return { stale: true };" in owner

    assert "const requestEpoch = ++partnerCrmDetailHydrationEpoch;" in detail
    assert "if (currentPortalPath() !== route) return null;" in detail
    assert "if (!partnerCrmRequestIsCurrent(requestEpoch, partnerCrmDetailHydrationEpoch, sessionEpoch, route)) return null;" in detail

    assert "const requestEpoch = ++partnerCrmManagerHydrationEpoch;" in manager
    assert 'const expectedPath = "/admin/crm/leads";' in manager
    assert "if (!partnerCrmRequestIsCurrent(requestEpoch, partnerCrmManagerHydrationEpoch, sessionEpoch, expectedPath)) return { stale: true };" in manager
