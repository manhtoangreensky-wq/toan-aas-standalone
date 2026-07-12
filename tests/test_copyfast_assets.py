"""Security and ownership contracts for the native Web Asset Vault."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-assets-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-asset-vault-session-secret")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Web Asset Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def upload_text(client: TestClient, csrf: str, *, key: str, content: bytes = b"Noi dung Web Workspace an toan", name: str = "brief.txt", display_name: str = "Brief ra mat"):
    return client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": display_name},
        files={"file": (name, content, "text/plain")},
    )


def test_asset_vault_is_web_owned_private_and_idempotent(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "asset-owner@example.com")
        # A signed Web-only account can open the native Portal route without
        # Telegram link or any bridge configuration.
        assert first.get("/asset-vault").status_code == 200
        denied = first.post(
            "/api/v1/asset-vault/upload",
            headers={"Idempotency-Key": "asset-vault-upload-0001"},
            data={"display_name": "Brief"},
            files={"file": ("brief.txt", b"Noi dung an toan", "text/plain")},
        )
        assert denied.status_code == 403

        uploaded = upload_text(first, csrf, key="asset-vault-upload-0001")
        assert uploaded.status_code == 200
        payload = uploaded.json()
        assert payload["ok"] is True
        asset = payload["data"]["asset"]
        assert asset["state"] == "active"
        assert "storage_key" not in uploaded.text
        assert "sha256" not in uploaded.text

        replay = upload_text(first, csrf, key="asset-vault-upload-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["asset"]["id"] == asset["id"]
        conflicting_replay = upload_text(
            first,
            csrf,
            key="asset-vault-upload-0001",
            content=b"Noi dung khac",
        )
        assert conflicting_replay.status_code == 409

        listing = first.get("/api/v1/asset-vault")
        assert listing.status_code == 200
        assert listing.json()["data"]["items"] == [asset]
        detail = first.get(f"/api/v1/asset-vault/{asset['id']}")
        assert detail.json()["data"]["asset"] == asset

        download = first.get(f"/api/v1/asset-vault/{asset['id']}/download")
        assert download.status_code == 200
        assert download.content == b"Noi dung Web Workspace an toan"
        assert "attachment" in download.headers["content-disposition"]
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["referrer-policy"] == "no-referrer"
        assert download.headers["content-security-policy"] == "sandbox"

        with sqlite3.connect(tmp_path / "copyfast-assets-test.db") as conn:
            audit = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action='web.asset_vault.upload'"
            ).fetchone()
        assert audit and audit[0] == asset["id"]
        assert "brief.txt" not in audit[1]
        assert "Noi dung" not in audit[1]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "asset-other@example.com")
            hidden = second.get(f"/api/v1/asset-vault/{asset['id']}")
            assert hidden.json()["ok"] is False
            assert hidden.json()["error_code"] == "WEB_ASSET_NOT_FOUND"
            hidden_download = second.get(f"/api/v1/asset-vault/{asset['id']}/download")
            assert hidden_download.json()["error_code"] == "WEB_ASSET_NOT_FOUND"
            blocked_archive = second.post(
                f"/api/v1/asset-vault/{asset['id']}/archive",
                headers={"X-CSRF-Token": csrf_second, "Idempotency-Key": "asset-vault-other-archive-0001"},
            )
            assert blocked_archive.json()["error_code"] == "WEB_ASSET_NOT_FOUND"

        archived = first.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-archive-0001"},
        )
        assert archived.status_code == 200
        assert archived.json()["data"]["asset"]["state"] == "archived"
        archived_replay = first.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-archive-0001"},
        )
        assert archived_replay.json() == archived.json()
        assert first.get(f"/api/v1/asset-vault/{asset['id']}/download").json()["error_code"] == "WEB_ASSET_NOT_FOUND"
        archived_list = first.get("/api/v1/asset-vault?state=archived")
        assert archived_list.json()["data"]["items"][0]["id"] == asset["id"]


def test_asset_vault_rejects_unsafe_input_and_fails_closed_when_blob_changes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "asset-safety@example.com")
        unsupported = upload_text(client, csrf, key="asset-vault-unsupported-0001", name="malware.exe")
        assert unsupported.status_code == 415
        mime_mismatch = client.post(
            "/api/v1/asset-vault/upload",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-mime-mismatch-0001"},
            files={"file": ("brief.txt", b"Noi dung", "application/pdf")},
        )
        assert mime_mismatch.status_code == 415
        invalid_magic = client.post(
            "/api/v1/asset-vault/upload",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-magic-mismatch-0001"},
            files={"file": ("photo.png", b"not-a-png", "image/png")},
        )
        assert invalid_magic.status_code == 422
        invalid_docx = client.post(
            "/api/v1/asset-vault/upload",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-docx-invalid-0001"},
            files={"file": ("brief.docx", b"not-a-zip", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert invalid_docx.status_code == 422
        too_large = upload_text(
            client,
            csrf,
            key="asset-vault-oversize-0001",
            content=b"x" * (1024 * 1024 + 1),
        )
        assert too_large.status_code == 413

        asset = upload_text(client, csrf, key="asset-vault-tamper-0001").json()["data"]["asset"]
        with sqlite3.connect(tmp_path / "copyfast-assets-test.db") as conn:
            storage_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (asset["id"],)).fetchone()[0]
        private_file = Path(tmp_path / "private-web-assets") / storage_key
        private_file.write_bytes(b"tampered")
        unavailable = client.get(f"/api/v1/asset-vault/{asset['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_ASSET_UNAVAILABLE"
        assert client.get(f"/api/v1/asset-vault/{asset['id']}").json()["error_code"] == "WEB_ASSET_NOT_FOUND"


def test_archiving_a_private_blob_does_not_bypass_account_quota(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "1")
        csrf = register_and_login(client, "asset-quota@example.com")
        first = upload_text(
            client,
            csrf,
            key="asset-vault-quota-first-0001",
            content=b"q" * (700 * 1024),
        )
        asset = first.json()["data"]["asset"]
        archived = client.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-quota-archive-0001"},
        )
        assert archived.json()["ok"] is True
        blocked = upload_text(
            client,
            csrf,
            key="asset-vault-quota-second-0001",
            content=b"r" * (400 * 1024),
        )
        assert blocked.status_code == 413


def test_asset_vault_validates_filename_and_production_volume_boundary(tmp_path, monkeypatch):
    module = importlib.import_module("copyfast_assets")
    with pytest.raises(HTTPException):
        module._safe_filename("../brief.txt")
    with pytest.raises(HTTPException):
        module._safe_filename("brief\r\n.txt")

    database = importlib.import_module("copyfast_db")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "not-a-volume"))
    with pytest.raises(RuntimeError):
        database.asset_vault_directory()

    volume = tmp_path / "railway-volume"
    volume.mkdir()
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(volume / "vault"))
    assert database.asset_vault_directory() == (volume / "vault").resolve()


def test_asset_vault_never_imports_bot_bridge_or_exposes_a_public_storage_path():
    source = Path("copyfast_assets.py").read_text(encoding="utf-8")
    assert "copyfast_bridge" not in source
    assert "bridge_request" not in source
    assert 'app.mount("/asset-vault"' not in Path("app.py").read_text(encoding="utf-8")
