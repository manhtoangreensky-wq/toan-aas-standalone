"""Static safety contracts for the Web-native Storyboard Prompt Pack Composer.

The private page can translate Bot-inspired storyboard grammar into a review
surface, but it cannot become a browser-side bridge, a media generator, a
provider/job/payment action, a cached private record or a fake delivery UI.
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
    start = PORTAL.index("function normalizeStoryboardComposerResult(raw)")
    end = PORTAL.index("function normalize", start + 12)
    return PORTAL[start:end]


def _integration_result_validator() -> str:
    start = INTEGRATION.index("function storyboardComposerResultIsSafe(value)")
    end = INTEGRATION.find("\n  // ", start + 12)
    return INTEGRATION[start:end if end != -1 else len(INTEGRATION)]


def _integration_action() -> str:
    start = INTEGRATION.index('if (action === "storyboard-composer-compose")')
    end = INTEGRATION.index('if (action === "storyboard-composer-save-plan")', start)
    return INTEGRATION[start:end]


def test_storyboard_composer_is_a_native_private_video_route_and_catalog_feature() -> None:
    assert 'customerPage("/video-studio/storyboard-composer", "Storyboard Prompt Pack Composer"' in PORTAL
    assert 'layout: "storyboard-composer", type: "storyboard-composer"' in PORTAL
    assert "function renderStoryboardComposer(page, context)" in PORTAL
    assert 'case "storyboard-composer": return renderStoryboardComposer(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="storyboard-composer-compose"' in PORTAL
    assert 'botCompanionPage("/video-studio/storyboard-composer"' not in PORTAL
    assert '"storyboard_composer"' in ENGINES
    assert 'WebFeature("storyboard_composer", "Storyboard Prompt Pack Composer", "video", "/video-studio/storyboard-composer"' in REGISTRY


def test_storyboard_composer_normalizer_and_validator_require_exact_flat_boundary() -> None:
    normalizer = _portal_normalizer()
    validator = _integration_result_validator()
    assert "function normalizeStoryboardComposerResult(raw)" in PORTAL
    assert "function storyboardComposerResultIsSafe(value)" in INTEGRATION
    for field in (
        "input_persisted",
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
        "fact_checked",
        "rights_verified",
    ):
        assert f"source.{field} !== false" in normalizer
        assert f"data.{field} === false" in validator
    assert 'source.execution !== "web_native_deterministic_storyboard_composer_only"' in normalizer
    assert 'data.execution === "web_native_deterministic_storyboard_composer_only"' in validator

    for source in (normalizer, validator):
        for key in (
            "template",
            "platform",
            "aspect_ratio",
            "duration_seconds",
            "style",
            "goal",
            "language",
            "idea_choice",
            "creative_directions",
            "selected_direction",
            "visual_canon",
            "shots",
            "scene_prompts",
            "meta_ai_prompts",
            "caption",
            "hashtags",
            "cta",
            "cautions",
            "review_before_use",
        ):
            assert key in source
    for state_field in (
        "storyboardComposerEnabled: source.storyboardComposerEnabled === true",
        "storyboardComposerResult: normalizeStoryboardComposerResult(source.storyboardComposerResult)",
        "storyboardComposerSaveSource: normalizeStoryboardComposerPlanSaveSource(source.storyboardComposerSaveSource)",
        "storyboardComposerSaveReceipt: normalizeStoryboardComposerPlanSaveReceipt(source.storyboardComposerSaveReceipt)",
    ):
        assert state_field in PORTAL

    normalized_return = normalizer[normalizer.rindex("return {"):]
    # The result object may use JavaScript property shorthand for a local
    # validated `shots` variable; either representation preserves the exact
    # renderer-facing array and must remain present.
    assert "shots:" in normalized_return or "shots," in normalized_return
    assert "scene_prompts:" in normalized_return
    assert "meta_ai_prompts:" in normalized_return

    renderer_start = PORTAL.index("function renderStoryboardComposerResult")
    renderer_end = PORTAL.index("function renderStoryboardComposer(page, context)", renderer_start)
    renderer = PORTAL[renderer_start:renderer_end]
    assert "safeText" in renderer
    assert "review_before_use" in renderer
    for forbidden in ("output_url", "job_id", "video_url", "preview_url", "asset_url", "payment_url", "download_url"):
        assert forbidden not in renderer


def test_storyboard_composer_uses_only_signed_csrf_native_api_without_browser_persistence() -> None:
    for helper in ("storyboardComposerPayload", "storyboardComposerResultIsSafe"):
        assert f"function {helper}" in INTEGRATION
    assert '"storyboard-composer-compose": Boolean(account && me.csrf_token && storyboardComposerEnabled)' in INTEGRATION
    assert '"/video-studio/storyboard-composer": account && storyboardComposerEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/video-studio/tools/storyboard-composer", {' in INTEGRATION
    assert "storyboardComposerResult: data" in INTEGRATION
    assert "storyboardComposerResult: {}," in INTEGRATION

    action = _integration_action().lower()
    for forbidden in (
        "bridgeavailable",
        "core bridge",
        "/payments",
        "/jobs",
        "payos",
        "idempotency_key",
        "localstorage",
        "sessionstorage",
        "provider",
    ):
        assert forbidden not in action
    assert "storyboardcomposerpayload(fields)" in action
    assert "storyboardcomposerresultissafe(data)" in action


def test_storyboard_composer_save_is_explicit_content_free_and_tab_bound() -> None:
    for helper in (
        "storyboardComposerPlanSaveSource",
        "storyboardComposerPlanSaveSourceMatchesResult",
        "storyboardComposerPlanSaveReceipt",
    ):
        assert f"function {helper}" in INTEGRATION
    assert '"storyboard-composer-save-plan": Boolean(account && me.csrf_token && storyboardComposerEnabled)' in INTEGRATION
    assert 'data-portal-action="storyboard-composer-save-plan"' in PORTAL
    assert 'api("/video-studio/tools/storyboard-composer/save", {' in INTEGRATION
    assert 'scope = "video-studio:storyboard-composer:save-plan"' in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "storyboardComposerPlanSaveReceipt(result.data)" in INTEGRATION
    assert "storyboardComposerSaveReceipt: receipt" in INTEGRATION
    save_start = INTEGRATION.index('if (action === "storyboard-composer-save-plan")')
    save_end = INTEGRATION.index('if (action === "video-studio-refresh")', save_start)
    save_action = INTEGRATION[save_start:save_end].lower()
    for forbidden in ("localstorage", "sessionstorage", "/payments", "/jobs", "payos"):
        assert forbidden not in save_action
    receipt_start = PORTAL.index("const STORYBOARD_COMPOSER_PLAN_SAVE_FALSE_BOUNDARY_FIELDS")
    receipt_end = PORTAL.index("const SUBTITLE_FORMAT_LAB_MODES", receipt_start)
    receipt = PORTAL[receipt_start:receipt_end]
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
        assert boundary in receipt


def test_storyboard_composer_backend_stays_request_only_and_never_claims_delivery() -> None:
    assert "class StoryboardComposerRequest(BaseModel)" in ROUTER
    assert "class StoryboardComposerResult(BaseModel)" in ROUTER
    assert '@router.post("/tools/storyboard-composer")' in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/storyboard-composer")')
    # The explicit persistent handoff is a separate endpoint.  Keep the
    # original Composer itself request-only even as the native Video Plan save
    # route is added below it.
    end = ROUTER.index('@router.post("/tools/storyboard-composer/save")', start)
    endpoint = ROUTER[start:end]
    assert "_require_enabled" in endpoint
    assert "web_native_deterministic_storyboard_composer_only" in ROUTER
    for forbidden_call in ("_idempotent(", "transaction(", "_record_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_storyboard_composer_save_is_a_separate_server_recomputed_video_plan_handoff() -> None:
    start = ROUTER.index('@router.post("/tools/storyboard-composer/save")')
    end = ROUTER.index('@router.get("/summary")', start)
    endpoint = ROUTER[start:end]
    for token in (
        "StoryboardComposerPlanSaveRequest",
        "Depends(require_csrf)",
        "_compose_storyboard_composer(payload)",
        "_storyboard_composer_to_video_plan(payload, composer)",
        "web_video_plans",
        "_insert_plan_version",
        "_insert_scene_version",
        "_event(",
        "_idempotent(",
        "web.video.storyboard_composer.save_plan",
        '"destination": "video_plan"',
    ):
        assert token in endpoint
    assert "web_native_video_plan_server_recomputed" in ROUTER
    for forbidden in (
        "copyfast_bridge",
        "httpx.",
        "requests.",
        "payos",
        "create_video",
        "provider_client",
    ):
        assert forbidden not in endpoint.lower()


def test_storyboard_composer_is_responsive_and_never_pwa_cached() -> None:
    for selector in (
        ".portal-storyboard-composer",
        ".portal-storyboard-composer-intro",
        ".portal-storyboard-composer-layout",
        ".portal-storyboard-composer-form",
        ".portal-storyboard-composer-boundary",
        ".portal-storyboard-composer-result",
        ".portal-storyboard-composer-canon",
        ".portal-storyboard-composer-timeline",
        ".portal-storyboard-composer-prompts",
        ".portal-storyboard-composer-review",
    ):
        assert selector in CSS
    assert "@media" in CSS

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/video-studio/storyboard-composer"' not in shell
    assert '"/video-studio/storyboard-composer"' in private_paths
    assert '"/" + "api/v1/video-studio"' in private_paths
    assert '"/api/v1/video-studio"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
