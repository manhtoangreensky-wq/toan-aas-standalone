"""Tests for V2V Owner Acceptance Job Bridge and Dispatcher Remediation (R16.09G).

Task: P0.PRODUCT_VIDEO_VIDEO_AI_VIDEO_REFERENCE_WEB_V2V_OWNER_ACCEPTANCE_JOB_BRIDGE_SOURCE_REMEDIATION_R16_09G
Scope:
- RED/GREEN coverage for V2V source_video_path formatting in claimed job
- Internal create_owner_acceptance_video_reference_job contract
- Initial blocked state immunity (generic claim, targeted claim, watchdog)
- Atomic release_owner_acceptance_video_reference_job contract
- Targeted claim after release returns exact V2V job with source_video_path
- Customer video_ai_prompt flow preserved and unchanged
- Zero provider calls, zero wallet mutations
"""

from datetime import datetime, timezone
import json
import pytest

import copyfast_db
from copyfast_product_video_dispatcher import (
    _format_claimed_job,
    claim_product_video_job,
    reconcile_stalled_product_video_jobs,
)
from copyfast_product_video_job_bridge import (
    CANONICAL_PRODUCT_KEY,
    compute_payload_hash,
    create_or_replay_product_video_job,
    create_owner_acceptance_video_reference_job,
    release_owner_acceptance_video_reference_job,
)


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    """Provide isolated SQLite session DB with schema initialized."""
    db_file = str(tmp_path / "test_v2v_session.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_file)
    monkeypatch.setenv("PRODUCT_VIDEO_WORKER_SECRET", "test-secret-v2v")
    copyfast_db.ensure_copyfast_schema()
    with copyfast_db.transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES ('acc_owner_v2v', 'owner@test.local', 'hash_owner', 'admin', '2026-10-01T00:00:00Z', '2026-10-01T00:00:00Z'),
                   ('acc_cust_normal', 'customer@test.local', 'hash_cust', 'user', '2026-10-01T00:00:00Z', '2026-10-01T00:00:00Z')
            """
        )
    return db_file


# ─── 1. CUSTOMER video_ai_prompt CONTRACT PRESERVATION ───────────────────────

def test_customer_video_ai_prompt_behavior_unchanged(test_db):
    """Customer flow for video_ai_prompt must continue functioning exactly as before."""
    job = create_or_replay_product_video_job(
        account_id="acc_cust_normal",
        payload={
            "prompt": "Futuristic neon perfume bottle",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 200,
        },
        request_id="req_cust_001",
    )
    assert job["product_key"] == "video_ai_prompt"
    assert job["status"] == "queued"
    assert job["duration_seconds"] == 5
    assert job["quality_tier"] == 200
    assert "source_video_path" not in job["payload"] if "payload" in job else True


def test_customer_cannot_self_create_owner_v2v_acceptance(test_db):
    """Customer endpoint / bridge must not permit creating video_ai_video_reference."""
    # Attempting to supply product_key=video_ai_video_reference is forced to canonical product_key
    job = create_or_replay_product_video_job(
        account_id="acc_cust_normal",
        payload={
            "prompt": "Trying to sneak v2v",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 500,
            "product_key": "video_ai_video_reference",
            "source_video_path": "/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4",
        },
        request_id="req_sneak_001",
    )
    assert job["product_key"] == CANONICAL_PRODUCT_KEY  # "video_ai_prompt"
    assert job["status"] == "queued"  # Normal customer jobs are queued, not blocked acceptance


# ─── 2. INTERNAL OWNER ACCEPTANCE V2V CREATOR CONTRACT ────────────────────────

def test_internal_v2v_creator_succeeds_with_contract_and_initial_blocked(test_db):
    """create_owner_acceptance_video_reference_job must initialize with exact contract and status=blocked."""
    fixture_path = "/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4"
    job = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="Transforming glowing perfume into golden liquid particles",
        source_video_path=fixture_path,
        aspect_ratio="9:16",
        duration_seconds=5,
        quality_tier=500,
        scene_count=1,
        request_id="req_v2v_owner_001",
        idempotency_key="idem_v2v_owner_001",
    )
    assert job["product_key"] == "video_ai_video_reference"
    assert job["routing_product_key"] == "video_ai_video_reference"
    assert job["status"] == "blocked"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_LIVE_ACCEPTANCE"
    assert job["duration_seconds"] == 5
    assert job["quality_tier"] == 500
    assert job["scene_count"] == 1
    assert job["aspect_ratio"] == "9:16"
    assert job["id"].startswith("pvj_")

    # Verify bridge envelope persistence
    env = job["bridge_envelope"]
    assert env["product_key"] == "video_ai_video_reference"
    assert env["routing_product_key"] == "video_ai_video_reference"
    assert env["source_video_path"] == fixture_path
    assert env["acceptance_only"] is True
    assert env["status"] == "blocked"


def test_internal_v2v_creator_hash_binds_source_path(test_db):
    """Payload hash for V2V must bind source_video_path; differing path must produce differing hash."""
    p1 = {
        "product_key": "video_ai_video_reference",
        "prompt": "Same prompt",
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
        "quality_tier": 500,
        "scene_count": 1,
        "source_video_path": "/path/one.mp4",
    }
    p2 = {
        "product_key": "video_ai_video_reference",
        "prompt": "Same prompt",
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
        "quality_tier": 500,
        "scene_count": 1,
        "source_video_path": "/path/two.mp4",
    }
    h1 = compute_payload_hash(p1)
    h2 = compute_payload_hash(p2)
    assert h1 != h2


def test_internal_v2v_creator_malformed_input_fails_closed(test_db):
    """Malformed or missing source_video_path, invalid duration, or tier must fail closed."""
    # Empty source_video_path
    with pytest.raises(ValueError, match="SOURCE_VIDEO_PATH"):
        create_owner_acceptance_video_reference_job(
            account_id="acc_owner_v2v",
            prompt="Valid prompt",
            source_video_path="",
        )

    # Relative source_video_path (not canonical absolute)
    with pytest.raises(ValueError, match="SOURCE_VIDEO_PATH"):
        create_owner_acceptance_video_reference_job(
            account_id="acc_owner_v2v",
            prompt="Valid prompt",
            source_video_path="relative/path/test.mp4",
        )

    # Path traversal sequence
    with pytest.raises(ValueError, match="SOURCE_VIDEO_PATH"):
        create_owner_acceptance_video_reference_job(
            account_id="acc_owner_v2v",
            prompt="Valid prompt",
            source_video_path="/opt/fixtures/../secret.mp4",
        )

    # Invalid duration (must be 5)
    with pytest.raises(ValueError, match="DURATION"):
        create_owner_acceptance_video_reference_job(
            account_id="acc_owner_v2v",
            prompt="Valid prompt",
            source_video_path="/opt/fixture.mp4",
            duration_seconds=10,
        )

    # Invalid quality tier (must be 500)
    with pytest.raises(ValueError, match="TIER"):
        create_owner_acceptance_video_reference_job(
            account_id="acc_owner_v2v",
            prompt="Valid prompt",
            source_video_path="/opt/fixture.mp4",
            quality_tier=200,
        )


# ─── 3. BLOCKED HOLD STATE IMMUNITY ──────────────────────────────────────────

def test_blocked_v2v_job_cannot_be_claimed_by_generic_daemon(test_db):
    """Generic worker claim must return None while job is blocked."""
    job = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="Glowing emerald particles",
        source_video_path="/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4",
    )
    claimed = claim_product_video_job(
        worker_id="worker-generic-daemon",
        lease_seconds=300,
        target_job_id=None,
    )
    assert claimed is None


def test_blocked_v2v_job_cannot_be_claimed_by_targeted_runner(test_db):
    """Targeted runner claim must return None while job is in blocked state."""
    job = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="Glowing emerald particles",
        source_video_path="/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4",
    )
    claimed = claim_product_video_job(
        worker_id="worker-targeted-runner",
        lease_seconds=300,
        target_job_id=job["id"],
    )
    assert claimed is None


def test_watchdog_ignores_blocked_v2v_job(test_db):
    """Watchdog reconciliation must ignore blocked jobs (only touches processing)."""
    job = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="Glowing emerald particles",
        source_video_path="/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4",
    )
    rec = reconcile_stalled_product_video_jobs(lease_grace_seconds=0)
    assert rec["total_reconciled"] == 0

    # Verify status is still blocked in DB
    with copyfast_db.read_transaction() as conn:
        row = conn.execute("SELECT status FROM web_product_video_jobs WHERE id = ?", (job["id"],)).fetchone()
        assert row[0] == "blocked"


# ─── 4. EXACT RELEASE TRANSACTION ────────────────────────────────────────────

def test_exact_release_transitions_only_matching_blocked_v2v_job(test_db):
    """release_owner_acceptance_video_reference_job must release only the exact target job."""
    fixture_path = "/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4"
    job1 = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="Prompt 1",
        source_video_path=fixture_path,
        request_id="req_rel_001",
    )
    job2 = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="Prompt 2",
        source_video_path=fixture_path,
        request_id="req_rel_002",
    )

    # Release only job1
    released = release_owner_acceptance_video_reference_job(job1["id"])
    assert released is not None
    assert released["id"] == job1["id"]
    assert released["status"] == "queued"
    assert released["status_reason"] == "RELEASED_FOR_OWNER_TARGETED_LIVE_ACCEPTANCE"

    # Job2 must remain blocked
    with copyfast_db.read_transaction() as conn:
        r2 = conn.execute("SELECT status FROM web_product_video_jobs WHERE id = ?", (job2["id"],)).fetchone()
        assert r2[0] == "blocked"


def test_release_rejects_wrong_product_wrong_state_or_repeat(test_db):
    """Release must fail/no-op safely on wrong ID, wrong product, or non-blocked state."""
    # 1. Non-existent job
    assert release_owner_acceptance_video_reference_job("pvj_nonexistent") is None

    # 2. Normal customer video_ai_prompt job (wrong product)
    cust_job = create_or_replay_product_video_job(
        account_id="acc_cust_normal",
        payload={
            "prompt": "Normal prompt",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 200,
        },
        request_id="req_cust_rel_001",
    )
    assert release_owner_acceptance_video_reference_job(cust_job["id"]) is None

    # 3. Already released V2V job (repeat release fails safe)
    fixture_path = "/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4"
    v2v_job = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="V2V prompt",
        source_video_path=fixture_path,
        request_id="req_repeat_001",
    )
    first_release = release_owner_acceptance_video_reference_job(v2v_job["id"])
    assert first_release is not None
    assert first_release["status"] == "queued"

    # Repeat release must return None (status is now queued, not blocked)
    second_release = release_owner_acceptance_video_reference_job(v2v_job["id"])
    assert second_release is None


# ─── 5. TARGETED CLAIM AFTER RELEASE & PAYLOAD FORWARDING ─────────────────────

def test_targeted_claim_after_release_returns_v2v_job_with_source_video_path(test_db):
    """After release, targeted claim returns exact job with source_video_path in payload."""
    fixture_path = "/opt/toanaas-worker/acceptance/fixtures/video_ai_video_reference/r16_09_canonical_v1.mp4"
    job = create_owner_acceptance_video_reference_job(
        account_id="acc_owner_v2v",
        prompt="High speed liquid splash transform",
        source_video_path=fixture_path,
        request_id="req_claim_v2v_001",
    )
    # Step A: Release
    released = release_owner_acceptance_video_reference_job(job["id"])
    assert released is not None

    # Step B: Targeted claim
    claimed = claim_product_video_job(
        worker_id="vps-live-acceptance-runner",
        lease_seconds=300,
        target_job_id=job["id"],
    )
    assert claimed is not None
    assert claimed["id"] == job["id"]
    assert claimed["product_key"] == "video_ai_video_reference"
    assert claimed["status"] == "processing"

    # Critical contract check: source_video_path must be present in payload
    payload = claimed["payload"]
    assert "source_video_path" in payload
    assert payload["source_video_path"] == fixture_path
    assert payload["duration_seconds"] == 5
    assert payload["aspect_ratio"] == "9:16"


def test_claimed_job_formatting_fails_closed_on_malformed_envelope(test_db):
    """_format_claimed_job must raise ValueError if V2V envelope has missing source_video_path."""
    row = (
        "pvj_malformed_001",   # 0: id
        "req_malformed_001",   # 1: request_id
        "acc_owner_v2v",       # 2: account_id
        "video_ai_video_reference",  # 3: product_key
        "video_ai_video_reference",  # 4: routing_product_key
        "Some prompt",         # 5: prompt
        "9:16",                # 6: aspect_ratio
        5,                     # 7: duration_seconds
        500,                   # 8: quality_tier
        1,                     # 9: scene_count
        "processing",          # 10: status
        "CLAIMED",             # 11: status_reason
        None,                  # 12: idempotency_key_hash
        "fakehash",            # 13: payload_hash
        json.dumps({"product_key": "video_ai_video_reference"}),  # 14: bridge_envelope missing source_video_path
        None,                  # 15: output_metadata
        "2026-10-01T00:00:00Z",# 16: created_at
        "2026-10-01T00:00:00Z",# 17: updated_at
        "worker-1",            # 18: worker_id
        "2026-10-01T00:00:00Z",# 19: claimed_at
        "2026-10-01T00:05:00Z",# 20: lease_expires_at
        1,                     # 21: attempts
        None,                  # 22: output_url
    )
    with pytest.raises(ValueError, match="MALFORMED_V2V_ENVELOPE"):
        _format_claimed_job(row)


def test_normal_video_ai_prompt_claimed_payload_unchanged(test_db):
    """Normal video_ai_prompt claimed payload must not be polluted with source_video_path."""
    job = create_or_replay_product_video_job(
        account_id="acc_cust_normal",
        payload={
            "prompt": "Perfume commercial bottle",
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "quality_tier": 200,
        },
        request_id="req_prompt_claim_001",
    )
    claimed = claim_product_video_job(
        worker_id="vps-normal-worker",
        lease_seconds=300,
        target_job_id=job["id"],
    )
    assert claimed is not None
    assert claimed["product_key"] == "video_ai_prompt"
    payload = claimed["payload"]
    assert "source_video_path" not in payload
    assert payload["prompt"] == "Perfume commercial bottle"
    assert payload["quality_tier"] == "200"
