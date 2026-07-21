"""Static Portal/PWA contracts for the Web-native Quick Image Planner."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_quick_image_planner_is_a_first_class_private_portal_route() -> None:
    assert 'customerPage("/image/quick-planner", "Quick Image Planner"' in PORTAL
    assert 'layout: "quick-image-planner", type: "quick-image-planner", fields: [], action: "none"' in PORTAL
    assert "function renderQuickImagePlanner(page, context)" in PORTAL
    assert 'data-portal-action="quick-image-planner-plan"' in PORTAL
    assert 'data-portal-route="/image/quick-planner"' in PORTAL
    assert 'case "quick-image-planner": return renderQuickImagePlanner(page, context);' in PORTAL
    assert "data-portal-no-transient" in PORTAL


def test_quick_image_planner_payload_result_and_action_are_strictly_plan_only() -> None:
    start = INTEGRATION.index("function quickImagePlannerPayload(fields)")
    end = INTEGRATION.index("function quickImagePlannerText", start)
    payload = INTEGRATION[start:end]
    for marker in (
        "idea_source", "suggestion_key", "custom_prompt", "aspect_ratio", "variation", "brand_direction",
        "brand_position", "language", "QUICK_IMAGE_PLANNER_SOURCES", "mediaFactorySafetyError(brandDirection)",
    ):
        assert marker in payload
    for forbidden in (
        "provider:", "url:", "path:", "asset:", "job:", "payment:", "idempotency", "publish:",
        "shopai", "confirm_token", "tier_price", "wallet:",
    ):
        assert forbidden not in payload

    normalizer = INTEGRATION[
        INTEGRATION.index("function quickImagePlannerBoundaryIsSafe"):INTEGRATION.index("// Creative Flow", INTEGRATION.index("function quickImagePlannerBoundaryIsSafe"))
    ]
    for marker in (
        'data.execution === "web_native_deterministic_quick_image_planner_only"',
        "data[field] === false",
        'plan.output_status === "prompt_plan_only_no_real_image"',
        "QUICK_IMAGE_PLANNER_WORKFLOWS",
        "QUICK_IMAGE_PLANNER_POSITIONS",
    ):
        assert marker in normalizer

    action = INTEGRATION[
        INTEGRATION.index('if (action === "quick-image-planner-plan")'):INTEGRATION.index('if (action === "media-factory-blueprint")')
    ]
    assert 'api("/quick-image-planner/plan"' in action
    assert "quickImagePlannerPayload(fields)" in action
    assert "quickImagePlannerResultIsSafe(data)" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action
    assert "idempotency_key" not in action
    assert "shopai" not in action.lower()


def test_quick_image_planner_clears_private_receipts_and_switches_source_fields_accessibly() -> None:
    action = INTEGRATION[
        INTEGRATION.index('if (action === "quick-image-planner-plan")'):INTEGRATION.index('if (action === "media-factory-blueprint")')
    ]
    assert action.index('merge({ quickImagePlannerResult: {} });') < action.index("quickImagePlannerPayload(fields)")
    assert 'error.status === 503' in action
    assert 'quickImagePlannerResult: {}' in action[action.index("catch (error)"):]

    for marker in (
        'data-quick-image-planner-source',
        'data-quick-image-planner-catalog',
        'data-quick-image-planner-custom',
        'data-quick-image-planner-source-status',
        'function synchronizeQuickImagePlannerForm(form)',
        'synchronizeQuickImagePlannerForm(form);',
        'control.required = active;',
        'field.hidden = !active;',
        'control.setAttribute("aria-required", String(active));',
    ):
        assert marker in PORTAL
    assert 'aria-live="polite"' not in PORTAL[PORTAL.index("function renderQuickImagePlannerResult"):PORTAL.index("function renderQuickImagePlanner(page, context)")]
    assert 'role="status"' in PORTAL[PORTAL.index("function renderQuickImagePlannerResult"):PORTAL.index("function renderQuickImagePlanner(page, context)")]


def test_quick_image_planner_is_bounded_before_parsing_and_never_pwa_cached() -> None:
    assert "QUICK_IMAGE_PLANNER_BODY_MAX_BYTES = 16 * 1024" in APP
    assert 'path.startswith("/api/v1/quick-image-planner/")' in APP
    assert '"quick-image-planner-write"' in APP
    assert '"WEB_QUICK_IMAGE_PLANNER_BODY_TOO_LARGE"' in APP
    assert '"/" + "api/v1/quick-image-planner"' in WORKER
    assert '"/image/quick-planner"' in WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in WORKER


def test_browser_surfaces_do_not_embed_frozen_bot_callback_or_checkout_tokens() -> None:
    browser_source = f"{PORTAL}\n{INTEGRATION}"
    for forbidden in (
        "create_media|qi_",
        "shopai|confirm",
        "shopai|package",
        "confirm_token",
        "qi_tier_",
    ):
        assert forbidden not in browser_source
