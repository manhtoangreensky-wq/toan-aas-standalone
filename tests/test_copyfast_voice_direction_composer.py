"""Focused contracts for the stateless Web-native Voice Direction Composer.

This is a safe conversion of the Bot's voice-style suggestion rules into a
text-only Web planning receipt.  It is deliberately *not* a TTS, voice clone,
preview, provider, job, wallet, payment, Asset Vault or Telegram surface.
The tests make those boundaries explicit before a richer delivery adapter is
ever considered.
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
    "raw_audio_stored",
    "consent_attestation_recorded",
    "provider_called",
    "provider_voice_id_stored",
    "tts_called",
    "voice_clone_called",
    "preview_created",
    "audio_created",
    "job_created",
    "wallet_mutated",
    "payment_started",
    "asset_saved",
    "output_created",
    "telegram_called",
)

EXPECTED_DATA_FIELDS = {"composer", *BOUNDARY_FIELDS}


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "voice-direction-composer-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "voice-direction-composer-test-session-secret")
    monkeypatch.setenv("WEBAPP_VOICE_STUDIO_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_VIDEO_STUDIO_ENABLED", "true")
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
            "display_name": "Voice Direction Owner",
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
        "text": "Chào mừng bạn đến với không gian làm việc gọn gàng, rõ ràng và đáng tin cậy.",
        "language": "vi",
        "suggestion_set": "core",
        "selected_suggestion": 1,
        "reading_speed": "normal",
    }
    payload.update(overrides)
    return payload


def voice_storage_counts(db_path) -> dict[str, int]:
    """All durable Voice Studio stores a stateless receipt must not touch."""

    tables = (
        "web_voice_vaults",
        "web_voice_vault_versions",
        "web_voice_scripts",
        "web_voice_script_versions",
        "web_voice_studio_events",
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
    assert data["execution"] == "web_native_deterministic_voice_direction_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def assert_composer_shape(composer: dict[str, Any], source: dict[str, Any]) -> None:
    assert set(composer) == {
        "title",
        "text",
        "language",
        "suggestion_set",
        "selected_suggestion",
        "reading_speed",
        "suggestions",
        "selected_direction",
        "delivery_notes",
        "cautions",
        "review_before_use",
    }
    assert isinstance(composer["title"], str) and composer["title"].strip()
    assert composer["text"] == source["text"]
    assert composer["language"] == source["language"]
    assert composer["suggestion_set"] == source["suggestion_set"]
    assert composer["selected_suggestion"] == source["selected_suggestion"]
    assert composer["reading_speed"] == source["reading_speed"]

    suggestions = composer["suggestions"]
    assert isinstance(suggestions, list) and len(suggestions) == 3
    for index, suggestion in enumerate(suggestions, start=1):
        assert set(suggestion) == {
            "choice", "id", "name", "tone", "pace", "use_case", "direction", "style_prompt",
        }
        assert suggestion["choice"] == index
        assert all(
            isinstance(suggestion[field], str) and suggestion[field].strip()
            for field in ("id", "name", "tone", "pace", "use_case", "direction", "style_prompt")
        )
    assert composer["selected_direction"] == suggestions[source["selected_suggestion"] - 1]

    delivery = composer["delivery_notes"]
    assert set(delivery) == {"pace_adjustment", "pause_notes", "emphasis_notes", "cta_notes"}
    assert all(isinstance(value, str) and value.strip() for value in delivery.values())

    for field, minimum in (("cautions", 0), ("review_before_use", 1)):
        values = composer[field]
        assert isinstance(values, list) and minimum <= len(values) <= 6
        assert all(isinstance(value, str) and value.strip() for value in values)


def assert_no_delivery_reference(data: dict[str, Any]) -> None:
    keys = set(_walk_keys(data))
    assert not keys.intersection({
        "provider_url", "provider_id", "provider_voice_id", "job_id", "payment_url",
        "output_url", "audio_url", "preview_url", "asset_url", "telegram_message_id",
    })
    strings = [item for item in _walk_values(data) if isinstance(item, str)]
    assert not any("http://" in item.lower() or "https://" in item.lower() for item in strings)


def test_voice_direction_composer_is_session_csrf_bounded_deterministic_and_non_persistent(tmp_path, monkeypatch):
    """A polished direction receipt must never silently call a voice engine."""

    db_path = tmp_path / "voice-direction-composer-test.db"
    path = "/api/v1/voice-studio/tools/direction-composer"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=composer_payload()).status_code == 401
        csrf = login(client, "voice-direction@example.com")
        before = voice_storage_counts(db_path)

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
        assert_no_delivery_reference(body["data"])

        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert repeated.status_code == 200
        assert repeated.json()["data"] == body["data"]

        # The helper deliberately creates no vault/profile/consent record,
        # script/version/event, idempotency receipt or audit event.
        assert voice_storage_counts(db_path) == before


@pytest.mark.parametrize(
    ("suggestion_set", "language", "selected_suggestion", "reading_speed"),
    (
        ("core", "vi", 1, "slow"),
        ("core", "en", 2, "normal"),
        ("core", "vi", 3, "fast"),
        ("extended", "en", 1, "slow"),
        ("extended", "vi", 2, "normal"),
        ("extended", "en", 3, "fast"),
    ),
)
def test_voice_direction_composer_covers_every_supported_choice(
    tmp_path,
    monkeypatch,
    suggestion_set,
    language,
    selected_suggestion,
    reading_speed,
):
    """Both Bot-inspired catalogs, choices and reading speeds remain local."""

    path = "/api/v1/voice-studio/tools/direction-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, f"voice-direction-{suggestion_set}-{language}-{selected_suggestion}@example.com")
        source = composer_payload(
            suggestion_set=suggestion_set,
            language=language,
            selected_suggestion=selected_suggestion,
            reading_speed=reading_speed,
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_boundary(data)
        assert_composer_shape(data["composer"], source)
        assert_no_delivery_reference(data)


@pytest.mark.parametrize(
    "overrides",
    (
        {"text": "x"},
        {"text": "x" * 261},
        {"text": 42},
        {"language": "fr"},
        {"language": True},
        {"suggestion_set": "all"},
        {"suggestion_set": 1},
        {"selected_suggestion": 0},
        {"selected_suggestion": 4},
        {"selected_suggestion": "1"},
        {"selected_suggestion": True},
        {"reading_speed": "very_fast"},
        {"reading_speed": 3},
        {"provider_url": "https://provider.invalid/private"},
        {"unexpected": "must be rejected"},
    ),
)
def test_voice_direction_composer_rejects_invalid_or_expanded_schema(tmp_path, monkeypatch, overrides):
    path = "/api/v1/voice-studio/tools/direction-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "voice-direction-schema@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(**overrides))
        assert response.status_code == 422
        assert response.headers["Cache-Control"] == "no-store, private"


def test_voice_direction_composer_rejects_dlp_and_guards_imitation_requests(tmp_path, monkeypatch):
    path = "/api/v1/voice-studio/tools/direction-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "voice-direction-policy@example.com")
        headers = {"X-CSRF-Token": csrf}

        for overrides in (
            {"text": "<img src=x onerror=alert(1)>"},
            {"text": "Đọc lại nội dung từ https://untrusted.example/private.mp3"},
            {"text": "api_key=super-secret-token-value-12345"},
            {"text": "Thanh toán theo mã giao dịch TXN-1234567890 và số tài khoản ngân hàng."},
        ):
            rejected = client.post(path, headers=headers, json=composer_payload(**overrides))
            assert rejected.status_code == 422
            assert rejected.headers["Cache-Control"] == "no-store, private"

        guarded = client.post(
            path,
            headers=headers,
            json=composer_payload(text="Hãy clone giọng và đọc giống giọng của một ca sĩ nổi tiếng."),
        )
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_VOICE_DIRECTION_ORIGINALITY_GUARD"
        assert "composer" not in body.get("data", {})
        assert set(body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"composer": {}, **body["data"]})
        assert_no_delivery_reference(body["data"])


def test_voice_direction_composer_respects_voice_studio_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/voice-studio/tools/direction-composer"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "voice-direction-disabled@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload())
        assert response.status_code == 503
        assert "WEBAPP_VOICE_STUDIO_ENABLED" in response.text


def test_voice_direction_composer_maximum_valid_text_never_500s_or_creates_audio(tmp_path, monkeypatch):
    """A maximum legal text is still only a compact deterministic receipt."""

    path = "/api/v1/voice-studio/tools/direction-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "voice-direction-maximum@example.com")
        source = composer_payload(
            text="n" * 260,
            language="en",
            suggestion_set="extended",
            selected_suggestion=3,
            reading_speed="fast",
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_boundary(data)
        assert_composer_shape(data["composer"], source)
        assert_no_delivery_reference(data)
