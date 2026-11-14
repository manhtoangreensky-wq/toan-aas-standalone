"""Completion follows canonical audio availability; all data and transport owned."""
from __future__ import annotations

import asyncio
import importlib
import uuid
from typing import Any

import pytest

import copyfast_db as db
import copyfast_voice_tts_job_bridge as tts


@pytest.fixture
def owned_tts(tmp_path, monkeypatch):
    # Earlier auth tests reload this module after collection. Match the
    # production function's dynamic import instead of patching a stale object.
    bridge = importlib.import_module("copyfast_bridge")
    monkeypatch.setattr(db, "session_database_path", lambda: str(tmp_path / "tts.db"))
    tts.ensure_voice_tts_schema()
    owner = "owned-" + uuid.uuid4().hex
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO web_accounts(id,email,password_hash,created_at,updated_at) VALUES(?,?,?,?,?)",
            (owner, owner + "@example.invalid", "not-for-login", db.utc_now(), db.utc_now()),
        )
    account = {"id": owner, "canonical_user_id": "owned-canonical"}
    job = tts.create_or_replay_voice_tts_job(
        account_id=owner,
        payload={"script": "Nội dung riêng để kiểm tra", "voice_source": "default", "default_voice_gender": "female"},
    )
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(bridge, "bridge_configured", lambda: True)

    def install(confirm_reply=None, read_reply=None, concurrent_completion=False):
        async def transport(method: str, path: str, **kwargs: Any):
            calls.append((method, path))
            assert kwargs["actor_id"] == account["canonical_user_id"]
            assert kwargs["owner_id"] == account["canonical_user_id"]
            if method == "POST" and path == "/internal/v1/web-voice-tts/jobs":
                return {"ok": True, "job": {"job_id": "runtime-" + job["id"], "status": "prepared", "quote_xu": 0}}
            if method == "POST" and path == f"/internal/v1/web-voice-tts/jobs/{job['id']}/confirm":
                assert confirm_reply is not None, "Unexpected second execution confirmation"
                return {"ok": True, "job": {"charged_xu": 0, **confirm_reply}}
            if method == "GET" and path == f"/internal/v1/web-voice-tts/jobs/{job['id']}":
                assert read_reply is not None, "Valid completed output must not be re-read"
                if concurrent_completion:
                    with db.transaction() as connection:
                        connection.execute(
                            "UPDATE web_voice_tts_jobs SET status='completed',output_url=?,completed_at=? WHERE id=?",
                            (f"/api/v1/features/voice_tts/jobs/{job['id']}/artifact", db.utc_now(), job["id"]),
                        )
                return {"ok": True, "job": {"charged_xu": 0, **read_reply}}
            raise AssertionError("Unexpected transport route: " + path)
        monkeypatch.setattr(bridge, "bridge_request", transport)

    def raw():
        with db.read_transaction() as connection:
            return connection.execute(
                "SELECT status,charged_xu,quote_xu,output_url,completed_at FROM web_voice_tts_jobs WHERE id=?",
                (job["id"],),
            ).fetchone()
    return account, job, calls, install, raw


@pytest.mark.parametrize("reply", [
    {"status": "prepared", "has_artifact": False},
    {"status": "queued", "has_artifact": False},
    {"status": "processing", "has_artifact": False},
    {"status": "completed", "has_artifact": False},
    {"status": "completed"},
    {"status": "completed", "has_artifact": "false"},
    {"status": "completed", "has_artifact": 1},
    {"status": "completed", "has_artifact": []},
])
def test_confirm_cannot_complete_without_strict_canonical_audio_proof(owned_tts, reply):
    account, job, calls, install, raw = owned_tts
    install(confirm_reply=reply, read_reply={"status": "completed", "has_artifact": True})
    confirmed = asyncio.run(tts.confirm_voice_tts_job(job["id"], account=account))
    assert confirmed["status"] == "processing"
    assert confirmed["has_artifact"] is False
    assert raw() == ("processing", 0, 0, None, None)
    reconciled = asyncio.run(tts.reconcile_voice_tts_job_status(job["id"], account=account))
    assert reconciled["status"] == "completed" and reconciled["has_artifact"] is True
    assert raw()[3] == f"/api/v1/features/voice_tts/jobs/{job['id']}/artifact"
    assert len([call for call in calls if call[0] == "GET"]) == 1
    assert len([call for call in calls if call[1].endswith("/confirm")]) == 1


@pytest.mark.parametrize("artifact", [False, None, "false", 1, []])
def test_read_without_strict_audio_proof_stays_pending_without_financial_change(owned_tts, artifact):
    account, job, calls, install, raw = owned_tts
    install(read_reply={"status": "completed", "has_artifact": artifact})
    result = asyncio.run(tts.reconcile_voice_tts_job_status(job["id"], account=account))
    assert result["status"] == "processing" and result["has_artifact"] is False
    assert raw() == ("processing", 0, 0, None, None)
    assert calls == [("GET", f"/internal/v1/web-voice-tts/jobs/{job['id']}")]


@pytest.mark.parametrize("reply,wanted", [
    ({"status": "processing", "has_artifact": False}, "processing"),
    ({"status": "completed", "has_artifact": False}, "processing"),
    ({"status": "failed", "has_artifact": False}, "failed"),
    ({"status": "error", "has_artifact": False}, "failed"),
    ({"status": "completed", "has_artifact": True}, "completed"),
])
def test_read_repairs_old_completed_record_missing_audio(owned_tts, reply, wanted):
    account, job, calls, install, raw = owned_tts
    with db.transaction() as connection:
        connection.execute("UPDATE web_voice_tts_jobs SET status='completed',output_url=NULL WHERE id=?", (job["id"],))
    install(read_reply=reply)
    result = asyncio.run(tts.reconcile_voice_tts_job_status(job["id"], account=account))
    assert result["status"] == wanted
    assert result["has_artifact"] is (wanted == "completed")
    assert raw()[1:3] == (0, 0)
    assert len(calls) == 1 and calls[0][0] == "GET"


def test_valid_completed_audio_never_reads_or_reconfirms(owned_tts):
    account, job, calls, install, raw = owned_tts
    install(confirm_reply={"status": "completed", "has_artifact": True})
    result = asyncio.run(tts.confirm_voice_tts_job(job["id"], account=account))
    assert result["status"] == "completed" and result["has_artifact"] is True
    saved, previous_calls = raw(), list(calls)
    assert asyncio.run(tts.confirm_voice_tts_job(job["id"], account=account))["has_artifact"] is True
    assert asyncio.run(tts.reconcile_voice_tts_job_status(job["id"], account=account))["has_artifact"] is True
    assert raw() == saved and calls == previous_calls


@pytest.mark.parametrize("reply", [
    {"status": "processing", "has_artifact": False},
    {"status": "failed", "has_artifact": False},
    {"status": "error", "has_artifact": False},
    {"status": "completed", "has_artifact": False},
])
def test_delayed_nonfinal_read_cannot_downgrade_concurrently_completed_audio(owned_tts, reply):
    account, job, calls, install, raw = owned_tts
    install(read_reply=reply, concurrent_completion=True)
    result = asyncio.run(tts.reconcile_voice_tts_job_status(job["id"], account=account))
    assert result["status"] == "completed" and result["has_artifact"] is True
    assert raw()[1:3] == (0, 0)
    assert len(calls) == 1 and calls[0][0] == "GET"
