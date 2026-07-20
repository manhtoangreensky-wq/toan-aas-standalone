"""Focused contracts for the local, read-only Admin Automation Monitor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import uuid

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_notification_center", "copyfast_notification_protocol", "copyfast_admin_automation",
]


def make_client(tmp_path, monkeypatch, *, erp: bool = True, center: bool = True, automation: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "automation-monitor.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "automation-monitor-session-secret")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true" if erp else "false")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_CENTER_ENABLED", "true" if center else "false")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_AUTOMATION_ENABLED", "true" if automation else "false")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TOPOLOGY", "sqlite_single_replica")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH", "RAILWAY_REPLICA_COUNT",
        "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT", "WEBAPP_NOTIFICATION_REQUIRE_REPLICA_ATTESTATION",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, db_path: Path, *, email: str, admin: bool) -> None:
    created = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Automation Admin"},
    )
    assert created.status_code == 200
    if admin:
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", (email,))
            conn.commit()
    signed = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed.status_code == 200


def seed_run(
    db_path: Path,
    *,
    state: str = "completed",
    actions: object = 1,
    candidates: object = 2,
    started_at: str | None = None,
    finished_at: str | None = None,
    marker: str = "secret-marker",
) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    started = started_at or now.isoformat()
    finished = finished_at if finished_at is not None else (now + timedelta(seconds=1)).isoformat()
    if state == "started" and finished_at is None:
        finished = None
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_notification_runs
               (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                action_count, candidate_count, deadline_at, started_at, finished_at, error_code, receipt_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                f"request-{marker}-{uuid.uuid4()}",
                f"trigger-{marker}",
                f"slot-{marker}",
                state,
                88,
                99,
                f"input-{marker}",
                actions,
                candidates,
                now.isoformat(),
                started,
                finished,
                f"error-{marker}",
                json.dumps({"receipt": marker, "nonce": f"nonce-{marker}", "account": "private@example.com"}),
            ),
        )
        conn.commit()


def test_monitor_requires_signed_local_admin_and_never_exposes_sensitive_run_columns(tmp_path, monkeypatch):
    db_path = tmp_path / "automation-monitor.db"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, db_path, email="ordinary@example.com", admin=False)
        assert client.get("/api/v1/admin/automation/summary").status_code == 403

    with make_client(tmp_path, monkeypatch) as client:
        login(client, db_path, email="admin@example.com", admin=True)
        seed_run(db_path, marker="TOP-SECRET-NONCE-LEASE-REQUEST")
        summary = client.get("/api/v1/admin/automation/summary")
        runs = client.get("/api/v1/admin/automation/runs?limit=25&offset=0")

    assert summary.status_code == 200 and runs.status_code == 200
    assert summary.json()["status"] == "read_only"
    payload = json.dumps({
        "summary": {
            "scheduler": summary.json()["data"]["scheduler"],
            "latest_run": summary.json()["data"]["latest_run"],
            "run_counts": summary.json()["data"]["run_counts"],
        },
        "runs": runs.json()["data"]["items"],
    })
    for forbidden in (
        "TOP-SECRET-NONCE-LEASE-REQUEST", "request-", "trigger-", "slot-", "input-", "error-",
        "receipt_json", "fence_token", "nonce", "private@example.com", "deadline_at",
    ):
        assert forbidden not in payload
    data = summary.json()["data"]
    assert set(data) == {"source", "policy_version", "read_only", "boundaries", "scheduler", "latest_run", "run_counts", "integrity_guarded"}
    assert set(data["latest_run"]) == {"state", "action_count", "candidate_count", "started_at", "finished_at"}
    assert data["scheduler"]["state"] == "ready"
    assert data["integrity_guarded"] is False
    assert runs.json()["data"]["items"] and set(runs.json()["data"]["items"][0]) == set(data["latest_run"])


def test_monitor_paginates_bounded_redacted_receipts_and_rejects_invalid_query(tmp_path, monkeypatch):
    db_path = tmp_path / "automation-monitor.db"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, db_path, email="page-admin@example.com", admin=True)
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for index in range(27):
            stamp = (base + timedelta(minutes=index)).isoformat()
            seed_run(db_path, started_at=stamp, finished_at=(base + timedelta(minutes=index, seconds=1)).isoformat(), marker=f"page-{index}")
        first = client.get("/api/v1/admin/automation/runs?limit=25&offset=0")
        second = client.get("/api/v1/admin/automation/runs?limit=25&offset=25")
        invalid_limit = client.get("/api/v1/admin/automation/runs?limit=51&offset=0")
        invalid_offset = client.get("/api/v1/admin/automation/runs?limit=25&offset=10001")

    assert first.status_code == 200 and second.status_code == 200
    first_data, second_data = first.json()["data"], second.json()["data"]
    assert first_data["returned"] == 25 and first_data["has_more"] is True and first_data["next_offset"] == 25
    assert second_data["returned"] == 2 and second_data["has_more"] is False and second_data["next_offset"] is None
    first_times = {item["started_at"] for item in first_data["items"]}
    assert not first_times.intersection({item["started_at"] for item in second_data["items"]})
    assert invalid_limit.status_code == 422 and invalid_offset.status_code == 422


def test_monitor_erp_and_center_guards_do_not_open_a_receipt_read(tmp_path, monkeypatch):
    for erp, center, expected_code in ((False, True, "WEBAPP_ADMIN_ERP_DISABLED"), (True, False, "ADMIN_AUTOMATION_MONITOR_GUARDED")):
        db_path = tmp_path / "automation-monitor.db"
        with make_client(tmp_path, monkeypatch, erp=erp, center=center) as client:
            login(client, db_path, email=f"guard-{erp}-{center}@example.com".lower(), admin=True)
            monitor = importlib.import_module("copyfast_admin_automation")
            called = {"read": False}

            def forbidden_read():
                called["read"] = True
                raise AssertionError("guarded monitor must not query receipts")

            monkeypatch.setattr(monitor, "read_transaction", forbidden_read)
            summary = client.get("/api/v1/admin/automation/summary")
            runs = client.get("/api/v1/admin/automation/runs?limit=25&offset=0")
        assert summary.status_code == 200 and runs.status_code == 200
        assert summary.json()["status"] == runs.json()["status"] == "guarded"
        assert summary.json()["error_code"] == runs.json()["error_code"] == expected_code
        assert summary.json()["data"]["latest_run"] is None and summary.json()["data"]["run_counts"] is None
        assert runs.json()["data"]["items"] == [] and called["read"] is False


def test_automation_disabled_can_report_history_but_malformed_receipts_fail_closed(tmp_path, monkeypatch):
    db_path = tmp_path / "automation-monitor.db"
    with make_client(tmp_path, monkeypatch, automation=False) as client:
        login(client, db_path, email="history-admin@example.com", admin=True)
        seed_run(db_path, state="completed", marker="history-marker")
        history = client.get("/api/v1/admin/automation/summary")
        assert history.status_code == 200
        assert history.json()["status"] == "guarded"
        assert history.json()["data"]["scheduler"]["state"] == "automation_disabled"
        assert history.json()["data"]["latest_run"]["state"] == "completed"
        seed_run(db_path, state="raw-private-state", actions=999, marker="MALFORMED-PRIVATE")
        guarded = client.get("/api/v1/admin/automation/summary")
        guarded_runs = client.get("/api/v1/admin/automation/runs?limit=25&offset=0")

    assert guarded.status_code == 200 and guarded.json()["status"] == "guarded"
    assert guarded.json()["error_code"] == "ADMIN_AUTOMATION_MONITOR_DATA_GUARDED"
    combined = json.dumps({"summary": guarded.json(), "runs": guarded_runs.json()})
    assert "MALFORMED-PRIVATE" not in combined and "raw-private-state" not in combined
    assert all(item["state"] in {"started", "completed", "failed", "guarded"} for item in guarded_runs.json()["data"]["items"])


def test_monitor_rejects_fractional_scheduler_counters_without_rounding(tmp_path, monkeypatch):
    db_path = tmp_path / "automation-monitor.db"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, db_path, email="fractional-admin@example.com", admin=True)
        started = datetime(2098, 1, 1, tzinfo=timezone.utc).isoformat()
        finished = datetime(2098, 1, 1, 0, 0, 1, tzinfo=timezone.utc).isoformat()
        seed_run(
            db_path,
            actions=1.5,
            candidates=2.5,
            started_at=started,
            finished_at=finished,
            marker="FRACTIONAL-PRIVATE",
        )
        # A full first page of valid newest receipts must not hide an older
        # fractional counter inside either aggregate or direct page APIs.
        newest_base = datetime(2099, 1, 1, tzinfo=timezone.utc)
        for index in range(26):
            stamp = newest_base + timedelta(minutes=index)
            seed_run(
                db_path,
                started_at=stamp.isoformat(),
                finished_at=(stamp + timedelta(seconds=1)).isoformat(),
                marker=f"VALID-NEWEST-{index}",
            )
        summary = client.get("/api/v1/admin/automation/summary")
        runs = client.get("/api/v1/admin/automation/runs?limit=25&offset=0")

    assert summary.status_code == 200 and runs.status_code == 200
    assert summary.json()["status"] == runs.json()["status"] == "guarded"
    assert summary.json()["error_code"] == runs.json()["error_code"] == "ADMIN_AUTOMATION_MONITOR_DATA_GUARDED"
    assert summary.json()["data"]["latest_run"]["state"] == "completed"
    assert summary.json()["data"]["integrity_guarded"] is True
    assert len(runs.json()["data"]["items"]) == 25
    assert runs.json()["data"]["items"][0]["state"] == "completed"
    assert "FRACTIONAL-PRIVATE" not in json.dumps({"summary": summary.json(), "runs": runs.json()})


def test_monitor_rejects_old_semantically_invalid_timestamp_across_first_page(tmp_path, monkeypatch):
    db_path = tmp_path / "automation-monitor.db"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, db_path, email="timestamp-admin@example.com", admin=True)
        # This looks like ISO text but datetime.fromisoformat correctly rejects
        # month 99. It is older than a whole visible first page.
        seed_run(
            db_path,
            started_at="2097-99-01T00:00:00+00:00",
            finished_at="2097-99-01T00:00:01+00:00",
            marker="INVALID-TIMESTAMP-PRIVATE",
        )
        newest_base = datetime(2099, 1, 1, tzinfo=timezone.utc)
        for index in range(26):
            stamp = newest_base + timedelta(minutes=index)
            seed_run(
                db_path,
                started_at=stamp.isoformat(),
                finished_at=(stamp + timedelta(seconds=1)).isoformat(),
                marker=f"VALID-TIMESTAMP-PAGE-{index}",
            )
        summary = client.get("/api/v1/admin/automation/summary")
        runs = client.get("/api/v1/admin/automation/runs?limit=25&offset=0")

    assert summary.status_code == 200 and runs.status_code == 200
    assert summary.json()["status"] == runs.json()["status"] == "guarded"
    assert summary.json()["error_code"] == runs.json()["error_code"] == "ADMIN_AUTOMATION_MONITOR_DATA_GUARDED"
    assert summary.json()["data"]["integrity_guarded"] is True
    assert len(runs.json()["data"]["items"]) == 25
    assert "INVALID-TIMESTAMP-PRIVATE" not in json.dumps({"summary": summary.json(), "runs": runs.json()})


def test_monitor_source_has_no_tick_bridge_or_write_route() -> None:
    source = (Path(__file__).parents[1] / "copyfast_admin_automation.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/api/v1/admin/automation"' in source
    assert '@router.get("/summary")' in source and '@router.get("/runs")' in source
    for forbidden in ("copyfast_bridge", "@router.post", "@router.patch", "@router.delete", "sign_tick(", "SELECT *"):
        assert forbidden not in source
    for forbidden_table in (
        "web_notification_nonces", "web_notification_leases", "web_notification_items",
        "web_notification_run_steps", "web_notification_events", "web_notification_dedupes",
    ):
        assert forbidden_table not in source
