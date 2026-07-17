"""Focused contracts for the Web-native Storyboard Prompt Pack Composer.

The source Bot's storyboard grammar is useful as a planning reference, but
this Web surface is deliberately a signed, transient text-composer.  It must
not become a render, provider, job, billing, Asset Vault, publish or durable
Video Studio workflow merely because its result is detailed.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from collections.abc import Iterator
from typing import Any

import pytest
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


BOUNDARY_FIELDS = (
    "execution",
    "input_persisted",
    "source_media_inspected",
    "provider_called",
    "image_created",
    "video_created",
    "audio_created",
    "preview_created",
    "output_created",
    "job_created",
    "payment_started",
    "wallet_mutated",
    "asset_saved",
    "publish_action_created",
    "fact_checked",
    "rights_verified",
)

EXPECTED_DATA_FIELDS = {"composer", *BOUNDARY_FIELDS}


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "storyboard-composer-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "storyboard-composer-test-session-secret")
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
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Storyboard Composer Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def composer_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "topic": "Ra mắt bình nước giữ nhiệt tối giản cho người đi làm bận rộn",
        "template": "product_ad",
        "platform": "tiktok_reels",
        "aspect_ratio": "9:16",
        "duration_seconds": 15,
        "style": "clean",
        "goal": "introduce",
        "language": "vi",
        "idea_choice": 1,
        "brief": "Giữ bố cục rõ, không tạo claim chưa được kiểm chứng và chừa CTA cho bước biên tập.",
    }
    payload.update(overrides)
    return payload


def storyboard_storage_counts(db_path) -> dict[str, int]:
    """All durable Video Studio stores a stateless composer must not touch."""

    tables = (
        "web_video_plans",
        "web_video_plan_versions",
        "web_video_scenes",
        "web_video_scene_versions",
        "web_video_studio_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def _walk_values(value: Any) -> Iterator[Any]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _walk_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def assert_boundary(data: dict[str, Any]) -> None:
    assert set(data) == EXPECTED_DATA_FIELDS
    assert data["execution"] == "web_native_deterministic_storyboard_composer_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def assert_choice(value: Any, expected_id: str) -> None:
    assert isinstance(value, dict)
    assert set(value) == {"id", "label"}
    assert value["id"] == expected_id
    assert isinstance(value["label"], str) and value["label"].strip()


def assert_composer_shape(composer: dict[str, Any], source: dict[str, Any]) -> None:
    """Exact data shape keeps a detailed plan renderer-safe and honest."""

    assert set(composer) == {
        "title",
        "topic",
        "brief",
        "template",
        "platform",
        "aspect_ratio",
        "duration_seconds",
        "style",
        "goal",
        "language",
        "idea_choice",
        "creative_directions",
        "selected_direction",
        "visual_canon",
        "shots",
        "scene_prompts",
        "meta_ai_prompts",
        "caption",
        "hashtags",
        "cta",
        "cautions",
        "review_before_use",
    }
    for field in ("title", "topic", "language"):
        assert isinstance(composer[field], str) and composer[field].strip()
    assert composer["topic"] == source["topic"]
    assert composer["brief"] == source.get("brief", "")
    assert composer["aspect_ratio"] == source["aspect_ratio"]
    assert composer["duration_seconds"] == source["duration_seconds"]
    assert composer["language"] == source["language"]
    assert composer["idea_choice"] == source["idea_choice"]
    for field in ("template", "platform", "style", "goal"):
        assert_choice(composer[field], source[field])

    directions = composer["creative_directions"]
    assert isinstance(directions, list) and len(directions) == 3
    for index, direction in enumerate(directions, start=1):
        assert set(direction) == {"index", "title", "premise", "hook", "structure", "cta"}
        assert direction["index"] == index
        assert all(
            isinstance(direction[field], str) and direction[field].strip()
            for field in ("title", "premise", "hook", "structure", "cta")
        )
    assert composer["selected_direction"] == directions[source["idea_choice"] - 1]

    canon = composer["visual_canon"]
    assert set(canon) == {
        "subject",
        "setting",
        "style",
        "aspect_ratio",
        "continuity_locks",
        "negative_constraints",
    }
    assert canon["aspect_ratio"] == source["aspect_ratio"]
    assert all(isinstance(canon[field], str) and canon[field].strip() for field in ("subject", "setting", "style"))
    for field, expected_count in (("continuity_locks", 4), ("negative_constraints", 5)):
        assert isinstance(canon[field], list) and len(canon[field]) == expected_count
        assert all(isinstance(item, str) and item.strip() for item in canon[field])

    expected_scene_count = {15: 5, 30: 6, 60: 10}[source["duration_seconds"]]
    shots = composer["shots"]
    prompts = composer["scene_prompts"]
    assert isinstance(shots, list) and len(shots) == expected_scene_count
    assert isinstance(prompts, list) and len(prompts) == expected_scene_count
    previous_end = 0
    for index, shot in enumerate(shots, start=1):
        assert set(shot) == {
            "index",
            "start_seconds",
            "end_seconds",
            "beat",
            "visual",
            "action",
            "camera",
            "transition",
            "voiceover",
            "cta_space",
        }
        assert shot["index"] == index
        assert isinstance(shot["start_seconds"], int | float)
        assert isinstance(shot["end_seconds"], int | float)
        assert 0 <= shot["start_seconds"] < shot["end_seconds"] <= source["duration_seconds"]
        assert shot["start_seconds"] == previous_end
        previous_end = shot["end_seconds"]
        assert all(
            isinstance(shot[field], str) and shot[field].strip()
            for field in ("beat", "visual", "action", "camera", "transition", "voiceover", "cta_space")
        )
    assert shots[-1]["end_seconds"] == source["duration_seconds"]

    for index, prompt in enumerate(prompts, start=1):
        assert set(prompt) == {"index", "image_prompt", "video_prompt", "negative_prompt"}
        assert prompt["index"] == index
        assert all(
            isinstance(prompt[field], str) and prompt[field].strip()
            for field in ("image_prompt", "video_prompt", "negative_prompt")
        )

    meta_prompts = composer["meta_ai_prompts"]
    assert isinstance(meta_prompts, list) and len(meta_prompts) == 3
    for index, prompt in enumerate(meta_prompts, start=1):
        assert set(prompt) == {"index", "label", "prompt"}
        assert prompt["index"] == index
        assert all(isinstance(prompt[field], str) and prompt[field].strip() for field in ("label", "prompt"))

    assert isinstance(composer["caption"], str) and composer["caption"].strip()
    assert isinstance(composer["cta"], str) and composer["cta"].strip()
    assert isinstance(composer["hashtags"], list) and len(composer["hashtags"]) == 4
    assert all(isinstance(tag, str) and tag.strip() for tag in composer["hashtags"])

    for field, minimum in (("cautions", 0), ("review_before_use", 1)):
        entries = composer[field]
        assert isinstance(entries, list) and minimum <= len(entries) <= 6
        assert all(isinstance(entry, str) and entry.strip() for entry in entries)


def assert_no_execution_or_delivery_reference(data: dict[str, Any]) -> None:
    keys = set(_walk_keys(data))
    assert not keys.intersection({
        "provider_url", "provider_id", "job_id", "payment_url", "output_url", "video_url",
        "preview_url", "asset_url", "download_url", "render_url",
    })
    strings = [item for item in _walk_values(data) if isinstance(item, str)]
    assert not any("http://" in item.lower() or "https://" in item.lower() for item in strings)


def test_storyboard_composer_is_session_csrf_bounded_deterministic_and_non_persistent(tmp_path, monkeypatch):
    """A complete-looking storyboard remains a planning receipt, never media work."""

    db_path = tmp_path / "storyboard-composer-test.db"
    path = "/api/v1/video-studio/tools/storyboard-composer"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=composer_payload()).status_code == 401
        csrf = login(client, "storyboard-composer@example.com")
        before = storyboard_storage_counts(db_path)

        assert client.post(path, json=composer_payload()).status_code == 403
        source = composer_payload()
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"])
        assert_composer_shape(body["data"]["composer"], source)
        assert_no_execution_or_delivery_reference(body["data"])

        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert repeated.status_code == 200
        assert repeated.json()["data"] == body["data"]
        assert storyboard_storage_counts(db_path) == before


def test_storyboard_composer_accepts_an_omitted_optional_brief(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/storyboard-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "storyboard-optional-brief@example.com")
        source = composer_payload()
        del source["brief"]
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_boundary(data)
        assert data["composer"]["brief"] == ""


@pytest.mark.parametrize(
    ("template", "platform", "aspect_ratio", "duration", "style", "goal", "language", "idea"),
    (
        ("product_ad", "tiktok_reels", "9:16", 15, "clean", "sell", "vi", 1),
        ("cinematic_story", "facebook", "16:9", 30, "cinematic", "engage", "en", 2),
        ("tiktok_reels", "youtube_shorts", "1:1", 60, "tiktok", "introduce", "vi", 3),
        ("tutorial", "youtube", "9:16", 15, "tech", "educate", "en", 1),
        ("shop_affiliate", "custom", "16:9", 30, "lifestyle", "custom", "vi", 2),
        ("custom", "tiktok_reels", "1:1", 60, "luxury", "sell", "en", 3),
        ("product_ad", "facebook", "9:16", 15, "drama", "engage", "vi", 1),
        ("cinematic_story", "youtube_shorts", "16:9", 30, "product", "introduce", "en", 2),
        ("tiktok_reels", "youtube", "1:1", 60, "custom", "educate", "vi", 3),
    ),
)
def test_storyboard_composer_covers_every_supported_public_choice(
    tmp_path,
    monkeypatch,
    template,
    platform,
    aspect_ratio,
    duration,
    style,
    goal,
    language,
    idea,
):
    """The compact matrix exercises every enum without running external work."""

    path = "/api/v1/video-studio/tools/storyboard-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, f"storyboard-{template}-{platform}-{duration}@example.com")
        source = composer_payload(
            template=template,
            platform=platform,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration,
            style=style,
            goal=goal,
            language=language,
            idea_choice=idea,
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200, source
        data = response.json()["data"]
        assert_boundary(data)
        assert_composer_shape(data["composer"], source)


@pytest.mark.parametrize(
    "overrides",
    (
        {"topic": "x"},
        {"topic": "x" * 501},
        {"brief": "x" * 501},
        {"template": "render_video"},
        {"platform": "instagram"},
        {"aspect_ratio": "4:5"},
        {"duration_seconds": "15"},
        {"duration_seconds": 10},
        {"duration_seconds": 120},
        {"style": "provider_model"},
        {"goal": "convert"},
        {"language": "fr"},
        {"idea_choice": True},
        {"idea_choice": 0},
        {"idea_choice": 4},
        {"provider_url": "https://provider.invalid/private"},
        {"unexpected": "must be rejected"},
    ),
)
def test_storyboard_composer_rejects_invalid_or_expanded_schema(tmp_path, monkeypatch, overrides):
    path = "/api/v1/video-studio/tools/storyboard-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "storyboard-schema@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(**overrides))
        assert response.status_code == 422
        assert response.headers["Cache-Control"] == "no-store, private"


def test_storyboard_composer_rejects_dlp_and_guards_originality_or_claims(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/storyboard-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "storyboard-policy@example.com")
        headers = {"X-CSRF-Token": csrf}

        for overrides in (
            {"topic": "<img src=x onerror=alert(1)>"},
            {"brief": "Dựng lại nội dung từ https://untrusted.example/private.mp4"},
            {"brief": "api_key=super-secret-token-value-12345"},
            {"topic": "Sản phẩm @render_handle"},
        ):
            rejected = client.post(path, headers=headers, json=composer_payload(**overrides))
            assert rejected.status_code == 422
            assert rejected.headers["Cache-Control"] == "no-store, private"

        originality = client.post(
            path,
            headers=headers,
            json=composer_payload(topic="Tạo quảng cáo với gương mặt giống một ca sĩ cụ thể."),
        )
        assert originality.status_code == 200
        originality_body = originality.json()
        assert originality_body["ok"] is False
        assert originality_body["status"] == "guarded"
        assert originality_body["error_code"] == "WEB_STORYBOARD_COMPOSER_ORIGINALITY_GUARD"
        assert "composer" not in originality_body.get("data", {})
        assert set(originality_body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"composer": {}, **originality_body["data"]})

        nonconsensual = client.post(
            path,
            headers=headers,
            json=composer_payload(brief="Dùng ca sĩ thật không có sự đồng ý làm chủ thể cho storyboard."),
        )
        assert nonconsensual.status_code == 200
        nonconsensual_body = nonconsensual.json()
        assert nonconsensual_body["ok"] is False
        assert nonconsensual_body["status"] == "guarded"
        assert nonconsensual_body["error_code"] == "WEB_STORYBOARD_COMPOSER_ORIGINALITY_GUARD"
        assert "composer" not in nonconsensual_body.get("data", {})
        assert set(nonconsensual_body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"composer": {}, **nonconsensual_body["data"]})

        claim = client.post(
            path,
            headers=headers,
            json=composer_payload(topic="Cam kết chữa khỏi bệnh trong 24 giờ."),
        )
        assert claim.status_code == 200
        claim_body = claim.json()
        assert claim_body["ok"] is False
        assert claim_body["status"] == "guarded"
        assert claim_body["error_code"] == "WEB_STORYBOARD_COMPOSER_CLAIM_GUARD"
        assert "composer" not in claim_body.get("data", {})
        assert set(claim_body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"composer": {}, **claim_body["data"]})


def test_storyboard_composer_respects_video_studio_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/storyboard-composer"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "storyboard-disabled@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload())
        assert response.status_code == 503
        assert "WEBAPP_VIDEO_STUDIO_ENABLED" in response.text


def test_storyboard_composer_maximum_valid_text_never_500s_or_delivers_media(tmp_path, monkeypatch):
    """Long valid text plus the ten-shot variant remains bounded and transient."""

    db_path = tmp_path / "storyboard-composer-test.db"
    path = "/api/v1/video-studio/tools/storyboard-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "storyboard-maximum@example.com")
        before = storyboard_storage_counts(db_path)
        source = composer_payload(
            topic="t" * 500,
            brief="b" * 500,
            template="custom",
            platform="custom",
            aspect_ratio="1:1",
            duration_seconds=60,
            style="custom",
            goal="custom",
            language="en",
            idea_choice=3,
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_boundary(data)
        assert_composer_shape(data["composer"], source)
        assert_no_execution_or_delivery_reference(data)
        assert storyboard_storage_counts(db_path) == before


def test_storyboard_composer_save_recomputes_a_private_draft_video_plan_once(tmp_path, monkeypatch):
    """The explicit save handoff persists only Web authoring records and receipt metadata."""

    db_path = tmp_path / "storyboard-composer-test.db"
    path = "/api/v1/video-studio/tools/storyboard-composer/save"
    topic = "Bình nước giữ nhiệt tối giản cho người đi làm bận rộn"
    source = composer_payload(
        topic=topic,
        duration_seconds=30,
        idea_choice=2,
        destination="video_plan",
        idempotency_key="storyboard-save-recompute-0001",
    )
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=source).status_code == 401
        csrf = login(client, "storyboard-save-owner@example.com")
        assert client.post(path, json=source).status_code == 403

        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert created.status_code == 200
        assert created.headers["Cache-Control"] == "no-store, private"
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert set(data) == {
            "destination",
            "plan",
            "scene_count",
            "execution",
            "draft_recomputed_on_server",
            "web_video_plan_persisted",
            "browser_result_persisted",
            "pending_bot_save_created",
            "telegram_state_changed",
            "bot_called",
            "bridge_called",
            "source_media_inspected",
            "provider_called",
            "image_created",
            "video_created",
            "audio_created",
            "preview_created",
            "output_created",
            "job_created",
            "wallet_mutated",
            "payment_started",
            "asset_saved",
            "publish_action_created",
            "delivery_created",
            "plan_approved",
            "plan_locked",
            "generation_started",
            "fact_checked",
            "rights_verified",
        }
        assert data["destination"] == "video_plan"
        assert data["execution"] == "web_native_video_plan_server_recomputed"
        assert data["draft_recomputed_on_server"] is True
        assert data["web_video_plan_persisted"] is True
        for field in set(data) - {"destination", "plan", "scene_count", "execution", "draft_recomputed_on_server", "web_video_plan_persisted"}:
            assert data[field] is False
        assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
        assert data["scene_count"] == 6
        assert topic not in created.text
        assert_no_execution_or_delivery_reference(data)

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert replay.status_code == 200
        assert replay.json() == body
        collision = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**source, "topic": "Bình nước mới với brief khác", "idempotency_key": source["idempotency_key"]},
        )
        assert collision.status_code == 409

        plan_id = data["plan"]["id"]
        detail = client.get(f"/api/v1/video-studio/plans/{plan_id}")
        assert detail.status_code == 200
        detail_data = detail.json()["data"]
        assert detail_data["plan"]["state"] == "draft"
        assert len(detail_data["scenes"]) == 6
        assert topic in detail_data["plan"]["brief"]
        assert all(scene["state"] == "active" and scene["revision"] == 1 for scene in detail_data["scenes"])

        second_csrf = login(client, "storyboard-save-other-owner@example.com")
        hidden = client.get(f"/api/v1/video-studio/plans/{plan_id}", headers={"X-CSRF-Token": second_csrf})
        assert hidden.status_code == 200
        assert hidden.json()["ok"] is False
        assert hidden.json()["error_code"] == "WEB_VIDEO_PLAN_NOT_FOUND"

        with sqlite3.connect(db_path) as connection:
            plan_count = connection.execute("SELECT COUNT(*) FROM web_video_plans").fetchone()[0]
            version_count = connection.execute("SELECT COUNT(*) FROM web_video_plan_versions").fetchone()[0]
            scene_count = connection.execute("SELECT COUNT(*) FROM web_video_scenes").fetchone()[0]
            scene_version_count = connection.execute("SELECT COUNT(*) FROM web_video_scene_versions").fetchone()[0]
            event_count = connection.execute("SELECT COUNT(*) FROM web_video_studio_events").fetchone()[0]
            receipt = connection.execute(
                "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%:storyboard-composer:save-plan'"
            ).fetchone()
            audit = connection.execute(
                "SELECT action, target, detail FROM web_audit_events WHERE action=?",
                ("web.video.storyboard_composer.save_plan",),
            ).fetchone()
        assert (plan_count, version_count, scene_count, scene_version_count, event_count) == (1, 1, 6, 6, 7)
        assert receipt is not None and topic not in str(receipt[0])
        assert audit is not None
        assert audit[0] == "web.video.storyboard_composer.save_plan"
        assert audit[1] == plan_id
        assert topic not in str(audit[2])


def test_storyboard_composer_save_has_strict_schema_guards_and_respects_video_gate(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/storyboard-composer/save"
    source = composer_payload(destination="video_plan", idempotency_key="storyboard-save-schema-0001")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "storyboard-save-schema@example.com")
        headers = {"X-CSRF-Token": csrf}
        for invalid in (
            {**source, "destination": "memory_note"},
            {**source, "idempotency_key": "short"},
            {**source, "composer": {"browser": "result"}},
            {**source, "scenes": []},
            {**source, "provider_id": "not-allowed"},
        ):
            response = client.post(path, headers=headers, json=invalid)
            assert response.status_code == 422
            assert response.headers["Cache-Control"] == "no-store, private"

        guarded = client.post(
            path,
            headers=headers,
            json={**source, "topic": "Cam kết chữa khỏi bệnh trong 24 giờ.", "idempotency_key": "storyboard-save-guarded-0001"},
        )
        assert guarded.status_code == 200
        guarded_body = guarded.json()
        assert guarded_body["ok"] is False
        assert guarded_body["error_code"] == "WEB_STORYBOARD_COMPOSER_CLAIM_GUARD"
        assert guarded_body["data"]["destination"] == "video_plan"
        assert guarded_body["data"]["draft_recomputed_on_server"] is False
        assert guarded_body["data"]["web_video_plan_persisted"] is False
        assert guarded_body["data"]["job_created"] is False
        assert guarded_body["data"]["provider_called"] is False

    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "storyboard-save-disabled@example.com")
        disabled = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert disabled.status_code == 503
        assert "WEBAPP_VIDEO_STUDIO_ENABLED" in disabled.text
