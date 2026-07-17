"""Static safety contracts for the Reference Format Planner Web route."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reference_format_planner_is_wired_as_a_private_web_native_route():
    integration = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    worker = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
    route = "/video-studio/reference-format-planner"

    assert route in integration
    assert 'api("/video-studio/tools/reference-format-planner/references")' in integration
    assert 'api("/video-studio/tools/reference-format-planner", {' in integration
    assert 'api("/video-studio/tools/reference-format-planner/save", {' in integration
    assert '"reference-format-planner-compose"' in integration
    assert '"reference-format-planner-save-plan"' in integration
    assert route in portal
    assert 'case "reference-format-planner": return renderReferenceFormatPlanner(page, context);' in portal
    assert route in worker


def test_reference_format_planner_does_not_advertise_video_analysis_or_execution():
    backend = (ROOT / "copyfast_video_studio.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "migration" / "REFERENCE_FORMAT_PLANNER_CONTRACT.md").read_text(encoding="utf-8")

    assert '"source_video_opened": False' in backend
    assert '"reference_analysis_performed": False' in backend
    assert '"source_link_fetched": False' in backend
    assert '"provider_called": False' in backend
    assert '"job_created": False' in backend
    assert '"wallet_mutated": False' in backend
    assert '"payment_started": False' in backend
    assert '"publish_action_created": False' in backend
    assert "never opens a video" in backend
    assert "does **not** open, download, decode, sample, inspect or analyze the video" in contract
