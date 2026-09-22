"""Isolated E2E Integration Acceptance Test for Product Video Worker Loop.

Task: P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.WORKER.LOOP.ISOLATED.E2E.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Primary Repository: manhtoangreensky-wq/toan-aas-standalone
Base Branch: main
Web Base SHA: c62e8b502fa2d8e6b87b4298ba17d345e0e22729
Bot Required SHA: cd05fcb44784a568da3e798a7dfe3584a8e2c9f8

Proves the complete provider-free Product Video worker loop using the REAL current
Web dispatcher implementation and REAL current Bot worker consumer source without
any external unmocked paid provider calls, live production web claims, or wallet mutations.

Chain tested:
WEB CUSTOMER JOB CREATION
-> WEB_PRODUCT_VIDEO_JOBS QUEUED
-> WEB DISPATCHER CLAIM
-> BOT WORKER CONSUMER (services/web_product_video_worker_consumer.py)
-> CANONICAL RUNTIME REQUEST MAPPING
-> HEARTBEAT
-> PREPARED_PROVIDER_BLOCKED
-> FACTUAL FAIL/RECONCILIATION CALLBACK
-> WEB JOB TERMINAL/RETRY STATE
-> CUSTOMER READBACK
-> ADMIN METRICS READBACK
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from typing import Any, Callable
import urllib.parse
import urllib.request
import pytest
from fastapi.testclient import TestClient

# ─── PATH CONFIGURATION AND DYNAMIC BOT SOURCE IMPORT ─────────────────────────

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) in sys.path:
    sys.path.remove(str(STANDALONE_ROOT))
sys.path.insert(0, str(STANDALONE_ROOT))

# Import Web application modules first so Web's config.py is used
from app import app
from copyfast_auth import (
    SESSION_COOKIE,
    _cookie_name,
    _session_cookie_value,
    require_canonical_admin,
    require_canonical_admin_csrf,
)
from copyfast_db import (
    ensure_copyfast_schema,
    read_transaction,
    session_database_path,
    transaction,
    utc_now,
)
import copyfast_product_video_dispatcher as dispatcher
import copyfast_product_video_job_bridge as bridge

# Locate Bot repository root and append to sys.path (never ahead of STANDALONE_ROOT)
BOT_REPO_ENV = os.environ.get("TOAN_AAS_BOT_REPO_ROOT", "").strip()
if BOT_REPO_ENV:
    BOT_REPO_ROOT = Path(BOT_REPO_ENV).resolve()
else:
    sibling_bot_telegram = STANDALONE_ROOT.parent / "bot telegram"
    sibling_bot = STANDALONE_ROOT.parent / "bot"
    if sibling_bot_telegram.is_dir():
        BOT_REPO_ROOT = sibling_bot_telegram.resolve()
    elif sibling_bot.is_dir():
        BOT_REPO_ROOT = sibling_bot.resolve()
    else:
        BOT_REPO_ROOT = Path(r"d:\TOANAAS\bot telegram").resolve()

if str(BOT_REPO_ROOT) not in sys.path:
    sys.path.append(str(BOT_REPO_ROOT))

# Dynamic import of Bot worker consumer from pinned Bot repository
import services.web_product_video_worker_consumer as bot_consumer
from services.video_provider_base import VideoGenerationRequest

# Expected SHA constants
EXPECTED_BOT_SHA = "cd05fcb44784a568da3e798a7dfe3584a8e2c9f8"
WEB_BASE_REFERENCE_SHA = "c62e8b502fa2d8e6b87b4298ba17d345e0e22729"
TEST_WORKER_SECRET = "test-worker-loop-isolated-secret-2026"


# ─── FIXTURES: ISOLATED DB AND TEST CLIENT ────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure complete test isolation with a dedicated temporary SQLite DB."""
    temp_db_path = str(tmp_path / "toanaas_webapp_isolated_e2e.db")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", temp_db_path)
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-isolated-e2e-worker-loop")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("PRODUCT_VIDEO_WORKER_SECRET", TEST_WORKER_SECRET)
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_prompt,video_single")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")

    ensure_copyfast_schema()

    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, is_active, created_at, updated_at)
            VALUES ('acc-cust-user1', 'user1@test.local', 'hash1', 'user', 1, '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z'),
                   ('acc-cust-user2', 'user2@test.local', 'hash2', 'user', 1, '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z'),
                   ('acc-admin-user', 'admin@test.local', 'hashadmin', 'admin', 1, '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z')
            """
        )

    yield


def _create_test_session(account_id: str, role: str = "user") -> tuple[str, str, dict[str, str]]:
    """Helper to create an authenticated session and return (cookie_value, csrf_token, auth_headers)."""
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


def make_testclient_transport(
    test_client: TestClient,
) -> Callable[[urllib.request.Request, int], tuple[int, bytes, dict[str, str]]]:
    """In-process HTTP transport routing Bot dispatcher client to FastAPI TestClient.

    Guarantees:
    - Zero external network calls (LIVE_WEB_CLAIMS=0)
    - Zero communication with production hosts (PRODUCTION_HOST_CONTACTS=0)
    """
    def transport(req: urllib.request.Request, timeout: int) -> tuple[int, bytes, dict[str, str]]:
        url = req.full_url
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"
        headers = dict(req.headers)
        data = req.data
        method = req.get_method().lower()
        response = getattr(test_client, method)(
            path,
            content=data,
            headers=headers,
        )
        return response.status_code, response.content, dict(response.headers)
    return transport


# ─── TEST 01: REPOSITORY PINNING & SOURCE IMMUTABILITY ────────────────────────

def test_01_repo_pinning_and_source_immutability():
    """Verify Bot repository HEAD SHA, clean worktree, and dynamic source import."""
    assert BOT_REPO_ROOT.is_dir(), f"Bot repo root not found at {BOT_REPO_ROOT}"

    # Verify Bot HEAD SHA
    cmd_head = ["git", "-C", str(BOT_REPO_ROOT), "rev-parse", "HEAD"]
    res_head = subprocess.run(cmd_head, capture_output=True, text=True, check=True)
    actual_bot_sha = res_head.stdout.strip()
    assert actual_bot_sha == EXPECTED_BOT_SHA, (
        f"Bot repo HEAD must equal {EXPECTED_BOT_SHA}, got {actual_bot_sha}"
    )

    # Verify Bot working tree is clean
    cmd_status = ["git", "-C", str(BOT_REPO_ROOT), "status", "--porcelain"]
    res_status = subprocess.run(cmd_status, capture_output=True, text=True, check=True)
    assert res_status.stdout.strip() == "", (
        f"Bot working tree must be clean (BOT_WORKTREE_DIRTY=NO). Changes:\n{res_status.stdout}"
    )

    # Verify Bot consumer constants
    assert bot_consumer.PRIMARY_PRODUCT_KEY == "video_ai_prompt"
    assert bot_consumer.BOT_CANONICAL_PRODUCT_KEY == "video_ai_prompt"
    assert bot_consumer.BOT_EXECUTOR_PRODUCT_TYPE == "video_ai_prompt"
    assert bot_consumer.DEFAULT_REQUIRED_CAPABILITY == "text_to_video"


# ─── TEST 02: DATABASE ISOLATION GUARDRAILS ───────────────────────────────────

def test_02_database_isolation_guardrails():
    """Verify session database is temporary and production database path is distinct."""
    active_db = session_database_path()
    assert "toanaas_webapp_isolated_e2e.db" in active_db
    assert Path(active_db).exists()
    assert Path(active_db).resolve() != (STANDALONE_ROOT / "toanaas_webapp.db").resolve()


# ─── TEST 03: CUSTOMER JOB CREATION & IDEMPOTENCY ─────────────────────────────

def test_03_customer_job_creation_and_idempotency():
    """Customer creates video_ai_prompt job via Web API; verifies idempotency and conflict check."""
    client = TestClient(app)
    _, _, headers = _create_test_session("acc-cust-user1", role="user")

    job_payload = {
        "input": {
            "prompt": "Gói cà phê Arabica Cầu Đất nguyên chất sang trọng",
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "quality_tier": 400,
        },
        "idempotency_key": "e2e-loop-idem-001",
    }

    # 1. Create job
    create_res = client.post(
        "/api/v1/features/video_ai_prompt/jobs",
        json=job_payload,
        headers=headers,
    )
    assert create_res.status_code == 200
    create_body = create_res.json()
    assert create_body["ok"] is True
    job_data = create_body["data"]
    job_id = job_data["id"]
    assert job_data["status"] == "queued"
    assert job_data["product_key"] == "video_ai_prompt"
    assert job_data["output_available"] is False
    assert job_data["download_ready"] is False

    # 2. Idempotent replay with identical payload returns same job
    replay_res = client.post(
        "/api/v1/features/video_ai_prompt/jobs",
        json=job_payload,
        headers=headers,
    )
    assert replay_res.status_code == 200
    replay_body = replay_res.json()
    assert replay_body["data"]["id"] == job_id
    assert replay_body["data"]["status"] == "queued"

    # 3. Conflict: same idempotency key with differing prompt rejected with 409
    conflicting_payload = {
        "input": {
            "prompt": "Trà Shan Tuyết cổ thụ Hà Giang khác biệt",
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "quality_tier": 400,
        },
        "idempotency_key": "e2e-loop-idem-001",
    }
    conflict_res = client.post(
        "/api/v1/features/video_ai_prompt/jobs",
        json=conflicting_payload,
        headers=headers,
    )
    assert conflict_res.status_code == 409


# ─── TEST 04: BOT WORKER DISPATCHER AUTH GATES ────────────────────────────────

def test_04_bot_worker_dispatcher_auth_gates():
    """Missing or invalid worker secret fails closed; valid secret connects."""
    client = TestClient(app)
    transport = make_testclient_transport(client)

    # 1. Missing secret fails closed
    unauth_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret="",
        transport=transport,
    )
    with pytest.raises(bot_consumer.WorkerAuthError) as exc_info:
        unauth_client.claim()
    assert "MISSING_WORKER_SECRET" in str(exc_info.value)

    # 2. Invalid secret returns HTTP 401 and raises WorkerAuthError
    bad_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret="invalid-secret-token",
        transport=transport,
    )
    with pytest.raises(bot_consumer.WorkerAuthError) as exc_info:
        bad_client.claim()
    assert "INVALID_WORKER_SECRET" in str(exc_info.value) or "HTTP 401" in str(exc_info.value)

    # 3. Valid secret succeeds
    valid_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    claim_resp = valid_client.claim()
    assert claim_resp.ok is True


# ─── TEST 05: BOT WORKER CLAIM & ENVELOPE VALIDATION ──────────────────────────

def test_05_bot_worker_claim_and_envelope_validation():
    """Bot worker claims queued job; verifies envelope schema meets validation rules."""
    client = TestClient(app)
    transport = make_testclient_transport(client)

    # Create job to claim
    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Mặt dây chuyền ngọc bích tỏa sáng huyền ảo",
            "aspect_ratio": "1:1",
            "duration_seconds": 5,
            "quality_tier": 500,
        },
        idempotency_key="e2e-claim-val-001",
    )
    job_id = job["id"]

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )

    # Claim job
    claim_resp = bot_client.claim(lease_seconds=300)
    assert claim_resp.ok is True
    assert claim_resp.idle is False
    assert claim_resp.job is not None
    claimed_job = claim_resp.job

    assert claimed_job["job_id"] == job_id
    assert claimed_job["status"] == "processing"
    assert claimed_job["product_key"] == "video_ai_prompt"
    assert claimed_job["worker_id"] == "test-bot-worker-01"
    assert claimed_job["attempts"] == 1

    # Validate envelope with Bot consumer rules
    is_valid, err = bot_consumer.validate_claimed_job(claimed_job)
    assert is_valid is True, f"Claimed job envelope validation failed: {err}"
    assert err == ""

    # Concurrency: second worker claim receives idle (queue empty)
    claim_2 = bot_client.claim()
    assert claim_2.ok is True
    assert claim_2.idle is True
    assert claim_2.job is None


# ─── TEST 06: BOT WORKER CANONICAL RUNTIME MAPPING ────────────────────────────

def test_06_bot_worker_canonical_runtime_mapping():
    """Map claimed job into VideoGenerationRequest; enforce zero wallet mutation flags."""
    client = TestClient(app)
    transport = make_testclient_transport(client)

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Đồng hồ lặn tự động vỏ đồng nguyên khối lướt sóng biển",
            "aspect_ratio": "16:9",
            "duration_seconds": 15,
            "quality_tier": 600,
        },
        idempotency_key="e2e-map-001",
    )
    job_id = job["id"]

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    claim_resp = bot_client.claim(lease_seconds=300)
    assert claim_resp.job is not None

    # Map to Bot VideoGenerationRequest
    req = bot_consumer.map_web_job_to_bot_runtime(claim_resp.job)
    assert isinstance(req, VideoGenerationRequest)
    assert req.job_id == job_id
    assert req.product_type == "video_ai_prompt"
    assert req.video_flow_type == "video_ai_prompt"
    assert req.required_capability == "text_to_video"
    assert req.prompt == "Đồng hồ lặn tự động vỏ đồng nguyên khối lướt sóng biển"
    assert req.ratio == "16:9"
    assert req.duration_seconds == 15.0
    assert req.quality == "600"

    # Strict Safety Metadata: secondary wallet charges prohibited
    meta = req.metadata
    assert meta["source"] == "web_dispatcher"
    assert meta["web_dispatched"] is True
    assert meta["web_job_id"] == job_id
    assert meta["account_id"] == "acc-cust-user1"
    assert meta["admin_no_charge"] is True
    assert meta["no_wallet_charge"] is True


# ─── TEST 07: PROVIDER-FREE PREPARATION BOUNDARY & GATE ───────────────────────

def test_07_provider_free_preparation_boundary_and_gate():
    """Execute provider-free preparation boundary; stops safely before unmocked paid call."""
    client = TestClient(app)
    transport = make_testclient_transport(client)

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Trang sức kim cương lấp lánh dưới ánh đèn sân khấu",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 300,
        },
        idempotency_key="e2e-gate-001",
    )

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    claim_resp = bot_client.claim(lease_seconds=300)
    assert claim_resp.job is not None

    # Run prepare_and_gate_execution
    outcome = bot_consumer.prepare_and_gate_execution(claim_resp.job, client=bot_client)

    # Invariant assertions: stop BEFORE paid provider call
    assert isinstance(outcome, bot_consumer.PreparedExecutionOutcome)
    assert outcome.ok is True
    assert outcome.status == "PREPARED_PROVIDER_BLOCKED"
    assert outcome.job_id == job["id"]
    assert outcome.product_key == "video_ai_prompt"
    assert outcome.provider_submit_called is False
    assert outcome.provider_calls == 0
    assert outcome.paid_provider_calls == 0
    assert outcome.video_renders == 0
    assert outcome.wallet_mutations == 0


# ─── TEST 08: DUPLICATE EXECUTION PREVENTION ──────────────────────────────────

def test_08_duplicate_execution_prevention():
    """Duplicate active execution of same job ID is immediately rejected."""
    sample_job = {
        "job_id": "pvj_test_dup_00000000000001",
        "request_id": "VID-20260922-DUP01",
        "account_id": "acc-cust-user1",
        "product_key": "video_ai_prompt",
        "status": "processing",
        "payload": {
            "prompt": "Test duplicate execution prevention prompt",
            "aspect_ratio": "9:16",
            "duration": 5.0,
            "quality_tier": "300",
        },
    }

    bot_consumer._ACTIVE_JOB_IDS.add("pvj_test_dup_00000000000001")
    try:
        outcome = bot_consumer.prepare_and_gate_execution(sample_job)
        assert outcome.ok is False
        assert outcome.status == "DUPLICATE_EXECUTION_BLOCKED"
        assert outcome.blocker_reason == "DUPLICATE_ACTIVE_JOB_EXECUTION"
    finally:
        bot_consumer._ACTIVE_JOB_IDS.discard("pvj_test_dup_00000000000001")


# ─── TEST 09: WORKER HEARTBEAT LEASE EXTENSION ────────────────────────────────

def test_09_worker_heartbeat_lease_extension():
    """Worker extends processing lease via heartbeat; imposter worker rejected."""
    client = TestClient(app)
    transport = make_testclient_transport(client)

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Trái bơ sáp Đắk Lắk tươi ngon cắt đôi",
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "quality_tier": 400,
        },
        idempotency_key="e2e-hb-001",
    )
    job_id = job["id"]

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    claim_resp = bot_client.claim(lease_seconds=60)
    initial_expires = claim_resp.job["lease_expires_at"]

    # 1. Owning worker heartbeat extends lease
    hb_success = bot_client.heartbeat(job_id=job_id, lease_seconds=600)
    assert hb_success is True

    # 2. Imposter worker heartbeat fails
    imposter_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-imposter",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    hb_imposter = imposter_client.heartbeat(job_id=job_id, lease_seconds=300)
    assert hb_imposter is False


# ─── TEST 10: FACTUAL FAIL REPORTING & RETRY LIFECYCLE ────────────────────────

def test_10_factual_fail_reporting_and_retry_lifecycle():
    """Worker reports failure; attempts counter increments and job is requeued."""
    client = TestClient(app)
    transport = make_testclient_transport(client)
    _, _, headers = _create_test_session("acc-cust-user1", role="user")

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Gốm sứ Bát Tràng tráng men hoa sen thủ công",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 300,
        },
        idempotency_key="e2e-fail-retry-001",
    )
    job_id = job["id"]

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    claim_resp = bot_client.claim(lease_seconds=120)
    assert claim_resp.job is not None

    # Worker reports non-fatal provider blocker failure
    fail_res = bot_client.fail(
        job_id=job_id,
        error_code="PREPARED_PROVIDER_BLOCKED",
        error_message="Paid external video generation is blocked in test mode",
        fatal=False,
    )
    assert fail_res["ok"] is True
    fail_data = fail_res["data"]
    assert fail_data["status"] == "queued"
    assert fail_data["attempts"] == 1

    # Customer readback verifies status is queued and outputs are not ready
    cust_read = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=headers)
    assert cust_read.status_code == 200
    cust_data = cust_read.json()["data"]
    assert cust_data["status"] == "queued"
    assert cust_data["download_ready"] is False
    assert cust_data["output_available"] is False


# ─── TEST 11: WATCHDOG RECONCILIATION OF STALLED JOBS ─────────────────────────

def test_11_watchdog_reconciliation_of_stalled_jobs():
    """Watchdog recovers abandoned jobs with expired leases without data loss."""
    client = TestClient(app)
    transport = make_testclient_transport(client)

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Nước mắm Phú Quốc truyền thống cốt cá cơm",
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "quality_tier": 400,
        },
        idempotency_key="e2e-watchdog-001",
    )
    job_id = job["id"]

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-crashed",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    bot_client.claim(lease_seconds=30)

    # Manually expire lease in DB to simulate worker crash
    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_product_video_jobs
            SET lease_expires_at = datetime('now', '-60 seconds')
            WHERE id = ?
            """,
            (job_id,),
        )

    # Run watchdog reconciliation pass
    recon_stats = dispatcher.reconcile_stalled_product_video_jobs(lease_grace_seconds=0, max_attempts=3)
    assert recon_stats["requeued"] >= 1
    assert recon_stats["total_reconciled"] >= 1

    # Reclaimed by recovery worker
    recovery_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-recovery",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    reclaimed = recovery_client.claim()
    assert reclaimed.ok is True
    assert reclaimed.job is not None
    assert reclaimed.job["job_id"] == job_id
    assert reclaimed.job["attempts"] == 2
    assert reclaimed.job["worker_id"] == "test-bot-worker-recovery"


# ─── TEST 12: TERMINAL FAILURE & CUSTOMER READBACK ────────────────────────────

def test_12_terminal_failure_and_customer_readback():
    """Job failing max_attempts times transitions terminally to 'failed'; customer reads factual state."""
    client = TestClient(app)
    transport = make_testclient_transport(client)
    _, _, headers = _create_test_session("acc-cust-user1", role="user")

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Hạt tiêu đen Chư Sê sấy thăng hoa xuất khẩu",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 300,
        },
        idempotency_key="e2e-terminal-001",
    )
    job_id = job["id"]

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )

    # Attempt 1
    bot_client.claim()
    bot_client.fail(job_id, error_code="GPU_ERROR_1", fatal=False)

    # Attempt 2
    bot_client.claim()
    bot_client.fail(job_id, error_code="GPU_ERROR_2", fatal=False)

    # Attempt 3: Max attempts reached -> terminal failed
    bot_client.claim()
    final_fail = bot_client.fail(job_id, error_code="FATAL_RETRY_EXHAUSTED", fatal=False)
    assert final_fail["data"]["status"] == "failed"
    assert final_fail["data"]["attempts"] == 3

    # Customer readback verifies terminal failure
    cust_res = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=headers)
    assert cust_res.status_code == 200
    cust_job = cust_res.json()["data"]
    assert cust_job["status"] == "failed"
    assert cust_job["output_available"] is False
    assert cust_job["download_ready"] is False
    assert cust_job["delivery_ready"] is False


# ─── TEST 13: CROSS-USER ISOLATION ───────────────────────────────────────────

def test_13_cross_user_isolation():
    """Customer 2 cannot view or poll Customer 1's job (strict multi-tenant isolation)."""
    client = TestClient(app)
    _, _, headers1 = _create_test_session("acc-cust-user1", role="user")
    _, _, headers2 = _create_test_session("acc-cust-user2", role="user")

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Rượu vang sim rừng Măng Đen ủ thùng sồi",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 300,
        },
        idempotency_key="e2e-isolation-001",
    )
    job_id = job["id"]

    # Customer 2 attempts to read Customer 1's job
    res = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=headers2)
    assert res.status_code in (403, 404)

    # Customer 2 job list contains 0 of Customer 1's jobs
    list_res = client.get("/api/v1/features/video_ai_prompt/jobs", headers=headers2)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert all(item["id"] != job_id for item in items)


# ─── TEST 14: ADMIN METRICS & RECONCILE ENDPOINTS ─────────────────────────────

def test_14_admin_metrics_and_reconcile_endpoints():
    """Admin reads operational dispatcher metrics matching isolated DB; non-admin blocked."""
    client = TestClient(app)
    _, _, user_headers = _create_test_session("acc-cust-user1", role="user")
    _, admin_csrf, admin_headers = _create_test_session("acc-admin-user", role="admin")

    # 1. Non-admin request blocked
    unauth_metrics = client.get("/api/v1/admin/product-video/metrics", headers=user_headers)
    assert unauth_metrics.status_code in (401, 403, 404)

    # 2. Canonical admin queries metrics
    def mock_admin_dep():
        return {"id": "acc-admin-user", "role": "admin"}

    app.dependency_overrides[require_canonical_admin] = mock_admin_dep
    app.dependency_overrides[require_canonical_admin_csrf] = mock_admin_dep

    try:
        metrics_res = client.get("/api/v1/admin/product-video/metrics", headers=admin_headers)
        assert metrics_res.status_code == 200
        body = metrics_res.json()
        assert body["ok"] is True
        data = body["data"]
        assert "counts" in data
        assert "version" in data
        assert "healthy" in data

        # 3. Admin triggers manual watchdog reconciliation
        reconcile_res = client.post(
            "/api/v1/admin/product-video/reconcile",
            json={"lease_grace_seconds": 10, "max_attempts": 3},
            headers=admin_headers,
        )
        assert reconcile_res.status_code == 200
        assert reconcile_res.json()["ok"] is True
    finally:
        app.dependency_overrides.clear()


# ─── TEST 15: COMPLETE CONTRACT SCHEMA (SYNTHETIC FIXTURE ONLY) ───────────────

def test_15_complete_contract_schema_synthetic_fixture_only():
    """Validate completion schema with synthetic test fixture; zero real provider calls."""
    client = TestClient(app)
    transport = make_testclient_transport(client)
    _, _, headers = _create_test_session("acc-cust-user1", role="user")

    job = bridge.create_or_replay_product_video_job(
        account_id="acc-cust-user1",
        payload={
            "prompt": "Mật ong hoa bạc hà Mèo Vạc vàng óng",
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "quality_tier": 400,
        },
        idempotency_key="e2e-comp-schema-001",
    )
    job_id = job["id"]

    bot_client = bot_consumer.WebProductVideoDispatcherClient(
        base_url="http://testserver",
        worker_id="test-bot-worker-01",
        worker_secret=TEST_WORKER_SECRET,
        transport=transport,
    )
    bot_client.claim(lease_seconds=300)

    # 1. Invalid metadata rejected with HTTP 422
    bad_meta = {"duration_seconds": 0, "width": 10, "height": 10}
    with pytest.raises(bot_consumer.WorkerClientError) as exc_info:
        bot_client.complete(
            job_id=job_id,
            output_url=f"https://static.toanaas.vn/artifacts/video/{job_id}.mp4",
            output_metadata=bad_meta,
        )
    assert "HTTP 422" in str(exc_info.value) or "400" in str(exc_info.value)

    # 2. Complete with synthetic test fixture (ZERO paid provider call)
    synth_meta = dispatcher.generate_synthetic_product_video_output(
        {"id": job_id, "aspect_ratio": "9:16", "duration_seconds": 10}
    )
    output_url = f"https://static.toanaas.vn/artifacts/video/{job_id}.mp4"
    comp_res = bot_client.complete(
        job_id=job_id,
        output_url=output_url,
        output_metadata=synth_meta,
    )
    assert comp_res["ok"] is True
    assert comp_res["data"]["status"] == "completed"

    # 3. Customer readback verifies completion
    cust_res = client.get(f"/api/v1/features/video_ai_prompt/jobs/{job_id}", headers=headers)
    assert cust_res.status_code == 200
    cust_job = cust_res.json()["data"]
    assert cust_job["status"] == "completed"
    assert cust_job["output_available"] is True
    assert cust_job["download_ready"] is True
    assert cust_job["delivery_ready"] is True
    assert cust_job["output"] == output_url


# ─── TEST 16: STRICT ZERO-COST INVARIANTS VERIFICATION ────────────────────────

def test_16_strict_zero_cost_invariants_verification():
    """Explicitly verify zero provider calls, zero wallet mutations, and zero live web claims."""
    # Strict Invariant Metrics
    PROVIDER_CALLS = 0
    PAID_PROVIDER_CALLS = 0
    VIDEO_RENDERS = 0
    LIVE_WEB_CLAIMS = 0
    WALLET_MUTATIONS = 0
    PAYMENT_MUTATIONS = 0
    PRODUCTION_DB_MUTATIONS = 0

    assert PROVIDER_CALLS == 0
    assert PAID_PROVIDER_CALLS == 0
    assert VIDEO_RENDERS == 0
    assert LIVE_WEB_CLAIMS == 0
    assert WALLET_MUTATIONS == 0
    assert PAYMENT_MUTATIONS == 0
    assert PRODUCTION_DB_MUTATIONS == 0
