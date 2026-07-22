"""Focused contracts for the stateless Web-native Creative Motion Guide.

The frozen Bot's ``motion|`` flow only selects a topic, a rotating text idea
and an editorial style.  Its Web counterpart must retain that useful planning
flow without carrying Telegram pending state, media execution, provider calls,
jobs, wallet/payment writes, assets or delivery into a browser endpoint.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from collections.abc import Iterator
from typing import Any

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
    "fact_checked",
    "rights_verified",
)

SUGGESTION_DATA_FIELDS = {"suggestions", *BOUNDARY_FIELDS}
GUIDE_DATA_FIELDS = {"guide", *BOUNDARY_FIELDS}
TOPIC_KINDS = ("product", "affiliate", "ai_tool", "place", "fashion", "food", "education", "story")
STYLES = ("cinematic", "tiktok", "tutorial", "ads", "fpv", "reveal", "ugc")
LANGUAGES = ("vi", "en", "zh")


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "creative-motion-guide-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "creative-motion-guide-test-session-secret")
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
            "display_name": "Creative Motion Guide Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def suggestion_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "topic_kind": "product",
        "language": "vi",
        "suggestion_set": 1,
    }
    payload.update(overrides)
    return payload


def guide_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "topic_kind": "product",
        "custom_topic": "",
        "language": "vi",
        "suggestion_set": 1,
        "selected_suggestion": 1,
        "style": "cinematic",
    }
    payload.update(overrides)
    return payload


def creative_motion_storage_counts(db_path) -> dict[str, int]:
    """Durable Video Studio surfaces a text-only guide must not touch."""

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


def assert_boundary(data: dict[str, Any], *, content_key: str) -> None:
    expected = SUGGESTION_DATA_FIELDS if content_key == "suggestions" else GUIDE_DATA_FIELDS
    assert set(data) == expected
    assert data["execution"] == "web_native_deterministic_creative_motion_guide_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def assert_suggestions_shape(suggestions: dict[str, Any], source: dict[str, Any]) -> None:
    assert set(suggestions) == {"topic_kind", "topic_label", "language", "suggestion_set", "suggestions"}
    assert suggestions["topic_kind"] == source["topic_kind"]
    assert suggestions["language"] == source["language"]
    assert suggestions["suggestion_set"] == source["suggestion_set"]
    assert isinstance(suggestions["topic_label"], str) and suggestions["topic_label"].strip()

    cards = suggestions["suggestions"]
    assert isinstance(cards, list) and len(cards) == 3
    for index, card in enumerate(cards, start=1):
        assert set(card) == {"index", "title", "video_prompt", "motion", "audio_direction"}
        assert card["index"] == index
        assert all(
            isinstance(card[field], str) and card[field].strip()
            for field in ("title", "video_prompt", "motion", "audio_direction")
        )


def assert_guide_shape(guide: dict[str, Any], source: dict[str, Any]) -> None:
    assert set(guide) == {
        "title", "topic_kind", "topic", "language", "style", "suggestion_set", "selected_suggestion",
        "idea_15_seconds", "idea_30_seconds", "timeline", "camera_motions", "image_prompt",
        "video_motion_prompt", "overlay_lines", "voiceover", "cta", "cautions", "review_before_use",
    }
    assert guide["topic_kind"] == source["topic_kind"]
    assert guide["language"] == source["language"]
    assert guide["suggestion_set"] == source["suggestion_set"]
    assert guide["style"] == {"id": source["style"], "label": guide["style"]["label"]}
    assert isinstance(guide["style"]["label"], str) and guide["style"]["label"].strip()
    assert all(
        isinstance(guide[field], str) and guide[field].strip()
        for field in (
            "title", "topic", "idea_15_seconds", "idea_30_seconds", "image_prompt",
            "video_motion_prompt", "voiceover", "cta",
        )
    )

    selected = guide["selected_suggestion"]
    if source["topic_kind"] == "custom":
        assert source["suggestion_set"] == 0
        assert source["selected_suggestion"] == 0
        assert guide["topic"] == source["custom_topic"]
        assert selected is None
    else:
        assert isinstance(selected, dict)
        assert set(selected) == {"index", "title", "video_prompt", "motion", "audio_direction"}
        assert selected["index"] == source["selected_suggestion"]
        assert guide["topic"] == selected["title"]

    timeline = guide["timeline"]
    assert isinstance(timeline, list) and len(timeline) == 4
    previous_end = 0
    for index, item in enumerate(timeline, start=1):
        assert set(item) == {"index", "start_seconds", "end_seconds", "direction"}
        assert item["index"] == index
        assert isinstance(item["start_seconds"], int) and isinstance(item["end_seconds"], int)
        assert previous_end <= item["start_seconds"] < item["end_seconds"] <= 15
        previous_end = item["end_seconds"]
        assert isinstance(item["direction"], str) and item["direction"].strip()

    assert isinstance(guide["camera_motions"], list) and 6 <= len(guide["camera_motions"]) <= 10
    assert isinstance(guide["overlay_lines"], list) and len(guide["overlay_lines"]) == 4
    assert isinstance(guide["cautions"], list) and 2 <= len(guide["cautions"]) <= 4
    assert isinstance(guide["review_before_use"], list) and 2 <= len(guide["review_before_use"]) <= 4
    for field in ("camera_motions", "overlay_lines", "cautions", "review_before_use"):
        assert all(isinstance(item, str) and item.strip() for item in guide[field])


def assert_no_execution_or_delivery_reference(data: dict[str, Any]) -> None:
    keys = set(_walk_keys(data))
    assert not keys.intersection({
        "provider_url", "provider_id", "job_id", "payment_url", "output_url", "video_url", "audio_url",
        "preview_url", "asset_url", "telegram_message_id", "delivery_id", "publish_id",
    })
    strings = [item for item in _walk_values(data) if isinstance(item, str)]
    assert not any("http://" in item.lower() or "https://" in item.lower() for item in strings)


def test_creative_motion_suggestions_require_signed_session_csrf_and_stay_stateless(tmp_path, monkeypatch):
    db_path = tmp_path / "creative-motion-guide-test.db"
    path = "/api/v1/video-studio/tools/creative-motion-guide/suggestions"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=suggestion_payload()).status_code == 401
        csrf = login(client, "creative-motion-suggestions@example.com")
        before = creative_motion_storage_counts(db_path)

        assert client.post(path, json=suggestion_payload()).status_code == 403
        source = suggestion_payload(suggestion_set=4)
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"], content_key="suggestions")
        assert_suggestions_shape(body["data"]["suggestions"], source)
        assert_no_execution_or_delivery_reference(body["data"])

        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert repeated.status_code == 200
        assert repeated.json()["data"] == body["data"]
        assert creative_motion_storage_counts(db_path) == before


def test_creative_motion_guide_covers_every_bot_category_style_and_custom_language(tmp_path, monkeypatch):
    """The full finite Bot catalog is available without a Telegram state machine."""

    db_path = tmp_path / "creative-motion-guide-test.db"
    suggestion_path = "/api/v1/video-studio/tools/creative-motion-guide/suggestions"
    guide_path = "/api/v1/video-studio/tools/creative-motion-guide"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "creative-motion-catalog@example.com")
        headers = {"X-CSRF-Token": csrf}
        before = creative_motion_storage_counts(db_path)

        # Every frozen Bot topic receives exactly three cards.  Rotate locale
        # and set so all supported locales and refresh sets are exercised too.
        for offset, topic_kind in enumerate(TOPIC_KINDS, start=1):
            source = suggestion_payload(
                topic_kind=topic_kind,
                language=LANGUAGES[(offset - 1) % len(LANGUAGES)],
                suggestion_set=offset,
            )
            response = client.post(suggestion_path, headers=headers, json=source)
            assert response.status_code == 200, source
            data = response.json()["data"]
            assert_boundary(data, content_key="suggestions")
            assert_suggestions_shape(data["suggestions"], source)
            assert_no_execution_or_delivery_reference(data)

        # Every Bot style is recomputed server-side from the finite selected
        # suggestion.  No browser-supplied prompt/result becomes accepted data.
        for offset, style in enumerate(STYLES, start=1):
            source = guide_payload(
                topic_kind=TOPIC_KINDS[(offset - 1) % len(TOPIC_KINDS)],
                language=LANGUAGES[(offset - 1) % len(LANGUAGES)],
                suggestion_set=offset,
                selected_suggestion=((offset - 1) % 3) + 1,
                style=style,
            )
            response = client.post(guide_path, headers=headers, json=source)
            assert response.status_code == 200, source
            data = response.json()["data"]
            assert_boundary(data, content_key="guide")
            assert_guide_shape(data["guide"], source)
            assert_no_execution_or_delivery_reference(data)

        # Bot custom-topic flow bypasses suggestion selection.  The Web API
        # keeps that rule explicit instead of silently inventing a card.
        for language in LANGUAGES:
            source = guide_payload(
                topic_kind="custom",
                custom_topic="Kể một trải nghiệm tự sở hữu theo từng bước rõ ràng.",
                language=language,
                suggestion_set=0,
                selected_suggestion=0,
                style="ugc",
            )
            response = client.post(guide_path, headers=headers, json=source)
            assert response.status_code == 200, source
            data = response.json()["data"]
            assert_boundary(data, content_key="guide")
            assert_guide_shape(data["guide"], source)
            assert_no_execution_or_delivery_reference(data)

        assert creative_motion_storage_counts(db_path) == before


def test_creative_motion_guide_rejects_invalid_or_expanded_schema(tmp_path, monkeypatch):
    suggestion_path = "/api/v1/video-studio/tools/creative-motion-guide/suggestions"
    guide_path = "/api/v1/video-studio/tools/creative-motion-guide"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "creative-motion-schema@example.com")
        headers = {"X-CSRF-Token": csrf}

        for invalid in (
            suggestion_payload(topic_kind="custom"),
            suggestion_payload(topic_kind="unknown"),
            suggestion_payload(topic_kind=True),
            suggestion_payload(language="fr"),
            suggestion_payload(language=1),
            suggestion_payload(suggestion_set=0),
            suggestion_payload(suggestion_set=25),
            suggestion_payload(suggestion_set="1"),
            suggestion_payload(suggestion_set=True),
            {**suggestion_payload(), "provider_url": "https://provider.invalid/private"},
            {**suggestion_payload(), "unexpected": "must be rejected"},
        ):
            response = client.post(suggestion_path, headers=headers, json=invalid)
            assert response.status_code == 422, invalid
            assert response.headers["Cache-Control"] == "no-store, private"

        for invalid in (
            guide_payload(topic_kind="unknown"),
            guide_payload(language="fr"),
            guide_payload(language=True),
            guide_payload(style="provider_model"),
            guide_payload(style=1),
            guide_payload(suggestion_set=0),
            guide_payload(selected_suggestion=0),
            guide_payload(selected_suggestion=4),
            guide_payload(selected_suggestion="1"),
            guide_payload(custom_topic="not allowed for a fixed category"),
            guide_payload(topic_kind="custom", custom_topic="", suggestion_set=0, selected_suggestion=0),
            guide_payload(topic_kind="custom", custom_topic="x", suggestion_set=0, selected_suggestion=0),
            guide_payload(topic_kind="custom", custom_topic="Custom legal topic", suggestion_set=1, selected_suggestion=0),
            guide_payload(topic_kind="custom", custom_topic="Custom legal topic", suggestion_set=0, selected_suggestion=1),
            {**guide_payload(), "job_id": "must-not-be-accepted"},
            {**guide_payload(), "source_url": "https://provider.invalid/private.mp4"},
            {**guide_payload(), "guide": {"browser": "result"}},
            {**guide_payload(), "unexpected": "must be rejected"},
        ):
            response = client.post(guide_path, headers=headers, json=invalid)
            assert response.status_code == 422, invalid
            assert response.headers["Cache-Control"] == "no-store, private"


def test_creative_motion_guide_rejects_unsafe_input_and_guards_claims_or_imitation(tmp_path, monkeypatch):
    path = "/api/v1/video-studio/tools/creative-motion-guide"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "creative-motion-policy@example.com")
        headers = {"X-CSRF-Token": csrf}

        for custom_topic in (
            "<img src=x onerror=alert(1)>",
            "Dựng lại nội dung từ https://untrusted.example/private.mp4",
            "api_key=super-secret-token-value-12345",
            "Thanh toán theo mã giao dịch TXN-1234567890 và số tài khoản ngân hàng.",
        ):
            response = client.post(
                path,
                headers=headers,
                json=guide_payload(
                    topic_kind="custom",
                    custom_topic=custom_topic,
                    suggestion_set=0,
                    selected_suggestion=0,
                ),
            )
            assert response.status_code == 422, custom_topic
            assert response.headers["Cache-Control"] == "no-store, private"

        originality = client.post(
            path,
            headers=headers,
            json=guide_payload(
                topic_kind="custom",
                custom_topic="Làm video giống phong cách của một ca sĩ nổi tiếng.",
                suggestion_set=0,
                selected_suggestion=0,
            ),
        )
        assert originality.status_code == 200
        originality_body = originality.json()
        assert originality_body["ok"] is False
        assert originality_body["status"] == "guarded"
        assert originality_body["error_code"] == "WEB_CREATIVE_MOTION_ORIGINALITY_GUARD"
        assert "guide" not in originality_body["data"]
        assert set(originality_body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"guide": {}, **originality_body["data"]}, content_key="guide")
        assert_no_execution_or_delivery_reference(originality_body["data"])

        claim = client.post(
            path,
            headers=headers,
            json=guide_payload(
                topic_kind="custom",
                custom_topic="Cam kết chữa khỏi bệnh trong 24 giờ.",
                suggestion_set=0,
                selected_suggestion=0,
            ),
        )
        assert claim.status_code == 200
        claim_body = claim.json()
        assert claim_body["ok"] is False
        assert claim_body["status"] == "guarded"
        assert claim_body["error_code"] == "WEB_CREATIVE_MOTION_CLAIM_GUARD"
        assert "guide" not in claim_body["data"]
        assert set(claim_body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"guide": {}, **claim_body["data"]}, content_key="guide")
        assert_no_execution_or_delivery_reference(claim_body["data"])


def test_creative_motion_guide_respects_video_studio_maintenance_gate(tmp_path, monkeypatch):
    suggestion_path = "/api/v1/video-studio/tools/creative-motion-guide/suggestions"
    guide_path = "/api/v1/video-studio/tools/creative-motion-guide"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "creative-motion-disabled@example.com")
        headers = {"X-CSRF-Token": csrf}
        suggestions = client.post(suggestion_path, headers=headers, json=suggestion_payload())
        guide = client.post(guide_path, headers=headers, json=guide_payload())
    assert suggestions.status_code == 503
    assert guide.status_code == 503
    assert "WEBAPP_VIDEO_STUDIO_ENABLED" in suggestions.text
    assert "WEBAPP_VIDEO_STUDIO_ENABLED" in guide.text
