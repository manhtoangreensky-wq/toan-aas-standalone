"""Focused contracts for the stateless Web-native Video Prompt Planner.

The planner preserves deterministic shot-direction ideas from the Telegram
Bot reference, but it is intentionally not a video engine.  These tests keep
the high-risk boundary explicit: signed-session + CSRF access, strict text
input, no durable Video Studio mutation, and no misleading delivery claim.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys

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
    "video_created",
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
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "video-prompt-planner-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "video-prompt-planner-test-session-secret")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Video Planner Owner"},
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
        "mode": "prompt_to_video",
        "brief": "Giới thiệu ứng dụng quản lý đơn hàng cho chủ cửa hàng bận rộn với demo thao tác rõ ràng.",
        "platform": "custom",
        "ratio": "9:16",
        "duration_seconds": 15,
        "scene_count": 3,
        "style_pack": "corporate_tech_commercial",
        "action_pack": "slow_push_in",
        "audio_mode": "modern_electronic",
        "detail_level": "director",
        "motion": "Máy quay tiến chậm theo thao tác tay tự nhiên.",
        "background": "Quầy làm việc sáng, tối giản và không có chữ sinh tự động.",
        "must_keep": ["Bố cục rõ ràng", "Màu thương hiệu đã được phê duyệt"],
        "must_avoid": ["Watermark", "Tuyên bố chưa được kiểm chứng"],
        "language": "vi",
    }
    payload.update(overrides)
    return payload


def planner_save_payload(**overrides) -> dict:
    payload = planner_payload(
        destination="video_plan",
        idempotency_key="video-prompt-planner-save-0001",
    )
    payload.update(overrides)
    return payload


def planner_storage_counts(db_path) -> dict[str, int]:
    """Return all durable Video Studio stores the planner must never touch."""

    tables = (
        "web_video_plans",
        "web_video_plan_versions",
        "web_video_scenes",
        "web_video_scene_versions",
        "web_video_studio_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def assert_no_execution_boundary(data: dict) -> None:
    assert set(data) == {"planner", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_video_plan_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def assert_plan_save_receipt(data: dict) -> None:
    assert set(data) == {"destination", "plan", "scene_count", *PLAN_SAVE_BOUNDARY_FIELDS}
    assert data["destination"] == "video_plan"
    assert data["execution"] == "web_native_video_plan_server_recomputed"
    assert data["draft_recomputed_on_server"] is True
    assert data["web_video_plan_persisted"] is True
    assert data["plan"] == {"id": data["plan"]["id"], "revision": 1, "state": "draft"}
    assert 1 <= data["scene_count"] <= 10
    for field in set(data) - {
        "destination",
        "plan",
        "scene_count",
        "execution",
        "draft_recomputed_on_server",
        "web_video_plan_persisted",
    }:
        assert data[field] is False


def assert_planner_shape(planner: dict, source: dict) -> None:
    """The transient result stays compact, exact and renderer-neutral."""

    assert set(planner) == {
        "title", "mode", "brief", "platform", "ratio", "duration_seconds", "scene_count",
        "style_pack", "action_pack", "audio_mode", "detail_level", "needs_clarification",
        "motion", "background", "must_keep", "must_avoid", "continuity_locks", "coverage",
        "cautions", "review_before_use", "prompt", "negative_prompt", "shots",
    }
    # ``language`` is validated at request time only.  It remains outside the
    # canonical persisted/display result schema so the planner does not invent
    # a second language/output contract.
    assert "language" not in planner
    assert planner["mode"] == source["mode"]
    assert planner["brief"] == source["brief"]
    assert planner["platform"] == source["platform"]
    assert planner["ratio"] == source["ratio"]
    assert planner["duration_seconds"] == source["duration_seconds"]
    assert 1 <= planner["scene_count"] <= 10
    assert planner["scene_count"] == len(planner["shots"])
    assert planner["detail_level"] == source["detail_level"]
    assert planner["motion"] == source["motion"]
    assert planner["background"] == source["background"]
    assert planner["must_keep"] == source["must_keep"]
    assert planner["must_avoid"] == source["must_avoid"]

    for field in ("style_pack", "action_pack", "audio_mode"):
        choice = planner[field]
        assert set(choice) == {"id", "label"}
        assert choice["id"] == source[field]
        assert isinstance(choice["label"], str) and choice["label"].strip()

    coverage = planner["coverage"]
    assert set(coverage) == {"ok", "missing"}
    assert isinstance(coverage["ok"], bool)
    assert coverage["ok"] is (not coverage["missing"])
    assert planner["needs_clarification"] is (not coverage["ok"])
    assert all(isinstance(item, str) and item.strip() for item in coverage["missing"])
    for field, maximum in (("continuity_locks", 12), ("cautions", 6), ("review_before_use", 6)):
        assert isinstance(planner[field], list) and len(planner[field]) <= maximum
        assert all(isinstance(item, str) and item.strip() for item in planner[field])
    assert planner["continuity_locks"]
    assert planner["review_before_use"]
    assert isinstance(planner["prompt"], str) and planner["prompt"].strip()
    assert isinstance(planner["negative_prompt"], str) and planner["negative_prompt"].strip()

    previous_end = 0.0
    for expected_index, shot in enumerate(planner["shots"], start=1):
        assert set(shot) == {"index", "start_seconds", "end_seconds", "beat", "visual", "action", "camera", "transition", "audio"}
        assert shot["index"] == expected_index
        assert 0 <= shot["start_seconds"] < shot["end_seconds"] <= source["duration_seconds"]
        assert shot["start_seconds"] >= previous_end
        previous_end = shot["end_seconds"]
        assert all(isinstance(shot[field], str) and shot[field].strip() for field in ("beat", "visual", "action", "camera", "transition", "audio"))
    assert planner["shots"][-1]["end_seconds"] == source["duration_seconds"]


def test_video_prompt_planner_is_session_csrf_bounded_deterministic_and_non_persistent(tmp_path, monkeypatch):
    """The Bot-derived planning surface must never secretly create video work."""

    db_path = tmp_path / "video-prompt-planner-test.db"
    path = "/api/v1/video-studio/tools/prompt-planner"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=planner_payload()).status_code == 401
        csrf = login(client, "video-prompt-planner@example.com")
        before = planner_storage_counts(db_path)

        assert client.post(path, json=planner_payload()).status_code == 403

        source = planner_payload()
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert_no_execution_boundary(data)
        assert_planner_shape(data["planner"], source)
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        # Same text input must return the same planning receipt.  It has no
        # idempotency key because no state-changing operation exists here.
        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert repeated.status_code == 200
        assert repeated.json()["data"]["planner"] == data["planner"]

        # No Video Studio record/version/event, idempotency receipt or audit
        # detail may be created by a request-only plan composition.
        assert planner_storage_counts(db_path) == before


@pytest.mark.parametrize(
    ("mode", "platform", "ratio", "duration_seconds", "detail_level", "language", "style_pack", "action_pack", "audio_mode"),
    [
        ("prompt_to_video", "custom", "9:16", 15, "quick", "vi", "corporate_tech_commercial", "slow_push_in", "modern_electronic"),
        ("trend_video", "tiktok", "16:9", 15, "director", "en", "tiktok_viral_product_demo", "before_after_wipe", "cinematic_light"),
        ("storyboard_video", "reels", "1:1", 18, "viral", "vi", "ugc_review_style", "phone_screen_transition", "asmr_only"),
        ("long_script", "youtube", "4:5", 60, "stability_first", "en", "documentary_premium", "walk_through_reveal", "voiceover_first"),
        ("prompt_to_video", "shorts", "9:16", 12, "cinematic", "vi", "emotional_storytelling", "ai_dashboard_reveal", "voiceover_vi"),
        ("trend_video", "facebook", "16:9", 15, "director", "en", "food_commercial", "customer_pain_to_solution", "silent"),
    ],
)
def test_video_prompt_planner_accepts_the_compact_planning_catalog(
    tmp_path,
    monkeypatch,
    mode,
    platform,
    ratio,
    duration_seconds,
    detail_level,
    language,
    style_pack,
    action_pack,
    audio_mode,
):
    """Exercise every public mode/platform/detail/language and compact pack."""

    path = "/api/v1/video-studio/tools/prompt-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, f"video-prompt-{mode}-{platform}@example.com")
        source = planner_payload(
            mode=mode,
            platform=platform,
            ratio=ratio,
            duration_seconds=duration_seconds,
            detail_level=detail_level,
            language=language,
            style_pack=style_pack,
            action_pack=action_pack,
            audio_mode=audio_mode,
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_no_execution_boundary(data)
        assert_planner_shape(data["planner"], source)


@pytest.mark.parametrize(
    "overrides",
    [
        {"mode": "render_video"},
        {"platform": "instagram"},
        {"ratio": "3:2"},
        {"duration_seconds": 2},
        {"duration_seconds": 181},
        {"scene_count": 11},
        {"detail_level": "maximum"},
        {"language": "fr"},
        {"style_pack": "provider_model"},
        {"action_pack": "unknown_action"},
        {"audio_mode": "unknown_audio"},
        {"must_keep": ["Hai ký tự"] * 7},
        {"provider_url": "https://provider.invalid/private"},
    ],
)
def test_video_prompt_planner_rejects_schema_expansion(tmp_path, monkeypatch, overrides):
    path = "/api/v1/video-studio/tools/prompt-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "video-prompt-schema@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=planner_payload(**overrides))
        assert response.status_code == 422
        assert response.headers["Cache-Control"] == "no-store, private"


def test_video_prompt_planner_blocks_sensitive_markup_and_unoriginal_requests(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/prompt-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "video-prompt-policy@example.com")
        headers = {"X-CSRF-Token": csrf}

        for overrides in (
            {"brief": "api_key=super-secret-token-value-12345"},
            {"brief": "Dùng video nguồn https://untrusted.example/private.mp4 để dựng lại."},
            {"background": "<img src=x onerror=alert(1)>"},
            {"must_keep": ["provider id: hidden-system-handle"]},
        ):
            rejected = client.post(path, headers=headers, json=planner_payload(**overrides))
            assert rejected.status_code == 422
            assert rejected.headers["Cache-Control"] == "no-store, private"

        guarded = client.post(
            path,
            headers=headers,
            json=planner_payload(brief="Tạo video theo phong cách của một ca sĩ cụ thể."),
        )
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_VIDEO_PROMPT_ORIGINALITY_GUARD"
        assert "planner" not in body.get("data", {})
        assert set(body["data"]) == set(BOUNDARY_FIELDS)
        assert body["data"]["execution"] == "web_native_deterministic_video_plan_only"
        assert all(body["data"][field] is False for field in BOUNDARY_FIELDS if field != "execution")

        oversized = client.post(
            path,
            headers={**headers, "Content-Type": "application/json"},
            content=b'{"brief":"' + (b"x" * (129 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_VIDEO_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["Cache-Control"] == "no-store, private"


def test_video_prompt_planner_respects_the_video_studio_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/prompt-planner"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "video-prompt-disabled@example.com")
        guarded = client.post(path, headers={"X-CSRF-Token": csrf}, json=planner_payload())
        assert guarded.status_code == 503
        assert "WEBAPP_VIDEO_STUDIO_ENABLED" in guarded.text


def test_video_prompt_planner_bounds_repeated_output_for_maximum_valid_brief(tmp_path, monkeypatch):
    """A valid long brief with ten shots must remain a bounded draft, not 500."""

    db_path = tmp_path / "video-prompt-planner-test.db"
    path = "/api/v1/video-studio/tools/prompt-planner"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "video-prompt-maximum@example.com")
        before = planner_storage_counts(db_path)
        source = planner_payload(
            brief="a" * 900,
            background="b" * 320,
            motion="c" * 320,
            duration_seconds=180,
            scene_count=10,
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_no_execution_boundary(data)
        assert_planner_shape(data["planner"], source)
        assert len(data["planner"]["prompt"]) <= 12_000
        assert all(len(shot["visual"]) <= 1_200 for shot in data["planner"]["shots"])
        assert planner_storage_counts(db_path) == before


def test_video_prompt_planner_save_recomputes_a_private_draft_video_plan_once(tmp_path, monkeypatch):
    """The explicit save stores only owner-scoped Web authoring metadata."""

    db_path = tmp_path / "video-prompt-planner-test.db"
    path = "/api/v1/video-studio/tools/prompt-planner/save"
    brief = "Giới thiệu ứng dụng quản lý đơn hàng có thao tác rõ ràng cho cửa hàng bận rộn."
    source = planner_save_payload(
        brief=brief,
        scene_count=3,
        idempotency_key="video-prompt-planner-save-recompute-0001",
    )
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=source).status_code == 401
        csrf = login(client, "video-prompt-save-owner@example.com")
        assert client.post(path, json=source).status_code == 403

        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert created.status_code == 200
        assert created.headers["Cache-Control"] == "no-store, private"
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert_plan_save_receipt(data)
        assert data["scene_count"] == 3
        # Save receipts deliberately contain no source brief, generated prompt,
        # scene content, asset handle or provider/job/payment/delivery claim.
        assert brief not in created.text
        assert "planner" not in data
        assert "prompt" not in data

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert replay.status_code == 200
        assert replay.json() == body
        collision = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={
                **source,
                "brief": "Một brief video khác phải không dùng được idempotency key cũ.",
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
        assert brief in detail_data["scenes"][0]["visual_direction"]

        second_csrf = login(client, "video-prompt-save-other-owner@example.com")
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
                "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%:prompt-planner:save-plan'"
            ).fetchone()
            audit = connection.execute(
                "SELECT action, target, detail FROM web_audit_events WHERE action=?",
                ("web.video.prompt_planner.save_plan",),
            ).fetchone()
        assert (plan_count, version_count, scene_count, scene_version_count, event_count) == (1, 1, 3, 3, 4)
        assert receipt is not None and brief not in str(receipt[0])
        assert audit is not None
        assert audit[0] == "web.video.prompt_planner.save_plan"
        assert audit[1] == plan_id
        assert brief not in str(audit[2])


def test_video_prompt_planner_save_has_strict_schema_guards_and_respects_video_gate(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/prompt-planner/save"
    source = planner_save_payload(idempotency_key="video-prompt-planner-save-schema-0001")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "video-prompt-save-schema@example.com")
        headers = {"X-CSRF-Token": csrf}
        for invalid in (
            {**source, "destination": "memory_note"},
            {**source, "idempotency_key": "short"},
            {**source, "duration_seconds": "15"},
            {**source, "planner": {"browser": "generated-result"}},
            {**source, "plan": {"browser": "generated-plan"}},
            {**source, "shots": []},
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
                "brief": "Tạo video theo phong cách của một ca sĩ cụ thể.",
                "idempotency_key": "video-prompt-planner-save-guarded-0001",
            },
        )
        assert guarded.status_code == 200
        guarded_body = guarded.json()
        assert guarded_body["ok"] is False
        assert guarded_body["error_code"] == "WEB_VIDEO_PROMPT_ORIGINALITY_GUARD"
        assert guarded_body["data"]["destination"] == "video_plan"
        assert guarded_body["data"]["draft_recomputed_on_server"] is False
        assert guarded_body["data"]["web_video_plan_persisted"] is False
        assert guarded_body["data"]["job_created"] is False
        assert guarded_body["data"]["provider_called"] is False

    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "video-prompt-save-disabled@example.com")
        disabled = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert disabled.status_code == 503
        assert "WEBAPP_VIDEO_STUDIO_ENABLED" in disabled.text
