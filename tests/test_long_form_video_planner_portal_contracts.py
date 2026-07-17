"""Static portal contracts for the Web-native Long-form Video Planner.

The Bot-derived planning conversation is intentionally translated into a
private, signed Web workflow.  It may compose a deterministic long-form
roadmap and explicitly save a recomputed private Video Plan draft, but it
must not become a Bot, bridge, provider, media, job, wallet, or payment
execution surface.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
BACKEND = (ROOT / "copyfast_video_studio.py").read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    """Return a source region without coupling this contract to line numbers."""

    offset = text.index(start)
    return text[offset:text.index(end, offset + len(start))]


def _action_block(action: str) -> str:
    """Return exactly one action handler, independent of its next sibling."""

    marker = f'if (action === "{action}")'
    offset = INTEGRATION.index(marker)
    next_offset = INTEGRATION.find('if (action === "', offset + len(marker))
    return INTEGRATION[offset:] if next_offset < 0 else INTEGRATION[offset:next_offset]


def test_long_form_video_planner_has_a_private_native_route_renderer_and_actions() -> None:
    route = "/video-studio/long-form-planner"

    assert 'customerPage("/video-studio/long-form-planner",' in PORTAL
    assert 'layout: "long-form-planner", type: "long-form-planner"' in PORTAL
    assert "function renderLongFormPlanner(page, context)" in PORTAL
    assert 'case "long-form-planner": return renderLongFormPlanner(page, context);' in PORTAL
    assert 'data-portal-action="long-form-roadmap-compose"' in PORTAL
    assert 'data-portal-action="long-form-roadmap-save-plan"' in PORTAL
    assert route in INTEGRATION
    assert 'botCompanionPage("/video-studio/long-form-planner"' not in PORTAL


def test_long_form_video_planner_uses_only_its_two_bounded_api_operations() -> None:
    compose = 'api("/video-studio/tools/long-form-roadmap", {'
    save = 'api("/video-studio/tools/long-form-roadmap/save", {'

    assert compose in INTEGRATION
    assert save in INTEGRATION
    assert INTEGRATION.count(compose) == 1
    assert INTEGRATION.count(save) == 1
    assert '"long-form-roadmap-compose": Boolean(account && me.csrf_token && longFormRoadmapEnabled)' in INTEGRATION
    assert '"long-form-roadmap-save-plan": Boolean(account && me.csrf_token && longFormRoadmapEnabled)' in INTEGRATION
    assert '"/video-studio/long-form-planner": account && longFormRoadmapEnabled ? "ready" : "guarded"' in INTEGRATION


def test_long_form_video_planner_keeps_the_no_execution_boundary_explicit() -> None:
    result_validator = _section(
        INTEGRATION,
        "function longFormRoadmapResultIsSafe(value)",
        "function longFormRoadmapPlanSaveSource(raw)",
    )
    receipt_validator = _section(
        INTEGRATION,
        "function longFormRoadmapPlanSaveReceipt(value)",
        "// Video Idea Planner",
    )

    # The result and explicit save receipt must prove that the Web action was
    # planning-only.  The backend literals make this contract reviewable even
    # if a future renderer changes.
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

    # Saving is a second, explicit, server-recomputed private Video Plan draft
    # only; no browser action may dispatch a provider/media/job/payment flow.
    assert 'data.destination !== "video_plan"' in receipt_validator
    assert 'data.draft_recomputed_on_server !== true' in receipt_validator
    assert 'data.web_video_plan_persisted !== true' in receipt_validator
    for action in (
        _action_block("long-form-roadmap-compose").lower(),
        _action_block("long-form-roadmap-save-plan").lower(),
    ):
        assert 'api("/providers' not in action
        assert "/payments" not in action
        assert "/jobs" not in action
        assert "payos" not in action
        assert "localstorage" not in action
        assert "sessionstorage" not in action


def test_long_form_video_planner_is_included_in_the_compact_mobile_studio_scope() -> None:
    mobile_nav = _section(PORTAL, "function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")

    assert 'matchesRouteFamily(path, "/video-studio")' in mobile_nav
