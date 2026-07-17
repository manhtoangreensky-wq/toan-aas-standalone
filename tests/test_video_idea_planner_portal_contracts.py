"""Static wiring and safety contracts for the Web-native Video Idea Planner.

The Bot-derived conversation is intentionally translated into a private,
request-only Web planning surface.  These checks keep the page wired to the
two bounded API operations without turning it into a Bot, provider, media,
job, wallet, or payment execution surface.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
BACKEND = (ROOT / "copyfast_video_studio.py").read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    """Return a small static source region without coupling to line numbers."""

    offset = text.index(start)
    return text[offset:text.index(end, offset + len(start))]


def test_video_idea_planner_has_a_private_native_route_renderer_and_actions() -> None:
    route = "/video-studio/idea-planner"

    assert 'customerPage("/video-studio/idea-planner", "Video Idea Planner"' in PORTAL
    assert 'layout: "video-idea-planner", type: "video-idea-planner"' in PORTAL
    assert "function renderVideoIdeaPlanner(page, context)" in PORTAL
    assert 'case "video-idea-planner": return renderVideoIdeaPlanner(page, context);' in PORTAL
    assert 'data-portal-action="video-idea-planner-compose"' in PORTAL
    assert 'data-portal-action="video-idea-planner-save-plan"' in PORTAL
    assert '["/video-studio/idea-planner", "Video Idea Planner", ICONS.video]' in PORTAL
    assert 'botCompanionPage("/video-studio/idea-planner"' not in PORTAL
    assert route in INTEGRATION


def test_video_idea_planner_uses_only_its_two_bounded_api_operations() -> None:
    compose = 'api("/video-studio/tools/video-idea-planner", {'
    save = 'api("/video-studio/tools/video-idea-planner/save", {'

    assert compose in INTEGRATION
    assert save in INTEGRATION
    assert INTEGRATION.count(compose) == 1
    assert INTEGRATION.count(save) == 1
    for capability in (
        '"video-idea-planner-compose"',
        '"video-idea-planner-save-plan"',
    ):
        assert capability in INTEGRATION


def test_video_idea_planner_keeps_the_no_execution_boundary_explicit() -> None:
    result_validator = _section(
        INTEGRATION,
        "function videoIdeaPlannerResultIsSafe(value)",
        "function videoIdeaPlanSaveSource(raw)",
    )
    receipt_validator = _section(
        INTEGRATION,
        "function videoIdeaPlanSaveReceipt(value)",
        "// Cinematic Concept Composer",
    )

    assert '"execution": "web_native_deterministic_video_idea_only"' in BACKEND
    assert '"execution": "web_native_video_plan_server_recomputed"' in BACKEND
    for field in (
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "source_media_inspected",
        "provider_called",
        "video_created",
        "preview_created",
        "output_created",
        "job_created",
        "payment_started",
        "wallet_mutated",
        "publish_action_created",
    ):
        assert f'"{field}": False' in BACKEND
        assert f"data.{field} === false" in result_validator or f"data.{field} === false" in receipt_validator

    # A successful explicit save is only a server-recomputed private Video Plan
    # draft; it must not permit a second execution endpoint from the browser.
    assert 'data.destination !== "video_plan"' in receipt_validator
    assert 'data.draft_recomputed_on_server !== true' in receipt_validator
    assert 'data.web_video_plan_persisted !== true' in receipt_validator


def test_video_idea_planner_is_included_in_the_compact_mobile_workspace_scope() -> None:
    mobile_nav = _section(PORTAL, "function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")

    assert '"/video-studio/idea-planner"' in mobile_nav
    assert 'path.startsWith("/video-studio/")' in mobile_nav
