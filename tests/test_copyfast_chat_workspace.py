"""Critical contracts for the private, Web-native Conversation Workspace.

This suite is intentionally narrow: it proves signed ownership, CSRF, raw
body bounds, idempotency redaction, revision/lifecycle locking and the core
no-model/no-wallet/no-output boundary without exercising unrelated providers.
"""

from __future__ import annotations

import importlib
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


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "chat-workspace-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "chat-workspace-test-session-secret")
    monkeypatch.setenv("WEBAPP_CHAT_WORKSPACE_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Conversation Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def thread_payload(key: str, **overrides) -> dict:
    value = {
        "title": "Chiến lược nội dung quý ba",
        "objective": "Chuẩn bị câu hỏi, bối cảnh và quyết định của nhóm trước khi dùng engine đã được duyệt.",
        "mode": "focus",
        "system_context": "Dùng tiếng Việt rõ ràng, giữ các giả định có thể kiểm tra và không tự tạo output.",
        "tags": ["q3", "content"],
        "project_id": "",
        "prompt_template_id": "",
        "pinned": True,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_thread(client: TestClient, csrf: str, key: str = "chat-thread-create-0001", **overrides) -> dict:
    response = client.post("/api/v1/chat-workspace/threads", headers={"X-CSRF-Token": csrf}, json=thread_payload(key, **overrides))
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["thread"]


def assert_authoring_only(data: dict) -> None:
    assert data["execution"] == "authoring_only"
    for key in (
        "ai_execution_available", "provider_called", "bot_called", "assistant_reply_created", "output_created",
        "job_created", "payment_started", "wallet_mutated", "payment_processed", "browser_file_upload",
        "browser_media_url", "stream_available",
    ):
        assert data[key] is False
    assert data["output_delivery"] == "guarded"


def test_chat_workspace_session_csrf_body_cap_and_idempotency_redaction(tmp_path, monkeypatch):
    db_path = tmp_path / "chat-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/chat-workspace/summary").status_code == 401
        csrf = login(client, "chat-auth@example.com")
        raw = thread_payload("chat-thread-idempotency-0001")
        assert client.post("/api/v1/chat-workspace/threads", json=raw).status_code == 403
        too_large = client.post(
            "/api/v1/chat-workspace/threads",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"title":"' + (b"x" * (65 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_CHAT_WORKSPACE_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        assert_authoring_only(too_large.json()["data"])
        created = client.post("/api/v1/chat-workspace/threads", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        assert_authoring_only(created.json()["data"])
        created_thread = created.json()["data"]["thread"]
        replay = client.post("/api/v1/chat-workspace/threads", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200 and replay.json()["ok"] is True
        assert replay.json()["data"]["thread"]["id"] == created_thread["id"]
        assert replay.json()["data"]["thread"]["revision"] == created_thread["revision"]
        collision = client.post(
            "/api/v1/chat-workspace/threads",
            headers={"X-CSRF-Token": csrf},
            json=thread_payload("chat-thread-idempotency-0001", objective="Mục tiêu khác hoàn toàn."),
        )
        assert collision.status_code == 409
    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-chat-workspace:%'").fetchall()
    assert receipts
    for row in receipts:
        stored = str(row[0])
        assert raw["title"] not in stored
        assert raw["objective"] not in stored
        assert raw["system_context"] not in stored


def test_chat_workspace_owner_isolation_and_human_authored_records(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first_csrf = login(client, "chat-owner@example.com")
        thread = create_thread(client, first_csrf, "chat-owner-thread-0001")
        context = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/contexts",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "kind": "brief", "title": "Ngữ cảnh sản phẩm", "body": "Sản phẩm dành cho người bán hàng nhỏ cần workflow rõ ràng.",
                "tags": ["brief"], "expected_revision": thread["revision"], "idempotency_key": "chat-owner-context-0001",
            },
        )
        assert context.status_code == 200 and context.json()["ok"] is True
        assert_authoring_only(context.json()["data"])
        revised = context.json()["data"]["thread"]
        turn = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/turns",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "kind": "prompt", "body": "Liệt kê các giả định cần được kiểm chứng trước khi xây landing page.",
                "expected_revision": revised["revision"], "idempotency_key": "chat-owner-turn-0001",
            },
        )
        assert turn.status_code == 200 and turn.json()["ok"] is True
        assert turn.json()["data"]["turn"]["assistant_reply_created"] is False
        detail = client.get(f"/api/v1/chat-workspace/threads/{thread['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        assert len(detail.json()["data"]["contexts"]) == 1
        assert len(detail.json()["data"]["turns"]) == 1
        assert detail.json()["data"]["turns"][0]["kind"] == "prompt"
        assert_authoring_only(detail.json()["data"])
        second_csrf = login(client, "chat-other@example.com")
        hidden = client.get(f"/api/v1/chat-workspace/threads/{thread['id']}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_CHAT_WORKSPACE_NOT_FOUND"
        denied = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/turns",
            headers={"X-CSRF-Token": second_csrf},
            json={"kind": "note", "body": "Không được ghi vào thread khác.", "expected_revision": 3, "idempotency_key": "chat-cross-owner-turn-0001"},
        )
        assert denied.status_code == 200
        assert denied.json()["error_code"] == "WEB_CHAT_WORKSPACE_NOT_FOUND"


def test_chat_workspace_lifecycle_freezes_execution_and_rejects_untrusted_content(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "chat-lifecycle@example.com")
        markup = client.post(
            "/api/v1/chat-workspace/threads",
            headers={"X-CSRF-Token": csrf},
            json=thread_payload("chat-markup-thread-0001", objective="<img src=x onerror=alert(1)>"),
        )
        assert markup.status_code == 422
        assert_authoring_only(markup.json()["data"])
        secret = client.post(
            "/api/v1/chat-workspace/threads",
            headers={"X-CSRF-Token": csrf},
            json=thread_payload("chat-secret-thread-0001", system_context="bot token: 1234567890:AAE1_example_token_value_123456"),
        )
        assert secret.status_code == 422
        thread = create_thread(client, csrf, "chat-lifecycle-thread-0001")
        reviewed = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "review", "expected_revision": thread["revision"], "idempotency_key": "chat-lifecycle-review-0001"},
        )
        assert reviewed.status_code == 200 and reviewed.json()["ok"] is True
        assert reviewed.json()["data"]["thread"]["state"] == "review"
        frozen = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/turns",
            headers={"X-CSRF-Token": csrf},
            json={"kind": "prompt", "body": "Không được ghi khi đang review.", "expected_revision": reviewed.json()["data"]["thread"]["revision"], "idempotency_key": "chat-lifecycle-frozen-turn-0001"},
        )
        assert frozen.status_code == 200
        assert frozen.json()["error_code"] == "WEB_CHAT_WORKSPACE_REVIEW_LOCKED"
        execution = client.get(f"/api/v1/chat-workspace/threads/{thread['id']}/execution-status")
        assert execution.status_code == 200
        execution_body = execution.json()
        assert execution_body["ok"] is True
        assert execution_body["status"] == "guarded"
        assert execution_body["error_code"] == "WEB_CHAT_EXECUTION_GUARDED"
        assert execution_body["data"]["execution"] == {
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
            "guard_code": "WEB_CHAT_EXECUTION_GUARDED",
        }


def test_chat_workspace_disable_and_never_imports_legacy_engine(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "chat-disabled@example.com")
        guarded = client.get("/api/v1/chat-workspace/summary")
        assert guarded.status_code == 503
        assert "WEBAPP_CHAT_WORKSPACE_ENABLED" in guarded.text
        assert csrf
    source = (importlib.import_module("pathlib").Path(__file__).parents[1] / "copyfast_chat_workspace.py").read_text(encoding="utf-8")
    for forbidden in ("ai_assistant", "google.generativeai", "copyfast_bridge", "PayOS", "wallet", "provider"):
        assert f"import {forbidden}" not in source


def test_chat_workspace_rejects_url_path_and_sensitive_transport_text(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "chat-transport@example.com")
        unsafe_values = (
            "https://example.invalid/private?token=abc",
            "file:///C:/private/source.txt",
            "data:text/plain;base64,c2VjcmV0",
            "javascript:alert(1)",
            "blob:https://app.toanaas.vn/opaque",
            r"C:\Users\owner\private.txt",
            r"\\server\share\private.txt",
            "/srv/private/source.txt",
        )
        for index, unsafe in enumerate(unsafe_values, start=1):
            response = client.post(
                "/api/v1/chat-workspace/threads",
                headers={"X-CSRF-Token": csrf},
                json=thread_payload(f"chat-unsafe-transport-{index:04d}", objective=unsafe),
            )
            assert response.status_code == 422
            assert_authoring_only(response.json()["data"])
        query = client.get("/api/v1/chat-workspace/threads", params={"q": "https://example.invalid/secret"})
        assert query.status_code == 422
        assert query.headers["Cache-Control"] == "no-store, private"
        assert_authoring_only(query.json()["data"])


def test_chat_workspace_thread_library_is_filterable_and_paginated(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "chat-library@example.com")
        created = [
            create_thread(
                client,
                csrf,
                f"chat-library-thread-{number:04d}",
                title=f"Thư viện hội thoại {number}",
                objective=f"Mục tiêu thư viện số {number} chỉ là ghi chú Web-owned.",
            )
            for number in range(1, 4)
        ]

        first = client.get("/api/v1/chat-workspace/threads", params={"limit": 1, "offset": 0})
        assert first.status_code == 200 and first.json()["ok"] is True
        first_data = first.json()["data"]
        assert_authoring_only(first_data)
        assert first_data["pagination"] == {
            "total": 3, "limit": 1, "offset": 0, "returned": 1,
            "has_more": True, "next_offset": 1, "previous_offset": None,
        }
        assert len(first_data["items"]) == 1

        second = client.get("/api/v1/chat-workspace/threads", params={"limit": 1, "offset": 1})
        assert second.status_code == 200
        second_data = second.json()["data"]
        assert_authoring_only(second_data)
        assert second_data["pagination"]["offset"] == 1
        assert second_data["pagination"]["previous_offset"] == 0
        assert second_data["items"][0]["id"] != first_data["items"][0]["id"]

        clamped = client.get("/api/v1/chat-workspace/threads", params={"limit": 1, "offset": 999})
        assert clamped.status_code == 200
        clamped_data = clamped.json()["data"]
        assert_authoring_only(clamped_data)
        assert clamped_data["pagination"]["offset"] == 2
        assert clamped_data["pagination"]["has_more"] is False
        assert clamped_data["pagination"]["previous_offset"] == 1

        filtered = client.get(
            "/api/v1/chat-workspace/threads",
            params={"state": "draft", "q": "Thư viện hội thoại 2", "limit": 50, "offset": 0},
        )
        assert filtered.status_code == 200
        filtered_data = filtered.json()["data"]
        assert_authoring_only(filtered_data)
        assert filtered_data["filter"] == {"state": "draft", "q": "Thư viện hội thoại 2"}
        assert filtered_data["pagination"]["total"] == 1
        assert filtered_data["pagination"]["returned"] == 1
        assert filtered_data["items"][0]["id"] in {thread["id"] for thread in created}
        assert filtered_data["items"][0]["title"] == "Thư viện hội thoại 2"

        literal = create_thread(
            client,
            csrf,
            "chat-library-literal-search-0001",
            title="Mốc 100%_literal",
            objective="Kiểm tra ký tự LIKE phải được tìm theo nghĩa chữ, không thành wildcard.",
        )
        literal_search = client.get(
            "/api/v1/chat-workspace/threads",
            params={"q": "100%_literal", "limit": 50, "offset": 0},
        )
        assert literal_search.status_code == 200
        literal_data = literal_search.json()["data"]
        assert_authoring_only(literal_data)
        assert literal_data["pagination"]["total"] == 1
        assert literal_data["items"][0]["id"] == literal["id"]


def test_chat_workspace_revision_child_records_and_stale_reference_are_safe(tmp_path, monkeypatch):
    db_path = tmp_path / "chat-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "chat-revisions@example.com")
        project_created = client.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Project tham chiếu Chat", "summary": "Brief riêng tư", "objective": "Rà soát context",
                "idempotency_key": "chat-reference-project-0001",
            },
        )
        assert project_created.status_code == 200
        project_id = project_created.json()["data"]["project"]["id"]
        thread = create_thread(client, csrf, "chat-revision-thread-0001", project_id=project_id)

        context_body = "Ràng buộc: không tự nhận có output hoặc quote AI."
        context = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/contexts",
            headers={"X-CSRF-Token": csrf},
            json={
                "kind": "constraint", "title": "Ràng buộc phát hành", "body": context_body, "tags": ["policy"],
                "expected_revision": thread["revision"], "idempotency_key": "chat-revision-context-0001",
            },
        )
        assert context.status_code == 200
        context_receipt = context.json()["data"]["context"]
        revision = context.json()["data"]["thread"]["revision"]
        turn_body = "Quyết định: chỉ handoff khi có adapter Web được kiểm định."
        turn = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/turns",
            headers={"X-CSRF-Token": csrf},
            json={
                "kind": "decision", "body": turn_body, "expected_revision": revision,
                "idempotency_key": "chat-revision-turn-0001",
            },
        )
        assert turn.status_code == 200
        turn_receipt = turn.json()["data"]["turn"]
        revision = turn.json()["data"]["thread"]["revision"]

        stale = client.patch(
            f"/api/v1/chat-workspace/threads/{thread['id']}/contexts/{context_receipt['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                "kind": "constraint", "title": "Ràng buộc cũ", "body": "Không được lưu khi revision đã stale.", "tags": [],
                "expected_revision": revision - 1, "idempotency_key": "chat-revision-context-stale-0001",
            },
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_CHAT_WORKSPACE_REVISION_CONFLICT"

        for endpoint, payload, state_key in (
            (f"/api/v1/chat-workspace/threads/{thread['id']}/contexts/{context_receipt['id']}/state", "archived", "context"),
            (f"/api/v1/chat-workspace/threads/{thread['id']}/turns/{turn_receipt['id']}/state", "archived", "turn"),
            (f"/api/v1/chat-workspace/threads/{thread['id']}/contexts/{context_receipt['id']}/state", "active", "context"),
            (f"/api/v1/chat-workspace/threads/{thread['id']}/turns/{turn_receipt['id']}/state", "active", "turn"),
        ):
            changed = client.post(
                endpoint,
                headers={"X-CSRF-Token": csrf},
                json={"state": payload, "expected_revision": revision, "idempotency_key": f"chat-{state_key}-{payload}-{revision:04d}"},
            )
            assert changed.status_code == 200 and changed.json()["ok"] is True
            revision = changed.json()["data"]["thread"]["revision"]

        updated = client.patch(
            f"/api/v1/chat-workspace/threads/{thread['id']}",
            headers={"X-CSRF-Token": csrf},
            json=thread_payload(
                "chat-revision-thread-update-0001", title="Thread đã biên tập", project_id=project_id,
                expected_revision=revision,
            ),
        )
        assert updated.status_code == 200
        revision = updated.json()["data"]["thread"]["revision"]
        restored = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/restore-version",
            headers={"X-CSRF-Token": csrf},
            json={"target_revision": 1, "expected_revision": revision, "idempotency_key": "chat-revision-restore-v1-0001"},
        )
        assert restored.status_code == 200
        revision = restored.json()["data"]["thread"]["revision"]
        assert client.get(f"/api/v1/chat-workspace/threads/{thread['id']}").json()["data"]["thread"]["title"] == "Chiến lược nội dung quý ba"

        review = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "review", "expected_revision": revision, "idempotency_key": "chat-revision-review-0001"},
        )
        assert review.status_code == 200
        revision = review.json()["data"]["thread"]["revision"]
        ready = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "ready", "expected_revision": revision, "idempotency_key": "chat-revision-ready-0001"},
        )
        assert ready.status_code == 200
        revision = ready.json()["data"]["thread"]["revision"]
        draft = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "draft", "expected_revision": revision, "idempotency_key": "chat-revision-draft-0001"},
        )
        assert draft.status_code == 200
        revision = draft.json()["data"]["thread"]["revision"]
        archived = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "archived", "expected_revision": revision, "idempotency_key": "chat-revision-archive-0001"},
        )
        assert archived.status_code == 200
        revision = archived.json()["data"]["thread"]["revision"]

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_projects SET state='archived' WHERE id=?", (project_id,))
            conn.commit()
        blocked = client.post(
            f"/api/v1/chat-workspace/threads/{thread['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "draft", "expected_revision": revision, "idempotency_key": "chat-revision-stale-reference-0001"},
        )
        assert blocked.status_code == 422
        assert_authoring_only(blocked.json()["data"])
        unchanged = client.get(f"/api/v1/chat-workspace/threads/{thread['id']}").json()["data"]["thread"]
        assert unchanged["state"] == "archived" and unchanged["revision"] == revision

    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-chat-workspace:%'").fetchall()
    assert receipts
    for row in receipts:
        assert context_body not in str(row[0])
        assert turn_body not in str(row[0])
