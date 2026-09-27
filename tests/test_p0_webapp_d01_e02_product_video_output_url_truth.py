"""Tests for D01-E02: Product video (video_ai_prompt) output URL delivery truth.

SPEC_ID=WEBAPP_D01_E02_PRODUCT_VIDEO_OUTPUT_URL_DELIVERY_TRUTH_R1
Parent: #573 (D01), #561 (Master Epic)
Issue: #576

Enforces fail-closed delivery truth:
1. Output availability requires both completion AND a safe external HTTPS output URL.
2. Zero fabricated fallback to /api/v1/assets/{id}/download when output_url is NULL or empty.
3. Unsafe URLs (HTTP, embedded credentials, path traversal, backslashes, nonstandard ports)
   are rejected and fail-closed to output_available=False, output=None.
4. Parity between typed public formatter, native compat projection, and dispatcher worker views.
5. Zero DB mutations on read projections.
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


def _seed_account(account_id: str) -> None:
    now = utc_now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, role_cache, created_at, updated_at)
            VALUES (?, ?, ?, 'user', ?, ?)
            """,
            (account_id, f"{account_id}@test.local", "hash1", now, now),
        )


def _make_row(
    job_id: str = "pvj-test-1",
    request_id: str = "req-test-1",
    account_id: str = "acc-test-1",
    status: str = "completed",
    status_reason: str = "NORMAL_COMPLETION",
    output_url: str | None = None,
    output_metadata: dict[str, Any] | None = None,
) -> tuple:
    now = utc_now()
    return (
        job_id,  # 0
        request_id,  # 1
        account_id,  # 2
        "video_ai_prompt",  # 3
        "video_ai_canonical",  # 4
        "A cute cat walking in Tokyo",  # 5
        "9:16",  # 6
        5,  # 7
        200,  # 8
        1,  # 9
        status,  # 10
        status_reason,  # 11
        "hash-idem",  # 12
        "hash-payload",  # 13
        json.dumps({"version": 1}),  # 14
        json.dumps(output_metadata) if output_metadata else None,  # 15
        now,  # 16
        now,  # 17
        "worker-1",  # 18
        now,  # 19
        now,  # 20
        1,  # 21
        output_url,  # 22
    )


# =============================================================================
# 1. Output URL Validation Contract (is_safe_video_output_url)
# =============================================================================

def test_is_safe_video_output_url_contract():
    """Verify is_safe_video_output_url exported from bridge matches security invariant."""
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/video.mp4") is True
    assert bridge.is_safe_video_output_url("https://tg.toanaas.vn/media/render.mp4") is True
    assert bridge.is_safe_video_output_url("https://cdn.example.com/asset.webm") is True
    assert bridge.is_safe_video_output_url("https://cdn.example.com/asset.mov") is True

    # Rejections: empty / invalid types
    assert bridge.is_safe_video_output_url(None) is False
    assert bridge.is_safe_video_output_url("") is False
    assert bridge.is_safe_video_output_url("   ") is False

    # Rejections: scheme & protocol
    assert bridge.is_safe_video_output_url("http://storage.googleapis.com/video.mp4") is False
    assert bridge.is_safe_video_output_url("ftp://server/video.mp4") is False
    assert bridge.is_safe_video_output_url("javascript:alert(1)") is False
    assert bridge.is_safe_video_output_url("data:video/mp4;base64,AAAA") is False

    # Rejections: credentials, traversal, path injection, nonstandard port
    assert bridge.is_safe_video_output_url("https://user:pass@example.com/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://example.com/path/../secret.mp4") is False
    assert bridge.is_safe_video_output_url("https://example.com/path%2esecret.mp4") is False
    assert bridge.is_safe_video_output_url("https://example.com/path\\video.mp4") is False
    assert bridge.is_safe_video_output_url("https://example.com:8080/video.mp4") is False

    # Rejections: non-video extensions
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/video.txt") is False
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/video.exe") is False
    assert bridge.is_safe_video_output_url("https://storage.googleapis.com/toanaas-media/video") is False

    # Rejections: private, loopback, link-local IPs and localhost (SSRF protection)
    assert bridge.is_safe_video_output_url("https://127.0.0.1/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://10.0.0.1/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://192.168.0.1/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://169.254.169.254/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://[::1]/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://localhost/video.mp4") is False
    assert bridge.is_safe_video_output_url("https://app.localhost/video.mp4") is False


# =============================================================================
# 2. Typed Public Job Formatter Delivery Truth
# =============================================================================

def test_format_public_job_completed_with_safe_url():
    """Completed job with safe HTTPS URL exposes delivery readiness and matching output URL."""
    safe_url = "https://storage.googleapis.com/toanaas-media/video.mp4"
    row = _make_row(status="completed", output_url=safe_url, output_metadata={"duration": 5.0})
    job = bridge._format_public_job(row)

    assert job["status"] == "completed"
    assert job["output_available"] is True
    assert job["download_ready"] is True
    assert job["delivery_ready"] is True
    assert job["output"] == safe_url
    assert job["output_url"] == safe_url
    assert job["output_metadata"] == {"duration": 5.0}


def test_format_public_job_completed_with_missing_url_no_fabricated_fallback():
    """Completed job with NULL/empty output_url must NOT fabricate /api/v1/assets/ download URL."""
    for empty_val in (None, ""):
        row = _make_row(status="completed", output_url=empty_val)
        job = bridge._format_public_job(row)

        assert job["status"] == "completed"
        assert job["output_available"] is False
        assert job["download_ready"] is False
        assert job["delivery_ready"] is False
        assert job["output"] is None
        assert job["output_url"] is None

        # Verify zero fabricated URL
        assert "/api/v1/assets/" not in str(job.get("output"))
        assert "/api/v1/assets/" not in str(job.get("output_url"))


def test_format_public_job_completed_with_unsafe_url_fails_closed():
    """Completed job with unsafe output_url fails closed to output_available=False, output=None."""
    unsafe_urls = [
        "http://insecure.com/video.mp4",
        "javascript:alert(1)",
        "https://admin:secret@cdn.example.com/video.mp4",
        "https://cdn.example.com/video/../secret.mp4",
        "https://cdn.example.com/video\\back.mp4",
        "https://cdn.example.com:8443/video.mp4",
        "data:video/mp4;base64,1234",
        "https://127.0.0.1/video.mp4",
        "https://10.0.0.1/video.mp4",
        "https://192.168.0.1/video.mp4",
        "https://169.254.169.254/video.mp4",
        "https://localhost/video.mp4",
        "https://sub.localhost/video.mp4",
        "https://storage.googleapis.com/toanaas-media/video.txt",
    ]
    for unsafe_url in unsafe_urls:
        row = _make_row(status="completed", output_url=unsafe_url)
        job = bridge._format_public_job(row)

        assert job["status"] == "completed"
        assert job["output_available"] is False
        assert job["download_ready"] is False
        assert job["delivery_ready"] is False
        assert job["output"] is None
        assert job["output_url"] is None


def test_format_public_job_non_terminal_states_have_no_output():
    """Queued and processing jobs must never expose output readiness."""
    safe_url = "https://storage.googleapis.com/toanaas-media/video.mp4"
    for state in ("queued", "processing"):
        row = _make_row(status=state, output_url=safe_url)
        job = bridge._format_public_job(row)

        assert job["output_available"] is False
        assert job["download_ready"] is False
        assert job["delivery_ready"] is False
        assert job["output"] is None
        assert job["output_url"] is None


def test_format_public_job_terminal_failure_states_have_no_output():
    """Failed, cancelled, and rejected jobs must never expose output readiness."""
    safe_url = "https://storage.googleapis.com/toanaas-media/video.mp4"
    for state in ("failed", "cancelled", "rejected"):
        row = _make_row(status=state, output_url=safe_url)
        job = bridge._format_public_job(row)

        assert job["output_available"] is False
        assert job["download_ready"] is False
        assert job["delivery_ready"] is False
        assert job["output"] is None
        assert job["output_url"] is None


# =============================================================================
# 3. Native Compat Projection Parity
# =============================================================================

def test_product_video_job_to_native_compat_parity():
    """Native compat projection must reflect truthful output availability."""
    safe_url = "https://storage.googleapis.com/toanaas-media/video.mp4"

    # Case A: Valid completed with safe URL
    typed_job_valid = bridge._format_public_job(_make_row(status="completed", output_url=safe_url))
    native_valid = bridge.product_video_job_to_native_compat(typed_job_valid)
    assert native_valid["output_available"] is True
    assert native_valid["download_ready"] is True
    assert native_valid["delivery_ready"] is True
    assert native_valid["output"] == safe_url

    # Case B: Completed with NULL output URL
    typed_job_null = bridge._format_public_job(_make_row(status="completed", output_url=None))
    native_null = bridge.product_video_job_to_native_compat(typed_job_null)
    assert native_null["output_available"] is False
    assert native_null["download_ready"] is False
    assert native_null["delivery_ready"] is False
    assert native_null["output"] is None

    # Case C: Completed with unsafe URL
    typed_job_unsafe = bridge._format_public_job(_make_row(status="completed", output_url="http://insecure.com/vid.mp4"))
    native_unsafe = bridge.product_video_job_to_native_compat(typed_job_unsafe)
    assert native_unsafe["output_available"] is False
    assert native_unsafe["download_ready"] is False
    assert native_unsafe["delivery_ready"] is False
    assert native_unsafe["output"] is None

    # Case D: Raw dictionary without output_available field defaults to False
    synthetic_raw_job = {
        "id": "pvj-raw",
        "status": "completed",
        "created_at": "2026-07-17T00:00:00Z",
        "updated_at": "2026-07-17T00:00:00Z",
        "output": safe_url,
    }
    native_raw = bridge.product_video_job_to_native_compat(synthetic_raw_job)
    assert native_raw["output_available"] is False
    assert native_raw["output"] is None


# =============================================================================
# 4. Dispatcher Completion & Dispatched Job Formatter Truth
# =============================================================================

def test_dispatcher_complete_and_format_truth(tmp_path, monkeypatch):
    """Dispatcher completion and formatted job must enforce safe output URL."""
    db_file = str(tmp_path / "test_dispatcher_truth.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_file))
    ensure_copyfast_schema()

    account_id = "acc-disp-1"
    req_id = "req-disp-1"
    _seed_account(account_id)
    job = bridge.create_or_replay_product_video_job(
        account_id=account_id,
        request_id=req_id,
        payload={"prompt": "A running dog in park", "aspect_ratio": "16:9", "duration_seconds": 5, "quality_tier": 200},
    )
    job_id = job["id"]

    # Claim the job as worker
    claim_res = dispatcher.claim_product_video_job(worker_id="worker-test-1")
    assert claim_res is not None
    assert claim_res["id"] == job_id

    synth_meta = dispatcher.generate_synthetic_product_video_output(
        {"id": job_id, "aspect_ratio": "16:9", "duration_seconds": 5}
    )

    # 1. Unsafe URL must be rejected with 422
    with pytest.raises(HTTPException) as exc_info:
        dispatcher.complete_product_video_job(
            job_id=job_id,
            worker_id="worker-test-1",
            output_url="http://insecure.com/output.mp4",
            output_metadata=synth_meta,
        )
    assert exc_info.value.status_code == 422
    assert "Output URL không an toàn" in str(exc_info.value.detail)

    # 2. Complete with safe URL succeeds
    safe_url = f"https://static.toanaas.vn/artifacts/video/{job_id}.mp4"
    complete_res = dispatcher.complete_product_video_job(
        job_id=job_id,
        worker_id="worker-test-1",
        output_url=safe_url,
        output_metadata=synth_meta,
    )
    assert complete_res["status"] == "completed"
    assert complete_res["output_url"] == safe_url
    assert complete_res["output_available"] is True
    assert complete_res["download_ready"] is True
    assert complete_res["delivery_ready"] is True
    assert complete_res["output"] == safe_url

    # Check via get_product_video_job
    public_job = bridge.get_product_video_job(account_id, job_id)
    assert public_job is not None
    assert public_job["output_available"] is True
    assert public_job["download_ready"] is True
    assert public_job["delivery_ready"] is True
    assert public_job["output"] == safe_url
    assert public_job["output_url"] == safe_url


def test_dispatcher_complete_without_output_url_does_not_fabricate(tmp_path, monkeypatch):
    """Completing a job without output_url leaves output_url as None, no fabricated download path."""
    db_file = str(tmp_path / "test_dispatcher_no_url.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_file))
    ensure_copyfast_schema()

    account_id = "acc-disp-2"
    _seed_account(account_id)
    job = bridge.create_or_replay_product_video_job(
        account_id=account_id,
        request_id="req-disp-2",
        payload={"prompt": "Sunrise on ocean beach", "aspect_ratio": "16:9", "duration_seconds": 5, "quality_tier": 200},
    )
    job_id = job["id"]

    claim_res = dispatcher.claim_product_video_job(worker_id="worker-test-2")
    assert claim_res is not None

    synth_meta = dispatcher.generate_synthetic_product_video_output(
        {"id": job_id, "aspect_ratio": "16:9", "duration_seconds": 5}
    )

    # Complete without output_url
    complete_res = dispatcher.complete_product_video_job(
        job_id=job_id,
        worker_id="worker-test-2",
        output_url="",
        output_metadata=synth_meta,
    )
    assert complete_res["status"] == "completed"
    assert complete_res["output_url"] is None
    assert complete_res["output_available"] is False
    assert complete_res["download_ready"] is False
    assert complete_res["delivery_ready"] is False
    assert complete_res["output"] is None

    # Check via get_product_video_job
    public_job = bridge.get_product_video_job(account_id, job_id)
    assert public_job is not None
    assert public_job["output_available"] is False
    assert public_job["download_ready"] is False
    assert public_job["delivery_ready"] is False
    assert public_job["output"] is None
    assert public_job["output_url"] is None
    assert "/api/v1/assets/" not in str(public_job)


def test_private_and_loopback_output_urls_rejected_in_all_surfaces(tmp_path, monkeypatch):
    """Explicitly verify 127.0.0.1, 10.0.0.1, 192.168.0.1, 169.254.169.254, localhost fail closed across bridge, compat, and dispatcher."""
    private_urls = [
        "https://127.0.0.1/video.mp4",
        "https://10.0.0.1/video.mp4",
        "https://192.168.0.1/video.mp4",
        "https://169.254.169.254/video.mp4",
        "https://localhost/video.mp4",
        "https://app.localhost/video.mp4",
    ]

    db_file = str(tmp_path / "test_private_ip_surfaces.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_file))
    ensure_copyfast_schema()

    account_id = "acc-priv-test"
    _seed_account(account_id)

    for idx, bad_url in enumerate(private_urls):
        # 1. Bridge public job formatter
        row = _make_row(job_id=f"pvj-priv-{idx}", account_id=account_id, status="completed", output_url=bad_url)
        job = bridge._format_public_job(row)
        assert job["output_available"] is False
        assert job["download_ready"] is False
        assert job["delivery_ready"] is False
        assert job["output"] is None
        assert job["output_url"] is None

        # 2. Native compat projection
        compat = bridge.product_video_job_to_native_compat(job)
        assert compat["output_available"] is False
        assert compat["download_ready"] is False
        assert compat["delivery_ready"] is False
        assert compat["output"] is None

        # 3. Dispatcher completion
        created = bridge.create_or_replay_product_video_job(
            account_id=account_id,
            request_id=f"req-priv-{idx}",
            payload={"prompt": "test private url", "aspect_ratio": "16:9", "duration_seconds": 5, "quality_tier": 200},
        )
        j_id = created["id"]
        dispatcher.claim_product_video_job(worker_id=f"worker-priv-{idx}")
        meta = dispatcher.generate_synthetic_product_video_output({"id": j_id, "aspect_ratio": "16:9", "duration_seconds": 5})

        with pytest.raises(HTTPException) as exc_info:
            dispatcher.complete_product_video_job(
                job_id=j_id,
                worker_id=f"worker-priv-{idx}",
                output_url=bad_url,
                output_metadata=meta,
            )
        assert exc_info.value.status_code == 422
        assert "Output URL không an toàn" in str(exc_info.value.detail)

    # Positive safe external HTTPS case across all surfaces
    safe_external = "https://storage.googleapis.com/toanaas-media/video.mp4"
    safe_row = _make_row(job_id="pvj-safe-ext", account_id=account_id, status="completed", output_url=safe_external)
    safe_job = bridge._format_public_job(safe_row)
    assert safe_job["output_available"] is True
    assert safe_job["download_ready"] is True
    assert safe_job["delivery_ready"] is True
    assert safe_job["output"] == safe_external
    assert safe_job["output_url"] == safe_external

    safe_compat = bridge.product_video_job_to_native_compat(safe_job)
    assert safe_compat["output_available"] is True
    assert safe_compat["download_ready"] is True
    assert safe_compat["delivery_ready"] is True
    assert safe_compat["output"] == safe_external

    safe_created = bridge.create_or_replay_product_video_job(
        account_id=account_id,
        request_id="req-safe-ext",
        payload={"prompt": "test safe ext url", "aspect_ratio": "16:9", "duration_seconds": 5, "quality_tier": 200},
    )
    safe_jid = safe_created["id"]
    dispatcher.claim_product_video_job(worker_id="worker-safe-ext")
    safe_meta = dispatcher.generate_synthetic_product_video_output({"id": safe_jid, "aspect_ratio": "16:9", "duration_seconds": 5})
    complete_res = dispatcher.complete_product_video_job(
        job_id=safe_jid,
        worker_id="worker-safe-ext",
        output_url=safe_external,
        output_metadata=safe_meta,
    )
    assert complete_res["status"] == "completed"
    assert complete_res["output_available"] is True
    assert complete_res["output_url"] == safe_external
    assert complete_res["output"] == safe_external
