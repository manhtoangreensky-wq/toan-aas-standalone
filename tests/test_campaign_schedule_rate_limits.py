"""Focused pre-DB rate-limit coverage for Campaign schedule routes.

These checks exercise only the signed Web API.  They never invoke a Bot,
bridge, provider, wallet, payment, job, notification delivery or deployment.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import sys
import time
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_campaign_schedule", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_image_studio", "copyfast_document_workspace", "copyfast_chat_workspace",
    "copyfast_analytics_workspace", "copyfast_workboard", "copyfast_memory", "copyfast_prompt_library",
    "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio", "copyfast_video_studio",
    "copyfast_subtitle_workspace", "copyfast_support", "copyfast_autopilot", "copyfast_notification_center",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "campaign-schedule-rate-limit-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "campaign-schedule-rate-limit-session-secret")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH", "RAILWAY_REPLICA_COUNT",
        "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT", "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "campaign-rate-owner@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Campaign Rate Owner",
        },
    )
    assert registered.status_code == 200
    signed = client.post(
        "/api/v1/auth/login",
        json={"email": "campaign-rate-owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert signed.status_code == 200
    return signed.json()["data"]["csrf_token"]


def create_plan(client: TestClient, csrf: str, *, suffix: str) -> dict:
    response = client.post(
        "/api/v1/campaigns",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": f"Campaign rate {suffix}",
            "destination_url": f"https://example.com/campaign-rate-{suffix}",
            "platform": "website",
            "objective": "traffic",
            "scheduled_for": "2026-12-01T09:00",
            "idempotency_key": f"campaign-rate-plan-{suffix}-0001",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["item"]


def schedule_payload(plan: dict) -> dict:
    zone = ZoneInfo("Asia/Ho_Chi_Minh")
    trigger = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=10)
    return {
        "trigger_local_at": trigger.astimezone(zone).replace(tzinfo=None).isoformat(timespec="seconds"),
        "timezone": "Asia/Ho_Chi_Minh",
        "expected_plan_revision": plan["revision"],
        "opt_in": True,
        "confirm": True,
        "idempotency_key": "campaign-rate-schedule-create-0001",
    }


def test_campaign_schedule_rate_limits_cover_normal_get_post_patch_with_fixed_families(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client)
        first_plan = create_plan(client, csrf, suffix="first")
        second_plan = create_plan(client, csrf, suffix="second")
        app_module = sys.modules["app"]
        app_module._auth_rate_windows.clear()

        listed = client.get(f"/api/v1/campaigns/{first_plan['id']}/schedule-intents")
        assert listed.status_code == 200 and listed.json()["ok"] is True
        created = client.post(
            f"/api/v1/campaigns/{first_plan['id']}/schedule-intents",
            headers={"X-CSRF-Token": csrf},
            json=schedule_payload(first_plan),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        updated = client.patch(
            f"/api/v1/campaigns/{second_plan['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": second_plan["title"],
                "destination_url": second_plan["destination_url"],
                "platform": second_plan["platform"],
                "objective": second_plan["objective"],
                "scheduled_for": second_plan["scheduled_for"],
                "idempotency_key": "campaign-rate-plan-update-0001",
            },
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True

        read_keys = [key for key in app_module._auth_rate_windows if key.startswith("campaign-schedule-read:")]
        write_keys = [key for key in app_module._auth_rate_windows if key.startswith("campaign-schedule-write:")]
        assert len(read_keys) == 1 and len(app_module._auth_rate_windows[read_keys[0]]) == 1
        # POST schedule creation and PATCH source editing intentionally share
        # one fixed write family rather than allocating a bucket per UUID.
        assert len(write_keys) == 1 and len(app_module._auth_rate_windows[write_keys[0]]) == 2

        # Saturating only the known fixed bucket must fail before the route can
        # parse payload/CSRF or touch its owner-scoped SQLite rows.  The reply
        # preserves the narrow schedule boundary instead of claiming delivery.
        app_module._auth_rate_windows[write_keys[0]] = [time.monotonic()] * 40
        guarded = client.post(f"/api/v1/campaigns/{first_plan['id']}/schedule-intents", json={})
        assert guarded.status_code == 429
        payload = guarded.json()
        assert payload["error_code"] == "AUTH_RATE_LIMITED"
        assert payload["status"] == "guarded"
        assert payload["data"]["execution"] == "web_native_in_app_record_intent_only"
        assert payload["data"]["notification_sent"] is False
