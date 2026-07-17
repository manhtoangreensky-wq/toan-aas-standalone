"""Focused contracts for the safe Web replacement of Bot ``imagevideo|save``.

The Bot callback retained a short-lived plan after an image workflow.  The
Web equivalent must be owner-scoped, metadata-only and explicitly truthful:
it can create an editable Video Plan draft but never opens media, renders a
video, creates a job or changes wallet/payment state.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_image_studio", "copyfast_memory",
    "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio",
    "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace",
    "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "image-motion-planner-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "image-motion-planner-test-session-secret")
    monkeypatch.setenv("WEBAPP_VIDEO_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_VOICE_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_CONTENT_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROMPT_LIBRARY_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Image Motion Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def insert_image_asset(db_path, email: str, *, state: str = "active") -> str:
    asset_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as conn:
        account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        assert account
        now = "2026-07-15T00:00:00+00:00"
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension, content_type,
                byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, 'png', 'image/png', ?, ?, ?, ?, ?, ?, NULL)""",
            (
                asset_id, str(account[0]), "Ảnh tham chiếu", "motion-reference.png", 123,
                "0" * 64, f"objects/{asset_id}.bin", state, now, now,
            ),
        )
    return asset_id


def make_reference(client: TestClient, csrf: str, db_path, email: str) -> dict[str, str]:
    artboard = client.post(
        "/api/v1/image-studio/artboards",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Image motion artboard",
            "image_intent": "edit",
            "language": "vi",
            "aspect_ratio": "9:16",
            "output_format": "png",
            "creative_brief": "Tạo nhịp chuyển động có kiểm soát cho sản phẩm trong một khung ảnh thuộc kho riêng.",
            "style_direction": "Ánh sáng sạch, chủ thể rõ và khoảng thở hợp lý.",
            "negative_direction": "Không đổi hình dạng sản phẩm, không tạo logo hoặc chữ giả.",
            "tags": ["motion"],
            "project_id": "",
            "idempotency_key": "image-motion-artboard-0001",
        },
    )
    assert artboard.status_code == 200 and artboard.json()["ok"] is True
    artifact = artboard.json()["data"]["artboard"]
    asset_id = insert_image_asset(db_path, email)
    direction = client.post(
        f"/api/v1/image-studio/artboards/{artifact['id']}/directions",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Hero product motion source",
            "operation": "edit",
            "prompt_text": "",
            "edit_instructions": "Giữ chai nước và nền tối giản; dùng để lên kế hoạch chuyển động gọn.",
            "composition_notes": "Sản phẩm ở giữa khung, có khoảng thở phía trên.",
            "negative_direction": "Không tạo watermark, chữ giả hoặc đổi logo.",
            "asset_id": asset_id,
            "reference_asset_id": "",
            "tags": ["hero"],
            "expected_revision": artifact["revision"],
            "idempotency_key": "image-motion-direction-0001",
        },
    )
    assert direction.status_code == 200 and direction.json()["ok"] is True
    return {
        "artboard_id": artifact["id"],
        "direction_id": direction.json()["data"]["direction"]["id"],
        "asset_id": asset_id,
    }


def planner_payload(direction_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "direction_id": direction_id,
        "style": "product_reveal",
        "motion": "orbit_reveal",
        "music": "cinematic_light",
        "duration_seconds": 10,
    }
    payload.update(overrides)
    return payload


def save_payload(direction_id: str, **overrides: Any) -> dict[str, Any]:
    payload = planner_payload(
        direction_id,
        destination="video_plan",
        idempotency_key="image-motion-plan-save-0001",
    )
    payload.update(overrides)
    return payload


def assert_planning_boundary(data: dict[str, Any]) -> None:
    expected = {
        "planner", "execution", "input_persisted", "source_media_inspected", "source_metadata_owner_checked",
        "provider_called", "image_created", "video_created", "audio_created", "preview_created", "output_created",
        "job_created", "payment_started", "wallet_mutated", "asset_saved", "publish_action_created",
        "fact_checked", "rights_verified",
    }
    assert set(data) == expected
    assert data["execution"] == "web_native_image_motion_planning_only"
    assert data["source_metadata_owner_checked"] is True
    for field in expected - {"planner", "execution", "source_metadata_owner_checked"}:
        assert data[field] is False


def assert_save_receipt(data: dict[str, Any]) -> None:
    expected = {
        "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server",
        "web_video_plan_persisted", "browser_result_persisted", "telegram_state_changed", "bot_called",
        "bridge_called", "source_media_inspected", "source_metadata_owner_checked", "media_uploads",
        "provider_called", "image_created", "video_created", "audio_created", "preview_created", "output_created",
        "job_created", "wallet_mutated", "payment_started", "asset_saved", "publish_action_created",
        "delivery_created", "approval_created", "plan_approved", "plan_locked", "generation_started",
        "fact_checked", "rights_verified",
    }
    assert set(data) == expected
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_image_motion_video_plan_server_recomputed"
    assert data["draft_recomputed_on_server"] is True
    assert data["web_video_plan_persisted"] is True
    assert data["source_metadata_owner_checked"] is True
    assert data["scene_count"] == 3
    assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
    for field in expected - {
        "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server",
        "web_video_plan_persisted", "source_metadata_owner_checked",
    }:
        assert data[field] is False


def test_image_motion_planner_is_owner_scoped_metadata_only_and_transient(tmp_path, monkeypatch):
    db_path = tmp_path / "image-motion-planner-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/video-studio/tools/image-motion-planner/references").status_code == 401
        csrf = login(client, "motion-owner@example.com")
        reference = make_reference(client, csrf, db_path, "motion-owner@example.com")

        listing = client.get("/api/v1/video-studio/tools/image-motion-planner/references")
        assert listing.status_code == 200 and listing.json()["ok"] is True
        references = listing.json()["data"]["references"]
        assert len(references) == 1
        item = references[0]
        assert set(item) == {"direction_id", "direction_title", "artboard_id", "artboard_title", "language", "aspect_ratio", "source_image_attached"}
        assert item["direction_id"] == reference["direction_id"]
        assert item["source_image_attached"] is True
        assert reference["asset_id"] not in listing.text

        csrf_missing = client.post("/api/v1/video-studio/tools/image-motion-planner", json=planner_payload(reference["direction_id"]))
        assert csrf_missing.status_code == 403
        result = client.post(
            "/api/v1/video-studio/tools/image-motion-planner",
            headers={"X-CSRF-Token": csrf},
            json=planner_payload(reference["direction_id"]),
        )
        assert result.status_code == 200 and result.json()["ok"] is True
        data = result.json()["data"]
        assert_planning_boundary(data)
        planner = data["planner"]
        assert set(planner) == {"reference", "title", "style", "motion", "music", "duration_seconds", "scenes", "review_before_use"}
        assert planner["reference"] == item
        assert [scene["index"] for scene in planner["scenes"]] == [1, 2, 3]
        assert planner["scenes"][-1]["end_seconds"] == 10
        assert reference["asset_id"] not in result.text
        assert "storage_key" not in result.text
        assert "render" not in str(planner).lower() or "not" in str(planner).lower()

        unsafe_extra = client.post(
            "/api/v1/video-studio/tools/image-motion-planner",
            headers={"X-CSRF-Token": csrf},
            json={**planner_payload(reference["direction_id"]), "asset_id": reference["asset_id"]},
        )
        assert unsafe_extra.status_code == 422

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = login(other, "motion-other@example.com")
            assert other.get("/api/v1/video-studio/tools/image-motion-planner/references").json()["data"]["references"] == []
            denied = other.post(
                "/api/v1/video-studio/tools/image-motion-planner",
                headers={"X-CSRF-Token": csrf_other},
                json=planner_payload(reference["direction_id"]),
            )
            assert denied.status_code == 404


def test_image_motion_planner_save_recomputes_private_plan_once_without_media_execution(tmp_path, monkeypatch):
    db_path = tmp_path / "image-motion-planner-test.db"
    source_phrase = "Giữ chai nước và nền tối giản; dùng để lên kế hoạch chuyển động gọn."
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "motion-save@example.com")
        reference = make_reference(client, csrf, db_path, "motion-save@example.com")
        body = save_payload(reference["direction_id"])
        created = client.post(
            "/api/v1/video-studio/tools/image-motion-planner/save",
            headers={"X-CSRF-Token": csrf},
            json=body,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        receipt = created.json()["data"]
        assert_save_receipt(receipt)
        assert reference["asset_id"] not in created.text
        assert source_phrase not in created.text

        replay = client.post(
            "/api/v1/video-studio/tools/image-motion-planner/save",
            headers={"X-CSRF-Token": csrf},
            json=body,
        )
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.post(
            "/api/v1/video-studio/tools/image-motion-planner/save",
            headers={"X-CSRF-Token": csrf},
            json=save_payload(reference["direction_id"], style="editorial"),
        )
        assert collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        plan_rows = conn.execute("SELECT brief FROM web_video_plans").fetchall()
        scene_count = conn.execute("SELECT COUNT(*) FROM web_video_scenes").fetchone()[0]
        idempotency = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%image-motion-planner%' ").fetchall()
        audits = conn.execute("SELECT detail FROM web_audit_events WHERE action='web.video.image_motion_planner.save_plan'").fetchall()
    assert len(plan_rows) == 1 and source_phrase not in str(plan_rows[0][0])
    assert scene_count == 3
    assert len(idempotency) == 1 and reference["asset_id"] not in str(idempotency[0][0]) and source_phrase not in str(idempotency[0][0])
    assert audits and source_phrase not in str(audits[0][0])


def test_image_motion_planner_rejects_missing_or_inactive_image_reference(tmp_path, monkeypatch):
    db_path = tmp_path / "image-motion-planner-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "motion-guard@example.com")
        artboard = client.post(
            "/api/v1/image-studio/artboards",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Không có ảnh", "image_intent": "create", "language": "vi", "aspect_ratio": "1:1",
                "output_format": "png", "creative_brief": "Draft direction chưa gắn asset.",
                "style_direction": "Sạch và rõ.", "negative_direction": "Không có watermark.", "tags": [],
                "project_id": "", "idempotency_key": "image-motion-empty-artboard-0001",
            },
        ).json()["data"]["artboard"]
        direction = client.post(
            f"/api/v1/image-studio/artboards/{artboard['id']}/directions",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Không có image vault", "operation": "create", "prompt_text": "Một direction chỉ có text.",
                "edit_instructions": "", "composition_notes": "", "negative_direction": "Không có watermark.",
                "asset_id": "", "reference_asset_id": "", "tags": [], "expected_revision": artboard["revision"],
                "idempotency_key": "image-motion-empty-direction-0001",
            },
        ).json()["data"]["direction"]
        missing = client.post(
            "/api/v1/video-studio/tools/image-motion-planner",
            headers={"X-CSRF-Token": csrf},
            json=planner_payload(direction["id"]),
        )
        assert missing.status_code == 422
        assert client.get("/api/v1/video-studio/tools/image-motion-planner/references").json()["data"]["references"] == []

        usable = make_reference(client, csrf, db_path, "motion-guard@example.com")
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_asset_files SET state='archived' WHERE id=?", (usable["asset_id"],))
        inactive = client.post(
            "/api/v1/video-studio/tools/image-motion-planner",
            headers={"X-CSRF-Token": csrf},
            json=planner_payload(usable["direction_id"]),
        )
        assert inactive.status_code == 422
