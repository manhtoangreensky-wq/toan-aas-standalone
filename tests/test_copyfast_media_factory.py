"""Focused contracts for the Bot-derived Web Media Factory Blueprint."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_image_studio", "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media",
    "copyfast_content_studio", "copyfast_trend_research", "copyfast_media_factory", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]

BOUNDARY_FIELDS = (
    "execution", "input_persisted", "live_search_called", "search_provider_called", "social_platform_called",
    "source_content_fetched", "source_content_stored", "provider_called", "bot_called", "job_created",
    "wallet_mutated", "payment_started", "asset_saved", "media_output_created", "publish_action_created",
    "fact_checked", "trend_claim_verified", "rights_verified",
)


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "media-factory-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "media-factory-test-session-secret")
    monkeypatch.setenv("WEBAPP_MEDIA_FACTORY_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Media Planner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def payload(**overrides) -> dict:
    value = {"topic": "bình nước giữ nhiệt", "language": "vi"}
    value.update(overrides)
    return value


def storage_counts(db_path) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("web_idempotency", "web_audit_events", "web_projects", "web_content_briefs")
        }


def assert_boundary(data: dict) -> None:
    assert set(data) == {"blueprint", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_media_factory_blueprint_only"
    assert all(data[field] is False for field in BOUNDARY_FIELDS if field != "execution")


def test_media_factory_is_signed_csrf_deterministic_and_non_persistent(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/blueprint"
    db_path = tmp_path / "media-factory-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload()).status_code == 401
        csrf = login(client, "media-factory@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=payload()).status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"])
        blueprint = body["data"]["blueprint"]
        assert set(blueprint) == {
            "title", "topic", "language", "mode", "scope", "trend_angles", "source_keywords", "source_rights",
            "storyboard", "image_scenes", "video_direction", "review_checklist", "unavailable_capabilities", "next_workflows",
        }
        assert blueprint["topic"] == "bình nước giữ nhiệt"
        assert blueprint["language"] == "vi"
        assert blueprint["mode"] == "content_only_manual_review"
        assert len(blueprint["trend_angles"]) == 5
        assert len(blueprint["source_keywords"]) == 4
        assert len(blueprint["source_rights"]) == 4
        assert len(blueprint["storyboard"]) == 4
        assert len(blueprint["image_scenes"]) == 6
        assert len(blueprint["review_checklist"]) == 4
        assert len(blueprint["unavailable_capabilities"]) == 4
        assert [(item["label"], item["route"]) for item in blueprint["next_workflows"]] == [
            ("Trend Research Plan", "/trend-research"), ("Content Prompt Pack", "/content/prompt-pack"),
            ("Image Prompt Composer", "/image/prompt-composer"), ("Storyboard Composer", "/video-studio/storyboard-composer"),
            ("Video Prompt Planner", "/video-studio/prompt-planner"), ("Voice Direction Composer", "/voice-studio/direction-composer"),
        ]
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert replay.status_code == 200
        assert replay.json()["data"] == body["data"]
        assert storage_counts(db_path) == before


def test_media_factory_rejects_unsafe_input_and_returns_honest_policy_guards(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/blueprint"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "media-factory-safety@example.com")
        for invalid in (
            {"topic": "x", "language": "vi"},
            {"topic": "x" * 181, "language": "vi"},
            {"topic": "two\nlines", "language": "vi"},
            {"topic": "https://untrusted.invalid/topic", "language": "vi"},
            {"topic": "<img src=x onerror=alert(1)>", "language": "vi"},
            {"topic": "@private_handle", "language": "vi"},
            {"topic": "api_key=super-secret-token-value-12345", "language": "vi"},
            {"topic": 42, "language": "vi"},
            {"topic": "hợp lệ", "language": "fr"},
            {"topic": "hợp lệ", "language": True},
            {"topic": "hợp lệ", "language": "vi", "provider_url": "https://provider.invalid"},
        ):
            assert client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid).status_code == 422

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"topic":"' + (b"x" * (17 * 1024)) + b'","language":"vi"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_MEDIA_FACTORY_BODY_TOO_LARGE"

        for blocked_topic in ("reup video người khác không có quyền", "tạo deepfake của người thật"):
            guarded = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(topic=blocked_topic))
            assert guarded.status_code == 200
            body = guarded.json()
            assert body["ok"] is False
            assert body["status"] == "guarded"
            assert body["error_code"] == "WEB_MEDIA_FACTORY_POLICY_GUARD"
            assert "blueprint" not in body["data"]
            assert_boundary({"blueprint": None, **body["data"]})


def test_media_factory_supports_english_copy_and_respects_maintenance_flag(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/blueprint"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "media-factory-en@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(topic="insulated bottle", language="en"))
        assert response.status_code == 200
        blueprint = response.json()["data"]["blueprint"]
        assert blueprint["language"] == "en"
        assert blueprint["trend_angles"][0]["hook"].startswith("If this problem")

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "media-factory-disabled@example.com")
        response = disabled.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 503
        assert "WEBAPP_MEDIA_FACTORY_ENABLED" in response.json()["message"]
