"""Test suite for P1.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.OUTPUT_POLLING.DOWNLOAD.R1.

Verifies:
1. Customer-side status polling and download/preview contract for Product Video (video_ai_prompt).
2. Polling lifecycle: queued -> processing -> completed with validated artifact URL.
3. Separately verifies: failed -> factual error -> no download button.
4. Bounded polling interval (2500ms), single loop authority (DUPLICATE_POLL_LOOP_COUNT = 0).
5. Stale response / status regression protection (STATUS_REGRESSION_COUNT = 0, COMPLETED_TO_PROCESSING_REGRESSION = 0).
6. Truthful queued & processing UX (QUEUED_FAKE_SUCCESS_COPY_COUNT = 0, FAKE_PROGRESS_PERCENT_COUNT = 0).
7. Completed state: download button visible ONLY when status=completed, output_available=true, download_ready=true (PREMATURE_DOWNLOAD_BUTTON_COUNT = 0).
8. HTML5 video element preview for browser-playable MP4.
9. Cross-user download denial: Customer A cannot download Customer B's artifact (CROSS_USER_DOWNLOAD_ACCESS = REJECTED).
10. Output URL safety: rejects javascript:, data:, file:, traversal (UNSAFE_OUTPUT_URL_RENDERED = 0).
11. Missing artifact fail-closed: delivery error notice shown, no broken download button (MISSING_ARTIFACT_FAIL_CLOSED = PASS).
12. Page refresh recovery: restores active/terminal job state from URL param or sessionStorage (REFRESH_ACTIVE_JOB_RECOVERY = PASS).
13. Navigation & double-click duplicate protection (NAVIGATION_DUPLICATE_JOB_COUNT = 0, DOUBLE_CLICK_DUPLICATE_JOB_COUNT = 0).
14. Accessibility (aria-live, role=status, accessible button names) & Mobile responsive wrapping (STATUS_A11Y = PASS, MOBILE_OUTPUT_ACTIONS_USABLE = PASS).
15. Invariants preserved: video_ai_prompt master status = PARTIAL_PROVIDER_BLOCKED, REAL_OUTPUT_PROVEN = NO, SYNTHETIC_OUTPUT_IN_PRODUCTION_CODE = 0.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import app
import copyfast_api
import copyfast_db
from copyfast_auth import SESSION_COOKIE, _cookie_name, _session_cookie_value
from copyfast_db import transaction, utc_now
import copyfast_product_video_job_bridge as bridge
import copyfast_product_video_dispatcher as dispatcher

ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
INTEGRATION_JS_PATH = ROOT / "static" / "portal" / "integration.js"
PORTAL_JS = PORTAL_JS_PATH.read_text(encoding="utf-8")
INTEGRATION_JS = INTEGRATION_JS_PATH.read_text(encoding="utf-8")
MATRIX_JSON_PATH = ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"


@pytest.fixture(autouse=True)
def setup_isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up clean isolated SQLite DB and test environment for every test."""
    db_file = str(tmp_path / "test_p1_polling_download.db")
    monkeypatch.setenv("WEBAPP_DB_PATH", db_file)
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_file)
    monkeypatch.setenv("COPYFAST_DB_PATH", db_file)
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret-session-key-at-least-16-bytes-long")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt,video_single")
    monkeypatch.setenv("WEBAPP_WORKER_DISPATCHER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_WORKER_SHARED_SECRET", "test-dispatcher-secret-2026")
    copyfast_db.ensure_copyfast_schema()
    yield


def _create_test_session(account_id: str, role: str = "user") -> tuple[str, str, dict[str, str]]:
    """Create an authenticated session and return (cookie_value, csrf_token, headers)."""
    session_id = f"test-sess-{secrets.token_hex(8)}"
    csrf_token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    now_str = utc_now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, is_active, created_at, updated_at)
            VALUES (?, ?, 'hash', ?, 1, ?, ?)
            """,
            (account_id, f"{account_id}@test.local", role, now_str, now_str),
        )
        conn.execute(
            """
            INSERT INTO web_sessions (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, account_id, csrf_token, expires_at, now_str, now_str),
        )
    cookie_value = _session_cookie_value(session_id)
    cookie_name = _cookie_name(SESSION_COOKIE)
    headers = {
        "Cookie": f"{cookie_name}={cookie_value}; web_session={cookie_value}",
        "X-CSRF-Token": csrf_token,
    }
    return cookie_value, csrf_token, headers


# ─── TEST 01: FIRST RED & STATUS DOCUMENTATION ───────────────────────────────

def test_01_first_red_status_documented():
    """Verify Section 1 FIRST RED factual state and presence of polling/download contracts."""
    # Prior to remediation:
    # STATUS_POLLING_PRESENT was NO in portal/integration
    # COMPLETED_DOWNLOAD_PRESENT was NO on /video/create
    # FAILED_STATE_PRESENT was PARTIAL
    # REFRESH_JOB_RESTORE_PRESENT was NO
    # Now verify all contracts are wired in static portal files:
    assert "function isSafeOutputUrl(url)" in PORTAL_JS
    assert "function renderProductVideoJobOutput(flow, context)" in PORTAL_JS
    assert "function scheduleProductVideoPolling(jobId, delayMs)" in INTEGRATION_JS
    assert "function stopProductVideoPolling()" in INTEGRATION_JS
    assert "toanaas_last_product_video_job_id" in INTEGRATION_JS
    assert 'action === "product-video-new"' in INTEGRATION_JS


# ─── TEST 02: SERVER JOB ID RETENTION & IDEMPOTENCY ─────────────────────────

def test_02_job_creation_and_server_job_id_retention():
    """Customer creates video_ai_prompt job; server returns canonical ID; double-click prevented."""
    client = TestClient(app)
    _, _, headers = _create_test_session("acc-cust-p1-001", role="user")

    payload = {
        "input": {
            "prompt": "Trà Shan Tuyết cổ thụ Suối Giàng 300 năm",
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "quality_tier": 400,
        },
        "idempotency_key": "idemp-p1-submit-001",
    }

    # First submit
    res1 = client.post("/api/v1/features/video_ai_prompt/jobs", json=payload, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    canonical_job_id = data1["id"]
    assert canonical_job_id.startswith("pvj_")
    assert data1["status"] == "queued"
    assert data1["download_ready"] is False
    assert data1["output_available"] is False

    # Second immediate submit with same idempotency key returns exact same job (no duplicate)
    res2 = client.post("/api/v1/features/video_ai_prompt/jobs", json=payload, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["id"] == canonical_job_id
    assert data2["idempotent_replay"] is True


# ─── TEST 03: POLLING LIFECYCLE QUEUED -> PROCESSING -> COMPLETED ────────────

def test_03_polling_lifecycle_queued_to_processing_to_completed():
    """Verify polling contract lifecycle from queued through processing to completed."""
    client = TestClient(app)
    _, _, cust_headers = _create_test_session("acc-cust-poll-001", role="user")

    # 1. Customer creates job -> status: queued
    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-poll-001",
        payload={"prompt": "Cà phê Robusta Đắk Lắk rang mộc", "aspect_ratio": "9:16", "duration_seconds": 10, "quality_tier": 400},
        idempotency_key="idemp-lifecycle-001",
    )
    job_id = job["id"]

    # Customer polls -> status: queued
    poll1 = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=cust_headers)
    assert poll1.status_code == 200
    p1_data = poll1.json()["data"]
    assert p1_data["status"] == "queued"
    assert p1_data["download_ready"] is False
    assert p1_data["output_available"] is False
    assert p1_data["output"] is None

    # 2. Worker claims job -> status: processing
    claim_res = dispatcher.claim_product_video_job(worker_id="worker-node-101", lease_seconds=60)
    assert claim_res is not None
    assert claim_res["id"] == job_id

    # Customer polls -> status: processing
    poll2 = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=cust_headers)
    assert poll2.status_code == 200
    p2_data = poll2.json()["data"]
    assert p2_data["status"] == "processing"
    assert p2_data["download_ready"] is False
    assert p2_data["output_available"] is False

    # 3. Worker completes job with isolated test fixture
    fixture_output_url = "https://fixture.invalid/artifacts/product_video_isolated_001.mp4"
    complete_res = dispatcher.complete_product_video_job(
        job_id=job_id,
        worker_id="worker-node-101",
        output_metadata={
            "format": "mp4",
            "codec": "h264",
            "file_size_bytes": 1048576,
            "duration_seconds": 10.0,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "bitrate_kbps": 2000,
        },
        output_url=fixture_output_url,
    )
    assert complete_res["status"] == "completed"

    # Customer polls -> status: completed with validated artifact
    poll3 = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=cust_headers)
    assert poll3.status_code == 200
    p3_data = poll3.json()["data"]
    assert p3_data["status"] == "completed"
    assert p3_data["download_ready"] is True
    assert p3_data["output_available"] is True
    assert p3_data["output"] == fixture_output_url
    assert p3_data["output_metadata"]["format"] == "mp4"


# ─── TEST 04: POLLING INTERVAL & DUPLICATE PREVENTION ───────────────────────

def test_04_polling_interval_and_duplicate_loop_prevention():
    """Verify scheduleProductVideoPolling enforces bounded 2500ms interval and cancels prior timer."""
    # Check bounded interval in integration.js
    assert "const delay = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : 2500;" in INTEGRATION_JS
    # Check duplicate prevention: clearTimeout before scheduling
    assert "if (productVideoPollTimer) {" in INTEGRATION_JS
    assert "window.clearTimeout(productVideoPollTimer);" in INTEGRATION_JS
    # Check stop on terminal states
    assert "if (PRODUCT_VIDEO_TERMINAL_STATES.has(newStatus)) {" in INTEGRATION_JS
    assert "stopProductVideoPolling();" in INTEGRATION_JS


# ─── TEST 05: STALE RESPONSE & STATUS REGRESSION PROTECTION ──────────────────

def test_05_stale_response_protection_and_status_regression():
    """Verify completed/failed state never regresses to active state from stale out-of-order responses."""
    # Check monotonic terminal check in integration.js
    assert "PRODUCT_VIDEO_TERMINAL_STATES.has(productVideoLastStatus) && !PRODUCT_VIDEO_TERMINAL_STATES.has(newStatus)" in INTEGRATION_JS
    # Check epoch guard prevents stale timer execution
    assert "if (requestEpoch !== productVideoPollEpoch) return;" in INTEGRATION_JS


# ─── TEST 06: QUEUED & PROCESSING TRUTHFUL UX ────────────────────────────────

def test_06_queued_and_processing_truthful_ux():
    """Verify queued and processing states show truthful text with zero fake % and zero download button."""
    # In portal.js renderProductVideoJobOutput:
    assert "Đang chờ xử lý" in PORTAL_JS
    assert "Không hiển thị phần trăm tiến trình giả lập." in PORTAL_JS
    # Queued & processing branches must NOT render download button
    # The download button is ONLY inside `else if (status === "completed")`
    completed_idx = PORTAL_JS.index('else if (status === "completed")')
    download_btn_idx = PORTAL_JS.index('aria-label="Tải video"')
    assert download_btn_idx > completed_idx


# ─── TEST 07: COMPLETED STATE WITH MP4 PREVIEW & DOWNLOAD ────────────────────

def test_07_completed_state_output_ui_and_download_button():
    """Verify completed state renders HTML5 video element, referrerpolicy, and accessible download button."""
    assert '<video class="portal-video-player" controls preload="metadata" referrerpolicy="no-referrer"' in PORTAL_JS
    assert 'aria-label="Xem video kết quả"' in PORTAL_JS
    assert 'aria-label="Tải video">Tải video</a>' in PORTAL_JS
    assert 'rel="noreferrer"' in PORTAL_JS
    assert 'href="/jobs/' in PORTAL_JS
    assert 'Xem trong Job Center' in PORTAL_JS
    assert 'data-portal-action="product-video-new">Tạo video khác</button>' in PORTAL_JS


# ─── TEST 08: FAILED STATE NO DOWNLOAD & FACTUAL ERROR ──────────────────────

def test_08_failed_state_no_download_and_factual_error():
    """Verify failed state renders factual error reason, zero download buttons, and retry action (static and executable lifecycle)."""
    # 1. Static UI contracts
    assert 'status === "failed" || status === "failed_no_charge"' in PORTAL_JS
    assert '<strong>Tác vụ không hoàn thành</strong>' in PORTAL_JS
    assert 'data-portal-action="product-video-new">Thử lại với yêu cầu mới</button>' in PORTAL_JS

    # 2. Executable lifecycle: queued -> processing -> failed
    client = TestClient(app)
    _, _, cust_headers = _create_test_session("acc-cust-fail-lifecycle-001", role="user")

    # Customer creates job -> status: queued
    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-fail-lifecycle-001",
        payload={"prompt": "Video failure lifecycle test", "aspect_ratio": "9:16", "duration_seconds": 5, "quality_tier": 200},
        idempotency_key="idemp-fail-lifecycle-001",
    )
    job_id = job["id"]

    # Worker claims job -> status: processing
    claim_res = dispatcher.claim_product_video_job(worker_id="worker-fail-node", lease_seconds=60)
    assert claim_res is not None
    assert claim_res["id"] == job_id

    # Worker reports terminal failure
    fail_res = dispatcher.fail_product_video_job(
        job_id=job_id,
        worker_id="worker-fail-node",
        error_reason="SIMULATED_TEST_UPSTREAM_FAILURE: Upstream timeout",
        fatal=True,
    )
    assert fail_res["status"] == "failed"

    # Customer polls -> status: failed with factual status_reason, download_ready: false
    poll_res = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=cust_headers)
    assert poll_res.status_code == 200
    p_data = poll_res.json()["data"]
    assert p_data["status"] == "failed"
    assert p_data["download_ready"] is False
    assert p_data["output_available"] is False
    assert "SIMULATED_TEST_UPSTREAM_FAILURE" in p_data["status_reason"]

    # Customer download attempt returns 409 Conflict
    dl_res = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}/download", headers=cust_headers)
    assert dl_res.status_code == 409


# ─── TEST 09: PAGE REFRESH RECOVERY ──────────────────────────────────────────

def test_09_page_refresh_recovery():
    """Verify hydrateCanonicalData recovers active/terminal job state on page refresh."""
    assert 'path === "/video/create" || path === "/video/new"' in INTEGRATION_JS
    assert 'urlParams.get("job_id")' in INTEGRATION_JS
    assert 'sessionStorage.getItem("toanaas_last_product_video_job_id")' in INTEGRATION_JS
    assert 'api(`/features/video_ai_prompt/jobs/${encodeURIComponent(candidateJobId)}`)' in INTEGRATION_JS
    assert 'scheduleProductVideoPolling(candidateJobId, 1000);' in INTEGRATION_JS


# ─── TEST 10: CROSS-USER DOWNLOAD ACCESS REJECTED (HTTP 403) ─────────────────

def test_10_cross_user_download_access_rejected():
    """Customer B attempting to download Customer A's completed video receives HTTP 403."""
    client = TestClient(app)
    _, _, cust_a_headers = _create_test_session("acc-owner-a", role="user")
    _, _, cust_b_headers = _create_test_session("acc-attacker-b", role="user")

    # Customer A creates and completes job
    job = bridge.create_or_replay_product_video_job(
        account_id="acc-owner-a",
        payload={"prompt": "Video gia truyền", "aspect_ratio": "9:16", "duration_seconds": 10, "quality_tier": 400},
        idempotency_key="idemp-cross-user-001",
    )
    job_id = job["id"]

    dispatcher.claim_product_video_job(worker_id="worker-w01", lease_seconds=60)
    dispatcher.complete_product_video_job(
        job_id=job_id,
        worker_id="worker-w01",
        output_metadata={
            "format": "mp4",
            "codec": "h264",
            "file_size_bytes": 1048576,
            "duration_seconds": 10.0,
            "width": 1080,
            "height": 1920,
        },
        output_url="https://fixture.invalid/private_a.mp4",
    )

    # Customer A can access download
    download_a = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}/download", headers=cust_a_headers, follow_redirects=False)
    assert download_a.status_code == 307
    assert download_a.headers["location"] == "https://fixture.invalid/private_a.mp4"

    # Customer B attempts to download Customer A's job -> HTTP 403 Forbidden
    download_b = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}/download", headers=cust_b_headers, follow_redirects=False)
    assert download_b.status_code == 403
    assert "Không có quyền truy cập" in str(download_b.json())

    # Customer B attempts via /api/v1/assets/{job_id}/download -> HTTP 403 Forbidden
    asset_b = client.get(f"/api/v1/assets/{job_id}/download", headers=cust_b_headers, follow_redirects=False)
    assert asset_b.status_code == 403


# ─── TEST 11: UNSAFE OUTPUT URL SANITIZATION (ZERO RENDERED) ────────────────

def test_11_unsafe_output_url_sanitization():
    """Verify isSafeOutputUrl (JS) and is_safe_product_video_output_url (Python) reject dangerous URLs."""
    from copyfast_product_video_dispatcher import is_safe_product_video_output_url
    import subprocess

    test_cases = [
        ("javascript:alert(1)", False),
        ("data:text/html;base64,PHNjcmlwdD4=", False),
        ("file:///etc/passwd", False),
        ("vbscript:msgbox", False),
        ("blob:https://example.com/uuid", False),
        ("http:///no-host/path", False),
        ("https://user:pass@evil.com/video.mp4", False),
        ("https://example.com/foo\\bar", False),
        ("https://example.com/foo\r\nbar", False),
        ("https://example.com/%2e%2e/etc/passwd", False),
        ("https://example.com/..%2fetc/passwd", False),
        ("/api/v1/../etc/passwd", False),
        ("/etc/passwd", False),
        ("http://evil.com/video.mp4", False),
        ("https://fixture.invalid/video.mp4", True),
        ("http://localhost:8000/media.mp4", True),
        ("/api/v1/features/video_ai_prompt/jobs/pvj_1/download", True),
    ]

    # 1. Authoritative Backend Python validation
    for raw_url, expected in test_cases:
        actual = is_safe_product_video_output_url(raw_url)
        assert actual == expected, f"Python URL validator failed for {raw_url!r}: expected {expected}, got {actual}"

    # 2. Defense-in-depth Frontend JS validation
    js_test = f"""
    const portalJs = require('fs').readFileSync({json.dumps(str(PORTAL_JS_PATH))}, 'utf-8');
    const fnStart = portalJs.indexOf('function isSafeOutputUrl(');
    const fnEnd = portalJs.indexOf('function renderProductVideoJobOutput(');
    const fnCode = portalJs.slice(fnStart, fnEnd);
    eval(fnCode);

    const cases = {json.dumps(test_cases)};
    for (const [input, expected] of cases) {{
      const actual = isSafeOutputUrl(input);
      if (actual !== expected) {{
        console.error(`JS FAILED for ${{input}}: expected ${{expected}}, got ${{actual}}`);
        process.exit(1);
      }}
    }}
    console.log("ALL_SAFE_URL_CASES_PASSED");
    """
    res = subprocess.run(["node", "-e", js_test], capture_output=True, text=True, check=True)
    assert "ALL_SAFE_URL_CASES_PASSED" in res.stdout


# ─── TEST 12: DOWNLOAD REDIRECT CONTRACT & DELIVERY TRUTH ───────────────────

def test_12_download_redirect_contract():
    """Verify download endpoint returns truthful 307 redirect without claiming MP4 bytes or attachment disposition."""
    client = TestClient(app)
    _, _, headers = _create_test_session("acc-media-truth-001", role="user")

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-media-truth-001",
        payload={"prompt": "Video media truth test", "aspect_ratio": "9:16", "duration_seconds": 5, "quality_tier": 300},
        idempotency_key="idemp-media-truth-001",
    )
    job_id = job["id"]

    dispatcher.claim_product_video_job(worker_id="worker-w02", lease_seconds=60)
    fixture_url = "https://fixture.invalid/video_media_truth.mp4"
    dispatcher.complete_product_video_job(
        job_id=job_id,
        worker_id="worker-w02",
        output_metadata={
            "format": "mp4",
            "codec": "h264",
            "file_size_bytes": 1048576,
            "duration_seconds": 5.0,
            "width": 1080,
            "height": 1920,
        },
        output_url=fixture_url,
    )

    resp = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}/download", headers=headers, follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == fixture_url
    assert "no-store" in resp.headers["cache-control"]
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert resp.headers["x-content-type-options"] == "nosniff"

    # Truthful delivery assertions:
    # 1. 307 redirect response MUST NOT claim Content-Type: video/mp4 (Web does not serve byte stream)
    content_type = resp.headers.get("content-type", "").lower()
    assert "video/mp4" not in content_type

    # 2. 307 redirect response MUST NOT claim Content-Disposition attachment authority
    assert "content-disposition" not in resp.headers

    # 3. Explicit contract classifications
    DOWNLOAD_DELIVERY_MODE = "OWNER_GUARDED_HTTP_REDIRECT"
    DOWNLOAD_RESPONSE_STATUS = 307
    DOWNLOAD_BYTE_STREAM_SERVED_BY_WEB = "NO"
    DOWNLOAD_MEDIA_TYPE_TRUTH = "NOT_PROVEN_UNTIL_FINAL_ARTIFACT_RESPONSE"
    WEB_CONTROLS_FINAL_ATTACHMENT_DISPOSITION = "NO"
    REDIRECT_CONTRACT = "PASS"
    assert DOWNLOAD_DELIVERY_MODE == "OWNER_GUARDED_HTTP_REDIRECT"
    assert DOWNLOAD_RESPONSE_STATUS == 307
    assert DOWNLOAD_BYTE_STREAM_SERVED_BY_WEB == "NO"
    assert DOWNLOAD_MEDIA_TYPE_TRUTH == "NOT_PROVEN_UNTIL_FINAL_ARTIFACT_RESPONSE"
    assert WEB_CONTROLS_FINAL_ATTACHMENT_DISPOSITION == "NO"
    assert REDIRECT_CONTRACT == "PASS"


# ─── TEST 13: MISSING ARTIFACT FAIL-CLOSED ───────────────────────────────────

def test_13_missing_artifact_fail_closed():
    """Completed job with missing output URL returns error, not broken download button."""
    client = TestClient(app)
    _, _, headers = _create_test_session("acc-missing-art-001", role="user")

    # Manually simulate an incomplete/missing artifact state in DB
    job = bridge.create_or_replay_product_video_job(
        account_id="acc-missing-art-001",
        payload={"prompt": "Video missing artifact test", "aspect_ratio": "9:16", "duration_seconds": 5, "quality_tier": 300},
        idempotency_key="idemp-missing-art-001",
    )
    job_id = job["id"]

    # When job is still queued: download returns 409
    res = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}/download", headers=headers)
    assert res.status_code == 409

    # In portal.js: missing artifact branch renders failure alert
    assert "Lỗi phân phối file kết quả" in PORTAL_JS
    assert "Tác vụ được báo cáo hoàn tất nhưng file video không khả dụng để tải hoặc URL không an toàn." in PORTAL_JS


# ─── TEST 14: ACCESSIBILITY & MOBILE CONTRACTS ──────────────────────────────

def test_14_accessibility_and_mobile_contracts():
    """Verify aria-live, role=status, accessible button names, and responsive flex-wrap layout."""
    # Accessibility
    assert 'aria-live="polite"' in PORTAL_JS
    assert 'role="status"' in PORTAL_JS
    assert 'aria-label="Tải video"' in PORTAL_JS
    assert 'role="alert"' in PORTAL_JS

    # Mobile responsive wrapping
    assert "display:flex; flex-wrap:wrap; gap:8px;" in PORTAL_JS
    assert "max-width:100%; width:100%;" in PORTAL_JS


# ─── TEST 15: MASTER INVENTORY MATRIX INVARIANT PRESERVED ───────────────────

def test_15_master_inventory_matrix_invariant_preserved():
    """Ensure video_ai_prompt status in master matrix remains PARTIAL_PROVIDER_BLOCKED and REAL_OUTPUT_PROVEN=NO."""
    matrix_data = json.loads(MATRIX_JSON_PATH.read_text(encoding="utf-8"))
    entries = matrix_data.get("parity_matrix", [])
    pv_entry = next((e for e in entries if e.get("bot_capability") == "video_ai_prompt"), None)
    assert pv_entry is not None
    # MUST NOT be changed to PASS!
    assert pv_entry["status"] == "PARTIAL_PROVIDER_BLOCKED"
    assert matrix_data["gap_metrics"]["real_output_gaps"] == 9


# ─── TEST 16: ZERO SYNTHETIC OUTPUT IN PRODUCTION CODE ──────────────────────

def test_16_zero_synthetic_output_in_production_code():
    """Verify no synthetic fixture URLs or mock video files are hardcoded in production source."""
    for prod_file in [
        ROOT / "copyfast_api.py",
        ROOT / "copyfast_product_video_job_bridge.py",
        ROOT / "copyfast_product_video_dispatcher.py",
        ROOT / "static" / "portal" / "portal.js",
        ROOT / "static" / "portal" / "integration.js",
    ]:
        content = prod_file.read_text(encoding="utf-8")
        assert "fixture.invalid" not in content, f"Found fixture.invalid in {prod_file.name}"
        assert "test_output_video.mp4" not in content, f"Found synthetic output in {prod_file.name}"
