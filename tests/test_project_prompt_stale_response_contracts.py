"""Focused race-safety contracts for private plans, projects and prompts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _source(name: str, next_name: str) -> str:
    start = INTEGRATION.index(f"async function {name}(")
    end = INTEGRATION.index(f"async function {next_name}(", start)
    return INTEGRATION[start:end]


def test_campaign_and_project_reads_are_session_route_and_order_fenced() -> None:
    for epoch in (
        "campaignSessionEpoch",
        "campaignListHydrationEpoch",
        "campaignDetailHydrationEpoch",
        "projectCenterSessionEpoch",
        "projectCenterListHydrationEpoch",
        "projectCenterDetailHydrationEpoch",
        "studioDocumentDetailHydrationEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    campaign_helper = INTEGRATION[
        INTEGRATION.index("function campaignRequestIsCurrent"):
        INTEGRATION.index("async function hydrateCampaignPlans")
    ]
    for requirement in (
        "sessionEpoch === campaignSessionEpoch",
        "currentPortalPath() === expectedPath",
        "isCampaignWorkspacePath(expectedPath)",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in campaign_helper

    project_helper = INTEGRATION[
        INTEGRATION.index("function projectCenterRequestIsCurrent"):
        INTEGRATION.index("function validWorkspaceDraftId")
    ]
    for requirement in (
        "sessionEpoch === projectCenterSessionEpoch",
        "currentPortalPath() === expectedPath",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in project_helper

    campaigns = _source("hydrateCampaignPlans", "hydrateCampaignPlanDetail")
    campaign_detail = _source("hydrateCampaignPlanDetail", "hydrateProjects")
    projects = _source("hydrateProjects", "hydrateMemoryCenter")
    project_detail = _source("hydrateProjectDetail", "hydrateProjectPackages")
    document = _source("hydrateStudioDocument", "hydrateAccountActivity")

    assert "const requestEpoch = ++campaignListHydrationEpoch;" in campaigns
    assert "campaignRequestIsCurrent(requestEpoch, campaignListHydrationEpoch, sessionEpoch, expectedPath)" in campaigns
    assert "const requestEpoch = ++campaignDetailHydrationEpoch;" in campaign_detail
    assert "campaignRequestIsCurrent(requestEpoch, campaignDetailHydrationEpoch, sessionEpoch, path)" in campaign_detail
    assert "const requestEpoch = ++projectCenterListHydrationEpoch;" in projects
    assert "projectCenterRequestIsCurrent(requestEpoch, projectCenterListHydrationEpoch, sessionEpoch, expectedPath)" in projects
    assert "const requestEpoch = ++projectCenterDetailHydrationEpoch;" in project_detail
    assert "++studioDocumentDetailHydrationEpoch;" in project_detail
    assert "const requestEpoch = ++studioDocumentDetailHydrationEpoch;" in document
    assert "projectCenterRequestIsCurrent(requestEpoch, studioDocumentDetailHydrationEpoch, sessionEpoch, expectedPath)" in document
    assert "String(document.project_id || \"\") !== expectedProjectId" in document


def test_prompt_library_and_gallery_reads_discard_late_private_responses() -> None:
    for epoch in (
        "promptLibrarySessionEpoch",
        "promptLibraryListHydrationEpoch",
        "promptTemplateHydrationEpoch",
        "freePromptGallerySessionEpoch",
        "freePromptGalleryListHydrationEpoch",
        "freePromptGalleryDetailHydrationEpoch",
    ):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    prompt_helper = INTEGRATION[
        INTEGRATION.index("function promptLibraryRequestIsCurrent"):
        INTEGRATION.index("function freePromptGalleryRequestIsCurrent")
    ]
    for requirement in (
        "sessionEpoch === promptLibrarySessionEpoch",
        "currentPortalPath() === expectedPath",
        "isNativePromptLibraryPath(expectedPath)",
        "base().promptLibraryEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in prompt_helper

    gallery_helper = INTEGRATION[
        INTEGRATION.index("function freePromptGalleryRequestIsCurrent"):
        INTEGRATION.index("async function hydratePromptLibrary")
    ]
    for requirement in (
        "sessionEpoch === freePromptGallerySessionEpoch",
        "currentPortalPath() === expectedPath",
        'expectedPath === "/free-prompt-gallery"',
        "base().freePromptGalleryEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in gallery_helper

    library = _source("hydratePromptLibrary", "hydrateFreePromptGallery")
    gallery = _source("hydrateFreePromptGallery", "hydrateFreePromptGalleryDetail")
    gallery_detail = _source("hydrateFreePromptGalleryDetail", "hydratePromptTemplate")
    template = _source("hydratePromptTemplate", "hydrateMediaWorkspace")

    assert "const requestEpoch = ++promptLibraryListHydrationEpoch;" in library
    assert "++promptTemplateHydrationEpoch;" in library
    assert "promptLibraryRequestIsCurrent(requestEpoch, promptLibraryListHydrationEpoch, sessionEpoch, path)" in library
    assert "promptTemplateHydrationEpoch === detailEpochAtRequestStart" in library
    assert "const requestEpoch = ++freePromptGalleryListHydrationEpoch;" in gallery
    assert "++freePromptGalleryDetailHydrationEpoch;" in gallery
    assert "freePromptGalleryRequestIsCurrent(requestEpoch, freePromptGalleryListHydrationEpoch, sessionEpoch, expectedPath)" in gallery
    assert "freePromptGalleryDetailHydrationEpoch !== detailEpochAtRequestStart" in gallery
    assert "const requestEpoch = ++freePromptGalleryDetailHydrationEpoch;" in gallery_detail
    assert "freePromptGalleryRequestIsCurrent(requestEpoch, freePromptGalleryDetailHydrationEpoch, sessionEpoch, expectedPath)" in gallery_detail
    assert "const requestEpoch = ++promptTemplateHydrationEpoch;" in template
    assert "promptLibraryRequestIsCurrent(requestEpoch, promptTemplateHydrationEpoch, sessionEpoch, route)" in template
