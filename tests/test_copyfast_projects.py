"""Contract tests for the independent Web Project Center."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_document_operations",
]


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-projects-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-project-session-secret")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Web Workspace"},
    )
    assert registered.status_code == 200
    assert registered.json()["ok"] is True
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def test_project_center_is_web_owned_versioned_and_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "project-owner@example.com")
        # The professional Web Workspace starts without a Telegram link or
        # bridge; signed ownership and CSRF are sufficient for Web-native work.
        assert first.get("/dashboard").status_code == 200
        denied = first.post(
            "/api/v1/projects",
            json={"title": "Ra mắt mùa hè", "summary": "Brief Web", "objective": "Chuyển đổi", "idempotency_key": "project-create-web-0001"},
        )
        assert denied.status_code == 403
        create_payload = {"title": "Ra mắt mùa hè", "summary": "Brief Web", "objective": "Chuyển đổi", "idempotency_key": "project-create-web-0001"}
        created = first.post("/api/v1/projects", headers={"X-CSRF-Token": csrf}, json=create_payload)
        assert created.status_code == 200
        assert created.json()["status"] == "completed"
        project = created.json()["data"]["project"]
        replay = first.post("/api/v1/projects", headers={"X-CSRF-Token": csrf}, json=create_payload)
        assert replay.json()["data"]["project"]["id"] == project["id"]

        document_payload = {
            "kind": "storyboard",
            "title": "Storyboard mở đầu",
            "content": "Cảnh 1: vấn đề.\nCảnh 2: giải pháp.\nCảnh 3: CTA.",
            "idempotency_key": "project-document-create-0001",
        }
        document_response = first.post(
            f"/api/v1/projects/{project['id']}/documents",
            headers={"X-CSRF-Token": csrf},
            json=document_payload,
        )
        assert document_response.status_code == 200
        document = document_response.json()["data"]["document"]
        assert document["revision"] == 1
        assert document["state"] == "active"

        listing = first.get("/api/v1/projects")
        assert listing.json()["data"]["items"][0]["document_count"] == 1
        detail = first.get(f"/api/v1/projects/{project['id']}")
        assert detail.json()["data"]["documents"][0]["id"] == document["id"]
        document_detail = first.get(f"/api/v1/projects/documents/{document['id']}")
        assert document_detail.json()["data"]["document"]["content"] == document_payload["content"]
        assert document_detail.json()["data"]["versions"] == [{"revision": 1, "title": "Storyboard mở đầu", "created_at": document["created_at"]}]

        update_payload = {
            "title": "Storyboard mở đầu đã rà soát",
            "content": "Cảnh 1: vấn đề rõ ràng.\nCảnh 2: giải pháp.\nCảnh 3: CTA an toàn.",
            "expected_revision": 1,
            "idempotency_key": "project-document-update-0001",
        }
        updated = first.patch(
            f"/api/v1/projects/documents/{document['id']}",
            headers={"X-CSRF-Token": csrf},
            json=update_payload,
        )
        assert updated.json()["data"]["document"]["revision"] == 2
        replay_update = first.patch(
            f"/api/v1/projects/documents/{document['id']}",
            headers={"X-CSRF-Token": csrf},
            json=update_payload,
        )
        assert replay_update.json()["data"]["document"]["revision"] == 2
        conflict = first.patch(
            f"/api/v1/projects/documents/{document['id']}",
            headers={"X-CSRF-Token": csrf},
            json={**update_payload, "title": "Ghi đè lỗi", "expected_revision": 1, "idempotency_key": "project-document-conflict-0001"},
        )
        assert conflict.json()["ok"] is False
        assert conflict.json()["error_code"] == "STUDIO_DOCUMENT_CONFLICT"
        assert conflict.json()["data"]["current_revision"] == 2

        restored = first.post(
            f"/api/v1/projects/documents/{document['id']}/restore/1",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "project-document-restore-0001"},
        )
        restored_document = restored.json()["data"]["document"]
        assert restored_document["revision"] == 3
        assert restored_document["content"] == document_payload["content"]

        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            audits = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action LIKE 'web.%' ORDER BY rowid"
            ).fetchall()
        assert audits
        assert all("Storyboard" not in row[1] and "Cảnh" not in row[1] for row in audits)

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "project-other@example.com")
            hidden_project = second.get(f"/api/v1/projects/{project['id']}")
            assert hidden_project.json()["error_code"] == "WEB_PROJECT_NOT_FOUND"
            assert "Ra mắt mùa hè" not in hidden_project.text
            hidden_document = second.get(f"/api/v1/projects/documents/{document['id']}")
            assert hidden_document.json()["error_code"] == "STUDIO_DOCUMENT_NOT_FOUND"
            assert "Cảnh 1" not in hidden_document.text
            denied_update = second.patch(
                f"/api/v1/projects/documents/{document['id']}",
                headers={"X-CSRF-Token": csrf_second},
                json={"title": "Không thuộc owner", "content": "Không được phép", "expected_revision": 3, "idempotency_key": "project-document-other-0001"},
            )
            assert denied_update.json()["error_code"] == "STUDIO_DOCUMENT_NOT_FOUND"


def test_project_center_rejects_sensitive_content_invalid_kind_and_archived_writes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "project-safety@example.com")
        project = client.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={"title": "Project an toàn", "summary": "", "objective": "", "idempotency_key": "project-safety-create-0001"},
        ).json()["data"]["project"]
        sensitive = client.post(
            f"/api/v1/projects/{project['id']}/documents",
            headers={"X-CSRF-Token": csrf},
            json={"kind": "prompt", "title": "Không lưu secret", "content": "api_key=sk_1234567890abcdefghi", "idempotency_key": "project-secret-content-0001"},
        )
        assert sensitive.status_code == 422
        invalid_kind = client.post(
            f"/api/v1/projects/{project['id']}/documents",
            headers={"X-CSRF-Token": csrf},
            json={"kind": "provider_job", "title": "Không hợp lệ", "content": "Nội dung an toàn", "idempotency_key": "project-invalid-kind-0001"},
        )
        assert invalid_kind.status_code == 422
        archived = client.patch(
            f"/api/v1/projects/{project['id']}",
            headers={"X-CSRF-Token": csrf},
            json={"title": project["title"], "summary": "", "objective": "", "state": "archived", "idempotency_key": "project-archive-0001"},
        )
        assert archived.json()["data"]["project"]["state"] == "archived"
        blocked = client.post(
            f"/api/v1/projects/{project['id']}/documents",
            headers={"X-CSRF-Token": csrf},
            json={"kind": "brief", "title": "Không thêm vào archived", "content": "Nội dung hợp lệ", "idempotency_key": "project-archived-doc-0001"},
        )
        assert blocked.json()["error_code"] == "WEB_PROJECT_ARCHIVED"


def test_project_center_has_no_bot_bridge_or_payment_dependency():
    source = open("copyfast_projects.py", encoding="utf-8").read()
    assert "from copyfast_bridge" not in source
    assert "import copyfast_bridge" not in source
    assert "bridge_request" not in source
