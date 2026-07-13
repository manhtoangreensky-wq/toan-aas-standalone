"""Contract tests for the private, Web-owned Memory Center."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_memory",
]


def make_client(tmp_path, monkeypatch, *, memory_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-memory-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-memory-session-secret")
    monkeypatch.setenv("WEBAPP_MEMORY_CENTER_ENABLED", "true" if memory_enabled else "false")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Memory Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def note_payload(key: str, **overrides) -> dict:
    payload = {
        "title": "Kế hoạch video mùa hè",
        "content": "Chốt hook, storyboard và CTA trước buổi quay.",
        "tags": ["video", "launch"],
        "category": "Marketing",
        "priority": "important",
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def future_local(minutes: int = 45) -> str:
    # The API intentionally treats an offset-free datetime as wall-clock time
    # in the caller's declared `Asia/Ho_Chi_Minh` zone.
    from zoneinfo import ZoneInfo

    value = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")) + timedelta(minutes=minutes)
    return value.strftime("%Y-%m-%dT%H:%M")


def test_memory_notes_are_versioned_idempotent_and_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "memory-owner@example.com")
        denied = first.post("/api/v1/memory/notes", json=note_payload("memory-note-create-0001"))
        assert denied.status_code == 403

        payload = note_payload("memory-note-create-0001")
        created = first.post("/api/v1/memory/notes", headers={"X-CSRF-Token": csrf}, json=payload)
        assert created.status_code == 200
        note = created.json()["data"]["note"]
        assert note["revision"] == 1
        assert "content" not in note
        replay = first.post("/api/v1/memory/notes", headers={"X-CSRF-Token": csrf}, json=payload)
        assert replay.json()["data"]["note"]["id"] == note["id"]
        collision = first.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-note-create-0001", title="Một ghi chú khác"),
        )
        assert collision.status_code == 409

        listing = first.get("/api/v1/memory/notes?state=all")
        listed = listing.json()["data"]["items"]
        assert listed[0]["id"] == note["id"]
        assert "content" not in listed[0]
        detail = first.get(f"/api/v1/memory/notes/{note['id']}")
        assert detail.json()["data"]["note"]["content"] == payload["content"]
        assert detail.json()["data"]["versions"] == [{"revision": 1, "title": payload["title"], "created_at": note["created_at"]}]

        update = first.post(
            f"/api/v1/memory/notes/{note['id']}/update",
            headers={"X-CSRF-Token": csrf},
            json=note_payload(
                "memory-note-update-0001",
                title="Kế hoạch video đã rà soát",
                content="Hook đã chốt, storyboard đã rà soát và CTA đã kiểm tra.",
                expected_revision=1,
            ),
        )
        assert update.status_code == 200
        assert update.json()["data"]["note"]["revision"] == 2
        conflict = first.post(
            f"/api/v1/memory/notes/{note['id']}/update",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-note-conflict-0001", expected_revision=1),
        )
        assert conflict.json()["error_code"] == "WEB_MEMORY_NOTE_CONFLICT"

        restored = first.post(
            f"/api/v1/memory/notes/{note['id']}/restore-version/1",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "memory-note-restore-v1-0001"},
        )
        restored_note = restored.json()["data"]["note"]
        assert restored_note["revision"] == 3
        assert restored_note["title"] == payload["title"]

        archived = first.post(
            f"/api/v1/memory/notes/{note['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 3, "idempotency_key": "memory-note-archive-0001"},
        )
        assert archived.json()["data"]["note"]["state"] == "archived"
        restored_active = first.post(
            f"/api/v1/memory/notes/{note['id']}/restore",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 4, "idempotency_key": "memory-note-unarchive-0001"},
        )
        assert restored_active.json()["data"]["note"]["state"] == "active"

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "memory-other@example.com")
            hidden = second.get(f"/api/v1/memory/notes/{note['id']}")
            assert hidden.json()["error_code"] == "WEB_MEMORY_NOTE_NOT_FOUND"
            assert payload["content"] not in hidden.text
            denied_update = second.post(
                f"/api/v1/memory/notes/{note['id']}/update",
                headers={"X-CSRF-Token": csrf_second},
                json=note_payload("memory-note-other-0001", expected_revision=5),
            )
            assert denied_update.json()["error_code"] == "WEB_MEMORY_NOTE_NOT_FOUND"


def test_memory_reminders_keep_explicit_lifecycle_without_delivery_claims(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "memory-reminder@example.com")
        note = client.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-reminder-note-0001"),
        ).json()["data"]["note"]

        recurring_payload = {
            "note_id": note["id"],
            "title": "Rà soát storyboard",
            "body": "Kiểm tra nhịp, CTA và phụ đề.",
            "due_at": future_local(),
            "timezone": "Asia/Ho_Chi_Minh",
            "repeat_rule": "weekly",
            "idempotency_key": "memory-reminder-create-0001",
        }
        recurring = client.post("/api/v1/memory/reminders", headers={"X-CSRF-Token": csrf}, json=recurring_payload)
        assert recurring.status_code == 200
        reminder = recurring.json()["data"]["reminder"]
        assert reminder["state"] == "active"
        assert reminder["note_id"] == note["id"]
        replay = client.post("/api/v1/memory/reminders", headers={"X-CSRF-Token": csrf}, json=recurring_payload)
        assert replay.json()["data"]["reminder"]["id"] == reminder["id"]

        paused = client.post(
            f"/api/v1/memory/reminders/{reminder['id']}/pause",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "memory-reminder-pause-0001"},
        )
        assert paused.json()["data"]["reminder"]["state"] == "paused"
        resumed = client.post(
            f"/api/v1/memory/reminders/{reminder['id']}/resume",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "memory-reminder-resume-0001"},
        )
        assert resumed.json()["data"]["reminder"]["state"] == "active"
        completed = client.post(
            f"/api/v1/memory/reminders/{reminder['id']}/complete",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 3, "idempotency_key": "memory-reminder-complete-0001"},
        )
        completed_item = completed.json()["data"]["reminder"]
        assert completed_item["state"] == "active"
        assert completed_item["last_completed_at"]
        assert completed_item["completed_at"] is None
        assert completed_item["next_run_at"] > reminder["next_run_at"]

        one_time = client.post(
            "/api/v1/memory/reminders",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Đọc lại brief", "body": "", "due_at": future_local(90), "timezone": "UTC", "repeat_rule": "none",
                "idempotency_key": "memory-reminder-once-0001",
            },
        ).json()["data"]["reminder"]
        terminal = client.post(
            f"/api/v1/memory/reminders/{one_time['id']}/complete",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "memory-reminder-once-complete-0001"},
        )
        assert terminal.json()["data"]["reminder"]["state"] == "completed"

        cancelled = client.post(
            f"/api/v1/memory/reminders/{reminder['id']}/cancel",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 4, "idempotency_key": "memory-reminder-cancel-0001"},
        )
        assert cancelled.json()["data"]["reminder"]["state"] == "cancelled"
        listing = client.get("/api/v1/memory/reminders?state=all")
        assert listing.json()["data"]["notification_delivery"] == "web_view_only"
        assert client.get("/api/v1/memory/summary").json()["data"]["notification_delivery"] == "web_view_only"
        assert client.post(
            "/api/v1/memory/reminders",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Quá khứ", "body": "", "due_at": "2001-01-01T09:00", "timezone": "Asia/Ho_Chi_Minh", "repeat_rule": "none",
                "idempotency_key": "memory-reminder-past-0001",
            },
        ).status_code == 422


def test_memory_rejects_sensitive_content_and_keeps_audit_sanitized(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "memory-safety@example.com")
        sensitive = client.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-note-secret-0001", content="api_key=sk_1234567890abcdefghi"),
        )
        assert sensitive.status_code == 422
        sensitive_title = client.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-note-secret-title-0001", title="token=abcdefghijklmno"),
        )
        assert sensitive_title.status_code == 422
        sensitive_category = client.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-note-secret-category-0001", category="card 4242 4242 4242 4242"),
        )
        assert sensitive_category.status_code == 422
        title = "Nội dung kín không được audit"
        content = "Chuỗi nội dung chỉ thuộc ghi chú riêng tư."
        note = client.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-note-audit-0001", title=title, content=content),
        ).json()["data"]["note"]
        with sqlite3.connect(tmp_path / "copyfast-memory-test.db") as conn:
            audit_rows = conn.execute("SELECT detail FROM web_audit_events WHERE action LIKE 'web.memory.%'").fetchall()
        assert audit_rows
        assert all(title not in row[0] and content not in row[0] for row in audit_rows)
        source = open("copyfast_memory.py", encoding="utf-8").read().lower()
        assert "copyfast_bridge" not in source
        assert "payos" not in source
        assert "wallet" not in source
        assert "telegram_send" not in source
        # The module may describe its no-provider policy in prose, but it must
        # not import or invoke a provider integration.
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "provider_request" not in source
        assert note["id"]


def test_memory_search_filters_and_reminder_update_are_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "memory-filter@example.com")
        first = client.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-filter-note-0001", title="Kế hoạch launch mùa thu", category="Marketing", priority="urgent"),
        ).json()["data"]["note"]
        second = client.post(
            "/api/v1/memory/notes",
            headers={"X-CSRF-Token": csrf},
            json=note_payload("memory-filter-note-0002", title="Checklist hậu kỳ", content="Rà soát màu sắc và phụ đề sau khi dựng.", tags=["hauky"], category="Video", priority="normal"),
        ).json()["data"]["note"]

        by_query = client.get("/api/v1/memory/notes", params={"state": "all", "q": "launch"})
        assert [item["id"] for item in by_query.json()["data"]["items"]] == [first["id"]]
        by_priority = client.get("/api/v1/memory/notes", params={"state": "all", "priority": "normal"})
        assert [item["id"] for item in by_priority.json()["data"]["items"]] == [second["id"]]
        assert client.get("/api/v1/memory/notes", params={"q": "x" * 81}).status_code == 422
        assert client.get("/api/v1/memory/notes", params={"q": "api_key=sk_1234567890abcdefghi"}).status_code == 422

        reminder = client.post(
            "/api/v1/memory/reminders",
            headers={"X-CSRF-Token": csrf},
            json={
                "note_id": first["id"], "title": "Chốt kịch bản", "body": "Kiểm tra CTA", "due_at": future_local(90),
                "timezone": "Asia/Ho_Chi_Minh", "repeat_rule": "none", "idempotency_key": "memory-update-reminder-0001",
            },
        ).json()["data"]["reminder"]
        updated = client.post(
            f"/api/v1/memory/reminders/{reminder['id']}/update",
            headers={"X-CSRF-Token": csrf},
            json={
                "note_id": second["id"], "title": "Chốt kịch bản bản mới", "body": "Kiểm tra CTA và phụ đề", "due_at": future_local(120),
                "timezone": "Asia/Ho_Chi_Minh", "repeat_rule": "daily", "expected_revision": 1,
                "idempotency_key": "memory-update-reminder-0002",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["reminder"]["revision"] == 2
        assert updated.json()["data"]["reminder"]["note_id"] == second["id"]

        archived = client.post(
            f"/api/v1/memory/notes/{second['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "memory-filter-archive-0001"},
        )
        assert archived.status_code == 200
        blocked = client.post(
            f"/api/v1/memory/reminders/{reminder['id']}/update",
            headers={"X-CSRF-Token": csrf},
            json={
                "note_id": second["id"], "title": "Không được cập nhật", "body": "", "due_at": future_local(150),
                "timezone": "Asia/Ho_Chi_Minh", "repeat_rule": "daily", "expected_revision": 2,
                "idempotency_key": "memory-update-reminder-archived-0001",
            },
        )
        assert blocked.json()["error_code"] == "WEB_MEMORY_NOTE_NOT_FOUND"


def test_memory_flag_fails_closed(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, memory_enabled=False) as client:
        register_and_login(client, "memory-disabled@example.com")
        response = client.get("/api/v1/memory/summary")
        assert response.status_code == 503
        assert response.json()["ok"] is False
