"""Risk-focused contracts for the private Web Audio Library & Briefing.

These tests deliberately exercise the security boundary rather than a broad
feature matrix: signed-session/CSRF writes, account ownership, Asset Vault
audio-only references, copyright guardrails, idempotency and archive state.
The workspace must never turn a brief into a provider call, job, charge or
public media delivery.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_memory", "copyfast_prompt_library",
    "copyfast_music_media", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-media-workspace-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-media-workspace-session-secret")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "1")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "10")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Media Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def collection_payload(key: str, **overrides) -> dict:
    payload = {
        "title": "Âm thanh chiến dịch mùa hè",
        "description": "Kho tham chiếu nội bộ cho video quảng bá mùa hè.",
        "creative_brief": "Nhạc nền tươi sáng, 108 BPM, guitar sạch, nhịp gọn cho voice-over.",
        "prompt_mode": "background",
        "use_context": "video quảng cáo 15 giây",
        "tags": ["summer", "launch"],
        "rights_note": "Tôi xác nhận có quyền sử dụng các tệp và brief trong collection này.",
        "project_id": "",
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def create_collection(client: TestClient, csrf: str, key: str = "media-collection-create-0001", **overrides) -> dict:
    response = client.post(
        "/api/v1/media-workspace/collections",
        headers={"X-CSRF-Token": csrf},
        json=collection_payload(key, **overrides),
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["status"] == "draft"
    return response.json()["data"]["collection"]


def upload_asset(client: TestClient, csrf: str, *, key: str, name: str, content: bytes, content_type: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Audio reference"},
        files={"file": (name, content, content_type)},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def wav_bytes() -> bytes:
    """A tiny RIFF/WAVE fixture; the Vault validates format magic, not playback."""
    return (
        b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little")
        + b"\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )


def attach_payload(asset_id: str, revision: int, key: str, **overrides) -> dict:
    payload = {
        "asset_id": asset_id,
        "expected_revision": revision,
        "idempotency_key": key,
        "role": "music",
        "title_override": "Nhạc intro đã duyệt",
        "attribution": "",
        "license_note": "Tôi chịu trách nhiệm kiểm tra license và quyền thương mại trước khi đăng.",
        "tags": ["intro"],
        "favorite": True,
        "user_declared_duration_seconds": 15,
    }
    payload.update(overrides)
    return payload


def test_media_workspace_is_csrf_owned_idempotent_and_never_persists_brief_receipts(tmp_path, monkeypatch):
    """A mutable media brief needs a signed owner and safe replay semantics."""
    db_path = tmp_path / "copyfast-media-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as first:
        assert first.get("/api/v1/media-workspace/summary").status_code == 401
        csrf = register_and_login(first, "media-owner@example.com")
        raw = collection_payload("media-collection-create-0001")

        denied = first.post("/api/v1/media-workspace/collections", json=raw)
        assert denied.status_code == 403

        # Reject a large body before Pydantic/SQLite can parse or persist any
        # part of it. The cap is a media-specific 64 KiB ASGI boundary.
        oversized = first.post(
            "/api/v1/media-workspace/collections",
            headers={"X-CSRF-Token": csrf},
            json={"title": "x" * (65 * 1024)},
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_MEDIA_WORKSPACE_BODY_TOO_LARGE"
        assert oversized.headers["cache-control"] == "no-store, private"
        assert first.get("/api/v1/media-workspace/summary").json()["data"]["collections"]["total"] == 0

        created = create_collection(first, csrf)
        assert created["revision"] == 1
        assert created["execution"] == "authoring_only"

        replay = first.post(
            "/api/v1/media-workspace/collections",
            headers={"X-CSRF-Token": csrf},
            json=raw,
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["collection"]["id"] == created["id"]

        collision = first.post(
            "/api/v1/media-workspace/collections",
            headers={"X-CSRF-Token": csrf},
            json=collection_payload("media-collection-create-0001", title="Một collection khác"),
        )
        assert collision.status_code == 409

        # Idempotency is valuable for a retry, but a receipt must not become a
        # second store for private creative material.
        with sqlite3.connect(db_path) as conn:
            receipts = conn.execute(
                "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-media-workspace:%'"
            ).fetchall()
        assert receipts
        assert all(raw["creative_brief"] not in str(row[0]) for row in receipts)
        assert all(raw["description"] not in str(row[0]) for row in receipts)

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "media-other@example.com")
            hidden = second.get(f"/api/v1/media-workspace/collections/{created['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_MEDIA_COLLECTION_NOT_FOUND"
            assert raw["creative_brief"] not in hidden.text

            forbidden = second.post(
                f"/api/v1/media-workspace/collections/{created['id']}/archive",
                headers={"X-CSRF-Token": csrf_second},
                json={"expected_revision": 1, "idempotency_key": "media-other-archive-0001"},
            )
            assert forbidden.status_code == 200
            assert forbidden.json()["error_code"] == "WEB_MEDIA_COLLECTION_NOT_FOUND"


def test_media_workspace_accepts_only_owned_active_audio_and_keeps_delivery_private(tmp_path, monkeypatch):
    """No URLs/provider previews: a collection can reference only its own active Vault audio."""
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "media-assets-owner@example.com")
        collection = create_collection(first, csrf, "media-assets-collection-create-0001")
        text_asset = upload_asset(
            first, csrf, key="media-assets-text-upload-0001", name="brief.txt",
            content=b"Private audio brief, not an audio file.", content_type="text/plain",
        )
        audio_asset = upload_asset(
            first, csrf, key="media-assets-wav-upload-0001", name="intro.wav",
            content=wav_bytes(), content_type="audio/wav",
        )

        # An unknown remote source is not a model field: URLs, Telegram file
        # IDs and provider previews cannot enter the owner-scoped relation.
        raw_source = first.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                audio_asset["id"], 1, "media-assets-raw-source-0001",
                source_url="https://untrusted.example/audio.mp3",
            ),
        )
        assert raw_source.status_code == 422

        non_audio = first.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(text_asset["id"], 1, "media-assets-text-attach-0001"),
        )
        assert non_audio.status_code == 200
        assert non_audio.json()["error_code"] == "WEB_MEDIA_AUDIO_ASSET_NOT_FOUND"

        attached = first.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(audio_asset["id"], 1, "media-assets-audio-attach-0001"),
        )
        assert attached.status_code == 200
        assert attached.json()["ok"] is True
        assert attached.json()["status"] == "draft"
        assert attached.json()["data"]["execution"] == "authoring_only"
        assert attached.json()["data"]["delivery"] == "asset_vault_attachment_only"
        assert attached.json()["data"]["revision"] == 2
        item_id = attached.json()["data"]["item_id"]

        detail = first.get(f"/api/v1/media-workspace/collections/{collection['id']}")
        assert detail.status_code == 200
        item = detail.json()["data"]["items"][0]
        assert item["id"] == item_id
        assert item["asset"]["id"] == audio_asset["id"]
        assert item["delivery"] == "asset_vault_attachment_only"
        assert "storage_key" not in detail.text
        assert "private-web-assets" not in detail.text
        assert "download_url" not in detail.text

        # A different signed account cannot smuggle an owner asset into its
        # own collection even if it knows the UUID.
        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "media-assets-other@example.com")
            other_collection = create_collection(second, csrf_second, "media-assets-other-collection-create-0001")
            cross_owner = second.post(
                f"/api/v1/media-workspace/collections/{other_collection['id']}/items",
                headers={"X-CSRF-Token": csrf_second},
                json=attach_payload(audio_asset["id"], 1, "media-assets-cross-owner-0001"),
            )
            assert cross_owner.status_code == 200
            assert cross_owner.json()["error_code"] == "WEB_MEDIA_AUDIO_ASSET_NOT_FOUND"


def test_media_workspace_blocks_imitation_and_never_claims_generation_or_delivery(tmp_path, monkeypatch):
    """Copyright-sensitive briefs remain guarded; local directions stay text-only."""
    db_path = tmp_path / "copyfast-media-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "media-policy@example.com")
        secret = client.post(
            "/api/v1/media-workspace/collections",
            headers={"X-CSRF-Token": csrf},
            json=collection_payload(
                "media-policy-secret-create-0001",
                creative_brief="api_key=super-secret-token-value-12345",
            ),
        )
        assert secret.status_code == 422

        guarded = client.post(
            "/api/v1/media-workspace/collections",
            headers={"X-CSRF-Token": csrf},
            json=collection_payload(
                "media-policy-guarded-create-0001",
                title="Bản mô phỏng",
                creative_brief="Hãy làm sound like một nghệ sĩ đang nổi tiếng.",
            ),
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_MEDIA_COPYRIGHT_GUARD"
        with sqlite3.connect(db_path) as conn:
            no_guarded_receipt = conn.execute(
                "SELECT COUNT(*) FROM web_idempotency WHERE key=?",
                ("media-policy-guarded-create-0001",),
            ).fetchone()[0]
        assert no_guarded_receipt == 0

        collection = create_collection(client, csrf, "media-policy-safe-create-0001")
        compose = client.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/compose",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1},
        )
        assert compose.status_code == 200
        data = compose.json()["data"]
        assert data["execution"] == "local_deterministic_draft_only"
        assert data["provider_called"] is False
        assert data["charge_started"] is False
        assert len(data["directions"]) == 3
        assert "job_id" not in data
        assert "output_url" not in data
        assert "asset_id" not in data

        archived = client.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "media-policy-safe-archive-0001"},
        )
        assert archived.status_code == 200
        assert archived.json()["data"]["collection"]["state"] == "archived"
        assert archived.json()["data"]["collection"]["revision"] == 2

        archived_replay = client.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "media-policy-safe-archive-0001"},
        )
        assert archived_replay.status_code == 200
        assert archived_replay.json() == archived.json()

        blocked_compose = client.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/compose",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2},
        )
        assert blocked_compose.status_code == 200
        assert blocked_compose.json()["error_code"] == "WEB_MEDIA_COLLECTION_ARCHIVED"
