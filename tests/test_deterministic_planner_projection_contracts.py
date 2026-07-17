"""Portal contracts for transient, no-execution planning receipts.

These tool results are already schema/boundary-checked by integration.js.
This focused contract prevents the presentation normalizer from discarding a
successful response during a Portal remount or passing a raw boundary object
through to the renderer.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def test_deterministic_planner_receipts_survive_strict_portal_projection() -> None:
    start = PORTAL.index("const DETERMINISTIC_PLANNER_BOUNDARY_FIELDS")
    end = PORTAL.index("function normalizeBootstrap", start)
    projection = PORTAL[start:end]
    for marker in (
        "deterministicPlannerBoundaryIsSafe",
        "normalizeTrendResearchResult",
        "normalizeMediaFactoryResult",
        "normalizeCreativeFlowResult",
        "normalizeStoryVideoPlanResult",
        "input_persisted",
        "provider_called",
        "media_output_created",
        "publish_action_created",
        "TREND_RECEIPT_WORKFLOWS",
        "MEDIA_FACTORY_RECEIPT_WORKFLOWS",
        "CREATIVE_FLOW_RECEIPT_WORKFLOWS",
        "STORY_VIDEO_RECEIPT_WORKFLOWS",
    ):
        assert marker in projection

    bootstrap_start = PORTAL.index("function normalizeBootstrap")
    bootstrap_end = PORTAL.index("function getBootstrap", bootstrap_start)
    bootstrap = PORTAL[bootstrap_start:bootstrap_end]
    for marker in (
        "const trendResearchResult = normalizeTrendResearchResult(source.trendResearchResult);",
        "const mediaFactoryResult = normalizeMediaFactoryResult(source.mediaFactoryResult);",
        "const creativeFlowResult = normalizeCreativeFlowResult(source.creativeFlowResult);",
        "const storyVideoPlanResult = normalizeStoryVideoPlanResult(source.storyVideoPlanResult);",
        "trendResearchResult,",
        "mediaFactoryResult,",
        "creativeFlowResult,",
        "storyVideoPlanResult,",
    ):
        assert marker in bootstrap

    # Results retain only the named planning containers. Boundary flags, Bot,
    # wallet/payment/job/provider/action data are checked then dropped.
    for return_marker in (
        "return {\n      plan: {",
        "return {\n      blueprint: {",
        "return {\n      flow: {",
    ):
        assert return_marker in projection
