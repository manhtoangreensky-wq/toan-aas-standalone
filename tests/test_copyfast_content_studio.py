"""Risk-focused contracts for the Web-native Creative Content Studio."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_memory", "copyfast_prompt_library",
    "copyfast_music_media", "copyfast_content_studio", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "content-studio-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "content-studio-test-session-secret")
    monkeypatch.setenv("WEBAPP_CONTENT_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROMPT_LIBRARY_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Content Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def brief_payload(key: str, **overrides) -> dict:
    payload = {
        "title": "Ra mắt bộ sưu tập mùa hè",
        "content_kind": "caption_hashtag",
        "subject": "Bộ sưu tập chăm sóc da mùa hè cho người bận rộn",
        "objective": "Giải thích lợi ích có thể kiểm chứng",
        "audience": "Người đi làm 22 đến 35 tuổi",
        "platform": "Instagram",
        "tone": "Rõ ràng và gần gũi",
        "language": "vi",
        "call_to_action": "Xem hướng dẫn sử dụng trước khi chọn sản phẩm.",
        "brief_text": "Nêu lợi ích thực tế, cách dùng an toàn và chỗ cần đội ngũ kiểm tra trước khi đăng.",
        "constraints": "Không nêu số liệu không có nguồn và không giả kết quả điều trị.",
        "tags": ["summer", "skincare"],
        "rights_note": "Tôi sẽ xác nhận quyền sử dụng tài sản và claim trước khi publish.",
        "project_id": "",
        "campaign_plan_id": "",
        "prompt_template_id": "",
        "media_collection_id": "",
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def create_brief(client: TestClient, csrf: str, key: str = "content-studio-create-0001", **overrides) -> dict:
    response = client.post("/api/v1/content-studio/briefs", headers={"X-CSRF-Token": csrf}, json=brief_payload(key, **overrides))
    assert response.status_code == 200
    assert response.json()["ok"] is True
    receipt = response.json()["data"]["brief"]
    detail = client.get(f"/api/v1/content-studio/briefs/{receipt['id']}")
    assert detail.status_code == 200
    return detail.json()["data"]["brief"]


def test_content_studio_requires_session_csrf_and_keeps_idempotency_receipts_content_free(tmp_path, monkeypatch):
    db_path = tmp_path / "content-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/content-studio/summary").status_code == 401
        csrf = register_and_login(client, "content-owner@example.com")
        raw = brief_payload("content-studio-create-0001")

        denied = client.post("/api/v1/content-studio/briefs", json=raw)
        assert denied.status_code == 403

        oversized = client.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json={"title": "x" * (129 * 1024)},
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_CONTENT_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["cache-control"] == "no-store, private"
        assert client.get("/api/v1/content-studio/summary").json()["data"]["briefs"]["total"] == 0

        created = client.post("/api/v1/content-studio/briefs", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200
        assert created.json()["status"] == "draft"
        brief_id = created.json()["data"]["brief"]["id"]
        assert raw["brief_text"] not in created.text
        assert raw["title"] not in created.text

        replay = client.post("/api/v1/content-studio/briefs", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200
        assert replay.json() == created.json()
        collision = client.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json=brief_payload("content-studio-create-0001", title="Brief khác"),
        )
        assert collision.status_code == 409

        detail = client.get(f"/api/v1/content-studio/briefs/{brief_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["brief"]["brief_text"] == raw["brief_text"]
        with sqlite3.connect(db_path) as conn:
            receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-content-studio:%'").fetchall()
        assert receipts
        assert all(raw["brief_text"] not in str(row[0]) for row in receipts)
        assert all(raw["title"] not in str(row[0]) for row in receipts)


def test_content_studio_keeps_references_and_content_pieces_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "content-first@example.com")
        brief = create_brief(first, csrf, "content-first-create-0001")

        invalid_ref = first.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json=brief_payload("content-invalid-reference-0001", project_id="1dcca218-d5a0-4c6a-9a62-3dd630db6a67"),
        )
        assert invalid_ref.status_code == 422

        secret = first.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json=brief_payload("content-secret-brief-0001", brief_text="api_key=super-secret-token-value-12345"),
        )
        assert secret.status_code == 422

        composed = first.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/compose",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": brief["revision"], "idempotency_key": "content-compose-local-0001"},
        )
        assert composed.status_code == 200
        data = composed.json()["data"]
        assert data["execution"] == "local_deterministic_draft_only"
        assert data["provider_called"] is False
        assert data["charge_started"] is False
        assert len(data["variant_ids"]) == 3
        assert "job_id" not in composed.text
        assert "output_url" not in composed.text

        detail = first.get(f"/api/v1/content-studio/briefs/{brief['id']}")
        variants = detail.json()["data"]["variants"]
        assert len(variants) == 3
        assert all(item["source_kind"] == "local_deterministic_draft_only" for item in variants)

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "content-second@example.com")
            hidden = second.get(f"/api/v1/content-studio/briefs/{brief['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_CONTENT_BRIEF_NOT_FOUND"
            assert brief["brief_text"] not in hidden.text
            blocked = second.post(
                f"/api/v1/content-studio/briefs/{brief['id']}/compose",
                headers={"X-CSRF-Token": csrf_second},
                json={"expected_revision": brief["revision"], "idempotency_key": "content-cross-owner-compose-0001"},
            )
            assert blocked.status_code == 200
            assert blocked.json()["error_code"] == "WEB_CONTENT_BRIEF_NOT_FOUND"


def test_content_studio_variant_revision_selection_and_archive_are_safe(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "content-variant@example.com")
        brief = create_brief(client, csrf, "content-variant-brief-0001", content_kind="hook_script")
        created = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/variants",
            headers={"X-CSRF-Token": csrf},
            json={
                "kind": "hook",
                "title": "Hook có kiểm tra",
                "content_text": "Một câu mở đầu được người dùng tự viết và sẽ được kiểm tra trước khi dùng.",
                "note": "",
                "tags": ["review"],
                "expected_revision": brief["revision"],
                "idempotency_key": "content-variant-create-0001",
            },
        )
        assert created.status_code == 200
        variant_id = created.json()["data"]["variant"]["id"]
        detail = client.get(f"/api/v1/content-studio/briefs/{brief['id']}")
        variant = next(item for item in detail.json()["data"]["variants"] if item["id"] == variant_id)
        selected = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/select-variant",
            headers={"X-CSRF-Token": csrf},
            json={"variant_id": variant_id, "expected_revision": brief["revision"], "idempotency_key": "content-select-variant-0001"},
        )
        assert selected.status_code == 200
        current_revision = selected.json()["data"]["brief"]["revision"]
        archived = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/variants/{variant_id}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": variant["revision"], "idempotency_key": "content-archive-variant-0001"},
        )
        assert archived.status_code == 200
        current = client.get(f"/api/v1/content-studio/briefs/{brief['id']}").json()["data"]["brief"]
        assert current["selected_variant_id"] is None
        stale = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/select-variant",
            headers={"X-CSRF-Token": csrf},
            json={"variant_id": variant_id, "expected_revision": current_revision, "idempotency_key": "content-select-archived-0001"},
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] in {"WEB_CONTENT_REVISION_CONFLICT", "WEB_CONTENT_VARIANT_NOT_FOUND"}
