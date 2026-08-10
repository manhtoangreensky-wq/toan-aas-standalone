"""RED contracts for copying verified Image Operation PNGs into Asset Vault."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
from PIL import Image


MODULES = [
    "app",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_auth_throttle",
    "copyfast_bridge",
    "copyfast_registry",
    "copyfast_api",
    "copyfast_projects",
    "copyfast_assets",
    "copyfast_project_packages",
    "copyfast_document_operations",
    "copyfast_image_runtime",
    "copyfast_image_operations",
    "copyfast_pages",
]


def make_client(
    tmp_path,
    monkeypatch,
    *,
    image_operation_export_enabled: bool = True,
    asset_vault_quota_mb: int = 100,
) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "image-operation-asset-export.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "image-operation-asset-export-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", str(asset_vault_quota_mb))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ROOT", str(tmp_path / "private-image-outputs"))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_RESIZE_ENABLED", "true")
    monkeypatch.setenv(
        "WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED",
        "true" if image_operation_export_enabled else "false",
    )
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_TO_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_WORD_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL",
        "CORE_BRIDGE_TOKEN",
        "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Image Export Owner",
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def image_bytes(*, size: tuple[int, int] = (160, 100), compress_level: int = 6) -> bytes:
    image = Image.new("RGB", size, (16, 80, 196))
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (240, 72 + (y % 32), 64) if x < size[0] // 2 else (32, 136, 232 - (y % 32))
    stream = BytesIO()
    try:
        image.save(stream, format="PNG", compress_level=compress_level)
        return stream.getvalue()
    finally:
        image.close()


def large_png_bytes() -> bytes:
    """A real, valid PNG larger than the minimum 1 MiB Vault quota."""
    body = image_bytes(size=(1024, 1024), compress_level=0)
    assert len(body) > 1024 * 1024
    return body


def upload_image(client: TestClient, csrf: str, *, key: str, body: bytes, name: str = "source.png") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Ảnh nguồn riêng tư"},
        files={"file": (name, body, "image/png")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["asset"]


def resize(client: TestClient, csrf: str, *, asset_id: str, key: str):
    return client.post(
        "/api/v1/image-operations/resize",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": asset_id,
            "preset": "custom",
            "target_width": 128,
            "target_height": 128,
            "fit_mode": "crop",
            "idempotency_key": key,
        },
    )


def completed_resize(client: TestClient, csrf: str, *, source_key: str, operation_key: str, body: bytes | None = None) -> tuple[dict, dict]:
    source = upload_image(
        client,
        csrf,
        key=source_key,
        body=body if body is not None else image_bytes(),
    )
    created = resize(client, csrf, asset_id=source["id"], key=operation_key)
    assert created.status_code == 200, created.text
    operation = created.json()["data"]["operation"]
    assert operation["kind"] == "image_resize"
    assert operation["state"] == "completed"
    assert operation["download_ready"] is True
    return source, operation


def export_operation(client: TestClient, csrf: str, operation_id: str, key: str):
    return client.post(
        f"/api/v1/image-operations/{operation_id}/export-to-asset-vault",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
    )


def asset_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM web_asset_files").fetchone()[0])


def operation_storage_key(db_path: Path, operation_id: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT storage_key FROM web_image_operations WHERE id=?",
            (operation_id,),
        ).fetchone()
    assert row and row[0]
    return str(row[0])


def operation_state(client: TestClient, operation_id: str) -> str:
    response = client.get(f"/api/v1/image-operations/{operation_id}")
    assert response.status_code == 200, response.text
    return str(response.json()["data"]["operation"]["state"])


def assert_safe_export_response(response) -> None:
    lowered = response.text.lower()
    for forbidden in (
        "storage_key",
        "sha256",
        "source_sha",
        "filesystem",
        "provider",
        "bridge",
        "wallet",
        "payment",
        "payos",
        "telegram",
        "bot",
        "xu",
    ):
        assert forbidden not in lowered


def test_completed_allowed_png_exports_once_to_a_distinct_verified_asset_vault_file(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "export-owner@example.com")
        source, operation = completed_resize(
            client,
            csrf,
            source_key="export-source-0001",
            operation_key="export-operation-0001",
        )
        db_path = tmp_path / "image-operation-asset-export.db"
        original = client.get(f"/api/v1/image-operations/{operation['id']}/download")
        assert original.status_code == 200, original.text
        assert original.headers["content-type"].startswith("image/png")

        exported = export_operation(client, csrf, operation["id"], "export-copy-0001")

        assert exported.status_code == 200, exported.text
        body = exported.json()
        assert body["ok"] is True
        asset = body["data"]["asset"]
        assert asset["id"] != source["id"]
        assert asset["state"] == "active"
        assert asset["extension"] == ".png"
        assert asset["content_type"] == "image/png"
        assert asset["byte_size"] == len(original.content)
        assert source["id"] not in exported.text
        assert "source.png" not in exported.text
        assert {
            "storage_key",
            "sha256",
            "source_sha256",
            "account_id",
        }.isdisjoint(asset)
        assert_safe_export_response(exported)

        saved = client.get(f"/api/v1/asset-vault/{asset['id']}/download")
        assert saved.status_code == 200, saved.text
        assert saved.content == original.content
        assert asset_count(db_path) == 2
        with sqlite3.connect(db_path) as conn:
            stored = conn.execute(
                "SELECT storage_key, sha256, state FROM web_asset_files WHERE id=?",
                (asset["id"],),
            ).fetchone()
            relation = conn.execute(
                """SELECT operation_id, account_id, asset_id, state
                   FROM web_image_operation_asset_exports WHERE operation_id=?""",
                (operation["id"],),
            ).fetchone()
            operation_owner = conn.execute(
                "SELECT account_id FROM web_image_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()
        assert stored and stored[0] and stored[1] and stored[2] == "active"
        assert relation == (operation["id"], operation_owner[0], asset["id"], "completed")
        assert operation_state(client, operation["id"]) == "completed"


def test_export_rejects_unsigned_foreign_nonexportable_and_tampered_operations(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "export-boundary-owner@example.com")
        _, operation = completed_resize(
            client,
            csrf,
            source_key="export-boundary-source-0001",
            operation_key="export-boundary-operation-0001",
        )
        db_path = tmp_path / "image-operation-asset-export.db"
        before = asset_count(db_path)

        missing_csrf = client.post(
            f"/api/v1/image-operations/{operation['id']}/export-to-asset-vault",
            headers={"Idempotency-Key": "export-no-csrf-0001"},
        )
        assert missing_csrf.status_code == 403
        assert asset_count(db_path) == before

        with make_client(tmp_path, monkeypatch) as anonymous:
            unsigned = anonymous.post(
                f"/api/v1/image-operations/{operation['id']}/export-to-asset-vault",
                headers={"Idempotency-Key": "export-anonymous-0001"},
            )
            assert unsigned.status_code == 401
        assert asset_count(db_path) == before

        with make_client(tmp_path, monkeypatch) as foreign:
            foreign_csrf = register_and_login(foreign, "export-foreign@example.com")
            hidden = export_operation(foreign, foreign_csrf, operation["id"], "export-foreign-0001")
            assert hidden.status_code == 200
            # A foreign UUID is deliberately indistinguishable from a
            # completed output that is not export-ready; neither response
            # leaks operation metadata or creates a Vault asset.
            assert hidden.json()["error_code"] == "WEB_IMAGE_OPERATION_EXPORT_NOT_READY"
            assert_safe_export_response(hidden)
        assert asset_count(db_path) == before

        _, processing = completed_resize(
            client,
            csrf,
            source_key="export-processing-source-0001",
            operation_key="export-processing-operation-0001",
        )
        _, unknown = completed_resize(
            client,
            csrf,
            source_key="export-unknown-source-0001",
            operation_key="export-unknown-operation-0001",
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_image_operations SET state='processing' WHERE id=?", (processing["id"],))
            conn.execute("UPDATE web_image_operations SET kind='unreviewed_local_png' WHERE id=?", (unknown["id"],))
            conn.commit()

        for operation_id, key in (
            (processing["id"], "export-processing-0001"),
            (unknown["id"], "export-unknown-kind-0001"),
        ):
            rejected = export_operation(client, csrf, operation_id, key)
            assert rejected.status_code >= 400 or rejected.json()["ok"] is False
            assert_safe_export_response(rejected)
            assert asset_count(db_path) == before + 2

        _, tampered = completed_resize(
            client,
            csrf,
            source_key="export-tampered-source-0001",
            operation_key="export-tampered-operation-0001",
        )
        tampered_path = tmp_path / "private-image-outputs" / operation_storage_key(db_path, tampered["id"])
        tampered_path.write_bytes(b"tampered-but-not-a-png")
        rejected_tampered = export_operation(client, csrf, tampered["id"], "export-tampered-0001")
        assert rejected_tampered.status_code == 200
        assert rejected_tampered.json()["ok"] is False
        assert_safe_export_response(rejected_tampered)
        assert operation_state(client, tampered["id"]) == "unavailable"
        assert asset_count(db_path) == before + 3


def test_export_is_disabled_by_default_for_the_route_without_creating_an_asset(tmp_path, monkeypatch):
    disabled_root = tmp_path / "disabled"
    disabled_root.mkdir()
    with make_client(disabled_root, monkeypatch, image_operation_export_enabled=False) as client:
        csrf = register_and_login(client, "export-disabled@example.com")
        _, operation = completed_resize(
            client,
            csrf,
            source_key="export-disabled-source-0001",
            operation_key="export-disabled-operation-0001",
        )
        db_path = disabled_root / "image-operation-asset-export.db"
        before = asset_count(db_path)

        disabled = export_operation(client, csrf, operation["id"], "export-disabled-copy-0001")

        assert disabled.status_code == 503
        assert_safe_export_response(disabled)
        assert asset_count(db_path) == before


def test_export_is_idempotent_quota_bound_and_keeps_original_and_exported_lifecycles_independent(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "export-replay-owner@example.com")
        _, operation = completed_resize(
            client,
            csrf,
            source_key="export-replay-source-0001",
            operation_key="export-replay-operation-0001",
        )
        db_path = tmp_path / "image-operation-asset-export.db"
        first = export_operation(client, csrf, operation["id"], "export-replay-copy-0001")
        assert first.status_code == 200, first.text
        asset = first.json()["data"]["asset"]
        original_bytes = client.get(f"/api/v1/image-operations/{operation['id']}/download").content

        replay = export_operation(client, csrf, operation["id"], "export-replay-copy-0001")
        different_key = export_operation(client, csrf, operation["id"], "export-replay-different-key-0001")
        assert replay.status_code == 200, replay.text
        assert different_key.status_code == 200, different_key.text
        assert replay.json()["data"]["asset"]["id"] == asset["id"]
        assert different_key.json()["data"]["asset"]["id"] == asset["id"]
        assert asset_count(db_path) == 2

        _, other_operation = completed_resize(
            client,
            csrf,
            source_key="export-replay-other-source-0001",
            operation_key="export-replay-other-operation-0001",
        )
        before_rebind = asset_count(db_path)
        rebind = export_operation(client, csrf, other_operation["id"], "export-replay-copy-0001")
        assert rebind.status_code == 409
        assert_safe_export_response(rebind)
        assert asset_count(db_path) == before_rebind

        lifecycle = client.get(f"/api/v1/asset-vault/{asset['id']}/lifecycle")
        assert lifecycle.status_code == 200, lifecycle.text
        revision = lifecycle.json()["data"]["lifecycle"]["lifecycle_revision"]
        archived = client.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "export-lifecycle-archive-0001"},
            json={"expected_revision": revision},
        )
        assert archived.status_code == 200, archived.text
        assert archived.json()["ok"] is True
        assert operation_state(client, operation["id"]) == "completed"
        assert client.get(f"/api/v1/image-operations/{operation['id']}/download").content == original_bytes

        archived_revision = client.get(f"/api/v1/asset-vault/{asset['id']}/lifecycle").json()["data"]["lifecycle"]["lifecycle_revision"]
        restored = client.post(
            f"/api/v1/asset-vault/{asset['id']}/restore",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": archived_revision,
                "idempotency_key": "export-lifecycle-restore-0001",
            },
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["ok"] is True

        (tmp_path / "private-image-outputs" / operation_storage_key(db_path, operation["id"])).write_bytes(b"tampered-original-output")
        guarded_download = client.get(f"/api/v1/image-operations/{operation['id']}/download")
        assert guarded_download.status_code == 200
        assert guarded_download.json()["error_code"] == "WEB_IMAGE_OPERATION_UNAVAILABLE"
        assert operation_state(client, operation["id"]) == "unavailable"
        assert client.get(f"/api/v1/asset-vault/{asset['id']}/download").content == original_bytes

    quota_root = tmp_path / "quota"
    quota_root.mkdir()
    with make_client(quota_root, monkeypatch, asset_vault_quota_mb=20) as quota_client:
        quota_csrf = register_and_login(quota_client, "export-quota@example.com")
        _, quota_operation = completed_resize(
            quota_client,
            quota_csrf,
            source_key="export-quota-source-0001",
            operation_key="export-quota-operation-0001",
            body=large_png_bytes(),
        )
        quota_db = quota_root / "image-operation-asset-export.db"
        before = asset_count(quota_db)
        monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "1")

        quota_denied = export_operation(quota_client, quota_csrf, quota_operation["id"], "export-quota-copy-0001")

        assert quota_denied.status_code == 413
        assert_safe_export_response(quota_denied)
        assert asset_count(quota_db) == before
