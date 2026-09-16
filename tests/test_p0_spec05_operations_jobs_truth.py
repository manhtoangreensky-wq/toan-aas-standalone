"""Test suite for SPEC-05: Operations / Jobs surface (P0.WEB.ERP.SPEC05.OPERATIONS.JOBS.TRUTH).

Validates:
- Canonical authority contracts (JOB_AUTHORITY=BOT_CORE, WEB_ROLE=READ_THROUGH_OR_PROJECTION)
- Safety invariants (WEB_DIRECT_BOT_DB_WRITE=NO, JOB_MUTATION_AVAILABLE=NO, RETRY_ACTIONS=0, CANCEL_ACTIONS=0, REQUEUE_ACTIONS=0, PROVIDER_ACTIONS=0)
- Standardized business state taxonomy (QUEUED, RUNNING, BLOCKED, SUCCEEDED, FAILED, UNKNOWN)
- Attention rules (concrete facts only: FAILED, BLOCKED, delivery missing, manual review, refund pending)
- Truthful semantics: UNKNOWN != 0, UNAVAILABLE != HEALTHY, EMPTY != UNKNOWN
- Fake zero prevention: FAKE_ZERO_JOB_COUNT=0, counts['total']=None when UNAVAILABLE
- Bounded read API: /admin/jobs, /admin/jobs/{id}, /api/v1/operations/jobs, /api/v1/operations/jobs/failed, /api/v1/operations/jobs/{id}
- Read-only control plane: POST retry/refund fail-closed with WEBAPP_ADMIN_WRITES_DISABLED
- RBAC: Anonymous & non-admin denied
- SPEC-04 Customer CRM integration: Shared jobs authority and attention linkage
- Browser routes: /admin/jobs, /admin/jobs/failed return HTTP 200
"""

import os
import uuid
import tempfile
import sqlite3
import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_auth
import copyfast_customer_crm_policy as crm_policy
import copyfast_db
from copyfast_db import utc_now
import copyfast_operations_jobs_policy as jobs_policy


@pytest.fixture(scope="module")
def env_setup():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "spec05_jobs_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "spec05-test-secret-67890"
    copyfast_db.ensure_copyfast_schema()
    yield db_path


@pytest.fixture(scope="module")
def auth_client(env_setup):
    client = TestClient(app_module.app)
    email = "admin_jobs_spec05@toanaas.vn"
    password = "correct-horse-battery-staple-2026!"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Jobs Admin"})
    assert reg.status_code == 200
    with sqlite3.connect(env_setup) as conn:
        conn.execute("UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?", (email,))
        conn.commit()
    signed_in = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert signed_in.status_code == 200
    csrf_token = signed_in.json().get("data", {}).get("csrf_token")
    if not csrf_token:
        with sqlite3.connect(env_setup) as conn:
            row = conn.execute("SELECT csrf_token FROM web_sessions ORDER BY created_at DESC LIMIT 1").fetchone()
            csrf_token = row[0] if row else "test-csrf-token"
    client.csrf_token = csrf_token
    return client


@pytest.fixture(scope="module")
def user_client(env_setup):
    client = TestClient(app_module.app)
    email = "regular_user_spec05@toanaas.vn"
    password = "correct-horse-battery-staple-2026!"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Standard User"})
    assert reg.status_code == 200
    signed_in = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert signed_in.status_code == 200
    return client


def test_01_canonical_authority_and_safety_invariants():
    """Verify Section 1: Canonical Authority and safety invariants."""
    assert jobs_policy.JOB_AUTHORITY == "BOT_CORE"
    assert jobs_policy.WEB_ROLE == "READ_THROUGH_OR_PROJECTION"
    assert jobs_policy.WEB_DIRECT_BOT_DB_WRITE is False
    assert jobs_policy.JOB_MUTATION_AVAILABLE is False
    assert jobs_policy.RETRY_ACTIONS == 0
    assert jobs_policy.CANCEL_ACTIONS == 0
    assert jobs_policy.REQUEUE_ACTIONS == 0
    assert jobs_policy.FORCE_COMPLETE_ACTIONS == 0
    assert jobs_policy.PROVIDER_ACTIONS == 0
    assert jobs_policy.FAKE_ZERO_JOB_COUNT == 0


def test_02_standardized_business_state_taxonomy_mapping():
    """Verify Section 2: Standardized business state taxonomy mapping."""
    # 6 Standard business states
    expected_states = {"QUEUED", "RUNNING", "BLOCKED", "SUCCEEDED", "FAILED", "UNKNOWN"}
    assert jobs_policy.VALID_BUSINESS_STATES == expected_states

    # Queued / Pending
    assert jobs_policy.map_job_state("queued") == "QUEUED"
    assert jobs_policy.map_job_state("pending") == "QUEUED"
    assert jobs_policy.map_job_state("submitted") == "QUEUED"

    # Running / Processing
    assert jobs_policy.map_job_state("processing") == "RUNNING"
    assert jobs_policy.map_job_state("running") == "RUNNING"
    assert jobs_policy.map_job_state("in_progress") == "RUNNING"
    assert jobs_policy.map_job_state("rendering") == "RUNNING"

    # Succeeded / Completed
    assert jobs_policy.map_job_state("completed") == "SUCCEEDED"
    assert jobs_policy.map_job_state("succeeded") == "SUCCEEDED"
    assert jobs_policy.map_job_state("success") == "SUCCEEDED"
    assert jobs_policy.map_job_state("done") == "SUCCEEDED"
    assert jobs_policy.map_job_state("delivered") == "SUCCEEDED"

    # Failed / Error
    assert jobs_policy.map_job_state("failed") == "FAILED"
    assert jobs_policy.map_job_state("failed_no_charge") == "FAILED"
    assert jobs_policy.map_job_state("error") == "FAILED"

    # Blocked / Cancelled / Refunded
    assert jobs_policy.map_job_state("cancelled") == "BLOCKED"
    assert jobs_policy.map_job_state("canceled") == "BLOCKED"
    assert jobs_policy.map_job_state("refunded") == "BLOCKED"
    assert jobs_policy.map_job_state("guarded") == "BLOCKED"
    assert jobs_policy.map_job_state("awaiting_confirm") == "BLOCKED"
    assert jobs_policy.map_job_state("draft") == "BLOCKED"

    # Unknown / Null / Unrecognized
    assert jobs_policy.map_job_state(None) == "UNKNOWN"
    assert jobs_policy.map_job_state("") == "UNKNOWN"
    assert jobs_policy.map_job_state("unrecognized_xyz") == "UNKNOWN"


def test_03_attention_rules_concrete_facts_only():
    """Verify Section 3: Safe Attention Rules based on concrete facts only."""
    # Failed jobs require attention
    failed_job = {"id": "j1", "status": "failed", "error_category": "GPU_OOM"}
    att, reasons = jobs_policy.evaluate_job_attention(failed_job)
    assert att is True
    assert any("GPU_OOM" in r for r in reasons)

    # Blocked / Cancelled jobs require attention
    cancelled_job = {"id": "j2", "status": "cancelled"}
    att, reasons = jobs_policy.evaluate_job_attention(cancelled_job)
    assert att is True
    assert "Tác vụ đã hủy" in reasons

    # Completed but missing delivery output requires attention
    broken_delivery_job = {"id": "j3", "status": "completed", "output_available": False, "download_ready": False}
    att, reasons = jobs_policy.evaluate_job_attention(broken_delivery_job)
    assert att is True
    assert any("thiếu tệp đầu ra" in r for r in reasons)

    # Manual review flag requires attention
    manual_review_job = {"id": "j4", "status": "processing", "manual_review": True}
    att, reasons = jobs_policy.evaluate_job_attention(manual_review_job)
    assert att is True
    assert "Yêu cầu quản trị viên đối soát thủ công" in reasons

    # Refund pending requires attention
    refund_pending_job = {"id": "j5", "status": "completed", "refund_status": "pending"}
    att, reasons = jobs_policy.evaluate_job_attention(refund_pending_job)
    assert att is True
    assert any("hoàn phí" in r for r in reasons)

    # Normal running does NOT require attention
    running_job = {"id": "j6", "status": "running"}
    att, reasons = jobs_policy.evaluate_job_attention(running_job)
    assert att is False
    assert len(reasons) == 0

    # Normal queued does NOT require attention
    queued_job = {"id": "j7", "status": "queued"}
    att, reasons = jobs_policy.evaluate_job_attention(queued_job)
    assert att is False
    assert len(reasons) == 0

    # Normal succeeded does NOT require attention
    succeeded_job = {"id": "j8", "status": "completed", "output_available": True, "download_ready": True}
    att, reasons = jobs_policy.evaluate_job_attention(succeeded_job)
    assert att is False
    assert len(reasons) == 0

    # UNKNOWN does NOT invent attention
    unknown_job = {"id": "j9", "status": "unknown_future_status"}
    att, reasons = jobs_policy.evaluate_job_attention(unknown_job)
    assert att is False
    assert len(reasons) == 0


def test_04_truthful_semantics_and_fake_zero_prevention():
    """Verify Section 4: Truthful Semantics (UNKNOWN!=0, UNAVAILABLE!=HEALTHY, FAKE_ZERO_JOB_COUNT=0)."""
    # 1. When bridge is UNAVAILABLE
    summary_unavailable = jobs_policy.synthesize_operations_jobs_summary(
        bridge_available=False,
        bridge_error="CORE_BRIDGE_NOT_CONFIGURED",
    )
    assert summary_unavailable["status"] == "UNAVAILABLE"
    assert summary_unavailable["job_authority"] == "BOT_CORE"
    assert summary_unavailable["fake_zero_job_count"] == 0
    # Must NOT have 0 counts: counts must be None
    assert summary_unavailable["counts"]["total"] is None
    assert summary_unavailable["counts"]["queued"] is None
    assert summary_unavailable["counts"]["running"] is None
    assert summary_unavailable["counts"]["failed"] is None
    assert summary_unavailable["counts"]["succeeded"] is None
    assert summary_unavailable["counts"]["attention"] is None
    assert summary_unavailable["items"] == []

    # 2. When bridge is AVAILABLE but EMPTY
    summary_empty = jobs_policy.synthesize_operations_jobs_summary(
        {"items": []},
        bridge_available=True,
    )
    assert summary_empty["status"] == "EMPTY"
    assert summary_empty["counts"]["total"] == 0
    assert summary_empty["counts"]["queued"] == 0
    assert summary_empty["items"] == []

    # 3. When bridge is AVAILABLE with jobs
    sample_jobs = [
        {"id": "j1", "status": "queued", "feature": "video_render"},
        {"id": "j2", "status": "running", "feature": "video_render"},
        {"id": "j3", "status": "failed", "feature": "image_render", "error_category": "PROVIDER_TIMEOUT"},
        {"id": "j4", "status": "completed", "feature": "audio_tts", "output_available": True, "download_ready": True},
        {"id": "j5", "status": "cancelled", "feature": "video_render"},
    ]
    summary_healthy = jobs_policy.synthesize_operations_jobs_summary(
        {"items": sample_jobs},
        bridge_available=True,
    )
    assert summary_healthy["status"] == "HEALTHY"
    assert summary_healthy["counts"]["total"] == 5
    assert summary_healthy["counts"]["queued"] == 1
    assert summary_healthy["counts"]["running"] == 1
    assert summary_healthy["counts"]["failed"] == 1
    assert summary_healthy["counts"]["succeeded"] == 1
    assert summary_healthy["counts"]["blocked"] == 1
    assert summary_healthy["counts"]["attention"] == 2  # failed + cancelled
    assert len(summary_healthy["items"]) == 5

    # Test filtering by state
    summary_failed_only = jobs_policy.synthesize_operations_jobs_summary(
        {"items": sample_jobs},
        bridge_available=True,
        filter_state="FAILED",
    )
    assert summary_failed_only["counts"]["total"] == 5  # Total count preserved
    assert len(summary_failed_only["items"]) == 1
    assert summary_failed_only["items"][0]["job_id"] == "j3"


def test_05_synthesize_operations_job_record():
    """Verify Section 5: Normalization of job record with customer and project linkage."""
    raw = {
        "id": "job-bot-9999",
        "user_id": "7126457028",
        "account_id": "acc-web-1111",
        "feature": "video_multiscene",
        "job_type": "video",
        "status": "processing",
        "charged_xu": 150,
        "estimated_xu": 150,
        "output_available": False,
        "download_ready": False,
        "created_at": "2026-09-16T10:00:00Z",
    }
    rec = jobs_policy.synthesize_operations_job_record(raw, source_system="BOT_CORE")
    assert rec["job_id"] == "job-bot-9999"
    assert rec["source"] == "BOT_CORE"
    assert rec["canonical_user_id"] == "7126457028"
    assert rec["customer_id"] == "acc-web-1111"
    assert rec["state"] == "RUNNING"
    assert rec["raw_state"] == "processing"
    assert rec["service_context"] == "video_multiscene"
    assert rec["charged_xu"] == 150
    assert rec["mutation_available"] is False
    assert rec["data_source_authority"] == "BOT_CORE"


def test_06_admin_and_operations_jobs_api_endpoints(auth_client):
    """Verify Section 6: Bounded read API endpoints for jobs."""
    # 1. GET /api/v1/admin/jobs
    r_admin_jobs = auth_client.get("/api/v1/admin/jobs")
    assert r_admin_jobs.status_code == 200
    res = r_admin_jobs.json()
    assert res["status"] in ("guarded", "read_only")
    assert "data" in res
    assert res["data"]["job_authority"] == "BOT_CORE"
    assert res["data"]["fake_zero_job_count"] == 0

    # 2. GET /api/v1/admin/jobs/{job_id}
    r_detail = auth_client.get("/api/v1/admin/jobs/job-test-001")
    assert r_detail.status_code == 200
    res_detail = r_detail.json()
    assert res_detail["data"]["job_id"] == "job-test-001"
    assert res_detail["data"]["data_source_authority"] == "BOT_CORE"

    # 3. GET /api/v1/operations/jobs
    r_ops_jobs = auth_client.get("/api/v1/operations/jobs")
    assert r_ops_jobs.status_code == 200
    res_ops = r_ops_jobs.json()
    assert res_ops["data"]["job_authority"] == "BOT_CORE"
    assert res_ops["data"]["fake_zero_job_count"] == 0

    # 4. GET /api/v1/operations/jobs/failed
    r_ops_failed = auth_client.get("/api/v1/operations/jobs/failed")
    assert r_ops_failed.status_code == 200
    res_failed = r_ops_failed.json()
    assert "data" in res_failed

    # 5. GET /api/v1/operations/jobs/{job_id}
    r_ops_detail = auth_client.get("/api/v1/operations/jobs/job-test-001")
    assert r_ops_detail.status_code == 200
    assert r_ops_detail.json()["data"]["job_id"] == "job-test-001"


def test_07_rbac_access_controls(user_client):
    """Verify Section 7: RBAC controls (anonymous & normal users denied)."""
    anon_client = TestClient(app_module.app)

    # Anonymous denied
    r_anon_admin = anon_client.get("/api/v1/admin/jobs")
    assert r_anon_admin.status_code in (401, 403, 307, 302)

    r_anon_ops = anon_client.get("/api/v1/operations/jobs")
    assert r_anon_ops.status_code in (401, 403, 307, 302)

    # Regular user denied
    r_user_admin = user_client.get("/api/v1/admin/jobs")
    assert r_user_admin.status_code == 403

    r_user_ops = user_client.get("/api/v1/operations/jobs")
    assert r_user_ops.status_code == 403


def test_08_read_only_invariants_and_mutation_lock(auth_client):
    """Verify Section 8: Write actions fail-closed (RETRY_ACTIONS=0, CANCEL_ACTIONS=0, etc.)."""
    headers = {"X-CSRF-Token": getattr(auth_client, "csrf_token", "")}

    # 1. POST /api/v1/admin/jobs/{job_id}/retry fails-closed
    r_retry = auth_client.post("/api/v1/admin/jobs/job-1/retry", headers=headers, json={"idempotency_key": "k" * 16})
    assert r_retry.status_code == 200
    res_retry = r_retry.json()
    assert res_retry["ok"] is False
    assert res_retry["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"

    # 2. POST /api/v1/admin/jobs/{job_id}/refund fails-closed
    r_refund = auth_client.post("/api/v1/admin/jobs/job-1/refund", headers=headers, json={"idempotency_key": "k" * 16})
    assert r_refund.status_code == 200
    res_refund = r_refund.json()
    assert res_refund["ok"] is False
    assert res_refund["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"

    # 3. POST /api/v1/operations/jobs/retry fails-closed
    r_ops_retry = auth_client.post("/api/v1/operations/jobs/retry")
    assert r_ops_retry.status_code == 200
    res_ops_retry = r_ops_retry.json()
    assert res_ops_retry["ok"] is False
    assert res_ops_retry["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"


def test_09_customer_crm_jobs_integration():
    """Verify Section 9: Integration with Customer CRM context (SPEC-04)."""
    account = {
        "id": "acc-12345",
        "display_name": "Test User",
        "canonical_user_id": "7126457028",
    }
    # Case 1: Default Unavailable
    crm_ctx = crm_policy.synthesize_customer_crm_context(account)
    assert crm_ctx["jobs"]["data_source"] == "BOT_CORE / CORE_BRIDGE_READ_MODEL"
    assert crm_ctx["jobs"]["status"] == "UNAVAILABLE"
    assert crm_ctx["jobs"]["mutation_available"] is False

    # Case 2: Injected jobs with attention needed triggers action_required
    jobs_summary = {
        "status": "HEALTHY",
        "counts": {"total": 2, "attention": 1},
        "recent_jobs": [{"job_id": "j-failed", "attention_required": True}],
    }
    crm_with_jobs = crm_policy.synthesize_customer_crm_context(account, jobs_summary=jobs_summary)
    assert crm_with_jobs["jobs"]["status"] == "HEALTHY"
    assert crm_with_jobs["action_required"]["has_action"] is True
    assert any("tác vụ cần người vận hành xử lý" in r for r in crm_with_jobs["action_required"]["reasons"])


def test_10_portal_shell_and_browser_routes(auth_client):
    """Verify Section 10: Browser routes render HTTP 200."""
    r_page_jobs = auth_client.get("/admin/jobs")
    assert r_page_jobs.status_code == 200
    assert "text/html" in r_page_jobs.headers["content-type"]

    r_page_failed = auth_client.get("/admin/jobs/failed")
    assert r_page_failed.status_code == 200
    assert "text/html" in r_page_failed.headers["content-type"]
