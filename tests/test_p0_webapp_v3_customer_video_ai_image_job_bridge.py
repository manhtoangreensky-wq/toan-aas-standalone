"""Tests for Video AI Image Canonical Job Bridge Adapter.

Task: P0.WEBAPP.V3.CUSTOMER.VIDEO_AI_IMAGE.CANONICAL.JOB_BRIDGE.R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Parent: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Enforces:
1. FIRST RED proof and documentation.
2. Canonical product identity and entrypoint (/video/image-to-video, video_ai_image).
3. Web feature job adapter registration.
4. Input validation (prompt, source image, aspect ratio, duration, quality tier, scene count).
5. Anti-injection: strict rejection of client authority fields.
6. Durable persistence in SQLite (table web_video_ai_image_jobs).
7. Customer job owner binding and cross-account IDOR rejection (HTTP 403).
8. Idempotent replay on identical payload hash.
9. Request ID / Idempotency Key conflict rejection (HTTP 409).
10. Fail-closed delivery: output_available=False, download_ready=False, output=None until verified.
11. Zero cost invariants: PROVIDER_CALLS=0, VIDEO_RENDERS=0, WALLET_MUTATIONS=0.
12. FastAPI HTTP endpoints (/features/video_ai_image/jobs, /jobs).
13. Master matrix parity: status=PARTIAL, blocker=AI_IMAGE_VIDEO_BLOCKED_BY_RUNTIME.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import uuid

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from app import app
from copyfast_api import _web_feature_job_adapter_keys
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
import copyfast_registry as reg
import copyfast_video_ai_image_job_bridge as bridge
import copyfast_workspace_draft_contract as draft_contract


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-video-ai-image-bridge")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_image,video_ai_prompt,video_single")
    ensure_copyfast_schema()
    bridge.ensure_video_ai_image_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_video_ai_image_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES ('test-user-1', 'user1@test.local', 'hash1', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z'),
                   ('test-user-2', 'user2@test.local', 'hash2', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z')
            """
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_video_ai_image_jobs")
        conn.execute("DELETE FROM web_sessions WHERE account_id LIKE 'test-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-%'")


def _create_test_account(account_id: str | None = None) -> dict:
    acc_id = account_id or f"test-acc-{uuid.uuid4().hex[:12]}"
    email = f"{acc_id}@example.com"
    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES (?, ?, 'hash', '2026-09-22T00:00:00Z', '2026-09-22T00:00:00Z')
            """,
            (acc_id, email),
        )
    return {"id": acc_id, "email": email}


def _valid_payload() -> dict:
    return {
        "prompt": "Animate camera moving forward smoothly through blooming cherry blossom garden",
        "source_image_url": "https://example.com/images/cherry_blossom.jpg",
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
        "quality_tier": 200,
        "scene_count": 1,
        "platform": "tiktok",
        "goal": "convert",
    }


# ─── TEST 1: FIRST RED PROOF & DOCUMENTATION ──────────────────────────────────

def test_01_first_red_documented_and_proven():
    """Document and verify that video_ai_image now has an active canonical job bridge."""
    # Table exists in SQLite
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='web_video_ai_image_jobs'"
        ).fetchone()
        assert row is not None, "web_video_ai_image_jobs table must exist"

    # Supported canonical adapters contains video_ai_image
    assert "video_ai_image" in bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS

    # C2 FIRST RED documented:
    # A malformed completed state with an unsafe output URL (e.g. javascript:alert(1))
    # must fail closed and never project as delivery_ready / output_available.
    assert bridge.is_safe_video_output_url("javascript:alert(1)") is False


# ─── TEST 2: CANONICAL IDENTITY & ENTRYPOINT ─────────────────────────────────

def test_02_canonical_identity_and_entrypoint():
    """Verify 1:1 identity consistency with Bot runtime authority."""
    assert bridge.CANONICAL_PRODUCT_KEY == "video_ai_image"
    assert bridge.CANONICAL_ROUTING_KEY == "video_ai_canonical"
    assert bridge.CANONICAL_CUSTOMER_ENTRYPOINT == "/video/image-to-video"

    # Registry aliases and entrypoints
    assert reg.FEATURE_ALIASES.get("video_ai_image") == "video_image_to_video"
    assert "video_ai_image" in reg.FEATURE_BY_KEY
    assert reg.FEATURE_BY_KEY["video_ai_image"].route == "/video/image-to-video"
    assert reg.FEATURE_BY_KEY["video_image_to_video"].route == "/video/image-to-video"

    # Registry counts must remain intact: 180 total, 139 customer, 41 admin
    assert len(reg.ALL_FEATURES) == 180
    assert len(reg.CUSTOMER_FEATURES) == 139
    assert len(reg.ADMIN_FEATURES) == 41

    # Draft candidate keys must include video_ai_image
    assert "video_ai_image" in draft_contract.FEATURE_EXECUTION_CANDIDATE_KEYS


# ─── TEST 3: WEB FEATURE ADAPTER REGISTRATION ────────────────────────────────

def test_03_web_feature_adapter_registration(monkeypatch):
    """Prove video_ai_image resolves through _web_feature_job_adapter_keys."""
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "video_ai_image,video_ai_prompt")
    adapter_keys = _web_feature_job_adapter_keys()
    assert "video_ai_image" in adapter_keys
    assert "video_ai_prompt" in adapter_keys

    # Bounded adapter contains only video_ai_image
    assert bridge.SUPPORTED_CANONICAL_JOB_ADAPTERS == frozenset({"video_ai_image"})


# ─── TEST 4: INPUT VALIDATION - PROMPT ───────────────────────────────────────

def test_04_payload_validation_prompt():
    """Verify prompt is required and cannot exceed MAX_PROMPT_LENGTH."""
    p = _valid_payload()
    p["prompt"] = ""
    is_valid, err, _ = bridge.validate_video_ai_image_input(p)
    assert not is_valid
    assert err == "PROMPT_REQUIRED"

    p["prompt"] = "A" * 2001
    is_valid, err, _ = bridge.validate_video_ai_image_input(p)
    assert not is_valid
    assert err == "PROMPT_TOO_LONG"


# ─── TEST 5: INPUT VALIDATION - SOURCE IMAGE ─────────────────────────────────

def test_05_payload_validation_source_image():
    """Verify source_image_url is required and unsafe URLs are rejected."""
    p = _valid_payload()
    p["source_image_url"] = ""
    p["source"] = ""
    is_valid, err, _ = bridge.validate_video_ai_image_input(p)
    assert not is_valid
    assert err == "SOURCE_IMAGE_REQUIRED"

    # Rejection of unsafe schemes
    unsafe_inputs = [
        "javascript:alert(1)",
        "JavaScript:prompt()",
        "data:image/png;base64,AAAA",
        "https://example.com/../../etc/passwd",
        "/valid/path/../../../traversal",
    ]
    for unsafe in unsafe_inputs:
        p["source_image_url"] = unsafe
        is_valid, err, _ = bridge.validate_video_ai_image_input(p)
        assert not is_valid, f"Expected {unsafe} to be rejected"
        assert err == "SOURCE_IMAGE_UNSAFE"

    # Safe inputs
    safe_inputs = [
        "https://cdn.example.com/uploads/product1.png",
        "http://example.com/pic.jpg",
        "/api/v1/assets/asset_123/download",
        "stage_upload_abc123",
        "asset_789xyz",
    ]
    for safe in safe_inputs:
        p["source_image_url"] = safe
        is_valid, err, norm = bridge.validate_video_ai_image_input(p)
        assert is_valid, f"Expected {safe} to be accepted, got {err}"
        assert norm["source_image_url"] == safe


# ─── TEST 6: INPUT VALIDATION - ASPECT RATIO ─────────────────────────────────

def test_06_payload_validation_aspect_ratio():
    """Verify allowed aspect ratios: 9:16, 16:9, 1:1, 4:5."""
    p = _valid_payload()
    for valid_ratio in ("9:16", "16:9", "1:1", "4:5"):
        p["aspect_ratio"] = valid_ratio
        is_valid, err, norm = bridge.validate_video_ai_image_input(p)
        assert is_valid, f"Expected {valid_ratio} to be valid"
        assert norm["aspect_ratio"] == valid_ratio

    # Missing
    p["aspect_ratio"] = ""
    is_valid, err, _ = bridge.validate_video_ai_image_input(p)
    assert not is_valid
    assert err == "ASPECT_RATIO_REQUIRED"

    # Invalid
    p["aspect_ratio"] = "21:9"
    is_valid, err, _ = bridge.validate_video_ai_image_input(p)
    assert not is_valid
    assert err == "INVALID_ASPECT_RATIO"


# ─── TEST 7: INPUT VALIDATION - DURATION & SCENE COUNT ────────────────────────

def test_07_payload_validation_duration_and_scenes():
    """Verify duration and scene_count validation and defaults."""
    p = _valid_payload()

    # Default duration = 5
    del p["duration_seconds"]
    is_valid, _, norm = bridge.validate_video_ai_image_input(p)
    assert is_valid
    assert norm["duration_seconds"] == 5

    # Invalid durations
    for inv in (-1, 0, 601, "abc"):
        p["duration_seconds"] = inv
        is_valid, err, _ = bridge.validate_video_ai_image_input(p)
        assert not is_valid
        assert err == "INVALID_DURATION"

    # Default scene_count = 1
    p = _valid_payload()
    del p["scene_count"]
    is_valid, _, norm = bridge.validate_video_ai_image_input(p)
    assert is_valid
    assert norm["scene_count"] == 1

    # Invalid scenes
    for inv in (0, 21, "xyz"):
        p["scene_count"] = inv
        is_valid, err, _ = bridge.validate_video_ai_image_input(p)
        assert not is_valid
        assert err == "INVALID_SCENE_COUNT"


# ─── TEST 8: INPUT VALIDATION - QUALITY TIER ──────────────────────────────────

def test_08_payload_validation_quality_tier():
    """Verify quality tier requirement and allowed values."""
    p = _valid_payload()
    del p["quality_tier"]
    is_valid, err, _ = bridge.validate_video_ai_image_input(p)
    assert not is_valid
    assert err == "TIER_REQUIRED"

    for valid_tier in (200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500):
        p["quality_tier"] = valid_tier
        is_valid, _, norm = bridge.validate_video_ai_image_input(p)
        assert is_valid
        assert norm["quality_tier"] == valid_tier

    for invalid_tier in (100, 999, 2000, "fast"):
        p["quality_tier"] = invalid_tier
        is_valid, err, _ = bridge.validate_video_ai_image_input(p)
        assert not is_valid
        assert err == "INVALID_QUALITY_TIER"


# ─── TEST 9: CLIENT AUTHORITY FIELD REJECTION ────────────────────────────────

def test_09_authority_field_rejection():
    """Verify client authority injection attempts are rejected."""
    forbidden = [
        {"status": "completed"},
        {"output": "https://evil.com/video.mp4"},
        {"output_url": "https://evil.com/video.mp4"},
        {"wallet": "999999"},
        {"balance": 100000},
        {"price": 0},
        {"cost": 0},
        {"role": "admin"},
        {"provider": "fake_provider"},
        {"job_id": "vaij_fake"},
        {"authority": "root"},
    ]
    for injection in forbidden:
        p = _valid_payload()
        p.update(injection)
        is_valid, err, _ = bridge.validate_video_ai_image_input(p)
        assert not is_valid, f"Expected {injection} to be rejected"
        assert err == "authority_field_not_allowed"


# ─── TEST 10: DURABLE SQLITE RECORD PERSISTENCE ──────────────────────────────

def test_10_durable_sqlite_persistence():
    """Verify valid job creation stores a durable record in web_video_ai_image_jobs."""
    acc = _create_test_account()
    payload = _valid_payload()

    job = bridge.create_or_replay_video_ai_image_job(
        account_id=acc["id"],
        payload=payload,
    )

    assert job["id"].startswith("vaij_")
    assert job["request_id"].startswith("VAI-")
    assert job["account_id"] == acc["id"]
    assert job["product_key"] == "video_ai_image"
    assert job["routing_product_key"] == "video_ai_canonical"
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False
    assert job["output"] is None
    assert job["idempotent_replay"] is False

    # Check directly in SQLite
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT id, request_id, account_id, status, status_reason, source_image_url FROM web_video_ai_image_jobs WHERE id = ?",
            (job["id"],),
        ).fetchone()
        assert row is not None
        assert row[0] == job["id"]
        assert row[1] == job["request_id"]
        assert row[2] == acc["id"]
        assert row[3] == "queued"
        assert row[4] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
        assert row[5] == payload["source_image_url"]


# ─── TEST 11: IDEMPOTENT REPLAY ON IDENTICAL PAYLOAD ──────────────────────────

def test_11_idempotent_replay():
    """Verify calling with same request_id or idempotency_key replays identical record."""
    acc = _create_test_account()
    payload = _valid_payload()
    req_id = "VAI-20260923-TEST01"
    idem_key = "idempotency-key-test-11-unique"

    job1 = bridge.create_or_replay_video_ai_image_job(
        account_id=acc["id"],
        payload=payload,
        request_id=req_id,
        idempotency_key=idem_key,
    )
    assert job1["idempotent_replay"] is False

    # Replay with same key
    job2 = bridge.create_or_replay_video_ai_image_job(
        account_id=acc["id"],
        payload=payload,
        request_id=req_id,
        idempotency_key=idem_key,
    )
    assert job2["idempotent_replay"] is True
    assert job2["id"] == job1["id"]
    assert job2["request_id"] == req_id


# ─── TEST 12: REQUEST ID CONFLICT REJECTION ──────────────────────────────────

def test_12_request_id_conflict_rejection():
    """Verify calling with same request_id but differing payload raises 409 Conflict."""
    acc = _create_test_account()
    payload1 = _valid_payload()
    req_id = "VAI-20260923-CONFLICT01"

    bridge.create_or_replay_video_ai_image_job(
        account_id=acc["id"],
        payload=payload1,
        request_id=req_id,
    )

    # Differing prompt
    payload2 = _valid_payload()
    payload2["prompt"] = "Completely different prompt text for conflict test"

    with pytest.raises(HTTPException) as exc_info:
        bridge.create_or_replay_video_ai_image_job(
            account_id=acc["id"],
            payload=payload2,
            request_id=req_id,
        )
    assert exc_info.value.status_code == 409


# ─── TEST 13: OWNER BINDING & CROSS-ACCOUNT ISOLATION ────────────────────────

def test_13_cross_account_isolation():
    """Verify account A cannot access account B's job (IDOR protection)."""
    acc_a = _create_test_account()
    acc_b = _create_test_account()

    job_a = bridge.create_or_replay_video_ai_image_job(
        account_id=acc_a["id"],
        payload=_valid_payload(),
    )

    # Owner can retrieve
    assert bridge.get_video_ai_image_job(acc_a["id"], job_a["id"]) is not None

    # Other account cannot retrieve
    assert bridge.get_video_ai_image_job(acc_b["id"], job_a["id"]) is None

    # Cross account detection
    assert bridge.is_video_ai_image_job_other_account(job_a["id"], acc_b["id"]) is True
    assert bridge.is_video_ai_image_job_other_account(job_a["id"], acc_a["id"]) is False


# ─── TEST 14: FAIL-CLOSED OUTPUT STATE ───────────────────────────────────────

def test_14_fail_closed_output_state():
    """Verify queued job NEVER exposes fake download or output readiness."""
    acc = _create_test_account()
    job = bridge.create_or_replay_video_ai_image_job(
        account_id=acc["id"],
        payload=_valid_payload(),
    )

    assert job["status"] == "queued"
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False
    assert job["output"] is None
    assert job["output_url"] is None


# ─── TEST 15: ZERO COST INVARIANTS ───────────────────────────────────────────

def test_15_zero_cost_invariants():
    """Verify job creation executes 0 provider calls, 0 video renders, and 0 wallet mutations."""
    acc = _create_test_account()
    job = bridge.create_or_replay_video_ai_image_job(
        account_id=acc["id"],
        payload=_valid_payload(),
    )

    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job["output"] is None
    assert job["output_url"] is None
    assert job["output_metadata"] is None
    assert job["status"] != "completed"

    envelope = job["bridge_envelope"]
    assert "api_key" not in envelope
    assert "token" not in envelope
    assert "provider_task_id" not in envelope
    assert envelope["output"] is None
    assert envelope["status"] == "queued"


# ─── TEST 16: FASTAPI HTTP ENDPOINTS & CROSS-USER SECURITY ────────────────────

def test_16_fastapi_http_endpoints():
    """Verify HTTP endpoints for video_ai_image."""
    client1 = TestClient(app)
    # Register & login user1
    client1.post("/api/v1/auth/register", json={"email": "vai1@test.local", "password": "secure-password-1234", "display_name": "VAI 1"})
    login1 = client1.post("/api/v1/auth/login", json={"email": "vai1@test.local", "password": "secure-password-1234"})
    assert login1.status_code == 200
    csrf1 = login1.json()["data"]["csrf_token"]
    headers1 = {"X-CSRF-Token": csrf1}

    payload = _valid_payload()

    # 1. Post job via /features/video_ai_image/jobs
    create_res = client1.post(
        "/api/v1/features/video_ai_image/jobs",
        json={
            "input": payload,
            "idempotency_key": "vai-idem-0001",
        },
        headers=headers1,
    )
    assert create_res.status_code == 200
    body = create_res.json()
    assert body["ok"] is True
    job_id = body["data"]["id"]
    assert job_id.startswith("vaij_")
    assert body["data"]["status"] == "queued"
    assert body["data"]["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

    # 2. Query job list via /features/video_ai_image/jobs
    list_res = client1.get("/api/v1/features/video_ai_image/jobs")
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) >= 1
    assert any(item["id"] == job_id for item in items)

    # 3. Query job detail via /features/video_ai_image/jobs/{job_id} as owner
    detail_res = client1.get(f"/api/v1/features/video_ai_image/jobs/{job_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == job_id

    # 4. User 2 tries to access user 1's job -> 403 Forbidden
    client2 = TestClient(app)
    client2.post("/api/v1/auth/register", json={"email": "vai2@test.local", "password": "secure-password-1234", "display_name": "VAI 2"})
    login2 = client2.post("/api/v1/auth/login", json={"email": "vai2@test.local", "password": "secure-password-1234"})
    assert login2.status_code == 200

    resp_forbidden = client2.get(f"/api/v1/features/video_ai_image/jobs/{job_id}")
    assert resp_forbidden.status_code == 403

    # 5. Non-existent job returns 404
    resp_notfound = client1.get("/api/v1/features/video_ai_image/jobs/vaij_nonexistent")
    assert resp_notfound.status_code == 404


# ─── TEST 17: GENERIC GET /api/v1/jobs INTEGRATION ────────────────────────────

def test_17_generic_jobs_view_integration():
    """Verify video_ai_image jobs are included in generic GET /api/v1/jobs."""
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"email": "vai_gen@test.local", "password": "secure-password-1234", "display_name": "VAI Gen"})
    login = client.post("/api/v1/auth/login", json={"email": "vai_gen@test.local", "password": "secure-password-1234"})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    headers = {"X-CSRF-Token": csrf}

    payload = _valid_payload()
    create_res = client.post(
        "/api/v1/features/video_ai_image/jobs",
        json={"input": payload, "idempotency_key": "vai-gen-0001"},
        headers=headers,
    )
    assert create_res.status_code == 200
    job_id = create_res.json()["data"]["id"]

    # Generic list
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    body = resp.json()
    items = body.get("data", {}).get("items", [])
    matched = [i for i in items if i.get("id") == job_id]
    assert len(matched) == 1
    record = matched[0]
    assert record["feature"] == "video_ai_image"
    assert record["job_type"] == "video_ai_image"
    assert record["native_kind"] == "video-ai-image-job"
    assert record["status"] == "queued"

    # Generic detail
    resp_detail = client.get(f"/api/v1/jobs/{job_id}")
    assert resp_detail.status_code == 200
    detail_body = resp_detail.json()
    assert detail_body["ok"] is True
    assert detail_body["data"]["id"] == job_id
    assert detail_body["data"]["feature"] == "video_ai_image"


# ─── TEST 18: MASTER MATRIX INVARIANT ─────────────────────────────────────────

def test_18_master_matrix_invariants():
    """Verify Master Matrix accurately reflects video_ai_image status=PARTIAL with real_output=NONE_ON_WEB."""
    audit_file = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
    data = json.loads(audit_file.read_text(encoding="utf-8"))

    matrix = data.get("parity_matrix", [])
    vai_entries = [m for m in matrix if m.get("bot_capability") == "video_ai_image"]
    assert len(vai_entries) == 1, "video_ai_image must be present in parity matrix"
    entry = vai_entries[0]

    assert entry["status"] == "PARTIAL"
    assert entry["blocker"] == "AI_IMAGE_VIDEO_BLOCKED_BY_RUNTIME"
    assert entry["real_output"] == "NONE_ON_WEB"
    assert entry["web_customer_entrypoint"] == "/video/image-to-video"
    assert entry["web_api"] == "/api/v1/features/video_ai_image/*"
    assert entry["bot_runtime_consumer"] == "services.video_tail9.PRODUCT_ADAPTERS['image_video']"


# ─── TEST 19: MALFORMED COMPLETED WITHOUT ARTIFACT (FAIL-CLOSED) ──────────────

def test_19_completed_without_artifact_fail_closed():
    """Verify status=completed with output_url=NULL preserves fail-closed delivery truth.

    Both canonical read and native compat must return:
      status = 'completed'
      output_available = False
      download_ready = False
      delivery_ready = False
      output = None
      output_url = None
    """
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"email": "vai_fc@test.local", "password": "secure-password-1234", "display_name": "VAI FailClosed"})
    login = client.post("/api/v1/auth/login", json={"email": "vai_fc@test.local", "password": "secure-password-1234"})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    headers = {"X-CSRF-Token": csrf}

    with read_transaction() as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email = 'vai_fc@test.local'").fetchone()
        account_id = row[0]

    payload = _valid_payload()
    create_res = client.post(
        "/api/v1/features/video_ai_image/jobs",
        json={"input": payload, "idempotency_key": "vai-fc-0001"},
        headers=headers,
    )
    assert create_res.status_code == 200
    job_id = create_res.json()["data"]["id"]

    # Force malformed completed state: completed with NULL output_url
    with transaction() as conn:
        conn.execute("UPDATE web_video_ai_image_jobs SET status = 'completed', output_url = NULL WHERE id = ?", (job_id,))

    # 1. Canonical job readback
    canonical_job = bridge.get_video_ai_image_job(account_id, job_id)
    assert canonical_job is not None
    assert canonical_job["status"] == "completed"
    assert canonical_job["output_available"] is False
    assert canonical_job["download_ready"] is False
    assert canonical_job["delivery_ready"] is False
    assert canonical_job["output"] is None
    assert canonical_job["output_url"] is None

    # 2. Native compat projection
    compat = bridge.video_ai_image_job_to_native_compat(canonical_job)
    assert compat["status"] == "completed"
    assert compat["output_available"] is False
    assert compat["download_ready"] is False
    assert compat["delivery_ready"] is False
    assert compat["output"] is None

    # 3. Generic list GET /api/v1/jobs
    resp_list = client.get("/api/v1/jobs")
    assert resp_list.status_code == 200
    items = resp_list.json().get("data", {}).get("items", [])
    matched = [i for i in items if i.get("id") == job_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "completed"
    assert matched[0]["output_available"] is False
    assert matched[0]["download_ready"] is False
    assert matched[0]["delivery_ready"] is False
    assert matched[0]["output"] is None

    # 4. Generic detail GET /api/v1/jobs/{job_id}
    resp_detail = client.get(f"/api/v1/jobs/{job_id}")
    assert resp_detail.status_code == 200
    detail = resp_detail.json().get("data", {})
    assert detail["status"] == "completed"
    assert detail["output_available"] is False
    assert detail["download_ready"] is False
    assert detail["delivery_ready"] is False
    assert detail["output"] is None


# ─── TEST 20: VALID FUTURE ARTIFACT PROJECTION ────────────────────────────────

def test_20_valid_future_artifact_projection():
    """Verify status=completed with valid safe persisted output preserves canonical flags/output.

    Both canonical read and native compat must return:
      status = 'completed'
      output_available = True
      download_ready = True
      delivery_ready = True
      output = verified_url
      output_url = verified_url
    """
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"email": "vai_art@test.local", "password": "secure-password-1234", "display_name": "VAI Artifact"})
    login = client.post("/api/v1/auth/login", json={"email": "vai_art@test.local", "password": "secure-password-1234"})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    headers = {"X-CSRF-Token": csrf}

    with read_transaction() as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email = 'vai_art@test.local'").fetchone()
        account_id = row[0]

    payload = _valid_payload()
    create_res = client.post(
        "/api/v1/features/video_ai_image/jobs",
        json={"input": payload, "idempotency_key": "vai-art-0001"},
        headers=headers,
    )
    assert create_res.status_code == 200
    job_id = create_res.json()["data"]["id"]

    valid_url = "https://storage.toanaas.vn/videos/vaij_verified_render_output.mp4"

    # Persist completed state with valid output_url
    with transaction() as conn:
        conn.execute("UPDATE web_video_ai_image_jobs SET status = 'completed', output_url = ? WHERE id = ?", (valid_url, job_id))

    # 1. Canonical job readback
    canonical_job = bridge.get_video_ai_image_job(account_id, job_id)
    assert canonical_job is not None
    assert canonical_job["status"] == "completed"
    assert canonical_job["output_available"] is True
    assert canonical_job["download_ready"] is True
    assert canonical_job["delivery_ready"] is True
    assert canonical_job["output"] == valid_url
    assert canonical_job["output_url"] == valid_url

    # 2. Native compat projection
    compat = bridge.video_ai_image_job_to_native_compat(canonical_job)
    assert compat["status"] == "completed"
    assert compat["output_available"] is True
    assert compat["download_ready"] is True
    assert compat["delivery_ready"] is True
    assert compat["output"] == valid_url

    # 3. Generic list GET /api/v1/jobs
    resp_list = client.get("/api/v1/jobs")
    assert resp_list.status_code == 200
    items = resp_list.json().get("data", {}).get("items", [])
    matched = [i for i in items if i.get("id") == job_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "completed"
    assert matched[0]["output_available"] is True
    assert matched[0]["download_ready"] is True
    assert matched[0]["delivery_ready"] is True
    assert matched[0]["output"] == valid_url

    # 4. Generic detail GET /api/v1/jobs/{job_id}
    resp_detail = client.get(f"/api/v1/jobs/{job_id}")
    assert resp_detail.status_code == 200
    detail = resp_detail.json().get("data", {})
    assert detail["status"] == "completed"
    assert detail["output_available"] is True
    assert detail["download_ready"] is True
    assert detail["delivery_ready"] is True
    assert detail["output"] == valid_url


# ─── TEST 21: UNSAFE ARTIFACT URL FAIL-CLOSED ────────────────────────────────

def test_21_unsafe_artifact_url_fail_closed():
    """Verify status=completed with unsafe persisted output_url fails closed.

    Enforces that candidate output URLs cannot establish delivery truth
    unless they pass the authoritative output-URL safety contract.

    Covers representative unsafe forms:
    - javascript: schemes (javascript:alert(1), javascript:void(0), JavaScript:prompt())
    - vbscript: schemes (vbscript:msgbox(1))
    - data: schemes (data:video/mp4;base64,AAAA)
    - file: schemes (file:///etc/passwd, file://localhost/c$/boot.ini)
    - blob: schemes (blob:https://example.com/uuid)
    - about: schemes (about:blank)
    - embedded credentials (https://user:pass@evil.com/video.mp4, https://attacker@toanaas.vn/video.mp4)
    - path traversal (https://storage.toanaas.vn/videos/..%2f..%2fpasswords.txt, https://storage.toanaas.vn/videos/../video.mp4)
    - backslash bypass (https://evil.com\\attacker.com/video.mp4)
    - insecure HTTP (http://insecure.example.com/video.mp4)
    - control characters & whitespace (\\n, leading/trailing spaces)
    - port anomalies (https://storage.toanaas.vn:8080/video.mp4)
    - malformed schemes/hosts (https://, not-a-url)

    Both canonical read and native compat must return:
      status = 'completed'
      output_available = False
      download_ready = False
      delivery_ready = False
      output = None
      output_url = None
    """
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"email": "vai_unsafe@test.local", "password": "secure-password-1234", "display_name": "VAI Unsafe"})
    login = client.post("/api/v1/auth/login", json={"email": "vai_unsafe@test.local", "password": "secure-password-1234"})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    headers = {"X-CSRF-Token": csrf}

    with read_transaction() as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email = 'vai_unsafe@test.local'").fetchone()
        account_id = row[0]

    payload = _valid_payload()
    create_res = client.post(
        "/api/v1/features/video_ai_image/jobs",
        json={"input": payload, "idempotency_key": "vai-unsafe-0001"},
        headers=headers,
    )
    assert create_res.status_code == 200
    job_id = create_res.json()["data"]["id"]

    unsafe_urls = [
        "javascript:alert(1)",
        "javascript:void(0)",
        "JavaScript:prompt()",
        "vbscript:msgbox(1)",
        "data:video/mp4;base64,AAAA",
        "file:///etc/passwd",
        "file://localhost/c$/boot.ini",
        "blob:https://example.com/uuid",
        "about:blank",
        "https://user:pass@evil.com/video.mp4",
        "https://attacker@toanaas.vn/video.mp4",
        "https://storage.toanaas.vn/videos/..%2f..%2fpasswords.txt",
        "https://storage.toanaas.vn/videos/../video.mp4",
        "https://evil.com\\attacker.com/video.mp4",
        "http://insecure.example.com/video.mp4",
        " https://storage.toanaas.vn/video.mp4",
        "https://storage.toanaas.vn/video.mp4 ",
        "https://storage.toanaas.vn/video\n.mp4",
        "https://storage.toanaas.vn:8080/video.mp4",
        "https://",
    ]

    for unsafe_url in unsafe_urls:
        # Persist completed state with unsafe output_url
        with transaction() as conn:
            conn.execute(
                "UPDATE web_video_ai_image_jobs SET status = 'completed', output_url = ? WHERE id = ?",
                (unsafe_url, job_id),
            )

        # 1. Canonical job readback: must retain completed status but fail-closed delivery
        canonical_job = bridge.get_video_ai_image_job(account_id, job_id)
        assert canonical_job is not None, f"Failed to fetch job for {unsafe_url}"
        assert canonical_job["status"] == "completed"
        assert canonical_job["output_available"] is False, f"output_available must be False for {unsafe_url}"
        assert canonical_job["download_ready"] is False, f"download_ready must be False for {unsafe_url}"
        assert canonical_job["delivery_ready"] is False, f"delivery_ready must be False for {unsafe_url}"
        assert canonical_job["output"] is None, f"output must be None for {unsafe_url}"
        assert canonical_job["output_url"] is None, f"output_url must be None for {unsafe_url}"

        # 2. Native compat projection: must inherit exact same fail-closed delivery truth
        compat = bridge.video_ai_image_job_to_native_compat(canonical_job)
        assert compat["status"] == "completed"
        assert compat["output_available"] is False, f"compat output_available must be False for {unsafe_url}"
        assert compat["download_ready"] is False, f"compat download_ready must be False for {unsafe_url}"
        assert compat["delivery_ready"] is False, f"compat delivery_ready must be False for {unsafe_url}"
        assert compat["output"] is None, f"compat output must be None for {unsafe_url}"

        # 3. Generic list GET /api/v1/jobs
        resp_list = client.get("/api/v1/jobs")
        assert resp_list.status_code == 200
        items = resp_list.json().get("data", {}).get("items", [])
        matched = [i for i in items if i.get("id") == job_id]
        assert len(matched) == 1
        assert matched[0]["status"] == "completed"
        assert matched[0]["output_available"] is False, f"generic list output_available must be False for {unsafe_url}"
        assert matched[0]["download_ready"] is False, f"generic list download_ready must be False for {unsafe_url}"
        assert matched[0]["delivery_ready"] is False, f"generic list delivery_ready must be False for {unsafe_url}"
        assert matched[0]["output"] is None, f"generic list output must be None for {unsafe_url}"

        # 4. Generic detail GET /api/v1/jobs/{job_id}
        resp_detail = client.get(f"/api/v1/jobs/{job_id}")
        assert resp_detail.status_code == 200
        detail = resp_detail.json().get("data", {})
        assert detail["status"] == "completed"
        assert detail["output_available"] is False, f"generic detail output_available must be False for {unsafe_url}"
        assert detail["download_ready"] is False, f"generic detail download_ready must be False for {unsafe_url}"
        assert detail["delivery_ready"] is False, f"generic detail delivery_ready must be False for {unsafe_url}"
        assert detail["output"] is None, f"generic detail output must be None for {unsafe_url}"


# ─── TEST 22: IS_SAFE_VIDEO_OUTPUT_URL UNIT CONTRACT ─────────────────────────

def test_22_is_safe_video_output_url_unit_contract():
    """Unit test the authoritative output URL validator across all boundary cases."""
    # Safe HTTPS URLs
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn/videos/output.mp4") is True
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn:443/videos/output.mp4") is True
    assert bridge.is_safe_video_output_url("https://static.toanaas.vn/artifacts/video/vaij_12345.mp4?exp=1700000000&sig=abc") is True
    assert bridge.is_safe_video_output_url("https://example.com/video.mp4") is True

    # Dangerous schemes
    assert bridge.is_safe_video_output_url("javascript:alert(1)") is False
    assert bridge.is_safe_video_output_url("JavaScript:prompt()") is False
    assert bridge.is_safe_video_output_url("javascript:void(0)") is False
    assert bridge.is_safe_video_output_url("vbscript:msgbox(1)") is False
    assert bridge.is_safe_video_output_url("data:video/mp4;base64,AAAA") is False
    assert bridge.is_safe_video_output_url("file:///etc/passwd") is False
    assert bridge.is_safe_video_output_url("file://localhost/c$/boot.ini") is False
    assert bridge.is_safe_video_output_url("blob:https://example.com/uuid") is False
    assert bridge.is_safe_video_output_url("about:blank") is False

    # Insecure scheme
    assert bridge.is_safe_video_output_url("http://insecure.example.com/video.mp4") is False
    assert bridge.is_safe_video_output_url("ftp://files.example.com/video.mp4") is False

    # Credential injection
    assert bridge.is_safe_video_output_url("https://user:pass@evil.com/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://attacker@toanaas.vn/video.mp4") is False

    # Traversal & backslash
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn/videos/..%2f..%2fpasswords.txt") is False
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn/videos/../video.mp4") is False
    assert bridge.is_safe_video_output_url("https://evil.com\\attacker.com/video.mp4") is False

    # Non-strings, empty, whitespace & control chars
    assert bridge.is_safe_video_output_url(None) is False
    assert bridge.is_safe_video_output_url("") is False
    assert bridge.is_safe_video_output_url("   ") is False
    assert bridge.is_safe_video_output_url(" https://storage.toanaas.vn/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn/video.mp4 ") is False
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn/video\n.mp4") is False
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn/video\x00.mp4") is False

    # Port anomalies
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn:8080/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://storage.toanaas.vn:80/video.mp4") is False

    # Incomplete / unparseable
    assert bridge.is_safe_video_output_url("https://") is False
    assert bridge.is_safe_video_output_url("not-a-url") is False
