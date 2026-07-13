"""Security and delivery contracts for Web-native immutable Project Packages."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3
import sys
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-project-packages-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-project-package-session-secret")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ROOT", str(tmp_path / "private-project-packages"))
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_MAX_MB", "5")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_QUOTA_MB", "20")
    monkeypatch.delenv("WEBAPP_ASSET_VAULT_ENABLED", raising=False)
    monkeypatch.delenv("WEBAPP_ASSET_VAULT_ROOT", raising=False)
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Project Package Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def create_project_with_document(client: TestClient, csrf: str):
    project = client.post(
        "/api/v1/projects",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": "Ra mắt mùa hè",
            "summary": "Brief Web riêng tư",
            "objective": "Tăng chuyển đổi",
            "idempotency_key": "project-package-project-create-0001",
        },
    ).json()["data"]["project"]
    document = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        headers={"X-CSRF-Token": csrf},
        json={
            "kind": "script",
            "title": "Kịch bản mở đầu",
            "content": "Cảnh 1: mở vấn đề.\nCảnh 2: giới thiệu giải pháp.\nCảnh 3: CTA.",
            "idempotency_key": "project-package-document-create-0001",
        },
    ).json()["data"]["document"]
    return project, document


def test_project_package_is_immutable_private_and_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "package-owner@example.com")
        assert first.get("/project-packages").status_code == 200
        project, document = create_project_with_document(first, csrf)
        denied = first.post(
            f"/api/v1/projects/{project['id']}/packages",
            json={"idempotency_key": "project-package-export-0001"},
        )
        assert denied.status_code == 403

        exported = first.post(
            f"/api/v1/projects/{project['id']}/packages",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "project-package-export-0001"},
        )
        assert exported.status_code == 200
        payload = exported.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        package = payload["data"]["package"]
        assert package["project_id"] == project["id"]
        assert package["document_count"] == 1
        assert package["asset_reference_count"] == 0
        assert package["download_ready"] is True
        assert "storage_key" not in exported.text
        assert "sha256" not in exported.text

        replay = first.post(
            f"/api/v1/projects/{project['id']}/packages",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "project-package-export-0001"},
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["package"]["id"] == package["id"]

        archive_response = first.get(f"/api/v1/project-packages/{package['id']}/download")
        assert archive_response.status_code == 200
        assert archive_response.headers["cache-control"] == "no-store, private"
        assert archive_response.headers["x-content-type-options"] == "nosniff"
        assert archive_response.headers["referrer-policy"] == "no-referrer"
        assert archive_response.headers["content-security-policy"] == "sandbox"
        assert "attachment" in archive_response.headers["content-disposition"]
        with ZipFile(BytesIO(archive_response.content)) as archive:
            assert set(archive.namelist()) == {"README.md", "manifest.json", "documents/001-script.txt"}
            manifest = archive.read("manifest.json").decode("utf-8")
            source_document = archive.read("documents/001-script.txt").decode("utf-8")
        assert "Cảnh 1: mở vấn đề." in source_document
        assert "Kịch bản mở đầu" in manifest
        # The artifact is customer-owned content, never an infrastructure or
        # identity dump. There is no path/hash/account/provider/payment data.
        for forbidden in ("storage_key", "sha256", "account_id", "canonical_user", "telegram", "provider", "payment", "payos"):
            assert forbidden not in manifest.lower()

        updated = first.patch(
            f"/api/v1/projects/documents/{document['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Kịch bản đã chỉnh sửa",
                "content": "Nội dung mới sau khi đã xuất package.",
                "expected_revision": 1,
                "idempotency_key": "project-package-document-update-0001",
            },
        )
        assert updated.status_code == 200
        immutable_download = first.get(f"/api/v1/project-packages/{package['id']}/download")
        with ZipFile(BytesIO(immutable_download.content)) as archive:
            snapshot_text = archive.read("documents/001-script.txt").decode("utf-8")
        assert "Nội dung mới" not in snapshot_text
        assert "Cảnh 1: mở vấn đề." in snapshot_text

        history = first.get(f"/api/v1/projects/{project['id']}/packages")
        assert history.status_code == 200
        assert history.json()["data"]["items"][0]["id"] == package["id"]
        detail = first.get(f"/api/v1/project-packages/{package['id']}")
        assert [item["state"] for item in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]

        with sqlite3.connect(tmp_path / "copyfast-project-packages-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.project_package.export'"
            ).fetchone()
        assert audit
        assert "Kịch bản" not in audit[0]
        assert "Cảnh" not in audit[0]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "package-other@example.com")
            hidden = second.get(f"/api/v1/project-packages/{package['id']}")
            assert hidden.json()["error_code"] == "WEB_PROJECT_PACKAGE_NOT_FOUND"
            assert "Ra mắt mùa hè" not in hidden.text
            blocked = second.get(f"/api/v1/project-packages/{package['id']}/download")
            assert blocked.json()["error_code"] == "WEB_PROJECT_PACKAGE_NOT_FOUND"
            hidden_history = second.get(f"/api/v1/projects/{project['id']}/packages")
            assert hidden_history.json()["error_code"] == "WEB_PROJECT_NOT_FOUND"
            rejected = second.post(
                f"/api/v1/projects/{project['id']}/packages",
                headers={"X-CSRF-Token": csrf_second},
                json={"idempotency_key": "project-package-other-export-0001"},
            )
            assert rejected.json()["error_code"] == "WEB_PROJECT_NOT_FOUND"


def test_project_package_marks_tampered_artifact_unavailable(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "package-integrity@example.com")
        project, _document = create_project_with_document(client, csrf)
        package = client.post(
            f"/api/v1/projects/{project['id']}/packages",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "project-package-integrity-0001"},
        ).json()["data"]["package"]
        with sqlite3.connect(tmp_path / "copyfast-project-packages-test.db") as conn:
            storage_key = conn.execute("SELECT storage_key FROM web_project_packages WHERE id=?", (package["id"],)).fetchone()[0]
        private_file = Path(tmp_path / "private-project-packages") / storage_key
        private_file.write_bytes(b"tampered")
        unavailable = client.get(f"/api/v1/project-packages/{package['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_PROJECT_PACKAGE_UNAVAILABLE"
        detail = client.get(f"/api/v1/project-packages/{package['id']}")
        assert detail.json()["data"]["package"]["state"] == "unavailable"
        assert detail.json()["data"]["package"]["download_ready"] is False


def test_project_package_requires_a_separate_private_production_root(tmp_path, monkeypatch):
    database = importlib.import_module("copyfast_db")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ROOT", str(tmp_path / "not-a-volume"))
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    with pytest.raises(RuntimeError):
        database.project_package_directory()

    volume = tmp_path / "railway-volume"
    volume.mkdir()
    package_root = volume / "project-packages"
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ROOT", str(package_root))
    assert database.project_package_directory() == package_root.resolve()

    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(package_root))
    with pytest.raises(RuntimeError):
        database.project_package_directory()


def test_project_package_never_imports_bot_bridge_or_exposes_static_storage():
    source = Path("copyfast_project_packages.py").read_text(encoding="utf-8")
    assert "from copyfast_bridge" not in source
    assert "import copyfast_bridge" not in source
    assert "bridge_request(" not in source
    assert 'app.mount("/project-packages"' not in Path("app.py").read_text(encoding="utf-8")
