"""High-risk contracts for private Web-native Frame Video Lab."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_media_runtime", "copyfast_video_operations", "copyfast_frame_video_operations",
    "copyfast_native_read_models", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-frame-video-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-frame-video-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "25")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    # Start disabled so application lifespan never needs a host FFmpeg. Tests
    # explicitly enable the feature only after startup and inject a fixed fake
    # binary contract for the small number of media calls under test.
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT", str(tmp_path / "private-frame-video-outputs"))
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_MAX_OUTPUT_MB", "25")
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_QUOTA_MB", "50")
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    for name in (
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET", "APP_ENV", "ENVIRONMENT",
        "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH", "WEBAPP_FRAME_VIDEO_OPERATIONS_TOPOLOGY",
        "WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", "RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Frame Video Owner"},
    )
    assert registration.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def image_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (640, 360), color)
    buffer = BytesIO()
    try:
        image.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()
    finally:
        image.close()
        buffer.close()


def upload_image(client: TestClient, csrf: str, *, key: str, color: tuple[int, int, int]) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Ảnh Frame Video private"},
        files={"file": ("source.jpg", image_bytes(color), "image/jpeg")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def activate_frame_runtime(monkeypatch):
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
    monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")
    module = importlib.import_module("copyfast_frame_video_operations")
    monkeypatch.setattr(module, "_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))
    commands: list[tuple[list[str], dict]] = []
    probe_stdout = (
        b'{"format":{"duration":"3.0"},'
        b'"streams":[{"codec_type":"video","codec_name":"h264","width":720,"height":1280}]}'
    )

    def fake_run(command, **kwargs):
        commands.append((list(command), dict(kwargs)))
        if command[0] == "trusted-ffprobe":
            return SimpleNamespace(returncode=0, stdout=probe_stdout)
        assert command[0] == "trusted-ffmpeg"
        output = Path(command[-1])
        # ffprobe is itself under test as a fixed trusted command. The fake
        # executable supplies a bounded ISO-BMFF marker rather than pretending
        # to parse user data or invoke a real provider/runtime.
        output.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2avc1" + (b"\x00" * 512))
        return SimpleNamespace(returncode=0, stdout=b"")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return module, commands


def create_frame_video(client: TestClient, csrf: str, *, asset_ids: list[str], key: str, effect: str = "random"):
    return client.post(
        "/api/v1/frame-video-operations",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_ids": asset_ids,
            "aspect_ratio": "9:16",
            "seconds_per_image": 1.5,
            "effect": effect,
            "idempotency_key": key,
        },
    )


def test_frame_video_is_false_by_default_and_body_is_bounded(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "frame-disabled@example.com")
        first = upload_image(client, csrf, key="frame-disabled-source-0001", color=(60, 100, 160))
        second = upload_image(client, csrf, key="frame-disabled-source-0002", color=(160, 100, 60))
        disabled = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-disabled-create-0001")
        assert disabled.status_code == 503

        oversized = client.post(
            "/api/v1/frame-video-operations",
            headers={"Content-Type": "application/json"},
            content=b'{"unused":"' + (b"x" * (16 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_FRAME_VIDEO_OPERATION_BODY_TOO_LARGE"
        assert oversized.headers["cross-origin-resource-policy"] == "same-origin"


def test_frame_video_requires_attested_single_replica_topology(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "frame-topology@example.com")
        first = upload_image(client, csrf, key="frame-topology-source-0001", color=(45, 100, 130))
        second = upload_image(client, csrf, key="frame-topology-source-0002", color=(130, 100, 45))
        monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "true")
        module = importlib.import_module("copyfast_frame_video_operations")
        monkeypatch.setattr(module, "_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))

        no_topology = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-topology-create-0001")
        assert no_topology.status_code == 503
        monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
        missing_replica = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-topology-create-0002")
        assert missing_replica.status_code == 503
        monkeypatch.setenv("RAILWAY_REPLICA_COUNT", "2")
        many_replicas = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-topology-create-0003")
        assert many_replicas.status_code == 503


def test_frame_video_generates_verified_private_mp4_idempotently_and_projects_generic_jobs(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "frame-owner@example.com")
        first = upload_image(client, csrf, key="frame-owner-source-0001", color=(30, 110, 190))
        second = upload_image(client, csrf, key="frame-owner-source-0002", color=(190, 110, 30))
        module, commands = activate_frame_runtime(monkeypatch)

        created = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-owner-create-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True and payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "frame_video"
        assert operation["state"] == "completed"
        assert operation["source_count"] == 2
        assert operation["output"]["content_type"] == "video/mp4"
        assert operation["output"]["width"] == 720 and operation["output"]["height"] == 1280
        assert operation["output"]["duration_ms"] == 3000
        assert operation["effective_effect"] in {"none", "fade", "zoom", "pan", "slide"}
        for forbidden in ("storage_key", "sha256", "provider", "payos", "wallet", "telegram"):
            assert forbidden not in created.text.lower()

        ffmpeg_commands = [entry for entry in commands if entry[0][0] == "trusted-ffmpeg"]
        assert len(ffmpeg_commands) == 1
        command, kwargs = ffmpeg_commands[0]
        assert command[:7] == ["trusted-ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-xerror", "-protocol_whitelist"]
        assert "-an" in command and "-c:v" in command and "libx264" in command
        assert "concat=n=2:v=1:a=0" in command[command.index("-filter_complex") + 1]
        assert kwargs["shell"] is False and kwargs["timeout"] == 60.0
        assert first["id"] not in " ".join(command) and second["id"] not in " ".join(command)

        before_replay = len(ffmpeg_commands)
        replay = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-owner-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["replay"] is True
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        assert len([entry for entry in commands if entry[0][0] == "trusted-ffmpeg"]) == before_replay
        conflict = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-owner-create-0001", effect="fade")
        assert conflict.status_code == 409

        direct = client.get(f"/api/v1/frame-video-operations/{operation['id']}/download")
        assert direct.status_code == 200
        assert direct.headers["content-type"].startswith("video/mp4")
        assert direct.headers["cache-control"] == "no-store, private"
        assert direct.headers["referrer-policy"] == "no-referrer"
        assert direct.headers["content-security-policy"] == "sandbox"
        assert direct.headers["cross-origin-resource-policy"] == "same-origin"
        assert direct.content[4:8] == b"ftyp"

        from copyfast_db import transaction
        from copyfast_native_read_models import encode_native_job_id, list_native_jobs

        opaque = encode_native_job_id("frame-video-operation", operation["id"])
        generic = client.get(f"/api/v1/assets/{opaque}/download")
        assert generic.status_code == 200
        assert generic.content == direct.content
        assert generic.headers["cache-control"] == "no-store, private"
        with transaction() as conn:
            account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", ("frame-owner@example.com",)).fetchone()[0]
        jobs = list_native_jobs(str(account_id))
        assert any(job["id"] == opaque for job in jobs)

        # Poster and Frame Video have independent route/data contracts, but
        # one process-wide FFmpeg gate prevents dual local execution.
        import copyfast_video_operations
        from copyfast_media_runtime import media_ffmpeg_capacity

        assert module.media_ffmpeg_capacity() is media_ffmpeg_capacity()
        assert copyfast_video_operations._PROCESS_GATE is media_ffmpeg_capacity()


def test_frame_video_rejects_foreign_or_duplicate_sources_and_tampered_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "frame-security-owner@example.com")
        first = upload_image(client, csrf, key="frame-security-source-0001", color=(30, 70, 160))
        second = upload_image(client, csrf, key="frame-security-source-0002", color=(160, 70, 30))
        _module, _commands = activate_frame_runtime(monkeypatch)

        duplicate = create_frame_video(client, csrf, asset_ids=[first["id"], first["id"]], key="frame-security-duplicate-0001")
        assert duplicate.status_code == 422
        extra = client.post(
            "/api/v1/frame-video-operations",
            headers={"X-CSRF-Token": csrf},
            json={
                "source_asset_ids": [first["id"], second["id"]], "aspect_ratio": "9:16", "seconds_per_image": 1.5,
                "effect": "fade", "idempotency_key": "frame-security-extra-0001", "ffmpeg_args": "-unsafe",
            },
        )
        assert extra.status_code == 422

        created = create_frame_video(client, csrf, asset_ids=[first["id"], second["id"]], key="frame-security-create-0001")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]

        csrf_other = register_and_login(client, "frame-security-other@example.com")
        foreign_create = create_frame_video(client, csrf_other, asset_ids=[first["id"], second["id"]], key="frame-security-foreign-0001")
        assert foreign_create.status_code == 200
        assert foreign_create.json()["error_code"] == "FRAME_VIDEO_SOURCE_UNAVAILABLE"
        foreign_download = client.get(f"/api/v1/frame-video-operations/{operation['id']}/download")
        assert foreign_download.status_code == 200
        assert foreign_download.json()["error_code"] == "FRAME_VIDEO_NOT_FOUND"

        owner_login = client.post(
            "/api/v1/auth/login",
            json={"email": "frame-security-owner@example.com", "password": "correct-horse-battery-staple"},
        )
        assert owner_login.status_code == 200

        from copyfast_db import transaction

        with transaction() as conn:
            storage_key = conn.execute(
                "SELECT storage_key FROM web_frame_video_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
        output_path = tmp_path / "private-frame-video-outputs" / str(storage_key)
        output_path.write_bytes(b"not-an-mp4")
        rejected = client.get(f"/api/v1/frame-video-operations/{operation['id']}/download")
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "unavailable"
        assert rejected.json()["error_code"] == "FRAME_VIDEO_OUTPUT_UNAVAILABLE"
