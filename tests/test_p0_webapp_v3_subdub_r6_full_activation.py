"""Tests for SubDub R6 Full Activation (WEBAPP_R6).

Task: WEBAPP_SUBDUB_R6_FULL_ACTIVATION_EXECUTION_R2
Repo: manhtoangreensky-wq/toan-aas-standalone
Tracker: #515

Enforces:
1. Empty allowlist blocks runtime.
2. SubDub allowlist enables only canonical SubDub path.
3. Provider flag false still blocks (fail-closed).
4. Adapter flag false still blocks (fail-closed).
5. Missing adapter key still blocks (fail-closed).
6. Invalid bridge configuration still blocks (fail-closed).
7. Unrelated features remain blocked.
8. Duplicate identical request remains idempotent.
9. Payload mismatch remains HTTP 409 conflict.
10. Activation alone cannot fabricate completed/output state (0 fake outputs, 0 fake running).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi import HTTPException

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

import copyfast_api as api
from copyfast_db import ensure_copyfast_schema, transaction
import copyfast_subdub_job_bridge as bridge

TEST_ACCOUNT_ID = "test-r6-activation-user"


@pytest.fixture(autouse=True)
def setup_db_and_clean(monkeypatch):
    """Ensure database schema is up to date and clean test data."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-p0-subdub-r6-activation")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "subdub,video_dub,subtitle_create,subtitle_translate")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "https://tg.toanaas.vn")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "valid-test-token-32-chars-long-abc")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "valid-test-secret-32-chars-long-xyz")
    ensure_copyfast_schema()

    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs WHERE account_id LIKE 'test-r6-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r6-%'")
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at)
            VALUES (?, 'r6@test.local', 'hash_r6', '2026-09-29T00:00:00Z', '2026-09-29T00:00:00Z')
            """,
            (TEST_ACCOUNT_ID,),
        )
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_subdub_jobs WHERE account_id LIKE 'test-r6-%'")
        conn.execute("DELETE FROM web_accounts WHERE id LIKE 'test-r6-%'")


def test_01_empty_allowlist_blocks_runtime(monkeypatch):
    """Prove empty allowlist blocks SubDub runtime execution."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset())
    assert not api._web_feature_runtime_active("subdub")


def test_02_subdub_allowlist_enables_only_canonical_subdub_path(monkeypatch):
    """Prove subdub allowlist enables canonical SubDub path under complete configuration."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub"}))
    assert api._web_feature_runtime_active("subdub")
    # Lane aliases also resolve through subdub authority
    assert api._web_feature_runtime_active("video_dub")
    assert api._web_feature_runtime_active("subtitle_create")
    assert api._web_feature_runtime_active("subtitle_translate")


def test_03_provider_flag_false_still_blocks(monkeypatch):
    """Prove provider calls flag false still fails closed even with subdub in allowlist."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub"}))
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    assert not api._web_feature_runtime_active("subdub")


def test_04_adapter_flag_false_still_blocks(monkeypatch):
    """Prove feature job adapter flag false still fails closed."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub"}))
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTER_ENABLED", "false")
    assert not api._web_feature_runtime_active("subdub")


def test_05_missing_adapter_key_still_blocks(monkeypatch):
    """Prove missing subdub in WEBAPP_FEATURE_JOB_ADAPTERS still fails closed."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub"}))
    monkeypatch.setenv("WEBAPP_FEATURE_JOB_ADAPTERS", "other_feature_only")
    assert not api._web_feature_runtime_active("subdub")


def test_06_invalid_bridge_configuration_still_blocks(monkeypatch):
    """Prove invalid/missing bridge configuration blocks runtime execution."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub"}))
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "")
    assert not api._web_feature_runtime_active("subdub")


def test_07_unrelated_features_remain_blocked(monkeypatch):
    """Prove unrelated features remain strictly blocked."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub"}))
    assert not api._web_feature_runtime_active("video_ai_prompt")
    assert not api._web_feature_runtime_active("product_video")
    assert not api._web_feature_runtime_active("storyboard_prompt")
    assert not api._web_feature_runtime_active("image_studio")


def test_08_duplicate_identical_request_remains_idempotent():
    """Prove duplicate identical requests return idempotent replay."""
    payload = {
        "mode": "subtitle_create",
        "upload_id": "upl_r6_idempotent_001",
        "output_format": "burn",
    }
    job1 = bridge.create_or_replay_subdub_job(
        account_id=TEST_ACCOUNT_ID,
        request_id="req_r6_idem_001",
        payload=payload,
    )
    assert job1["idempotent_replay"] is False

    job2 = bridge.create_or_replay_subdub_job(
        account_id=TEST_ACCOUNT_ID,
        request_id="req_r6_idem_001",
        payload=payload,
    )
    assert job2["idempotent_replay"] is True
    assert job2["id"] == job1["id"]
    assert job2["status"] == "queued"


def test_09_payload_mismatch_remains_409():
    """Prove payload mismatch on same request_id raises HTTP 409."""
    payload1 = {
        "mode": "subtitle_create",
        "upload_id": "upl_r6_conflict_001",
        "output_format": "burn",
    }
    payload2 = {
        "mode": "subtitle_translate",
        "upload_id": "upl_r6_conflict_001",
        "target_language": "en",
        "output_format": "burn",
    }
    bridge.create_or_replay_subdub_job(
        account_id=TEST_ACCOUNT_ID,
        request_id="req_r6_conflict_001",
        payload=payload1,
    )
    with pytest.raises(HTTPException) as exc:
        bridge.create_or_replay_subdub_job(
            account_id=TEST_ACCOUNT_ID,
            request_id="req_r6_conflict_001",
            payload=payload2,
        )
    assert exc.value.status_code == 409


def test_10_activation_alone_cannot_fabricate_output(monkeypatch):
    """Prove activation alone cannot fabricate running/completed state or output artifacts."""
    monkeypatch.setattr(api, "WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES", frozenset({"subdub"}))
    payload = {
        "mode": "dub",
        "upload_id": "upl_r6_truth_001",
        "target_language": "vi",
        "voice_profile_id": "voice_std_01",
    }
    job = bridge.create_or_replay_subdub_job(
        account_id=TEST_ACCOUNT_ID,
        request_id="req_r6_truth_001",
        payload=payload,
    )
    assert job["status"] == "queued"
    assert job["status_reason"] == "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"
    assert job["output"] is None
    assert job["output_url"] is None
    assert job["output_available"] is False
    assert job["download_ready"] is False
    assert job["delivery_ready"] is False
