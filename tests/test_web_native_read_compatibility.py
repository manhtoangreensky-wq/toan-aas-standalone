"""Focused integration coverage for generic Web-native Jobs / Assets reads."""

from __future__ import annotations

import importlib
from io import BytesIO
from pathlib import Path
import sqlite3
import sys
from zipfile import ZipFile

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_native_read_models", "copyfast_api", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "native-read-compatibility.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "native-read-compatibility-session-secret")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "5")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "20")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ROOT", str(tmp_path / "private-packages"))
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_MAX_MB", "5")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_QUOTA_MB", "20")
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
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Native Read Account",
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def create_native_records(client: TestClient, csrf: str, *, tag: str) -> tuple[dict, dict, bytes]:
    source_bytes = f"private native source for {tag}".encode("utf-8")
    uploaded = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": f"native-read-asset-{tag}-0001"},
        data={"display_name": f"Private source {tag}"},
        files={"file": (f"{tag}-brief.txt", source_bytes, "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    asset = uploaded.json()["data"]["asset"]

    project_response = client.post(
        "/api/v1/projects",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": f"Native package {tag}",
            "summary": "Private Web-native package test",
            "objective": "Verify generic compatibility reads",
            "idempotency_key": f"native-read-project-{tag}-0001",
        },
    )
    assert project_response.status_code == 200, project_response.text
    project = project_response.json()["data"]["project"]
    document_response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        headers={"X-CSRF-Token": csrf},
        json={
            "kind": "script",
            "title": f"Private document {tag}",
            "content": f"This document belongs only to {tag}.",
            "idempotency_key": f"native-read-document-{tag}-0001",
        },
    )
    assert document_response.status_code == 200, document_response.text
    package_response = client.post(
        f"/api/v1/projects/{project['id']}/packages",
        headers={"X-CSRF-Token": csrf},
        json={"idempotency_key": f"native-read-package-{tag}-0001"},
    )
    assert package_response.status_code == 200, package_response.text
    package = package_response.json()["data"]["package"]
    assert package["state"] == "completed"
    return asset, package, source_bytes


def _native_job(items: list[dict]) -> dict:
    return next(item for item in items if str(item.get("id") or "").startswith("wnj:v1:"))


def _native_vault_asset(items: list[dict]) -> dict:
    return next(item for item in items if str(item.get("id") or "").startswith("wna:v1:"))


def test_unlinked_accounts_receive_only_their_native_records_and_verified_downloads(tmp_path, monkeypatch):
    database_path = tmp_path / "native-read-compatibility.db"
    with make_client(tmp_path, monkeypatch) as owner:
        owner_csrf = register_and_login(owner, "native-owner@example.com")
        owner_asset, owner_package, owner_source = create_native_records(owner, owner_csrf, tag="owner")
        with sqlite3.connect(database_path) as conn:
            owner_storage_key, owner_digest = conn.execute(
                "SELECT storage_key, sha256 FROM web_project_packages WHERE id=?",
                (owner_package["id"],),
            ).fetchone()

        jobs_response = owner.get("/api/v1/jobs")
        assert jobs_response.status_code == 200, jobs_response.text
        jobs = jobs_response.json()
        assert jobs["ok"] is True
        assert jobs["status"] == "read_only"
        assert jobs["data"]["source"] == "web_native"
        job = _native_job(jobs["data"]["items"])
        assert job["source"] == "web_native"
        assert job["source_state"] == "local_only"
        assert job["status"] == "completed"
        assert job["output_available"] is True
        assert job["download_ready"] is True
        assert job["id"] != owner_package["id"]

        detail = owner.get(f"/api/v1/jobs/{job['id']}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["data"]["id"] == job["id"]
        assert detail.json()["data"]["source"] == "web_native"

        assets_response = owner.get("/api/v1/assets")
        assert assets_response.status_code == 200, assets_response.text
        assets = assets_response.json()
        assert assets["data"]["source"] == "web_native"
        vault_asset = _native_vault_asset(assets["data"]["items"])
        job_output_asset = next(item for item in assets["data"]["items"] if item["id"] == job["id"])
        assert vault_asset["download_ready"] is False
        assert vault_asset["output_available"] is False
        assert job_output_asset["download_ready"] is True
        assert job_output_asset["source"] == "web_native"

        public_text = jobs_response.text + assets_response.text + detail.text
        for private_value in (owner_asset["id"], owner_package["id"], owner_storage_key, owner_digest):
            assert private_value not in public_text
        assert "storage_key" not in public_text
        assert "sha256" not in public_text

        vault_download = owner.get(f"/api/v1/assets/{vault_asset['id']}/download")
        assert vault_download.status_code == 200
        assert vault_download.content == owner_source
        package_download = owner.get(f"/api/v1/assets/{job['id']}/download")
        assert package_download.status_code == 200
        with ZipFile(BytesIO(package_download.content)) as archive:
            assert "documents/001-script.txt" in archive.namelist()

    with make_client(tmp_path, monkeypatch) as other:
        other_csrf = register_and_login(other, "native-other@example.com")
        other_asset, other_package, other_source = create_native_records(other, other_csrf, tag="other")
        other_jobs = other.get("/api/v1/jobs").json()
        other_job = _native_job(other_jobs["data"]["items"])
        assert other_job["id"] != job["id"]
        assert owner_package["id"] not in str(other_jobs)
        assert other_package["id"] not in str(other_jobs)
        assert owner_asset["id"] not in str(other_jobs)
        assert other_asset["id"] not in str(other_jobs)

        foreign_detail = other.get(f"/api/v1/jobs/{job['id']}")
        assert foreign_detail.json()["error_code"] == "WEB_NATIVE_JOB_NOT_FOUND"
        foreign_package = other.get(f"/api/v1/assets/{job['id']}/download")
        assert foreign_package.json()["error_code"] == "WEB_NATIVE_ASSET_UNAVAILABLE"
        foreign_vault = other.get(f"/api/v1/assets/{vault_asset['id']}/download")
        assert foreign_vault.json()["error_code"] == "WEB_ASSET_NOT_FOUND"
        assert owner_source not in foreign_package.content
        assert owner_source not in foreign_vault.content
        assert other.get(f"/api/v1/assets/{_native_vault_asset(other.get('/api/v1/assets').json()['data']['items'])['id']}/download").content == other_source


def test_successful_canonical_lists_keep_explicit_web_native_items(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "native-bridge@example.com")
        _asset, _package, _source = create_native_records(client, csrf, tag="bridge")
        database_path = tmp_path / "native-read-compatibility.db"
        with sqlite3.connect(database_path) as conn:
            conn.execute(
                "UPDATE web_accounts SET canonical_user_id=? WHERE email=?",
                ("telegram-native-bridge", "native-bridge@example.com"),
            )

        api = importlib.import_module("copyfast_api")
        bridge_calls: list[str] = []

        async def canonical_bridge(method, path, **_kwargs):
            bridge_calls.append(f"{method}:{path}")
            if path.endswith("/jobs"):
                items = [{"id": "canonical-job-1", "feature": "video_single", "status": "completed"}]
            else:
                items = [{"id": "canonical-asset-1", "feature": "video_single", "status": "completed", "download_ready": True}]
            return {"ok": True, "status": "completed", "message": "canonical", "data": {"items": items}}

        monkeypatch.setattr(api, "bridge_configured", lambda: True)
        monkeypatch.setattr(api, "bridge_request", canonical_bridge)
        jobs = client.get("/api/v1/jobs").json()
        assets = client.get("/api/v1/assets").json()
        assert "canonical-job-1" in {item["id"] for item in jobs["data"]["items"]}
        assert any(item.get("source") == "web_native" for item in jobs["data"]["items"])
        assert "canonical-asset-1" in {item["id"] for item in assets["data"]["items"]}
        assert any(item.get("source") == "web_native" for item in assets["data"]["items"])
        assert jobs["data"]["source"] == "canonical_and_web_native"
        assert assets["data"]["source"] == "canonical_and_web_native"
        assert bridge_calls == ["GET:/internal/v1/jobs", "GET:/internal/v1/assets"]


def test_web_native_asset_namespace_never_reaches_canonical_job_bridge(tmp_path, monkeypatch):
    """A portal job link for a Vault ID cannot become a Bot bridge request."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "native-vault-job-route@example.com")
        create_native_records(client, csrf, tag="vault-job-route")
        assets = client.get("/api/v1/assets").json()["data"]["items"]
        vault_id = _native_vault_asset(assets)["id"]
        api = importlib.import_module("copyfast_api")
        bridge_calls: list[str] = []

        async def canonical_bridge(method, path, **_kwargs):
            bridge_calls.append(f"{method}:{path}")
            return {"ok": True, "status": "completed", "message": "unexpected", "data": {}}

        # Force the downstream canonical branch to be reachable if the route
        # fails to reserve the Web-native namespace first.
        monkeypatch.setattr(api, "_canonical_companion_ready", lambda _account: True)
        monkeypatch.setattr(api, "bridge_request", canonical_bridge)
        response = client.get(f"/api/v1/jobs/{vault_id}")

        assert response.status_code == 200
        assert response.json()["error_code"] == "WEB_NATIVE_JOB_NOT_FOUND"
        assert bridge_calls == []


def test_generic_assets_reads_completed_outputs_from_dedicated_projection(tmp_path, monkeypatch):
    """Assets must not derive deliverable outputs from the paged Jobs read."""

    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "native-dedicated-assets@example.com")
        api = importlib.import_module("copyfast_api")
        calls: list[tuple[str, int]] = []

        def completed_outputs(account_id, *, limit=100):
            calls.append((str(account_id), int(limit)))
            return []

        def unexpected_jobs(*_args, **_kwargs):
            raise AssertionError("generic Assets must not read the paged Jobs projection")

        monkeypatch.setattr(api, "list_native_completed_outputs", completed_outputs)
        monkeypatch.setattr(api, "list_native_jobs", unexpected_jobs)
        response = client.get("/api/v1/assets")

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert calls and calls[0][1] == 100
