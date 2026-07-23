"""Focused contracts for the Web-native Music Directions preset endpoint.

This endpoint is deliberately a small, server-owned upgrade path rather than
a compatibility surface for Telegram ``suggest_music|*`` callbacks.  A signed
Web session may choose one of five reviewed Web IDs and receive text-only
music directions; it may never create audio, jobs, credits, a Memory note, or
any other durable delivery side effect.
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

PATH = "/api/v1/media-workspace/tools/music-directions/compose"

BOUNDARY_FIELDS = (
    "execution",
    "input_persisted",
    "source_audio_inspected",
    "provider_called",
    "ai_music_called",
    "lyrics_generated",
    "audio_created",
    "preview_created",
    "output_created",
    "job_created",
    "wallet_mutated",
    "payment_started",
    "asset_saved",
    "collection_saved",
    "publish_action_created",
    "telegram_called",
    "rights_verified",
)

# These are intentionally Web IDs, not Bot callback data or Bot music
# keywords.  The server must own the narrow mapping to its deterministic
# Composer choices so a browser cannot select an undisclosed fallback.
PRESET_COMPOSER_CHOICES = {
    "commercial_bright": ("background", "primary", 1),
    "technology_future": ("background", "alternate", 1),
    "cinematic_brand": ("background", "primary", 2),
    "warm_story": ("background", "primary", 3),
    "short_viral": ("background", "alternate", 2),
}


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "music-directions-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "music-directions-test-session-secret")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_MEMORY_CENTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
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
            "display_name": "Music Directions Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def direction_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": "Nhạc nền nguyên bản, gọn và rõ cho video giới thiệu ứng dụng quản lý đơn hàng.",
        "language": "vi",
        "web_preset_id": "commercial_bright",
    }
    payload.update(overrides)
    return payload


def relevant_storage_counts(db_path) -> dict[str, int]:
    """Every durable store this stateless receipt must leave untouched."""

    tables = (
        "web_media_collections",
        "web_media_collection_versions",
        "web_media_items",
        "web_media_events",
        "web_memory_notes",
        "web_memory_note_versions",
        "web_memory_events",
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


def assert_boundary(data: dict[str, Any], *, composer_present: bool) -> None:
    expected = set(BOUNDARY_FIELDS)
    if composer_present:
        expected.add("composer")
    assert set(data) == expected
    assert data["execution"] == "web_native_deterministic_music_direction_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def assert_no_delivery_reference(data: dict[str, Any]) -> None:
    keys = set(_walk_keys(data))
    assert not keys.intersection({
        "provider_url", "provider_id", "job_id", "payment_url", "output_url",
        "audio_url", "preview_url", "asset_url", "collection_id", "telegram_message_id",
    })
    strings = [item for item in _walk_values(data) if isinstance(item, str)]
    assert not any("http://" in item.lower() or "https://" in item.lower() for item in strings)


def assert_composer_choice(data: dict[str, Any], source: dict[str, Any]) -> None:
    mode, suggestion_set, selected_suggestion = PRESET_COMPOSER_CHOICES[source["web_preset_id"]]
    composer = data["composer"]
    assert composer["description"] == source["description"]
    assert composer["language"] == source["language"]
    assert composer["mode"] == mode
    assert composer["suggestion_set"] == suggestion_set
    assert composer["selected_suggestion"] == selected_suggestion
    assert isinstance(composer["suggestions"], list) and len(composer["suggestions"]) == 3
    assert composer["selected_direction"] == composer["suggestions"][selected_suggestion - 1]
    assert all(
        isinstance(item, str) and item.strip()
        for item in composer["review_before_use"]
    )


def test_music_directions_requires_signed_session_csrf_uses_exact_web_ids_and_never_persists(tmp_path, monkeypatch):
    """A radio choice must be explicit, deterministic, and purely transient."""

    db_path = tmp_path / "music-directions-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(PATH, json=direction_payload()).status_code == 401
        csrf = login(client, "music-directions-owner@example.com")
        before = relevant_storage_counts(db_path)

        assert client.post(PATH, json=direction_payload()).status_code == 403
        headers = {"X-CSRF-Token": csrf}
        for preset_id in PRESET_COMPOSER_CHOICES:
            source = direction_payload(web_preset_id=preset_id)
            response = client.post(PATH, headers=headers, json=source)
            assert response.status_code == 200, source
            assert response.headers["Cache-Control"] == "no-store, private"
            body = response.json()
            assert body["ok"] is True
            assert body["status"] == "draft"
            assert body["error_code"] is None
            assert_boundary(body["data"], composer_present=True)
            assert_composer_choice(body["data"], source)
            assert_no_delivery_reference(body["data"])

            # Repeating a read-only composition stays deterministic and cannot
            # turn a selection into a durable idempotency/audit receipt.
            repeat = client.post(PATH, headers=headers, json=source)
            assert repeat.status_code == 200
            assert repeat.json()["data"] == body["data"]

        assert relevant_storage_counts(db_path) == before


def test_music_directions_rejects_raw_bot_inputs_case_variants_and_schema_expansion(tmp_path, monkeypatch):
    """No raw callback, Bot keyword, alias, or client-side Composer field is accepted."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "music-directions-schema@example.com")
        invalid_payloads = (
            {"description": "x", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "x" * 501, "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": 42, "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "Hướng nhạc hợp lệ", "language": "VI", "web_preset_id": "commercial_bright"},
            {"description": "Hướng nhạc hợp lệ", "language": "fr", "web_preset_id": "commercial_bright"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "COMMERCIAL_BRIGHT"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "Commercial_Bright"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "suggest_music|sales"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "suggest_music|cinematic"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "/music_library sales"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "sales"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "cinematic"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "commercial_bright|fallback"},
            {"description": "suggest_music|sales", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "suggest_music|unknown", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "suggest_music|sales|suffix", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "suggest_music|", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "/music_library cinematic", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "/music_library any-keyword", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "trend", "language": "vi", "web_preset_id": "commercial_bright"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "commercial_bright", "mode": "background"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "commercial_bright", "suggestion_set": "primary"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "commercial_bright", "selected_suggestion": 1},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "commercial_bright", "callback_data": "suggest_music|sales"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi", "web_preset_id": "commercial_bright", "provider_url": "https://provider.invalid/private"},
            {"description": "Hướng nhạc hợp lệ", "language": "vi"},
        )
        for payload in invalid_payloads:
            response = client.post(PATH, headers={"X-CSRF-Token": csrf}, json=payload)
            assert response.status_code == 422, payload
            assert response.headers["Cache-Control"] == "no-store, private"


def test_music_directions_copyright_guard_returns_its_own_all_false_boundary_without_write(tmp_path, monkeypatch):
    db_path = tmp_path / "music-directions-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "music-directions-policy@example.com")
        before = relevant_storage_counts(db_path)
        response = client.post(
            PATH,
            headers={"X-CSRF-Token": csrf},
            json=direction_payload(description="Tạo nhạc giống bài hát, beat và giọng của một ca sĩ nổi tiếng."),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_MUSIC_DIRECTION_COPYRIGHT_GUARD"
        assert_boundary(body["data"], composer_present=False)
        assert_no_delivery_reference(body["data"])
        assert relevant_storage_counts(db_path) == before


def test_music_directions_respects_media_workspace_maintenance_gate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "music-directions-disabled@example.com")
        response = client.post(PATH, headers={"X-CSRF-Token": csrf}, json=direction_payload())
        assert response.status_code == 503
        assert "WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED" in response.text
