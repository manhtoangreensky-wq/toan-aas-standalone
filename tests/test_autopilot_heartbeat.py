"""Focused contracts for the Web-only missed-Cron heartbeat follow-up.

These tests use only a temporary standalone Web SQLite database and signed
internal tick requests. They never invoke a Bot, bridge, provider, wallet,
PayOS, job, deployment or notification adapter.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import sqlite3
import sys
import uuid

from fastapi.testclient import TestClient

from copyfast_autopilot_protocol import PROTOCOL_VERSION, canonical_json, sign_tick


TICK_SECRET = "t" * 32
INCIDENT_SECRET = "i" * 32
MODULES = (
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_projects", "copyfast_assets", "copyfast_project_packages", "copyfast_document_operations",
    "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio", "copyfast_document_workspace",
    "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard", "copyfast_memory",
    "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support", "copyfast_reliability",
    "copyfast_autopilot",
)


def make_client(tmp_path, monkeypatch, *, expected_seconds: str | None = "300") -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "operations-heartbeat-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "operations-heartbeat-test-session-secret")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_HEARTBEAT_FOLLOWUP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_SECRET", TICK_SECRET)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_INCIDENT_SECRET", INCIDENT_SECRET)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_KEY_ID", "primary")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TOPOLOGY", "sqlite_single_replica")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_HEARTBEAT_GRACE_SECONDS", "0")
    if expected_seconds is None:
        monkeypatch.delenv("WEBAPP_AUTOPILOT_HEARTBEAT_EXPECTED_SECONDS", raising=False)
    else:
        monkeypatch.setenv("WEBAPP_AUTOPILOT_HEARTBEAT_EXPECTED_SECONDS", expected_seconds)
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def tick_body(timestamp: str | None = None) -> tuple[bytes, str]:
    timestamp = timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
    return canonical_json({"protocol_version": PROTOCOL_VERSION, "trigger": "railway_cron", "requested_at": timestamp}), timestamp


def tick_headers(*, body: bytes, timestamp: str, nonce: str) -> dict[str, str]:
    request_id = str(uuid.uuid4())
    return {
        "Content-Type": "application/json",
        "X-Ops-Timestamp": timestamp,
        "X-Ops-Nonce": nonce,
        "X-Ops-Request-Id": request_id,
        "X-Ops-Key-Id": "primary",
        "X-Ops-Signature": sign_tick(
            secret=TICK_SECRET, timestamp=timestamp, nonce=nonce, request_id=request_id, key_id="primary", body=body,
        ),
    }


def seed_completed_run(db_path: Path, *, started_at: str, request_id: str | None = None) -> str:
    run_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_ops_runs
               (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                action_count, triaged_case_count, incident_count, deadline_at, started_at, finished_at,
                error_code, receipt_json)
               VALUES (?, ?, 'railway_cron', ?, 'completed', 1, 1, 'heartbeat-test', 0, 0, 0, ?, ?, ?, NULL, '{}')""",
            (run_id, request_id or str(uuid.uuid4()), started_at[:16], started_at, started_at, started_at),
        )
        conn.commit()
    return run_id


def test_first_valid_tick_never_creates_a_heartbeat_finding(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-heartbeat-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        # A feature can be enabled against a database that already contains
        # old completed scheduler rows. They are history, not an implicit
        # baseline for this newly armed optional playbook.
        old = (datetime.now(timezone.utc) - timedelta(minutes=11)).replace(microsecond=0).isoformat(timespec="seconds")
        historical_run_id = seed_completed_run(db_path, started_at=old)
        body, timestamp = tick_body()
        response = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="A" * 24),
            content=body,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["data"]["scheduler_heartbeat_state"] == "baseline_pending"
        assert payload["data"]["scheduler_heartbeat_late_count"] == 0
        for key in ("bot_called", "provider_called", "wallet_mutated", "payment_mutated", "job_retried", "deployment_changed"):
            assert payload["data"][key] is False
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM web_ops_incidents WHERE kind='scheduler_heartbeat_late'"
        ).fetchone() == (0,)
        baseline = conn.execute(
            """SELECT config_fingerprint, process_epoch, last_completed_run_id, last_completed_at
               FROM web_ops_heartbeat_baselines WHERE scope='railway_cron'"""
        ).fetchone()
        assert baseline is not None
        assert baseline[0] and baseline[1] and baseline[3]
        assert baseline[2] != historical_run_id
        assert conn.execute(
            "SELECT state FROM web_ops_runs WHERE id=?", (baseline[2],)
        ).fetchone() == ("completed",)


def test_late_completed_gap_creates_one_deduped_local_followup_only(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-heartbeat-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        # First successful tick arms its own baseline and cannot create a
        # finding. Make that exact baseline old to model one missed interval.
        body, timestamp = tick_body()
        armed = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="B" * 24),
            content=body,
        )
        assert armed.status_code == 200 and armed.json()["status"] == "completed"
        assert armed.json()["data"]["scheduler_heartbeat_state"] == "baseline_pending"
        with sqlite3.connect(db_path) as conn:
            baseline_run_id, baseline_completed_at = conn.execute(
                """SELECT last_completed_run_id, last_completed_at
                   FROM web_ops_heartbeat_baselines WHERE scope='railway_cron'"""
            ).fetchone()
            old = (datetime.now(timezone.utc) - timedelta(minutes=11)).replace(microsecond=0).isoformat(timespec="seconds")
            conn.execute(
                "UPDATE web_ops_runs SET started_at=?, finished_at=? WHERE id=?",
                (old, old, baseline_run_id),
            )
            conn.commit()
        body, timestamp = tick_body()
        late = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="C" * 24),
            content=body,
        )
        assert late.status_code == 200 and late.json()["status"] == "completed"
        assert late.json()["data"]["scheduler_heartbeat_state"] == "late"
        assert late.json()["data"]["scheduler_heartbeat_late_count"] == 1
        # A stale baseline restored by a retry/race sees the same opaque gap
        # marker but cannot append a second observation or mutate the same
        # incident again.
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """UPDATE web_ops_heartbeat_baselines
                   SET last_completed_run_id=?, last_completed_at=?
                   WHERE scope='railway_cron'""",
                (baseline_run_id, baseline_completed_at),
            )
            conn.commit()
        body, timestamp = tick_body()
        deduped = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="D" * 24),
            content=body,
        )
        assert deduped.status_code == 200 and deduped.json()["status"] == "completed"
        assert deduped.json()["data"]["scheduler_heartbeat_state"] == "late"
        assert deduped.json()["data"]["scheduler_heartbeat_late_count"] == 0
        body, timestamp = tick_body()
        on_time = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="E" * 24),
            content=body,
        )
        assert on_time.status_code == 200 and on_time.json()["status"] == "completed"
        assert on_time.json()["data"]["scheduler_heartbeat_state"] == "within_window"
        assert on_time.json()["data"]["scheduler_heartbeat_late_count"] == 0
    with sqlite3.connect(db_path) as conn:
        incident = conn.execute(
            """SELECT scope_kind, account_id, support_case_id, state, observation_count
               FROM web_ops_incidents WHERE kind='scheduler_heartbeat_late'"""
        ).fetchone()
        assert incident == ("scheduler", None, None, "open", 1)
        assert conn.execute(
            "SELECT COUNT(*) FROM web_ops_incident_observations WHERE observation='scheduler_heartbeat_late'"
        ).fetchone() == (1,)
        assert conn.execute("SELECT COUNT(*) FROM web_support_cases").fetchone() == (0,)
        assert conn.execute("SELECT COUNT(*) FROM web_ops_approvals").fetchone() == (0,)


def test_redeploy_rearms_heartbeat_before_it_can_assess_a_gap(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-heartbeat-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        body, timestamp = tick_body()
        first = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="F" * 24),
            content=body,
        )
        assert first.status_code == 200 and first.json()["status"] == "completed"
        assert first.json()["data"]["scheduler_heartbeat_state"] == "baseline_pending"
    with make_client(tmp_path, monkeypatch) as client:
        body, timestamp = tick_body()
        rearmed = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="G" * 24),
            content=body,
        )
        assert rearmed.status_code == 200 and rearmed.json()["status"] == "completed"
        assert rearmed.json()["data"]["scheduler_heartbeat_state"] == "baseline_pending"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM web_ops_incidents WHERE kind='scheduler_heartbeat_late'"
        ).fetchone() == (0,)


def test_heartbeat_config_and_active_lease_fail_closed_without_followup(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-heartbeat-test.db"
    with make_client(tmp_path, monkeypatch, expected_seconds=None) as client:
        body, timestamp = tick_body()
        guarded = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="D" * 24),
            content=body,
        )
        assert guarded.status_code == 200 and guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["guarded_code"] == "OPS_HEARTBEAT_CONFIG_UNVERIFIED"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_ops_incidents WHERE kind='scheduler_heartbeat_late'").fetchone() == (0,)

    with make_client(tmp_path, monkeypatch) as client:
        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        now = now_dt.isoformat(timespec="seconds")
        owner_run_id = seed_completed_run(db_path, started_at=(now_dt - timedelta(minutes=11)).isoformat(timespec="seconds"))
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_ops_leases (name, owner_run_id, fence_token, acquired_at, expires_at, updated_at)
                   VALUES ('operations_autopilot_tick', ?, 7, ?, ?, ?)""",
                (owner_run_id, now, (now_dt + timedelta(minutes=10)).isoformat(timespec="seconds"), now),
            )
            conn.commit()
        body, timestamp = tick_body(now)
        held = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="E" * 24),
            content=body,
        )
        assert held.status_code == 200 and held.json()["status"] == "guarded"
        assert held.json()["data"]["guarded_code"] == "OPS_TICK_LEASE_HELD"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_ops_incidents WHERE kind='scheduler_heartbeat_late'").fetchone() == (0,)


def test_heartbeat_source_has_no_external_execution_imports():
    source = (Path(__file__).resolve().parents[1] / "copyfast_autopilot.py").read_text(encoding="utf-8")
    for forbidden in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge",
        "import PayOS", "from PayOS", "import requests", "import httpx", "import urllib",
        "import wallet", "from wallet", "import provider", "from provider",
    ):
        assert forbidden not in source
    customer_status = source.split('@router.get("/api/v1/operations/status")', 1)[1].split(
        '@router.get("/api/v1/operations/incidents")', 1
    )[0]
    admin_summary = source.split('@router.get("/api/v1/operations/admin/summary")', 1)[1].split(
        '@router.get("/api/v1/operations/admin/runs")', 1
    )[0]
    assert "scheduler_heartbeat" not in customer_status
    assert "scheduler_heartbeat" in admin_summary
