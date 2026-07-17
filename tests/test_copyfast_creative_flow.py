"""Focused contracts for the Bot-derived Web Creative Flow Composer."""

from __future__ import annotations

from test_copyfast_media_factory import BOUNDARY_FIELDS, login, make_client


def payload(**overrides) -> dict:
    value = {"idea": "video quảng cáo máy xay sinh tố mini TikTok 15 giây", "language": "vi"}
    value.update(overrides)
    return value


def assert_boundary(data: dict) -> None:
    assert set(data) == {"flow", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_creative_flow_only"
    assert all(data[field] is False for field in BOUNDARY_FIELDS if field != "execution")


def test_creative_flow_is_signed_csrf_deterministic_and_contains_bot_template_sections(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/creative-flow"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload()).status_code == 401
        csrf = login(client, "creative-flow@example.com")
        assert client.post(path, json=payload()).status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"])
        flow = body["data"]["flow"]
        assert set(flow) == {
            "title", "idea", "language", "mode", "script_framework", "image_prompt", "image_story_direction",
            "music_search", "sfx_search", "caption_hashtags", "cta", "next_workflows", "review_checklist",
        }
        assert flow["idea"] == payload()["idea"]
        assert flow["mode"] == "template_only_manual_review"
        assert len(flow["script_framework"]) == 5
        assert len(flow["review_checklist"]) == 3
        assert [(item["label"], item["route"]) for item in flow["next_workflows"]] == [
            ("Image Prompt Composer", "/image/prompt-composer"),
            ("Storyboard Composer", "/video-studio/storyboard-composer"),
            ("Music Prompt Composer", "/media-workspace/music-prompt-composer"),
            ("Content Prompt Pack", "/content/prompt-pack"),
        ]
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert replay.status_code == 200
        assert replay.json()["data"] == body["data"]


def test_creative_flow_rejects_unsafe_input_and_preserves_guarded_boundary(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/creative-flow"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "creative-flow-safety@example.com")
        for invalid in (
            {"idea": "x", "language": "vi"},
            {"idea": "x" * 181, "language": "vi"},
            {"idea": "two\nlines", "language": "vi"},
            {"idea": "https://untrusted.invalid/idea", "language": "vi"},
            {"idea": "api_key=super-secret-token-value-12345", "language": "vi"},
            {"idea": 42, "language": "vi"},
            {"idea": "hợp lệ", "language": "fr"},
            {"idea": "hợp lệ", "language": "vi", "provider": "x"},
        ):
            assert client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid).status_code == 422

        guarded = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(idea="reup video người khác không có quyền"))
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_CREATIVE_FLOW_POLICY_GUARD"
        assert "flow" not in body["data"]
        assert body["data"]["execution"] == "web_native_deterministic_creative_flow_only"
        assert all(body["data"][field] is False for field in BOUNDARY_FIELDS if field != "execution")

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"idea":"' + (b"x" * (17 * 1024)) + b'","language":"vi"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_MEDIA_FACTORY_BODY_TOO_LARGE"


def test_creative_flow_supports_english_copy_and_shared_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/media-factory/creative-flow"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "creative-flow-en@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(idea="portable blender TikTok 15 seconds", language="en"))
        assert response.status_code == 200
        assert response.json()["data"]["flow"]["language"] == "en"
        assert response.json()["data"]["flow"]["script_framework"][0].startswith("Open with")

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "creative-flow-disabled@example.com")
        response = disabled.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 503
        assert "WEBAPP_MEDIA_FACTORY_ENABLED" in response.json()["message"]
