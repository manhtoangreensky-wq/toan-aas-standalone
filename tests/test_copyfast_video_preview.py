"""High-risk owner and delivery contracts for the private Video Inspector."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_web_engine", "copyfast_api", "copyfast_projects", "copyfast_assets",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-video-preview-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-video-preview-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "25")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    # Preview begins disabled. It has no process/runtime dependency and can be
    # enabled after startup solely for the endpoint contract under test.
    monkeypatch.setenv("WEBAPP_VIDEO_PREVIEW_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Video Preview Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def mp4_bytes() -> bytes:
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2avc1" + (b"m" * 1536)


def webm_bytes() -> bytes:
    return b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01" + (b"w" * 1536)


def upload_video(client: TestClient, csrf: str, *, key: str, name: str, content: bytes, content_type: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": f"Nguồn private {name}"},
        files={"file": (name, content, content_type)},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def assert_private_preview_headers(response, *, content_type: str, byte_size: int) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"].split(";", 1)[0] == content_type
    assert "inline" in response.headers["content-disposition"].lower()
    assert response.headers["content-length"] == str(byte_size)
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"] == "sandbox"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "accept-ranges" not in {name.lower() for name in response.headers}


def test_video_preview_is_false_by_default_then_uses_a_sealed_owner_scoped_blob_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "copyfast-video-preview-test.db"
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "preview-owner@example.com")
        source_mp4 = upload_video(
            owner, csrf, key="preview-owner-mp4-0001", name="source.mp4", content=mp4_bytes(), content_type="video/mp4"
        )
        source_webm = upload_video(
            owner, csrf, key="preview-owner-webm-0001", name="source.webm", content=webm_bytes(), content_type="video/webm"
        )
        source_mov = upload_video(
            owner, csrf, key="preview-owner-mov-0001", name="source.mov", content=mp4_bytes(), content_type="video/quicktime"
        )

        disabled = owner.get(f"/api/v1/asset-vault/{source_mp4['id']}/preview")
        assert disabled.status_code == 503
        assert disabled.headers["cache-control"] == "no-store, private"

        monkeypatch.setenv("WEBAPP_VIDEO_PREVIEW_ENABLED", "true")
        status = owner.get("/api/v1/core/status")
        assert status.status_code == 200
        assert status.json()["data"]["flags"]["video_preview_enabled"] is True

        typed_listing = owner.get("/api/v1/asset-vault", params={"state": "active", "reference_kind": "video_preview"})
        assert typed_listing.status_code == 200
        typed_items = typed_listing.json()["data"]["items"]
        assert {item["id"] for item in typed_items} == {source_mp4["id"], source_webm["id"]}
        assert {(item["extension"], item["content_type"]) for item in typed_items} == {
            (".mp4", "video/mp4"), (".webm", "video/webm")
        }
        assert source_mov["id"] not in {item["id"] for item in typed_items}

        mp4_preview = owner.get(f"/api/v1/asset-vault/{source_mp4['id']}/preview")
        assert_private_preview_headers(mp4_preview, content_type="video/mp4", byte_size=len(mp4_bytes()))
        assert mp4_preview.content == mp4_bytes()
        webm_preview = owner.get(f"/api/v1/asset-vault/{source_webm['id']}/preview")
        assert_private_preview_headers(webm_preview, content_type="video/webm", byte_size=len(webm_bytes()))
        assert webm_preview.content == webm_bytes()

        ranged = owner.get(f"/api/v1/asset-vault/{source_mp4['id']}/preview", headers={"Range": "bytes=0-10"})
        assert ranged.status_code == 416
        assert ranged.headers["cache-control"] == "no-store, private"
        assert ranged.headers["referrer-policy"] == "no-referrer"
        assert ranged.headers["content-security-policy"] == "sandbox"
        assert ranged.headers["cross-origin-resource-policy"] == "same-origin"
        assert "accept-ranges" not in {name.lower() for name in ranged.headers}

        mov = owner.get(f"/api/v1/asset-vault/{source_mov['id']}/preview")
        assert mov.status_code == 200
        assert mov.json()["error_code"] == "WEB_ASSET_NOT_FOUND"
        assert "video/quicktime" not in mov.text

        with make_client(tmp_path, monkeypatch) as other:
            # make_client deliberately starts every isolated app with Preview
            # disabled; enable it again after that fresh app has reset the
            # process environment so this assertion exercises ownership, not
            # the feature gate.
            monkeypatch.setenv("WEBAPP_VIDEO_PREVIEW_ENABLED", "true")
            register_and_login(other, "preview-other@example.com")
            foreign = other.get(f"/api/v1/asset-vault/{source_mp4['id']}/preview")
            assert foreign.status_code == 200
            assert foreign.json()["error_code"] == "WEB_ASSET_NOT_FOUND"
            assert "source.mp4" not in foreign.text

        archived = owner.post(
            f"/api/v1/asset-vault/{source_webm['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "preview-owner-archive-0001"},
            json={"expected_revision": 1},
        )
        assert archived.status_code == 200
        hidden_archived = owner.get(f"/api/v1/asset-vault/{source_webm['id']}/preview")
        assert hidden_archived.json()["error_code"] == "WEB_ASSET_NOT_FOUND"

        with sqlite3.connect(db_path) as conn:
            audit = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action='web.asset_vault.video_preview' AND target=?",
                (source_mp4["id"],),
            ).fetchone()
            storage_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (source_mp4["id"],)).fetchone()[0]
        assert audit and audit[0] == source_mp4["id"]
        assert audit[1] == f"format=mp4;bytes={len(mp4_bytes())};delivery=inline_no_range"
        for forbidden in ("source.mp4", str(storage_key), "sha256", "http", "provider"):
            assert forbidden not in audit[1].lower()

        # A private source mutation cannot be served: the endpoint marks the
        # row unavailable and returns only the generic guarded envelope.
        private_file = Path(tmp_path / "private-web-assets") / storage_key
        private_file.write_bytes(b"tampered-video")
        tampered = owner.get(f"/api/v1/asset-vault/{source_mp4['id']}/preview")
        assert tampered.status_code == 200
        assert tampered.json()["error_code"] == "WEB_ASSET_UNAVAILABLE"
        with sqlite3.connect(db_path) as conn:
            state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (source_mp4["id"],)).fetchone()[0]
        assert state == "unavailable"


def test_video_preview_typed_picker_and_endpoint_reject_an_over_cap_source(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "preview-cap@example.com")
        source = upload_video(
            client, csrf, key="preview-cap-source-0001", name="cap.mp4", content=mp4_bytes(), content_type="video/mp4"
        )
        monkeypatch.setenv("WEBAPP_VIDEO_PREVIEW_ENABLED", "true")
        assets = importlib.import_module("copyfast_assets")
        monkeypatch.setattr(assets, "VIDEO_PREVIEW_MAX_BYTES", len(mp4_bytes()) - 1)

        listing = client.get("/api/v1/asset-vault", params={"reference_kind": "video_preview"})
        assert listing.status_code == 200
        assert listing.json()["data"]["items"] == []
        blocked = client.get(f"/api/v1/asset-vault/{source['id']}/preview")
        assert blocked.status_code == 200
        assert blocked.json()["error_code"] == "WEB_ASSET_NOT_FOUND"
