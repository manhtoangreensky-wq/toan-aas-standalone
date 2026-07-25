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
import uuid

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


def upload_asset(
    client: TestClient,
    csrf: str,
    *,
    key: str,
    name: str,
    content: bytes,
    content_type: str,
    display_name: str | None = "Audio reference",
) -> dict:
    data = {} if display_name is None else {"display_name": display_name}
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data=data,
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


def test_media_workspace_preview_is_flagged_owner_scoped_verified_and_never_public(tmp_path, monkeypatch):
    """An inline preview is an opt-in read of one attached owner audio file."""
    db_path = tmp_path / "copyfast-media-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "media-preview-owner@example.com")
        collection = create_collection(owner, csrf, "media-preview-collection-create-0001")
        audio = upload_asset(
            owner,
            csrf,
            key="media-preview-audio-upload-0001",
            name="private-intro.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        attached = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(audio["id"], 1, "media-preview-attach-0001"),
        )
        assert attached.status_code == 200
        item_id = attached.json()["data"]["item_id"]
        endpoint = f"/api/v1/media-workspace/collections/{collection['id']}/items/{item_id}/preview"

        # The feature is intentionally unavailable until an operator elects
        # to expose same-origin previews.  It has no provider/Bot fallback.
        disabled = owner.get(endpoint)
        assert disabled.status_code == 503
        assert "WEBAPP_MEDIA_WORKSPACE_PREVIEW_ENABLED" in disabled.text

        monkeypatch.setenv("WEBAPP_MEDIA_WORKSPACE_PREVIEW_ENABLED", "true")
        preview = owner.get(endpoint)
        assert preview.status_code == 200
        assert preview.content == wav_bytes()
        assert preview.headers["content-type"].startswith("audio/wav")
        assert preview.headers["content-disposition"].startswith("inline;")
        assert preview.headers["cache-control"] == "no-store, private"
        assert preview.headers["cross-origin-resource-policy"] == "same-origin"
        assert preview.headers["referrer-policy"] == "no-referrer"
        assert "accept-ranges" not in preview.headers
        assert "private-web-assets" not in preview.text
        with sqlite3.connect(db_path) as conn:
            audit = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action='web.media.item.preview'"
            ).fetchone()
        assert audit is not None
        assert audit[0] == item_id
        assert "owner_scoped_verified" in audit[1]
        assert audio["id"] not in audit[1]

        # A different signed account sees the same non-enumerating 404 and
        # never receives another account's bytes or a public URL.
        with make_client(tmp_path, monkeypatch) as other:
            register_and_login(other, "media-preview-other@example.com")
            foreign = other.get(endpoint)
            assert foreign.status_code == 404
            assert wav_bytes() not in foreign.content

        archived = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "media-preview-archive-0001"},
        )
        assert archived.status_code == 200
        assert owner.get(endpoint).status_code == 404


def test_media_workspace_preview_fails_closed_when_the_private_blob_changes(tmp_path, monkeypatch):
    """Preview must not stream a swapped/tampered Asset Vault object."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "media-preview-integrity@example.com")
        collection = create_collection(client, csrf, "media-preview-integrity-collection-0001")
        audio = upload_asset(
            client,
            csrf,
            key="media-preview-integrity-upload-0001",
            name="integrity.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        attached = client.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(audio["id"], 1, "media-preview-integrity-attach-0001"),
        )
        item_id = attached.json()["data"]["item_id"]
        blob = next((tmp_path / "private-web-assets" / "objects").glob("*.blob"))
        blob.write_bytes(b"not-the-verified-audio")
        monkeypatch.setenv("WEBAPP_MEDIA_WORKSPACE_PREVIEW_ENABLED", "true")
        endpoint = f"/api/v1/media-workspace/collections/{collection['id']}/items/{item_id}/preview"
        failed = client.get(endpoint)
        assert failed.status_code == 404
        assert b"not-the-verified-audio" not in failed.content


def test_media_audio_listing_filters_before_pagination_and_is_owner_scoped(tmp_path, monkeypatch):
    """Older Vault audio stays searchable even after hundreds of non-audio files."""
    db_path = tmp_path / "copyfast-media-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "media-audio-list-owner@example.com")
        with sqlite3.connect(db_path) as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("media-audio-list-owner@example.com",),
            ).fetchone()[0]
            noise_rows = [
                (
                    str(uuid.uuid4()), account_id, None, f"Noise asset {index}", f"noise-{index}.txt", ".txt",
                    "text/plain", 12, f"{index:064x}", f"noise-storage-{index}", "active",
                    "2099-01-01T00:00:00+00:00", "2099-01-01T00:00:00+00:00", None,
                )
                for index in range(301)
            ]
            newer_audio_id = str(uuid.uuid4())
            older_audio_id = str(uuid.uuid4())
            audio_rows = [
                (
                    newer_audio_id, account_id, None, "Needle audio mới", "needle-new.wav", ".wav",
                    "audio/wav", 44, "a" * 64, "needle-storage-new", "active",
                    "2001-01-01T00:00:00+00:00", "2001-01-01T00:00:00+00:00", None,
                ),
                (
                    older_audio_id, account_id, None, "Needle audio cũ", "needle-old.wav", ".wav",
                    "audio/wav", 44, "b" * 64, "needle-storage-old", "active",
                    "2000-01-01T00:00:00+00:00", "2000-01-01T00:00:00+00:00", None,
                ),
            ]
            conn.executemany(
                """INSERT INTO web_asset_files (
                    id, account_id, project_id, display_name, original_filename, extension, content_type,
                    byte_size, sha256, storage_key, state, created_at, updated_at, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [*noise_rows, *audio_rows],
            )

        first = client.get(
            "/api/v1/media-workspace/audio-assets",
            params={"q": "Needle audio", "limit": 1, "offset": 0},
        )
        assert first.status_code == 200
        first_data = first.json()["data"]
        assert [item["id"] for item in first_data["items"]] == [newer_audio_id]
        assert first_data["has_more"] is True
        assert first_data["next_offset"] == 1
        assert first_data["filters"] == {"q": "Needle audio"}
        assert first_data["pagination"] == {"limit": 1, "offset": 0, "returned": 1}

        second = client.get(
            "/api/v1/media-workspace/audio-assets",
            params={"q": "Needle audio", "limit": 1, "offset": 1},
        )
        assert second.status_code == 200
        second_data = second.json()["data"]
        assert [item["id"] for item in second_data["items"]] == [older_audio_id]
        assert second_data["has_more"] is False
        assert second_data["next_offset"] is None

        with make_client(tmp_path, monkeypatch) as other:
            register_and_login(other, "media-audio-list-other@example.com")
            hidden = other.get("/api/v1/media-workspace/audio-assets", params={"q": "Needle audio", "limit": 1})
            assert hidden.status_code == 200
            assert hidden.json()["data"]["items"] == []


def test_music_sfx_library_is_active_owner_scoped_metadata_only_and_never_persists(tmp_path, monkeypatch):
    """The Web library is a read-only collection index, never a media delivery surface."""
    db_path = tmp_path / "copyfast-media-workspace-test.db"
    endpoint = "/api/v1/media-workspace/library-items"
    with make_client(tmp_path, monkeypatch) as owner:
        assert owner.get(endpoint, params={"role": "music"}).status_code == 401
        csrf = register_and_login(owner, "media-library-owner@example.com")

        collection = create_collection(
            owner,
            csrf,
            "media-library-owner-collection-create-0001",
            title="Thư viện chiến dịch hè",
        )
        music_primary = upload_asset(
            owner,
            csrf,
            key="media-library-primary-upload-0001",
            name="private-primary.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        primary_attached = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                music_primary["id"],
                1,
                "media-library-primary-attach-0001",
                title_override="Nhạc mở đầu chiến dịch",
                tags=["summer", "brand"],
                favorite=True,
                user_declared_duration_seconds=15,
            ),
        )
        assert primary_attached.status_code == 200
        primary_item_id = primary_attached.json()["data"]["item_id"]

        music_secondary = upload_asset(
            owner,
            csrf,
            key="media-library-secondary-upload-0001",
            name="private-secondary.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        secondary_attached = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                music_secondary["id"],
                2,
                "media-library-secondary-attach-0001",
                title_override="Nhạc nền ambient",
                tags=["ambient"],
                favorite=False,
                user_declared_duration_seconds=None,
            ),
        )
        assert secondary_attached.status_code == 200
        secondary_item_id = secondary_attached.json()["data"]["item_id"]

        sfx = upload_asset(
            owner,
            csrf,
            key="media-library-sfx-upload-0001",
            name="private-transition.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        sfx_attached = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                sfx["id"],
                3,
                "media-library-sfx-attach-0001",
                role="sfx",
                title_override="SFX chuyển cảnh",
                tags=["transition"],
                favorite=True,
                user_declared_duration_seconds=2,
            ),
        )
        assert sfx_attached.status_code == 200
        sfx_item_id = sfx_attached.json()["data"]["item_id"]

        reference = upload_asset(
            owner,
            csrf,
            key="media-library-reference-upload-0001",
            name="private-reference.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        reference_attached = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                reference["id"],
                4,
                "media-library-reference-attach-0001",
                role="reference",
                title_override="Tham chiếu nội bộ",
            ),
        )
        assert reference_attached.status_code == 200
        reference_item_id = reference_attached.json()["data"]["item_id"]

        archived_collection = create_collection(
            owner,
            csrf,
            "media-library-archived-collection-create-0001",
            title="Collection đã archive",
        )
        archived_attached = owner.post(
            f"/api/v1/media-workspace/collections/{archived_collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                music_primary["id"],
                1,
                "media-library-archived-attach-0001",
                title_override="Không được liệt kê archive",
            ),
        )
        assert archived_attached.status_code == 200
        archived_item_id = archived_attached.json()["data"]["item_id"]
        archived = owner.post(
            f"/api/v1/media-workspace/collections/{archived_collection['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "media-library-archive-0001"},
        )
        assert archived.status_code == 200

        inactive_collection = create_collection(
            owner,
            csrf,
            "media-library-inactive-collection-create-0001",
            title="Collection asset inactive",
        )
        inactive_asset = upload_asset(
            owner,
            csrf,
            key="media-library-inactive-upload-0001",
            name="private-inactive.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        inactive_attached = owner.post(
            f"/api/v1/media-workspace/collections/{inactive_collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                inactive_asset["id"],
                1,
                "media-library-inactive-attach-0001",
                title_override="Không được liệt kê inactive",
            ),
        )
        assert inactive_attached.status_code == 200
        inactive_item_id = inactive_attached.json()["data"]["item_id"]
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_asset_files SET state='archived' WHERE id=?",
                (inactive_asset["id"],),
            )
            conn.commit()

        def library_table_counts() -> dict[str, int]:
            with sqlite3.connect(db_path) as conn:
                return {
                    table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in (
                        "web_media_collections", "web_media_items", "web_media_events",
                        "web_idempotency", "web_audit_events",
                    )
                }

        before = library_table_counts()
        invalid = owner.get(endpoint, params={"role": "reference"})
        assert invalid.status_code == 422

        first = owner.get(endpoint, params={"role": "music", "limit": 1, "offset": 0})
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["ok"] is True
        assert first_body["status"] == "read_only"
        assert set(first_body["data"]) == {"items", "filters", "pagination", "boundary"}
        first_data = first_body["data"]
        assert first_data["filters"] == {"role": "music", "q": ""}
        assert first_data["pagination"] == {
            "limit": 1, "offset": 0, "returned": 1, "has_more": True, "next_offset": 1,
        }
        assert set(first_data["items"][0]) == {
            "collection_id", "collection_title", "role", "reference_title", "tags", "favorite",
            "user_declared_duration_seconds", "updated_at", "collection_updated_at",
        }
        assert first_data["items"][0]["role"] == "music"
        assert first_data["items"][0]["collection_id"] == collection["id"]
        assert first_data["items"][0]["reference_title"] == "Nhạc mở đầu chiến dịch"
        assert first_data["items"][0]["tags"] == ["summer", "brand"]
        assert first_data["items"][0]["favorite"] is True
        assert first_data["items"][0]["user_declared_duration_seconds"] == 15
        assert first_data["boundary"] == {
            "execution": "web_native_media_library_read_only",
            "library_persisted": False,
            "collection_mutated": False,
            "input_persisted": False,
            "source_audio_inspected": False,
            "provider_called": False,
            "catalog_searched": False,
            "player_opened": False,
            "preview_created": False,
            "audio_created": False,
            "output_created": False,
            "job_created": False,
            "wallet_mutated": False,
            "payment_started": False,
            "asset_saved": False,
            "delivery_created": False,
            "bot_called": False,
            "telegram_called": False,
            "rights_verified": False,
            "release_approved": False,
        }

        second = owner.get(endpoint, params={"role": "music", "limit": 1, "offset": 1})
        assert second.status_code == 200
        second_data = second.json()["data"]
        assert second_data["pagination"] == {
            "limit": 1, "offset": 1, "returned": 1, "has_more": False, "next_offset": None,
        }
        assert {first_data["items"][0]["reference_title"], second_data["items"][0]["reference_title"]} == {
            "Nhạc mở đầu chiến dịch", "Nhạc nền ambient",
        }

        filtered = owner.get(endpoint, params={"role": "music", "q": "ambient", "limit": 24})
        assert filtered.status_code == 200
        assert [item["reference_title"] for item in filtered.json()["data"]["items"]] == ["Nhạc nền ambient"]

        sfx_listing = owner.get(endpoint, params={"role": "sfx", "limit": 24})
        assert sfx_listing.status_code == 200
        assert [item["reference_title"] for item in sfx_listing.json()["data"]["items"]] == ["SFX chuyển cảnh"]

        for private_value in (
            music_primary["id"], music_secondary["id"], sfx["id"], reference["id"], inactive_asset["id"],
            primary_item_id, secondary_item_id, sfx_item_id, reference_item_id, archived_item_id, inactive_item_id,
            "private-primary.wav", "private-secondary.wav", "private-transition.wav", "private-reference.wav",
            "private-inactive.wav", "private-web-assets", "storage_key", "original_filename",
            "Không được liệt kê archive", "Không được liệt kê inactive", "Tham chiếu nội bộ",
        ):
            assert private_value not in first.text
            assert private_value not in second.text
            assert private_value not in sfx_listing.text
        assert library_table_counts() == before

        # Asset Vault defaults an omitted display label from the upload name.
        # The library must never use that source-derived value as a visible
        # fallback or a searchable field; only an explicit item title is safe
        # here. This regression is intentionally after the read-count check:
        # attaching the fixture is a separate existing Workspace write.
        source_named = upload_asset(
            owner,
            csrf,
            key="media-library-source-derived-upload-0001",
            name="source-derived-private-name.wav",
            content=wav_bytes(),
            content_type="audio/wav",
            display_name=None,
        )
        source_named_attached = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(
                source_named["id"],
                5,
                "media-library-source-derived-attach-0001",
                title_override="",
                tags=[],
                favorite=False,
                user_declared_duration_seconds=None,
            ),
        )
        assert source_named_attached.status_code == 200
        neutral_listing = owner.get(endpoint, params={"role": "music", "limit": 24})
        assert neutral_listing.status_code == 200
        neutral_items = neutral_listing.json()["data"]["items"]
        assert any(item["reference_title"] == "Audio reference" for item in neutral_items)
        assert source_named["id"] not in neutral_listing.text
        assert "source-derived-private-name.wav" not in neutral_listing.text
        source_name_filter = owner.get(
            endpoint,
            params={"role": "music", "q": "source-derived-private-name", "limit": 24},
        )
        assert source_name_filter.status_code == 200
        assert source_name_filter.json()["data"]["items"] == []

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "media-library-other@example.com")
            foreign_collection = create_collection(
                other,
                csrf_other,
                "media-library-other-collection-create-0001",
                title="Collection người khác",
            )
            foreign_audio = upload_asset(
                other,
                csrf_other,
                key="media-library-other-upload-0001",
                name="foreign-private.wav",
                content=wav_bytes(),
                content_type="audio/wav",
            )
            foreign_attached = other.post(
                f"/api/v1/media-workspace/collections/{foreign_collection['id']}/items",
                headers={"X-CSRF-Token": csrf_other},
                json=attach_payload(
                    foreign_audio["id"], 1, "media-library-other-attach-0001",
                    title_override="Nhạc của người khác",
                ),
            )
            assert foreign_attached.status_code == 200
            foreign = other.get(endpoint, params={"role": "music", "limit": 24})
            assert [item["reference_title"] for item in foreign.json()["data"]["items"]] == ["Nhạc của người khác"]

        owner_after_foreign = owner.get(endpoint, params={"role": "music", "limit": 24})
        assert owner_after_foreign.status_code == 200
        assert {item["reference_title"] for item in owner_after_foreign.json()["data"]["items"]} == {
            "Nhạc mở đầu chiến dịch", "Nhạc nền ambient", "Audio reference",
        }
        assert "Nhạc của người khác" not in owner_after_foreign.text


def test_media_collections_are_paginated_and_owner_scoped(tmp_path, monkeypatch):
    """Every collection remains reachable through bounded owner-scoped pages."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "media-collection-list-owner@example.com")
        created = [
            create_collection(
                client,
                csrf,
                f"media-collection-browse-{index:04d}",
                title=f"Browse pagination {index}",
            )
            for index in range(1, 4)
        ]
        pages = [
            client.get(
                "/api/v1/media-workspace/collections",
                params={"state": "all", "q": "Browse pagination", "limit": 1, "offset": offset},
            )
            for offset in range(3)
        ]
        assert all(page.status_code == 200 for page in pages)
        page_data = [page.json()["data"] for page in pages]
        seen_ids = {item["id"] for data in page_data for item in data["items"]}
        assert seen_ids == {item["id"] for item in created}
        assert page_data[0]["has_more"] is True
        assert page_data[0]["next_offset"] == 1
        assert page_data[1]["next_offset"] == 2
        assert page_data[2]["has_more"] is False
        assert page_data[2]["next_offset"] is None
        assert page_data[0]["filters"] == {
            "q": "Browse pagination", "tag": "", "prompt_mode": "", "state": "all",
        }
        assert page_data[0]["pagination"] == {"limit": 1, "offset": 0, "returned": 1}

        with make_client(tmp_path, monkeypatch) as other:
            register_and_login(other, "media-collection-list-other@example.com")
            hidden = other.get("/api/v1/media-workspace/collections", params={"state": "all", "limit": 1})
            assert hidden.status_code == 200
            assert hidden.json()["data"]["items"] == []


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


def test_collection_review_pack_is_owner_scoped_revision_bound_and_never_persists(tmp_path, monkeypatch):
    """A review receipt may reveal readiness counts, never a faux clearance."""
    db_path = tmp_path / "copyfast-media-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as owner:
        endpoint = "/api/v1/media-workspace/collections/00000000-0000-4000-8000-000000000001/review-pack"
        assert owner.post(endpoint, json={"expected_revision": 1}).status_code == 401

        csrf = register_and_login(owner, "media-review-owner@example.com")
        collection = create_collection(owner, csrf, "media-review-create-0001")
        endpoint = f"/api/v1/media-workspace/collections/{collection['id']}/review-pack"

        denied = owner.post(endpoint, json={"expected_revision": 1})
        assert denied.status_code == 403
        assert owner.post(endpoint, headers={"X-CSRF-Token": csrf}, json={"expected_revision": 1, "extra": True}).status_code == 422

        audio = upload_asset(
            owner,
            csrf,
            key="media-review-audio-upload-0001",
            name="review-private.wav",
            content=wav_bytes(),
            content_type="audio/wav",
        )
        attached = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items",
            headers={"X-CSRF-Token": csrf},
            json=attach_payload(audio["id"], 1, "media-review-attach-0001", attribution=""),
        )
        assert attached.status_code == 200
        assert attached.json()["data"]["revision"] == 2

        def table_counts() -> dict[str, int]:
            with sqlite3.connect(db_path) as conn:
                return {
                    table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("web_media_collections", "web_media_items", "web_media_events", "web_idempotency", "web_audit_events")
                }

        before = table_counts()
        review = owner.post(endpoint, headers={"X-CSRF-Token": csrf}, json={"expected_revision": 2})
        assert review.status_code == 200
        body = review.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        pack = data["review_pack"]
        assert data["collection_id"] == collection["id"]
        assert data["revision"] == 2
        assert pack["review_state"] == "needs_reference_metadata"
        assert pack["reference_summary"] == {
            "total": 1,
            "music": 1,
            "sfx": 0,
            "reference": 0,
            "favorite": 1,
            "duration_declared": 1,
            "attribution_missing": 1,
            "license_missing": 0,
            "unavailable": 0,
            "collection_rights_note_declared": True,
        }
        assert [check["id"] for check in pack["checks"]] == [
            "brief_originality", "reference_metadata", "mix_accessibility", "release_handoff",
        ]
        for key in (
            "collection_mutated", "review_pack_persisted", "approval_recorded", "input_persisted",
            "source_audio_inspected", "source_video_inspected", "provider_called", "catalog_searched", "player_opened",
            "preview_created", "audio_created", "output_created", "job_created", "wallet_mutated", "payment_started",
            "asset_saved", "delivery_created", "bot_called", "telegram_called", "rights_verified", "release_approved",
        ):
            assert data[key] is False
        assert data["execution"] == "web_native_collection_review_only"
        for private_value in (
            collection_payload("unused")["creative_brief"],
            collection_payload("unused")["rights_note"],
            audio["id"],
            "review-private.wav",
            "private-web-assets",
        ):
            assert private_value not in review.text
        assert table_counts() == before

        replay = owner.post(endpoint, headers={"X-CSRF-Token": csrf}, json={"expected_revision": 2})
        assert replay.status_code == 200
        assert replay.json() == body
        assert table_counts() == before

        stale = owner.post(endpoint, headers={"X-CSRF-Token": csrf}, json={"expected_revision": 1})
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_MEDIA_REVISION_CONFLICT"

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "media-review-other@example.com")
            foreign = other.post(endpoint, headers={"X-CSRF-Token": csrf_other}, json={"expected_revision": 2})
            assert foreign.status_code == 200
            assert foreign.json()["error_code"] == "WEB_MEDIA_COLLECTION_NOT_FOUND"
            assert collection_payload("unused")["creative_brief"] not in foreign.text

        archived = owner.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "media-review-archive-0001"},
        )
        assert archived.status_code == 200
        blocked = owner.post(endpoint, headers={"X-CSRF-Token": csrf}, json={"expected_revision": 3})
        assert blocked.status_code == 200
        assert blocked.json()["error_code"] == "WEB_MEDIA_COLLECTION_ARCHIVED"
