"""Static safety contracts for the Web-native Video Prompt Planner.

The private page may help a signed customer formulate a video direction, but
must never turn that text receipt into a legacy Bot handoff, media source,
provider request, video/preview/output, job, payment, asset, publish action
or PWA-cached private record.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_video_studio.py").read_text(encoding="utf-8")
ENGINES = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _portal_normalizer() -> str:
    start = PORTAL.index("function normalizeVideoPromptPlannerResult(raw)")
    end = PORTAL.index("function normalize", start + 12)
    return PORTAL[start:end]


def _integration_result_validator() -> str:
    start = INTEGRATION.index("function videoPromptPlannerResultIsSafe(value)")
    end = INTEGRATION.index("// A durable Video Plan is a second, confirmed action.", start)
    return INTEGRATION[start:end]


def test_video_prompt_planner_is_a_native_route_and_catalog_feature() -> None:
    assert 'customerPage("/video-studio/prompt-planner", "Video Prompt Planner"' in PORTAL
    assert 'layout: "video-prompt-planner", type: "video-prompt-planner"' in PORTAL
    assert "function renderVideoPromptPlanner(page, context)" in PORTAL
    assert 'case "video-prompt-planner": return renderVideoPromptPlanner(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="video-prompt-plan"' in PORTAL
    assert '["/video-studio/prompt-planner", "Video Prompt Planner", ICONS.video]' in PORTAL
    assert 'botCompanionPage("/video-studio/prompt-planner"' not in PORTAL
    assert '"video_prompt_planner"' in ENGINES
    assert 'WebFeature("video_prompt_planner", "Video Prompt Planner", "video", "/video-studio/prompt-planner"' in REGISTRY


def test_video_prompt_planner_result_is_exact_bounded_and_honest() -> None:
    normalizer = _portal_normalizer()
    validator = _integration_result_validator()
    assert "const VIDEO_PROMPT_PLANNER_MODES" in PORTAL
    assert "function normalizeVideoPromptPlannerResult(raw)" in PORTAL
    assert "function videoPromptPlannerResultIsSafe(value)" in INTEGRATION
    for field in (
        "input_persisted",
        "source_media_inspected",
        "provider_called",
        "video_created",
        "preview_created",
        "output_created",
        "job_created",
        "payment_started",
        "wallet_mutated",
        "asset_saved",
        "publish_action_created",
        "fact_checked",
        "rights_verified",
    ):
        # The portal discards an incomplete server receipt; integration keeps
        # it out of transient state before render.  They use opposite checks
        # (`!==` reject vs `===` accept) by design.
        assert f"source.{field} !== false" in normalizer
        assert f"data.{field} === false" in validator
    assert 'source.execution !== "web_native_deterministic_video_plan_only"' in normalizer
    assert 'data.execution === "web_native_deterministic_video_plan_only"' in validator
    for source in (normalizer, validator):
        assert "style_pack" in source
        assert "action_pack" in source
        assert "audio_mode" in source
        assert "coverage" in source
        assert "cautions" in source
        assert "review_before_use" in source
        assert "shots" in source

    # `language` is request validation only, not a second result/output schema.
    assert "planner.language" not in normalizer
    assert "planner.language" not in validator
    # Response validators must use the backend's exact result bounds.  The
    # form can remain more compact for UX, but a valid server receipt may not
    # be discarded merely because it contains a full-length direction.
    for expectation in (
        "videoPromptPlannerText(planner.motion, 0, 320, true)",
        "videoPromptPlannerText(planner.background, 0, 320, true)",
        "videoPromptPlannerTextList(planner.must_keep, 0, 6, 2, 220)",
        "videoPromptPlannerTextList(planner.must_avoid, 0, 6, 2, 220)",
        "videoPromptPlannerTextList(planner.continuity_locks, 1, 12, 2, 360)",
        "videoPromptPlannerTextList(planner.cautions, 0, 6, 2, 360)",
        "videoPromptPlannerTextList(planner.review_before_use, 1, 6, 2, 360)",
        "videoPromptPlannerText(planner.prompt, 1, 12000, false)",
        "videoPromptPlannerText(planner.negative_prompt, 1, 12000, false)",
    ):
        assert expectation in normalizer
    for expectation in (
        "planner.motion.length <= 320",
        "planner.background.length <= 320",
        "videoPromptPlannerStringListIsSafe(coverage.missing || [], 0, 6, 220)",
        "videoPromptPlannerStringListIsSafe(planner.must_keep || [], 0, 6, 220)",
        "videoPromptPlannerStringListIsSafe(planner.must_avoid || [], 0, 6, 220)",
        "videoPromptPlannerStringListIsSafe(planner.continuity_locks, 1, 12, 360)",
        "videoPromptPlannerStringListIsSafe(planner.cautions || [], 0, 6, 360)",
        "videoPromptPlannerStringListIsSafe(planner.review_before_use, 1, 6, 360)",
        "planner.prompt.length > 0 && planner.prompt.length <= 12000",
        "planner.negative_prompt.length > 0 && planner.negative_prompt.length <= 12000",
        "item[field].length > 0 && item[field].length <= 1200",
    ):
        assert expectation in validator
    for state_field in (
        "videoPromptPlannerEnabled: source.videoPromptPlannerEnabled === true",
        "videoPromptPlannerResult: normalizeVideoPromptPlannerResult(source.videoPromptPlannerResult)",
        "videoPromptPlannerSaveSource: normalizeVideoPromptPlannerPlanSaveSource(source.videoPromptPlannerSaveSource)",
        "videoPromptPlannerSaveReceipt: normalizeVideoPromptPlannerPlanSaveReceipt(source.videoPromptPlannerSaveReceipt)",
    ):
        assert state_field in PORTAL

    start = PORTAL.index("function renderVideoPromptPlannerResult")
    end = PORTAL.index("function renderVideoPromptPlanner(page, context)", start)
    renderer = PORTAL[start:end]
    assert "safeText" in renderer
    assert "review_before_use" in renderer
    assert "output_url" not in renderer
    assert "job_id" not in renderer
    assert "video_url" not in renderer


def test_video_prompt_planner_uses_only_the_signed_csrf_native_api() -> None:
    for helper in ("videoPromptPlannerPayload", "videoPromptPlannerResultIsSafe"):
        assert f"function {helper}" in INTEGRATION
    assert '"video-prompt-plan": Boolean(account && me.csrf_token && videoPromptPlannerEnabled)' in INTEGRATION
    assert '"/video-studio/prompt-planner": account && videoPromptPlannerEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/video-studio/tools/prompt-planner", {' in INTEGRATION
    assert "videoPromptPlannerResult: data" in INTEGRATION
    assert "videoPromptPlannerResult: {}," in INTEGRATION

    start = INTEGRATION.index('if (action === "video-prompt-plan")')
    end = INTEGRATION.index('if (action === "video-prompt-plan-save")', start)
    action = INTEGRATION[start:end].lower()
    for forbidden in (
        "bridgeavailable",
        "core bridge",
        "/payments",
        "/jobs",
        "payos",
        "idempotency_key",
        "localstorage",
        "sessionstorage",
    ):
        assert forbidden not in action
    assert 'api("/providers' not in action
    assert "videopromptplannerpayload(fields)" in action
    assert "videopromptplannerresultissafe(data)" in action


def test_video_prompt_planner_save_is_explicit_content_free_and_tab_bound() -> None:
    for helper in (
        "videoPromptPlannerPlanSaveSource",
        "videoPromptPlannerPlanSaveSourceMatchesResult",
        "videoPromptPlannerPlanSaveReceipt",
    ):
        assert f"function {helper}" in INTEGRATION
    for helper in (
        "normalizeVideoPromptPlannerPlanSaveSource",
        "normalizeVideoPromptPlannerPlanSaveReceipt",
        "renderVideoPromptPlannerSavePanel",
    ):
        assert f"function {helper}" in PORTAL
    assert '"video-prompt-plan-save": Boolean(account && me.csrf_token && videoPromptPlannerEnabled)' in INTEGRATION
    assert 'data-portal-action="video-prompt-plan-save"' in PORTAL
    assert 'api("/video-studio/tools/prompt-planner/save", {' in INTEGRATION
    assert 'destination: "video_plan"' in INTEGRATION
    assert 'scope = "video-studio:prompt-planner:save-plan"' in INTEGRATION
    assert "acquireSubmission(scope, JSON.stringify(payload))" in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "videoPromptPlannerPlanSaveReceipt(result.data)" in INTEGRATION
    assert "videoPromptPlannerSaveReceipt: receipt" in INTEGRATION
    assert "videoPromptPlannerSaveSource: {}, videoPromptPlannerSaveReceipt: {}" in INTEGRATION
    assert "Never send the visible prompt, scene timeline" in INTEGRATION
    save_start = INTEGRATION.index('if (action === "video-prompt-plan-save")')
    save_end = INTEGRATION.index('if (action === "cinematic-concept-compose")', save_start)
    save_action = INTEGRATION[save_start:save_end].lower()
    assert "localstorage" not in save_action
    assert "sessionstorage" not in save_action
    assert "/payments" not in save_action
    assert "/jobs" not in save_action

    receipt_normalizer_start = PORTAL.index("const VIDEO_PROMPT_PLANNER_PLAN_SAVE_FALSE_BOUNDARY_FIELDS")
    receipt_normalizer_end = PORTAL.index("// The Cinematic Concept Composer", receipt_normalizer_start)
    receipt_normalizer = PORTAL[receipt_normalizer_start:receipt_normalizer_end]
    for boundary in (
        "browser_result_persisted",
        "pending_bot_save_created",
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "provider_called",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "asset_saved",
        "publish_action_created",
        "delivery_created",
        "plan_approved",
        "plan_locked",
        "generation_started",
    ):
        assert boundary in receipt_normalizer
    assert 'source.execution !== "web_native_video_plan_server_recomputed"' in receipt_normalizer
    assert "Receipt không giữ brief, prompt, timeline hoặc scene content" in PORTAL


def test_video_prompt_planner_backend_is_request_only_with_no_durable_mutation() -> None:
    assert "class VideoPromptPlannerRequest(BaseModel)" in ROUTER
    assert "class VideoPromptPlannerResult(BaseModel)" in ROUTER
    assert '@router.post("/tools/prompt-planner")' in ROUTER
    assert "VIDEO_PROMPT_PLANNER_MODES" in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/prompt-planner")')
    end = ROUTER.index('@router.post("/tools/prompt-planner/save")', start)
    endpoint = ROUTER[start:end]
    assert "_require_enabled" in endpoint
    assert "_video_prompt_planner_guard" in endpoint
    assert "_compose_video_prompt_plan" in endpoint
    assert '"web_native_deterministic_video_plan_only"' in ROUTER
    for field in (
        '"input_persisted": False',
        '"source_media_inspected": False',
        '"provider_called": False',
        '"video_created": False',
        '"preview_created": False',
        '"output_created": False',
        '"job_created": False',
        '"payment_started": False',
        '"wallet_mutated": False',
        '"asset_saved": False',
        '"publish_action_created": False',
        '"fact_checked": False',
        '"rights_verified": False',
    ):
        assert field in ROUTER
    for forbidden_call in ("_idempotent(", "transaction(", "_record_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_video_prompt_planner_save_is_a_separate_server_recomputed_video_plan_handoff() -> None:
    start = ROUTER.index('@router.post("/tools/prompt-planner/save")')
    end = ROUTER.index('@router.post("/tools/cinematic-concept")', start)
    endpoint = ROUTER[start:end]
    for token in (
        "VideoPromptPlannerPlanSaveRequest",
        "Depends(require_csrf)",
        "_compose_video_prompt_plan(payload)",
        "_video_prompt_planner_to_video_plan(payload, planner)",
        "web_video_plans",
        "_insert_plan_version",
        "_insert_scene_version",
        "_event(",
        "_idempotent(",
        "web.video.prompt_planner.save_plan",
        '"destination": "video_plan"',
    ):
        assert token in endpoint
    assert "class VideoPromptPlannerPlanSaveRequest(VideoPromptPlannerRequest)" in ROUTER
    assert "web_native_video_plan_server_recomputed" in ROUTER
    for forbidden in (
        "copyfast_bridge",
        "httpx.",
        "requests.",
        "payos",
        "provider_client",
        "create_video",
    ):
        assert forbidden not in endpoint.lower()


def test_video_prompt_planner_is_private_responsive_and_never_pwa_cached() -> None:
    for selector in (
        ".portal-video-prompt-planner",
        ".portal-video-prompt-planner-intro",
        ".portal-video-prompt-planner-layout",
        ".portal-video-prompt-planner-form",
        ".portal-video-prompt-planner-boundary",
        ".portal-video-prompt-planner-result",
        ".portal-video-prompt-planner-timeline",
        ".portal-video-prompt-planner-prompts",
        ".portal-video-prompt-planner-cautions",
    ):
        assert selector in CSS

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/video-studio/prompt-planner"' not in shell
    assert '"/video-studio/prompt-planner"' in private_paths
    assert '"/api/v1/video-studio"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
