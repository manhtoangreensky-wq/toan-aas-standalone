"""High-risk contracts for the private, Web-native Workboard.

The suite tests only the essential security and lifecycle boundaries. It does
not invoke Telegram, a provider, payment, wallet, job, publishing or a
notification service.
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
    "copyfast_document_workspace", "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard",
    "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio",
    "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "workboard-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "workboard-test-session-secret")
    monkeypatch.setenv("WEBAPP_WORKBOARD_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Workboard Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def payload(key: str, **overrides) -> dict:
    value = {
        "title": "Chuẩn bị tự rà soát bộ nội dung tháng bảy",
        "description": "Thẻ Web-native để điều phối kiểm tra nội bộ trước khi chuyển sang workflow độc lập tiếp theo.",
        "priority": "high",
        "due_at": "2026-07-31T16:30:00",
        "references": [],
        "checklist": [{"body": "Kiểm tra brief", "is_done": False}, {"body": "Xác nhận tự rà soát", "is_done": False}],
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_item(client: TestClient, csrf: str, key: str = "workboard-create-item-0001", **overrides) -> dict:
    response = client.post("/api/v1/workboard/items", headers={"X-CSRF-Token": csrf}, json=payload(key, **overrides))
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["item"]


def seed_native_references(db_path, email: str) -> tuple[str, str]:
    """Create owner-scoped Web-native records without starting a provider/job.

    The queued image row deliberately has no delivered output: Workboard may
    coordinate it, but the test proves that this never fabricates delivery.
    """

    with sqlite3.connect(db_path) as conn:
        account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email.lower(),)).fetchone()
        assert account
        account_id = str(account[0])
        now = "2026-07-17T12:00:00+00:00"
        asset_id = "workboard-native-asset"
        job_id = "workboard-native-job"
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, lifecycle_revision, created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.png', 'image/png', 1024, ?, ?, 'active', 1, ?, ?, NULL)""",
            (
                asset_id,
                account_id,
                "Workboard native source",
                "workboard-native-source.png",
                "a" * 64,
                f"private-workboard/{account_id}/{asset_id}.blob",
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO web_image_operations
               (id, account_id, source_asset_id, project_id, kind, state,
                idempotency_key, request_fingerprint, source_sha256,
                source_byte_size, source_width, source_height, target_width,
                target_height, preset, fit_mode, storage_key,
                original_filename, content_type, byte_size, sha256,
                failure_code, created_at, queued_at, started_at, completed_at,
                updated_at, settings_json)
               VALUES (?, ?, ?, NULL, 'image_resize', 'queued', ?, ?, ?,
                       1024, 1600, 1200, 1024, 1024, '1:1', 'crop', NULL,
                       NULL, NULL, NULL, NULL, NULL, ?, ?, NULL, NULL, ?, '{}')""",
            (
                job_id,
                account_id,
                asset_id,
                "workboard-native-job-create-0001",
                "workboard-native-fingerprint",
                "a" * 64,
                now,
                now,
                now,
            ),
        )
    models = importlib.import_module("copyfast_native_read_models")
    return (
        models.encode_native_job_id("image-operation", job_id),
        models.encode_native_asset_id(asset_id),
    )


def test_workboard_requires_signed_session_csrf_bounded_body_and_idempotency(tmp_path, monkeypatch):
    db_path = tmp_path / "workboard-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/workboard/summary").status_code == 401
        csrf = login(client, "workboard-auth@example.com")
        raw = payload("workboard-idempotency-0001")
        assert client.post("/api/v1/workboard/items", json=raw).status_code == 403
        too_large = client.post(
            "/api/v1/workboard/items",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"title":"' + (b"x" * (129 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_WORKBOARD_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        created = client.post("/api/v1/workboard/items", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        item = created.json()["data"]["item"]
        replay = client.post("/api/v1/workboard/items", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200 and replay.json()["data"]["item"]["id"] == item["id"]
        collision = client.post(
            "/api/v1/workboard/items",
            headers={"X-CSRF-Token": csrf},
            json=payload("workboard-idempotency-0001", title="Một thẻ khác hẳn"),
        )
        assert collision.status_code == 409
    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-workboard:%'").fetchall()
    assert receipts
    for (stored,) in receipts:
        assert raw["title"] not in str(stored)
        assert raw["description"] not in str(stored)


def test_workboard_list_filter_and_pagination_stay_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "workboard-listing@example.com")
        first = create_item(
            client,
            csrf,
            "workboard-list-first-0001",
            title="Rà soát báo cáo phiên bản một",
            priority="high",
        )
        second = create_item(
            client,
            csrf,
            "workboard-list-second-0001",
            title="Chuẩn bị tài liệu đào tạo hai",
            priority="normal",
        )
        filtered = client.get("/api/v1/workboard/items", params={"q": "Rà soát", "priority": "high", "limit": 1})
        assert filtered.status_code == 200 and filtered.json()["ok"] is True
        filtered_data = filtered.json()["data"]
        assert [entry["id"] for entry in filtered_data["items"]] == [first["id"]]
        assert filtered_data["has_more"] is False

        page_one = client.get("/api/v1/workboard/items", params={"limit": 1})
        assert page_one.status_code == 200 and page_one.json()["ok"] is True
        page_one_data = page_one.json()["data"]
        assert page_one_data["has_more"] is True
        assert page_one_data["next_offset"] == 1
        page_two = client.get("/api/v1/workboard/items", params={"limit": 1, "offset": page_one_data["next_offset"]})
        assert page_two.status_code == 200 and page_two.json()["ok"] is True
        assert page_two.json()["data"]["items"][0]["id"] in {first["id"], second["id"]}
        assert page_two.json()["data"]["items"][0]["id"] != page_one_data["items"][0]["id"]

        second_csrf = login(client, "workboard-listing-other@example.com")
        isolated = client.get("/api/v1/workboard/items", params={"limit": 100})
        assert isolated.status_code == 200 and isolated.json()["data"]["items"] == []
        assert second_csrf


def test_workboard_owner_scopes_references_and_revisioned_checklist(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first_csrf = login(client, "workboard-owner@example.com")
        project = client.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "title": "Project nguồn riêng tư", "summary": "Nguồn Web-owned", "objective": "Rà soát",
                "idempotency_key": "workboard-source-project-0001",
            },
        ).json()["data"]["project"]
        item = create_item(
            client,
            first_csrf,
            "workboard-reference-create-0001",
            references=[{"ref_type": "project", "ref_id": project["id"]}],
        )
        detail = client.get(f"/api/v1/workboard/items/{item['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        detail_data = detail.json()["data"]
        assert detail_data["item"]["references"] == [{"ref_type": "project", "ref_id": project["id"]}]
        checklist = detail_data["checklist"]
        assert len(checklist) == 2
        updated = client.patch(
            f"/api/v1/workboard/items/{item['id']}/checklist/{checklist[0]['id']}",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "is_done": True,
                "expected_revision": detail_data["item"]["revision"],
                "expected_checklist_revision": checklist[0]["revision"],
                "idempotency_key": "workboard-checklist-update-0001",
            },
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True
        moved = client.post(
            f"/api/v1/workboard/items/{item['id']}/state",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "state": "review", "expected_revision": updated.json()["data"]["item"]["revision"],
                "idempotency_key": "workboard-state-review-0001",
            },
        )
        assert moved.status_code == 200 and moved.json()["data"]["item"]["state"] == "review"
        restored = client.post(
            f"/api/v1/workboard/items/{item['id']}/restore/1",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "expected_revision": moved.json()["data"]["item"]["revision"],
                "idempotency_key": "workboard-restore-version-0001",
            },
        )
        assert restored.status_code == 200 and restored.json()["ok"] is True
        restored_detail = client.get(f"/api/v1/workboard/items/{item['id']}").json()["data"]
        assert restored_detail["item"]["state"] == "backlog"
        assert len(restored_detail["versions"]) >= 4
        second_csrf = login(client, "workboard-other@example.com")
        hidden = client.get(f"/api/v1/workboard/items/{item['id']}")
        assert hidden.status_code == 200 and hidden.json()["error_code"] == "WEB_WORKBOARD_ITEM_NOT_FOUND"
        foreign_ref = client.post(
            "/api/v1/workboard/items",
            headers={"X-CSRF-Token": second_csrf},
            json=payload("workboard-foreign-reference-0001", references=[{"ref_type": "project", "ref_id": project["id"]}]),
        )
        assert foreign_ref.status_code == 200
        assert foreign_ref.json()["error_code"] in {"WEB_WORKBOARD_REFERENCE_NOT_FOUND", "WEB_WORKBOARD_REFERENCE_INVALID"}


def test_workboard_native_references_are_opaque_owner_scoped_and_not_delivery(tmp_path, monkeypatch):
    db_path = tmp_path / "workboard-test.db"
    owner_email = "workboard-native-owner@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = login(client, owner_email)
        native_job, native_asset = seed_native_references(db_path, owner_email)

        catalog = client.get("/api/v1/workboard/references")
        assert catalog.status_code == 200 and catalog.json()["ok"] is True
        choices = catalog.json()["data"]["references"]
        assert {choice["ref_id"] for choice in choices["native_job"]} == {native_job}
        assert {choice["ref_id"] for choice in choices["native_asset"]} == {native_asset}
        # Public catalog data stays opaque: internal DB IDs and storage keys do
        # not cross this boundary, and a queued job has no delivery field.
        serialized_catalog = str(choices)
        assert "workboard-native-job" not in serialized_catalog
        assert "workboard-native-asset" not in serialized_catalog
        assert "private-workboard" not in serialized_catalog

        item = create_item(
            client,
            owner_csrf,
            "workboard-native-reference-create-0001",
            references=[
                {"ref_type": "native_job", "ref_id": native_job},
                {"ref_type": "native_asset", "ref_id": native_asset},
            ],
        )
        detail = client.get(f"/api/v1/workboard/items/{item['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        assert detail.json()["data"]["item"]["references"] == [
            {"ref_type": "native_job", "ref_id": native_job},
            {"ref_type": "native_asset", "ref_id": native_asset},
        ]
        assert "output" not in detail.json()["data"]["item"]
        filtered = client.get(
            "/api/v1/workboard/items",
            params={"ref_type": "native_output", "ref_id": native_job},
        )
        assert filtered.status_code == 200
        assert [entry["id"] for entry in filtered.json()["data"]["items"]] == [item["id"]]
        malformed_filter = client.get(
            "/api/v1/workboard/items",
            params={"ref_type": "native_job", "ref_id": "not-an-opaque-id"},
        )
        assert malformed_filter.status_code == 422

        # A revision restore preserves the typed opaque links while the owner
        # record remains valid; it does not reconnect through another account.
        changed = client.patch(
            f"/api/v1/workboard/items/{item['id']}",
            headers={"X-CSRF-Token": owner_csrf},
            json={
                "description": "Cập nhật metadata điều phối Web-native, không yêu cầu chạy hay giao output.",
                "expected_revision": item["revision"],
                "idempotency_key": "workboard-native-reference-update-0001",
            },
        )
        assert changed.status_code == 200 and changed.json()["ok"] is True
        restored = client.post(
            f"/api/v1/workboard/items/{item['id']}/restore/1",
            headers={"X-CSRF-Token": owner_csrf},
            json={
                "expected_revision": changed.json()["data"]["item"]["revision"],
                "idempotency_key": "workboard-native-reference-restore-0001",
            },
        )
        assert restored.status_code == 200 and restored.json()["ok"] is True
        restored_refs = client.get(f"/api/v1/workboard/items/{item['id']}").json()["data"]["item"]["references"]
        assert restored_refs == [
            {"ref_type": "native_job", "ref_id": native_job},
            {"ref_type": "native_asset", "ref_id": native_asset},
        ]

        other_csrf = login(client, "workboard-native-other@example.com")
        denied = client.post(
            "/api/v1/workboard/items",
            headers={"X-CSRF-Token": other_csrf},
            json=payload(
                "workboard-native-reference-foreign-0001",
                references=[
                    {"ref_type": "native_job", "ref_id": native_job},
                    {"ref_type": "native_asset", "ref_id": native_asset},
                ],
            ),
        )
        assert denied.status_code == 200
        assert denied.json()["error_code"] == "WEB_WORKBOARD_REFERENCE_NOT_FOUND"

        # A later archive invalidates the asset reference.  Restore fails
        # closed instead of preserving a stale cross-lifecycle association.
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_asset_files SET state='archived' WHERE id='workboard-native-asset'")
        owner_csrf = login(client, owner_email)
        blocked_restore = client.post(
            f"/api/v1/workboard/items/{item['id']}/restore/1",
            headers={"X-CSRF-Token": owner_csrf},
            json={
                "expected_revision": restored.json()["data"]["item"]["revision"],
                "idempotency_key": "workboard-native-reference-restore-stale-0001",
            },
        )
        assert blocked_restore.status_code == 200
        assert blocked_restore.json()["error_code"] == "WEB_WORKBOARD_REFERENCE_NOT_FOUND"


def test_workboard_rejects_sensitive_or_external_input_and_has_no_fake_automation(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "workboard-validation@example.com")
        for index, unsafe in enumerate((
            "https://example.invalid/task?token=abc", "file:///C:/private/brief.txt", "<script>alert(1)</script>",
            "api_key=not-a-real-secret-value", "Mã giao dịch: 123456789", "4111 1111 1111 1111",
        ), start=1):
            response = client.post(
                "/api/v1/workboard/items",
                headers={"X-CSRF-Token": csrf},
                json=payload(f"workboard-unsafe-{index:04d}", description=unsafe),
            )
            assert response.status_code == 422
        item = create_item(client, csrf, "workboard-safe-create-0001")
        denied = client.post(
            f"/api/v1/workboard/items/{item['id']}/state",
            headers={"X-CSRF-Token": csrf},
            json={"state": "published", "expected_revision": item["revision"], "idempotency_key": "workboard-no-publish-0001"},
        )
        assert denied.status_code == 422
        policy = client.get("/api/v1/workboard/policy")
        assert policy.status_code == 200 and policy.json()["ok"] is True
        boundary = policy.json()["data"]
        for key in ("bot_called", "provider_called", "wallet_mutated", "payment_processed", "job_created", "publish_action_created", "notification_sent"):
            assert boundary[key] is False


def test_workboard_disabled_mode_and_source_boundary(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "workboard-disabled@example.com")
        guarded = client.get("/api/v1/workboard/summary")
        assert guarded.status_code == 503
        assert "WEBAPP_WORKBOARD_ENABLED" in guarded.text
        assert csrf
    source = (importlib.import_module("pathlib").Path(__file__).parents[1] / "copyfast_workboard.py").read_text(encoding="utf-8")
    for forbidden in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS",
        "import wallet", "from wallet", "import requests", "import httpx", "import urllib",
    ):
        assert forbidden not in source


def test_workboard_portal_routes_render_for_a_signed_account(tmp_path, monkeypatch):
    """The server must recognise the board, create and UUID detail routes."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "workboard-routes@example.com")
        item = create_item(client, csrf, "workboard-portal-route-create-0001")
        for route in ("/workboard", "/workboard/new", f"/workboard/{item['id']}"):
            response = client.get(route)
            assert response.status_code == 200
            assert "TOAN AAS" in response.text
