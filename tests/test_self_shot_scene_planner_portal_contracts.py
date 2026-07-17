"""Static wiring and safety contracts for Self-shot Scene Planner.

The Bot-inspired scene-planning conversation is a signed, private Web-native
planning surface.  It must collect an explicit right-to-use acknowledgement,
but it must never become an implicit Bot, provider, media, job, wallet, or
payment execution flow.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
BACKEND = (ROOT / "copyfast_video_studio.py").read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    """Return one small, named source region without using fragile line numbers."""

    offset = text.index(start)
    return text[offset:text.index(end, offset + len(start))]


def _action_block(action: str) -> str:
    start = INTEGRATION.index(f'if (action === "{action}")')
    following = INTEGRATION.find('\n    if (action === "', start + 20)
    return INTEGRATION[start:following if following != -1 else len(INTEGRATION)]


def test_self_shot_scene_planner_is_a_private_route_with_desktop_and_mobile_navigation() -> None:
    route = "/video-studio/self-shot-planner"
    desktop_nav = _section(PORTAL, "function navGroups(context, currentPage)", "function matchesRouteFamily")
    current_nav = _section(PORTAL, "function isNavCurrent(linkPath, page)", "function isMobileNavCurrent(key, page)")
    mobile_nav = _section(PORTAL, "function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")

    assert 'customerPage("/video-studio/self-shot-planner", "Self-shot Scene Planner"' in PORTAL
    assert 'layout: "self-shot-scene-planner", type: "self-shot-scene-planner"' in PORTAL
    assert "function renderSelfShotScenePlanner(page, context)" in PORTAL
    assert 'case "self-shot-scene-planner": return renderSelfShotScenePlanner(page, context);' in PORTAL
    assert 'data-portal-action="self-shot-scene-planner-compose"' in PORTAL
    assert 'data-portal-action="self-shot-scene-planner-save-plan"' in PORTAL
    assert route in desktop_nav
    assert f'if (linkPath === "{route}") return path === "{route}";' in current_nav
    assert f'"{route}"' in mobile_nav
    assert 'botCompanionPage("/video-studio/self-shot-planner"' not in PORTAL


def test_self_shot_scene_planner_has_only_two_bounded_signed_api_operations() -> None:
    compose = 'api("/video-studio/tools/self-shot-scene-planner", {'
    save = 'api("/video-studio/tools/self-shot-scene-planner/save", {'
    compose_action = _action_block("self-shot-scene-planner-compose").lower()
    save_action = _action_block("self-shot-scene-planner-save-plan").lower()

    assert compose in INTEGRATION
    assert save in INTEGRATION
    assert INTEGRATION.count(compose) == 1
    assert INTEGRATION.count(save) == 1
    for capability in (
        '"self-shot-scene-planner-compose"',
        '"self-shot-scene-planner-save-plan"',
    ):
        assert capability in INTEGRATION
    assert '@router.post("/tools/self-shot-scene-planner")' in BACKEND
    assert '@router.post("/tools/self-shot-scene-planner/save")' in BACKEND

    # Compose may only submit the signed native request.  The explicit save is
    # permitted to create a private Video Plan draft, never a runtime job.
    for action in (compose_action, save_action):
        for forbidden_call in (
            'api("/jobs',
            'api("/payments',
            'api("/wallet',
            'api("/internal',
            "window.telegram",
            "payos",
            "fetch(",
        ):
            assert forbidden_call not in action


def test_self_shot_scene_planner_requires_explicit_consent_and_right_to_use() -> None:
    renderer = _section(PORTAL, "function renderSelfShotScenePlanner(page, context)", "function renderPage(page, context)")
    compose_action = _action_block("self-shot-scene-planner-compose").lower()
    backend_lower = BACKEND.lower()

    # A planner may turn a user's own recording brief into text directions only
    # after the user explicitly acknowledges both consent and right-to-use.
    assert "consent" in renderer.lower()
    assert any(marker in renderer.lower() for marker in ("right_to_use", "right-to-use", "quyền sử dụng"))
    assert "consent" in compose_action
    assert "right" in compose_action
    assert "consent" in backend_lower
    assert "right" in backend_lower


def test_self_shot_scene_planner_keeps_provider_media_job_payment_and_bot_calls_off() -> None:
    boundary = _section(
        BACKEND,
        "def _self_shot_scene_boundary()",
        "def _self_shot_scene_plan_save_boundary(",
    )
    compose_endpoint = _section(
        BACKEND,
        '@router.post("/tools/self-shot-scene-planner")',
        '@router.post("/tools/self-shot-scene-planner/save")',
    ).lower()

    assert '"execution": "web_native_deterministic_self_shot_scene_planner_only"' in boundary
    for field in (
        "input_persisted",
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "source_media_inspected",
        "provider_called",
        "image_created",
        "video_created",
        "audio_created",
        "preview_created",
        "output_created",
        "job_created",
        "payment_started",
        "wallet_mutated",
        "asset_saved",
        "publish_action_created",
        "rights_verified",
    ):
        assert f'"{field}": False' in boundary

    # The compose endpoint is request-only.  Durable persistence, if chosen,
    # belongs exclusively to its distinct server-recomputed Video Plan save.
    for forbidden_call in ("_idempotent(", "transaction(", "_record_audit(", "_event(", "provider", "telegram", "wallet", "payment", "job"):
        assert forbidden_call not in compose_endpoint
