"""Focused contracts for the Bot-derived Web Script-to-Screen Planner.

``script_image_video`` and ``multi_scene_film`` are deliberately translated
as deterministic, Web-native planning tools.  They may create an owner-scoped
Video Plan only after an explicit save; neither route may call a provider,
inspect media, mutate a Bot/Wallet, or imply that a video was delivered.
"""

from __future__ import annotations

import importlib
import json
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


BOUNDARY_FIELDS = {
    "execution", "input_persisted", "telegram_state_changed", "bot_called", "bridge_called",
    "provider_called", "media_opened", "media_created", "preview_created", "output_created",
    "job_created", "wallet_changed", "payment_changed", "asset_created", "published", "delivered",
}

SAVE_FIELDS = {
    "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server", "web_video_plan_persisted",
    "telegram_state_changed", "bot_called", "bridge_called", "provider_called", "media_opened",
    "media_created", "preview_created", "output_created", "job_created", "wallet_changed",
    "payment_changed", "asset_created", "published", "delivered",
}


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "script-to-screen-planner-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "script-to-screen-planner-test-session-secret")
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
            "display_name": "Script-to-Screen Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def planner_payload(**overrides: Any) -> dict[str, Any]:
    """The compact, Bot-compatible text-only planning input contract."""

    payload: dict[str, Any] = {
        "project_kind": "script_image_video",
        "brief": "Giới thiệu bình nước giữ nhiệt tối giản cho người đi làm bận rộn.",
        "audience": "Người đi làm muốn giữ thói quen uống nước trong ngày.",
        "platform": "tiktok",
        "aspect_ratio": "9:16",
        "scene_count": 6,
        "episode_count": 1,
        "selected_episode": 1,
        "style": "product_demo",
        "color_mood": "bright",
        "pace": "balanced",
        "image_plan": "per_scene",
        "extra_scene": False,
        "extra_scene_count": 0,
        "output_target": "prompt_pack",
        "cta": "Lưu video để xem lại khi cần.",
        "language": "vi",
    }
    payload.update(overrides)
    return payload


def save_payload(**overrides: Any) -> dict[str, Any]:
    payload = planner_payload(
        destination="video_plan",
        idempotency_key="script-to-screen-save-0001",
    )
    payload.update(overrides)
    return payload


def storage_counts(db_path) -> dict[str, int]:
    tables = (
        "web_video_plans", "web_video_plan_versions", "web_video_scenes", "web_video_scene_versions",
        "web_video_studio_events", "web_idempotency", "web_audit_events",
    )
    with sqlite3.connect(db_path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def _walk_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _walk_values(value: Any) -> Iterator[Any]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def assert_transient_boundary(data: dict[str, Any]) -> None:
    assert set(data) == {"planner", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_script_to_screen_planner_only"
    for field in BOUNDARY_FIELDS - {"execution"}:
        assert data[field] is False


def assert_save_receipt(data: dict[str, Any], *, expected_scene_count: int) -> None:
    assert set(data) == SAVE_FIELDS
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_script_to_screen_video_plan_server_recomputed"
    assert data["draft_recomputed_on_server"] is True
    assert data["web_video_plan_persisted"] is True
    assert data["scene_count"] == expected_scene_count
    assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
    for field in SAVE_FIELDS - {
        "destination", "plan", "scene_count", "execution", "draft_recomputed_on_server", "web_video_plan_persisted",
    }:
        assert data[field] is False


def assert_no_delivery_or_execution_reference(data: dict[str, Any]) -> None:
    """A planning receipt must not look like a provider/job/output response."""

    forbidden_keys = {
        "provider_url", "provider_id", "job_id", "payment_url", "output_url", "video_url",
        "preview_url", "asset_url", "wallet_transaction_id", "telegram_chat_id",
    }
    assert not set(_walk_keys(data)).intersection(forbidden_keys)
    strings = [value for value in _walk_values(data) if isinstance(value, str)]
    assert not any("http://" in value.lower() or "https://" in value.lower() for value in strings)


def expected_scene_count(source: dict[str, Any]) -> int:
    """Canonical count, with the old boolean accepted only for old callers."""

    return int(source["scene_count"]) + int(source.get("extra_scene_count", int(source.get("extra_scene", False))))


def assert_planner_shape(planner: dict[str, Any], source: dict[str, Any]) -> None:
    """Keep the Bot prompt compiler's useful structure, without execution state."""

    assert set(planner) == {
        "title", "project_kind", "platform", "aspect_ratio", "style", "color_mood", "pace",
        "image_plan", "output_target", "brief", "audience", "scene_count", "series", "creative_summary",
        "script", "storyboard", "caption", "hashtags", "negative_constraints", "review_before_use",
    }
    for field in (
        "title", "aspect_ratio", "brief", "audience", "creative_summary", "caption",
    ):
        assert isinstance(planner[field], str) and planner[field].strip()
    assert planner["brief"] == source["brief"]
    assert planner["audience"] == source["audience"]
    assert planner["aspect_ratio"] == source["aspect_ratio"]
    for field in ("project_kind", "platform", "style", "color_mood", "pace", "image_plan", "output_target"):
        choice = planner[field]
        assert set(choice) == {"id", "label"}
        assert choice["id"] == source[field]
        assert isinstance(choice["label"], str) and choice["label"].strip()

    count = expected_scene_count(source)
    assert planner["scene_count"] == count
    assert len(planner["storyboard"]) == count
    series = planner["series"]
    assert set(series) == {
        "mode", "episode_count", "selected_episode", "episodes", "continuity_bible", "save_scope",
    }
    assert series["episode_count"] == source["episode_count"]
    assert series["selected_episode"] == source["selected_episode"]
    assert series["mode"] == ("episodic_series" if source["project_kind"] == "multi_scene_film" else "single_episode")
    assert len(series["episodes"]) == source["episode_count"]
    assert [episode["index"] for episode in series["episodes"]] == list(range(1, source["episode_count"] + 1))
    for episode in series["episodes"]:
        assert set(episode) == {"index", "title", "arc", "focus", "cliffhanger", "scene_count"}
        assert episode["scene_count"] == count
        assert all(isinstance(episode[field], str) and episode[field].strip() for field in ("title", "arc", "focus", "cliffhanger"))
    assert len(series["continuity_bible"]) == 3
    assert all(isinstance(item, str) and item.strip() for item in series["continuity_bible"])
    assert isinstance(series["save_scope"], str) and series["save_scope"].strip()

    storyboard_fields = {
        "index", "phase", "title", "duration_seconds", "purpose", "narration", "on_screen_text",
        "shot", "image_prompt", "video_prompt", "transition",
    }
    for index, scene in enumerate(planner["storyboard"], start=1):
        assert set(scene) == storyboard_fields
        assert scene["index"] == index
        assert isinstance(scene["duration_seconds"], int) and scene["duration_seconds"] > 0
        for field in storyboard_fields - {"index", "duration_seconds"}:
            assert isinstance(scene[field], str) and scene[field].strip()

    script = planner["script"]
    assert set(script) == {"hook", "arc", "voice_direction", "cta"}
    assert all(isinstance(value, str) and value.strip() for value in script.values())
    assert isinstance(planner["hashtags"], list) and planner["hashtags"]
    assert all(isinstance(item, str) and item.strip() for item in planner["hashtags"])
    for field in ("negative_constraints", "review_before_use"):
        assert isinstance(planner[field], list) and planner[field]
        assert all(isinstance(item, str) and item.strip() for item in planner[field])


def test_script_to_screen_requires_signed_session_csrf_is_deterministic_and_stays_transient(tmp_path, monkeypatch):
    """Planning cannot silently begin an image/video, payment or Bot workflow."""

    db_path = tmp_path / "script-to-screen-planner-test.db"
    path = "/api/v1/video-studio/tools/script-to-screen-planner"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=planner_payload()).status_code == 401
        csrf = login(client, "script-to-screen-compose@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=planner_payload()).status_code == 403

        source = planner_payload()
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True and body["status"] == "draft"
        assert_transient_boundary(body["data"])
        assert_planner_shape(body["data"]["planner"], source)
        assert_no_delivery_or_execution_reference(body["data"])

        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert repeated.status_code == 200
        assert repeated.json()["data"] == body["data"]

        multi_scene = planner_payload(
            project_kind="multi_scene_film",
            platform="youtube",
            aspect_ratio="16:9",
            scene_count=7,
            style="cinematic",
            color_mood="premium",
            pace="ad_rhythm",
            image_plan="single_continuity",
            extra_scene=True,
            extra_scene_count=1,
            output_target="storyboard",
            cta="Review the plan before production.",
            language="en",
            episode_count=4,
            selected_episode=2,
        )
        film = client.post(path, headers={"X-CSRF-Token": csrf}, json=multi_scene)
        assert film.status_code == 200
        assert_transient_boundary(film.json()["data"])
        assert_planner_shape(film.json()["data"]["planner"], multi_scene)

        # Compose requests must not write a plan/revision/scene/event, an
        # idempotency receipt, or audit record before explicit save.
        assert storage_counts(db_path) == before


def test_script_to_screen_accepts_bot_panel_grammar_and_canonical_two_extra_scenes(tmp_path, monkeypatch):
    """The expanded planner remains bounded, recomputed and execution-free."""

    compose_path = "/api/v1/video-studio/tools/script-to-screen-planner"
    save_path = "/api/v1/video-studio/tools/script-to-screen-planner/save"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "script-to-screen-bot-grammar@example.com")
        headers = {"X-CSRF-Token": csrf}

        # The frozen Bot presents these familiar panel counts. Each is a
        # fresh Web form choice, never a Bot session callback replay.
        for panel_count in (6, 9, 12, 16):
            response = client.post(compose_path, headers=headers, json=planner_payload(scene_count=panel_count))
            assert response.status_code == 200
            assert response.json()["data"]["planner"]["scene_count"] == panel_count

        source = planner_payload(
            project_kind="multi_scene_film",
            brief="Chuỗi tập ngắn giới thiệu cách vận hành cửa hàng nhỏ có kiểm soát.",
            platform="youtube",
            aspect_ratio="16:9",
            scene_count=16,
            episode_count=3,
            selected_episode=2,
            style="realistic",
            image_plan="skip",
            extra_scene=True,
            extra_scene_count=2,
        )
        composed = client.post(compose_path, headers=headers, json=source)
        assert composed.status_code == 200 and composed.json()["ok"] is True
        data = composed.json()["data"]
        assert_transient_boundary(data)
        assert_planner_shape(data["planner"], source)
        assert data["planner"]["scene_count"] == 18
        assert all("Không yêu cầu direction ảnh" in scene["image_prompt"] for scene in data["planner"]["storyboard"])

        saved = client.post(
            save_path,
            headers=headers,
            json={**source, "destination": "video_plan", "idempotency_key": "script-to-screen-18-scenes-0001"},
        )
        assert saved.status_code == 200 and saved.json()["ok"] is True
        receipt = saved.json()["data"]
        assert_save_receipt(receipt, expected_scene_count=18)
        plan_id = receipt["plan"]["id"]
        detail = client.get(f"/api/v1/video-studio/plans/{plan_id}")
        assert detail.status_code == 200 and len(detail.json()["data"]["scenes"]) == 18

        # The legacy flag remains one extra scene only when the count is
        # genuinely omitted; it must not reject the new canonical 0/1/2 form.
        legacy = planner_payload(extra_scene=True)
        legacy.pop("extra_scene_count")
        legacy_response = client.post(compose_path, headers=headers, json=legacy)
        assert legacy_response.status_code == 200
        assert legacy_response.json()["data"]["planner"]["scene_count"] == 7


@pytest.mark.parametrize(
    "overrides",
    (
        {"project_kind": "video_ai_real"},
        {"platform": "instagram"},
        {"aspect_ratio": "3:2"},
        {"scene_count": 2},
        {"scene_count": 17},
        {"extra_scene_count": 3},
        {"extra_scene": False, "extra_scene_count": 1},
        {"episode_count": 0},
        {"episode_count": 9},
        {"selected_episode": 0},
        {"selected_episode": 2},
        {"project_kind": "script_image_video", "episode_count": 2},
        {"project_kind": "multi_scene_film", "episode_count": 1},
        {"project_kind": "multi_scene_film", "episode_count": 3, "selected_episode": 4},
        {"style": "provider_model"},
        {"color_mood": "unknown_color"},
        {"pace": "unknown_pace"},
        {"image_plan": "provider_keyframe"},
        {"output_target": "render_video"},
        {"language": "fr"},
        {"source_media_url": "https://provider.invalid/private.mp4"},
        {"job_id": "browser-supplied-job"},
        {"provider_url": "https://provider.invalid/submit"},
        {"output_url": "https://provider.invalid/output.mp4"},
        {"planner": {"browser": "generated-result"}},
    ),
)
def test_script_to_screen_rejects_schema_expansion_and_untrusted_execution_state(tmp_path, monkeypatch, overrides):
    path = "/api/v1/video-studio/tools/script-to-screen-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "script-to-screen-schema@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=planner_payload(**overrides))
        assert response.status_code == 422
        assert response.headers["Cache-Control"] == "no-store, private"


def test_script_to_screen_guards_impersonation_and_unverified_guarantee_claims(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/script-to-screen-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "script-to-screen-policy@example.com")
        headers = {"X-CSRF-Token": csrf}

        originality = client.post(
            path,
            headers=headers,
            json=planner_payload(brief="Tạo phim có gương mặt giống hệt một ca sĩ nổi tiếng trong quảng cáo mới."),
        )
        assert originality.status_code == 200
        originality_body = originality.json()
        assert originality_body["ok"] is False and originality_body["status"] == "guarded"
        assert originality_body["error_code"] == "WEB_SCRIPT_TO_SCREEN_ORIGINALITY_GUARD"
        assert "planner" not in originality_body.get("data", {})
        assert set(originality_body["data"]) == BOUNDARY_FIELDS
        assert originality_body["data"]["execution"] == "web_native_deterministic_script_to_screen_planner_only"
        assert all(
            originality_body["data"][field] is False
            for field in BOUNDARY_FIELDS - {"execution"}
        )

        claim = client.post(
            path,
            headers=headers,
            json=planner_payload(brief="Video quảng cáo cam kết chữa khỏi bệnh 100% chỉ sau một ngày."),
        )
        assert claim.status_code == 200
        claim_body = claim.json()
        assert claim_body["ok"] is False and claim_body["status"] == "guarded"
        assert claim_body["error_code"] == "WEB_SCRIPT_TO_SCREEN_CLAIM_GUARD"
        assert "planner" not in claim_body.get("data", {})
        assert set(claim_body["data"]) == BOUNDARY_FIELDS
        assert claim_body["data"]["provider_called"] is False
        assert claim_body["data"]["media_created"] is False


def test_script_to_screen_save_is_server_recomputed_idempotent_and_private_to_owner(tmp_path, monkeypatch):
    db_path = tmp_path / "script-to-screen-planner-test.db"
    path = "/api/v1/video-studio/tools/script-to-screen-planner/save"
    brief = "Giới thiệu bình nước giữ nhiệt tối giản cho người đi làm bận rộn."
    source = save_payload(idempotency_key="script-to-screen-save-recompute-0001")
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=source).status_code == 401
        csrf = login(client, "script-to-screen-save-owner@example.com")
        assert client.post(path, json=source).status_code == 403

        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert created.status_code == 200
        assert created.headers["Cache-Control"] == "no-store, private"
        body = created.json()
        assert body["ok"] is True and body["status"] == "draft"
        receipt = body["data"]
        assert_save_receipt(receipt, expected_scene_count=expected_scene_count(source))
        assert brief not in created.text
        assert "planner" not in receipt and "prompt" not in receipt

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert replay.status_code == 200 and replay.json() == body
        collision = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**source, "brief": "Một brief khác không thể tái dùng idempotency key cũ."},
        )
        assert collision.status_code == 409

        plan_id = receipt["plan"]["id"]
        detail = client.get(f"/api/v1/video-studio/plans/{plan_id}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        detail_data = detail.json()["data"]
        assert detail_data["plan"]["state"] == "draft"
        assert "Web-native plan rebuilt on the server" in detail_data["plan"]["brief"]
        assert len(detail_data["scenes"]) == expected_scene_count(source)
        assert all(scene["state"] == "active" and scene["revision"] == 1 for scene in detail_data["scenes"])
        assert brief in detail_data["scenes"][0]["visual_direction"]

        other_csrf = login(client, "script-to-screen-save-other@example.com")
        hidden = client.get(f"/api/v1/video-studio/plans/{plan_id}", headers={"X-CSRF-Token": other_csrf})
        assert hidden.status_code == 200
        assert hidden.json()["ok"] is False
        assert hidden.json()["error_code"] == "WEB_VIDEO_PLAN_NOT_FOUND"

    with sqlite3.connect(db_path) as connection:
        counts = tuple(
            int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "web_video_plans", "web_video_plan_versions", "web_video_scenes",
                "web_video_scene_versions", "web_video_studio_events",
            )
        )
        idempotency = connection.execute(
            "SELECT response_json FROM web_idempotency "
            "WHERE scope LIKE 'web-video-studio:%:script-to-screen-planner:save-plan'"
        ).fetchone()
        audit = connection.execute(
            "SELECT action, target, detail FROM web_audit_events WHERE action=?",
            ("web.video.script_to_screen.save_plan",),
        ).fetchone()
    scene_total = expected_scene_count(source)
    expected = (1, 1, scene_total, scene_total, scene_total + 1)
    assert counts == expected
    assert idempotency is not None
    idempotency_data = json.loads(str(idempotency[0]))["data"]
    assert idempotency_data["provider_called"] is False and brief not in str(idempotency[0])
    assert audit is not None
    assert audit[0] == "web.video.script_to_screen.save_plan"
    assert audit[1] == plan_id
    assert brief not in str(audit[2])


def test_episodic_series_expands_and_saves_only_the_selected_episode(tmp_path, monkeypatch):
    """A season roadmap must not silently turn into many plans or a render."""

    db_path = tmp_path / "script-to-screen-planner-test.db"
    source = planner_payload(
        project_kind="multi_scene_film",
        brief="Chuỗi ngắn hướng dẫn chủ shop thiết lập quy trình xử lý đơn hàng.",
        platform="youtube",
        aspect_ratio="16:9",
        scene_count=4,
        episode_count=4,
        selected_episode=3,
        style="educational",
        color_mood="premium",
        pace="balanced",
        image_plan="single_continuity",
    )
    save_source = {
        **source,
        "destination": "video_plan",
        "idempotency_key": "script-to-screen-episodic-save-0001",
    }
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "script-to-screen-series@example.com")
        headers = {"X-CSRF-Token": csrf}
        composed = client.post("/api/v1/video-studio/tools/script-to-screen-planner", headers=headers, json=source)
        assert composed.status_code == 200 and composed.json()["ok"] is True
        planner = composed.json()["data"]["planner"]
        assert planner["series"]["mode"] == "episodic_series"
        assert planner["series"]["episode_count"] == 4
        assert planner["series"]["selected_episode"] == 3
        assert len(planner["series"]["episodes"]) == 4
        assert "Tập 3/4" in planner["title"]
        assert all("Tập 3/4" in scene["narration"] for scene in planner["storyboard"])

        saved = client.post("/api/v1/video-studio/tools/script-to-screen-planner/save", headers=headers, json=save_source)
        assert saved.status_code == 200 and saved.json()["ok"] is True
        receipt = saved.json()["data"]
        assert_save_receipt(receipt, expected_scene_count=4)
        plan_id = receipt["plan"]["id"]
        detail = client.get(f"/api/v1/video-studio/plans/{plan_id}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        plan = detail.json()["data"]["plan"]
        assert "Tập 3/4" in plan["title"]
        assert len(detail.json()["data"]["scenes"]) == 4

    with sqlite3.connect(db_path) as connection:
        plan_count = int(connection.execute("SELECT COUNT(*) FROM web_video_plans").fetchone()[0])
        tags = connection.execute("SELECT tags_json FROM web_video_plans").fetchone()[0]
    assert plan_count == 1
    assert "season-4" in str(tags) and "episode-3" in str(tags)


def test_script_to_screen_save_has_strict_schema_guards_and_respects_video_gate(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/script-to-screen-planner/save"
    source = save_payload(idempotency_key="script-to-screen-save-schema-0001")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "script-to-screen-save-schema@example.com")
        headers = {"X-CSRF-Token": csrf}
        for invalid in (
            {**source, "destination": "memory_note"},
            {**source, "idempotency_key": "short"},
            {**source, "scene_count": "6"},
            {**source, "plan": {"browser": "generated-plan"}},
            {**source, "planner": {"browser": "generated-result"}},
            {**source, "shot_table": []},
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
                "brief": "Cam kết chữa khỏi bệnh 100% chỉ sau một ngày.",
                "idempotency_key": "script-to-screen-save-guarded-0001",
            },
        )
        assert guarded.status_code == 200
        guarded_body = guarded.json()
        assert guarded_body["ok"] is False
        assert guarded_body["error_code"] == "WEB_SCRIPT_TO_SCREEN_CLAIM_GUARD"
        assert guarded_body["data"]["destination"] == "video_plan"
        assert guarded_body["data"]["draft_recomputed_on_server"] is False
        assert guarded_body["data"]["web_video_plan_persisted"] is False
        assert guarded_body["data"]["job_created"] is False
        assert guarded_body["data"]["provider_called"] is False

    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "script-to-screen-disabled@example.com")
        disabled = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert disabled.status_code == 503
        assert "WEBAPP_VIDEO_STUDIO_ENABLED" in disabled.text
