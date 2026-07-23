"""Focused contracts preventing stale Support Desk reads from crossing views."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _function_source(name: str, next_name: str) -> str:
    start = INTEGRATION.index(f"async function {name}(")
    end = INTEGRATION.index(f"async function {next_name}(", start)
    return INTEGRATION[start:end]


def test_support_reads_are_epoch_guarded_by_signed_session_and_native_route() -> None:
    for epoch in (
        "supportSessionEpoch",
        "supportAdvisorHydrationEpoch",
        "supportCustomerListHydrationEpoch",
        "supportCustomerDetailHydrationEpoch",
        "supportAdminListHydrationEpoch",
        "supportAdminDetailHydrationEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    helper = INTEGRATION[INTEGRATION.index("function supportRequestIsCurrent"):INTEGRATION.index("async function hydrateSupportDesk")]
    for requirement in (
        "sessionEpoch === supportSessionEpoch",
        "currentPortalPath() === expectedPath",
        "isNativeSupportPath(expectedPath)",
        "base().supportDeskEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper


def test_support_advisor_discards_stale_or_malformed_guidance_before_rendering() -> None:
    helper = INTEGRATION[
        INTEGRATION.index("function supportAdvisorRequestIsCurrent"):
        INTEGRATION.index("async function hydrateSupportDesk")
    ]
    for requirement in (
        "requestEpoch === supportAdvisorHydrationEpoch",
        "sessionEpoch === supportSessionEpoch",
        'currentPortalPath() === "/support"',
        "base().supportDeskEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper

    hydration = _function_source("hydrateSupportAdvisor", "hydrateSupportDesk")
    assert "const requestEpoch = ++supportAdvisorHydrationEpoch;" in hydration
    assert 'merge({ supportAdvisor: {}, supportAdvisorReadState: "loading", supportAdvisorSelection: category });' in hydration
    assert 'api(`/support/advisor?category=${encodeURIComponent(category)}`)' in hydration
    assert "const projection = supportAdvisorGuideProjection(result);" in hydration
    assert "if (!supportAdvisorRequestIsCurrent(requestEpoch, sessionEpoch))" in hydration
    assert 'merge({ supportAdvisor: {}, supportAdvisorReadState: "guarded", supportAdvisorSelection: category });' in hydration


def test_customer_and_staff_support_hydrators_ignore_late_responses_before_merge() -> None:
    customer_list = _function_source("hydrateSupportDesk", "hydrateSupportCase")
    customer_case = _function_source("hydrateSupportCase", "hydrateSupportAdmin")
    admin_list = _function_source("hydrateSupportAdmin", "hydrateSupportAdminCase")
    admin_case = _function_source("hydrateSupportAdminCase", "hydrateOperations")

    assert "const requestEpoch = ++supportCustomerListHydrationEpoch;" in customer_list
    assert "return { stale: true };" in customer_list
    assert "if (!supportRequestIsCurrent(requestEpoch, supportCustomerListHydrationEpoch, sessionEpoch, currentPath)) return { stale: true };" in customer_list

    assert "const route = `/tickets/${caseId}`;" in customer_case
    assert "const requestEpoch = ++supportCustomerDetailHydrationEpoch;" in customer_case
    assert "const triageResult = await api" in customer_case
    assert "if (!supportRequestIsCurrent(requestEpoch, supportCustomerDetailHydrationEpoch, sessionEpoch, route)) return null;" in customer_case

    assert 'const route = "/admin/support";' in admin_list
    assert "const requestEpoch = ++supportAdminListHydrationEpoch;" in admin_list
    assert "if (!supportRequestIsCurrent(requestEpoch, supportAdminListHydrationEpoch, sessionEpoch, route)) return { stale: true };" in admin_list

    assert "const route = `/admin/support/${caseId}`;" in admin_case
    assert "const requestEpoch = ++supportAdminDetailHydrationEpoch;" in admin_case
    assert "const staffResult = role === \"manager\" ? await api" in admin_case
    assert "if (!supportRequestIsCurrent(requestEpoch, supportAdminDetailHydrationEpoch, sessionEpoch, route)) return null;" in admin_case
