"""Contract tests for the independent Web Project Center."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_workspace_draft_contract", "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
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
        secret_key = client.post(
            f"/api/v1/projects/{project['id']}/documents",
            headers={"X-CSRF-Token": csrf},
            json={"kind": "prompt", "title": "Không lưu secret key", "content": "secret_key: abcdefghijkl", "idempotency_key": "project-secret-key-content-0001"},
        )
        assert secret_key.status_code == 422
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


def test_workspace_draft_attach_creates_one_owner_scoped_snapshot(tmp_path, monkeypatch):
    """A Web draft can be handed to Project Studio exactly once per pair."""
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "handoff-owner@example.com")
        project = first.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Project handoff",
                "summary": "Workspace summary",
                "objective": "Studio snapshot",
                "idempotency_key": "handoff-project-create-0001",
            },
        ).json()["data"]["project"]
        draft = first.post(
            "/api/v1/workspace/drafts",
            headers={"X-CSRF-Token": csrf},
            json={
                "feature_key": "video_product",
                "title": "Video ra mắt handoff",
                "input": {"brief": "Brief giữ nguyên", "platform": "TikTok", "format": "9:16"},
                "idempotency_key": "handoff-draft-create-0001",
            },
        ).json()["data"]["item"]
        attach_payload = {"confirmed": True, "idempotency_key": "handoff-attach-request-0001"}
        denied = first.post(
            f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach",
            json=attach_payload,
        )
        assert denied.status_code == 403

        attached = first.post(
            f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload,
        )
        assert attached.status_code == 200
        body = attached.json()
        assert body["ok"] is True
        assert body["status"] == "completed"
        receipt = body["data"]
        assert receipt["project"]["id"] == project["id"]
        assert receipt["draft"]["id"] == draft["id"]
        assert receipt["document"]["revision"] == 1
        assert receipt["document"]["kind"] == "brief"
        assert "content" not in receipt["document"]
        document_detail = first.get(f"/api/v1/projects/documents/{receipt['document']['id']}")
        assert "Brief giữ nguyên" in document_detail.json()["data"]["document"]["content"]
        assert "platform: TikTok" in document_detail.json()["data"]["document"]["content"]

        # A different client retry key must still resolve the same durable handoff.
        replay = first.post(
            f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach",
            headers={"X-CSRF-Token": csrf},
            json={"confirmed": True, "idempotency_key": "handoff-attach-request-0002"},
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["document"]["id"] == receipt["document"]["id"]
        project_detail = first.get(f"/api/v1/projects/{project['id']}").json()["data"]
        assert project_detail["project"]["document_count"] == 1
        assert [item["id"] for item in project_detail["documents"]] == [receipt["document"]["id"]]
        # The source draft remains active and unchanged after the one-way snapshot.
        source = first.get(f"/api/v1/workspace/drafts/{draft['id']}").json()["data"]["item"]
        assert source["state"] == "active"
        assert source["input"] == {"brief": "Brief giữ nguyên", "platform": "TikTok", "format": "9:16"}

        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            handoffs = conn.execute(
                "SELECT account_id, project_id, draft_id, document_id FROM web_workspace_draft_handoffs"
            ).fetchall()
            audits = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action='web.workspace_draft.attach'"
            ).fetchall()
        assert len(handoffs) == 1
        assert len(audits) == 1
        assert audits[0][0] == receipt["document"]["id"]
        assert "Brief giữ nguyên" not in audits[0][1]


def test_workspace_draft_attach_guards_ownership_archived_and_corrupt_rows(tmp_path, monkeypatch):
    """Attach fails closed for foreign, archived or malformed Web-owned rows."""
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "handoff-guards-owner@example.com")
        project = owner.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={"title": "Guard project", "idempotency_key": "handoff-guard-project-0001"},
        ).json()["data"]["project"]
        draft = owner.post(
            "/api/v1/workspace/drafts",
            headers={"X-CSRF-Token": csrf},
            json={
                "feature_key": "voice_tts",
                "title": "Voice draft",
                "input": {"brief": "Xin chào"},
                "idempotency_key": "handoff-guard-draft-0001",
            },
        ).json()["data"]["item"]

        with make_client(tmp_path, monkeypatch) as other:
            other_csrf = register_and_login(other, "handoff-guards-other@example.com")
            foreign = other.post(
                f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach",
                headers={"X-CSRF-Token": other_csrf},
                json={"confirmed": True, "idempotency_key": "handoff-foreign-attach-0001"},
            )
            assert foreign.status_code == 200
            assert foreign.json()["error_code"] == "WEB_PROJECT_NOT_FOUND"

        archived = owner.post(
            f"/api/v1/workspace/drafts/{draft['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "handoff-guard-archive-0001"},
        )
        assert archived.json()["status"] == "archived"
        blocked = owner.post(
            f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach",
            headers={"X-CSRF-Token": csrf},
            json={"confirmed": True, "idempotency_key": "handoff-archived-attach-0001"},
        )
        assert blocked.json()["error_code"] == "WORKSPACE_DRAFT_ARCHIVED"

        malformed = owner.post(
            "/api/v1/workspace/drafts",
            headers={"X-CSRF-Token": csrf},
            json={
                "feature_key": "video_product",
                "title": "Malformed draft",
                "input": {"brief": "valid before corruption"},
                "idempotency_key": "handoff-corrupt-draft-0001",
            },
        ).json()["data"]["item"]
        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            conn.execute(
                "UPDATE web_workspace_drafts SET input_json=? WHERE id=?",
                ('{"forbidden_field":"should fail closed"}', malformed["id"]),
            )
            conn.commit()
        corrupt = owner.post(
            f"/api/v1/projects/{project['id']}/workspace-drafts/{malformed['id']}/attach",
            headers={"X-CSRF-Token": csrf},
            json={"confirmed": True, "idempotency_key": "handoff-corrupt-attach-0001"},
        )
        assert corrupt.json()["error_code"] == "WORKSPACE_DRAFT_INVALID"


def test_workspace_draft_attach_rejects_unregistered_corrupt_feature_without_side_effects(tmp_path, monkeypatch):
    """A repaired DB row cannot turn an arbitrary workflow into a Studio snapshot."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "handoff-feature-boundary@example.com")
        project = client.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={"title": "Feature boundary project", "idempotency_key": "handoff-feature-project-0001"},
        ).json()["data"]["project"]
        draft = client.post(
            "/api/v1/workspace/drafts",
            headers={"X-CSRF-Token": csrf},
            json={
                "feature_key": "video_product",
                "title": "Registered draft before corruption",
                "input": {"brief": "A safe brief that remains valid"},
                "idempotency_key": "handoff-feature-draft-0001",
            },
        ).json()["data"]["item"]

        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            conn.execute(
                "UPDATE web_workspace_drafts SET feature_key=? WHERE id=?",
                ("arbitrary_feature", draft["id"]),
            )
            conn.commit()

        rejected = client.post(
            f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach",
            headers={"X-CSRF-Token": csrf},
            json={"confirmed": True, "idempotency_key": "handoff-feature-attach-0001"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["ok"] is False
        assert rejected.json()["status"] == "guarded"
        assert rejected.json()["error_code"] == "WORKSPACE_DRAFT_INVALID"

        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_studio_documents").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM web_studio_document_versions").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM web_workspace_draft_handoffs").fetchone()[0] == 0
            assert conn.execute(
                "SELECT COUNT(*) FROM web_audit_events WHERE action='web.workspace_draft.attach'"
            ).fetchone()[0] == 0


def test_workspace_draft_attach_requires_strict_confirmation_without_side_effects(tmp_path, monkeypatch):
    """Only a JSON boolean true can create an otherwise-valid Studio snapshot."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "handoff-confirm-owner@example.com")
        project = client.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={"title": "Confirmation project", "idempotency_key": "handoff-confirm-project-0001"},
        ).json()["data"]["project"]
        draft = client.post(
            "/api/v1/workspace/drafts",
            headers={"X-CSRF-Token": csrf},
            json={
                "feature_key": "video_product",
                "title": "Confirmation draft",
                "input": {"brief": "A valid handoff brief"},
                "idempotency_key": "handoff-confirm-draft-0001",
            },
        ).json()["data"]["item"]
        endpoint = f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach"

        rejected_payloads = (
            {"idempotency_key": "handoff-confirm-missing-0001"},
            {"confirmed": False, "idempotency_key": "handoff-confirm-false-0001"},
            {"confirmed": "true", "idempotency_key": "handoff-confirm-string-0001"},
            {"confirmed": 1, "idempotency_key": "handoff-confirm-number-0001"},
        )
        for payload in rejected_payloads:
            rejected = client.post(endpoint, headers={"X-CSRF-Token": csrf}, json=payload)
            assert rejected.status_code == 422

        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_studio_documents").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM web_workspace_draft_handoffs").fetchone()[0] == 0
            assert conn.execute(
                "SELECT COUNT(*) FROM web_audit_events WHERE action='web.workspace_draft.attach'"
            ).fetchone()[0] == 0

        accepted = client.post(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json={"confirmed": True, "idempotency_key": "handoff-confirm-accepted-0001"},
        )
        assert accepted.status_code == 200
        assert accepted.json()["ok"] is True


def test_workspace_draft_attach_rejects_sensitive_corrupt_snapshot_rows(tmp_path, monkeypatch):
    """A damaged persisted draft cannot smuggle credentials or payment proof into Studio."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "handoff-sensitive-owner@example.com")
        project = client.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={"title": "Sensitive guard project", "idempotency_key": "handoff-sensitive-project-0001"},
        ).json()["data"]["project"]
        corrupt_rows = []
        for index, corrupted_input in enumerate((
            '{"brief":"Bearer abcdefghijkl"}',
            '{"notes":"Mã giao dịch: 123456"}',
            '{"notes":"secret_key: abcdefghijkl"}',
        ), start=1):
            draft = client.post(
                "/api/v1/workspace/drafts",
                headers={"X-CSRF-Token": csrf},
                json={
                    "feature_key": "video_product",
                    "title": f"Sensitive draft {index}",
                    "input": {"brief": "Valid before database corruption"},
                    "idempotency_key": f"handoff-sensitive-draft-{index:04d}",
                },
            ).json()["data"]["item"]
            corrupt_rows.append((draft, corrupted_input))

        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            for draft, corrupted_input in corrupt_rows:
                conn.execute(
                    "UPDATE web_workspace_drafts SET input_json=? WHERE id=?",
                    (corrupted_input, draft["id"]),
                )
            conn.commit()

        for index, (draft, _corrupted_input) in enumerate(corrupt_rows, start=1):
            rejected = client.post(
                f"/api/v1/projects/{project['id']}/workspace-drafts/{draft['id']}/attach",
                headers={"X-CSRF-Token": csrf},
                json={"confirmed": True, "idempotency_key": f"handoff-sensitive-attach-{index:04d}"},
            )
            assert rejected.status_code == 200
            assert rejected.json()["ok"] is False
            assert rejected.json()["error_code"] == "WORKSPACE_DRAFT_INVALID"

        with sqlite3.connect(tmp_path / "copyfast-projects-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_studio_documents").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM web_workspace_draft_handoffs").fetchone()[0] == 0
            assert conn.execute(
                "SELECT COUNT(*) FROM web_audit_events WHERE action='web.workspace_draft.attach'"
            ).fetchone()[0] == 0


def test_project_list_filter_pagination_and_owner_scope(tmp_path, monkeypatch):
    """Project search stays server-side, bounded and private to its owner."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "project-listing@example.com")
        created = []
        for index, title in enumerate(("Portfolio 2026 Alpha", "Portfolio 2026 Beta", "Portfolio 2026 Archive"), start=1):
            response = client.post(
                "/api/v1/projects",
                headers={"X-CSRF-Token": csrf},
                json={
                    "title": title,
                    "summary": "Danh sách Project owner-scoped",
                    "objective": "Kiểm tra bộ lọc",
                    "idempotency_key": f"project-list-create-{index:04d}",
                },
            )
            assert response.status_code == 200
            created.append(response.json()["data"]["project"])

        archived = created[-1]
        archived_response = client.patch(
            f"/api/v1/projects/{archived['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": archived["title"],
                "summary": archived["summary"],
                "objective": archived["objective"],
                "state": "archived",
                "idempotency_key": "project-list-archive-0001",
            },
        )
        assert archived_response.status_code == 200

        active_page_one = client.get(
            "/api/v1/projects",
            params={"q": "Portfolio 2026", "state": "active", "limit": 1},
        )
        assert active_page_one.status_code == 200 and active_page_one.json()["ok"] is True
        page_one = active_page_one.json()["data"]
        assert page_one["filters"] == {"q": "Portfolio 2026", "state": "active"}
        assert page_one["pagination"] == {"limit": 1, "offset": 0, "returned": 1}
        assert page_one["has_more"] is True and page_one["next_offset"] == 1

        active_page_two = client.get(
            "/api/v1/projects",
            params={"q": "Portfolio 2026", "state": "active", "limit": 1, "offset": page_one["next_offset"]},
        )
        page_two = active_page_two.json()["data"]
        assert active_page_two.status_code == 200 and page_two["has_more"] is False
        assert page_two["items"][0]["id"] != page_one["items"][0]["id"]

        archived_only = client.get("/api/v1/projects", params={"q": "Portfolio 2026", "state": "archived", "limit": 10})
        assert [item["id"] for item in archived_only.json()["data"]["items"]] == [archived["id"]]

        literal_title = client.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Literal 100% Project",
                "summary": "Ký tự wildcard phải là ký tự thường",
                "objective": "Kiểm tra escape LIKE",
                "idempotency_key": "project-list-literal-0001",
            },
        ).json()["data"]["project"]
        literal_search = client.get("/api/v1/projects", params={"q": "%", "limit": 100})
        assert [item["id"] for item in literal_search.json()["data"]["items"]] == [literal_title["id"]]
        assert client.get("/api/v1/projects", params={"state": "unknown"}).status_code == 422

        register_and_login(client, "project-listing-other@example.com")
        isolated = client.get("/api/v1/projects", params={"q": "Portfolio 2026", "limit": 100})
        assert isolated.status_code == 200
        assert isolated.json()["data"]["items"] == []


def test_project_center_has_no_bot_bridge_or_payment_dependency():
    source = open("copyfast_projects.py", encoding="utf-8").read()
    assert "from copyfast_bridge" not in source
    assert "import copyfast_bridge" not in source
    assert "bridge_request" not in source
