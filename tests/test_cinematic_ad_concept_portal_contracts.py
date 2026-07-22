"""Static privacy and contract checks for Cinematic Ad Concept Composer.

The page is a signed, transient creative-planning surface.  It may display a
carefully bounded Bot-inspired idea, but it must never become a browser-side
bridge, provider request, job/payment request, cached private record or fake
media delivery UI.
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
MIGRATION_CONTRACT = (ROOT / "docs" / "migration" / "CINEMATIC_AD_CONCEPT_CONTRACT.md").read_text(encoding="utf-8")


def _portal_normalizer() -> str:
    start = PORTAL.index("function normalizeCinematicConceptResult(raw)")
    end = PORTAL.index("function normalize", start + 12)
    return PORTAL[start:end]


def _integration_result_validator() -> str:
    start = INTEGRATION.index("function cinematicConceptResultIsSafe(value)")
    end = INTEGRATION.find("\n  // ", start + 12)
    return INTEGRATION[start:end if end != -1 else len(INTEGRATION)]


def _integration_action() -> str:
    start = INTEGRATION.index('if (action === "cinematic-concept-compose")')
    end = INTEGRATION.index('if (action === "cinematic-concept-save-plan")', start)
    return INTEGRATION[start:end]


def _integration_save_action() -> str:
    start = INTEGRATION.index('if (action === "cinematic-concept-save-plan")')
    end = INTEGRATION.index('if (action === "storyboard-composer-compose")', start)
    return INTEGRATION[start:end]


def _cinematic_concept_save_panel() -> str:
    start = PORTAL.index("function renderCinematicConceptPlanSavePanel")
    end = PORTAL.index("function renderCinematicConcept(page, context)", start)
    return PORTAL[start:end]


def _cinematic_concept_css() -> str:
    start = CSS.index("/* Cinematic Concept Composer")
    end = CSS.index("/* Storyboard Prompt Pack", start)
    return CSS[start:end]


def test_cinematic_concept_is_a_native_private_video_route_and_catalog_feature() -> None:
    assert 'customerPage("/video-studio/cinematic-concept", "Cinematic Ad Concept Composer"' in PORTAL
    assert 'layout: "cinematic-concept", type: "cinematic-concept"' in PORTAL
    assert "function renderCinematicConcept(page, context)" in PORTAL
    assert 'case "cinematic-concept": return renderCinematicConcept(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="cinematic-concept-compose"' in PORTAL
    assert 'botCompanionPage("/video-studio/cinematic-concept"' not in PORTAL
    assert '"cinematic_ad_concept"' in ENGINES
    assert 'WebFeature("cinematic_ad_concept", "Cinematic Ad Concept Composer", "video", "/video-studio/cinematic-concept"' in REGISTRY


def test_cinematic_concept_migration_copy_distinguishes_transient_compose_from_explicit_owner_plan_save() -> None:
    """Catalog/engine/docs must not present a Bot callback as a durable save."""

    for source in (REGISTRY, ENGINES):
        assert "server-recomputed owner Web Video Plan Draft" in source or "server-recompute input gốc" in source
        assert "save/lock/finalize" in source
        assert "render" in source
        assert "delivery" in source

    for marker in (
        "POST /api/v1/video-studio/tools/cinematic-concept/save",
        '"destination": "video_plan"',
        "server validates the strict bounded request",
        "pending_bot_save_created",
        "generation_started",
        "Frozen Bot callback disposition",
        "CINEMATIC_AD_RUNTIME_CONTRACT_REQUIRED",
        "admin_video_smoke",
        "message_mode: \"bot_default\"",
        "music-direction prompt",
        "The Bot and Web both support Vietnamese",
        "Chinese",
    ):
        assert marker in MIGRATION_CONTRACT


def test_cinematic_concept_normalizer_and_validator_require_the_exact_flat_boundary() -> None:
    normalizer = _portal_normalizer()
    validator = _integration_result_validator()
    assert "function normalizeCinematicConceptResult(raw)" in PORTAL
    assert "function cinematicConceptResultIsSafe(value)" in INTEGRATION

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
    assert 'source.execution !== "web_native_deterministic_cinematic_concept_only"' in normalizer
    assert 'data.execution === "web_native_deterministic_cinematic_concept_only"' in validator

    # The browser must accept only the exact response family: no loose or
    # legacy output/asset/job fields can flow into transient render state.
    for source in (normalizer, validator):
        for key in (
            "message_theme",
            "style",
            "language",
            "idea_choice",
            "motion_choice",
            "video_duration_variant",
            "music_choice",
            "creative_directions",
            "selected_direction",
            "scripts",
            "storyboard",
            "shot_list",
            "image_prompts",
            "video_prompts",
            "motion_plan",
            "music_direction",
            "cautions",
            "review_before_use",
        ):
            assert key in source
    for state_field in (
        "cinematicConceptEnabled: source.cinematicConceptEnabled === true",
        "cinematicConceptResult: normalizeCinematicConceptResult(source.cinematicConceptResult)",
        "cinematicConceptSaveSource: normalizeCinematicConceptPlanSaveSource(source.cinematicConceptSaveSource)",
        "cinematicConceptSaveReceipt: normalizeCinematicConceptPlanSaveReceipt(source.cinematicConceptSaveReceipt)",
    ):
        assert state_field in PORTAL
    # The normalizer may reject malformed receipts, but it must not silently
    # drop the valid Bot-derived shot list before the renderer sees it.
    # Other normalizers may define local helper functions between this one and
    # the next `function normalize…` declaration, so do not use `rindex` over
    # that broad static slice.  Assert the exact Cinematic return mapping
    # instead: it proves the normalized shot list is preserved rather than
    # merely mentioned while validating the receipt.
    assert "shot_list: shotList" in normalizer

    renderer_start = PORTAL.index("function renderCinematicConceptResult")
    renderer_end = PORTAL.index("function renderCinematicConcept(page, context)", renderer_start)
    renderer = PORTAL[renderer_start:renderer_end]
    assert "safeText" in renderer
    assert "review_before_use" in renderer
    for forbidden in ("output_url", "job_id", "video_url", "preview_url", "asset_url", "payment_url"):
        assert forbidden not in renderer


def test_cinematic_concept_uses_only_signed_csrf_native_api_without_browser_persistence() -> None:
    for helper in ("cinematicConceptPayload", "cinematicConceptResultIsSafe"):
        assert f"function {helper}" in INTEGRATION
    assert '"cinematic-concept-compose": Boolean(account && me.csrf_token && cinematicConceptEnabled)' in INTEGRATION
    assert '"/video-studio/cinematic-concept": account && cinematicConceptEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/video-studio/tools/cinematic-concept", {' in INTEGRATION
    assert "cinematicConceptResult: data" in INTEGRATION
    assert "cinematicConceptResult: {}," in INTEGRATION

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
    assert "cinematicconceptpayload(fields)" in action
    assert "cinematicconceptresultissafe(data)" in action


def test_cinematic_concept_save_is_explicit_content_free_and_tab_bound() -> None:
    for helper in (
        "cinematicConceptPlanSaveSource",
        "cinematicConceptPlanSaveSourceMatchesResult",
        "cinematicConceptPlanSaveReceipt",
    ):
        assert f"function {helper}" in INTEGRATION
    for helper in (
        "normalizeCinematicConceptPlanSaveSource",
        "normalizeCinematicConceptPlanSaveReceipt",
        "renderCinematicConceptPlanSavePanel",
    ):
        assert f"function {helper}" in PORTAL
    assert '"cinematic-concept-save-plan": Boolean(account && me.csrf_token && cinematicConceptEnabled)' in INTEGRATION
    assert 'data-portal-action="cinematic-concept-save-plan"' in PORTAL
    assert 'api("/video-studio/tools/cinematic-concept/save", {' in INTEGRATION
    assert 'destination: "video_plan"' in INTEGRATION
    assert 'scope = "video-studio:cinematic-concept:save-plan"' in INTEGRATION
    assert "acquireSubmission(scope, JSON.stringify(payload))" in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "cinematicConceptPlanSaveReceipt(result.data)" in INTEGRATION
    assert "cinematicConceptSaveReceipt: receipt" in INTEGRATION
    assert "cinematicConceptSaveSource: {}, cinematicConceptSaveReceipt: {}" in INTEGRATION

    save_action = _integration_save_action().lower()
    for forbidden in ("localstorage", "sessionstorage", "/payments", "/jobs", "payos"):
        assert forbidden not in save_action
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
        assert boundary in PORTAL
    assert 'source.execution !== "web_native_video_plan_server_recomputed"' in PORTAL
    assert "Receipt không giữ product, message, concept, storyboard hoặc prompt" in PORTAL


def test_cinematic_concept_backend_stays_request_only_and_never_claims_delivery() -> None:
    assert "class CinematicAdConceptRequest(BaseModel)" in ROUTER
    assert "class CinematicAdConceptResult(BaseModel)" in ROUTER
    assert '@router.post("/tools/cinematic-concept")' in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/cinematic-concept")')
    end = ROUTER.index('@router.post("/tools/cinematic-concept/save")', start)
    endpoint = ROUTER[start:end]
    assert "_require_enabled" in endpoint
    assert "web_native_deterministic_cinematic_concept_only" in ROUTER
    for forbidden_call in ("_idempotent(", "transaction(", "_record_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_cinematic_concept_save_is_a_separate_server_recomputed_video_plan_handoff() -> None:
    start = ROUTER.index('@router.post("/tools/cinematic-concept/save")')
    end = ROUTER.index('@router.post("/tools/storyboard-composer")', start)
    endpoint = ROUTER[start:end]
    for token in (
        "CinematicAdConceptPlanSaveRequest",
        "Depends(require_csrf)",
        "_compose_cinematic_ad_concept(payload)",
        "_cinematic_ad_concept_to_video_plan(payload, composer)",
        "web_video_plans",
        "_insert_plan_version",
        "_insert_scene_version",
        "_event(",
        "_idempotent(",
        "web.video.cinematic_concept.save_plan",
        '"destination": "video_plan"',
    ):
        assert token in endpoint
    assert "class CinematicAdConceptPlanSaveRequest(CinematicAdConceptRequest)" in ROUTER
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


def test_cinematic_concept_is_responsive_and_never_pwa_cached() -> None:
    for selector in (
        ".portal-cinematic-concept",
        ".portal-cinematic-concept-intro",
        ".portal-cinematic-concept-layout",
        ".portal-cinematic-concept-form",
        ".portal-cinematic-concept-boundary",
        ".portal-cinematic-concept-result",
        ".portal-cinematic-concept-storyboard",
        ".portal-cinematic-concept-prompts",
        ".portal-cinematic-concept-review",
    ):
        assert selector in CSS
    assert "@media" in CSS

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/video-studio/cinematic-concept"' not in shell
    assert '"/video-studio/cinematic-concept"' in private_paths
    assert '"/" + "api/v1/video-studio"' in private_paths
    assert '"/api/v1/video-studio"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER


def test_cinematic_concept_frontend_prevents_duplicate_saves_and_drops_stale_responses() -> None:
    panel = _cinematic_concept_save_panel()
    save_action = _integration_save_action()
    compose_action = _integration_action()

    # Once the content-free receipt is valid, the renderer returns the receipt
    # surface before it can render another primary save control.
    assert panel.index("const receiptPlan") < panel.index("const saveControl")
    assert 'if (receiptPlan && validVideoStudioPlanId(receiptPlan.id)) {' in panel
    assert panel.index('if (receiptPlan && validVideoStudioPlanId(receiptPlan.id)) {') < panel.index("const saveControl")
    assert "return `${savePanel}" not in panel

    # The handler has the same defence in case a stale/replayed DOM event
    # bypasses the visual control. It happens before an idempotency submission
    # can be acquired with a fresh key.
    assert "const savedReceipt = cinematicConceptPlanSaveReceipt(base().cinematicConceptSaveReceipt);" in save_action
    assert "if (savedReceipt) {" in save_action
    assert save_action.index("if (savedReceipt) {") < save_action.index("acquireSubmission(scope, JSON.stringify(payload))")

    for token in (
        "let cinematicConceptSessionEpoch = 0;",
        "let cinematicConceptComposeRequestEpoch = 0;",
        "let cinematicConceptSaveRequestEpoch = 0;",
        "function cinematicConceptRequestIsCurrent(kind, requestEpoch, sessionEpoch, expectedAccountId, expectedPath)",
        "String(account.id || \"\") === expectedAccountId",
        "currentPortalPath() === expectedPath",
        "sessionEpoch === cinematicConceptSessionEpoch",
    ):
        assert token in INTEGRATION
    assert 'const requestEpoch = ++cinematicConceptComposeRequestEpoch;' in compose_action
    assert 'cinematicConceptRequestIsCurrent("compose", requestEpoch, sessionEpoch, expectedAccountId, expectedPath)' in compose_action
    assert 'const requestEpoch = ++cinematicConceptSaveRequestEpoch;' in save_action
    assert 'cinematicConceptRequestIsCurrent("save", requestEpoch, sessionEpoch, expectedAccountId, expectedPath)' in save_action


def test_cinematic_concept_editing_visible_brief_invalidates_old_save_source() -> None:
    save_action = _integration_save_action()

    # The result panel's save control is explicitly paired to the visible
    # compose form. Editing that form marks the old receipt/result stale and
    # disables the control before an accidental click can save a previous
    # brief.
    assert 'id="cinematic-concept-form"' in PORTAL
    assert 'data-portal-form-id="cinematic-concept-form"' in PORTAL
    assert 'data-cinematic-concept-stale-note' in PORTAL
    assert 'data-cinematic-concept-rendered-result' in PORTAL
    assert 'data-cinematic-concept-saved-receipt' in PORTAL
    assert "function cinematicConceptFormMatchesSavedSource(form)" in PORTAL
    assert "function synchronizeCinematicConceptDraftFreshness(form)" in PORTAL
    assert "control.disabled = disabled;" in PORTAL
    assert "synchronizeCinematicConceptDraftFreshness(form);" in PORTAL

    # The integration handler repeats the same invariant using live form
    # fields, before it can create a retry/idempotency submission. This also
    # protects against stale/replayed DOM events that bypass visual controls.
    assert "function cinematicConceptPlanSaveSourceMatchesCurrentFields(source, fields)" in INTEGRATION
    assert "cinematicConceptPlanSaveSourceMatchesCurrentFields(source, fields)" in save_action
    assert save_action.index("cinematicConceptPlanSaveSourceMatchesCurrentFields(source, fields)") < save_action.index("acquireSubmission(scope, JSON.stringify(payload))")


def test_cinematic_concept_default_message_preserves_only_raw_source_choices() -> None:
    save_action = _integration_save_action()

    # The browser accepts the supported UI choices, but a Bot-default message
    # remains an empty raw source. The server resolves text; rendered text is
    # never promoted back into a later write payload.
    for source in (PORTAL, INTEGRATION):
        assert '"zh"' in source
        assert '"ai_prompt"' in source
        assert '"message_mode"' in source
    assert "const CINEMATIC_CONCEPT_MESSAGE_MODES = new Set([\"provided\", \"bot_default\"]);" in PORTAL
    assert "const CINEMATIC_CONCEPT_MESSAGE_MODES = new Set([\"provided\", \"bot_default\"]);" in INTEGRATION
    assert "message_mode: messageMode" in PORTAL
    assert "message_mode: messageMode" in INTEGRATION
    assert 'messageMode === "bot_default"' in PORTAL
    assert 'messageMode === "bot_default"' in INTEGRATION
    assert 'source.message === ""' in PORTAL
    assert 'selection.message === ""' in INTEGRATION
    assert "message_mode: retainedSource.message_mode" in PORTAL
    assert "function synchronizeCinematicConceptMessageMode(form)" in PORTAL
    assert "message.value = \"\";" in PORTAL
    assert "message.disabled = disabled;" in PORTAL
    assert "aria-live" in PORTAL
    assert '["zh", "中文（简体）"]' in PORTAL
    assert '["ai_prompt", "Prompt nhạc AI (chỉ text)"]' in PORTAL
    assert "cinematicConceptPlanSaveSourceMatchesResult(saveSource, data)" in save_action or "cinematicConceptPlanSaveSourceMatchesResult(source, currentResult)" in save_action


def test_cinematic_concept_component_uses_readable_slate_teal_tokens_and_mobile_controls() -> None:
    css = _cinematic_concept_css()
    for token in (
        "var(--portal-bg)",
        "var(--portal-surface)",
        "var(--portal-surface-strong)",
        "var(--portal-border)",
        "var(--portal-accent)",
        ":focus-visible",
        "min-height: 44px",
    ):
        assert token in css
    assert "linear-gradient" not in css
    for too_small in ("font-size: 7px", "font-size: 8px", "font-size: 9px", "font-size: 10px", "font-size: 11px"):
        assert too_small not in css
