"""Static contracts for the owner-scoped Web Image Motion Planner UI."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_video_studio.py").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ENGINE = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _action(start_token: str, end_token: str) -> str:
    start = INTEGRATION.index(start_token)
    end = INTEGRATION.index(end_token, start)
    return INTEGRATION[start:end]


def test_image_motion_planner_is_a_native_video_studio_surface() -> None:
    assert 'customerPage("/video-studio/image-motion-planner", "Image Motion Planner"' in PORTAL
    assert 'layout: "image-motion-planner", type: "image-motion-planner"' in PORTAL
    assert "function renderImageMotionPlanner(page, context)" in PORTAL
    assert 'case "image-motion-planner": return renderImageMotionPlanner(page, context);' in PORTAL
    assert '"/video-studio/image-motion-planner"' in WORKER
    assert '"image_motion_planner"' in ENGINE
    assert 'WebFeature("image_motion_planner", "Image Motion Planner", "video", "/video-studio/image-motion-planner"' in REGISTRY


def test_image_motion_ui_accepts_only_owner_scoped_metadata_and_content_free_save_receipts() -> None:
    for helper in (
        "normalizeImageMotionReference",
        "normalizeImageMotionReferences",
        "normalizeImageMotionResult",
        "normalizeImageMotionSaveSource",
        "normalizeImageMotionSaveReceipt",
    ):
        assert f"function {helper}" in PORTAL
    for state in (
        "imageMotionPlannerReferences: normalizeImageMotionReferences(source.imageMotionPlannerReferences)",
        "imageMotionPlannerResult: normalizeImageMotionResult(source.imageMotionPlannerResult)",
        "imageMotionPlannerSaveSource: normalizeImageMotionSaveSource(source.imageMotionPlannerSaveSource)",
        "imageMotionPlannerSaveReceipt: normalizeImageMotionSaveReceipt(source.imageMotionPlannerSaveReceipt)",
    ):
        assert state in PORTAL
    result_renderer = PORTAL[
        PORTAL.index("function renderImageMotionPlannerResult"):
        PORTAL.index("function renderImageMotionPlannerSavePanel")
    ]
    save_panel = PORTAL[
        PORTAL.index("function renderImageMotionPlannerSavePanel"):
        PORTAL.index("function renderImageMotionPlanner(page, context)")
    ]
    # Keep the scope to Image Motion.  The old end marker crossed into the
    # unrelated Reference Format planner, whose private owner reference has a
    # legitimate `asset_id` field.  Image Motion exposes only its direction
    # metadata and its save receipt remains content-free.
    for forbidden in ("asset_id", "storage_key", "source_url", "preview_url", "video_url", "output_url", "payment_url"):
        assert forbidden not in result_renderer
        assert forbidden not in save_panel


def test_image_motion_uses_csrf_native_apis_and_recomputes_on_save() -> None:
    assert '"image-motion-planner-compose": Boolean(account && me.csrf_token && imageMotionPlannerEnabled)' in INTEGRATION
    assert '"image-motion-planner-save-plan": Boolean(account && me.csrf_token && imageMotionPlannerEnabled)' in INTEGRATION
    assert 'api("/video-studio/tools/image-motion-planner", {' in INTEGRATION
    assert 'api("/video-studio/tools/image-motion-planner/save", {' in INTEGRATION
    compose = _action('if (action === "image-motion-planner-compose")', 'if (action === "image-motion-planner-save-plan")').lower()
    save = _action('if (action === "image-motion-planner-save-plan")', 'if (action === "storyboard-composer-compose")').lower()
    for forbidden in ("localstorage", "sessionstorage", "payos", "/payments", "/jobs", "core bridge"):
        assert forbidden not in compose
        assert forbidden not in save
    assert "idempotency_key: submission.key" in save
    assert "imagemotionplansavereceipt(result.data)" in save


def test_image_motion_backend_checks_metadata_not_media_and_never_runs_execution() -> None:
    for token in (
        '"/tools/image-motion-planner/references"',
        '"/tools/image-motion-planner"',
        '"/tools/image-motion-planner/save"',
        "ImageMotionPlannerRequest",
        "ImageMotionPlannerPlanSaveRequest",
        "_image_motion_direction_reference",
        "_image_motion_asset_is_active_image",
        "web_native_image_motion_planning_only",
        "web_native_image_motion_video_plan_server_recomputed",
        "web.video.image_motion_planner.save_plan",
    ):
        assert token in ROUTER
    compose_start = ROUTER.index('@router.post("/tools/image-motion-planner")')
    compose_end = ROUTER.index('@router.post("/tools/image-motion-planner/save")', compose_start)
    compose = ROUTER[compose_start:compose_end].lower()
    for forbidden in ("copyfast_bridge", "httpx.", "requests.", "payos", "storage_key", "open("):
        assert forbidden not in compose
