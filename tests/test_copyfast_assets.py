"""Security and ownership contracts for the native Web Asset Vault."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
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


def upload_text(
    client: TestClient,
    csrf: str,
    *,
    key: str,
    content: bytes = b"Noi dung Web Workspace an toan",
    name: str = "brief.txt",
    display_name: str = "Brief ra mat",
    project_id: str = "",
):
    data = {"display_name": display_name}
    if project_id:
        data["project_id"] = project_id
    return client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data=data,
        files={"file": (name, content, "text/plain")},
    )


def seed_typed_reference_assets(db_path: Path, email: str, *, kind: str, count: int = 101) -> list[str]:
    """Seed a realistic large owner-scoped reference library without uploads.

    The interactive upload API intentionally has conservative body limits, so
    direct metadata fixtures are the only practical way to exercise the
    picker contract beyond its first 50 rows.  The list endpoint must never
    dereference these private storage keys.
    """
    account_email = str(email).strip().lower()
    media_by_kind = {
        "pdf": ((".pdf", "application/pdf"),),
        "image": (
            (".jpg", "image/jpeg"),
            (".jpeg", "image/jpeg"),
            (".png", "image/png"),
            (".webp", "image/webp"),
        ),
        "subtitle": (
            (".srt", "application/x-subrip"),
            (".vtt", "text/vtt"),
        ),
    }
    assert kind in media_by_kind
    label = {"pdf": "PDF", "image": "Image", "subtitle": "Subtitle"}[kind]
    ids: list[str] = []
    with sqlite3.connect(db_path) as conn:
        account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (account_email,)).fetchone()
        assert account
        account_id = str(account[0])
        for index in range(count):
            asset_id = str(uuid.uuid4())
            extension, content_type = media_by_kind[kind][index % len(media_by_kind[kind])]
            timestamp = f"2026-07-16T00:{index // 60:02d}:{index % 60:02d}+00:00"
            conn.execute(
                """INSERT INTO web_asset_files
                   (id, account_id, project_id, display_name, original_filename, extension, content_type,
                    byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
                   VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
                (
                    asset_id,
                    account_id,
                    f"{label} typed reference {index:03d}",
                    f"{label.lower()}-original-{index:03d}{extension}",
                    extension,
                    content_type,
                    1024 + index,
                    f"{index + 1:064x}",
                    f"private-reference-blobs/{account_id}/{asset_id}.blob",
                    timestamp,
                    timestamp,
                ),
            )
            ids.append(asset_id)
    return ids


def seed_malformed_reference_assets(db_path: Path, email: str) -> list[str]:
    """Rows that look close to a source type but must never enter a picker."""
    malformed_pairs = (
        (".pdf", "image/png"),
        (".png", "application/pdf"),
        (".gif", "image/gif"),
        (".txt", "text/plain"),
        (".srt", "text/plain"),
        (".srt", "text/vtt"),
        (".vtt", "application/x-subrip"),
    )
    ids: list[str] = []
    with sqlite3.connect(db_path) as conn:
        account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (str(email).strip().lower(),)).fetchone()
        assert account
        account_id = str(account[0])
        for index, (extension, content_type) in enumerate(malformed_pairs):
            asset_id = str(uuid.uuid4())
            timestamp = f"2026-07-16T01:00:0{index}+00:00"
            conn.execute(
                """INSERT INTO web_asset_files
                   (id, account_id, project_id, display_name, original_filename, extension, content_type,
                    byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
                   VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
                (
                    asset_id,
                    account_id,
                    f"Malformed typed reference {index}",
                    f"malformed-reference-{index}{extension}",
                    extension,
                    content_type,
                    2048 + index,
                    f"{1000 + index:064x}",
                    f"private-reference-blobs/{account_id}/malformed-{asset_id}.blob",
                    timestamp,
                    timestamp,
                ),
            )
            ids.append(asset_id)
    return ids


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
        assert listing.json()["status"] == "completed"
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
                json={"expected_revision": 1},
            )
            assert blocked_archive.json()["error_code"] == "WEB_ASSET_NOT_FOUND"

        archived = first.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-archive-0001"},
            json={"expected_revision": 1},
        )
        assert archived.status_code == 200
        assert archived.json()["data"]["asset"]["state"] == "archived"
        archived_replay = first.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-vault-archive-0001"},
            json={"expected_revision": 1},
        )
        assert archived_replay.json() == archived.json()
        assert first.get(f"/api/v1/asset-vault/{asset['id']}/download").json()["error_code"] == "WEB_ASSET_NOT_FOUND"
        archived_list = first.get("/api/v1/asset-vault?state=archived")
        assert archived_list.json()["data"]["items"][0]["id"] == asset["id"]


def test_asset_vault_library_search_filters_pagination_and_owner_scope(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "asset-library-owner@example.com")
        project = owner.post(
            "/api/v1/projects",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Asset Library Launch",
                "summary": "Project scope for private files",
                "objective": "Review files",
                "idempotency_key": "asset-library-project-0001",
            },
        )
        assert project.status_code == 200
        project_id = project.json()["data"]["project"]["id"]

        first = upload_text(
            owner,
            csrf,
            key="asset-library-upload-0001",
            name="launch-brief.txt",
            display_name="Launch brief",
            project_id=project_id,
        ).json()["data"]["asset"]
        second = upload_text(
            owner,
            csrf,
            key="asset-library-upload-0002",
            name="launch-storyboard.txt",
            display_name="Launch storyboard",
        ).json()["data"]["asset"]
        archived = upload_text(
            owner,
            csrf,
            key="asset-library-upload-0003",
            name="archive-launch.txt",
            display_name="Archived launch notes",
            project_id=project_id,
        ).json()["data"]["asset"]
        archive = owner.post(
            f"/api/v1/asset-vault/{archived['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-library-archive-0001"},
            json={"expected_revision": 1},
        )
        assert archive.status_code == 200

        active_page_one = owner.get("/api/v1/asset-vault", params={"q": "launch", "limit": 1})
        assert active_page_one.status_code == 200
        first_page_data = active_page_one.json()["data"]
        assert first_page_data["state"] == "active"
        assert first_page_data["filters"] == {"q": "launch", "state": "active", "project_id": None, "reference_kind": "all"}
        assert first_page_data["pagination"] == {"limit": 1, "offset": 0, "returned": 1}
        assert first_page_data["has_more"] is True
        assert first_page_data["next_offset"] == 1
        first_page_ids = {item["id"] for item in first_page_data["items"]}

        active_page_two = owner.get("/api/v1/asset-vault", params={"q": "launch", "limit": 1, "offset": 1})
        assert active_page_two.status_code == 200
        second_page_data = active_page_two.json()["data"]
        assert second_page_data["pagination"] == {"limit": 1, "offset": 1, "returned": 1}
        assert second_page_data["has_more"] is False
        assert second_page_data["next_offset"] is None
        second_page_ids = {item["id"] for item in second_page_data["items"]}
        assert first_page_ids.isdisjoint(second_page_ids)
        assert first_page_ids | second_page_ids == {first["id"], second["id"]}

        in_project = owner.get("/api/v1/asset-vault", params={"project_id": project_id, "q": "launch"})
        assert {item["id"] for item in in_project.json()["data"]["items"]} == {first["id"]}
        all_project_states = owner.get(
            "/api/v1/asset-vault",
            params={"project_id": project_id, "q": "launch", "state": "all"},
        )
        assert {item["id"] for item in all_project_states.json()["data"]["items"]} == {first["id"], archived["id"]}
        archived_only = owner.get("/api/v1/asset-vault", params={"state": "archived"})
        assert {item["id"] for item in archived_only.json()["data"]["items"]} == {archived["id"]}

        with make_client(tmp_path, monkeypatch) as other:
            other_csrf = register_and_login(other, "asset-library-other@example.com")
            foreign = upload_text(
                other,
                other_csrf,
                key="asset-library-other-upload-0001",
                name="launch-private.txt",
                display_name="Launch private other account",
            ).json()["data"]["asset"]
            own_search = owner.get("/api/v1/asset-vault", params={"q": "launch", "state": "all"})
            assert foreign["id"] not in {item["id"] for item in own_search.json()["data"]["items"]}

        assert owner.get("/api/v1/asset-vault", params={"state": "unavailable"}).status_code == 422
        assert owner.get("/api/v1/asset-vault", params={"project_id": "not-a-project"}).status_code == 422
        assert owner.get("/api/v1/asset-vault", params={"q": "api_token=very-secret-token"}).status_code == 422
        assert owner.get("/api/v1/asset-vault", params={"q": "x" * 101}).status_code == 422


def test_asset_vault_typed_reference_picker_filters_pages_and_redacts_private_storage(tmp_path, monkeypatch):
    """Typed picker pages remain complete, owner-scoped and metadata-only."""
    db_path = tmp_path / "copyfast-assets-test.db"
    with make_client(tmp_path, monkeypatch) as owner:
        register_and_login(owner, "typed-reference-owner@example.com")
        with make_client(tmp_path, monkeypatch) as other:
            register_and_login(other, "typed-reference-other@example.com")

        # 101 items forces three distinct 50-row pages, including the old
        # asset that a first-page-only client would otherwise hide.
        owner_pdf_ids = seed_typed_reference_assets(db_path, "typed-reference-owner@example.com", kind="pdf")
        owner_image_ids = seed_typed_reference_assets(db_path, "typed-reference-owner@example.com", kind="image")
        owner_subtitle_ids = seed_typed_reference_assets(db_path, "typed-reference-owner@example.com", kind="subtitle")
        malformed_ids = seed_malformed_reference_assets(db_path, "typed-reference-owner@example.com")
        foreign_pdf_ids = seed_typed_reference_assets(db_path, "typed-reference-other@example.com", kind="pdf")
        foreign_image_ids = seed_typed_reference_assets(db_path, "typed-reference-other@example.com", kind="image")
        foreign_subtitle_ids = seed_typed_reference_assets(db_path, "typed-reference-other@example.com", kind="subtitle")

        allowed_pairs = {
            "pdf": {(".pdf", "application/pdf")},
            "image": {
                (".jpg", "image/jpeg"),
                (".jpeg", "image/jpeg"),
                (".png", "image/png"),
                (".webp", "image/webp"),
            },
            "subtitle": {
                (".srt", "application/x-subrip"),
                (".vtt", "text/vtt"),
            },
        }
        for kind, expected_ids in (
            ("pdf", owner_pdf_ids),
            ("image", owner_image_ids),
            ("subtitle", owner_subtitle_ids),
        ):
            pages = []
            raw_pages = []
            for offset, expected_returned, expected_more, expected_next in (
                (0, 50, True, 50),
                (50, 50, True, 100),
                (100, 1, False, None),
            ):
                response = owner.get(
                    "/api/v1/asset-vault",
                    params={
                        "reference_kind": kind,
                        "q": "typed reference",
                        "state": "active",
                        "limit": 50,
                        "offset": offset,
                    },
                )
                assert response.status_code == 200
                raw_pages.append(response.text)
                data = response.json()["data"]
                assert data["filters"] == {
                    "q": "typed reference",
                    "state": "active",
                    "project_id": None,
                    "reference_kind": kind,
                }
                assert data["pagination"] == {"limit": 50, "offset": offset, "returned": expected_returned}
                assert data["has_more"] is expected_more
                assert data["next_offset"] == expected_next
                assert len(data["items"]) == expected_returned
                assert all((item["extension"], item["content_type"]) in allowed_pairs[kind] for item in data["items"])
                assert all({"storage_key", "sha256", "account_id"}.isdisjoint(item) for item in data["items"])
                pages.append({item["id"] for item in data["items"]})

            assert pages[0].isdisjoint(pages[1])
            assert pages[0].isdisjoint(pages[2])
            assert pages[1].isdisjoint(pages[2])
            assert set().union(*pages) == set(expected_ids)
            assert not set().union(*pages).intersection(malformed_ids)
            assert not set().union(*pages).intersection(
                set(foreign_pdf_ids) | set(foreign_image_ids) | set(foreign_subtitle_ids)
            )
            assert all("private-reference-blobs" not in body for body in raw_pages)

        default_kind = owner.get(
            "/api/v1/asset-vault",
            params={"q": "typed reference", "state": "active", "limit": 1},
        )
        assert default_kind.status_code == 200
        assert default_kind.json()["data"]["filters"]["reference_kind"] == "all"
        assert owner.get("/api/v1/asset-vault", params={"reference_kind": "video"}).status_code == 422
        assert owner.get("/api/v1/asset-vault", params={"reference_kind": "subtitles"}).status_code == 422


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
        all_visible = client.get("/api/v1/asset-vault", params={"state": "all"})
        assert asset["id"] not in {item["id"] for item in all_visible.json()["data"]["items"]}


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
            json={"expected_revision": 1},
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
