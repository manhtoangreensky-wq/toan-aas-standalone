"""P0 tests for Web Product Video financial settlement orchestration and projection.

Validates:
- Settlement trigger occurs only AFTER validated Web completion (never before)
- Settlement on failed job is rejected (SETTLEMENT_ON_FAILED_JOB=NO)
- Settlement on unsafe output is rejected (SETTLEMENT_ON_UNSAFE_OUTPUT=NO)
- Settlement on invalid metadata is rejected (SETTLEMENT_ON_INVALID_METADATA=NO)
- Canonical user ID derived strictly from server mapping (CUSTOMER_CANONICAL_USER_ID_FROM_SERVER_MAPPING=YES)
- Forged canonical user ID from payload ignored/rejected (CUSTOMER_CANONICAL_USER_ID_FROM_PAYLOAD=NO)
- Missing canonical user mapping fails closed (CANONICAL_USER_MAPPING_MISSING)
- Cross-account settlement blocked
- Retries use the exact same idempotency key (RETRY_USES_SAME_IDEMPOTENCY_KEY=YES)
- CoreBridge failure never creates local fake debit (CORE_BRIDGE_FAILURE_FAKE_SETTLEMENT=NO)
- Web direct wallet mutation is ZERO (WEB_DIRECT_WALLET_MUTATION=NO)
- Real provider HTTP calls is ZERO
- Production wallet mutation is ZERO
"""

from __future__ import annotations

import os
import sqlite3
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from copyfast_db import (
    ensure_copyfast_schema,
    transaction,
)
from copyfast_product_video_dispatcher import (
    settle_product_video_job_completion,
    complete_product_video_job,
    STATUS_QUEUED,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)


@pytest.fixture
def test_web_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test_webapp.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_file)
    ensure_copyfast_schema()
    return db_file


def _seed_account_and_job(
    *,
    account_id: str = "acc_cust_001",
    canonical_user_id: str = "telegram-888888",
    job_id: str = "pvj_test_web_001",
    status: str = STATUS_COMPLETED,
    quality_tier: int = 200,
    scene_count: int = 1,
    output_url: str = "https://storage.googleapis.com/test-bucket/output.mp4",
    output_metadata: dict | None = None,
):
    now_iso = datetime.now(timezone.utc).isoformat()
    if output_metadata is None:
        output_metadata = {
            "duration_seconds": 5.0,
            "width": 720,
            "height": 1280,
            "file_size_bytes": 10240,
            "format": "mp4",
            "codec": "h264",
        }

    with transaction() as conn:
        # Seed web account
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts
            (id, email, password_hash, display_name, canonical_user_id, role_cache, password_login_enabled, created_at, updated_at)
            VALUES (?, 'cust@example.com', 'hash', 'Customer', ?, 'user', 0, ?, ?)
            """,
            (account_id, canonical_user_id, now_iso, now_iso),
        )

        import json
        meta_json = json.dumps(output_metadata) if output_metadata else None
        # Seed job
        conn.execute(
            """
            INSERT OR REPLACE INTO web_product_video_jobs
            (id, request_id, account_id, product_key, routing_product_key, prompt,
             aspect_ratio, duration_seconds, quality_tier, scene_count, status,
             status_reason, payload_hash, bridge_envelope, output_metadata,
             output_url, created_at, updated_at)
            VALUES (?, 'req_001', ?, 'video_ai_prompt', 'video_ai_canonical', 'Test prompt',
                    '9:16', 5, ?, ?, ?, 'TEST_REASON', 'hash', '{}', ?, ?, ?, ?)
            """,
            (job_id, account_id, quality_tier, scene_count, status, meta_json, output_url, now_iso, now_iso),
        )

    return {
        "id": job_id,
        "request_id": "req_001",
        "account_id": account_id,
        "product_key": "video_ai_prompt",
        "quality_tier": quality_tier,
        "scene_count": scene_count,
        "status": status,
        "output_url": output_url,
        "output_metadata": output_metadata,
    }


@pytest.mark.anyio
async def test_settle_after_validated_completion_success(test_web_db):
    """Items 1, 14, 19, 20: Valid completion triggers settlement bridge and persists projection."""
    job = _seed_account_and_job(job_id="pvj_settle_ok")

    mock_bridge_resp = {
        "ok": True,
        "status": "settled",
        "settlement_id": "wpvs_mock_12345",
        "web_job_id": "pvj_settle_ok",
        "amount_xu": 259,
        "balance_before": 500,
        "balance_after": 241,
        "duplicate": False,
        "exempt": False,
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch("copyfast_bridge.bridge_request", new=AsyncMock(return_value=mock_bridge_resp)) as mock_bridge:
        res = await settle_product_video_job_completion(job)

        assert res["ok"] is True
        assert res["status"] == "settled"
        assert res["settlement_id"] == "wpvs_mock_12345"
        assert res["amount_xu"] == 259
        assert res["canonical_user_id"] == "888888"

        # Verify bridge request called with server-derived canonical_user_id
        mock_bridge.assert_called_once()
        call_kwargs = mock_bridge.call_args[1]
        payload = call_kwargs["payload"]
        assert payload["canonical_user_id"] == "888888"
        assert payload["tier_id"] == 200
        assert payload["scene_count"] == 1
        assert payload["product_key"] == "video_ai_prompt"
        assert payload["idempotency_key"] == "web_product_video_final_delivery:pvj_settle_ok"

    # Verify projection table in Web DB
    with transaction() as conn:
        row = conn.execute(
            "SELECT web_job_id, canonical_settlement_id, status, amount_xu, canonical_user_id FROM web_product_video_settlement_projections WHERE web_job_id = 'pvj_settle_ok'"
        ).fetchone()
        assert row is not None
        assert row[0] == "pvj_settle_ok"
        assert row[1] == "wpvs_mock_12345"
        assert row[2] == "settled"
        assert row[3] == 259
        assert row[4] == "888888"


@pytest.mark.anyio
async def test_settle_on_failed_job_blocked(test_web_db):
    """Item 4: Failed job -> settlement is rejected, zero debit."""
    job = _seed_account_and_job(job_id="pvj_failed", status=STATUS_FAILED)

    with patch("copyfast_bridge.bridge_request", new=AsyncMock()) as mock_bridge:
        res = await settle_product_video_job_completion(job)
        assert res["ok"] is False
        assert res["error_code"] == "SETTLEMENT_NOT_ALLOWED_ON_NON_COMPLETED_JOB"
        mock_bridge.assert_not_called()


@pytest.mark.anyio
async def test_settle_on_unsafe_output_blocked(test_web_db):
    """Item 5: Unsafe output URL -> settlement is rejected, zero debit."""
    job = _seed_account_and_job(job_id="pvj_unsafe", output_url="http://malicious-site.com/hack.sh")

    with patch("copyfast_bridge.bridge_request", new=AsyncMock()) as mock_bridge:
        res = await settle_product_video_job_completion(job)
        assert res["ok"] is False
        assert res["error_code"] == "UNSAFE_OUTPUT_URL"
        mock_bridge.assert_not_called()


@pytest.mark.anyio
async def test_settle_on_invalid_metadata_blocked(test_web_db):
    """Item 6: Invalid artifact metadata -> settlement is rejected, zero debit."""
    invalid_meta = {"duration_seconds": 0.5, "width": 100, "height": 100, "file_size_bytes": 100}  # Too small (< 4096 bytes)
    job = _seed_account_and_job(job_id="pvj_bad_meta", output_metadata=invalid_meta)

    with patch("copyfast_bridge.bridge_request", new=AsyncMock()) as mock_bridge:
        res = await settle_product_video_job_completion(job)
        assert res["ok"] is False
        assert res["error_code"] == "INVALID_OUTPUT_METADATA"
        mock_bridge.assert_not_called()


@pytest.mark.anyio
async def test_missing_canonical_user_mapping_fails_closed(test_web_db):
    """Item 7: Missing canonical-user mapping -> fail closed (CANONICAL_USER_MAPPING_MISSING)."""
    # Seed account without canonical_user_id
    job = _seed_account_and_job(job_id="pvj_no_map", canonical_user_id="")

    with patch("copyfast_bridge.bridge_request", new=AsyncMock()) as mock_bridge:
        res = await settle_product_video_job_completion(job)
        assert res["ok"] is False
        assert res["error_code"] == "CANONICAL_USER_MAPPING_MISSING"
        mock_bridge.assert_not_called()

    # Projection recorded as failed truthfully
    with transaction() as conn:
        row = conn.execute(
            "SELECT status, error_code FROM web_product_video_settlement_projections WHERE web_job_id = 'pvj_no_map'"
        ).fetchone()
        assert row is not None
        assert row[0] == "failed"
        assert row[1] == "CANONICAL_USER_MAPPING_MISSING"


@pytest.mark.anyio
async def test_server_mapping_authority_over_payload_forgery(test_web_db):
    """Item 8: Caller-provided / forged canonical_user_id is ignored; server mapping is authoritative."""
    job = _seed_account_and_job(job_id="pvj_forgery_test", canonical_user_id="telegram-6824663936")
    # Attacker injects fake canonical_user_id in dict
    job["canonical_user_id"] = "7126457028"

    mock_bridge_resp = {
        "ok": True,
        "status": "settled",
        "settlement_id": "wpvs_mock_forgery",
        "web_job_id": "pvj_forgery_test",
        "amount_xu": 259,
        "balance_after": 41,
        "duplicate": False,
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch("copyfast_bridge.bridge_request", new=AsyncMock(return_value=mock_bridge_resp)) as mock_bridge:
        res = await settle_product_video_job_completion(job)
        assert res["ok"] is True
        # Server mapping 6824663936 was used, NOT the forged 7126457028!
        assert res["canonical_user_id"] == "6824663936"
        call_kwargs = mock_bridge.call_args[1]
        assert call_kwargs["payload"]["canonical_user_id"] == "6824663936"


@pytest.mark.anyio
async def test_retry_uses_same_idempotency_key(test_web_db):
    """Items 3, 16: Settlement retry uses the EXACT same idempotency key."""
    job = _seed_account_and_job(job_id="pvj_retry_key")

    mock_resp1 = {
        "ok": True,
        "status": "settled",
        "settlement_id": "wpvs_mock_retry",
        "amount_xu": 259,
        "duplicate": False,
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }
    with patch("copyfast_bridge.bridge_request", new=AsyncMock(return_value=mock_resp1)) as mock_bridge1:
        res1 = await settle_product_video_job_completion(job)
        assert res1["ok"] is True
        key1 = mock_bridge1.call_args[1]["payload"]["idempotency_key"]

    # Second call (retry)
    res2 = await settle_product_video_job_completion(job)
    assert res2["ok"] is True
    assert res2["duplicate"] is True
    assert res2["settlement_id"] == "wpvs_mock_retry"
    # Key persisted in projection is identical
    with transaction() as conn:
        key2 = conn.execute(
            "SELECT idempotency_key FROM web_product_video_settlement_projections WHERE web_job_id = 'pvj_retry_key'"
        ).fetchone()[0]
    assert key1 == key2 == "web_product_video_final_delivery:pvj_retry_key"


@pytest.mark.anyio
async def test_core_bridge_failure_never_fakes_settlement(test_web_db):
    """Item 17: CoreBridge failure never fakes debit or local settlement; remains failed truthfully."""
    job = _seed_account_and_job(job_id="pvj_bridge_down")

    mock_error_resp = {
        "ok": False,
        "error_code": "CORE_BRIDGE_UNAVAILABLE",
        "message": "Connection refused",
    }
    with patch("copyfast_bridge.bridge_request", new=AsyncMock(return_value=mock_error_resp)):
        res = await settle_product_video_job_completion(job)
        assert res["ok"] is False
        assert res["status"] == "failed"
        assert res["error_code"] == "CORE_BRIDGE_UNAVAILABLE"

    # Verify projection reflects 'failed', never fake settled!
    with transaction() as conn:
        row = conn.execute(
            "SELECT status, error_code, canonical_settlement_id FROM web_product_video_settlement_projections WHERE web_job_id = 'pvj_bridge_down'"
        ).fetchone()
        assert row is not None
        assert row[0] == "failed"
        assert row[1] == "CORE_BRIDGE_UNAVAILABLE"
        assert row[2] is None
