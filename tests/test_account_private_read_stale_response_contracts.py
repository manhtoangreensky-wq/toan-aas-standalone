"""Contracts preventing late small-account reads from crossing sessions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _source(name: str, next_name: str) -> str:
    start = INTEGRATION.index(f"async function {name}(")
    end = INTEGRATION.index(f"async function {next_name}(", start)
    return INTEGRATION[start:end]


def test_account_activity_and_workspace_drafts_are_session_route_fenced() -> None:
    for epoch in (
        "accountActivitySessionEpoch",
        "accountActivityHydrationEpoch",
        "workspaceDraftSessionEpoch",
        "workspaceDraftHydrationEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    activity_helper = INTEGRATION[
        INTEGRATION.index("function accountActivityRequestIsCurrent"):
        INTEGRATION.index("function workspaceDraftRequestIsCurrent")
    ]
    for requirement in (
        "requestEpoch === accountActivityHydrationEpoch",
        "sessionEpoch === accountActivitySessionEpoch",
        "currentPortalPath() === expectedPath",
        'expectedPath === "/account/activity"',
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in activity_helper

    draft_helper = INTEGRATION[
        INTEGRATION.index("function workspaceDraftRequestIsCurrent"):
        INTEGRATION.index("async function hydrateAccountActivity")
    ]
    assert '["/workspace", "/dashboard"].includes(expectedPath)' in draft_helper
    assert "sessionEpoch === workspaceDraftSessionEpoch" in draft_helper

    activity = _source("hydrateAccountActivity", "hydrateWorkspaceDrafts")
    drafts = _source("hydrateWorkspaceDrafts", "hydrateCanonicalAdminData")
    assert "const requestEpoch = ++accountActivityHydrationEpoch;" in activity
    assert "accountActivityRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)" in activity
    assert "const requestEpoch = ++workspaceDraftHydrationEpoch;" in drafts
    assert "workspaceDraftRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)" in drafts
    assert "workspaceDraftListing: isLibraryView" in drafts
    assert "workspaceDraftListing: emptyListing" in drafts
    assert "accountActivity: []," in INTEGRATION
    assert "workspaceDrafts: []," in INTEGRATION
    assert "workspaceDraftListing: workspaceDraftListingProjection(" in INTEGRATION


def test_telegram_link_and_payment_options_discard_late_private_metadata() -> None:
    for epoch in (
        "telegramLinkStatusSessionEpoch",
        "telegramLinkStatusHydrationEpoch",
        "paymentOptionsSessionEpoch",
        "paymentOptionsHydrationEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    link_helper = INTEGRATION[
        INTEGRATION.index("function telegramLinkStatusRequestIsCurrent"):
        INTEGRATION.index("function paymentOptionsRequestIsCurrent")
    ]
    assert '["/onboarding", "/account"].includes(expectedPath)' in link_helper
    assert "sessionEpoch === telegramLinkStatusSessionEpoch" in link_helper

    payment_helper = INTEGRATION[
        INTEGRATION.index("function paymentOptionsRequestIsCurrent"):
        INTEGRATION.index("async function hydrateLinkStatus")
    ]
    assert 'expectedPath === "/wallet/topup"' in payment_helper
    assert "sessionEpoch === paymentOptionsSessionEpoch" in payment_helper

    link = _source("hydrateLinkStatus", "hydratePaymentOptions")
    payment = _source("hydratePaymentOptions", "hydrateCampaignPlans")
    assert "const requestEpoch = ++telegramLinkStatusHydrationEpoch;" in link
    assert "telegramLinkStatusRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)" in link
    assert "const requestEpoch = ++paymentOptionsHydrationEpoch;" in payment
    assert "paymentOptionsRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)" in payment
    assert "paymentOptions: {}," in INTEGRATION
