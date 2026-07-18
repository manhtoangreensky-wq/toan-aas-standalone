"""High-risk contracts for private Web-native Video Finishing operations."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_media_runtime", "copyfast_video_operations", "copyfast_frame_video_operations",
    "copyfast_video_transform_operations", "copyfast_native_read_models", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-video-transform-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-video-transform-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "25")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    # Keep all FFmpeg-backed work false by default so startup never needs a
    # host runtime. Individual tests enable only this module after startup.
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT", str(tmp_path / "private-video-transform-outputs"))
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_MAX_OUTPUT_MB", "25")
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_QUOTA_MB", "50")
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    for name in (
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET", "APP_ENV", "ENVIRONMENT",
        "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH", "WEBAPP_VIDEO_TRANSFORM_OPERATIONS_TOPOLOGY",
        "WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", "RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Video Finishing Owner"},
    )
    assert registered.status_code == 200
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["data"]["csrf_token"]


def video_bytes() -> bytes:
    # Asset Vault validates the ISO-BMFF marker.  Tests mock fixed trusted
    # ffprobe/ffmpeg rather than attempting to treat this fixture as media.
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2avc1" + (b"\x00" * 1024)


def upload_video(client: TestClient, csrf: str, *, key: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Video nguồn private"},
        files={"file": ("source.mp4", video_bytes(), "video/mp4")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def activate_transform_runtime(monkeypatch, *, source_audio: bool = True, output_audio: bool | None = None):
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
    monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")
    module = importlib.import_module("copyfast_video_transform_operations")
    monkeypatch.setattr(module, "_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))
    commands: list[tuple[list[str], dict]] = []
    output_audio = source_audio if output_audio is None else output_audio

    def probe_stdout(has_audio: bool) -> bytes:
        streams = [{
            "codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280,
            "pix_fmt": "yuv420p", "avg_frame_rate": "30/1", "r_frame_rate": "30/1",
            "disposition": {"attached_pic": 0},
        }]
        if has_audio:
            streams.append({"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"})
        return json.dumps(
            {"format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "3.0"}, "streams": streams},
            separators=(",", ":"),
        ).encode("utf-8")

    def fake_run(command, **kwargs):
        commands.append((list(command), dict(kwargs)))
        if command[0] == "trusted-ffprobe":
            is_staged_source = str(command[-1]).endswith(".source.mp4")
            return SimpleNamespace(returncode=0, stdout=probe_stdout(source_audio if is_staged_source else output_audio))
        assert command[0] == "trusted-ffmpeg"
        output = Path(command[-1])
        output.write_bytes(video_bytes())
        return SimpleNamespace(returncode=0, stdout=b"")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return module, commands


def create_transform(
    client: TestClient,
    csrf: str,
    *,
    asset_id: str,
    key: str,
    fit_mode: str = "blur_pad",
    preserve_audio: bool = True,
):
    return client.post(
        "/api/v1/video-transform-operations",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": asset_id,
            "target_ratio": "9:16",
            "fit_mode": fit_mode,
            "preset": "cinematic",
            "sharpen": True,
            "preserve_audio": preserve_audio,
            "idempotency_key": key,
        },
    )


def test_video_finishing_is_disabled_by_default_and_body_is_bounded(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "transform-disabled@example.com")
        source = upload_video(client, csrf, key="transform-disabled-source-0001")
        disabled = create_transform(client, csrf, asset_id=source["id"], key="transform-disabled-create-0001")
        assert disabled.status_code == 503

        oversized = client.post(
            "/api/v1/video-transform-operations",
            headers={"Content-Type": "application/json"},
            content=b'{"unused":"' + (b"x" * (16 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_VIDEO_TRANSFORM_OPERATION_BODY_TOO_LARGE"
        assert oversized.headers["cross-origin-resource-policy"] == "same-origin"


def test_video_finishing_requires_attested_single_replica_topology(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "transform-topology@example.com")
        source = upload_video(client, csrf, key="transform-topology-source-0001")
        monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED", "true")
        module = importlib.import_module("copyfast_video_transform_operations")
        monkeypatch.setattr(module, "_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))

        no_topology = create_transform(client, csrf, asset_id=source["id"], key="transform-topology-create-0001")
        assert no_topology.status_code == 503
        monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
        no_replica = create_transform(client, csrf, asset_id=source["id"], key="transform-topology-create-0002")
        assert no_replica.status_code == 503
        monkeypatch.setenv("RAILWAY_REPLICA_COUNT", "2")
        many_replicas = create_transform(client, csrf, asset_id=source["id"], key="transform-topology-create-0003")
        assert many_replicas.status_code == 503


def test_video_finishing_rejects_materially_short_h264_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch):
        module = importlib.import_module("copyfast_video_transform_operations")
        probe_payload = {
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "2.4"},
            "streams": [{
                "codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280,
                "pix_fmt": "yuv420p", "avg_frame_rate": "30/1", "r_frame_rate": "30/1",
            }],
        }
        monkeypatch.setattr(
            module.subprocess,
            "run",
            lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(probe_payload).encode("utf-8")),
        )
        with pytest.raises(module.VideoTransformError) as error:
            module._probe_output(
                "trusted-ffprobe",
                tmp_path / "short.mp4",
                expected_width=720,
                expected_height=1280,
                expected_duration_seconds=3.0,
                expected_audio=False,
            )
        assert error.value.code == "VIDEO_TRANSFORM_OUTPUT_INVALID"


def test_video_finishing_generates_private_mp4_idempotently_and_projects_jobs(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "transform-owner@example.com")
        source = upload_video(client, csrf, key="transform-owner-source-0001")
        module, commands = activate_transform_runtime(monkeypatch)

        created = create_transform(client, csrf, asset_id=source["id"], key="transform-owner-create-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True and payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "video_transform"
        assert operation["state"] == "completed"
        assert operation["target_ratio"] == "9:16"
        assert operation["fit_mode"] == "blur_pad"
        assert operation["output"]["content_type"] == "video/mp4"
        assert operation["output"]["width"] == 720 and operation["output"]["height"] == 1280
        assert operation["output"]["has_audio"] is True
        for forbidden in ("storage_key", "sha256", "provider", "payos", "wallet", "telegram"):
            assert forbidden not in created.text.lower()

        ffmpeg = [entry for entry in commands if entry[0][0] == "trusted-ffmpeg"]
        assert len(ffmpeg) == 1
        command, kwargs = ffmpeg[0]
        assert command[:7] == ["trusted-ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-xerror", "-threads"]
        assert "-filter_complex" in command and "gblur=sigma=20:steps=2" in command[command.index("-filter_complex") + 1]
        assert "-map" in command and "0:a:0?" in command
        assert "-sn" in command and "-dn" in command and "-map_metadata" in command
        assert command[command.index("-fs") + 1] == str(module._maximum_output_bytes())
        assert command[-1].endswith(".rendered.mp4")
        assert source["id"] not in " ".join(command)
        assert kwargs["shell"] is False and kwargs["timeout"] == 75.0

        replay = create_transform(client, csrf, asset_id=source["id"], key="transform-owner-create-0001")
        assert replay.status_code == 200 and replay.json()["data"]["replay"] is True
        assert replay.json()["data"]["operation"]["id"] == operation["id"]

        # A completed receipt stays replayable while the new-work runtime
        # gate is temporarily guarded; it must not re-render or become 503.
        monkeypatch.delenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_TOPOLOGY", raising=False)
        guarded_replay = create_transform(client, csrf, asset_id=source["id"], key="transform-owner-create-0001")
        assert guarded_replay.status_code == 200 and guarded_replay.json()["data"]["replay"] is True
        assert len([entry for entry in commands if entry[0][0] == "trusted-ffmpeg"]) == 1
        monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_TOPOLOGY", "sqlite_single_replica")

        conflict = create_transform(client, csrf, asset_id=source["id"], key="transform-owner-create-0001", fit_mode="crop")
        assert conflict.status_code == 409

        download_events: list[str] = []
        reserve_download = module._reserve_download_capacity
        verify_output = module._verify_mp4_output

        def observed_reserve():
            download_events.append("reserve")
            return reserve_download()

        def observed_verify(*args, **kwargs):
            download_events.append("verify")
            return verify_output(*args, **kwargs)

        monkeypatch.setattr(module, "_reserve_download_capacity", observed_reserve)
        monkeypatch.setattr(module, "_verify_mp4_output", observed_verify)
        direct = client.get(f"/api/v1/video-transform-operations/{operation['id']}/download")
        assert direct.status_code == 200
        assert download_events[:2] == ["reserve", "verify"]
        assert direct.content[4:8] == b"ftyp"
        assert direct.headers["cache-control"] == "no-store, private"
        assert direct.headers["referrer-policy"] == "no-referrer"
        assert direct.headers["content-security-policy"] == "sandbox"
        assert direct.headers["cross-origin-resource-policy"] == "same-origin"

        from copyfast_native_read_models import encode_native_job_id, list_native_jobs
        from copyfast_db import transaction
        from copyfast_media_runtime import media_ffmpeg_capacity
        import copyfast_video_operations
        import copyfast_frame_video_operations

        opaque = encode_native_job_id("video-transform-operation", operation["id"])
        generic = client.get(f"/api/v1/assets/{opaque}/download")
        assert generic.status_code == 200 and generic.content == direct.content
        assert generic.headers["cache-control"] == "no-store, private"
        with transaction() as conn:
            account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", ("transform-owner@example.com",)).fetchone()[0]
        assert any(job["id"] == opaque for job in list_native_jobs(str(account_id)))
        assert module.media_ffmpeg_capacity() is media_ffmpeg_capacity()
        assert copyfast_video_operations._PROCESS_GATE is media_ffmpeg_capacity()
        assert copyfast_frame_video_operations.media_ffmpeg_capacity() is media_ffmpeg_capacity()


def test_video_finishing_explicitly_mutes_instead_of_copying_source_audio(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "transform-mute@example.com")
        source = upload_video(client, csrf, key="transform-mute-source-0001")
        _module, commands = activate_transform_runtime(monkeypatch, source_audio=True, output_audio=False)
        muted = create_transform(
            client,
            csrf,
            asset_id=source["id"],
            key="transform-mute-create-0001",
            preserve_audio=False,
        )
        assert muted.status_code == 200
        operation = muted.json()["data"]["operation"]
        assert operation["output"]["has_audio"] is False
        command = next(command for command, _kwargs in commands if command[0] == "trusted-ffmpeg")
        assert "-an" in command
        assert "0:a:0?" not in command


def test_video_finishing_rejects_unsafe_inputs_foreign_sources_and_tampered_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "transform-security-owner@example.com")
        source = upload_video(client, csrf, key="transform-security-source-0001")
        module, _commands = activate_transform_runtime(monkeypatch)

        extra = client.post(
            "/api/v1/video-transform-operations",
            headers={"X-CSRF-Token": csrf},
            json={
                "source_asset_id": source["id"], "target_ratio": "9:16", "fit_mode": "crop", "preset": "none",
                "sharpen": False, "preserve_audio": False, "idempotency_key": "transform-security-extra-0001",
                "filter_complex": "movie=/etc/passwd",
            },
        )
        assert extra.status_code == 422
        created = create_transform(client, csrf, asset_id=source["id"], key="transform-security-create-0001")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]

        csrf_other = register_and_login(client, "transform-security-other@example.com")
        foreign = create_transform(client, csrf_other, asset_id=source["id"], key="transform-security-foreign-0001")
        assert foreign.status_code == 200 and foreign.json()["error_code"] == "VIDEO_TRANSFORM_SOURCE_UNAVAILABLE"
        foreign_download = client.get(f"/api/v1/video-transform-operations/{operation['id']}/download")
        assert foreign_download.status_code == 200 and foreign_download.json()["error_code"] == "VIDEO_TRANSFORM_NOT_FOUND"

        owner_login = client.post(
            "/api/v1/auth/login",
            json={"email": "transform-security-owner@example.com", "password": "correct-horse-battery-staple"},
        )
        assert owner_login.status_code == 200
        from copyfast_db import transaction
        with transaction() as conn:
            storage_key = conn.execute(
                "SELECT storage_key FROM web_video_transform_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
        output_path = tmp_path / "private-video-transform-outputs" / str(storage_key)

        original_verify = module._verify_mp4_output

        def temporary_probe_outage(*_args, **_kwargs):
            raise module.VideoTransformError(
                "Runtime kiểm tra tạm thời không sẵn sàng",
                code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE",
            )

        monkeypatch.setattr(module, "_verify_mp4_output", temporary_probe_outage)
        transient = client.get(f"/api/v1/video-transform-operations/{operation['id']}/download")
        assert transient.status_code == 503
        assert output_path.is_file()
        with transaction() as conn:
            assert conn.execute(
                "SELECT state FROM web_video_transform_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0] == "completed"
        monkeypatch.setattr(module, "_verify_mp4_output", original_verify)

        def temporary_policy_limit(*_args, **_kwargs):
            raise module.VideoTransformError(
                "Vượt policy dung lượng hiện tại",
                code="VIDEO_TRANSFORM_OUTPUT_LIMIT",
            )

        monkeypatch.setattr(module, "_verify_mp4_output", temporary_policy_limit)
        policy_guard = client.get(f"/api/v1/video-transform-operations/{operation['id']}/download")
        assert policy_guard.status_code == 200
        assert policy_guard.json()["error_code"] == "VIDEO_TRANSFORM_OUTPUT_LIMIT"
        assert output_path.is_file()
        with transaction() as conn:
            assert conn.execute(
                "SELECT state FROM web_video_transform_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0] == "completed"
        monkeypatch.setattr(module, "_verify_mp4_output", original_verify)

        # Receipt mismatch must win over a smaller current policy cap: this
        # is tampering, not a legitimate historical artifact to retain.
        monkeypatch.setattr(module, "_maximum_output_bytes", lambda: 128)
        output_path.write_bytes(video_bytes() + b"tampered")
        rejected = client.get(f"/api/v1/video-transform-operations/{operation['id']}/download")
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "unavailable"
        assert rejected.json()["error_code"] == "VIDEO_TRANSFORM_OUTPUT_UNAVAILABLE"
