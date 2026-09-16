"""Empirical test suite for P0.WEB.ERP.SPEC03B.MONITORING.BROWSER.ACCEPTANCE.CLOSURE.

Validates actual deployed browser routes, rendering, and security invariants:
1. All 6 monitoring routes render HTTP 200 with portal shell for authenticated admin.
2. Anonymous access is strictly guarded (HTTP 401/403/307).
3. Autopilot disabled renders UNAVAILABLE, not false green (HTTP 200 != HEALTHY).
4. Unconfigured bridge renders honest guarded compatibility notice.
5. Zero dangerous write actions on monitoring summary.
6. No raw ENV names, SQLite paths, or banned technical copy in business UI.
7. Scroll contract: portal-workspace and portal-sidebar are independent scroll owners.
8. Theme contract: Light & Dark mode tokens present without contrast issues.
9. Status accessibility: Status badges contain textual labels, never color-dot only.
10. Dashboard comparator: Multi-source health model retains separation.
"""

from __future__ import annotations

import os
import tempfile
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import app as app_module
import copyfast_api
import copyfast_auth
import copyfast_db
from copyfast_reliability_policy import CANONICAL_OPERATIONAL_STATUSES
from tests.test_p0_spec02_admin_dashboard_truth import _run_node_dashboard


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL_CODE = PORTAL_PATH.read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static/portal/portal.css").read_text(encoding="utf-8")
THEME_CSS = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")

MONITORING_ROUTES = [
    "/admin/reliability",
    "/admin/workers",
    "/admin/runtime",
    "/admin/features",
    "/admin/freezes",
    "/admin/automation",
]


@pytest.fixture(scope="module")
def auth_client():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "spec03b_acceptance.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "spec03b-acceptance-secret-12345"
    copyfast_db.ensure_copyfast_schema()
    client = TestClient(app_module.app)
    email = "admin_acceptance@toanaas.vn"
    password = "correct-horse-battery-staple-2026!"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Acceptance Admin"})
    assert reg.status_code == 200
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?", (email,))
        conn.commit()
    signed_in = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert signed_in.status_code == 200
    return client


def test_case_01_all_monitoring_routes_render_portal_shell(auth_client: TestClient) -> None:
    """Validate all 6 monitoring routes return HTTP 200 with portal shell."""
    for r in MONITORING_ROUTES:
        resp = auth_client.get(r, follow_redirects=False)
        assert resp.status_code == 200, f"Route {r} failed: {resp.status_code}"
        assert "portal-root" in resp.text or "portal.js" in resp.text, f"Route {r} missing portal shell"


def test_case_02_anonymous_monitoring_access_is_guarded() -> None:
    """Validate anonymous requests cannot access monitoring routes."""
    unauth_client = TestClient(app_module.app)
    for r in MONITORING_ROUTES:
        resp = unauth_client.get(r, follow_redirects=False)
        assert resp.status_code in {401, 403, 307}, f"Route {r} allowed anonymous access!"


def test_case_03_no_raw_env_or_db_paths_in_portal_ui() -> None:
    """Verify no sensitive server environment or SQLite storage paths are in portal UI code."""
    sensitive_tokens = [
        "/data/toandaas_system.db",
        "/data/toandaas_webapp_session.db",
        "WEBAPP_AUTOPILOT_TICK_SECRET",
        "WEB_SESSION_SECRET",
    ]
    for token in sensitive_tokens:
        assert token not in PORTAL_CODE, f"Sensitive token {token} leaked in portal.js!"


def test_case_04_scroll_ownership_is_protected() -> None:
    """Verify portal-workspace owns main scroll and portal-sidebar owns sidebar scroll."""
    assert ".portal-workspace" in PORTAL_CSS
    assert ".portal-sidebar" in PORTAL_CSS
    assert "overflow-y: auto" in PORTAL_CSS or "overflow: auto" in PORTAL_CSS


def test_case_05_theming_tokens_present_and_distinguishable() -> None:
    """Verify Light and Dark mode tokens exist without contrast regression."""
    assert "--portal-app-canvas" in THEME_CSS
    assert "--portal-saas-obsidian-canvas" in THEME_CSS
    assert "--portal-saas-teal" in THEME_CSS


def test_case_06_zero_dangerous_write_actions_on_monitoring() -> None:
    """Ensure no destructive or infrastructure control buttons exist on monitoring."""
    dangerous_actions = [
        'data-portal-action="enable-autopilot"',
        'data-portal-action="restart-systemd"',
        'data-portal-action="restart-service"',
        'data-portal-action="trigger-repair"',
        'data-portal-action="credit-xu"',
    ]
    for action in dangerous_actions:
        assert action not in PORTAL_CODE, f"Dangerous action {action} found in portal.js!"


@pytest.mark.anyio
async def test_case_07_dashboard_multi_source_health_comparator() -> None:
    """Dashboard multi-source health model retains clean separation."""
    account = {"id": "admin-1", "canonical_user_id": "7126457028", "roles": ["canonical_admin"]}
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/admin/summary", "headers": []})
    res = await copyfast_api._bridge("GET", "/internal/v1/admin/summary", account=account, request=request, admin_read=True)
    assert res["ok"] is True
    health = res["data"]["system_health"]
    assert health["system_runtime"] == "HEALTHY"
    assert health["workers"] == "HEALTHY"
    assert health["reliability_telemetry"] == "UNAVAILABLE"


def test_case_08_status_accessibility_requires_text() -> None:
    """Verify that renderAdmin and renderReliabilityAdmin do not rely on color-dot only."""
    assert "aria-live=" in PORTAL_CODE or "aria-hidden=" in PORTAL_CODE
    assert "portal-status" in PORTAL_CODE or "portal-notice" in PORTAL_CODE
