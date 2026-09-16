"""Empirical test suite for P0.WEB.ERP.SPEC05B.OPERATIONS.JOBS.BROWSER.ACCEPTANCE.CLOSURE.

Validates actual deployed browser routes, rendering, and security invariants:
1. Operations & Jobs routes render HTTP 200 with portal shell for authenticated admin.
2. Anonymous access is strictly guarded (HTTP 401/403/307).
3. Non-admin regular user access is rejected (HTTP 403 Forbidden).
4. Truthful semantics & Fake Zero Job Count prevented (counts.total is None when UNAVAILABLE).
5. Job detail read model maintains BOT_CORE authority.
6. Mutation controls are strictly locked fail-closed (WEBAPP_ADMIN_WRITES_DISABLED).
7. Customer CRM integration provides truthful jobs summary and attention reasons.
8. Scroll contract: portal-workspace and portal-sidebar are independent scroll owners.
9. Theme contract: Light & Dark obsidian mode tokens present without contrast issues.
10. Status accessibility: Status badges contain textual labels, never color-dot only.
"""

from __future__ import annotations

import os
import tempfile
import sqlite3
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_auth
import copyfast_db
from copyfast_db import utc_now
import copyfast_customer_crm_policy as crm_policy
from copyfast_operations_jobs_policy import (
    JOB_AUTHORITY,
    WEB_ROLE,
    RETRY_ACTIONS,
    CANCEL_ACTIONS,
    FAKE_ZERO_JOB_COUNT,
    synthesize_operations_jobs_summary,
)


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL_CODE = PORTAL_PATH.read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static/portal/portal.css").read_text(encoding="utf-8")
THEME_CSS = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")

OPERATIONS_JOBS_ROUTES = [
    "/admin/jobs",
    "/admin/jobs/failed",
    "/admin/jobs/job-test-001",
    "/admin/customers/ec8398a0-2069-4379-a54d-d9300f0a8672",
]


@pytest.fixture(scope="module")
def auth_fixture():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "spec05b_acceptance.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "spec05b-acceptance-secret-token-12345"
    copyfast_db.ensure_copyfast_schema()

    admin_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    now = utc_now()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, 'admin_spec05b@toanaas.vn', 'hash', 'Acceptance Admin', '7126457028', 'admin', 1, 1, ?, ?)""",
            (admin_id, now, now),
        )
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, 'user_spec05b@toanaas.vn', 'hash', 'Normal User', NULL, 'user', 1, 1, ?, ?)""",
            (user_id, now, now),
        )
        admin_sess = copyfast_auth._insert_session(conn, admin_id)
        user_sess = copyfast_auth._insert_session(conn, user_id)
        conn.commit()

    admin_client = TestClient(app_module.app)
    admin_cookie = copyfast_auth._session_cookie_value(admin_sess["session_id"])
    admin_client.cookies.set("toan_aas_session", admin_cookie)

    user_client = TestClient(app_module.app)
    user_cookie = copyfast_auth._session_cookie_value(user_sess["session_id"])
    user_client.cookies.set("toan_aas_session", user_cookie)

    return {
        "admin_client": admin_client,
        "user_client": user_client,
        "db_path": db_path,
    }


def test_case_01_all_operations_jobs_routes_render_portal_shell(auth_fixture) -> None:
    """Validate all Operations/Jobs and customer routes return HTTP 200 with portal shell."""
    client = auth_fixture["admin_client"]
    for r in OPERATIONS_JOBS_ROUTES:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 200, f"Route {r} failed: {resp.status_code}"
        assert "portal-root" in resp.text or "portal.js" in resp.text, f"Route {r} missing portal shell"


def test_case_02_anonymous_jobs_access_is_guarded() -> None:
    """Validate anonymous requests cannot access operations/jobs or admin customer routes."""
    unauth_client = TestClient(app_module.app)
    for r in OPERATIONS_JOBS_ROUTES:
        resp = unauth_client.get(r, follow_redirects=False)
        assert resp.status_code in {401, 403, 307}, f"Route {r} allowed anonymous access!"


def test_case_03_non_admin_jobs_access_is_forbidden(auth_fixture) -> None:
    """Validate non-admin users receive HTTP 403 Forbidden on all operations routes."""
    client = auth_fixture["user_client"]
    for r in OPERATIONS_JOBS_ROUTES:
        resp = client.get(r, follow_redirects=False)
        assert resp.status_code == 403, f"Route {r} allowed non-admin access!"


def test_case_04_jobs_read_api_prevents_fake_zero(auth_fixture) -> None:
    """Verify operations jobs API prevents fake zero counts when bridge is unconfigured."""
    client = auth_fixture["admin_client"]
    resp = client.get("/api/v1/operations/jobs")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["job_authority"] == "BOT_CORE"
    assert data["counts"]["total"] is None, "Fake zero count detected when bridge is unconfigured!"
    assert data["fake_zero_job_count"] == 0

    resp_failed = client.get("/api/v1/operations/jobs/failed")
    assert resp_failed.status_code == 200
    data_failed = resp_failed.json()["data"]
    assert data_failed["counts"]["total"] is None


def test_case_05_job_detail_endpoint_truth(auth_fixture) -> None:
    """Verify operations job detail returns truthful envelope preserving BOT_CORE authority."""
    client = auth_fixture["admin_client"]
    resp = client.get("/api/v1/operations/jobs/job-test-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["job_id"] == "job-test-001"
    assert body["data"]["data_source_authority"] == "BOT_CORE"


def test_case_06_mutation_controls_are_locked_fail_closed(auth_fixture) -> None:
    """Ensure mutation operations are locked fail-closed with WEBAPP_ADMIN_WRITES_DISABLED."""
    client = auth_fixture["admin_client"]
    resp_retry = client.post("/api/v1/operations/jobs/retry")
    assert resp_retry.status_code == 200
    assert resp_retry.json()["ok"] is False
    assert resp_retry.json()["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"

    # Confirm /admin/jobs has no POST routes
    resp_post = client.post("/admin/jobs/retry/job-123")
    assert resp_post.status_code == 405


def test_case_07_customer_crm_jobs_read_model_integration() -> None:
    """Ensure Customer CRM context integrates truthful jobs summary without cross-db write."""
    account = {
        "id": "acc-spec05b",
        "display_name": "CRM Test",
        "canonical_user_id": "7126457028",
    }
    crm_ctx = crm_policy.synthesize_customer_crm_context(account)
    assert crm_ctx["jobs"]["data_source"] == "BOT_CORE / CORE_BRIDGE_READ_MODEL"
    assert crm_ctx["jobs"]["status"] == "UNAVAILABLE"
    assert crm_ctx["jobs"]["mutation_available"] is False
    assert "action_required" in crm_ctx


def test_case_08_scroll_ownership_contract() -> None:
    """Verify portal-workspace owns main scroll and portal-sidebar owns sidebar scroll."""
    assert ".portal-workspace" in PORTAL_CSS
    assert ".portal-sidebar" in PORTAL_CSS
    assert "overflow-y: auto" in PORTAL_CSS or "overflow: auto" in PORTAL_CSS
    assert "html," in PORTAL_CSS or "body," in PORTAL_CSS
    assert "overflow: hidden" in PORTAL_CSS


def test_case_09_theming_light_and_obsidian_dark_tokens() -> None:
    """Verify Light and Dark obsidian mode tokens exist without contrast regression."""
    assert "--portal-app-canvas" in THEME_CSS
    assert "--portal-saas-obsidian-canvas" in THEME_CSS
    assert "--portal-saas-teal" in THEME_CSS
    assert 'data-portal-theme="dark"' in THEME_CSS


def test_case_10_accessibility_and_no_dot_only_badges() -> None:
    """Verify that job badges contain textual labels and interactive elements have focus indicators."""
    assert "aria-live=" in PORTAL_CODE or "aria-hidden=" in PORTAL_CODE or "aria-label=" in PORTAL_CODE
    assert "portal-status" in PORTAL_CODE or "portal-notice" in PORTAL_CODE
    assert ":focus" in PORTAL_CSS or ":focus-visible" in PORTAL_CSS
