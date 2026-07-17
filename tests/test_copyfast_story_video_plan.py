"""Focused contracts for Bot-derived prompt-only Story Video Planner."""

from __future__ import annotations

from test_copyfast_media_factory import BOUNDARY_FIELDS, login, make_client


def payload(**overrides) -> dict:
    value = {"topic": "câu chuyện tự viết về người con trở về quê", "language": "vi"}
    value.update(overrides)
    return value


def assert_boundary(data: dict) -> None:
    assert set(data) == {"plan", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_story_video_plan_only"
    assert all(data[field] is False for field in BOUNDARY_FIELDS if field != "execution")


def test_story_video_plan_is_signed_csrf_and_prompt_only(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/story-video-plan"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload()).status_code == 401
        csrf = login(client, "story-video@example.com")
        assert client.post(path, json=payload()).status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"])
        plan = body["data"]["plan"]
        assert set(plan) == {
            "title", "topic", "language", "mode", "story_steps", "motion_prompt", "camera_movement", "style",
            "output_status", "next_workflows", "review_checklist",
        }
        assert plan["mode"] == "prompt_only_manual_review"
        assert plan["output_status"] == "prompt_only_no_real_video"
        assert len(plan["story_steps"]) == 7
        assert len(plan["review_checklist"]) == 3
        assert [(item["label"], item["route"]) for item in plan["next_workflows"]] == [
            ("Storyboard Composer", "/video-studio/storyboard-composer"),
            ("Video Prompt Planner", "/video-studio/prompt-planner"),
            ("Voice Direction Composer", "/voice-studio/direction-composer"),
            ("Content Prompt Pack", "/content/prompt-pack"),
        ]
        assert "job_id" not in response.text
        assert "output_url" not in response.text


def test_story_video_plan_rejects_unsafe_input_and_preserves_guarded_boundary(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/story-video-plan"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "story-video-safety@example.com")
        for invalid in (
            {"topic": "x", "language": "vi"},
            {"topic": "x" * 181, "language": "vi"},
            {"topic": "two\nlines", "language": "vi"},
            {"topic": "https://untrusted.invalid/story", "language": "vi"},
            {"topic": "api_key=super-secret-token-value-12345", "language": "vi"},
            {"topic": 42, "language": "vi"},
            {"topic": "hợp lệ", "language": "fr"},
            {"topic": "hợp lệ", "language": "vi", "provider_url": "https://provider.invalid"},
        ):
            assert client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid).status_code == 422

        guarded = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(topic="tạo deepfake của người thật"))
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_STORY_VIDEO_POLICY_GUARD"
        assert body["data"]["execution"] == "web_native_deterministic_story_video_plan_only"
        assert all(body["data"][field] is False for field in BOUNDARY_FIELDS if field != "execution")

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"topic":"' + (b"x" * (17 * 1024)) + b'","language":"vi"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_MEDIA_FACTORY_BODY_TOO_LARGE"


def test_story_video_plan_supports_english_and_shared_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/story-video-plan"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "story-video-en@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(topic="an original story about returning home", language="en"))
        assert response.status_code == 200
        plan = response.json()["data"]["plan"]
        assert plan["language"] == "en"
        assert plan["story_steps"][0].startswith("Choose material")

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "story-video-disabled@example.com")
        response = disabled.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 503
        assert "WEBAPP_MEDIA_FACTORY_ENABLED" in response.json()["message"]
