"""Focused high-risk contracts for private Web-native Audio Asset Operations.

The runtime never executes a host FFmpeg/ffprobe in these tests.  A fixed
server-side substitute is injected only after application startup, so the
optional feature remains false-by-default and tests cannot accidentally invoke
an external binary, provider, Bot, wallet or payment flow.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app",
    "copyfast_api",
    "copyfast_assets",
    "copyfast_audio_asset_operations",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_db",
    "copyfast_document_operations",
    "copyfast_frame_video_operations",
    "copyfast_image_operations",
    "copyfast_media_runtime",
    "copyfast_native_read_models",
    "copyfast_project_packages",
    "copyfast_registry",
    "copyfast_subtitle_asset_operations",
    "copyfast_video_operations",
    "copyfast_video_transform_operations",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-audio-asset-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-audio-asset-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "2")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "20")
    # Audio execution stays off while the ASGI lifespan starts.  Individual
    # tests turn it on only after injecting a fixed in-process fake runtime.
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


def register_and_login(client: TestClient, email: str, *, display_name: str = "Audio Owner") -> str:
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
    # Asset Vault validates MP3 magic.  Metadata parsing is separately mocked
    # below, so this remains a harmless deterministic fixture rather than an
    # attempt to execute or decode user media in the test process.
    return b"ID3\x04\x00\x00" + marker + (b"\x00" * 1024)


def upload_mp3(client: TestClient, csrf: str, *, key: str, marker: bytes = b"source") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Audio nguồn riêng tư"},
        files={"file": ("source.mp3", mp3_bytes(marker), "audio/mpeg")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def inspect(client: TestClient, csrf: str, *, asset_id: str, key: str):
    return client.post(
        "/api/v1/audio-asset-operations/inspect",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "idempotency_key": key},
    )


def convert(client: TestClient, csrf: str, *, asset_id: str, target_format: str, key: str):
    return client.post(
        "/api/v1/audio-asset-operations/convert",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "target_format": target_format, "idempotency_key": key},
    )


def activate_audio_runtime(monkeypatch):
    """Enable the optional feature with a deterministic no-process substitute."""

    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
    monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")
    module = importlib.import_module("copyfast_audio_asset_operations")
    monkeypatch.setattr(module, "_audio_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))
    render_calls: list[dict[str, object]] = []

    def fake_probe(_ffprobe: str, path: Path) -> dict[str, object]:
        suffix = path.suffix.lower()
        if suffix == ".m4a":
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

    def fake_render(
        _ffmpeg: str,
        source: Path,
        destination: Path,
        *,
        target_format: str,
        normalize: bool,
    ) -> None:
        assert source.suffix == ".mp3"
        render_calls.append({"target_format": target_format, "normalize": normalize})
        if target_format == "m4a":
            destination.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2" + (b"\x00" * 256))
        else:
            destination.write_bytes(mp3_bytes(b"rendered"))

    monkeypatch.setattr(module, "_probe_audio", fake_probe)
    monkeypatch.setattr(module, "_render_audio", fake_render)
    return module, render_calls


def test_audio_asset_operations_are_false_by_default_and_raw_body_is_bounded(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-disabled@example.com")
        source = upload_mp3(client, csrf, key="audio-disabled-source-0001")

        disabled = inspect(client, csrf, asset_id=source["id"], key="audio-disabled-inspect-0001")
        assert disabled.status_code == 503

        oversized = client.post(
            "/api/v1/audio-asset-operations/inspect",
            headers={"Content-Type": "application/json"},
            content=b'{"unused":"' + (b"x" * (16 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_AUDIO_ASSET_OPERATION_BODY_TOO_LARGE"
        assert oversized.headers["cross-origin-resource-policy"] == "same-origin"


def test_audio_asset_operations_require_attested_single_replica_topology(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-topology@example.com")
        source = upload_mp3(client, csrf, key="audio-topology-source-0001")
        monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "true")
        module = importlib.import_module("copyfast_audio_asset_operations")
        monkeypatch.setattr(module, "_audio_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))

        no_topology = inspect(client, csrf, asset_id=source["id"], key="audio-topology-inspect-0001")
        assert no_topology.status_code == 503
        monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
        no_replica_attestation = inspect(client, csrf, asset_id=source["id"], key="audio-topology-inspect-0002")
        assert no_replica_attestation.status_code == 503
        monkeypatch.setenv("RAILWAY_REPLICA_COUNT", "2")
        many_replicas = inspect(client, csrf, asset_id=source["id"], key="audio-topology-inspect-0003")
        assert many_replicas.status_code == 503


def test_audio_inspect_requires_csrf_is_owner_scoped_and_never_creates_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-owner@example.com")
        source = upload_mp3(client, csrf, key="audio-owner-source-0001")
        module, render_calls = activate_audio_runtime(monkeypatch)

        denied = client.post(
            "/api/v1/audio-asset-operations/inspect",
            json={"source_asset_id": source["id"], "idempotency_key": "audio-owner-denied-0001"},
        )
        assert denied.status_code == 403

        created = inspect(client, csrf, asset_id=source["id"], key="audio-owner-inspect-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True and payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == module.AUDIO_INSPECT_KIND
        assert operation["state"] == "completed"
        assert operation["output_available"] is False
        assert operation["filename"] is None
        assert operation["content_type"] is None
        assert render_calls == []
        for forbidden in ("source_asset_id", "storage_key", "sha256", "provider", "payos", "wallet", "telegram"):
            assert forbidden not in created.text.lower()

        replay = inspect(client, csrf, asset_id=source["id"], key="audio-owner-inspect-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["replay"] is True
        assert replay.json()["data"]["operation"]["id"] == operation["id"]

        alternate = upload_mp3(client, csrf, key="audio-owner-source-0002", marker=b"alternate")
        conflict = inspect(client, csrf, asset_id=alternate["id"], key="audio-owner-inspect-0001")
        assert conflict.status_code == 409

        detail = client.get(f"/api/v1/audio-asset-operations/{operation['id']}")
        assert detail.status_code == 200
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        unavailable = client.get(f"/api/v1/audio-asset-operations/{operation['id']}/download")
        assert unavailable.status_code == 200
        assert unavailable.json()["error_code"] == "WEB_AUDIO_ASSET_OUTPUT_UNAVAILABLE"

        # A separate signed Web account must neither read the receipt nor use
        # the owner's Asset Vault UUID as a source.
        with TestClient(client.app) as other:
            other_csrf = register_and_login(other, "audio-other@example.com", display_name="Other Audio User")
            hidden = other.get(f"/api/v1/audio-asset-operations/{operation['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_AUDIO_ASSET_OPERATION_NOT_FOUND"
            rejected = inspect(other, other_csrf, asset_id=source["id"], key="audio-other-inspect-0001")
            assert rejected.status_code == 422


def test_audio_transform_rechecks_private_output_before_download_and_after_tamper(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-transform@example.com")
        source = upload_mp3(client, csrf, key="audio-transform-source-0001")
        module, render_calls = activate_audio_runtime(monkeypatch)

        created = convert(
            client,
            csrf,
            asset_id=source["id"],
            target_format="mp3",
            key="audio-transform-convert-0001",
        )
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True and payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == module.AUDIO_CONVERT_KIND
        assert operation["output_available"] is True
        assert operation["content_type"] == "audio/mpeg"
        assert operation["output_codec"] == "mp3"
        assert render_calls == [{"target_format": "mp3", "normalize": False}]

        replay = convert(
            client,
            csrf,
            asset_id=source["id"],
            target_format="mp3",
            key="audio-transform-convert-0001",
        )
        assert replay.status_code == 200 and replay.json()["data"]["replay"] is True
        assert len(render_calls) == 1

        downloaded = client.get(f"/api/v1/audio-asset-operations/{operation['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("audio/mpeg")
        assert downloaded.headers["cache-control"] == "no-store, private"
        assert downloaded.headers["x-content-type-options"] == "nosniff"
        assert downloaded.headers["referrer-policy"] == "no-referrer"
        assert downloaded.headers["content-security-policy"] == "sandbox"
        assert downloaded.headers["cross-origin-resource-policy"] == "same-origin"
        assert "attachment" in downloaded.headers["content-disposition"]
        assert downloaded.content.startswith(b"ID3")

        database = tmp_path / "copyfast-audio-asset-test.db"
        with sqlite3.connect(database) as conn:
            row = conn.execute(
                "SELECT storage_key FROM web_audio_asset_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()
        assert row and str(row[0]).endswith(".mp3")
        private_output = tmp_path / "private-audio-outputs" / str(row[0])
        private_output.write_bytes(b"ID3tampered-private-output")

        # A read model may retain the completed receipt, but it must not
        # advertise a modified blob as available.  Delivery then records the
        # durable unavailable state instead of serving the stale file.
        stale_detail = client.get(f"/api/v1/audio-asset-operations/{operation['id']}")
        stale_operation = stale_detail.json()["data"]["operation"]
        assert stale_operation["state"] == "completed"
        assert stale_operation["output_available"] is False
        blocked = client.get(f"/api/v1/audio-asset-operations/{operation['id']}/download")
        assert blocked.status_code == 200
        assert blocked.json()["error_code"] == "WEB_AUDIO_ASSET_OUTPUT_UNAVAILABLE"
        final_detail = client.get(f"/api/v1/audio-asset-operations/{operation['id']}")
        assert final_detail.json()["data"]["operation"]["state"] == "unavailable"
