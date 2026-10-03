"""Security test matrix and dispatcher integration regression for ShopAIKey signed content safe URLs.

TASK=WEBAPP_PRODUCT_VIDEO_SHOPAIKEY_SIGNED_CONTENT_SAFE_URL_REMEDIATION_R1
"""

from __future__ import annotations

import json
from typing import Any
import uuid

from fastapi import HTTPException
import pytest

import copyfast_product_video_job_bridge as bridge
import copyfast_product_video_dispatcher as dispatcher
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now


def _seed_test_account(account_id: str) -> None:
    now = utc_now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES (?, ?, ?, 'user', ?, ?)
            """,
            (account_id, f"{account_id}@test.local", "hash1", now, now),
        )


def _seed_processing_job(job_id: str, worker_id: str = "test-worker-1") -> str:
    now = utc_now()
    account_id = f"acc-{uuid.uuid4().hex[:8]}"
    _seed_test_account(account_id)
    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_product_video_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                prompt, aspect_ratio, duration_seconds, quality_tier, scene_count,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope, output_metadata, created_at, updated_at,
                worker_id, claimed_at, lease_expires_at, attempts, output_url
            ) VALUES (
                ?, ?, ?, 'video_ai_prompt', 'video_ai_canonical',
                'Test prompt', '9:16', 5, 200, 1,
                'processing', 'PROCESSING_BY_WORKER', 'idem-hash', 'payload-hash',
                '{}', NULL, ?, ?,
                ?, ?, ?, 1, NULL
            )
            """,
            (
                job_id,
                f"req-{job_id}",
                account_id,
                now,
                now,
                worker_id,
                now,
                now,
            ),
        )
    return job_id


# =============================================================================
# 1. ShopAIKey Signed Content URL Unit Tests
# =============================================================================

def test_shopaikey_positive_synthetic_cases():
    valid_urls = [
        "https://api.shopaikey.com/v1/videos/task_TEST-123/content?exp=1791676800&sig=synthetic_signature",
        "https://api.shopaikey.com/v1/videos/task_4ovf5LyjaLn1MKOsm5XcVO8VmSZIESMj/content?exp=1791676800&sig=9513e0d6922c911d9a81aa0995e7ee87",
        "https://api.shopaikey.com:443/v1/videos/task_abc_123/content?exp=12345&sig=abcdef",
        "https://api.shopaikey.com/v1/videos/task-valid-uuid-001/content?sig=sigval&exp=9999999999&extra=param",
    ]
    for url in valid_urls:
        assert bridge.is_safe_shopaikey_content_url(url) is True, f"Failed on valid: {url}"
        assert bridge.is_safe_video_output_url(url) is True, f"Failed on valid: {url}"


def test_shopaikey_negative_cases_reject_insecure():
    negative_cases = [
        # Insecure scheme
        "http://api.shopaikey.com/v1/videos/task_1/content?exp=1&sig=x",
        # Subdomain / wildcard spoofing
        "https://evil.api.shopaikey.com/v1/videos/task_1/content?exp=1&sig=x",
        "https://api.shopaikey.com.evil.example/v1/videos/task_1/content?exp=1&sig=x",
        # Userinfo credentials
        "https://user:pass@api.shopaikey.com/v1/videos/task_1/content?exp=1&sig=x",
        # Non-standard port
        "https://api.shopaikey.com:444/v1/videos/task_1/content?exp=1&sig=x",
        "https://api.shopaikey.com:8080/v1/videos/task_1/content?exp=1&sig=x",
        # Missing query parameters
        "https://api.shopaikey.com/v1/videos/task_1/content",
        "https://api.shopaikey.com/v1/videos/task_1/content?exp=&sig=x",
        "https://api.shopaikey.com/v1/videos/task_1/content?exp=1&sig=",
        "https://api.shopaikey.com/v1/videos/task_1/content?exp=1",
        "https://api.shopaikey.com/v1/videos/task_1/content?sig=x",
        # Extra or malformed path
        "https://api.shopaikey.com/v1/videos/task_1/content/extra?exp=1&sig=x",
        "https://api.shopaikey.com/v1/videos/task_1/bad/content?exp=1&sig=x",
        "https://api.shopaikey.com/v1/videos//content?exp=1&sig=x",
        # Path traversal
        "https://api.shopaikey.com/v1/videos/../content?exp=1&sig=x",
        "https://api.shopaikey.com/v1/videos/%2e/content?exp=1&sig=x",
        "https://api.shopaikey.com/v1/videos/..%2fcontent?exp=1&sig=x",
        # Fragments
        "https://api.shopaikey.com/v1/videos/task_1/content?exp=1&sig=x#fragment",
        # Control characters and backslashes
        "https://api.shopaikey.com/v1/videos/task_1/content?exp=1&sig=x\n",
        "https://api.shopaikey.com\\v1/videos/task_1/content?exp=1&sig=x",
        # Non-strings and empty
        None,
        "",
        "   ",
        123,
    ]
    for url in negative_cases:
        assert bridge.is_safe_shopaikey_content_url(url) is False, f"Should reject: {url}"


def test_legacy_video_extension_policy_preserved():
    # Valid legacy URLs
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/video.mp4") is True
    assert bridge.is_safe_video_output_url("https://tg.toanaas.vn/media/render.webm") is True
    assert bridge.is_safe_video_output_url("https://cdn.example.com/asset.mov") is True

    # Legacy rejections remain strict
    assert bridge.is_safe_video_output_url("http://storage.googleapis.com/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://127.0.0.1/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://10.0.0.1/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://169.254.169.254/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://[::1]/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://localhost/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://app.localhost/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/video.txt") is False
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/video") is False
    assert bridge.is_safe_video_output_url("https://example.com/video.mp4#hash") is False


# =============================================================================
# 2. Dispatcher Integration Tests
# =============================================================================

def test_dispatcher_complete_with_synthetic_shopaikey_signed_url():
    ensure_copyfast_schema()
    job_id = f"pvj-test-{uuid.uuid4().hex[:8]}"
    worker_id = "test-worker-alpha"
    _seed_processing_job(job_id, worker_id)

    synthetic_url = (
        "https://api.shopaikey.com/v1/videos/task_TEST-123/content?exp=1791676800&sig=synthetic_signature"
    )
    valid_meta = {
        "duration_seconds": 5.0,
        "width": 720,
        "height": 1280,
        "file_size_bytes": 1048576,
        "format": "mp4",
        "codec": "h264",
    }

    result = dispatcher.complete_product_video_job(
        job_id=job_id,
        worker_id=worker_id,
        output_metadata=valid_meta,
        output_url=synthetic_url,
    )

    assert result["id"] == job_id
    assert result["status"] == "completed"
    assert result["output_url"] == synthetic_url

    # Check persistence in database
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT status, output_url, output_metadata FROM web_product_video_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == "completed"
        assert row[1] == synthetic_url
        persisted_meta = json.loads(row[2])
        assert persisted_meta["duration_seconds"] == 5.0
        assert persisted_meta["file_size_bytes"] == 1048576


def test_dispatcher_complete_rejects_invalid_shopaikey_url():
    ensure_copyfast_schema()
    job_id = f"pvj-test-{uuid.uuid4().hex[:8]}"
    worker_id = "test-worker-beta"
    _seed_processing_job(job_id, worker_id)

    invalid_url = (
        "http://api.shopaikey.com/v1/videos/task_TEST-123/content?exp=1791676800&sig=synthetic_signature"
    )
    valid_meta = {
        "duration_seconds": 5.0,
        "width": 720,
        "height": 1280,
        "file_size_bytes": 1048576,
        "format": "mp4",
        "codec": "h264",
    }

    with pytest.raises(HTTPException) as exc_info:
        dispatcher.complete_product_video_job(
            job_id=job_id,
            worker_id=worker_id,
            output_metadata=valid_meta,
            output_url=invalid_url,
        )
    assert exc_info.value.status_code == 422
    assert "Output URL không an toàn" in exc_info.value.detail

    # Verify job was NOT completed
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT status FROM web_product_video_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        assert row[0] == "processing"
