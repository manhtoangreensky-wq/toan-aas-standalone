"""Focused contracts for the Bot-derived Web Video Idea Planner.

The Bot ``videoidea`` callback tree only created Telegram planning state.  Its
Web translation must be signed-session/CSRF bounded, deterministic, and never
claim that a provider, media job, payment, asset or delivery was created.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys

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


BOUNDARY_FIELDS = {
    "execution", "input_persisted", "telegram_state_changed", "bot_called", "bridge_called",
    "source_media_inspected", "provider_called", "image_created", "video_created", "audio_created",
    "preview_created", "output_created", "job_created", "payment_started", "wallet_mutated",
    "asset_saved", "publish_action_created", "fact_checked", "rights_verified",
}

SAVE_FIELDS = {
    "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server",
    "web_video_plan_persisted", "browser_result_persisted", "pending_bot_save_created",
    "telegram_state_changed", "bot_called", "bridge_called", "source_media_inspected",
    "media_uploads", "provider_called", "image_created", "video_created", "audio_created",
    "preview_created", "output_created", "job_created", "wallet_mutated", "payment_started",
    "asset_saved", "publish_action_created", "delivery_created", "approval_created",
    "plan_approved", "plan_locked", "generation_started", "fact_checked", "rights_verified",
}


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "video-idea-planner-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "video-idea-planner-test-session-secret")
    monkeypatch.setenv("WEBAPP_VIDEO_STUDIO_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Video Idea Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def planner_payload(**overrides) -> dict:
    payload = {
        "idea_kind": "ad",
        "product_type": "service",
        "topic": "Ứng dụng quản lý đơn hàng cho shop online bận rộn",
        "audience": "Chủ shop nhỏ cần quy trình gọn và dễ theo dõi",
        "goal": "sales",
        "context": "technology",
        "platform": "tiktok",
        "language": "vi",
        "duration_seconds": 30,
        "idea_set": 2,
        "idea_choice": 3,
        "custom_brief": "",
    }
    payload.update(overrides)
    return payload


def save_payload(**overrides) -> dict:
    payload = planner_payload(destination="video_plan", idempotency_key="video-idea-plan-save-0001")
    payload.update(overrides)
    return payload


def storage_counts(db_path) -> dict[str, int]:
    tables = (
        "web_video_plans", "web_video_plan_versions", "web_video_scenes", "web_video_scene_versions",
        "web_video_studio_events", "web_idempotency", "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}


def assert_transient_boundary(data: dict) -> None:
    assert set(data) == {"planner", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_video_idea_only"
    for field in BOUNDARY_FIELDS - {"execution"}:
        assert data[field] is False


def assert_save_receipt(data: dict) -> None:
    assert set(data) == SAVE_FIELDS
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_video_plan_server_recomputed"
    assert data["draft_recomputed_on_server"] is True
    assert data["web_video_plan_persisted"] is True
    assert data["scene_count"] == 6
    assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
    for field in SAVE_FIELDS - {
        "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server", "web_video_plan_persisted",
    }:
        assert data[field] is False


def test_video_idea_planner_requires_signed_session_csrf_and_stays_transient(tmp_path, monkeypatch):
    db_path = tmp_path / "video-idea-planner-test.db"
    path = "/api/v1/video-studio/tools/video-idea-planner"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=planner_payload()).status_code == 401
        csrf = login(client, "video-idea@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=planner_payload()).status_code == 403

        body = planner_payload()
        result = client.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert result.status_code == 200 and result.json()["ok"] is True
        data = result.json()["data"]
        assert_transient_boundary(data)
        planner = data["planner"]
        assert set(planner) == {
            "title", "idea_kind", "product_type", "platform", "aspect_ratio", "goal", "context", "topic",
            "audience", "language", "duration_seconds", "idea_set", "selected_concept", "concepts", "scenes",
            "caption", "hashtags", "review_before_use",
        }
        assert planner["topic"] == body["topic"]
        assert planner["idea_set"] == body["idea_set"]
        assert planner["selected_concept"]["index"] == body["idea_choice"]
        assert [item["index"] for item in planner["concepts"]] == [1, 2, 3]
        assert [scene["index"] for scene in planner["scenes"]] == [1, 2, 3, 4, 5, 6]
        assert planner["scenes"][-1]["end_seconds"] == body["duration_seconds"]
        assert all(scene["end_seconds"] > scene["start_seconds"] for scene in planner["scenes"])
        assert "provider" not in str(planner).lower() or "không tạo" in result.json()["message"].lower()
        assert storage_counts(db_path) == before


def test_video_idea_planner_can_save_one_server_recomputed_private_plan_and_replay(tmp_path, monkeypatch):
    db_path = tmp_path / "video-idea-planner-test.db"
    path = "/api/v1/video-studio/tools/video-idea-planner/save"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "video-idea-save@example.com")
        body = save_payload()
        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert created.status_code == 200 and created.json()["ok"] is True
        assert_save_receipt(created.json()["data"])
        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.post(path, headers={"X-CSRF-Token": csrf}, json=save_payload(goal="brand"))
        assert collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        plan = conn.execute("SELECT title, brief FROM web_video_plans").fetchone()
        scene_count = conn.execute("SELECT COUNT(*) FROM web_video_scenes").fetchone()[0]
        receipt = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%video-idea-planner%' ").fetchone()
        audit = conn.execute("SELECT detail FROM web_audit_events WHERE action='web.video.idea_planner.save_plan'").fetchone()
    assert plan and "Video Idea" in plan[0]
    assert scene_count == 6
    assert receipt and json.loads(str(receipt[0]))["data"]["provider_called"] is False
    assert audit and "server-recomputed" in str(audit[0])


def test_video_idea_planner_rejects_extra_state_sensitive_inputs_and_guards_unsafe_text(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/video-idea-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "video-idea-schema@example.com")
        headers = {"X-CSRF-Token": csrf}
        assert client.post(path, headers=headers, json={**planner_payload(), "job_id": "should-not-exist"}).status_code == 422
        assert client.post(path, headers=headers, json=planner_payload(idea_kind="custom", custom_brief="")).status_code == 422
        custom = client.post(
            path,
            headers=headers,
            json=planner_payload(idea_kind="custom", custom_brief="Kể lại hành trình khách hàng theo trải nghiệm do thương hiệu tự sở hữu."),
        )
        assert custom.status_code == 200 and custom.json()["ok"] is True
        guarded = client.post(
            path,
            headers=headers,
            json=planner_payload(topic="Tạo video giống phong cách của một ca sĩ nổi tiếng"),
        )
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["provider_called"] is False


def test_video_idea_planner_respects_video_studio_gate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "video-idea-disabled@example.com")
        response = client.post(
            "/api/v1/video-studio/tools/video-idea-planner",
            headers={"X-CSRF-Token": csrf},
            json=planner_payload(),
        )
    assert response.status_code == 503
