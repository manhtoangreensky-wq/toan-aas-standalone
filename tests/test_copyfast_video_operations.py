"""High-risk contracts for bounded, private Web-native Video Poster work."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
from PIL import Image
import pytest


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_video_operations", "copyfast_native_read_models", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-video-operations-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-video-operations-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "25")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    # Start disabled so the app startup check never depends on a developer's
    # locally installed FFmpeg. Individual tests enable only the operation
    # after the test client has started, then provide a sealed fake runtime.
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ROOT", str(tmp_path / "private-video-outputs"))
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_MAX_OUTPUT_MB", "4")
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_QUOTA_MB", "50")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.delenv("WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", raising=False)
    monkeypatch.delenv("RAILWAY_REPLICA_COUNT", raising=False)
    monkeypatch.delenv("RAILWAY_REPLICAS", raising=False)
    monkeypatch.delenv("WEBAPP_REPLICA_COUNT", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Video Poster Owner"},
    )
    assert registration.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def video_bytes() -> bytes:
    # Asset Vault validates the fixed ISO-BMFF marker before any poster code
    # runs. ffprobe itself is mocked in tests; no fake media parser is used.
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2avc1" + (b"\x00" * 512)


def upload_video(client: TestClient, csrf: str, *, key: str, name: str = "source.mp4") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Video nguồn private"},
        files={"file": (name, video_bytes(), "video/mp4")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def activate_video_runtime(monkeypatch, *, failure: str | None = None):
    """Enable a deterministic fake FFmpeg/ffprobe pair after app startup."""

    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
    monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")
    module = importlib.import_module("copyfast_video_operations")
    monkeypatch.setattr(module, "_poster_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))
    commands: list[tuple[list[str], dict]] = []
    probe_stdout = (
        b'{"format":{"duration":"9.0"},'
        b'"streams":[{"codec_type":"video","width":1080,"height":1920}]}'
    )

    def fake_run(command, **kwargs):
        commands.append((list(command), dict(kwargs)))
        if command[0] == "trusted-ffprobe":
            if failure == "probe-timeout":
                raise subprocess.TimeoutExpired(command, kwargs.get("timeout", 0))
            if failure == "probe-failure":
                return SimpleNamespace(returncode=1, stdout=b"")
            return SimpleNamespace(returncode=0, stdout=probe_stdout)
        if failure == "render-timeout":
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout", 0))
        if failure == "render-failure":
            return SimpleNamespace(returncode=1, stdout=b"")
        output = Path(command[-1])
        image = Image.new("RGB", (720, 1280), (32, 128, 208))
        try:
            image.save(output, format="JPEG", quality=88)
        finally:
            image.close()
        return SimpleNamespace(returncode=0, stdout=b"")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return module, commands


def create_poster(client: TestClient, csrf: str, *, asset_id: str, key: str, position: str = "middle"):
    return client.post(
        "/api/v1/video-operations/poster",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "poster_position": position, "idempotency_key": key},
    )


def test_video_poster_is_false_by_default_and_raw_body_is_bounded(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-disabled@example.com")
        source = upload_video(client, csrf, key="video-disabled-source-0001")
        disabled = create_poster(client, csrf, asset_id=source["id"], key="video-disabled-create-0001")
        assert disabled.status_code == 503
        assert "video" in str(disabled.json()).lower()

        oversized = client.post(
            "/api/v1/video-operations/poster",
            headers={"Content-Type": "application/json"},
            content=b'{"unused":"' + (b"x" * (16 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_VIDEO_OPERATION_BODY_TOO_LARGE"
        assert oversized.headers["cross-origin-resource-policy"] == "same-origin"


def test_video_poster_requires_confirmed_single_replica_topology(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-topology@example.com")
        source = upload_video(client, csrf, key="video-topology-source-0001")
        monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "true")
        monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "true")
        module = importlib.import_module("copyfast_video_operations")
        monkeypatch.setattr(module, "_poster_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))

        no_topology = create_poster(client, csrf, asset_id=source["id"], key="video-topology-create-0001")
        assert no_topology.status_code == 503

        monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
        missing_replica_count = create_poster(client, csrf, asset_id=source["id"], key="video-topology-create-0002")
        assert missing_replica_count.status_code == 503

        monkeypatch.setenv("RAILWAY_REPLICA_COUNT", "2")
        multiple_replicas = create_poster(client, csrf, asset_id=source["id"], key="video-topology-create-0003")
        assert multiple_replicas.status_code == 503


def test_video_poster_generates_verified_private_jpeg_idempotently_and_is_generic_asset_safe(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-owner@example.com")
        source = upload_video(client, csrf, key="video-owner-source-0001")
        _module, commands = activate_video_runtime(monkeypatch)

        created = create_poster(client, csrf, asset_id=source["id"], key="video-owner-create-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "video_poster"
        assert operation["state"] == "completed"
        assert operation["output_available"] is True
        assert operation["output_width"] == 720
        assert operation["output_height"] == 1280
        assert operation["source_asset_id"] == source["id"]
        for forbidden in ("storage_key", "sha256", "provider", "payos", "wallet", "xu"):
            assert forbidden not in created.text.lower()

        assert len(commands) == 2
        probe_command, probe_kwargs = commands[0]
        render_command, render_kwargs = commands[1]
        assert probe_command[:5] == ["trusted-ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe"]
        assert render_command[:7] == ["trusted-ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-xerror", "-protocol_whitelist"]
        assert "file,pipe" in render_command
        assert "scale=1280:1280:force_original_aspect_ratio=decrease:force_divisible_by=2" in render_command
        assert probe_kwargs["shell"] is False and probe_kwargs["timeout"] == 6.0
        assert render_kwargs["shell"] is False and render_kwargs["timeout"] == 15.0

        replay = create_poster(client, csrf, asset_id=source["id"], key="video-owner-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["replay"] is True
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        conflict = create_poster(client, csrf, asset_id=source["id"], key="video-owner-create-0001", position="start")
        assert conflict.status_code == 409

        downloaded = client.get(f"/api/v1/video-operations/{operation['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("image/jpeg")
        assert downloaded.headers["cache-control"] == "no-store, private"
        assert downloaded.headers["x-content-type-options"] == "nosniff"
        assert downloaded.headers["referrer-policy"] == "no-referrer"
        assert downloaded.headers["content-security-policy"] == "sandbox"
        assert downloaded.headers["cross-origin-resource-policy"] == "same-origin"
        with Image.open(BytesIO(downloaded.content)) as poster:
            poster.verify()

        from copyfast_native_read_models import encode_native_job_id

        opaque_job_id = encode_native_job_id("video-operation", operation["id"])
        generic_delivery = client.get(f"/api/v1/assets/{opaque_job_id}/download")
        assert generic_delivery.status_code == 200
        assert generic_delivery.content == downloaded.content
        # The opaque Jobs/Assets route must keep the exact same private
        # attachment boundary as the direct Video Poster delivery route.
        # Otherwise the generic adapter could leak referrer context or be
        # cached even though it dispatches the same owner-scoped JPEG stream.
        assert generic_delivery.headers["cache-control"] == "no-store, private"
        assert generic_delivery.headers["referrer-policy"] == "no-referrer"
        assert generic_delivery.headers["content-security-policy"] == "sandbox"
        assert generic_delivery.headers["cross-origin-resource-policy"] == "same-origin"

        history = client.get("/api/v1/video-operations")
        assert history.status_code == 200
        assert history.headers["cache-control"] == "no-store, private"
        assert history.headers["cross-origin-resource-policy"] == "same-origin"

        csrf_other = register_and_login(client, "video-other@example.com")
        foreign = create_poster(client, csrf_other, asset_id=source["id"], key="video-other-create-0001")
        assert foreign.status_code == 422
        foreign_download = client.get(f"/api/v1/video-operations/{operation['id']}/download")
        assert foreign_download.status_code == 200
        assert foreign_download.json()["error_code"] == "VIDEO_OUTPUT_UNAVAILABLE"


def test_video_poster_terminally_fails_for_runtime_errors_quota_and_archived_queued_source(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        email = "video-failure@example.com"
        csrf = register_and_login(client, email)
        source = upload_video(client, csrf, key="video-failure-source-0001")
        module, _commands = activate_video_runtime(monkeypatch, failure="probe-timeout")

        runtime_failed = create_poster(client, csrf, asset_id=source["id"], key="video-timeout-create-0001")
        assert runtime_failed.status_code == 200
        assert runtime_failed.json()["ok"] is False
        assert runtime_failed.json()["status"] == "failed"
        assert runtime_failed.json()["data"]["operation"]["output_available"] is False

        # A completed artifact is published only after the account quota is
        # checked in the same transaction. Lower the test-only quota beneath
        # even the smallest valid JPEG to exercise cleanup after publication.
        module, _commands = activate_video_runtime(monkeypatch)
        monkeypatch.setattr(module, "_maximum_account_bytes", lambda: 1)
        quota_failed = create_poster(client, csrf, asset_id=source["id"], key="video-quota-create-0001")
        assert quota_failed.status_code == 200
        assert quota_failed.json()["status"] == "failed"
        assert quota_failed.json()["data"]["operation"]["output_available"] is False

        # Queue a record, then archive its source before execution. The
        # executor must terminally fail it rather than return a pending job
        # that no independent worker exists to resume.
        from copyfast_db import transaction, utc_now

        queued_source = upload_video(client, csrf, key="video-queued-source-0001")
        queued_id = str(uuid.uuid4())
        with transaction() as conn:
            account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
            asset = conn.execute(
                "SELECT sha256, byte_size, extension, content_type FROM web_asset_files WHERE id=?",
                (queued_source["id"],),
            ).fetchone()
            now = utc_now()
            conn.execute(
                """INSERT INTO web_video_operations
                       (id, account_id, source_asset_id, kind, state, idempotency_key,
                        request_fingerprint, source_sha256, source_byte_size,
                        source_extension, source_content_type, poster_position,
                        created_at, queued_at, updated_at)
                     VALUES (?, ?, ?, 'video_poster', 'queued', ?, ?, ?, ?, ?, ?, 'middle', ?, ?, ?)""",
                (
                    queued_id, account_id, queued_source["id"], "video-queued-internal-0001",
                    "f" * 64, str(asset[0]), int(asset[1]), str(asset[2]), str(asset[3]), now, now, now,
                ),
            )
            conn.execute("UPDATE web_asset_files SET state='archived' WHERE id=?", (queued_source["id"],))
        queued_result = module._execute_poster(
            queued_id,
            str(account_id),
            ffmpeg="trusted-ffmpeg",
            ffprobe="trusted-ffprobe",
            request_id="video-queued-test",
        )
        assert queued_result["state"] == "failed"
        assert queued_result["output_available"] is False


def test_video_poster_rejects_tampered_output_without_delivery(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-tamper@example.com")
        source = upload_video(client, csrf, key="video-tamper-source-0001")
        _module, _commands = activate_video_runtime(monkeypatch)
        created = create_poster(client, csrf, asset_id=source["id"], key="video-tamper-create-0001")
        operation = created.json()["data"]["operation"]
        assert operation["state"] == "completed"

        from copyfast_db import transaction

        with transaction() as conn:
            row = conn.execute("SELECT storage_key FROM web_video_operations WHERE id=?", (operation["id"],)).fetchone()
        assert row and isinstance(row[0], str)
        output_path = tmp_path / "private-video-outputs" / str(row[0])
        output_path.write_bytes(b"not-a-jpeg")

        rejected = client.get(f"/api/v1/video-operations/{operation['id']}/download")
        assert rejected.status_code == 200
        assert rejected.json()["ok"] is False
        assert rejected.json()["status"] == "unavailable"
        assert rejected.json()["error_code"] == "VIDEO_OUTPUT_UNAVAILABLE"
        assert rejected.headers["cache-control"] == "no-store, private"
        assert rejected.headers["cross-origin-resource-policy"] == "same-origin"


def test_video_poster_download_streams_a_sealed_snapshot_not_mutable_persistent_output(tmp_path, monkeypatch):
    """Mutation after verification cannot alter bytes handed to the client."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-sealed-delivery@example.com")
        source = upload_video(client, csrf, key="video-sealed-delivery-source-0001")
        module, _commands = activate_video_runtime(monkeypatch)
        created = create_poster(client, csrf, asset_id=source["id"], key="video-sealed-delivery-create-0001")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]

        from copyfast_db import transaction

        with transaction() as conn:
            row = conn.execute(
                "SELECT storage_key FROM web_video_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()
        assert row and isinstance(row[0], str)
        output_path = tmp_path / "private-video-outputs" / str(row[0])
        expected_body = output_path.read_bytes()
        original_attachment_response = module._attachment_response
        captured: dict[str, object] = {}

        def mutate_persistent_output_after_seal(stream, *, byte_size: int):
            # The route calls this only after it has created its private
            # ephemeral snapshot. If it accidentally passed the persistent
            # descriptor through, this mutation would corrupt the response.
            captured["stream"] = stream
            output_path.write_bytes(b"not-a-jpeg-after-stream-open")
            return original_attachment_response(stream, byte_size=byte_size)

        monkeypatch.setattr(module, "_attachment_response", mutate_persistent_output_after_seal)
        downloaded = client.get(f"/api/v1/video-operations/{operation['id']}/download")

        assert downloaded.status_code == 200
        assert downloaded.content == expected_body
        assert output_path.read_bytes() == b"not-a-jpeg-after-stream-open"
        sealed_stream = captured.get("stream")
        assert sealed_stream is not None and getattr(sealed_stream, "closed", False) is True
        with Image.open(BytesIO(downloaded.content)) as poster:
            poster.verify()


def test_video_poster_never_follows_a_symlinked_output_parent(tmp_path, monkeypatch):
    """A prepared parent symlink must fail before a poster is published."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-output-parent@example.com")
        source = upload_video(client, csrf, key="video-output-parent-source-0001")
        _module, _commands = activate_video_runtime(monkeypatch)
        root = tmp_path / "private-video-outputs"
        escaped_directory = tmp_path / "outside-private-video-root"
        root.mkdir(exist_ok=True)
        escaped_directory.mkdir()
        output_directory = root / "outputs"
        try:
            output_directory.symlink_to(escaped_directory, target_is_directory=True)
        except OSError:
            pytest.skip("Current test runtime cannot create directory symlinks")

        rejected = create_poster(
            client,
            csrf,
            asset_id=source["id"],
            key="video-output-parent-create-0001",
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "failed"
        assert rejected.json()["data"]["operation"]["output_available"] is False
        assert list(escaped_directory.iterdir()) == []
