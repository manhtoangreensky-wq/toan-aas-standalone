"""Focused privacy and pagination contracts for Project Package history.

Project Packages are immutable Web-native artifacts, not Bot packages.  These
tests deliberately keep the fixture small while exercising the two history
surfaces that can grow without bound: the account-wide archive and one
Project's archive.  The assertions only depend on public API output, apart
from deterministic timestamps and an injected internal failure marker used to
prove redaction.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")

MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "project-package-pagination.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "project-package-pagination-session-secret")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Package Pagination Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def create_project_with_document(client: TestClient, csrf: str, suffix: str) -> dict:
    project_response = client.post(
        "/api/v1/projects",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": f"Project Package Pagination {suffix}",
            "summary": "Lịch sử export Web riêng tư.",
            "objective": "Kiểm thử phân trang an toàn.",
            "idempotency_key": f"package-pagination-project-{suffix}-0001",
        },
    )
    assert project_response.status_code == 200
    project = project_response.json()["data"]["project"]
    document_response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        headers={"X-CSRF-Token": csrf},
        json={
            "kind": "brief",
            "title": f"Brief {suffix}",
            "content": "Nội dung snapshot tối thiểu để tạo ZIP private.",
            "idempotency_key": f"package-pagination-document-{suffix}-0001",
        },
    )
    assert document_response.status_code == 200
    return project


def export_package(client: TestClient, csrf: str, project_id: str, ordinal: int) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/packages",
        headers={"X-CSRF-Token": csrf},
        json={"idempotency_key": f"package-pagination-export-{ordinal:04d}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    package = payload["data"]["package"]
    assert package["download_ready"] is True
    return package


def set_listing_order(db_path: Path, packages: list[dict], secret: str) -> None:
    """Set distinct ordering keys without observing any private DB data."""
    with sqlite3.connect(db_path) as connection:
        for index, package in enumerate(packages, start=1):
            connection.execute(
                "UPDATE web_project_packages SET updated_at=?, failure_code=? WHERE id=?",
                (f"2026-07-16T00:00:0{index}+00:00", secret, package["id"]),
            )


def assert_private_public_item(item: dict, secret: str) -> None:
    forbidden = {
        "account_id", "canonical_user_id", "failure_code", "storage_key", "sha256",
        "snapshot_digest", "source_snapshot_json", "idempotency_key", "request_fingerprint",
        "path", "filesystem", "provider", "payment", "payos",
    }
    assert not (forbidden & set(item))
    assert secret not in repr(item)


def assert_page(
    response,
    expected_ids: list[str],
    *,
    has_more: bool,
    next_offset: int | None,
    secret: str,
    project_id: str | None = None,
) -> dict:
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert [item["id"] for item in data["items"]] == expected_ids
    assert data["has_more"] is has_more
    assert data["next_offset"] == next_offset
    if project_id is None:
        assert "project_id" not in data
    else:
        assert data["project_id"] == project_id
    assert secret not in response.text
    for item in data["items"]:
        assert_private_public_item(item, secret)
    return data


def test_project_package_history_pagination_is_owner_scoped_and_redacted(tmp_path, monkeypatch) -> None:
    secret = "PRIVATE_PACKAGE_FAILURE_MARKER_MUST_NEVER_REACH_BROWSER"
    database = tmp_path / "project-package-pagination.db"
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "project-package-pagination-owner@example.com")
        first_project = create_project_with_document(owner, csrf, "first")
        second_project = create_project_with_document(owner, csrf, "second")
        first_old = export_package(owner, csrf, first_project["id"], 1)
        first_middle = export_package(owner, csrf, first_project["id"], 2)
        first_new = export_package(owner, csrf, first_project["id"], 3)
        second_newest = export_package(owner, csrf, second_project["id"], 4)
        set_listing_order(database, [first_old, first_middle, first_new, second_newest], secret)

        all_first = owner.get("/api/v1/project-packages", params={"limit": 2, "offset": 0})
        assert_page(
            all_first,
            [second_newest["id"], first_new["id"]],
            has_more=True,
            next_offset=2,
            secret=secret,
        )
        all_second = owner.get("/api/v1/project-packages", params={"limit": 2, "offset": 2})
        assert_page(
            all_second,
            [first_middle["id"], first_old["id"]],
            has_more=False,
            next_offset=None,
            secret=secret,
        )

        scoped_first = owner.get(
            f"/api/v1/projects/{first_project['id']}/packages",
            params={"limit": 2, "offset": 0},
        )
        assert_page(
            scoped_first,
            [first_new["id"], first_middle["id"]],
            has_more=True,
            next_offset=2,
            secret=secret,
            project_id=first_project["id"],
        )
        scoped_second = owner.get(
            f"/api/v1/projects/{first_project['id']}/packages",
            params={"limit": 2, "offset": 2},
        )
        assert_page(
            scoped_second,
            [first_old["id"]],
            has_more=False,
            next_offset=None,
            secret=secret,
            project_id=first_project["id"],
        )

        # Preserve the legacy bounded limit behavior for existing callers.
        clamped = owner.get("/api/v1/project-packages", params={"limit": 0, "offset": 0})
        assert_page(clamped, [second_newest["id"]], has_more=True, next_offset=1, secret=secret)

        # A usable listing may advertise a same-origin attachment, but neither
        # list response can disclose the internal storage identity used by it.
        assert all_first.json()["data"]["items"][0]["download_ready"] is True
        own_download = owner.get(f"/api/v1/project-packages/{first_new['id']}/download")
        assert own_download.status_code == 200
        assert own_download.headers["cache-control"] == "no-store, private"

        for path in (
            "/api/v1/project-packages?offset=-1",
            "/api/v1/project-packages?offset=10001",
            "/api/v1/project-packages?offset=not-an-offset",
            f"/api/v1/projects/{first_project['id']}/packages?offset=-1",
            f"/api/v1/projects/{first_project['id']}/packages?offset=10001",
            f"/api/v1/projects/{first_project['id']}/packages?offset=not-an-offset",
        ):
            invalid = owner.get(path)
            assert invalid.status_code == 422
            assert secret not in invalid.text

    with make_client(tmp_path, monkeypatch) as other:
        register_and_login(other, "project-package-pagination-other@example.com")
        hidden_all = other.get("/api/v1/project-packages", params={"limit": 2, "offset": 0})
        assert_page(hidden_all, [], has_more=False, next_offset=None, secret=secret)
        hidden_project = other.get(f"/api/v1/projects/{first_project['id']}/packages", params={"limit": 2, "offset": 0})
        assert hidden_project.status_code == 200
        assert hidden_project.json()["error_code"] == "WEB_PROJECT_NOT_FOUND"
        assert secret not in hidden_project.text
        blocked_download = other.get(f"/api/v1/project-packages/{first_new['id']}/download")
        assert blocked_download.status_code == 200
        assert blocked_download.json()["error_code"] == "WEB_PROJECT_PACKAGE_NOT_FOUND"
        assert secret not in blocked_download.text


def test_project_package_portal_has_independent_global_and_project_history_pagers() -> None:
    """The browser keeps a separate cursor for global vs. each Project view."""
    for token in (
        "PROJECT_PACKAGE_LIST_LIMIT = 50",
        "PROJECT_PACKAGE_MAX_LIST_OFFSET = 10000",
        "function projectPackageListOffset",
        "function projectPackageListingProjection",
        "projectPackageListing",
        "projectPackageProjectListings",
        "projectPackageProjectItems",
        'action === "project-package-page"',
        "fields.__projectPackageOffset",
        "fields.__projectPackageProjectId",
    ):
        assert token in INTEGRATION

    for token in (
        "projectPackageListing",
        "projectPackageProjectListings",
        "projectPackageProjectItems",
        "project-package-page",
        "data-project-package-offset",
        "data-project-package-project-id",
    ):
        assert token in PORTAL

    hydration = INTEGRATION[
        INTEGRATION.index("async function hydrateProjectPackages"):INTEGRATION.index("async function hydrateStudioDocument")
    ]
    assert "localStorage" not in hydration
    assert "bridge_request" not in hydration
    assert "CORE_BRIDGE" not in hydration
