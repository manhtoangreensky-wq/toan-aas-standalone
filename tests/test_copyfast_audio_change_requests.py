"""High-risk lifecycle contracts for Web-native Audio Change Requests.

The feature layers an explicit draft -> estimate -> confirm boundary over the
existing verified Audio Asset Operations executor.  Tests use a fixed in
process substitute after startup; no host FFmpeg, provider, Bot, payment or
wallet path can run here.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app",
    "copyfast_api",
    "copyfast_assets",
    "copyfast_audio_asset_operations",
    "copyfast_audio_change_requests",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_db",
    "copyfast_document_operations",
    "copyfast_image_operations",
    "copyfast_media_runtime",
    "copyfast_music_media",
    "copyfast_native_read_models",
    "copyfast_project_packages",
    "copyfast_registry",
    "copyfast_subtitle_asset_operations",
    "copyfast_video_operations",
    "copyfast_video_transform_operations",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-audio-change-request-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-audio-change-request-session-secret")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "2")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "20")
    monkeypatch.setenv("WEBAPP_AUDIO_CHANGE_REQUESTS_ENABLED", "true")
    # Runtime execution remains disabled while the ASGI lifespan starts.
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT", str(tmp_path / "private-audio-outputs"))
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_QUOTA_MB", "24")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED", "false")
    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL",
        "CORE_BRIDGE_TOKEN",
        "CORE_BRIDGE_HMAC_SECRET",
        "WEBAPP_AUDIO_ASSET_OPERATIONS_TOPOLOGY",
        "RAILWAY_REPLICA_COUNT",
        "RAILWAY_REPLICAS",
        "WEBAPP_REPLICA_COUNT",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str, *, display_name: str = "Audio Change Owner") -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": display_name},
    )
    assert registered.status_code == 200
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["data"]["csrf_token"]


def mp3_bytes(marker: bytes = b"source") -> bytes:
    return b"ID3\x04\x00\x00" + marker + (b"\x00" * 1024)


def upload_mp3(client: TestClient, csrf: str, *, key: str, marker: bytes = b"source") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Audio change source"},
        files={"file": ("source.mp3", mp3_bytes(marker), "audio/mpeg")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def create_collection(client: TestClient, csrf: str) -> dict:
    response = client.post(
        "/api/v1/media-workspace/collections",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Collection Audio Change Request",
            "description": "Kiểm tra thao tác audio private theo hai bước.",
            "creative_brief": "Nhạc nền nguyên bản, rõ lời đọc và nhịp ổn định.",
            "prompt_mode": "background",
            "use_context": "video giới thiệu sản phẩm",
            "tags": ["audio", "review"],
            "rights_note": "Tôi xác nhận có quyền sử dụng các tệp và brief trong collection này.",
            "project_id": "",
            "idempotency_key": "audio-change-collection-create-0001",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["collection"]


def attach(client: TestClient, csrf: str, *, collection: dict, asset: dict) -> dict:
    response = client.post(
        f"/api/v1/media-workspace/collections/{collection['id']}/items",
        headers={"X-CSRF-Token": csrf},
        json={
            "asset_id": asset["id"],
            "expected_revision": collection["revision"],
            "idempotency_key": "audio-change-attachment-0001",
            "role": "music",
            "title_override": "Audio source",
            "attribution": "",
            "license_note": "Tôi chịu trách nhiệm kiểm tra license và quyền thương mại trước khi đăng.",
            "tags": ["source"],
            "favorite": False,
            "user_declared_duration_seconds": 10,
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def activate_audio_runtime(monkeypatch):
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
    monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")
    module = importlib.import_module("copyfast_audio_asset_operations")
    monkeypatch.setattr(module, "_audio_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))
    render_calls: list[dict[str, object]] = []

    def fake_probe(_ffprobe: str, path: Path) -> dict[str, object]:
        if path.suffix.lower() == ".m4a":
            return {
                "duration_seconds": 2.0,
                "duration_ms": 2000,
                "channels": 2,
                "sample_rate": 48000,
                "codec": "aac",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            }
        return {
            "duration_seconds": 2.0,
            "duration_ms": 2000,
            "channels": 2,
            "sample_rate": 48000,
            "codec": "mp3",
            "format_name": "mp3",
        }

    def fake_render(_ffmpeg: str, source: Path, destination: Path, *, target_format: str, normalize: bool) -> None:
        assert source.suffix == ".mp3"
        render_calls.append({"target_format": target_format, "normalize": normalize})
        if target_format == "m4a":
            destination.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2" + (b"\x00" * 256))
        else:
            destination.write_bytes(mp3_bytes(b"rendered"))

    monkeypatch.setattr(module, "_probe_audio", fake_probe)
    monkeypatch.setattr(module, "_render_audio", fake_render)
    return render_calls


def test_audio_change_request_is_csrf_owner_scoped_and_requires_explicit_confirm(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/audio-change-requests/drafts").status_code == 401
        oversized = client.post(
            "/api/v1/audio-change-requests/drafts",
            headers={"Content-Type": "application/json"},
            content=b'{"unused":"' + (b"x" * (16 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_AUDIO_CHANGE_REQUEST_BODY_TOO_LARGE"
        csrf = register_and_login(client, "audio-change-owner@example.com")
        collection = create_collection(client, csrf)
        asset = upload_mp3(client, csrf, key="audio-change-source-0001")
        attachment = attach(client, csrf, collection=collection, asset=asset)

        draft_payload = {
            "collection_id": collection["id"],
            "item_id": attachment["item_id"],
            "operation": "convert_mp3",
            "idempotency_key": "audio-change-draft-0001",
        }
        denied = client.post("/api/v1/audio-change-requests/drafts", json=draft_payload)
        assert denied.status_code == 403

        draft = client.post(
            "/api/v1/audio-change-requests/drafts",
            headers={"X-CSRF-Token": csrf},
            json=draft_payload,
        )
        assert draft.status_code == 200
        assert draft.json()["ok"] is True
        request = draft.json()["data"]["request"]
        assert draft.json()["status"] == "draft"
        assert request["state"] == "draft"
        assert request["operation"] == "convert_mp3"
        for forbidden in ("source_asset_id", "sha256", "storage_key", "wallet", "payos", "provider", "telegram"):
            assert forbidden not in draft.text.lower()

        render_calls = activate_audio_runtime(monkeypatch)
        estimate_payload = {
            "expected_revision": request["revision"],
            "idempotency_key": "audio-change-estimate-0001",
        }
        estimate = client.post(
            f"/api/v1/audio-change-requests/drafts/{request['id']}/estimate",
            headers={"X-CSRF-Token": csrf},
            json=estimate_payload,
        )
        assert estimate.status_code == 200
        assert estimate.json()["ok"] is True
        assert estimate.json()["status"] == "awaiting_confirm"
        estimated = estimate.json()["data"]["request"]
        assert estimated["state"] == "awaiting_confirm"
        assert estimated["requires_confirmation"] is True
        assert estimated["plan"]["target_format"] == "mp3"
        assert render_calls == []
        assert all(key not in estimate.text.lower() for key in ("price", "xu", "wallet", "payos", "eta", "provider"))

        replay_estimate = client.post(
            f"/api/v1/audio-change-requests/drafts/{request['id']}/estimate",
            headers={"X-CSRF-Token": csrf},
            json=estimate_payload,
        )
        assert replay_estimate.status_code == 200
        assert replay_estimate.json() == estimate.json()
        assert render_calls == []

        confirm_payload = {
            "expected_revision": estimated["revision"],
            "confirm": True,
            "idempotency_key": "audio-change-confirm-0001",
        }
        confirmed = client.post(
            f"/api/v1/audio-change-requests/drafts/{request['id']}/confirm",
            headers={"X-CSRF-Token": csrf},
            json=confirm_payload,
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["ok"] is True
        assert confirmed.json()["status"] == "completed"
        confirmed_request = confirmed.json()["data"]["request"]
        assert confirmed_request["state"] == "completed"
        assert confirmed_request["operation"]["output_available"] is True
        assert render_calls == [{"target_format": "mp3", "normalize": False}]

        replay_confirm = client.post(
            f"/api/v1/audio-change-requests/drafts/{request['id']}/confirm",
            headers={"X-CSRF-Token": csrf},
            json=confirm_payload,
        )
        assert replay_confirm.status_code == 200
        assert replay_confirm.json() == confirmed.json()
        assert len(render_calls) == 1

        listed = client.get("/api/v1/audio-change-requests/drafts", params={"collection_id": collection["id"]})
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["data"]["requests"]] == [request["id"]]

        with TestClient(client.app) as other:
            other_csrf = register_and_login(other, "audio-change-other@example.com", display_name="Other")
            hidden = other.get(f"/api/v1/audio-change-requests/drafts/{request['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_AUDIO_CHANGE_REQUEST_NOT_FOUND"
            foreign = other.post(
                "/api/v1/audio-change-requests/drafts",
                headers={"X-CSRF-Token": other_csrf},
                json={**draft_payload, "idempotency_key": "audio-change-other-draft-0001"},
            )
            assert foreign.status_code == 200
            assert foreign.json()["error_code"] == "WEB_AUDIO_CHANGE_REQUEST_SOURCE_GUARDED"


def test_audio_change_request_guards_collection_revision_before_executor_runs(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-change-race@example.com")
        collection = create_collection(client, csrf)
        asset = upload_mp3(client, csrf, key="audio-change-race-source-0001")
        attachment = attach(client, csrf, collection=collection, asset=asset)
        draft = client.post(
            "/api/v1/audio-change-requests/drafts",
            headers={"X-CSRF-Token": csrf},
            json={
                "collection_id": collection["id"],
                "item_id": attachment["item_id"],
                "operation": "normalize",
                "idempotency_key": "audio-change-race-draft-0001",
            },
        )
        assert draft.status_code == 200
        request = draft.json()["data"]["request"]
        render_calls = activate_audio_runtime(monkeypatch)

        archived = client.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": attachment["revision"], "idempotency_key": "audio-change-race-archive-0001"},
        )
        assert archived.status_code == 200

        guarded = client.post(
            f"/api/v1/audio-change-requests/drafts/{request['id']}/estimate",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": request["revision"], "idempotency_key": "audio-change-race-estimate-0001"},
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_AUDIO_CHANGE_REQUEST_SOURCE_CHANGED"
        assert render_calls == []


def test_audio_change_request_history_does_not_block_detach_and_later_guards(tmp_path, monkeypatch):
    """A mutable collection item must not become undeletable because of history.

    The request owns an immutable snapshot.  Detaching the source remains a
    normal Media Workspace action; a later lifecycle transition must fail
    closed before the Audio Asset Operations executor can run.
    """
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-change-detach@example.com")
        collection = create_collection(client, csrf)
        asset = upload_mp3(client, csrf, key="audio-change-detach-source-0001")
        attachment = attach(client, csrf, collection=collection, asset=asset)
        draft = client.post(
            "/api/v1/audio-change-requests/drafts",
            headers={"X-CSRF-Token": csrf},
            json={
                "collection_id": collection["id"],
                "item_id": attachment["item_id"],
                "operation": "convert_m4a",
                "idempotency_key": "audio-change-detach-draft-0001",
            },
        )
        assert draft.status_code == 200
        request = draft.json()["data"]["request"]

        render_calls = activate_audio_runtime(monkeypatch)
        estimated = client.post(
            f"/api/v1/audio-change-requests/drafts/{request['id']}/estimate",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": request["revision"],
                "idempotency_key": "audio-change-detach-estimate-0001",
            },
        )
        assert estimated.status_code == 200
        assert estimated.json()["status"] == "awaiting_confirm"
        estimated_request = estimated.json()["data"]["request"]
        assert render_calls == []

        detached = client.post(
            f"/api/v1/media-workspace/collections/{collection['id']}/items/{attachment['item_id']}/detach",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": attachment["revision"],
                "idempotency_key": "audio-change-detach-item-0001",
                "confirm": True,
            },
        )
        assert detached.status_code == 200
        assert detached.json()["ok"] is True

        guarded = client.post(
            f"/api/v1/audio-change-requests/drafts/{request['id']}/confirm",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": estimated_request["revision"],
                "confirm": True,
                "idempotency_key": "audio-change-detach-confirm-0001",
            },
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_AUDIO_CHANGE_REQUEST_SOURCE_GUARDED"
        assert render_calls == []
