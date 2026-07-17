"""Focused contracts for the safe Web replacement of Bot ``videoref`` plans.

The Web planner must use a signed, owner-scoped Asset Vault video selector,
but never open or analyze that video.  It may persist only a server-recomputed
private Video Plan draft after explicit idempotent confirmation.
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
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "reference-format-planner-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "reference-format-planner-test-session-secret")
    monkeypatch.setenv("WEBAPP_VIDEO_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Reference Planner Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def insert_video_asset(db_path, email: str, *, state: str = "active", extension: str = "mp4", content_type: str = "video/mp4") -> str:
    asset_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as conn:
        account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        assert account
        now = "2026-07-15T00:00:00+00:00"
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension, content_type,
                byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
            (
                asset_id, str(account[0]), "Video format tham chiếu", f"reference.{extension}", extension,
                content_type, 456, "1" * 64, f"objects/{asset_id}.bin", state, now, now,
            ),
        )
    return asset_id


def planner_payload(asset_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "asset_id": asset_id,
        "direction": "product_ad",
        "platform": "tiktok",
        "goal": "educate",
        "tone": "clear",
        "topic": "Bộ công cụ quản lý đơn hàng cho shop online nhỏ",
        "audience": "Chủ shop online cần quy trình gọn và dễ theo dõi",
        "language": "vi",
        "duration_seconds": 30,
    }
    payload.update(overrides)
    return payload


def save_payload(asset_id: str, **overrides: Any) -> dict[str, Any]:
    payload = planner_payload(asset_id, destination="video_plan", idempotency_key="reference-format-plan-save-0001")
    payload.update(overrides)
    return payload


def assert_planning_boundary(data: dict[str, Any]) -> None:
    expected = {
        "planner", "execution", "input_persisted", "source_video_opened", "source_metadata_owner_checked",
        "reference_analysis_performed", "source_link_fetched", "provider_called", "image_created", "video_created",
        "audio_created", "preview_created", "output_created", "job_created", "payment_started", "wallet_mutated",
        "asset_saved", "publish_action_created", "fact_checked", "rights_verified",
    }
    assert set(data) == expected
    assert data["execution"] == "web_native_reference_format_planning_only"
    assert data["source_metadata_owner_checked"] is True
    for field in expected - {"planner", "execution", "source_metadata_owner_checked"}:
        assert data[field] is False


def assert_save_receipt(data: dict[str, Any]) -> None:
    expected = {
        "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server", "web_video_plan_persisted",
        "browser_result_persisted", "telegram_state_changed", "bot_called", "bridge_called", "source_video_opened",
        "source_metadata_owner_checked", "reference_analysis_performed", "source_link_fetched", "media_uploads",
        "provider_called", "image_created", "video_created", "audio_created", "preview_created", "output_created",
        "job_created", "wallet_mutated", "payment_started", "asset_saved", "publish_action_created", "delivery_created",
        "approval_created", "plan_approved", "plan_locked", "generation_started", "fact_checked", "rights_verified",
    }
    assert set(data) == expected
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_reference_format_video_plan_server_recomputed"
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


def test_reference_format_planner_is_owner_scoped_metadata_only_and_transient(tmp_path, monkeypatch):
    db_path = tmp_path / "reference-format-planner-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/video-studio/tools/reference-format-planner/references").status_code == 401
        csrf = login(client, "reference-owner@example.com")
        asset_id = insert_video_asset(db_path, "reference-owner@example.com")

        listing = client.get("/api/v1/video-studio/tools/reference-format-planner/references")
        assert listing.status_code == 200 and listing.json()["ok"] is True
        references = listing.json()["data"]["references"]
        assert references == [{
            "asset_id": asset_id, "display_name": "Video format tham chiếu", "extension": "mp4",
            "content_type": "video/mp4", "source_video_attached": True,
        }]
        assert "storage_key" not in listing.text and "objects/" not in listing.text

        assert client.post("/api/v1/video-studio/tools/reference-format-planner", json=planner_payload(asset_id)).status_code == 403
        result = client.post(
            "/api/v1/video-studio/tools/reference-format-planner",
            headers={"X-CSRF-Token": csrf},
            json=planner_payload(asset_id),
        )
        assert result.status_code == 200 and result.json()["ok"] is True
        data = result.json()["data"]
        assert_planning_boundary(data)
        planner = data["planner"]
        assert set(planner) == {"reference", "title", "direction", "platform", "goal", "tone", "topic", "audience", "language", "duration_seconds", "scenes", "review_before_use"}
        assert planner["reference"] == references[0]
        assert [scene["index"] for scene in planner["scenes"]] == [1, 2, 3]
        assert planner["scenes"][-1]["end_seconds"] == 30
        assert "storage_key" not in result.text and "objects/" not in result.text
        assert "not opened" in str(planner).lower() or "không bị mở" in str(planner).lower()

        extra = client.post(
            "/api/v1/video-studio/tools/reference-format-planner",
            headers={"X-CSRF-Token": csrf},
            json={**planner_payload(asset_id), "source_url": "https://example.com/video"},
        )
        assert extra.status_code == 422

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = login(other, "reference-other@example.com")
            assert other.get("/api/v1/video-studio/tools/reference-format-planner/references").json()["data"]["references"] == []
            denied = other.post(
                "/api/v1/video-studio/tools/reference-format-planner",
                headers={"X-CSRF-Token": csrf_other},
                json=planner_payload(asset_id),
            )
            assert denied.status_code == 404


def test_reference_format_planner_save_recomputes_private_plan_once_without_video_execution(tmp_path, monkeypatch):
    db_path = tmp_path / "reference-format-planner-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "reference-save@example.com")
        asset_id = insert_video_asset(db_path, "reference-save@example.com")
        body = save_payload(asset_id)
        created = client.post(
            "/api/v1/video-studio/tools/reference-format-planner/save",
            headers={"X-CSRF-Token": csrf},
            json=body,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        receipt = created.json()["data"]
        assert_save_receipt(receipt)
        assert asset_id not in created.text
        replay = client.post(
            "/api/v1/video-studio/tools/reference-format-planner/save",
            headers={"X-CSRF-Token": csrf},
            json=body,
        )
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.post(
            "/api/v1/video-studio/tools/reference-format-planner/save",
            headers={"X-CSRF-Token": csrf},
            json=save_payload(asset_id, tone="premium"),
        )
        assert collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        plan_rows = conn.execute("SELECT brief FROM web_video_plans").fetchall()
        scene_count = conn.execute("SELECT COUNT(*) FROM web_video_scenes").fetchone()[0]
        idempotency = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%reference-format-planner%' ").fetchall()
        audits = conn.execute("SELECT detail FROM web_audit_events WHERE action='web.video.reference_format_planner.save_plan'").fetchall()
    assert len(plan_rows) == 1 and asset_id not in str(plan_rows[0][0])
    assert scene_count == 3
    assert len(idempotency) == 1 and asset_id not in str(idempotency[0][0])
    assert audits and asset_id not in str(audits[0][0])


def test_reference_format_planner_rejects_inactive_or_non_video_asset(tmp_path, monkeypatch):
    db_path = tmp_path / "reference-format-planner-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "reference-guard@example.com")
        inactive = insert_video_asset(db_path, "reference-guard@example.com", state="archived")
        wrong_kind = insert_video_asset(db_path, "reference-guard@example.com", extension="png", content_type="image/png")
        assert client.get("/api/v1/video-studio/tools/reference-format-planner/references").json()["data"]["references"] == []
        for asset_id in (inactive, wrong_kind):
            response = client.post(
                "/api/v1/video-studio/tools/reference-format-planner",
                headers={"X-CSRF-Token": csrf},
                json=planner_payload(asset_id),
            )
            assert response.status_code == 422
