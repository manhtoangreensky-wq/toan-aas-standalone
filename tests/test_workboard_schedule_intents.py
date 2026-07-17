"""Focused contract tests for explicit Workboard in-app schedule intents.

The suite exercises only signed local SQLite state and the existing mocked
internal notification tick.  It never calls a Bot, bridge, provider, payment,
wallet, job, email, Telegram, push or external scheduler.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import sqlite3
import sys
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

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
TICK_SECRET = "s" * 32


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "workboard-schedule-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "workboard-schedule-session-secret")
    monkeypatch.setenv("WEBAPP_WORKBOARD_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_CENTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_AUTOMATION_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_SECRET", TICK_SECRET)
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_KEY_ID", "primary")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TOPOLOGY", "sqlite_single_replica")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH", "RAILWAY_REPLICA_COUNT",
        "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT", "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Schedule Owner"},
    )
    assert registered.status_code == 200
    signed = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed.status_code == 200
    return signed.json()["data"]["csrf_token"]


def create_item(client: TestClient, csrf: str, key: str) -> dict:
    response = client.post(
        "/api/v1/workboard/items",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Rà soát lịch nhắc Workboard riêng tư",
            "description": "Nội dung nguồn chỉ thuộc Workboard và không được copy vào schedule hay Inbox.",
            "priority": "high",
            "references": [],
            "checklist": [{"body": "Rà soát source snapshot", "is_done": False}],
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["item"]


def future_local(minutes: int = 10) -> tuple[str, str, str]:
    zone = ZoneInfo("Asia/Ho_Chi_Minh")
    target = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=minutes))
    return (
        target.astimezone(zone).replace(tzinfo=None).isoformat(timespec="seconds"),
        "Asia/Ho_Chi_Minh",
        target.isoformat(timespec="seconds"),
    )


def schedule_payload(item: dict, key: str, *, local: str | None = None, zone: str = "Asia/Ho_Chi_Minh") -> dict:
    local = local or future_local()[0]
    return {
        "trigger_local_at": local,
        "timezone": zone,
        "expected_item_revision": item["revision"],
        "opt_in": True,
        "confirm": True,
        "idempotency_key": key,
    }


def tick_body() -> tuple[bytes, str]:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
    return canonical_json({"protocol_version": PROTOCOL_VERSION, "trigger": "railway_cron", "requested_at": timestamp}), timestamp


def tick_headers(*, body: bytes, timestamp: str, nonce: str) -> dict[str, str]:
    request_id = str(uuid.uuid4())
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


def set_intent_trigger(db_path, intent_id: str, *, utc_value: datetime, local_value: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_workboard_schedule_intents SET trigger_at=?, trigger_local_at=? WHERE id=?",
            (utc_value.replace(microsecond=0).isoformat(timespec="seconds"), local_value, intent_id),
        )
        conn.commit()


def test_owner_opt_in_normalizes_utc_and_materializes_only_one_private_inbox_record(tmp_path, monkeypatch):
    db_path = tmp_path / "workboard-schedule-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = login(client, "schedule-owner@example.com")
        item = create_item(client, owner_csrf, "workboard-schedule-item-create-0001")
        request = schedule_payload(item, "workboard-schedule-intent-create-0001")
        created = client.post(
            f"/api/v1/workboard/items/{item['id']}/schedule-intents",
            headers={"X-CSRF-Token": owner_csrf}, json=request,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        receipt = created.json()["data"]["schedule_intent"]
        intent_id = receipt["id"]
        assert receipt["delivery"] == "in_app_record_only"
        assert receipt["trigger_at"].endswith("+00:00")
        assert "title" not in receipt and "description" not in receipt and "source_snapshot_hash" not in receipt
        replay = client.post(
            f"/api/v1/workboard/items/{item['id']}/schedule-intents",
            headers={"X-CSRF-Token": owner_csrf}, json=request,
        )
        assert replay.status_code == 200 and replay.json()["data"]["schedule_intent"]["id"] == intent_id

        other_csrf = login(client, "schedule-other@example.com")
        hidden = client.get(f"/api/v1/workboard/items/{item['id']}/schedule-intents")
        assert hidden.status_code == 200 and hidden.json()["error_code"] == "WEB_WORKBOARD_ITEM_NOT_FOUND"
        assert other_csrf
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "schedule-owner@example.com", "password": "correct-horse-battery-staple"},
        )
        owner_csrf = login_response.json()["data"]["csrf_token"]

        before = None
        with sqlite3.connect(db_path) as conn:
            before = conn.execute(
                "SELECT state, revision, title, description FROM web_workboard_items WHERE id=?", (item["id"],),
            ).fetchone()
            columns = {row[1] for row in conn.execute("PRAGMA table_info(web_workboard_schedule_intents)").fetchall()}
        assert {"title", "description", "snapshot_json", "body"}.isdisjoint(columns)
        past = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=2)
        set_intent_trigger(db_path, intent_id, utc_value=past, local_value=past.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None).isoformat(timespec="seconds"))
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="S" * 24), content=body,
        )
        assert tick.status_code == 200 and tick.json()["status"] == "completed"
        assert tick.json()["data"]["action_count"] == 1
        assert tick.json()["data"]["in_app_record_count"] == 1
        assert tick.json()["data"]["guarded_source_count"] == 0
        for field in ("bot_called", "provider_called", "wallet_mutated", "payment_mutated", "telegram_sent", "email_sent", "web_push_sent"):
            assert tick.json()["data"][field] is False
        inbox = client.get("/api/v1/inbox/items")
        records = inbox.json()["data"]["items"]
        assert len(records) == 1
        record = records[0]
        assert record["kind"] == "workboard_schedule_due"
        assert record["source_kind"] == "workboard_schedule_intent"
        assert record["source_id"] == intent_id
        assert "title" not in record and "description" not in record and "payload" not in record
        intent_list = client.get(f"/api/v1/workboard/items/{item['id']}/schedule-intents")
        intent = intent_list.json()["data"]["schedule_intents"][0]
        assert intent["state"] == "dispatched"
        with sqlite3.connect(db_path) as conn:
            after = conn.execute(
                "SELECT state, revision, title, description FROM web_workboard_items WHERE id=?", (item["id"],),
            ).fetchone()
        assert after == before


def test_source_change_guards_without_delivery_then_requires_explicit_reconfirmation(tmp_path, monkeypatch):
    db_path = tmp_path / "workboard-schedule-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "schedule-guard@example.com")
        item = create_item(client, csrf, "workboard-schedule-guard-item-0001")
        created = client.post(
            f"/api/v1/workboard/items/{item['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf}, json=schedule_payload(item, "workboard-schedule-guard-create-0001"),
        )
        intent_id = created.json()["data"]["schedule_intent"]["id"]
        changed = client.patch(
            f"/api/v1/workboard/items/{item['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                "description": "Revision mới thay đổi source nên lịch cũ phải dừng chờ owner xác nhận.",
                "expected_revision": item["revision"], "idempotency_key": "workboard-schedule-source-update-0001",
            },
        )
        assert changed.status_code == 200 and changed.json()["ok"] is True
        current_item = changed.json()["data"]["item"]
        past = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=2)
        set_intent_trigger(db_path, intent_id, utc_value=past, local_value=past.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None).isoformat(timespec="seconds"))
        with sqlite3.connect(db_path) as conn:
            before_tick = conn.execute(
                "SELECT state, revision, title, description FROM web_workboard_items WHERE id=?", (item["id"],),
            ).fetchone()
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="G" * 24), content=body,
        )
        assert tick.status_code == 200 and tick.json()["status"] == "completed"
        assert tick.json()["data"]["in_app_record_count"] == 0
        assert tick.json()["data"]["guarded_source_count"] == 1
        assert client.get("/api/v1/inbox/items").json()["data"]["items"] == []
        listing = client.get(f"/api/v1/workboard/items/{item['id']}/schedule-intents")
        intent = listing.json()["data"]["schedule_intents"][0]
        assert intent["state"] == "guarded"
        assert intent["guard_code"] == "WORKBOARD_SCHEDULE_SOURCE_CHANGED"
        assert intent["reconfirmation_required"] is True
        with sqlite3.connect(db_path) as conn:
            after_tick = conn.execute(
                "SELECT state, revision, title, description FROM web_workboard_items WHERE id=?", (item["id"],),
            ).fetchone()
        assert after_tick == before_tick

        future_local_at, _zone, future_utc = future_local(minutes=10)
        set_intent_trigger(
            db_path, intent_id, utc_value=datetime.fromisoformat(future_utc), local_value=future_local_at,
        )
        reconfirmed = client.post(
            f"/api/v1/workboard/items/{item['id']}/schedule-intents/{intent_id}/reconfirm",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": intent["revision"],
                "expected_item_revision": current_item["revision"],
                "confirm": True,
                "idempotency_key": "workboard-schedule-reconfirm-0001",
            },
        )
        assert reconfirmed.status_code == 200 and reconfirmed.json()["ok"] is True
        refreshed = client.get(f"/api/v1/workboard/items/{item['id']}/schedule-intents").json()["data"]["schedule_intents"][0]
        assert refreshed["state"] == "active"
        assert refreshed["source_revision"] == current_item["revision"]
        assert refreshed["trigger_at"] == future_utc


def test_schedule_requires_explicit_opt_in_and_rejects_ambiguous_iana_dst_time(tmp_path, monkeypatch):
    """The API must not infer consent or silently choose a DST fold."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "schedule-time-contract@example.com")
        item = create_item(client, csrf, "workboard-schedule-time-item-create-0001")
        missing_opt_in = schedule_payload(item, "workboard-schedule-missing-optin-0001")
        missing_opt_in["opt_in"] = False
        rejected_consent = client.post(
            f"/api/v1/workboard/items/{item['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf}, json=missing_opt_in,
        )
        assert rejected_consent.status_code == 422

        # 01:30 occurs twice at the 2026 New York fall-back transition.  The
        # explicit rejection protects the user from a silent earlier/later
        # dispatch decision even if the calendar date is eventually in the past.
        ambiguous = schedule_payload(
            item,
            "workboard-schedule-ambiguous-dst-0001",
            local="2026-11-01T01:30",
            zone="America/New_York",
        )
        rejected_dst = client.post(
            f"/api/v1/workboard/items/{item['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf}, json=ambiguous,
        )
        assert rejected_dst.status_code == 422
        assert "trùng" in str(rejected_dst.json().get("message") or "")
        listed = client.get(f"/api/v1/workboard/items/{item['id']}/schedule-intents")
        assert listed.status_code == 200
        assert listed.json()["data"]["schedule_intents"] == []


def test_schedule_source_has_no_bot_bridge_or_external_delivery_imports() -> None:
    root = importlib.import_module("pathlib").Path(__file__).parents[1]
    workboard = (root / "copyfast_workboard.py").read_text(encoding="utf-8")
    notification = (root / "copyfast_notification_center.py").read_text(encoding="utf-8")
    for source in (workboard, notification):
        for forbidden in (
            "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS",
            "import requests", "import httpx", "import urllib", "import smtplib", "from telegram",
        ):
            assert forbidden not in source
    assert "web_workboard_schedule_intents" in workboard
    assert "workboard_schedule_due" in notification
    assert "source_snapshot_hash" in notification


def test_malformed_active_workboard_schedule_is_guarded_before_due_without_inbox_delivery(tmp_path, monkeypatch):
    """An invalid stored trigger is fenced even though it cannot become due."""
    db_path = tmp_path / "workboard-schedule-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "workboard-schedule-malformed@example.com")
        item = create_item(client, csrf, "workboard-schedule-malformed-item-0001")
        created = client.post(
            f"/api/v1/workboard/items/{item['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf},
            json=schedule_payload(item, "workboard-schedule-malformed-create-0001"),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        intent_id = created.json()["data"]["schedule_intent"]["id"]
        # A lexical/non-ISO value would never satisfy the ordinary due query.
        # The integrity branch must therefore guard it in the same local
        # scheduler transaction rather than leave an unserviceable active row.
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_workboard_schedule_intents SET trigger_at=? WHERE id=?",
                ("not-a-timestamp", intent_id),
            )
            conn.commit()
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/notifications/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="M" * 24), content=body,
        )
        assert tick.status_code == 200 and tick.json()["status"] == "completed"
        receipt = tick.json()["data"]
        assert receipt["action_count"] == 1 and receipt["guarded_source_count"] == 1
        assert receipt["in_app_record_count"] == 0
        assert "trigger_at" not in receipt and "Rà soát lịch nhắc Workboard riêng tư" not in str(receipt)
        listing = client.get(f"/api/v1/workboard/items/{item['id']}/schedule-intents")
        intent = listing.json()["data"]["schedule_intents"][0]
        assert intent["state"] == "guarded"
        assert intent["guard_code"] == "WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED"
        assert intent["reconfirmation_required"] is True
        assert client.get("/api/v1/inbox/items").json()["data"]["items"] == []
        with sqlite3.connect(db_path) as conn:
            state, revision, dispatched_at, guarded_at, guard_code = conn.execute(
                "SELECT state, revision, dispatched_at, guarded_at, guard_code "
                "FROM web_workboard_schedule_intents WHERE id=?",
                (intent_id,),
            ).fetchone()
        assert (state, revision, dispatched_at, guard_code) == (
            "guarded", 2, None, "WORKBOARD_SCHEDULE_SOURCE_UNVERIFIED",
        )
        assert guarded_at


def test_schedule_portal_contract_is_owner_scoped_and_never_pwa_cached() -> None:
    """Keep the in-app schedule surface separate from public/offline shell state."""
    root = Path(__file__).parents[1]
    integration = (root / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    portal = (root / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    service_worker = (root / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")

    for action in (
        "workboard-schedule-create",
        "workboard-schedule-cancel",
        "workboard-schedule-reconfirm",
    ):
        assert action in integration
        assert action in portal
    assert 'api("/workboard/items/" + encodeURIComponent(String(itemId)) + "/schedule-intents")' in integration
    assert 'data-portal-confirm="Hủy lịch nhắc này?' in portal
    assert "Không Telegram, email, push, Bot, provider hay tự chạy browser." in portal

    # The worker's allow-list is intentionally fixed.  Private Workboard and
    # Inbox state must never be placed in Cache Storage or served as an offline
    # fallback after a sign-out/account switch.
    assert '"/" + "api/v1/workboard"' in service_worker
    assert '"/workboard"' in service_worker
    assert '"/" + "api/v1/inbox"' in service_worker
    assert '"/inbox"' in service_worker
    shell = service_worker.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/workboard"' not in shell
    assert '"/inbox"' not in shell
