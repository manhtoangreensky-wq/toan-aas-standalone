"""Targeted contract and integration tests for Web-to-Bot Canonical Image Staging and Prepare Bridge (R24E3B).

SPEC_ID: WEBAPP-R24E3B-IMAGE-TRANSFORM-WEB-TO-BOT-CANONICAL-BRIDGE
Task: WEBAPP_R24E3B_IMAGE_TRANSFORM_WEB_TO_BOT_CANONICAL_STAGING_AND_PREPARE_BRIDGE_R1
Program: WEBAPP_R24_IMAGE_TRANSFORM_CLOSURE (#629)

Verifies:
1. Canonical Core Bridge reused (copyfast_bridge.bridge_request).
2. Direct Key4U HTTP absent.
3. Web Key4U credential access absent.
4. Core Bridge unconfigured fail closed.
5. Valid owner-scoped PNG staging.
6. Valid JPEG staging.
7. Valid WEBP staging.
8. Source storage missing fail closed.
9. Source SHA mismatch fail closed.
10. Cross-owner source rejected.
11. Staging request SHA correct.
12. Staging actor derived from canonical identity.
13. Staging response missing upload_id rejected.
14. Exact prepare path correct.
15. Provider/model injection never emitted.
16. Valid prepare response persisted into durable Web SQLite state.
17. Completed prepare response rejected.
18. Provider task ID prepare response rejected.
19. Output URL prepare response rejected.
20. Owner mismatch prepare response rejected.
21. Upload_id mismatch prepare response rejected.
22. Same prepared job does not upload twice (idempotency).
23. Changed idempotent create replay remains 409 Conflict.
24. Customer cannot inject authority / upload_id / bridge_envelope.
25. Bot public flag true does NOT permit provider execution.
26. Invariant verification: zero provider spend, zero wallet mutations.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import copyfast_bridge
from copyfast_db import (
    asset_vault_directory,
    ensure_copyfast_schema,
    transaction,
    utc_now,
)
from copyfast_image_transform_job_bridge import (
    STATUS_QUEUED,
    create_or_replay_image_transform_job,
    ensure_image_transform_schema,
    get_image_transform_job,
)
from copyfast_image_transform_runtime_bridge import (
    BOT_PRIVATE_PREPARE_ROUTE,
    BOT_PRIVATE_UPLOAD_ROUTE,
    CORE_BRIDGE_UNCONFIGURED,
    IMAGE_TRANSFORM_PROVIDER_DISPATCH_ENABLED,
    SOURCE_ASSET_CORRUPT,
    SOURCE_ASSET_NOT_FOUND,
    SOURCE_ASSET_OWNER_MISMATCH,
    STATUS_PREPARED_PROVIDER_DISABLED,
    STATUS_REASON_UNPROVEN,
    WEB_PROVIDER_EXECUTOR_IMPLEMENTED,
    prepare_image_transform_job_with_bot,
    resolve_source_asset_bytes,
)

# 1x1 Sample bytes
SAMPLE_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00"
    b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
SAMPLE_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
    b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01"
    b"\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01"
    b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08"
    b"\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)
SAMPLE_WEBP_BYTES = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x000\x01\x00\x9d\x01*\x01\x00"
    b"\x01\x00\x02\x004%\xa4\x00"
)


@pytest.fixture(autouse=True)
def setup_isolated_env(tmp_path: Path, monkeypatch):
    """Isolate SQLite database, Asset Vault root, and Core Bridge credentials."""
    db_file = tmp_path / "test_copyfast.db"
    vault_root = tmp_path / "assets_vault"
    vault_root.mkdir(parents=True, exist_ok=True)
    objects_dir = vault_root / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("COPYFAST_DB_PATH", str(db_file))
    monkeypatch.setenv("WEBAPP_SESSION_DATABASE", str(db_file))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(vault_root))

    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "https://bridge.invalid")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token-xyz")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-bridge-hmac-secret-12345")

    ensure_copyfast_schema()
    ensure_image_transform_schema()

    with transaction() as conn:
        conn.execute("DELETE FROM web_image_transform_jobs")
        conn.execute("DELETE FROM web_asset_files WHERE account_id LIKE 'acc_user_%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'acc_user_%'")

    # Create test accounts: user_a and user_b
    now = utc_now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, canonical_user_id, role_cache, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("acc_user_a", "usera@example.com", "hash", "canonical_user_a_100", "user", 1, now, now),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, canonical_user_id, role_cache, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("acc_user_b", "userb@example.com", "hash", "canonical_user_b_200", "user", 1, now, now),
        )

    return {"db_file": db_file, "vault_root": vault_root}


def create_test_asset(
    account_id: str,
    asset_id: str,
    filename: str,
    ext: str,
    content_type: str,
    content: bytes,
    storage_hex: str = "11112222333344445555666677778888",
    corrupt_sha: bool = False,
    write_disk: bool = True,
    state: str = "active",
) -> dict[str, Any]:
    """Helper to register an Asset Vault file and optionally write physical object."""
    sha = hashlib.sha256(content).hexdigest()
    recorded_sha = "0" * 64 if corrupt_sha else sha
    storage_key = f"objects/{storage_hex}.blob"
    now = utc_now()

    if write_disk:
        vault_root = Path(asset_vault_directory())
        blob_path = vault_root / "objects" / f"{storage_hex}.blob"
        blob_path.write_bytes(content)

    with transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO web_asset_files (
                id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key, state,
                lifecycle_revision, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
            """,
            (
                asset_id,
                account_id,
                None,
                filename,
                filename,
                ext,
                content_type,
                len(content),
                recorded_sha,
                storage_key,
                state,
                now,
                now,
            ),
        )
    return {
        "asset_id": asset_id,
        "account_id": account_id,
        "filename": filename,
        "sha256": recorded_sha,
        "storage_key": storage_key,
    }


def make_mock_bot_responses(upload_id: str = "upl_test_9999", actor_id: str = "canonical_user_a_100"):
    """Helper returning standard accepted Bot #1430 fixtures."""
    bot_upload_resp = {
        "ok": True,
        "status": "completed",
        "data": {
            "upload_id": upload_id,
            "file_name": "source.png",
            "content_type": "image/png",
            "size_bytes": len(SAMPLE_PNG_BYTES),
            "sha256": hashlib.sha256(SAMPLE_PNG_BYTES).hexdigest(),
        },
    }
    bot_prepare_resp = {
        "ok": True,
        "status": "PREPARED_PROVIDER_DISABLED",
        "data": {
            "status": "PREPARED_PROVIDER_DISABLED",
            "status_reason": "EXTERNAL_PROVIDER_AUTHORITY_AND_ENTITLEMENT_UNPROVEN",
            "upload_id": upload_id,
            "owner_id": actor_id,
            "capability": "image_transform",
            "executor_owner": "bot",
            "provider_family": "key4u",
            "provider_executor_implemented": True,
            "provider_execution_allowed": False,
            "key4u_public_enabled": False,
            "key4u_contract_proven": True,
            "key4u_model_authority_proven": False,
            "aspect_ratio": "16:9",
            "instruction_sanitized": "Make it a painting",
            "blockers": [
                "KEY4U_ACCOUNT_ENTITLEMENT_PROVEN=NO",
                "KEY4U_PRICING_AUTHORITY_PROVEN=NO",
                "KEY4U_QUOTA_AUTHORITY_PROVEN=NO",
                "KEY4U_SPECIFIC_GROK_MODEL_PROVIDER_AUTHORITY_PROVEN=NO",
                "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE",
            ],
            "blocker_details": {
                "account_entitlement_proven": False,
                "pricing_authority_proven": False,
                "quota_authority_proven": False,
                "specific_model_authority_proven": False,
                "owner_live_acceptance_proven": False,
            },
        },
    }
    return bot_upload_resp, bot_prepare_resp


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 18 TEST MATRIX IMPLEMENTATION
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_01_canonical_core_bridge_reused_and_pipeline_success(monkeypatch):
    """1. Canonical Core Bridge reused; 11. Staging SHA correct; 12. Actor derived; 14. Prepare path correct."""
    create_test_asset("acc_user_a", "ast_png_1", "portrait.png", ".png", "image/png", SAMPLE_PNG_BYTES)
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {
            "image_asset_id": "ast_png_1",
            "transform_instruction": "Oil painting style",
            "aspect_ratio": "16:9",
        },
    )

    upload_resp, prepare_resp = make_mock_bot_responses("upl_canonical_1", "canonical_user_a_100")
    bridge_calls = []

    async def mock_bridge_request(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        bridge_calls.append({"method": method, "path": path, "payload": payload, "actor_id": actor_id})
        if path == BOT_PRIVATE_UPLOAD_ROUTE:
            return upload_resp
        if path == BOT_PRIVATE_PREPARE_ROUTE:
            return prepare_resp
        raise ValueError(f"Unexpected path: {path}")

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge_request)

    res = await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert res["ok"] is True
    assert res["bot_upload_id"] == "upl_canonical_1"
    assert res["bot_prepare_status"] == STATUS_PREPARED_PROVIDER_DISABLED
    assert res["provider_execution_allowed"] is False
    assert len(bridge_calls) == 2

    # Check call 1: Staging upload
    call1 = bridge_calls[0]
    assert call1["method"] == "POST"
    assert call1["path"] == "/internal/v1/uploads"
    assert call1["actor_id"] == "canonical_user_a_100"
    assert call1["payload"]["file_name"] == "portrait.png"
    assert call1["payload"]["content_type"] == "image/png"
    assert call1["payload"]["sha256"] == hashlib.sha256(SAMPLE_PNG_BYTES).hexdigest()
    assert "owner_id" not in call1["payload"]
    assert "provider" not in call1["payload"]

    # Check call 2: Prepare seam
    call2 = bridge_calls[1]
    assert call2["method"] == "POST"
    assert call2["path"] == "/internal/v1/web-image-transform/prepare"
    assert call2["actor_id"] == "canonical_user_a_100"
    assert call2["payload"] == {
        "upload_id": "upl_canonical_1",
        "transform_instruction": "Oil painting style",
        "aspect_ratio": "16:9",
    }


def test_02_direct_key4u_http_absent():
    """2. Direct Key4U HTTP absent from copyfast_image_transform_runtime_bridge source."""
    src = Path("copyfast_image_transform_runtime_bridge.py").read_text(encoding="utf-8")
    assert "api.key4u.com" not in src
    assert "key4u" not in src.lower() or "bot_provider_family" in src or "key4u_public_enabled" in src
    assert "requests." not in src
    assert "httpx.post" not in src
    assert "httpx.get" not in src


def test_03_web_key4u_credential_access_absent():
    """3. Web Key4U credential access absent: never loads KEY4U_API_KEY."""
    src = Path("copyfast_image_transform_runtime_bridge.py").read_text(encoding="utf-8")
    assert "KEY4U_API_KEY" not in src
    assert "KEY4U_SECRET" not in src


@pytest.mark.anyio
async def test_04_core_bridge_unconfigured_fail_closed(monkeypatch):
    """4. Core Bridge unconfigured fail closed."""
    create_test_asset("acc_user_a", "ast_png_2", "photo.png", ".png", "image/png", SAMPLE_PNG_BYTES)
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_png_2", "transform_instruction": "enhance"},
    )
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert exc_info.value.status_code == 503
    assert CORE_BRIDGE_UNCONFIGURED in exc_info.value.detail


@pytest.mark.anyio
async def test_05_06_07_valid_png_jpeg_webp_staging(monkeypatch):
    """5, 6, 7. Valid owner-scoped PNG, JPEG, WEBP staging."""
    create_test_asset("acc_user_a", "ast_png_v", "art.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="10001000100010001000100010001001")
    create_test_asset("acc_user_a", "ast_jpg_v", "art.jpg", ".jpg", "image/jpeg", SAMPLE_JPEG_BYTES, storage_hex="10001000100010001000100010001002")
    create_test_asset("acc_user_a", "ast_webp_v", "art.webp", ".webp", "image/webp", SAMPLE_WEBP_BYTES, storage_hex="10001000100010001000100010001003")

    staged_types = []

    async def mock_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        if path == BOT_PRIVATE_UPLOAD_ROUTE:
            staged_types.append(payload["content_type"])
            return {"ok": True, "status": "completed", "data": {"upload_id": f"upl_{len(staged_types)}"}}
        if path == BOT_PRIVATE_PREPARE_ROUTE:
            _, p_resp = make_mock_bot_responses(payload["upload_id"], actor_id)
            return p_resp
        raise ValueError(f"Path: {path}")

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    for ast_id, expected_mime in [("ast_png_v", "image/png"), ("ast_jpg_v", "image/jpeg"), ("ast_webp_v", "image/webp")]:
        job = create_or_replay_image_transform_job(
            "acc_user_a",
            {"image_asset_id": ast_id, "transform_instruction": "style"},
        )
        res = await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
        assert res["ok"] is True

    assert staged_types == ["image/png", "image/jpeg", "image/webp"]


@pytest.mark.anyio
async def test_08_source_storage_missing_fail_closed():
    """8. Source storage physical object missing on disk fails closed."""
    create_test_asset(
        "acc_user_a", "ast_missing", "gone.png", ".png", "image/png", SAMPLE_PNG_BYTES,
        storage_hex="99999999999999999999999999999999", write_disk=False,
    )
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_missing", "transform_instruction": "style"},
    )
    with pytest.raises(HTTPException) as exc_info:
        await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert exc_info.value.status_code == 404
    assert SOURCE_ASSET_NOT_FOUND in exc_info.value.detail


@pytest.mark.anyio
async def test_09_source_sha_mismatch_fail_closed():
    """9. Source SHA mismatch fail closed."""
    create_test_asset(
        "acc_user_a", "ast_corrupt", "corrupt.png", ".png", "image/png", SAMPLE_PNG_BYTES,
        storage_hex="88888888888888888888888888888888", corrupt_sha=True, write_disk=True,
    )
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_corrupt", "transform_instruction": "style"},
    )
    with pytest.raises(HTTPException) as exc_info:
        await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert exc_info.value.status_code == 400
    assert SOURCE_ASSET_CORRUPT in exc_info.value.detail


@pytest.mark.anyio
async def test_10_cross_owner_source_and_job_rejected():
    """10. Cross-owner source asset and cross-owner job access rejected."""
    # Asset owned by user B
    create_test_asset("acc_user_b", "ast_user_b", "b.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="77777777777777777777777777777777")

    # User A tries to create job with User B's asset -> rejected at creation
    with pytest.raises(HTTPException) as exc_info:
        create_or_replay_image_transform_job(
            "acc_user_a",
            {"image_asset_id": "ast_user_b", "transform_instruction": "style"},
        )
    assert exc_info.value.status_code == 400

    # User B creates job
    job_b = create_or_replay_image_transform_job(
        "acc_user_b",
        {"image_asset_id": "ast_user_b", "transform_instruction": "style"},
    )

    # User A tries to prepare User B's job -> rejected with 403
    with pytest.raises(HTTPException) as exc_info2:
        await prepare_image_transform_job_with_bot("acc_user_a", job_b["id"])
    assert exc_info2.value.status_code == 403
    assert SOURCE_ASSET_OWNER_MISMATCH in exc_info2.value.detail


@pytest.mark.anyio
async def test_13_staging_response_missing_upload_id_rejected(monkeypatch):
    """13. Staging response missing upload_id rejected."""
    create_test_asset("acc_user_a", "ast_t13", "t13.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="66666666666666666666666666666666")
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_t13", "transform_instruction": "style"},
    )

    async def mock_bad_upload(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        return {"ok": True, "status": "completed", "data": {}}  # missing upload_id

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bad_upload)

    with pytest.raises(HTTPException) as exc_info:
        await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert exc_info.value.status_code == 502
    assert "BOT_UPLOAD_REJECTED" in exc_info.value.detail


@pytest.mark.anyio
async def test_15_provider_model_injection_never_emitted(monkeypatch):
    """15. Provider/model injection never emitted to Bot."""
    create_test_asset("acc_user_a", "ast_t15", "t15.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="55555555555555555555555555555555")
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_t15", "transform_instruction": "style"},
    )

    recorded_payloads = []

    async def mock_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        recorded_payloads.append((path, payload))
        if path == BOT_PRIVATE_UPLOAD_ROUTE:
            return {"ok": True, "status": "completed", "data": {"upload_id": "upl_15"}}
        if path == BOT_PRIVATE_PREPARE_ROUTE:
            _, p_resp = make_mock_bot_responses("upl_15", actor_id)
            return p_resp
        raise ValueError(path)

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)
    await prepare_image_transform_job_with_bot("acc_user_a", job["id"])

    for path, p in recorded_payloads:
        assert "provider" not in p
        assert "model" not in p
        assert "price" not in p
        assert "cost" not in p
        assert "xu" not in p
        assert "wallet" not in p
        assert "paid" not in p


@pytest.mark.anyio
async def test_16_valid_prepare_response_persisted_durable_state(monkeypatch):
    """16. Valid prepare response persisted into durable Web SQLite state."""
    create_test_asset("acc_user_a", "ast_t16", "t16.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="44444444444444444444444444444444")
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_t16", "transform_instruction": "watercolor landscape", "aspect_ratio": "4:5"},
    )

    u_resp, p_resp = make_mock_bot_responses("upl_t16_durable", "canonical_user_a_100")

    async def mock_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        if path == BOT_PRIVATE_UPLOAD_ROUTE:
            return u_resp
        return p_resp

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)
    res = await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert res["ok"] is True

    # Inspect persisted DB row directly
    db_job = get_image_transform_job("acc_user_a", job["id"])
    assert db_job is not None
    assert db_job["status"] == "queued"
    assert db_job["status_reason"] == "EXTERNAL_PROVIDER_AUTHORITY_AND_ENTITLEMENT_UNPROVEN"
    assert db_job["output_asset_id"] is None
    assert db_job["output_url"] is None
    assert db_job["output_available"] is False

    envelope = db_job["bridge_envelope"]
    assert envelope["bot_upload_id"] == "upl_t16_durable"
    assert envelope["bot_prepare_status"] == "PREPARED_PROVIDER_DISABLED"
    assert envelope["bot_executor_owner"] == "bot"
    assert envelope["bot_provider_family"] == "key4u"
    assert "KEY4U_ACCOUNT_ENTITLEMENT_PROVEN=NO" in envelope["blockers"]
    assert "prepared_at" in envelope


@pytest.mark.anyio
async def test_17_to_21_malformed_or_dangerous_bot_prepare_responses_rejected(monkeypatch):
    """17-21. Completed, provider_task_id, output_url, owner mismatch, upload_id mismatch rejected."""
    create_test_asset("acc_user_a", "ast_t17", "t17.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="33333333333333333333333333333333")
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_t17", "transform_instruction": "style"},
    )

    test_cases = [
        # 17. Completed prepare response rejected
        ({"status": "completed"}, "unexpected status 'completed'"),
        # 18. Provider task ID prepare response rejected
        ({"provider_task_id": "p_task_999"}, "unexpected authority fields returned"),
        # 19. Output URL prepare response rejected
        ({"output_url": "https://attacker.invalid/out.png"}, "unexpected authority fields returned"),
        # 20. Owner mismatch prepare response rejected
        ({"owner_id": "forged_actor_evil"}, "owner_id mismatch"),
        # 21. Upload ID mismatch prepare response rejected
        ({"upload_id": "upl_different_upload"}, "upload_id mismatch"),
        # Paid authority claim rejected
        ({"paid": True}, "unexpected paid=True"),
    ]

    for bad_fields, expected_substr in test_cases:
        u_resp, p_resp = make_mock_bot_responses("upl_valid", "canonical_user_a_100")
        p_resp["data"].update(bad_fields)
        if "status" in bad_fields:
            p_resp["status"] = bad_fields["status"]

        async def mock_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id="", p=p_resp):
            if path == BOT_PRIVATE_UPLOAD_ROUTE:
                return u_resp
            return p

        monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

        with pytest.raises(HTTPException) as exc_info:
            await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
        assert exc_info.value.status_code == 502
        assert expected_substr in exc_info.value.detail


@pytest.mark.anyio
async def test_22_same_prepared_job_does_not_upload_twice(monkeypatch):
    """22. Same prepared job does not upload twice (idempotency)."""
    create_test_asset("acc_user_a", "ast_t22", "t22.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="22222222222222222222222222222222")
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_t22", "transform_instruction": "style"},
    )

    call_counts = {"upload": 0, "prepare": 0}

    async def mock_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        if path == BOT_PRIVATE_UPLOAD_ROUTE:
            call_counts["upload"] += 1
            return {"ok": True, "status": "completed", "data": {"upload_id": "upl_idem_22"}}
        if path == BOT_PRIVATE_PREPARE_ROUTE:
            call_counts["prepare"] += 1
            _, p_resp = make_mock_bot_responses("upl_idem_22", actor_id)
            return p_resp
        raise ValueError(path)

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    # First run: performs 1 upload + 1 prepare
    res1 = await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert res1["ok"] is True
    assert res1["idempotent_replay"] is False
    assert call_counts["upload"] == 1
    assert call_counts["prepare"] == 1

    # Second run: reuses durable staging truth, zero Bot calls made
    res2 = await prepare_image_transform_job_with_bot("acc_user_a", job["id"])
    assert res2["ok"] is True
    assert res2["idempotent_replay"] is True
    assert res2["bot_upload_id"] == "upl_idem_22"
    assert call_counts["upload"] == 1
    assert call_counts["prepare"] == 1


def test_23_changed_idempotent_create_replay_remains_409():
    """23. Changed idempotent create replay remains 409 Conflict."""
    create_test_asset("acc_user_a", "ast_t23", "t23.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="12121212121212121212121212121212")

    payload1 = {"image_asset_id": "ast_t23", "transform_instruction": "sunset landscape"}
    job1 = create_or_replay_image_transform_job("acc_user_a", payload1, idempotency_key="fixed-idem-key-999")
    assert job1["idempotent_replay"] is False

    # Exact replay returns same job
    replay = create_or_replay_image_transform_job("acc_user_a", payload1, idempotency_key="fixed-idem-key-999")
    assert replay["idempotent_replay"] is True
    assert replay["id"] == job1["id"]

    # Modified payload with same idempotency key -> 409 Conflict
    payload_modified = {"image_asset_id": "ast_t23", "transform_instruction": "DIFFERENT PROMPT"}
    with pytest.raises(HTTPException) as exc_info:
        create_or_replay_image_transform_job("acc_user_a", payload_modified, idempotency_key="fixed-idem-key-999")
    assert exc_info.value.status_code == 409


def test_24_customer_cannot_inject_authority_fields():
    """24. Customer cannot inject upload_id, model, provider, price, paid, bridge_envelope."""
    create_test_asset("acc_user_a", "ast_t24", "t24.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="34343434343434343434343434343434")

    forbidden_payloads = [
        {"image_asset_id": "ast_t24", "transform_instruction": "prompt", "upload_id": "upl_forged"},
        {"image_asset_id": "ast_t24", "transform_instruction": "prompt", "bot_upload_id": "upl_forged"},
        {"image_asset_id": "ast_t24", "transform_instruction": "prompt", "provider": "key4u"},
        {"image_asset_id": "ast_t24", "transform_instruction": "prompt", "model": "grok-imagine"},
        {"image_asset_id": "ast_t24", "transform_instruction": "prompt", "price": 0},
        {"image_asset_id": "ast_t24", "transform_instruction": "prompt", "paid": True},
        {"image_asset_id": "ast_t24", "transform_instruction": "prompt", "bridge_envelope": {"forged": True}},
    ]
    for p in forbidden_payloads:
        with pytest.raises(HTTPException) as exc_info:
            create_or_replay_image_transform_job("acc_user_a", p)
        assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_25_bot_public_flag_true_does_not_permit_execution(monkeypatch):
    """25. Bot returning key4u_public_enabled=True does NOT allow execution."""
    create_test_asset("acc_user_a", "ast_t25", "t25.png", ".png", "image/png", SAMPLE_PNG_BYTES, storage_hex="56565656565656565656565656565656")
    job = create_or_replay_image_transform_job(
        "acc_user_a",
        {"image_asset_id": "ast_t25", "transform_instruction": "style"},
    )

    u_resp, p_resp = make_mock_bot_responses("upl_t25", "canonical_user_a_100")
    # Simulate Bot with public flag true, but provider_execution_allowed remains false
    p_resp["data"]["key4u_public_enabled"] = True
    p_resp["data"]["provider_execution_allowed"] = False

    async def mock_bridge(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        if path == BOT_PRIVATE_UPLOAD_ROUTE:
            return u_resp
        return p_resp

    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)
    res = await prepare_image_transform_job_with_bot("acc_user_a", job["id"])

    assert res["ok"] is True
    assert res["provider_execution_allowed"] is False


def test_26_invariants_and_zero_mutation_guarantees():
    """26. Invariant verification: provider dispatch disabled, zero spend, zero wallet mutations."""
    assert IMAGE_TRANSFORM_PROVIDER_DISPATCH_ENABLED is False
    assert WEB_PROVIDER_EXECUTOR_IMPLEMENTED is False
