"""Focused contracts for the stateless Web-native Music Prompt Composer.

The Composer carries only the useful, copyright-safe planning semantics from
the frozen Telegram Bot into the Web App.  It is intentionally not a Suno or
other provider adapter, a lyrics/audio generator, preview player, job,
wallet/payment, Asset Vault, collection, publishing, or Telegram surface.
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

EXPECTED_DATA_FIELDS = {"composer", *BOUNDARY_FIELDS}


def make_client(tmp_path, monkeypatch, *, enabled: bool = True, memory_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "music-prompt-composer-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "music-prompt-composer-test-session-secret")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_MEMORY_CENTER_ENABLED", "true" if memory_enabled else "false")
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
            "display_name": "Music Prompt Owner",
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
        "description": "Nhạc nền gọn, ấm áp cho video giới thiệu ứng dụng quản lý đơn hàng.",
        "mode": "background",
        "language": "vi",
        "suggestion_set": "primary",
        "selected_suggestion": 1,
    }
    payload.update(overrides)
    return payload


def music_storage_counts(db_path) -> dict[str, int]:
    """Durable Media Workspace stores the stateless tool must never touch."""

    tables = (
        "web_media_collections",
        "web_media_collection_versions",
        "web_media_items",
        "web_media_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def music_prompt_memory_storage_counts(db_path) -> dict[str, int]:
    """All stores that the explicit Memory handoff may or may not touch."""

    tables = (
        "web_memory_notes",
        "web_memory_note_versions",
        "web_memory_events",
        "web_idempotency",
        "web_audit_events",
        "web_media_collections",
        "web_media_collection_versions",
        "web_media_items",
        "web_media_events",
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
    assert data["execution"] == "web_native_deterministic_music_prompt_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def assert_composer_shape(composer: dict[str, Any], source: dict[str, Any]) -> None:
    assert set(composer) == {
        "title",
        "description",
        "mode",
        "language",
        "suggestion_set",
        "selected_suggestion",
        "suggestions",
        "selected_direction",
        "usage_notes",
        "cautions",
        "review_before_use",
    }
    assert isinstance(composer["title"], str) and composer["title"].strip()
    assert composer["description"] == source["description"]
    assert composer["mode"] == source["mode"]
    assert composer["language"] == source["language"]
    assert composer["suggestion_set"] == source["suggestion_set"]
    assert composer["selected_suggestion"] == source["selected_suggestion"]

    suggestions = composer["suggestions"]
    assert isinstance(suggestions, list) and len(suggestions) == 3
    for index, suggestion in enumerate(suggestions, start=1):
        assert set(suggestion) == {
            "choice", "name", "mood", "tempo", "instruments", "duration",
            "vocal", "lyric_direction", "use_case", "prompt",
        }
        assert suggestion["choice"] == index
        assert all(
            isinstance(suggestion[field], str) and suggestion[field].strip()
            for field in (
                "name", "mood", "tempo", "instruments", "duration", "vocal",
                "lyric_direction", "use_case", "prompt",
            )
        )
    assert composer["selected_direction"] == suggestions[source["selected_suggestion"] - 1]

    usage_notes = composer["usage_notes"]
    assert set(usage_notes) == {
        "voice_mix_notes", "edit_notes", "rights_notes", "delivery_notes",
    }
    assert all(isinstance(value, str) and value.strip() for value in usage_notes.values())

    for field, minimum in (("cautions", 0), ("review_before_use", 1)):
        values = composer[field]
        assert isinstance(values, list) and minimum <= len(values) <= 6
        assert all(isinstance(value, str) and value.strip() for value in values)


def assert_no_delivery_reference(data: dict[str, Any]) -> None:
    keys = set(_walk_keys(data))
    assert not keys.intersection({
        "provider_url", "provider_id", "job_id", "payment_url", "output_url",
        "audio_url", "preview_url", "asset_url", "collection_id", "telegram_message_id",
    })
    strings = [item for item in _walk_values(data) if isinstance(item, str)]
    assert not any("http://" in item.lower() or "https://" in item.lower() for item in strings)


def test_music_prompt_composer_is_session_csrf_bounded_deterministic_and_non_persistent(tmp_path, monkeypatch):
    """A polished music prompt must never silently make an audio workflow."""

    db_path = tmp_path / "music-prompt-composer-test.db"
    path = "/api/v1/media-workspace/tools/music-prompt-composer"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=composer_payload()).status_code == 401
        csrf = login(client, "music-prompt@example.com")
        before = music_storage_counts(db_path)

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

        # This is a transient planning receipt: it may not write a collection,
        # history/event, idempotency receipt or audit event.
        assert music_storage_counts(db_path) == before


@pytest.mark.parametrize(
    ("mode", "language", "suggestion_set", "selected_suggestion"),
    (
        ("background", "vi", "primary", 1),
        ("background", "en", "alternate", 2),
        ("lyrics", "vi", "primary", 3),
        ("lyrics", "en", "alternate", 1),
        ("melody", "vi", "primary", 2),
        ("melody", "en", "alternate", 3),
        ("script", "vi", "primary", 1),
        ("script", "en", "alternate", 2),
        ("custom", "vi", "primary", 3),
        ("custom", "en", "alternate", 1),
    ),
)
def test_music_prompt_composer_covers_all_public_modes_sets_and_selections(
    tmp_path,
    monkeypatch,
    mode,
    language,
    suggestion_set,
    selected_suggestion,
):
    """All Bot-derived text-only branches remain local and deterministic."""

    path = "/api/v1/media-workspace/tools/music-prompt-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, f"music-{mode}-{language}-{suggestion_set}@example.com")
        source = composer_payload(
            mode=mode,
            language=language,
            suggestion_set=suggestion_set,
            selected_suggestion=selected_suggestion,
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200, source
        data = response.json()["data"]
        assert_boundary(data)
        assert_composer_shape(data["composer"], source)
        assert_no_delivery_reference(data)


@pytest.mark.parametrize(
    "overrides",
    (
        {"description": "x"},
        {"description": "x" * 501},
        {"description": 42},
        {"mode": "BACKGROUND"},
        {"mode": "render"},
        {"mode": 1},
        {"language": "fr"},
        {"language": True},
        {"suggestion_set": "all"},
        {"suggestion_set": 1},
        {"selected_suggestion": 0},
        {"selected_suggestion": 4},
        {"selected_suggestion": "1"},
        {"selected_suggestion": True},
        {"provider_url": "https://provider.invalid/private"},
        {"unexpected": "must be rejected"},
    ),
)
def test_music_prompt_composer_rejects_invalid_or_expanded_schema(tmp_path, monkeypatch, overrides):
    path = "/api/v1/media-workspace/tools/music-prompt-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "music-prompt-schema@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(**overrides))
        assert response.status_code == 422
        assert response.headers["Cache-Control"] == "no-store, private"


def test_music_prompt_composer_rejects_dlp_and_guards_copyright_imitation(tmp_path, monkeypatch):
    path = "/api/v1/media-workspace/tools/music-prompt-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "music-prompt-policy@example.com")
        headers = {"X-CSRF-Token": csrf}

        for overrides in (
            {"description": "<img src=x onerror=alert(1)>"},
            {"description": "Dùng lại file từ https://untrusted.example/private.mp3"},
            {"description": "Mở file:///private/audio.wav để lấy giai điệu"},
            {"description": "api_key=super-secret-token-value-12345"},
            {"description": "Thanh toán theo mã giao dịch TXN-1234567890 và số tài khoản ngân hàng."},
            {"description": "Dùng @private_audio_handle làm âm thanh tham chiếu."},
        ):
            rejected = client.post(path, headers=headers, json=composer_payload(**overrides))
            assert rejected.status_code == 422
            assert rejected.headers["Cache-Control"] == "no-store, private"

        guarded = client.post(
            path,
            headers=headers,
            json=composer_payload(description="Tạo nhạc giống bài hát, beat và giọng của một ca sĩ nổi tiếng."),
        )
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_MUSIC_PROMPT_COPYRIGHT_GUARD"
        assert "composer" not in body.get("data", {})
        assert set(body["data"]) == set(BOUNDARY_FIELDS)
        assert_boundary({"composer": {}, **body["data"]})
        assert_no_delivery_reference(body["data"])


def test_music_prompt_composer_respects_media_workspace_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/media-workspace/tools/music-prompt-composer"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "music-prompt-disabled@example.com")
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload())
        assert response.status_code == 503
        assert "WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED" in response.text


def test_music_prompt_composer_maximum_valid_description_stays_bounded_and_non_delivering(tmp_path, monkeypatch):
    """The longest legal brief remains a compact local planning receipt."""

    path = "/api/v1/media-workspace/tools/music-prompt-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "music-prompt-maximum@example.com")
        source = composer_payload(
            description="m" * 500,
            mode="custom",
            language="en",
            suggestion_set="alternate",
            selected_suggestion=3,
        )
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=source)
        assert response.status_code == 200
        data = response.json()["data"]
        assert_boundary(data)
        assert_composer_shape(data["composer"], source)
        assert_no_delivery_reference(data)


def test_music_prompt_composer_memory_save_is_signed_recomputed_and_owner_scoped(tmp_path, monkeypatch):
    """A selected direction becomes one private Web note, never media state."""

    db_path = tmp_path / "music-prompt-composer-test.db"
    path = "/api/v1/media-workspace/tools/music-prompt-composer/save"
    description = "Nhạc nền gọn, ấm áp cho video giới thiệu ứng dụng quản lý đơn hàng."
    payload = composer_payload(
        description=description,
        mode="background",
        language="vi",
        suggestion_set="alternate",
        selected_suggestion=2,
        destination="memory_note",
        idempotency_key="music-prompt-composer-save-memory-0001",
    )
    boundary_keys = (
        "draft_recomputed_on_server",
        "web_note_persisted",
        "browser_result_persisted",
        "pending_bot_save_created",
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
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
        "delivery_created",
        "fact_checked",
        "rights_verified",
    )
    with make_client(tmp_path, monkeypatch) as client:
        # Signed cookie and matching CSRF are mandatory before this durable
        # write accepts an otherwise valid selection.
        assert client.post(path, json=payload).status_code == 401
        csrf = login(client, "music-prompt-memory-owner@example.com")
        assert client.post(path, json=payload).status_code == 403
        before = music_prompt_memory_storage_counts(db_path)

        # The browser cannot inject a computed result/body/title, choose a
        # different account, or redirect the handoff into another store.
        invalid_requests = (
            {key: value for key, value in payload.items() if key != "destination"},
            {**payload, "destination": "collection"},
            {key: value for key, value in payload.items() if key != "idempotency_key"},
            {**payload, "content": "browser-authored text must never be stored"},
            {**payload, "title": "browser-authored note title must never be stored"},
            {**payload, "composer": {"selected_direction": "browser result must never be stored"}},
            {**payload, "account_id": "browser-selected-account"},
            {**payload, "selected_suggestion": "2"},
        )
        for invalid in invalid_requests:
            rejected = client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid)
            assert rejected.status_code == 422
        assert music_prompt_memory_storage_counts(db_path) == before

        # The saved material must equal a fresh server computation, but the
        # browser does not submit preview text as part of the save payload.
        preview = client.post(
            "/api/v1/media-workspace/tools/music-prompt-composer",
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(
                description=description,
                mode="background",
                language="vi",
                suggestion_set="alternate",
                selected_suggestion=2,
            ),
        )
        assert preview.status_code == 200
        expected = preview.json()["data"]["composer"]

        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert created.status_code == 200
        assert created.headers["Cache-Control"] == "no-store, private"
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "completed"
        assert description not in created.text
        data = body["data"]
        assert data["destination"] == "memory_note"
        assert data["execution"] == "web_native_memory_note_server_recomputed"
        assert data["note"] == {
            "id": data["note"]["id"],
            "revision": 1,
            "state": "active",
            "category": "Music Prompt Composer",
            "priority": "normal",
        }
        assert all(
            data[key] is (key in {"draft_recomputed_on_server", "web_note_persisted"})
            for key in boundary_keys
        )
        assert "job_id" not in created.text
        assert "output_url" not in created.text

        note_id = data["note"]["id"]
        detail = client.get(f"/api/v1/memory/notes/{note_id}")
        assert detail.status_code == 200
        saved_note = detail.json()["data"]["note"]
        assert saved_note["title"] == "Music Prompt Composer"
        assert saved_note["category"] == "Music Prompt Composer"
        assert saved_note["content"].startswith("Music Prompt Composer — bản nháp Web đã được dựng lại trên máy chủ.")
        assert f"Mô tả: {description}" in saved_note["content"]
        selected = expected["selected_direction"]
        assert f"Tên: {selected['name']}" in saved_note["content"]
        assert selected["prompt"] in saved_note["content"]
        assert expected["usage_notes"]["voice_mix_notes"] in saved_note["content"]
        assert all(item in saved_note["content"] for item in expected["cautions"])
        assert all(item in saved_note["content"] for item in expected["review_before_use"])

        after_create = music_prompt_memory_storage_counts(db_path)
        assert after_create["web_memory_notes"] == before["web_memory_notes"] + 1
        assert after_create["web_memory_note_versions"] == before["web_memory_note_versions"] + 1
        assert after_create["web_memory_events"] == before["web_memory_events"] + 1
        assert after_create["web_idempotency"] == before["web_idempotency"] + 1
        assert after_create["web_audit_events"] == before["web_audit_events"] + 1
        for table in (
            "web_media_collections",
            "web_media_collection_versions",
            "web_media_items",
            "web_media_events",
        ):
            assert after_create[table] == before[table]

        # The replay receipt and audit are content-free. The one-way request
        # fingerprint binds the selection, but must not retain it verbatim.
        with sqlite3.connect(db_path) as conn:
            receipt = conn.execute(
                "SELECT response_json, request_fingerprint FROM web_idempotency WHERE key=?",
                (payload["idempotency_key"],),
            ).fetchone()
            audit_rows = conn.execute(
                "SELECT action, target, detail FROM web_audit_events WHERE action=?",
                ("web.media_workspace.music_prompt_composer.save_memory",),
            ).fetchall()
        assert receipt is not None
        assert description not in str(receipt[0])
        assert description not in str(receipt[1])
        assert audit_rows
        assert all(description not in "\n".join(str(value or "") for value in row) for row in audit_rows)

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert replay.status_code == 200
        assert replay.json() == body
        assert music_prompt_memory_storage_counts(db_path) == after_create

        # A reused key cannot attach a second note to different source input.
        altered = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "description": "Nhạc nền nhịp nhanh cho video giới thiệu sản phẩm khác."},
        )
        assert altered.status_code == 409
        assert music_prompt_memory_storage_counts(db_path) == after_create

        # An originality guard is not a partial save and does not create a
        # fallback result that a browser could mistake for a selected prompt.
        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={
                **payload,
                "description": "Tạo nhạc giống bài hát và giọng của một ca sĩ nổi tiếng.",
                "idempotency_key": "music-prompt-composer-save-guard-0001",
            },
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_MUSIC_PROMPT_COPYRIGHT_GUARD"
        guarded_data = guarded.json()["data"]
        assert guarded_data["draft_recomputed_on_server"] is False
        assert guarded_data["web_note_persisted"] is False
        assert "note" not in guarded_data
        assert music_prompt_memory_storage_counts(db_path) == after_create

        # Memory reads retain owner-only access even though this note came
        # from the Media Workspace route family.
        with make_client(tmp_path, monkeypatch) as other:
            other_csrf = login(other, "music-prompt-memory-other@example.com")
            assert other_csrf
            hidden = other.get(f"/api/v1/memory/notes/{note_id}")
            assert hidden.status_code == 200
            assert hidden.json()["ok"] is False
            assert hidden.json()["error_code"] == "WEB_MEMORY_NOTE_NOT_FOUND"
            assert description not in hidden.text


def test_music_prompt_composer_memory_save_respects_memory_center_maintenance_gate(tmp_path, monkeypatch):
    path = "/api/v1/media-workspace/tools/music-prompt-composer/save"
    with make_client(tmp_path, monkeypatch, memory_enabled=False) as client:
        csrf = login(client, "music-prompt-memory-disabled@example.com")
        response = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(destination="memory_note", idempotency_key="music-prompt-memory-disabled-0001"),
        )
        assert response.status_code == 503
        assert "WEBAPP_MEMORY_CENTER_ENABLED" in response.text
