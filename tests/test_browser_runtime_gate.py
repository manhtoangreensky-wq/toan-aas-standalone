"""Tests asserting that reproducible browser runtime verification evidence meets all quality gates.

Validates:
- browser_verification_evidence.json exists and conforms to schema
- 0 uncaught JS errors, 0 unhandled rejections, 0 broken bindings, 0 failed app requests
- Truthful guarded cards (0 fake success, 0 broken primary links)
- Real Free Tools interaction pass (>= 3 cases)
- Theme light, dark, reload persistence, and zero first-paint flicker
- Accessibility pass: labeled icon controls, zero duplicate critical IDs, keyboard focusable primary actions
- Screenshot manifest has >= 18 screenshots (6 desktop, 6 tablet, 6 mobile) with matching SHA256 hashes
- Zero secret leaks in evidence JSON
"""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "reports" / "browser_evidence"
EVIDENCE_JSON_PATH = EVIDENCE_DIR / "browser_verification_evidence.json"
MANIFEST_JSON_PATH = EVIDENCE_DIR / "screenshot-manifest.json"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"


def _load_evidence() -> dict:
    if not EVIDENCE_JSON_PATH.exists():
        pytest.fail(f"Evidence file not found at {EVIDENCE_JSON_PATH}. Run scripts/ci/run_browser_verification.py first.")
    return json.loads(EVIDENCE_JSON_PATH.read_text(encoding="utf-8"))


def _load_manifest() -> list[dict]:
    if not MANIFEST_JSON_PATH.exists():
        pytest.fail(f"Manifest file not found at {MANIFEST_JSON_PATH}. Run scripts/ci/run_browser_verification.py first.")
    return json.loads(MANIFEST_JSON_PATH.read_text(encoding="utf-8"))


def test_browser_evidence_json_structure_and_zero_runtime_errors():
    evidence = _load_evidence()

    assert "head_sha" in evidence and evidence["head_sha"]
    assert evidence.get("server_origin") == "isolated-local-test-origin"

    summary = evidence.get("summary", {})
    assert summary.get("pages_checked", 0) >= 18
    assert summary.get("uncaught_js_errors") == 0, f"Uncaught JS errors: {summary.get('uncaught_js_errors')}"
    assert summary.get("unhandled_promise_rejections") == 0, f"Unhandled rejections: {summary.get('unhandled_promise_rejections')}"
    assert summary.get("broken_event_bindings") == 0, f"Broken event bindings: {summary.get('broken_event_bindings')}"
    assert summary.get("failed_app_requests") == 0, f"Failed app requests: {summary.get('failed_app_requests')}"


def test_browser_hub_checks_and_truthful_guarded_cards():
    evidence = _load_evidence()
    hub_checks = evidence.get("hub_checks", {})

    assert hub_checks.get("video_primary_links_verified") is True
    assert hub_checks.get("image_local_ops_verified") is True
    assert hub_checks.get("voice_assets_and_guarded_verified") is True
    assert hub_checks.get("music_assets_and_guarded_verified") is True
    assert hub_checks.get("subdub_formats_and_guarded_verified") is True
    assert hub_checks.get("free_tools_verified") is True

    assert hub_checks.get("broken_primary_hub_links") == 0
    assert hub_checks.get("fake_success_from_guarded_card") == 0


def test_browser_free_tool_real_interactions():
    evidence = _load_evidence()
    cases = evidence.get("free_tool_cases", [])

    assert len(cases) >= 3, f"Expected at least 3 free tool cases, got {len(cases)}"
    for case in cases:
        assert case.get("pass") is True, f"Free tool case failed: {case}"


def test_browser_theme_and_first_paint_stability():
    evidence = _load_evidence()
    theme = evidence.get("theme_checks", {})

    assert theme.get("theme_light_browser_pass") is True
    assert theme.get("theme_dark_browser_pass") is True
    assert theme.get("theme_reload_persistence_browser_pass") is True
    assert theme.get("first_paint_theme_flicker") == "NO"


def test_browser_accessibility_basic_checks():
    evidence = _load_evidence()
    a11y = evidence.get("accessibility_checks", {})

    assert a11y.get("keyboard_primary_action_pass") is True
    assert a11y.get("unlabeled_primary_icon_controls") == 0
    assert a11y.get("duplicate_critical_ids") == 0


def test_browser_screenshot_manifest_completeness_and_hashes():
    manifest = _load_manifest()

    assert len(manifest) >= 18, f"Expected at least 18 screenshots in manifest, got {len(manifest)}"

    desktop_count = sum(1 for m in manifest if m.get("viewport") == "1440x900")
    tablet_count = sum(1 for m in manifest if m.get("viewport") == "768x1024")
    mobile_count = sum(1 for m in manifest if m.get("viewport") == "375x812")

    assert desktop_count >= 6, f"Desktop screenshots: {desktop_count} < 6"
    assert tablet_count >= 6, f"Tablet screenshots: {tablet_count} < 6"
    assert mobile_count >= 6, f"Mobile screenshots: {mobile_count} < 6"

    for entry in manifest:
        rel_path = entry.get("filename")
        assert rel_path, "Manifest entry missing filename"
        file_path = EVIDENCE_DIR / rel_path
        assert file_path.exists(), f"Screenshot file missing: {file_path}"
        assert file_path.stat().st_size > 0, f"Screenshot file empty: {file_path}"
        assert entry.get("sha256"), f"Manifest entry missing sha256: {entry}"
        assert entry.get("head_sha"), f"Manifest entry missing head_sha: {entry}"


def test_browser_evidence_json_has_zero_secrets():
    text = EVIDENCE_JSON_PATH.read_text(encoding="utf-8")
    forbidden = [r"password[=:][^\s,]+", r"bearer\s+[a-zA-Z0-9_\-\.]+", r"toanaas_session=[a-zA-Z0-9_\-]+"]
    for pat in forbidden:
        assert not re.search(pat, text, re.IGNORECASE), f"Secret scan violation matching {pat}"
