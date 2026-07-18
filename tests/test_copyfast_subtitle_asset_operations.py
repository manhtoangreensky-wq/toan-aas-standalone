"""High-risk contracts for private SRT/VTT Asset Vault operations."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
import pytest


MODULES = [
    "app",
    "copyfast_api",
    "copyfast_assets",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_db",
    "copyfast_document_operations",
    "copyfast_image_operations",
    "copyfast_native_read_models",
    "copyfast_project_packages",
    "copyfast_registry",
    "copyfast_subtitle_asset_operations",
    "copyfast_subtitle_format_core",
]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True, topology: str = "sqlite_single_replica") -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-subtitle-asset-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-subtitle-asset-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "2")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "20")
    monkeypatch.setenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT", str(tmp_path / "private-subtitle-outputs"))
    monkeypatch.setenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_TOPOLOGY", topology)
    monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")
    monkeypatch.setenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_QUOTA_KB", "512")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ROOT", raising=False)
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
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Subtitle Owner"},
    ).status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def upload_subtitle(
    client: TestClient,
    csrf: str,
    *,
    key: str,
    body: bytes,
    name: str = "source.srt",
    content_type: str = "application/x-subrip",
) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Subtitle nguồn riêng tư"},
        files={"file": (name, body, content_type)},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


SRT = (
    b"1\n"
    b"00:00:01,000 --> 00:00:02,400\n"
    b"Xin chao\n\n"
    b"2\n"
    b"00:00:02,400 --> 00:00:03,000\n"
    b"Dong thu hai\n"
)


def convert(client: TestClient, csrf: str, *, asset_id: str, target_format: str, key: str):
    return client.post(
        "/api/v1/subtitle-asset-operations/convert",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "target_format": target_format, "idempotency_key": key},
    )


def validate(client: TestClient, csrf: str, *, asset_id: str, key: str):
    return client.post(
        "/api/v1/subtitle-asset-operations/validate",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "idempotency_key": key},
    )


def test_convert_is_owner_scoped_idempotent_and_seals_private_vtt(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "subtitle-owner@example.com")
        source = upload_subtitle(client, csrf, key="subtitle-source-0001", body=SRT)

        denied = client.post(
            "/api/v1/subtitle-asset-operations/convert",
            json={"source_asset_id": source["id"], "target_format": "vtt", "idempotency_key": "subtitle-denied-0001"},
        )
        assert denied.status_code == 403

        created = convert(client, csrf, asset_id=source["id"], target_format="vtt", key="subtitle-convert-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "subtitle_convert"
        assert operation["source_format"] == "srt"
        assert operation["target_format"] == "vtt"
        assert operation["cue_count"] == 2
        assert operation["timed_duration_ms"] == 3000
        assert operation["output_available"] is True
        assert operation["filename"] == "toan-aas-subtitle.vtt"
        for forbidden in ("source_asset_id", "storage_key", "sha256", "semantic", "provider", "payment", "payos", "xu"):
            assert forbidden not in created.text.lower()

        replay = convert(client, csrf, asset_id=source["id"], target_format="vtt", key="subtitle-convert-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["replay"] is True
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        # A retried receipt is immutable: archiving the source later cannot
        # turn a completed conversion into a new validation/error path.
        database = tmp_path / "copyfast-subtitle-asset-test.db"
        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE web_asset_files SET state='archived' WHERE id=?", (source["id"],))
            conn.commit()
        replay_after_archive = convert(client, csrf, asset_id=source["id"], target_format="vtt", key="subtitle-convert-0001")
        assert replay_after_archive.status_code == 200
        assert replay_after_archive.json()["data"]["replay"] is True
        assert replay_after_archive.json()["data"]["operation"]["id"] == operation["id"]
        other_source = upload_subtitle(client, csrf, key="subtitle-source-0002", body=SRT, name="other.srt")
        conflict = convert(client, csrf, asset_id=other_source["id"], target_format="vtt", key="subtitle-convert-0001")
        assert conflict.status_code == 409

        history = client.get("/api/v1/subtitle-asset-operations?limit=100")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["data"]["operations"]] == [operation["id"]]
        detail = client.get(f"/api/v1/subtitle-asset-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]

        downloaded = client.get(f"/api/v1/subtitle-asset-operations/{operation['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("text/vtt")
        assert downloaded.headers["cache-control"] == "no-store, private"
        assert downloaded.headers["x-content-type-options"] == "nosniff"
        assert downloaded.headers["referrer-policy"] == "no-referrer"
        assert downloaded.headers["content-security-policy"] == "sandbox"
        assert downloaded.headers["cross-origin-resource-policy"] == "same-origin"
        assert "attachment" in downloaded.headers["content-disposition"]
        assert downloaded.content == (
            b"WEBVTT\n\n"
            b"00:00:01.000 --> 00:00:02.400\nXin chao\n\n"
            b"00:00:02.400 --> 00:00:03.000\nDong thu hai\n"
        )

        with sqlite3.connect(database) as conn:
            row = conn.execute(
                "SELECT storage_key, account_id FROM web_subtitle_asset_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.subtitle_asset_operation.converted'"
            ).fetchone()
        assert row and row[0].endswith(".vtt")
        assert audit and source["id"] not in audit[0]

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "subtitle-other@example.com")
            hidden = other.get(f"/api/v1/subtitle-asset-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_SUBTITLE_ASSET_OPERATION_NOT_FOUND"
            hidden_download = other.get(f"/api/v1/subtitle-asset-operations/{operation['id']}/download")
            assert hidden_download.json()["error_code"] == "WEB_SUBTITLE_ASSET_OUTPUT_UNAVAILABLE"
            rejected = convert(other, csrf_other, asset_id=source["id"], target_format="vtt", key="subtitle-other-0001")
            assert rejected.status_code == 422

        # A completed row never delivers a mutable/tampered private file.
        (tmp_path / "private-subtitle-outputs" / row[0]).write_bytes(b"WEBVTT\n\n00:00.000 --> 00:01.000\ntampered\n")
        stale_detail = client.get(f"/api/v1/subtitle-asset-operations/{operation['id']}")
        assert stale_detail.json()["data"]["operation"]["state"] == "completed"
        assert stale_detail.json()["data"]["operation"]["output_available"] is False
        # Generic Jobs/Assets use the same verified-output gate. They must not
        # advertise a stale local file as a ready download before the typed
        # endpoint persists its durable unavailable state.
        native_jobs = client.get("/api/v1/jobs").json()["data"]["items"]
        native_job = next(item for item in native_jobs if item.get("native_kind") == "subtitle-asset-operation")
        assert native_job["id"] != operation["id"]
        assert native_job["output_available"] is False
        assert native_job["download_ready"] is False
        assert native_job["delivery_ready"] is False
        native_assets = client.get("/api/v1/assets").json()["data"]["items"]
        assert native_job["id"] not in {item.get("id") for item in native_assets}
        unavailable = client.get(f"/api/v1/subtitle-asset-operations/{operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_SUBTITLE_ASSET_OUTPUT_UNAVAILABLE"
        assert client.get(f"/api/v1/subtitle-asset-operations/{operation['id']}").json()["data"]["operation"]["state"] == "unavailable"


def test_validate_never_creates_file_and_invalid_subtitle_never_reports_success(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "subtitle-validate@example.com")
        valid_vtt = upload_subtitle(
            client,
            csrf,
            key="subtitle-valid-vtt-0001",
            name="source.vtt",
            content_type="text/vtt",
            body=b"WEBVTT\n\n00:00.000 --> 00:01.000\nNoi dung\n",
        )
        checked = validate(client, csrf, asset_id=valid_vtt["id"], key="subtitle-validate-0001")
        assert checked.status_code == 200
        checked_operation = checked.json()["data"]["operation"]
        assert checked.json()["ok"] is True
        assert checked_operation["kind"] == "subtitle_validate"
        assert checked_operation["output_available"] is False
        unavailable = client.get(f"/api/v1/subtitle-asset-operations/{checked_operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_SUBTITLE_ASSET_OUTPUT_UNAVAILABLE"

        invalid = upload_subtitle(
            client,
            csrf,
            key="subtitle-invalid-0001",
            body=b"1\n00:00:02,000 --> 00:00:01,000\nBad timing\n",
        )
        failed = convert(client, csrf, asset_id=invalid["id"], target_format="vtt", key="subtitle-invalid-convert-0001")
        assert failed.status_code == 200
        assert failed.json()["ok"] is False
        assert failed.json()["status"] == "failed"
        assert failed.json()["data"]["operation"]["output_available"] is False
        assert "SUBTITLE_FORMAT_INVALID" not in failed.text
        assert list((tmp_path / "private-subtitle-outputs" / "outputs").glob("*")) == []


def test_raw_body_limit_and_topology_guard_fail_closed(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        too_large = client.post(
            "/api/v1/subtitle-asset-operations/convert",
            data=b"x" * (16 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_SUBTITLE_ASSET_OPERATION_BODY_TOO_LARGE"

    with pytest.raises(RuntimeError, match="topology SQLite single-replica"):
        with make_client(tmp_path, monkeypatch, topology=""):
            pass
