"""Focused security contracts for Web-native Chat Run receipts.

The standalone Web App can preserve a signed customer's own message and a
truthful guarded execution record before a reviewed model adapter exists.  It
must never turn that useful receipt into a synthetic assistant response,
provider call, Bot handoff, wallet mutation, job, output or delivery claim.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_chat_workspace", "copyfast_memory", "copyfast_prompt_library",
    "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio", "copyfast_video_studio",
    "copyfast_subtitle_workspace", "copyfast_support",
]


def make_client(tmp_path, monkeypatch, *, execution_requested: bool = False) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "chat-execution-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "chat-execution-test-session-secret")
    monkeypatch.setenv("WEBAPP_CHAT_WORKSPACE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_CHAT_EXECUTION_ENABLED", "true" if execution_requested else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Chat Run Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def create_thread(client: TestClient, csrf: str) -> dict:
    response = client.post(
        "/api/v1/chat-workspace/threads",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Chat Run có kiểm soát",
            "objective": "Lưu câu hỏi do khách hàng soạn trước khi một adapter Web được duyệt.",
            "mode": "focus",
            "system_context": "Không tự nhận đã có phản hồi AI hoặc output.",
            "tags": ["chat-run"],
            "project_id": "",
            "prompt_template_id": "",
            "pinned": False,
            "idempotency_key": "chat-run-thread-create-0001",
        },
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["thread"]


def run_payload(thread: dict, *, key: str, message: str = "Hãy phân tích các rủi ro trước khi nhóm duyệt hướng triển khai.") -> dict:
    return {
        "client_message": message,
        "expected_revision": thread["revision"],
        "idempotency_key": key,
    }


def assert_guarded_boundary(data: dict, *, code: str) -> None:
    execution = data["execution"]
    assert execution == {
        "mode": "web_native_chat_run",
        "run_submission_available": True,
        "provider_execution_available": False,
        "assistant_reply_available": False,
        "cancel_available": False,
        "provider_called": False,
        "bot_called": False,
        "wallet_mutated": False,
        "payment_started": False,
        "job_created": False,
        "output_created": False,
        "stream_available": False,
        "output_delivery": "guarded",
        "guard_code": code,
    }
    for name in ("provider_called", "bot_called", "assistant_reply_created", "output_created", "job_created", "payment_started", "wallet_mutated", "payment_processed", "stream_available"):
        assert data[name] is False


def test_chat_run_persists_owner_message_and_truthful_guarded_receipt(tmp_path, monkeypatch):
    db_path = tmp_path / "chat-execution-test.db"
    message = "Hãy phân tích các rủi ro trước khi nhóm duyệt hướng triển khai."
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = login(client, "chat-run-owner@example.com")
        thread = create_thread(client, owner_csrf)
        endpoint = f"/api/v1/chat-workspace/threads/{thread['id']}/runs"
        status = client.get("/api/v1/core/status")
        assert status.status_code == 200
        assert status.json()["data"]["flags"]["chat_execution_enabled"] is False
        no_csrf = client.post(endpoint, json=run_payload(thread, key="chat-run-csrf-denied-0001"))
        assert no_csrf.status_code == 403
        browser_assistant = client.post(
            endpoint,
            headers={"X-CSRF-Token": owner_csrf},
            json=run_payload(thread, key="chat-run-browser-assistant-0001") | {"assistant_message": "Không được phép."},
        )
        assert browser_assistant.status_code == 422

        created = client.post(
            endpoint,
            headers={"X-CSRF-Token": owner_csrf},
            json=run_payload(thread, key="chat-run-guarded-create-0001", message=message),
        )
        assert created.status_code == 200
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_CHAT_EXECUTION_GUARDED"
        data = body["data"]
        assert_guarded_boundary(data, code="WEB_CHAT_EXECUTION_GUARDED")
        assert data["thread"]["revision"] == thread["revision"] + 1
        assert data["run"]["state"] == "guarded"
        assert data["run"]["assistant_message_id"] is None
        assert data["request_message"]["role"] == "user"
        assert data["request_message"]["body"] == message
        assert data["assistant_message"] is None
        assert [event["state"] for event in data["events"]] == ["draft", "queued", "guarded"]
        assert all(event["state"] != "processing" for event in data["events"])
        run_id = data["run"]["id"]

        replay = client.post(
            endpoint,
            headers={"X-CSRF-Token": owner_csrf},
            json=run_payload(thread, key="chat-run-guarded-create-0001", message=message),
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["run"]["id"] == run_id
        assert "body" not in replay.json()["data"]["request_message"]
        collision = client.post(
            endpoint,
            headers={"X-CSRF-Token": owner_csrf},
            json=run_payload(thread, key="chat-run-guarded-create-0001", message="Một yêu cầu khác không được dùng lại receipt."),
        )
        assert collision.status_code == 409

        listing = client.get(endpoint)
        assert listing.status_code == 200 and listing.json()["ok"] is True
        listing_data = listing.json()["data"]
        assert_guarded_boundary(listing_data, code="WEB_CHAT_EXECUTION_GUARDED")
        assert listing_data["pagination"] == {
            "total": 1,
            "limit": 50,
            "offset": 0,
            "returned": 1,
            "has_more": False,
            "next_offset": None,
            "previous_offset": None,
        }
        assert listing_data["items"][0]["id"] == run_id
        assert message not in json.dumps(listing_data, ensure_ascii=False)

        detail = client.get(f"{endpoint}/{run_id}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        assert detail.json()["data"]["request_message"]["body"] == message
        assert detail.json()["data"]["assistant_message"] is None
        assert [event["action"] for event in detail.json()["data"]["events"]] == ["run_created", "run_queued", "execution_guarded"]

        other_csrf = login(client, "chat-run-other@example.com")
        hidden = client.get(f"{endpoint}/{run_id}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_CHAT_WORKSPACE_NOT_FOUND"
        assert other_csrf

    with sqlite3.connect(db_path) as conn:
        roles = conn.execute("SELECT role, body FROM web_chat_messages").fetchall()
        run_row = conn.execute("SELECT state, assistant_message_id, error_code FROM web_chat_runs").fetchone()
        events = conn.execute("SELECT state FROM web_chat_run_events ORDER BY sequence ASC").fetchall()
        audit = conn.execute("SELECT action, detail FROM web_audit_events WHERE action='chat_run_guarded'").fetchone()
        receipts = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-chat-workspace:%:run:create'"
        ).fetchall()
    assert roles == [("user", message)]
    assert run_row == ("guarded", None, "WEB_CHAT_EXECUTION_GUARDED")
    assert events == [("draft",), ("queued",), ("guarded",)]
    assert audit and message not in str(audit[1])
    assert len(receipts) == 1 and message not in str(receipts[0][0])


def test_chat_execution_intent_flag_still_fails_closed_without_adapter(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, execution_requested=True) as client:
        csrf = login(client, "chat-run-adapter-intent@example.com")
        thread = create_thread(client, csrf)
        status = client.get("/api/v1/core/status")
        assert status.status_code == 200
        assert status.json()["data"]["flags"]["chat_execution_enabled"] is True
        response = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/runs",
            headers={"X-CSRF-Token": csrf},
            json=run_payload(thread, key="chat-run-intent-guarded-0001"),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True and body["status"] == "guarded"
        assert body["error_code"] == "WEB_CHAT_EXECUTION_ADAPTER_UNAVAILABLE"
        data = body["data"]
        assert data["run"]["state"] == "guarded"
        assert data["run"]["execution_requested"] is True
        assert_guarded_boundary(data, code="WEB_CHAT_EXECUTION_ADAPTER_UNAVAILABLE")
        assert data["assistant_message"] is None


def test_chat_run_history_is_newest_first_when_receipts_share_a_timestamp(tmp_path, monkeypatch):
    """SQLite timestamps are second-granularity, so UUID order is not chronology."""
    db_path = tmp_path / "chat-execution-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "chat-run-order@example.com")
        thread = create_thread(client, csrf)
        endpoint = f"/api/v1/chat-workspace/threads/{thread['id']}/runs"
        first = client.post(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json=run_payload(thread, key="chat-run-order-first-0001", message="Yêu cầu thứ nhất."),
        )
        assert first.status_code == 200
        first_data = first.json()["data"]
        second = client.post(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json=run_payload(
                first_data["thread"],
                key="chat-run-order-second-0001",
                message="Yêu cầu thứ hai.",
            ),
        )
        assert second.status_code == 200
        first_id = first_data["run"]["id"]
        second_id = second.json()["data"]["run"]["id"]

        # Force the realistic same-second collision and verify the listing uses
        # insertion order, not arbitrary UUID lexicographic order, as its tie
        # breaker. This is a read-model integrity test, not a provider test.
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_chat_runs SET updated_at=? WHERE id IN (?, ?)",
                ("2030-01-01T00:00:00+00:00", first_id, second_id),
            )
            conn.commit()

        listing = client.get(endpoint)
        assert listing.status_code == 200
        assert [item["id"] for item in listing.json()["data"]["items"][:2]] == [second_id, first_id]
