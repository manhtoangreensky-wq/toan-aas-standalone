"""Focused contracts for private Workboard history pagination.

These checks cover only bounded owner-scoped revision/activity history and
the client fences that keep delayed private reads out of a new session/route.
They deliberately do not invoke a Bot, provider, payment, job or deploy.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKBOARD = (ROOT / "copyfast_workboard.py").read_text(encoding="utf-8")

MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard",
    "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio",
    "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "workboard-history.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "workboard-history-session-secret")
    monkeypatch.setenv("WEBAPP_WORKBOARD_ENABLED", "true")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Workboard History Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def create_item(client: TestClient, csrf: str) -> dict:
    response = client.post(
        "/api/v1/workboard/items",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Lịch sử Workboard riêng tư",
            "description": "PRIVATE_WORKBOARD_DESCRIPTION_MUST_NOT_APPEAR_IN_HISTORY",
            "priority": "normal",
            "references": [],
            "checklist": [],
            "idempotency_key": "workboard-history-create-0001",
        },
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["item"]


def update_item(client: TestClient, csrf: str, item: dict, number: int) -> dict:
    response = client.patch(
        f"/api/v1/workboard/items/{item['id']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": f"Lịch sử Workboard riêng tư {number}",
            "expected_revision": item["revision"],
            "idempotency_key": f"workboard-history-update-{number:04d}",
        },
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["item"]


def assert_page(response, key: str, *, returned: int, has_more: bool, next_offset: int | None) -> dict:
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert len(data["items"]) == returned
    assert data[key] == data["items"]
    assert data["pagination"]["returned"] == returned
    assert data["has_more"] is has_more
    assert data["next_offset"] == next_offset
    assert "PRIVATE_WORKBOARD_DESCRIPTION_MUST_NOT_APPEAR_IN_HISTORY" not in response.text
    return data


def test_workboard_history_pages_are_bounded_private_and_owner_scoped(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = login(owner, "workboard-history-owner@example.com")
        item = create_item(owner, csrf)
        for number in range(1, 4):
            item = update_item(owner, csrf, item, number)

        versions_first = owner.get(f"/api/v1/workboard/items/{item['id']}/versions", params={"limit": 2, "offset": 0})
        first_data = assert_page(versions_first, "versions", returned=2, has_more=True, next_offset=2)
        versions_second = owner.get(f"/api/v1/workboard/items/{item['id']}/versions", params={"limit": 2, "offset": first_data["next_offset"]})
        assert_page(versions_second, "versions", returned=2, has_more=False, next_offset=None)

        events_first = owner.get(f"/api/v1/workboard/items/{item['id']}/events", params={"limit": 2, "offset": 0})
        event_data = assert_page(events_first, "events", returned=2, has_more=True, next_offset=2)
        events_second = owner.get(f"/api/v1/workboard/items/{item['id']}/events", params={"limit": 2, "offset": event_data["next_offset"]})
        assert_page(events_second, "events", returned=2, has_more=False, next_offset=None)

        global_events = owner.get("/api/v1/workboard/events", params={"limit": 2, "offset": 0})
        assert_page(global_events, "events", returned=2, has_more=True, next_offset=2)
        for endpoint in ("versions", "events"):
            for offset in ("-1", "10001", "not-an-offset"):
                assert owner.get(f"/api/v1/workboard/items/{item['id']}/{endpoint}", params={"offset": offset}).status_code == 422

    with make_client(tmp_path, monkeypatch) as other:
        login(other, "workboard-history-other@example.com")
        hidden = other.get(f"/api/v1/workboard/items/{item['id']}/versions", params={"limit": 2})
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_WORKBOARD_ITEM_NOT_FOUND"


def test_workboard_client_fences_private_list_and_detail_history_reads() -> None:
    for name in ("workboardSessionEpoch", "workboardListHydrationEpoch", "workboardDetailHydrationEpoch"):
        assert name in INTEGRATION
    assert INTEGRATION.count("workboardRequestIsCurrent(") >= 3
    assert "const requestEpoch = ++workboardListHydrationEpoch;" in INTEGRATION
    assert "const requestEpoch = ++workboardDetailHydrationEpoch;" in INTEGRATION
    assert "function workboardHistoryPath(itemId, kind, offset)" in INTEGRATION
    assert "workboard-history-version-page" in INTEGRATION
    assert "workboard-history-event-page" in INTEGRATION
    assert "MAX_LIST_OFFSET = 10_000" in WORKBOARD
    assert "LIMIT ? OFFSET ?" in WORKBOARD
