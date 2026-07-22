"""Focused browser contracts for the finite Creative Motion Guide.

The server tests validate the text-only endpoint.  These checks protect the
customer-facing decision flow: every visible button has one allowed next step,
old form data cannot leak into another topic mode, and a guarded reply is not
mistaken for a transport failure or a finished guide.
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
MIGRATION_CONTRACT = (ROOT / "docs" / "migration" / "CREATIVE_MOTION_GUIDE_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")


def _portal_form_sync() -> str:
    start = PORTAL.index("function synchronizeCreativeMotionGuideForm(form)")
    end = PORTAL.index("function markCreativeMotionGuideDraftEdited(form)", start)
    return PORTAL[start:end]


def _integration_action() -> str:
    start = INTEGRATION.index('if (["creative-motion-guide-suggest", "creative-motion-guide-refresh"].includes(action))')
    end = INTEGRATION.index('if (action === "cinematic-concept-compose")', start)
    return INTEGRATION[start:end]


def _integration_payload() -> str:
    start = INTEGRATION.index("function creativeMotionGuidePayload(fields, options)")
    end = INTEGRATION.index("function creativeMotionGuideChoiceIsSafe", start)
    return INTEGRATION[start:end]


def _integration_current_fields() -> str:
    start = INTEGRATION.index("function creativeMotionGuideCurrentFormFields(form)")
    end = INTEGRATION.index("function creativeMotionGuideFormMatchesPayload", start)
    return INTEGRATION[start:end]


def test_creative_motion_guide_is_a_private_native_route_not_image_motion_or_pwa_shell() -> None:
    assert 'customerPage("/video-studio/motion-guide", "Creative Motion Guide"' in PORTAL
    assert 'layout: "creative-motion-guide", type: "creative-motion-guide"' in PORTAL
    assert "function renderCreativeMotionGuide(page, context)" in PORTAL
    assert 'case "creative-motion-guide": return renderCreativeMotionGuide(page, context);' in PORTAL
    assert 'WebFeature("creative_motion_guide", "Creative Motion Guide", "video", "/video-studio/motion-guide"' in REGISTRY
    assert '"creative_motion_guide"' in ENGINES
    assert '"/video-studio/motion-guide"' in SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES", 1)[1]
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/video-studio/motion-guide"' not in shell
    assert "Image Motion Planner" in PORTAL
    assert "không là Image Motion Planner" in PORTAL


def test_creative_motion_guide_rejects_cross_mode_custom_data_without_erasing_the_draft() -> None:
    sync = _portal_form_sync()
    payload = _integration_payload()

    # The hidden field remains in the DOM so a user may switch back, but both
    # normalizers deliberately omit it from a catalog topic.
    assert 'topicKind === "custom" ? creativeMotionGuideText(fields.custom_topic, 0, 500, true) : ""' in PORTAL
    assert 'const customTopic = topicKind === "custom"' in payload
    assert 'videoStudioBody(source.custom_topic, "Chủ đề tự nhập", 500, true)' in payload
    assert "customInput.disabled = formDisabled || !isCustom;" in sync
    assert "preserve its DOM value" in PORTAL


def test_creative_motion_guide_enforces_finite_suggestion_steps_and_one_processing_lane() -> None:
    sync = _portal_form_sync()
    action = _integration_action()

    # Refresh has no fallback-to-generate behaviour.  It needs the exact
    # rendered set for the current category/language/set before it can advance.
    assert "!canSuggest || !matchingSuggestions || flowPending" in sync
    assert 'if (action === "creative-motion-guide-refresh" && !sameExistingTopic)' in action
    assert "Hãy tạo đúng ba gợi ý" in action
    assert "const currentSet = Number(fields.suggestion_set);" in action
    assert "currentSet === Number(existingSet.suggestion_set)" in action

    # Suggest, refresh, card selection and compose all see the same in-flight
    # lane; the form controls also lock, so editing cannot strand page state.
    for token in (
        "let creativeMotionGuideSuggestionsPendingRequestEpoch = 0;",
        "let creativeMotionGuideComposePendingRequestEpoch = 0;",
        "function creativeMotionGuidePendingKind()",
        "function synchronizeCreativeMotionGuideBusyState(route)",
        "if (creativeMotionGuidePendingKind())",
        "form.dataset.creativeMotionGuideBusy = pendingKind;",
        "const flowPending = busyKind === \"suggestions\" || busyKind === \"compose\";",
        "data-creative-motion-guide-topic-kind], [data-creative-motion-guide-language], [data-creative-motion-guide-style]",
        "form.dataset.creativeMotionGuideState = flowPending ? \"processing\"",
    ):
        assert token in INTEGRATION or token in sync

    assert 'creativeMotionGuideSuggestionsPendingRequestEpoch = requestEpoch;' in action
    assert 'creativeMotionGuideComposePendingRequestEpoch = requestEpoch;' in action
    assert action.count("synchronizeCreativeMotionGuideBusyState(route);") >= 4


def test_creative_motion_guide_handles_server_guarded_envelope_and_preserves_disabled_form_values() -> None:
    action = _integration_action()
    fields = _integration_current_fields()
    payload = _integration_payload()

    # api() turns {ok:false} into error.payload; this branch must verify the
    # boundary and known guard codes instead of treating it as a generic error.
    assert "const guarded = error && error.payload" in action
    assert 'guarded.status === "guarded"' in action
    assert "creativeMotionGuideBoundaryIsSafe(guardedData)" in action
    assert "WEB_CREATIVE_MOTION_CLAIM_GUARD" in action
    assert "WEB_CREATIVE_MOTION_ORIGINALITY_GUARD" in action
    assert '[expectedPath]: "guarded"' in action
    assert "creativeMotionGuideResult: {}" not in action

    # Claim/originality is classified by the endpoint, while local hard safety
    # still blocks URL/secret/payment/markup content.  The flow lock disables
    # controls, so current-form comparison cannot use FormData.
    assert "return cinematicConceptSafetyError" not in payload
    assert "const standard = videoStudioSafetyError(...values);" in INTEGRATION
    assert "CINEMATIC_CONCEPT_MARKUP_PATTERN" in INTEGRATION
    assert "new FormData(form)" not in fields
    assert 'form.querySelectorAll("input, textarea, select")' in fields


def test_creative_motion_guide_keeps_stale_cards_and_runtime_out_of_the_product_claim() -> None:
    sync = _portal_form_sync()
    assert "data-creative-motion-guide-suggestions-stale" in sync
    assert "suggestionCards.hidden = staleSuggestions;" in sync
    assert "Các card của bộ trước được ẩn" in sync
    assert "Its 23 emitted `motion|...` literals" in MIGRATION_CONTRACT
    assert "does not inspect/upload source media" in MIGRATION_CONTRACT

    endpoint_start = ROUTER.index('@router.post("/tools/creative-motion-guide")')
    endpoint_end = ROUTER.index('@router.post("/tools/cinematic-concept/save")', endpoint_start)
    endpoint = ROUTER[endpoint_start:endpoint_end].lower()
    for forbidden in ("copyfast_bridge", "httpx.", "requests.", "_idempotent(", "transaction(", "_record_audit(", "_event("):
        assert forbidden not in endpoint
    assert "không có telegram/bot state, ảnh, video, audio, preview, output, job, xu, payos, asset, publish hoặc delivery" in endpoint
    assert ".portal-creative-motion-guide" in CSS
    assert ":focus-visible" in CSS
    assert "min-height: 44px" in CSS
