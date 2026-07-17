"""Focused contracts for explicit Campaign Planner in-app schedule intents.

The suite uses only local signed Web state and the existing mocked notification
tick.  It never calls Bot, bridge, provider, payment, wallet, jobs, email,
Telegram, push or an external scheduler.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import sqlite3
import sys
import uuid
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from copyfast_notification_protocol import PROTOCOL_VERSION, canonical_json, sign_tick


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_campaign_schedule", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_image_studio", "copyfast_document_workspace", "copyfast_chat_workspace",
    "copyfast_analytics_workspace", "copyfast_workboard", "copyfast_memory", "copyfast_prompt_library",
    "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio", "copyfast_video_studio",
    "copyfast_subtitle_workspace", "copyfast_support", "copyfast_autopilot", "copyfast_notification_center",
    "copyfast_notification_protocol",
]
TICK_SECRET = "c" * 32


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "campaign-schedule-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "campaign-schedule-session-secret")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Campaign Owner"},
    )
    assert registered.status_code == 200
    signed = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed.status_code == 200
    return signed.json()["data"]["csrf_token"]


def create_plan(client: TestClient, csrf: str, key: str) -> dict:
    response = client.post(
        "/api/v1/campaigns",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Campaign nhắc việc riêng tư",
            "destination_url": "https://example.com/campaign-plan",
            "platform": "website",
            "objective": "traffic",
            # This existing field remains a local inert planning marker. It
            # must not create a scheduler candidate on its own.
            "scheduled_for": "2026-12-01T09:00",
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    plan = response.json()["data"]["item"]
    assert plan["revision"] == 1
    return plan


def future_local(minutes: int = 10) -> tuple[str, str, str]:
    zone = ZoneInfo("Asia/Ho_Chi_Minh")
    target = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=minutes)
    return (
        target.astimezone(zone).replace(tzinfo=None).isoformat(timespec="seconds"),
        "Asia/Ho_Chi_Minh",
        target.isoformat(timespec="seconds"),
    )


def schedule_payload(plan: dict, key: str, *, local: str | None = None, zone: str = "Asia/Ho_Chi_Minh") -> dict:
    return {
        "trigger_local_at": local or future_local()[0],
        "timezone": zone,
        "expected_plan_revision": plan["revision"],
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
            "UPDATE web_campaign_schedule_intents SET trigger_at=?, trigger_local_at=? WHERE id=?",
            (utc_value.replace(microsecond=0).isoformat(timespec="seconds"), local_value, intent_id),
        )
        conn.commit()


def test_campaign_schedule_is_explicit_owner_scoped_and_materializes_once(tmp_path, monkeypatch):
    db_path = tmp_path / "campaign-schedule-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = login(client, "campaign-schedule-owner@example.com")
        plan = create_plan(client, owner_csrf, "campaign-schedule-plan-create-0001")

        # The old planning timestamp is inert — no intent means no Inbox item.
        body, timestamp = tick_body()
        inert_tick = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="I" * 24), content=body,
        )
        assert inert_tick.status_code == 200 and inert_tick.json()["data"]["candidate_count"] == 0

        request = schedule_payload(plan, "campaign-schedule-intent-create-0001")
        created = client.post(
            f"/api/v1/campaigns/{plan['id']}/schedule-intents",
            headers={"X-CSRF-Token": owner_csrf}, json=request,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        receipt = created.json()["data"]["schedule_intent"]
        intent_id = receipt["id"]
        assert receipt["delivery"] == "in_app_record_only"
        assert receipt["trigger_at"].endswith("+00:00")
        assert {"title", "destination_url", "review_note", "source_snapshot_hash"}.isdisjoint(receipt)
        replay = client.post(
            f"/api/v1/campaigns/{plan['id']}/schedule-intents",
            headers={"X-CSRF-Token": owner_csrf}, json=request,
        )
        assert replay.status_code == 200 and replay.json()["data"]["schedule_intent"]["id"] == intent_id

        other_csrf = login(client, "campaign-schedule-other@example.com")
        hidden = client.get(f"/api/v1/campaigns/{plan['id']}/schedule-intents")
        assert hidden.status_code == 200 and hidden.json()["error_code"] == "CAMPAIGN_SCHEDULE_PLAN_NOT_FOUND"
        assert other_csrf
        owner_csrf = client.post(
            "/api/v1/auth/login",
            json={"email": "campaign-schedule-owner@example.com", "password": "correct-horse-battery-staple"},
        ).json()["data"]["csrf_token"]

        with sqlite3.connect(db_path) as conn:
            plan_before = conn.execute(
                "SELECT title, destination_url, approval_status, review_note, revision FROM web_campaign_plans WHERE id=?",
                (plan["id"],),
            ).fetchone()
            columns = {row[1] for row in conn.execute("PRAGMA table_info(web_campaign_schedule_intents)").fetchall()}
        assert {"title", "destination_url", "review_note", "snapshot_json", "body"}.isdisjoint(columns)
        past = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=2)
        set_intent_trigger(
            db_path, intent_id, utc_value=past,
            local_value=past.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None).isoformat(timespec="seconds"),
        )
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="C" * 24), content=body,
        )
        assert tick.status_code == 200 and tick.json()["status"] == "completed"
        assert tick.json()["data"]["in_app_record_count"] == 1
        for field in ("bot_called", "provider_called", "wallet_mutated", "payment_mutated", "telegram_sent", "email_sent", "web_push_sent"):
            assert tick.json()["data"][field] is False
        records = client.get("/api/v1/inbox/items").json()["data"]["items"]
        assert len(records) == 1
        record = records[0]
        assert record["kind"] == "campaign_schedule_due"
        assert record["source_kind"] == "campaign_schedule_intent"
        assert record["source_id"] == intent_id
        assert {"title", "destination_url", "review_note", "payload"}.isdisjoint(record)
        intent = client.get(f"/api/v1/campaigns/{plan['id']}/schedule-intents").json()["data"]["schedule_intents"][0]
        assert intent["state"] == "dispatched"
        with sqlite3.connect(db_path) as conn:
            plan_after = conn.execute(
                "SELECT title, destination_url, approval_status, review_note, revision FROM web_campaign_plans WHERE id=?",
                (plan["id"],),
            ).fetchone()
        assert plan_after == plan_before


def test_campaign_source_change_guards_and_requires_reconfirmation_without_reschedule(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "campaign-schedule-guard@example.com")
        plan = create_plan(client, csrf, "campaign-schedule-guard-plan-create-0001")
        created = client.post(
            f"/api/v1/campaigns/{plan['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf}, json=schedule_payload(plan, "campaign-schedule-guard-create-0001"),
        )
        created_intent = created.json()["data"]["schedule_intent"]
        intent_id = created_intent["id"]
        original_trigger_at = created_intent["trigger_at"]
        changed = client.patch(
            f"/api/v1/campaigns/{plan['id']}", headers={"X-CSRF-Token": csrf},
            json={
                "title": "Campaign revision mới cần owner xác nhận lại lịch",
                "destination_url": "https://example.com/campaign-revised",
                "platform": "website", "objective": "traffic", "scheduled_for": "2026-12-02T09:00",
                "idempotency_key": "campaign-schedule-source-update-0001",
            },
        )
        assert changed.status_code == 200 and changed.json()["ok"] is True
        updated_plan = changed.json()["data"]["item"]
        assert updated_plan["revision"] == plan["revision"] + 1
        # Guard immediately in the same local plan-write transaction. The
        # original future trigger remains usable, so reconfirm is a real owner
        # workflow rather than a dead-end that only appears after the time has
        # already passed.
        intent = client.get(f"/api/v1/campaigns/{plan['id']}/schedule-intents").json()["data"]["schedule_intents"][0]
        assert intent["state"] == "guarded"
        assert intent["guard_code"] == "CAMPAIGN_SCHEDULE_SOURCE_CHANGED"
        assert intent["reconfirmation_required"] is True
        assert intent["trigger_at"] == original_trigger_at

        # A guarded source must not enter the scheduler candidate set or
        # create an Inbox record while the owner is deciding what to do.
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/notifications/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="G" * 24), content=body,
        )
        assert tick.status_code == 200 and tick.json()["data"]["in_app_record_count"] == 0
        assert tick.json()["data"]["candidate_count"] == 0
        assert client.get("/api/v1/inbox/items").json()["data"]["items"] == []
        reconfirmed = client.post(
            f"/api/v1/campaigns/{plan['id']}/schedule-intents/{intent_id}/reconfirm",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": intent["revision"], "expected_plan_revision": updated_plan["revision"],
                "confirm": True, "idempotency_key": "campaign-schedule-reconfirm-0001",
            },
        )
        assert reconfirmed.status_code == 200 and reconfirmed.json()["ok"] is True
        refreshed = client.get(f"/api/v1/campaigns/{plan['id']}/schedule-intents").json()["data"]["schedule_intents"][0]
        assert refreshed["state"] == "active"
        assert refreshed["source_revision"] == updated_plan["revision"]
        assert refreshed["trigger_at"] == original_trigger_at


def test_campaign_schedule_requires_opt_in_and_rejects_ambiguous_dst_without_external_imports(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "campaign-schedule-time@example.com")
        plan = create_plan(client, csrf, "campaign-schedule-time-plan-create-0001")
        missing_opt_in = schedule_payload(plan, "campaign-schedule-missing-optin-0001")
        missing_opt_in["opt_in"] = False
        rejected_consent = client.post(
            f"/api/v1/campaigns/{plan['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf}, json=missing_opt_in,
        )
        assert rejected_consent.status_code == 422
        ambiguous = schedule_payload(
            plan, "campaign-schedule-ambiguous-dst-0001", local="2026-11-01T01:30", zone="America/New_York",
        )
        rejected_dst = client.post(
            f"/api/v1/campaigns/{plan['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf}, json=ambiguous,
        )
        assert rejected_dst.status_code == 422
        assert "trùng" in str(rejected_dst.json().get("message") or "")
        assert client.get(f"/api/v1/campaigns/{plan['id']}/schedule-intents").json()["data"]["schedule_intents"] == []

    root = importlib.import_module("pathlib").Path(__file__).parents[1]
    scheduler = (root / "copyfast_campaign_schedule.py").read_text(encoding="utf-8")
    notification = (root / "copyfast_notification_center.py").read_text(encoding="utf-8")
    for source in (scheduler, notification):
        for forbidden in (
            "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS",
            "import requests", "import httpx", "import urllib", "import smtplib", "from telegram",
        ):
            assert forbidden not in source
    assert "campaign_schedule_due" in notification
    assert "campaign_source_hash" in notification


def test_malformed_active_campaign_schedule_is_guarded_before_due_without_inbox_delivery(tmp_path, monkeypatch):
    """A corrupt future intent must not remain active just because it is not due.

    This exercises the scheduler's row-level fail-closed transition only.  It
    does not call a Bot, provider, payment flow, external notification or
    Campaign publication path.
    """
    db_path = tmp_path / "campaign-schedule-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "campaign-schedule-malformed@example.com")
        plan = create_plan(client, csrf, "campaign-schedule-malformed-plan-0001")
        created = client.post(
            f"/api/v1/campaigns/{plan['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf},
            json=schedule_payload(plan, "campaign-schedule-malformed-create-0001"),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        intent_id = created.json()["data"]["schedule_intent"]["id"]
        # This remains in the future.  The malformed digest itself is enough
        # to make the scheduler guard it before an impossible due check can
        # leave it active forever.
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_campaign_schedule_intents SET source_snapshot_hash=? WHERE id=?",
                ("corrupt", intent_id),
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
        assert "source_snapshot_hash" not in receipt and "Campaign nhắc việc riêng tư" not in str(receipt)
        listed = client.get(f"/api/v1/campaigns/{plan['id']}/schedule-intents")
        intent = listed.json()["data"]["schedule_intents"][0]
        assert intent["state"] == "guarded"
        assert intent["guard_code"] == "CAMPAIGN_SCHEDULE_SOURCE_UNVERIFIED"
        assert intent["reconfirmation_required"] is True
        assert client.get("/api/v1/inbox/items").json()["data"]["items"] == []
        with sqlite3.connect(db_path) as conn:
            state, revision, dispatched_at, guarded_at, guard_code = conn.execute(
                "SELECT state, revision, dispatched_at, guarded_at, guard_code "
                "FROM web_campaign_schedule_intents WHERE id=?",
                (intent_id,),
            ).fetchone()
        assert (state, revision, dispatched_at, guard_code) == (
            "guarded", 2, None, "CAMPAIGN_SCHEDULE_SOURCE_UNVERIFIED",
        )
        assert guarded_at


def test_campaign_schedule_portal_contract_fails_closed_and_stays_private() -> None:
    """The browser may only write the route-scoped schedule schema it owns."""
    root = importlib.import_module("pathlib").Path(__file__).parents[1]
    integration = (root / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    portal = (root / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    service_worker = (root / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")

    for action in (
        "campaign-schedule-create",
        "campaign-schedule-cancel",
        "campaign-schedule-reconfirm",
    ):
        assert action in integration
        assert action in portal
    # `plan_id` selects the route only. The API rejects extras, so the client
    # must remove it from the JSON body before adding an idempotency key.
    assert "const { plan_id: planId, ...payload } = schedule;" in integration
    assert "campaignScheduleBoundaryIsSafe(scheduleData)" in integration
    assert "campaignScheduleIntentIsSafe(intent, planId)" in integration
    assert '"campaign_schedule_due"' in integration
    assert '"campaign_schedule_due"' in portal
    assert "Lịch nhắc in-app riêng tư" in portal
    assert "Không Telegram, email, push, Bot, provider, publish hay tự chạy browser." in portal

    shell = service_worker.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    for private_prefix in (
        '"/" + "api/v1/campaigns"',
        '"/campaigns"',
        '"/calendar"',
        '"/approvals"',
    ):
        assert private_prefix in service_worker
        assert private_prefix not in shell
