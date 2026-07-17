"""Focused contracts for the Bot-derived Web ``selfscene`` planner.

The Web translation deliberately accepts only a bounded text direction brief.
It must require affirmative customer assertions for consent/right-to-use,
avoid every media/provider/Bot side effect, and save only an owner-scoped Web
Video Plan when the customer explicitly asks for that handoff.
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
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "self-shot-scene-planner-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "self-shot-scene-planner-test-session-secret")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Self-shot Owner"},
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
        "subject_kind": "product",
        "subject_description": "Chai nước giữ nhiệt do thương hiệu sở hữu",
        "preserve_details": "dáng chai, màu xanh đậm và logo đã được cấp quyền",
        "direction_mode": "context",
        "custom_direction": "",
        "target_context": "bàn làm việc sáng, gọn và có chiều sâu tự nhiên",
        "motion": "pushin",
        "custom_motion": "",
        "music": "corporate",
        "custom_music": "",
        "platform": "reels",
        "duration_seconds": 20,
        "language": "vi",
        "rights_to_source_confirmed": True,
        "person_likeness_consent_confirmed": True,
        "brand_or_logo_rights_confirmed": True,
        "no_impersonation_or_harm_confirmed": True,
    }
    payload.update(overrides)
    return payload


def save_payload(**overrides) -> dict:
    payload = planner_payload(destination="video_plan", idempotency_key="self-shot-scene-save-0001")
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
    assert data["execution"] == "web_native_deterministic_self_shot_scene_planner_only"
    for field in BOUNDARY_FIELDS - {"execution"}:
        assert data[field] is False


def assert_save_receipt(data: dict) -> None:
    assert set(data) == SAVE_FIELDS
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_self_shot_scene_video_plan_server_recomputed"
    assert data["draft_recomputed_on_server"] is True
    assert data["web_video_plan_persisted"] is True
    assert data["scene_count"] == 1
    assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
    for field in SAVE_FIELDS - {
        "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server", "web_video_plan_persisted",
    }:
        assert data[field] is False


def test_self_shot_scene_planner_requires_signed_session_csrf_and_all_four_assertions(tmp_path, monkeypatch):
    db_path = tmp_path / "self-shot-scene-planner-test.db"
    path = "/api/v1/video-studio/tools/self-shot-scene-planner"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=planner_payload()).status_code == 401
        csrf = login(client, "self-shot-compose@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=planner_payload()).status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=planner_payload())
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert_transient_boundary(data)
        planner = data["planner"]
        assert set(planner) == {
            "title", "subject_kind", "subject_description", "preserve_details", "direction_mode",
            "direction_label", "target_context", "motion", "motion_label", "music", "music_label",
            "platform", "aspect_ratio", "duration_seconds", "language", "transformation_brief",
            "video_prompt", "keyframe_image_prompt", "motion_suggestions", "identity_safety",
            "finishing_notes", "review_before_use",
        }
        assert planner["subject_description"] == planner_payload()["subject_description"]
        assert planner["duration_seconds"] == 20
        assert planner["aspect_ratio"] == "9:16"
        assert len(planner["motion_suggestions"]) == 3
        assert "không nhận, mở, kiểm tra hay biến đổi media" in " ".join(planner["review_before_use"])
        assert storage_counts(db_path) == before

        headers = {"X-CSRF-Token": csrf}
        for assertion in (
            "rights_to_source_confirmed",
            "person_likeness_consent_confirmed",
            "brand_or_logo_rights_confirmed",
            "no_impersonation_or_harm_confirmed",
        ):
            rejected = client.post(path, headers=headers, json=planner_payload(**{assertion: False}))
            assert rejected.status_code == 422, assertion


def test_self_shot_scene_planner_guards_impersonation_and_rejects_untrusted_state_inputs(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/self-shot-scene-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "self-shot-guard@example.com")
        headers = {"X-CSRF-Token": csrf}
        extra = client.post(path, headers=headers, json={**planner_payload(), "source_media_url": "https://example.invalid/source.mp4"})
        assert extra.status_code == 422
        guarded = client.post(
            path,
            headers=headers,
            json=planner_payload(subject_description="Mô phỏng khuôn mặt của một ca sĩ trong khung cảnh mới"),
        )
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False and body["status"] == "guarded"
        assert body["error_code"] == "WEB_SELF_SHOT_SCENE_LIKENESS_GUARD"
        assert set(body["data"]) == BOUNDARY_FIELDS
        assert body["data"]["provider_called"] is False
        assert body["data"]["rights_verified"] is False


def test_self_shot_scene_save_is_server_recomputed_idempotent_and_private_to_owner(tmp_path, monkeypatch):
    db_path = tmp_path / "self-shot-scene-planner-test.db"
    path = "/api/v1/video-studio/tools/self-shot-scene-planner/save"
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = login(owner, "self-shot-owner@example.com")
        body = save_payload()
        created = owner.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert created.status_code == 200 and created.json()["ok"] is True
        receipt = created.json()["data"]
        assert_save_receipt(receipt)
        plan_id = receipt["plan"]["id"]

        replay = owner.post(path, headers={"X-CSRF-Token": csrf}, json=body)
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = owner.post(path, headers={"X-CSRF-Token": csrf}, json=save_payload(duration_seconds=30))
        assert collision.status_code == 409

        with make_client(tmp_path, monkeypatch) as other:
            login(other, "self-shot-other@example.com")
            denied = other.get(f"/api/v1/video-studio/plans/{plan_id}")
            assert denied.status_code == 200
            assert denied.json()["ok"] is False
            assert denied.json()["error_code"] == "WEB_VIDEO_PLAN_NOT_FOUND"

    with sqlite3.connect(db_path) as conn:
        plan = conn.execute("SELECT title, target_duration_seconds, brief FROM web_video_plans").fetchone()
        scene = conn.execute("SELECT duration_seconds, shot_notes FROM web_video_scenes").fetchone()
        receipt_row = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%self-shot-scene-planner%'"
        ).fetchone()
        audit = conn.execute(
            "SELECT detail FROM web_audit_events WHERE action='web.video.self_shot_scene.save_plan'"
        ).fetchone()
    assert plan and "Self-shot Scene Direction" in str(plan[0]) and plan[1] == 20
    assert "No source media" in str(plan[2])
    assert scene and scene[0] == 20 and "No media, preview, provider, job, payment or delivery" in str(scene[1])
    assert receipt_row and json.loads(str(receipt_row[0]))["data"]["provider_called"] is False
    assert audit and "server-recomputed" in str(audit[0])


def test_self_shot_scene_planner_respects_video_studio_gate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "self-shot-disabled@example.com")
        response = client.post(
            "/api/v1/video-studio/tools/self-shot-scene-planner",
            headers={"X-CSRF-Token": csrf},
            json=planner_payload(),
        )
    assert response.status_code == 503
