"""High-risk contracts for private Web Inbox Automation.

The suite never sends a real notification or invokes Bot/provider/payment
authority.  It proves signed scheduler replay/lease/dedupe and signed-owner
inbox state boundaries using an isolated temporary SQLite database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import json
import sqlite3
import sys
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from copyfast_notification_center import MAX_ACTIONS_PER_RUN, MAX_CANDIDATES_PER_RUN
from copyfast_notification_protocol import PROTOCOL_VERSION, canonical_json, sign_tick


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_projects", "copyfast_assets", "copyfast_project_packages", "copyfast_document_operations",
    "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio", "copyfast_document_workspace",
    "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard", "copyfast_memory",
    "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support", "copyfast_autopilot",
    "copyfast_notification_center", "copyfast_notification_protocol",
]

TICK_SECRET = "n" * 32


def make_client(tmp_path, monkeypatch, *, center: bool = True, automation: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "notification-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "notification-test-session-secret")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_CENTER_ENABLED", "true" if center else "false")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_AUTOMATION_ENABLED", "true" if automation else "false")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_SECRET", TICK_SECRET)
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_KEY_ID", "primary")
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


def login(client: TestClient, email: str) -> str:
    created = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Inbox Owner"},
    )
    assert created.status_code == 200
    signed = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed.status_code == 200
    return signed.json()["data"]["csrf_token"]


def login_existing(client: TestClient, email: str) -> str:
    signed = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed.status_code == 200
    return signed.json()["data"]["csrf_token"]


def tick_body(timestamp: str | None = None) -> tuple[bytes, str]:
    timestamp = timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
    return canonical_json({"protocol_version": PROTOCOL_VERSION, "trigger": "railway_cron", "requested_at": timestamp}), timestamp


def tick_headers(*, body: bytes, timestamp: str, nonce: str, request_id: str | None = None) -> dict[str, str]:
    request_id = request_id or str(uuid.uuid4())
    return {
        "Content-Type": "application/json",
        "X-Notify-Timestamp": timestamp,
        "X-Notify-Nonce": nonce,
        "X-Notify-Request-Id": request_id,
        "X-Notify-Key-Id": "primary",
        "X-Notify-Signature": sign_tick(
            secret=TICK_SECRET, timestamp=timestamp, nonce=nonce, request_id=request_id, key_id="primary", body=body,
        ),
    }


def insert_overdue_reminder(db_path, email: str, *, state: str = "active") -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    due = (now - timedelta(minutes=10)).isoformat(timespec="seconds")
    reminder_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as conn:
        account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
        conn.execute(
            """INSERT INTO web_memory_reminders
               (id, account_id, note_id, title, body, due_at, next_run_at, timezone, repeat_rule, state,
                revision, last_completed_at, completed_at, created_at, updated_at)
               VALUES (?, ?, NULL, ?, ?, ?, ?, 'Asia/Ho_Chi_Minh', 'none', ?, 1, NULL, NULL, ?, ?)""",
            (reminder_id, account_id, "Private source title", "Private source body", due, due, state, due, due),
        )
        conn.commit()
    return reminder_id


def insert_many_overdue_reminders(db_path, email: str, *, count: int) -> list[str]:
    """Create a deterministic overdue queue without exposing source content."""
    assert count > 0
    base = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)
    reminder_ids = [str(uuid.uuid4()) for _ in range(count)]
    with sqlite3.connect(db_path) as conn:
        account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
        rows = []
        for offset, reminder_id in enumerate(reminder_ids):
            due = (base + timedelta(seconds=offset)).isoformat(timespec="seconds")
            rows.append(
                (
                    reminder_id,
                    account_id,
                    f"Private queue title {offset}",
                    "Private queue body",
                    due,
                    due,
                    due,
                    due,
                )
            )
        conn.executemany(
            """INSERT INTO web_memory_reminders
               (id, account_id, note_id, title, body, due_at, next_run_at, timezone, repeat_rule, state,
                revision, last_completed_at, completed_at, created_at, updated_at)
               VALUES (?, ?, NULL, ?, ?, ?, ?, 'Asia/Ho_Chi_Minh', 'none', 'active', 1, NULL, NULL, ?, ?)""",
            rows,
        )
        conn.commit()
    return reminder_ids


def insert_inbox_records(
    db_path, email: str, *, records: list[tuple[str, str]], base_time: datetime | None = None,
) -> list[dict[str, str]]:
    """Seed only opaque in-app metadata for the signed Inbox list contract."""
    base = (base_time or datetime(2026, 1, 1, tzinfo=timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    inserted: list[dict[str, str]] = []
    with sqlite3.connect(db_path) as conn:
        account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
        rows = []
        for offset, (state, severity) in enumerate(records):
            item_id = str(uuid.uuid4())
            source_id = str(uuid.uuid4())
            timestamp = (base + timedelta(seconds=offset)).isoformat(timespec="seconds")
            rows.append(
                (
                    item_id, account_id, "reminder_due", "memory_reminder", source_id, 1, timestamp,
                    severity, state, 1, f"fixture-notification:{item_id}", None, timestamp, timestamp,
                    timestamp if state == "read" else None,
                    timestamp if state == "dismissed" else None,
                )
            )
            inserted.append({"id": item_id, "state": state})
        conn.executemany(
            """INSERT INTO web_notification_items
               (id, account_id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state,
                revision, dedupe_fingerprint, created_by_run_id, created_at, updated_at, read_at, dismissed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
    return inserted


def test_scheduler_materializes_one_owner_scoped_in_app_record_and_never_delivers_external(tmp_path, monkeypatch):
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        owner_csrf = login(client, "inbox-owner@example.com")
        reminder_id = insert_overdue_reminder(db_path, "inbox-owner@example.com")
        body, timestamp = tick_body()
        first = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="N" * 24), content=body,
        )
        assert first.status_code == 200 and first.json()["status"] == "completed"
        receipt = first.json()["data"]
        assert receipt["action_count"] == 1 and receipt["in_app_record_created"] is True
        for key in (
            "bot_called", "provider_called", "wallet_mutated", "payment_mutated", "payment_processed",
            "customer_reply_sent", "external_notification_sent", "telegram_sent", "email_sent", "sms_sent",
            "web_push_sent", "job_retried", "deployment_changed", "self_modifying_code",
        ):
            assert receipt[key] is False
        body, timestamp = tick_body()
        duplicate_occurrence = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="O" * 24), content=body,
        )
        assert duplicate_occurrence.status_code == 200 and duplicate_occurrence.json()["data"]["action_count"] == 0
        listed = client.get("/api/v1/inbox/items")
        assert listed.status_code == 200 and listed.json()["ok"] is True
        items = listed.json()["data"]["items"]
        assert len(items) == 1
        item = items[0]
        assert item["kind"] == "reminder_due" and item["source_id"] == reminder_id
        assert item["delivery"] == "in_app_record_only"
        assert "title" not in item and "body" not in item and "payload" not in item
        read = client.post(
            f"/api/v1/inbox/items/{item['id']}/read",
            headers={"X-CSRF-Token": owner_csrf},
            json={"expected_revision": item["revision"], "idempotency_key": "inbox-owner-read-item-0001"},
        )
        assert read.status_code == 200 and read.json()["data"]["item"]["state"] == "read"
        read_item = read.json()["data"]["item"]
        dismiss = client.post(
            f"/api/v1/inbox/items/{item['id']}/dismiss",
            headers={"X-CSRF-Token": owner_csrf},
            json={
                "expected_revision": read_item["revision"], "confirm": True,
                "idempotency_key": "inbox-owner-dismiss-item-0001",
            },
        )
        assert dismiss.status_code == 200 and dismiss.json()["data"]["item"]["state"] == "dismissed"
        other_csrf = login(client, "inbox-other@example.com")
        hidden = client.post(
            f"/api/v1/inbox/items/{item['id']}/read",
            headers={"X-CSRF-Token": other_csrf},
            json={"expected_revision": 1, "idempotency_key": "inbox-other-read-item-0001"},
        )
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_INBOX_ITEM_NOT_FOUND"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_notification_items").fetchone()[0] == 1
        assert conn.execute("SELECT state FROM web_memory_reminders WHERE id=?", (reminder_id,)).fetchone() == ("active",)


def test_scheduler_escalates_only_old_unread_warning_records_without_source_or_delivery_changes(tmp_path, monkeypatch):
    """A signed tick may raise local urgency, never create/deliver/mutate a source."""
    db_path = tmp_path / "notification-test.db"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        owner_csrf = login(client, "inbox-urgency-owner@example.com")
        records = insert_inbox_records(
            db_path,
            "inbox-urgency-owner@example.com",
            records=[
                ("unread", "warning"), ("read", "warning"), ("dismissed", "warning"),
                ("unread", "urgent"), ("unread", "warning"), ("unread", "warning"),
            ],
            base_time=now - timedelta(days=2),
        )
        old_warning, read_warning, dismissed_warning, already_urgent, recent_warning, malformed_warning = records
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_notification_items SET occurrence_at=? WHERE id=?",
                ((now - timedelta(hours=23)).isoformat(timespec="seconds"), recent_warning["id"]),
            )
            conn.execute(
                "UPDATE web_notification_items SET occurrence_at=? WHERE id=?",
                ("not-a-timestamp", malformed_warning["id"]),
            )
            source_before = conn.execute(
                "SELECT COUNT(*) FROM web_memory_reminders"
            ).fetchone()[0]
            conn.commit()

        body, timestamp = tick_body()
        first = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="U" * 24), content=body,
        )
        assert first.status_code == 200 and first.json()["status"] == "completed"
        receipt = first.json()["data"]
        assert receipt["action_count"] == 1
        assert receipt["in_app_record_count"] == 0 and receipt["in_app_record_created"] is False
        assert receipt["urgency_escalation_count"] == 1 and receipt["in_app_urgency_maintained"] is True

        # A fresh signed tick is idempotent: the record is already urgent, so
        # it cannot receive a second revision/event.
        body, timestamp = tick_body()
        repeated = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="V" * 24), content=body,
        )
        assert repeated.status_code == 200
        assert repeated.json()["data"]["action_count"] == 0
        assert repeated.json()["data"]["urgency_escalation_count"] == 0

        stale_read = client.post(
            f"/api/v1/inbox/items/{old_warning['id']}/read",
            headers={"X-CSRF-Token": owner_csrf},
            json={"expected_revision": 1, "idempotency_key": "inbox-urgency-stale-read-0001"},
        )
        assert stale_read.status_code == 200
        assert stale_read.json()["error_code"] == "WEB_INBOX_ITEM_CONFLICT"
        refreshed = stale_read.json()["data"]["item"]
        assert refreshed["severity"] == "urgent" and refreshed["revision"] == 2
        read = client.post(
            f"/api/v1/inbox/items/{old_warning['id']}/read",
            headers={"X-CSRF-Token": owner_csrf},
            json={"expected_revision": 2, "idempotency_key": "inbox-urgency-fresh-read-0001"},
        )
        assert read.status_code == 200 and read.json()["data"]["item"]["state"] == "read"

    with sqlite3.connect(db_path) as conn:
        rows = {
            row[0]: row[1:]
            for row in conn.execute(
                "SELECT id, state, severity, revision FROM web_notification_items"
            )
        }
        events = conn.execute(
            "SELECT notification_id, actor_account_id, action, state, revision FROM web_notification_events"
        ).fetchall()
        # Schema backfill mirrors pre-existing items into opaque dedupe
        # tombstones. Escalation itself must not add a seventh coordinate.
        assert conn.execute("SELECT COUNT(*) FROM web_notification_dedupes").fetchone()[0] == len(records)
        assert conn.execute("SELECT COUNT(*) FROM web_memory_reminders").fetchone()[0] == source_before
    assert rows[old_warning["id"]] == ("read", "urgent", 3)
    assert rows[read_warning["id"]] == ("read", "warning", 1)
    assert rows[dismissed_warning["id"]] == ("dismissed", "warning", 1)
    assert rows[already_urgent["id"]] == ("unread", "urgent", 1)
    assert rows[recent_warning["id"]] == ("unread", "warning", 1)
    assert rows[malformed_warning["id"]] == ("unread", "warning", 1)
    assert (old_warning["id"], None, "overdue_escalated", "unread", 2) in events
    assert sum(1 for event in events if event[2] == "overdue_escalated") == 1


def test_overdue_warning_urgency_maintenance_is_fair_and_bounded(tmp_path, monkeypatch):
    """One account's old Inbox backlog cannot starve another account's record."""
    db_path = tmp_path / "notification-test.db"
    base_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=2)
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-urgency-heavy@example.com")
        login(client, "inbox-urgency-waiting@example.com")
        insert_inbox_records(
            db_path,
            "inbox-urgency-heavy@example.com",
            records=[("unread", "warning")] * (MAX_ACTIONS_PER_RUN + 5),
            base_time=base_time,
        )
        waiting = insert_inbox_records(
            db_path,
            "inbox-urgency-waiting@example.com",
            records=[("unread", "warning")],
            base_time=base_time,
        )[0]
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="W" * 24), content=body,
        )
        assert tick.status_code == 200 and tick.json()["status"] == "guarded"
        receipt = tick.json()["data"]
        assert receipt["action_count"] == MAX_ACTIONS_PER_RUN
        assert receipt["urgency_escalation_count"] == MAX_ACTIONS_PER_RUN
        login_existing(client, "inbox-urgency-waiting@example.com")
        waiting_items = client.get("/api/v1/inbox/items").json()["data"]["items"]
        assert [(item["id"], item["severity"], item["revision"]) for item in waiting_items] == [
            (waiting["id"], "urgent", 2),
        ]


def test_notification_scheduler_consumes_preflight_guard_and_ignores_paused_source(tmp_path, monkeypatch):
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-guard@example.com")
        body, timestamp = tick_body()
        headers = tick_headers(body=body, timestamp=timestamp, nonce="G" * 24)
        monkeypatch.setenv("RAILWAY_REPLICA_COUNT", "2")
        guarded = client.post("/internal/v1/notifications/tick", headers=headers, content=body)
        assert guarded.status_code == 200 and guarded.json()["data"]["guarded_code"] == "NOTIFY_MULTI_REPLICA_BLOCKED"
        monkeypatch.delenv("RAILWAY_REPLICA_COUNT", raising=False)
        replay = client.post("/internal/v1/notifications/tick", headers=headers, content=body)
        assert replay.status_code == 200 and replay.json()["data"]["guarded_code"] == "NOTIFY_TICK_REPLAYED"
        paused_id = insert_overdue_reminder(db_path, "inbox-guard@example.com", state="paused")
        body, timestamp = tick_body()
        normal = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="P" * 24), content=body,
        )
        assert normal.status_code == 200 and normal.json()["status"] == "completed"
        assert normal.json()["data"]["action_count"] == 0
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_notification_items").fetchone()[0] == 0
        assert conn.execute("SELECT state FROM web_memory_reminders WHERE id=?", (paused_id,)).fetchone() == ("paused",)
        codes = set(conn.execute("SELECT state, error_code FROM web_notification_runs").fetchall())
        assert ("guarded", "NOTIFY_MULTI_REPLICA_BLOCKED") in codes


def test_candidate_window_eventually_reaches_the_101st_due_reminder_without_mutating_sources(tmp_path, monkeypatch):
    """A full first candidate page must not starve later overdue reminders forever."""
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-queue@example.com")
        reminder_ids = insert_many_overdue_reminders(db_path, "inbox-queue@example.com", count=101)
        target_reminder_id = reminder_ids[-1]
        with sqlite3.connect(db_path) as conn:
            source_before = conn.execute(
                "SELECT id, state, revision, next_run_at FROM web_memory_reminders ORDER BY id"
            ).fetchall()

        # The action budget is 20. Six independent ticks must therefore reach
        # the last item even though each source snapshot is capped at 100.
        for sequence in range(6):
            body, timestamp = tick_body()
            tick = client.post(
                "/internal/v1/notifications/tick",
                headers=tick_headers(
                    body=body,
                    timestamp=timestamp,
                    nonce=f"Q{sequence:023d}",
                ),
                content=body,
            )
            assert tick.status_code == 200 and tick.json()["ok"] is True

    with sqlite3.connect(db_path) as conn:
        target_count = conn.execute(
            "SELECT COUNT(*) FROM web_notification_items WHERE source_id=?",
            (target_reminder_id,),
        ).fetchone()[0]
        source_after = conn.execute(
            "SELECT id, state, revision, next_run_at FROM web_memory_reminders ORDER BY id"
        ).fetchall()
    assert target_count == 1
    assert source_after == source_before


def test_inbox_items_use_owner_scoped_state_filter_and_pagination(tmp_path, monkeypatch):
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-page-owner@example.com")
        owner_records = insert_inbox_records(
            db_path,
            "inbox-page-owner@example.com",
            records=[
                ("unread", "urgent"), ("unread", "warning"), ("unread", "warning"),
                ("read", "warning"), ("dismissed", "warning"),
            ],
        )
        login(client, "inbox-page-other@example.com")
        insert_inbox_records(db_path, "inbox-page-other@example.com", records=[("unread", "urgent")])
        login_existing(client, "inbox-page-owner@example.com")
        owner_unread = {item["id"] for item in owner_records if item["state"] == "unread"}
        owner_read = next(item["id"] for item in owner_records if item["state"] == "read")

        first = client.get("/api/v1/inbox/items?state=unread&limit=2&offset=0")
        assert first.status_code == 200
        first_data = first.json()["data"]
        first_ids = {item["id"] for item in first_data["items"]}
        assert first_ids <= owner_unread and len(first_ids) == 2
        assert first_data["has_more"] is True and first_data["next_offset"] == 2
        assert first_data["filters"] == {"state": "unread"}
        assert first_data["pagination"] == {"limit": 2, "offset": 0, "returned": 2}

        second = client.get("/api/v1/inbox/items?state=unread&limit=2&offset=2")
        assert second.status_code == 200
        second_data = second.json()["data"]
        second_ids = {item["id"] for item in second_data["items"]}
        assert second_ids == owner_unread - first_ids
        assert second_data["has_more"] is False and second_data["next_offset"] is None
        assert second_data["pagination"] == {"limit": 2, "offset": 2, "returned": 1}

        read_only = client.get("/api/v1/inbox/items?state=read&limit=2")
        assert read_only.status_code == 200
        assert [item["id"] for item in read_only.json()["data"]["items"]] == [owner_read]
        clamped = client.get("/api/v1/inbox/items?state=unread&limit=2&offset=10001")
        assert clamped.status_code == 200 and clamped.json()["data"]["pagination"]["offset"] == 10_000
        assert client.get("/api/v1/inbox/items?state=not-a-state").status_code == 422

        login(client, "inbox-page-other@example.com")
        other = client.get("/api/v1/inbox/items?state=unread&limit=2")
        assert other.status_code == 200
        assert len(other.json()["data"]["items"]) == 1
        assert other.json()["data"]["items"][0]["id"] not in owner_unread


@pytest.mark.parametrize(
    ("env_name", "bad_value", "expected_code"),
    [
        ("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS", "0", "NOTIFY_MAX_RUN_SECONDS_UNVERIFIED"),
        ("WEBAPP_NOTIFICATION_MAX_ACTIONS_PER_RUN", "not-an-integer", "NOTIFY_MAX_ACTIONS_UNVERIFIED"),
    ],
)
def test_invalid_runtime_budget_is_guarded_and_consumes_the_signed_nonce(
    tmp_path, monkeypatch, env_name, bad_value, expected_code,
):
    """A bad local scheduler setting must never become a 5xx retry loop."""
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        monkeypatch.setenv(env_name, bad_value)
        body, timestamp = tick_body()
        request_id = str(uuid.uuid4())
        headers = tick_headers(
            body=body,
            timestamp=timestamp,
            nonce="R" * 24,
            request_id=request_id,
        )
        guarded = client.post("/internal/v1/notifications/tick", headers=headers, content=body)
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["guarded_code"] == expected_code

        monkeypatch.delenv(env_name, raising=False)
        replay = client.post("/internal/v1/notifications/tick", headers=headers, content=body)
        assert replay.status_code == 200
        assert replay.json()["status"] == "guarded"
        assert replay.json()["data"]["guarded_code"] == "NOTIFY_TICK_REPLAYED"

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT state, error_code FROM web_notification_runs WHERE request_id=?",
            (request_id,),
        ).fetchone() == ("guarded", expected_code)


def test_customer_summary_never_exposes_a_global_scheduler_run_from_another_account(tmp_path, monkeypatch):
    """Accounts without records learn neither global scheduler IDs nor run state."""
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-summary-a@example.com")
        login(client, "inbox-summary-b@example.com")
        insert_overdue_reminder(db_path, "inbox-summary-b@example.com")
        body, timestamp = tick_body()
        request_id = str(uuid.uuid4())
        materialized = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(
                body=body,
                timestamp=timestamp,
                nonce="S" * 24,
                request_id=request_id,
            ),
            content=body,
        )
        assert materialized.status_code == 200 and materialized.json()["data"]["action_count"] == 1

        login_existing(client, "inbox-summary-a@example.com")
        summary = client.get("/api/v1/inbox/summary")
        assert summary.status_code == 200 and summary.json()["ok"] is True
        data = summary.json()["data"]
        assert data["unread_count"] == 0
        # A later account-specific aggregate may use ``last_run`` only when it
        # is derived from this account's own materialized item.  It cannot be
        # the global scheduler receipt created for account B.
        assert data.get("last_run") in (None, {})
        assert request_id not in json.dumps(data, sort_keys=True)


def test_candidate_fairness_materializes_another_account_despite_one_large_overdue_queue(tmp_path, monkeypatch):
    """One account's backlog cannot fill every candidate slot indefinitely."""
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-fairness-heavy@example.com")
        login(client, "inbox-fairness-waiting@example.com")
        # All heavy-account occurrences are older than the waiting account's
        # occurrence.  The previous global LIMIT selected only the first 100
        # heavy rows, so the waiting account could never reach a scheduler run.
        insert_many_overdue_reminders(
            db_path, "inbox-fairness-heavy@example.com", count=MAX_CANDIDATES_PER_RUN + 25,
        )
        waiting_reminder_id = insert_overdue_reminder(db_path, "inbox-fairness-waiting@example.com")
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="F" * 24), content=body,
        )
        # One bounded run intentionally stops at its action budget; this is a
        # guarded scheduler receipt, not a failed delivery.
        assert tick.status_code == 200 and tick.json()["status"] == "guarded"
        assert tick.json()["data"]["action_count"] == MAX_ACTIONS_PER_RUN
        # The candidate scan is both bounded and account-round-robin.  The
        # waiting account's one record is therefore materialized in this same
        # run rather than waiting for the entire older backlog to drain.
        waiting_items = client.get("/api/v1/inbox/items").json()["data"]["items"]
        assert [item["source_id"] for item in waiting_items] == [waiting_reminder_id]
        assert waiting_items[0]["delivery"] == "in_app_record_only"


def test_production_scheduler_requires_explicit_single_replica_attestation(tmp_path, monkeypatch):
    """Persistent SQLite is insufficient in production without replica proof."""
    client = make_client(tmp_path, monkeypatch, center=True, automation=True)
    volume = tmp_path / "persistent-volume"
    volume.mkdir()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(volume / "notification-test.db"))
    for env_name in ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT"):
        monkeypatch.delenv(env_name, raising=False)

    with client:
        body, timestamp = tick_body()
        guarded = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="A" * 24),
            content=body,
        )
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["guarded_code"] == "NOTIFY_REPLICA_COUNT_UNVERIFIED"


def test_production_false_replica_override_cannot_bypass_single_replica_attestation(tmp_path, monkeypatch):
    """A copied local ``false`` value must not weaken production SQLite safety."""
    client = make_client(tmp_path, monkeypatch, center=True, automation=True)
    volume = tmp_path / "persistent-volume"
    volume.mkdir()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(volume / "notification-test.db"))
    monkeypatch.setenv("WEBAPP_NOTIFICATION_REQUIRE_REPLICA_ATTESTATION", "false")
    for env_name in ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT"):
        monkeypatch.delenv(env_name, raising=False)

    with client:
        body, timestamp = tick_body()
        guarded = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="B" * 24),
            content=body,
        )
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["guarded_code"] == "NOTIFY_REPLICA_COUNT_UNVERIFIED"


def test_sqlite_contention_stops_at_tick_deadline_then_retries_without_duplicate_materialization(tmp_path, monkeypatch):
    """The tick must never inherit the application's 30-second busy timeout."""
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-contention@example.com")
        reminder_id = insert_overdue_reminder(db_path, "inbox-contention@example.com")
        monkeypatch.setenv("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS", "1")
        body, timestamp = tick_body()
        headers = tick_headers(body=body, timestamp=timestamp, nonce="D" * 24)
        lock = sqlite3.connect(db_path, timeout=0.1)
        lock.execute("BEGIN IMMEDIATE")
        try:
            started = time.monotonic()
            guarded = client.post("/internal/v1/notifications/tick", headers=headers, content=body)
            elapsed = time.monotonic() - started
        finally:
            lock.rollback()
            lock.close()

        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["guarded_code"] == "NOTIFY_TICK_DEADLINE_REACHED"
        # This leaves ample CI slack while proving it did not wait for the
        # general transaction helper's 30-second SQLite timeout.
        assert elapsed < 3.0
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_notification_items").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM web_notification_runs").fetchone()[0] == 0

        retry = client.post("/internal/v1/notifications/tick", headers=headers, content=body)
        assert retry.status_code == 200 and retry.json()["status"] == "completed"
        assert retry.json()["data"]["action_count"] == 1
        items = client.get("/api/v1/inbox/items").json()["data"]["items"]
        assert [item["source_id"] for item in items] == [reminder_id]


def test_late_unexpected_failure_receipt_keeps_materialized_progress_counts(tmp_path, monkeypatch):
    """A failed receipt must not erase counts from already committed local rows."""
    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-progress@example.com")
        insert_overdue_reminder(db_path, "inbox-progress@example.com")
        insert_overdue_reminder(db_path, "inbox-progress@example.com")
        center = importlib.import_module("copyfast_notification_center")
        real_materialize = center._materialize_reminder
        calls = {"count": 0}

        def fail_after_first(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("test-only late materialization failure")
            return real_materialize(*args, **kwargs)

        monkeypatch.setattr(center, "_materialize_reminder", fail_after_first)
        body, timestamp = tick_body()
        request_id = str(uuid.uuid4())
        failed = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="E" * 24, request_id=request_id),
            content=body,
        )
        assert failed.status_code == 500

    with sqlite3.connect(db_path) as conn:
        run = conn.execute(
            "SELECT state, action_count, candidate_count, error_code, receipt_json FROM web_notification_runs WHERE request_id=?",
            (request_id,),
        ).fetchone()
        item_count = conn.execute("SELECT COUNT(*) FROM web_notification_items").fetchone()[0]
    assert run is not None
    state, action_count, candidate_count, error_code, receipt_json = run
    receipt = json.loads(receipt_json)
    assert state == "failed" and error_code == "NOTIFY_TICK_INTERNAL_FAILURE"
    assert action_count == 1 and candidate_count >= 2 and item_count == 1
    assert receipt["action_count"] == 1 and receipt["candidate_count"] >= 2
    assert receipt["in_app_record_count"] == 1 and receipt["failure"] == "internal_guarded"


def test_terminal_notification_run_retention_is_bounded_and_preserves_provenance_lease_and_replay(tmp_path, monkeypatch):
    """Retention trims only old unreferenced terminal audit metadata."""

    db_path = tmp_path / "notification-test.db"
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        login(client, "inbox-retention@example.com")
        center = importlib.import_module("copyfast_notification_center")
        monkeypatch.setenv("WEBAPP_NOTIFICATION_RUN_RETENTION_DAYS", "7")
        monkeypatch.setenv("WEBAPP_NOTIFICATION_RUN_PRUNE_BATCH_SIZE", "2")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        old = (now - timedelta(days=8)).isoformat(timespec="seconds")
        current = str(uuid.uuid4())
        old_completed = str(uuid.uuid4())
        old_guarded = str(uuid.uuid4())
        referenced = str(uuid.uuid4())
        leased = str(uuid.uuid4())
        replay = str(uuid.uuid4())
        account_id = ""

        def seed_run(conn, run_id: str, *, state: str, error_code: str | None = None, finished_at: str | None = old) -> None:
            conn.execute(
                """INSERT INTO web_notification_runs
                   (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                    action_count, candidate_count, deadline_at, started_at, finished_at, error_code, receipt_json)
                   VALUES (?, ?, 'railway_cron', '2026-01-01T00:00', ?, 1, 1, ?, 0, 0, ?, ?, ?, ?, '{}')""",
                (run_id, str(uuid.uuid4()), state, "a" * 64, old, old, finished_at, error_code),
            )
            conn.execute(
                """INSERT INTO web_notification_run_steps
                   (id, run_id, sequence, playbook, state, idempotency_key, input_hash, result_code, started_at, finished_at)
                   VALUES (?, ?, 1, 'fixture', ?, ?, ?, 'fixture', ?, ?)""",
                (str(uuid.uuid4()), run_id, state, f"fixture-step:{run_id}", "b" * 64, old, finished_at),
            )

        with sqlite3.connect(db_path) as conn:
            account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", ("inbox-retention@example.com",)).fetchone()[0]
            seed_run(conn, current, state="started", finished_at=None)
            seed_run(conn, old_completed, state="completed")
            seed_run(conn, old_guarded, state="guarded", error_code="NOTIFY_ACTION_BUDGET_REACHED")
            seed_run(conn, referenced, state="completed")
            seed_run(conn, leased, state="completed")
            seed_run(conn, replay, state="guarded", error_code="NOTIFY_TICK_REPLAYED")
            conn.execute(
                """INSERT INTO web_notification_items
                   (id, account_id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state,
                    revision, dedupe_fingerprint, created_by_run_id, created_at, updated_at)
                   VALUES (?, ?, 'reminder_due', 'memory_reminder', ?, 1, ?, 'warning', 'unread', 1, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), account_id, str(uuid.uuid4()), old, f"retention-item:{referenced}", referenced, old, old),
            )
            conn.execute(
                """INSERT INTO web_notification_leases
                   (name, owner_run_id, fence_token, acquired_at, expires_at, updated_at)
                   VALUES ('retention-fixture-lease', ?, 1, ?, ?, ?)""",
                (leased, old, (now + timedelta(hours=1)).isoformat(timespec="seconds"), old),
            )
            conn.commit()

        deadline = datetime.now(timezone.utc) + timedelta(seconds=5)
        with center._tick_write_transaction(deadline=deadline) as conn:
            deleted = center._prune_finished_run_history(
                conn,
                current_run_id=current,
                deadline=deadline,
            )
        assert deleted == 2

    with sqlite3.connect(db_path) as conn:
        surviving = {
            row[0]
            for row in conn.execute("SELECT id FROM web_notification_runs")
        }
        step_counts = {
            run_id: conn.execute("SELECT COUNT(*) FROM web_notification_run_steps WHERE run_id=?", (run_id,)).fetchone()[0]
            for run_id in (old_completed, old_guarded, referenced, leased, replay, current)
        }
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(web_notification_runs)")}
        item_indexes = {row[1] for row in conn.execute("PRAGMA index_list(web_notification_items)")}
    assert old_completed not in surviving and old_guarded not in surviving
    assert referenced in surviving and leased in surviving and replay in surviving and current in surviving
    assert step_counts[old_completed] == 0 and step_counts[old_guarded] == 0
    assert step_counts[referenced] == 1 and step_counts[leased] == 1 and step_counts[replay] == 1 and step_counts[current] == 1
    assert "idx_web_notification_runs_terminal_finished" in indexes
    assert "idx_web_notification_items_created_by_run" in item_indexes
    assert "idx_web_notification_items_unread_warning_occurrence" in item_indexes


def test_malformed_notification_tick_burst_is_rate_limited_before_hmac_work(tmp_path, monkeypatch):
    """The isolated Cron endpoint has an early fixed-family flood gate."""
    with make_client(tmp_path, monkeypatch, center=True, automation=True) as client:
        for _ in range(12):
            malformed = client.post(
                "/internal/v1/notifications/tick",
                headers={"Content-Type": "application/json"},
                content=b"{}",
            )
            # Missing scheduler signature is rejected by the HMAC boundary.
            # The point of this loop is that the first 12 requests reach that
            # boundary; the thirteenth must be stopped by the earlier gate.
            assert malformed.status_code == 401

        limited = client.post(
            "/internal/v1/notifications/tick",
            headers={"Content-Type": "application/json"},
            content=b"{}",
        )
        assert limited.status_code == 429
        body = limited.json()
        assert body["error_code"] == "AUTH_RATE_LIMITED"
        assert body["data"]["execution"] == "web_native_in_app_record_materialization_and_urgency_maintenance_only"
        assert body["data"]["external_notification_sent"] is False


def test_notification_center_source_stays_outside_external_authorities():
    root = importlib.import_module("pathlib").Path(__file__).parents[1]
    source = (root / "copyfast_notification_center.py").read_text(encoding="utf-8")
    for forbidden in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS",
        "import wallet", "from wallet", "import requests", "import httpx", "import urllib", "showNotification",
    ):
        assert forbidden not in source
