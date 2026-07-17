"""Static contracts for the read-only Bot-derived Video Factory workflow."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_video_factory_workflow_is_private_navigation_not_execution() -> None:
    assert 'customerPage("/video-studio/workflow", "Video Factory Workflow"' in PORTAL
    assert 'layout: "video-factory-workflow", type: "video-factory-workflow", fields: [], action: "none"' in PORTAL
    assert "const VIDEO_FACTORY_WORKFLOW_STEPS" in PORTAL
    assert "function renderVideoFactoryWorkflow(page, context)" in PORTAL
    assert 'case "video-factory-workflow": return renderVideoFactoryWorkflow(page, context);' in PORTAL
    workflow = PORTAL[PORTAL.index("const VIDEO_FACTORY_WORKFLOW_STEPS"):PORTAL.index("const STORY_VIDEO_LANGUAGE_OPTIONS")]
    assert workflow.count('number: "') == 7
    for forbidden in ("api(", "fetch(", "data-portal-action", "job_created", "payment_started", "publish_action_created"):
        assert forbidden not in workflow


def test_video_factory_workflow_has_ready_gate_and_never_enters_pwa_cache() -> None:
    assert '"/video-studio/workflow": account && videoStudioEnabled ? "ready" : "guarded"' in INTEGRATION
    assert '"/video-studio/workflow"' in WORKER
    # Build-scoped generations clear only stale public shell caches.  The
    # workflow's private no-cache boundary is independent of each build ID.
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in WORKER
    assert "const BUILD_ID = workerBuildId();" in WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in WORKER
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in WORKER
