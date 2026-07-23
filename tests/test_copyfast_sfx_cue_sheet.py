"""Focused contracts for the Web-native SFX Cue Sheet endpoint.

The endpoint is deliberately an editorial receipt, not a compatibility layer
for Telegram SFX callbacks or the Bot's Freesound catalog/preview workflow.
A signed Web session may choose one reviewed opaque preset and receive exactly
three semantic positions.  It cannot create media, timing, a job, credits, a
Memory note, an asset, or another durable delivery side effect.
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

PATH = "/api/v1/media-workspace/tools/sfx-cue-sheet/compose"

PRESET_FAMILIES = {
    "motion_transition": "motion",
    "interface_confirm": "interface",
    "reveal_impact": "impact",
    "status_signal": "signal",
    "caption_emphasis": "emphasis",
}

PLACEMENT_IDS = ("opening", "transition", "closing")

BOUNDARY_BOOLEAN_FIELDS = (
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
    "source_video_inspected",
    "catalog_searched",
    "sfx_generated",
)


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "sfx-cue-sheet-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "sfx-cue-sheet-test-session-secret")
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
            "display_name": "SFX Cue Sheet Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def cue_sheet_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": "Mở video giới thiệu ứng dụng quản lý đơn hàng, chuyển sang phần bằng chứng và kết bằng CTA rõ ràng.",
        "language": "vi",
        "web_sfx_preset_id": "motion_transition",
    }
    payload.update(overrides)
    return payload


def relevant_storage_counts(db_path) -> dict[str, int]:
    """Every durable store a transient cue receipt must leave untouched."""

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


def assert_boundary(data: dict[str, Any], *, cue_sheet_present: bool) -> None:
    expected = {"execution", *BOUNDARY_BOOLEAN_FIELDS}
    if cue_sheet_present:
        expected.add("cue_sheet")
    assert set(data) == expected
    assert data["execution"] == "web_native_deterministic_sfx_cue_sheet_only"
    for field in BOUNDARY_BOOLEAN_FIELDS:
        assert data[field] is False


def assert_no_delivery_or_timeline_reference(data: dict[str, Any]) -> None:
    keys = set(_walk_keys(data))
    assert not keys.intersection({
        "provider_url", "provider_id", "job_id", "payment_url", "output_url",
        "audio_url", "preview_url", "asset_url", "collection_id", "telegram_message_id",
        "duration_seconds", "start_ms", "end_ms", "timestamp", "timeline", "waveform",
        "beat_position", "catalog_result", "preview_id",
    })
    strings = [item for item in _walk_values(data) if isinstance(item, str)]
    assert not any("http://" in item.lower() or "https://" in item.lower() for item in strings)


def assert_cue_sheet(data: dict[str, Any], source: dict[str, Any]) -> None:
    cue_sheet = data["cue_sheet"]
    assert cue_sheet["description"] == source["description"]
    assert cue_sheet["language"] == source["language"]
    assert cue_sheet["web_sfx_preset_id"] == source["web_sfx_preset_id"]
    assert cue_sheet["cue_family"] == PRESET_FAMILIES[source["web_sfx_preset_id"]]
    assert isinstance(cue_sheet["title"], str) and cue_sheet["title"].strip()
    assert isinstance(cue_sheet["placement_notice"], str) and cue_sheet["placement_notice"].strip()
    assert [cue["ordinal"] for cue in cue_sheet["cues"]] == [1, 2, 3]
    assert [cue["placement_id"] for cue in cue_sheet["cues"]] == list(PLACEMENT_IDS)
    for cue in cue_sheet["cues"]:
        assert set(cue) == {
            "ordinal", "placement_id", "placement", "cue_role", "direction", "mix_note",
            "avoid_note", "editorial_note",
        }
        assert all(isinstance(cue[field], str) and cue[field].strip() for field in cue if field != "ordinal")
    assert all(isinstance(item, str) and item.strip() for item in cue_sheet["cautions"])
    assert all(isinstance(item, str) and item.strip() for item in cue_sheet["review_before_use"])


def test_sfx_cue_sheet_requires_signed_session_csrf_and_returns_only_three_semantic_positions(tmp_path, monkeypatch):
    """The explicit radio preset produces text-only editor positions, never a fake timeline."""

    db_path = tmp_path / "sfx-cue-sheet-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(PATH, json=cue_sheet_payload()).status_code == 401
        csrf = login(client, "sfx-cue-sheet-owner@example.com")
        before = relevant_storage_counts(db_path)

        assert client.post(PATH, json=cue_sheet_payload()).status_code == 403
        headers = {"X-CSRF-Token": csrf}
        for preset_id in PRESET_FAMILIES:
            source = cue_sheet_payload(
                web_sfx_preset_id=preset_id,
                # This must remain regular prose, not become a raw Bot keyword.
                description="Dùng whoosh nhẹ khi chuyển đoạn, nhưng giữ lời đọc và CTA rõ ràng.",
            )
            response = client.post(PATH, headers=headers, json=source)
            assert response.status_code == 200, source
            assert response.headers["Cache-Control"] == "no-store, private"
            body = response.json()
            assert body["ok"] is True
            assert body["status"] == "draft"
            assert body["error_code"] is None
            assert_boundary(body["data"], cue_sheet_present=True)
            assert_cue_sheet(body["data"], source)
            assert_no_delivery_or_timeline_reference(body["data"])

            # Repeating a stateless composition cannot turn the receipt into a
            # persisted catalog, memory, asset or idempotency record.
            repeat = client.post(PATH, headers=headers, json=source)
            assert repeat.status_code == 200
            assert repeat.json()["data"] == body["data"]

        english_source = cue_sheet_payload(
            description="Open the product story, clarify the proof transition, and leave space for a clear closing CTA.",
            language="en",
            web_sfx_preset_id="caption_emphasis",
        )
        english = client.post(PATH, headers=headers, json=english_source)
        assert english.status_code == 200
        assert_cue_sheet(english.json()["data"], english_source)
        assert english.json()["data"]["cue_sheet"]["cues"][0]["placement"] == "Opening"

        assert relevant_storage_counts(db_path) == before


def test_sfx_cue_sheet_rejects_raw_bot_inputs_timeline_fields_and_schema_expansion(tmp_path, monkeypatch):
    """No callback, Bot command, provider selector, or fabricated time field enters the Web contract."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "sfx-cue-sheet-schema@example.com")
        invalid_payloads = (
            {"description": "x", "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": "x" * 501, "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": 42, "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": "Brief SFX hợp lệ", "language": "VI", "web_sfx_preset_id": "motion_transition"},
            {"description": "Brief SFX hợp lệ", "language": "zh", "web_sfx_preset_id": "motion_transition"},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "MOTION_TRANSITION"},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "sfx_quick|whoosh"},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "whoosh"},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "motion_transition|fallback"},
            {"description": "sfx_quick|showroom|whoosh", "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": "music_quick|showroom|custom_sfx", "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": "/sfx_library whoosh", "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": "play_sfx|sfx|1", "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": "whoosh", "language": "vi", "web_sfx_preset_id": "motion_transition"},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "motion_transition", "duration_seconds": 30},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "motion_transition", "start_ms": 0},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "motion_transition", "timeline": []},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "motion_transition", "callback_data": "sfx_quick|whoosh"},
            {"description": "Brief SFX hợp lệ", "language": "vi", "web_sfx_preset_id": "motion_transition", "provider_url": "https://provider.invalid/private"},
            {"description": "Brief SFX hợp lệ", "language": "vi"},
        )
        for payload in invalid_payloads:
            response = client.post(PATH, headers={"X-CSRF-Token": csrf}, json=payload)
            assert response.status_code == 422, payload
            assert response.headers["Cache-Control"] == "no-store, private"


def test_sfx_cue_sheet_guard_and_maintenance_preserve_the_no_runtime_boundary(tmp_path, monkeypatch):
    db_path = tmp_path / "sfx-cue-sheet-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "sfx-cue-sheet-policy@example.com")
        before = relevant_storage_counts(db_path)
        response = client.post(
            PATH,
            headers={"X-CSRF-Token": csrf},
            json=cue_sheet_payload(description="Tạo hiệu ứng giống bài hát, beat và giọng của một ca sĩ nổi tiếng."),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_SFX_CUE_COPYRIGHT_GUARD"
        assert_boundary(body["data"], cue_sheet_present=False)
        assert_no_delivery_or_timeline_reference(body["data"])
        assert relevant_storage_counts(db_path) == before

    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "sfx-cue-sheet-disabled@example.com")
        response = client.post(PATH, headers={"X-CSRF-Token": csrf}, json=cue_sheet_payload())
        assert response.status_code == 503
        assert "WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED" in response.text


def test_sfx_cue_sheet_keeps_a_punctuated_brief_clean_in_each_editorial_direction(tmp_path, monkeypatch):
    """A normal sentence-ending period must not render as an accidental ``..`` cue."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "sfx-cue-sheet-punctuation@example.com")
        response = client.post(
            PATH,
            headers={"X-CSRF-Token": csrf},
            json=cue_sheet_payload(description="Brief kết thúc bằng dấu chấm."),
        )
        assert response.status_code == 200
        directions = response.json()["data"]["cue_sheet"]["cues"]
        assert len(directions) == 3
        assert all(".." not in cue["direction"] for cue in directions)
