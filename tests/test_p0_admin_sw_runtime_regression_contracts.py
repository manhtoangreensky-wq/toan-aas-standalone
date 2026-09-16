"""Contract tests for Service Worker Runtime Regression Closure.

TASK: P0.WEB.ADMIN.UI.PR454.SERVICE_WORKER.RUNTIME.REGRESSION.CLOSURE
PROGRAM: P0.WEB.ERP.PRODUCTION_COMPLETION
"""

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVICE_WORKER_JS = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
SW_REPORT_PATH = ROOT / "reports" / "visual_reset" / "sw_runtime_report.json"


def test_service_worker_runtime_regression_closure_two_generation_takeover() -> None:
    """Validate empirical two-generation service worker runtime takeover invariants."""
    # 1. Source code invariants
    assert "self.skipWaiting()" in SERVICE_WORKER_JS
    assert "self.clients.claim()" in SERVICE_WORKER_JS
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER_JS
    assert "const PRIVATE_PATH_PREFIXES" in SERVICE_WORKER_JS

    # 2. Empirical runtime report verification
    if not SW_REPORT_PATH.exists():
        pytest.skip("SW runtime report not generated yet")

    report = json.loads(SW_REPORT_PATH.read_text(encoding="utf-8"))

    # Two-generation takeover
    assert report["BUILD_B_ACTIVATED"] == "YES"
    assert report["CLIENT_CLAIMED_BY_BUILD_B"] == "YES"
    assert report["UNSAVED_FORM_SENTINEL_PRESERVED"] == "YES"
    assert report["UNEXPECTED_NAVIGATION"] == "NO"
    assert report["UNEXPECTED_RELOAD"] == "NO"

    # Mixed generation proof
    assert report["ACTIVE_BUILD_ID"] == "build_b_20260916_v2"
    assert report["CSS_BUILD_ID"] == "BUILD_B"
    assert report["THEME_CSS_BUILD_ID"] == "BUILD_B"
    assert report["THEME_JS_BUILD_ID"] == "BUILD_B"
    assert report["PORTAL_JS_BUILD_ID"] == "BUILD_B"
    assert report["MIXED_ASSET_GENERATION"] == "NO"

    # Cache storage proof
    assert report["BUILD_B_CACHE_PRESENT"] == "YES"
    assert report["BUILD_A_PORTAL_CACHE_REMOVED"] == "YES"
    assert report["UNRELATED_ORIGIN_CACHE_DELETED"] == "NO"
    assert report["PRIVATE_ADMIN_RESPONSE_CACHED"] == "NO"
    assert report["PRIVATE_API_RESPONSE_CACHED"] == "NO"

    # Reload loop & stability
    assert report["NAVIGATION_COUNT_AFTER_TAKEOVER"] == 0
    assert report["SERVICE_WORKER_RELOAD_LOOP"] == "NO"
    assert report["CONTROLLERCHANGE_LOOP"] == "NO"

    # Auth & session preservation
    assert report["SESSION_LOST"] == "NO"
    assert report["UNEXPECTED_LOGIN_REDIRECT"] == "NO"

    # UI appearance & mobile drawer
    assert report["ADMIN_LIGHT_THEME_AFTER_TAKEOVER"] == "YES"
    assert report["MOBILE_DRAWER_AFTER_TAKEOVER"] == "YES"

    # Final gate pass
    assert report["SW_RUNTIME_PASS"] == "YES"
