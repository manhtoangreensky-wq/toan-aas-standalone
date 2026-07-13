"""Critical contracts for the Web-native Image Creative Studio.

The studio is intentionally an authoring/reference surface.  These focused
tests guard the dangerous regressions: identity/CSRF, receipt redaction,
owner-only image references, child CAS, lifecycle freezes and the promise not
to manufacture an image/output status.
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
    "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio",
    "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "image-studio-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "image-studio-test-session-secret")
    monkeypatch.setenv("WEBAPP_IMAGE_STUDIO_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Image Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def artboard_payload(key: str, **overrides) -> dict:
    value = {
        "title": "Key visual cho bộ nhận diện mùa hè",
        "image_intent": "create",
        "language": "vi",
        "aspect_ratio": "4:5",
        "output_format": "png",
        "creative_brief": "Không khí sáng, sạch, lấy sản phẩm làm trọng tâm và đủ khoảng thở cho chữ.",
        "style_direction": "Studio tối giản, ánh sáng mềm, độ tương phản vừa phải.",
        "negative_direction": "Không chèn logo giả hoặc chữ khó đọc.",
        "tags": ["brand", "summer"],
        "project_id": "",
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def direction_payload(key: str, expected_revision: int, **overrides) -> dict:
    value = {
        "title": "Hero product clean studio",
        "operation": "create",
        "prompt_text": "Chai sản phẩm đứng giữa bàn đá sáng, nền tối giản, ánh sáng cửa sổ dịu.",
        "edit_instructions": "",
        "composition_notes": "Căn giữa, chừa khoảng thở phía trên cho headline.",
        "negative_direction": "Tránh watermark, chữ nhỏ và bàn tay dư thừa.",
        "asset_id": "",
        "reference_asset_id": "",
        "tags": ["hero"],
        "expected_revision": expected_revision,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_artboard(client: TestClient, csrf: str, key: str = "image-artboard-create-0001", **overrides) -> dict:
    response = client.post("/api/v1/image-studio/artboards", headers={"X-CSRF-Token": csrf}, json=artboard_payload(key, **overrides))
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["artboard"]


def insert_image_asset(db_path, email: str, *, extension: str = "png", content_type: str = "image/png") -> str:
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
                asset_id, str(account[0]), "Ảnh tham chiếu", f"reference.{extension}", extension, content_type,
                123, "0" * 64, f"objects/{asset_id}.bin", now, now,
            ),
        )
    return asset_id


def test_image_studio_session_csrf_body_cap_and_receipt_redaction(tmp_path, monkeypatch):
    db_path = tmp_path / "image-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/image-studio/summary").status_code == 401
        csrf = login(client, "image-auth@example.com")
        unsafe_search = client.get("/api/v1/image-studio/artboards?q=https://provider.example/private")
        assert unsafe_search.status_code == 422
        raw = artboard_payload("image-artboard-idempotency-0001")
        assert client.post("/api/v1/image-studio/artboards", json=raw).status_code == 403
        too_large = client.post(
            "/api/v1/image-studio/artboards",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"title":"' + (b"x" * (129 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_IMAGE_STUDIO_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        created = client.post("/api/v1/image-studio/artboards", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        data = created.json()["data"]
        assert data["execution"] == "authoring_only"
        for key in ("provider_called", "image_created", "output_created", "job_created", "payment_started", "wallet_mutated", "payment_processed"):
            assert data[key] is False
        assert raw["creative_brief"] not in created.text
        replay = client.post("/api/v1/image-studio/artboards", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.post(
            "/api/v1/image-studio/artboards", headers={"X-CSRF-Token": csrf},
            json=artboard_payload("image-artboard-idempotency-0001", creative_brief="Nội dung thay đổi."),
        )
        assert collision.status_code == 409
    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-image-studio:%'").fetchall()
    assert receipts and all(raw["title"] not in str(row[0]) and raw["creative_brief"] not in str(row[0]) for row in receipts)


def test_image_studio_owner_assets_markup_and_child_cas(tmp_path, monkeypatch):
    db_path = tmp_path / "image-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "image-owner@example.com")
        unsafe_artboard = client.post(
            "/api/v1/image-studio/artboards", headers={"X-CSRF-Token": csrf},
            json=artboard_payload("image-artboard-markup-0001", creative_brief="<img src=x onerror=alert(1)>"),
        )
        assert unsafe_artboard.status_code == 422
        artboard = create_artboard(client, csrf, "image-owner-artboard-0001")
        image_asset = insert_image_asset(db_path, "image-owner@example.com")
        ignored_asset = insert_image_asset(db_path, "image-owner@example.com", extension="gif", content_type="image/gif")
        refs = client.get("/api/v1/image-studio/references")
        assert refs.status_code == 200
        assert [item["id"] for item in refs.json()["data"]["image_assets"]] == [image_asset]
        markup = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-markup-0001", artboard["revision"], prompt_text="<svg onload=alert(1)>"),
        )
        assert markup.status_code == 422
        invalid_asset = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-non-image-0001", artboard["revision"], operation="upscale", prompt_text="", asset_id=ignored_asset),
        )
        assert invalid_asset.status_code == 422
        created = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-edit-asset-0001", artboard["revision"], operation="edit", prompt_text="", edit_instructions="Làm nền sạch hơn, giữ ánh sáng hiện có.", asset_id=image_asset),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        direction = created.json()["data"]["direction"]
        detail = client.get(f"/api/v1/image-studio/artboards/{artboard['id']}").json()["data"]
        assert detail["directions"][0]["asset_id"] == image_asset
        updated = client.patch(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions/{direction['id']}", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-direction-update-0001", direction["revision"], operation="edit", prompt_text="", edit_instructions="Giữ sản phẩm, giảm bóng cứng.", asset_id=image_asset),
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True
        stale = client.patch(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions/{direction['id']}", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-direction-stale-0001", direction["revision"], operation="edit", prompt_text="", edit_instructions="Yêu cầu cũ.", asset_id=image_asset),
        )
        assert stale.status_code == 200 and stale.json()["error_code"] == "WEB_IMAGE_REVISION_CONFLICT"
        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = login(second, "image-other@example.com")
            hidden = second.get(f"/api/v1/image-studio/artboards/{artboard['id']}")
            assert hidden.status_code == 200 and hidden.json()["error_code"] == "WEB_IMAGE_ARTBOARD_NOT_FOUND"
            denied = second.post(
                f"/api/v1/image-studio/artboards/{artboard['id']}/directions", headers={"X-CSRF-Token": csrf_second},
                json=direction_payload("image-cross-owner-0001", 1),
            )
            assert denied.status_code == 200 and denied.json()["error_code"] == "WEB_IMAGE_ARTBOARD_NOT_FOUND"


def test_image_studio_lifecycle_archive_estimate_and_direction_reorder(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "image-lifecycle@example.com")
        artboard = create_artboard(client, csrf, "image-life-artboard-0001")
        first = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-life-first-0001", artboard["revision"], prompt_text="Góc chụp chính diện, sản phẩm sáng rõ."),
        ).json()["data"]
        second = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-life-second-0001", first["artboard"]["revision"], title="Lifestyle frame", prompt_text="Khung lifestyle nhiều khoảng thở, ánh sáng tự nhiên."),
        ).json()["data"]
        reviewed = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/lifecycle", headers={"X-CSRF-Token": csrf},
            json={"state": "review", "expected_revision": second["artboard"]["revision"], "idempotency_key": "image-life-review-0001"},
        )
        assert reviewed.status_code == 200 and reviewed.json()["data"]["artboard"]["state"] == "review"
        frozen = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions", headers={"X-CSRF-Token": csrf},
            json=direction_payload("image-life-frozen-0001", reviewed.json()["data"]["artboard"]["revision"]),
        )
        assert frozen.status_code == 200 and frozen.json()["error_code"] == "WEB_IMAGE_ARTBOARD_REVIEW_LOCKED"
        reopened = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/lifecycle", headers={"X-CSRF-Token": csrf},
            json={"state": "draft", "expected_revision": reviewed.json()["data"]["artboard"]["revision"], "idempotency_key": "image-life-reopen-0001"},
        ).json()["data"]["artboard"]
        archived = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions/{first['direction']['id']}/archive", headers={"X-CSRF-Token": csrf},
            json={"expected_revision": first["direction"]["revision"], "idempotency_key": "image-life-archive-direction-0001"},
        )
        assert archived.status_code == 200 and archived.json()["data"]["direction"]["state"] == "archived"
        current = archived.json()["data"]["artboard"]
        reordered = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions/reorder", headers={"X-CSRF-Token": csrf},
            json={"direction_ids": [second["direction"]["id"]], "expected_revision": current["revision"], "idempotency_key": "image-life-reorder-0001"},
        )
        assert reordered.status_code == 200 and reordered.json()["ok"] is True
        final = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/lifecycle", headers={"X-CSRF-Token": csrf},
            json={"state": "archived", "expected_revision": reordered.json()["data"]["artboard"]["revision"], "idempotency_key": "image-life-archive-artboard-0001"},
        )
        assert final.status_code == 200 and final.json()["data"]["artboard"]["state"] == "archived"
        estimate = client.get(f"/api/v1/image-studio/artboards/{artboard['id']}/estimate")
        assert estimate.status_code == 200 and estimate.json()["error_code"] == "WEB_IMAGE_ARTBOARD_ARCHIVED"
        assert "completed" not in estimate.text


def test_image_studio_explicit_disable_is_a_maintenance_guard(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "image-disabled@example.com")
        guarded = client.get("/api/v1/image-studio/summary")
        assert guarded.status_code == 503
        assert "WEBAPP_IMAGE_STUDIO_ENABLED" in guarded.text
        assert csrf
