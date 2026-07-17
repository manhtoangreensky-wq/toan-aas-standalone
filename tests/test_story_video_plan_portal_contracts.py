"""Static Portal/PWA contracts for the prompt-only Story Video Planner."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_story_video_plan_is_a_first_class_private_portal_route() -> None:
    assert 'customerPage("/video-studio/story-video-plan", "Story Video Planner"' in PORTAL
    assert 'layout: "story-video-plan", type: "story-video-plan", fields: [], action: "none"' in PORTAL
    assert "function renderStoryVideoPlan(page, context)" in PORTAL
    assert 'data-portal-action="story-video-plan"' in PORTAL
    assert 'data-portal-route="/video-studio/story-video-plan"' in PORTAL
    assert 'case "story-video-plan": return renderStoryVideoPlan(page, context);' in PORTAL


def test_story_video_payload_boundary_and_action_are_prompt_only() -> None:
    start = INTEGRATION.index("function storyVideoPlanPayload(fields)")
    end = INTEGRATION.index("function storyVideoPlanText", start)
    payload = INTEGRATION[start:end]
    assert "return { topic, language };" in payload
    for forbidden in ("provider", "url", "path", "asset", "job", "payment", "idempotency", "publish"):
        assert f"{forbidden}:" not in payload

    normalizer = INTEGRATION[
        INTEGRATION.index("function storyVideoPlanBoundaryIsSafe"):INTEGRATION.index("// Voice Studio", INTEGRATION.index("function storyVideoPlanBoundaryIsSafe"))
    ]
    for marker in (
        'data.execution === "web_native_deterministic_story_video_plan_only"',
        "data[field] === false",
        'plan.mode === "prompt_only_manual_review"',
        'plan.output_status === "prompt_only_no_real_video"',
        "STORY_VIDEO_WORKFLOWS",
    ):
        assert marker in normalizer

    action = INTEGRATION[
        INTEGRATION.index('if (action === "story-video-plan")'):INTEGRATION.index('if (action === "music-prompt-compose")')
    ]
    assert 'api("/media-factory/story-video-plan"' in action
    assert "storyVideoPlanPayload(fields)" in action
    assert "storyVideoPlanResultIsSafe(data)" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action
    assert "idempotency_key" not in action


def test_story_video_plan_receipts_are_never_pwa_cached() -> None:
    assert '"/video-studio/story-video-plan"' in WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in WORKER
    assert "const BUILD_ID = workerBuildId();" in WORKER
