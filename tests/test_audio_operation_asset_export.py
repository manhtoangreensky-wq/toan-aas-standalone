"""RED contracts for explicit Audio Asset Operation -> Asset Vault export.

These tests use the existing deterministic, in-process audio runtime pattern.
They never start FFmpeg/ffprobe or invoke a provider, Bot, wallet, payment, or
external delivery workflow.
"""

from __future__ import annotations

import importlib
import inspect
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
import pytest


def _is_application_module(name: str) -> bool:
    return name == "app" or name.startswith("copyfast_")


@pytest.fixture(autouse=True)
def isolate_application_imports():
    """Import this app fresh, then return every affected module to its caller.

    The application reads feature flags at import time.  Removing these modules
    before each test keeps the temporary environment deterministic; restoring
    the exact prior entries prevents this RED suite from leaking its app into
    another test module in the same pytest process.
    """

    original_modules = {
        name: module for name, module in sys.modules.items() if _is_application_module(name)
    }
    for name in tuple(sys.modules):
        if _is_application_module(name):
            sys.modules.pop(name, None)
    yield
    for name in tuple(sys.modules):
        if _is_application_module(name):
            sys.modules.pop(name, None)
    sys.modules.update(original_modules)


def make_client(tmp_path, monkeypatch, *, export_enabled: bool | None = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "audio-operation-asset-export.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "audio-operation-asset-export-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "2")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "20")
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ROOT", str(tmp_path / "private-audio-outputs"))
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_QUOTA_MB", "24")
    if export_enabled is None:
        monkeypatch.delenv("WEBAPP_AUDIO_ASSET_OPERATION_EXPORT_ENABLED", raising=False)
    else:
        monkeypatch.setenv(
            "WEBAPP_AUDIO_ASSET_OPERATION_EXPORT_ENABLED", "true" if export_enabled else "false"
        )
    for name in (
        "WEBAPP_DOCUMENT_OPERATIONS_ENABLED",
        "WEBAPP_IMAGE_OPERATIONS_ENABLED",
        "WEBAPP_PROJECT_PACKAGE_ENABLED",
        "WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED",
        "WEBAPP_VIDEO_OPERATIONS_ENABLED",
        "WEBAPP_VIDEO_POSTER_ENABLED",
        "WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED",
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
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Audio Export Owner",
        },
    )
    assert registered.status_code == 200, registered.text
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert logged_in.status_code == 200, logged_in.text
    return logged_in.json()["data"]["csrf_token"]


def mp3_bytes(marker: bytes = b"source") -> bytes:
    return b"ID3\x04\x00\x00" + marker + (b"\x00" * 1024)


def upload_mp3(client: TestClient, csrf: str, *, key: str, marker: bytes = b"source") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Audio nguồn riêng tư"},
        files={"file": ("source.mp3", mp3_bytes(marker), "audio/mpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["asset"]


def activate_audio_runtime(monkeypatch):
    """Enable a fixed local substitute only after ASGI startup."""

    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
    monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")
    module = importlib.import_module("copyfast_audio_asset_operations")
    monkeypatch.setattr(module, "_audio_runtime", lambda: ("trusted-ffmpeg", "trusted-ffprobe"))
    calls: list[dict[str, object]] = []

    def fake_probe(_ffprobe: str, path: Path | str, *, input_bytes: bytes | None = None) -> dict[str, object]:
        if (input_bytes is not None and input_bytes[4:8] == b"ftyp") or Path(path).suffix.lower() == ".m4a":
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
        _ffmpeg: str, source: Path, destination: Path, *, target_format: str, normalize: bool
    ) -> None:
        assert source.suffix == ".mp3"
        calls.append({"target_format": target_format, "normalize": normalize})
        if target_format == "m4a":
            destination.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2" + (b"\x00" * 256))
        else:
            destination.write_bytes(mp3_bytes(b"rendered"))

    monkeypatch.setattr(module, "_probe_audio", fake_probe)
    monkeypatch.setattr(module, "_render_audio", fake_render)
    return calls


def test_audio_export_bootstrap_capability_requires_every_private_gate(monkeypatch) -> None:
    """Portal must not advertise export when any server gate is paused."""

    for name in (
        "WEBAPP_ASSET_VAULT_ENABLED",
        "WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED",
        "WEBAPP_AUDIO_ASSET_OPERATION_EXPORT_ENABLED",
    ):
        monkeypatch.setenv(name, "true")
    api = importlib.import_module("copyfast_api")

    assert api._flags()["audio_asset_operation_export_enabled"] is True
    for paused_gate in (
        "WEBAPP_ASSET_VAULT_ENABLED",
        "WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED",
        "WEBAPP_AUDIO_ASSET_OPERATION_EXPORT_ENABLED",
    ):
        monkeypatch.setenv(paused_gate, "false")
        assert api._flags()["audio_asset_operation_export_enabled"] is False
        monkeypatch.setenv(paused_gate, "true")


def test_export_reserves_before_offloaded_private_output_work(tmp_path, monkeypatch) -> None:
    """The lease fences repeat requests before a worker opens or probes audio."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-export-reserve-first@example.com")
        activate_audio_runtime(monkeypatch)
        audio_module = importlib.import_module("copyfast_audio_asset_operations")
        assets = importlib.import_module("copyfast_assets")
        operation_id = "00000000-0000-4000-8000-000000000011"
        payload = mp3_bytes(b"reserve-before-open")
        digest = hashlib.sha256(payload).hexdigest()
        events: list[str] = []
        lease = assets.AudioOperationAssetExportLease(
            "owner", operation_id, 1, "lease-token", "2099-01-01T00:00:00+00:00",
            "objects/00000000000000000000000000000000.pending", len(payload), digest,
        )
        source = audio_module.AudioOperationAssetExportPinnedSource(
            stream=BytesIO(payload), kind="audio_convert", project_id=None,
            target_format="mp3", extension=".mp3", content_type="audio/mpeg",
            byte_size=len(payload), digest=digest, duration_seconds=2.0, duration_ms=2000,
            channels=2, sample_rate=48000, codec="mp3", format_name="mp3",
        )

        monkeypatch.setattr(assets, "replay_audio_operation_asset_export", lambda **_kwargs: None)

        def reserve(**kwargs):
            events.append("reserve")
            assert set(kwargs) == {"account_id", "operation_id", "idempotency_key"}
            assert kwargs["operation_id"] == operation_id
            return assets.AudioOperationAssetExportReservation(state="leased", lease=lease)

        def open_source(**_kwargs):
            events.append("open")
            assert events == ["reserve", "thread:open_source", "open"]
            return audio_module.AudioOperationAssetExportSourceResult(
                source=source, failure=None, _operation_id=operation_id, _account_id="owner",
            )

        def finalize(**kwargs):
            events.append("finalize")
            assert events == [
                "reserve",
                "thread:open_source",
                "open",
                "thread:finalize",
                "finalize",
            ]
            kwargs["source"].stream.close()
            return assets.AudioOperationAssetExportFinalization(
                state="completed",
                asset={"id": "00000000-0000-4000-8000-000000000012", "state": "active"},
            )

        async def in_worker(function, *args, **kwargs):
            events.append(f"thread:{function.__name__}")
            return function(*args, **kwargs)

        receipt = assets.AudioOperationAssetExportFinalization(
            state="completed", asset={"id": "00000000-0000-4000-8000-000000000012", "state": "active"},
        )
        monkeypatch.setattr(assets, "reserve_audio_operation_asset_export", reserve)
        monkeypatch.setattr(audio_module, "open_audio_operation_asset_export_source", open_source)
        monkeypatch.setattr(assets, "finalize_audio_operation_asset_export", finalize)
        monkeypatch.setattr(assets, "get_audio_operation_asset_export_receipt", lambda **_kwargs: receipt)
        monkeypatch.setattr(audio_module, "run_in_threadpool", in_worker)

        response = export_operation(client, csrf, operation_id, "audio-export-reserve-first-0001")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed", (response.text, events)
    assert events[-1] == "finalize"


def transform(client: TestClient, csrf: str, *, asset_id: str, kind: str, key: str) -> dict:
    if kind == "audio_normalize":
        path, payload = "/api/v1/audio-asset-operations/normalize", {"source_asset_id": asset_id, "idempotency_key": key}
    else:
        target = "mp3" if kind == "audio_convert_mp3" else "m4a"
        path, payload = "/api/v1/audio-asset-operations/convert", {
            "source_asset_id": asset_id,
            "target_format": target,
            "idempotency_key": key,
        }
    response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
    assert response.status_code == 200, response.text
    operation = response.json()["data"]["operation"]
    assert operation["state"] == "completed" and operation["output_available"] is True
    return operation


def inspect_operation(client: TestClient, csrf: str, *, asset_id: str, key: str) -> dict:
    response = client.post(
        "/api/v1/audio-asset-operations/inspect",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "idempotency_key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["operation"]


def export_operation(client: TestClient, csrf: str, operation_id: str, key: str, *, content: bytes | None = None):
    return client.post(
        f"/api/v1/audio-asset-operations/{operation_id}/export-to-asset-vault",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        content=content,
    )


def asset_count(database: Path) -> int:
    with sqlite3.connect(database) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM web_asset_files").fetchone()[0])


def operation_storage_key(database: Path, operation_id: str) -> str:
    with sqlite3.connect(database) as conn:
        row = conn.execute(
            "SELECT storage_key FROM web_audio_asset_operations WHERE id=?", (operation_id,)
        ).fetchone()
    assert row and row[0]
    return str(row[0])


def assert_safe(response) -> None:
    lowered = response.text.lower()
    for forbidden in (
        "storage_key", "sha256", "source_asset_id", "filesystem", "provider", "bridge",
        "wallet", "payment", "payos", "telegram", "bot", "content handoff",
    ):
        assert forbidden not in lowered


def assert_truthful_rejection(response, database: Path, expected_count: int, *, statuses: set[str]) -> None:
    """A rejected private export never fabricates a Vault asset receipt."""

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert body["status"] in statuses
    assert "asset" not in body.get("data", {})
    assert_safe(response)
    assert asset_count(database) == expected_count


def operation_account_id(database: Path, operation_id: str) -> str:
    with sqlite3.connect(database) as conn:
        row = conn.execute(
            "SELECT account_id FROM web_audio_asset_operations WHERE id=?", (operation_id,)
        ).fetchone()
    assert row and row[0]
    return str(row[0])


def audio_export_source(assets, *, account_id: str, operation_id: str, payload: bytes, kind: str = "audio_convert", project_id: str | None = None, target_format: str = "mp3", extension: str = ".mp3", content_type: str = "audio/mpeg", codec: str = "mp3", format_name: str = "mp3"):
    """The finalizer receives a server-opened stream plus a closed descriptor only."""

    return assets.AudioOperationAssetExportSource(
        account_id=account_id,
        operation_id=operation_id,
        kind=kind,
        project_id=project_id,
        original_filename=f"toan-aas-audio{extension}",
        target_format=target_format,
        extension=extension,
        content_type=content_type,
        byte_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        duration_seconds=2.0,
        duration_ms=2000,
        channels=2,
        sample_rate=48000,
        codec=codec,
        format_name=format_name,
        stream=BytesIO(payload),
    )


def test_verified_completed_mp3_and_m4a_transforms_export_once_with_an_opaque_empty_body(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-export-owner@example.com")
        source = upload_mp3(client, csrf, key="audio-export-source-0001")
        calls = activate_audio_runtime(monkeypatch)
        database = tmp_path / "audio-operation-asset-export.db"

        for index, kind in enumerate(("audio_convert_mp3", "audio_convert_m4a", "audio_normalize"), start=1):
            operation = transform(
                client, csrf, asset_id=source["id"], kind=kind, key=f"audio-export-transform-{index:04d}"
            )
            expected_extension = ".mp3" if kind == "audio_convert_mp3" else ".m4a"
            expected_content_type = "audio/mpeg" if expected_extension == ".mp3" else "audio/mp4"
            original = client.get(f"/api/v1/audio-asset-operations/{operation['id']}/download")
            assert original.status_code == 200, original.text
            before = asset_count(database)

            exported = export_operation(
                client,
                csrf,
                operation["id"],
                f"audio-export-copy-{index:04d}",
                # The endpoint owns every source/output descriptor; browser
                # body values must neither be required nor influence export.
                content=b'{"path":"/not/used","sha256":"not-used","body":"not-used"}',
            )

            assert exported.status_code == 200, exported.text
            body = exported.json()
            assert body["ok"] is True and body["status"] == "completed"
            asset = body["data"]["asset"]
            assert asset["state"] == "active"
            assert asset["extension"] == expected_extension
            assert asset["content_type"] == expected_content_type
            assert asset["byte_size"] == len(original.content)
            assert {"storage_key", "sha256", "account_id", "source_asset_id"}.isdisjoint(asset)
            assert_safe(exported)
            saved = client.get(f"/api/v1/asset-vault/{asset['id']}/download")
            assert saved.status_code == 200, saved.text
            assert saved.content == original.content

            replay = export_operation(client, csrf, operation["id"], f"audio-export-copy-{index:04d}")
            assert replay.status_code == 200, replay.text
            assert replay.json()["data"]["asset"]["id"] == asset["id"]
            new_key_replay = export_operation(
                client, csrf, operation["id"], f"audio-export-copy-new-key-{index:04d}"
            )
            assert new_key_replay.status_code == 200, new_key_replay.text
            assert new_key_replay.json()["data"]["asset"]["id"] == asset["id"]
            assert asset_count(database) == before + 1

        assert calls == [
            {"target_format": "mp3", "normalize": False},
            {"target_format": "m4a", "normalize": False},
            {"target_format": "m4a", "normalize": True},
        ]


def test_export_requires_enabled_capability_csrf_and_an_unreused_idempotency_key(tmp_path, monkeypatch):
    disabled_root = tmp_path / "disabled"
    disabled_root.mkdir()
    with make_client(disabled_root, monkeypatch, export_enabled=False) as disabled_client:
        disabled_csrf = register_and_login(disabled_client, "audio-export-disabled@example.com")
        disabled_source = upload_mp3(disabled_client, disabled_csrf, key="audio-export-disabled-source-0001")
        activate_audio_runtime(monkeypatch)
        disabled_operation = transform(
            disabled_client, disabled_csrf, asset_id=disabled_source["id"], kind="audio_convert_mp3", key="audio-export-disabled-transform-0001"
        )
        disabled = export_operation(disabled_client, disabled_csrf, disabled_operation["id"], "audio-export-disabled-copy-0001")
        assert disabled.status_code == 503
        assert asset_count(disabled_root / "audio-operation-asset-export.db") == 1

    unset_root = tmp_path / "unset"
    unset_root.mkdir()
    with make_client(unset_root, monkeypatch, export_enabled=None) as unset_client:
        unset_csrf = register_and_login(unset_client, "audio-export-unset@example.com")
        unset_source = upload_mp3(unset_client, unset_csrf, key="audio-export-unset-source-0001")
        activate_audio_runtime(monkeypatch)
        unset_operation = transform(
            unset_client, unset_csrf, asset_id=unset_source["id"], kind="audio_convert_mp3", key="audio-export-unset-transform-0001"
        )
        unset = export_operation(unset_client, unset_csrf, unset_operation["id"], "audio-export-unset-copy-0001")
        assert unset.status_code == 503
        assert asset_count(unset_root / "audio-operation-asset-export.db") == 1

    enabled_root = tmp_path / "enabled"
    enabled_root.mkdir()
    with make_client(enabled_root, monkeypatch) as client:
        csrf = register_and_login(client, "audio-export-boundary@example.com")
        source = upload_mp3(client, csrf, key="audio-export-boundary-source-0001")
        activate_audio_runtime(monkeypatch)
        operation = transform(client, csrf, asset_id=source["id"], kind="audio_convert_mp3", key="audio-export-boundary-transform-0001")
        database = enabled_root / "audio-operation-asset-export.db"
        before = asset_count(database)

        missing_csrf = client.post(
            f"/api/v1/audio-asset-operations/{operation['id']}/export-to-asset-vault",
            headers={"Idempotency-Key": "audio-export-missing-csrf-0001"},
        )
        assert missing_csrf.status_code == 403
        missing_key = client.post(
            f"/api/v1/audio-asset-operations/{operation['id']}/export-to-asset-vault",
            headers={"X-CSRF-Token": csrf},
        )
        assert missing_key.status_code == 422
        assert asset_count(database) == before
        first = export_operation(client, csrf, operation["id"], "audio-export-rebind-0001")
        assert first.status_code == 200, first.text
        second_source = upload_mp3(client, csrf, key="audio-export-rebind-source-0002", marker=b"second")
        second = transform(client, csrf, asset_id=second_source["id"], kind="audio_convert_mp3", key="audio-export-rebind-transform-0002")
        collision = export_operation(client, csrf, second["id"], "audio-export-rebind-0001")
        assert collision.status_code == 409
        assert asset_count(database) == before + 2


def test_disabled_export_gate_runs_before_replay_or_private_output_open(tmp_path, monkeypatch):
    """A disabled retention capability must not inspect an otherwise valid output."""

    with make_client(tmp_path, monkeypatch, export_enabled=False) as client:
        csrf = register_and_login(client, "audio-export-gate-order@example.com")
        source = upload_mp3(client, csrf, key="audio-export-gate-order-source-0001")
        activate_audio_runtime(monkeypatch)
        operation = transform(
            client,
            csrf,
            asset_id=source["id"],
            kind="audio_convert_mp3",
            key="audio-export-gate-order-transform-0001",
        )
        audio_operations = importlib.import_module("copyfast_audio_asset_operations")
        assets = importlib.import_module("copyfast_assets")
        touched: list[str] = []

        def must_not_replay(**_kwargs):
            touched.append("replay")
            raise AssertionError("disabled export must not query replay state")

        def must_not_open(**_kwargs):
            touched.append("open")
            raise AssertionError("disabled export must not open a private output")

        monkeypatch.setattr(assets, "replay_audio_operation_asset_export", must_not_replay)
        monkeypatch.setattr(audio_operations, "open_audio_operation_asset_export_source", must_not_open)

        response = export_operation(
            client,
            csrf,
            operation["id"],
            "audio-export-gate-order-copy-0001",
        )

    assert response.status_code == 503
    assert touched == []


def test_export_returns_guarded_replay_or_reservation_truthfully(tmp_path, monkeypatch):
    """An invalidated receipt is never presented as an in-progress copy."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-export-guarded-receipt@example.com")
        activate_audio_runtime(monkeypatch)
        audio_operations = importlib.import_module("copyfast_audio_asset_operations")
        assets = importlib.import_module("copyfast_assets")
        operation_id = "00000000-0000-4000-8000-000000000001"
        guarded = assets.AudioOperationAssetExportFinalization(state="guarded", asset=None)

        monkeypatch.setattr(
            assets,
            "replay_audio_operation_asset_export",
            lambda **_kwargs: guarded,
        )
        replay = export_operation(client, csrf, operation_id, "audio-export-guarded-replay-0001")

        payload = mp3_bytes(b"guarded-reservation")
        pinned = audio_operations.AudioOperationAssetExportPinnedSource(
            stream=BytesIO(payload),
            kind="audio_convert",
            project_id=None,
            target_format="mp3",
            extension=".mp3",
            content_type="audio/mpeg",
            byte_size=len(payload),
            digest=hashlib.sha256(payload).hexdigest(),
            duration_seconds=2.0,
            duration_ms=2000,
            channels=2,
            sample_rate=48000,
            codec="mp3",
            format_name="mp3",
        )
        source_result = audio_operations.AudioOperationAssetExportSourceResult(
            source=pinned,
            failure=None,
            _operation_id=operation_id,
            _account_id="ignored-by-mock",
        )
        monkeypatch.setattr(assets, "replay_audio_operation_asset_export", lambda **_kwargs: None)
        monkeypatch.setattr(
            audio_operations,
            "open_audio_operation_asset_export_source",
            lambda **_kwargs: source_result,
        )
        monkeypatch.setattr(
            assets,
            "reserve_audio_operation_asset_export",
            lambda **_kwargs: assets.AudioOperationAssetExportReservation(state="guarded"),
        )
        monkeypatch.setattr(assets, "get_audio_operation_asset_export_receipt", lambda **_kwargs: guarded)
        reservation = export_operation(client, csrf, operation_id, "audio-export-guarded-reservation-0001")

    for response in (replay, reservation):
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_AUDIO_OPERATION_EXPORT_GUARDED"
    # A refused reservation no longer opens the private source at all. The
    # fixture owns this unused stream and closes it explicitly.
    assert not pinned.stream.closed
    pinned.close()
    assert pinned.stream.closed


def test_export_hides_foreign_and_rejects_inspect_pending_tampered_or_unavailable_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-export-guard-owner@example.com")
        source = upload_mp3(client, csrf, key="audio-export-guard-source-0001")
        activate_audio_runtime(monkeypatch)
        operation = transform(client, csrf, asset_id=source["id"], kind="audio_convert_mp3", key="audio-export-guard-transform-0001")
        database = tmp_path / "audio-operation-asset-export.db"
        before = asset_count(database)

        with TestClient(client.app) as foreign:
            foreign_csrf = register_and_login(foreign, "audio-export-foreign@example.com")
            hidden = export_operation(foreign, foreign_csrf, operation["id"], "audio-export-foreign-0001")
            assert_truthful_rejection(hidden, database, before, statuses={"guarded"})

        inspect_only = inspect_operation(client, csrf, asset_id=source["id"], key="audio-export-inspect-0001")
        rejected_inspect = export_operation(client, csrf, inspect_only["id"], "audio-export-inspect-copy-0001")
        assert_truthful_rejection(rejected_inspect, database, before, statuses={"guarded"})

        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE web_audio_asset_operations SET state='processing' WHERE id=?", (operation["id"],))
            conn.commit()
        pending = export_operation(client, csrf, operation["id"], "audio-export-pending-0001")
        assert_truthful_rejection(pending, database, before, statuses={"processing", "guarded"})

        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE web_audio_asset_operations SET state='completed' WHERE id=?", (operation["id"],))
            conn.commit()
        output = tmp_path / "private-audio-outputs" / operation_storage_key(database, operation["id"])
        output.write_bytes(b"ID3tampered-private-output")
        tampered = export_operation(client, csrf, operation["id"], "audio-export-tampered-0001")
        assert_truthful_rejection(tampered, database, before, statuses={"unavailable", "guarded"})

        clean = transform(client, csrf, asset_id=source["id"], kind="audio_convert_m4a", key="audio-export-unavailable-transform-0001")
        unavailable_output = tmp_path / "private-audio-outputs" / operation_storage_key(database, clean["id"])
        unavailable_output.unlink()
        unavailable = export_operation(client, csrf, clean["id"], "audio-export-unavailable-copy-0001")
        assert_truthful_rejection(unavailable, database, before, statuses={"unavailable", "guarded"})


def test_export_rejects_every_noncanonical_mp3_m4a_descriptor_without_an_asset(tmp_path, monkeypatch):
    """Target, media type, stored suffix, and probe must agree before export."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-export-descriptor-owner@example.com")
        source = upload_mp3(client, csrf, key="audio-export-descriptor-source-0001")
        activate_audio_runtime(monkeypatch)
        database = tmp_path / "audio-operation-asset-export.db"
        before = asset_count(database)

        target_mismatch = transform(client, csrf, asset_id=source["id"], kind="audio_convert_mp3", key="audio-export-descriptor-target-0001")
        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE web_audio_asset_operations SET target_format='m4a' WHERE id=?", (target_mismatch["id"],))
            conn.commit()
        assert_truthful_rejection(
            export_operation(client, csrf, target_mismatch["id"], "audio-export-descriptor-target-copy-0001"),
            database,
            before,
            statuses={"unavailable", "guarded"},
        )

        content_type_mismatch = transform(client, csrf, asset_id=source["id"], kind="audio_convert_mp3", key="audio-export-descriptor-content-type-0001")
        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE web_audio_asset_operations SET content_type='audio/mp4' WHERE id=?", (content_type_mismatch["id"],))
            conn.commit()
        assert_truthful_rejection(
            export_operation(client, csrf, content_type_mismatch["id"], "audio-export-descriptor-content-type-copy-0001"),
            database,
            before,
            statuses={"unavailable", "guarded"},
        )

        suffix_mismatch = transform(client, csrf, asset_id=source["id"], kind="audio_convert_mp3", key="audio-export-descriptor-suffix-0001")
        original_path = tmp_path / "private-audio-outputs" / operation_storage_key(database, suffix_mismatch["id"])
        mismatched_key = operation_storage_key(database, suffix_mismatch["id"]).removesuffix(".mp3") + ".m4a"
        mismatched_path = tmp_path / "private-audio-outputs" / mismatched_key
        mismatched_path.parent.mkdir(parents=True, exist_ok=True)
        mismatched_path.write_bytes(original_path.read_bytes())
        original_path.unlink()
        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE web_audio_asset_operations SET storage_key=? WHERE id=?", (mismatched_key, suffix_mismatch["id"]))
            conn.commit()
        assert_truthful_rejection(
            export_operation(client, csrf, suffix_mismatch["id"], "audio-export-descriptor-suffix-copy-0001"),
            database,
            before,
            statuses={"unavailable", "guarded"},
        )

        probe_mismatch = transform(client, csrf, asset_id=source["id"], kind="audio_convert_mp3", key="audio-export-descriptor-probe-0001")
        audio_module = importlib.import_module("copyfast_audio_asset_operations")
        monkeypatch.setattr(
            audio_module,
            "_probe_audio",
            lambda _ffprobe, _path, **_kwargs: {
                "duration_seconds": 2.0,
                "duration_ms": 2000,
                "channels": 2,
                "sample_rate": 48000,
                "codec": "aac",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            },
        )
        assert_truthful_rejection(
            export_operation(client, csrf, probe_mismatch["id"], "audio-export-descriptor-probe-copy-0001"),
            database,
            before,
            statuses={"unavailable", "guarded"},
        )


def test_stale_audio_export_finalizer_cannot_publish_or_delete_the_current_attempt(tmp_path, monkeypatch):
    """A reclaimed lease fences a stale writer away from the current asset."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "audio-export-stale-owner@example.com")
        source = upload_mp3(client, csrf, key="audio-export-stale-source-0001")
        activate_audio_runtime(monkeypatch)
        operation = transform(client, csrf, asset_id=source["id"], kind="audio_convert_mp3", key="audio-export-stale-transform-0001")
        database = tmp_path / "audio-operation-asset-export.db"
        payload = (tmp_path / "private-audio-outputs" / operation_storage_key(database, operation["id"])).read_bytes()
        account_id = operation_account_id(database, operation["id"])
        assets = importlib.import_module("copyfast_assets")
        digest = hashlib.sha256(payload).hexdigest()

        first = assets.reserve_audio_operation_asset_export(
            account_id=account_id,
            operation_id=operation["id"],
            idempotency_key="audio-export-stale-first-0001",
            request_fingerprint=digest,
            expected_bytes=len(payload),
        )
        assert first.lease is not None
        abandoned = assets._storage_path(assets.asset_vault_directory(), first.lease.pending_storage_key)
        abandoned.parent.mkdir(parents=True, exist_ok=True)
        abandoned.write_bytes(payload)
        with sqlite3.connect(database) as conn:
            conn.execute(
                "UPDATE web_audio_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
                ("1970-01-01T00:00:00+00:00", operation["id"]),
            )
            conn.commit()
        reclaimed = assets.reserve_audio_operation_asset_export(
            account_id=account_id,
            operation_id=operation["id"],
            idempotency_key="audio-export-stale-reclaimed-0001",
            request_fingerprint=digest,
            expected_bytes=len(payload),
        )
        assert reclaimed.lease is not None
        assert reclaimed.lease.pending_storage_key != first.lease.pending_storage_key
        assert not abandoned.exists()
        completed = assets.finalize_audio_operation_asset_export(
            lease=reclaimed.lease,
            source=audio_export_source(
                assets, account_id=account_id, operation_id=operation["id"], payload=payload
            ),
            request_id="audio-export-stale-reclaimed-complete",
        )

        with pytest.raises(RuntimeError, match="lease"):
            assets.finalize_audio_operation_asset_export(
                lease=first.lease,
                source=audio_export_source(
                    assets, account_id=account_id, operation_id=operation["id"], payload=payload
                ),
                request_id="audio-export-stale-late-finalizer",
            )

        with sqlite3.connect(database) as conn:
            relation = conn.execute(
                "SELECT asset_id, state FROM web_audio_operation_asset_exports WHERE operation_id=?",
                (operation["id"],),
            ).fetchone()
        assert relation == (completed.asset["id"], "completed")
        assert asset_count(database) == 2
        saved = client.get(f"/api/v1/asset-vault/{completed.asset['id']}/download")
        assert saved.status_code == 200, saved.text
        assert saved.content == payload


def test_audio_export_byte_validation_uses_audio_public_error_domain(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as _client:
        assets = importlib.import_module("copyfast_assets")
        with pytest.raises(HTTPException) as invalid:
            assets._audio_operation_export_expected_bytes(False)

    detail = str(invalid.value.detail).lower()
    assert "audio" in detail
    assert "document" not in detail


def test_pinned_audio_export_probe_uses_server_stream_not_private_path(monkeypatch):
    audio_operations = importlib.import_module("copyfast_audio_asset_operations")
    payload = mp3_bytes(b"pinned-probe")
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "format": {"format_name": "mp3", "duration": "2.0"},
                    "streams": [
                        {
                            "codec_type": "audio",
                            "codec_name": "mp3",
                            "channels": 2,
                            "sample_rate": "48000",
                        }
                    ],
                }
            ).encode("utf-8"),
        )

    monkeypatch.setattr(audio_operations.subprocess, "run", fake_run)
    metadata = audio_operations._probe_pinned_audio_export_stream(
        "trusted-ffprobe",
        BytesIO(payload),
    )

    assert metadata["codec"] == "mp3"
    assert captured["command"][-1] == "pipe:0"
    assert captured["kwargs"]["input"] == payload
    assert "stdin" not in captured["kwargs"]


@pytest.mark.parametrize(
    ("source_changes", "stored_changes", "mismatch"),
    (
        ({"kind": "audio_normalize"}, {}, "kind"),
        ({"project_id": "project-from-another-operation"}, {"project_id": "project-for-this-operation"}, "project"),
    ),
)
def test_finalizer_rejects_source_provenance_mismatched_to_completed_operation_before_copy(
    tmp_path, monkeypatch, source_changes, stored_changes, mismatch
):
    """The final source descriptor must exactly retain its completed-operation provenance."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, f"audio-export-{mismatch}-owner@example.com")
        source = upload_mp3(client, csrf, key=f"audio-export-{mismatch}-source-0001")
        activate_audio_runtime(monkeypatch)
        operation = transform(
            client,
            csrf,
            asset_id=source["id"],
            kind="audio_convert_mp3",
            key=f"audio-export-{mismatch}-transform-0001",
        )
        database = tmp_path / "audio-operation-asset-export.db"
        payload = (
            tmp_path / "private-audio-outputs" / operation_storage_key(database, operation["id"])
        ).read_bytes()
        account_id = operation_account_id(database, operation["id"])
        assets = importlib.import_module("copyfast_assets")
        with sqlite3.connect(database) as conn:
            for column, value in stored_changes.items():
                conn.execute(
                    f"UPDATE web_audio_asset_operations SET {column}=? WHERE id=?",
                    (value, operation["id"]),
                )
            conn.commit()
        reservation = assets.reserve_audio_operation_asset_export(
            account_id=account_id,
            operation_id=operation["id"],
            idempotency_key=f"audio-export-{mismatch}-reserve-0001",
            request_fingerprint=hashlib.sha256(payload).hexdigest(),
            expected_bytes=len(payload),
        )
        assert reservation.lease is not None
        before = asset_count(database)

        def fail_if_copy_started(*_args, **_kwargs):
            raise AssertionError("provenance validation reached Vault copy")

        monkeypatch.setattr(assets, "_copy_audio_operation_asset_export_source", fail_if_copy_started)
        with pytest.raises(RuntimeError, match=mismatch):
            assets.finalize_audio_operation_asset_export(
                lease=reservation.lease,
                source=audio_export_source(
                    assets,
                    account_id=account_id,
                    operation_id=operation["id"],
                    payload=payload,
                    **source_changes,
                ),
                request_id=f"audio-export-{mismatch}-finalize-0001",
            )
        assert asset_count(database) == before


@pytest.mark.parametrize(
    ("kind", "normalization_profile"),
    (
        ("audio_normalize", "not-speech-safe"),
        ("audio_convert_mp3", "speech_safe_v1"),
    ),
)
def test_reservation_rejects_completed_operation_with_noncanonical_normalization_profile(
    tmp_path, monkeypatch, kind, normalization_profile
):
    """Normalize requires speech_safe_v1; conversion must not carry a profile."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, f"audio-export-profile-{kind}@example.com")
        source = upload_mp3(client, csrf, key=f"audio-export-profile-{kind}-source-0001")
        activate_audio_runtime(monkeypatch)
        operation = transform(
            client,
            csrf,
            asset_id=source["id"],
            kind=kind,
            key=f"audio-export-profile-{kind}-transform-0001",
        )
        database = tmp_path / "audio-operation-asset-export.db"
        payload = (
            tmp_path / "private-audio-outputs" / operation_storage_key(database, operation["id"])
        ).read_bytes()
        account_id = operation_account_id(database, operation["id"])
        with sqlite3.connect(database) as conn:
            conn.execute(
                "UPDATE web_audio_asset_operations SET normalization_profile=? WHERE id=?",
                (normalization_profile, operation["id"]),
            )
            conn.commit()
        assets = importlib.import_module("copyfast_assets")
        before = asset_count(database)

        with pytest.raises(HTTPException, match="Audio Operation chưa sẵn sàng để lưu"):
            assets.reserve_audio_operation_asset_export(
                account_id=account_id,
                operation_id=operation["id"],
                idempotency_key=f"audio-export-profile-{kind}-reserve-0001",
                request_fingerprint=hashlib.sha256(payload).hexdigest(),
                expected_bytes=len(payload),
            )
        assert asset_count(database) == before


def _all_dependants(dependant):
    yield dependant
    for dependency in dependant.dependencies:
        yield from _all_dependants(dependency)


def test_export_route_is_a_csrf_protected_header_only_post(tmp_path, monkeypatch) -> None:
    """The browser can submit only an operation id and idempotency header."""

    with make_client(tmp_path, monkeypatch) as client:
        routes = [
            route
            for route in client.app.routes
            if isinstance(route, APIRoute)
            and route.path.startswith("/api/v1/audio-asset-operations/")
            and route.path.endswith("/export-to-asset-vault")
        ]

    assert len(routes) == 1
    route = routes[0]
    assert route.methods == {"POST"}
    assert route.path.count("{") == route.path.count("}") == 1

    dependants = tuple(_all_dependants(route.dependant))
    assert not any(dependant.body_params or dependant.query_params for dependant in dependants)
    header_names = {
        parameter.alias.lower()
        for dependant in dependants
        for parameter in dependant.header_params
    }
    assert {"x-csrf-token", "idempotency-key"}.issubset(header_names)

    # A server-side descriptor may legitimately be opened after this boundary,
    # but the public handler cannot accept browser-controlled media or source
    # descriptors.  Inspect the selected endpoint rather than its declaration
    # order or a particular Request annotation.
    endpoint_source = inspect.getsource(route.endpoint)
    for forbidden in (
        "source_asset_id", "storage_key", "sha256", "filename", "content_type",
        "UploadFile", "Body(", "Query(", "Form(", "request.query_params",
        "request.body(", "request.json(", "request.form(", "request.stream(",
    ):
        assert forbidden not in endpoint_source


@pytest.mark.parametrize("export_enabled", (False, None))
def test_export_route_fails_closed_before_replay_or_source_when_export_flag_disabled(
    tmp_path, monkeypatch, export_enabled
) -> None:
    """Disabled export capability must stop before account-scoped replay/source work."""

    with make_client(tmp_path, monkeypatch, export_enabled=export_enabled) as client:
        csrf = register_and_login(client, f"audio-export-gate-{export_enabled}@example.com")
        assets = importlib.import_module("copyfast_assets")
        audio_module = importlib.import_module("copyfast_audio_asset_operations")

        def fail_if_called(*_args, **_kwargs):
            raise AssertionError("disabled export reached account-dependent export work")

        monkeypatch.setattr(assets, "replay_audio_operation_asset_export", fail_if_called)
        monkeypatch.setattr(audio_module, "open_audio_operation_asset_export_source", fail_if_called)

        response = client.post(
            "/api/v1/audio-asset-operations/00000000-0000-4000-8000-000000000001/export-to-asset-vault",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "audio-export-gate-copy-0001"},
        )

    assert response.status_code == 503
