"""Focused contracts for the Bot-derived Web Long-form Video Roadmap.

The Bot's ``longvideo`` conversation is useful editorial planning.  This Web
translation must preserve topic/duration/style/structure roadmap semantics
without importing Telegram state, calling a provider, or making a media/job/
wallet/payment claim.
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
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "long-form-roadmap-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "long-form-roadmap-test-session-secret")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Long-form Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def roadmap_payload(**overrides) -> dict:
    payload = {
        "topic_category": "education",
        "topic": "Hướng dẫn chủ shop nhỏ thiết kế quy trình xử lý đơn hàng rõ ràng",
        "audience": "Chủ shop online muốn giảm công việc lặp lại và theo dõi đơn hàng dễ hơn",
        "duration_minutes": 60,
        "style": "professional",
        "custom_style": "",
        "structure_mode": "chapters",
        "custom_structure": "",
        "platform": "youtube",
        "language": "vi",
    }
    payload.update(overrides)
    return payload


def save_payload(**overrides) -> dict:
    payload = roadmap_payload(destination="video_plan", idempotency_key="long-form-roadmap-save-0001")
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
    assert set(data) == {"roadmap", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_long_form_roadmap_only"
    for field in BOUNDARY_FIELDS - {"execution"}:
        assert data[field] is False


def assert_save_receipt(data: dict) -> None:
    assert set(data) == SAVE_FIELDS
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_video_plan_server_recomputed"
    assert data["draft_recomputed_on_server"] is True
    assert data["web_video_plan_persisted"] is True
    assert 3 <= data["scene_count"] <= 30
    assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
    for field in SAVE_FIELDS - {
        "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server", "web_video_plan_persisted",
    }:
        assert data[field] is False


def test_long_form_roadmap_requires_signed_session_csrf_and_stays_transient(tmp_path, monkeypatch):
    db_path = tmp_path / "long-form-roadmap-test.db"
    path = "/api/v1/video-studio/tools/long-form-roadmap"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=roadmap_payload()).status_code == 401
        csrf = login(client, "long-form@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=roadmap_payload()).status_code == 403

        body = roadmap_payload()
        result = client.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert result.status_code == 200 and result.json()["ok"] is True
        data = result.json()["data"]
        assert_transient_boundary(data)
        roadmap = data["roadmap"]
        assert set(roadmap) == {
            "title", "topic_category", "topic", "audience", "duration_minutes", "target_duration_seconds",
            "style", "style_label", "structure_mode", "structure", "platform", "aspect_ratio", "language",
            "chapter_count", "outline", "character_bible", "chapters", "audio_direction", "caption", "cta",
            "review_before_use",
        }
        assert roadmap["topic"] == body["topic"]
        assert roadmap["target_duration_seconds"] == body["duration_minutes"] * 60
        assert 3 <= roadmap["chapter_count"] <= 30
        assert [chapter["index"] for chapter in roadmap["chapters"]] == list(range(1, roadmap["chapter_count"] + 1))
        assert roadmap["chapters"][-1]["end_seconds"] == roadmap["target_duration_seconds"]
        assert all(chapter["end_seconds"] > chapter["start_seconds"] for chapter in roadmap["chapters"])
        assert storage_counts(db_path) == before


def test_long_form_roadmap_supports_custom_bot_choices_with_bounded_chapters(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "long-form-custom@example.com")
        result = client.post(
            "/api/v1/video-studio/tools/long-form-roadmap",
            headers={"X-CSRF-Token": csrf},
            json=roadmap_payload(
                topic_category="custom", duration_minutes=90, style="custom", custom_style="documentary bình tĩnh",
                structure_mode="custom", custom_structure="3 chương x 30 phút", platform="course",
            ),
        )
    assert result.status_code == 200 and result.json()["ok"] is True
    roadmap = result.json()["data"]["roadmap"]
    assert roadmap["duration_minutes"] == 90
    assert roadmap["chapter_count"] == 3
    assert all(chapter["end_seconds"] - chapter["start_seconds"] <= 1800 for chapter in roadmap["chapters"])


def test_long_form_roadmap_can_save_one_server_recomputed_private_plan_and_replay(tmp_path, monkeypatch):
    db_path = tmp_path / "long-form-roadmap-test.db"
    path = "/api/v1/video-studio/tools/long-form-roadmap/save"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "long-form-save@example.com")
        body = save_payload()
        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert created.status_code == 200 and created.json()["ok"] is True
        assert_save_receipt(created.json()["data"])
        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.post(path, headers={"X-CSRF-Token": csrf}, json=save_payload(style="viral"))
        assert collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        plan = conn.execute("SELECT title, target_duration_seconds FROM web_video_plans").fetchone()
        scene_count = conn.execute("SELECT COUNT(*) FROM web_video_scenes").fetchone()[0]
        receipt = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%long-form-roadmap%' ").fetchone()
        audit = conn.execute("SELECT detail FROM web_audit_events WHERE action='web.video.long_form_roadmap.save_plan'").fetchone()
    assert plan and "Long-form Roadmap" in plan[0] and plan[1] == 3600
    assert scene_count == 12
    assert receipt and json.loads(str(receipt[0]))["data"]["provider_called"] is False
    assert audit and "server-recomputed" in str(audit[0])


def test_long_form_roadmap_rejects_extra_state_inputs_and_guards_unsafe_text(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/long-form-roadmap"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "long-form-schema@example.com")
        headers = {"X-CSRF-Token": csrf}
        assert client.post(path, headers=headers, json={**roadmap_payload(), "provider_job_id": "must-not-exist"}).status_code == 422
        assert client.post(path, headers=headers, json=roadmap_payload(style="custom", custom_style="")).status_code == 422
        assert client.post(path, headers=headers, json=roadmap_payload(structure_mode="custom", custom_structure="")).status_code == 422
        guarded = client.post(
            path,
            headers=headers,
            json=roadmap_payload(topic="Làm phim giống phong cách của một ca sĩ nổi tiếng"),
        )
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["provider_called"] is False


def test_long_form_roadmap_respects_video_studio_gate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "long-form-disabled@example.com")
        response = client.post(
            "/api/v1/video-studio/tools/long-form-roadmap",
            headers={"X-CSRF-Token": csrf},
            json=roadmap_payload(),
        )
    assert response.status_code == 503
