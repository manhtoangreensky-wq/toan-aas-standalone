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

import hashlib
import json
import os
from pathlib import Path
import re

import pytest

from tests.test_p0_webapp_v3_browser_false_green_first_red import (
    test_remediated_hub_hardcode_purged,
    test_remediated_unhandled_rejection_captured,
    test_remediated_first_paint_flicker_actively_measured,
    test_remediated_primary_clipping_inspects_ctas,
    test_remediated_responsive_drawer_closed_and_content_verified,
    test_remediated_keyboard_vacuous_pass_purged,
    test_first_red_sentinel_self_injection_false_green_purged,
    test_first_red_wrong_head_manifest_rejected,
    test_first_red_wrong_screenshot_hash_rejected,
    test_first_red_duplicate_matrix_entry_rejected,
    test_first_red_primary_control_missing_vacuous_pass_purged,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "reports" / "browser_evidence"
EVIDENCE_JSON_PATH = EVIDENCE_DIR / "browser_verification_evidence.json"
MANIFEST_JSON_PATH = EVIDENCE_DIR / "screenshot-manifest.json"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"

CANONICAL_ROUTES = ("/tools/video", "/tools/image", "/voice", "/music", "/subdub", "/tools/free")
CANONICAL_VIEWPORTS = ("1440x900", "768x1024", "375x812")
EXPECTED_PAIRS = {(r, v) for r in CANONICAL_ROUTES for v in CANONICAL_VIEWPORTS}


def _load_evidence() -> dict:
    if not EVIDENCE_JSON_PATH.exists():
        pytest.fail(f"Evidence file not found at {EVIDENCE_JSON_PATH}. Run scripts/ci/run_browser_verification.py first.")
    return json.loads(EVIDENCE_JSON_PATH.read_text(encoding="utf-8"))


def _load_manifest() -> list[dict]:
    if not MANIFEST_JSON_PATH.exists():
        pytest.fail(f"Manifest file not found at {MANIFEST_JSON_PATH}. Run scripts/ci/run_browser_verification.py first.")
    return json.loads(MANIFEST_JSON_PATH.read_text(encoding="utf-8"))


def _resolve_current_ci_head() -> str:
    ci_head = os.environ.get("HEAD_SHA")
    if ci_head and len(ci_head.strip()) >= 7:
        return ci_head.strip()
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).exists():
        try:
            event_data = json.loads(Path(event_path).read_text(encoding="utf-8"))
            pr_head = event_data.get("pull_request", {}).get("head", {}).get("sha")
            if pr_head and len(pr_head.strip()) >= 7:
                return pr_head.strip()
        except Exception:
            pass
    evidence = _load_evidence()
    evidence_head = evidence.get("head_sha", "")
    try:
        import subprocess
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        git_head = res.stdout.strip()
        if evidence_head and git_head == evidence_head:
            return git_head
        res_parent = subprocess.run(["git", "rev-parse", "HEAD~1"], capture_output=True, text=True)
        if res_parent.returncode == 0 and res_parent.stdout.strip() == evidence_head:
            return evidence_head
        if git_head and len(git_head) >= 7:
            return git_head
    except Exception:
        pass
    ci_head = os.environ.get("GITHUB_SHA")
    if ci_head and len(ci_head.strip()) >= 7:
        return ci_head.strip()
    return evidence_head


def test_browser_evidence_json_structure_and_zero_runtime_errors():
    evidence = _load_evidence()
    expected_head = _resolve_current_ci_head()

    assert evidence.get("head_sha") == expected_head, (
        f"Evidence head_sha mismatch: expected {expected_head}, got {evidence.get('head_sha')}"
    )
    assert evidence.get("server_origin") == "isolated-local-test-origin"

    summary = evidence.get("summary", {})
    assert summary.get("pages_checked") == 18, f"Expected exactly 18 pages checked, got {summary.get('pages_checked')}"
    assert summary.get("uncaught_js_errors") == 0, f"Uncaught JS errors: {summary.get('uncaught_js_errors')}"
    assert summary.get("unhandled_promise_rejections") == 0, f"Unhandled rejections: {summary.get('unhandled_promise_rejections')}"
    assert summary.get("broken_event_bindings") == 0, f"Broken event bindings: {summary.get('broken_event_bindings')}"
    assert summary.get("failed_app_requests") == 0, f"Failed app requests: {summary.get('failed_app_requests')}"


def test_browser_unhandled_rejection_instrumentation():
    evidence = _load_evidence()
    ur = evidence.get("unhandled_rejection_checks", {})

    assert ur.get("instrumentation_installed") is True, "Unhandled rejection hook not installed"
    assert ur.get("real_promise_rejection_sentinel") is True, "Real promise rejection sentinel flag missing"
    assert ur.get("sentinel_rejection_detected") is True, "Unhandled rejection sentinel test not detected"
    assert ur.get("sentinel_manual_event_dispatch") == 0, "Sentinel manual event dispatch detected"
    assert ur.get("sentinel_direct_array_push") == 0, "Sentinel direct array push detected"
    assert ur.get("sentinel_forced_true_fallback") == 0, "Sentinel forced true fallback detected"


def test_browser_hub_checks_and_truthful_guarded_cards():
    evidence = _load_evidence()
    hub_checks = evidence.get("hub_checks", {})

    assert hub_checks.get("video_primary_links_verified") is True
    assert hub_checks.get("image_local_ops_verified") is True
    assert hub_checks.get("voice_assets_and_guarded_verified") is True
    assert hub_checks.get("music_assets_and_guarded_verified") is True
    assert hub_checks.get("subdub_formats_and_guarded_verified") is True
    assert hub_checks.get("free_tools_verified") is True

    assert hub_checks.get("hubs_behaviorally_checked") == 6, f"Expected 6 hubs behaviorally checked, got {hub_checks.get('hubs_behaviorally_checked')}"
    assert hub_checks.get("hardcoded_hub_pass_flags") == 0, f"Hardcoded hub pass flags: {hub_checks.get('hardcoded_hub_pass_flags')}"

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
    assert theme.get("first_paint_measurement_active") is True, "First paint measurement was not active"
    assert theme.get("first_paint_theme_flicker") == "NO", f"First paint flicker: {theme.get('first_paint_theme_flicker')}"
    assert theme.get("flicker_events_count") == 0, f"Flicker events: {theme.get('flicker_events_count')}"


def test_browser_accessibility_basic_checks():
    evidence = _load_evidence()
    a11y = evidence.get("accessibility_checks", {})

    assert a11y.get("keyboard_primary_action_pass") is True
    assert a11y.get("keyboard_vacuous_pass") == 0, "Keyboard accessibility used vacuous pass"
    assert len(a11y.get("keyboard_failures", [])) == 0, f"Keyboard failures: {a11y.get('keyboard_failures')}"
    assert a11y.get("unlabeled_primary_icon_controls") == 0
    assert a11y.get("duplicate_critical_ids") == 0


def test_browser_canonical_screenshots_route_content_and_zero_clipping():
    evidence = _load_evidence()
    pages = evidence.get("pages", [])

    assert len(pages) == 18, f"Expected exactly 18 pages, got {len(pages)}"

    page_pairs = [(p["route"], p["viewport"]) for p in pages]
    assert len(page_pairs) == 18, "Page pairs length must be exactly 18"
    assert len(set(page_pairs)) == 18, f"Duplicate page matrix pairs found: {len(page_pairs) - len(set(page_pairs))}"
    assert set(page_pairs) == EXPECTED_PAIRS, f"Page matrix mismatch: missing {EXPECTED_PAIRS - set(page_pairs)}, extra {set(page_pairs) - EXPECTED_PAIRS}"

    for page in pages:
        route = page.get("route")
        vp = page.get("viewport")
        assert page.get("main_content_visible") is True, f"Main content not visible on {route} ({vp})"
        assert page.get("heading_visible") is True, f"Heading not visible on {route} ({vp})"
        assert page.get("primary_controls_visible") is True, f"Primary control not visible on {route} ({vp})"
        assert page.get("primary_control_clipping") is False, f"Primary control clipped on {route} ({vp}): {page.get('clipped_controls')}"
        assert page.get("canonical_screenshot_shows_route_content") is True, f"Canonical screenshot obscured on {route} ({vp})"


def test_browser_screenshot_manifest_completeness_and_hashes():
    manifest = _load_manifest()
    expected_head = _resolve_current_ci_head()

    assert len(manifest) == 18, f"Expected exactly 18 screenshots in manifest, got {len(manifest)}"

    manifest_pairs = [(m["route"], m["viewport"]) for m in manifest]
    assert len(manifest_pairs) == 18, "Manifest pairs length must be exactly 18"
    assert len(set(manifest_pairs)) == 18, f"Duplicate manifest matrix pairs found: {len(manifest_pairs) - len(set(manifest_pairs))}"
    assert set(manifest_pairs) == EXPECTED_PAIRS, f"Manifest matrix mismatch: missing {EXPECTED_PAIRS - set(manifest_pairs)}, extra {set(manifest_pairs) - EXPECTED_PAIRS}"

    desktop_count = sum(1 for m in manifest if m.get("viewport") == "1440x900")
    tablet_count = sum(1 for m in manifest if m.get("viewport") == "768x1024")
    mobile_count = sum(1 for m in manifest if m.get("viewport") == "375x812")

    assert desktop_count == 6, f"Desktop screenshots: {desktop_count} != 6"
    assert tablet_count == 6, f"Tablet screenshots: {tablet_count} != 6"
    assert mobile_count == 6, f"Mobile screenshots: {mobile_count} != 6"

    for entry in manifest:
        rel_path = entry.get("filename")
        assert rel_path, "Manifest entry missing filename"
        file_path = EVIDENCE_DIR / rel_path
        assert file_path.exists(), f"Screenshot file missing: {file_path}"
        assert file_path.stat().st_size > 0, f"Screenshot file empty: {file_path}"

        # Exact file size match
        assert file_path.stat().st_size == entry.get("file_size"), (
            f"File size mismatch for {rel_path}: actual {file_path.stat().st_size} != recorded {entry.get('file_size')}"
        )

        # Recomputed SHA256 match
        actual_sha256 = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_sha256 == entry.get("sha256"), (
            f"SHA256 mismatch for {rel_path}: actual {actual_sha256} != recorded {entry.get('sha256')}"
        )

        # Exact head_sha match against canonical current head
        assert entry.get("head_sha") == expected_head, (
            f"Manifest head_sha mismatch for {rel_path}: actual {entry.get('head_sha')} != expected {expected_head}"
        )


def test_browser_evidence_json_has_zero_secrets():
    text = EVIDENCE_JSON_PATH.read_text(encoding="utf-8")
    forbidden = [r"password[=:][^\s,]+", r"bearer\s+[a-zA-Z0-9_\-\.]+", r"toanaas_session=[a-zA-Z0-9_\-]+"]
    for pat in forbidden:
        assert not re.search(pat, text, re.IGNORECASE), f"Secret scan violation matching {pat}"
