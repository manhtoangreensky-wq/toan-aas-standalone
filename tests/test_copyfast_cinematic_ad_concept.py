"""Focused contracts for the Web-native Cinematic Ad Concept Composer.

This Bot-derived composer is intentionally a deterministic planning receipt,
not a render, media, provider, job, billing, Asset Vault or publishing
surface.  These checks keep the high-risk access, schema and honesty
boundaries explicit while the product-facing composition remains fast.
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


PLAN_SAVE_BOUNDARY_FIELDS = (
    "execution",
    "draft_recomputed_on_server",
    "web_video_plan_persisted",
    "browser_result_persisted",
    "pending_bot_save_created",
    "telegram_state_changed",
    "bot_called",
    "bridge_called",
    "source_media_inspected",
    "media_uploads",
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
    "approval_created",
    "plan_approved",
    "plan_locked",
    "generation_started",
    "fact_checked",
    "rights_verified",
)


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "cinematic-ad-concept-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "cinematic-ad-concept-test-session-secret")
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
            "display_name": "Cinematic Concept Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def concept_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "product": "Bình nước giữ nhiệt gọn nhẹ cho người đi làm",
        "message": "Giữ nhịp ngày bận rộn với một thói quen nhỏ rõ ràng và đáng tin cậy.",
        "message_theme": "time_save",
        "style": "cinematic",
        "language": "vi",
        "idea_choice": 1,
        "motion_choice": 1,
        "video_duration_variant": 15,
        "music_choice": "1",
    }
    payload.update(overrides)
    return payload


def concept_save_payload(**overrides: Any) -> dict[str, Any]:
    payload = concept_payload(
        destination="video_plan",
        idempotency_key="cinematic-concept-save-0001",
    )
    payload.update(overrides)
    return payload


def cinematic_storage_counts(db_path) -> dict[str, int]:
    """All durable Video Studio stores a stateless concept must not touch."""

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
    assert data["execution"] == "web_native_deterministic_cinematic_concept_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def assert_plan_save_receipt(data: dict[str, Any]) -> None:
    assert set(data) == {"destination", "plan", "scene_count", *PLAN_SAVE_BOUNDARY_FIELDS}
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_video_plan_server_recomputed"
    assert data["draft_recomputed_on_server"] is True
    assert data["web_video_plan_persisted"] is True
    assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
    assert data["scene_count"] == 3
    for field in set(data) - {
        "destination",
        "plan",
        "scene_count",
        "execution",
        "draft_recomputed_on_server",
        "web_video_plan_persisted",
    }:
        assert data[field] is False


def assert_choice(value: Any, expected_id: str) -> None:
    assert isinstance(value, dict)
    assert set(value) == {"id", "label"}
    assert value["id"] == expected_id
    assert isinstance(value["label"], str) and value["label"].strip()


def assert_concept_shape(composer: dict[str, Any], source: dict[str, Any]) -> None:
    assert set(composer) == {
        "title",
        "product",
        "message",
        "message_theme",
        "style",
        "language",
        "idea_choice",
        "motion_choice",
        "video_duration_variant",
        "music_choice",
        "topic",
        "creative_directions",
        "selected_direction",
        "scripts",
        "storyboard",
        "shot_list",
        "image_prompts",
        "video_prompts",
        "motion_plan",
        "music_direction",
        "cautions",
        "review_before_use",
    }
    assert all(
        isinstance(composer[field], str) and composer[field].strip()
        for field in ("title", "product", "message", "language", "topic")
    )
    assert composer["product"] == source["product"]
    assert composer["message"] == source["message"]
    assert composer["language"] == source["language"]
    assert composer["idea_choice"] == source["idea_choice"]
    assert composer["motion_choice"] == source["motion_choice"]
    assert composer["video_duration_variant"] == source["video_duration_variant"]
    # ``message_theme`` and ``style`` expose user-facing catalog labels.
    # ``music_choice`` deliberately stays the exact input code; the detailed
    # labelled text object is ``music_direction`` below.
    assert_choice(composer["message_theme"], source["message_theme"])
    assert_choice(composer["style"], source["style"])
    assert composer["music_choice"] == source["music_choice"]

    directions = composer["creative_directions"]
    assert isinstance(directions, list) and len(directions) == 3
    for index, direction in enumerate(directions, start=1):
        assert set(direction) == {"index", "title", "premise", "brand_story", "hook", "cta"}
        assert direction["index"] == index
        assert all(
            isinstance(direction[field], str) and direction[field].strip()
            for field in ("title", "premise", "brand_story", "hook", "cta")
        )
    assert composer["selected_direction"] == directions[source["idea_choice"] - 1]

    scripts = composer["scripts"]
    assert isinstance(scripts, dict)
    assert set(scripts) == {"15s", "30s", "60s"}
    assert all(isinstance(script, str) and script.strip() for script in scripts.values())

    storyboard = composer["storyboard"]
    assert isinstance(storyboard, list) and len(storyboard) == 3
    previous_end = 0
    for index, beat in enumerate(storyboard, start=1):
        assert set(beat) == {
            "index", "start_seconds", "end_seconds", "setting", "subject", "action",
            "emotion", "camera", "transition", "voiceover", "cta_space",
        }
        assert beat["index"] == index
        assert isinstance(beat["start_seconds"], int | float)
        assert isinstance(beat["end_seconds"], int | float)
        assert 0 <= beat["start_seconds"] < beat["end_seconds"] <= source["video_duration_variant"]
        assert beat["start_seconds"] >= previous_end
        previous_end = beat["end_seconds"]
        assert all(
            isinstance(beat[field], str) and beat[field].strip()
            for field in ("setting", "subject", "action", "emotion", "camera", "transition", "voiceover", "cta_space")
        )
    assert storyboard[-1]["end_seconds"] == source["video_duration_variant"]

    shots = composer["shot_list"]
    assert isinstance(shots, list) and 1 <= len(shots) <= 10
    assert all(isinstance(shot, str) and shot.strip() for shot in shots)

    image_prompts = composer["image_prompts"]
    assert isinstance(image_prompts, list) and len(image_prompts) == 3
    for index, prompt in enumerate(image_prompts, start=1):
        assert set(prompt) == {"index", "label", "prompt", "negative_prompt"}
        assert prompt["index"] == index
        assert all(isinstance(prompt[field], str) and prompt[field].strip() for field in ("label", "prompt", "negative_prompt"))

    video_prompts = composer["video_prompts"]
    assert isinstance(video_prompts, list) and len(video_prompts) == 3
    assert [prompt["duration_seconds"] for prompt in video_prompts] == [5, 10, 15]
    for prompt in video_prompts:
        assert set(prompt) == {"duration_seconds", "prompt", "negative_prompt"}
        assert all(isinstance(prompt[field], str) and prompt[field].strip() for field in ("prompt", "negative_prompt"))

    motion = composer["motion_plan"]
    assert isinstance(motion, dict)
    assert set(motion) == {"id", "title", "timeline", "camera", "transitions", "shot_direction"}
    # The motion direction itself uses a compact catalog code; the request's
    # selected ``motion_choice`` remains the integer selection above.
    assert motion["id"] == str(source["motion_choice"])
    assert all(isinstance(motion[field], str) and motion[field].strip() for field in motion)

    music = composer["music_direction"]
    assert isinstance(music, dict)
    assert set(music) == {"id", "label", "direction", "ai_music_prompt"}
    assert music["id"] == source["music_choice"]
    assert all(isinstance(music[field], str) and music[field].strip() for field in music)

    for field, minimum in (("cautions", 0), ("review_before_use", 1)):
        entries = composer[field]
        assert isinstance(entries, list) and minimum <= len(entries) <= 6
        assert all(isinstance(entry, str) and entry.strip() for entry in entries)


def assert_no_execution_or_delivery_reference(data: dict[str, Any]) -> None:
    keys = set(_walk_keys(data))
    assert not keys.intersection({"provider_url", "provider_id", "job_id", "payment_url", "output_url", "video_url", "preview_url", "asset_url"})
    strings = [item for item in _walk_values(data) if isinstance(item, str)]
    assert not any("http://" in item.lower() or "https://" in item.lower() for item in strings)


def test_cinematic_concept_is_session_csrf_bounded_deterministic_and_non_persistent(tmp_path, monkeypatch):
    """A high-quality creative brief must not silently create a video workflow."""

    db_path = tmp_path / "cinematic-ad-concept-test.db"
    path = "/api/v1/video-studio/tools/cinematic-concept"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=concept_payload()).status_code == 401
        csrf = login(client, "cinematic-concept@example.com")
        before = cinematic_storage_counts(db_path)

        assert client.post(path, json=concept_payload()).status_code == 403
        source = concept_payload()
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"])
        assert_concept_shape(body["data"]["composer"], source)
        assert_no_execution_or_delivery_reference(body["data"])

        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert repeated.status_code == 200
        assert repeated.json()["data"] == body["data"]

        # This helper is intentionally not a plan write, revision, event,
        # idempotency receipt or audit event.
        assert cinematic_storage_counts(db_path) == before


def test_cinematic_concept_covers_every_supported_public_choice(tmp_path, monkeypatch):
    """One compact matrix covers all fixed catalog values without live calls."""

    path = "/api/v1/video-studio/tools/cinematic-concept"
    matrix = (
        ("memory", "cinematic", "vi", 1, 1, 5, "1"),
        ("success", "bw_luxury", "en", 2, 2, 10, "2"),
        ("confidence", "viral", "vi", 3, 3, 15, "3"),
        ("time_save", "direct_sales", "en", 1, 1, 5, "none"),
        ("luxury", "ugc", "vi", 2, 2, 10, "1"),
        ("future", "fpv", "en", 3, 3, 15, "2"),
        ("family", "product_reveal", "vi", 1, 1, 5, "3"),
        ("before_after", "cinematic", "en", 2, 2, 10, "none"),
        ("custom", "bw_luxury", "vi", 3, 3, 15, "1"),
        ("memory", "direct_sales", "zh", 1, 3, 15, "ai_prompt"),
    )
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "cinematic-catalog@example.com")
        for theme, style, language, idea, motion, duration, music in matrix:
            source = concept_payload(
                message_theme=theme,
                style=style,
                language=language,
                idea_choice=idea,
                motion_choice=motion,
                video_duration_variant=duration,
                music_choice=music,
            )
            response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
            assert response.status_code == 200, source
            data = response.json()["data"]
            assert_boundary(data)
            assert_concept_shape(data["composer"], source)


def test_cinematic_concept_resolves_bot_default_message_server_side_and_recomputes_save(tmp_path, monkeypatch):
    """The Bot's skip text is explicit input metadata, never browser composer text."""

    compose_path = "/api/v1/video-studio/tools/cinematic-concept"
    save_path = "/api/v1/video-studio/tools/cinematic-concept/save"
    bot_default_zh = "清晰易懂地介绍产品/服务，建立信任，并用轻柔 CTA 引导行动。"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "cinematic-default-message@example.com")
        headers = {"X-CSRF-Token": csrf}
        source = concept_payload(
            message="",
            message_mode="bot_default",
            language="zh",
            music_choice="ai_prompt",
        )
        composed = client.post(compose_path, headers=headers, json=source)
        assert composed.status_code == 200
        composer = composed.json()["data"]["composer"]
        assert_concept_shape(composer, {**source, "message": bot_default_zh})
        assert "message_mode" not in composer
        assert composer["message"] == bot_default_zh
        assert composer["music_direction"]["id"] == "ai_prompt"
        assert "编辑文本" in composer["music_direction"]["direction"]
        assert "不创建音频" in composer["music_direction"]["ai_music_prompt"]

        # A browser may request the canonical skip mode, but cannot replay the
        # resolved sentence while claiming it came from the Bot-default path.
        mixed = client.post(
            compose_path,
            headers=headers,
            json=concept_payload(message=bot_default_zh, message_mode="bot_default", language="zh"),
        )
        assert mixed.status_code == 422

        save_source = concept_save_payload(
            message="",
            message_mode="bot_default",
            language="zh",
            music_choice="ai_prompt",
            idempotency_key="cinematic-concept-default-message-0001",
        )
        saved = client.post(save_path, headers=headers, json=save_source)
        assert saved.status_code == 200
        save_data = saved.json()["data"]
        assert_plan_save_receipt(save_data)
        assert bot_default_zh not in saved.text
        detail = client.get(f"/api/v1/video-studio/plans/{save_data['plan']['id']}")
        assert detail.status_code == 200
        assert bot_default_zh in detail.json()["data"]["plan"]["brief"]


def test_cinematic_concept_localizes_zh_and_style_changes_direction_without_vietnamese_english_mix(tmp_path, monkeypatch):
    """Locale and style remain deterministic editorial text, not provider knobs."""

    path = "/api/v1/video-studio/tools/cinematic-concept"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "cinematic-localized-style@example.com")
        headers = {"X-CSRF-Token": csrf}
        english = concept_payload(language="en", style="cinematic", music_choice="ai_prompt")
        luxury = {**english, "style": "bw_luxury"}
        chinese = {**english, "language": "zh", "style": "product_reveal"}

        english_composer = client.post(path, headers=headers, json=english).json()["data"]["composer"]
        luxury_composer = client.post(path, headers=headers, json=luxury).json()["data"]["composer"]
        chinese_response = client.post(path, headers=headers, json=chinese)
        assert chinese_response.status_code == 200
        chinese_composer = chinese_response.json()["data"]["composer"]

        assert "Hướng motion video" not in english_composer["video_prompts"][0]["prompt"]
        assert english_composer["video_prompts"][0]["prompt"].startswith("Editorial 5s video motion direction")
        assert "soft directional light" in english_composer["image_prompts"][0]["prompt"]
        assert "sculpted monochrome light" in luxury_composer["image_prompts"][0]["prompt"]
        assert english_composer["storyboard"][0]["camera"] != luxury_composer["storyboard"][0]["camera"]
        assert english_composer["video_prompts"][0]["prompt"] != luxury_composer["video_prompts"][0]["prompt"]
        assert chinese_composer["message_theme"]["label"] == "省时、轻松工作"
        assert "产品揭示" in chinese_composer["video_prompts"][0]["prompt"]
        assert "仅是文本计划" in chinese_composer["video_prompts"][0]["prompt"]


@pytest.mark.parametrize(
    "overrides",
    (
        {"product": "x"},
        {"product": "x" * 501},
        {"message": ""},
        {"message": "x"},
        {"message": "x" * 501},
        {"message_mode": "telegram_skip"},
        {"message_theme": "live_trend"},
        {"style": "provider_model"},
        {"language": "fr"},
        {"idea_choice": 0},
        {"idea_choice": 4},
        {"motion_choice": 0},
        {"motion_choice": 4},
        {"video_duration_variant": 12},
        {"music_choice": "0"},
        {"provider_url": "https://provider.invalid/private"},
        {"unexpected": "must be rejected"},
    ),
)
def test_cinematic_concept_rejects_invalid_or_expanded_schema(tmp_path, monkeypatch, overrides):
    path = "/api/v1/video-studio/tools/cinematic-concept"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "cinematic-schema@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=concept_payload(**overrides))
        assert response.status_code == 422
        assert response.headers["Cache-Control"] == "no-store, private"


def test_cinematic_concept_rejects_dlp_and_guards_originality_or_claims(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/cinematic-concept"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "cinematic-policy@example.com")
        headers = {"X-CSRF-Token": csrf}

        for overrides in (
            {"product": "<img src=x onerror=alert(1)>"},
            {"message": "Dựng lại nội dung từ https://untrusted.example/private.mp4"},
            {"message": "api_key=super-secret-token-value-12345"},
            {"product": "Sản phẩm @render_handle"},
        ):
            rejected = client.post(path, headers=headers, json=concept_payload(**overrides))
            assert rejected.status_code == 422
            assert rejected.headers["Cache-Control"] == "no-store, private"

        originality = client.post(
            path,
            headers=headers,
            json=concept_payload(message="Tạo hình ảnh người nổi tiếng với gương mặt giống ca sĩ cụ thể."),
        )
        assert originality.status_code == 200
        originality_body = originality.json()
        assert originality_body["ok"] is False
        assert originality_body["status"] == "guarded"
        assert originality_body["error_code"] == "WEB_CINEMATIC_CONCEPT_ORIGINALITY_GUARD"
        assert "composer" not in originality_body.get("data", {})
        assert set(originality_body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"composer": {}, **originality_body["data"]})

        claim = client.post(
            path,
            headers=headers,
            json=concept_payload(message="Cam kết chữa khỏi bệnh trong 24 giờ."),
        )
        assert claim.status_code == 200
        claim_body = claim.json()
        assert claim_body["ok"] is False
        assert claim_body["status"] == "guarded"
        assert claim_body["error_code"] == "WEB_CINEMATIC_CONCEPT_CLAIM_GUARD"
        assert "composer" not in claim_body.get("data", {})
        assert set(claim_body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"composer": {}, **claim_body["data"]})


def test_cinematic_concept_respects_video_studio_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/cinematic-concept"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "cinematic-disabled@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=concept_payload())
        assert response.status_code == 503
        assert "WEBAPP_VIDEO_STUDIO_ENABLED" in response.text


def test_cinematic_concept_maximum_valid_text_never_500s_or_delivers_media(tmp_path, monkeypatch):
    """Long but valid inputs stay a bounded plan and never become a delivery."""

    path = "/api/v1/video-studio/tools/cinematic-concept"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "cinematic-maximum@example.com")
        source = concept_payload(
            product="p" * 500,
            message="m" * 500,
            message_theme="custom",
            style="product_reveal",
            language="en",
            idea_choice=3,
            motion_choice=3,
            video_duration_variant=15,
            music_choice="none",
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_boundary(data)
        assert_concept_shape(data["composer"], source)
        assert_no_execution_or_delivery_reference(data)


def test_cinematic_concept_save_recomputes_a_private_draft_video_plan_once(tmp_path, monkeypatch):
    """A durable handoff writes only owner-scoped Web authoring metadata."""

    db_path = tmp_path / "cinematic-ad-concept-test.db"
    path = "/api/v1/video-studio/tools/cinematic-concept/save"
    product = "Bình nước giữ nhiệt gọn nhẹ cho người đi làm"
    message = "Giữ nhịp ngày bận rộn với một thói quen nhỏ rõ ràng và đáng tin cậy."
    source = concept_save_payload(
        product=product,
        message=message,
        idempotency_key="cinematic-concept-save-recompute-0001",
    )
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=source).status_code == 401
        csrf = login(client, "cinematic-save-owner@example.com")
        assert client.post(path, json=source).status_code == 403

        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert created.status_code == 200
        assert created.headers["Cache-Control"] == "no-store, private"
        body = created.json()
        assert body["ok"] is True and body["status"] == "draft"
        data = body["data"]
        assert_plan_save_receipt(data)
        # Receipt/idempotency data is deliberately content-free: no product,
        # message, prompt, storyboard, asset/provider/job/payment or delivery
        # reference is reflected to the browser for this write.
        assert product not in created.text
        assert message not in created.text
        assert "composer" not in data and "prompt" not in data

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert replay.status_code == 200
        assert replay.json() == body
        collision = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={
                **source,
                "message": "Một thông điệp khác không thể tái sử dụng idempotency key cũ.",
                "idempotency_key": source["idempotency_key"],
            },
        )
        assert collision.status_code == 409

        plan_id = data["plan"]["id"]
        detail = client.get(f"/api/v1/video-studio/plans/{plan_id}")
        assert detail.status_code == 200
        detail_data = detail.json()["data"]
        assert detail_data["plan"]["state"] == "draft"
        assert "Web-native plan rebuilt on the server" in detail_data["plan"]["brief"]
        assert len(detail_data["scenes"]) == 3
        assert all(scene["state"] == "active" and scene["revision"] == 1 for scene in detail_data["scenes"])
        assert product in detail_data["scenes"][0]["visual_direction"]

        second_csrf = login(client, "cinematic-save-other-owner@example.com")
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
                "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%:cinematic-concept:save-plan'"
            ).fetchone()
            audit = connection.execute(
                "SELECT action, target, detail FROM web_audit_events WHERE action=?",
                ("web.video.cinematic_concept.save_plan",),
            ).fetchone()
        assert (plan_count, version_count, scene_count, scene_version_count, event_count) == (1, 1, 3, 3, 4)
        assert receipt is not None and product not in str(receipt[0]) and message not in str(receipt[0])
        assert audit is not None
        assert audit[0] == "web.video.cinematic_concept.save_plan"
        assert audit[1] == plan_id
        assert product not in str(audit[2]) and message not in str(audit[2])


def test_cinematic_concept_save_has_strict_schema_guards_and_respects_video_gate(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/cinematic-concept/save"
    source = concept_save_payload(idempotency_key="cinematic-concept-save-schema-0001")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "cinematic-save-schema@example.com")
        headers = {"X-CSRF-Token": csrf}
        for invalid in (
            {**source, "destination": "memory_note"},
            {**source, "idempotency_key": "short"},
            {**source, "idea_choice": "1"},
            {**source, "composer": {"browser": "generated-result"}},
            {**source, "plan": {"browser": "generated-plan"}},
            {**source, "storyboard": []},
            {**source, "imagevideo": {"source": "not-allowed"}},
            {**source, "files": ["not-allowed"]},
            {**source, "source_url": "https://provider.invalid/private.mp4"},
            {**source, "asset_id": "not-allowed"},
        ):
            response = client.post(path, headers=headers, json=invalid)
            assert response.status_code == 422
            assert response.headers["Cache-Control"] == "no-store, private"

        guarded = client.post(
            path,
            headers=headers,
            json={
                **source,
                "message": "Cam kết chữa khỏi bệnh trong 24 giờ.",
                "idempotency_key": "cinematic-concept-save-guarded-0001",
            },
        )
        assert guarded.status_code == 200
        guarded_body = guarded.json()
        assert guarded_body["ok"] is False
        assert guarded_body["error_code"] == "WEB_CINEMATIC_CONCEPT_CLAIM_GUARD"
        assert guarded_body["data"]["destination"] == "video_plan"
        assert guarded_body["data"]["draft_recomputed_on_server"] is False
        assert guarded_body["data"]["web_video_plan_persisted"] is False
        assert guarded_body["data"]["job_created"] is False
        assert guarded_body["data"]["provider_called"] is False

    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "cinematic-save-disabled@example.com")
        disabled = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert disabled.status_code == 503
        assert "WEBAPP_VIDEO_STUDIO_ENABLED" in disabled.text
