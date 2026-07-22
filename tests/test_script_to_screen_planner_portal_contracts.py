"""Static contracts for the signed, Web-native Script-to-Screen Planner.

The Web planner takes only the useful text-first shape of Bot Task3D
``vproduct``.  It may generate reviewable direction and explicitly save a
server-recomputed private Video Plan draft.  It must never become a covert Bot,
provider, media, job, wallet, or payment execution surface.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
BACKEND = (ROOT / "copyfast_video_studio.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    offset = text.index(start)
    return text[offset:text.index(end, offset + len(start))]


def _action_block(action: str) -> str:
    marker = f'if (action === "{action}")'
    offset = INTEGRATION.index(marker)
    next_offset = INTEGRATION.find('if (action === "', offset + len(marker))
    return INTEGRATION[offset:] if next_offset < 0 else INTEGRATION[offset:next_offset]


def test_script_to_screen_planner_has_one_native_route_and_keeps_the_episodic_label() -> None:
    route = "/video-studio/script-to-screen-planner"
    desktop_nav = _section(PORTAL, "function navGroups(context, currentPage)", "function matchesRouteFamily")
    mobile_nav = _section(PORTAL, "function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")

    assert 'WebFeature("script_to_screen_planner"' in REGISTRY
    assert 'customerPage("/video-studio/script-to-screen-planner", "Script-to-Screen Planner"' in PORTAL
    assert 'layout: "script-to-screen-planner", type: "script-to-screen-planner"' in PORTAL
    assert "function renderScriptToScreenPlanner(page, context)" in PORTAL
    assert 'case "script-to-screen-planner": return renderScriptToScreenPlanner(page, context);' in PORTAL
    assert route in desktop_nav
    # The compact mobile dock deliberately groups all signed Video Studio
    # workspaces under one stable item instead of duplicating every planner.
    assert 'matchesRouteFamily(path, "/video-studio")' in mobile_nav
    assert "Phim dài tập" in PORTAL
    assert '"multi_scene_film", "Phim dài tập"' in PORTAL
    assert '"multi_scene_film": {"vi": "Phim dài tập", "en": "Episodic series"}' in BACKEND


def test_episodic_series_is_a_bounded_season_map_and_saves_only_one_selected_episode() -> None:
    """The renamed product must expose real episode semantics without runtime."""

    assert 'name: "episode_count"' in PORTAL
    assert 'name: "selected_episode"' in PORTAL
    assert "function scriptToScreenSeriesMarkup(raw)" in PORTAL
    assert "data-script-to-screen-episode-select" in PORTAL
    assert "function scriptToScreenSeriesIsSafe(value, projectKind, sceneCount)" in INTEGRATION
    assert "function synchronizeScriptToScreenEpisodeFields(target)" in INTEGRATION
    assert "function selectScriptToScreenEpisode(target)" in INTEGRATION
    assert 'data-script-to-screen-episode-select' in INTEGRATION
    assert 'form[data-portal-action="script-to-screen-planner-compose"]' in INTEGRATION
    assert 'target.name !== "project_kind" && target.name !== "episode_count"' in INTEGRATION
    assert 'const SCRIPT_TO_SCREEN_SERIES_MODES = new Set(["single_episode", "episodic_series"]);' in INTEGRATION
    assert "source.episode_count === Number(planner.series && planner.series.episode_count)" in INTEGRATION
    assert "source.selected_episode === Number(planner.series && planner.series.selected_episode)" in INTEGRATION
    assert "episode_count: StrictInt | None = None" in BACKEND
    assert "selected_episode: StrictInt | None = None" in BACKEND
    assert '"mode": "episodic_series" if total > 1 else "single_episode"' in BACKEND
    assert "Episode {selected_episode}/{episode_count}" in BACKEND
    assert '"season-{episode_count}"' in BACKEND
    assert '"episode-{selected_episode}"' in BACKEND
    assert "const series = normalizeScriptToScreenSeries(planner.series" in PORTAL
    assert "scriptToScreenSeriesMarkup(planner.series)" in PORTAL


def test_script_to_screen_uses_only_two_bounded_signed_operations() -> None:
    compose = 'api("/video-studio/tools/script-to-screen-planner", {'
    save = 'api("/video-studio/tools/script-to-screen-planner/save", {'
    compose_action = _action_block("script-to-screen-planner-compose").lower()
    save_action = _action_block("script-to-screen-planner-save-plan").lower()

    assert compose in INTEGRATION
    assert save in INTEGRATION
    assert INTEGRATION.count(compose) == 1
    assert INTEGRATION.count(save) == 1
    assert '"script-to-screen-planner-compose": Boolean(account && me.csrf_token && scriptToScreenPlannerEnabled)' in INTEGRATION
    assert '"script-to-screen-planner-save-plan": Boolean(account && me.csrf_token && scriptToScreenPlannerEnabled)' in INTEGRATION
    assert '@router.post("/tools/script-to-screen-planner")' in BACKEND
    assert '@router.post("/tools/script-to-screen-planner/save")' in BACKEND

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


def test_script_to_screen_validates_the_no_execution_boundary_and_private_save_receipt() -> None:
    result_validator = _section(
        INTEGRATION,
        "function scriptToScreenPlannerResultIsSafe(value)",
        "function scriptToScreenPlanSaveSource(raw)",
    )
    receipt_validator = _section(
        INTEGRATION,
        "function scriptToScreenPlanSaveReceipt(value)",
        "// Cinematic Concept Composer",
    )
    boundary = _section(
        BACKEND,
        "def _script_to_screen_boundary()",
        "def _script_to_screen_plan_save_boundary(",
    )

    assert '"execution": "web_native_deterministic_script_to_screen_planner_only"' in boundary
    for field in (
        "input_persisted",
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "provider_called",
        "media_opened",
        "media_created",
        "preview_created",
        "output_created",
        "job_created",
        "wallet_changed",
        "payment_changed",
        "asset_created",
        "published",
        "delivered",
    ):
        assert f'"{field}": False' in BACKEND
        assert f"data.{field} === false" in result_validator or f"data[field] === false" in receipt_validator

    assert 'data.destination !== "video_plan"' in receipt_validator
    assert 'data.execution !== "web_native_script_to_screen_video_plan_server_recomputed"' in receipt_validator
    assert "data.draft_recomputed_on_server !== true" in receipt_validator
    assert "data.web_video_plan_persisted !== true" in receipt_validator
    assert "SCRIPT_TO_SCREEN_SAVE_FALSE_FIELDS.every" in receipt_validator


def test_script_to_screen_uses_the_bounded_bot_panel_and_extra_scene_grammar() -> None:
    """The browser and server must agree on 3–16 plus 0/1/2, never a hidden render batch."""

    assert "scene_count: StrictInt = Field(ge=3, le=16)" in BACKEND
    assert "extra_scene_count: StrictInt = Field(default=0, ge=0, le=2)" in BACKEND
    assert "if self.scene_count + self.extra_scene_count > 18:" in BACKEND
    assert '"skip": {"vi": "không tạo direction ảnh"' in BACKEND
    assert "SCRIPT_TO_SCREEN_EXTRA_SCENE_OPTIONS" in PORTAL
    assert '"2", "Thêm 2 cảnh kết"' in PORTAL
    assert 'name: "scene_count"' in PORTAL and "max: 16" in PORTAL
    assert 'name: "extra_scene_count"' in PORTAL
    assert 'id="script-to-screen-planner-form"' in PORTAL
    assert 'type="button" data-portal-action="script-to-screen-planner-compose" data-portal-route="/video-studio/script-to-screen-planner" data-portal-form-id="script-to-screen-planner-form"' in PORTAL
    assert "SCRIPT_TO_SCREEN_SOURCE_KEYS" in INTEGRATION
    assert "extra_scene_count" in INTEGRATION
    assert "hasExtraSceneCount" in PORTAL
    assert "hasExtraSceneCount" in INTEGRATION
    assert "fields.extra_scene !== (extraSceneCount > 0)" in INTEGRATION
    assert "value.extra_scene !== (extraSceneCount > 0)" in PORTAL
    assert "source.scene_count + source.extra_scene_count" in INTEGRATION


def test_script_to_screen_preserves_current_form_and_fences_stale_save_actions() -> None:
    """A late receipt can never turn an edited brief back into a saveable plan."""

    compose_action = _action_block("script-to-screen-planner-compose")
    save_action = _action_block("script-to-screen-planner-save-plan")
    current_form_match = "scriptToScreenPlanSaveSourceMatchesCurrentFields(source, fields)"

    assert "scriptToScreenPlannerComposePendingRequestEpoch" in INTEGRATION
    assert "function scriptToScreenCurrentFormSaveSource(fields)" in INTEGRATION
    assert "function scriptToScreenPlannerCurrentFormFields(form)" in INTEGRATION
    assert "function reconcileScriptToScreenPlannerSaveControls(route)" in INTEGRATION
    assert "scriptToScreenPlannerCurrentFormFields(form)" in INTEGRATION
    assert "collectFormFields(form)" not in INTEGRATION
    assert "scriptToScreenPlannerComposePendingRequestEpoch = requestEpoch;" in compose_action
    assert "scriptToScreenPlannerComposePendingRequestEpoch === requestEpoch" in compose_action
    assert compose_action.index("scriptToScreenPlannerComposePendingRequestEpoch = requestEpoch;") < compose_action.index("reconcileScriptToScreenPlannerSaveControls(route);")
    assert "scriptToScreenPlannerResult: {}, scriptToScreenPlannerSaveSource: {}" not in compose_action
    assert "scriptToScreenPlannerRequestIsCurrent(\"compose\"" in compose_action
    assert current_form_match in save_action
    assert save_action.index(current_form_match) < save_action.index("acquireSubmission(")
    assert "scriptToScreenPlannerComposePendingRequestEpoch" in save_action
    assert "reconcileScriptToScreenPlannerSaveControls(route);" in save_action
    assert 'new CustomEvent("toanaas:script-to-screen-draft-edited")' in PORTAL
    assert 'window.addEventListener("toanaas:script-to-screen-draft-edited"' in INTEGRATION
    assert 'selectedEpisode.dispatchEvent(new Event("change", { bubbles: true }));' in INTEGRATION
    assert "data-script-to-screen-rendered-result" in PORTAL
    assert "data-script-to-screen-saved-receipt" in PORTAL
    assert "data-portal-form-id=\"script-to-screen-planner-form\"" in PORTAL
    assert "if (!form.id) form.id = \"script-to-screen-planner-form\";" in PORTAL
    assert "function renderScriptToScreenPlannerResult(raw, rawSource, rawReceipt, canSaveToVideoPlan)" in PORTAL
    assert "const receipt = normalizeScriptToScreenPlannerSaveReceipt(rawReceipt);" in PORTAL
    assert "const save = sourceMatches && !alreadySaved" in PORTAL
    assert "const saveAllowed = fresh && !alreadySaved;" in PORTAL
