"""Critical contracts for the Web-native Document & PDF Workspace.

The workspace is deliberately an account-owned authoring surface, rather than
another document executor.  These focused checks preserve the important
boundaries: signed-session/CSRF, input size, redacted idempotency receipts,
owner-only opaque Asset Vault references, frozen self-review lifecycle and no
invented OCR/translation/output/job/payment result.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
import uuid

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media",
    "copyfast_content_studio", "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace",
    "copyfast_support",
]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-workspace-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "document-workspace-test-session-secret")
    monkeypatch.setenv("WEBAPP_DOCUMENT_WORKSPACE_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Document Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def workspace_payload(key: str, **overrides) -> dict:
    value = {
        "title": "Hồ sơ tài liệu sản phẩm quý ba",
        "document_type": "pdf",
        "source_summary": "Bản brief gồm thông số sản phẩm, ảnh tham khảo và nội dung cần chuẩn hoá.",
        "objective": "Chuẩn bị kế hoạch rà soát, sắp xếp và xuất bản hồ sơ nội bộ sạch.",
        "language": "vi",
        "target_language": "",
        "tags": ["catalog", "q3"],
        "project_id": "",
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def plan_payload(key: str, expected_revision: int, **overrides) -> dict:
    value = {
        "title": "Rà soát cấu trúc và thứ tự phụ lục",
        "operation": "organize",
        "instructions": "Kiểm tra cấu trúc mục lục, đánh dấu phụ lục cần hoàn thiện và lưu checklist cho người duyệt.",
        "source_asset_id": "",
        "reference_asset_id": "",
        "tags": ["review"],
        "expected_revision": expected_revision,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_workspace(client: TestClient, csrf: str, key: str = "document-workspace-create-0001", **overrides) -> dict:
    response = client.post(
        "/api/v1/document-workspace/workspaces",
        headers={"X-CSRF-Token": csrf},
        json=workspace_payload(key, **overrides),
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["workspace"]


def insert_document_asset(db_path, email: str, *, extension: str = ".PDF", content_type: str = "application/pdf") -> str:
    asset_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as conn:
        account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        assert account
        now = "2026-07-14T00:00:00+00:00"
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension, content_type,
                byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
            (
                asset_id,
                str(account[0]),
                "Tài liệu nguồn",
                "private-source.PDF",
                extension,
                content_type,
                123,
                "0" * 64,
                f"objects/{asset_id}.bin",
                now,
                now,
            ),
        )
    return asset_id


def assert_authoring_only(data: dict) -> None:
    assert data["execution"] == "authoring_only"
    for key in (
        "provider_called", "ocr_called", "translation_called", "output_created", "job_created",
        "payment_started", "wallet_mutated", "payment_processed", "browser_file_upload",
        "browser_media_url", "preview_available",
    ):
        assert data[key] is False
    assert data["output_delivery"] == "guarded"


def test_document_workspace_signed_session_csrf_body_cap_and_receipt_redaction(tmp_path, monkeypatch):
    db_path = tmp_path / "document-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/document-workspace/summary").status_code == 401
        csrf = login(client, "document-auth@example.com")
        raw = workspace_payload("document-workspace-idempotency-0001")
        assert client.post("/api/v1/document-workspace/workspaces", json=raw).status_code == 403
        too_large = client.post(
            "/api/v1/document-workspace/workspaces",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"title":"' + (b"x" * (129 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_DOCUMENT_WORKSPACE_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        created = client.post(
            "/api/v1/document-workspace/workspaces", headers={"X-CSRF-Token": csrf}, json=raw,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        data = created.json()["data"]
        assert_authoring_only(data)
        for private_value in (raw["title"], raw["source_summary"], raw["objective"]):
            assert private_value not in created.text
        replay = client.post(
            "/api/v1/document-workspace/workspaces", headers={"X-CSRF-Token": csrf}, json=raw,
        )
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.post(
            "/api/v1/document-workspace/workspaces",
            headers={"X-CSRF-Token": csrf},
            json=workspace_payload("document-workspace-idempotency-0001", objective="Mục tiêu đã thay đổi."),
        )
        assert collision.status_code == 409
    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-document-workspace:%'"
        ).fetchall()
    assert receipts
    for row in receipts:
        text = str(row[0])
        assert raw["title"] not in text
        assert raw["source_summary"] not in text
        assert raw["objective"] not in text


def test_document_workspace_policy_has_only_closed_navigation_handoffs(tmp_path, monkeypatch):
    """A plan may open a new tool, but it cannot carry Bot/Web state into it."""

    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/document-workspace/policy").status_code == 401
        login(client, "document-handoff-policy@example.com")
        response = client.get("/api/v1/document-workspace/policy")
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert_authoring_only(data)
        catalog = data["handoff_catalog"]
        assert len(catalog) == 11
        by_operation = {item["operation"]: item for item in catalog}
        assert set(by_operation) == {
            "organize", "split", "merge", "optimize", "image_to_pdf", "pdf_to_images",
            "pdf_to_word", "ocr", "translate", "convert", "other",
        }
        assert {
            operation: item["route"]
            for operation, item in by_operation.items()
            if item["availability"] == "available"
        } == {
            "split": "/documents/split",
            "merge": "/documents/merge",
            "optimize": "/documents/compress",
            "image_to_pdf": "/documents/image-to-pdf",
            "pdf_to_images": "/documents/pdf-to-images",
            "pdf_to_word": "/documents/pdf-to-word",
        }
        assert {operation for operation, item in by_operation.items() if item["availability"] == "guarded"} == {
            "ocr", "translate", "convert",
        }
        assert {operation for operation, item in by_operation.items() if item["availability"] == "guidance"} == {
            "organize", "other",
        }
        for item in catalog:
            assert item["requires_new_tool_input"] is True
            assert item["workspace_data_transferred"] is False
            assert item["auto_execute"] is False
            assert item["workspace_output_shared"] is False
            assert set(item).isdisjoint({
                "workspace_id", "plan_id", "asset_id", "source_asset_id", "file", "path", "url",
                "token", "receipt", "job", "provider", "wallet", "payment", "payos",
            })
            if item["availability"] != "available":
                assert item["route"] is None
        assert "light/medium/strong" in by_operation["optimize"]["summary"]


def test_document_workspace_summary_remains_account_scoped_with_handoff_catalog(tmp_path, monkeypatch):
    """Policy metadata must not change the independent summary read model."""

    with make_client(tmp_path, monkeypatch) as client:
        login(client, "document-summary-handoff@example.com")
        response = client.get("/api/v1/document-workspace/summary")
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert_authoring_only(data)
        assert data["workspaces"] == {
            "draft": 0,
            "review": 0,
            "approved": 0,
            "archived": 0,
            "total": 0,
            "limit_per_account": 300,
        }
        assert data["plans"] == {"active": 0, "limit_per_workspace": 120}


def test_document_workspace_owner_assets_markup_and_dotted_extensions(tmp_path, monkeypatch):
    db_path = tmp_path / "document-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "document-owner@example.com")
        workspace = create_workspace(client, csrf, "document-owner-workspace-0001")
        dotted_pdf_id = insert_document_asset(db_path, "document-owner@example.com")
        references = client.get("/api/v1/document-workspace/references")
        assert references.status_code == 200
        document_assets = references.json()["data"]["document_assets"]
        assert [asset["id"] for asset in document_assets] == [dotted_pdf_id]
        assert document_assets[0]["extension"] == ".pdf"
        assert "original_filename" not in document_assets[0]
        markup = client.post(
            f"/api/v1/document-workspace/workspaces/{workspace['id']}/plans",
            headers={"X-CSRF-Token": csrf},
            json=plan_payload(
                "document-plan-markup-0001", workspace["revision"],
                instructions="<img src=x onerror=alert(1)>",
            ),
        )
        assert markup.status_code == 422
        bot_token = client.post(
            "/api/v1/document-workspace/workspaces",
            headers={"X-CSRF-Token": csrf},
            json=workspace_payload(
                "document-workspace-bot-token-0001",
                source_summary="bot_id: 1234567890; bot token: 1234567890:AAE1_example_token_value_123456",
            ),
        )
        assert bot_token.status_code == 422
        assert_authoring_only(bot_token.json()["data"])
        created = client.post(
            f"/api/v1/document-workspace/workspaces/{workspace['id']}/plans",
            headers={"X-CSRF-Token": csrf},
            json=plan_payload(
                "document-plan-dotted-pdf-0001", workspace["revision"], source_asset_id=dotted_pdf_id,
            ),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        assert_authoring_only(created.json()["data"])
        detail = client.get(f"/api/v1/document-workspace/workspaces/{workspace['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        plan = detail.json()["data"]["plans"][0]
        assert plan["source_asset_id"] == dotted_pdf_id
        assert plan["source_asset_available"] is True
        assert plan["output_created"] is False
        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = login(second, "document-other@example.com")
            hidden = second.get(f"/api/v1/document-workspace/workspaces/{workspace['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_DOCUMENT_WORKSPACE_NOT_FOUND"
            denied = second.post(
                f"/api/v1/document-workspace/workspaces/{workspace['id']}/plans",
                headers={"X-CSRF-Token": csrf_second},
                json=plan_payload("document-plan-cross-owner-0001", 1),
            )
            assert denied.status_code == 200
            assert denied.json()["error_code"] == "WEB_DOCUMENT_WORKSPACE_NOT_FOUND"


def test_document_workspace_lifecycle_freezes_and_never_fakes_execution(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "document-lifecycle@example.com")
        workspace = create_workspace(client, csrf, "document-life-workspace-0001")
        plan_created = client.post(
            f"/api/v1/document-workspace/workspaces/{workspace['id']}/plans",
            headers={"X-CSRF-Token": csrf},
            json=plan_payload("document-life-plan-0001", workspace["revision"]),
        )
        assert plan_created.status_code == 200 and plan_created.json()["ok"] is True
        changed_workspace = plan_created.json()["data"]["workspace"]
        reviewed = client.post(
            f"/api/v1/document-workspace/workspaces/{workspace['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={
                "state": "review",
                "expected_revision": changed_workspace["revision"],
                "idempotency_key": "document-life-review-0001",
            },
        )
        assert reviewed.status_code == 200 and reviewed.json()["ok"] is True
        reviewed_workspace = reviewed.json()["data"]["workspace"]
        assert reviewed_workspace["state"] == "review"
        assert_authoring_only(reviewed.json()["data"])
        frozen_update = client.patch(
            f"/api/v1/document-workspace/workspaces/{workspace['id']}",
            headers={"X-CSRF-Token": csrf},
            json=workspace_payload(
                "document-life-frozen-update-0001",
                title="Tên không được lưu trong review",
                source_summary="Nguồn mới không được lưu trong review.",
                objective="Mục tiêu mới không được lưu trong review.",
            ) | {"expected_revision": reviewed_workspace["revision"]},
        )
        assert frozen_update.status_code == 200
        assert frozen_update.json()["error_code"] == "WEB_DOCUMENT_WORKSPACE_REVIEW_LOCKED"
        frozen_plan = client.post(
            f"/api/v1/document-workspace/workspaces/{workspace['id']}/plans",
            headers={"X-CSRF-Token": csrf},
            json=plan_payload("document-life-frozen-plan-0001", reviewed_workspace["revision"]),
        )
        assert frozen_plan.status_code == 200
        assert frozen_plan.json()["error_code"] == "WEB_DOCUMENT_WORKSPACE_REVIEW_LOCKED"
        estimate = client.get(f"/api/v1/document-workspace/workspaces/{workspace['id']}/estimate")
        assert estimate.status_code == 200
        assert estimate.json()["error_code"] == "WEB_DOCUMENT_WORKSPACE_REVIEW_LOCKED"
        assert_authoring_only(estimate.json()["data"])
        assert "completed" not in estimate.text


def test_document_workspace_explicit_disable_is_a_maintenance_guard(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "document-disabled@example.com")
        guarded = client.get("/api/v1/document-workspace/summary")
        assert guarded.status_code == 503
        assert "WEBAPP_DOCUMENT_WORKSPACE_ENABLED" in guarded.text
        assert csrf
